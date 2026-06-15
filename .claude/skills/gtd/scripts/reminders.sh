#!/bin/bash
# GTD Reminders AppleScript Wrapper
# Usage: ./reminders.sh <command> [args...]

set -e

# ============================================================================
# UNDO SUPPORT
# ============================================================================

UNDO_FILE="${SCRIPT_DIR:-/tmp}/../.undo_stack"

# Save action for potential undo
save_undo() {
    local action="$1"    # delete, move, complete
    local id="$2"
    local data="$3"      # original list for move, reminder data for delete

    echo "$action|$id|$data|$(date +%s)" >> "$UNDO_FILE"

    # Keep only last 10 undos
    if [[ -f "$UNDO_FILE" ]]; then
        tail -10 "$UNDO_FILE" > "${UNDO_FILE}.tmp"
        mv "${UNDO_FILE}.tmp" "$UNDO_FILE"
    fi
}

# Get last action for undo
get_last_undo() {
    if [[ -f "$UNDO_FILE" ]]; then
        tail -1 "$UNDO_FILE"
    fi
}

# Remove last undo entry
pop_undo() {
    if [[ -f "$UNDO_FILE" ]]; then
        head -n -1 "$UNDO_FILE" > "${UNDO_FILE}.tmp"
        mv "${UNDO_FILE}.tmp" "$UNDO_FILE"
    fi
}

# Perform undo
do_undo() {
    local last=$(get_last_undo)
    if [[ -z "$last" ]]; then
        echo "Nothing to undo"
        return 1
    fi

    IFS='|' read -r action id data timestamp <<< "$last"

    case "$action" in
        "move")
            # Move back to original list
            move_reminder "$id" "$data"
            echo "Undone: moved back to $data"
            ;;
        "complete")
            # Uncomplete
            osascript - "$id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        set completed of r to false
    end tell
end run
APPLESCRIPT
            echo "Undone: marked incomplete"
            ;;
        "delete")
            echo "Cannot undo delete (item permanently removed)"
            return 1
            ;;
        *)
            echo "Unknown action: $action"
            return 1
            ;;
    esac

    pop_undo
}

# ============================================================================
# DATE PARSING
# ============================================================================

# Parse natural language dates to YYYY-MM-DD HH:MM format
# Supports: today, tomorrow, next monday, 3pm, tomorrow 2pm, etc.
parse_date() {
    local input="$1"
    local result=""

    # Already in correct format?
    if [[ "$input" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
        echo "$input"
        return
    fi

    # Lowercase and trim
    input=$(echo "$input" | tr '[:upper:]' '[:lower:]' | xargs)

    local date_part=""
    local time_part=""

    # Extract time if present (e.g., "2pm", "14:00", "2:30pm")
    if [[ "$input" =~ ([0-9]{1,2})(:[0-9]{2})?(am|pm)? ]]; then
        local hour="${BASH_REMATCH[1]}"
        local mins="${BASH_REMATCH[2]:-:00}"
        local ampm="${BASH_REMATCH[3]}"

        mins="${mins#:}"  # Remove leading colon

        # Convert to 24hr
        if [[ "$ampm" == "pm" && "$hour" -lt 12 ]]; then
            hour=$((hour + 12))
        elif [[ "$ampm" == "am" && "$hour" -eq 12 ]]; then
            hour=0
        fi

        time_part=$(printf "%02d:%02d" "$hour" "$mins")

        # Remove time from input to parse date
        input=$(echo "$input" | sed -E 's/[0-9]{1,2}(:[0-9]{2})?(am|pm)?//g' | xargs)
    fi

    # Parse date part
    case "$input" in
        ""|"today")
            date_part=$(date +%Y-%m-%d)
            ;;
        "tomorrow"|"tmr"|"tom")
            date_part=$(date -v+1d +%Y-%m-%d)
            ;;
        "next week")
            date_part=$(date -v+7d +%Y-%m-%d)
            ;;
        "next monday"|"monday"|"mon")
            date_part=$(date -v+monday +%Y-%m-%d)
            ;;
        "next tuesday"|"tuesday"|"tue")
            date_part=$(date -v+tuesday +%Y-%m-%d)
            ;;
        "next wednesday"|"wednesday"|"wed")
            date_part=$(date -v+wednesday +%Y-%m-%d)
            ;;
        "next thursday"|"thursday"|"thu")
            date_part=$(date -v+thursday +%Y-%m-%d)
            ;;
        "next friday"|"friday"|"fri")
            date_part=$(date -v+friday +%Y-%m-%d)
            ;;
        "next saturday"|"saturday"|"sat")
            date_part=$(date -v+saturday +%Y-%m-%d)
            ;;
        "next sunday"|"sunday"|"sun")
            date_part=$(date -v+sunday +%Y-%m-%d)
            ;;
        *)
            # Try to parse with date command
            date_part=$(date -j -f "%B %d" "$input" +%Y-%m-%d 2>/dev/null) || \
            date_part=$(date -j -f "%b %d" "$input" +%Y-%m-%d 2>/dev/null) || \
            date_part=$(date -j -f "%m/%d" "$input" +%Y-%m-%d 2>/dev/null) || \
            date_part=""

            if [[ -z "$date_part" ]]; then
                echo "Error: Cannot parse date '$input'" >&2
                return 1
            fi
            ;;
    esac

    # Combine date and time
    if [[ -n "$time_part" ]]; then
        echo "$date_part $time_part"
    else
        echo "$date_part"
    fi
}

# Add reminder with natural language date support
add_reminder_natural() {
    local title="$1"
    local list_name="${2:-Inbox}"
    local due_natural="${3:-}"
    local notes="${4:-}"
    local flagged="${5:-false}"

    local due_date=""
    if [[ -n "$due_natural" ]]; then
        due_date=$(parse_date "$due_natural") || return 1
    fi

    add_reminder "$title" "$list_name" "$notes" "$due_date" "$flagged"
}

# ============================================================================
# SCAN HELPER — shared scaffolding for all-lists reminder queries
# ============================================================================
#
# scan_reminders COMPLETED_FILTER PREDICATE_FRAG ROW_FRAG [user_arg ...]
#
# $1 — AppleScript whose-clause fragment appended to "reminders of lst whose"
#      (e.g. "completed is false", "completed is true")
# $2 — AppleScript boolean expression (true/false) evaluated per reminder r.
#      May reference: r, rid, rname, rbody, rdue, rdueStr, rflagged, rlist,
#      theQuery (= the first user arg). Use "true" to include every reminder
#      passing the whose-clause.
# $3 — AppleScript expression appended to output per matching r (the TSV row).
#      Must end with & "\n".  Same vars available as above.
# $4+ — optional extra argv items passed into the script as argv items 3, 4, …
#        (argv item 1 = $1, argv item 2 = $2 are unused at runtime; the real
#         predicate/row are baked in at heredoc generation time as script-
#         controlled fragments — NOT user input).
#        The first extra arg becomes theQuery inside AppleScript.
#
# NOTE: predicate/row fragments are script-controlled strings (not user input)
#       and are safely interpolated via bash into the heredoc body.
#       User-supplied values are passed via argv (items 3+).
#
scan_reminders() {
    local whose_filter="$1"
    local predicate_frag="$2"
    local row_frag="$3"
    shift 3
    # remaining "$@" are user-supplied args forwarded via osascript argv

    osascript - "$@" <<APPLESCRIPT
on run argv
    -- argv item 1+ are user-supplied strings (e.g. search query, context tag)
    set theQuery to ""
    if (count of argv) >= 1 then set theQuery to item 1 of argv

    tell application "Reminders"
        set output to ""
        repeat with lst in lists
            set rems to (reminders of lst whose ${whose_filter})
            repeat with r in rems
                set rid to id of r
                set rname to name of r
                set rbody to body of r
                if rbody is missing value then set rbody to ""
                set rdue to due date of r
                if rdue is missing value then
                    set rdueStr to ""
                else
                    set rdueStr to (rdue as string)
                end if
                set rflagged to flagged of r
                set rlist to name of container of r

                if ${predicate_frag} then
                    set output to output & ${row_frag}
                end if
            end repeat
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

# ============================================================================
# LIST OPERATIONS
# ============================================================================

list_all_lists() {
    osascript -e 'tell application "Reminders" to get name of every list'
}

ensure_gtd_lists() {
    # Create GTD lists if they don't exist
    local lists=("Inbox" "Next Actions" "Waiting For" "Someday" "Projects")
    for list_name in "${lists[@]}"; do
        osascript - "$list_name" <<'APPLESCRIPT' 2>/dev/null || true
on run argv
    set theList to item 1 of argv
    tell application "Reminders"
        if not (exists list theList) then
            make new list with properties {name:theList}
        end if
    end tell
end run
APPLESCRIPT
    done
    echo "GTD lists ready"
}

# ============================================================================
# READ OPERATIONS
# ============================================================================

get_list() {
    local list_name="${1:-Inbox}"
    # Single-list scan — does NOT include a list-name column (different schema)
    osascript - "$list_name" <<'APPLESCRIPT'
on run argv
    set theList to item 1 of argv
    tell application "Reminders"
        set output to ""
        set rems to (reminders of list theList whose completed is false)
        repeat with r in rems
            set rid to id of r
            set rname to name of r
            set rbody to body of r
            if rbody is missing value then set rbody to ""
            set rdue to due date of r
            if rdue is missing value then
                set rdueStr to ""
            else
                set rdueStr to (rdue as string)
            end if
            set rflagged to flagged of r
            set rpriority to priority of r
            set output to output & rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rflagged & "\t" & rpriority & "\n"
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

get_today() {
    # Get reminders due today or flagged
    # Uses a complex conditional that can't be expressed as a simple whose-clause,
    # so it runs its own osascript with the shared field-prep pattern.
    osascript <<'APPLESCRIPT'
tell application "Reminders"
    set output to ""
    set today to current date
    set today's time to 0
    set tomorrow to today + 1 * days

    repeat with lst in lists
        set rems to (reminders of lst whose completed is false)
        repeat with r in rems
            set rdue to due date of r
            set rflagged to flagged of r
            set include to false

            if rflagged then
                set include to true
            else if rdue is not missing value then
                if rdue ≥ today and rdue < tomorrow then
                    set include to true
                end if
            end if

            if include then
                set rid to id of r
                set rname to name of r
                set rbody to body of r
                if rbody is missing value then set rbody to ""
                set rlist to name of container of r
                if rdue is missing value then
                    set rdueStr to ""
                else
                    set rdueStr to (rdue as string)
                end if
                set output to output & rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rflagged & "\t" & rlist & "\n"
            end if
        end repeat
    end repeat
    return output
end tell
APPLESCRIPT
}

get_upcoming() {
    # Columns: id, name, body, due, listName
    # Uses 'today' date arithmetic — kept as own script since scan_reminders
    # does not define the 'today' variable.
    osascript <<'APPLESCRIPT'
tell application "Reminders"
    set output to ""
    set today to current date
    set today's time to 0

    repeat with lst in lists
        set rems to (reminders of lst whose completed is false)
        repeat with r in rems
            set rdue to due date of r
            if rdue is not missing value and rdue > today then
                set rid to id of r
                set rname to name of r
                set rbody to body of r
                if rbody is missing value then set rbody to ""
                set rlist to name of container of r
                set rdueStr to (rdue as string)
                set output to output & rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rlist & "\n"
            end if
        end repeat
    end repeat
    return output
end tell
APPLESCRIPT
}

get_completed() {
    local days="${1:-7}"
    # Columns: id, name, completionDate, listName
    # Uses completed is true + cutoff filter; cutoff is a script-controlled integer.
    osascript - "$days" <<'APPLESCRIPT'
on run argv
    set theDays to (item 1 of argv) as integer
    tell application "Reminders"
        set output to ""
        set cutoff to (current date) - theDays * days

        repeat with lst in lists
            set rems to (reminders of lst whose completed is true)
            repeat with r in rems
                set cdate to completion date of r
                if cdate is not missing value and cdate > cutoff then
                    set rid to id of r
                    set rname to name of r
                    set rlist to name of container of r
                    set cdateStr to (cdate as string)
                    set output to output & rid & "\t" & rname & "\t" & cdateStr & "\t" & rlist & "\n"
                end if
            end repeat
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

# ============================================================================
# SEARCH OPERATIONS
# ============================================================================

search_reminders() {
    local query="$1"
    # Columns: id, name, body, due, flagged, listName
    scan_reminders \
        "completed is false" \
        '(rname contains theQuery) or (rbody contains theQuery)' \
        'rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rflagged & "\t" & rlist & "\n"' \
        "$query"
}

search_by_priority() {
    local priority="$1"  # 0=none, 1=high, 5=medium, 9=low
    # Columns: id, name, body, listName
    # priority is a script-controlled integer — safe to interpolate
    scan_reminders \
        "completed is false and priority is ${priority}" \
        "true" \
        'rid & "\t" & rname & "\t" & rbody & "\t" & rlist & "\n"'
}

search_flagged() {
    # Columns: id, name, body, due, listName
    scan_reminders \
        "completed is false and flagged is true" \
        "true" \
        'rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rlist & "\n"'
}

# ============================================================================
# WRITE OPERATIONS
# ============================================================================

add_reminder() {
    local title="$1"
    local list_name="${2:-Inbox}"
    local notes="${3:-}"
    local due_date="${4:-}"  # Format: YYYY-MM-DD or YYYY-MM-DD HH:MM
    local flagged="${5:-false}"
    local priority="${6:-0}"  # 0=none, 1=high, 5=medium, 9=low

    local flagged_bool="false"
    if [[ "$flagged" == "true" ]]; then
        flagged_bool="true"
    fi

    if [[ -n "$due_date" ]]; then
        osascript - "$title" "$list_name" "$notes" "$due_date" "$flagged_bool" "$priority" <<'APPLESCRIPT'
on run argv
    set theTitle to item 1 of argv
    set theList to item 2 of argv
    set theNotes to item 3 of argv
    set theDue to item 4 of argv
    set theFlagged to (item 5 of argv) as boolean
    set thePriority to (item 6 of argv) as integer
    tell application "Reminders"
        tell list theList
            set newReminder to make new reminder with properties {name:theTitle, body:theNotes, flagged:theFlagged, priority:thePriority, due date:date theDue}
            return id of newReminder
        end tell
    end tell
end run
APPLESCRIPT
    else
        osascript - "$title" "$list_name" "$notes" "$flagged_bool" "$priority" <<'APPLESCRIPT'
on run argv
    set theTitle to item 1 of argv
    set theList to item 2 of argv
    set theNotes to item 3 of argv
    set theFlagged to (item 4 of argv) as boolean
    set thePriority to (item 5 of argv) as integer
    tell application "Reminders"
        tell list theList
            set newReminder to make new reminder with properties {name:theTitle, body:theNotes, flagged:theFlagged, priority:thePriority}
            return id of newReminder
        end tell
    end tell
end run
APPLESCRIPT
    fi
}

update_reminder() {
    local reminder_id="$1"
    local property="$2"  # name, body, due date, flagged, priority, completed
    local value="$3"

    case "$property" in
        "name"|"body")
            osascript - "$reminder_id" "$value" <<APPLESCRIPT
on run argv
    set theID to item 1 of argv
    set theValue to item 2 of argv
    tell application "Reminders"
        set r to reminder id theID
        set ${property} of r to theValue
    end tell
end run
APPLESCRIPT
            ;;
        "flagged"|"completed")
            osascript - "$reminder_id" <<APPLESCRIPT
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        set ${property} of r to ${value}
    end tell
end run
APPLESCRIPT
            ;;
        "priority")
            osascript - "$reminder_id" <<APPLESCRIPT
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        set priority of r to ${value}
    end tell
end run
APPLESCRIPT
            ;;
        "due")
            if [[ -z "$value" || "$value" == "none" ]]; then
                osascript - "$reminder_id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        set due date of r to missing value
    end tell
end run
APPLESCRIPT
            else
                osascript - "$reminder_id" "$value" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    set theDate to item 2 of argv
    tell application "Reminders"
        set r to reminder id theID
        set due date of r to date theDate
    end tell
end run
APPLESCRIPT
            fi
            ;;
    esac
}

move_reminder() {
    local reminder_id="$1"
    local target_list="$2"

    # Get current list for undo
    local current_list
    current_list=$(osascript - "$reminder_id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        return name of container of r
    end tell
end run
APPLESCRIPT
    ) || true

    osascript - "$reminder_id" "$target_list" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    set theList to item 2 of argv
    tell application "Reminders"
        set r to reminder id theID
        set targetList to list theList
        move r to targetList
    end tell
end run
APPLESCRIPT

    # Save for undo
    if [[ -n "$current_list" ]]; then
        save_undo "move" "$reminder_id" "$current_list"
    fi
}

complete_reminder() {
    local reminder_id="$1"

    # Save for undo before completing
    save_undo "complete" "$reminder_id" ""

    osascript - "$reminder_id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        set completed of r to true
    end tell
end run
APPLESCRIPT
}

# Safe delete with confirmation message
delete_reminder() {
    local reminder_id="$1"
    local force="${2:-false}"

    # Get name for confirmation
    local name
    name=$(osascript - "$reminder_id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        return name of r
    end tell
end run
APPLESCRIPT
    ) || true

    if [[ "$force" != "true" && "$force" != "-f" ]]; then
        echo "Deleting: '$name' (cannot be undone)"
    fi

    osascript - "$reminder_id" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    tell application "Reminders"
        set r to reminder id theID
        delete r
    end tell
end run
APPLESCRIPT

    echo "Deleted: $name"
}

# ============================================================================
# GTD-SPECIFIC OPERATIONS
# ============================================================================

# Move from Inbox to Next Actions with optional tags in notes
process_to_next() {
    local reminder_id="$1"
    local context="${2:-}"    # @home, @office, @errands, @calls
    local energy="${3:-}"     # #high, #low, #quick
    local duration="${4:-}"   # #5min, #15min, #30min, #1hour, #deep

    # Build tags string
    local tags=""
    [[ -n "$context" ]] && tags="$context"
    [[ -n "$energy" ]] && tags="$tags $energy"
    [[ -n "$duration" ]] && tags="$tags $duration"
    tags=$(echo "$tags" | xargs)  # trim

    osascript - "$reminder_id" "$tags" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    set tagLine to item 2 of argv
    tell application "Reminders"
        set r to reminder id theID
        set currentBody to body of r
        if currentBody is missing value then set currentBody to ""

        if tagLine is not "" then
            if currentBody is "" then
                set body of r to tagLine
            else
                set body of r to tagLine & return & currentBody
            end if
        end if

        set targetList to list "Next Actions"
        move r to targetList
    end tell
end run
APPLESCRIPT
}

# Move to Waiting For with who/what info
delegate_reminder() {
    local reminder_id="$1"
    local waiting_for="$2"  # Person or thing waiting for

    osascript - "$reminder_id" "$waiting_for" <<'APPLESCRIPT'
on run argv
    set theID to item 1 of argv
    set theWaiting to item 2 of argv
    tell application "Reminders"
        set r to reminder id theID
        set currentBody to body of r
        if currentBody is missing value then set currentBody to ""

        set waitingLine to "@waiting: " & theWaiting
        if currentBody is "" then
            set body of r to waitingLine
        else
            set body of r to waitingLine & return & currentBody
        end if

        set targetList to list "Waiting For"
        move r to targetList
    end tell
end run
APPLESCRIPT
}

# Move to Someday
defer_reminder() {
    local reminder_id="$1"
    move_reminder "$reminder_id" "Someday"
}

# Batch defer all stale items (for recovery/bankruptcy)
batch_defer_stale() {
    local days="${1:-14}"
    local count=0

    # Get stale items
    local stale_output=$(get_stale "$days")

    if [[ -z "$stale_output" ]]; then
        echo "No stale items older than $days days"
        return
    fi

    echo "Deferring items older than $days days..."

    while IFS=$'\t' read -r id name date list; do
        [[ -z "$id" ]] && continue
        # Skip if already in Someday
        if [[ "$list" == "Someday" ]]; then
            continue
        fi
        move_reminder "$id" "Someday" 2>/dev/null && {
            echo "  → $name"
            ((count++))
        }
    done <<< "$stale_output"

    echo "Deferred $count items to Someday"
}

# Get items by context tag (searches in notes)
get_by_context() {
    local context="$1"  # @home, @office, etc.
    # Columns: id, name, body, due, listName
    scan_reminders \
        "completed is false" \
        "rbody is not missing value and rbody contains theQuery" \
        'rid & "\t" & rname & "\t" & rbody & "\t" & rdueStr & "\t" & rlist & "\n"' \
        "$context"
}

# Get stale items (no activity in X days)
get_stale() {
    local days="${1:-7}"
    # Columns: id, name, modDate, listName
    # days is a script-controlled integer — safe to interpolate
    osascript - "$days" <<'APPLESCRIPT'
on run argv
    set theDays to (item 1 of argv) as integer
    tell application "Reminders"
        set output to ""
        set cutoff to (current date) - theDays * days

        repeat with lst in lists
            set rems to (reminders of lst whose completed is false)
            repeat with r in rems
                set mdate to modification date of r
                if mdate < cutoff then
                    set rid to id of r
                    set rname to name of r
                    set rlist to name of container of r
                    set mdateStr to (mdate as string)
                    set output to output & rid & "\t" & rname & "\t" & mdateStr & "\t" & rlist & "\n"
                end if
            end repeat
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

# Check project health - projects without recent next actions
get_orphan_projects() {
    osascript <<'APPLESCRIPT'
tell application "Reminders"
    set output to ""
    set projectList to list "Projects"
    set nextList to list "Next Actions"

    set projects to reminders of projectList whose completed is false
    repeat with p in projects
        set pname to name of p
        set pid to id of p
        set pnotes to body of p
        if pnotes is missing value then set pnotes to ""

        -- Search for related next actions (by name match or tag)
        set hasAction to false
        set nextActions to reminders of nextList whose completed is false
        repeat with na in nextActions
            set naName to name of na
            set naNotes to body of na
            if naNotes is missing value then set naNotes to ""

            -- Check if next action references this project
            if naName contains pname or naNotes contains pname then
                set hasAction to true
                exit repeat
            end if
        end repeat

        if not hasAction then
            set output to output & pid & "\t" & pname & "\t" & "no next action" & "\n"
        end if
    end repeat
    return output
end tell
APPLESCRIPT
}

# Get waiting items with age
get_waiting_with_age() {
    osascript <<'APPLESCRIPT'
tell application "Reminders"
    set output to ""
    set today to current date
    set waitList to list "Waiting For"

    set rems to reminders of waitList whose completed is false
    repeat with r in rems
        set rid to id of r
        set rname to name of r
        set rbody to body of r
        if rbody is missing value then set rbody to ""
        set mdate to modification date of r
        set ageInDays to ((today - mdate) / days) as integer

        -- Extract who from @waiting: tag
        set waitingFor to ""
        if rbody contains "@waiting:" then
            set AppleScript's text item delimiters to "@waiting: "
            set parts to text items of rbody
            if (count of parts) > 1 then
                set waitingFor to item 2 of parts
                set AppleScript's text item delimiters to return
                set waitingFor to item 1 of (text items of waitingFor)
            end if
        end if

        set output to output & rid & "\t" & rname & "\t" & waitingFor & "\t" & ageInDays & " days\n"
    end repeat
    return output
end tell
APPLESCRIPT
}

# Count items per list
get_counts() {
    osascript <<'APPLESCRIPT'
tell application "Reminders"
    set output to ""
    repeat with lst in lists
        set listName to name of lst
        set count_ to count of (reminders of lst whose completed is false)
        set output to output & listName & "\t" & count_ & "\n"
    end repeat
    return output
end tell
APPLESCRIPT
}

# ============================================================================
# MAIN DISPATCHER
# ============================================================================

case "${1:-help}" in
    # List operations
    "lists") list_all_lists ;;
    "setup") ensure_gtd_lists ;;

    # Read operations
    "inbox") get_list "Inbox" ;;
    "next") get_list "Next Actions" ;;
    "waiting") get_list "Waiting For" ;;
    "someday") get_list "Someday" ;;
    "projects") get_list "Projects" ;;
    "list") get_list "$2" ;;
    "today") get_today ;;
    "upcoming") get_upcoming ;;
    "completed") get_completed "${2:-7}" ;;
    "counts") get_counts ;;

    # Search operations
    "search") search_reminders "$2" ;;
    "priority") search_by_priority "$2" ;;
    "flagged") search_flagged ;;
    "context") get_by_context "$2" ;;
    "stale") get_stale "${2:-7}" ;;

    # Write operations
    "add") add_reminder "$2" "${3:-Inbox}" "${4:-}" "${5:-}" "${6:-false}" "${7:-0}" ;;
    "add-natural") add_reminder_natural "$2" "${3:-Inbox}" "$4" "${5:-}" "${6:-false}" ;;
    "parse-date") parse_date "$2" ;;
    "update") update_reminder "$2" "$3" "$4" ;;
    "move") move_reminder "$2" "$3" ;;
    "complete") complete_reminder "$2" ;;
    "delete") delete_reminder "$2" ;;

    # GTD operations
    "process") process_to_next "$2" "$3" "$4" "$5" ;;
    "delegate") delegate_reminder "$2" "$3" ;;
    "defer") defer_reminder "$2" ;;
    "batch-defer") batch_defer_stale "${2:-14}" ;;
    "orphan-projects") get_orphan_projects ;;
    "waiting-age") get_waiting_with_age ;;
    "undo") do_undo ;;

    # Help
    *)
        echo "GTD Reminders CLI"
        echo ""
        echo "List Operations:"
        echo "  lists              - List all reminder lists"
        echo "  setup              - Create GTD lists if missing"
        echo ""
        echo "Read Operations:"
        echo "  inbox              - Get Inbox items"
        echo "  next               - Get Next Actions"
        echo "  waiting            - Get Waiting For items"
        echo "  someday            - Get Someday items"
        echo "  projects           - Get Projects"
        echo "  list <name>        - Get items from specific list"
        echo "  today              - Get today's items (due today or flagged)"
        echo "  upcoming           - Get upcoming items with due dates"
        echo "  completed [days]   - Get completed items (default: 7 days)"
        echo "  counts             - Get item counts per list"
        echo ""
        echo "Search Operations:"
        echo "  search <query>     - Search by text"
        echo "  priority <0-9>     - Search by priority (1=high, 5=med, 9=low)"
        echo "  flagged            - Get flagged items"
        echo "  context <tag>      - Get items by context (@home, @office, etc.)"
        echo "  stale [days]       - Get stale items (default: 7 days)"
        echo ""
        echo "Write Operations:"
        echo "  add <title> [list] [notes] [due] [flagged] [priority]"
        echo "  add-natural <title> [list] <due> [notes] [flagged]"
        echo "      due: 'tomorrow', 'next monday', 'fri 2pm', 'Jan 15', etc."
        echo "  parse-date <string>  - Test date parsing"
        echo "  update <id> <property> <value>"
        echo "  move <id> <list>   - Move to another list"
        echo "  complete <id>      - Mark as complete"
        echo "  delete <id>        - Delete reminder"
        echo ""
        echo "GTD Operations:"
        echo "  process <id> [context] [energy] [duration]"
        echo "  delegate <id> <waiting_for>"
        echo "  defer <id>         - Move to Someday"
        echo "  batch-defer [days] - Defer all stale items (default: 14 days)"
        echo "  orphan-projects    - Find projects without next actions"
        echo "  waiting-age        - Show waiting items with age"
        echo "  undo               - Undo last move/complete action"
        ;;
esac
