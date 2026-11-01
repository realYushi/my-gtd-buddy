# Coach Mode

For planning, focus, energy matching, and getting unstuck. The goal is always to narrow down to ONE next action.

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh today
.claude/skills/gtd/scripts/reminders.sh counts
.claude/skills/gtd/scripts/calendar.sh free
.claude/skills/gtd/scripts/state.sh trends
.claude/skills/gtd/scripts/state.sh begin coach
```

Keep the printed session ID. Available time means the rest of today inside the 9AM–6PM workday, with overlapping events counted once.

Assess silently. Pick what is relevant to the user's intent and lead with ONE focusing question or suggestion.

## Patterns

### "Plan my day" / "Start my day" / "Morning"

This is a daily briefing. Show it as a compact dashboard, not a wall of text:

```
Today — [Day], [Date]

📅 [N] events ([next event] at [time])
✅ [X] due/flagged
📥 [Y] in inbox
⏳ [Z] waiting

Top 3 candidates:
1. [task] — [why: due today / flagged / stalled N days]
2. [task]
3. [task]

Start with #1, or pick another?
```

Pull candidates from: flagged items first, then due today, then oldest in Next Actions. Keep it to 3. If calendar is packed, say "Tight day — [X]h available. Pick one thing."

### "What should I do?" / "What should I work on?"

Don't show everything. Ask energy first if you don't have context:

```
Energy? (high/medium/low)
```

Then suggest 3 tasks matched to energy level. If user already mentioned energy ("I'm tired"), skip the question and go straight to suggestions.

### "I'm overwhelmed"

Pull the actual task counts, then reduce:

```
[X] in Next Actions, [Y] in inbox.

Ignore all of it. What ONE thing would make you feel progress?
```

→ User names it → Flag it, then offer: "Hide the rest for today? (y/n)"

The point is to shrink the world, not add to it. Don't list tasks, don't suggest strategies, don't lecture about GTD. One thing.

### "I'm stuck on [task]"

```
What's blocking '[task]'?

1. Unclear next step
2. Need info from someone
3. Too big
4. Avoiding it
```

Based on answer:
- **1 (unclear):** "What would you do if you only had 5 minutes? That's your next action."
- **2 (need info):** "Who? I'll add a waiting-for." → `delegate <id> <person>`
- **3 (too big):** "What's the smallest piece? I'll add it as a next action."
- **4 (avoiding):** "What would make it less painful? Timer for 15 min? Different environment? Or just do the first 2 minutes."

### "Help me prioritize"

```bash
.claude/skills/gtd/scripts/reminders.sh next
```

Show the full Next Actions list, then:

```
Pick 3 for today. I'll flag them, rest stays off your radar.
```

User picks → flag those 3 → done.

### "I'm tired" / "Low energy" / "Quick wins"

```bash
.claude/skills/gtd/scripts/reminders.sh context #quick
.claude/skills/gtd/scripts/reminders.sh context #low
```

If tagged tasks exist, suggest up to 3. If none are tagged:

```bash
.claude/skills/gtd/scripts/reminders.sh next
```

Pick the simplest-sounding items (short titles, admin-type tasks) and suggest those. Never suggest deep work or creative tasks when energy is low.

```
Low energy mode. 3 quick ones:
1. [task]
2. [task]
3. [task]

Pick one, or rest? No shame in resting.
```

## Using Historical Data

`state.sh trends` returns dated weeks and completion snapshots. Use it only when `trends_available` is true; that requires two or more dated weeks.

| Data | How to use it |
|------|---------------|
| `processing_velocity` | "You usually process [N] per session." Only compare processing sessions. |
| A week's `contexts` with `contexts_complete: true` | "You do a lot @[context] — want to batch those?" |
| `weekly_processed` with `processed_complete: true` | Compare processing volume; omit incomplete weeks. |
| `completion_snapshots` | Show the latest seven-day count as a snapshot. Never add snapshots or call them weekly completions. |

Missing or incomplete values are unknown, not zero. Compare only dated, complete observations; older undated history stays out of weekly claims.

## Energy Mapping

| Energy | Suggest | Avoid |
|--------|---------|-------|
| High | Deep work, creative, complex | Admin busywork |
| Medium | Regular tasks, meetings prep | Heavy creative |
| Low | Admin, quick wins, or rest | Deep work, anything requiring focus |

## Context Suggestions

If user mentions a location or context:

```bash
.claude/skills/gtd/scripts/reminders.sh context @home
```

Suggest top 3 from that context. If no tasks tagged with that context, say so: "Nothing tagged @home. Want to tag some tasks?"

## Session End

```bash
.claude/skills/gtd/scripts/state.sh session coach --id <session-id>
```

Coach does not affect processing velocity. Record context counts only when this session assigned contexts. Repeating the same call with the same ID is safe.
