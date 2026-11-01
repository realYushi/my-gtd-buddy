# Weekly Review

5 parts, under 10 minutes. Move fast — the value is in the habit, not the thoroughness.

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh counts
.claude/skills/gtd/scripts/reminders.sh completed 7
.claude/skills/gtd/scripts/reminders.sh stale 7
.claude/skills/gtd/scripts/reminders.sh orphan-projects
.claude/skills/gtd/scripts/reminders.sh waiting-age
.claude/skills/gtd/scripts/state.sh begin review
```

Keep the printed review ID. `completed 7` is a rolling seven-day completion snapshot, not an additive weekly total.

```
Weekly review. ~[N] min based on what's here.

Last 7 days: [X] completed
[Y] in Next Actions, [Z] in inbox, [W] stale

Ready?
```

Estimate time: 2 min base + 30s per stale item + 30s per orphan project + 30s per waiting item. Cap at 10 min estimate.

## Part 1: Wins (1 min)

Show completed items. Ask: "Biggest win?"

Acknowledge briefly ("Nice." / "Solid.") and move on.

## Part 2: Stuck Items (2-3 min)

**Stale (7+ days):**

If many stale items (8+), offer batch option first:
```
[N] items sitting 7+ days. Want to:
1. Triage one by one
2. Bulk move old ones to Someday (keeps recent)
```

Otherwise go item by item:
```
[N] stale items:

1. '[item]' ([X] days) — keep/someday/delete?
```

| Response | Action |
|----------|--------|
| `y` or `keep` | Keep in Next Actions |
| `someday` | `reminders.sh defer <id>` |
| `delete` | `reminders.sh delete <id>` |

Every move and completion is one undoable decision. Command outcomes follow [Error Recovery](../SKILL.md#error-recovery).

## Part 3: Project Health (1-2 min)

**Orphan projects (no next action):**

Skip if none. Otherwise:
```
[N] projects need a next action:

1. '[project]' — next step?
```

User gives next action → add to Next Actions → next project.

If user says "drop it" → delete project.

## Part 4: Waiting Check (1-2 min)

**Waiting items with age:**

Skip if none. Otherwise:
```
Waiting on:
• '[item]' — [person] — [X] days
```

For each: "Still waiting? (y/nudge/done)"

| Response | Action |
|----------|--------|
| `y` | Keep waiting |
| `nudge` | Add "Follow up with [person] re: [item]" to Next Actions |
| `done` | Mark complete |

## Part 5: Mind Sweep (2 min)

```
Anything floating in your head not captured?
```

Add each to inbox. "Got it." Repeat until "done" or "no."

## Close

```bash
.claude/skills/gtd/scripts/state.sh review <completed_count> "<focus>" --id <review-id>
```

If the user has no focus, omit it. Repeating the same review with the same ID is safe. Review snapshots are dated observations; the tracking module never adds overlapping seven-day windows together.

```
Review done.
• [X] completed this week
• [Y] stale triaged
• [Z] projects checked
• [W] waiting reviewed

Focus for next week?
```

Save their answer as the focus. If they don't have one, that's fine — don't push.
