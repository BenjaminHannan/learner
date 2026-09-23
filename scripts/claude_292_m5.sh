#!/bin/bash
# Merge 292 -- M5: fresh blind panel mixpanel292 (the PASS claim rests on
# it). Waits for artifacts/claude-mixpanel292-20260923/SEAL.sha256.txt on
# origin builder-outbox (git fetch every 2 min, up to 180 min), copies the
# folder unchanged, checks the seal, then runs M5 ONCE on 291, 266b, 268b,
# 293 and 292 and scores all five arms with the panel's sealed
# score_panel.py. All rows/logs stay in the tmpdir (outside the repo);
# only the ids-only tally is copied into the artifact dir. usage:
#   scripts/claude_292_m5.sh <tmpdir>
set -u
T=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
P292=artifacts/claude-mixpanel292-20260923
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
  if git cat-file -e origin/builder-outbox:$P292/SEAL.sha256.txt 2>/dev/null; then
    echo "$(date +%T) panel seal found after $TRIES tries" | tee -a "$T/uptime.log"
    break
  fi
  TRIES=$((TRIES + 1))
  echo "$(date +%T) panel not yet on builder-outbox ($TRIES/90)" | tee -a "$T/uptime.log"
  sleep 120
done
git cat-file -e origin/builder-outbox:$P292/SEAL.sha256.txt 2>/dev/null \
  || { echo "PANEL NEVER LANDED AFTER 180 MIN: M5 PENDING, REPORT"; exit 6; }
# ---- copy the folder unchanged (never check out, merge or push main)
rm -rf "$P292"
mkdir -p "$P292"
git archive origin/builder-outbox "$P292" | tar -x
ls "$P292" | tee -a "$T/uptime.log"
# ---- check the seal (repo-root paths, from the repo root)
( cd . && shasum -a 256 -c $P292/SEAL.sha256.txt ) > $T/seal-mix292.txt 2>&1 || { cat $T/seal-mix292.txt; echo "PANEL SEAL MIX292 FAILED: VOID"; exit 4; }
cat $T/seal-mix292.txt
cat $P292/README.md 2>/dev/null | head -n 60 | tee $T/panel-readme.txt
# ---- dispatch on the panel's own convention (logged; anything else VOID)
waitload M5-arms
if ls $P292/panel.jsonl >/dev/null 2>&1; then ITEMS=$P292/panel.jsonl; else echo "NO panel.jsonl: VOID"; exit 4; fi
FIELDS=$(SPY -c "import json;print(sorted(json.loads(open('$ITEMS').readline()).keys()))" 2>&1 | tail -n 1)
echo "panel item fields: $FIELDS" | tee -a "$T/uptime.log"
case "$FIELDS" in
  *question*)
    echo "convention: setup/question (+expect/gold); runner claude_292_m5run.py" | tee -a "$T/uptime.log"
    waitload M5-291
    PY scripts/claude_292_m5run.py $ITEMS scripts/claude_loop291_agent.py artifacts/claude-join291-20260923/loop291-config.json $T/mixpanel292-291.jsonl > $T/mixpanel292-291.log 2>&1
    waitload M5-266b
    PY scripts/claude_292_m5run.py $ITEMS scripts/claude_loop266b_agent.py artifacts/claude-chain266b-20260923/loop266b-config.json $T/mixpanel292-266b.jsonl > $T/mixpanel292-266b.log 2>&1
    waitload M5-268b
    PY scripts/claude_292_m5run.py $ITEMS scripts/claude_loop268b_agent.py artifacts/claude-nhop268b-20260923/loop268b-config.json $T/mixpanel292-268b.jsonl > $T/mixpanel292-268b.log 2>&1
    waitload M5-293
    PY scripts/claude_292_m5run.py $ITEMS scripts/claude_loop293_agent.py artifacts/claude-yesno293-20260923/loop293-config.json $T/mixpanel292-293.jsonl > $T/mixpanel292-293.log 2>&1
    waitload M5-292
    PY scripts/claude_292_m5run.py $ITEMS scripts/claude_loop292_agent.py artifacts/claude-merge292-20260923/loop292-config.json $T/mixpanel292-292.jsonl > $T/mixpanel292-292.log 2>&1
    ;;
  *)
    echo "UNKNOWN panel convention ($FIELDS): VOID, report"; exit 4;;
esac
# ---- score all five arms with the panel's SEALED scorer (schema first)
ls $P292/score_panel.py >/dev/null 2>&1 || { echo "NO sealed score_panel.py: VOID"; exit 4; }
for arm in 291 266b 268b 293 292; do
  SPY $P292/score_panel.py $ITEMS $T/mixpanel292-$arm.jsonl $T/score-mixpanel292-$arm.json > $T/score-mixpanel292-$arm.log 2>&1
  SC=$?; echo "score $arm exit $SC" | tee -a "$T/uptime.log"
  [ $SC -eq 0 ] || { echo "scorer exit $SC on $arm: VOID (never score by hand)"; exit $SC; }
done
# ---- tally (ids, families and counts only; raw rows stay in the tmpdir)
SPY scripts/claude_292_score.py m5 --dir $T --out $T/m5-check.json > $T/m5-check.txt 2>&1
echo "scorer exit $?" >> $T/m5-check.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $T/uptime.log
cat $T/m5-check.txt
