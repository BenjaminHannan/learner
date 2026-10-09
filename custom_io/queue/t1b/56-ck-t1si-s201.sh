# MEM 0
# PAR 0
# Checkpoint of 53-t1si-s201 (T1SI_s201) off the box through its log (custom_io/box/ck_export.sh), so the box can be destroyed with every
# checkpoint kept. Waits for the run and its re-score, then for custom_io/queue/t1b/CKGO2 (pushed when a collector is reading the log), at most 3 h.
for n in 53-t1si-s201 54-wc-t1si-s201; do while [ ! -f $J/state/$n.done ]; do sleep 60; done; done
w=0; while [ ! -f $J/mine/custom_io/queue/t1b/CKGO2 ] && [ $w -lt 180 ]; do sleep 60; w=$((w + 1)); done
[ -f $J/mine/custom_io/queue/t1b/CKGO2 ] || { echo "no CKGO2 after 3 h: checkpoints not exported"; exit 0; }
RESULTS="53-t1si-s201 54-wc-t1si-s201"
GLOB="$J/w/53-t1si-s201/*/checkpoint.pt"
PFX=ckt1sib
PACE=100
source custom_io/box/ck_export.sh
