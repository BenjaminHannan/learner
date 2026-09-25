#!/usr/bin/env python3
"""lis-319 training data = lis-318's data, every prompt rebuilt WITH the earlier conversation, plus dialog rows
written to need that history (the one change: the reader reads the conversation, not one turn).

Steps:
  1. Build lis-318's data exactly (scripts/claude_lis318_data.py, same args) into OUT/base318.
  2. Re-prompt every row with claude_lis319_common.build_prompt_hist. Rows from single-turn sources (o0b, opus,
     opus301 and their dev rows) get history "(none)". chat318 rows get their dialog's earlier turns (from
     artifacts/claude-lis318-20260925/data/chat_w*.jsonl). chat318 rows whose frame has an UNCLEAR fact or act
     are dropped: they were labelled for a reader without history.
  3. Add hist319 rows (artifacts/claude-lis319-20260925/data/hist_w*.jsonl) that a blind second labeller, who also
     read each dialog in order, reproduced (--agree319): 10% of dialogs to dev (src hist319_dev), the rest x --repeat.
Targets are unchanged (claude_lis300_common.frame_text). No LoCoMo / LongMemEval text anywhere.
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
from claude_lis300_common import frame_text  # noqa: E402
from claude_lis319_common import build_prompt_hist, dialog_histories  # noqa: E402

CHAT318 = HERE.parent / "artifacts/claude-lis318-20260925/data"


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def split_prompt(prompt):
    head, turn = prompt.rsplit("\nUser said: ", 1)
    turn = turn[: -len("\nFrame: ")] if turn.endswith("\nFrame: ") else turn
    prev = head.rsplit("\nAssistant said: ", 1)[1]
    return turn, ("" if prev == "(nothing)" else prev)


def unclear(frame):
    return frame.get("act") == "UNCLEAR" or any(
        isinstance(f, dict) and f.get("mode") == "UNCLEAR" for f in frame.get("facts") or [])


def dialog_of(r):
    return r["id"].rsplit("-t", 1)[0]


def order_of(r):
    return int(r["id"].rsplit("-t", 1)[1])


def main():
    ap = argparse.ArgumentParser()
    for k in ("--o0b", "--o0a2", "--opus300", "--agree300", "--opus301", "--agree301", "--dev-agree",
              "--chat318", "--agree318", "--hist319", "--agree319", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--repeat", type=int, default=4)
    ap.add_argument("--dev-frac", type=float, default=0.1)
    a = ap.parse_args()
    out = Path(a.out)
    base = out / "base318"
    args318 = []
    for k in ("o0b", "o0a2", "opus300", "agree300", "opus301", "agree301", "dev_agree", "chat318", "agree318"):
        args318 += ["--" + k.replace("_", "-"), getattr(a, k)]
    subprocess.run([sys.executable, str(HERE / "claude_lis318_data.py"), *args318, "--out", str(base)], check=True)
    chat_all = []
    for p in sorted(Path(a.chat318).glob("chat_w*.jsonl")):
        chat_all += read_jsonl(p)
    chat_by = {r["id"]: r for r in chat_all}
    chat_hist = dialog_histories(chat_all, dialog_of, order_of)
    c = Counter()

    def reprompt(r):
        if r["src"].startswith("chat318"):
            src = chat_by[r["id"]]
            if unclear(src["frame"]):
                c["dropped_chat318_unclear:" + r["src"]] += 1
                return None
            return dict(r, prompt=build_prompt_hist(src["turn"], src.get("prev_reply", ""), chat_hist[r["id"]]))
        turn, prev = split_prompt(r["prompt"])
        return dict(r, prompt=build_prompt_hist(turn, prev, None))

    train = [x for x in (reprompt(r) for r in read_jsonl(base / "train.jsonl")) if x]
    dev = [x for x in (reprompt(r) for r in read_jsonl(base / "dev.jsonl")) if x]
    for r in dev:
        if "history" not in r:
            r["history"] = chat_hist.get(r["id"], []) if r["src"].startswith("chat318") else []
    hist_all = []
    for p in sorted(Path(a.hist319).glob("hist_w*.jsonl")):
        hist_all += read_jsonl(p)
    hh = dialog_histories(hist_all, dialog_of, order_of)
    agree = set(Path(a.agree319).read_text().split())
    rows = [r for r in hist_all if r["id"] in agree]
    dialogs = sorted({dialog_of(r) for r in rows})
    rng = random.Random(319)
    rng.shuffle(dialogs)
    dev_d = set(dialogs[: int(len(dialogs) * a.dev_frac)])
    for r in rows:
        row = {"id": r["id"], "prompt": build_prompt_hist(r["turn"], r.get("prev_reply", ""), hh[r["id"]]),
               "target": frame_text(r["frame"]), "src": "hist319", "family": r.get("family", "")}
        if dialog_of(r) in dev_d:
            dev.append(dict(row, src="hist319_dev", turn=r["turn"], prev_reply=r.get("prev_reply", ""),
                            frame=r["frame"], history=hh[r["id"]]))
        else:
            train.extend([row] * a.repeat)
    rng.shuffle(train)
    for name, rs in (("train", train), ("dev", dev)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"train": len(train), "dev": len(dev), "hist319_agreed": len(rows), **c,
                      "train_src": Counter(r["src"] for r in train),
                      "dev_src": Counter(r["src"] for r in dev)}, indent=1))


if __name__ == "__main__":
    main()
