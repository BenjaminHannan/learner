#!/usr/bin/env python3
"""rsn-296 runner: exactly rsn-294's runner (same arms, sizes, steps, reward, eval), with the
one change that practice and dev episodes come from the varied "sleep school" generator.

  python claude_rsn296_run.py train|dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode)

runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
