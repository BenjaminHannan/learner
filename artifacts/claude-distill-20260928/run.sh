#!/usr/bin/env bash
# Runner: wait for rebuilt sources, rebuild k0/k64/k16384, teacher scores, then 60 sleeps, 4 at a time.
set -u
cd "$(dirname "$0")/../../scripts"
A=../artifacts/claude-distill-20260928
L=$A/rebuild/logs
while [ ! -f $A/rebuild/qual-loop-s0/source.json ] || [ ! -f $A/rebuild/qual-loop-s1/source.json ]; do sleep 60; done
echo "sources done $(date -u +%FT%TZ)" >> $L/runner.log
for s in 0 1; do for k in 64 16384; do
  python claude_fewex_distill_sleep.py rebuild --seed $s --k $k > $L/rebuild-s$s-k$k.log 2>&1 &
done; done
wait
echo "rebuild done $(date -u +%FT%TZ)" >> $L/runner.log
python claude_fewex_distill_sleep.py teacher > $L/teacher.log 2>&1
mkdir -p $A/sleeps
for arm in R128 D128 W128 R16 D16; do for d in 0 1 2; do for s in 0 1; do for k in 64 16384; do
  echo "$s $k $arm $d"
done; done; done; done | xargs -P 4 -L 1 sh -c 'python claude_fewex_distill_sleep.py sleep --seed $0 --k $1 --arm $2 --draw $3 > '$L'/sleep-s$0-k$1-$2-d$3.log 2>&1'
echo "sleeps done $(date -u +%FT%TZ)" >> $L/runner.log
