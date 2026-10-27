#!/usr/bin/env python3
"""dl-7: does a KL anchor on the base's SHAKY short facts stop the forgetting that copy-practice nights cause?
(Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl7-20260926/PASSMARKS.md)

Why. Copy-practice nights (dl-2, registered PASS) learn the day's work but lose 16-39 of the base's 200 right general
panel items by night 7. dl-3 (replay of the base's greedy chat answers) and dl-4 (KL anchor on the base's chat
answers; KL to the base fell about 5x) are registered FAILs: losses stayed at 20-36. fd-1 (artifacts/claude-fd1-20260926,
report-only) found the lost items lean to the base's least confident right answers: 17 of 29 in the lowest third
(fixed bar 60%, missed by one), and 17 of the 19 lost capitals in the less confident half of the base's right capitals.
So the nights mostly knock over thin-margin FACTS, while dl-4's anchor held long chat replies, where the model's
margins are wide (suggested, not shown).

ONE change from dl-4's K arm: the anchor pool. An anchor item is a SHORT QUIZ question the BASE wrote itself plus the
BASE's own greedy short answer, kept only if the base's confidence in that answer (smallest token probability among
its first 4 tokens, fd-1's measure) is in the lowest third of the pool. Questions touching the harm panel's topics are
dropped (dl-3's panel_words: capitals, every panel country and city, opposites, plurals, days, months, letters, counts,
numbers), so the panel is never used to find, pick or train anchor items. Loss = dl-4's KL(base || current) over the
full vocabulary at every answer position, weight 1.0, shuffled with the puzzle examples through dl-2's loop
(3 epochs, lr 2e-4, batch 8, one growing LoRA r16 on q,k,v,o). Arms:
  S  dl-2's night unchanged (claude_dl1_nights.train_copy).
  F  S + the shaky-fact anchor (as many anchor items as puzzle examples, a new random sample each night).
Same day, TEST, HARM (lost = right at base and wrong now) and KL measure as dl-2/3/4/6. New seeds 12 and 13, TEST seed
3290, pool seed 3291.

  python -B scripts/claude_dl7_fragile.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl7_fragile.py --selftest
  python -B scripts/claude_dl7_fragile.py --model M --out DIR --dev  (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402
import claude_dl3_replay as R  # noqa: E402
import claude_dl4_anchor as K  # noqa: E402

TEST_SEED = 3290
POOL_SEED = 3291
ASKS = ("Write one short quiz question about science, history, animals, food, sport, music, the human body or "
        "inventions whose answer is a single word or name. Reply with the question only.",
        "Write one trivia question that has a one-word answer. Reply with the question only.")
SUFFIX = " Reply with the answer only."
MAX_ANS = 16
MIN_FRAGILE = 100


def answer_conf(s, q, m=None):
    """fd-1's measure: the greedy answer, whether it finished within MAX_ANS tokens, and the smallest token
    probability among its first 4 tokens."""
    m = m if m is not None else s.model
    ids = R.chat_ids(s, q).unsqueeze(0).to(s.dev)
    with s.torch.no_grad():
        out = m.generate(input_ids=ids, attention_mask=s.torch.ones_like(ids), max_new_tokens=MAX_ANS,
                         do_sample=False, pad_token_id=s.tok.eos_token_id, output_scores=True,
                         return_dict_in_generate=True)
    gen = out.sequences[0][ids.shape[1]:]
    probs = [float(sc[0].float().softmax(-1)[t]) for sc, t in zip(out.scores, gen)]
    done = int(gen[-1]) == s.tok.eos_token_id or len(gen) < MAX_ANS
    return s.tok.decode(gen, skip_special_tokens=True).strip(), done, (min(probs[:4]) if probs else 0.0)


def make_pool(s, n_ask, seed) -> dict:
    """Base-written short quiz questions (panel topics dropped) + the base's greedy answers + confidence; the
    fragile pool is the lowest-confidence third of the finished, non-empty answers."""
    s.torch.manual_seed(seed)
    bad = R.panel_words()
    qs, seen, left, b = [], set(), n_ask, 0
    while left > 0:
        ids = R.chat_ids(s, ASKS[b % len(ASKS)]).unsqueeze(0).to(s.dev)
        b += 1
        k = min(50, left)
        with s.torch.no_grad():
            out = s.model.generate(input_ids=ids.repeat(k, 1), attention_mask=s.torch.ones_like(ids.repeat(k, 1)),
                                   max_new_tokens=R.MAX_Q, do_sample=True, temperature=1.0, top_p=0.95,
                                   pad_token_id=s.tok.eos_token_id)
        for o in out:
            q = R.clean_question(s.tok.decode(o[ids.shape[1]:], skip_special_tokens=True), bad)
            if q and q.lower() not in seen:
                seen.add(q.lower())
                qs.append(q)
        left -= k
    rows = []
    for q in qs:
        a, done, conf = answer_conf(s, q + SUFFIX)
        if a and done:
            rows.append({"q": q + SUFFIX, "a": a, "conf": round(conf, 4)})
    rows.sort(key=lambda r: r["conf"])
    cut = len(rows) // 3
    return {"asked": n_ask, "questions": len(qs), "answered": len(rows), "fragile": rows[:cut],
            "conf_cut": rows[cut]["conf"] if rows[cut:] else None}


def run_arm(s, arm, seed, a, test, panel, replies, base_harm, fragile) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights, prev = [], base_harm
    items = [(r["q"], r["a"], True) for r in fragile]
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right)}
        if not right:
            rec["train"] = {"examples": 0}
        elif arm == "S":
            rec["train"] = D1.train_copy(s, m, right, seed * 1000 + d)
        else:
            anc = random.Random(seed * 1000 + d).sample(items, min(len(items), len(right)))
            rec["train"] = K.train_anchor(s, m, right, anc, seed * 1000 + d)
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["harm_vs_prev"] = D1.flips(prev, meas["harm"])
        rec["harm_items"] = meas["harm"]
        prev = meas["harm"]
        rec["kl"] = meas["kl"]
        if d == a.nights:                              # report only: what the lost items now say
            rec["lost_replies"] = {str(i): D1.free_answer(s, panel[i]["q"], m)
                                   for i, (b0, n) in enumerate(zip(base_harm, meas["harm"])) if b0 and not n}
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl7] {arm} s{seed} night {d}: " + json.dumps(
            {k: v for k, v in rec.items() if k not in ("harm_items", "lost_replies")}), flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md): dl-3's F1-F5 with F in place of A; INCONCLUSIVE also if the fragile
    pool holds fewer than MIN_FRAGILE items."""
    sub = {"base": res["base"], "pool_size": 100 if res.get("fragile_size", 0) >= MIN_FRAGILE else 0,
           "arms": [dict(r, arm="A" if r["arm"] == "F" else r["arm"]) for r in res["arms"]]}
    m3 = R.score(sub)
    return {k.replace("A_", "F_").replace(": A ", ": F ").replace(" A ", " F "): v for k, v in m3.items()}


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    pool = make_pool(s, a.n_ask, POOL_SEED + a.seed_shift)
    (out / "fragile_pool.json").write_text(json.dumps(pool, indent=0), encoding="utf-8")
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED, "beta": K.BETA,
           "pool": {k: v for k, v in pool.items() if k != "fragile"}, "fragile_size": len(pool["fragile"])}
    print(f"[dl7] pool: {res['pool']} fragile {res['fragile_size']}", flush=True)
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    res["base_harm_items"] = bm["harm"]
    res["base_panel_conf"] = [round(answer_conf(s, it["q"])[2], 4) for it in panel]   # report only
    print(f"[dl7] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"], pool["fragile"]))
            (out / "dl7_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= {"S", "F"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl7_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    def arm(name, sd, lucky, lost, reached=40):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v, "reached": reached},
                                                      "harm": {"lost": l}} for v, l in zip(lucky, lost)]}
    res = {"base": {"lucky": 60, "reached": 35}, "fragile_size": 250,
           "arms": [arm("S", 12, [90, 100, 110, 120, 125, 130, 140], [5, 8, 12, 16, 18, 24, 26]),
                    arm("S", 13, [80, 95, 90, 110, 120, 128, 135], [6, 9, 11, 15, 20, 28, 25]),
                    arm("F", 12, [85, 100, 105, 118, 120, 125, 130], [3, 4, 6, 5, 7, 8, 9]),
                    arm("F", 13, [85, 92, 99, 110, 115, 120, 128], [4, 5, 4, 6, 8, 7, 10])]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    assert any(k.startswith("F1") and ": F " in k for k in m), list(m)
    res["fragile_size"] = 99
    assert score(res)["verdict"] == "INCONCLUSIVE"
    res["fragile_size"] = 250
    res["arms"][2]["nights"][-1]["harm"]["lost"] = 26
    assert score(res)["verdict"] == "FAIL"
    bad = R.panel_words()
    assert R.clean_question("What is the capital of Freedonia?", bad) is None
    assert R.clean_question("Which planet is known as the red planet?", bad)
    assert K.BETA == 1.0
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,F")
    ap.add_argument("--seeds", default="12,13")
    ap.add_argument("--nights", type=int, default=7)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--n-ask", type=int, default=3000)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl, a.n_ask = 1, 4, 4, 3, 3, 12, 4, 60
        a.seed_shift, a.seeds = a.seed_shift or 60000, "12"
    run(a)


if __name__ == "__main__":
    main()
