#!/usr/bin/env python3
"""Launcher for rsn-358a v2 when it shares BensPC's GPU with another job (sleep research thread, 2026-09-26).

Caps this process's GPU memory (default 4 GB, env RSN358A_GPU_GB) before anything touches CUDA, then runs
scripts/claude_rsn358a2_run.py unchanged with the same arguments. If the cap is hit, PyTorch raises an
out-of-memory error in THIS process only; the other job's memory is untouched.
  python -B scripts/claude_rsn358a2_shared.py train --arm loop --seed 1 --out W/loop-s1
"""
import os
import runpy
import sys
from pathlib import Path

import torch

if torch.cuda.is_available():
    total = torch.cuda.get_device_properties(0).total_memory
    cap_gb = float(os.environ.get("RSN358A_GPU_GB", "4"))
    torch.cuda.set_per_process_memory_fraction(min(1.0, cap_gb * 2**30 / total), 0)
    print(f"GPU memory cap {cap_gb} GB of {total / 2**30:.1f} GB", flush=True)
sys.argv[0] = str(Path(__file__).with_name("claude_rsn358a2_run.py"))
runpy.run_path(sys.argv[0], run_name="__main__")
