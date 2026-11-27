# MEM 0
# PAR 0
# Checkpoint of 70-t1sdr-s201 (T1SDR_s201) off the box through its log (custom_io/box/ck_export.sh), so the box can be destroyed with the
# checkpoint kept. Waits for the run and its re-score, then for custom_io/queue/t1r2/CKGO (pushed when a collector is reading the log), at most 3 h.
for n in 70-t1sdr-s201 71-wc-t1sdr-s201; do while [ ! -f $J/state/$n.done ]; do sleep 60; done; done
w=0; while [ ! -f $J/mine/custom_io/queue/t1r2/CKGO ] && [ $w -lt 180 ]; do sleep 60; w=$((w + 1)); done
[ -f $J/mine/custom_io/queue/t1r2/CKGO ] || { echo "no CKGO after 3 h: checkpoints not exported"; exit 0; }
RESULTS="70-t1sdr-s201 71-wc-t1sdr-s201"
GLOB="$J/w/70-t1sdr-s201/*/checkpoint.pt"
PFX=ckt1sdrb
PACE=200   # 200 s per part (q60 lost one part at 100 s)
source custom_io/box/ck_export.sh
