#!/usr/bin/env python3
"""rd-378 note-writer training rows from Opus-written dialogs (notes_w*.jsonl) and a judge's verdicts (judge_w*.jsonl).

A non-assistant turn becomes a row only when every note on it was judged "ok" and the judge found nothing missed
(missed == 0); other turns are dropped (never trained on) but still appear as earlier context for later turns.
10% of dialogs (by id hash) go to dev; their turns (no notes) are also written to dev_dialogs.jsonl. Rows: {"id","prompt","target","src","family"} (+ dev rows keep "notes","kind").
No DEV bank, panel, bank A/B, LoCoMo or LongMemEval text: the dialogs are written from scratch.
python claude_rd378_data.py --notes DIR --out OUT [--repeat 3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378_common import build_nprompt, notes_text  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeat", type=int, default=3)
    a = ap.parse_args()
    c = Counter()
    train, dev, dev_dialogs = [], [], []
    for p in sorted(Path(a.notes).glob("notes_w*.jsonl")):
        jp = p.with_name(p.name.replace("notes_", "judge_"))
        judge = {}
        for line in jp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                j = json.loads(line)
                judge[(j["dialog"], int(j["t"]))] = j
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            is_dev = int(hashlib.sha256(d["dialog"].encode()).hexdigest(), 16) % 10 == 0
            if is_dev:
                dev_dialogs.append({k: v for k, v in d.items() if k != "turns"} |
                                   {"turns": [{kk: vv for kk, vv in t.items() if kk != "notes"} for t in d["turns"]]})
            turns = d["turns"]
            for k, t in enumerate(turns):
                if d["kind"] == "chat" and t["speaker"] == "assistant":
                    continue
                c["turns"] += 1
                j = judge.get((d["dialog"], int(t["t"])))
                notes = t.get("notes") or []
                if j is None:
                    c["no_verdict"] += 1
                    continue
                if any(v != "ok" for v in j["verdicts"]) or j.get("missed", 0) or len(j["verdicts"]) != len(notes):
                    c["dropped"] += 1
                    continue
                row = {"id": f"{d['dialog']}-t{t['t']}", "src": "notes378_dev" if is_dev else "notes378",
                       "family": d["kind"] + (":empty" if not notes else ""),
                       "prompt": build_nprompt(d["kind"], d.get("date", ""), turns[:k], t),
                       "target": notes_text(notes)}
                if is_dev:
                    dev.append(dict(row, notes=notes, kind=d["kind"]))
                else:
                    train += [row] * a.repeat
                c["kept_dev" if is_dev else "kept_train"] += 1
                c["notes_kept"] += len(notes)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "dev_dialogs.jsonl", "w", encoding="utf-8") as fh:  # dev dialogs without notes, for the writer CLI
        for d in dev_dialogs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    c["train_rows"], c["dev_rows"], c["dev_dialogs"] = len(train), len(dev), len(dev_dialogs)
    print(json.dumps(dict(sorted(c.items())), indent=1))


if __name__ == "__main__":
    main()
