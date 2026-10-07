# MEM 12000
# PAR 2
# R0 and EGE seed 201 (PASS-MARKS.md addenda 4, 6 and 13, written before any R0 or EGE run), on box B (54540404) after EGR_s201, the same
# box that trained B2V_s201. R0 is B2 with its +-4-character window removed; EGE is B2 with its window kept and EmbeddingGemma added.
# Base: B2V_s201 on this same box. Same recipe and flags as queue 38's lines.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run R0_s201 --model ledger --cfg '{"copy":true,"reader_layers":0}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval &
run EGE_s201 --model ledger --cfg '{"copy":true,"eg_embed":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval &
wait
