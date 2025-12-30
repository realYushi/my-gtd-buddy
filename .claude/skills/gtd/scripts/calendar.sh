#!/bin/bash
# macOS Calendar AppleScript Wrapper
# Usage: ./calendar.sh <command> [args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# ERROR HANDLING
# ============================================================================

# Run osascript with error handling
run_applescript() {
    local result
    local exit_code

    result=$(osascript -e "$1" 2>&1) && exit_code=0 || exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        if [[ "$result" == *"not found"* ]]; then
            echo "Error: Calendar or event not found" >&2
            return 1
        elif [[ "$result" == *"not running"* ]]; then
            echo "Error: Calendar app not running. Opening..." >&2
            open -a "Calendar"
            sleep 1
            result=$(osascript -e "$1" 2>&1) || {
                echo "Error: $result" >&2
                return 1
            }
        else
            echo "Error: $result" >&2
            return 1
        fi
    fi

    echo "$result"
}

# ============================================================================
# CALENDAR OPERATIONS
# ============================================================================

list_calendars() {
    osascript -e 'tell application "Calendar" to get name of every calendar'
}

# ============================================================================
# READ OPERATIONS
# ============================================================================

get_today() {
    local calendar="${1:-}"

    if [[ -n "$calendar" ]]; then
        osascript -e "
            tell application \"Calendar\"
                set today to current date
                set today_start to today - (time of today)
                set today_end to today_start + 1 * days

                set output to \"\"
                set cal to calendar \"$calendar\"
                set evts to (every event of cal whose start date ≥ today_start and start date < today_end)
                repeat with e in evts
                    set eid to uid of e
                    set ename to summary of e
                    set estart to start date of e
                    set eend to end date of e
                    set eloc to location of e
                    if eloc is missing value then set eloc to \"\"
                    set enotes to description of e
                    if enotes is missing value then set enotes to \"\"
                    set eallday to allday event of e
                    set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & enotes & \"\t\" & eallday & \"\n\"
                end repeat
                return output
            end tell
        "
    else
        osascript -e "
            tell application \"Calendar\"
                set today to current date
                set today_start to today - (time of today)
                set today_end to today_start + 1 * days

                set output to \"\"
                repeat with cal in calendars
                    set calName to name of cal
                    set evts to (every event of cal whose start date ≥ today_start and start date < today_end)
                    repeat with e in evts
                        set eid to uid of e
                        set ename to summary of e
                        set estart to start date of e
                        set eend to end date of e
                        set eloc to location of e
                        if eloc is missing value then set eloc to \"\"
                        set enotes to description of e
                        if enotes is missing value then set enotes to \"\"
                        set eallday to allday event of e
                        set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                    end repeat
                end repeat
                return output
            end tell
        "
    fi
}

get_tomorrow() {
    local calendar="${1:-}"

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set tomorrow_start to today_start + 1 * days
            set tomorrow_end to tomorrow_start + 1 * days

            set output to \"\"
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

            repeat with cal in cals
                set calName to name of cal
                set evts to (every event of cal whose start date ≥ tomorrow_start and start date < tomorrow_end)
                repeat with e in evts
                    set eid to uid of e
                    set ename to summary of e
                    set estart to start date of e
                    set eend to end date of e
                    set eloc to location of e
                    if eloc is missing value then set eloc to \"\"
                    set eallday to allday event of e
                    set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                end repeat
            end repeat
            return output
        end tell
    "
}

get_week() {
    local calendar="${1:-}"

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set week_end to today_start + 7 * days

            set output to \"\"
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

            repeat with cal in cals
                set calName to name of cal
                set evts to (every event of cal whose start date ≥ today_start and start date < week_end)
                repeat with e in evts
                    set eid to uid of e
                    set ename to summary of e
                    set estart to start date of e
                    set eend to end date of e
                    set eloc to location of e
                    if eloc is missing value then set eloc to \"\"
                    set eallday to allday event of e
                    set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                end repeat
            end repeat
            return output
        end tell
    "
}

get_date() {
    local date_str="$1"  # YYYY-MM-DD format
    local calendar="${2:-}"

    # Parse date components
    local year="${date_str:0:4}"
    local month="${date_str:5:2}"
    local day="${date_str:8:2}"

    # Remove leading zeros for AppleScript
    month=$((10#$month))
    day=$((10#$day))

    osascript -e "
        tell application \"Calendar\"
            set targetDate to current date
            set year of targetDate to $year
            set month of targetDate to $month
            set day of targetDate to $day
            set time of targetDate to 0
            set nextDay to targetDate + 1 * days

            set output to \"\"
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

            repeat with cal in cals
                set calName to name of cal
                set evts to (every event of cal whose start date ≥ targetDate and start date < nextDay)
                repeat with e in evts
                    set eid to uid of e
                    set ename to summary of e
                    set estart to start date of e
                    set eend to end date of e
                    set eloc to location of e
                    if eloc is missing value then set eloc to \"\"
                    set eallday to allday event of e
                    set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                end repeat
            end repeat
            return output
        end tell
    "
}

get_upcoming() {
    local days="${1:-7}"
    local calendar="${2:-}"

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set end_date to today_start + $days * days

            set output to \"\"
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

            repeat with cal in cals
                set calName to name of cal
                set evts to (every event of cal whose start date ≥ today_start and start date < end_date)
                repeat with e in evts
                    set eid to uid of e
                    set ename to summary of e
                    set estart to start date of e
                    set eend to end date of e
                    set eloc to location of e
                    if eloc is missing value then set eloc to \"\"
                    set eallday to allday event of e
                    set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                end repeat
            end repeat
            return output
        end tell
    "
}

# ============================================================================
# SEARCH OPERATIONS
# ============================================================================

search_events() {
    local query="$1"
    local calendar="${2:-}"
    local days="${3:-30}"

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set end_date to today_start + $days * days

            set output to \"\"
            set searchTerm to \"$query\"
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

            repeat with cal in cals
                set calName to name of cal
                set evts to (every event of cal whose start date ≥ today_start and start date < end_date)
                repeat with e in evts
                    set ename to summary of e
                    set enotes to description of e
                    if enotes is missing value then set enotes to \"\"

                    if ename contains searchTerm or enotes contains searchTerm then
                        set eid to uid of e
                        set estart to start date of e
                        set eend to end date of e
                        set eloc to location of e
                        if eloc is missing value then set eloc to \"\"
                        set eallday to allday event of e
                        set output to output & eid & \"\t\" & ename & \"\t\" & (estart as string) & \"\t\" & (eend as string) & \"\t\" & eloc & \"\t\" & calName & \"\t\" & eallday & \"\n\"
                    end if
                end repeat
            end repeat
            return output
        end tell
    "
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

    # Parse start date/time
    local start_date="${start_datetime:0:10}"
    local start_time="${start_datetime:11:5}"
    local start_year="${start_date:0:4}"
    local start_month="${start_date:5:2}"
    local start_day="${start_date:8:2}"
    local start_hour="${start_time:0:2}"
    local start_min="${start_time:3:2}"

    # Parse end date/time
    local end_date="${end_datetime:0:10}"
    local end_time="${end_datetime:11:5}"
    local end_year="${end_date:0:4}"
    local end_month="${end_date:5:2}"
    local end_day="${end_date:8:2}"
    local end_hour="${end_time:0:2}"
    local end_min="${end_time:3:2}"

    # Remove leading zeros
    start_month=$((10#$start_month))
    start_day=$((10#$start_day))
    start_hour=$((10#$start_hour))
    start_min=$((10#$start_min))
    end_month=$((10#$end_month))
    end_day=$((10#$end_day))
    end_hour=$((10#$end_hour))
    end_min=$((10#$end_min))

    osascript -e "
        tell application \"Calendar\"
            set startDate to current date
            set year of startDate to $start_year
            set month of startDate to $start_month
            set day of startDate to $start_day
            set hours of startDate to $start_hour
            set minutes of startDate to $start_min
            set seconds of startDate to 0

            set endDate to current date
            set year of endDate to $end_year
            set month of endDate to $end_month
            set day of endDate to $end_day
            set hours of endDate to $end_hour
            set minutes of endDate to $end_min
            set seconds of endDate to 0

            tell calendar \"$calendar\"
                set newEvent to make new event with properties {summary:\"$title\", start date:startDate, end date:endDate, location:\"$location\", description:\"$notes\"}
                return uid of newEvent
            end tell
        end tell
    "
}

add_allday_event() {
    local title="$1"
    local date_str="$2"  # Format: YYYY-MM-DD
    local calendar="${3:-Personal}"
    local notes="${4:-}"

    local year="${date_str:0:4}"
    local month="${date_str:5:2}"
    local day="${date_str:8:2}"

    month=$((10#$month))
    day=$((10#$day))

    osascript -e "
        tell application \"Calendar\"
            set eventDate to current date
            set year of eventDate to $year
            set month of eventDate to $month
            set day of eventDate to $day
            set time of eventDate to 0

            set endDate to eventDate + 1 * days

            tell calendar \"$calendar\"
                set newEvent to make new event with properties {summary:\"$title\", start date:eventDate, end date:endDate, allday event:true, description:\"$notes\"}
                return uid of newEvent
            end tell
        end tell
    "
}

delete_event() {
    local event_id="$1"
    local calendar="$2"

    osascript -e "
        tell application \"Calendar\"
            tell calendar \"$calendar\"
                set evt to first event whose uid is \"$event_id\"
                delete evt
            end tell
        end tell
    "
}

# ============================================================================
# GAP DETECTION (for GTD)
# ============================================================================

find_gaps() {
    local min_minutes="${1:-30}"
    local calendar="${2:-}"

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set today_end to today_start + 1 * days
            set workStart to today_start + 9 * hours  -- 9 AM
            set workEnd to today_start + 18 * hours   -- 6 PM

            -- Collect all events for today
            set allEvents to {}
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

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

    osascript -e "
        tell application \"Calendar\"
            set today to current date
            set today_start to today - (time of today)
            set workStart to today_start + 9 * hours
            set workEnd to today_start + 18 * hours

            set totalBusy to 0
            set cals to calendars
            if \"$calendar\" is not \"\" then
                set cals to {calendar \"$calendar\"}
            end if

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
