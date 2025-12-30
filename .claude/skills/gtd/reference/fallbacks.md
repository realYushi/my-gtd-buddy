# Things URL Scheme Fallbacks

When MCP tools fail, use these clickable links:

| Action | URL |
|--------|-----|
| Open Today | `things:///show?id=today` |
| Open Inbox | `things:///show?id=inbox` |
| Open Upcoming | `things:///show?id=upcoming` |
| Open Anytime | `things:///show?id=anytime` |
| Open Someday | `things:///show?id=someday` |
| Open Logbook | `things:///show?id=logbook` |
| Add to Inbox | `things:///add?title=TASK_NAME` |
| Add to Today | `things:///add?title=TASK_NAME&when=today` |
| Quick search | `things:///search?query=SEARCH_TERM` |

## Example Fallback

```
"MCP unavailable. Open Things manually:
→ things:///show?id=inbox
Then tell me what you see."
```
