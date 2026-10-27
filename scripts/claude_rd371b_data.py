#!/usr/bin/env python3
"""rd-371b: checker training rows from judged note drafts (graded own drafts) plus code-made perturbations.

python claude_rd371b_data.py --pair JUDGE_IN.jsonl:JUDGE_OUT.jsonl [--pair ...] --out DIR [--dev-frac 0.1]
JUDGE_IN rows = dialogs whose non-assistant turns carry "notes" (the union of a turn's distinct drafts);
JUDGE_OUT rows {"dialog","t","verdicts":[...]} (brief artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md).
Labels: ok, bad_cite -> yes; unsupported, bad_when -> no; bad_form skipped. Perturbations of "ok" notes (a name from
the window swapped in, or a number changed) -> no, at most as many as the real "no" rows. Split by dialog. Counts only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd371b_common import build_sprompt, windows  # noqa: E402

LAB = {"ok": "yes", "bad_cite": "yes", "unsupported": "no", "bad_when": "no"}
CAP = re.compile(r"\b[A-Z][a-z]{2,}\b")
NUM = re.compile(r"\b\d+\b")
STOP = {"The", "User", "Assistant", "She", "He", "They", "This", "That", "On", "In", "At", "January", "February",
        "March", "April", "May", "June", "July", "August", "September", "October", "November", "December", "Monday",
        "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def perturb(text, window_text, rng):
    names = [n for n in dict.fromkeys(CAP.findall(window_text)) if n not in STOP]
    inn = [n for n in names if re.search(rf"\b{n}\b", text)]
    out_ = [n for n in names if n not in inn]
    opts = []
    if inn and out_:
        a, b = rng.choice(inn), rng.choice(out_)
        opts.append(("name", re.sub(rf"\b{a}\b", b, text)))
    nums = NUM.findall(text)
    if nums:
        a = rng.choice(nums)
        b = str(int(a) + rng.randint(1, 9))
        if b not in window_text:
            opts.append(("number", re.sub(rf"\b{a}\b", b, text, count=1)))
    return rng.choice(opts) if opts else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=371)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    real, oks = [], []
    c = Counter()
    for pair in a.pair:
        jin, jout = pair.split(":")
        V = {(r["dialog"], int(r["t"])): r["verdicts"] for r in load(jout)}
        for d in load(jin):
            for t, earlier, latest in windows(d):
                vs = V.get((d["dialog"], t))
                notes = latest.get("notes") or []
                if vs is None or len(vs) != len(notes):
                    c["turns_unmatched"] += 1
                    continue
                win = " ".join(x["text"] for x in earlier[-6:] + [latest])
                for n, v in zip(notes, vs):
                    c["v:" + v] += 1
                    if v not in LAB:
                        continue
                    row = {"dialog": d["dialog"], "prompt": build_sprompt(d["kind"], d.get("date", ""), earlier, latest,
                                                                         n["text"]), "target": LAB[v], "family": v}
                    real.append(row)
                    if v == "ok":
                        oks.append((d, earlier, latest, n["text"], win))
    n_no = sum(r["target"] == "no" for r in real)
    rng.shuffle(oks)
    pert = []
    for d, earlier, latest, text, win in oks:
        if len(pert) >= n_no:
            break
        p = perturb(text, win, rng)
        if p:
            pert.append({"dialog": d["dialog"], "prompt": build_sprompt(d["kind"], d.get("date", ""), earlier, latest,
                                                                       p[1]), "target": "no", "family": "pert_" + p[0]})
    rows = real + pert
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tr, dv = [], []
    for i, r in enumerate(rows):
        r["id"] = f"c371b-{i:06d}"
        h = int(hashlib.sha256(r["dialog"].encode()).hexdigest(), 16) % 1000
        (dv if h < a.dev_frac * 1000 else tr).append(r)
    rng.shuffle(tr)
    for name, rs in (("train", tr), ("dev", dv)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    rep = {"train": len(tr), "dev": len(dv), "yes": sum(r["target"] == "yes" for r in rows),
           "no": sum(r["target"] == "no" for r in rows), "by_family": dict(Counter(r["family"] for r in rows)),
           "verdicts": {k[2:]: v for k, v in c.items() if k.startswith("v:")}, "turns_unmatched": c["turns_unmatched"]}
    (out / "summary.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
