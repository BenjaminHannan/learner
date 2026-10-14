#!/bin/bash
# reset the dry-run work root except the cached inputs (data8a, EmbeddingGemma 2, the pool): what is left of a fresh box is the heavy downloads
J=/dev/shm/ptcdry/J
for d in out state res src-ptc base ovl cur work/code work/results work/data work/data_big guard.py mkcmd.py code_identity.py; do rm -rf $J/$d; done
ls $J $J/work
df -m /dev/shm | tail -1
