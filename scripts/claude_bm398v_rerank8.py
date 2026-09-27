#!/usr/bin/env python3
"""bm-398v: does the plain 1B's own reranking, with a wider cut, beat reading all 20 of the store's lines?
(benchmarks thread, 2026-09-27). Plan and marks: artifacts/claude-bm398v-20260927/PLAN.md. Follows bm-398u
(d8078eda4): the 1B's own ranking beat store B's order at 3 lines, but 3 lines lost to all 20. Here the cut is wider
(TOP_K, set by the PLAN's finding-only rule on conversations 0-4) and the claim is against all 20 lines, on LoCoMo
conversations 5-9, where no store-B, notes or reranker answer has been judged. Development measurement on LoCoMo
("after using LoCoMo for development"). Nothing is trained. No question, answer, turn or reply text is printed.

Arms (both answer from store B's lines on rd-378u's ranked_turns.jsonl, laid out and prompted as bm-398n did):
  BN  the 1B answers from store B's first 20 distinct turns, in chat order under their session dates.
  BU  the same 20 turns, scored by the same 1B as sum log P(question | turn) (bm-398u's UPR scorer, unchanged);
      only the TOP_K best (ties to store B's order) go to the 1B, in chat order.

  run      python -B scripts/claude_bm398v_rerank8.py run --data DATA --ranked RANKED --model DIR --out OUT [--limit N]
           (the real run refuses any ranked file but rd-378u's; --dev takes rd-378L's file, conversations 0-4,
           for a smoke that never touches conversations 5-9)
  score    python -B scripts/claude_bm398v_rerank8.py score --data DATA --ranked RANKED --runs OUT --out S
  prep     python -B scripts/claude_bm398v_rerank8.py prep --data DATA --ranked RANKED --runs OUT --work W
  jscore   python -B scripts/claude_bm398v_rerank8.py jscore --data DATA --ranked RANKED --work W
  selftest python -B scripts/claude_bm398v_rerank8.py selftest
WORK and OUT hold benchmark text: keep them outside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402
import claude_bm398n_notes as N  # noqa: E402
import claude_bm398u_rerank as U  # noqa: E402

RANKED_SHA = "785c9c9adf26071b83716d53465c03663e96f99a517348f4a98f03b792d9ff5e"   # rd-378u, conversations 5-9
DEV_SHA = N.RANKED_SHA                                                             # rd-378L, conversations 0-4
ARMS = ["BN", "BU"]
N_QUESTIONS, TURNS = 772, 20
K_CHOICES, K_SHARE = (5, 8, 10), 0.90
TOP_K = 8                         # set by the PLAN's rule (K_CHOICES, K_SHARE) on bm-398u's saved scores, 0-4 only
JUDGE_SEED, BATCH, X1_N = 3999, 50, 60
W1_MIN_GAIN, W1_MAX_P, W2_MAX_EXTRA_D, W3_MAX_CAT_DROP = 15, 0.05, 8, 3


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def ranked(path: str, dev: bool = False) -> tuple[list[str], dict]:
    """(qids in file order, {(qid, store): turns}); refuses any file but the pinned one."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != (DEV_SHA if dev else RANKED_SHA):
        raise SystemExit("bm398v: ranked_turns.jsonl is not the pinned file")
    qids, rt = [], {}
    for r in _jsonl(path):
        if r["qid"] not in qids:
            qids.append(r["qid"])
        rt[(r["qid"], r["arm"])] = list(r["turns"])
    return qids, rt


def check(qids: list[str], rt: dict, info: dict, n_expected: int = N_QUESTIONS) -> None:
    if len(qids) != n_expected:
        raise SystemExit(f"bm398v: expected {n_expected} questions")
    for q in qids:
        conv, _i, qa, gold = info[q]
        n = len(D.items_of(conv))
        t = rt[(q, "B")]
        if qa["category"] not in (1, 2, 3, 4) or not gold:
            raise SystemExit("bm398v: a question outside categories 1-4 or without evidence")
        if len(t) != TURNS or len(set(t)) != TURNS or not all(0 <= p < n for p in t):
            raise SystemExit("bm398v: bad turn list")


def pick_k(rows: dict, info: dict, qids: list[str]) -> dict:
    """The PLAN's rule, on bm-398u's saved scores (conversations 0-4): the smallest k in K_CHOICES whose reranked
    any@k is at least K_SHARE of any@20."""
    full = sum(bool(set(info[q][3]) & set(rows[q]["pool"])) for q in qids)
    got = {k: sum(bool(set(info[q][3]) & set(U.top(rows[q]["pool"], rows[q]["scores"], k))) for q in qids)
           for k in K_CHOICES}
    k = next((k for k in K_CHOICES if got[k] >= K_SHARE * full), max(K_CHOICES))
    return {"any_at_20": full, "any_at_k": got, "top_k": k}


def run(a) -> int:
    dev = bool(a.dev)
    qids, rt = ranked(a.ranked, dev)
    _kept, info = D.sample(Path(a.data))
    check(qids, rt, info, 759 if dev else N_QUESTIONS)
    if a.limit:
        qids = qids[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fh = {arm: (out / f"locomo_{arm}.jsonl").open("w", encoding="utf-8") for arm in ARMS}
    t_all = time.time()
    for n, q in enumerate(qids):
        conv, i, qa, _gold = info[q]
        items = D.items_of(conv)
        pool = rt[(q, "B")]
        t0 = time.time()
        sc = U.upr_scores(a.model, qa["question"], [U.passage(items, p) for p in pool])
        rank_ms = round((time.time() - t0) * 1000, 1)
        for arm, keep in (("BN", pool), ("BU", U.top(pool, sc, TOP_K))):
            t1 = time.time()
            user = D.context(conv, items, keep) + "\n\n" + B.QA_PROMPT.format(B.question_text(conv["sample_id"], i, qa))
            reply, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
            row = {"qid": q, "category": qa["category"], "reply": reply, "turns": keep,
                   "ms": round((time.time() - t1) * 1000, 1), "prompt_tokens": ntok}
            if arm == "BU":
                row |= {"pool": pool, "scores": sc, "rank_ms": rank_ms}
            fh[arm].write(json.dumps(row, ensure_ascii=False) + "\n")
            fh[arm].flush()
        if (n + 1) % 25 == 0:
            print(f"[bm398v] {n + 1}/{len(qids)} seconds={time.time() - t_all:.0f}", flush=True)
    for arm in ARMS:
        fh[arm].close()
        f = out / f"locomo_{arm}.jsonl"
        print(f"wrote locomo_{arm}.jsonl rows={len(_jsonl(f))} sha256={hashlib.sha256(f.read_bytes()).hexdigest()}",
              flush=True)
    print(json.dumps({"questions": len(qids), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def _replies(a, qids, rt) -> dict:
    out = {arm: {r["qid"]: r for r in _jsonl(Path(a.runs) / f"locomo_{arm}.jsonl")} for arm in ARMS}
    for arm in ARMS:
        if sorted(out[arm]) != sorted(qids):
            raise SystemExit(f"bm398v: {arm} does not cover the {N_QUESTIONS}")
    for q in qids:
        pool = rt[(q, "B")]
        if out["BN"][q]["turns"] != pool or out["BU"][q]["pool"] != pool:
            raise SystemExit("bm398v: BN is not store B's 20")
        if out["BU"][q]["turns"] != U.top(pool, out["BU"][q]["scores"], TOP_K):
            raise SystemExit("bm398v: BU is not the reranked top TOP_K")
    return out


def finding_split(info: dict, qids: list[str], rep: dict) -> dict:
    """Pre-registered report-only split: did an evidence turn reach BU's lines, or only BN's 20?"""
    return {q: ("both" if set(info[q][3]) & set(rep["BU"][q]["turns"]) else
                "BN only" if set(info[q][3]) & set(rep["BN"][q]["turns"]) else "neither") for q in qids}


def score(a) -> int:
    import claude_bm390_score as SC
    qids, rt = ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    rep = _replies(a, qids, rt)
    res = {"n": len(qids), "top_k": TOP_K}
    for arm in ARMS:
        s = SC.score_locomo(Path(a.data), [rep[arm][q] for q in qids])["summary"]
        res[arm] = {k: s[k] for k in ("cat1to4_n", "cat1to4_f1", "cat1to4_abstain", "cat1to4_confident_wrong",
                                      "cat1to4_half_right", "cat1_f1", "cat2_f1", "cat3_f1", "cat4_f1")}
        res[arm]["evidence_in_lines"] = [sum(bool(set(info[q][3]) & set(rep[arm][q]["turns"])) for q in qids),
                                         sum(set(info[q][3]) <= set(rep[arm][q]["turns"]) for q in qids)]
    res["BU_minus_BN_f1"] = round(res["BU"]["cat1to4_f1"] - res["BN"]["cat1to4_f1"], 2)
    res["split_counts"] = dict(Counter(finding_split(info, qids, rep).values()))
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return 0


def latin(qids: list[str], rng: random.Random) -> dict[str, list[tuple[str, str]]]:
    groups = {f"L{g}": [(q, ARMS[(n + g) % 2]) for n, q in enumerate(qids)] for g in range(2)}
    groups["X1"] = [(q, ARMS[n % 2]) for n, q in enumerate(qids[:X1_N])]
    for g in groups:
        rng.shuffle(groups[g])
    return groups


def prep(a) -> int:
    import claude_bm397_judge as J
    qids, rt = ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    rep = _replies(a, qids, rt)
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    key, batches, counter = {}, [], 0
    for g, pairs in latin(qids, random.Random(JUDGE_SEED)).items():
        its = []
        for q, arm in pairs:
            conv, _i, qa, gold = info[q]
            items = D.items_of(conv)
            counter += 1
            iid = f"v{counter:05d}"
            key[iid] = {"qid": q, "arm": arm}
            evid = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
            its.append({"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": evid,
                        "reply": rep[arm][q]["reply"]})
        size = BATCH if g.startswith("L") else len(its)
        for k in range(0, len(its), size):
            name = f"{g}{k // size + 1:02d}"
            (work / "batches" / f"{name}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in its[k:k + size]), encoding="utf-8")
            batches.append(name)
    same = [q for q in qids if rep["BN"][q]["reply"] == rep["BU"][q]["reply"]]
    split = finding_split(info, qids, rep)
    (work / "key.json").write_text(json.dumps({"qids": qids, "items": key, "same": same, "split": split}),
                                   encoding="utf-8")
    print(json.dumps({"questions": len(qids), "items": len(key), "batches": batches, "identical": len(same)}))
    return 0


def verdict(by: dict, qids: list[str], cats: dict, same: set, split: dict) -> dict:
    """same = questions whose BN and BU replies are byte-identical: one answer, so both arms take group L0's label
    (the arm L0 holds, ARMS[n % 2]) and the question is a tie; how often the two judges agreed is reported."""
    full = [q for q in qids if set(by[q]) == set(ARMS)]
    agree = sum(by[q]["BN"] == by[q]["BU"] for q in full if q in same)
    pos = {q: n for n, q in enumerate(qids)}
    by = {q: ({arm: by[q][ARMS[pos[q] % 2]] for arm in ARMS} if q in same and q in full else by[q]) for q in by}
    res = {"questions": len(qids), "fully_judged": len(full), "identical_replies": sum(q in same for q in full),
           "identical_replies_judges_agree": agree}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "D": c["D"], "E": c["E"], "labels": dict(sorted(c.items()))}
    diff = {q: int(by[q]["BU"] == "A") - int(by[q]["BN"] == "A") for q in full}
    g, lo = sum(v > 0 for v in diff.values()), sum(v < 0 for v in diff.values())
    res["BU-BN"] = {"A": res["BU"]["A"] - res["BN"]["A"], "gained": g, "lost": lo,
                    "mcnemar_p": round(N.mcnemar_p(g, lo), 5),
                    "ci95_by_conversation_report_only": N._boot(full, diff) if full else None}
    res["A_by_category"] = {str(c): {arm: sum(by[q][arm] == "A" for q in full if cats[q] == c) for arm in ARMS} | {
        "n": sum(cats[q] == c for q in full)} for c in (1, 2, 3, 4)}
    res["split_report_only"] = {s: {"n": sum(split[q] == s for q in full)} | {
        arm: sum(by[q][arm] == "A" for q in full if split[q] == s) for arm in ARMS} for s in ("both", "BN only", "neither")}
    res["W1"] = res["BU-BN"]["A"] >= W1_MIN_GAIN and res["BU-BN"]["mcnemar_p"] < W1_MAX_P and g > lo
    res["W2"] = res["BU"]["D"] <= res["BN"]["D"] + W2_MAX_EXTRA_D
    res["W3"] = all(v["BN"] - v["BU"] <= max(W3_MAX_CAT_DROP, round(W3_MAX_CAT_DROP * v["n"] / 100))
                    for v in res["A_by_category"].values())
    res["proved_wrong"] = res["BU-BN"]["A"] <= 0
    res["verdict"] = "PASS" if res["W1"] and res["W2"] and res["W3"] else "FAIL"
    res["table_BN_to_BU"] = dict(sorted(Counter(f"{by[q]['BN']}->{by[q]['BU']}" for q in full).items()))
    return res


def jscore(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if not lab or lab not in "ABCDE":
                raise SystemExit(f"bm398v jscore: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    _kept, info = D.sample(Path(a.data))
    res = verdict(by, k["qids"], {q: info[q][2]["category"] for q in k["qids"]}, set(k["same"]), k["split"])
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    print(json.dumps(res))
    return 0


def kcheck(a) -> int:
    """Re-derive TOP_K from bm-398u's saved BU rows (conversations 0-4 only). Prints counts."""
    qids, _rt = N.ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    rows = {r["qid"]: r for r in _jsonl(Path(a.runs) / "locomo_BU.jsonl")}
    res = pick_k(rows, info, qids)
    res["matches_TOP_K"] = res["top_k"] == TOP_K
    print(json.dumps(res))
    return 0 if res["matches_TOP_K"] else 1


def selftest(a) -> int:
    ok = {}
    qids = [f"conv-{c}#{i}" for c in (1, 2, 3) for i in range(40)]
    groups = latin(qids, random.Random(JUDGE_SEED))
    ok["each group holds every question once, arms balanced"] = all(
        sorted(q for q, _ in groups[g]) == sorted(qids) and Counter(x for _, x in groups[g]) == Counter(
            {"BN": 60, "BU": 60}) for g in ("L0", "L1"))
    ok["a question's two arms are in different groups"] = all(
        dict(groups["L0"])[q] != dict(groups["L1"])[q] for q in qids)
    ok["X1 is L0's first 60 questions, same arms"] = sorted(groups["X1"]) == sorted(
        (q, ARMS[n % 2]) for n, q in enumerate(qids[:X1_N]))
    cats = {q: 1 + (n % 4) for n, q in enumerate(qids)}
    split = {q: "both" for q in qids}
    good = {q: {"BN": "D" if n % 5 == 0 else "A", "BU": "A"} for n, q in enumerate(qids)}
    v1 = verdict(good, qids, cats, set(), split)
    ok["a clear gain passes"] = v1["verdict"] == "PASS" and v1["BU-BN"]["A"] == 24 and not v1["proved_wrong"]
    v2 = verdict({q: {"BN": "A", "BU": "A"} for q in qids}, qids, cats, set(), split)
    ok["no gain fails and is proved wrong"] = v2["verdict"] == "FAIL" and v2["proved_wrong"]
    wrong = {q: {"BN": "E" if n % 3 else "A", "BU": "A" if n % 3 else "D"} for n, q in enumerate(qids)}
    v3 = verdict(wrong, qids, cats, set(), split)
    ok["more wrong answers fail W2"] = v3["W1"] and not v3["W2"] and v3["verdict"] == "FAIL"
    drop = {q: {"BN": "A" if cats[q] == 3 else "D", "BU": "D" if cats[q] == 3 else "A"} for q in qids}
    v4 = verdict(drop, qids, cats, set(), split)
    ok["a category drop fails W3"] = v4["W1"] and not v4["W3"] and v4["verdict"] == "FAIL"
    alt = {q: ({"BN": "A", "BU": "D"} if n % 2 else {"BN": "D", "BU": "A"}) for n, q in enumerate(qids)}
    v5 = verdict(alt, qids, cats, set(qids), split)
    want = sum(alt[q][ARMS[n % 2]] == "A" for n, q in enumerate(qids))
    ok["identical replies are ties with L0's label"] = (v5["BU-BN"]["gained"] == 0 and v5["BU-BN"]["lost"] == 0
                                                       and v5["BU"]["A"] == v5["BN"]["A"] == want)
    ok["top keeps the best k, ties to the store's order"] = U.top([7, 3, 9, 1, 5], [-1, -5, -1, -9, -2], 2) == [7, 9]
    info = {q: (None, 0, {"category": 1}, [n % 20]) for n, q in enumerate(qids)}
    rows = {q: {"pool": list(range(20)), "scores": [-(abs(p - n % 20)) for p in range(20)]} for n, q in enumerate(qids)}
    ok["pick_k takes the smallest k that keeps K_SHARE of the finds"] = pick_k(rows, info, qids)["top_k"] == 5
    rep = {"BN": {q: {"turns": list(range(20))} for q in qids},
           "BU": {q: {"turns": [0, 1]} for q in qids}}
    fs = finding_split({q: (None, 0, {}, [n % 3]) for n, q in enumerate(qids)}, qids, rep)
    ok["finding split: both when BU holds evidence, else BN only"] = Counter(fs.values()) == Counter(
        {"both": 80, "BN only": 40})
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398V-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "prep", "jscore", "kcheck", "selftest"])
    for x in ("data", "ranked", "model", "out", "runs", "work"):
        ap.add_argument("--" + x, default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    return {"run": run, "score": score, "prep": prep, "jscore": jscore, "kcheck": kcheck,
            "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
