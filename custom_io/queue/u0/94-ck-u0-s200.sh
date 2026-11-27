# MEM 0
# PAR 0
# Re-print U0_s200's checkpoint once more (the collector missed its part 2 in both job 90 and job 93), slower still.
GLOB="$J/w/41-u0-s200/*/checkpoint.pt"
PFX=cku0s
PACE=240
source custom_io/box/ck_export.sh
