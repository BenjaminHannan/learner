#!/bin/bash
# Merge 291 -- M8: fresh blind panel corrpanel291 (the PASS claim rests on
# it). Waits for artifacts/claude-corrpanel291-20260923/SEAL.sha256.txt on
# origin builder-outbox (git fetch every 2 min, up to 180 min), copies the
# folder unchanged, checks the seal, then runs M8 ONCE on 138nb, 138p and
# 291 and scores all three arms with the panel's sealed score_panel.py.
# All rows/logs stay in the tmpdir (outside the repo); only the ids-only
# tally is copied into the artifact dir. usage:
#   scripts/claude_291_m8.sh <tmpdir>
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
P291=artifacts/claude-corrpanel291-20260923
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
# ---- wait for the sealed panel (fetch every 2 min, up to 180 min)
TRIES=0
while [ $TRIES -lt 90 ]; do
  git fetch -q origin builder-outbox 2>&1 | head -n 3
  if git cat-file -e origin/builder-outbox:$P291/SEAL.sha256.txt 2>/dev/null; then
    echo "$(date +%T) panel seal found after $TRIES tries" | tee -a "$T/uptime.log"
    break
  fi
  TRIES=$((TRIES + 1))
  echo "$(date +%T) panel not yet on builder-outbox ($TRIES/90)" | tee -a "$T/uptime.log"
  sleep 120
done
git cat-file -e origin/builder-outbox:$P291/SEAL.sha256.txt 2>/dev/null \
  || { echo "PANEL NEVER LANDED AFTER 180 MIN: M8 PENDING, REPORT"; exit 6; }
# ---- copy the folder unchanged (never check out, merge or push main)
rm -rf "$P291"
mkdir -p "$P291"
git archive origin/builder-outbox "$P291" | tar -x
ls "$P291" | tee -a "$T/uptime.log"
# ---- check the seal (repo-root paths, from the repo root)
( cd . && shasum -a 256 -c $P291/SEAL.sha256.txt ) > $T/seal-corr291.txt 2>&1 || { cat $T/seal-corr291.txt; echo "PANEL SEAL CORR291 FAILED: VOID"; exit 4; }
cat $T/seal-corr291.txt
cat $P291/README.md 2>/dev/null | head -n 60 | tee $T/panel-readme.txt
# ---- dispatch on the panel's own convention (logged; anything else VOID)
waitload M8-arms
if ls $P291/panel.jsonl >/dev/null 2>&1; then ITEMS=$P291/panel.jsonl; else echo "NO panel.jsonl: VOID"; exit 4; fi
FIELDS=$(SPY -c "import json;print(sorted(json.loads(open('$ITEMS').readline()).keys()))" 2>&1 | tail -n 1)
echo "panel item fields: $FIELDS" | tee -a "$T/uptime.log"
case "$FIELDS" in
  *followup*)
    echo "convention: corrtail-style (setup/turn/followup); runner claude_corr252_run.py" | tee -a "$T/uptime.log"
    for arm in 138nb 138p 291; do
      case $arm in
        138nb) AG=$ANB; CF=$CNB;;
        138p) AG=$AP; CF=$CP;;
        291) AG=$A291; CF=$C291;;
      esac
      PY scripts/claude_corr252_run.py --agent $AG --config $CF --cases $ITEMS --work $T/work/m8-$arm --out $T/corrpanel291-$arm.jsonl > $T/corrpanel291-$arm.log 2>&1
    done
    ;;
  *question*)
    echo "convention: invpanel-style (setup/question); runner claude_291_m7run.py" | tee -a "$T/uptime.log"
    for arm in 138nb 138p 291; do
      PY scripts/claude_291_m7run.py inv --arm $arm --items $ITEMS --out $T/corrpanel291-$arm.jsonl --work $T/work/m8-$arm > $T/corrpanel291-$arm.log 2>&1
    done
    ;;
  *)
    echo "UNKNOWN panel convention ($FIELDS): VOID, report"; exit 4;;
esac
# ---- score all three arms with the panel's SEALED scorer (schema first)
ls $P291/score_panel.py >/dev/null 2>&1 || { echo "NO sealed score_panel.py: VOID"; exit 4; }
for arm in 138nb 138p 291; do
  SPY $P291/score_panel.py $ITEMS $T/corrpanel291-$arm.jsonl $T/score-corrpanel291-$arm.json > $T/score-corrpanel291-$arm.log 2>&1
  SC=$?; echo "score $arm exit $SC" | tee -a "$T/uptime.log"
  [ $SC -eq 0 ] || { echo "scorer exit $SC on $arm: VOID (never score by hand)"; exit $SC; }
done
# ---- tally (ids, families and counts only; raw rows stay in the tmpdir)
SPY scripts/claude_291_score.py m8 $T $PRED $T/m8-check.json > $T/m8-check.txt 2>&1
echo "scorer exit $?" >> $T/m8-check.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $T/uptime.log
cat $T/m8-check.txt
