# MEM 0
# PAR 0
# Checkpoints of 80-t1sdr-s202 and 80-t1sdr-s203 (T1SDR_s202, T1SDR_s203) off the box through its log (custom_io/box/ck_export.sh), so the box can be
# destroyed with the checkpoints kept. Waits for both runs and their re-scores, then for custom_io/queue/t1c1/CKGO (pushed when a collector is
# reading the log), at most 3 h.
for n in 80-t1sdr-s202 80-t1sdr-s203 81-wc-t1sdr-s202 81-wc-t1sdr-s203; do while [ ! -f $J/state/$n.done ]; do sleep 60; done; done
w=0; while [ ! -f $J/mine/custom_io/queue/t1c1/CKGO ] && [ $w -lt 180 ]; do sleep 60; w=$((w + 1)); done
[ -f $J/mine/custom_io/queue/t1c1/CKGO ] || { echo "no CKGO after 3 h: checkpoints not exported"; exit 0; }
RESULTS="80-t1sdr-s202 80-t1sdr-s203 81-wc-t1sdr-s202 81-wc-t1sdr-s203"
GLOB="$J/w/80-t1sdr-s202/*/checkpoint.pt $J/w/80-t1sdr-s203/*/checkpoint.pt"
PFX=ckc1
PACE=200   # 200 s per part (q60 lost one part at 100 s)
source custom_io/box/ck_export.sh
