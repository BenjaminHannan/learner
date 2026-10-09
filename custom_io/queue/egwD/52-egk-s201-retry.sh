# MEM 8000
# PAR 1
# EGK seed 201 RETRY (PASS-MARKS.md addendum 14, retry note): job 51 hit a non-finite loss at update 3,000 (status nonfinite_loss, not judged).
# Identical recipe, flags and seed, on the same box D. Base: B2V_s201 from box B (addendum 13).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGK_s201 --model ledger --cfg '{"copy":true,"eg_embed":true,"eg_thinker":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval
