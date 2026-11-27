# MEM 12000
# PAR 4
# Ingredient test (PASS-MARKS.md addendum 1): place codes alone on plain_tf and plain_tf_steps, seeds 100 and 101,
# paired with the screen's tf and tfsteps runs. One change: place=true. 24k updates, batch 256.
run tfp_s100 --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4,"place":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 500 --final-eval --minutes 150 &
run tfp_s101 --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4,"place":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
run tfstepsp_s100 --model plain_tf_steps --cfg '{"place":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 500 --final-eval --minutes 150 &
run tfstepsp_s101 --model plain_tf_steps --cfg '{"place":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 101 --log-every 500 --final-eval --minutes 150 &
wait
