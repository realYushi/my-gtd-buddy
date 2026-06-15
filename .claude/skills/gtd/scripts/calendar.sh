#!/bin/bash
# macOS Calendar AppleScript Wrapper
# Usage: ./calendar.sh <command> [args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# CALENDAR OPERATIONS
# ============================================================================

list_calendars() {
    osascript -e 'tell application "Calendar" to get name of every calendar'
}

# ============================================================================
# DATE PARSING HELPER
# ============================================================================

# parse_date_components YYYY-MM-DD
# Outputs: year month day  (leading zeros stripped)
parse_date_components() {
    local s="$1"
    local year="${s:0:4}"
    local month=$((10#${s:5:2}))
    local day=$((10#${s:8:2}))
    echo "$year $month $day"
}

# parse_datetime_components YYYY-MM-DD HH:MM
# Outputs: year month day hour min  (leading zeros stripped)
parse_datetime_components() {
    local s="$1"
    local date_part="${s:0:10}"
    local time_part="${s:11:5}"
    local year="${date_part:0:4}"
    local month=$((10#${date_part:5:2}))
    local day=$((10#${date_part:8:2}))
    local hour=$((10#${time_part:0:2}))
    local min=$((10#${time_part:3:2}))
    echo "$year $month $day $hour $min"
}

# ============================================================================
# READ OPERATIONS
# ============================================================================

# scan_events — emits 7-field TSV rows for events in a date window.
#   $1 = AppleScript fragment that sets winStart and winEnd (may use today_start)
#   $2 = optional AppleScript boolean predicate over event e (default: "true")
#   $3 = optional calendar name (routes through argv to avoid injection)
#
# All user-supplied strings (calendar name) are passed via argv, not interpolated.
# The window/predicate fragments are script-controlled (numeric offsets), not user input.
scan_events() {
    local window="$1"
    local predicate="${2:-true}"
    local calendar="${3:-}"

    osascript - "$calendar" <<APPLESCRIPT
on run argv
    set theCal to item 1 of argv
    tell application "Calendar"
        set today_start to (current date) - (time of (current date))
        $window
        set output to ""
        set cals to calendars
        if theCal is not "" then set cals to {calendar theCal}
        repeat with cal in cals
            set calName to name of cal
            repeat with e in (every event of cal whose start date >= winStart and start date < winEnd)
                if ($predicate) then
                    set eloc to location of e
                    if eloc is missing value then set eloc to ""
                    set output to output & (uid of e) & "\t" & (summary of e) & "\t" & (start date of e as string) & "\t" & (end date of e as string) & "\t" & eloc & "\t" & calName & "\t" & (allday event of e) & "\n"
                end if
            end repeat
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

get_today() {
    local calendar="${1:-}"
    scan_events \
        'set winStart to today_start
         set winEnd to today_start + 1 * days' \
        'true' \
        "$calendar"
}

get_tomorrow() {
    local calendar="${1:-}"
    scan_events \
        'set winStart to today_start + 1 * days
         set winEnd to today_start + 2 * days' \
        'true' \
        "$calendar"
}

get_week() {
    local calendar="${1:-}"
    scan_events \
        'set winStart to today_start
         set winEnd to today_start + 7 * days' \
        'true' \
        "$calendar"
}

get_date() {
    local date_str="$1"
    local calendar="${2:-}"
    read -r year month day <<< "$(parse_date_components "$date_str")"
    scan_events \
        "set targetDate to current date
         set year of targetDate to $year
         set month of targetDate to $month
         set day of targetDate to $day
         set time of targetDate to 0
         set winStart to targetDate
         set winEnd to targetDate + 1 * days" \
        'true' \
        "$calendar"
}

get_upcoming() {
    local days="${1:-7}"
    local calendar="${2:-}"
    scan_events \
        "set winStart to today_start
         set winEnd to today_start + $days * days" \
        'true' \
        "$calendar"
}

# ============================================================================
# SEARCH OPERATIONS
# ============================================================================

search_events() {
    local query="$1"
    local calendar="${2:-}"
    local days="${3:-30}"

    # query is user input — passed via argv to avoid AppleScript injection
    osascript - "$query" "$calendar" <<APPLESCRIPT
on run argv
    set theQuery to item 1 of argv
    set theCal to item 2 of argv
    tell application "Calendar"
        set today_start to (current date) - (time of (current date))
        set winStart to today_start
        set winEnd to today_start + $days * days
        set output to ""
        set cals to calendars
        if theCal is not "" then set cals to {calendar theCal}
        repeat with cal in cals
            set calName to name of cal
            repeat with e in (every event of cal whose start date >= winStart and start date < winEnd)
                set ename to summary of e
                set enotes to description of e
                if enotes is missing value then set enotes to ""
                if ename contains theQuery or enotes contains theQuery then
                    set eloc to location of e
                    if eloc is missing value then set eloc to ""
                    set output to output & (uid of e) & "\t" & ename & "\t" & (start date of e as string) & "\t" & (end date of e as string) & "\t" & eloc & "\t" & calName & "\t" & (allday event of e) & "\n"
                end if
            end repeat
        end repeat
        return output
    end tell
end run
APPLESCRIPT
}

# ============================================================================
# WRITE OPERATIONS
# ============================================================================

add_event() {
    local title="$1"
    local start_datetime="$2"  # Format: YYYY-MM-DD HH:MM
    local end_datetime="$3"    # Format: YYYY-MM-DD HH:MM
    local calendar="${4:-Personal}"
    local location="${5:-}"
    local notes="${6:-}"

    read -r sy sm sd sh smin <<< "$(parse_datetime_components "$start_datetime")"
    read -r ey em ed eh emin <<< "$(parse_datetime_components "$end_datetime")"

    osascript - "$title" "$location" "$notes" "$calendar" <<APPLESCRIPT
on run argv
    set theTitle to item 1 of argv
    set theLoc to item 2 of argv
    set theNotes to item 3 of argv
    set theCal to item 4 of argv
    tell application "Calendar"
        set startDate to current date
        set year of startDate to $sy
        set month of startDate to $sm
        set day of startDate to $sd
        set hours of startDate to $sh
        set minutes of startDate to $smin
        set seconds of startDate to 0

        set endDate to current date
        set year of endDate to $ey
        set month of endDate to $em
        set day of endDate to $ed
        set hours of endDate to $eh
        set minutes of endDate to $emin
        set seconds of endDate to 0

        tell calendar theCal
            set newEvent to make new event with properties {summary:theTitle, start date:startDate, end date:endDate, location:theLoc, description:theNotes}
            return uid of newEvent
        end tell
    end tell
end run
APPLESCRIPT
}

add_allday_event() {
    local title="$1"
    local date_str="$2"  # Format: YYYY-MM-DD
    local calendar="${3:-Personal}"
    local notes="${4:-}"

    read -r year month day <<< "$(parse_date_components "$date_str")"

    osascript - "$title" "$notes" "$calendar" <<APPLESCRIPT
on run argv
    set theTitle to item 1 of argv
    set theNotes to item 2 of argv
    set theCal to item 3 of argv
    tell application "Calendar"
        set eventDate to current date
        set year of eventDate to $year
        set month of eventDate to $month
        set day of eventDate to $day
        set time of eventDate to 0

        set endDate to eventDate + 1 * days

        tell calendar theCal
            set newEvent to make new event with properties {summary:theTitle, start date:eventDate, end date:endDate, allday event:true, description:theNotes}
            return uid of newEvent
        end tell
    end tell
end run
APPLESCRIPT
}

delete_event() {
    local event_id="$1"
    local calendar="$2"

    osascript - "$event_id" "$calendar" <<'APPLESCRIPT'
on run argv
    set theId to item 1 of argv
    set theCal to item 2 of argv
    tell application "Calendar"
        tell calendar theCal
            set evt to first event whose uid is theId
            delete evt
        end tell
    end tell
end run
APPLESCRIPT
}

# ============================================================================
# GAP DETECTION (for GTD)
# ============================================================================

find_gaps() {
    local min_minutes="${1:-30}"
    local calendar="${2:-}"

    # Calendar name passed via env (system attribute) to avoid AppleScript injection
    GTD_CAL="$calendar" osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set today_end to today_start + 1 * days
            set workStart to today_start + 9 * hours  -- 9 AM
            set workEnd to today_start + 18 * hours   -- 6 PM

            -- Collect all events for today
            set allEvents to {}
            set cals to calendars
            set theCal to (system attribute \"GTD_CAL\")
            if theCal is not \"\" then set cals to {calendar theCal}

            repeat with cal in cals
                set evts to (every event of cal whose start date ≥ workStart and start date < workEnd and allday event is false)
                repeat with e in evts
                    set end of allEvents to {startTime:start date of e, endTime:end date of e}
                end repeat
            end repeat

            -- Sort events by start time (simple bubble sort)
            repeat with i from 1 to (count of allEvents) - 1
                repeat with j from i + 1 to count of allEvents
                    if startTime of item j of allEvents < startTime of item i of allEvents then
                        set temp to item i of allEvents
                        set item i of allEvents to item j of allEvents
                        set item j of allEvents to temp
                    end if
                end repeat
            end repeat

            -- Find gaps
            set output to \"\"
            set minGap to $min_minutes * minutes
            set currentTime to workStart
            if currentTime < today then set currentTime to today

            repeat with evt in allEvents
                set evtStart to startTime of evt
                set evtEnd to endTime of evt

                if evtStart > currentTime then
                    set gapDuration to (evtStart - currentTime) / minutes
                    if gapDuration ≥ $min_minutes then
                        set output to output & (currentTime as string) & \"\t\" & (evtStart as string) & \"\t\" & (round gapDuration) & \" min\n\"
                    end if
                end if

                if evtEnd > currentTime then
                    set currentTime to evtEnd
                end if
            end repeat

            -- Check gap after last event until work end
            if currentTime < workEnd then
                set gapDuration to (workEnd - currentTime) / minutes
                if gapDuration ≥ $min_minutes then
                    set output to output & (currentTime as string) & \"\t\" & (workEnd as string) & \"\t\" & (round gapDuration) & \" min\n\"
                end if
            end if

            return output
        end tell
    "
}

get_free_time() {
    # Total free time today (in work hours)
    local calendar="${1:-}"

    # Calendar name passed via env (system attribute) to avoid AppleScript injection
    GTD_CAL="$calendar" osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set workStart to today_start + 9 * hours
            set workEnd to today_start + 18 * hours

            set totalBusy to 0
            set cals to calendars
            set theCal to (system attribute \"GTD_CAL\")
            if theCal is not \"\" then set cals to {calendar theCal}

            repeat with cal in cals
                set evts to (every event of cal whose start date ≥ workStart and start date < workEnd and allday event is false)
                repeat with e in evts
                    set estart to start date of e
                    set eend to end date of e
                    -- Clamp to work hours
                    if estart < workStart then set estart to workStart
                    if eend > workEnd then set eend to workEnd
                    set totalBusy to totalBusy + (eend - estart)
                end repeat
            end repeat

            set workHours to 9 * hours
            set freeTime to workHours - totalBusy
            set freeMinutes to round (freeTime / minutes)
            set freeHours to freeMinutes div 60
            set remainingMins to freeMinutes mod 60

            return (freeHours as string) & \"h \" & (remainingMins as string) & \"m free today (9AM-6PM)\"
        end tell
    "
}

# ============================================================================
# MAIN DISPATCHER
# ============================================================================

case "${1:-help}" in
    # Calendar operations
    "calendars") list_calendars ;;

    # Read operations
    "today") get_today "$2" ;;
    "tomorrow") get_tomorrow "$2" ;;
    "week") get_week "$2" ;;
    "date") get_date "$2" "$3" ;;
    "upcoming") get_upcoming "${2:-7}" "$3" ;;

    # Search operations
    "search") search_events "$2" "$3" "${4:-30}" ;;

    # Write operations
    "add") add_event "$2" "$3" "$4" "${5:-Personal}" "$6" "$7" ;;
    "add-allday") add_allday_event "$2" "$3" "${4:-Personal}" "$5" ;;
    "delete") delete_event "$2" "$3" ;;

    # GTD helpers
    "gaps") find_gaps "${2:-30}" "$3" ;;
    "free") get_free_time "$2" ;;

    # Help
    *)
        echo "macOS Calendar CLI"
        echo ""
        echo "Calendar Operations:"
        echo "  calendars          - List all calendars"
        echo ""
        echo "Read Operations:"
        echo "  today [calendar]   - Get today's events"
        echo "  tomorrow [calendar] - Get tomorrow's events"
        echo "  week [calendar]    - Get this week's events"
        echo "  date <YYYY-MM-DD> [calendar] - Get events for specific date"
        echo "  upcoming [days] [calendar] - Get upcoming events (default: 7 days)"
        echo ""
        echo "Search Operations:"
        echo "  search <query> [calendar] [days] - Search events (default: 30 days)"
        echo ""
        echo "Write Operations:"
        echo "  add <title> <start> <end> [calendar] [location] [notes]"
        echo "      start/end format: YYYY-MM-DD HH:MM"
        echo "  add-allday <title> <YYYY-MM-DD> [calendar] [notes]"
        echo "  delete <event_id> <calendar>"
        echo ""
        echo "GTD Helpers:"
        echo "  gaps [min_minutes] [calendar] - Find free gaps today (default: 30 min)"
        echo "  free [calendar]    - Show total free time today"
        echo ""
        echo "Output Format:"
        echo "  <id>  <title>  <start>  <end>  <location>  <calendar>  <allday>"
        ;;
esac
