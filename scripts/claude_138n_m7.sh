#!/bin/bash
# Merge 138n -- M7 blind panels, TEST-ONLY, run ONCE after the seal.
# Each panel's SEAL is checked first; each panel is run through its own
# sealed runner and scored by its own sealed scorer, on 138n and 138m.
# All runner/scorer stdout goes to log files that are NOT printed (they can
# hold item text); only claude_138n_m7.py compare prints counts and ids.
# usage: scripts/claude_138n_m7.sh <m7_dir OUTSIDE the repo>
# (runner rows/logs hold panel item text, so they stay out of the repo;
#  only the counts-and-ids compare file is copied into the artifact dir)
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AGM=$PWD/scripts/claude_loop138m_agent.py
CFM=$PWD/artifacts/claude-merge138m-20260922/loop138m-config.json
AGN=$PWD/scripts/claude_loop138n_agent.py
CFN=$PWD/artifacts/claude-merge138n-20260922/loop138n-config.json
A=artifacts
W=$R/work
mkdir -p "$R" "$W"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" >> "$R/uptime.log"
    df -g / | tail -1 >> "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
seal_ok() {  # $1 = panel dir; prints OK / SEAL-FAIL only
  (cd "$1" && shasum -a 256 -c SEAL.sha256.txt >/dev/null 2>&1) && echo OK \
    || (cd . && shasum -a 256 -c "$1/SEAL.sha256.txt" >/dev/null 2>&1 && echo OK) \
    || echo SEAL-FAIL
}
agent() { if [ $1 = n ]; then echo "$AGN $CFN"; else echo "$AGM $CFM"; fi; }

# ---- tablepanel221 (221's runner, arm "221" built as 138n / 138m)
P=tablepanel221; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  st=OK
  for a in n m; do
    waitload $P-$a
    PY scripts/claude_138n_m7.py run221 --arm $a --items $D/panel.jsonl \
      --out $R/$P/out-$a --work $W/$P-$a > $R/$P/log-$a.txt 2>&1 || st="ERR-$a"
  done
  echo $st > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

# ---- tablepanel221b (221c's runner, arms n and m)
P=tablepanel221b; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  waitload $P
  PY scripts/claude_qnorm221c_run.py --items $D/panel.jsonl --out $R/$P/out \
    --work $W/$P --arm n=$AGN,$CFN --arm m=$AGM,$CFM > $R/$P/log.txt 2>&1 \
    && echo OK > $R/$P/status.txt || echo ERR > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

# ---- teachpanel229
P=teachpanel229; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  st=OK
  for a in n m; do
    waitload $P-$a
    set -- $(agent $a)
    PY scripts/claude_teach229_run.py run --agent $1 --config $2 --cases $D/panel.jsonl \
      --work $W/$P-$a --out $R/$P/rows-$a.jsonl > $R/$P/log-$a.txt 2>&1 || st="ERR-run-$a"
    PY scripts/claude_teach229_run.py score --cases $D/panel.jsonl \
      --base $A/claude-tableteach229-20260922/runs/panel-138i.jsonl \
      --new $R/$P/rows-$a.jsonl --out $R/$P/score-$a.json > $R/$P/score-log-$a.txt 2>&1
    rc=$?; [ $rc = 3 ] && st="VOID-SCHEMA-$a"
    [ -s $R/$P/score-$a.json ] || { [ $st = OK ] && st="ERR-score-$a"; }
  done
  echo $st > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

# ---- namepanel232c
P=namepanel232c; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  st=OK
  for a in n m; do
    waitload $P-$a
    set -- $(agent $a)
    PY scripts/claude_fullname232_run.py --agent $1 --config $2 --cases $D/panel.jsonl \
      --work $W/$P-$a --out $R/$P/rows-$a.jsonl > $R/$P/log-$a.txt 2>&1 || st="ERR-run-$a"
    PY scripts/claude_fullname232c_score.py --cases $D/panel.jsonl \
      --base $A/claude-fullname232c-20260922/registered/panel-138i-A.jsonl \
      --new $R/$P/rows-$a.jsonl --base-panel $D/base138i.jsonl \
      --expect-counts multi=36,one=36,trap=8,stated_extra=4 \
      --out $R/$P/score-$a.json > $R/$P/score-log-$a.txt 2>&1
    rc=$?; [ $rc = 3 ] && st="VOID-SCHEMA-$a"
    [ -s $R/$P/score-$a.json ] || { [ $st = OK ] && st="ERR-score-$a"; }
  done
  echo $st > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

# ---- firstnamepanel236
P=firstnamepanel236; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  st=OK
  for a in n m; do
    waitload $P-$a
    set -- $(agent $a)
    PY scripts/claude_fullname232_run.py --agent $1 --config $2 --cases $D/panel.jsonl \
      --work $W/$P-$a --out $R/$P/rows-$a.jsonl > $R/$P/log-$a.txt 2>&1 || st="ERR-run-$a"
    PY scripts/claude_firstname236_score.py $D/panel.jsonl $R/$P/rows-$a.jsonl \
      $A/claude-firstname236-20260922/panel-rows221.jsonl $R/$P/score-$a.json \
      > $R/$P/score-log-$a.txt 2>&1
    rc=$?; [ $rc = 3 ] && st="VOID-SCHEMA-$a"
    [ -s $R/$P/score-$a.json ] || { [ $st = OK ] && st="ERR-score-$a"; }
  done
  echo $st > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

# ---- aliaspanel237
P=aliaspanel237; D=$A/claude-$P-20260922; mkdir -p $R/$P
S=$(seal_ok $D); echo "$S" > $R/$P/seal.txt
if [ "$S" = OK ]; then
  st=OK
  for a in n m; do
    waitload $P-$a
    set -- $(agent $a)
    PY scripts/claude_table237_run.py $1 $2 $D/panel.jsonl $W/$P-$a \
      $R/$P/rows-$a.jsonl > $R/$P/log-$a.txt 2>&1 || st="ERR-run-$a"
    PY scripts/claude_table237_score.py $R/$P/rows-$a.jsonl $D/base221.jsonl \
      $A/claude-table237-20260922/m1panel/fieldmap.json $R/$P/score-$a.json \
      > $R/$P/score-log-$a.txt 2>&1
    rc=$?; [ $rc = 3 ] && st="VOID-SCHEMA-$a"
    [ -s $R/$P/score-$a.json ] || { [ $st = OK ] && st="ERR-score-$a"; }
  done
  echo $st > $R/$P/status.txt
else echo SEAL-FAIL > $R/$P/status.txt; fi

for p in tablepanel221 tablepanel221b teachpanel229 namepanel232c firstnamepanel236 aliaspanel237; do
  echo "$p seal=$(cat $R/$p/seal.txt) status=$(cat $R/$p/status.txt)"
done
python3 scripts/claude_138n_m7.py compare --dir $R --out $R/m7-compare.json
mkdir -p artifacts/claude-merge138n-20260922/m7
cp $R/m7-compare.json artifacts/claude-merge138n-20260922/m7/m7-compare.json
for p in tablepanel221 tablepanel221b teachpanel229 namepanel232c firstnamepanel236 aliaspanel237; do
  echo "$p seal=$(cat $R/$p/seal.txt) status=$(cat $R/$p/status.txt)"
done > artifacts/claude-merge138n-20260922/m7/m7-status.txt
