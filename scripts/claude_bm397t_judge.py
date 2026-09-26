#!/usr/bin/env python3
"""bm-397t A3: blind correctness check of the trained 1B (TS) against the plain 1B (T) on LoCoMo (benchmarks thread,
2026-09-26). Written before any TS output exists. Same design as bm-397's F2 (scripts/claude_bm397_judge.py) except
the sample: 300 ids drawn with random.Random(3972).sample from ALL sorted category 1-4 ids (not only changed ones).

  prep:   python -B scripts/claude_bm397t_judge.py prep --data DATA --t RUN/locomo_T.jsonl --ts RUN/locomo_TS.jsonl --work WORK
  score:  python -B scripts/claude_bm397t_judge.py score --work WORK

Group A holds T's replies for the first 150 sampled questions and TS's for the other 150; group B the opposite; 50
items a batch, shuffled; no judge sees both replies to one question. Relabel batches: the first 30 sampled
questions, both arms (60 items), for two further judges. Labels A-E as in bm-397. WORK holds benchmark text: keep it
outside the repository. score prints counts only: A-count for T and TS, the T-by-TS label table, and A3 = TS's
A-count >= T's A-count - 3.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm397_judge as J  # noqa: E402

SEED = 3972
N = 300


def prep(a) -> None:
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    qs = {f"{c['sample_id']}#{i}": qa for c in lc for i, qa in enumerate(c["qa"])}
    arms = {"T": {r["qid"]: r for r in J._jsonl(Path(a.t))}, "TS": {r["qid"]: r for r in J._jsonl(Path(a.ts))}}
    ids = sorted(q for q, qa in qs.items() if qa["category"] in (1, 2, 3, 4) and q in arms["T"] and q in arms["TS"])
    sample = random.Random(SEED).sample(ids, N)
    rng = random.Random(SEED + 1)
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    key, counter = {}, [0]

    def item(qid: str, arm: str) -> dict:
        counter[0] += 1
        iid = f"i{counter[0]:04d}"
        key[iid] = {"qid": qid, "arm": arm}
        return {"item": iid, "question": qs[qid]["question"], "gold_answer": J._gold(qs[qid]),
                "reply": arms[arm][qid]["reply"]}

    half = N // 2
    groups = {"A": [item(q, "T") for q in sample[:half]] + [item(q, "TS") for q in sample[half:]],
              "B": [item(q, "TS") for q in sample[:half]] + [item(q, "T") for q in sample[half:]]}
    first = sample[:30]
    groups["R1"] = [item(q, "T") for q in first[:15]] + [item(q, "TS") for q in first[15:]]
    groups["R2"] = [item(q, "TS") for q in first[:15]] + [item(q, "T") for q in first[15:]]
    batches = []
    for g, items in groups.items():
        rng.shuffle(items)
        size = J.BATCH if g in ("A", "B") else len(items)
        for k in range(0, len(items), size):
            name = f"{g}{k // size + 1:02d}"
            (work / "batches" / f"{name}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items[k:k + size]), encoding="utf-8")
            batches.append(name)
    (work / "key.json").write_text(json.dumps({"sample": sample, "items": key}), encoding="utf-8")
    print(json.dumps({"eligible": len(ids), "sampled": len(sample), "items": len(key), "batches": batches}))


def score(a) -> None:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("R") else main
        for r in J._jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in J.LABELS:
                raise SystemExit(f"bm397t-judge: bad label in {f.name}")
            sink[r["item"]] = lab
    by_q: dict = {}
    for iid, lab in main.items():
        m = k["items"][iid]
        by_q.setdefault(m["qid"], {})[m["arm"]] = lab
    both = {q: v for q, v in by_q.items() if set(v) == {"T", "TS"}}
    missing = len(k["sample"]) - len(both)
    t_a = sum(v["T"] == "A" for v in both.values())
    ts_a = sum(v["TS"] == "A" for v in both.values())
    table = Counter(f"{v['T']}->{v['TS']}" for v in both.values())
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pairs = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pairs = [p for p in pairs if p[0] is not None]
    print(json.dumps({"sampled": len(k["sample"]), "judged_pairs": len(both), "missing": missing,
                      "T_labels": dict(Counter(v["T"] for v in both.values())),
                      "TS_labels": dict(Counter(v["TS"] for v in both.values())),
                      "T_A": t_a, "TS_A": ts_a, "T_by_TS": dict(sorted(table.items())),
                      "A3": "PASS" if (ts_a >= t_a - 3 and missing == 0) else "FAIL",
                      "relabel_agree": f"{sum(x == y for x, y in pairs)}/{len(pairs)}"}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "score"])
    ap.add_argument("--data", default="")
    ap.add_argument("--t", default="")
    ap.add_argument("--ts", default="")
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    prep(a) if a.cmd == "prep" else score(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
