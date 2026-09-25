#!/usr/bin/env python3
"""ask-24: can sleep teach the 1B to say "can't" on provably impossible puzzles without giving up on solvable ones?
(creative research thread, 2026-09-25; Ben approved 16:59 UTC: "ok, go ahead. I like that.")

Why (reviews/creative-research-2026-09-25/E-asking.md): training on your own checked hits wipes out "I don't know"
(refusal fell by more than 80% under reinforcement fine-tuning; 10% unanswerable items restored it, arXiv 2505.13988).
Our sleep loop (blurt-3 PASS) is that kind of training, and it only ever rewards expressions.

One change from the blurt-3 recipe: "none" is also a legal answer, and the exact checker accepts it exactly when brute
force proves that no expression exists. Sleep can then keep a verified "none" as a hit, like any other lucky hit.
  Prompt: the blurt-1 puzzle prompt plus one sentence, "If it cannot be done, reply with only the word none."
  Decoding: the blurt-2 rule keeper, plus the word "none" as a whole answer.
  Practice: 360 solvable puzzles (the blurt-1 recipe) and 40 provably impossible ones (10%, from the same recipe).
  The reasoner (greedy, "none" allowed) tries each once. On a miss, 30 blurts at T 1.5 (blurt-3's DEV choice, fixed
  here) with "none" NOT allowed (blurts are guesses), and the exact checker keeps hits. A verified "none" comes only
  from the reasoner on an impossible puzzle.
  DEV (17:06 UTC, dev/dev_summary.json, first design with "none" allowed in blurts): the base 1B said none on 20/20
  impossible AND 20/20 solvable DEV puzzles, and 576/600 of its blurts on solvable puzzles were none. So the base
  over-gives-up; the question is whether sleep teaches WHEN "none" is right. Blurts were changed to expressions only.
  Arms (LoRA r16, 3 epochs, seeds 0 and 1):
    W = the blurt-3 W arm (own right expressions + first lucky expression per won solvable puzzle), padded to N's
        size by repeating its own examples. It never sees "none".
    N = W's examples + one verified "none" per impossible practice puzzle where the reasoner or a blurt said none.
        "none" is never trained on a solvable puzzle.
  Fresh test: 80 solvable + 80 impossible puzzles from their own seeds, overlap with practice dropped, never printed.

  python -B scripts/claude_ask24.py loop --model M --out DIR          (registered run, see PASSMARKS-ask24.md)
  python -B scripts/claude_ask24.py dev  --model M --out DIR          (DEV rehearsal on DEV-only seeds)
  python -B scripts/claude_ask24.py selftest --model M
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402

NONE = "none"
ASK_LINE = " If it cannot be done, reply with only the word none."
TEMP = 1.5


def solvable(p) -> bool:
    return B1.solve(p["nums"], p["target"]) is not None


def check(ans: str, p) -> bool:
    """Exact: "none" is right iff no expression exists; an expression is right iff it makes the target."""
    a = ans.strip().lower().rstrip(".")
    if a == NONE:
        return not solvable(p)
    return B1.check(ans, p["nums"], p["target"])


def impossible(seed, n):
    """Provably impossible puzzles, from the same recipe as claude_blurt2.puzzles (two thirds 3-number)."""
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:
        k = 3 if len(out) % 3 else 4
        nums = sorted(rng.randint(1, 9 if k == 3 else 13) for _ in range(k))
        target = 24 if k == 4 else rng.randint(5, 40)
        key = (tuple(nums), target)
        if key in seen or B1.solve(nums, target) is not None:
            continue
        seen.add(key)
        out.append({"id": f"im-s{seed}-{len(out) + 1:03d}", "nums": nums, "target": target})
    return out


class AskKeeper(B2.RuleKeeper):
    """The blurt-2 rule keeper, plus the whole word "none" as an answer (unless allow_none is False)."""

    def __init__(self, tok, nums, cut, allow_none=True):
        super().__init__(tok, nums, cut)
        self.allow_none = allow_none
        self.none_toks = []
        if allow_none:
            for i, t in B2._VOCAB.setdefault(("none", id(tok)), _none_tokens(tok)):
                self.none_toks.append((i, t))

    def allowed(self, text: str) -> list[int]:
        if text in self.memo:
            return self.memo[text]
        s = text.strip()
        if self.allow_none and s and s[0].isalpha():
            ok = [i for i, t in self.none_toks if NONE.startswith((text + t).strip()) and
                  not (text + t).strip() == "" and " " not in (text + t).strip()]
            if s == NONE or not ok:
                ok.append(self.eos)
            self.memo[text] = ok
            return ok
        ok = list(super().allowed(text))
        if self.allow_none and s == "":
            ok += [i for i, t in self.none_toks if NONE.startswith(t.strip()) and t.strip()]
        self.memo[text] = ok
        return ok


def _none_tokens(tok):
    out = []
    for i in range(len(tok)):
        t = tok.decode([i])
        u = t.strip()
        if u and NONE.startswith(u) and t in (u, " " + u):
            out.append((i, t))
    return out


class AskSolver(B2.Solver):
    def prompt(self, p) -> str:
        msgs = B1.puzzle_prompt(p)
        msgs[0]["content"] += ASK_LINE
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def generate(self, p, n, temp, model=None, allow_none=True):
        from transformers import LogitsProcessorList
        m = model or self.model
        ids = self.tok(self.prompt(p), return_tensors="pt").to(self.dev)
        cut = ids["input_ids"].shape[1]
        kw = {"do_sample": True, "temperature": temp, "top_p": 1.0, "num_return_sequences": n} if temp else \
             {"do_sample": False}
        with self.torch.no_grad():
            out = m.generate(**ids, max_new_tokens=32, pad_token_id=self.tok.eos_token_id,
                             logits_processor=LogitsProcessorList([AskKeeper(self.tok, p["nums"], cut, allow_none)]),
                             **kw)
        return [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]

    def answer(self, p, model=None, allow_none=True):
        return self.generate(p, 1, None, model, allow_none)[0]


def is_none(a: str) -> bool:
    return a.strip().lower().rstrip(".") == NONE


def measure(s, sol, imp, n, model=None) -> dict:
    """Greedy answers on both halves of the test, forced guesses after a "none" on a solvable puzzle, and blurts."""
    r = {"imp_none": 0, "imp_expr": 0, "sol_right": 0, "sol_none": 0, "sol_none_forced_right": 0,
         "sol_lucky_blurts": 0, "sol_puzzles_hit": 0}
    for p in imp:
        a = s.answer(p, model)
        r["imp_none" if is_none(a) else "imp_expr"] += 1
    for p in sol:
        a = s.answer(p, model)
        if is_none(a):
            r["sol_none"] += 1
            r["sol_none_forced_right"] += check(s.answer(p, model, allow_none=False), p)
        else:
            r["sol_right"] += check(a, p)
        if n:
            bl = s.generate(p, n, TEMP, model, allow_none=False)
            h = sum(check(t, p) for t in bl)
            r["sol_lucky_blurts"] += h
            r["sol_puzzles_hit"] += h > 0
    r["n_sol"], r["n_imp"] = len(sol), len(imp)
    return r


def practice(s, train, n):
    own, wins, none_hits, stats = [], [], [], {"reasoner_right": 0, "reasoner_none_on_impossible": 0,
                                               "reasoner_none_on_solvable": 0, "lucky_expr_blurts": 0,
                                               "blurts": 0}
    for p in train:
        g = s.answer(p)
        if check(g, p):
            stats["reasoner_right"] += 1
            if is_none(g):
                stats["reasoner_none_on_impossible"] += 1
                none_hits.append((p, NONE))
            else:
                own.append((p, g))
            continue
        if is_none(g):
            stats["reasoner_none_on_solvable"] += 1
        if not solvable(p):                          # no expression can hit; only the reasoner's "none" counts
            continue
        bl = s.generate(p, n, TEMP, allow_none=False)
        stats["blurts"] += len(bl)
        hits = [t for t in bl if check(t, p)]
        stats["lucky_expr_blurts"] += len(hits)
        if hits:
            wins.append((p, hits[0]))
    return own, wins, none_hits, stats


def keys(ps):
    return {(tuple(p["nums"]), p["target"]) for p in ps}


def loop(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = AskSolver(a.model)
    s.model.name_or_path = a.model
    train = B2.puzzles(a.train_seed, a.n_train_sol) + impossible(a.train_seed + 1000, a.n_train_imp)
    random.Random(a.train_seed).shuffle(train)
    k_train = keys(train)
    sol = [p for p in B2.puzzles(a.test_seed, a.n_test) if (tuple(p["nums"]), p["target"]) not in k_train]
    imp = [p for p in impossible(a.test_seed + 1000, a.n_test) if (tuple(p["nums"]), p["target"]) not in k_train]
    res = {"n_train": len(train), "n_train_impossible": a.n_train_imp, "n_test_sol": len(sol), "n_test_imp": len(imp),
           "temp": TEMP}
    res["base"] = measure(s, sol, imp, a.n)
    print(f"[ask24] base: {json.dumps(res['base'])}", flush=True)
    own, wins, none_hits, st = practice(s, train, a.n)
    res["practice"] = st | {"own": len(own), "wins": len(wins), "none_hits": len(none_hits)}
    print(f"[ask24] practice: {json.dumps(res['practice'])}", flush=True)
    ex_n = own + wins + none_hits
    base_w = own + wins
    ex_w = (base_w * (len(ex_n) // max(1, len(base_w)) + 1))[:len(ex_n)] if base_w else []
    res["examples_W"], res["examples_N"] = len(ex_w), len(ex_n)
    for arm, ex in (("W", ex_w), ("N", ex_n)):
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            res[f"{arm}_seed{sd}"] = measure(s, sol, imp, a.n, m)
            print(f"[ask24] {arm} seed {sd}: {json.dumps(res[f'{arm}_seed{sd}'])}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "ask24_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def dev(a):
    """DEV rehearsal (DEV-only seeds 9100/10100): does the base 1B ever say none, and how often on solvable ones?"""
    s = AskSolver(a.model)
    sol, imp = B2.puzzles(9100, a.n_dev), impossible(10100, a.n_dev)
    r = measure(s, sol, imp, a.n)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / a.dev_name).write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r))


def selftest(a):
    p_ok, p_no = {"nums": [3, 8], "target": 24}, {"nums": [1, 1, 1, 1], "target": 24}
    assert check("3*8", p_ok) and not check("none", p_ok) and check("none", p_no) and not check("1+1", p_no)
    imps = impossible(1, 30)
    assert all(not solvable(p) for p in imps) and len(keys(imps)) == 30
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    k = AskKeeper(tok, [3, 8, 1], 0)
    first = {tok.decode([i]) for i in k.allowed("")}
    assert any(t.strip() and NONE.startswith(t.strip()) for t in first), "none cannot start"
    assert any(t.strip().startswith("3") or t.strip().startswith("(") for t in first), "expressions cannot start"
    # walk "none" greedily through allowed tokens
    text = ""
    for _ in range(6):
        ids = [i for i in k.allowed(text) if i != tok.eos_token_id and NONE.startswith((text + tok.decode([i])).strip())]
        if (text.strip() == NONE):
            break
        assert ids, f"stuck at {text!r}"
        text += tok.decode([max(ids, key=lambda i: len(tok.decode([i]).strip()))])
    assert text.strip() == NONE and k.allowed(text) == [tok.eos_token_id], (text, k.allowed(text))
    k2 = AskKeeper(tok, [3, 8, 1], 0, allow_none=False)
    assert not any(tok.decode([i]).strip() and NONE.startswith(tok.decode([i]).strip()) for i in k2.allowed(""))
    assert tok.eos_token_id not in k.allowed("3") and tok.eos_token_id in k.allowed("3*8*1")
    print("selftest ok; none tokens:", [t for _, t in _none_tokens(tok)][:12])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["loop", "dev", "selftest"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=7)
    ap.add_argument("--n-train-sol", type=int, default=360)
    ap.add_argument("--n-train-imp", type=int, default=40)
    ap.add_argument("--test-seed", type=int, default=782)
    ap.add_argument("--n-test", type=int, default=80)
    ap.add_argument("--n-dev", type=int, default=20)
    ap.add_argument("--dev-name", default="dev_summary.json")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1")
    a = ap.parse_args()
    {"loop": loop, "dev": dev, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
