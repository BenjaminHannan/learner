#!/usr/bin/env python3
"""lis-318 training data = lis-301 data rebuilt unchanged + chatty Opus rows (the one change).

Steps:
  1. Build the lis-301 data exactly as before (scripts/claude_lis301_data.py, same args) into OUT/base301.
  2. Add the chat rows (artifacts/claude-lis318-20260925/data/chat_w*.jsonl) that a blind second Opus
     labeller reproduced (--agree318, from claude_lis300_agree.py): 10% of them go to dev
     (src chat318_dev), the rest are repeated --repeat times in train (src chat318), as lis-301 did.
Same prompt, frame format and target text (claude_lis300_common). No LoCoMo / LongMemEval text: every
chat row was written from scratch by Opus agents for this experiment.

python3 scripts/claude_lis318_data.py <all claude_lis301_data.py args> --chat318 DIR --agree318 FILE --out DIR
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
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    for k in ("--o0b", "--o0a2", "--opus300", "--agree300", "--opus301", "--agree301", "--dev-agree"):
        ap.add_argument(k, required=True)
    ap.add_argument("--chat318", required=True)
    ap.add_argument("--agree318", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeat", type=int, default=4)
    ap.add_argument("--dev-frac", type=float, default=0.1)
    a = ap.parse_args()
    out = Path(a.out)
    base = out / "base301"
    subprocess.run([sys.executable, str(HERE / "claude_lis301_data.py"), "--o0b", a.o0b, "--o0a2", a.o0a2,
                    "--opus300", a.opus300, "--agree300", a.agree300, "--opus301", a.opus301,
                    "--agree301", a.agree301, "--dev-agree", a.dev_agree, "--out", str(base)], check=True)
    train = read_jsonl(base / "train.jsonl")
    dev = read_jsonl(base / "dev.jsonl")
    agree = set(Path(a.agree318).read_text().split())
    rows = []
    for p in sorted(Path(a.chat318).glob("chat_w*.jsonl")):
        rows += [r for r in read_jsonl(p) if r["id"] in agree]
    # split by dialog so no dialog is in both train and dev
    dialogs = sorted({r["id"].rsplit("-t", 1)[0] for r in rows})
    rng = random.Random(318)
    rng.shuffle(dialogs)
    dev_d = set(dialogs[: int(len(dialogs) * a.dev_frac)])
    n_dev = 0
    for r in rows:
        row = {"id": r["id"], "prompt": build_prompt(r["turn"], r.get("prev_reply", "")),
               "target": frame_text(r["frame"]), "src": "chat318", "family": r.get("family", "")}
        if r["id"].rsplit("-t", 1)[0] in dev_d:
            dev.append(dict(row, src="chat318_dev", turn=r["turn"], prev_reply=r.get("prev_reply", ""),
                            frame=r["frame"]))
            n_dev += 1
        else:
            train.extend([row] * a.repeat)
    rng.shuffle(train)
    for name, rs in (("train", train), ("dev", dev)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"train": len(train), "dev": len(dev), "chat318_agreed": len(rows), "chat318_dev": n_dev,
                      "train_src": Counter(r["src"] for r in train),
                      "dev_src": Counter(r["src"] for r in dev)}, indent=1))


if __name__ == "__main__":
    main()
