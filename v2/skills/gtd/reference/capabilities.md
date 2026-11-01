# Backend Capabilities

A profile declares what the selected backend can actually do. The skill degrades instead of pretending.

## Required For MCP Mode

Task backend:

- capture an item
- list and read items
- update container and fields
- complete an item

The Projects tool is optional. Without it, project review uses the list tool restricted to the Projects container and degrades explicitly when that is insufficient.

Calendar backend:

- list events in a window
- an explicit IANA timezone in the profile

## Optional

- delete
- native undo
- completed-item query
- due dates
- labels
- priority or flag
- modified date or age
- free/busy query
- project-to-task links
- batch operations

## Degradation

| Missing capability | Behavior |
|--------------------|----------|
| undo | Confirm before destructive changes; state that undo is unavailable |
| completed query | Ask for the recent completion count; label it as user-reported |
| modified date | Ask which items feel stale; do not invent ages |
| free/busy | Use complete event data; if unavailable, ask for available time |
| labels | Keep tags in the backend's supported field; if none, state the limitation |
| project links | Ask the user to confirm each project's next action |
| batch tools | Process item by item |

## Verification

When the backend supports reading after writing:

1. apply the change,
2. read the item back,
3. compare the changed fields,
4. report partial or uncertain outcomes explicitly.

When it does not support reading back, say the change is unverified.
