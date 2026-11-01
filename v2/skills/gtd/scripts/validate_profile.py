#!/usr/bin/env python3
"""Validate a GTD V2 backend profile without contacting any service."""
import argparse
import json
from pathlib import Path
import re
import sys


CONTAINERS = ("inbox", "next", "waiting", "someday", "projects")
LABEL_GROUPS = ("contexts", "energy", "duration")
CAPABILITIES = ("undo", "delete", "completed_query", "due_dates", "labels", "priority")
OPTIONAL_TASK_CAPABILITIES = ("modified_date", "project_links", "batch")
OPTIONAL_CALENDAR_CAPABILITIES = ("freebusy",)
TASK_TOOLS = ("capture", "list", "read", "update", "complete", "projects")
SENSITIVE = ("token", "secret", "password", "api_key", "apikey", "credential")
WORKDAY = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(document):
    errors = []

    def fail(path, message):
        errors.append(f"{path}: {message}")

    if not isinstance(document, dict):
        return ["root: must be a JSON object"]
    if document.get("schema") != 1 or type(document.get("schema")) is not int:
        fail("schema", "must be the integer 1")
    if not nonempty(document.get("name")):
        fail("name", "must be a non-empty string")

    task = document.get("task")
    if not isinstance(task, dict):
        fail("task", "must be an object")
        task = {}
    mode = task.get("mode")
    if mode not in ("mcp", "manual"):
        fail("task.mode", "must be 'mcp' or 'manual'")
    if not nonempty(task.get("provider")):
        fail("task.provider", "must be a non-empty string")

    containers = task.get("containers")
    names = []
    if not isinstance(containers, dict):
        fail("task.containers", "must be an object")
    else:
        for key in CONTAINERS:
            value = containers.get(key)
            if not nonempty(value):
                fail(f"task.containers.{key}", "must name a container")
            else:
                names.append(value.casefold())
        if len(names) != len(set(names)):
            fail("task.containers", "the five GTD containers must be distinct")

    labels = task.get("labels")
    if not isinstance(labels, dict):
        fail("task.labels", "must be an object")
    else:
        for group in LABEL_GROUPS:
            values = labels.get(group)
            if not isinstance(values, list) or any(not nonempty(item) for item in values):
                fail(f"task.labels.{group}", "must be a list of non-empty strings")

    tools = task.get("tools")
    if not isinstance(tools, dict):
        fail("task.tools", "must be an object")
        tools = {}
    for key, value in tools.items():
        if not nonempty(value):
            fail(f"task.tools.{key}", "must be a tool name")
    if mode == "mcp":
        for key in TASK_TOOLS:
            if not nonempty(tools.get(key)):
                fail(f"task.tools.{key}", "is required in mcp mode")

    capabilities = task.get("capabilities")
    if not isinstance(capabilities, dict):
        fail("task.capabilities", "must be an object")
        capabilities = {}
    for key in CAPABILITIES:
        if type(capabilities.get(key)) is not bool:
            fail(f"task.capabilities.{key}", "must be true or false")
    for key in OPTIONAL_TASK_CAPABILITIES:
        if key in capabilities and type(capabilities[key]) is not bool:
            fail(f"task.capabilities.{key}", "must be true or false")
    if capabilities.get("completed_query") is True and not nonempty(tools.get("completed")):
        fail("task.tools.completed", "is required when completed_query is true")
    if capabilities.get("delete") is True and mode == "mcp" and not nonempty(tools.get("delete")):
        fail("task.tools.delete", "is required in mcp mode when delete is true")

    calendar = document.get("calendar")
    if not isinstance(calendar, dict):
        fail("calendar", "must be an object")
        calendar = {}
    if calendar.get("mode") not in ("mcp", "manual"):
        fail("calendar.mode", "must be 'mcp' or 'manual'")
    if not nonempty(calendar.get("provider")):
        fail("calendar.provider", "must be a non-empty string")
    workday = calendar.get("workday")
    match = WORKDAY.fullmatch(workday) if isinstance(workday, str) else None
    if not match:
        fail("calendar.workday", "must look like 09:00-18:00")
    elif match.group(1) >= match.group(2):
        fail("calendar.workday", "start must be before end")
    calendar_tools = calendar.get("tools")
    if not isinstance(calendar_tools, dict):
        fail("calendar.tools", "must be an object")
        calendar_tools = {}
    for key, value in calendar_tools.items():
        if not nonempty(value):
            fail(f"calendar.tools.{key}", "must be a tool name")
    if calendar.get("mode") == "mcp" and not nonempty(calendar_tools.get("events")):
        fail("calendar.tools.events", "is required in mcp mode")
    calendar_capabilities = calendar.get("capabilities", {})
    if not isinstance(calendar_capabilities, dict):
        fail("calendar.capabilities", "must be an object")
        calendar_capabilities = {}
    for key in OPTIONAL_CALENDAR_CAPABILITIES:
        if key in calendar_capabilities and type(calendar_capabilities[key]) is not bool:
            fail(f"calendar.capabilities.{key}", "must be true or false")
    if calendar_capabilities.get("freebusy") is True and not nonempty(calendar_tools.get("freebusy")):
        fail("calendar.tools.freebusy", "is required when freebusy is true")

    preferences = document.get("preferences")
    if not isinstance(preferences, dict):
        fail("preferences", "must be an object")
        preferences = {}
    if preferences.get("processing_style") not in ("quick", "thorough"):
        fail("preferences.processing_style", "must be 'quick' or 'thorough'")
    if "timezone" in preferences and not nonempty(preferences["timezone"]):
        fail("preferences.timezone", "must be a non-empty string when present")

    def scan(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.casefold()
                if any(word in lowered for word in SENSITIVE):
                    fail(f"{path}.{key}", "looks like a credential; keep credentials out of profiles")
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")

    scan(document, "profile")
    return errors


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
    errors = validate(document)
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, indent=2))
        return 1
    task = document["task"]
    calendar = document["calendar"]
    print(json.dumps({
        "status": "valid",
        "name": document["name"],
        "task": {"provider": task["provider"], "mode": task["mode"]},
        "calendar": {"provider": calendar["provider"], "mode": calendar["mode"]},
        "capabilities": task["capabilities"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
