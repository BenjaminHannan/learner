# MEM 9000
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
run CRSMOKE --copy-path --gen-fix --families $W8 --updates 30 --eval-every 30 --dev-n 16 --sample-seed 1 --steps --steps-rich --seq-steps-v2 --plan-route 300 --final-lesions
