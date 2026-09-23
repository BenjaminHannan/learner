#!/bin/bash
# Merge 138p -- M7: blind panels (TEST-ONLY; never read item by item).
# For each panel: FIRST re-run the registered piece's own arm with exactly
# the runner and scorer that produced its registered rows and show it
# reproduces those rows (fidelity count). Then score 138p with that SAME
# runner and scorer. If fidelity is not 100%, the panel is VOID (report why;
# never score by hand).
# Panels: openpanel260 (arm 260), corrtail258 + corrpanel252 (arm 252c).
# Each panel runs ONCE per arm. usage: scripts/claude_138p_panel.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
AP=scripts/claude_loop138p_agent.py
CP=artifacts/claude-merge138p-20260923/loop138p-config.json
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
PRED=artifacts/claude-merge138p-20260923/predicted_moves138p.json
P260=artifacts/claude-openpanel260-20260922
A260=scripts/claude_loop260_agent.py
C260=artifacts/claude-openers260-20260922/loop260-config.json
PTAIL=artifacts/claude-corrtail258-20260922
PPAN=artifacts/claude-corrpanel252-20260922
A252C=scripts/claude_loop252c_agent.py
C252C=artifacts/claude-merge252c-20260922/loop252c-config.json
R252B=artifacts/claude-correct252b-20260922/run
R258=artifacts/claude-comment258-20260922/run
R259=artifacts/claude-boundary259-20260922/run
mkdir -p "$R" "$R/work" "$R/m7"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
  F=$(df -g / | tail -1 | awk '{print $4}')
  if [ "$F" -lt 3 ]; then echo "free disk ${F} GB < 3: STOP"; exit 5; fi
}
T0=$(date +%s)
# ---- panel seals first
( cd . && shasum -a 256 -c $P260/SEAL.sha256.txt ) > $R/m7/seal-260.txt 2>&1 || { cat $R/m7/seal-260.txt; echo "PANEL SEAL 260 FAILED"; exit 4; }
( cd . && shasum -a 256 -c $PTAIL/SEAL.sha256.txt ) > $R/m7/seal-tail.txt 2>&1 || { cat $R/m7/seal-tail.txt; echo "PANEL SEAL TAIL FAILED"; exit 4; }
( cd . && shasum -a 256 -c $PPAN/SEAL.sha256.txt ) > $R/m7/seal-panel.txt 2>&1 || { cat $R/m7/seal-panel.txt; echo "PANEL SEAL PANEL FAILED"; exit 4; }
# ---- openpanel260: fidelity of 260 arm, then 138m + 138p, same runner+scorer
waitload M7-openpanel260
PY scripts/claude_openers260_score.py schema $P260 > $R/m7/panel260-schema.txt 2>&1
SC=$?; cat $R/m7/panel260-schema.txt
[ $SC -eq 0 ] || { echo "schema check exit $SC: run VOID"; exit $SC; }
PY scripts/claude_openers260_run.py panel $A260 $C260 $R/work/m7-260 $P260/panel.jsonl $R/m7/panel-260.jsonl > $R/m7/panel-260.log 2>&1
PY scripts/claude_openers260_run.py panel $AM $CM $R/work/m7-m $P260/panel.jsonl $R/m7/panel-138m.jsonl > $R/m7/panel-138m.log 2>&1
PY scripts/claude_openers260_run.py panel $AP $CP $R/work/m7-p $P260/panel.jsonl $R/m7/panel-138p.jsonl > $R/m7/panel-138p.log 2>&1
# ---- corrtail258: fidelity of 252c arm, then 138p, same runner+scorer
waitload M7-corrtail258
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $PTAIL/panel.jsonl --work $R/work/m7-tail252c --out $R/m7/corrtail258-252c.jsonl > $R/m7/corrtail258-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $PTAIL/panel.jsonl --work $R/work/m7-tail138p --out $R/m7/corrtail258-138p.jsonl > $R/m7/corrtail258-138p.log 2>&1
# ---- corrpanel252: fidelity of 252c arm, then 138p, same runner+scorer
waitload M7-corrpanel252
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $PPAN/panel.jsonl --work $R/work/m7-panel252c --out $R/m7/corrpanel252-252c.jsonl > $R/m7/corrpanel252-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $PPAN/panel.jsonl --work $R/work/m7-panel138p --out $R/m7/corrpanel252-138p.jsonl > $R/m7/corrpanel252-138p.log 2>&1
# ---- score every arm with the SAME sealed runner+scorer that produced the
# registered rows (lesson from 138n: never compare rows across scorers)
SPY scripts/claude_openers260_score.py panel $P260 $R/m7/panel-260.jsonl \
  $R/m7/panel-138m.jsonl $R/m7/score-260.json > $R/m7/score-260.log 2>&1
SPY scripts/claude_openers260_score.py panel $P260 $R/m7/panel-138p.jsonl \
  $R/m7/panel-138m.jsonl $R/m7/score-138p260.json > $R/m7/score-138p260.log 2>&1
SPY scripts/claude_merge252c_score.py m1 $PTAIL $R/m7/corrtail258-252c.jsonl \
  $R258/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl \
  $R259/panel258-259.jsonl > $R/m7/score-tail252c.json 2>&1
SPY scripts/claude_merge252c_score.py m1 $PTAIL $R/m7/corrtail258-138p.jsonl \
  $R258/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl \
  $R259/panel258-259.jsonl > $R/m7/score-tail138p.json 2>&1
SPY scripts/claude_merge252c_score.py m4 $PPAN $R/m7/corrpanel252-252c.jsonl \
  $R2B/panel-252b.jsonl $R258/corrpanel252-258.jsonl \
  $R259/panel252-259.jsonl > $R/m7/score-panel252c.json 2>&1
SPY scripts/claude_merge252c_score.py m4 $PPAN $R/m7/corrpanel252-138p.jsonl \
  $R2B/panel-252b.jsonl $R258/corrpanel252-258.jsonl \
  $R259/panel252-259.jsonl > $R/m7/score-panel138p.json 2>&1
SPY scripts/claude_138p_score.py m7 $R/m7 $PRED $R/m7-check.json > $R/m7-check.txt 2>&1
echo "scorer exit $?" >> $R/m7-check.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/m7-check.txt
