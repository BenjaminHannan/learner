# MEM 9000
# PAR 3
# Speed probe (no verdict): screen window 1 arms, 400 updates, shared 3 ways, small final eval (30 rows per split) to catch GPU-only eval bugs.
run A_probe --model register_loop --cfg '{}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 --final-eval --eval-max 30 &
run tf_probe --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 --final-eval --eval-max 30 &
run tfsteps_probe --model plain_tf_steps --cfg '{}' --steps 400 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 100 --final-eval --eval-max 30 &
wait
