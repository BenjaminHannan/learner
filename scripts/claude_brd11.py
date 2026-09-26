#!/usr/bin/env python3
"""brd-11: replicate brd-9 (three nights of own checked hits) in a NEW world, number squares, and test the textbook
fix for nights that stop improving (a stronger night search). Creative research thread, 2026-09-26; problem 7.

World: the shared number squares (scripts/claude_world_latin.py, Sleep research), blanks reply mode: the prompt shows
a 4x4 square with blanks and asks for only the missing numbers; check_blanks fills them in and checks exactly.
No RuleKeeper and no constrained decoding: plain sampling (Ben's 16:04 redirect). The training target is the model's
own reply string plus EOS, prompt tokens masked (no added text of any kind).

Per arm and LoRA seed s (0/1/2), three nights; each night has 400 NEW practice squares (the same squares in every arm):
- practise: greedy reply; if wrong, n_miss samples at temperature T, first checked hit kept; misses give nothing.
- sleep: a fresh LoRA from base on everything kept so far (all earlier nights too), 3 epochs (brd-9's recipe).
Arms (ONE change each, against its own comparator):
- R: n_miss = 30 (brd-9's recipe). Claim: R3 vs base (the replication).
- S: n_miss = 120 (a stronger night search on the misses only). Claim: S3 vs R3.
Test: a fixed panel of squares (30 samples each) for base, night 1 and night 3 of every arm and seed. Harm: Fix
sleep's 300 general items (claude_dl1_nights.harm_panel), greedy, for base and night 3 of every arm and seed.

  python -B scripts/claude_brd11.py --model M --out DIR --test-puzzles T
  python -B scripts/claude_brd11.py --selftest
  python -B scripts/claude_brd11.py --make-panel OUT
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
import claude_world_latin as W  # noqa: E402

NIGHTS = 3
SIZE = 4
BLANKS = (5, 7)                  # half the items each; fixed from DEV (artifacts/claude-brd11-20260926/DEV.md)
PRACTICE_SEED0 = 910000          # night k practice items: seeds PRACTICE_SEED0 + 1000 * k + i
TEST_SEED0 = 950000              # test panel seeds (never practised)
DEV_SEEDS = range(900000, 901000)  # DEV only (claude_latin_dev.py)


def item(seed, blanks):
    it = W.make(seed, SIZE, blanks)
    return dict(it, prompt=W.prompt_blanks(it))


def key(it):
    return json.dumps(it["puz"])


def night_items(k, n):
    return [item(PRACTICE_SEED0 + 1000 * k + i, BLANKS[i % len(BLANKS)]) for i in range(n)]


def make_panel(n=240, banned=()):
    banned, out, seed = set(banned), [], TEST_SEED0
    while len(out) < n:
        it = item(seed, BLANKS[len(out) % len(BLANKS)])
        seed += 1
        if key(it) in banned:
            continue
        banned.add(key(it))
        out.append({"seed": it["seed"], "size": SIZE, "blanks": it["blanks"]})
    return out


class Solver:
    """claude_blurt2.Solver's model loading, with the square prompt and plain sampling."""
    def __init__(self, model_dir):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True,
                                                          dtype=torch.bfloat16).to(self.dev).eval()
        self.model.name_or_path = model_dir

    def prompt(self, it) -> str:
        return self.tok.apply_chat_template([{"role": "user", "content": it["prompt"]}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)

    def generate(self, it, n, temp, model=None, chunk=30):
        m = model or self.model
        ids = self.tok(self.prompt(it), return_tensors="pt").to(self.dev)
        cut, cap, outs = ids["input_ids"].shape[1], 3 * it["blanks"] + 8, []
        for k in range(0, n, chunk) if temp else [0]:
            kw = {"do_sample": True, "temperature": temp, "top_p": 1.0,
                  "num_return_sequences": min(chunk, n - k)} if temp else {"do_sample": False}
            with self.torch.no_grad():
                out = m.generate(**ids, max_new_tokens=cap, pad_token_id=self.tok.eos_token_id, **kw)
            outs += [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]
        return outs

    def answer(self, it, model=None):
        return self.generate(it, 1, None, model)[0]


def gather(s, items, n_miss, temp, model=None):
    """(examples, rows): greedy reply when right, else the first checked hit among n_miss samples."""
    ex, rows = [], []
    for it in items:
        g = s.answer(it, model)
        if W.check_blanks(it, g):
            ex.append((it, g))
            rows.append({"seed": it["seed"], "blanks": it["blanks"], "kind": "own", "answer": g})
            continue
        hits = [t for t in s.generate(it, n_miss, temp, model) if W.check_blanks(it, t)]
        if hits:
            ex.append((it, hits[0]))
        rows.append({"seed": it["seed"], "blanks": it["blanks"], "kind": "win" if hits else "miss",
                     "answer": hits[0] if hits else None})
    return ex, rows


def counts(rows):
    return {k: sum(r["kind"] == k for r in rows) for k in ("own", "win", "miss")}


def coverage(s, test, n, temp, model=None):
    """Per item: index (1-based) of the first right sample among n, or 0; and the count of right samples."""
    out = []
    for it in test:
        hits = [W.check_blanks(it, t) for t in s.generate(it, n, temp, model)]
        out.append((hits.index(True) + 1 if any(hits) else 0, sum(hits)))
    return out


def summ(st, test):
    r = {f"cov@{k}": sum(1 for f, _ in st if 0 < f <= k) for k in (1, 5, 10, 30)}
    r["lucky"] = sum(h for _, h in st)
    for b in BLANKS:
        r[f"cov@30_blanks{b}"] = sum(1 for (f, _), it in zip(st, test) if f > 0 and it["blanks"] == b)
    return r


def boot_ci(n_items, a_streams, b_streams, reps=2000, seed=0):
    """Item bootstrap of the mean cov@30 difference (a - b) in points, averaged over seeds."""
    rng, diffs = random.Random(seed), []
    for _ in range(reps):
        idx = [rng.randrange(n_items) for _ in range(n_items)]
        da = sum(sum(1 for i in idx if st[i][0] > 0) for st in a_streams) / len(a_streams)
        db = sum(sum(1 for i in idx if st[i][0] > 0) for st in b_streams) / len(b_streams)
        diffs.append((da - db) / n_items)
    diffs.sort()
    return round(diffs[int(0.025 * reps)] * 100, 2), round(diffs[int(0.975 * reps)] * 100, 2)


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = Solver(a.model)
    test = [item(r["seed"], r["blanks"]) for r in (json.loads(x) for x in Path(a.test_puzzles).read_text().splitlines()
                                                    if x.strip())]
    nights = [night_items(k, a.n_night) for k in range(1, NIGHTS + 1)]
    prac = {key(it) for ns in nights for it in ns}
    dev = {key(item(sd, b)) for sd in DEV_SEEDS for b in BLANKS}
    assert not any(key(it) in prac or key(it) in dev for it in test), "panel overlaps practice or DEV"
    harm = D1.harm_panel()[:a.n_harm]
    res = {"temp": a.temp, "n_test": len(test), "n_night": a.n_night, "blanks": list(BLANKS)}
    base = coverage(s, test, a.n, a.temp)
    res["base"] = summ(base, test)
    res["base_unreached"] = len(test) - res["base"]["cov@30"]
    res["bar_pass"] = 0.2 * res["base_unreached"]
    base_harm = D1.harm_scores(s, s.model, harm)
    res["base_harm_right"] = sum(base_harm)
    print(f"[brd11] base {res['base']} harm right {res['base_harm_right']}", flush=True)
    streams, log, first = {}, {}, {}
    for arm, n_miss in (("R", 30), ("S", a.s_miss)):
        first[arm] = gather(s, nights[0], n_miss, a.temp)       # the base model's night-1 practice, per arm
        res[f"{arm}_night1_practice"] = counts(first[arm][1])
        log[f"{arm}_night1"] = first[arm][1]
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            ex, m = list(first[arm][0]), None
            for k in range(1, NIGHTS + 1):
                if k > 1:
                    ex_k, rows_k = gather(s, nights[k - 1], n_miss, a.temp, m)
                    ex += ex_k
                    res[f"{arm}_night{k}_practice_seed{sd}"] = counts(rows_k)
                    log[f"{arm}_night{k}_seed{sd}"] = rows_k
                    del m
                    if s.dev == "cuda":
                        s.torch.cuda.empty_cache()
                m = B2.train_lora(s, list(ex), a.epochs, sd)
                if k in (1, NIGHTS):
                    st = coverage(s, test, a.n, a.temp, m)
                    streams.setdefault(f"{arm}{k}", []).append(st)
                    res[f"{arm}{k}_seed{sd}"] = summ(st, test) | {"examples": len(ex)}
                if k == NIGHTS:
                    res[f"{arm}{k}_seed{sd}"]["harm"] = D1.flips(base_harm, D1.harm_scores(s, m, harm))
                print(f"[brd11] {arm} seed {sd} night {k}: {res.get(f'{arm}{k}_seed{sd}', 'trained')}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
            (out / "practice.json").write_text(json.dumps(log), encoding="utf-8")
    n = len(test)
    res["ci95_R3_minus_base_cov30_pct"] = boot_ci(n, streams["R3"], [base])
    res["ci95_S3_minus_R3_cov30_pct"] = boot_ci(n, streams["S3"], streams["R3"])
    res["ci95_S3_minus_S1_cov30_pct"] = boot_ci(n, streams["S3"], streams["S1"])
    res["ci95_R3_minus_R1_cov30_pct"] = boot_ci(n, streams["R3"], streams["R1"])
    res["ci95_S3_minus_base_cov30_pct"] = boot_ci(n, streams["S3"], [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd11_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    it = item(950000, 5)
    sol = [it["sol"][r][c] for r in range(SIZE) for c in range(SIZE) if it["puz"][r][c] == 0]
    assert W.check_blanks(it, " ".join(map(str, sol))) and not W.check_blanks(it, " ".join(map(str, sol[:-1])))
    ns = [night_items(k, 50) for k in range(1, NIGHTS + 1)]
    assert len({key(x) for n in ns for x in n}) >= 145
    p = make_panel(20)
    assert len(p) == 20 and {r["blanks"] for r in p} == set(BLANKS)
    st = [(1, 2), (0, 0), (5, 1)]
    assert summ(st, [item(950000, 5), item(950001, 7), item(950002, 5)])["cov@30_blanks5"] == 2
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--s-miss", type=int, default=120)
    ap.add_argument("--n-night", type=int, default=400)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--make-panel", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.make_panel:
        banned = {key(it) for k in range(1, NIGHTS + 1) for it in night_items(k, a.n_night)}
        banned |= {key(item(sd, b)) for sd in DEV_SEEDS for b in BLANKS}
        Path(a.make_panel).write_text("".join(json.dumps(r) + "\n" for r in make_panel(240, banned)), encoding="utf-8")
    else:
        run(a)


if __name__ == "__main__":
    main()
