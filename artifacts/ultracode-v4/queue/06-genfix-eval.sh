# MEM 7000
EV="--copy-path --eval-only --updates 0"
run bug   $EV --families $W8 --dev-kinds in_dist --dev-n 320 --sample-seed 1 --fixed-rows 2000
run fix   $EV --families $W8 --dev-kinds in_dist --dev-n 320 --sample-seed 1 --fixed-rows 2000 --gen-fix
run all   $EV --dev-kinds in_dist --dev-n 5000 --gen-fix
run zero  $EV --dev-kinds in_dist --dev-n 5000 --gen-fix --zero-pool
run shuf  $EV --dev-kinds in_dist --dev-n 5000 --gen-fix --shuffle-pool
