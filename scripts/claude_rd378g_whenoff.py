#!/usr/bin/env python3
"""rd-378g report-only row (Trustworthy notes, 2026-09-26): the same rd-378u confirm scoring with ONE hand-written step
off: the note's "when" string is NOT appended in brackets to its text before indexing (claude_rd378L_recall.py:108-109).
Asked by the Thread manager (17:31 UTC): how much of the notes gain rides on that step. Report only, never a mark.
Everything else is claude_rd378u_confirm.score unchanged (same stores, same questions, same outputs).

python claude_rd378g_whenoff.py score --data DATA --convs 5-9 --notes NOTES.jsonl --out OUT_DIR
python claude_rd378g_whenoff.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rd378u_confirm as C  # noqa: E402

_note_rows = C.R.note_rows


def note_rows_when_off(path):
    by, c = _note_rows(path)
    return {k: [(t, dlg, dict(n, when=None)) for t, dlg, n in v] for k, v in by.items()}, c


def selftest():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "n.jsonl"
        p.write_text(json.dumps({"dialog": "x#1", "t": 3, "notes": [{"text": "Wren moved.", "cites": [0],
                                                                      "when": "in May"}]}) + "\n")
        by, c = note_rows_when_off(p)
        ok = by["x"][0][2]["when"] is None and by["x"][0][2]["text"] == "Wren moved." and c["notes"] == 1
        with_when = _note_rows(p)[0]["x"][0][2]["when"] == "in May"
    print("RD378G-WHENOFF-SELFTEST " + ("PASS" if ok and with_when else "FAIL"))
    return 0 if ok and with_when else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        sys.exit(selftest())
    C.R.note_rows = note_rows_when_off
    sys.exit(C.main())
