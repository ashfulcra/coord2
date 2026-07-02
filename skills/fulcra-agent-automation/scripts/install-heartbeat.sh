#!/usr/bin/env bash
# install-heartbeat.sh — schedule `coord-engine reconcile <team>` on a timer so a
# fulcra-agent-teams space's index/views stay healed without a human running it.
#
# Usage:
#   install-heartbeat.sh <team> [interval-minutes]   # default 20
#   install-heartbeat.sh --uninstall <team>
#
# macOS -> a launchd LaunchAgent; Linux -> a crontab line. Idempotent. Requires
# `coord-engine` and `fulcra-api` (authenticated) on PATH.
set -euo pipefail

UNINSTALL=0
if [[ "${1:-}" == "--uninstall" ]]; then UNINSTALL=1; shift; fi
TEAM="${1:?usage: install-heartbeat.sh <team> [interval-minutes] | --uninstall <team>}"
INTERVAL="${2:-20}"
LABEL="com.fulcra.coord-engine.heartbeat.${TEAM}"
CMD="$(command -v coord-engine || echo coord-engine) reconcile ${TEAM}"

os="$(uname -s)"
if [[ "$os" == "Darwin" ]]; then
  PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
  LOGDIR="$HOME/Library/Logs/coord-engine"; mkdir -p "$LOGDIR"
  if [[ "$UNINSTALL" == "1" ]]; then
    launchctl unload "$PLIST" 2>/dev/null || true; rm -f "$PLIST"
    echo "uninstalled launchd heartbeat for team/${TEAM}"; exit 0
  fi
  launchctl unload "$PLIST" 2>/dev/null || true
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>/bin/sh</string><string>-c</string><string>${CMD}</string>
  </array>
  <key>StartInterval</key><integer>$(( INTERVAL * 60 ))</integer>
  <key>StandardErrorPath</key><string>${LOGDIR}/heartbeat-${TEAM}.err.log</string>
  <key>StandardOutPath</key><string>${LOGDIR}/heartbeat-${TEAM}.out.log</string>
</dict></plist>
PLIST
  launchctl load "$PLIST"
  echo "installed launchd heartbeat: team/${TEAM} every ${INTERVAL}m ($PLIST)"
else
  LINE="*/${INTERVAL} * * * * ${CMD} >> \$HOME/.cache/coord-engine/heartbeat-${TEAM}.log 2>&1  # ${LABEL}"
  mkdir -p "$HOME/.cache/coord-engine"
  current="$(crontab -l 2>/dev/null || true)"
  filtered="$(printf '%s\n' "$current" | grep -v "# ${LABEL}\$" || true)"
  if [[ "$UNINSTALL" == "1" ]]; then
    printf '%s\n' "$filtered" | crontab -
    echo "uninstalled cron heartbeat for team/${TEAM}"; exit 0
  fi
  printf '%s\n%s\n' "$filtered" "$LINE" | grep -v '^$' | crontab -
  echo "installed cron heartbeat: team/${TEAM} every ${INTERVAL}m"
fi
