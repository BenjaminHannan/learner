#!/bin/bash
# lf_sha256.py on the real pool (LF) and on a CRLF copy made the way a Windows text-mode write does it
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
POOL=/dev/shm/ptcdry/J/work/g8a/pools/p10-rung30-s400-a64-L/train.jsonl
T=/dev/shm/ptcdry/train_crlf.jsonl
python3 -I $K/lf_sha256.py $POOL
python3 -I -c "
b = open('$POOL', 'rb').read()
open('$T', 'wb').write(b.replace(b'\n', b'\r\n'))
"
python3 -I $K/lf_sha256.py $T
rm -f $T
