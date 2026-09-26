#!/usr/bin/env python3
"""bm-398u: the plain 1B reranks its candidate lines before it answers (benchmarks thread, 2026-09-26). Plan and
marks: artifacts/claude-bm398u-20260926/PLAN.md. The textbook "retrieve, rerank, read" fix that had not been tested
here: an unsupervised reranker (UPR, Sachan et al. 2022) that scores each candidate line by how likely the model
finds the question after reading it. No training, no new model, no hand-written rule: the same plain MiniCPM5-1B
that answers does the ranking. Development measurement on LoCoMo ("after using LoCoMo for development"). No question,
answer, turn or reply text is printed: counts only.

Arms (all answer from store B's lines, laid out and prompted the same way; only which lines differ):
  BN  bm-398n's arm: the 1B answers from store B's first 20 distinct turns (rd-378L's ranked_turns.jsonl, pinned
      by claude_bm398n_notes.RANKED_SHA), in chat order. Its replies come from bm-398n's run, unchanged.
  BF  store B's own fused order, cut to its first TOP_K turns.
  BU  the same 20 turns, each scored by the 1B as sum log P(question | turn) under UPR_USER; only the TOP_K
      highest (ties by store B's order) go to the 1B. BU against BF is the registered claim (ranking only, same
      number of lines); BU against BN is the "against today's store" row with its own mark.

  run      python -B scripts/claude_bm398u_rerank.py run --data DATA --ranked RANKED --model DIR --out OUT [--limit N]
  score    python -B scripts/claude_bm398u_rerank.py score --data DATA --ranked RANKED --bn BN.jsonl --runs OUT --out S
  prep     python -B scripts/claude_bm398u_rerank.py prep --data DATA --ranked RANKED --bn BN.jsonl --runs OUT --work W
  jscore   python -B scripts/claude_bm398u_rerank.py jscore --data DATA --work WORK
  devcheck python -B scripts/claude_bm398u_rerank.py devcheck --made MADE.json --model DIR [--limit N]
           (code-made chats, never LoCoMo: is an evidence turn in the reranker's top TOP_K of 20? Sanity only.)
  selftest python -B scripts/claude_bm398u_rerank.py selftest --tok DIR
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

ARMS = ["BN", "BF", "BU"]
NEW_ARMS = ["BF", "BU"]
K_CHOICES = (3, 5, 8)
TOP_K, SCORE_BATCH = 3, 10       # TOP_K set by the PLAN's rule from the code-made devcheck (DEVCHECK.md)
UPR_SYSTEM = B.GENERAL_SYSTEM
UPR_USER = "{passage}\n\nWrite a question that this message answers."
JUDGE_SEED, BATCH, X1_N = 3997, 50, 60
U1_MIN_GAIN, U1_MAX_P, U2_MAX_EXTRA_D, U3_MAX_CAT_DROP = 15, 0.05, 8, 3   # BU against BF, and V1/V2 against BN
DEV_SEED = 3998


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def passage(items: list, p: int) -> str:
    _si, date, t = items[p]
    return "DATE: " + date + "\n" + B.turn_text(t).strip()


def upr_scores(model_dir: str, question: str, passages: list[str]) -> list[float]:
    """sum log P(question tokens | UPR prompt with the passage), one number per passage."""
    import torch
    tok, model, dev, _ = B.plain_model(model_dir)
    q_ids = tok(question, add_special_tokens=False)["input_ids"]
    prompts = [B._ids(tok, UPR_SYSTEM, UPR_USER.format(passage=x))["input_ids"][0].tolist() for x in passages]
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    out: list[float] = []
    for k in range(0, len(prompts), SCORE_BATCH):
        chunk = prompts[k:k + SCORE_BATCH]
        width = max(len(p) for p in chunk) + len(q_ids)
        ids = torch.full((len(chunk), width), pad, dtype=torch.long)
        mask = torch.zeros((len(chunk), width), dtype=torch.long)
        for r, p in enumerate(chunk):
            full = p + q_ids
            ids[r, :len(full)] = torch.tensor(full)
            mask[r, :len(full)] = 1
        with torch.no_grad():
            logp = torch.log_softmax(model(input_ids=ids.to(dev), attention_mask=mask.to(dev)).logits.float(), -1)
        for r, p in enumerate(chunk):
            pos = torch.arange(len(p) - 1, len(p) - 1 + len(q_ids))
            out.append(round(logp[r, pos, torch.tensor(q_ids)].sum().item(), 4))
    return out


def top(turns: list[int], scores: list[float], k: int = TOP_K) -> list[int]:
    """The k best-scored turns; ties go to the earlier one in the store's own order."""
    order = sorted(range(len(turns)), key=lambda i: (-scores[i], i))
    return [turns[i] for i in order[:k]]


def run(a) -> int:
    qids, rt = N.ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    N.check(qids, rt, info)
    if a.limit:
        qids = qids[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fh = {arm: (out / f"locomo_{arm}.jsonl").open("w", encoding="utf-8") for arm in NEW_ARMS}
    t_all = time.time()
    for n, q in enumerate(qids):
        conv, i, qa, _gold = info[q]
        items = D.items_of(conv)
        pool = rt[(q, "B")]
        t0 = time.time()
        sc = upr_scores(a.model, qa["question"], [passage(items, p) for p in pool])
        rank_ms = round((time.time() - t0) * 1000, 1)
        for arm, keep in (("BF", pool[:TOP_K]), ("BU", top(pool, sc))):
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
            print(f"[bm398u] {n + 1}/{len(qids)} seconds={time.time() - t_all:.0f}", flush=True)
    for arm in NEW_ARMS:
        fh[arm].close()
        f = out / f"locomo_{arm}.jsonl"
        print(f"wrote locomo_{arm}.jsonl rows={len(_jsonl(f))} sha256={hashlib.sha256(f.read_bytes()).hexdigest()}",
              flush=True)
    print(json.dumps({"questions": len(qids), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def _bn(path: str, qids: list[str], rt: dict) -> dict:
    rows = {r["qid"]: r for r in _jsonl(path)}
    if sorted(rows) != sorted(qids) or any(rows[q]["turns"] != rt[(q, "B")] for q in qids):
        raise SystemExit("bm398u: --bn is not bm-398n's BN arm on the 759")
    return rows


def _replies(a, qids, rt) -> dict:
    out = {"BN": _bn(a.bn, qids, rt)}
    for arm in NEW_ARMS:
        out[arm] = {r["qid"]: r for r in _jsonl(Path(a.runs) / f"locomo_{arm}.jsonl")}
        if sorted(out[arm]) != sorted(qids):
            raise SystemExit(f"bm398u: {arm} does not cover the 759")
    if any(out["BF"][q]["turns"] != rt[(q, "B")][:TOP_K] for q in qids):
        raise SystemExit("bm398u: BF is not store B's fused top TOP_K")
    return out


def score(a) -> int:
    import claude_bm390_score as SC
    qids, rt = N.ranked(a.ranked)
    _kept, info = D.sample(Path(a.data))
    rep = _replies(a, qids, rt)
    res = {"n": len(qids), "bn_sha256": hashlib.sha256(Path(a.bn).read_bytes()).hexdigest()}
    for arm in ARMS:
        rows = [rep[arm][q] for q in qids]
        s = SC.score_locomo(Path(a.data), rows)["summary"]
        res[arm] = {k: s[k] for k in ("cat1to4_n", "cat1to4_f1", "cat1to4_abstain", "cat1to4_confident_wrong",
                                      "cat1to4_half_right", "cat1_f1", "cat2_f1", "cat3_f1", "cat4_f1")}
    ev = lambda ts: (sum(bool(set(info[q][3]) & set(ts[q])) for q in qids),  # noqa: E731
                     sum(set(info[q][3]) <= set(ts[q]) for q in qids))
    res["finding_report_only"] = {
        "store_B_all_20": ev({q: rt[(q, "B")] for q in qids}),
        "store_B_fused_top5": ev({q: rt[(q, "B")][:TOP_K] for q in qids}),
        "reranked_top5": ev({q: rep["BU"][q]["turns"] for q in qids}),
        "note": "(questions with any evidence turn, with all evidence turns) among the lines shown"}
    res["BU_minus_BF_f1"] = round(res["BU"]["cat1to4_f1"] - res["BF"]["cat1to4_f1"], 2)
    res["BU_minus_BN_f1"] = round(res["BU"]["cat1to4_f1"] - res["BN"]["cat1to4_f1"], 2)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return 0


def group_of(arm: str, n: int) -> int:
    """The group that holds this arm of question n: group g holds ARMS[(n + g) % 3]."""
    return (ARMS.index(arm) - n) % len(ARMS)


def latin(qids: list[str], rng: random.Random) -> dict[str, list[tuple[str, str]]]:
    k = len(ARMS)
    groups = {f"L{g}": [(q, ARMS[(n + g) % k]) for n, q in enumerate(qids)] for g in range(k)}
    groups["X1"] = [(q, ARMS[n % k]) for n, q in enumerate(qids[:X1_N])]
    for g in groups:
        rng.shuffle(groups[g])
    return groups


def prep(a) -> int:
    import claude_bm397_judge as J
    qids, rt = N.ranked(a.ranked)
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
            iid = f"u{counter:05d}"
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
    same = {q: [[x, y] for j, x in enumerate(ARMS) for y in ARMS[j + 1:] if rep[x][q]["reply"] == rep[y][q]["reply"]]
            for q in qids}
    same = {q: v for q, v in same.items() if v}
    (work / "key.json").write_text(json.dumps({"qids": qids, "items": key, "same": same}), encoding="utf-8")
    print(json.dumps({"questions": len(qids), "items": len(key), "batches": batches,
                      "identical_pairs": dict(Counter("=".join(p) for v in same.values() for p in v))}))
    return 0


def verdict(by: dict, qids: list[str], cats: dict, same: dict) -> dict:
    """same = {question: [[arm, arm], ...]} for byte-identical replies. Identical replies are one answer: every arm
    in such a set takes the label of the member in the lowest-numbered group, and the pair is a tie. How often the
    judges agreed on identical pairs is reported."""
    full = [q for q in qids if set(by[q]) == set(ARMS)]
    pos = {q: n for n, q in enumerate(qids)}
    agree = sum(by[q][x] == by[q][y] for q in full for x, y in same.get(q, []))
    npairs = sum(len(same.get(q, [])) for q in full)
    fixed = {}
    for q in by:
        lab = dict(by[q])
        if q in full and same.get(q):
            link = {a: {a} for a in ARMS}
            for x, y in same[q]:
                u = link[x] | link[y]
                for a in u:
                    link[a] = u
            for a in ARMS:
                lab[a] = by[q][min(link[a], key=lambda z: group_of(z, pos[q]))]
        fixed[q] = lab
    by = fixed
    res = {"questions": len(qids), "fully_judged": len(full), "identical_pairs": npairs,
           "identical_pairs_judges_agree": agree}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "D": c["D"], "E": c["E"], "labels": dict(sorted(c.items()))}

    def pair(x: str, y: str) -> dict:
        diff = {q: int(by[q][x] == "A") - int(by[q][y] == "A") for q in full}
        g, lo = sum(v > 0 for v in diff.values()), sum(v < 0 for v in diff.values())
        return {"A": res[x]["A"] - res[y]["A"], "gained": g, "lost": lo, "mcnemar_p": round(N.mcnemar_p(g, lo), 5),
                "ci95_by_conversation_report_only": N._boot(full, diff) if full else None}

    res["BU-BF"], res["BU-BN"], res["BF-BN_report_only"] = pair("BU", "BF"), pair("BU", "BN"), pair("BF", "BN")
    res["A_by_category"] = {str(c): {arm: sum(by[q][arm] == "A" for q in full if cats[q] == c) for arm in ARMS} | {
        "n": sum(cats[q] == c for q in full)} for c in (1, 2, 3, 4)}
    u, v = res["BU-BF"], res["BU-BN"]
    res["U1"] = u["A"] >= U1_MIN_GAIN and u["mcnemar_p"] < U1_MAX_P and u["gained"] > u["lost"]
    res["U2"] = res["BU"]["D"] <= res["BF"]["D"] + U2_MAX_EXTRA_D
    res["U3"] = all(c["BF"] - c["BU"] <= max(U3_MAX_CAT_DROP, round(U3_MAX_CAT_DROP * c["n"] / 100))
                    for c in res["A_by_category"].values())
    res["proved_wrong"] = u["A"] <= 0
    res["verdict"] = "PASS" if res["U1"] and res["U2"] and res["U3"] else "FAIL"
    res["V1"] = v["A"] >= U1_MIN_GAIN and v["mcnemar_p"] < U1_MAX_P and v["gained"] > v["lost"]
    res["V2"] = res["BU"]["D"] <= res["BN"]["D"] + U2_MAX_EXTRA_D
    res["verdict_vs_store"] = "PASS" if res["V1"] and res["V2"] else "FAIL"
    res["table_BF_to_BU"] = dict(sorted(Counter(f"{by[q]['BF']}->{by[q]['BU']}" for q in full).items()))
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
                raise SystemExit(f"bm398u jscore: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    _kept, info = D.sample(Path(a.data))
    res = verdict(by, k["qids"], {q: info[q][2]["category"] for q in k["qids"]}, k["same"])
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    print(json.dumps(res))
    return 0


def devcheck(a) -> int:
    """Code-made chats only. For each question with evidence: the evidence turn(s) plus other turns of the same chat
    up to 20, in a seeded random order; count how often any, and all, evidence turns are in the reranker's top k for
    k in K_CHOICES (chance is about k / 20 for one evidence turn). Sanity only, not a mark; prints counts."""
    convs = json.loads(Path(a.made).read_text(encoding="utf-8"))
    rng = random.Random(DEV_SEED)
    n, hit_any, hit_all, hit_first = 0, Counter(), Counter(), 0
    t0 = time.time()
    for c in convs:
        items = D.items_of(c)
        ids = {t["dia_id"]: p for p, (_s, _d, t) in enumerate(items)}
        for qa in c["qa"]:
            ev = [ids[e] for e in qa.get("evidence", []) if e in ids]
            if not ev or qa["category"] not in (1, 2, 3, 4):
                continue
            others = [p for p in range(len(items)) if p not in ev]
            pool = ev + rng.sample(others, min(20 - len(ev), len(others)))
            rng.shuffle(pool)
            sc = upr_scores(a.model, qa["question"], [passage(items, p) for p in pool])
            n += 1
            for k in K_CHOICES:
                keep = top(pool, sc, k)
                hit_any[k] += bool(set(ev) & set(keep))
                hit_all[k] += set(ev) <= set(keep)
            hit_first += top(pool, sc, 1)[0] in ev
            if a.limit and n >= a.limit:
                break
        if a.limit and n >= a.limit:
            break
    print(json.dumps({"questions": n, "any_evidence_in_top_k": {k: hit_any[k] for k in K_CHOICES},
                      "all_evidence_in_top_k": {k: hit_all[k] for k in K_CHOICES}, "evidence_ranked_first": hit_first,
                      "chance_top_k_one_evidence": {k: round(k / 20, 2) for k in K_CHOICES},
                      "seconds": round(time.time() - t0)}))
    return 0


def selftest(a) -> int:
    import tempfile
    import torch
    from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM
    ok = {}
    ok["top keeps the best k, ties to the store's order"] = top([7, 3, 9, 1, 5, 2], [-1, -5, -1, -9, -2, -3], 3) == [7, 9, 5]
    ok["top never adds turns"] = set(top(list(range(20)), [0.0] * 20)) <= set(range(20)) and len(top(list(range(20)), [0.0] * 20)) == TOP_K
    tok = AutoTokenizer.from_pretrained(a.tok)
    with tempfile.TemporaryDirectory() as d:
        torch.manual_seed(0)
        cfg = LlamaConfig(vocab_size=len(tok), hidden_size=16, intermediate_size=32, num_hidden_layers=1,
                          num_attention_heads=2, num_key_value_heads=1, max_position_embeddings=4096,
                          bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, pad_token_id=tok.pad_token_id)
        m = LlamaForCausalLM(cfg)
        m.save_pretrained(Path(d) / "m")
        tok.save_pretrained(Path(d) / "m")
        ps = [f"DATE: 1 May 2023\nWren said, \"line number {i} {'x ' * i}\"" for i in range(13)]
        sc = upr_scores(str(Path(d) / "m"), "Where did Wren go?", ps)
        ok["one finite score per passage"] = len(sc) == 13 and all(s == s and s < 0 for s in sc)
        one = [upr_scores(str(Path(d) / "m"), "Where did Wren go?", [p])[0] for p in ps[:3]]
        ok["batched scores equal one-at-a-time (padding is harmless)"] = all(abs(x - y) < 1e-2 for x, y in zip(one, sc[:3]))
        tk, mdl, dev, _ = B.plain_model(str(Path(d) / "m"))
        q = tk("Where did Wren go?", add_special_tokens=False)["input_ids"]
        p0 = B._ids(tk, UPR_SYSTEM, UPR_USER.format(passage=ps[0]))["input_ids"][0].tolist()
        with torch.no_grad():
            lp = torch.log_softmax(mdl(input_ids=torch.tensor([p0 + q])).logits.float(), -1)[0]
        ref = sum(lp[len(p0) - 1 + j, t].item() for j, t in enumerate(q))
        ok["score is sum log P(question | passage prompt)"] = abs(ref - sc[0]) < 1e-2
        ok["the passage reaches the prompt"] = "line number 0" in tk.decode(p0) and "Write a question" in tk.decode(p0)
    qids = [f"conv-{c}#{i}" for c in (1, 2, 3) for i in range(40)]
    groups = latin(qids, random.Random(JUDGE_SEED))
    ok["each group holds every question once, arms balanced"] = all(
        sorted(q for q, _ in groups[g]) == sorted(qids) and Counter(x for _, x in groups[g]) == Counter(
            {"BN": 40, "BF": 40, "BU": 40}) for g in ("L0", "L1", "L2"))
    ok["a question's three arms are in three different groups"] = all(
        len({dict(groups[g])[q] for g in ("L0", "L1", "L2")}) == 3 for q in qids)
    ok["group_of matches the square"] = all(
        dict(groups[f"L{group_of(arm, n)}"])[q] == arm for n, q in enumerate(qids) for arm in ARMS)
    ok["X1 is L0's first 60 questions, same arms"] = sorted(groups["X1"]) == sorted(
        (q, ARMS[n % 3]) for n, q in enumerate(qids[:X1_N]))
    cats = {q: 1 + (n % 4) for n, q in enumerate(qids)}
    good = {q: {"BN": "D", "BF": "D" if n % 5 == 0 else "A", "BU": "A"} for n, q in enumerate(qids)}
    v1 = verdict(good, qids, cats, {})
    ok["a clear gain over BF passes; BN row has its own mark"] = (
        v1["verdict"] == "PASS" and v1["BU-BF"]["A"] == 24 and not v1["proved_wrong"]
        and v1["verdict_vs_store"] == "PASS" and v1["BU-BN"]["A"] == 120)
    v2 = verdict({q: {"BN": "D", "BF": "A", "BU": "A"} for q in qids}, qids, cats, {})
    ok["beating BN but not BF fails and is proved wrong"] = (v2["verdict"] == "FAIL" and v2["proved_wrong"]
                                                             and v2["verdict_vs_store"] == "PASS")
    wrong = {q: {"BN": "E", "BF": "E" if n % 3 else "A", "BU": "A" if n % 3 else "D"} for n, q in enumerate(qids)}
    v3 = verdict(wrong, qids, cats, {})
    ok["more confident-wrong answers fail U2"] = v3["U1"] and not v3["U2"] and v3["verdict"] == "FAIL"
    drop = {q: {"BN": "D", "BF": "A" if cats[q] == 3 else "D", "BU": "D" if cats[q] == 3 else "A"} for q in qids}
    v4 = verdict(drop, qids, cats, {})
    ok["a category drop fails U3"] = v4["U1"] and not v4["U3"] and v4["verdict"] == "FAIL"
    split = {q: {"BN": "D", "BF": "A", "BU": "D"} if n % 2 else {"BN": "D", "BF": "D", "BU": "A"}
             for n, q in enumerate(qids)}
    v5 = verdict(split, qids, cats, {q: [["BF", "BU"]] for q in qids})
    ok["identical BF/BU replies are ties"] = (v5["BU-BF"]["gained"] == 0 and v5["BU-BF"]["lost"] == 0
                                             and v5["identical_pairs"] == 120)
    first = v5["BF"]["A"] == v5["BU"]["A"]
    lab = {q: min(("BF", "BU"), key=lambda z: group_of(z, n)) for n, q in enumerate(qids)}
    want = sum(split[q][lab[q]] == "A" for q in qids)
    ok["a tie takes the label from the lower-numbered group"] = first and v5["BU"]["A"] == want
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398U-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "prep", "jscore", "devcheck", "selftest"])
    for x in ("data", "ranked", "model", "out", "runs", "work", "bn", "made", "tok"):
        ap.add_argument("--" + x, default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"run": run, "score": score, "prep": prep, "jscore": jscore, "devcheck": devcheck,
            "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
