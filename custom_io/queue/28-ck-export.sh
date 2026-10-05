# MEM 0
# PAR 1
# Keep every checkpoint on box C (screen jobs 20-22, place-code job 24): after job 27 (whose one-piece print was too big
# for the Vast log reader), re-print job 24's results, then print the checkpoints in 3 MB parts, one every 100 s
# (custom_io/box/ck_export.sh; read back with vast.py collectck).
while [ ! -f $J/state/27-export-ckpt-24.done ]; do sleep 30; done
RESULTS="24-ingredient-place"
GLOB="$J/w/2[0-4]-*/*/checkpoint.pt"
PACE=100
source custom_io/box/ck_export.sh
