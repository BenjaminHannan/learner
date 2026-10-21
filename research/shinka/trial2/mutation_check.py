#!/usr/bin/env python3
"""Proof that the guard tests have teeth: switch off each GUARD line in a temp copy of money.py and
require the unit tests to FAIL. Exit 0 only if every removal is caught. Run: python mutation_check.py"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "money.py").read_text().splitlines(keepends=True)
targets = [i for i, l in enumerate(src) if "# GUARD-" in l]
bad = []
for i in targets:
    name = re.search(r"# (GUARD-[\w-]+)", src[i]).group(1)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for f in ("pricing.json", "guarded.py", "test_money.py"):
            shutil.copy(HERE / f, d / f)
        lines = list(src)
        if lines[i].lstrip().startswith("if "):
            lines[i] = lines[i].replace("if ", "if False and ", 1)
        else:                                            # a bare statement: turn it into a no-op
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = indent + "pass  # mutated\n"
        (d / "money.py").write_text("".join(lines))
        (d / "results").mkdir()
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=d,
                           capture_output=True, text=True)
        caught = r.returncode != 0
        print(f"{name:22s} removed -> tests {'FAIL (good)' if caught else 'STILL PASS (BAD)'}")
        if not caught:
            bad.append(name)
print("ALL GUARDS COVERED" if not bad else f"NOT COVERED: {bad}")
sys.exit(1 if bad else 0)
