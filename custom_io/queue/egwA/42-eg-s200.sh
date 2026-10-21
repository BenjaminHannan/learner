# MEM 12000
# PAR 1
# EGM then EGO, seed 200, on the same rented RTX 5090 as EGW_s200 and B2V_s200 (PASS-MARKS.md addendum 11, written before any EGW, EGM or EGO
# result), same recipe as queue 36. MEM 12000 makes it wait until B2V_s200 has ended, so it never squeezes EGW. Both are judged against
# B2V_s200 (plain B2 on this box, same seed). expandable_segments only changes how PyTorch reserves GPU memory, not the math.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run EGM_s200 --model ledger --cfg '{"copy":true,"eg_embed":true,"reader_layers":0,"letters_in":false,"eg_adapter":"mlp"}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 200 --log-every 500 --final-eval
run EGO_s200 --model ledger --cfg '{"copy":true,"eg_embed":true,"reader_layers":0,"letters_in":false}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 200 --log-every 500 --final-eval
