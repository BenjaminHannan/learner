"""Leap-1 (see backbone/PREREG-leap1.md). Arms: self, leapu, leap (5 rounds of explore -> LoRA sleep -> merge -> score), ref (score only).

  python backbone/leap/leap1.py --arm leap --model Qwen/Qwen3.5-0.8B --seed 0 --out out/leap
  python backbone/leap/leap1.py --arm leap --smoke --rounds 2 --out /tmp/leapsmoke      # CPU, tiny random qwen3_5

Never trains on EVAL/DEV (signatures held out, asserted). The puzzle `answer` is never used for training: verified = reproduces the examples.
"""
import argparse
import itertools
import json
import math
import random
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "creative"))
sys.path.insert(0, str(HERE.parent / "sleep"))
sys.path.insert(0, str(HERE.parent))
from creative1 import (PRIMS, SYS, compile_prog, is_correct, judge, make_puzzle, parse_program, rand_step, run_prog,  # noqa: E402
                       signature, split_prompt)

DEPTHS = range(1, 7)
HELD_SEED, EVAL_SEED, DEV_SEED = 777, 1000, 2000


# ------------------------------------------------------------------ data
def all_sigs(d):
    return sorted(s for s in itertools.product(PRIMS, repeat=d) if not any(a == b == "rev" for a, b in zip(s, s[1:])))


def gen_puzzles(d, n, rng, ok_sig, seen, tag):
    out, tries = [], 0
    while len(out) < n:
        tries += 1
        if tries > 200000 * max(n, 1):
            raise RuntimeError(f"puzzle generation stuck at depth {d}")
        steps = [rand_step(rng) for _ in range(d)]
        if not ok_sig(signature(steps)):
            continue
        p = make_puzzle(steps, rng)  # None on overflow/degenerate -> retry
        if p is None or p["prompt"] in seen:
            continue
        seen.add(p["prompt"])
        p["id"], p["depth"] = f"{tag}:d{d}:{len(out):04d}", d
        out.append(p)
    return out


def build_eval_dev(n_eval=100, n_dev=30):
    """-> eval rows, dev rows, held = {depth: set(signatures)} for d>=2. d=2,3: eval/dev draw only from a seeded 30% of all
    signatures (all banned from POOL); d>=4: eval/dev drawn freely, then their signatures are banned. d=1: nothing banned."""
    hr = random.Random(HELD_SEED)
    held, seen, ev, dv = {}, set(), [], []
    for d in (2, 3):
        s = all_sigs(d)
        hr.shuffle(s)
        held[d] = set(s[:math.ceil(0.3 * len(s))])
    er, dr = random.Random(EVAL_SEED), random.Random(DEV_SEED)
    for d in DEPTHS:
        ok = (lambda s, d=d: s in held[d]) if d in held else (lambda s: True)
        e = gen_puzzles(d, n_eval, er, ok, seen, "eval")
        if d >= 4:
            held[d] = {tuple(p["signature"]) for p in e}
            ok = lambda s, d=d: s not in held[d]  # noqa: E731  dev disjoint from eval signatures at d>=4
        g = gen_puzzles(d, n_dev, dr, ok, seen, "dev")
        if d >= 4:
            held[d] |= {tuple(p["signature"]) for p in g}
        ev += e
        dv += g
    return ev, dv, held


def build_eval(n_eval=100):
    return build_eval_dev(n_eval, 30)[0]


def build_pool(depths, seed, held, banned_prompts):
    """depths: list of depth per puzzle. Rejects held-out signatures (asserted) and EVAL/DEV prompts."""
    rng, seen, out = random.Random(seed), set(banned_prompts), []
    for d, n in sorted({d: depths.count(d) for d in set(depths)}.items()):
        out += gen_puzzles(d, n, rng, (lambda s, d=d: s not in held.get(d, ())), seen, f"pool{seed}")
    for p in out:
        assert tuple(p["signature"]) not in held.get(p["depth"], ()), "held-out signature leaked into pool"
        p.pop("answer", None); p.pop("accepted", None)  # unlabelled use only
    rng.shuffle(out)
    return out


def pool_depths(arm, f, n, seed):
    if arm != "leap":
        return [1 + i % 6 for i in range(n)]
    a, b, rng = round(0.4 * n), round(0.3 * n), random.Random(seed)
    return ([min(f + 1, 6)] * a + [min(f + 2, 6)] * b + [rng.randint(1, max(f, 1)) for _ in range(n - a - b)])


def frontier(dev_acc):
    return max([d for d in DEPTHS if dev_acc.get(d, 0) >= 0.5], default=0)


# ------------------------------------------------------------------ prompts / generation
def render_msgs(L, msgs):
    if hasattr(L.tok, "apply_chat_template") and not L.smoke:
        return L.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return "".join(f"{m['role']}: {m['content']}\n" for m in msgs) + "assistant: "


def feedback(src, prompt):
    exs, _ = split_prompt(prompt)
    fn = compile_prog(src)
    parts = []
    for a, b in exs:
        got = sys.modules["creative1"].run_prog(fn, a)
        parts.append(f"{a} -> {'error' if got is None else got} (want {b})")
    return "Your program gives " + "; ".join(parts) + ". Fix it. Reply with only the lambda."


def repair_prompt(L, prompt, src):
    return render_msgs(L, [{"role": "system", "content": SYS}, {"role": "user", "content": prompt},
                           {"role": "assistant", "content": src}, {"role": "user", "content": feedback(src, prompt)}])


_GOOD = ["lambda x: x*x", "lambda x: 2*x+1", "lambda x: x+3", "lambda x: sum(int(d) for d in str(x))", "lambda x: int(str(x)[::-1])",
         "```python\nlambda x: x**2\n```", "lambda x: __import__('os')", "lambda x: x**99999999", "lambda x: [x for _ in range(3)]", "lambda x: 1/0"]


def gen_flat(L, args, model, prompts, rows, sample, temp, rng=None):
    """prompts: rendered strings (duplicates = independent samples); rows: parallel puzzle rows (smoke injection only)."""
    raw = L.generate(model, prompts, max_new=args.max_new, bs=args.gen_bs, sample=sample, temp=temp)
    if args.smoke:  # random tiny model emits noise: inject known-good / true / broken lambdas so verify + repair paths run
        rng = rng or random.Random(0)
        raw = [rng.choice(_GOOD) if rng.random() < 0.4 else (r_["program"] if rng.random() < 0.2 else r) for r, r_ in zip(raw, rows)]
    return raw


def verify(src, prompt):
    f, a = judge(src, prompt)
    return f and a is not None


def prompts_of(L, rows):
    return [L.render(SYS, r["prompt"]) for r in rows]


# ------------------------------------------------------------------ scoring
def score_rows(L, args, model, rows):
    reps = gen_flat(L, args, model, prompts_of(L, rows), rows, False, 0.0)
    recs = []
    for r, rep in zip(rows, reps):
        src = parse_program(rep)
        f, ans = judge(src, r["prompt"])
        recs.append({"id": r["id"], "depth": r["depth"], "program": src, "fits_examples": f, "answer": ans, "correct": is_correct(r, ans)})
    return recs


def score_c16(L, args, model, rows, n, rng):
    reps = gen_flat(L, args, model, [p for p in prompts_of(L, rows) for _ in range(n)], [r for r in rows for _ in range(n)], True, 0.8, rng)
    recs = []
    for i, r in enumerate(rows):
        chosen, ans, nv = None, None, 0
        for rep in reps[i * n:(i + 1) * n]:
            src = parse_program(rep)
            f, a = judge(src, r["prompt"])
            if f and a is not None:
                nv += 1
                if chosen is None:
                    chosen, ans = src, a
        recs.append({"id": r["id"], "depth": r["depth"], "program": chosen, "answered": ans is not None, "answer": ans,
                     "correct": is_correct(r, ans), "n_verified": nv})
    return recs


def by_depth(recs, key="correct"):
    d = {}
    for r in recs:
        d.setdefault(r["depth"], []).append(r[key])
    return {k: sum(v) / len(v) for k, v in sorted(d.items())}


def summarize(recs):
    bd = by_depth(recs)
    return {"by_depth": bd, "mean": sum(bd.values()) / len(bd), "fits_rate": sum(r["fits_examples"] for r in recs) / len(recs)}


def summarize_c16(recs):
    bd = by_depth(recs)
    ans = [r for r in recs if r["answered"]]
    return {"by_depth": bd, "mean": sum(bd.values()) / len(bd), "answered_rate": len(ans) / len(recs),
            "precision": (sum(r["correct"] for r in ans) / len(ans)) if ans else None, "answered_by_depth": by_depth(recs, "answered")}


def dump(path, recs):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in recs))


def score_round(L, args, model, ev, dv, tag, r, out, c16, arc, log, rng):
    t = time.time()
    er = score_rows(L, args, model, ev)
    dump(out / f"eval_{tag}_r{r}.jsonl", er)
    e = summarize(er)
    dr = score_rows(L, args, model, dv)
    dacc = by_depth(dr)
    res = {"round": r, "eval": e, "dev": {"by_depth": dacc, "mean": sum(dacc.values()) / len(dacc)}, "frontier": frontier(dacc)}
    if c16:
        cr = score_c16(L, args, model, ev, 4 if args.smoke else 16, rng)
        dump(out / f"evalc16_{tag}_r{r}.jsonl", cr)
        res["c16"] = summarize_c16(cr)
    if arc is not None:
        from sleep1 import score_arc
        try:
            res["arc_easy"] = score_arc(L, model, arc)["acc"]
        except Exception as ex:  # noqa: BLE001
            res["arc_easy"] = None
            log(f"[arc] failed {ex!r}")
    res["score_seconds"] = time.time() - t
    return res


# ------------------------------------------------------------------ explorers
def explore(L, args, model, rows, arm, rng):
    """-> pairs [(prompt, program, source, depth)], stats."""
    t = time.time()
    n, temp = (args.n_self, 0.8) if arm == "self" else (args.n_leap, 1.0)
    flat_rows = [r for r in rows for _ in range(n)]
    reps = gen_flat(L, args, model, prompts_of(L, flat_rows), flat_rows, True, temp, rng)
    ver, fails = [], []
    for i, r in enumerate(rows):
        v, f = [], []
        for rep in reps[i * n:(i + 1) * n]:
            src = parse_program(rep)
            if src is None:
                continue
            if verify(src, r["prompt"]):
                if src not in v:
                    v.append(src)
            elif src not in f:
                f.append(src)
        ver.append(v)
        fails.append(f)
    rep_ver = [[] for _ in rows]
    n_rep_puz = n_rep_gen = 0
    if arm != "self":
        fr, fp = [], []
        for i, r in enumerate(rows):
            if ver[i] or not fails[i]:
                continue
            n_rep_puz += 1
            fs = fails[i][:2]
            k = args.n_repair // len(fs)
            for s in fs:
                fr += [(i, s)] * k
        fp = [repair_prompt(L, rows[i]["prompt"], s) for i, s in fr]
        n_rep_gen = len(fp)
        out = gen_flat(L, args, model, fp, [rows[i] for i, _ in fr], True, 1.0, rng) if fp else []
        for (i, _), rep in zip(fr, out):
            src = parse_program(rep)
            if src is not None and verify(src, rows[i]["prompt"]) and src not in rep_ver[i]:
                rep_ver[i].append(src)
    pairs, from_s, from_r = [], 0, 0
    vd = {d: 0 for d in DEPTHS}
    for i, r in enumerate(rows):
        got = [(s, "sample") for s in ver[i]] + [(s, "repair") for s in rep_ver[i] if s not in ver[i]]
        for s, how in got[:2]:
            pairs.append((r["prompt"], s, how, r["depth"]))
            from_s += how == "sample"
            from_r += how == "repair"
        vd[r["depth"]] += bool(got)
    nd = {d: sum(1 for r in rows if r["depth"] == d) for d in DEPTHS}
    return pairs, {"n_puzzles": len(rows), "puzzles_by_depth": nd, "verified_by_depth": vd, "verified_puzzles": sum(vd.values()),
                   "verified_by_sample_only": sum(1 for v in ver if v), "repair_puzzles": n_rep_puz, "repair_samples": n_rep_gen,
                   "pairs": len(pairs), "pairs_from_samples": from_s, "pairs_from_repair": from_r, "samples": len(flat_rows),
                   "seconds": time.time() - t}


# ------------------------------------------------------------------ unit checks
def unit_checks(L, args, ev, dv, held):
    sigs = {tuple(p["signature"]) for p in ev + dv}
    for d in DEPTHS:
        assert sum(p["depth"] == d for p in ev) == args.eval_n and sum(p["depth"] == d for p in dv) == args.dev_n
    assert all(p["n_steps"] == p["depth"] for p in ev + dv)
    for p in ev + dv:
        if p["depth"] >= 2:
            assert tuple(p["signature"]) in held[p["depth"]]
    pool = build_pool([1 + i % 6 for i in range(60)] + [2] * 40 + [3] * 40, 5, held, {p["prompt"] for p in ev + dv})
    assert not any(tuple(p["signature"]) in held.get(p["depth"], ()) for p in pool)
    assert not {p["prompt"] for p in pool} & {p["prompt"] for p in ev + dv}
    assert len({tuple(p["signature"]) for p in pool if p["depth"] >= 2} & sigs) == 0
    p0 = pool[0]
    rp = repair_prompt(L, p0["prompt"], "lambda x: x+1")
    assert "Fix it. Reply with only the lambda." in rp and "lambda x: x+1" in rp and p0["prompt"] in rp and "want" in rp
    return {"pool_check_n": len(pool)}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["self", "leapu", "leap", "ref"])
    ap.add_argument("--allow-branch", action="store_true", help="off by default: checker rejects if/else, comparisons, and/or (PREREG-leap1-addendum-1.md)")
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--pool", type=int, default=1000)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay", type=int, default=200)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--gen-bs", type=int, default=128)
    ap.add_argument("--n-self", type=int, default=4)
    ap.add_argument("--n-leap", type=int, default=16)
    ap.add_argument("--n-repair", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=64)
    ap.add_argument("--eval-n", type=int, default=100)
    ap.add_argument("--dev-n", type=int, default=30)
    ap.add_argument("--no-arc", action="store_true")
    ap.add_argument("--c16", action="store_true", help="ref arm: also checked search (16 samples T0.8) on EVAL")
    args = ap.parse_args()
    import creative1
    creative1.NO_BRANCH = not args.allow_branch
    if not hasattr(signal, "setitimer"):  # Windows: no SIGALRM timer; programs are whitelisted (pow <= 6, no loops but str(x)), so run untimed
        def _run_untimed(fn, v, limit=0.1):
            try:
                return creative1._to_int(fn(v))
            except Exception:  # noqa: BLE001
                return None
        creative1.run_prog = _run_untimed
    if args.smoke:
        args.steps, args.bsz, args.replay_bsz, args.pool, args.replay, args.gen_bs = 6, 4, 2, 12, 6, 8
        args.n_self, args.n_leap, args.n_repair, args.max_new, args.eval_n, args.dev_n = 4, 6, 4, 16, 3, 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{args.arm}_s{args.seed}"
    logf = open(out / f"log_{tag}.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    import torch
    from sleep1 import Lang, generic_prompts, load_arc, train
    from train import LORA_TARGETS, load_model
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    lm, tok = load_model(args, device, dtype)
    L = Lang(tok, args.smoke, device)
    rng = random.Random(args.seed)
    ev, dv, held = build_eval_dev(args.eval_n, args.dev_n)
    checks = unit_checks(L, args, ev, dv, held)
    banned = {p["prompt"] for p in ev + dv}
    arc = None
    if not args.no_arc:
        try:
            arc = load_arc(args.smoke)
        except Exception as e:  # noqa: BLE001
            log(f"[arc] load failed {e!r}")
    result = {"arm": args.arm, "model": args.model, "seed": args.seed, "smoke": args.smoke,
              "config": {k: v for k, v in vars(args).items() if k not in ("out",)},
              "heldout": {"signatures_by_depth": {d: len(s) for d, s in sorted(held.items())},
                          "eval_n": len(ev), "dev_n": len(dv), "checks": checks, "pool_signature_overlap": 0},
              "rounds": []}
    rfile = out / f"result_{tag}.json"

    def save():
        result["wall_seconds"] = time.time() - t0
        rfile.write_text(json.dumps(result, indent=1))

    r0 = score_round(L, args, lm, ev, dv, tag, 0, out, args.arm != "ref" or args.c16, arc, log, rng)
    result["rounds"].append(r0)
    save()

    def line(r):
        e, bd = r["eval"], r["eval"]["by_depth"]
        ex = r.get("explore", {})
        log(f"[round] {tag} r{r['round']} mean {e['mean']:.3f} d={' '.join(f'{v:.2f}' for v in bd.values())} dev_f {r['frontier']} "
            f"arc {r.get('arc_easy')} verified {ex.get('verified_puzzles', '-')}/{ex.get('n_puzzles', '-')} pairs {ex.get('pairs', '-')} "
            f"(s {ex.get('pairs_from_samples', '-')} r {ex.get('pairs_from_repair', '-')}) wall {time.time() - t0:.0f}s")

    line(r0)
    if args.arm == "ref":
        save()
        log(f"[done] {tag} wall {result['wall_seconds']:.0f}s -> {rfile}")
        return
    from peft import LoraConfig, get_peft_model
    buf, gp = {}, generic_prompts()[:args.replay]
    for r in range(1, args.rounds + 1):
        tr = time.time()
        f = result["rounds"][-1]["frontier"]
        pool = build_pool(pool_depths(args.arm, f, args.pool, 100 * r + args.seed), 100 * r + args.seed, held, banned)
        pairs, st = explore(L, args, lm, pool, args.arm, rng)
        st["frontier_used"] = f
        for p, s, how, d in pairs:
            buf.setdefault((p, s), (p, s, how, d))
        gprompts = [L.render(None, g) for g in gp]
        resp = L.generate(lm, gprompts, max_new=8 if args.smoke else 48, bs=args.gen_bs)
        replay = []
        for p, rr in zip(gprompts, resp):
            pi = L.ids(p)
            replay.append((pi + L.ids(rr) + [L.eos], len(pi)))
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        examples = []
        for p, s, _, _ in buf.values():
            pi = L.ids(L.render(SYS, p))
            examples.append((pi + L.ids(s) + [L.eos], len(pi)))
        a = argparse.Namespace(**{**vars(args), "seed": 1000 * args.seed + r})
        tt = time.time()
        curve = train(L, pm, examples, a, replay, log) if examples else []
        ts = time.time() - tt
        lm = pm.merge_and_unload()
        for p in lm.parameters():
            p.requires_grad_(False)
        lm.eval()
        res = score_round(L, args, lm, ev, dv, tag, r, out, args.arm != "ref" and r == args.rounds, arc, log, rng)
        res.update({"explore": st, "n_buffer": len(buf), "n_train_examples": len(examples), "train_seconds": ts,
                    "loss_end": curve[-1] if curve else None, "round_seconds": time.time() - tr})
        result["rounds"].append(res)
        (out / f"pairs_{tag}.json").write_text(json.dumps([list(v) for v in buf.values()]))
        save()
        line(res)
    log(f"[done] {tag} wall {result['wall_seconds']:.0f}s -> {rfile}")


if __name__ == "__main__":
    main()
