# MEM 8000
# PAR 1
# EGR seed 201 (EmbeddingGemma plus each char's own letter, no window; PASS-MARKS.md addenda 6 and 12, written before any EGR run), on the same
# rented RTX 5090 as B2V_s201, which is its base. Same recipe and flags as queue 38's EGR line.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGR_s201 --model ledger --cfg '{"copy":true,"eg_embed":true,"reader_layers":0}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
