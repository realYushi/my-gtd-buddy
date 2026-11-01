# GTD V2

A tool-neutral GTD skill. The skill carries the SOP; a one-time setup mode maps it to the user's task manager and calendar through a declarative backend profile.

This package is intentionally outside `.claude/skills`, so it does not compete with the existing V1 skill. Install it by copying `v2/skills/gtd` into the skill directory used by your agent, or by packaging that folder as a Grok Bot plugin.

## Shape

```text
v2/skills/gtd/
├── SKILL.md
├── modes/
│   ├── setup.md
│   ├── capture.md
│   ├── process.md
│   ├── coach.md
│   ├── waiting.md
│   ├── review.md
│   └── health.md
├── reference/
│   ├── sop.md
│   ├── glossary.md
│   ├── capabilities.md
│   └── profile.md
├── backends/
│   ├── todoist-google.example.json
│   └── manual.example.json
└── scripts/
    └── validate_profile.py
```

## Install

1. Install either V1 or V2 as `gtd`. Two model-invoked GTD skills create competing trigger descriptions.
2. Copy `v2/skills/gtd` to your agent's skill directory.
3. Run `/gtd setup` or say "set up GTD".
4. Choose a task backend and calendar backend from the tools the agent can actually see.
5. Let setup write and validate `.gtd/profile.json`.

The profile is per-user configuration. It is gitignored and contains no credentials.

## Verify

```bash
python3 -m unittest discover -s v2/tests -v
```

The tests validate profile structure and documentation links. They do not contact task or calendar services.

## Boundaries

- V2 stores no task database.
- The selected task manager is the source of truth.
- Manual mode coaches the user without writing.
- Undo, completion history, and exact completion snapshots are available only when the backend exposes them.
- Backend tool names come from discovery. Setup never invents them.
