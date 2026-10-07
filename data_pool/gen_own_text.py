"""Own-text rows for the 8a rungs (data plan step 3): generator rows + TEACH, one nested set, prefixes = rungs.

  python3 gen_own_text.py --out OUT --skills-repo DIR_WITH_skills_curriculum --b1-teach DIR_WITH_gen_english.py \
        --teach plan-b/data/teach.jsonl --gen-existing plan-b/data/gen.jsonl --dev DIR1 [DIR2 ...]

Deterministic (same arguments -> same bytes). No new teacher, no new kinds: skills_curriculum's 34 train families (items pass its own
verify.check_item, are train-clean, never equal a dev prompt) + gen_english's 12 existing kinds (round-6 mode) + the 171,940 TEACH rows.
Budgets (LFM2.5 tokens, row = prompt+answer, or passage+question+answer): total 72.0M = TEACH 3.25M + English 22.0M + skills the rest.
All rows are shuffled once (seed 20261007); rung 3 = first 7.6M tokens, rung 10 = first 22.8M, rung 30 = all 72.0M, so every prefix has the
same mix. Each row carries `rung` (smallest rung containing it) and `pos` (global order). Writes skills.jsonl, english.jsonl, teach.jsonl, MANIFEST.json.
"""
import argparse, collections, hashlib, json, os, random, re, sys
from multiprocessing import Pool

RUNGS = [(3, 7.6e6), (10, 22.8e6), (30, 72.0e6)]
FAM_N = 34
NO_LEN_FILTER = True   # Ben 2:04 PM ET 10-07: do not cut off long items. skills_curriculum.build drops est_tokens > 62 silently; this script keeps them and counts them.


def skills_worker(args):
    fid, target, max_draws, repo, dev_prompts = args
    sys.path.insert(0, repo)
    from skills_curriculum import skills  # noqa: F401
    from skills_curriculum.core import make_item, MAX_TOKENS_EST
    max_est = None if NO_LEN_FILTER else MAX_TOKENS_EST
    from skills_curriculum.build import DIFF_WEIGHTS
    from skills_curriculum import verify
    rng = random.Random(f"own|{fid}")
    seen, rows, bad, i = set(), [], 0, 0
    rej = collections.Counter()
    for i in range(1, max_draws + 1):
        diff = rng.choices((0, 1, 2), DIFF_WEIGHTS)[0]
        it = make_item(fid, "O1", i, diff)
        if max_est is not None and it["est_tokens"] > max_est:
            rej["over_est_tokens"] += 1; continue
        if any(it["flags"].values()):
            rej["heldout_flag"] += 1; continue
        if it["est_tokens"] > MAX_TOKENS_EST:
            rej["over_est_tokens_KEPT"] += 1     # would have been thrown away by skills_curriculum.build; counted, not dropped
        p = it["prompt"]
        if p in seen: rej["duplicate_prompt"] += 1; continue
        if p in dev_prompts: rej["equals_dev_prompt"] += 1; continue
        probs = verify.check_item(it)
        if any(x.startswith("too long") for x in probs):
            rej["verify_too_long_KEPT"] += 1       # verify's own length check; the answer/step checks below still must pass
        probs = [x for x in probs if not x.startswith("too long")]
        if probs:
            bad += 1; continue
        seen.add(p)
        rows.append({"id": f"own-{fid}-{i}", "family": fid, "level": it["level"], "variant": it.get("variant"), "stage": 9,
                     "prompt": p, "answer": it["answer"], "accepted": it["accepted"], "steps": it.get("steps"), "est_tokens": it["est_tokens"]})
        if len(rows) >= target:
            break
    return fid, rows, bad, i, dict(rej)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--skills-repo", required=True); ap.add_argument("--b1-teach", required=True)
    ap.add_argument("--teach", required=True); ap.add_argument("--gen-existing", required=True); ap.add_argument("--dev", nargs="*", default=[])
    ap.add_argument("--teach-tokens", type=float, default=None); ap.add_argument("--english-tokens", type=float, default=22.0e6)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("LiquidAI/LFM2.5-1.2B-Instruct", revision="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
    def ntok(texts):
        return [len(x) for x in tok(texts, add_special_tokens=False)["input_ids"]]

    # ---- TEACH (flattened exactly like gen_control: one question per row)
    teach = []
    for line in open(a.teach):
        e = json.loads(line)
        for qi, q in enumerate(e["questions"]):
            teach.append({"id": f"{e['id']}-q{qi}", "kind": e["family"], "source_text": e["source_text"], "paraphrase": e["paraphrase"],
                          "question": q["question"], "type": q["type"], "canonical_answer": q["canonical_answer"], "accepted_answers": q["accepted_answers"]})
    t_tok = ntok([r["source_text"] + " " + r["question"] + " " + r["canonical_answer"] for r in teach])
    T = sum(t_tok); print("teach rows", len(teach), "tokens", T, flush=True)

    # ---- English generator: 12 existing kinds, new seed, avoiding every GEN passage already used
    sys.path.insert(0, a.b1_teach)
    import gen_english as GE
    avoid = {json.loads(l)["source_text"] for l in open(a.gen_existing)}
    avoid |= {r["source_text"] for r in teach}
    fits_rej = collections.Counter(); _fits = GE.fits
    def counting_fits(texts):
        ok = _fits(texts); fits_rej["fits_ok" if ok else "over_48_token_cap_KEPT"] += 1; return True   # Ben: no cut-offs; counted, not dropped
    GE.fits = counting_fits
    ex = GE.make(int(a.english_tokens / 25 / 2 * 1.3), 9001, "train", avoid=avoid, kinds=12, block_files=GE.BLOCK_R6)
    over_by_kind = collections.Counter(); n_by_kind = collections.Counter()
    for e in ex:
        n_by_kind[e["family"]] += 1
        if any(len(tok.encode(t + " " + q["question"], add_special_tokens=False)) > GE.CAP for t in (e["source_text"], e["paraphrase"]) for q in e["questions"]):
            over_by_kind[e["family"]] += 1
    eng = []
    for e in ex:
        for qi, q in enumerate(e["questions"]):
            eng.append({"id": f"{e['id']}-q{qi}", "kind": e["family"], "source_text": e["source_text"], "paraphrase": e["paraphrase"],
                        "question": q["question"], "type": q["type"], "canonical_answer": q["canonical_answer"], "accepted_answers": q["accepted_answers"]})
    e_tok = ntok([r["source_text"] + " " + r["question"] + " " + r["canonical_answer"] for r in eng])
    cum, keep = 0, 0
    for i, t in enumerate(e_tok):
        if cum >= a.english_tokens and i % 2 == 0: break   # whole examples (2 questions) only
        cum += t; keep = i + 1
    eng, e_tok = eng[:keep], e_tok[:keep]; E = sum(e_tok); print("english rows", len(eng), "tokens", E, flush=True)

    # ---- skills: water-filling over the 34 train families
    S_budget = RUNGS[-1][1] - T - E
    dev_prompts = set()
    for d in a.dev:
        for fn in os.listdir(d):
            if fn.endswith(".jsonl"):
                dev_prompts |= {json.loads(l)["prompt"] for l in open(os.path.join(d, fn))}
    sys.path.insert(0, a.skills_repo)
    from skills_curriculum import skills  # noqa: F401
    from skills_curriculum.build import train_families
    fams = train_families(); assert len(fams) == FAM_N, len(fams)
    rows_by = {f: [] for f in fams}; capped = set(); drawn = {}; rejects = {}
    est_rows = int(S_budget / 27.0)
    target = {f: est_rows // FAM_N for f in fams}
    for rnd in range(6):
        todo = [f for f in fams if f not in capped]
        with Pool(a.procs) as p:
            res = p.map(skills_worker, [(f, target[f], target[f] * 40, a.skills_repo, dev_prompts) for f in todo], chunksize=1)
        for f, rows, bad, i, rej in res:
            assert bad == 0, (f, bad)
            rows_by[f] = rows; drawn[f] = i; rejects[f] = rej
            if len(rows) < target[f]: capped.add(f)
        have = sum(len(v) for v in rows_by.values())
        short = est_rows - have
        print("round", rnd, "rows", have, "capped", sorted(capped), flush=True)
        if short <= 0 or len(capped) == FAM_N: break
        open_f = [f for f in fams if f not in capped]
        for f in open_f: target[f] = len(rows_by[f]) + short // len(open_f) + 1
    sk = [r for f in fams for r in rows_by[f]]
    s_tok = ntok([r["prompt"] + " " + r["answer"] for r in sk])
    # trim to the token budget by dropping rows from the end of a seeded shuffle (keeps family mix)
    order = list(range(len(sk))); random.Random(11).shuffle(order)
    cum, kept = 0, []
    for i in order:
        if cum + s_tok[i] > S_budget: continue
        cum += s_tok[i]; kept.append(i)
    sk_rows = [sk[i] for i in kept]; sk_t = [s_tok[i] for i in kept]; S = sum(sk_t)
    print("skills rows", len(sk_rows), "tokens", S, flush=True)

    # ---- one shuffle, nested prefixes
    allr = [("skills", r, t) for r, t in zip(sk_rows, sk_t)] + [("english", r, t) for r, t in zip(eng, e_tok)] + [("teach", r, t) for r, t in zip(teach, t_tok)]
    random.Random(20261007).shuffle(allr)
    outs = {s: open(os.path.join(a.out, f"{s}.jsonl"), "w") for s in ("skills", "english", "teach")}
    cum, tot_by = 0, collections.defaultdict(lambda: collections.Counter()); seen_exact, seen_shape = set(), collections.defaultdict(set)
    dup = collections.defaultdict(lambda: collections.Counter())
    for pos, (src, r, t) in enumerate(allr):
        if cum >= RUNGS[-1][1]: break
        cum += t
        rung = next(k for k, lim in RUNGS if cum <= lim) if cum <= RUNGS[-1][1] else 30
        r = dict(r); r["rung"] = rung; r["pos"] = pos
        outs[src].write(json.dumps(r) + "\n")
        text = r["prompt"] if src == "skills" else r["source_text"] + " | " + r["question"]
        shape = re.sub(r"\d+", "#", text) if src == "skills" else text
        for k, _ in RUNGS:
            if k >= rung:
                tot_by[k][src] += t; tot_by[k]["rows_" + src] += 1
                dup[k]["rows"] += 1
                key = (k, text); skey = (k, shape)
                if key in seen_exact: dup[k]["exact"] += 1
                seen_exact.add(key)
                if skey in seen_shape[k]: dup[k]["shape"] += 1
                seen_shape[k].add(skey)
    for f in outs.values(): f.close()
    man = {"budgets": dict(RUNGS), "tokenizer": "LiquidAI/LFM2.5-1.2B-Instruct@0f604ada", "tokens_total": cum,
           "by_rung": {str(k): {"tokens": {s: tot_by[k][s] for s in ("skills", "english", "teach")},
                                "rows": {s: tot_by[k]["rows_" + s] for s in ("skills", "english", "teach")},
                                "exact_duplicate_share": dup[k]["exact"] / max(1, dup[k]["rows"]),
                                "digit_or_name_shape_duplicate_share": dup[k]["shape"] / max(1, dup[k]["rows"])} for k, _ in RUNGS},
           "skills_family_rows": {f: len(rows_by[f]) for f in fams}, "skills_length_filter": "OFF (est_tokens > 62 kept)" if NO_LEN_FILTER else "ON",
           "skills_rejects_by_family": rejects, "skills_rejects_total": dict(sum((collections.Counter(v) for v in rejects.values()), collections.Counter())),
           "skills_rows_over_62_est_tokens_kept": sum(1 for r in sk_rows if r["est_tokens"] > 62),
           "english_gen_filter_counts": dict(fits_rej), "english_gen_filter": "OFF (gen_english.fits forced True; passage+question over 48 tokens kept)",
           "english_examples_over_48_tokens_by_kind": {k: [over_by_kind[k], n_by_kind[k]] for k in n_by_kind}, "capped_families": sorted(capped),
           "sha256": {fn: hashlib.sha256(open(os.path.join(a.out, fn), "rb").read()).hexdigest() for fn in ("skills.jsonl", "english.jsonl", "teach.jsonl")}}
    json.dump(man, open(os.path.join(a.out, "MANIFEST.json"), "w"), indent=1); print(json.dumps(man["by_rung"], indent=1))


if __name__ == "__main__":
    main()
