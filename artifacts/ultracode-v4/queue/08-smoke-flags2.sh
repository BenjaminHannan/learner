# MEM 7000
SM="--copy-path --gen-fix --families arith_bare,seq_next --sample-seed 9 --fixed-rows 20 --passes 2 --updates 40 --eval-every 20 --dev-n 10 --eval-at-start"
run moe    $SM --moe-revive 0.02 --aux-weight 1.0
run opt    $SM --fresh-adam --wd 0.1 --accum 4
