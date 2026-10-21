# MEM 0
# PAR 0
# Checkpoint of 50-t1s-s201 (T1S_s201, re-screen read 10-07: NOT SHOWN: answer selection) off the box through its log
# (custom_io/box/ck_export.sh), so the box can be destroyed with every checkpoint kept. The run is done; CKGO is already in place.
for n in 50-t1s-s201; do while [ ! -f $J/state/$n.done ]; do sleep 60; done; done
[ -f $J/mine/custom_io/queue/t1b/CKGO ] || { echo "no CKGO: checkpoints not exported"; exit 0; }
RESULTS=""
GLOB="$J/w/50-t1s-s201/*/checkpoint.pt"
PFX=ckt1sb
PACE=100
source custom_io/box/ck_export.sh
