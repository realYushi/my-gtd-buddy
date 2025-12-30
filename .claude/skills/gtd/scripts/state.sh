#!/bin/bash
# GTD State Management
# Usage: ./scripts/state.sh <command> [args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$SCRIPT_DIR/../state.yaml"

# Ensure state file exists with full structure
init_state() {
    if [[ ! -f "$STATE_FILE" ]]; then
        cat > "$STATE_FILE" << 'EOF'
# GTD State

last_session:
  date: null
  mode: null
  items_processed: 0

last_review:
  date: null
  completed_count: 0
  focus: null

# Weekly trends (rolling 4 weeks)
trends:
  weekly_completed: []
  weekly_processed: []
  weekly_deferred: []

# Context usage frequency
contexts:
  home: 0
  office: 0
  errands: 0
  calls: 0

# Observed patterns
patterns:
  peak_days: []
  defer_days: []
  avg_process_velocity: 0

preferences:
  processing_style: quick
EOF
    fi
}

# Read entire state
read_state() {
    init_state
    cat "$STATE_FILE"
}

# Update session info
# Usage: update_session <mode> <items_processed>
update_session() {
    local mode="${1:-process}"
    local items="${2:-0}"
    local today=$(date +%Y-%m-%d)

    init_state

    yq -i ".last_session.date = \"$today\" | .last_session.mode = \"$mode\" | .last_session.items_processed = $items" "$STATE_FILE"

    echo "Updated: $mode, $items items"
}

# Update review info
# Usage: update_review <completed_count> [focus]
update_review() {
    local count="${1:-0}"
    local focus="${2:-null}"
    local today=$(date +%Y-%m-%d)

    init_state

    yq -i ".last_review.date = \"$today\" | .last_review.completed_count = $count | .last_review.focus = \"$focus\"" "$STATE_FILE"

    echo "Review updated: $count completed"
}

# Get days since last review
days_since_review() {
    init_state
    local last_date=$(yq ".last_review.date" "$STATE_FILE")

    if [[ "$last_date" == "null" || -z "$last_date" ]]; then
        echo "never"
        return
    fi

    local last_ts=$(date -j -f "%Y-%m-%d" "$last_date" "+%s" 2>/dev/null || echo "0")
    local now_ts=$(date "+%s")
    local diff=$(( (now_ts - last_ts) / 86400 ))
    echo "$diff"
}

# Quick health summary
health() {
    init_state
    local last=$(yq ".last_session.date" "$STATE_FILE")
    local review_days=$(days_since_review)
    echo "Last session: $last"
    echo "Days since review: $review_days"
}

# ============================================================================
# TREND TRACKING
# ============================================================================

# Increment context usage
# Usage: increment_context <context>
increment_context() {
    local context="$1"  # home, office, errands, calls
    init_state

    # Use default 0 if null, then increment
    yq -i ".contexts.$context = (.contexts.$context // 0) + 1" "$STATE_FILE"
}

# Add to weekly trends (called at end of week/review)
# Usage: update_weekly_trends <completed> <processed> <deferred>
update_weekly_trends() {
    local completed="${1:-0}"
    local processed="${2:-0}"
    local deferred="${3:-0}"

    init_state

    # Add new values to arrays and keep only last 4
    yq -i ".trends.weekly_completed += [$completed] | .trends.weekly_completed |= .[-4:]" "$STATE_FILE"
    yq -i ".trends.weekly_processed += [$processed] | .trends.weekly_processed |= .[-4:]" "$STATE_FILE"
    yq -i ".trends.weekly_deferred += [$deferred] | .trends.weekly_deferred |= .[-4:]" "$STATE_FILE"

    echo "Trends updated"
}

# Update average processing velocity
# Usage: update_velocity <items_this_session>
update_velocity() {
    local items="$1"
    init_state

    # Exponential moving average (weight recent more)
    # yq can do basic math
    yq -i ".patterns.avg_process_velocity = ((.patterns.avg_process_velocity // 0) * 0.7 + $items * 0.3)" "$STATE_FILE"
}

# Record peak/defer day pattern
# Usage: record_day_pattern <type> <day>
# type: peak | defer
record_day_pattern() {
    local type="$1"  # peak or defer
    local day="$2"   # Monday, Tuesday, etc.
    local key="${type}_days"

    init_state

    # Add if not present (idempotent)
    yq -i ".patterns.$key += [\"$day\"] | .patterns.$key |= unique" "$STATE_FILE"
}

# Get trends summary
get_trends() {
    init_state
    echo "=== Trends (last 4 weeks) ==="
    yq ".trends" "$STATE_FILE"
    echo ""
    echo "=== Patterns ==="
    yq ".patterns" "$STATE_FILE"
    echo ""
    echo "=== Context Usage ==="
    yq ".contexts" "$STATE_FILE"
}

# ============================================================================
# MAIN
# ============================================================================

if ! command -v yq &> /dev/null; then
    echo "Error: yq is required. Install with: brew install yq"
    exit 1
fi

case "${1:-help}" in
    "init") init_state ;;
    "read") read_state ;;
    "session") update_session "$2" "$3" ;;
    "review") update_review "$2" "$3" ;;
    "review-days") days_since_review ;;
    "health") health ;;
    "trends") get_trends ;;
    "context") increment_context "$2" ;;
    "weekly") update_weekly_trends "$2" "$3" "$4" ;;
    "velocity") update_velocity "$2" ;;
    "pattern") record_day_pattern "$2" "$3" ;;
    *)
        echo "Usage: state.sh <command>"
        echo ""
        echo "Basic:"
        echo "  read                  - Read state"
        echo "  session <mode> <n>    - Update after session"
        echo "  review <n> [focus]    - Update after review"
        echo "  review-days           - Days since review"
        echo "  health                - Health summary"
        echo ""
        echo "Tracking:"
        echo "  trends                - Show trends and patterns"
        echo "  context <name>        - Increment context usage (home/office/errands/calls)"
        echo "  weekly <c> <p> <d>    - Update weekly trends (completed/processed/deferred)"
        echo "  velocity <n>          - Update processing velocity"
        echo "  pattern <type> <day>  - Record day pattern (peak/defer)"
        ;;
esac
