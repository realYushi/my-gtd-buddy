# Proactive Surfacing

AI-initiated suggestions based on real-time context. Don't wait to be asked.

## Trigger Conditions

| Condition | Detection | Response |
|-----------|-----------|----------|
| Calendar gap | 15+ min free | "25 min before 2pm meeting — '[task]'?" |
| Deadline near | Within 48h | "'[task]' due tomorrow. Tackle now?" |
| Waiting aging | @waiting 5+ days | "[Person] hasn't responded — follow up?" |
| Stale task | 7+ days old | "'[task]' has been sitting. Still relevant?" |
| Task completed | Just finished | "Nice. '[similar task]' next?" |
| Session start | Morning greeting | "Morning. 3 things today — start with '[task]'?" |
| End of day | After 5pm | "2 items left. Tomorrow or quick finish?" |

## Context Inference

Don't ask — infer:

| Signal | Inference |
|--------|-----------|
| Morning (6-9am) | Planning mode |
| Work hours (9-6) | Work context, higher energy |
| After 6pm weekday | Personal, lighter tasks |
| Weekend | Personal, flexible |
| Just completed task | High momentum |
| Long gap (2+ hours) | Energy reset, easy starter |
| Calendar-heavy day | Suggest #quick in gaps |
| Calendar-light day | Suggest #deep work blocks |

## Suggestion Format

Specific and actionable:

```
"[Context observation] — [specific task]?"
```

✓ "20 min before standup — review blockers?"
✓ "3 tasks done this morning — keep streak with 'Email vendor'?"
✗ "Would you like me to suggest some tasks?"
✗ "Here are your options: 1, 2, 3, 4, 5..."

## Friction Detection

| Pattern | Response |
|---------|----------|
| Task 7+ days on Today | "Keep hitting snags? Break down / Delegate / Someday / Delete" |
| Task type consistently slips | "I notice [category] tasks slip. Pattern?" |
| Today list > 8 regularly | "Prioritize top 5?" |

## Workflow Handoffs

- User engages → switch to [Execution](execution.md)
- Inbox items found → offer [Daily Planning](daily-planning.md)
- Patterns suggest issues → trigger micro-review from [Review](review.md)
