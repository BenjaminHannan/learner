#!/usr/bin/env python3
"""Exp 129a Q4 -- no reply in any 129a Q2/Q3 transcript contains an
underscore inside a relation name (same scan rule as exp 117 Q4).

Scans every reply string in q2-129a-report.json, p2-129a-report.json,
the p3-129a L-mark reports, and p4-129a-report.json. Exit 0 iff zero
relation-name leaks. (A literal VALUE containing an underscore is reported
separately, never a leak.)

Run (after Q2 and Q3; read-only over the reports):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129a_q4scan.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (vocab, read-only)
import fable_fix129_common as C129  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = C129.ART129

TOKEN = re.compile(r"[A-Za-z][A-Za-z_]*_[A-Za-z_]*")
POSS = re.compile(r"'s\s+([A-Za-z][A-Za-z_]*)")

VOCAB: set[str] = {rel for _, rel in B73.STATEMENT_PATTERNS}
VOCAB.update(B73.REV_OF_NOUNS.values())
try:
    VOCAB.update(B73.REV_BY_VERBS.values())
except AttributeError:
    pass
VOCAB.update({"country_of_citizenship", "maternal_grandmother"})


def replies_in(obj, path: str):
    """Yield (path, reply) for every reply-looking string in the reports."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key in ("reply", "replies", "got", "loop129a_final",
                        "after_final", "base_reply", "loop96_reply"):
                items = val if isinstance(val, list) else [val]
                for i, item in enumerate(items):
                    if isinstance(item, str):
                        yield (f"{path}.{key}[{i}]", item)
                    else:
                        yield from replies_in(item, f"{path}.{key}[{i}]")
            else:
                yield from replies_in(val, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from replies_in(item, f"{path}[{i}]")


def leaks_in(reply: str) -> tuple[list[str], list[str]]:
    """Return (relation-name leaks, non-relation underscore tokens)."""
    leaks, others = [], []
    for m in POSS.findall(reply):
        if "_" in m:
            leaks.append(m)
    for m in TOKEN.findall(reply):
        if m in leaks:
            continue
        if m in VOCAB:
            leaks.append(m)
        else:
            others.append(m)
    return leaks, others


def main() -> int:
    files = [ART / "q2-129a-report.json", ART / "p2-129a-report.json",
             ART / "p4-129a-report.json"]
    p3 = ART / "p3-129a"
    if p3.is_dir():
        files.extend(sorted(p3.glob("*.json")) + sorted(p3.glob("*.jsonl")))
    leaks: list = []
    notes: list = []
    for path in files:
        if not path.exists():
            print(f"missing: {path.relative_to(ROOT)}")
            continue
        blobs = []
        if path.suffix == ".jsonl":
            for n, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines()):
                if line.strip():
                    blobs.append((f"{path.name}:{n}", json.loads(line)))
        else:
            blobs.append((path.name,
                          json.loads(path.read_text(encoding="utf-8"))))
        for name, obj in blobs:
            for loc, reply in replies_in(obj, name):
                rel_leaks, other = leaks_in(reply)
                for tok in rel_leaks:
                    leaks.append((loc, tok, reply.strip()[:120]))
                for tok in other:
                    notes.append((loc, tok, reply.strip()[:120]))
    for loc, tok, reply in leaks:
        print(f"LEAK {loc}: {tok!r} in {reply!r}")
    for loc, tok, reply in notes:
        print(f"note (value, not a relation): {loc}: {tok!r} in {reply!r}")
    print(f"Q4-129a: {len(leaks)} relation-name underscore leaks "
          f"-> {'PASS' if not leaks else 'FAIL'}")
    return 0 if not leaks else 1


if __name__ == "__main__":
    sys.exit(main())
