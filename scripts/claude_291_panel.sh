#!/bin/bash
# Merge 291 -- M7: regression panels (seen panels only; each arm runs ONCE,
# after the seal). For each panel: FIRST re-run the registered piece's own
# arm with exactly the runner and scorer that produced its registered rows
# and show it reproduces those rows (fidelity count). Then score 291 with
# that SAME runner and scorer. If fidelity is not 100%, the panel is VOID
# (report why; never score by hand).
# Panels: openpanel260 (arm 260), corrtail258 + corrpanel252 (arm 252c),
# invpanel138nb (arm 138n vs writer base), tablepanel221 (arms 138n/138nb
# vs 138nb's registered M6 relationship).
# All rows/logs stay in the tmpdir (outside the repo); only the ids-only
# tally is copied into the artifact dir. usage:
#   scripts/claude_291_panel.sh <tmpdir>
set -u
T=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
ANB=scripts/claude_loop138nb_agent.py
CNB=artifacts/claude-merge138nb-20260923/loop138nb-config.json
AP=scripts/claude_loop138p_agent.py
CP=artifacts/claude-merge138p-20260923/loop138p-config.json
A291=scripts/claude_loop291_agent.py
C291=artifacts/claude-join291-20260923/loop291-config.json
PRED=artifacts/claude-join291-20260923/predicted_moves291.json
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
PINV=artifacts/claude-invpanel138nb-20260923
PT221=artifacts/claude-tablepanel221-20260922/panel.jsonl
mkdir -p "$T" "$T/work"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$T/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
  F=$(df -g / | tail -1 | awk '{print $4}')
  if [ "$F" -lt 3 ]; then echo "free disk ${F} GB < 3: STOP"; exit 5; fi
}
T0=$(date +%s)
# ---- panel seals first
( cd . && shasum -a 256 -c $P260/SEAL.sha256.txt ) > $T/seal-260.txt 2>&1 || { cat $T/seal-260.txt; echo "PANEL SEAL 260 FAILED"; exit 4; }
( cd . && shasum -a 256 -c $PTAIL/SEAL.sha256.txt ) > $T/seal-tail.txt 2>&1 || { cat $T/seal-tail.txt; echo "PANEL SEAL TAIL FAILED"; exit 4; }
( cd . && shasum -a 256 -c $PPAN/SEAL.sha256.txt ) > $T/seal-panel.txt 2>&1 || { cat $T/seal-panel.txt; echo "PANEL SEAL PANEL FAILED"; exit 4; }
( cd . && shasum -a 256 -c $PINV/SEAL.sha256.txt ) > $T/seal-inv.txt 2>&1 || { cat $T/seal-inv.txt; echo "PANEL SEAL INV FAILED"; exit 4; }
# ---- openpanel260: fidelity of 260 arm, then 138nb + 138p + 291
waitload M7-openpanel260
PY scripts/claude_openers260_score.py schema $P260 > $T/panel260-schema.txt 2>&1
SC=$?; cat $T/panel260-schema.txt
[ $SC -eq 0 ] || { echo "schema check exit $SC: run VOID"; exit $SC; }
PY scripts/claude_openers260_run.py panel $A260 $C260 $T/work/m7-260 $P260/panel.jsonl $T/open-260.jsonl > $T/open-260.log 2>&1
PY scripts/claude_openers260_run.py panel $ANB $CNB $T/work/m7-nb $P260/panel.jsonl $T/open-138nb.jsonl > $T/open-138nb.log 2>&1
PY scripts/claude_openers260_run.py panel $AP $CP $T/work/m7-138p $P260/panel.jsonl $T/open-138p.jsonl > $T/open-138p.log 2>&1
PY scripts/claude_openers260_run.py panel $A291 $C291 $T/work/m7-291 $P260/panel.jsonl $T/open-291.jsonl > $T/open-291.log 2>&1
# ---- corrtail258: fidelity of 252c arm, then 138nb + 138p + 291
waitload M7-corrtail258
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $PTAIL/panel.jsonl --work $T/work/m7-tail252c --out $T/corrtail258-252c.jsonl > $T/corrtail258-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $ANB --config $CNB --cases $PTAIL/panel.jsonl --work $T/work/m7-tailnb --out $T/corrtail258-138nb.jsonl > $T/corrtail258-138nb.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $PTAIL/panel.jsonl --work $T/work/m7-tail138p --out $T/corrtail258-138p.jsonl > $T/corrtail258-138p.log 2>&1
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $PTAIL/panel.jsonl --work $T/work/m7-tail291 --out $T/corrtail258-291.jsonl > $T/corrtail258-291.log 2>&1
# ---- corrpanel252: fidelity of 252c arm, then 138nb + 138p + 291
waitload M7-corrpanel252
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $PPAN/panel.jsonl --work $T/work/m7-panel252c --out $T/corrpanel252-252c.jsonl > $T/corrpanel252-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $ANB --config $CNB --cases $PPAN/panel.jsonl --work $T/work/m7-panelnb --out $T/corrpanel252-138nb.jsonl > $T/corrpanel252-138nb.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $PPAN/panel.jsonl --work $T/work/m7-panel138p --out $T/corrpanel252-138p.jsonl > $T/corrpanel252-138p.log 2>&1
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $PPAN/panel.jsonl --work $T/work/m7-panel291 --out $T/corrpanel252-291.jsonl > $T/corrpanel252-291.log 2>&1
# ---- score every arm with the SAME sealed scorer that produced the
# registered rows (lesson from 138n: never compare rows across scorers)
SPY scripts/claude_openers260_score.py panel $P260 $T/open-260.jsonl \
  $T/open-138nb.jsonl $T/score-260.json > $T/score-260.log 2>&1
SPY scripts/claude_openers260_score.py panel $P260 $T/open-291.jsonl \
  $T/open-138nb.jsonl $T/score-291-260.json > $T/score-291-260.log 2>&1
SPY scripts/claude_openers260_score.py panel $P260 $T/open-138p.jsonl \
  $T/open-138nb.jsonl $T/score-138p-260.json > $T/score-138p-260.log 2>&1
SPY scripts/claude_merge252c_score.py m1 $PTAIL $T/corrtail258-252c.jsonl \
  $R252B/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl \
  $R259/panel258-259.jsonl > $T/score-tail252c.json 2>&1
SPY scripts/claude_merge252c_score.py m1 $PTAIL $T/corrtail258-291.jsonl \
  $R252B/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl \
  $R259/panel258-259.jsonl > $T/score-tail291.json 2>&1
SPY scripts/claude_merge252c_score.py m1 $PTAIL $T/corrtail258-138p.jsonl \
  $R252B/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl \
  $R259/panel258-259.jsonl > $T/score-tail138p.json 2>&1
SPY scripts/claude_merge252c_score.py m4 $PPAN $T/corrpanel252-252c.jsonl \
  $R252B/panel-252b.jsonl $R258/corrpanel252-258.jsonl \
  $R259/panel252-259.jsonl > $T/score-panel252c.json 2>&1
SPY scripts/claude_merge252c_score.py m4 $PPAN $T/corrpanel252-291.jsonl \
  $R252B/panel-252b.jsonl $R258/corrpanel252-258.jsonl \
  $R259/panel252-259.jsonl > $T/score-panel291.json 2>&1
SPY scripts/claude_merge252c_score.py m4 $PPAN $T/corrpanel252-138p.jsonl \
  $R252B/panel-252b.jsonl $R258/corrpanel252-258.jsonl \
  $R259/panel252-259.jsonl > $T/score-panel138p.json 2>&1
# ---- invpanel138nb: 138n arm (fidelity vs writer base), then nb/p/291
waitload M7-invpanel
cp $PINV/base138n.jsonl $T/inv-base.jsonl
PY scripts/claude_138nb_m1.py run --arm n --items $PINV/panel.jsonl --out $T/inv-138n.jsonl --work $T/work/inv-n > $T/inv-138n.log 2>&1
PY scripts/claude_138nb_m1.py run --arm nb --items $PINV/panel.jsonl --out $T/inv-138nb.jsonl --work $T/work/inv-nb > $T/inv-138nb.log 2>&1
PY scripts/claude_291_m7run.py inv --arm p --items $PINV/panel.jsonl --out $T/inv-138p.jsonl --work $T/work/inv-p > $T/inv-138p.log 2>&1
PY scripts/claude_291_m7run.py inv --arm 291 --items $PINV/panel.jsonl --out $T/inv-291.jsonl --work $T/work/inv-291 > $T/inv-291.log 2>&1
for arm in 138n 138nb 138p 291; do
  SPY $PINV/score_panel.py $PINV/panel.jsonl $T/inv-$arm.jsonl $T/score-inv-$arm.json > $T/score-inv-$arm.log 2>&1
done
# ---- tablepanel221: scorer sha check, then n/nb (fidelity pair) + p + 291
waitload M7-tablepanel221
PY scripts/claude_138nb_m6.py check > $T/panelmap-sha.txt 2>&1
SC=$?; cat $T/panelmap-sha.txt
[ $SC -eq 0 ] || { echo "panelmap sha exit $SC: run VOID"; exit $SC; }
PY scripts/claude_138n_m7.py run221 --arm n --items $PT221 --out $T/t221-n --work $T/work/t221-n > $T/t221-n.log 2>&1
PY scripts/claude_138nb_m6.py run --arm nb --items $PT221 --out $T/t221-nb --work $T/work/t221-nb > $T/t221-nb.log 2>&1
PY scripts/claude_291_m7run.py t221 --arm p --items $PT221 --out $T/t221-138p --work $T/work/t221-p > $T/t221-138p.log 2>&1
PY scripts/claude_291_m7run.py t221 --arm 291 --items $PT221 --out $T/t221-291 --work $T/work/t221-291 > $T/t221-291.log 2>&1
# ---- tally (ids, families and counts only; raw rows stay in the tmpdir)
SPY scripts/claude_291_score.py m7 $T $PRED $T/m7-check.json > $T/m7-check.txt 2>&1
echo "scorer exit $?" >> $T/m7-check.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $T/uptime.log
cat $T/m7-check.txt
