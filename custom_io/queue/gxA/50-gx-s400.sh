# MEM 8000
# PAR 1
# GX stage 1, seed 400, on rented RTX 5090 box A (spec design/8a-gx-experts-2026-10-09.md addendum G, written before any box result):
# GX-3M and its same-box G-B2 3M control side by side. Box: vast.py create --label gxA --qsub /gxA
#   --env "BR=claude/project-thread-x2cm2v TFVER=5.19.0 EG=1 MAXH=6.5 IDLE_EXIT=600 END_SLEEP=300 FAIL_SLEEP=600"
bash custom_io/box/gx_box.sh 400 8aG1d
