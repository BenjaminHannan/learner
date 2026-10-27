#!/usr/bin/env python3
"""lis-319: add "history" to dialog rows so claude_lis319_read.py can read them (prints counts only).

Input rows need id, turn, prev_reply and a dialog order: either "dialog" + "t" (readpanel319) or ids of the form
<dialog>-t<T> (chat/hist training rows), or life_id + turn_index (e2e DEV bank rows via claude_lis317_rows.py ids
"<life>:<turn>"). history for a row = the earlier rows of its dialog as (turn, reply to that turn), where the reply
to row k is row k+1's prev_reply.
python claude_lis319_rows.py --rows IN.jsonl --out OUT.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis319_common import dialog_histories  # noqa: E402


def keys(r):
    if "dialog" in r and "t" in r:
        return r["dialog"], int(r["t"])
    if ":" in r["id"]:
        life, t = r["id"].rsplit(":", 1)
        return life, int(t)
    d, t = r["id"].rsplit("-t", 1)
    return d, int(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding="utf-8").splitlines() if x.strip()]
    hist = dialog_histories(rows, lambda r: keys(r)[0], lambda r: keys(r)[1])
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(dict(r, history=hist[r["id"]]), ensure_ascii=False) + "\n")
    print("rows", len(rows), "with history", sum(1 for r in rows if hist[r["id"]]))


if __name__ == "__main__":
    main()
