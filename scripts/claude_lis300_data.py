#!/usr/bin/env python3
"""lis-300 training data builder.

Sources:
  1. own-O0b generator rows (builder-outbox artifacts/claude-own-o0b-20260923, sealed PASS),
     converted from character spans to the frame-spec strings; a fixed-seed sample per family.
  2. Opus-written natural rows (artifacts/claude-lis300-20260923/data/opus_w*.jsonl), only the
     rows whose frame a blind second Opus labeller reproduced (audit_agree ids file).
Output: train.jsonl / dev.jsonl with {"id","prompt","target","src","family"}.

python3 scripts/claude_lis300_data.py --o0b DIR --opus DIR --agree FILE --out DIR [--per-family 3000] [--opus-repeat 4]
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_common import build_prompt, frame_text  # noqa: E402

ACT = {"STATE": "STATE", "CORRECT": "CORRECT", "DENY": "NEGATE", "ASK": "ASK", "CHECK": "CHECK",
       "SUPPOSE": "SUPPOSE", "PLAN": "PLAN", "CHAT": "CHAT", "UNCLEAR": "UNCLEAR"}
MODE = {"ASSERT": "ASSERT", "CORRECT": "CORRECT", "DENY": "NEGATED", "CHECK": "CHECK",
        "SUPPOSE": "SUPPOSE", "PLAN": "PLAN", "REPORTED": "REPORTED", "ASK": "QUESTION",
        "NONE": "UNCLEAR"}


def span(turn, s):
    if s == "ME":
        return "me"
    if s == "WE":
        return "we"
    return turn[s[0]:s[1]]


PRONOUNS = {"he", "she", "his", "her", "hers", "him", "they", "them", "their", "it", "its"}


def pronoun_owner(r):
    """own-O0b bug found 2026-09-23: 9,903 binding rows store the pronoun itself as the owner."""
    if r.get("family") == "binding":
        return True  # whole family dropped: its pronoun labels rest on a gender guess (own-model thread, 11:0x UTC)
    t = r["turn"]
    return any(isinstance(f["owner"], list) and t[f["owner"][0]:f["owner"][1]].lower() in PRONOUNS
               for f in r["facts"])


def convert_o0b(r):
    t = r["turn"]
    facts = [{"owner": span(t, f["owner"]), "rel": f["relation"], "value": span(t, f["value_span"]),
              "mode": MODE[f["mode"]]} for f in r["facts"]]
    ask = None
    q = r.get("question")
    if q:
        ask = {"owner": span(t, q["owner_span"]), "rel": (q.get("relations") or ["other"])[0],
               "inverse": bool(q.get("inverse"))}
    return {"act": ACT[r["act"]], "facts": facts, "ask": ask}


def load_gz(paths):
    for p in paths:
        with gzip.open(p, "rt") as fh:
            for line in fh:
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--o0b", required=True)
    ap.add_argument("--opus", required=True)
    ap.add_argument("--agree", required=True, help="file with one agreed Opus row id per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-family", type=int, default=3000)
    ap.add_argument("--opus-repeat", type=int, default=4)
    ap.add_argument("--opus-dev-frac", type=float, default=0.1)
    ap.add_argument("--o0a2", help="dir with own-O0a2 turns.jsonl + gold.jsonl (fresh dev turns)")
    a = ap.parse_args()
    rng = random.Random(300)
    o0b = Path(a.o0b)
    by_fam = {}
    dropped = 0
    for r in load_gz(sorted(o0b.glob("train-*.jsonl.gz"))):
        if pronoun_owner(r):
            dropped += 1
            continue
        by_fam.setdefault(r["family"], []).append(r)
    train, dev = [], []
    for fam, rows in sorted(by_fam.items()):
        rng.shuffle(rows)
        for r in rows[: a.per_family]:
            train.append({"id": r["id"], "prompt": build_prompt(r["turn"], r["prev_reply"]),
                          "target": frame_text(convert_o0b(r)), "src": "o0b", "family": fam})
    for r in load_gz(sorted(o0b.glob("l2dev-*.jsonl.gz"))):
        if rng.random() < 0.1 and not pronoun_owner(r):
            dev.append({"id": r["id"], "prompt": build_prompt(r["turn"], r["prev_reply"]),
                        "target": frame_text(convert_o0b(r)), "src": "o0b_l2", "family": r["family"],
                        "turn": r["turn"], "prev_reply": r["prev_reply"], "frame": convert_o0b(r)})
    agree = set(Path(a.agree).read_text().split())
    opus = []
    for p in sorted(Path(a.opus).glob("opus_w*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r["id"] in agree:
                    opus.append(r)
    rng.shuffle(opus)
    ndev = int(len(opus) * a.opus_dev_frac)
    for i, r in enumerate(opus):
        row = {"id": r["id"], "prompt": build_prompt(r["turn"], r.get("prev_reply", "")),
               "target": frame_text(r["frame"]), "src": "opus", "family": r.get("family", "")}
        if i < ndev:
            dev.append(dict(row, src="opus_dev", turn=r["turn"], prev_reply=r.get("prev_reply", ""),
                            frame=r["frame"]))
        else:
            train.extend([row] * a.opus_repeat)
    if a.o0a2:
        d = Path(a.o0a2)
        turns = {r["id"]: r for r in map(json.loads, (d / "turns.jsonl").read_text().splitlines()) if r}
        for g in map(json.loads, (d / "gold.jsonl").read_text().splitlines()):
            t = turns[g["id"]]
            facts = [{"owner": {"ME": "me", "WE": "we"}.get(f["owner"], f["owner"]), "rel": f["relation"],
                      "value": f["value"], "mode": MODE.get(f["mode"], f["mode"])} for f in g["facts"]]
            fr = {"act": "STATE" if facts else "CHAT", "facts": facts, "ask": None}
            dev.append({"id": g["id"], "prompt": build_prompt(t["turn"], t.get("prev_reply", "")),
                        "target": frame_text(fr), "src": "o0a2", "family": "o0a2",
                        "turn": t["turn"], "prev_reply": t.get("prev_reply", ""), "frame": fr})
    rng.shuffle(train)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev)):
        with open(out / f"{name}.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"train": len(train), "dev": len(dev), "opus_agreed": len(opus), "o0b_pronoun_owner_dropped": dropped,
                      "train_src": Counter(r["src"] for r in train),
                      "dev_src": Counter(r["src"] for r in dev)}, indent=1))


if __name__ == "__main__":
    main()
