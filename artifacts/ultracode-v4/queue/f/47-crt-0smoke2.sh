# MEM 6000
run CRTSMOKE2 --copy-path --gen-fix --families chain_ops,state_update,chain_story2,var_chain --fixed-rows 300 --passes 2 --updates 600 --eval-every 600 --dev-n 16 --sample-seed 9 --steps --steps-rich --seq-steps-v2 --plan-route 2000 --plan-cosine --plan-talk --final-lesions --save-texts
