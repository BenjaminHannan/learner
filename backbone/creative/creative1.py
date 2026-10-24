"""Creative-1 (see backbone/PREREG-creative1.md). Arms: f0 (greedy program), c16 (16 samples, check, abstain), sleep (F1 + post-sleep C16).

  python backbone/creative/creative1.py --arm c16 --model Qwen/Qwen3.5-0.8B --out out/creative/c16
  python backbone/creative/creative1.py --arm sleep --smoke --out /tmp/x      # CPU, tiny random qwen3_5
  python backbone/creative/creative1.py --arm sleep --aha --model Qwen/Qwen3.5-0.8B --out out/creative/aha   # Aha-1 (PREREG-aha1.md)
  python backbone/creative/creative1.py --arm sleep --smoke --aha --out /tmp/x

Never reads any test.jsonl. The C2 pool's `answer` field is never used (fit = reproduces the examples shown in the prompt).
"""
import argparse
import ast
import json
import random
import re
import signal
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sleep"))
sys.path.insert(0, str(HERE.parent))
from sleep1 import Lang, generic_prompts, train  # noqa: E402  (reused: chat template, generation, LoRA train + KL guard)
from train import LORA_TARGETS, load_model  # noqa: E402

SYS = "Write a Python lambda that maps the input to the output for all examples. Reply with only the lambda."

# ------------------------------------------------------------------ primitives, HARD set, dreams
PRIMS = ["add", "sub", "mul", "sq", "fdiv", "mod", "rev", "dsum"]


def _rev(v):
    return int(str(v)[::-1])


def _dsum(v):
    return sum(int(d) for d in str(v))


def apply_prim(name, c, v):
    if name == "add": return v + c
    if name == "sub": return v - c
    if name == "mul": return v * c
    if name == "sq": return v * v
    if name == "fdiv": return v // c
    if name == "mod": return v % c
    if name == "rev": return _rev(v)
    if name == "dsum": return _dsum(v)
    raise ValueError(name)


def rand_step(rng):
    n = rng.choice(PRIMS)
    c = {"add": lambda: rng.randint(1, 9), "sub": lambda: rng.randint(1, 9), "mul": lambda: rng.randint(2, 5),
         "fdiv": lambda: rng.randint(2, 5), "mod": lambda: rng.randint(2, 9)}.get(n, lambda: None)()
    return (n, c)


def run_steps(steps, v):
    for n, c in steps:
        v = apply_prim(n, c, v)
        if v < 0 or v >= 10 ** 6:
            return None
    return v


def canon(steps):
    e = "x"
    for n, c in steps:
        e = {"add": f"({e}+{c})", "sub": f"({e}-{c})", "mul": f"({e}*{c})", "sq": f"({e})**2", "fdiv": f"({e})//{c}",
             "mod": f"({e})%{c}", "rev": f"int(str({e})[::-1])", "dsum": f"sum(int(d) for d in str({e}))"}[n]
    return "lambda x: " + e


def signature(steps):
    return tuple(n for n, _ in steps)


def make_puzzle(steps, rng):
    """3 examples + 1 query on distinct inputs in 1..30; None if any output invalid or the rule is degenerate."""
    if any(a == b == "rev" for a, b in zip(signature(steps), signature(steps)[1:])):
        return None  # rev,rev is a near no-op
    xs = rng.sample(range(1, 31), 4)
    ys = [run_steps(steps, v) for v in xs]
    if any(y is None for y in ys) or len(set(ys)) < 3:
        return None
    ex = "; ".join(f"{a} -> {b}" for a, b in zip(xs[:3], ys[:3]))
    return {"prompt": f"Examples: {ex}. Now {xs[3]} -> ?", "answer": str(ys[3]), "accepted": [str(ys[3])],
            "steps": [[n, c] for n, c in steps], "signature": list(signature(steps)), "n_steps": len(steps), "program": canon(steps)}


def build_hard(n=300, seed=0):
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:
        steps = [rand_step(rng) for _ in range(3)]
        p = make_puzzle(steps, rng)
        if p is None or p["prompt"] in seen:
            continue
        seen.add(p["prompt"])
        p["id"] = f"hard:{len(out):04d}"
        p["kind"] = "hard3"
        out.append(p)
    return out


def build_dreams(hard, n, seed=1):
    banned = {tuple(h["signature"]) for h in hard}
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:
        k = rng.choices([1, 2, 3], [0.2, 0.35, 0.45])[0]
        steps = [rand_step(rng) for _ in range(k)]
        if signature(steps) in banned:
            continue
        p = make_puzzle(steps, rng)
        if p is None or p["prompt"] in seen:
            continue
        assert tuple(p["signature"]) not in banned
        seen.add(p["prompt"])
        p["id"] = f"dream:{len(out):04d}"
        p["kind"] = f"dream{k}"
        out.append(p)
    assert not ({tuple(d["signature"]) for d in out} & banned)
    return out


# ------------------------------------------------------------------ safe program evaluation
SAFE = {"abs": abs, "min": min, "max": max, "int": int, "str": str, "sum": sum, "len": len, "round": round}
_OK = (ast.Expression, ast.Lambda, ast.arguments, ast.arg, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call,
       ast.Name, ast.Constant, ast.Subscript, ast.Slice, ast.GeneratorExp, ast.ListComp, ast.comprehension, ast.Tuple, ast.List,
       ast.Load, ast.Store, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Not, ast.And,
       ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Index if hasattr(ast, "Index") else ast.Load)


AHA = False  # Aha-1 (--aha): C16 samples are written from prompts that hide one example each (PREREG-aha1.md)
NO_BRANCH = False  # Creative-2 (--no-branch): reject if/else, comparisons and and/or, so a lookup table of the examples can't "fit"
_BRANCH = (ast.IfExp, ast.Compare, ast.BoolOp)


def _check(tree):
    bound = {"x"}
    for n in ast.walk(tree):
        if isinstance(n, ast.comprehension):
            for t in ast.walk(n.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
        if isinstance(n, ast.arg):
            bound.add(n.arg)
    for n in ast.walk(tree):
        if not isinstance(n, _OK) or (NO_BRANCH and isinstance(n, _BRANCH)):
            raise ValueError("node " + type(n).__name__)
        if isinstance(n, ast.Name) and n.id not in bound and n.id not in SAFE:
            raise ValueError("name " + n.id)
        if isinstance(n, ast.Constant) and not (isinstance(n.value, (int, float, str, bool)) and (not isinstance(n.value, (int, float)) or abs(n.value) <= 10 ** 6)):
            raise ValueError("const")
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow):
            if not (isinstance(n.right, ast.Constant) and isinstance(n.right.value, int) and 0 <= n.right.value <= 6):
                raise ValueError("pow")
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in SAFE and not n.keywords):
            raise ValueError("call")


class _TO(Exception):
    pass


def _alarm(sig, frm):
    raise _TO()


def _to_int(r):
    if isinstance(r, bool):
        r = int(r)
    if isinstance(r, float) and r == r and abs(r) < 1e15 and r == int(r):
        r = int(r)
    return r if isinstance(r, int) and abs(r) < 10 ** 15 else None


def compile_prog(src):
    """src: 'lambda x: ...' -> callable or None. Static whitelist check, restricted globals."""
    try:
        tree = ast.parse(src.strip(), mode="eval")
        if not isinstance(tree.body, ast.Lambda):
            return None
        _check(tree)
        return eval(compile(tree, "<prog>", "eval"), {"__builtins__": SAFE}, {})
    except BaseException as e:  # noqa: BLE001
        if isinstance(e, KeyboardInterrupt):
            raise
        return None


def run_prog(fn, v, limit=0.1):
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, limit)
    try:
        return _to_int(fn(v))
    except BaseException as e:  # noqa: BLE001
        if isinstance(e, KeyboardInterrupt):
            raise
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


_LAM = re.compile(r"lambda\s+x\s*:[^\n]*")


def parse_program(text):
    """First `lambda x: ...` in the reply -> cleaned source string that compiles, else None."""
    m = _LAM.search(text or "")
    if not m:
        return None
    s = re.sub(r"\s+", " ", m.group(0)).strip()
    for _ in range(6):
        if compile_prog(s) is not None:
            return s
        s = s.rstrip("`'\".;, ")
        if compile_prog(s) is not None:
            return s
        if s.count(")") > s.count("("):
            s = s[:-1]
        else:
            break
    return None


_EX = re.compile(r"(-?\d+) -> (-?\d+)")
_Q = re.compile(r"Now (-?\d+) -> \?")


def split_prompt(prompt):
    exs = [(int(a), int(b)) for a, b in _EX.findall(prompt.split(". Now")[0])]
    return exs, int(_Q.search(prompt).group(1))


def hide_example(prompt, h):
    """Same puzzle with example h removed (two examples left, same query and format)."""
    exs, q = split_prompt(prompt)
    keep = "; ".join(f"{a} -> {b}" for i, (a, b) in enumerate(exs) if i != h)
    return f"Examples: {keep}. Now {q} -> ?"


SHORTEST = False  # Aha-2 (--shortest): among fitting samples pick the fewest AST nodes, in C16 and for sleep data


def size(src):
    return sum(1 for _ in ast.walk(ast.parse(src.strip(), mode="eval")))


def has_branch(src):
    """True if the program contains an if/else, comparison or and/or."""
    try:
        return any(isinstance(n, _BRANCH) for n in ast.walk(ast.parse(src.strip(), mode="eval")))
    except SyntaxError:
        return False


def judge(src, prompt):
    """-> (fits_all_examples, answer string or None) for one program source."""
    if src is None:
        return False, None
    fn = compile_prog(src)
    if fn is None:
        return False, None
    exs, q = split_prompt(prompt)
    fits = all(run_prog(fn, a) == b for a, b in exs)
    r = run_prog(fn, q)
    return fits, (str(r) if r is not None else None)


# ------------------------------------------------------------------ generation / scoring
class Ctx:
    def __init__(self, L, args):
        self.L, self.args = L, args
        self.n_samples = 4 if args.smoke else 16
        self.max_new = 16 if args.smoke else 64

    def user_prompts(self, rows):
        return [self.L.render(SYS, r["prompt"]) for r in rows]

    def propose(self, model, rows, n, sample, seed=0):
        """-> list (per row) of n raw replies. Smoke mode injects a few known-good lambdas so the fit path is exercised."""
        ps = self.user_prompts(rows)
        flat = [p for p in ps for _ in range(n)]
        raw = self.L.generate(model, flat, max_new=self.max_new, bs=self.args.gen_bs, sample=sample, temp=0.8)
        return self._smoke_inject(raw, rows, n, seed)

    def propose_holdout(self, model, rows, n, seed=0):
        """Aha-1: like propose(sample=True), but sample i of each row sees the prompt with example i % 3 hidden."""
        flat = [self.L.render(SYS, hide_example(r["prompt"], i % 3)) for r in rows for i in range(n)]
        raw = self.L.generate(model, flat, max_new=self.max_new, bs=self.args.gen_bs, sample=True, temp=0.8)
        return self._smoke_inject(raw, rows, n, seed)

    def _smoke_inject(self, raw, rows, n, seed):
        if self.args.smoke:
            rng = random.Random(seed)
            good = ["lambda x: x*x", "lambda x: 2*x+1", "lambda x: x+3", "lambda x: sum(int(d) for d in str(x))", "lambda x: int(str(x)[::-1])",
                    "```python\nlambda x: x**2\n```", "lambda x: __import__('os')", "lambda x: x**99999999", "lambda x: [x for _ in range(3)]",
                    "lambda x: sum(int(d) for d in str(x)) * (x*x*x)", "lambda x: 1/0"]
            raw = [rng.choice(good) if rng.random() < 0.5 else r for r in raw]
        return [raw[i * n:(i + 1) * n] for i in range(len(rows))]


def is_correct(row, ans):
    return ans is not None and ans in [str(a) for a in row.get("accepted", [row["answer"]])]


def tally(rows, flags, key):
    d = {}
    for r, f in zip(rows, flags):
        d.setdefault(r[key], []).append(f)
    return {k: {"acc": sum(v) / len(v), "n": len(v)} for k, v in sorted(d.items())}


def eval_f0(C, model, rows, name):
    reps = [x[0] for x in C.propose(model, rows, 1, sample=False)]
    ok, fit, parsed, ex = [], [], [], []
    for r, rep in zip(rows, reps):
        src = parse_program(rep)
        f, ans = judge(src, r["prompt"])
        c = is_correct(r, ans)
        ok.append(c); fit.append(f); parsed.append(src is not None)
        if len(ex) < 15:
            ex.append({"id": r["id"], "prompt": r["prompt"], "gold": r["answer"], "reply": rep[:200], "program": src, "fits_examples": f, "answer": ans, "correct": c})
    out = {"set": name, "arm": "f0", "n": len(rows), "acc": sum(ok) / len(ok), "parse_rate": sum(parsed) / len(rows), "fits_examples_rate": sum(fit) / len(rows),
           "by_kind": tally(rows, ok, "kind"), "examples": ex}
    if "n_steps" in rows[0]:
        out["by_steps"] = tally(rows, ok, "n_steps")
    return out


def eval_c16(C, model, rows, name, seed=0):
    reps = C.propose_holdout(model, rows, C.n_samples, seed=seed) if AHA else C.propose(model, rows, C.n_samples, sample=True, seed=seed)
    ok, answered, fitany, ex, nfit = [], [], [], [], []
    ans_all, br = [], []  # br: (answered program has a branch, correct)
    for r, rs in zip(rows, reps):
        chosen, ans, nf, hid = None, None, 0, None
        for i, rep in enumerate(rs):
            src = parse_program(rep)
            f, a = judge(src, r["prompt"])  # always the FULL prompt: must reproduce all 3 examples
            if f and a is not None:
                nf += 1
                if chosen is None or (SHORTEST and size(src) < size(chosen)):
                    chosen, ans, hid = src, a, (i % 3 if AHA else None)
        c = is_correct(r, ans)
        if chosen is not None:
            br.append((has_branch(chosen), c))
        ok.append(c); answered.append(ans is not None); nfit.append(nf)
        ans_all.append(ans)
        if len(ex) < 15:
            ex.append({"id": r["id"], "prompt": r["prompt"], "gold": r["answer"], "program": chosen, "answer": ans, "abstained": ans is None,
                       "correct": c, "n_fitting_of_samples": nf, "hidden": hid, "sample0": rs[0][:150]})
    na = sum(answered)
    wrong_answered = sum(1 for a, c in zip(answered, ok) if a and not c)
    bc = [c for b, c in br if b]
    out = {"set": name, "arm": "c16", "n": len(rows), "n_samples": C.n_samples, "acc": sum(ok) / len(ok), "answered_rate": na / len(rows),
           "precision_among_answered": (sum(ok) / na) if na else None, "wrong_among_answered_frac_of_all": wrong_answered / len(rows),
           "mean_fitting_samples": sum(nfit) / len(nfit), "branch_answered": len(bc),
           "branch_precision": (sum(bc) / len(bc)) if bc else None, "by_kind": tally(rows, ok, "kind"), "examples": ex}
    if "n_steps" in rows[0]:
        out["by_steps"] = tally(rows, ok, "n_steps")
    return out


def load_jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


# ------------------------------------------------------------------ sleep data
def collect_fitting(C, model, rows, per_row, log, tag):
    """Sample n programs per row; keep up to per_row distinct fitting sources per row (fit = reproduces the prompt's own examples)."""
    reps = C.propose_holdout(model, rows, C.n_samples, seed=7) if AHA else C.propose(model, rows, C.n_samples, sample=True, seed=7)
    pairs, n_with, n_br = [], 0, 0
    for r, rs in zip(rows, reps):
        kept = []
        for rep in rs:
            src = parse_program(rep)
            f, a = judge(src, r["prompt"])
            if f and a is not None and src not in kept:
                kept.append(src)
            if len(kept) >= per_row and not SHORTEST:
                break
        if SHORTEST:
            kept = sorted(kept, key=size)[:per_row]
        n_with += bool(kept)
        pairs += [(r["prompt"], s) for s in kept]  # full prompt, even under --aha
        n_br += sum(has_branch(s) for s in kept)
    log(f"[sleep] {tag}: {n_with}/{len(rows)} puzzles with a fitting program, {len(pairs)} pairs, {n_br} with a branch")
    return pairs, n_with, n_br


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["f0", "c16", "sleep"])
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gen-bs", type=int, default=128)
    ap.add_argument("--n-dreams", type=int, default=1000)
    ap.add_argument("--no-branch", action="store_true", help="Creative-2: checker rejects branching programs (PREREG-creative2.md)")
    ap.add_argument("--shortest", action="store_true", help="Aha-2: pick the shortest fitting program (PREREG-aha2.md)")
    ap.add_argument("--aha", action="store_true", help="Aha-1: each C16 sample hides one example (PREREG-aha1.md)")
    args = ap.parse_args()
    global NO_BRANCH, AHA, SHORTEST
    NO_BRANCH, AHA, SHORTEST = args.no_branch, args.aha, args.shortest
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / f"log_{args.arm}.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    if args.smoke:
        args.steps, args.bsz, args.replay_bsz, args.n_dreams, args.gen_bs = 6, 4, 2, 24, 8
    lm, tok = load_model(args, device, dtype)
    L = Lang(tok, args.smoke, device)
    C = Ctx(L, args)
    dev = load_jsonl(HERE / "c2_dev.jsonl")
    pool = load_jsonl(HERE / "c2_pool.jsonl")
    for r in pool:  # unlabelled use only
        r.pop("answer", None); r.pop("accepted", None)
    hard = build_hard(300, 0)
    dreams = build_dreams(hard, args.n_dreams)
    if args.smoke:
        dev, pool, hard = dev[:10], pool[:12], hard[:10]
    sets = {"c2_dev": dev, "hard": hard}
    log(f"[data] dev {len(dev)} hard {len(hard)} pool {len(pool)} dreams {len(dreams)}; hard signatures {len({tuple(h['signature']) for h in hard})}")
    result = {"arm": args.arm, "model": args.model, "smoke": args.smoke, "n_samples": C.n_samples, "no_branch": NO_BRANCH, "aha": AHA, "shortest": SHORTEST,
              "hard_signatures": len({tuple(h['signature']) for h in hard}), "hard_example_puzzles": [
                  {k: h[k] for k in ("prompt", "answer", "program", "signature")} for h in hard[:5]]}
    model = lm

    def run_evals(m, tag, modes):
        for name, rows in sets.items():
            for mode in modes:
                res = eval_f0(C, m, rows, name) if mode == "f0" else eval_c16(C, m, rows, name)
                key = f"{tag}_{mode}_{name}"
                result[key] = res
                extra = f" answered {res['answered_rate']:.3f} prec {res['precision_among_answered']}" if mode == "c16" else ""
                log(f"[eval] {key} acc {res['acc']:.3f} (n={res['n']}){extra}")

    if args.arm == "f0":
        run_evals(lm, "pre", ["f0"])
    elif args.arm == "c16":
        run_evals(lm, "pre", ["c16"])
    else:
        pairs_pool, n_pool_fit, n_pool_br = collect_fitting(C, lm, pool, 2, log, "pool")
        pairs_dream_q, n_dream_fit, n_dream_br = collect_fitting(C, lm, dreams, 1, log, "dreams(qwen)")
        pairs_dream_c = [(d["prompt"], d["program"]) for d in dreams]
        pairs = pairs_pool + pairs_dream_c + [p for p in pairs_dream_q]
        result["sleep_data"] = {"pool_puzzles": len(pool), "pool_with_fit": n_pool_fit, "pool_pairs": len(pairs_pool), "dreams": len(dreams),
                                "dream_canonical_pairs": len(pairs_dream_c), "dream_qwen_fit_puzzles": n_dream_fit, "dream_qwen_pairs": len(pairs_dream_q),
                                "pool_pairs_with_branch": n_pool_br, "dream_qwen_pairs_with_branch": n_dream_br,
                                "total_pairs": len(pairs), "examples": [{"prompt": p, "target": t} for p, t in random.Random(0).sample(pairs, min(15, len(pairs)))]}
        (out / "sleep_pairs.json").write_text(json.dumps(pairs, indent=0))
        gp = generic_prompts()[:(6 if args.smoke else 200)]
        gprompts = [L.render(None, g) for g in gp]
        resp = L.generate(lm, gprompts, max_new=8 if args.smoke else 48, bs=args.gen_bs)
        replay = []
        for p, r in zip(gprompts, resp):
            pi = L.ids(p)
            replay.append((pi + L.ids(r) + [L.eos], len(pi)))
        from peft import LoraConfig, get_peft_model
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        log(f"[lora] trainable {sum(p.numel() for p in pm.parameters() if p.requires_grad):,}")
        examples = []
        for p, t in pairs:
            pi = L.ids(L.render(SYS, p))
            examples.append((pi + L.ids(t) + [L.eos], len(pi)))
        result["n_train_examples"] = len(examples)
        tt = time.time()
        result["loss_curve"] = train(L, pm, examples, args, replay, log)
        result["train_seconds"] = time.time() - tt
        pm.eval()
        run_evals(pm, "post", ["f0", "c16"])  # F1 = post_f0
    result["wall_seconds"] = time.time() - t0
    (out / f"result_{args.arm}.json").write_text(json.dumps(result, indent=1))
    log(f"[done] {args.arm} wall {result['wall_seconds']:.0f}s -> {out}/result_{args.arm}.json")


if __name__ == "__main__":
    main()
