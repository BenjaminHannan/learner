# MEM 0
# PAR 0
# Re-print part 2 of T1SD_s201's checkpoint export (job 62's log read missed it) from the part files 62 left in $J/res, so the checkpoint
# can be reassembled off the box before the box is destroyed (Ben 10-08: a stopped box holding something we need is emptied, then deleted).
PARTS="60-t1sd-s201/T1SD_s201:2"
PFX=rpt1sdb
PACE=200
source custom_io/box/ck_reprint.sh
