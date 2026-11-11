# MEM 12000
# PAR 2
# R0 and EGE seed 200 (PASS-MARKS.md addenda 4, 6 and 13, written before any R0 or EGE run), on a new rented RTX 5090 (box C) with the same
# image and env as boxes A and B. R0 is B2 with its +-4-character window removed; EGE is B2 with its window kept and EmbeddingGemma added.
# Base: B2V_s200 from box A (same GPU model, image and data; disclosed in addendum 13). Same recipe and flags as queue 38's lines.
# Box: vast.py create --qsub /egwC --env "TFVER=5.19.0 EG=1 MAXH=7.5 IDLE_EXIT=3600 END_SLEEP=600 FAIL_SLEEP=1800"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run R0_s200 --model ledger --cfg '{"copy":true,"reader_layers":0}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 200 --log-every 500 --final-eval &
run EGE_s200 --model ledger --cfg '{"copy":true,"eg_embed":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 200 --log-every 500 --final-eval &
wait
