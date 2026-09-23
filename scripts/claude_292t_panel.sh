#!/bin/bash
# Exp 292t -- M1: the blind joinpanel292t once on all five arms
# (292, 292+280b, 292+281, 292+282b, 292t); M3: smalltalkpanel234 once on
# 292 and 292t.
# usage: scripts/claude_292t_panel.sh <run_dir>
# Strict schema (columns dialog_id, turn_index, user_text, category, gold;
# categories ability/called/teach/smalltalk/mixed/control; `user` also
# accepted for the text): scripts/claude_join292t_run.py refuses to run on
# any schema violation or empty turn text, and
# scripts/claude_join292t_score.py gates SCHEMA-MISMATCH (exit 3 = VOID).
# No code change to any agent: the sealed agents/configs run read-only.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-joinpanel292t-20260923
S234=artifacts/claude-smalltalkpanel234-20260922
A292=scripts/claude_loop292_agent.py
C292=artifacts/claude-merge292-20260923/loop292-config.json
A280B=scripts/claude_292t_280b_agent.py
C280B=artifacts/claude-join292t-20260923/loop292t-config.json
A281=scripts/claude_292t_281_agent.py
C281=artifacts/claude-join292t-20260923/loop292t-config.json
A282B=scripts/claude_292t_282b_agent.py
C282B=artifacts/claude-join292t-20260923/loop292t-config.json
A292T=scripts/claude_loop292t_agent.py
C292T=artifacts/claude-join292t-20260923/loop292t-config.json
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl $P/panel.json 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_join292t_run.py panel $A292 $C292 $R/work/p292 \
  $PANEL $R/panel-292.json $R/probes-292.json > $R/panel-292.log 2>&1
PY scripts/claude_join292t_run.py panel $A280B $C280B $R/work/p280b \
  $PANEL $R/panel-280b.json $R/probes-280b.json > $R/panel-280b.log 2>&1
PY scripts/claude_join292t_run.py panel $A281 $C281 $R/work/p281 \
  $PANEL $R/panel-281.json $R/probes-281.json > $R/panel-281.log 2>&1
PY scripts/claude_join292t_run.py panel $A282B $C282B $R/work/p282b \
  $PANEL $R/panel-282b.json $R/probes-282b.json > $R/panel-282b.log 2>&1
PY scripts/claude_join292t_run.py panel $A292T $C292T $R/work/p292t \
  $PANEL $R/panel-292t.json $R/probes-292t.json > $R/panel-292t.log 2>&1
PY scripts/claude_join292t_score.py panel $PANEL $R/panel-292.json \
  $R/panel-280b.json $R/panel-281.json $R/panel-282b.json $R/panel-292t.json \
  $R/probes-292.json $R/probes-280b.json $R/probes-281.json \
  $R/probes-282b.json $R/probes-292t.json $R/panel-score292t.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
PY scripts/claude_join292t_run.py st234 $A292 $C292 $R/work/s292 \
  $S234/panel.jsonl $R/st234-292.json $R/st234-probes-292.json > $R/st234-292.log 2>&1
PY scripts/claude_join292t_run.py st234 $A292T $C292T $R/work/s292t \
  $S234/panel.jsonl $R/st234-292t.json $R/st234-probes-292t.json > $R/st234-292t.log 2>&1
PY scripts/claude_join292t_score.py st234 $S234/panel.jsonl $R/st234-292.json \
  $R/st234-292t.json $R/st234-probes-292.json $R/st234-probes-292t.json $R/st234-score292t.json >> $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
