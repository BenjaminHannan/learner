# MEM 8000
# PAR 1
# EGE seed 201 (PASS-MARKS.md addenda 4 and 13, written before any EGE run): B2 with its +-4-character window kept and EmbeddingGemma added. It
# moved here from box B, which ran it at 2.8 updates/s and would have hit its 7.5-hour cap before the end (addendum 13, second timing note).
# Base: B2V_s201 from box B (same GPU model, image and data). Same recipe and flags as queue 38's line.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGE_s201 --model ledger --cfg '{"copy":true,"eg_embed":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
