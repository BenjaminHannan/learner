#!/usr/bin/env python3
"""bm-397 F2: the blind semantic audit (benchmarks thread, 2026-09-26). Written before any finaliser output exists;
it implements artifacts/claude-bm397-20260926/PLAN.md's F2 as fixed there.

  prep:   python -B scripts/claude_bm397_judge.py prep --data DATA --drafts DRAFTS/locomo_T.jsonl \
              --finals RUN/locomo_TF.jsonl --work WORK
  score:  python -B scripts/claude_bm397_judge.py score --work WORK

prep draws the sample: 300 ids with random.Random(397).sample from the sorted category 1-4 ids whose final_kept is
"changed", or all of them if fewer. It writes judge batches to WORK/batches/ (question, gold answer, one reply; no
arm, no id that reveals the kind) and the private key to WORK/key.json. Main batches: group A holds the drafts of
the first half of the sample and the finals of the second half; group B the opposite; 50 items a batch, shuffled.
So no judge sees both replies of one question. Relabel batches: the first 30 sampled questions, both kinds (60
items), split the same way into two batches for two further judges. WORK holds benchmark text: keep it outside the
repository; only counts go in the repository.

Judges write WORK/labels/<batch>.jsonl lines {"item": "...", "label": "A|B|C|D|E"}.
- A = right and complete (extra words are fine);
- B = contains the right answer and also an incompatible alternative;
- C = partly right;
- D = wrong;
- E = says it doesn't know.
score prints counts only: the draft-by-final label table; lost (draft A becoming C, D or E); picked (draft B
becoming A); F2 = lost <= 3 and picked <= 3; and the agreement between the main labels and the relabels.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

SEED = 397
N = 300
BATCH = 50
LABELS = "ABCDE"


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _gold(qa: dict) -> str:
    g = str(qa["answer"])
    return g.split(";")[0].strip() if qa["category"] == 3 else g


def prep(a) -> None:
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    qs = {f"{c['sample_id']}#{i}": qa for c in lc for i, qa in enumerate(c["qa"])}
    drafts = {r["qid"]: r for r in _jsonl(Path(a.drafts))}
    finals = {r["qid"]: r for r in _jsonl(Path(a.finals))}
    ids = sorted(q for q, r in finals.items() if r.get("final_kept") == "changed" and r["category"] in (1, 2, 3, 4))
    sample = random.Random(SEED).sample(ids, N) if len(ids) > N else list(ids)
    rng = random.Random(SEED + 1)
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    key, counter = {}, [0]

    def item(qid: str, kind: str) -> dict:
        counter[0] += 1
        iid = f"i{counter[0]:04d}"
        key[iid] = {"qid": qid, "kind": kind}
        reply = (drafts if kind == "draft" else finals)[qid]["reply"]
        return {"item": iid, "question": qs[qid]["question"], "gold_answer": _gold(qs[qid]), "reply": reply}

    half = len(sample) // 2
    groups = {
        "A": [item(q, "draft") for q in sample[:half]] + [item(q, "final") for q in sample[half:]],
        "B": [item(q, "final") for q in sample[:half]] + [item(q, "draft") for q in sample[half:]],
    }
    first = sample[:30]
    groups["R1"] = [item(q, "draft") for q in first[:15]] + [item(q, "final") for q in first[15:]]
    groups["R2"] = [item(q, "final") for q in first[:15]] + [item(q, "draft") for q in first[15:]]
    batches = []
    for g, items in groups.items():
        rng.shuffle(items)
        size = BATCH if g in ("A", "B") else len(items)
        for k in range(0, len(items), size):
            name = f"{g}{k // size + 1:02d}"
            (work / "batches" / f"{name}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items[k:k + size]), encoding="utf-8")
            batches.append(name)
    (work / "key.json").write_text(json.dumps({"sample": sample, "items": key}), encoding="utf-8")
    print(json.dumps({"changed_ids": len(ids), "sampled": len(sample), "items": len(key), "batches": batches}))


def score(a) -> None:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    relabel: dict[str, str] = {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = relabel if f.stem.startswith("R") else labels
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in LABELS:
                raise SystemExit(f"bm397-judge: bad label in {f.name}")
            sink[r["item"]] = lab
    by_q: dict[str, dict] = {}
    for iid, lab in labels.items():
        m = k["items"][iid]
        by_q.setdefault(m["qid"], {})[m["kind"]] = lab
    missing = [q for q in k["sample"] if set(by_q.get(q, {})) != {"draft", "final"}]
    table = Counter((v["draft"], v["final"]) for q, v in by_q.items() if set(v) == {"draft", "final"})
    lost = sum(n for (d, f), n in table.items() if d == "A" and f in "CDE")
    picked = sum(n for (d, f), n in table.items() if d == "B" and f == "A")
    # agreement: a relabel item and the main label for the same question and kind
    main = {(k["items"][i]["qid"], k["items"][i]["kind"]): lab for i, lab in labels.items()}
    pairs = [(main.get((k["items"][i]["qid"], k["items"][i]["kind"])), lab) for i, lab in relabel.items()]
    pairs = [p for p in pairs if p[0] is not None]
    agree = sum(x == y for x, y in pairs)
    print(json.dumps({"sampled": len(k["sample"]), "judged_pairs": sum(table.values()), "missing": len(missing),
                      "draft_by_final": {f"{d}->{f}": n for (d, f), n in sorted(table.items())},
                      "draft_labels": dict(Counter(v["draft"] for v in by_q.values() if "draft" in v)),
                      "final_labels": dict(Counter(v["final"] for v in by_q.values() if "final" in v)),
                      "lost": lost, "picked": picked, "F2": "PASS" if (lost <= 3 and picked <= 3 and not missing)
                      else "FAIL", "relabel_agree": f"{agree}/{len(pairs)}"}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "score"])
    ap.add_argument("--data", default="")
    ap.add_argument("--drafts", default="")
    ap.add_argument("--finals", default="")
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    prep(a) if a.cmd == "prep" else score(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
