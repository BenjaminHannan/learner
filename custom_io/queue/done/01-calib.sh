# MEM 9000
# PAR 3
# Calibration only (no verdict rides on it): how hard is the benchmark for plain char transformers, how fast do runs go,
# and is 8,000 updates at batch 256 enough. See custom_io/CALIBRATION.md.
run tf3m  --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4}' --steps 8000 --batch 256 --lr 1e-3 --bf16 --eval-every 2000 --final-eval --minutes 35 --seed 0 &
run tf10m --model plain_tf --cfg '{"d_model":384,"n_layers":6,"n_heads":6}' --steps 8000 --batch 256 --lr 7e-4 --bf16 --eval-every 2000 --final-eval --minutes 35 --seed 0 &
run tf2x4 --model plain_tf --cfg '{"d_model":256,"n_layers":2,"n_heads":4,"n_loops":4}' --steps 8000 --batch 256 --lr 1e-3 --bf16 --eval-every 2000 --final-eval --minutes 35 --seed 0 &
wait
