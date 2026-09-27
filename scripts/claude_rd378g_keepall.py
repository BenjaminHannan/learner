#!/usr/bin/env python3
"""rd-378g ungraded rows: a keep-all verdict file, so the sealed row builder runs unchanged with no grade filter
(Trustworthy notes thread, 2026-09-27; rd-378g DRAFT-ADDENDUM-K). New file.

This is NOT a grade. No model and no rule looks at any note. For every turn the row builder
(scripts/claude_rd378_data.py) would read, it writes {"dialog","t","verdicts": ["ok"] * number of notes, "missed": 0},
so every turn is kept exactly as its writer (GLM or Luna) wrote it, including turns where the writer chose no note.
Prints counts only, never text.

python -B scripts/claude_rd378g_keepall.py make --notes DIR/notes_w1.jsonl --out DIR/judge_w1.jsonl
python -B scripts/claude_rd378g_keepall.py selftest
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def keep_all(dialogs):
    out, c = [], Counter()
    for d in dialogs:
        c["dialogs"] += 1
        c["writer:" + d.get("writer", "unknown")] += 1
        for t in d["turns"]:
            if d["kind"] == "chat" and t["speaker"] == "assistant":
                continue
            n = len(t.get("notes") or [])
            out.append({"dialog": d["dialog"], "t": int(t["t"]), "verdicts": ["ok"] * n, "missed": 0})
            c["turns"] += 1
            c["notes"] += n
            c["turns_no_note"] += n == 0
    return out, dict(sorted(c.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["make", "selftest"])
    ap.add_argument("--notes", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.mode == "selftest":
        d = [{"dialog": "kg-1", "kind": "chat", "writer": "w", "turns": [
            {"t": 0, "speaker": "user", "text": "x", "notes": [{"text": "a"}, {"text": "b"}]},
            {"t": 1, "speaker": "assistant", "text": "y"},
            {"t": 2, "speaker": "user", "text": "z", "notes": []}]},
             {"dialog": "kg-2", "kind": "overheard", "turns": [
                 {"t": 0, "speaker": "A", "text": "x", "notes": [{"text": "a"}]},
                 {"t": 1, "speaker": "B", "text": "y"}]}]
        out, c = keep_all(d)
        assert out == [{"dialog": "kg-1", "t": 0, "verdicts": ["ok", "ok"], "missed": 0},
                       {"dialog": "kg-1", "t": 2, "verdicts": [], "missed": 0},
                       {"dialog": "kg-2", "t": 0, "verdicts": ["ok"], "missed": 0},
                       {"dialog": "kg-2", "t": 1, "verdicts": [], "missed": 0}], out
        assert c["turns"] == 4 and c["notes"] == 3 and c["turns_no_note"] == 2 and c["dialogs"] == 2, c
        print("rd378g keepall selftest 1/1 ok")
        return
    dialogs = [json.loads(x) for x in Path(a.notes).read_text(encoding="utf-8").splitlines() if x.strip()]
    out, c = keep_all(dialogs)
    Path(a.out).write_text("".join(json.dumps(x) + "\n" for x in out), encoding="utf-8")
    print(json.dumps(c))


if __name__ == "__main__":
    main()
