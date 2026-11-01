# Inbox Processing

Turn every Inbox item into one disposition: now, later, delegate, someday, or delete.

## Start

Read Inbox with the profile's list tool. In manual mode, ask the user for the list.

Show `N/total: 'Title'` for the first item and ask:

```text
Actionable? (now/later/someday/delete)
```

## Dispositions

| Response | Change |
|----------|--------|
| `now` | Move to Next Actions, flag or prioritize for today, add any context/energy tags in one update |
| `later` | Move to Next Actions and add tags |
| `delegate [person]` | Move to Waiting For and record the owner |
| `someday` | Move to Someday |
| `delete` | Confirm, then delete |

Use one update per item. Do not process and then make a separate flag change.

**Project clue:** If the item is multi-step, ask for one next action. Keep or create the project item, then add the next action.

**Due date clue:** Ask for the date and set it when the backend supports due dates.

In manual mode, state the exact change and ask the user to make it. Confirm the result before moving on.

## Position And Flow

- Show `N/total: 'Title'`.
- Move immediately to the next item after a disposition.
- On `skip`, leave the item unchanged and move on.
- On `stop`, end at the current item and summarize the session.

Processing is complete when Inbox is empty or the user stops. Report how many items received each disposition. Do not claim persistent processing totals unless the backend records them.
