#!/usr/bin/env python3
"""rv-388: does a learned "is this still solvable?" judge make going back pay off? (thought-memory thread, 2026-09-26)

Why: Ben's 12:48 UTC rule (join functions across threads). Going back needs a "this path is going wrong" signal
(design/v3/30-modes/384b-revert-and-retry.md). Creative's feas-24b judge (a logistic head on the frozen 1B's layer-16
state, artifacts/claude-feas24b-20260925/) ranks a still-solvable 24-game state above a dead end in 153-158 of 200
pairs (NOT SHOWN: 68-71 of 100 on 3-value states). Its VERIFY says whether it speeds up search needs its own test.
Creative (12:55 UTC): go ahead, reuse its recipe unchanged, test hands from its held-out hands, add an exact-code ORACLE
arm as a report-only ceiling.

Task: the plain MiniCPM5-1B (bf16, enable_thinking=False) plays 4-card 24-game hands one step at a time. At each state
every step (two numbers, + - * /, both orders for - and /; exact fractions, as feas-24) is scored by the 1B's
log-probability of the step text after the reply prefix; steps that give the same next state are pooled; one is
sampled at temperature 1.5. A state with one number is checked exactly (24 or not). The search is depth-first with
code bookkeeping (rv-385's lesson): a failed step is banned at its state, a state with every step banned is a dead
end and the search goes back one more step.
Arms (same hands, same budget of model steps, same random numbers per hand):
  END     go back only when a path ends in a number that is not 24.
  JUDGE   also go back as soon as the judge flags the new 3- or 2-number state as a dead end. Soft: a flagged step is
          set aside, not banned, and comes back once every unflagged step at that state is banned.
  PLACEBO the same, with the judge fitted on labels shuffled within each stage (feas-24b's placebo); its cut flags the
          same share of practice states as the real judge's cut.
  ORACLE  report only: the flag is exact code reachability (feas24.reach). Code can check these tiny states exactly,
          so this is the free ceiling any judge result must be read against.
One change between END and JUDGE: the early go-back signal. JUDGE vs PLACEBO: whether the signal carries information.

  python -B scripts/claude_rv388.py judge-check --model DIR --out DIR   (refit the heads; reproduce feas-24b seed 0)
  python -B scripts/claude_rv388.py calibrate --model DIR --out DIR --seed S --n N --budget B   (practice hands)
  python -B scripts/claude_rv388.py run --model DIR --out DIR --seed S --n N --budget B --arms end,judge,placebo,oracle
  python -B scripts/claude_rv388.py selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_feas24 as F  # noqa: E402  (Creative's states, text, reachability and split; read-only)
import claude_feas24b as FB  # noqa: E402  (Creative's Newton fit; read-only)

SPLIT_SEED, LAYER, L2, HEAD_SEED = 792, 16, 100.0, 0     # feas-24b's frozen choice; seed-0 heads
THREADS = 2          # feas-24b ran on 2 CPU threads; bf16 features on this CPU change with the thread count (4 vs 2)
TEMP = 1.5
ARMS = ["end", "judge", "placebo", "oracle"]
OPS = ("+", "-", "*", "/")


# ---------------- hands ----------------
def all_hands():
    return [tuple(Fraction(c) for c in h) for h in itertools.combinations_with_replacement(range(1, 14), 4)]


def held_out_hands():
    """the last 25% of feas-24's seed-792 shuffle: no test pair of the judge came from other hands"""
    hands = all_hands()
    random.Random(SPLIT_SEED).shuffle(hands)
    return hands[int(0.75 * len(hands)):], hands[:int(0.75 * len(hands))]


def pick_hands(seed, n, pool):
    good = sorted(h for h in pool if F.reach(tuple(sorted(h))))
    random.Random(f"rv388-hands|{seed}").shuffle(good)
    return good[:n]


TEST_SEEDS = (388101, 388202)


def test_hands(seed, n):
    """the registered test: one fixed shuffle of the 348 solvable held-out hands, cut into disjoint blocks per seed."""
    test, _ = held_out_hands()
    good = sorted(h for h in test if F.reach(tuple(sorted(h))))
    random.Random("rv388-test").shuffle(good)
    k = TEST_SEEDS.index(seed)
    return good[k * n:(k + 1) * n]


# ---------------- steps ----------------
def moves(state):
    """[(text, next_state)] for every step from a state (sorted tuple of Fractions)."""
    out = []
    vals = list(state)
    for i, j in itertools.combinations(range(len(vals)), 2):
        a, b = vals[i], vals[j]
        rest = [vals[k] for k in range(len(vals)) if k not in (i, j)]
        opts = [(a, "+", b, a + b), (a, "*", b, a * b), (a, "-", b, a - b), (b, "-", a, b - a)]
        if b:
            opts.append((a, "/", b, a / b))
        if a:
            opts.append((b, "/", a, b / a))
        for x, op, y, v in opts:
            out.append((f"{F.fmt(x)} {op} {F.fmt(y)}", tuple(sorted(rest + [v]))))
    return out


def step_prompt(state):
    nums = ", ".join(F.fmt(v) for v in state)
    return (f"Make 24. Each step combines two of the numbers with +, -, * or / into one new number, until one number "
            f"is left, and every number is used exactly once. Numbers left: {nums}. What is the next step? Answer "
            f"with one step, like 8 - 3."), "Next step: "


# ---------------- model ----------------
class Model:
    def __init__(self, model_dir):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(THREADS)
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.m = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, trust_remote_code=True).eval()
        self.move_cache, self.feat_cache = {}, {}
        self.calls = {"move_states": 0, "judge_states": 0}

    def load_feats(self, path):
        if path and Path(path).exists():
            d = np.load(path, allow_pickle=True)
            for k, x in zip(d["keys"], d["X"]):
                self.feat_cache[tuple(Fraction(v) for v in k.split(","))] = x.astype(np.float64)

    def save_feats(self, path):
        keys = list(self.feat_cache)
        np.savez_compressed(path, X=np.stack([self.feat_cache[k] for k in keys]).astype(np.float16),
                            keys=np.array([",".join(str(v) for v in k) for k in keys]))

    def move_scores(self, state):
        """{next_state: pooled log-probability} over every step from this state (cached by state)."""
        if state in self.move_cache:
            return self.move_cache[state]
        torch, tok = self.torch, self.tok
        msg, pre = step_prompt(state)
        p_ids = tok(tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False) + pre)["input_ids"]
        mv = moves(state)
        c_ids = [tok(t, add_special_tokens=False)["input_ids"] for t, _ in mv]
        L = len(p_ids) + max(len(c) for c in c_ids)
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        ids = torch.full((len(mv), L), pad)
        att = torch.zeros((len(mv), L), dtype=torch.long)
        for k, c in enumerate(c_ids):
            seq = p_ids + c
            ids[k, :len(seq)] = torch.tensor(seq)
            att[k, :len(seq)] = 1
        lp = []
        with torch.inference_mode():
            for k0 in range(0, len(mv), 16):
                lg = self.m(input_ids=ids[k0:k0 + 16], attention_mask=att[k0:k0 + 16]).logits.float()
                ls = torch.log_softmax(lg, -1)
                for k in range(k0, min(k0 + 16, len(mv))):
                    c = c_ids[k]
                    pos = torch.arange(len(p_ids) - 1, len(p_ids) - 1 + len(c))
                    lp.append(float(ls[k - k0, pos, torch.tensor(c)].sum()))
        pooled = {}
        for (_, nxt), s in zip(mv, lp):
            pooled[nxt] = s if nxt not in pooled else float(np.logaddexp(pooled[nxt], s))
        self.move_cache[state] = pooled
        self.calls["move_states"] += 1
        return pooled

    def feature(self, state):
        """layer-16 hidden state of the last prompt token of feas-24's text, batch 1, rounded to float16 (as feas-24)."""
        if state in self.feat_cache:
            return self.feat_cache[state]
        torch, tok = self.torch, self.tok
        s = tok.apply_chat_template([{"role": "user", "content": F.text(state)}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=False)
        with torch.inference_mode():
            hs = self.m(**tok(s, return_tensors="pt"), output_hidden_states=True).hidden_states
        x = hs[LAYER][0, -1].float().numpy().astype(np.float16).astype(np.float64)
        self.feat_cache[state] = x
        self.calls["judge_states"] += 1
        return x


# ---------------- judge (feas-24b recipe, unchanged) ----------------
def fit_heads(model):
    """seed-0 real and shuffled heads exactly as claude_feas24b.run fits them (its sub() and shuffled())."""
    train, _dev, pairs = F.build(SPLIT_SEED)
    X = np.stack([model.feature(s) for s, _ in train])
    ytr = np.array([float(r) for _, r in train])
    stage = np.array([len(s) for s, _ in train])
    r = np.random.default_rng(HEAD_SEED)
    take = []
    for k in (2, 3):
        for lab in (0.0, 1.0):
            cell = np.where((stage == k) & (ytr == lab))[0]
            take += r.choice(cell, int(0.85 * len(cell)), replace=False).tolist()
    rows = np.array(sorted(take))
    rs = np.random.default_rng(1000 + HEAD_SEED)
    ysh = ytr[rows].copy()
    for k in (2, 3):
        msk = stage[rows] == k
        ysh[msk] = rs.permutation(ysh[msk])
    heads = {"real": FB.fit_newton(X[rows], ytr[rows], L2), "shuffled": FB.fit_newton(X[rows], ysh, L2)}
    trained = {train[i][0] for i in rows}
    return heads, trained, pairs


def logit(h, x):
    return float(((x - h["mean"]) / h["std"]) @ h["w"] + h["b"])


def judge_check(a):
    """reproduce feas-24b's seed-0 pair counts (real 158, shuffled 111) from the refit heads."""
    model = Model(a.model)
    model.load_feats(a.feats)
    heads, trained, pairs = fit_heads(model)
    out = {"trained_states": len(trained)}
    for name, h in heads.items():
        right = {k: sum((lambda p, q: (p > q) + 0.5 * (p == q))(logit(h, model.feature(p)), logit(h, model.feature(q)))
                        for _, p, q in pairs[k]) for k in (3, 2)}
        out[name] = {"pairs_right": right[3] + right[2], "pairs_right_3": right[3], "pairs_right_2": right[2],
                     "final_grad": h["grad"]}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "judge-check.json").write_text(json.dumps(out, indent=1) + "\n")
    if a.feats:
        model.save_feats(a.feats)
    print(json.dumps(out))


# ---------------- one hand's search ----------------
class Search:
    def __init__(self, hand, arm, seed, flag):
        self.hand, self.arm, self.flag = hand, arm, flag
        self.root = tuple(sorted(hand))
        self.path = [self.root]              # states entered, root first
        self.ban = {}                        # state -> next states ruled out
        self.aside = {}                      # state -> next states set aside by the flag (soft)
        self.steps = self.flags = self.backs = 0
        self.solved = False
        self.visited = set()
        self.rng = random.Random(f"rv388|{seed}|{hand}")      # same numbers in every arm

    def step(self, scores):
        cur = self.path[-1]
        ban, aside = self.ban.setdefault(cur, set()), self.aside.setdefault(cur, set())
        live = [s for s in scores if s not in ban]
        pick_from = [s for s in live if s not in aside] or live
        w = [math.exp((scores[s] - max(scores[t] for t in pick_from)) / TEMP) for s in pick_from]
        x, acc, nxt = self.rng.random() * sum(w), 0.0, pick_from[-1]
        for s, ws in zip(pick_from, w):
            acc += ws
            if x <= acc:
                nxt = s
                break
        self.steps += 1
        if len(nxt) == 1:
            if nxt[0] == F.T:
                self.solved = True
                self.path.append(nxt)
                return
            ban.add(nxt)
        elif self.flag is not None and nxt not in aside and self.flag(nxt):
            aside.add(nxt)
            self.flags += 1
        else:
            self.visited.add(nxt)
            self.path.append(nxt)          # (a state reached again by another route keeps its bans)
        self._back_if_dead()

    def _dead(self, state):
        return bool(self.ban.get(state)) and set(self.scores_of(state)) <= self.ban[state]

    def _back_if_dead(self):
        # a state whose every next state is banned is a dead end: leave it and ban it at its parent
        while len(self.path) > 1 and self._dead(self.path[-1]):
            dead = self.path.pop()
            self.ban.setdefault(self.path[-1], set()).add(dead)
            self.backs += 1

    def scores_of(self, state):
        return self._scores(state)

    def result(self):
        return {"hand": [F.fmt(v) for v in self.hand], "arm": self.arm, "solved": self.solved, "steps": self.steps,
                "flags": self.flags, "backs": self.backs, "path": [[F.fmt(v) for v in s] for s in self.path]}


def run_arm(model, hands, arm, seed, budget, flag):
    out = []
    for h in hands:
        x = Search(h, arm, seed, flag)
        x._scores = model.move_scores
        while not x.solved and x.steps < budget:
            x.step(model.move_scores(x.path[-1]))
        out.append(x)
    return out


def flags_for(arm, model, heads, cuts):
    if arm == "end":
        return None
    if arm == "oracle":
        return lambda s: not F.reach(s)
    h = heads["real" if arm == "judge" else "shuffled"]
    return lambda s: logit(h, model.feature(s)) < cuts[arm]


def calibrate(a):
    """practice hands only (never the held-out test hands): END's solved-by-step curve for the budget, and the
    placebo cut that flags the same share of END's entered states as the real judge at logit 0."""
    model = Model(a.model)
    model.load_feats(a.feats)
    heads, _, _ = fit_heads(model)
    _, practice = held_out_hands()
    hands = pick_hands(a.seed, a.n, practice)
    xs = run_arm(model, hands, "end", a.seed, a.budget, None)
    at = [x.steps for x in xs if x.solved]
    curve = {b: sum(s <= b for s in at) for b in range(5, a.budget + 1, 5)}
    states = sorted(set().union(*[x.visited for x in xs]))
    real = np.array([logit(heads["real"], model.feature(st)) for st in states])
    shuf = np.array([logit(heads["shuffled"], model.feature(st)) for st in states])
    reach = np.array([F.reach(st) for st in states])
    share = float((real < 0).mean())
    out = {"seed": a.seed, "n": len(hands), "max_budget": a.budget, "end_solved_by_step": curve,
           "entered_states": len(states), "reachable": int(reach.sum()), "real_flag_share": round(share, 4),
           "real_flags_on_dead": int(((real < 0) & ~reach).sum()), "real_flags_on_live": int(((real < 0) & reach).sum()),
           "cuts": {"judge": 0.0, "placebo": float(np.quantile(shuf, share))}, "calls": model.calls}
    out["placebo_flags_on_dead"] = int(((shuf < out["cuts"]["placebo"]) & ~reach).sum())
    out["placebo_flags_on_live"] = int(((shuf < out["cuts"]["placebo"]) & reach).sum())
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / f"calibrate-seed{a.seed}.json").write_text(json.dumps(out, indent=1) + "\n")
    if a.feats:
        model.save_feats(a.feats)
    print(json.dumps(out))


def run(a):
    model = Model(a.model)
    model.load_feats(a.feats)
    heads, trained, _ = fit_heads(model)
    cuts = json.loads(Path(a.cuts).read_text()) if a.cuts else {"judge": 0.0, "placebo": 0.0}
    _, practice = held_out_hands()
    hands = pick_hands(a.seed, a.n, practice) if a.practice else test_hands(a.seed, a.n)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for arm in a.arms.split(","):
        t0 = time.time()
        xs = run_arm(model, hands, arm, a.seed, a.budget, flags_for(arm, model, heads, cuts))
        seen = set().union(*[x.visited for x in xs]) if xs else set()
        rec = {"arm": arm, "seed": a.seed, "practice": a.practice, "n": len(xs), "budget": a.budget,
               "solved": sum(x.solved for x in xs), "steps": sum(x.steps for x in xs),
               "flags": sum(x.flags for x in xs), "backs": sum(x.backs for x in xs),
               "entered_states": len(seen), "entered_in_judge_training": len(seen & trained),
               "cuts": cuts, "calls": dict(model.calls), "sec": round(time.time() - t0)}
        (out / f"{arm}-seed{a.seed}{'-practice' if a.practice else ''}.jsonl").write_text(
            "".join(json.dumps(x.result()) + "\n" for x in xs))
        print(json.dumps(rec), flush=True)


def selftest():
    # every step keeps the numbers exact; the root's next states match feas-24's steps()
    h = (Fraction(4), Fraction(7), Fraction(8), Fraction(8))
    assert {s for _, s in moves(h)} == F.steps(list(h))
    test, practice = held_out_hands()
    assert len(test) == 455 and not set(test) & set(practice)
    th = pick_hands(1, 20, test)
    assert all(F.reach(tuple(sorted(x))) for x in th) and len(set(th)) == 20
    a_, b_ = test_hands(TEST_SEEDS[0], 80), test_hands(TEST_SEEDS[1], 80)
    assert len(a_) == len(b_) == 80 and not set(a_) & set(b_) and set(a_) <= set(test)
    # with uniform scores the arms make identical choices until a flag fires; END never flags
    fake = lambda s: {nxt: 0.0 for _, nxt in moves(s)}
    for hand in th[:5]:
        runs = {}
        for arm, flag in (("end", None), ("oracle", lambda s: not F.reach(s))):
            x = Search(hand, arm, 1, flag)
            x._scores = fake
            while not x.solved and x.steps < 400:
                x.step(fake(x.path[-1]))
            runs[arm] = x
        assert runs["end"].solved and runs["oracle"].solved      # exhaustive enough: solvable hands get solved
        assert runs["end"].flags == 0
        assert runs["oracle"].steps <= runs["end"].steps           # exact flags never cost steps
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["judge-check", "calibrate", "run", "selftest"])
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--budget", type=int, default=30)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--cuts", default="")
    ap.add_argument("--practice", action="store_true")
    ap.add_argument("--feats", default="")
    a = ap.parse_args()
    {"judge-check": judge_check, "calibrate": calibrate, "run": run, "selftest": lambda _a: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
