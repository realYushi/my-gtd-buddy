#!/usr/bin/env python3
"""Compile a GTD V2 backend profile without contacting any service."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CONTAINERS = ("inbox", "next", "waiting", "someday", "projects")
LABEL_GROUPS = ("contexts", "energy", "duration")
CAPABILITIES = ("undo", "delete", "completed_query", "due_dates", "labels", "priority")
OPTIONAL_TASK_CAPABILITIES = ("modified_date", "project_links", "batch")
TASK_TOOLS = ("capture", "list", "read", "update", "complete")
SENSITIVE = ("token", "secret", "password", "api_key", "apikey", "credential")
WORKDAY = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class Issue:
    path: str
    code: str
    message: str


@dataclass(frozen=True)
class UseTool:
    name: str
    limitation: str = None


@dataclass(frozen=True)
class AskUser:
    request: str
    limitation: str = None


@dataclass(frozen=True)
class Unavailable:
    reason: str


@dataclass(frozen=True)
class Workday:
    start_minute: int
    end_minute: int
    timezone: str
    recurrence: str = "every_day"


@dataclass(frozen=True)
class Ready:
    name: str
    task_provider: str
    calendar_provider: str
    containers: object
    labels: object
    processing_style: str
    workday: Workday
    instructions: object
    live_verification: str = "unknown"


@dataclass(frozen=True)
class Rejected:
    issues: tuple


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timezone_name(value):
    if not nonempty(value):
        return False
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def compile_profile(document):
    issues = []

    def fail(path, code, message):
        issues.append(Issue(path, code, message))

    if not isinstance(document, dict):
        return Rejected((Issue("profile", "root", "must be a JSON object"),))
    if document.get("schema") != 1 or type(document.get("schema")) is not int:
        fail("schema", "schema", "must be the integer 1")
    if not nonempty(document.get("name")):
        fail("name", "name", "must be a non-empty string")

    task = document.get("task")
    if not isinstance(task, dict):
        fail("task", "task", "must be an object")
        task = {}
    mode = task.get("mode")
    if mode not in ("mcp", "manual"):
        fail("task.mode", "mode", "must be 'mcp' or 'manual'")
    if not nonempty(task.get("provider")):
        fail("task.provider", "provider", "must be a non-empty string")

    containers = task.get("containers")
    names = []
    if not isinstance(containers, dict):
        fail("task.containers", "containers", "must be an object")
        containers = {}
    else:
        for key in CONTAINERS:
            value = containers.get(key)
            if not nonempty(value):
                fail(f"task.containers.{key}", "container", "must name a container")
            else:
                names.append(value.casefold())
        if len(names) != len(set(names)):
            fail("task.containers", "containers", "the five GTD containers must be distinct")

    labels = task.get("labels")
    if not isinstance(labels, dict):
        fail("task.labels", "labels", "must be an object")
        labels = {}
    else:
        for group in LABEL_GROUPS:
            values = labels.get(group)
            if not isinstance(values, list) or any(not nonempty(item) for item in values):
                fail(f"task.labels.{group}", "labels", "must be a list of non-empty strings")

    tools = task.get("tools")
    if not isinstance(tools, dict):
        fail("task.tools", "tools", "must be an object")
        tools = {}
    for key, value in tools.items():
        if not nonempty(value):
            fail(f"task.tools.{key}", "tool", "must be a tool name")
    if mode == "manual" and tools:
        fail("task.tools", "manual_tools", "must be empty in manual mode")
    if mode == "mcp":
        for key in TASK_TOOLS:
            if not nonempty(tools.get(key)):
                fail(f"task.tools.{key}", "required_tool", "is required in mcp mode")

    capabilities = task.get("capabilities")
    if not isinstance(capabilities, dict):
        fail("task.capabilities", "capabilities", "must be an object")
        capabilities = {}
    for key in CAPABILITIES:
        if type(capabilities.get(key)) is not bool:
            fail(f"task.capabilities.{key}", "capability", "must be true or false")
    for key in OPTIONAL_TASK_CAPABILITIES:
        if key in capabilities and type(capabilities[key]) is not bool:
            fail(f"task.capabilities.{key}", "capability", "must be true or false")
    if capabilities.get("completed_query") is True and not nonempty(tools.get("completed")):
        fail("task.tools.completed", "required_tool", "is required when completed_query is true")
    if capabilities.get("delete") is True and mode == "mcp" and not nonempty(tools.get("delete")):
        fail("task.tools.delete", "required_tool", "is required in mcp mode when delete is true")
    if capabilities.get("undo") is True and mode == "mcp" and not nonempty(tools.get("undo")):
        fail("task.tools.undo", "required_tool", "is required in mcp mode when undo is true")

    calendar = document.get("calendar")
    if not isinstance(calendar, dict):
        fail("calendar", "calendar", "must be an object")
        calendar = {}
    calendar_mode = calendar.get("mode")
    if calendar_mode not in ("mcp", "manual"):
        fail("calendar.mode", "mode", "must be 'mcp' or 'manual'")
    if not nonempty(calendar.get("provider")):
        fail("calendar.provider", "provider", "must be a non-empty string")
    match = WORKDAY.fullmatch(calendar.get("workday")) if isinstance(calendar.get("workday"), str) else None
    if not match:
        fail("calendar.workday", "workday", "must look like 09:00-18:00")
        workday = None
    else:
        start = int(match.group(1)) * 60 + int(match.group(2))
        end = int(match.group(3)) * 60 + int(match.group(4))
        if start >= end:
            fail("calendar.workday", "workday", "start must be before end")
            workday = None
        else:
            workday = (start, end)

    calendar_tools = calendar.get("tools")
    if not isinstance(calendar_tools, dict):
        fail("calendar.tools", "tools", "must be an object")
        calendar_tools = {}
    for key, value in calendar_tools.items():
        if not nonempty(value):
            fail(f"calendar.tools.{key}", "tool", "must be a tool name")
    if calendar_mode == "manual" and calendar_tools:
        fail("calendar.tools", "manual_tools", "must be empty in manual mode")
    if calendar_mode == "mcp" and not nonempty(calendar_tools.get("events")):
        fail("calendar.tools.events", "required_tool", "is required in mcp mode")

    calendar_capabilities = calendar.get("capabilities", {})
    if not isinstance(calendar_capabilities, dict):
        fail("calendar.capabilities", "capabilities", "must be an object")
        calendar_capabilities = {}
    for key, value in calendar_capabilities.items():
        if key not in ("freebusy",):
            continue
        if type(value) is not bool:
            fail(f"calendar.capabilities.{key}", "capability", "must be true or false")
    if calendar_capabilities.get("freebusy") is True and not nonempty(calendar_tools.get("freebusy")):
        fail("calendar.tools.freebusy", "required_tool", "is required when freebusy is true")

    preferences = document.get("preferences")
    if not isinstance(preferences, dict):
        fail("preferences", "preferences", "must be an object")
        preferences = {}
    if preferences.get("processing_style") not in ("quick", "thorough"):
        fail("preferences.processing_style", "processing_style", "must be 'quick' or 'thorough'")
    zone = preferences.get("timezone")
    if zone is not None:
        if not timezone_name(zone):
            fail("preferences.timezone", "timezone", "must be a valid IANA timezone")
    elif calendar_mode == "mcp":
        fail("preferences.timezone", "timezone", "is required for an mcp calendar")

    def scan(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.casefold()
                if any(word in lowered for word in SENSITIVE):
                    fail(f"{path}.{key}", "credential", "looks like a credential; keep credentials out of profiles")
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")

    scan(document, "profile")
    if issues:
        return Rejected(tuple(issues))

    if mode == "manual":
        instructions = manual_task_instructions(capabilities)
    else:
        instructions = mcp_task_instructions(tools, capabilities)
    instructions.update(calendar_instructions(calendar_mode, calendar_tools, calendar_capabilities))

    return Ready(
        name=document["name"],
        task_provider=task["provider"],
        calendar_provider=calendar["provider"],
        containers=MappingProxyType({key: containers[key] for key in CONTAINERS}),
        labels=MappingProxyType({key: tuple(labels[key]) for key in LABEL_GROUPS}),
        processing_style=preferences["processing_style"],
        workday=Workday(workday[0], workday[1], zone or ""),
        instructions=MappingProxyType(instructions),
    )


def manual_task_instructions(capabilities):
    instructions = {
        need: AskUser(f"Ask the user to perform or confirm {need} in their task manager.")
        for need in TASK_TOOLS
    }
    instructions["projects"] = AskUser(
        "Ask the user to enumerate Projects or confirm each project's next action."
    )
    instructions["completed"] = AskUser(
        "Ask the user for a recent completion count; label it user-reported."
    )
    for need in ("delete", "undo", "due_dates", "labels", "priority", "modified_date",
                 "project_links", "batch"):
        if capabilities.get(need) is True:
            instructions[need] = AskUser(
                f"Ask the user to perform or confirm {need} in their task manager."
            )
        else:
            instructions[need] = Unavailable(f"{need} is not declared for this backend.")
    return instructions


def mcp_task_instructions(tools, capabilities):
    instructions = {need: UseTool(tools[need]) for need in TASK_TOOLS}
    if nonempty(tools.get("projects")):
        instructions["projects"] = UseTool(tools["projects"])
    else:
        instructions["projects"] = UseTool(
            tools["list"], "Use the list tool restricted to the Projects container."
        )
    if capabilities.get("completed_query") is True:
        instructions["completed"] = UseTool(tools["completed"])
    else:
        instructions["completed"] = AskUser(
            "Ask the user for a recent completion count; label it user-reported."
        )
    for need in ("delete", "undo"):
        if capabilities.get(need) is True:
            instructions[need] = UseTool(tools[need])
        else:
            instructions[need] = Unavailable(f"{need} is not declared for this backend.")
    for need in ("due_dates", "labels", "priority"):
        if capabilities.get(need) is True:
            instructions[need] = UseTool(
                tools["update"], f"Apply {need} through the update tool."
            )
        else:
            instructions[need] = Unavailable(f"{need} is not declared for this backend.")
    if capabilities.get("modified_date") is True:
        instructions["modified_date"] = UseTool(
            tools["list"], "Use modified dates returned by the list tool."
        )
    else:
        instructions["modified_date"] = AskUser(
            "Ask which items feel stale; do not invent ages."
        )
    if capabilities.get("project_links") is True:
        instructions["project_links"] = UseTool(
            tools.get("projects", tools["list"]),
            "Use project links returned by the backend.",
        )
    else:
        instructions["project_links"] = AskUser(
            "Ask the user to confirm each project's next action."
        )
    if capabilities.get("batch") is True:
        instructions["batch"] = UseTool(
            tools["update"], "Apply the batch through the update tool."
        )
    else:
        instructions["batch"] = Unavailable("Process item by item.")
    return instructions


def calendar_instructions(mode, tools, capabilities):
    if mode == "manual":
        instructions = {"events": AskUser("Ask the user for today's calendar events.")}
        instructions["freebusy"] = AskUser("Ask the user for available time.")
        return instructions
    instructions = {"events": UseTool(tools["events"])}
    if capabilities.get("freebusy") is True:
        instructions["freebusy"] = UseTool(tools["freebusy"])
    else:
        instructions["freebusy"] = Unavailable(
            "Use complete event data instead of a free/busy query."
        )
    return instructions


def validate(document):
    result = compile_profile(document)
    if isinstance(result, Rejected):
        return [f"{issue.path}: {issue.message}" for issue in result.issues]
    return []


def route_json(route):
    if isinstance(route, UseTool):
        return {"route": "tool", "name": route.name, "limitation": route.limitation}
    if isinstance(route, AskUser):
        return {"route": "user", "request": route.request, "limitation": route.limitation}
    return {"route": "unavailable", "reason": route.reason}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".gtd/profile.json")
    args = parser.parse_args(argv)
    path = Path(args.path).expanduser()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(json.dumps({"status": "invalid", "errors": [f"{path}: {exc}"]}))
        return 1
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "invalid", "errors": [f"{path}: invalid JSON: {exc}"]}))
        return 1
    result = compile_profile(document)
    if isinstance(result, Rejected):
        print(json.dumps({
            "status": "invalid",
            "errors": [f"{issue.path}: {issue.message}" for issue in result.issues],
        }, indent=2))
        return 1
    print(json.dumps({
        "status": "valid",
        "name": result.name,
        "task": {"provider": result.task_provider, "mode": document["task"]["mode"]},
        "calendar": {"provider": result.calendar_provider, "mode": document["calendar"]["mode"]},
        "capabilities": document["task"]["capabilities"],
        "workday": {
            "start_minute": result.workday.start_minute,
            "end_minute": result.workday.end_minute,
            "timezone": result.workday.timezone,
        },
        "instructions": {key: route_json(route) for key, route in result.instructions.items()},
        "live_verification": result.live_verification,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
