# MEM 30000
python $P/scripts/cap256_launch/uc_diag_v4.py --mode plan --warmup 200 --fresh-core --op-attend --lr-cosine --root $P --data $D --out $P/artifacts/uc/$JOB --parent-path $M2 --fresh-rows 34000 --plan-fams chain_ops,state_update,chain_story2,var_chain,cipher_map,fewshot_number_rule,group_induct,seq_cycle --sample-seed 1
