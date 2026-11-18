#!/usr/bin/env bash
# Runs every check in checks/. Prints GREEN only if all pass; RED otherwise.
# Task checks (tracker.py, gto.py, accounts.py) are run only once their task
# output exists; until then STATE.md must not mark that task done.
set -u
cd "$(dirname "$0")/.." || exit 2
fail=0
for c in checks/check_*.py; do
  out=$(python3 -I "$c" 2>&1); rc=$?
  if [ $rc -ne 0 ]; then echo "FAIL $c"; echo "$out" | sed 's/^/    /'; fail=1
  else echo "ok   $c"; fi
done
if [ $fail -eq 0 ]; then echo GREEN; else echo RED; exit 1; fi
