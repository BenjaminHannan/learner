#!/bin/bash
# Recovery after the 12:08 UTC container restart killed the s205 control at update 240/256 (the other five controls and all six fd runs were complete).
# Order: s205 rp (3 threads) beside the holdout scoring of s200-s204 (1 thread); then the s205 holdout and the confirm scoring.
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=3
C=~/consol/C
python3 -m creative.consol run --parent-dir $HOME/rl/parents/s205 --out $C/s205 --seed 0 --threads 3 --micro 128 --arm rp --updates 256 --batch 512 --check-every 64 >> $C/s205-rp.log 2>&1 &
RP=$!
for p in s200 s201 s202 s203 s204; do OMP_NUM_THREADS=1 python3 -m creative.consol_report holdout --out $C/$p --arms fd --threads 1 >> $C/holdout.log 2>&1; done
wait $RP; echo "C s205 rp rc=$?" >> $C/chainC.txt
OMP_NUM_THREADS=3 python3 -m creative.consol_report holdout --out $C/s205 --arms fd --threads 3 >> $C/holdout.log 2>&1
OMP_NUM_THREADS=3 python3 -m creative.consol_report confirm --root $C --b2-dir $HOME/work/ckpt --threads 3 > $C/confirm-marks.txt 2>&1
echo "CHAIND done" >> $C/chainC.txt
