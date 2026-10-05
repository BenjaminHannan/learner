# MEM 9000
# PAR 3
# Calibration only (no verdict): seed-to-seed spread of the 3.2M plain transformer at 24k updates, to size the marks.
for s in 1 2 3; do
run tf3m_24k_s$s --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --final-eval --minutes 50 --seed $s &
done
wait
