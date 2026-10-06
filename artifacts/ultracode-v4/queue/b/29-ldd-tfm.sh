# MEM 14000
python $P/scripts/cap256_launch/uc_diag_v4.py --mode direct --head vocab --target step1 --learner tfm --families chain_ops,state_update,chain_story2,var_chain --warmup 200 --fresh-rows 17000 --root $P --data $D --out $P/artifacts/uc/$JOB --parent-path $M2 --sample-seed 1
