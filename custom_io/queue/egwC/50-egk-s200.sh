# MEM 8000
# PAR 1
# EGK seed 200 (PASS-MARKS.md addendum 14, written before any EGK run): EGE with EmbeddingGemma feeding only the thinker (the talker and the
# workspace read B2's own reader output). Base: B2V_s200 from box A (addendum 13). Same recipe and flags as queue 38's lines.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGK_s200 --model ledger --cfg '{"copy":true,"eg_embed":true,"eg_thinker":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 200 --log-every 500 --final-eval
