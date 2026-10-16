#!/bin/bash
# wait_for.sh LOG PATTERN [SECONDS]: wait (default 150 s) until PATTERN (extended regex) appears in LOG, then show the last lines without the R| payload
LOG=$1; PAT=$2; N=${3:-150}
for i in $(seq 1 $((N / 5))); do
  grep -q -E -- "$PAT" "$LOG" 2>/dev/null && break
  sleep 5
done
grep -v '^R|' "$LOG" | cut -c1-260 | tail -n ${4:-18}
