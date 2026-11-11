# MEM 0
# PAR 1
# After the B2 screen (job 29) and the re-print (job 30): re-print job 29's results, then print the two B2 checkpoints in
# 3 MB parts (custom_io/box/ck_export.sh, labels ckb1..), so box C can be destroyed with every checkpoint kept.
while [ ! -f $J/state/29-b2-screen.done ] || [ ! -f $J/state/30-ck-reprint.done ]; do sleep 30; done
sleep 120
RESULTS="29-b2-screen"
GLOB="$J/w/29-*/*/checkpoint.pt"
PFX=ckb
PACE=100
source custom_io/box/ck_export.sh
