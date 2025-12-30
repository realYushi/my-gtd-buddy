# Execution Workflow

## Progress Checklist

```
Execution Session:
- [ ] Assess context (time / energy / location)
- [ ] Filter tasks by context
- [ ] Suggest 1-3 options
- [ ] Open selected task in Things
- [ ] Track completion, suggest next
```

## Context Assessment

First time: "How much time?" / "Energy?" / "Where?"

Follow-up: Remember context, only ask what changed.

## Filtering Strategy

| Time | Filter |
|------|--------|
| 5-15 min | `#quick` + Today |
| 30-60 min | Medium tasks from Today/Anytime |
| 2+ hours | `#high` + project deep work |

| Energy | Filter |
|--------|--------|
| High | `#high` + creative/complex |
| Medium | Regular Today tasks |
| Low | `#low` + admin, or suggest break |

| Location | Filter |
|----------|--------|
| Home | `@home` + personal |
| Office | `@office` + work |
| Out | `@errands` + location-specific |

## Response Format

Suggest 1-3 specific tasks:

```
"30 min, medium energy, home:

1. 'Review budget' — @home, #quick
2. 'Outline blog post' — @home, medium

Which feels right?"
```

After selection → `show_item` to open in Things.

## Interruptions

```
User: "Oh, I need to call the dentist"
→ add_todo("Call dentist", inbox)
→ "Captured. Back to: [current task]"
```

## Time Estimation

Things 3 has no time field. Use:
- Notes prefix: "~15m", "~1h"
- Duration tags: `#5min`, `#15min`, `#30min`, `#1hour`, `#deep`
- Inference: quick keywords → ~10 min, review/write → ~30 min, complex → ~1 hour

## Deadline Awareness

Use `search_advanced(deadline: "YYYY-MM-DD")`:
"Heads up: '[task]' due tomorrow — tackle now?"
