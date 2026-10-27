#!/bin/bash
# Split bm-398d batches into 12 private judge folders. J1-J10: two per L group, three batches each; J11 X1; J12 X2.
set -e
W=$1; J=$2
rm -rf $J; mkdir -p $J
n=1
for g in 0 1 2 3 4; do
  for half in "01 02 03" "04 05 06"; do
    d=$J/J$n; mkdir -p $d/batches $d/labels
    cp /home/user/learner/artifacts/claude-bm398d-20260926/INSTRUCTIONS.md $d/
    for b in $half; do cp $W/batches/L$g$b.jsonl $d/batches/; done
    n=$((n+1))
  done
done
for x in X101 X201; do
  d=$J/J$n; mkdir -p $d/batches $d/labels
  cp /home/user/learner/artifacts/claude-bm398d-20260926/INSTRUCTIONS.md $d/
  cp $W/batches/$x.jsonl $d/batches/
  n=$((n+1))
done
for d in $J/J*; do echo "$(basename $d) $(ls $d/batches | tr '\n' ' ') items=$(cat $d/batches/*.jsonl | wc -l)"; done
