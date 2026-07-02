#!/usr/bin/env bash
# listener-tick.sh — one scheduled inbox check for an agent. Invoked by the job
# install-listener.sh creates (or manually). On NEW items since the last tick:
# a macOS notification (osascript) or a log line, and optionally a consent-gated
# wake command. Exit 0 always (a tick never fails the schedule).
#
# Usage: listener-tick.sh <team> <agent> [wake-cmd...]
set -euo pipefail

TEAM="${1:?usage: listener-tick.sh <team> <agent> [wake-cmd...]}"
AGENT="${2:?usage: listener-tick.sh <team> <agent> [wake-cmd...]}"
shift 2 || true

STATE_DIR="${COORD_LISTENER_STATE:-$HOME/.cache/coord-engine}"
mkdir -p "$STATE_DIR"
SAFE_KEY="$(printf '%s-%s' "$TEAM" "$AGENT" | tr -c 'A-Za-z0-9_.-' '-')"
COUNT_FILE="$STATE_DIR/listener-$SAFE_KEY.count"

ITEMS="$(coord-engine inbox "$TEAM" --agent "$AGENT" --json 2>/dev/null || echo '[]')"
COUNT="$(printf '%s' "$ITEMS" | python3 -c 'import json,sys
try: print(len(json.load(sys.stdin)))
except Exception: print(0)')"
PREV="$(cat "$COUNT_FILE" 2>/dev/null || echo 0)"
printf '%s' "$COUNT" > "$COUNT_FILE"

if [[ "$COUNT" -gt "$PREV" ]]; then
  NEW=$(( COUNT - PREV ))
  MSG="coord2: ${NEW} new directive(s) for ${AGENT} in team/${TEAM} (${COUNT} open)"
  echo "$(date -u +%FT%TZ) $MSG"
  if command -v osascript >/dev/null 2>&1; then
    # display only; TEAM/AGENT are validated by the installer, but escape quotes anyway
    SAFE_MSG="${MSG//\"/}"
    osascript -e "display notification \"${SAFE_MSG}\" with title \"coord2 inbox\"" || true
  fi
  if [[ "$#" -gt 0 ]]; then
    # consent-gated wake command (installer requires explicit --wake-cmd)
    "$@" || echo "$(date -u +%FT%TZ) wake command failed (exit $?)" >&2
  fi
else
  echo "$(date -u +%FT%TZ) no new items (${COUNT} open) for ${AGENT}/${TEAM}"
fi
exit 0
