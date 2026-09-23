#!/usr/bin/env python3
"""own-M1 data: own-M0 rows -> {prompt, target} rows for claude_lis300_train.py.

M0 rows: {"record", "user_turn", "tag", "reply"} with the reply already slotted.
Every target is re-checked with claude_own_m1_common.slot_check; failures are dropped and counted.
Usage: python claude_own_m1_data.py --m0 <M0 artifacts dir> --out <dir>   (writes train.jsonl, dev.jsonl, counts.json)
"""
import argparse, collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_own_m1_common import build_prompt, slot_check  # noqa: E402


def rows(path):
    import gzip
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as fh:
        for l in fh:
            if l.strip():
                yield json.loads(l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m0", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m0, out = Path(a.m0), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in ("train", "dev"):
        files = sorted(m0.glob(f"{split}*.jsonl")) + sorted(m0.glob(f"{split}*.jsonl.gz"))
        if not files:
            sys.exit(f"no {split}*.jsonl in {m0}")
        kept, dropped, reasons = 0, 0, collections.Counter()
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as fh:
            for f in files:
                for r in rows(f):
                    probs = slot_check(r["reply"], r["record"])
                    if probs:
                        dropped += 1
                        reasons.update(p.split(":")[0] for p in probs)
                        continue
                    fh.write(json.dumps({"prompt": build_prompt(r["record"], r.get("user_turn", ""), r["tag"]),
                                         "target": r["reply"].strip() + "\n<END>",
                                         "record": r["record"], "user_turn": r.get("user_turn", ""),
                                         "tag": r["tag"]}, ensure_ascii=False) + "\n")
                    kept += 1
        counts[split] = {"kept": kept, "dropped": dropped, "reasons": dict(reasons)}
    (out / "counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
