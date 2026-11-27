# MEM 11000
# PAR 3
# Screen (marks: custom_io/PASS-MARKS.md), seed 101, window 2: B, A0, plain_tf L2x2. 24k updates, batch 256.
run B_s101 --model ledger --cfg '{}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 300 &
run A0_s101 --model register_loop --cfg '{"steps":false}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 300 &
run l2x2_s101 --model plain_tf --cfg '{"d_model":256,"n_layers":2,"n_heads":4,"n_loops":2}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 300 &
wait
