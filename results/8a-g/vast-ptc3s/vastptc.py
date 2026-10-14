#!/usr/bin/env python3
"""Run the kit's vast.py (custom_io/box/vast.py of branch claude/project-thread-x2cm2v) with THIS folder's box script, without editing the kit.

  python3 vastptc.py KIT_VAST_PY search --gpu "RTX 4090" --n 8
  python3 vastptc.py KIT_VAST_PY create --offer ID --label ptc3s --env "MAXH=6 DPH=0.38 PROJ_CAP_USD=4"
  python3 vastptc.py KIT_VAST_PY status|tail|collect|collectck|destroy|credit ...      (the kit's own arguments, unchanged)

KIT_VAST_PY is the path of the kit's vast.py (see RUNBOOK.md for how to get it and which sha256 it must have). Three changes are made to the loaded module before its
main() runs, nothing else:
  BOX = ptc3s_box.sh next to this file   (the kit's create reads custom_io/box/box.sh)
  OUT = ./collected/ (or $PTC_OUT)       (the kit's collectck writes the result blocks it meets into OUT = custom_io/results of the kit's repo, ignoring --out; here they land beside the rest)
  collect only: checkpoint-part blocks are dropped from the log text first. The kit's collect unpacks every RBEGIN line as 4 fields, and the 7-field RBEGIN lines of
                the checkpoint parts (printed right after the result) make it stop with "too many values to unpack". Use collectck for the checkpoint itself.
Every network call is the kit's own (the proxy adds the Vast key; this file never reads or prints one).
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if len(sys.argv) < 3 or not sys.argv[1].endswith('.py'):
    sys.exit(__doc__)
kit = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('vast', kit)
vast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vast)
vast.BOX = HERE / 'ptc3s_box.sh'
vast.OUT = Path(os.environ.get('PTC_OUT', HERE / 'collected'))

if sys.argv[2] == 'collect':
    _log_text = vast.log_text

    def log_text_without_ck_parts(i, tail=20000):
        keep, skip = [], False
        for ln in _log_text(i, tail).splitlines():
            if ln.startswith('RBEGIN|') and ln.count('|') > 3:      # a checkpoint part: RBEGIN|ckN|sha|size|job/run|k|n
                skip = True
            elif skip:
                skip = not ln.startswith('REND|')
            else:
                keep.append(ln)
        return '\n'.join(keep)
    vast.log_text = log_text_without_ck_parts

sys.argv = [str(kit)] + sys.argv[2:]
vast.main()
