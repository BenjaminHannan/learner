#!/usr/bin/env bash
# Deadline guard for sleepb_pc5 (addendum 17, fourth try), used only if it keeps running: the same projection rule as sleepb_pc6.
# Within 5 min of night 2+ ending: the remaining nights at 1.25x that night's seconds, plus 75 min of final scoring. If that would end
# after $DEADLINE, it stops pc5's python only; pc5 then writes pull3/DONE (the looping thread's segment 1 starts) and clears GPU-BUSY.txt.
set -uo pipefail
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
P=$R/pull3
L=$R/add17d/sleepb/ab_ob_b4_nb/sleepb.log
DEADLINE=${DEADLINE:-2026-10-27T18:00:00Z}
exec >>"$P/run.log" 2>&1
echo "== sleepb-pc5guard start $(date -u +%FT%TZ), deadline $DEADLINE"
dl=$(date -d "$DEADLINE" +%s)
seen=0
while sleep 300; do
  [ -f "$P/DONE" ] && { echo "== sleepb-pc5guard: pc5 ended, guard stops $(date -u +%T)"; exit 0; }
  last=$(grep '^\[night [0-9]*\] done steps .* [0-9]*s$' "$L" | tail -1)
  n=$(echo "$last" | sed -n 's/^\[night \([0-9]*\)\].*/\1/p'); sec=$(echo "$last" | sed -n 's/.* \([0-9]*\)s$/\1/p')
  if [ -n "$n" ] && [ -n "$sec" ] && [ "$n" -ge 2 ] && [ "$n" -lt 7 ] && [ "$n" -ne "$seen" ]; then
    seen=$n
    end=$(( $(date +%s) + (7 - n) * sec * 5 / 4 + 4500 ))
    echo "== pc5guard: after night $n (${sec}s) projected end $(date -u -d @$end +%FT%TZ)"
    if [ "$end" -gt "$dl" ]; then
      echo "== pc5guard: after $DEADLINE; stopping pc5's python"; touch "$P/TOO-SLOW"
      pkill -f "sleepb.py --arm ab_ob_b4_nb --out $R/add17d/" ; exit 0
    fi
  fi
done
