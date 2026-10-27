#!/usr/bin/env python3
"""Exp 129a Q1 -- F5 + M5 reproducers through REAL loop129a daemon subprocesses.

Same two reproducer conversations as exp 117 Q1 (sealed exp-110 F5/M5
shapes), daemon binary swapped to scripts/fable_loop129a_agent.py with the
exp-129 config. Bar: F5 turn contains Paris absent Lisbon; M5 turn contains
Lisbon.

Writes: artifacts/fable-fix129-20260922/repro129a/{F5,M5}.json
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129a_repro.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (this experiment)

ART = C129.ART129
CFG = ART / "loop129a-config.json"
OUTDIR = ART / "repro129a"

CASES = {
    "F5": (["Mira's city is Lisbon.", "Please forget Mira city",
            "Mira's city is Paris.", "Who is Mira's city?"],
           {"contains": "Paris", "absent": "Lisbon"}),
    "M5": (["Mira's city is Lisbon.", "WHO IS MIRA'S CITY?"],
           {"contains": "Lisbon", "absent": None}),
}


def run_case(name: str, turns: list[str]) -> dict:
    root = Path(tempfile.mkdtemp(prefix=f"129a_{name}_"))
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    proc = subprocess.Popen(
        ["uv", "run", "--offline", "--no-project", "--python", "3.12",
         "--with", "torch", "--with", "numpy", "python", "-B",
         str(SCRIPTS / "fable_loop129a_agent.py"),
         "--daemon", "--dir", str(root), "--config", str(CFG),
         "--idle-seconds", "3600"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        for _ in range(2400):
            if (root / "daemon_status.json").exists() or \
                    proc.poll() is not None:
                break
            time.sleep(0.05)
        replies = []
        for j, text in enumerate(turns):
            fname = f"m{j}.txt"
            (root / "inbox" / fname).write_text(text, encoding="utf-8")
            for _ in range(2400):
                if (root / "done" / fname).exists():
                    break
                time.sleep(0.05)
            replies.append((root / "outbox" / fname).read_text(
                encoding="utf-8").strip())
    finally:
        (root / "STOP").write_text("stop\n")
        proc.wait(timeout=60)
    return {"id": name, "turns": turns, "replies": replies}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, (turns, exp) in CASES.items():
        rec = run_case(name, turns)
        last = rec["replies"][-1] if rec["replies"] else ""
        good = exp["contains"] in last and (
            exp["absent"] is None or exp["absent"] not in last)
        rec.update({"expect": exp, "pass": bool(good)})
        (OUTDIR / f"{name}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Q1-129a {name}: {'OK' if good else 'FAIL'} :: {last[:120]!r}",
              flush=True)
        ok = ok and good
    print(f"Q1-129a -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
