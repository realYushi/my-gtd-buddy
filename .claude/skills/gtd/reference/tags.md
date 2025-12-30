# Tag System

## Core Tags

| Type | Tags | Use |
|------|------|-----|
| Location | `@home` `@office` `@errands` `@calls` | Where you can do it |
| Energy | `#high` `#low` `#quick` | What it requires |
| Duration | `#5min` `#15min` `#30min` `#1hour` `#deep` | Time estimate (optional) |
| Status | `@waiting` | Blocked/delegated |

## First-Time Setup

Check existing tags with `get_tags`. If missing core tags, offer to create:

```
things:///add-tag?title=@home
things:///add-tag?title=@office
things:///add-tag?title=@errands
things:///add-tag?title=@calls
things:///add-tag?title=%23high
things:///add-tag?title=%23low
things:///add-tag?title=%23quick
things:///add-tag?title=@waiting
```

Optional duration tags:
```
things:///add-tag?title=%235min
things:///add-tag?title=%2315min
things:///add-tag?title=%2330min
things:///add-tag?title=%231hour
things:///add-tag?title=%23deep
```

**Note:** `#` must be URL-encoded as `%23` in Things URLs.
