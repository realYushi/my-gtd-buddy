# My GTD Buddy

A Reminders-native Getting Things Done (GTD) workflow powered by Claude Code. This project implements a streamlined GTD system using Apple Reminders with an intelligent AI skill to orchestrate workflow management.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [GTD Workflow](#gtd-workflow)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Important Warning](#important-warning)
- [Setup Guide](#setup-guide)
- [How to Use](#how-to-use)
- [Daily Workflow](#daily-workflow)
- [Customization](#customization)
- [Privacy Note](#privacy-note)

## Overview

This is my personal implementation of David Allen's GTD methodology, designed around Apple Reminders with an intelligent Claude Code skill to orchestrate workflows. **While I use Apple Reminders, you can adapt this system to work with any todo list app** by modifying the shell scripts.

The system focuses on:

- **Instant capture** — Everything goes to Reminders Inbox first
- **Daily planning** — Inbox to zero with interactive processing
- **Focused execution** — Context-aware task selection with energy matching
- **Continuous review** — AI-driven micro-reviews with project health checks
- **Proactive surfacing** — AI surfaces relevant info using historical patterns
- **Whole-decision undo** — Safely reverse moves, processing, delegation, deferral, flags, and completion

> **See It In Action**: Check out [A Day with My GTD System.md](A%20Day%20with%20My%20GTD%20System.md) — a complete walkthrough from morning to night showing how the system handles real interruptions, context switching, and maintains focus. Also see [SCENARIOS.md](SCENARIOS.md) for recipes for common situations like "Post-Vacation Reset" or "5-Minute Gap".

## Key Features

- **Apple Reminders native** — Uses standard Reminders lists (Inbox, Next Actions, Waiting For, Someday, Projects)
- **Calendar integration** — macOS Calendar for appointment + task coordination
- **Context tags** — Location (@home, @office) and energy (#high, #low, #quick) in notes
- **Dated history** — Tracks processing velocity, context usage, and completion snapshots for grounded suggestions
- **Project health** — Detects orphan projects without next actions
- **Waiting nudges** — Shows waiting items with age, prompts for follow-ups
- **Whole-decision undo** — Restore every field a decision changed while preserving later edits
- **Natural language dates** — "tomorrow 2pm", "next friday", "Jan 15"
- **Batch operations** — Declare bankruptcy on stale items
- **Terse communication** — "Captured: [item]" not "I've successfully added..."

## Technology Stack

- **[Claude Code](https://claude.ai/code)** — AI-powered CLI with Skills support
- **Apple Reminders** — Native macOS/iOS reminders app
- **macOS Calendar** — Native calendar app
- **yq** — YAML processor for robust state management
- **AppleScript** — Shell scripts wrapping osascript for Reminders/Calendar access

## System Architecture

```mermaid
graph TB
    subgraph "Claude Code Skill"
        SKILL[GTD Skill<br/>Workflow Orchestrator]
        PROCESS[Process Mode<br/>Inbox Processing]
        COACH[Coach Mode<br/>Context-Aware Selection]
        REVIEW[Review Mode<br/>Weekly + Project Health]
        HEALTH[Health Mode<br/>System Recovery]

        SKILL --> PROCESS
        SKILL --> COACH
        SKILL --> REVIEW
        SKILL --> HEALTH
    end

    subgraph "Command + Decision Modules"
        RSCRIPT[reminders.sh<br/>AppleScript queries]
        RDECIDE[gtd_reminders.py<br/>decisions + undo]
        CSCRIPT[calendar.sh<br/>event queries]
        CAVAIL[gtd_calendar.py<br/>availability]
        SSCRIPT[state.sh<br/>compatibility entry]
        STRACK[gtd_tracking.py<br/>dated outcomes]
    end

    subgraph "Apple Reminders"
        INBOX[Inbox]
        NEXT[Next Actions]
        WAITING[Waiting For]
        SOMEDAY[Someday]
        PROJECTS[Projects]
    end

    subgraph "macOS Calendar"
        EVENTS[Events]
        FREE[Free Time]
    end

    subgraph "State"
        TRENDS[Dated Weeks]
        SNAPSHOTS[Completion Snapshots]
        VELOCITY[Processing Velocity]
    end

    SKILL --> RSCRIPT
    SKILL --> CSCRIPT
    SKILL --> SSCRIPT
    RSCRIPT --> INBOX
    RSCRIPT --> NEXT
    RSCRIPT --> WAITING
    RSCRIPT --> SOMEDAY
    RSCRIPT --> PROJECTS
    RSCRIPT --> RDECIDE
    CSCRIPT --> EVENTS
    CSCRIPT --> FREE
    CSCRIPT --> CAVAIL
    SSCRIPT --> STRACK
    STRACK --> TRENDS
    STRACK --> SNAPSHOTS
    STRACK --> VELOCITY
```

## GTD Workflow

### Workflow Phases

```mermaid
graph LR
    CAPTURE[CAPTURE<br/>Instant<br/>→ Inbox]
    PROCESS[PROCESS<br/>10 min<br/>Inbox → 0]
    COACH[COACH<br/>All Day<br/>Energy-Aware]
    REVIEW[REVIEW<br/>Weekly<br/>5 Parts]

    CAPTURE --> PROCESS
    PROCESS --> COACH
    COACH --> REVIEW
    REVIEW --> CAPTURE

    classDef capture fill:#e1f5fe
    classDef process fill:#f3e5f5
    classDef coach fill:#e8f5e8
    classDef review fill:#fff3e0

    class CAPTURE capture
    class PROCESS process
    class COACH coach
    class REVIEW review
```

### Reminders List Flow

```mermaid
flowchart TD
    START[Idea/Task] --> INBOX[INBOX]
    INBOX --> DECISION{Processing}

    DECISION -->|"y now"| NEXT_FLAG[NEXT ACTIONS<br/>Flagged for today]
    DECISION -->|"y later"| NEXT[NEXT ACTIONS<br/>Ready when needed]
    DECISION -->|"someday"| SOMEDAY[SOMEDAY<br/>Future consideration]
    DECISION -->|"delete"| DELETE[Deleted]

    NEXT_FLAG --> EXECUTE[EXECUTE]
    NEXT --> CONTEXT[Context Filter]
    SOMEDAY --> REVIEW_CYCLE[Weekly Review]

    REVIEW_CYCLE --> NEXT
    CONTEXT --> EXECUTE
```

## Project Structure

```
.claude/
└── skills/
    └── gtd/
        ├── SKILL.md              # Main orchestrator + routing
        ├── state.yaml            # Dated outcomes, snapshots, preferences
        ├── modes/
        │   ├── process.md        # Interactive inbox processing
        │   ├── coach.md          # Context + energy-aware selection
        │   ├── review.md         # 5-part weekly review
        │   ├── health.md         # System health + recovery
        │   ├── capture.md        # Quick capture to Inbox
        │   └── waiting.md        # Waiting review and nudges
        ├── scripts/
        │   ├── reminders.sh      # Reminder queries + command entry point
        │   ├── gtd_reminders.py  # Decision, undo, and failure handling
        │   ├── calendar.sh       # Calendar queries + command entry point
        │   ├── gtd_calendar.py   # Shared availability calculation
        │   ├── state.sh          # State command entry point
        │   └── gtd_tracking.py   # Dated outcomes through yq
        └── reference/
            └── tools.md          # Complete CLI reference

tests/                            # Interface tests with fake adapters
GLOSSARY.md                       # GTD domain language
A Day with My GTD System.md       # Real workflow example
SCENARIOS.md                      # Common scenarios and recipes
```

## Requirements

- **macOS** — Required for AppleScript integration
- **Apple Reminders** — Pre-installed on macOS
- **macOS Calendar** — Pre-installed on macOS
- **Claude Code** — AI-powered CLI
- **Python 3** — Standard library only (`python3 --version`)
- **yq** — Portable command-line YAML processor (`brew install yq`)

## Important Warning

**AI systems can make mistakes!** This system has direct access to your Reminders and Calendar data. The AI may:

- Accidentally delete or modify reminders
- Move items to wrong lists
- Create duplicate entries
- Mess up calendar events

**Recommendations:**

- **Test with non-critical data first**
- **Start slowly** — Begin with read-only commands
- **Use undo** — `.claude/skills/gtd/scripts/reminders.sh undo` reverses the last decision while preserving later edits
- **Review AI actions** — Always verify, especially for important tasks

## Setup Guide

### 1. Install Prerequisites

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Install yq (Python 3 ships with macOS)
brew install yq
```

### 2. Clone This Repository

```bash
git clone https://github.com/realYushi/my-gtd-buddy.git
cd my-gtd-buddy
```

### 3. Set Up GTD Lists in Reminders

Open Apple Reminders and create these lists:
- **Inbox** — Capture bucket
- **Next Actions** — Actionable tasks
- **Waiting For** — Delegated/waiting items
- **Someday** — Maybe later
- **Projects** — Multi-step outcomes

Or run the setup script:
```bash
.claude/skills/gtd/scripts/reminders.sh setup
```

### 4. Make Scripts Executable

```bash
chmod +x .claude/skills/gtd/scripts/*.sh
```

### 5. Verify Setup

```bash
cd /path/to/my-gtd-buddy
claude

# Test Reminders connection
> /gtd
# Should show inbox count and health status

# Test specific commands
> process inbox
# Should start interactive inbox processing
```

**Troubleshooting:**
- If Reminders access fails: Grant Terminal/Claude access in System Settings → Privacy & Security → Automation
- If Calendar access fails: Grant access in System Settings → Privacy & Security → Calendars
- If `state.sh` fails: Ensure `yq` is installed (`brew install yq`)

### 6. Run Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests use fake Reminders/Calendar adapters and temporary state files. They never touch your live data. Tracking tests require `yq`.

## How to Use

### Natural Language Commands

The GTD skill automatically routes based on intent:

```
# Processing (→ Process mode)
process inbox
clear inbox
/gtd

# Coaching (→ Coach mode)
what should I do
I'm stuck
help me prioritize
feeling tired

# Review (→ Review mode)
weekly review
how am I doing
review

# Recovery (→ Health mode)
system is a mess
need to reset
cleanup
```

### Proactive AI Behavior

The skill surfaces information using your historical patterns:

- **Velocity**: "You usually process 12 items per session"
- **Context**: "You do a lot @home — filter those?"
- **Completion snapshot**: "23 completed in the last seven days"
- **Dated weeks**: Compare processing volume only when enough complete weeks exist
- **Orphan projects**: "3 projects need a next action"
- **Stale waiting**: "'Email from John' waiting 10 days. Nudge?"

### Context-Aware Filtering

```
# By energy
feeling tired → suggests #low energy tasks
high energy → suggests deep work, creative tasks

# By location
I'm at home → filters for @home tasks

# By time available
I have 15 minutes → suggests #quick tasks
```

## Daily Workflow

### Morning (10 minutes)

1. **"process inbox"** — Interactive inbox processing
2. Answer: "Actionable? When?" → "y later" / "n delete" / "someday"
3. Result: Inbox to zero, Next Actions ready

### Throughout Day

1. **"what should I do"** — Energy + context-aware suggestions
2. **"I'm stuck on [task]"** — Get unstuck with breakdown
3. **Capture interruptions** — Added to inbox, process later

### Weekly Review (10 minutes)

5 parts:
1. **Wins** — Celebrate completed items
2. **Stuck** — Triage stale items (7+ days)
3. **Projects** — Ensure each has a next action
4. **Waiting** — Check waiting items, send nudges
5. **Mind sweep** — Capture anything floating in head

### Recovery (When Needed)

When system gets messy:
1. **Declare bankruptcy** — Batch defer all stale items
2. **Inbox blitz** — Rapid keep/dump
3. **Focus mode** — Pick just 3 for the week

## Customization

### For Different Todo Apps

1. Replace `reminders.sh` with scripts for your app
2. Update `reference/tools.md` with your commands
3. Modify mode files for your app's terminology

### For Different Workflows

1. Edit files in `.claude/skills/gtd/modes/`
2. Adjust routing patterns in `SKILL.md`
3. Modify tag system in `reference/tools.md`

### Tracking Preferences

Edit `state.yaml` to customize:
- `processing_style`: quick | thorough
- Health thresholds in `modes/health.md`

## Privacy Note

This is a **personal use project**. All data stays local on your Mac. The scripts use AppleScript to communicate with Reminders and Calendar — no cloud sync required.

---

_Built for personal productivity using GTD principles and Claude Code._
