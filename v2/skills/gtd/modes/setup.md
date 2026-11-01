# Setup

Create a validated backend profile that maps GTD concepts to the tools the user actually has.

Setup is complete when:

1. the user confirms one task backend and one calendar backend;
2. every required GTD container has a real name;
3. every mapped tool name was discovered, not invented;
4. read-only probes verify the containers, labels, projects, and upcoming events;
5. the profile validator passes;
6. an automated task backend passes one disposable write, read-back, move, and cleanup;
7. capabilities and degradations are stated.

## 1. Inventory

Ask which task manager and calendar the user wants. Inspect the available MCP tools and read their schemas. Record the exact names.

If the user has no writable task tool, create a **manual** profile and continue in coach mode.

## 2. Map

Show a compact table before writing:

| GTD concept | Backend object | Tool |
|-------------|----------------|------|
| Inbox | ... | ... |
| Next Actions | ... | ... |
| Waiting For | ... | ... |
| Someday | ... | ... |
| Projects | ... | ... |
| Contexts | ... | ... |
| Calendar events | ... | ... |

Ask about workday hours and timezone. An mcp calendar requires an IANA timezone. Ask which labels represent contexts, energy, and duration.

## 3. Probe Read-Only

Use read-only tools to verify containers, labels, projects, and upcoming events. If a GTD container is missing, ask before creating it.

## 4. Write The Profile

Use [the profile format](../reference/profile.md). Store it at `.gtd/profile.json` unless the user chooses another path. Keep it out of version control and keep credentials out of it. Manual Mode applies per backend: leave that backend's tools empty.

For multiple available backends, write one active profile. The user can create another later; the core skill uses one per session.

## 5. Validate

From the skill directory, run:

```bash
python3 scripts/validate_profile.py <profile-path>
```

The output includes resolved `instructions` for each capability and `live_verification: "unknown"`. If the skill cannot run shell commands, check every required field against [the profile format](../reference/profile.md). Fix every error. Do not hand-wave a missing tool by writing a guessed name.

## 6. Prove One Write

With confirmation, create a disposable item in Inbox, read it back, move it, complete or delete it, and read it back again. If the backend is read-only, skip this step and record `manual` mode.

## 7. Close

Report:

- active task backend
- active calendar backend
- supported capabilities
- unsupported capabilities and how the skill degrades
- profile path

Re-run setup when a tool disappears, a container is renamed, or validation fails.
