#!/usr/bin/env python3
"""bm-398d, the evidence diagnostic (benchmarks thread, 2026-09-26). Where do the plain 1B's wrong LoCoMo answers come
from: finding the right lines, being distracted by others, or reading them? Plan and decision rules:
artifacts/claude-bm398d-20260926/PLAN.md. Development measurement on LoCoMo ("after using LoCoMo for development").
Nothing is trained; no question, answer or reply text is printed.

The sample is bm-397t's judged 300 (random.Random(3972).sample of the sorted category 1-4 ids), kept only where
LoCoMo annotates at least one evidence turn that maps to a chat position. Two new inputs for the plain MiniCPM5-1B:
  G   the annotated evidence turns only;
  GD  the annotated evidence turns plus the store's highest-ranked other turns (bm-395's E20 ranking, saved in its
      "turns" field) until 20 lines, or only the evidence if it has more than 20 lines.
Both are laid out exactly as bm-395 laid out E20 (claude_bm395_store_answer.store_context: bm-390's header, "DATE: /
CONVERSATION:" blocks in time order, '<speaker> said, "<text>"'), then bm-390's QA prompt with its category-2 date
hint, its system prompt, greedy, 50 new tokens, thinking off (claude_bm390.generate). Only the lines shown change.
Existing arms joined for the blind check: E20 (bm-395, the store's top 20), T (bm-390 run2, whole chat) and Q2
(bm-390 run2, Qwen3.5-2B, whole chat).

  python -B scripts/claude_bm398d_evidence.py selftest --data DATA [--key KEY397T]
  python -B scripts/claude_bm398d_evidence.py run --data DATA --e20 E20.jsonl --model BASE --out OUT [--limit N]
  python -B scripts/claude_bm398d_evidence.py prep --data DATA --out OUT --e20 E20.jsonl --t T.jsonl --q2 Q2DIR --work WORK
  python -B scripts/claude_bm398d_evidence.py score --data DATA --work WORK --out OUT --e20 E20.jsonl
run also regenerates E20's first 30 sampled questions on this machine (arm E20c, report only), to measure how often
CPU fp32 decoding gives the same reply as the GPU bf16 run. WORK holds benchmark text: keep it outside the repository.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402

SEED = 3972          # bm-397t's judged sample
N = 300
GD_LINES = 20
ARMS = ["T", "E20", "GD", "G", "Q2"]
JUDGE_SEED = 3981
BATCH = 50
BOOT_SEED, BOOT_N = 398, 10000
LABELS = "ABCDE"


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def items_of(conv: dict) -> list:
    """items[position] = (session_index, date, turn), positions as bm-395 numbered them."""
    out = []
    for si, (date, turns) in enumerate(B.sessions(conv)):
        for t in turns:
            out.append((si, date, t))
    return out


def context(conv: dict, items: list, positions) -> str:
    """claude_bm395_store_answer.store_context, repeated here so this file needs no MiniLM."""
    out = B.start_text(conv)
    cur = None
    for p in sorted(set(positions)):
        si, date, t = items[p]
        if si != cur:
            out += "\nDATE: " + date + "\n" + "CONVERSATION:\n"
            cur = si
        out += B.turn_text(t) + "\n"
    return out


def evidence(conv: dict, qa: dict) -> list[int]:
    pos = {}
    for _date, turns in B.sessions(conv):
        for t in turns:
            pos[t.get("dia_id")] = len(pos)
    return sorted({pos[e] for e in qa.get("evidence", []) if e in pos})


def sample(data: Path) -> tuple[list[str], dict]:
    """(kept ids in sample order, info); info maps qid -> (conv, index, qa, evidence positions)."""
    convs = B.load_locomo(data, "")
    info = {}
    for c in convs:
        for i, qa in enumerate(c["qa"]):
            info[f"{c['sample_id']}#{i}"] = (c, i, qa, evidence(c, qa))
    ids = sorted(q for q, v in info.items() if v[2]["category"] in (1, 2, 3, 4))
    drawn = random.Random(SEED).sample(ids, N)
    return [q for q in drawn if info[q][3]], info


def gd_positions(gold: list[int], ranked: list[int]) -> list[int]:
    out = list(gold)
    for p in ranked:
        if len(out) >= GD_LINES:
            break
        if p not in out:
            out.append(p)
    return out


def selftest(a) -> int:
    ok = {}
    import claude_bm395_store_answer as A
    import tempfile
    data = Path(a.data)
    kept, info = sample(data)
    conv0 = B.load_locomo(data, "")[0]
    with tempfile.TemporaryDirectory() as d:
        s, items_a = A.build_store(conv0, d)
    items = items_of(conv0)
    ok["positions match bm-395's store numbering"] = [x[2].get("dia_id") for x in items] == \
        [x[2].get("dia_id") for x in items_a]
    ok["layout matches bm-395's store_context"] = all(
        context(conv0, items, ps) == A.store_context(conv0, items_a, ps) for ps in ([0, 5, 9], [3], list(range(12))))
    ok["sample keeps only questions with evidence"] = all(info[q][3] for q in kept) and 200 <= len(kept) <= N
    g = [4, 9]
    gd = gd_positions(g, [9, 1, 2, 4, 7] + list(range(20, 60)))
    ok["GD holds all gold, 20 lines, no repeats"] = set(g) <= set(gd) and len(gd) == 20 and len(set(gd)) == 20
    ok["GD keeps a gold set over 20 whole"] = gd_positions(list(range(25)), [30, 31]) == list(range(25))
    if a.key:
        k = json.loads(Path(a.key).read_text(encoding="utf-8"))
        drawn = random.Random(SEED).sample(sorted(q for q, v in info.items() if v[2]["category"] in (1, 2, 3, 4)), N)
        ok["same 300 as bm-397t's judged sample"] = drawn == k["sample"]
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print(f"sample kept {len(kept)} of {N}")
    print("BM398D-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def run(a) -> int:
    kept, info = sample(Path(a.data))
    if a.limit:
        kept = kept[: a.limit]
    e20 = {r["qid"]: r for r in _jsonl(Path(a.e20))}
    rows = {"G": [], "GD": [], "E20c": []}
    t_all = time.time()
    for n, q in enumerate(kept):
        conv, i, qa, gold = info[q]
        items = items_of(conv)
        qtext = B.question_text(conv["sample_id"], i, qa)
        arms = [("G", gold), ("GD", gd_positions(gold, e20[q]["turns"]))]
        if n < 30:
            arms.append(("E20c", e20[q]["turns"][:20]))
        for name, ps in arms:
            t0 = time.time()
            user = context(conv, items, ps) + "\n\n" + B.QA_PROMPT.format(qtext)
            reply, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
            rows[name].append({"qid": q, "category": qa["category"], "reply": reply,
                               "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": ntok, "turns": ps})
        if (n + 1) % 25 == 0:
            print(f"[bm398d] {n + 1}/{len(kept)} seconds={time.time() - t_all:.0f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in ("G", "GD"):
        B._write(out / f"locomo_{name}.jsonl", rows[name])
        print(f"wrote locomo_{name}.jsonl rows={len(rows[name])}", flush=True)
    same = sum(r["reply"] == e20[r["qid"]]["reply"] for r in rows["E20c"])
    B._write(out / "locomo_E20c.jsonl", rows["E20c"])
    (out / "precision.json").write_text(json.dumps({"E20c_rows": len(rows["E20c"]), "identical_to_gpu_E20": same}),
                                        encoding="utf-8")
    print(json.dumps({"E20c_rows": len(rows["E20c"]), "identical_to_gpu_E20": same,
                      "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def _replies(path: Path) -> dict:
    files = [path] if path.is_file() else sorted(path.glob("locomo_Q2*.jsonl"))
    return {r["qid"]: r["reply"] for f in files for r in _jsonl(f)}


def prep(a) -> int:
    import claude_bm397_judge as J
    kept, info = sample(Path(a.data))
    out = Path(a.out)
    rep = {"G": _replies(out / "locomo_G.jsonl"), "GD": _replies(out / "locomo_GD.jsonl"),
           "E20": _replies(Path(a.e20)), "T": _replies(Path(a.t)), "Q2": _replies(Path(a.q2))}
    miss = {k: sum(q not in v for q in kept) for k, v in rep.items()}
    if any(miss.values()):
        raise SystemExit(f"bm398d prep: missing replies {miss}")
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    rng = random.Random(JUDGE_SEED)
    key, counter = {}, [0]

    def item(q: str, arm: str) -> dict:
        conv, i, qa, gold = info[q]
        items = items_of(conv)
        counter[0] += 1
        iid = f"i{counter[0]:05d}"
        key[iid] = {"qid": q, "arm": arm}
        ev = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
        return {"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": ev,
                "reply": rep[arm][q]}

    groups = {f"L{g}": [item(q, ARMS[(n + g) % len(ARMS)]) for n, q in enumerate(kept)] for g in range(len(ARMS))}
    groups["X1"] = [item(q, ARMS[n % len(ARMS)]) for n, q in enumerate(kept[:60])]
    groups["X2"] = [item(q, ARMS[(n + 1) % len(ARMS)]) for n, q in enumerate(kept[:60])]
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
    print(json.dumps({"kept": len(kept), "items": len(key), "batches": batches}))
    return 0


def _boot(qs: list[str], diff: dict) -> list[float]:
    conv = defaultdict(list)
    for q in qs:
        conv[q.split("#")[0]].append(diff[q])
    cs = sorted(conv)
    rng = random.Random(BOOT_SEED)
    ds = []
    for _ in range(BOOT_N):
        vals = [x for c in (rng.choice(cs) for _ in cs) for x in conv[c]]
        ds.append(100 * sum(vals) / len(vals))
    ds.sort()
    return [round(ds[int(0.025 * BOOT_N)], 1), round(ds[int(0.975 * BOOT_N) - 1], 1)]


def score(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    _, info = sample(Path(a.data))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if lab not in LABELS:
                raise SystemExit(f"bm398d score: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    full = [q for q in k["kept"] if set(by[q]) == set(ARMS)]
    res = {"kept": len(k["kept"]), "fully_judged": len(full)}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "A_pct": round(100 * c["A"] / max(1, len(full)), 1), "labels": dict(sorted(c.items()))}
    pairs = {"G-T": ("G", "T"), "GD-G": ("GD", "G"), "GD-E20": ("GD", "E20"), "T-E20": ("T", "E20"),
             "Q2-T": ("Q2", "T"), "Q2-G": ("Q2", "G")}
    for name, (x, y) in pairs.items():
        diff = {q: int(by[q][x] == "A") - int(by[q][y] == "A") for q in full}
        res[name] = {"points": round(100 * sum(diff.values()) / max(1, len(full)), 1), "ci95_by_conversation": _boot(full, diff),
                     "gained": sum(v > 0 for v in diff.values()), "lost": sum(v < 0 for v in diff.values())}
    res["by_category_A_pct"] = {
        arm: {c: round(100 * sum(by[q][arm] == "A" for q in full if info[q][2]["category"] == c)
                       / max(1, sum(info[q][2]["category"] == c for q in full)), 1) for c in (1, 2, 3, 4)}
        for arm in ARMS}
    res["category_n"] = dict(Counter(info[q][2]["category"] for q in full))
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    g = res["G-T"]
    if a.out and a.e20:
        # GD and E20 get the same lines wherever E20's top 20 already held every evidence line; there the only
        # difference is CPU fp32 (GD) vs GPU bf16 (E20) decoding. The rest is where retrieval missed evidence.
        gdr = {r["qid"]: r for r in _jsonl(Path(a.out) / "locomo_GD.jsonl")}
        e20 = {r["qid"]: r for r in _jsonl(Path(a.e20))}
        same = [q for q in full if set(gdr[q]["turns"]) == set(e20[q]["turns"][:20])]
        miss = [q for q in full if q not in set(same)]
        ident = [q for q in same if gdr[q]["reply"] == e20[q]["reply"]]
        for name, qs in (("same_lines", same), ("retrieval_missed", miss)):
            diff = {q: int(by[q]["GD"] == "A") - int(by[q]["E20"] == "A") for q in qs}
            res[f"GD-E20_{name}"] = {"n": len(qs), "points": round(100 * sum(diff.values()) / max(1, len(qs)), 1),
                                     "ci95_by_conversation": _boot(qs, diff) if qs else None}
        res["identical_replies_same_lines"] = f"{len(ident)}/{len(same)}"
        res["same_label_on_identical_replies"] = f"{sum(by[q]['GD'] == by[q]['E20'] for q in ident)}/{len(ident)}"
        pj = Path(a.out) / "precision.json"
        if pj.exists():
            res["E20c"] = json.loads(pj.read_text(encoding="utf-8"))
        res["precision_guard_ok"] = abs(res["GD-E20_same_lines"]["points"]) <= 5
    res["D1"] = ("finding" if g["points"] >= 15 and g["ci95_by_conversation"][0] > 0 else
                 "reading" if g["points"] <= 5 else "both")
    res["D2_distraction"] = res["GD-G"]["points"] <= -10 and res["GD-G"]["ci95_by_conversation"][1] < 0
    res["D3_retrieval_misses"] = res["GD-E20"]["points"] >= 10 and res["GD-E20"]["ci95_by_conversation"][0] > 0
    res["INVALID_annotations"] = g["points"] <= -5
    print(json.dumps(res))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "run", "prep", "score"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--key", default="")
    ap.add_argument("--e20", default="")
    ap.add_argument("--t", default="")
    ap.add_argument("--q2", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--work", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"selftest": selftest, "run": run, "prep": prep, "score": score}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
