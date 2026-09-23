#!/usr/bin/env python3
"""Experiment 165 -- pre-seal shape scan (Muse). Read-only vs repo.

Scans every sealed G1/G2/G3 input corpus for the 165 claim shape:
a no-apostrophe word ending in s/S directly followed by a person-relation
word, in teach position (``W R is``) or question position
(``who/what/where is|are W R``). The 165 frame cannot fire without this
shape (plus notebook gates that only narrow it), so zero shape hits
justifies the ZERO-moves predictions. Prints hit count and exits nonzero
if any hit is found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)

ROOT = SCRIPTS.parent


def main() -> int:
    rels = set(A.PERSON_RELATIONS)
    tok_re = re.compile(r"[A-Za-z]+")
    qwords = {"who", "what", "where"}
    files: list[Path] = [
        ROOT / "artifacts" / "fable-redteam136-20260922" / "cases136.json",
        ROOT / "artifacts" / "fable-session152-20260922" / "sessions152.json",
    ]
    import fable_loop129b_bench as B129  # noqa: E402 (bench paths, read-only)
    files += [Path(B129.DATA_EDIT200), Path(B129.DATA_OLD),
              Path(B129.DATA_NEW)]
    import fable_redteam143_run as R143  # noqa: E402 (cases path, read-only)
    files.append(Path(R143.CASES_PATH))
    # Marks123 suite inputs: scan the small sealed case files only (the
    # full per-case byte-identity is established by the registered G2 run).
    extra = [
        ROOT / "artifacts" / "fable-redteam110-20260921"
        / "fable_redteam110_cases.json",
        ROOT / "artifacts" / "fable-redteam81-20260921"
        / "fable_redteam81_results.json",
    ]
    for p in extra:
        if p.exists():
            files.append(p)
    hits = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        print(f"scan {f} ({len(text)} chars)", flush=True)
        for line in text.splitlines():
            toks = [t for t in tok_re.findall(line)]
            low = [t.lower() for t in toks]
            for i, t in enumerate(toks):
                if len(t) < 2 or t[-1] not in ("s", "S"):
                    continue
                if i + 1 < len(toks) and low[i + 1] in rels:
                    # teach shape W R is | question shape Q be W R
                    teach = (i + 2 < len(toks) and low[i + 2] == "is")
                    quest = (i >= 2 and low[i - 2] in qwords
                             and low[i - 1] in ("is", "are"))
                    if teach or quest:
                        hits.append((str(f), line[:120]))
                        break
    print(f"scanned {len(files)} files, shape hits: {len(hits)}")
    for f, line in hits[:30]:
        print(f"  HIT {f}: {line}")
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
