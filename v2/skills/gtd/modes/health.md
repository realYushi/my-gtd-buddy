# System Health

State facts and offer one action. No lectures.

## Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Inbox | 0-5 | 6-15 | 16+ |
| Stale (14+ days) | 0-3 | 4-10 | 11+ |
| Days since review | 0-7 | 8-14 | 15+ |
| Next Actions | 5-20 | 21-40 | 41+ |

Use only metrics the backend can supply. Days since review comes from the user or a durable note; V2 keeps no state store. Mark anything else unknown.

## Surfacing

Pick the worst metric and offer the matching action:

- Inbox high: process it.
- Stale high: prune or move to Someday.
- Review overdue: run a short review.
- Next Actions high: trim or defer.

## Recovery

1. **Bankruptcy:** move stale items to Someday. Confirm the batch and the target container.
2. **Blitz:** rapid keep/dump through Inbox. One disposition per item.
3. **Focus 3:** choose three next actions for the week and flag or prioritize them when supported.

Every bulk change gets explicit confirmation and a summary. If the backend lacks batch tools, work item by item.

Recovery is complete when the chosen action is done and the changed count is reported.
