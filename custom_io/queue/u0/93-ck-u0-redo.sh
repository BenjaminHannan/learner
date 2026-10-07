# MEM 0
# PAR 0
# Re-print both U0 checkpoints (the collector missed part 2 of U0_s200 and part 1 of U0_s201 in job 90's export), at a slower pace.
GLOB="$J/w/41-u0-s200/*/checkpoint.pt $J/w/41-u0-s201/*/checkpoint.pt"
PFX=cku0r
PACE=150
source custom_io/box/ck_export.sh
