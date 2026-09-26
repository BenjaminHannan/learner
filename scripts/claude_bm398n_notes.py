#!/usr/bin/env python3
"""bm-398n: do the reader's notes give more right answers? (benchmarks thread, 2026-09-26). The answer-level
follow-up agreed at 12:50 UTC with the notes thread, registered only because rd-378L's L1 passed (blind recount
274fae558). Plan and marks: artifacts/claude-bm398n-20260926/PLAN.md. Development measurement on LoCoMo ("after using
LoCoMo for development"); nothing is trained. No question, answer, turn or reply text is printed: counts only.

rd-378L's ranked_turns.jsonl gives, for each of its 759 questions (LoCoMo conversations 0-4, categories 1-4, with
evidence) and each store (A = heard turns only, B = heard turns plus the reader's notes, each note pointing to the
turns it cites), the first 20 distinct turn positions in fused rank order, numbered as bm-395 numbered them.

  run     the plain 1B answers each question twice: from store A's 20 turns (arm AN) and store B's (arm BN), laid
          out exactly as bm-398d laid out its store arms (claude_bm398d_evidence.context: the chat's opening line,
          then the turns in chat order under their session dates), bm-390's system, QA prompt and 50 new tokens.
          Rows are written as they finish.
            python -B scripts/claude_bm398n_notes.py run --data DATA --ranked RANKED --model DIR --out OUT [--limit N]
  score   F1 with the sealed bm-390 scorer on the 759, abstentions, and evidence found in the 20 turns (report only).
            python -B scripts/claude_bm398n_notes.py score --data DATA --ranked RANKED --runs OUT --out score.json
  prep    the blind check with bm-398d's rubric (judges see the evidence lines). Latin square: group L<g> holds arm
          ARMS[(n + g) % 2] of question n, so each group has every question once; 50-item batches shuffled with
          random.Random(3995). X1 = the first 60 questions as L0 has them, for a relabel judge who judges no group.
            python -B scripts/claude_bm398n_notes.py prep --data DATA --runs OUT --work WORK
  jscore  A-counts, BN - AN, gained and lost, McNemar's exact test on them, the conversation bootstrap (report
          only: there are only 5 conversations), A by category, the AN-by-BN label table, relabel agreement, and the
          marks N1, N2, proved wrong. Questions whose two replies are byte-identical count as ties.
            python -B scripts/claude_bm398n_notes.py jscore --data DATA --work WORK [--score score.json]
  selftest
WORK and OUT hold benchmark text: keep them outside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402

RANKED_SHA = "2792906c947485d6042cbc37a8e84c4987094c4f3b3c94c3298934a2154d97d4"
ARMS = ["AN", "BN"]
STORE = {"AN": "A", "BN": "B"}
N_QUESTIONS, TURNS = 759, 20
JUDGE_SEED, BOOT_SEED, BOOT_N, BATCH, X1_N = 3995, 3995, 10000, 50, 60
N1_MIN_GAIN, N1_MAX_P, N2_MAX_CAT_DROP = 15, 0.05, 3


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def ranked(path: str) -> tuple[list[str], dict]:
    """(qids in file order, {(qid, store): turns}); refuses a file that is not the sealed one."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != RANKED_SHA:
        raise SystemExit("bm398n: ranked_turns.jsonl is not the pinned file")
    qids, rt = [], {}
    for r in _jsonl(path):
        if r["qid"] not in qids:
            qids.append(r["qid"])
        rt[(r["qid"], r["arm"])] = list(r["turns"])
    return qids, rt


def check(qids: list[str], rt: dict, info: dict) -> None:
    if len(qids) != N_QUESTIONS or len(rt) != 2 * N_QUESTIONS:
        raise SystemExit("bm398n: expected 759 questions with stores A and B")
    for q in qids:
        conv, _i, qa, gold = info[q]
        n = len(D.items_of(conv))
        if qa["category"] not in (1, 2, 3, 4) or not gold:
            raise SystemExit("bm398n: a question outside categories 1-4 or without evidence")
        for s in ("A", "B"):
            t = rt[(q, s)]
            if len(t) != len(set(t)) or len(t) > TURNS or not all(0 <= p < n for p in t):
                raise SystemExit("bm398n: bad turn list")


def run(a) -> int:
    qids, rt = ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    check(qids, rt, info)
    if a.limit:
        qids = qids[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fh = {arm: (out / f"locomo_{arm}.jsonl").open("w", encoding="utf-8") for arm in ARMS}
    t_all = time.time()
    for n, q in enumerate(qids):
        conv, i, qa, _gold = info[q]
        items = D.items_of(conv)
        qtext = B.question_text(conv["sample_id"], i, qa)
        for arm in ARMS:
            ps = rt[(q, STORE[arm])]
            t0 = time.time()
            user = D.context(conv, items, ps) + "\n\n" + B.QA_PROMPT.format(qtext)
            reply, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
            fh[arm].write(json.dumps({"qid": q, "category": qa["category"], "reply": reply,
                                      "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": ntok,
                                      "turns": ps}, ensure_ascii=False) + "\n")
            fh[arm].flush()
        if (n + 1) % 25 == 0:
            print(f"[bm398n] {n + 1}/{len(qids)} seconds={time.time() - t_all:.0f}", flush=True)
    for arm in ARMS:
        fh[arm].close()
        f = out / f"locomo_{arm}.jsonl"
        print(f"wrote locomo_{arm}.jsonl rows={len(_jsonl(f))} sha256={hashlib.sha256(f.read_bytes()).hexdigest()}",
              flush=True)
    print(json.dumps({"questions": len(qids), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def score(a) -> int:
    import claude_bm390_score as SC
    qids, rt = ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    res = {"n": len(qids)}
    for arm in ARMS:
        rows = _jsonl(Path(a.runs) / f"locomo_{arm}.jsonl")
        if sorted(r["qid"] for r in rows) != sorted(qids):
            raise SystemExit(f"bm398n score: {arm} does not cover the 759")
        s = SC.score_locomo(Path(a.data), rows)["summary"]
        res[arm] = {k: s[k] for k in ("cat1to4_n", "cat1to4_f1", "cat1to4_abstain", "cat1to4_confident_wrong",
                                      "cat1to4_half_right", "cat1_f1", "cat2_f1", "cat3_f1", "cat4_f1")}
        res[arm]["evidence_in_turns"] = sum(bool(set(info[q][3]) & set(rt[(q, STORE[arm])])) for q in qids)
        res[arm]["all_evidence_in_turns"] = sum(set(info[q][3]) <= set(rt[(q, STORE[arm])]) for q in qids)
    res["BN_minus_AN_f1"] = round(res["BN"]["cat1to4_f1"] - res["AN"]["cat1to4_f1"], 2)
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
    _kept, info = D.sample(Path(a.data))
    rep = {arm: {r["qid"]: r["reply"] for r in _jsonl(Path(a.runs) / f"locomo_{arm}.jsonl")} for arm in ARMS}
    qids = [r["qid"] for r in _jsonl(Path(a.runs) / "locomo_AN.jsonl")]
    if len(qids) != N_QUESTIONS or any(q not in rep["BN"] for q in qids):
        raise SystemExit("bm398n prep: replies do not cover the 759 in both arms")
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
            iid = f"n{counter:05d}"
            key[iid] = {"qid": q, "arm": arm}
            ev = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
            its.append({"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": ev,
                        "reply": rep[arm][q]})
        size = BATCH if g.startswith("L") else len(its)
        for k in range(0, len(its), size):
            name = f"{g}{k // size + 1:02d}"
            (work / "batches" / f"{name}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in its[k:k + size]), encoding="utf-8")
            batches.append(name)
    same = [q for q in qids if rep["AN"][q] == rep["BN"][q]]
    (work / "key.json").write_text(json.dumps({"qids": qids, "items": key, "same": same}), encoding="utf-8")
    print(json.dumps({"questions": len(qids), "items": len(key), "batches": batches,
                      "bn_equals_an": sum(rep["AN"][q] == rep["BN"][q] for q in qids)}))
    return 0


def mcnemar_p(gained: int, lost: int) -> float:
    """Two-sided exact McNemar test: binomial(gained + lost, 1/2)."""
    n, k = gained + lost, min(gained, lost)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _boot(ids: list[str], diff: dict) -> list[float]:
    conv = defaultdict(list)
    for q in ids:
        conv[q.split("#")[0]].append(diff[q])
    cs = sorted(conv)
    rng = random.Random(BOOT_SEED)
    ds = sorted(100 * sum(v) / len(v) for v in
                ([x for c in (rng.choice(cs) for _ in cs) for x in conv[c]] for _ in range(BOOT_N)))
    return [round(ds[int(0.025 * BOOT_N)], 2), round(ds[int(0.975 * BOOT_N) - 1], 2)]


def verdict(by: dict, qids: list[str], cats: dict, same: set) -> dict:
    """same = questions whose AN and BN replies are byte-identical: one answer, so both arms take group L0's label
    (the arm L0 holds, ARMS[n % 2]) and the question counts as a tie; how often the two judges agreed is reported."""
    full = [q for q in qids if set(by[q]) == set(ARMS)]
    agree = sum(by[q]["AN"] == by[q]["BN"] for q in full if q in same)
    pos = {q: n for n, q in enumerate(qids)}
    by = {q: ({arm: by[q][ARMS[pos[q] % 2]] for arm in ARMS} if q in same and q in full else by[q]) for q in by}
    res = {"questions": len(qids), "fully_judged": len(full), "identical_replies": sum(q in same for q in full),
           "identical_replies_judges_agree": agree}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "labels": dict(sorted(c.items()))}
    diff = {q: int(by[q]["BN"] == "A") - int(by[q]["AN"] == "A") for q in full}
    g, l = sum(v > 0 for v in diff.values()), sum(v < 0 for v in diff.values())
    res["BN-AN"] = {"A": res["BN"]["A"] - res["AN"]["A"], "points": round(100 * sum(diff.values()) / max(1, len(full)), 1),
                    "gained": g, "lost": l, "mcnemar_p": round(mcnemar_p(g, l), 5),
                    "ci95_by_conversation_report_only": _boot(full, diff) if full else None}
    res["A_by_category"] = {str(c): {arm: sum(by[q][arm] == "A" for q in full if cats[q] == c) for arm in ARMS} | {
        "n": sum(cats[q] == c for q in full)} for c in (1, 2, 3, 4)}
    res["N1"] = res["BN-AN"]["A"] >= N1_MIN_GAIN and res["BN-AN"]["mcnemar_p"] < N1_MAX_P and g > l
    res["N2"] = all(v["AN"] - v["BN"] <= max(N2_MAX_CAT_DROP, round(N2_MAX_CAT_DROP * v["n"] / 100))
                    for v in res["A_by_category"].values())
    res["proved_wrong"] = res["BN-AN"]["A"] <= 0
    res["verdict"] = "PASS" if res["N1"] and res["N2"] else "FAIL"
    res["table_AN_to_BN"] = dict(sorted(Counter(f"{by[q]['AN']}->{by[q]['BN']}" for q in full).items()))
    return res


def jscore(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in "ABCDE" or not lab:
                raise SystemExit(f"bm398n jscore: bad label in {f.name}")
            sink[r["item"]] = lab
    if not a.data:
        raise SystemExit("bm398n jscore: --data is needed for the categories")
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    _kept, info = D.sample(Path(a.data))
    res = verdict(by, k["qids"], {q: info[q][2]["category"] for q in k["qids"]}, set(k["same"]))
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    if a.score:
        s = json.loads(Path(a.score).read_text(encoding="utf-8"))
        res["f1_report_only"] = {"AN": s["AN"]["cat1to4_f1"], "BN": s["BN"]["cat1to4_f1"]}
    print(json.dumps(res))
    return 0


def selftest(a) -> int:
    ok = {}
    qids = [f"conv-{c}#{i}" for c in (1, 2, 3) for i in range(40)]
    groups = latin(qids, random.Random(JUDGE_SEED))
    for g in ("L0", "L1"):
        ok[f"{g} holds every question once"] = sorted(q for q, _ in groups[g]) == sorted(qids)
    ok["each question's two arms are in different groups"] = all(
        dict(groups["L0"])[q] != dict(groups["L1"])[q] for q in qids)
    ok["arms balanced in each group"] = all(Counter(a for _, a in groups[g]) == Counter({"AN": 60, "BN": 60})
                                            for g in ("L0", "L1"))
    ok["X1 is L0's first 60 questions, same arms"] = sorted(groups["X1"]) == sorted(
        (q, ARMS[n % 2]) for n, q in enumerate(qids[:X1_N]))
    ok["mcnemar exact"] = (abs(mcnemar_p(10, 0) - 2 / 1024) < 1e-12 and mcnemar_p(5, 5) == 1.0
                           and abs(mcnemar_p(15, 5) - 0.04138946533203125) < 1e-12)
    rng = random.Random(1)
    cats = {q: 1 + (n % 4) for n, q in enumerate(qids)}
    by = {q: {"AN": rng.choice("AD"), "BN": rng.choice("AD")} for q in qids}
    v0 = verdict(by, qids, cats, set())
    ok["verdict counts add up"] = (v0["BN-AN"]["A"] == v0["BN"]["A"] - v0["AN"]["A"]
                                   and v0["BN-AN"]["gained"] - v0["BN-AN"]["lost"] == v0["BN-AN"]["A"])
    good = {q: {"AN": "D" if n % 5 == 0 else "A", "BN": "A"} for n, q in enumerate(qids)}
    v1 = verdict(good, qids, cats, set())
    ok["a clear gain passes"] = v1["verdict"] == "PASS" and v1["BN-AN"]["A"] == 24 and not v1["proved_wrong"]
    same = {q: {"AN": "A", "BN": "A"} for q in qids}
    v2 = verdict(same, qids, cats, set())
    ok["no gain fails and is proved wrong"] = v2["verdict"] == "FAIL" and v2["proved_wrong"]
    drop = {q: {"AN": "A" if cats[q] == 3 else "D", "BN": "D" if cats[q] == 3 else "A"} for q in qids}
    v3 = verdict(drop, qids, cats, set())
    ok["a category drop fails N2"] = v3["N1"] and not v3["N2"] and v3["verdict"] == "FAIL"
    split = {q: {"AN": "A", "BN": "D"} if n % 2 else {"AN": "D", "BN": "A"} for n, q in enumerate(qids)}
    v4 = verdict(split, qids, cats, set(qids))
    ok["identical replies are ties with L0's label"] = (v4["BN-AN"]["gained"] == 0 and v4["BN-AN"]["lost"] == 0
                                                        and v4["AN"]["A"] == 0 and v4["identical_replies"] == 120
                                                        and v4["identical_replies_judges_agree"] == 0)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398N-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "prep", "jscore", "selftest"])
    for x in ("data", "ranked", "model", "out", "runs", "work", "score"):
        ap.add_argument("--" + x, default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"run": run, "score": score, "prep": prep, "jscore": jscore, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
