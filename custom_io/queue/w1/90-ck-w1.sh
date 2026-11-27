# MEM 0
# PAR 0
# Checkpoints of 42-w1-s200 42-w1-s201 off the box through its log (custom_io/box/ck_export.sh), so the box can be destroyed with every
# checkpoint kept. Waits for the training jobs, then for custom_io/queue/w1/CKGO (pushed when a collector is reading the log), at most 3 h.
for n in 42-w1-s200 42-w1-s201; do while [ ! -f $J/state/$n.done ]; do sleep 60; done; done
w=0; while [ ! -f $J/mine/custom_io/queue/w1/CKGO ] && [ $w -lt 180 ]; do sleep 60; w=$((w + 1)); done
[ -f $J/mine/custom_io/queue/w1/CKGO ] || { echo "no CKGO after 3 h: checkpoints not exported"; exit 0; }
RESULTS="42-w1-s200 42-w1-s201"
GLOB="$J/w/42-w1-s200/*/checkpoint.pt $J/w/42-w1-s201/*/checkpoint.pt"
PFX=ckw1
PACE=100
source custom_io/box/ck_export.sh
