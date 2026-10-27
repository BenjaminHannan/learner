#!/usr/bin/env python3
"""bm-398e X2, the blind check of the trimmer (benchmarks thread, 2026-09-26). Written and sealed before any
trimmed LoCoMo reply exists. Same sample, rubric and judge rules as bm-398d (its 297 questions with evidence;
judges see the question, the gold answer, the evidence lines with dates and one reply; artifacts/
claude-bm398d-20260926/INSTRUCTIONS.md), with two arms: T (the plain 1B's whole-chat reply, untouched) and TT (the
same reply after the trimmer).

  prep:  python -B scripts/claude_bm398e_judge.py prep --data DATA --t T.jsonl --tt TT.jsonl --work WORK
  score: python -B scripts/claude_bm398e_judge.py score --data DATA --work WORK
Groups: L0 holds T for even-numbered questions and TT for odd, L1 the opposite; 50-item batches, shuffled with
random.Random(3985). Relabel: X1 = the first 60 questions as L0 has them. One judge per batch set, never two arms of
one question; the relabel judge judges neither L0 nor L1. WORK holds benchmark text: keep it outside the repository.
score prints counts only: A-counts per arm, TT − T with a conversation bootstrap (seed 3986, 10,000), the T-by-TT
label table, relabel agreement, and X2 = TT A-count >= T A-count - 3.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402

ARMS = ["T", "TT"]
JUDGE_SEED, BOOT_SEED, BOOT_N, BATCH = 3985, 3986, 10000, 50


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def prep(a) -> int:
    import claude_bm397_judge as J
    kept, info = D.sample(Path(a.data))
    rep = {"T": {r["qid"]: r["reply"] for r in _jsonl(a.t)}, "TT": {r["qid"]: r["reply"] for r in _jsonl(a.tt)}}
    miss = {k: sum(q not in v for q in kept) for k, v in rep.items()}
    if any(miss.values()):
        raise SystemExit(f"bm398e judge prep: missing replies {miss}")
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    rng = random.Random(JUDGE_SEED)
    key, counter = {}, [0]

    def item(q: str, arm: str) -> dict:
        conv, i, qa, gold = info[q]
        items = D.items_of(conv)
        counter[0] += 1
        iid = f"e{counter[0]:05d}"
        key[iid] = {"qid": q, "arm": arm}
        ev = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
        return {"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": ev,
                "reply": rep[arm][q]}

    groups = {f"L{g}": [item(q, ARMS[(n + g) % 2]) for n, q in enumerate(kept)] for g in range(2)}
    groups["X1"] = [item(q, ARMS[n % 2]) for n, q in enumerate(kept[:60])]
    batches = []
    for g, its in groups.items():
        rng.shuffle(its)
        size = BATCH if g.startswith("L") else len(its)
        for k in range(0, len(its), size):
            name = f"{g}{k // size + 1:02d}"
            (work / "batches" / f"{name}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in its[k:k + size]), encoding="utf-8")
            batches.append(name)
    (work / "key.json").write_text(json.dumps({"kept": kept, "items": key}), encoding="utf-8")
    same = sum(rep["T"][q] == rep["TT"][q] for q in kept)
    print(json.dumps({"kept": len(kept), "items": len(key), "batches": batches, "tt_equals_t": same}))
    return 0


def score(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in "ABCDE":
                raise SystemExit(f"bm398e judge score: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    full = [q for q in k["kept"] if set(by[q]) == set(ARMS)]
    res = {"kept": len(k["kept"]), "fully_judged": len(full)}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "labels": dict(sorted(c.items()))}
    diff = {q: int(by[q]["TT"] == "A") - int(by[q]["T"] == "A") for q in full}
    conv = defaultdict(list)
    for q in full:
        conv[q.split("#")[0]].append(diff[q])
    cs = sorted(conv)
    rng = random.Random(BOOT_SEED)
    ds = sorted(100 * sum(v) / len(v) for v in
                ([x for c in (rng.choice(cs) for _ in cs) for x in conv[c]] for _ in range(BOOT_N)))
    res["TT-T"] = {"points": round(100 * sum(diff.values()) / max(1, len(full)), 1),
                   "ci95_by_conversation": [round(ds[int(0.025 * BOOT_N)], 1), round(ds[int(0.975 * BOOT_N) - 1], 1)],
                   "gained": sum(v > 0 for v in diff.values()), "lost": sum(v < 0 for v in diff.values())}
    res["table_T_to_TT"] = dict(sorted(Counter(f"{by[q]['T']}->{by[q]['TT']}" for q in full).items()))
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    res["X2"] = res["TT"]["A"] >= res["T"]["A"] - 3
    print(json.dumps(res))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "score"])
    for x in ("data", "t", "tt", "work"):
        ap.add_argument("--" + x, default="")
    a = ap.parse_args()
    return {"prep": prep, "score": score}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
