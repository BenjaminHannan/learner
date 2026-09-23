#!/bin/bash
# exp 241b M5 wall re-measure (director ruling item 3, 2026-09-23):
# D6 protocol (3 alternated runs each, 228 vs 241b), CPU only.
# New file; all outputs go under artifacts/claude-mouth241b-20260922/wall-remeasure/.
# Suite invocations mirror artifacts/claude-mouth241b-20260922/runs/run.sh exactly.
R=artifacts/claude-mouth241b-20260922/wall-remeasure
CF=artifacts/claude-determinism228-20260922/loop228-config.json
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
GATE=40
MAXWAIT=5400
STEP=120
wait_gate() {
  waited=0
  while true; do
    u=$(uptime)
    printf '%s\n' "$u" >> "$R/uptimes.log"
    l1=$(printf '%s' "$u" | perl -ne 'print $1 if /load averages:\s*([\d.]+)/')
    printf 'gate: load1=%s waited=%ss\n' "$l1" "$waited" >> "$R/uptimes.log"
    printf 'gate: load1=%s waited=%ss\n' "$l1" "$waited" >&2
    over=$(perl -e "print (($l1 >= $GATE) ? 1 : 0)")
    if [ "$over" = "0" ]; then printf '%s' "$l1"; return 0; fi
    if [ "$waited" -ge "$MAXWAIT" ]; then return 1; fi
    sleep $STEP
    waited=$((waited + STEP))
  done
}
: > "$R/uptimes.log"
: > "$R/walls.txt"
for k in 1 2 3; do
  for ag in 228 241b; do
    l1=$(wait_gate)
    grc=$?
    if [ $grc -ne 0 ]; then printf 'LOAD GATE NOT MET before agent=%s run=%s\n' "$ag" "$k" >> "$R/walls.txt"; printf 'NOTMET\n'; exit 2; fi
    printf 'RUN agent=%s run=%s load1=%s\n' "$ag" "$k" "$l1" >> "$R/walls.txt"
    if [ "$ag" = 228 ]; then AG=scripts/claude_loop228_agent.py; ML=""; SC=""; else AG=scripts/claude_loop241b_agent.py; ML="--mouthlog $R/mouth241b-run$k.log"; SC="--scorer241b"; fi
    t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    # shellcheck disable=SC2086
    uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/claude_mouth241b_suites.py --capture "$R/cap$ag-run$k" $ML $SC -- --agent $AG --config $CF --base 138i --only rt136,rt143,sessions152,bench --out "$R/out$ag-run$k" > "$R/suites-$ag-run$k.log" 2>&1
    rc=$?
    t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    printf 'WALL agent=%s run=%s rc=%s seconds=%s load1=%s\n' "$ag" "$k" "$rc" "$(perl -e "printf q(%.1f), $t1-$t0")" "$l1" >> "$R/walls.txt"
  done
done
printf 'ALLDONE\n' >> "$R/walls.txt"
printf 'ALLDONE\n'
