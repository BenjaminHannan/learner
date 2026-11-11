#!/bin/bash
# the six harness calls of the PROFILE stage on the CPU with tiny shapes; prints rc and seconds of each
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
T="--device cpu --tiny --rows 400 --batch 32 --updates 2 --warmup 1"
bash $B/prof_try.sh a --arm PTC --rung 3M --accum 16 $T --pad-updates 5 --sweep-updates 1 --sweep-warmup 1
bash $B/prof_try.sh b --arm PTC --rung 3M --accum 16 $T --sections bench --bench-rounds 1 --bench-list "baseline;eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;eg_once,sortpad,bigmb,oldw,prefetch;tf32"
bash $B/prof_try.sh c --arm PTC --rung 3M --accum 16 $T --sections equiv --equiv-check --curve-updates 0 --equiv-list "eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;sortpad;bigmb;tf32;prefetch"
bash $B/prof_try.sh d --arm PTC --rung 3M --accum 16 $T --sections equiv --equiv-check --curve-updates 6 --equiv-list "eg_once"
bash $B/prof_try.sh f1 --arm B3G2 --rung 3M --accum 32 --caps /dev/shm/ptcdry/J/src-ptc/custom_io/g8a/caps_b3g2.json $T --sections breakdown,throughput,padding,syncs --pad-updates 5 --pad-rounds-updates 2
bash $B/prof_try.sh f2 --arm B3G2 --rung 3M --accum 32 --caps /dev/shm/ptcdry/J/src-ptc/custom_io/g8a/caps_b3g2.json $T --sections bench --bench-rounds 1 --bench-list "baseline;eg_once"
