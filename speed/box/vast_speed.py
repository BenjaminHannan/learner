#!/usr/bin/env python3
"""Thin wrapper over backbone/vast.py for the speed box (nothing in backbone/ is edited).
Same commands (pack/search/create/status/logs/cat/stop/destroy), three differences:
  * the box runs speed/box/run_speed_box.sh instead of backbone/run_box.sh;
  * `pack --minutes N` (instead of --hours, which is an integer there): the job script is killed at N-5 minutes;
  * pack packs only what the three benches import (backbone/sleep, train.py, speed/) unless --files is given.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backbone"))
import vast  # noqa: E402

vast.JOB = (vast.JOB.replace("bash backbone/run_box.sh", "bash speed/box/run_speed_box.sh")
            .replace("$((HOURS*3600 - 600))", "$((HOURS*60 - 300))"))
assert "run_speed_box.sh" in vast.JOB and "HOURS*60" in vast.JOB, "backbone/vast.py JOB changed; update this wrapper"
FILES = "backbone/sleep,backbone/train.py,backbone/label_report.py,backbone/requirements.txt,speed"

argv = ["--minutes" == a and "--hours" or a for a in sys.argv[1:]]
if argv and argv[0] == "pack" and "--files" not in argv:
    argv += ["--files", FILES]
sys.argv = [sys.argv[0]] + argv
vast.main()
