#!/bin/bash
# code_identity.py must give the same answer for an LF tree and the same tree with CRLF line endings (what a Windows checkout does: every LF becomes CRLF); local_runner.code_hash must not
SRC=$(ls -d /dev/shm/ptcdry/J/work/code/8aPTC3S-pc-* | head -1)
KIT=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
T=/dev/shm/ptcdry/crlf
rm -rf $T; mkdir -p $T; cp -r $SRC/custom_io $T/custom_io
python3 -I -c "
import pathlib, sys
n = 0
for f in pathlib.Path('$T/custom_io').rglob('*'):
    if f.is_file() and f.suffix in ('.py', '.json', '.txt'):
        b = f.read_bytes()
        f.write_bytes(b.replace(b'\n', b'\r\n')); n += 1
print('converted', n, 'files to CRLF')
"
echo "LF tree:   $(python3 -I $KIT/code_identity.py $SRC | tr '\n' ' ')"
echo "CRLF tree: $(python3 -I $KIT/code_identity.py $T | tr '\n' ' ')"
echo "raw local_runner.code_hash, LF tree:   $(cd $SRC && /dev/shm/ptcdry/venv/bin/python -c 'from custom_io.local_runner import code_hash; print(code_hash())')"
echo "raw local_runner.code_hash, CRLF tree: $(cd $T && /dev/shm/ptcdry/venv/bin/python -c 'from custom_io.local_runner import code_hash; print(code_hash())')"
rm -rf $T
