#!/usr/bin/env python3
"""Exp 293 M1 row-strip (driver fix 2): the sealed score_panel.py demands
exactly the 7 base-row fields in the base order; the arm runner wrote 2
extra diagnostic fields (family, label). This file derives stripped
copies from the ONCE-per-arm rows (no re-run, no text touched).

New file only. Disclosed driver-only fix; sealed files untouched.

Usage:
  uv run ... python -B scripts/claude_293_rowstrip.py <in_rows> <out_rows>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FIELDS = ["id", "setup_replies", "question_reply", "question_stage",
          "stored_after_setup_actual", "stored_after_question_actual",
          "question_wrote"]


def main() -> int:
    src, dst = sys.argv[1:3]
    n = 0
    with open(dst, "w", encoding="utf-8") as f:
        for line in Path(src).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            f.write(json.dumps({k: r[k] for k in FIELDS}) + "\n")
            n += 1
    print(f"STRIPPED {n} rows -> {dst}")


if __name__ == "__main__":
    main()
