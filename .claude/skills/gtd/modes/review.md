# Weekly Review

Keep it under 10 minutes. 5 parts: wins, stuck, projects, waiting, mind sweep.

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh counts
.claude/skills/gtd/scripts/reminders.sh completed 7
.claude/skills/gtd/scripts/reminders.sh stale 7
.claude/skills/gtd/scripts/reminders.sh orphan-projects
.claude/skills/gtd/scripts/reminders.sh waiting-age
.claude/skills/gtd/scripts/state.sh trends
```

```
"Weekly review. Quick.

Last 7 days: [X] completed
[Y] in Next Actions, [Z] in inbox

Ready?"
```

## Part 1: Wins (1 min)

Show completed items. Ask: "Biggest win?"

Acknowledge briefly, move on.

## Part 2: Stuck Items (2-3 min)

**Stale (7+ days):**
```
"[N] items sitting 7+ days:

1. '[item]' — still relevant? (y/n/someday)"
```

## Part 3: Project Health (1-2 min)

**Orphan projects (no next action):**
```
"[N] projects need a next action:

1. '[project]' — what's the next step?"
```

Add next action to Next Actions, continue.

## Part 4: Waiting Check (1-2 min)

**Waiting items with age:**
```
"Waiting on:
• '[item]' — [person] — [X] days
  Still waiting? (y/nudge/done)"
```

| Response | Action |
|----------|--------|
| `y` | Keep waiting |
| `nudge` | Add "Follow up with [person] re: [item]" to Next Actions |
| `done` | Mark complete |

## Part 5: Mind Sweep (2 min)

```
"Anything floating in your head not captured?"
```

Add each to inbox. "Got it." Repeat until "done."

## Close

```bash
.claude/skills/gtd/scripts/state.sh review <completed_count> "<focus>"
.claude/skills/gtd/scripts/state.sh weekly <completed> <processed> <deferred>
```

```
"Review done.
• [X] completed
• [Y] stale triaged
• [Z] projects checked
• [W] waiting reviewed

Next week focus?"
```
