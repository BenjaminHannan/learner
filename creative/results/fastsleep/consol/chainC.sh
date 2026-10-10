#!/bin/bash
# Confirm (MARKS.md, last section): fd with --self-stop (256 updates max) and the rp control on s200-s205; 2 runs at a time, 2 threads each.
# Nights for s200/s203/s204/s205 are prepared one at a time beside a running sleep (a night peaks near 6.4 GB; the cgroup limit is 13.4 GiB).
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=2
C=~/consol/C
job() {
  kind=$1; p=$2
  base="python3 -m creative.consol run --parent-dir $HOME/rl/parents/$p --out $C/$p --seed 0 --threads 2 --micro 128"
  case $kind in
    prep) $base --arm fd --updates 256 --prepare >> $C/$p-prep.log 2>&1; echo "C $p prep rc=$?" >> $C/chainC.txt ;;
    fd)   $base --arm fd --updates 256 --check-every 32 --self-stop >> $C/$p-fd.log 2>&1; echo "C $p fd rc=$?" >> $C/chainC.txt ;;
    rp)   until grep -q harm_vs_N $C/$p/fd/result.json 2>/dev/null; do sleep 60; done
          u=$(python3 -c "import json;print(json.load(open('$C/$p/fd/result.json'))['sleep']['updates_done'])")
          $base --arm rp --updates $u --batch 512 --check-every 64 >> $C/$p-rp.log 2>&1; echo "C $p rp rc=$?" >> $C/chainC.txt ;;
  esac
}
export -f job; export C
printf '%s\n' "fd s201" "prep s200" "prep s203" "prep s204" "prep s205" "fd s202" "fd s200" "fd s203" "fd s204" "fd s205" "rp s201" "rp s202" "rp s200" "rp s203" "rp s204" "rp s205" | xargs -P 2 -I{} bash -c 'job {}'
for p in s200 s201 s202 s203 s204 s205; do python3 -m creative.consol_report holdout --out $C/$p --arms fd --threads 2 >> $C/holdout.log 2>&1; done
echo "CHAINC done" >> $C/chainC.txt
