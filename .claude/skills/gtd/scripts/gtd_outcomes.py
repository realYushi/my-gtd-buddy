#!/usr/bin/env python3
"""Durable Session outcomes for Inbox processing.

The caller supplies dispositions; this module owns reminder mutation ordering,
pending intent, observation, Undo correlation, close, and recovery.
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gtd_reminders import AppleScriptAdapter, CommandAdapter, ReminderChanges


SCHEMA = 1
TARGETS = {
    "now": "Next Actions",
    "later": "Next Actions",
    "delegate": "Waiting For",
    "someday": "Someday",
}


class OutcomeError(Exception):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def ledger_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def fresh_ledger():
    return {"schema": SCHEMA, "active": {}, "receipts": {}, "closed": {}}


def load_ledger(path):
    path = Path(path)
    if not path.exists():
        return fresh_ledger()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OutcomeError("outcome ledger is not valid JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise OutcomeError("unsupported outcome ledger")
    for key in ("active", "receipts", "closed"):
        if not isinstance(value.get(key), dict):
            raise OutcomeError(f"malformed outcome ledger: {key}")
    return value


def fingerprint(reply):
    return json.dumps(reply, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def public_decisions(session):
    return [
        {
            "decision_id": decision["decision_id"],
            "reminder_id": decision["reminder_id"],
            "disposition": decision["disposition"],
            "observation": decision["observation"],
            "optional_changes": decision["optional_changes"],
            "undo": decision["undo"],
        }
        for decision in session["decisions"]
    ]


def turn(session):
    result = {
        "session_id": session["id"],
        "ticket": session["ticket"],
        "phase": session["phase"],
        "decisions": public_decisions(session),
    }
    if session.get("outcome") is not None:
        result["outcome"] = session["outcome"]
    if session.get("issue"):
        result["issue"] = session["issue"]
    return result


def session_outcome(session):
    decisions = session["decisions"]
    unknown = [decision for decision in decisions if decision["observation"] == "unknown"]
    processed = None if unknown else sum(
        decision["contribution"]["processed"] for decision in decisions
    )
    deferred_unknown = any(
        decision["observation"] == "unknown" and decision["disposition"] == "someday"
        for decision in decisions
    )
    deferred = None if deferred_unknown else sum(
        decision["contribution"]["deferred"] for decision in decisions
    )
    contexts_unknown = any(
        decision["observation"] == "unknown" and decision.get("context") is not None
        for decision in decisions
    )
    contexts = None
    if not contexts_unknown:
        contexts = {}
        for decision in decisions:
            for name, count in decision["contribution"]["contexts"].items():
                contexts[name] = contexts.get(name, 0) + count
    outcome = {"incomplete": bool(unknown)}
    if processed is not None:
        outcome["processed"] = processed
    if deferred is not None:
        outcome["deferred"] = deferred
    if contexts is not None:
        outcome["contexts"] = contexts
    return outcome


class ProcessingOutcomes:
    def __init__(self, changes, ledger, track_session):
        self.changes = changes
        self.ledger = Path(ledger)
        self.track_session = track_session

    @classmethod
    def from_environment(cls):
        adapter = (
            CommandAdapter(os.environ["GTD_REMINDERS_ADAPTER"])
            if os.environ.get("GTD_REMINDERS_ADAPTER")
            else AppleScriptAdapter()
        )
        skill = Path(__file__).resolve().parent.parent
        history = Path(os.environ.get("GTD_UNDO_FILE", str(skill / ".undo_stack")))
        ledger = Path(os.environ.get("GTD_OUTCOME_LEDGER", str(skill / ".processing-outcomes.json")))
        return cls(ReminderChanges(adapter, history), ledger, track_with_state)

    def begin(self, mode="process"):
        if mode != "process":
            raise OutcomeError("automatic Session outcomes support process mode only")
        with ledger_lock(self.ledger):
            ledger = load_ledger(self.ledger)
            active = ledger["active"].get("process")
            if active is not None:
                return turn(active)
            active = {
                "id": str(uuid.uuid4()),
                "mode": "process",
                "phase": "open",
                "ticket": str(uuid.uuid4()),
                "decisions": [],
                "pending": None,
                "outcome": None,
                "issue": None,
            }
            ledger["active"]["process"] = active
            atomic_json(self.ledger, ledger)
            return turn(active)

    def answer(self, ticket, reply):
        if not isinstance(reply, dict) or not isinstance(reply.get("type"), str):
            raise OutcomeError("reply must be an object with a type")
        reply_type = reply["type"]
        if reply_type not in ("dispose", "undo", "observe", "close"):
            raise OutcomeError("unsupported reply type")
        with ledger_lock(self.ledger):
            ledger = load_ledger(self.ledger)
            active = ledger["active"].get("process")
            if active is None:
                receipt = ledger["receipts"].get(ticket)
                if receipt is not None and receipt["fingerprint"] == fingerprint(reply):
                    return receipt["turn"]
                raise OutcomeError("session is not active")
            if active["ticket"] != ticket:
                receipt = ledger["receipts"].get(ticket)
                if receipt is not None and receipt["fingerprint"] == fingerprint(reply):
                    return receipt["turn"]
                raise OutcomeError("stale or unknown ticket")

            pending = active.get("pending")
            if reply_type == "close":
                if pending is not None:
                    self._resolve_pending_unknown(active, pending["reply"])
                    active["pending"] = None
                return self._close(ledger, active, ticket, reply)

            if pending is not None:
                if pending["ticket"] != ticket or pending["fingerprint"] != fingerprint(reply):
                    raise OutcomeError("a different reply is already pending for this ticket")
                issue = self._resume_pending(active, reply)
                active["pending"] = None
                active["issue"] = issue
                result = self._advance(ledger, active, ticket, reply)
                atomic_json(self.ledger, ledger)
                return result

            active["pending"] = {
                "ticket": ticket,
                "reply": reply,
                "fingerprint": fingerprint(reply),
            }
            atomic_json(self.ledger, ledger)
            issue = None
            if reply_type == "dispose":
                self._dispose(active, reply)
            elif reply_type == "undo":
                issue = self._undo(active, reply)
            else:
                self._observe(active)
            active["pending"] = None
            active["issue"] = issue
            result = self._advance(ledger, active, ticket, reply)
            atomic_json(self.ledger, ledger)
            return result

    def _advance(self, ledger, active, ticket, reply):
        active["ticket"] = str(uuid.uuid4())
        result = turn(active)
        ledger["receipts"][ticket] = {
            "fingerprint": fingerprint(reply),
            "turn": result,
        }
        return result

    def _dispose(self, active, reply):
        reminder_id = reply.get("reminder_id")
        disposition = reply.get("disposition")
        if not isinstance(reminder_id, str) or not reminder_id:
            raise OutcomeError("dispose requires a reminder_id")
        if disposition not in ("now", "later", "delegate", "someday", "delete"):
            raise OutcomeError("dispose requires a known disposition")
        options = {}
        for key in ("context", "energy", "duration", "person"):
            if reply.get(key) is not None:
                options[key] = reply[key]
        if disposition == "delegate" and not options.get("person"):
            raise OutcomeError("delegate requires a person")

        operation = {
            "now": "now", "later": "process", "delegate": "delegate",
            "someday": "defer", "delete": "delete",
        }[disposition]
        try:
            result = self.changes.change(operation, reminder_id, **options)
        except (OSError, ValueError, RuntimeError) as exc:
            result = {"status": "uncertain", "error": str(exc), "changed": {}}

        status = result.get("status")
        changed = result.get("changed") or {}
        observation = "not_applied"
        if status == "uncertain":
            observation = "unknown"
        elif disposition == "delete" and status == "changed":
            observation = "confirmed"
        elif disposition != "delete" and changed.get("list") == TARGETS[disposition]:
            observation = "confirmed"
        elif status in ("changed", "partial"):
            observation = "unknown"

        optional = "complete"
        if status == "partial":
            optional = "partial"
        elif status == "uncertain":
            optional = "unknown"
        self._append_decision(
            active, reply, observation, changed, optional, result.get("decision_id")
        )

    def _append_decision(self, active, reply, observation, changed, optional, decision_id):
        reminder_id = reply["reminder_id"]
        disposition = reply["disposition"]
        contribution = {"processed": 0, "deferred": 0, "contexts": {}}
        if observation == "confirmed":
            contribution["processed"] = 1
            if disposition == "someday":
                contribution["deferred"] = 1
            context = reply.get("context")
            if context and disposition in ("now", "later"):
                tag = "@" + str(context).lstrip("@")
                if tag in str(changed.get("body", "")).split():
                    contribution["contexts"][str(context).lstrip("@")] = 1

        undo = "permanent" if disposition == "delete" else (
            "available" if decision_id else "unknown"
        )
        active["decisions"].append({
            "decision_id": decision_id or str(uuid.uuid4()),
            "reminder_id": reminder_id,
            "disposition": disposition,
            "observation": observation,
            "optional_changes": optional,
            "undo": "unknown" if observation == "unknown" else undo,
            "context": reply.get("context"),
            "target": TARGETS.get(disposition),
            "contribution": contribution,
        })

    def _resume_pending(self, active, reply):
        reply_type = reply["type"]
        if reply_type == "observe":
            self._observe(active)
            return None
        if reply_type == "undo":
            self._mark_latest_undo_unknown(active, reply.get("decision_id"))
            return "Undo outcome is unknown after interruption"

        reminder_id = reply["reminder_id"]
        try:
            item = self.changes.adapter.read(reminder_id)
        except Exception as exc:
            self._append_decision(
                active, reply, "unknown", {}, "unknown", None
            )
            return "Pending disposition is unknown: " + str(exc)
        target = TARGETS.get(reply["disposition"])
        if reply["disposition"] == "delete":
            # A present item proves the delete did not apply; retry is safe.
            self._dispose(active, reply)
            return None
        if item.get("list") == target:
            self._append_decision(
                active,
                reply,
                "confirmed",
                {"list": item.get("list"), "body": item.get("body", "")},
                "partial",
                None,
            )
            return None
        self._dispose(active, reply)
        return None

    def _resolve_pending_unknown(self, active, reply):
        if reply.get("type") == "dispose":
            self._append_decision(active, reply, "unknown", {}, "unknown", None)
        elif reply.get("type") == "undo":
            self._mark_latest_undo_unknown(active, reply.get("decision_id"))

    def _mark_latest_undo_unknown(self, active, decision_id):
        for decision in reversed(active["decisions"]):
            if decision_id is None or decision["decision_id"] == decision_id:
                decision["observation"] = "unknown"
                decision["undo"] = "unknown"
                decision["contribution"] = {
                    "processed": 0, "deferred": 0, "contexts": {}
                }
                return

    def _undo(self, active, reply):
        wanted = reply.get("decision_id")
        if not active["decisions"] or active["decisions"][-1]["undo"] != "available":
            return "no decision is available to undo"
        expected = active["decisions"][-1]
        if wanted and wanted != expected["decision_id"]:
            raise OutcomeError("only the latest eligible decision can be undone")
        result = self.changes.undo()
        if result.get("status") == "undone" and result.get("decision_id") == expected["decision_id"]:
            expected["undo"] = "reversed"
            expected["contribution"] = {"processed": 0, "deferred": 0, "contexts": {}}
            return None
        if result.get("status") == "conflict":
            return "the reminder changed since that decision; Undo left it untouched"
        if result.get("status") in ("uncertain", "partial"):
            expected["undo"] = "unknown"
            return result.get("error") or "Undo outcome is unknown"
        return result.get("error") or "Undo did not reverse the decision"

    def _observe(self, active):
        for decision in active["decisions"]:
            if decision["observation"] != "unknown":
                continue
            try:
                item = self.changes.adapter.read(decision["reminder_id"])
            except Exception:
                continue
            if decision["disposition"] == "delete":
                decision["observation"] = "not_applied"
                decision["undo"] = "permanent"
                continue
            if item.get("list") == decision["target"]:
                decision["observation"] = "confirmed"
                decision["optional_changes"] = "unknown"
                decision["undo"] = "available"
                decision["contribution"] = {
                    "processed": 1,
                    "deferred": 1 if decision["disposition"] == "someday" else 0,
                    "contexts": {},
                }
            else:
                decision["observation"] = "not_applied"
                decision["undo"] = "unknown"

    def _close(self, ledger, active, ticket, reply):
        outcome = session_outcome(active)
        active["phase"] = "closing"
        active["outcome"] = outcome
        active["issue"] = None
        atomic_json(self.ledger, ledger)
        try:
            self.track_session(
                active["id"],
                outcome.get("processed"),
                outcome.get("deferred"),
                outcome.get("contexts"),
            )
        except (OSError, RuntimeError, ValueError) as exc:
            active["issue"] = "Session outcome is frozen; tracking delivery is pending: " + str(exc)
            atomic_json(self.ledger, ledger)
            return turn(active)

        active["phase"] = "closed"
        final = turn(active)
        ledger["closed"][active["id"]] = final
        del ledger["active"]["process"]
        ledger["receipts"][ticket] = {
            "fingerprint": fingerprint(reply),
            "turn": final,
        }
        atomic_json(self.ledger, ledger)
        return final


def track_with_state(session_id, processed, deferred, contexts):
    state = Path(__file__).resolve().parent / "state.sh"
    command = ["/bin/bash", str(state), "session", "process"]
    if processed is not None:
        command.append(str(processed))
    command.extend(["--id", session_id])
    if deferred is not None:
        command.extend(["--deferred", str(deferred)])
    if contexts is not None:
        command.extend(["--contexts", json.dumps(contexts, sort_keys=True)])
    result = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "tracking delivery failed")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("begin")
    begin.add_argument("mode", nargs="?", default="process")
    answer = commands.add_parser("answer")
    answer.add_argument("ticket")
    answer.add_argument("reply")
    args = parser.parse_args(argv)
    try:
        outcomes = ProcessingOutcomes.from_environment()
        if args.command == "begin":
            result = outcomes.begin(args.mode)
        else:
            text = sys.stdin.read() if args.reply == "-" else args.reply
            result = outcomes.answer(args.ticket, json.loads(text))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, OutcomeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
