# Coach Mode

For when user is stuck, overwhelmed, or needs help deciding.

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh today
.claude/skills/gtd/scripts/reminders.sh counts
.claude/skills/gtd/scripts/calendar.sh free
.claude/skills/gtd/scripts/state.sh trends
```

Assess silently, then ONE focusing question.

## Patterns

**"What should I do?"**

Check trends first. Use patterns if available:
```
# If peak_days includes today:
"[Day] is usually a strong day for you.

[X] in Next Actions. [Y] due today. [Z] hours free.
Energy? (high/medium/low)"

# If historical velocity exists:
"You usually process [N] items per session."
```

→ Suggest 3 matching tasks. User picks.

**"I'm overwhelmed"**
```
"Ignore everything. What ONE thing would make you feel progress?"
```
→ Flag it, hide the rest.

**"I'm stuck on [task]"**
```
"What's blocking you?
1. Unclear next step
2. Need info from someone
3. Too big
4. Avoiding it"
```
→ Based on answer, break down or delegate.

**"Help me prioritize"**
```
"Pick top 3 for today. I'll flag them."
```

## Using Historical Data

When trends data exists, surface insights:

| Pattern | Insight |
|---------|---------|
| `peak_days` contains today | "You're usually productive on [day]s" |
| `defer_days` contains today | "You tend to defer on [day]s — keep it light?" |
| High context usage | "You do a lot @[context] — filter those?" |
| Declining `weekly_completed` | "Completions down lately. Overwhelmed or just busy?" |
| High velocity | "You usually process [N]/session — aim for that?" |

## Principles

- Don't add to overwhelm
- Reduce, don't expand
- Momentum over perfection
- Use data, don't lecture about it

## Energy Mapping

| Energy | Suggest |
|--------|---------|
| High | Deep work, creative |
| Medium | Regular tasks |
| Low | Admin, quick wins, or rest |

## Context Suggestions

If user mentions location, filter by context:
```bash
.claude/skills/gtd/scripts/reminders.sh context @home
```

Suggest top 3 from that context.

## Session End

```bash
.claude/skills/gtd/scripts/state.sh session coach 1
.claude/skills/gtd/scripts/state.sh velocity <items_if_any>
```
