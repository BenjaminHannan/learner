#!/bin/bash
# CPU test of the real text of the i4_b3g2_pair stage cut out of the generated box script: stage_test.sh SCRIPT CASE
# The functions (say, stage, sha, kill_cur, runp, prof_left, prof_pair_helpers, pair_alive, pair_run, prof_b3g2_pair) and the PROF_PAIR_/B3G2_ variable lines are taken from SCRIPT as they are.
# Replaced: fetch_sha (copies the real custom_io of 74d6e92c75 from a local export instead of cloning), and the job itself (fake_job.sh stands in for `python -m custom_io.g8a.job`, after checking the command line it was given).
SCRIPT=${1:?}; CASE=${2:-happy}
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/pair
T=$P/run_$CASE
rm -rf $T; mkdir -p $T
export J=$T/J W=$T/J/work
mkdir -p $J/state $J/out $W/data $W/g8a
RES=$W/results/8aPTC3S-pc; PRAW=$J/profraw; SB3=$J/src-b3g2; mkdir -p $PRAW $RES
cutfn() {   # NAME : the function's text from SCRIPT
  awk -v n="$1" '
    $0 ~ "^" n "\\(\\) \\{" { on = 1; multi = ($0 ~ /\{[[:space:]]*(#.*)?$/); print; if (!multi) { exit } ; next }
    on { print; if ($0 == "}") exit }' $SCRIPT
}
for f in say stage sha kill_cur runp prof_left prof_pair_helpers pair_alive pair_run pair_derive prof_b3g2_pair; do cutfn $f; done > $T/funcs.sh
grep -E '^(PROF_PAIR_[A-Z0-9_]+=|B3G2_SHA=|B3G2_Q_SHA=)' $SCRIPT | sed 's/ \{1,\}#.*$//' > $T/vars.sh
{ cat $T/vars.sh; } >/dev/null
echo "cut: $(grep -c . $T/funcs.sh) lines of functions, vars: $(cat $T/vars.sh | tr '\n' ' ' | cut -c1-300)"
bash -n $T/funcs.sh || exit 1
export TOTAL_FUNCS=$T/funcs.sh
cat > $T/drv.sh <<'DRV'
set -u
. $TVARS
PROFILE=1; PROF_PLAN=b3ab; MAXH=${MAXH:-4.5}; PROF_MAXMIN=${PROF_MAXMIN:-190}; PROF_MIN_LEFT=${PROF_MIN_LEFT:-240}
PROF_DRY_FAIL=${PROF_DRY_FAIL:-}; PROF_DRY_HANG=${PROF_DRY_HANG:-}; PTC_DRY_EXTRA=${PTC_DRY_EXTRA:-[]}
T0=$(date +%s); PT0=$T0; PFAIL=; PSKIP=
. $TFUNCS
fetch_sha() {   # test double: the real custom_io of the commit, exported locally (data_b1 and results left out)
  [ "$2" = "$B3G2_SHA" ] || { echo "fetch_sha: unexpected sha $2"; return 1; }
  [ "${NOFETCH:-0}" = 1 ] && return 1
  rm -rf $1; mkdir -p $1; cp -r $EXPORT/custom_io $1/
  [ -n "${TAMPER:-}" ] && echo "# tampered" >> $1/custom_io/$TAMPER
  return 0
}
# the job: runp is the real one; only the command it is asked to run is swapped when it is one of the two job scripts
real_runp=$(declare -f runp | sed '1s/runp/real_runp/')
eval "$real_runp"
runp() {
  local a=() x
  for x in "$@"; do case $x in */cmd.i4_*.sh) a+=("$FAKEJOB" "$x");; *) a+=("$x");; esac; done
  real_runp "${a[@]}"
}
prof_b3g2_pair
echo "PFAIL=[$PFAIL] PSKIP=[$PSKIP]"
echo "--- prof_steps.txt"; cat $J/state/prof_steps.txt 2>/dev/null
echo "--- profraw"; ls -la $PRAW | sed 1d | awk '{print $5, $9}'
DRV
cat > $T/fake_job.sh <<'FAKE'
#!/bin/bash
# stands in for `python -m custom_io.g8a.job ...`: checks the command line the box built, then logs train events (step, loss, elapsed) forever like the real job would
src=$1
cmd=$(tail -n 1 $src)
case "$cmd" in exec\ *-m\ custom_io.g8a.job*) ;; *) echo "FAKE: unexpected command: $cmd" >&2; exit 90;; esac
eval "set -- ${cmd#exec }"
out=; acc=; tx=; nex=0
while [ $# -gt 0 ]; do case $1 in --out) out=$2; shift;; --accum) acc=$2; shift;; --train-extra) tx=$2; nex=$((nex + 1)); shift;; esac; shift; done
echo "FAKE-JOB cwd=$(pwd) out=$out accum=$acc train-extra=[$tx] n_train_extra=$nex" >> $FAKE_LOG
case "$cmd" in *--steps*|*--ckpt-every*|*--resume*) echo "FAKE-JOB BAD FLAGS in: $cmd" >> $FAKE_LOG;; esac
[ "$tx" = "${EXPECT_TX:---log-every 1}" ] || echo "FAKE-JOB BAD TRAIN-EXTRA [$tx]" >> $FAKE_LOG
mkdir -p $out/B3G2
[ "${STUBBORN:-0}" = 1 ] && trap '' TERM
per=0.5; [ "$acc" = "B3G2=32" ] && per=2.5
s=0
while :; do
  s=$((s + 1))
  echo "{\"event\": \"train\", \"step\": $s, \"loss\": 5.$((1000 - s)), \"lr\": 0.0003, \"elapsed\": $(awk "BEGIN{printf \"%.1f\", 3 + $s * $per}"), \"cap_hits\": 0}" >> $out/B3G2/stdout.txt
  sleep 0.05
done
FAKE
chmod +x $T/fake_job.sh
export FAKE_LOG=$T/fake.log FAKEJOB=$T/fake_job.sh TVARS=$T/vars.sh TFUNCS=$T/funcs.sh EXPORT=$P/src-b3g2
export RES PRAW SB3 W
: > $FAKE_LOG
case $CASE in
  happy) ;;
  stubborn) export STUBBORN=1;;
  hang) export PROF_DRY_HANG=i4_a4;;
  fail) export PROF_DRY_FAIL=i4_a32;;
  nobudget) export PROF_MAXMIN=100;;
  tamper) export TAMPER=models/b3g2.py;;
  nofetch) export NOFETCH=1;;
  controls) export PROF_PAIR_RUNS=a8:8:400:1,a4s401:4:401:1;;
esac
# speed the test: timeouts of 1 and 2 minutes, a stop at step 60 instead of 300
export PROF_PAIR_A4_MIN=${PROF_PAIR_A4_MIN:-1} PROF_PAIR_A32_MIN=${PROF_PAIR_A32_MIN:-2} PROF_PAIR_STEP=${PROF_PAIR_STEP:-60}
[ "$CASE" = hang ] && export PROF_PAIR_A4_MIN=0.2
bash $T/drv.sh 2>&1 | sed 's/\x1b//g' | cut -c1-900
echo "--- fake.log"; cat $FAKE_LOG
echo "--- leftover job processes:"; ps -eo args= | grep -F "$T" | grep -v -F grep | cut -c1-120
for k in a4 a32 a8 a4s401; do [ -f $J/profraw/pair_${k}_events.jsonl ] && echo "pair_${k}_events.jsonl: $(wc -l < $J/profraw/pair_${k}_events.jsonl) lines, first: $(head -n 1 $J/profraw/pair_${k}_events.jsonl | cut -c1-120), last: $(tail -n 1 $J/profraw/pair_${k}_events.jsonl | cut -c1-120)"; done
true
