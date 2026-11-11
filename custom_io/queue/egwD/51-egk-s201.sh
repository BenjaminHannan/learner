# MEM 8000
# PAR 1
# EGK seed 201 (PASS-MARKS.md addendum 14, written before any EGK run), on a new rented RTX 5090 (box D) with the same image and env as boxes
# A-C. Base: B2V_s201 from box B (addendum 13). Same recipe and flags as queue 38's lines.
# Box: vast.py create --qsub /egwD --env "TFVER=5.19.0 EG=1 MAXH=7.5 IDLE_EXIT=3600 END_SLEEP=600 FAIL_SLEEP=1800"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGK_s201 --model ledger --cfg '{"copy":true,"eg_embed":true,"eg_thinker":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
