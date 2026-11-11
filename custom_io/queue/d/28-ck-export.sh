# MEM 0
# PAR 1
# Keep every checkpoint on box D (screen job 23): re-print job 23's results (buried under job 26's one-piece print),
# then print the checkpoints in 3 MB parts, one every 100 s (custom_io/box/ck_export.sh; read back with vast.py collectck).
RESULTS="23-screen-s101-w2"
GLOB="$J/w/23-*/*/checkpoint.pt"
PACE=100
source custom_io/box/ck_export.sh
