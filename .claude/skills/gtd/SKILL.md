---
name: gtd
description: Orchestrates GTD workflows via Things 3 for inbox processing, daily planning, task execution, and reviews. Triggers on productivity requests like "process inbox", "plan my day", "what should I do", "I have 30 minutes", "weekly review", "end of day", or when user mentions tasks, to-dos, or asks what to work on next.
allowed-tools: mcp__things__*, mcp__calendar__*
user-invocable: true
---

# GTD Workflow Orchestrator

## Contents

- [Workflows](#workflows) - Planning, execution, review, proactive
- [Reference](#reference) - Tools, tags, fallbacks

## Requirements

- Things 3 for Mac (Things Helper enabled)
- things-mcp server connected
- macos-calendar-mcp (optional)

Verify: `get_inbox` and `list-today-events` should succeed.

## Workflows

Route based on user intent:

| Intent | Workflow | Triggers |
|--------|----------|----------|
| **Planning** | [daily-planning.md](workflows/daily-planning.md) | "process inbox", "plan my day", "organize", morning |
| **Execution** | [execution.md](workflows/execution.md) | "what should I do", "I have X minutes", energy/location mentions |
| **Review** | [review.md](workflows/review.md) | "weekly review", "how did I do", "progress check" |
| **Proactive** | [proactive.md](workflows/proactive.md) | AI-initiated: session start, task completion, deadlines, stale items |

**Capture intent** ("remind me to...", "add [task]"): `add_todo` to inbox, confirm tersely, continue.

**Ambiguous?** Ask: "Plan tasks, work on something, or review progress?"

## Proactive Triggers

Surface automatically (don't wait to be asked):
- Session start → morning briefing
- Task completion → suggest next
- Deadline within 48h → alert
- @waiting item 5+ days → follow-up prompt
- Stale task 7+ days → "Still relevant?"
- End of day → completion summary

## Communication Style

```
✓ "Captured: [item]"
✓ "Done."
✓ "3 of 12: '[item]' — actionable?"

✗ "Let me think..." (just do it)
✗ "I've successfully added..." (too verbose)
```

## Reference

- **Tools**: [reference/tools.md](reference/tools.md) - MCP tool reference and patterns
- **Tags**: [reference/tags.md](reference/tags.md) - Context tags and setup
- **Fallbacks**: [reference/fallbacks.md](reference/fallbacks.md) - Things URL schemes when MCP fails
