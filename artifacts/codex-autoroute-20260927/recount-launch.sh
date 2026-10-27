#!/bin/sh
# Run from the repository root, using the already-installed experiment runtime.
set -eu
exec /Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B - <<'PY'
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

root = Path('artifacts/codex-autoroute-20260927').resolve()
sys.path.insert(0, str(root))
import torch
torch.set_num_threads(4)
import recount

stamp = subprocess.check_output(['date', '-u'], text=True).strip()
with (root / 'RECOUNT-RUN-NOTE.md').open('x') as handle:
    handle.write(f'# Full independent AR1 recount\n\nStart (`date -u`): {stamp}\n\n'
                 f'Machine: {platform.node()}; PID {os.getpid()}.\n\n'
                 'Command: `sh artifacts/codex-autoroute-20260927/recount-launch.sh`\n\n'
                 'Uses the unchanged registered recount.py, float32 MPS, four CPU threads. '
                 'The wrapper adds progress logging only; it does not modify model inputs, '
                 'outputs, weights, checks or scoring.\n')

original = recount.replay_checkpoint
def logged(checkpoint, raw_file, panel):
    print(f'Replaying {checkpoint.parent.name}: {len(panel)} requests', flush=True)
    result = original(checkpoint, raw_file, panel)
    print(f'{checkpoint.parent.name}: {result["mismatches"]}', flush=True)
    return result
recount.replay_checkpoint = logged
sys.argv = ['recount.py', '--out', str(root / 'RECOUNT-FINAL.json')]
started = time.monotonic()
recount.main()
elapsed = (time.monotonic() - started) / 60
with (root / 'RECOUNT-RUN-NOTE.md').open('a') as handle:
    handle.write(f'\nElapsed minutes: {elapsed:.6f}.\n\n'
                 f'End (`date -u`): {subprocess.check_output(["date", "-u"], text=True).strip()}\n')
print(f'Recount minutes: {elapsed:.6f}', flush=True)
PY
