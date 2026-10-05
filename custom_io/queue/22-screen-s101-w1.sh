# MEM 11000
# PAR 3
# Screen (marks: custom_io/PASS-MARKS.md), seed 101, window 1: A, plain_tf S, plain_tf_steps S. 24k updates, batch 256.
run A_s101 --model register_loop --cfg '{}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
run tf_s101 --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
run tfsteps_s101 --model plain_tf_steps --cfg '{}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
wait
