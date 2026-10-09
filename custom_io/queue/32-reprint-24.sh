# MEM 0
# PAR 1
# Job 24's result tarball again: the earlier re-prints used 480-char base64 lines, and with the 19-char job name the
# R| lines were 502 chars, over the Vast log's 500-char line limit (now 300, as box.sh uses).
RESULTS="24-ingredient-place"
PARTS=""
PFX=rpd
source custom_io/box/ck_reprint.sh
