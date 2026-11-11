# MEM 8000
# PAR 1
# STOPPED about 03:05 UTC 10-07 with box B (too slow to finish before the cap); EGE_s201 reruns as box C job 49 (addendum 13).
# EGE seed 201 (PASS-MARKS.md addenda 4 and 13, written before any EGE run), on box B (54540404), the same box that trained B2V_s201, which is
# its base. EGE is B2 with its +-4-character window kept and EmbeddingGemma added. Alone at PAR 1 so it ends before box B's 7.5-hour cap;
# R0_s201 runs on box C instead (addendum 13, timing note). Same recipe and flags as queue 38's line.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGE_s201 --model ledger --cfg '{"copy":true,"eg_embed":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
