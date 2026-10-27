#!/usr/bin/env python3
"""lis-301 training data builder = lis-300 data + targeted hard-case Opus rows (the one change).

Steps:
  1. Build the lis-300 data exactly as before (scripts/claude_lis300_data.py, same args, same seed).
  2. Dev key fix (not a system change): keep an opus_dev / o0a2 dev row only if a blind second
     Opus labeller agreed with its gold frame (--dev-agree ids file). o0b_l2 dev rows are kept.
  3. Add the new Opus rows (opus_w4..w6) that a blind second labeller reproduced (--agree301):
     10% to dev (src opus301_dev), the rest repeated --opus-repeat times in train (src opus301).

python3 scripts/claude_lis301_data.py --o0b DIR --o0a2 DIR --opus300 DIR --agree300 FILE \
    --opus301 DIR --agree301 FILE --dev-agree FILE --out DIR
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from claude_lis300_common import build_prompt, frame_text  # noqa: E402


def read_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--o0b", required=True)
    ap.add_argument("--o0a2", required=True)
    ap.add_argument("--opus300", required=True)
    ap.add_argument("--agree300", required=True)
    ap.add_argument("--opus301", required=True)
    ap.add_argument("--agree301", required=True)
    ap.add_argument("--dev-agree", required=True, help="ids of opus_dev/o0a2 dev rows a blind relabel agreed on")
    ap.add_argument("--out", required=True)
    ap.add_argument("--opus-repeat", type=int, default=4)
    ap.add_argument("--opus-dev-frac", type=float, default=0.1)
    a = ap.parse_args()
    out = Path(a.out)
    base = out / "base300"
    subprocess.run([sys.executable, str(HERE / "claude_lis300_data.py"), "--o0b", a.o0b, "--opus", a.opus300,
                    "--agree", a.agree300, "--o0a2", a.o0a2, "--out", str(base)], check=True)
    train = read_jsonl(base / "train.jsonl")
    dev0 = read_jsonl(base / "dev.jsonl")
    keep = set(Path(a.dev_agree).read_text().split())
    dev = [r for r in dev0 if r["src"] == "o0b_l2" or r["id"] in keep]
    dropped = Counter(r["src"] for r in dev0 if r not in dev)
    agree = set(Path(a.agree301).read_text().split())
    rows = []
    for p in sorted(Path(a.opus301).glob("opus_w*.jsonl")):
        rows += [r for r in read_jsonl(p) if r["id"] in agree]
    rng = random.Random(301)
    rng.shuffle(rows)
    ndev = int(len(rows) * a.opus_dev_frac)
    for i, r in enumerate(rows):
        row = {"id": r["id"], "prompt": build_prompt(r["turn"], r.get("prev_reply", "")),
               "target": frame_text(r["frame"]), "src": "opus301", "family": r.get("family", "")}
        if i < ndev:
            dev.append(dict(row, src="opus301_dev", turn=r["turn"], prev_reply=r.get("prev_reply", ""),
                            frame=r["frame"]))
        else:
            train.extend([row] * a.opus_repeat)
    rng.shuffle(train)
    for name, rs in (("train", train), ("dev", dev)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"train": len(train), "dev": len(dev), "opus301_agreed": len(rows),
                      "dev_dropped_by_relabel": dict(dropped),
                      "train_src": Counter(r["src"] for r in train),
                      "dev_src": Counter(r["src"] for r in dev)}, indent=1))


if __name__ == "__main__":
    main()
