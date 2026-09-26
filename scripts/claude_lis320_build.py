#!/usr/bin/env python3
"""lis-320 data build: code-checked GLM rows (claude_lis320_check.py output) -> train.jsonl / dev.jsonl (reading thread).

Every row is GLM-worded with a code-written label; nothing else goes in (no Opus rows, no o0b, no lis-319f sentences).
Dev = the dialogs whose sha256(dialog id) falls in the lowest --dev-pct percent; whole dialogs go to one side only.
python3 claude_lis320_build.py --kept KEPT.jsonl [--kept MORE.jsonl] --out DIR [--dev-pct 3]
Prints counts only (rows per split and family).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def dialog_of(row_id):
    return row_id.rsplit("-t", 1)[0]


def is_dev(row_id, pct):
    return int(hashlib.sha256(dialog_of(row_id).encode()).hexdigest()[:8], 16) % 1000 < pct * 10


def build(rows, pct):
    seen, train, dev = set(), [], []
    for r in rows:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        assert r["src"] == "glm320", r["id"]
        (dev if is_dev(r["id"], pct) else train).append(r)
    return train, dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev-pct", type=float, default=3.0)
    a = ap.parse_args()
    rows = [json.loads(x) for p in a.kept for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    train, dev = build(rows, a.dev_pct)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rs in (("train", train), ("dev", dev)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8")
    res = {"rows_in": len(rows), "train": len(train), "dev": len(dev),
           "dev_dialogs": len({dialog_of(r["id"]) for r in dev}),
           "train_dialogs": len({dialog_of(r["id"]) for r in train}),
           "overlap_dialogs": len({dialog_of(r["id"]) for r in dev} & {dialog_of(r["id"]) for r in train}),
           "train_by_family": dict(sorted(Counter(r["family"] for r in train).items())),
           "dev_by_family": dict(sorted(Counter(r["family"] for r in dev).items()))}
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
