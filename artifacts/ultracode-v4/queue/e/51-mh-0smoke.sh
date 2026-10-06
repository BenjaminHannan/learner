# MEM 6000
run MHSMOKE --copy-path --gen-fix --families $W8 --fixed-rows 100 --passes 1 --updates 100 --eval-every 100 --dev-n 16 --sample-seed 9 --steps --steps-rich --seq-steps-v2 --plan-route 300 --plan-cosine --direct-reader --final-lesions --save-texts
