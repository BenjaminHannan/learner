# MEM 12000
# PAR 2
# B2 screen (design/design-B2.md; marks in PASS-MARKS.md addendum 2, written before this run): B + content-addressed copy
# talker, seeds 100 and 101, B's exact screen flags. Runs on box C's idle GPU while job 28 prints checkpoints (the box stays
# up for that anyway; Ben's own machines are unreachable since 04:01 UTC). Paired with tf, tfsteps and B from jobs 20-23.
run B2_s100 --model ledger --cfg '{"copy":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 500 --final-eval --minutes 150 &
run B2_s101 --model ledger --cfg '{"copy":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
wait
