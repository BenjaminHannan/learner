# MEM 9000
# PAR 3
# Speed probe (no verdict): screen window 2 arms, 400 updates, shared 3 ways, no final eval.
run B_probe --model ledger --cfg '{}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 &
run A0_probe --model register_loop --cfg '{"steps":false}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 &
run l2x2_probe --model plain_tf --cfg '{"d_model":256,"n_layers":2,"n_heads":4,"n_loops":2}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 &
wait
