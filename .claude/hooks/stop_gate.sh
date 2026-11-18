#!/usr/bin/env bash
# Stop gate: no "done" without GREEN from checks/run.sh.
# First stop on RED is blocked and the failures go back to Claude to fix.
# If Claude is already continuing from this hook (stop_hook_active), it may stop,
# but the RED result is shown so the turn cannot be reported as done.
input=$(cat)
cd "$(dirname "$0")/../.." || exit 0
out=$(bash checks/run.sh 2>&1)
if printf '%s\n' "$out" | tail -1 | grep -qx GREEN; then
  exit 0
fi
active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)
if [ "$active" = "true" ]; then
  jq -n --arg m "Checks are RED — this work is NOT done. Report it to Sumit as blocked:
$out" '{systemMessage: $m}'
  exit 0
fi
jq -n --arg r "checks/run.sh is RED. Fix the failures (never weaken a check), then stop again:
$out" '{decision: "block", reason: $r}'
