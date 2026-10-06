# MEM 6000
run CRTSMOKE --copy-path --gen-fix --families $W8 --fixed-rows 20 --passes 2 --updates 40 --eval-every 40 --dev-n 16 --sample-seed 9 --steps --steps-rich --seq-steps-v2 --plan-route 300 --plan-cosine --plan-talk --final-lesions --save-texts
