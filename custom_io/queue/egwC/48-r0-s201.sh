# MEM 8000
# PAR 1
# R0 seed 201 (PASS-MARKS.md addenda 6 and 13, written before any R0 run): B2 with its +-4-character window removed and nothing added. It moved
# here from box B so box B's EGE_s201 ends before that box's 7.5-hour cap (addendum 13, timing note). Base: B2V_s201 from box B (same GPU
# model, image and data). Same recipe and flags as queue 38's line.
run R0_s201 --model ledger --cfg '{"copy":true,"reader_layers":0}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
