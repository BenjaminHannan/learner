#!/bin/bash
# Exp 258 registered runs, once each, in order M2 M3 M4 M5 M6 M7 (M1 is
# run separately after the blind panel's seal: claude_comment258_m1.sh).
# Run from the repo root. Outputs: artifacts/claude-comment258-20260922/run/
set -u
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
D=artifacts/claude-comment258-20260922
R=$D/run
B=artifacts/claude-correct252b-20260922
A=scripts/claude_loop258_agent.py
C=$D/loop258-config.json
AB=scripts/claude_loop252b_agent.py
CB=$B/loop252b-config.json
V=artifacts/claude-verify-20260922/138k
W=${TMPDIR:-/tmp}/claude258-work
SC=scripts/claude_comment258_score.py
mkdir -p $R $W
DEV252B_MOVES=b252-001,b252-002,b252-004,b252-005,b252-006,b252-007,b252-008,b252-010,b252-011,b252-013,b252-014,b252-016,b252-017,b252-018,b252-019,b252-020,b252-021,b252-023,b252-024,b252-026,b252-027,b252-029,b252-030,b252-031,b252-032,b252-033,b252-035,b252-036,b252-037
DEV258_MOVES=d258-001,d258-002,d258-004,d258-005,d258-006,d258-008,d258-009,d258-010,d258-011,d258-012,d258-013,d258-015,d258-016,d258-017,d258-018,d258-019,d258-020,d258-021,d258-022,d258-023,d258-024,d258-026,d258-027,d258-028,d258-029,d258-030,d258-031,d258-032,d258-033,d258-034,d258-035,d258-061,d258-062,d258-063,d258-065,d258-066,d258-075,d258-076,d258-077,d258-078,d258-079
gate() { uptime; df -g / | tail -1; }

echo "== M2 dev252b (both arms, same session) + dev258 reference"; gate
$PY scripts/claude_corr252_run.py --agent $AB --config $CB --cases $B/dev252b.jsonl --work $W/m2b --out $R/dev252b-252b.jsonl > $R/dev252b-252b.log 2>&1
$PY scripts/claude_corr252_run.py --agent $A --config $C --cases $B/dev252b.jsonl --work $W/m2m --out $R/dev252b-258.jsonl > $R/dev252b-258.log 2>&1
python3 scripts/claude_corr252b_score.py dev $B/dev252b.jsonl $R/dev252b-258.jsonl $R/dev252b-252b.jsonl > $R/m2-check.txt
python3 $SC moves $R/dev252b-252b.jsonl $R/dev252b-258.jsonl $DEV252B_MOVES > $R/m2-moves.txt
$PY scripts/claude_corr252_run.py --agent $AB --config $CB --cases $D/dev258.jsonl --work $W/d8b --out $R/dev258-252b.jsonl > $R/dev258-252b.log 2>&1
$PY scripts/claude_corr252_run.py --agent $A --config $C --cases $D/dev258.jsonl --work $W/d8m --out $R/dev258-258.jsonl > $R/dev258-258.log 2>&1
python3 $SC dev $D/dev258.jsonl $R/dev258-258.jsonl $R/dev258-252b.jsonl > $R/dev258-score.txt
python3 $SC moves $R/dev258-252b.jsonl $R/dev258-258.jsonl $DEV258_MOVES > $R/dev258-moves.txt

echo "== M3 corrpanel252 (TEST-ONLY), mine vs 252b registered rows"; gate
$PY scripts/claude_corr252_run.py --agent $A --config $C --cases artifacts/claude-corrpanel252-20260922/panel.jsonl --work $W/m3 --out $R/corrpanel252-258.jsonl > $R/corrpanel252-258.log 2>&1
python3 $SC m3 artifacts/claude-corrpanel252-20260922 $B/run/panel-252b.jsonl $R/corrpanel252-258.jsonl c252-022 > $R/m3-check.txt

echo "== M4 suites"; gate
$PY scripts/fable_suitediff218.py --agent $A --config $C --base-dir artifacts/claude-correct252-20260922/run/base138k-rows --out $R/sd-258 --only rt136,rt143,sessions152,bench > $R/sd-258.log 2>&1
python3 $SC suites $B/run/sd-252b $R/sd-258 > $R/m4-check.txt

echo "== M5 sleep smoke"; gate
$PY scripts/fable_sleepsmoke206.py --agent $A --config $C --root $W/smoke --report $R/smoke-258.json --label 258 --idle-seconds 5.0 > $R/smoke-258.log 2>&1
python3 $SC smoke $B/run/smoke-252b.json $R/smoke-258.json > $R/m5-check.txt

echo "== M6 restart dialogs"; gate
$PY scripts/claude_merge138k_probe.py $A $C $W/m6a $V/v-dialogs.json $R/m6-258-v-dialogs.json > $R/m6-258-v-dialogs.log 2>&1
$PY scripts/claude_merge138k_probe.py $A $C $W/m6b $V/v-supp.json $R/m6-258-v-supp.json > $R/m6-258-v-supp.log 2>&1
python3 scripts/claude_corr252_m6check.py m6 $B/run/m6-252b-v-dialogs.json $R/m6-258-v-dialogs.json $B/run/m6-252b-v-supp.json $R/m6-258-v-supp.json > $R/m6-check.txt

echo "== M7 latency (252b, 258 alternating, 3 runs each, 2 reps)"; gate
for i in 1 2 3; do
  $PY scripts/claude_merge138k_latency.py $AB $CB $W/lb$i 2 $R/lat-252b-$i.json $V/v-dialogs.json $V/v-supp.json >> $R/lat.log 2>&1
  $PY scripts/claude_merge138k_latency.py $A $C $W/lm$i 2 $R/lat-258-$i.json $V/v-dialogs.json $V/v-supp.json >> $R/lat.log 2>&1
done
python3 scripts/claude_corr252_m6check.py m5 $R/lat-252b-1.json $R/lat-252b-2.json $R/lat-252b-3.json -- $R/lat-258-1.json $R/lat-258-2.json $R/lat-258-3.json > $R/m7-check.txt
echo "== done M2-M7"; gate
