# MEM 7000
SM="--copy-path --gen-fix --families arith_bare,seq_next --sample-seed 9 --fixed-rows 20 --passes 2 --updates 40 --eval-every 20 --dev-n 10 --eval-at-start"
run back   $SM --back 8
run chat   $SM --chat --back 8
run chatnf $SM --chat --back 8 --no-front
run two    $SM --two-path 0.5
run acc    $SM --accum 4
run chat0  $SM --chat
