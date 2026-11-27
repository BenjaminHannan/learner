# MEM 9000
# PAR 2
# Calibration only (no verdict): do plain char transformers keep improving at 3x the updates?
run tf3m_24k  --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --eval-every 4000 --final-eval --minutes 50 --seed 0 &
run tf10m_24k --model plain_tf --cfg '{"d_model":384,"n_layers":6,"n_heads":6}' --steps 24000 --batch 256 --lr 7e-4 --bf16 --eval-every 4000 --final-eval --minutes 50 --seed 0 &
wait
