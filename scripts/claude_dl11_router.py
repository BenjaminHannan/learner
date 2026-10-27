#!/usr/bin/env python3
"""dl-11: can a learned router pick the right skill among LOOK-ALIKE requests, keep what each night learned, and stop
the forgetting? (Fix-sleep thread, 2026-09-27; marks: artifacts/claude-dl11-20260927/PASSMARKS.md.) Next step after
dl-9 (PASS, one expert, kinds that look nothing alike). Ben 11:34 09-27: "It should for each request be able to
automatically decide what."

Two skills made of numbers, practised each night on one frozen MiniCPM5-1B:
  P  dl-9's day puzzles ("make the target from these numbers"), GLM 5.3 Flash's frame (sha-pinned); targets are the
     1B's own code-checked expressions (dl-2's copy rows); RuleKeeper scaffolding as in every dl run.
  Q  code-made arithmetic (two numbers: + or - on 2..99, * on 2..19); Luna's frame; an expression enters the
     night's rows if the 1B got it right at least once (greedy + N_QG samples); the row's target is the code-made
     bare value.
Each night the P-expert and the Q-expert each gather their own day and train on their own rows; S (one shared
adapter) trains on exactly the same P and Q rows together. All are LoRA r16 on q,k,v,o with dl-2's recipe (3 epochs,
lr 2e-4, batch 8, AdamW), growing over nights. The base is frozen throughout.

Router: 3-way logistic regression (base / P / Q) on the frozen base's last-layer state at the last prompt token
(dl-9's switch with three outputs), refit each night. Labels come from where an item came from: P = every P day item
so far, Q = every Q day item so far, base = the base's own quiz questions (dl-9's recipe) plus Luna's look-alike
everyday number questions (claude_dl11_luna.py), 80% fit / 20% held out, half with GLM's answer-only suffix. No kind
label is an input; no hand-written routing rule; no Claude-written text in any training row or router input.

Serving arms, all generated live at the last night with the same torch seed per pass:
  S  shared adapter always on        X  router's choice (base, P-expert or Q-expert)
  M  soft: P-expert at p(P) and Q-expert at p(Q)   R  X's choices shuffled over the same 600 requests
  O  oracle, report-only: the true kind picks the expert (panel -> base)
  AP / AQ  report-only: the P-expert / the Q-expert always on (each expert's own spill, no router; S trains on about
     twice the rows of either expert)
Night 1 and every night: the router's choices only (no generation).
Q is scored lenient (last integer in the reply is the value; graded) and strict (bare value; reported). Report-only
rows at the last night: P and Q under their other frames, and the first 100 Q TEST items written in words by code
(does the router route on content or on symbols?).

  python -B scripts/claude_dl11_router.py --selftest
  python -B scripts/claude_dl11_router.py --model M --out DIR                    (registered run)
  python -B scripts/claude_dl11_router.py --model M --out DIR --dev --luna F     (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import claude_blurt1 as B1  # noqa: E402
import claude_dl6c_glmframe as G  # noqa: E402
import claude_dl9_experts as E  # noqa: E402

LUNA = ROOT / "artifacts/claude-dl11-20260927/luna/luna_texts.json"
P_TEST_SEED, Q_TEST_SEED, POOL_SEED, LOOK_SEED = 2990, 2991, 2992, 2993
Q_DAY_SEED = 2800                      # Q day d of seed s: expressions(Q_DAY_SEED + shift + 100 * s + d)
Q_TEMP, Q_MAX = 0.7, 16
NAMES = ("S", "P", "Q")
KINDS = ("base", "P", "Q")
ARMS = ("S", "X", "M", "R", "O", "AP", "AQ")
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
OPW = {"+": "plus", "-": "minus", "*": "times"}


# ---------------------------------------------------------------- Q: code-made expressions
def expressions(seed, n) -> list[dict]:
    """Two numbers and one operation: + or - on 2..99, * on 2..19 (CPU probe 09-27, dev seed: the 1B answered
    3-4-number expressions right 0 of 30 with a number-only reply, and 2-number ones 5 of 20 greedy, 9 of 20 at least
    once in 11 tries, so this size leaves room to learn)."""
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:
        op = rng.choice("+-*")
        hi = 19 if op == "*" else 99
        expr = f"{rng.randint(2, hi)} {op} {rng.randint(2, hi)}"
        if expr in seen:
            continue
        seen.add(expr)
        out.append({"id": f"ex-s{seed}-{len(out) + 1:03d}", "expr": expr, "value": int(eval(expr))})  # code-made
    return out


def q_text(frame: str, e: dict) -> str:
    return frame.replace("{EXPR}", e["expr"])


# ---------------------------------------------------------------- several LoRA sets on one frozen model
class Mixer:
    def __init__(self):
        self.w = {n: 0.0 for n in NAMES}

    def set(self, **kw):
        self.w = {n: float(kw.get(n, 0.0)) for n in NAMES}


def add_multi_lora(model, mixer, r=16, alpha=32, dropout=0.05, names=("q_proj", "k_proj", "v_proj", "o_proj")):
    """claude_blurt2.add_lora with one (A, B) pair per expert name; each adds scale * mixer.w[name] * B@A x.
    B starts at zero, so every expert starts exactly as the base."""
    import math
    import torch
    nn = torch.nn

    class MultiLoRALinear(nn.Module):
        def __init__(self, base):
            super().__init__()
            self.base = base
            dev = base.weight.device
            self.A = nn.ParameterDict({n: nn.Parameter(torch.empty(r, base.in_features, dtype=torch.float32,
                                                                   device=dev)) for n in NAMES})
            self.B = nn.ParameterDict({n: nn.Parameter(torch.zeros(base.out_features, r, dtype=torch.float32,
                                                                   device=dev)) for n in NAMES})
            for n in NAMES:
                nn.init.kaiming_uniform_(self.A[n], a=math.sqrt(5))
            self.drop, self.scale = nn.Dropout(dropout), alpha / r

        def forward(self, x):
            y = self.base(x)
            for n, w in mixer.w.items():
                if w:
                    y = y + ((self.drop(x).float() @ self.A[n].t() @ self.B[n].t()) * (self.scale * w)).to(x.dtype)
            return y

    for prm in model.parameters():
        prm.requires_grad_(False)
    for _, mod in list(model.named_modules()):
        for child, sub in list(mod.named_children()):
            if child in names and isinstance(sub, nn.Linear):
                setattr(mod, child, MultiLoRALinear(sub))
    return model


def expert_params(m, name) -> list:
    return [p for k, p in m.named_parameters() if p.requires_grad and k.endswith("." + name)]


def fresh_model(s, mixer):
    import torch
    from transformers import AutoModelForCausalLM
    base = AutoModelForCausalLM.from_pretrained(s.model.name_or_path, trust_remote_code=True,
                                                dtype=torch.bfloat16).to(s.dev)
    return add_multi_lora(base, mixer).eval()


def train_rows(s, m, mixer, name, rows, seed, epochs=3, lr=2e-4) -> dict:
    """claude_dl1_nights.train_copy on (prompt text, target) rows, updating only expert `name` (the others off)."""
    import torch
    torch.manual_seed(seed)
    mixer.set(**{name: 1.0})
    opt = torch.optim.AdamW(expert_params(m, name), lr=lr)
    rng, last = random.Random(seed), 0.0
    m.train()
    for _ in range(epochs):
        ex = list(rows)
        rng.shuffle(ex)
        for i in range(0, len(ex), 8):
            batch = ex[i:i + 8]
            tot = 0.0
            for prompt, target in batch:
                pr = s.tok(prompt, return_tensors="pt")["input_ids"][0]
                an = s.tok(target, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
                ids = torch.cat([pr, an, torch.tensor([s.tok.eos_token_id])]).unsqueeze(0).to(s.dev)
                lab = ids.clone()
                lab[0, :len(pr)] = -100
                loss = m(input_ids=ids, labels=lab).loss / len(batch)
                loss.backward()
                tot += float(loss.detach())
            opt.step()
            opt.zero_grad()
            last = tot
    m.eval()
    mixer.set()
    return {"rows": len(rows), "last_loss": round(last, 4)}


# ---------------------------------------------------------------- answering
def q_answers(s, model, text: str, n: int) -> list[str]:
    """Greedy (n=0) or n samples at Q_TEMP, free text, no rule-keeper."""
    ids = s.tok(E.chat_text(s, text), return_tensors="pt").to(s.dev)
    kw = {"do_sample": True, "temperature": Q_TEMP, "top_p": 1.0, "num_return_sequences": n} if n else \
         {"do_sample": False}
    with s.torch.no_grad():
        out = model.generate(**ids, max_new_tokens=Q_MAX, pad_token_id=s.tok.eos_token_id, **kw)
    return [s.tok.decode(o[ids["input_ids"].shape[1]:], skip_special_tokens=True).strip() for o in out]


def q_right(reply: str, e: dict) -> int:
    """Lenient (graded): the LAST integer in the reply is the value. (Not "anywhere": an echoed expression such as
    "6 - 3" would then count whenever the value equals an operand.)"""
    import re
    ints = re.findall(r"-?\d+", reply.replace(",", ""))
    return int(bool(ints) and int(ints[-1]) == e["value"])


def q_strict(reply: str, e: dict) -> int:
    """Strict: the reply is the bare value and nothing else."""
    import re
    t = reply.strip().rstrip(".")
    return int(bool(re.fullmatch(r"-?\d+", t)) and int(t) == e["value"])


def num_words(n: int) -> str:
    if n < 0:
        return "minus " + num_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    return ONES[n // 100] + " hundred" + (" and " + num_words(n % 100) if n % 100 else "")


def words_expr(e: dict) -> dict:
    """The same two-number item written in words by code ("seven times eleven"), report-only."""
    a, op, b = e["expr"].split()
    return dict(e, expr=f"{num_words(int(a))} {OPW[op]} {num_words(int(b))}")


def gather_q(s, m, frame, day, n_guess) -> tuple[list, int]:
    rows, greedy = [], 0
    for e in day:
        t = q_text(frame, e)
        g = q_right(q_answers(s, m, t, 0)[0], e)
        greedy += g
        if g or any(q_right(x, e) for x in q_answers(s, m, t, n_guess)):
            rows.append((E.chat_text(s, t), str(e["value"])))
    return rows, greedy


# ---------------------------------------------------------------- router
def fit_router(torch, X, y, seed, steps=400) -> dict:
    """Class-balanced 3-way logistic regression on standardised features (dl-9's fit_switch with three outputs)."""
    g = torch.Generator().manual_seed(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    W = (torch.randn(Z.shape[1], 3, generator=g) * 0.01).requires_grad_()
    b = torch.zeros(3, requires_grad=True)
    cnt = torch.bincount(y, minlength=3).float().clamp(min=1)
    wt = len(y) / (3 * cnt)
    opt = torch.optim.Adam([W, b], lr=1e-2, weight_decay=1e-3)
    for _ in range(steps):
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(Z @ W + b, y, weight=wt)
        loss.backward()
        opt.step()
    return {"mu": mu, "sd": sd, "W": W.detach(), "b": b.detach(), "train_loss": round(float(loss.detach()), 5)}


def route(rt, X) -> list[list[float]]:
    """Probabilities (base, P, Q) per row."""
    if len(X) == 0:
        return []
    return (((X - rt["mu"]) / rt["sd"]) @ rt["W"] + rt["b"]).softmax(-1).tolist()


def choice(pr: list[float]) -> int:
    return max(range(3), key=lambda k: pr[k])


def weights(arm: str, pr, kind_true: int, pick: int) -> dict:
    if arm == "S":
        return {"S": 1.0}
    if arm in ("AP", "AQ"):
        return {arm[1]: 1.0}
    if arm == "M":
        return {"P": pr[1], "Q": pr[2]}
    k = kind_true if arm == "O" else pick
    return {KINDS[k]: 1.0} if k else {}


def shuffled_choices(picks: list[int], seed: int) -> list[int]:
    out = list(picks)
    random.Random(seed).shuffle(out)
    return out


# ---------------------------------------------------------------- one serving pass
def serve_pass(s, m, mixer, ctx, ws: list[dict], seed: int) -> dict:
    """ws: per-request expert weights over [P TEST..., Q TEST..., panel...]."""
    import claude_dl1_nights as D1
    s.torch.manual_seed(seed)
    tp, tq, panel = ctx["p_test"], ctx["q_test"], ctx["panel"]
    hits, greedy, qr, qs, harm = [], [], [], [], []
    for i, p in enumerate(tp):
        mixer.set(**ws[i])
        hits.append(sum(B1.check(t, p["nums"], p["target"]) for t in s.generate(p, ctx["n_guess_test"], D1.TEMP, m)))
        greedy.append(int(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"])))
    for j, e in enumerate(tq):
        mixer.set(**ws[len(tp) + j])
        r = q_answers(s, m, q_text(ctx["q_frame"], e), 0)[0]
        qr.append(q_right(r, e))
        qs.append(q_strict(r, e))
    for k, it in enumerate(panel):
        mixer.set(**ws[len(tp) + len(tq) + k])
        harm.append(int(D1.harm_right(it, D1.free_answer(s, it["q"], m))))
    mixer.set()
    return {"hits": hits, "greedy": greedy, "q_right": qr, "q_strict": qs, "harm": harm}


def summarize(p: dict, base: dict) -> dict:
    import claude_dl1_nights as D1
    fl = D1.flips(base["harm"], p["harm"])
    return {"lucky": sum(p["hits"]), "reached": sum(h > 0 for h in p["hits"]), "greedy": sum(p["greedy"]),
            "q_right": sum(p["q_right"]), "q_strict": sum(p["q_strict"]), "harm": fl}


def spill_kept(base_h, s_h, arm_h) -> dict:
    gs = [i for i, (b, x) in enumerate(zip(base_h, s_h)) if x and not b]
    kept = sum(arm_h[i] for i in gs)
    share = kept / len(gs) if gs else 0.0
    grade = "none" if share < 0.10 else ("some" if share < 0.50 else "most")
    return {"S_gained": len(gs), "kept": kept, "share": round(share, 3), "grade": grade}


# ---------------------------------------------------------------- one seed
def run_seed(s, seed, a, ctx) -> dict:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    torch = s.torch
    torch.manual_seed(seed)
    mixer = Mixer()
    m = fresh_model(s, mixer)
    feats_p, feats_q, nights = [], [], []
    rt = None
    for d in range(1, a.nights + 1):
        t0 = time.time()
        pday = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        qday = expressions(Q_DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        mixer.set(P=1.0)
        groups = D1.gather(s, m, pday, a.n_guess)
        prows = [(s.prompt(p), expr) for p, expr in D1.copy_examples(groups)]
        mixer.set(Q=1.0)
        qrows, q_greedy = gather_q(s, m, ctx["q_frame"], qday, a.n_qguess)
        mixer.set()
        rec = {"night": d, "p_day_greedy_right": sum(g["greedy_right"] for g in groups),
               "p_rows": len(prows), "q_day_greedy_right": q_greedy, "q_rows": len(qrows)}
        rec["train"] = {n: (train_rows(s, m, mixer, n, rows, seed * 1000 + d * 10 + i) if rows else {"rows": 0})
                        for i, (n, rows) in enumerate((("P", prows), ("Q", qrows), ("S", prows + qrows)))}
        feats_p.append(E.feats(s, [s.prompt(p) for p in pday]))
        feats_q.append(E.feats(s, [E.chat_text(s, q_text(ctx["q_frame"], e)) for e in qday]))
        FP, FQ, FN = torch.cat(feats_p), torch.cat(feats_q), ctx["neg_fit"]
        rt = fit_router(torch, torch.cat([FN, FP, FQ]),
                        torch.cat([torch.zeros(len(FN)), torch.ones(len(FP)), 2 * torch.ones(len(FQ))]).long(),
                        seed * 1000 + d)
        rec["router"] = router_report(rt, ctx, len(FN), len(FP), len(FQ))
        if d == a.nights:
            rec.update(final_arms(s, m, mixer, rt, ctx, seed * 1000 + d))
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl11] s{seed} night {d}: " + json.dumps({k: v for k, v in rec.items() if k != "items"}), flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"seed": seed, "nights": nights}


def router_report(rt, ctx, n_neg, n_p, n_q) -> dict:
    picks = {k: [choice(p) for p in route(rt, ctx["f"][k])] for k in ("p_test", "q_test", "panel", "look_held",
                                                                       "pool_held")}
    cnt = {k: [sum(c == j for c in v) for j in range(3)] for k, v in picks.items()}
    panel = ctx["panel"]
    by_kind = {kd: [sum(c == j for c, it in zip(picks["panel"], panel) if it["kind"] == kd) for j in range(3)]
               for kd in ctx["kinds"]}
    return {"train_rows": [n_neg, n_p, n_q], "train_loss": rt["train_loss"],
            "p_test_to_P": cnt["p_test"][1], "q_test_to_Q": cnt["q_test"][2], "panel_to_base": cnt["panel"][0],
            "bigger_to_base": by_kind.get("bigger", [0, 0, 0])[0], "look_held_to_base": cnt["look_held"][0],
            "pool_held_to_base": cnt["pool_held"][0], "counts_base_P_Q": cnt, "panel_by_kind_base_P_Q": by_kind}


def final_arms(s, m, mixer, rt, ctx, seed) -> dict:
    tp, tq, panel = ctx["p_test"], ctx["q_test"], ctx["panel"]
    probs = route(rt, ctx["f"]["p_test"]) + route(rt, ctx["f"]["q_test"]) + route(rt, ctx["f"]["panel"])
    true = [1] * len(tp) + [2] * len(tq) + [0] * len(panel)
    picks = [choice(p) for p in probs]
    rpicks = shuffled_choices(picks, seed)
    out, items = {}, {}
    for arm in ARMS:
        pk = rpicks if arm == "R" else picks
        ws = [weights(arm, pr, t, c) for pr, t, c in zip(probs, true, pk)]
        p = serve_pass(s, m, mixer, ctx, ws, seed)
        out[arm] = summarize(p, ctx["base"])
        items[arm] = p["harm"]
    for arm in ("X", "M", "O"):
        out[arm]["spill"] = spill_kept(ctx["base"]["harm"], items["S"], items[arm])
    nb = [i for i, it in enumerate(panel) if it["kind"] == "bigger"]
    off = len(tp) + len(tq)
    out["M_mean_p_on_bigger"] = [round(sum(probs[off + i][j] for i in nb) / max(1, len(nb)), 4) for j in range(3)]
    out["R_counts_base_P_Q"] = [sum(c == j for c in rpicks) for j in range(3)]
    out["items"] = {"harm": items, "picks": picks}
    out["reworded"] = reworded(s, m, mixer, rt, ctx)
    out["words"] = words_row(s, m, mixer, rt, ctx)
    return out


def words_row(s, m, mixer, rt, ctx) -> dict:
    """Report-only: Q TEST items written in words by code; the router's choice, and right for base, Q-expert, X."""
    picks = [choice(p) for p in route(rt, ctx["f_words"])]
    ex, xs = [], []
    for e, c in zip(ctx["words"], picks):
        t = q_text(ctx["q_frame"], e)
        mixer.set(Q=1.0)
        ex.append(q_right(q_answers(s, m, t, 0)[0], e))
        mixer.set(**({KINDS[c]: 1.0} if c else {}))
        xs.append(q_right(q_answers(s, m, t, 0)[0], e))
    mixer.set()
    return {"n": len(picks), "to_base_P_Q": [sum(c == j for c in picks) for j in range(3)],
            "right_base": sum(ctx["words_base"]), "right_Q_expert": sum(ex), "right_X": sum(xs)}


def reworded(s, m, mixer, rt, ctx) -> list:
    rows = []
    for fr, fe, fb in zip(ctx["p_other"], ctx["f_p_reword"], ctx["p_reword_base"]):
        picks = [choice(p) for p in route(rt, fe)]
        ex, xs = [], []
        for p, c in zip(ctx["p_test"], picks):
            mixer.set(P=1.0)
            gp = E.with_frame(fr, lambda: int(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"])))
            mixer.set(**({KINDS[c]: 1.0} if c else {}))
            gx = E.with_frame(fr, lambda: int(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"])))
            ex.append(gp)
            xs.append(gx)
        rows.append({"kind": "P", "frame": fr, "to_P": sum(c == 1 for c in picks), "greedy_base": sum(fb),
                     "greedy_expert": sum(ex), "greedy_X": sum(xs)})
    for fr, fe, fb in zip(ctx["q_other"], ctx["f_q_reword"], ctx["q_reword_base"]):
        picks = [choice(p) for p in route(rt, fe)]
        ex, xs = [], []
        for e, c in zip(ctx["q_test"], picks):
            mixer.set(Q=1.0)
            ex.append(q_right(q_answers(s, m, q_text(fr, e), 0)[0], e))
            mixer.set(**({KINDS[c]: 1.0} if c else {}))
            xs.append(q_right(q_answers(s, m, q_text(fr, e), 0)[0], e))
        rows.append({"kind": "Q", "frame": fr, "to_Q": sum(c == 2 for c in picks), "greedy_base": sum(fb),
                     "greedy_expert": sum(ex), "greedy_X": sum(xs)})
    mixer.set()
    return rows


# ---------------------------------------------------------------- marks
def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md): night N (last) unless stated; H3 also on night 1."""
    L0, Q0 = res["base"]["lucky"], res["base"]["q_right"]
    seeds = sorted(r["seed"] for r in res["seeds"])
    fin = {r["seed"]: r["nights"][-1] for r in res["seeds"]}
    first = {r["seed"]: r["nights"][0] for r in res["seeds"]}
    nP, nQ, nH, nB = res["n_p_test"], res["n_q_test"], res["n_harm"], res["n_bigger"]
    lost = {k: [fin[sd][k]["harm"]["lost"] for sd in seeds] for k in ARMS}
    gp = {k: [fin[sd][k]["lucky"] - L0 for sd in seeds] for k in ARMS}
    gq = {k: [fin[sd][k]["q_right"] - Q0 for sd in seeds] for k in ARMS}
    gqs = {k: [fin[sd][k]["q_strict"] - res["base"]["q_strict"] for sd in seeds] for k in ARMS}
    m = {"L0": L0, "Q0": Q0, "final_lost": lost, "gain_P": gp, "gain_Q": gq, "gain_Q_strict_report_only": gqs,
         "router_night1": {sd: {k: first[sd]["router"][k] for k in ("p_test_to_P", "q_test_to_Q", "panel_to_base",
                                                                    "bigger_to_base")} for sd in seeds},
         "router_final": {sd: {k: fin[sd]["router"][k] for k in ("p_test_to_P", "q_test_to_Q", "panel_to_base",
                                                                 "bigger_to_base")} for sd in seeds}}

    def h3(r):
        return (r["p_test_to_P"] >= 0.95 * nP and r["q_test_to_Q"] >= 0.95 * nQ and r["panel_to_base"] >= 0.95 * nH
                and r["bigger_to_base"] >= 0.95 * nB)
    m["H1 forgetting stopped: X lost <= 5 on each seed, and X lost <= 0.25 x S lost (sums)"] = \
        max(lost["X"]) <= 5 and sum(lost["X"]) <= 0.25 * sum(lost["S"])
    m["H2 learning kept: X gain >= 0.9 x S gain on P and on Q, each seed (negative S gain counts as 0)"] = \
        all(x >= 0.9 * max(y, 0) for x, y in zip(gp["X"], gp["S"])) and \
        all(x >= 0.9 * max(y, 0) for x, y in zip(gq["X"], gq["S"]))
    m["H3 router picks right on look-alikes: >= 95% on P TEST, Q TEST, panel and bigger items, nights 1 and last, "
      "each seed"] = all(h3(first[sd]["router"]) and h3(fin[sd]["router"]) for sd in seeds)
    m["H4 choosing beats chance: X gain >= 2 x R gain on P and on Q, and X lost <= R lost (sums)"] = \
        sum(gp["X"]) >= 2 * sum(gp["R"]) and sum(gq["X"]) >= 2 * sum(gq["R"]) and sum(lost["X"]) <= sum(lost["R"])
    keys = [k for k in m if k[:1] == "H" and k[1].isdigit()]
    m["verdict"] = ("INCONCLUSIVE" if L0 < 10 or sum(lost["S"]) < 20 or sum(gq["S"]) < 10 else
                    ("PASS" if all(m[k] for k in keys) else "FAIL"))
    m["proved_wrong"] = (any(x > 0.5 * y for x, y in zip(lost["X"], lost["S"]))
                         or any(y > 0 and x < 0.8 * y for x, y in zip(gp["X"], gp["S"]))
                         or any(y > 0 and x < 0.8 * y for x, y in zip(gq["X"], gq["S"]))
                         or any(fin[sd]["router"]["bigger_to_base"] < 0.75 * nB for sd in seeds))
    m["spill_graded"] = {sd: {k: fin[sd][k]["spill"] | {"lost": fin[sd][k]["harm"]["lost"]} for k in ("X", "M", "O")}
                         for sd in seeds}
    return m


# ---------------------------------------------------------------- run
def load_luna(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def run(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    frame, p_other, suffix = E.glm_texts()
    luna, luna_sha = load_luna(Path(a.luna))
    q_frame, q_other = luna["q_frames"][0], luna["q_frames"][1:]
    B1.puzzle_prompt = G.make_prompt(frame)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    pkeys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
             for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    qkeys = {e["expr"] for sd in seeds for d in range(1, a.nights + 1)
             for e in expressions(Q_DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    p_test = [p for p in B2.puzzles(P_TEST_SEED + a.seed_shift, a.n_test + 300)
              if (tuple(p["nums"]), p["target"]) not in pkeys][:a.n_test]
    q_test = [e for e in expressions(Q_TEST_SEED + a.seed_shift, a.n_qtest + 300) if e["expr"] not in qkeys][:a.n_qtest]
    panel = D1.harm_panel()[:a.n_harm]
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_p_test": len(p_test),
           "n_q_test": len(q_test), "n_harm": len(panel), "n_bigger": sum(it["kind"] == "bigger" for it in panel),
           "temp": D1.TEMP, "q_temp": Q_TEMP, "frame": frame, "p_other_frames": p_other, "suffix": suffix,
           "frame_sha256": G.FRAMES_SHA256, "luna_file": str(a.luna), "luna_sha256": luna_sha, "q_frame": q_frame,
           "q_other_frames": q_other}
    print(f"[dl11] luna {a.luna} sha256 {luna_sha}; q_frame {q_frame!r}", flush=True)
    qs = E.question_pool(s, a.n_ask, POOL_SEED + a.seed_shift)
    rng = random.Random(POOL_SEED)
    rng.shuffle(qs)
    look = list(luna["lookalikes"])
    random.Random(LOOK_SEED).shuffle(look)
    cq, cl = int(0.8 * len(qs)), int(0.8 * len(look))
    neg = [(t + " " + suffix) if rng.random() < 0.5 else t for t in qs + look]
    neg_q, neg_l = neg[:len(qs)], neg[len(qs):]
    res["pool"] = {"asked": a.n_ask, "questions": len(qs), "fit": cq, "held": len(qs) - cq, "sample": qs[:5]}
    res["look"] = {"lookalikes": len(look), "fit": cl, "held": len(look) - cl, "sample": look[:5]}
    print(f"[dl11] pool {json.dumps(res['pool'])} look {json.dumps(res['look'])}", flush=True)
    ctx = {"p_test": p_test, "q_test": q_test, "panel": panel, "q_frame": q_frame, "n_guess_test": a.n_guess_test,
           "kinds": sorted({it["kind"] for it in panel}), "p_other": p_other, "q_other": q_other}
    ctx["neg_fit"] = E.feats(s, [E.chat_text(s, t) for t in neg_q[:cq] + neg_l[:cl]])
    ctx["f"] = {"pool_held": E.feats(s, [E.chat_text(s, t) for t in neg_q[cq:]]),
                "look_held": E.feats(s, [E.chat_text(s, t) for t in neg_l[cl:]]),
                "p_test": E.feats(s, [s.prompt(p) for p in p_test]),
                "q_test": E.feats(s, [E.chat_text(s, q_text(q_frame, e)) for e in q_test]),
                "panel": E.feats(s, [E.chat_text(s, it["q"]) for it in panel])}
    ctx["f_p_reword"] = [E.with_frame(fr, lambda: E.feats(s, [s.prompt(p) for p in p_test])) for fr in p_other]
    ctx["f_q_reword"] = [E.feats(s, [E.chat_text(s, q_text(fr, e)) for e in q_test]) for fr in q_other]
    base_m = s.model
    s.torch.manual_seed(P_TEST_SEED)
    hits = [sum(B1.check(t, p["nums"], p["target"]) for t in s.generate(p, a.n_guess_test, D1.TEMP, base_m))
            for p in p_test]
    greedy = [int(B1.check(s.generate(p, 1, None, base_m)[0], p["nums"], p["target"])) for p in p_test]
    qa = [q_answers(s, base_m, q_text(q_frame, e), 0)[0] for e in q_test]
    qr, qst = [q_right(r, e) for r, e in zip(qa, q_test)], [q_strict(r, e) for r, e in zip(qa, q_test)]
    ctx["base"] = {"hits": hits, "greedy": greedy, "q_right": qr, "q_strict": qst,
                   "harm": D1.harm_scores(s, base_m, panel)}
    ctx["words"] = [words_expr(e) for e in q_test[:a.n_words]]
    ctx["f_words"] = E.feats(s, [E.chat_text(s, q_text(q_frame, e)) for e in ctx["words"]])
    ctx["words_base"] = [q_right(q_answers(s, base_m, q_text(q_frame, e), 0)[0], e) for e in ctx["words"]]
    ctx["p_reword_base"] = [E.with_frame(fr, lambda: [int(B1.check(s.generate(p, 1, None, base_m)[0], p["nums"],
                                                                     p["target"])) for p in p_test]) for fr in p_other]
    ctx["q_reword_base"] = [[q_right(q_answers(s, base_m, q_text(fr, e), 0)[0], e) for e in q_test] for fr in q_other]
    res["base"] = {"lucky": sum(hits), "reached": sum(h > 0 for h in hits), "greedy": sum(greedy), "q_right": sum(qr),
                   "q_strict": sum(qst), "words_right": sum(ctx["words_base"]),
                   "harm_right": sum(ctx["base"]["harm"]), "p_reworded_greedy": [sum(x) for x in ctx["p_reword_base"]],
                   "q_reworded_right": [sum(x) for x in ctx["q_reword_base"]]}
    res["base_harm_items"] = ctx["base"]["harm"]
    print(f"[dl11] base: {res['base']}", flush=True)
    res["seeds"] = []
    for sd in seeds:
        res["seeds"].append(run_seed(s, sd, a, ctx))
        (out / "dl11_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if len(seeds) >= 2:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl11_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


# ---------------------------------------------------------------- selftest
def selftest() -> None:
    import torch
    ex = expressions(7, 50)
    assert len({e["expr"] for e in ex}) == 50 and all(isinstance(e["value"], int) for e in ex)
    assert all(e["value"] == eval(e["expr"]) for e in ex) and expressions(7, 50) == ex
    assert all(set(e["expr"]) <= set("0123456789 +-*") and e["expr"].count(" ") == 2 for e in ex)
    assert q_text("Work out {EXPR}.", {"expr": "2 + 3"}) == "Work out 2 + 3."
    assert q_right("The answer is 5", {"value": 5}) == 1 and q_right("2 + 3 = 5", {"value": 5}) == 1
    assert q_right("5 = 2 + 3", {"value": 5}) == 0 and q_strict("5", {"value": 5}) == 1
    assert q_strict("5.", {"value": 5}) == 1 and q_strict("The answer is 5", {"value": 5}) == 0
    assert q_strict("-40", {"value": -40}) == 1 and q_right("-40", {"value": -40}) == 1
    assert words_expr({"expr": "19 * 3", "value": 57})["expr"] == "nineteen times three"
    assert words_expr({"expr": "55 - 90", "value": -35})["expr"] == "fifty-five minus ninety"
    assert num_words(99) == "ninety-nine" and num_words(40) == "forty" and num_words(12) == "twelve"
    assert weights("AP", [1, 0, 0], 0, 0) == {"P": 1.0} and weights("AQ", [1, 0, 0], 0, 0) == {"Q": 1.0}

    # router separates three clusters and reports probabilities
    X = torch.cat([torch.randn(40, 6) + torch.tensor([4., 0, 0, 0, 0, 0]), torch.randn(40, 6) - 4,
                   torch.randn(40, 6) + torch.tensor([0., 0, 0, 0, 0, 5])])
    y = torch.cat([torch.zeros(40), torch.ones(40), 2 * torch.ones(40)]).long()
    rt = fit_router(torch, X, y, 0)
    picks = [choice(p) for p in route(rt, X)]
    assert sum(p == t for p, t in zip(picks, y.tolist())) >= 114, picks
    assert weights("S", [1, 0, 0], 1, 0) == {"S": 1.0} and weights("X", [0, 1, 0], 2, 1) == {"P": 1.0}
    assert weights("X", [1, 0, 0], 1, 0) == {} and weights("O", [1, 0, 0], 2, 0) == {"Q": 1.0}
    assert weights("M", [0.2, 0.5, 0.3], 1, 1) == {"P": 0.5, "Q": 0.3}
    sc = shuffled_choices([0, 0, 1, 2, 2], 3)
    assert sorted(sc) == [0, 0, 1, 2, 2]
    assert spill_kept([0, 0, 1, 0], [1, 1, 1, 0], [1, 0, 0, 0]) == {"S_gained": 2, "kept": 1, "share": 0.5,
                                                                    "grade": "most"}

    # several LoRA sets: expert off = base exactly; only the named expert's parameters train
    lin = torch.nn.Sequential()
    lin.add_module("q_proj", torch.nn.Linear(4, 4))
    mx = Mixer()
    add_multi_lora(lin, mx)
    x = torch.randn(2, 4)
    base_y = lin.q_proj.base(x)
    for n in NAMES:
        lin.q_proj.B[n].data.normal_()
    lin.eval()
    assert torch.allclose(lin(x), base_y)
    mx.set(P=1.0)
    yp = lin(x)
    mx.set(P=0.5, Q=0.5)
    ym = lin(x)
    mx.set(Q=1.0)
    yq = lin(x)
    assert not torch.allclose(yp, base_y) and torch.allclose(ym, 0.5 * yp + 0.5 * yq, atol=1e-5)
    assert len(expert_params(lin, "P")) == 2 and not any(p is q for p in expert_params(lin, "P")
                                                          for q in expert_params(lin, "Q"))

    # marks
    def night(lx, ls, lr, gpx, gps, gpr, gqx, gqs, gqr, r=(100, 200, 300, 119)):
        rr = dict(zip(("p_test_to_P", "q_test_to_Q", "panel_to_base", "bigger_to_base"), r))
        arm = lambda lost, gp, gq: {"lucky": 50 + gp, "q_right": 80 + gq, "q_strict": 70 + gq,  # noqa: E731
                                    "harm": {"lost": lost}}
        return {"router": rr, "S": arm(ls, gps, gqs), "X": arm(lx, gpx, gqx), "R": arm(lr, gpr, gqr),
                "AP": arm(ls, gps, 0), "AQ": arm(ls, 0, gqs),
                "M": arm(lx, gpx, gqx) | {"spill": {"S_gained": 1, "kept": 0, "share": 0.0, "grade": "none"}},
                "O": arm(lx, gpx, gqx) | {"spill": {"S_gained": 1, "kept": 0, "share": 0.0, "grade": "none"}}}
    res = {"base": {"lucky": 50, "q_right": 80, "q_strict": 70}, "n_p_test": 100, "n_q_test": 200, "n_harm": 300, "n_bigger": 119}
    n1 = night(0, 0, 0, 0, 0, 0, 0, 0, 0)
    fin = night(1, 25, 6, 170, 175, 45, 30, 32, 8)
    fin["X"]["spill"] = {"S_gained": 1, "kept": 0, "share": 0.0, "grade": "none"}
    res["seeds"] = [{"seed": 18, "nights": [n1, fin]}, {"seed": 19, "nights": [n1, json.loads(json.dumps(fin))]}]
    mk = score(res)
    assert mk["verdict"] == "PASS" and not mk["proved_wrong"], mk
    res["seeds"][0]["nights"][0] = night(0, 0, 0, 0, 0, 0, 0, 0, 0, r=(100, 200, 300, 100))
    mk = score(res)
    assert mk["verdict"] == "FAIL" and not mk["proved_wrong"], mk
    res["seeds"][0]["nights"][1]["router"]["bigger_to_base"] = 80
    assert score(res)["proved_wrong"]
    frame, others, suffix = E.glm_texts()
    assert len(others) == 4 and suffix == "Answer only, no explanation."
    print("dl11 selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--luna", default=str(LUNA))
    ap.add_argument("--seeds", default="18,19")
    ap.add_argument("--nights", type=int, default=5)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-qguess", type=int, default=10)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-qtest", type=int, default=200)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-words", type=int, default=100)
    ap.add_argument("--n-ask", type=int, default=1000)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_qguess, a.n_test, a.n_qtest, a.n_guess_test, a.n_harm, a.n_ask = \
            2, 3, 3, 2, 2, 3, 2, 12, 20
        a.n_words = 2
        a.seed_shift, a.seeds = a.seed_shift or 60000, "18"
    run(a)


if __name__ == "__main__":
    main()
