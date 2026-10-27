#!/usr/bin/env python3
"""bm-398r evaluation (benchmarks thread, 2026-09-26): the reader adapter's replies, their scores and the blind check.
Plan and marks: artifacts/claude-bm398r-20260926/PLAN.md. Development measurement on LoCoMo ("after using LoCoMo for
development"). Nothing is trained here. No question, answer or reply text is printed: counts only.

  evidence  (rental) bm-398d's 297 questions from three inputs, each laid out as bm-398d laid them out:
            G = the annotated evidence lines, GD = those plus the store's other top lines to 20, E20 = the store's
            top 20 (bm-395's ranking). Writes locomo_G<name>, locomo_GD<name>, locomo_E20<name>.
              python -B scripts/claude_bm398r_eval.py evidence --data DATA --e20 E20.jsonl --model DIR --name R --out OUT
  score     F1 with the sealed bm-390 scorer, all 1,540 category 1-4 questions: TR (the adapter, whole chat) against
            T (the plain 1B, whole chat), the conversation-level interval of TR - T (seed 3994, 10,000 draws),
            abstentions, median words; GSM8K and MMLU with the adapter merged in (report only); the evidence arms'
            F1 on the 297 (report only).
              python -B scripts/claude_bm398r_eval.py score --data DATA --runs RUNS --t T.jsonl --out score.json
  prep      the blind check: T, TR and Q2 (Qwen3.5-2B, whole chat) on the 297, judged with bm-398d's rubric (judges
            see the evidence lines). Latin square: group L<g> holds arm ARMS[(n + g) % 3] of question n, so each
            group has every question once and each arm about 99 times; 50-item batches shuffled with
            random.Random(3993). X1 = the first 60 questions as L0 has them, for a relabel judge who judges no group.
              python -B scripts/claude_bm398r_eval.py prep --data DATA --t T.jsonl --tr TR.jsonl --q2 Q2DIR --work WORK
  jscore    A-counts, TR - T and TR - Q2 with a conversation bootstrap (seed 3993, 10,000), the T-by-TR label table,
            relabel agreement, and the verdict with score.json: R1, R2, R3, PASS, proved wrong.
              python -B scripts/claude_bm398r_eval.py jscore --work WORK --score score.json
WORK holds benchmark text: keep it outside the repository.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm390_score as SC  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402

ARMS = ["T", "TR", "Q2"]
JUDGE_SEED, BOOT_SEED, F1_SEED, BOOT_N, BATCH = 3993, 3993, 3994, 10000, 50
R1_MIN_GAIN, R2_MIN_F1, R3_MAX_EXTRA_ABSTAIN = 15, 32.50, 20


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _boot(ids: list[str], diff: dict, seed: int) -> list[float]:
    conv = defaultdict(list)
    for q in ids:
        conv[q.split("#")[0]].append(diff[q])
    cs = sorted(conv)
    rng = random.Random(seed)
    ds = sorted(100 * sum(v) / len(v) for v in
                ([x for c in (rng.choice(cs) for _ in cs) for x in conv[c]] for _ in range(BOOT_N)))
    return [round(ds[int(0.025 * BOOT_N)], 2), round(ds[int(0.975 * BOOT_N) - 1], 2)]


def evidence(a) -> int:
    kept, info = D.sample(Path(a.data))
    if a.limit:
        kept = kept[: a.limit]
    e20 = {r["qid"]: r for r in _jsonl(a.e20)}
    rows = {"G": [], "GD": [], "E20": []}
    t_all = time.time()
    for n, q in enumerate(kept):
        conv, i, qa, gold = info[q]
        items = D.items_of(conv)
        qtext = B.question_text(conv["sample_id"], i, qa)
        for name, ps in (("G", gold), ("GD", D.gd_positions(gold, e20[q]["turns"])), ("E20", e20[q]["turns"][:20])):
            t0 = time.time()
            user = D.context(conv, items, ps) + "\n\n" + B.QA_PROMPT.format(qtext)
            reply, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
            rows[name].append({"qid": q, "category": qa["category"], "reply": reply,
                               "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": ntok, "turns": ps})
        if (n + 1) % 50 == 0:
            print(f"[bm398r] evidence {n + 1}/{len(kept)} seconds={time.time() - t_all:.0f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rs in rows.items():
        B._write(out / f"locomo_{name}{a.name}.jsonl", rs)
        print(f"wrote locomo_{name}{a.name}.jsonl rows={len(rs)}", flush=True)
    return 0


def score(a) -> int:
    data, runs = Path(a.data), Path(a.runs)
    t = SC.score_locomo(data, _jsonl(a.t))
    tr = SC.score_locomo(data, _jsonl(runs / "locomo_TR.jsonl"))
    ids = sorted(q for q, v in t["per"].items() if v["cat"] in (1, 2, 3, 4))
    if sorted(q for q, v in tr["per"].items() if v["cat"] in (1, 2, 3, 4)) != ids:
        raise SystemExit("bm398r score: TR does not cover the same category 1-4 questions as T")
    diff = {q: tr["per"][q]["f1"] - t["per"][q]["f1"] for q in ids}
    trr = {r["qid"]: r["reply"] for r in _jsonl(runs / "locomo_TR.jsonl")}
    tt = {r["qid"]: r["reply"] for r in _jsonl(a.t)}
    first = lambda s: (s.strip().split("\n") or [""])[0]
    res = {"n": len(ids), "T": t["summary"], "TR": tr["summary"],
           "TR_minus_T_f1": round(tr["summary"]["cat1to4_f1"] - t["summary"]["cat1to4_f1"], 2),
           "ci95_by_conversation": _boot(ids, diff, F1_SEED),
           "median_words_first_line": {"T": statistics.median(len(first(tt[q]).split()) for q in ids),
                                       "TR": statistics.median(len(first(trr[q]).split()) for q in ids)},
           "gained": sum(v > 0 for v in diff.values()), "lost": sum(v < 0 for v in diff.values())}
    res["R2"] = res["TR"]["cat1to4_f1"] >= R2_MIN_F1 and res["ci95_by_conversation"][0] > 0
    res["R3"] = res["TR"]["cat1to4_abstain"] <= res["T"]["cat1to4_abstain"] + R3_MAX_EXTRA_ABSTAIN
    gen = {}
    for task in ("mmlu", "gsm8k"):
        f = runs / f"{task}_TR.jsonl"
        if f.exists():
            gen[task] = SC.score_general(data, task, _jsonl(f))["summary"]
    res["general_adapter_always_on_report_only"] = gen
    kept, info = D.sample(data)
    ev = {}
    for name in ("GB", "GR", "GDB", "GDR", "E20B", "E20R"):
        f = runs / f"locomo_{name}.jsonl"
        if f.exists():
            per = SC.score_locomo(data, _jsonl(f))["per"]
            ev[name] = round(100 * sum(per[q]["f1"] for q in kept) / len(kept), 2)
    res["evidence_f1_on_297_report_only"] = ev
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n", "TR_minus_T_f1", "ci95_by_conversation", "R2", "R3")}))
    return 0


def prep(a) -> int:
    import claude_bm397_judge as J
    kept, info = D.sample(Path(a.data))
    rep = {"T": {r["qid"]: r["reply"] for r in _jsonl(a.t)}, "TR": {r["qid"]: r["reply"] for r in _jsonl(a.tr)},
           "Q2": D._replies(Path(a.q2))}
    miss = {k: sum(q not in v for q in kept) for k, v in rep.items()}
    if any(miss.values()):
        raise SystemExit(f"bm398r prep: missing replies {miss}")
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    rng = random.Random(JUDGE_SEED)
    key, counter = {}, [0]

    def item(q: str, arm: str) -> dict:
        conv, i, qa, gold = info[q]
        items = D.items_of(conv)
        counter[0] += 1
        iid = f"r{counter[0]:05d}"
        key[iid] = {"qid": q, "arm": arm}
        ev = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
        return {"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": ev,
                "reply": rep[arm][q]}

    groups = {f"L{g}": [item(q, ARMS[(n + g) % 3]) for n, q in enumerate(kept)] for g in range(3)}
    groups["X1"] = [item(q, ARMS[n % 3]) for n, q in enumerate(kept[:60])]
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
    print(json.dumps({"kept": len(kept), "items": len(key), "batches": batches,
                      "tr_equals_t": sum(rep["T"][q] == rep["TR"][q] for q in kept)}))
    return 0


def jscore(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in "ABCDE":
                raise SystemExit(f"bm398r jscore: bad label in {f.name}")
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
    for other in ("T", "Q2"):
        diff = {q: int(by[q]["TR"] == "A") - int(by[q][other] == "A") for q in full}
        res[f"TR-{other}"] = {"points": round(100 * sum(diff.values()) / max(1, len(full)), 1),
                              "ci95_by_conversation": _boot(full, diff, BOOT_SEED),
                              "gained": sum(v > 0 for v in diff.values()), "lost": sum(v < 0 for v in diff.values())}
    res["table_T_to_TR"] = dict(sorted(Counter(f"{by[q]['T']}->{by[q]['TR']}" for q in full).items()))
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    res["R1"] = (res["TR"]["A"] >= res["T"]["A"] + R1_MIN_GAIN and res["TR-T"]["ci95_by_conversation"][0] > 0)
    res["proved_wrong"] = res["TR-T"]["points"] <= 0
    if a.score:
        s = json.loads(Path(a.score).read_text(encoding="utf-8"))
        res["R2"], res["R3"] = s["R2"], s["R3"]
        res["verdict"] = "PASS" if res["R1"] and res["R2"] and res["R3"] else "FAIL"
    print(json.dumps(res))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["evidence", "score", "prep", "jscore"])
    for x in ("data", "e20", "model", "name", "out", "runs", "t", "tr", "q2", "work", "score"):
        ap.add_argument("--" + x, default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"evidence": evidence, "score": score, "prep": prep, "jscore": jscore}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
