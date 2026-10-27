#!/usr/bin/env python3
"""dl-9: does keeping the night's learning in a SEPARATE expert, switched on per question by a LEARNED switch, stop
the forgetting while keeping the learning? (Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl9-20260926/
PASSMARKS.md). Ben's idea, 19:15 UTC via the Thread manager: "What if we separated parts of the brain?" ... "like we
did a mixture of expert style thing."

Why. Every copy-practice night so far (dl-2..dl-6) trains one always-on adapter, and it answers every question
afterwards. dl-5's carry row (artifacts/claude-dl5-20260926/CARRY.md) found 299-300 of 300 panel replies took the grid
answer's shape with that adapter on; dl-6 found forgetting tracks the total amount trained. Whether this spill onto
unrelated questions causes the forgetting is untested. Brain first: the cortex keeps skills in partly separate
circuits and the prefrontal cortex / basal ganglia gate which one runs for the task at hand (context-dependent gating,
suggested as a guard against interference). Silicon version, simplest form first: the night's adapter is the expert;
the frozen 1B answers everything else; a small learned switch reads each question and turns the whole adapter on or off.

ONE change from dl-2's night (claude_dl1_nights.train_copy, 3 epochs, lr 2e-4, batch 8, one growing LoRA r16 on
q,k,v,o): how the trained model is SERVED. Training is identical, so each seed trains one adapter and three ways of
serving it are measured on the same answers:
  S  adapter always on (dl-2 as served until now).
  X  learned switch: adapter on only for questions the switch says belong to the expert; otherwise the frozen base.
  R  random switch with X's on-rate over the same questions (control: "on less often" without choosing).
Because the frozen base is the adapter at scale 0 and panel answers are greedy, X and R reuse the per-question answers
of the base and of the adapter; nothing is generated twice.
The switch: logistic regression on the FROZEN base's last-layer hidden state at the last prompt token. Labels are
code-made from where the item came from: 1 = a day puzzle the night practised (every puzzle of nights 1..d, solved or
not); 0 = a short quiz question the BASE wrote itself (dl-7's pool recipe, panel topics dropped, seed 3091), half of
them with GLM 5.3 Flash's answer-only suffix appended so "answer only" wording is not a cue. No rule, no Claude text
in the switch's inputs. Refit each night; 20% of the base's questions are held out to measure it.
Puzzle instruction: GLM 5.3 Flash's (claude_dl6c_glmframe, sha-pinned); targets are the 1B's own code-checked
expressions. Seeds 16 and 17, 7 nights, TEST seed 3090, HARM = the 300-item panel (lost = right at base, wrong now).
Report-only: the switch's on-rate per panel kind (count and bigger are number questions, the hardest to route);
and at night 7 a reworded row: TEST puzzles under GLM's four other candidate wordings (never trained), greedy solves
with the base, with the adapter, and served by the switch.

  python -B scripts/claude_dl9_experts.py --selftest
  python -B scripts/claude_dl9_experts.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl9_experts.py --model M --out DIR --dev  (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_blurt1 as B1  # noqa: E402
import claude_dl6c_glmframe as G  # noqa: E402

TEST_SEED = 3090
POOL_SEED = 3091
MODES = ("S", "X", "R")


def glm_texts() -> tuple[str, list[str], str]:
    """The chosen GLM puzzle frame, the four other GLM candidate frames, and GLM's chosen suffix (sha-pinned file)."""
    import hashlib
    raw = G.FRAMES.read_bytes()
    if hashlib.sha256(raw).hexdigest() != G.FRAMES_SHA256:
        raise SystemExit("frames.json sha256 does not match the pin")
    d = json.loads(raw.decode("utf-8"))
    chosen = d["puzzle"]["chosen"]
    others = [c["text"] for c in d["puzzle"]["candidates"] if c["ok"] and c["text"] != chosen]
    return chosen, others, d["suffix"]["chosen"]


def question_pool(s, n_ask, seed) -> list[str]:
    """dl-7's recipe, questions only: the base writes short quiz questions; panel topics and digits are dropped."""
    import claude_dl3_replay as R
    import claude_dl7_fragile as F7
    s.torch.manual_seed(seed)
    bad = R.panel_words()
    qs, seen, left, b = [], set(), n_ask, 0
    while left > 0:
        ids = R.chat_ids(s, F7.ASKS[b % len(F7.ASKS)]).unsqueeze(0).to(s.dev)
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
    return qs


def chat_text(s, q: str) -> str:
    return s.tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                     enable_thinking=False)


def feats(s, texts: list[str]):
    """Frozen base, last layer, last prompt token (the position the answer starts from)."""
    rows = []
    with s.torch.no_grad():
        for t in texts:
            ids = s.tok(t, return_tensors="pt").to(s.dev)
            h = s.model(**ids, output_hidden_states=True).hidden_states[-1][0, -1]
            rows.append(h.float().cpu())
    return s.torch.stack(rows) if rows else s.torch.zeros(0, 1)


def fit_switch(torch, X, y, seed, steps=400) -> dict:
    """Class-balanced logistic regression on standardised features (the switch's only learned parameters)."""
    g = torch.Generator().manual_seed(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    w = (torch.randn(Z.shape[1], generator=g) * 0.01).requires_grad_()
    b = torch.zeros(1, requires_grad=True)
    pos = float(y.sum())
    wt = torch.where(y > 0, len(y) / (2 * max(pos, 1)), len(y) / (2 * max(len(y) - pos, 1)))
    opt = torch.optim.Adam([w, b], lr=1e-2, weight_decay=1e-3)
    for _ in range(steps):
        opt.zero_grad()
        loss = (torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b, y, reduction="none") * wt).mean()
        loss.backward()
        opt.step()
    return {"mu": mu, "sd": sd, "w": w.detach(), "b": b.detach(), "train_loss": round(float(loss.detach()), 5)}


def switch_on(sw, X) -> list[bool]:
    if len(X) == 0:
        return []
    return [bool(v) for v in (((X - sw["mu"]) / sw["sd"]) @ sw["w"] + sw["b"] > 0).tolist()]


def per_puzzle(s, m, ps, n, temp) -> tuple[list[int], list[int]]:
    """Right sampled guesses per puzzle (n at temp) and greedy right per puzzle."""
    hits = [sum(B1.check(t, p["nums"], p["target"]) for t in s.generate(p, n, temp, m)) for p in ps]
    greedy = [int(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"])) for p in ps]
    return hits, greedy


def serve(on: list[bool], adapter: list, base: list) -> list:
    return [a if o else b for o, a, b in zip(on, adapter, base)]


def random_gate(n_items: int, n_on: int, seed: int) -> list[bool]:
    on = set(random.Random(seed).sample(range(n_items), n_on))
    return [i in on for i in range(n_items)]


def with_frame(frame: str, fn):
    old = B1.puzzle_prompt
    B1.puzzle_prompt = G.make_prompt(frame)
    try:
        return fn()
    finally:
        B1.puzzle_prompt = old


def run_seed(s, seed, a, ctx) -> dict:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    torch = s.torch
    torch.manual_seed(seed)
    m = D1.fresh_model(s)
    test, panel, base = ctx["test"], ctx["panel"], ctx["base"]
    nT, nP = len(test), len(panel)
    pos_feats, nights = [], []
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right)}
        rec["train"] = D1.train_copy(s, m, right, seed * 1000 + d) if right else {"examples": 0}
        # the switch: day puzzles practised so far (1) vs the base's own questions (0); frozen-base features
        pos_feats.append(feats(s, [s.prompt(p) for p in day]))
        P = torch.cat(pos_feats)
        N = ctx["neg_train"]
        sw = fit_switch(torch, torch.cat([P, N]), torch.cat([torch.ones(len(P)), torch.zeros(len(N))]),
                        seed * 1000 + d)
        on_test, on_panel = switch_on(sw, ctx["f_test"]), switch_on(sw, ctx["f_panel"])
        on_held = switch_on(sw, ctx["neg_held"])
        rec["switch"] = {"train_rows": [len(P), len(N)], "train_loss": sw["train_loss"],
                         "test_on": sum(on_test), "panel_on": sum(on_panel), "held_neg_on": sum(on_held),
                         "held_neg": len(on_held),
                         "panel_on_by_kind": {k: sum(o for o, it in zip(on_panel, panel) if it["kind"] == k)
                                              for k in ctx["kinds"]}}
        # the adapter's own answers, once; S / X / R are ways of serving them
        m.eval()
        hits, greedy = per_puzzle(s, m, test, a.n_guess_test, D1.TEMP)
        harm = D1.harm_scores(s, m, panel)
        rg = random_gate(nT + nP, sum(on_test) + sum(on_panel), seed * 1000 + d)
        gates = {"S": ([True] * nT, [True] * nP), "X": (on_test, on_panel), "R": (rg[:nT], rg[nT:])}
        for k, (gt, gp) in gates.items():
            h, gr, hm = serve(gt, hits, base["hits"]), serve(gt, greedy, base["greedy"]), serve(gp, harm, base["harm"])
            rec[k] = {"lucky": sum(h), "reached": sum(x > 0 for x in h), "greedy": sum(gr),
                      "harm": D1.flips(base["harm"], hm), "on": sum(gt) + sum(gp)}
        rec["lost_items_S"] = [i for i, (b0, x) in enumerate(zip(base["harm"], harm)) if b0 and not x]
        rec["lost_items_S_switched_on"] = sum(on_panel[i] for i in rec["lost_items_S"])
        rec["harm_items_adapter"] = harm
        rec["kl_S"] = D1.kl_to_base(s, m, ctx["replies"])
        if d == a.nights:
            rec["reworded"] = []
            for fr, fb, ff in zip(ctx["other_frames"], ctx["reword_base"], ctx["f_reword"]):
                gm = with_frame(fr, lambda: [int(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"]))
                                             for p in test])
                on = switch_on(sw, ff)
                rec["reworded"].append({"frame": fr, "switch_on": sum(on), "greedy_base": sum(fb),
                                        "greedy_adapter": sum(gm), "greedy_X": sum(serve(on, gm, fb))})
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl9] s{seed} night {d}: " + json.dumps({k: v for k, v in rec.items() if k != "harm_items_adapter"}),
              flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md), on night 7."""
    L0 = res["base"]["lucky"]
    fin = {r["seed"]: r["nights"][-1] for r in res["seeds"]}
    seeds = sorted(fin)
    lost = {k: [fin[sd][k]["harm"]["lost"] for sd in seeds] for k in MODES}
    luck = {k: [fin[sd][k]["lucky"] for sd in seeds] for k in MODES}
    gain = {k: [x - L0 for x in luck[k]] for k in MODES}
    t_on = [fin[sd]["switch"]["test_on"] for sd in seeds]
    p_on = [fin[sd]["switch"]["panel_on"] for sd in seeds]
    n_t, n_p = res["n_test"], res["n_harm"]
    m = {"L0": L0, "final_lost": lost, "final_lucky": luck, "gain_over_L0": gain, "switch_test_on": t_on,
         "switch_panel_on": p_on}
    m["H1 forgetting stopped: X lost <= 5 on each seed, and X lost <= 0.25 x S lost (sums)"] = \
        max(lost["X"]) <= 5 and sum(lost["X"]) <= 0.25 * sum(lost["S"])
    m["H2 learning kept: X gain >= 0.9 x S gain on each seed"] = \
        all(gx >= 0.9 * gs for gx, gs in zip(gain["X"], gain["S"]))
    m["H3 switch learned: on for >= 95% of TEST puzzles and off for >= 95% of panel items, each seed"] = \
        all(t >= 0.95 * n_t for t in t_on) and all(p <= 0.05 * n_p for p in p_on)
    m["H4 choosing beats chance: X gain >= 2 x R gain and X lost <= R lost (sums)"] = \
        sum(gain["X"]) >= 2 * sum(gain["R"]) and sum(lost["X"]) <= sum(lost["R"])
    keys = [k for k in m if k[:1] == "H" and k[1].isdigit()]
    m["verdict"] = ("INCONCLUSIVE" if L0 < 10 or sum(lost["S"]) < 20 else
                    ("PASS" if all(m[k] for k in keys) else "FAIL"))
    m["proved_wrong"] = any(lx > 0.5 * ls for lx, ls in zip(lost["X"], lost["S"])) or \
        any(gx < 0.8 * gs for gx, gs in zip(gain["X"], gain["S"]))
    return m


def run(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    frame, other_frames, suffix = glm_texts()
    B1.puzzle_prompt = G.make_prompt(frame)            # Solver.prompt looks it up on the module
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED, "pool_seed": POOL_SEED, "frame": frame,
           "other_frames": other_frames, "suffix": suffix, "frame_sha256": G.FRAMES_SHA256}
    qs = question_pool(s, a.n_ask, POOL_SEED + a.seed_shift)
    rng = random.Random(POOL_SEED)
    rng.shuffle(qs)
    cut = int(0.8 * len(qs))
    tag = [rng.random() < 0.5 for _ in qs]
    neg = [q + " " + suffix if t else q for q, t in zip(qs, tag)]
    res["pool"] = {"asked": a.n_ask, "questions": len(qs), "train": cut, "held": len(qs) - cut,
                   "with_suffix": sum(tag), "sample": qs[:5]}
    print(f"[dl9] pool: {json.dumps(res['pool'])}", flush=True)
    ctx = {"test": test, "panel": panel, "other_frames": other_frames,
           "kinds": sorted({it["kind"] for it in panel})}
    ctx["neg_train"] = feats(s, [chat_text(s, q) for q in neg[:cut]])
    ctx["neg_held"] = feats(s, [chat_text(s, q) for q in neg[cut:]])
    ctx["f_test"] = feats(s, [s.prompt(p) for p in test])
    ctx["f_panel"] = feats(s, [chat_text(s, it["q"]) for it in panel])
    ctx["f_reword"] = [with_frame(fr, lambda: feats(s, [s.prompt(p) for p in test])) for fr in other_frames]
    base = s.model
    ctx["replies"] = [(q, D1.free_answer(s, q, base, 40)) for q in
                      (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    s.torch.manual_seed(TEST_SEED)
    hits, greedy = per_puzzle(s, base, test, a.n_guess_test, D1.TEMP)
    ctx["base"] = {"hits": hits, "greedy": greedy, "harm": D1.harm_scores(s, base, panel)}
    ctx["reword_base"] = [with_frame(fr, lambda: [int(B1.check(s.generate(p, 1, None, base)[0], p["nums"],
                                                                 p["target"])) for p in test])
                          for fr in other_frames]
    res["base"] = {"lucky": sum(hits), "reached": sum(h > 0 for h in hits), "greedy": sum(greedy),
                   "harm_right": sum(ctx["base"]["harm"]), "reworded_greedy": [sum(x) for x in ctx["reword_base"]]}
    res["base_harm_items"] = ctx["base"]["harm"]
    print(f"[dl9] base: {res['base']}", flush=True)
    res["seeds"] = []
    for sd in seeds:
        res["seeds"].append(run_seed(s, sd, a, ctx))
        (out / "dl9_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if len(seeds) >= 2:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl9_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    import torch

    def night(lx, ls, lr, gx, gs, gr, t_on=100, p_on=3):
        return {"S": {"lucky": 60 + gs, "harm": {"lost": ls}}, "X": {"lucky": 60 + gx, "harm": {"lost": lx}},
                "R": {"lucky": 60 + gr, "harm": {"lost": lr}}, "switch": {"test_on": t_on, "panel_on": p_on}}
    res = {"base": {"lucky": 60}, "n_test": 100, "n_harm": 300,
           "seeds": [{"seed": 16, "nights": [night(1, 25, 6, 170, 175, 45)]},
                     {"seed": 17, "nights": [night(2, 20, 5, 160, 170, 40)]}]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["seeds"][0]["nights"][0] = night(14, 25, 6, 170, 175, 45, p_on=40)
    m = score(res)
    assert m["verdict"] == "FAIL" and m["proved_wrong"], m
    assert serve([True, False], [1, 1], [0, 0]) == [1, 0]
    g = random_gate(10, 4, 1)
    assert sum(g) == 4 and len(g) == 10
    X = torch.cat([torch.randn(40, 6) + 3, torch.randn(40, 6) - 3])
    y = torch.cat([torch.ones(40), torch.zeros(40)])
    sw = fit_switch(torch, X, y, 0)
    on = switch_on(sw, X)
    assert sum(on[:40]) >= 38 and sum(on[40:]) <= 2, sum(on)
    frame, others, suffix = glm_texts()
    assert frame.count("{NUMS}") == 1 and len(others) == 4 and all(o.count("{TARGET}") == 1 for o in others)
    assert suffix == "Answer only, no explanation."
    print("dl9 selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--seeds", default="16,17")
    ap.add_argument("--nights", type=int, default=7)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--n-ask", type=int, default=1000)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl, a.n_ask = 2, 4, 4, 3, 3, 12, 4, 20
        a.seed_shift, a.seeds = a.seed_shift or 60000, "16"
    run(a)


if __name__ == "__main__":
    main()
