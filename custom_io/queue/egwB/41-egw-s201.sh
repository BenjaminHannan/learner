# MEM 20000
# PAR 2
# EGW seed 201 on its own rented RTX 5090 (PASS-MARKS.md addenda 9 and 10, written before any EGW, EGM or EGO result). EGW is too slow and too
# big for Ben's PC (0.75 updates/s, 16 GB), so it moved here with the same recipe as queue 36. B2V_s201 is plain B2 on this same box and seed,
# with queue 33's B2 flags: EGW is judged against it (same machine), and B2V minus queue 33's B2_s201 is the read-only device check.
# Box: vast.py create --qsub /egwB --env "TFVER=5.19.0 EG=1 MAXH=8.5 IDLE_EXIT=3600 END_SLEEP=600 FAIL_SLEEP=1800"
run EGW_s201 --model ledger --cfg '{"copy":true,"d":768,"n_heads":12,"eg_embed":true,"reader_layers":0,"letters_in":false,"eg_adapter":"none"}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval &
run B2V_s201 --model ledger --cfg '{"copy":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval &
wait
