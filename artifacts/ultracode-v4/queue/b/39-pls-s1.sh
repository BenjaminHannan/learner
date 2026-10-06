# MEM 6000
python $P/scripts/cap256_launch/uc_diag_v4.py --mode plan --warmup 200 --fresh-core --op-attend --lr-cosine --root $P --data $D --out $P/artifacts/uc/$JOB --parent-path $M2 --screen-rows --sample-seed 1
