# Continuous Review System

AI-driven micro-reviews replace scheduled heavy reviews. Surface issues as they arise.

## Micro-Reviews (AI-Initiated)

### End of Day
**Trigger:** After 5pm or "done for today"

```
get_logbook(period:'1d'), get_today

"Today: [X] done, [Y] remaining. [Biggest win].
Remaining items — tomorrow, or quick finish now?"
```

### Stale Items
**Trigger:** Task 7+ days old, detected during any interaction

```
"'[task]' added [X] days ago, untouched. Still on your radar?"
→ Keep / Someday / Delete / Break down
```

Surface 1-2 at natural pauses, not batched.

### Stuck Projects
**Trigger:** Project with no completion in 14+ days

```
"'[Project]' hasn't moved in [X] days. Status?"
→ Active (define next action) / Paused / Complete / Abandon
```

### Waiting Follow-up
**Trigger:** @waiting item older than 5 days

```
"Waiting on [person] for '[task]' — [X] days. Follow up?"
→ add_todo("Follow up with [person]", today, @calls)
```

### Overload Warning
**Trigger:** Today list > 8 items

```
"Today has [N] items. Pick your top 5 must-dos?"
```

## Weekly Mind Sweep (5 min)

**Trigger:** "weekly review" OR Sunday/Monday OR 7+ days since last

```
get_logbook(period:'7d'), get_projects, get_tagged_items("@waiting")

"Week recap: [X] done. Wins: [highlights]
Mind sweep — anything not captured?"
```

Flow:
1. Brain dump → capture to inbox
2. Waiting check → quick yes/no on aging items
3. Someday glance → 3 items to promote/keep/drop
4. Forward look → prep for upcoming week

## Monthly Health Check (10 min)

**Trigger:** "monthly review" OR first week of month

```
get_logbook(period:'1m'), get_projects, get_areas, get_someday
```

1. Project audit: active vs stale
2. Area balance: completion distribution
3. Someday prune: oldest 5, quick decisions
4. System friction: any recurring issues?

## Anti-Patterns

❌ Long scheduled reviews
❌ Batched issue surfacing ("12 stale items to review")
❌ Guilt-tripping
❌ Forced reflection

✅ Continuous small nudges
✅ Respect flow — surface at pauses
✅ User makes quick decisions, AI handles maintenance
