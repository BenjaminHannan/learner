#!/bin/bash
# Exp 280m -- M1: the blind joinpanel280m once on all five arms
# (260, 280b, 281, 282b, 280m); M3: smalltalkpanel234 once on 260 and 280m.
# usage: scripts/claude_280m_panel.sh <run_dir>
# Strict schema (columns dialog_id, turn_index, user_text, category, gold;
# categories ability/called/teach/smalltalk/mixed/control; `user` also
# accepted for the text): scripts/claude_join280m_run.py refuses to run on
# any schema violation or empty turn text, and
# scripts/claude_join280m_score.py gates SCHEMA-MISMATCH (exit 3 = VOID).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-joinpanel280m-20260923
S234=artifacts/claude-smalltalkpanel234-20260922
A260=scripts/claude_loop260_agent.py
C260=artifacts/claude-openers260-20260922/loop260-config.json
A280B=scripts/claude_loop280b_agent.py
C280B=artifacts/claude-capab280b-20260923/loop280b-config.json
A281=scripts/claude_loop281_agent.py
C281=artifacts/claude-called281-20260923/loop281-config.json
A282B=scripts/claude_loop282b_agent.py
C282B=artifacts/claude-small282b-20260923/loop282b-config.json
A280M=scripts/claude_loop280m_agent.py
C280M=artifacts/claude-join280m-20260923/loop280m-config.json
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl $P/panel.json 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_join280m_run.py panel $A260 $C260 $R/work/p260 \
  $PANEL $R/panel-260.json $R/probes-260.json > $R/panel-260.log 2>&1
PY scripts/claude_join280m_run.py panel $A280B $C280B $R/work/p280b \
  $PANEL $R/panel-280b.json $R/probes-280b.json > $R/panel-280b.log 2>&1
PY scripts/claude_join280m_run.py panel $A281 $C281 $R/work/p281 \
  $PANEL $R/panel-281.json $R/probes-281.json > $R/panel-281.log 2>&1
PY scripts/claude_join280m_run.py panel $A282B $C282B $R/work/p282b \
  $PANEL $R/panel-282b.json $R/probes-282b.json > $R/panel-282b.log 2>&1
PY scripts/claude_join280m_run.py panel $A280M $C280M $R/work/p280m \
  $PANEL $R/panel-280m.json $R/probes-280m.json > $R/panel-280m.log 2>&1
PY scripts/claude_join280m_score.py panel $PANEL $R/panel-260.json \
  $R/panel-280b.json $R/panel-281.json $R/panel-282b.json $R/panel-280m.json \
  $R/probes-260.json $R/probes-280b.json $R/probes-281.json \
  $R/probes-282b.json $R/probes-280m.json $R/panel-score280m.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
PY scripts/claude_join280m_run.py st234 $A260 $C260 $R/work/s260 \
  $S234/panel.jsonl $R/st234-260.json $R/st234-probes-260.json > $R/st234-260.log 2>&1
PY scripts/claude_join280m_run.py st234 $A280M $C280M $R/work/s280m \
  $S234/panel.jsonl $R/st234-280m.json $R/st234-probes-280m.json > $R/st234-280m.log 2>&1
PY scripts/claude_join280m_score.py st234 $S234/panel.jsonl $R/st234-260.json \
  $R/st234-280m.json $R/st234-probes-260.json $R/st234-probes-280m.json $R/st234-score280m.json >> $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
