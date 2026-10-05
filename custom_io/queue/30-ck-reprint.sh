# MEM 0
# PAR 1
# Re-print what the collector missed from job 28: A_s100's checkpoint parts 0-2 and job 24's result tarball
# (custom_io/box/ck_reprint.sh; labels rpc1.. so they never clash with earlier blocks in the log).
RESULTS="24-ingredient-place"
PARTS="20-screen-s100-w1/A_s100:0 20-screen-s100-w1/A_s100:1 20-screen-s100-w1/A_s100:2"
PFX=rpc
PACE=100
source custom_io/box/ck_reprint.sh
