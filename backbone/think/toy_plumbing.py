"""Toy plumbing check (codi-plan section 9): can the thinking block carry information from a story to the answer at all? A positive control
for the swap and zero lesions. Its numbers say nothing about village.

Task: "Ana is with Bo. Bo is in the mill." + "Where is Ana?" -> "the mill" (random names, 10 places, chance 10%). The story goes only to the refiner
(the slot passes read its prompt cache). The answer pass holds only [notes, question, " [answer]"]: it runs on a SEPARATE prefill of the question alone
(positions placed just before the answer's, as in the village answer pass), so nothing of the story reaches it except through the gated read of the slots.
(board.py's blind=True drops the question too, which this task needs; the question-only cache is the same idea with the question kept.)
Same ThinkBoard and backbone as village: a fresh LoRA trains jointly with the board as in tj (--no-lora: board only), laps 0..4, loss = mean over laps of
answer CE + the step penalty, as board.train_loss. Eval = greedy exact match with the true notes, swapped notes (another row's last-lap slot K/V, other answer),
zeroed notes (all-zero notes on an empty cache, board.zero_notes_kv), and the gates-off read.

    python backbone/think/toy_plumbing.py --out out/toy --alpha-init 0     # gates start shut
    python backbone/think/toy_plumbing.py --out out/toy --alpha-init 0.3   # gates start open (tanh 0.3 = 0.291)
    python backbone/think/toy_plumbing.py --compare out/toy/result_toy_s0_a0.json out/toy/result_toy_s0_a0.3.json

Verdict per run (section 9): pass = EM >= 90% with the swap and zero lesions both <= 20%; bug (proved wrong) = EM <= 20% with the true notes, or EM >= 90% with a swap
cost under 10 points (the lesion is not swapping); anything else is "not shown". The gate check needs both runs: --compare reads the first eval at or above 90%
(a = 0 needing more than twice a = 0.3's steps, or never, shows starvation, 3.1). The refiner's gradient norm is logged for the first 100 steps.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import train as T  # noqa: E402
import board as B  # noqa: E402
import think1 as K  # noqa: E402

NAMES = ["Ana", "Bo", "Cy", "Di", "Ed", "Flo", "Gus", "Hal", "Ivy", "Jo", "Kai", "Lu", "Max", "Ned", "Oli", "Pam", "Quin", "Ray", "Sue", "Tom",
         "Uma", "Vic", "Wes", "Xan", "Yul", "Zed", "Abe", "Bea", "Cal", "Dee", "Eli", "Fay", "Gil", "Hope", "Ike", "Jay", "Kim", "Lee", "Mo", "Nia"]
PLACES = ["mill", "cave", "hut", "pond", "harbour", "barn", "tower", "well", "forge", "grove"]
PASS_EM, PASS_LESION, WRONG_EM, WRONG_SWAP_COST = 0.9, 0.2, 0.2, 0.10


# ---------------------------------------------------------------- data

def make_rows(n, seed, avoid=()):
    """n distinct two-hop rows (A, B, place) not in `avoid`. visit_id is unique per row, depth is 2."""
    rng, seen, rows = random.Random(seed), set(avoid), []
    while len(rows) < n:
        a, b = rng.sample(NAMES, 2)
        place = rng.choice(PLACES)
        if (a, b, place) in seen:
            continue
        seen.add((a, b, place))
        rows.append(dict(id=f"toy-{seed}-{len(rows)}", visit_id=f"toy-{seed}-{len(rows)}", context=f"{a} is with {b}. {b} is in the {place}.",
                         question=f"Where is {a}?", answer=f"the {place}", depth=2, key=(a, b, place)))
    return rows


def make_splits(n_train, n_eval, seed):
    train = make_rows(n_train, seed)
    return train, make_rows(n_eval, seed + 1, avoid={r["key"] for r in train})  # eval stories never appear in train


# ---------------------------------------------------------------- the two passes

@torch.no_grad()
def question_cache(runner, qprompts, p):
    """Prefill of each question prompt alone, left-padded, at positions that END at the story's p_i (the question's last token sits at p_i, the answer's
    position 0), so the answer's offset to the slots (which start at p_i) is the same for every row, as in the village answer pass."""
    from transformers import DynamicCache
    dev = B.model_device(runner)
    ids, mask = T.left_pad([q[:-1] for q in qprompts])
    ids, mask = ids.to(dev), mask.to(dev)
    m = torch.tensor([len(q) - 1 for q in qprompts], device=dev)
    pos = ((mask.cumsum(1) - 1) + (p - m)[:, None]).clamp(min=0)
    C = DynamicCache(config=runner.cfg)
    B.run_layers(runner, runner.lm.model.embed_tokens(ids), mask, pos, C)
    return C, mask, B.last_ids(qprompts, dev)


def toy_inputs(runner, enc, rows, device):
    """Story side (cache C, mask, p) and answer side (question-only cache Cq, mask_q, last token) of a list of rows, plus the answer tokens."""
    story = [enc.prompt(r)[0] for r in rows]
    C, mask, p = B.prefill(runner, story)
    Cq, mq, lq = question_cache(runner, [enc.prompt(dict(r, context=""))[0] for r in rows], p)
    return (C, mask, p), (Cq, mq, lq), [enc.ids(" " + r["answer"]) + [enc.eos] for r in rows]


def toy_loss(board, runner, side, ans, L_max, n_norm, row_frac, lam=K.LAMBDA, ckpt=True):
    """board.train_loss with the answer pass moved onto the question-only cache: mean over laps 0..L_max of answer CE / n_norm + lam * row_frac * penalty."""
    (C, mask, p), (Cq, mq, lq) = side
    kv, st = B.think(board, runner, C, mask, p, L_max, keep=range(L_max + 1), stats=False, ckpt=ckpt)
    ces = []
    for t in range(L_max + 1):
        s, n = B.answer_ce(runner, board, Cq, mq, p, lq, ans, kv[t], ckpt=ckpt)
        ces.append(s)
    pen = torch.stack(st["pen"]).mean() if st["pen"] else ces[0].new_zeros(())
    return torch.stack(ces).mean() / (n_norm or n) + lam * row_frac * pen


# ---------------------------------------------------------------- eval

def swap_in_batch(answers):
    """For each row the nearest following row (cyclic) with another answer; its own index if the whole batch has one answer (counted by the caller)."""
    n = len(answers)
    return [next(((i + s) % n for s in range(1, n) if answers[(i + s) % n] != answers[i]), i) for i in range(n)]


@torch.no_grad()
def eval_toy(runner, board, enc, rows, device, L, bsz=100):
    """Greedy exact match on rows with the true, swapped, zeroed notes and gates off. Returns {acc..., n, swap_same_answer_rows}."""
    hits = {k: 0 for k in ("true", "swap", "zero", "gates_off")}
    same, off = 0, torch.zeros_like(board.alpha)
    for k in range(0, len(rows), bsz):
        mb = rows[k:k + bsz]
        (C, mask, p), (Cq, mq, lq), _ = toy_inputs(runner, enc, mb, device)
        kv = B.think(board, runner, C, mask, p, L, keep={L}, stats=False)[0][L]
        idx = swap_in_batch([r["answer"] for r in mb])
        same += sum(i == j for i, j in enumerate(idx))
        for kind, skv, gates in (("true", kv, None), ("swap", B.swap_kv(kv, torch.tensor(idx)), None), ("zero", B.zero_notes_kv(runner, board, p), None), ("gates_off", kv, off)):
            gen = B.decode(runner, board, Cq, mq, p, lq, skv, eos=enc.eos, gates=gates)
            hits[kind] += sum(T.normalise(enc.tok.decode(g, skip_special_tokens=True)) == T.normalise(r["answer"]) for g, r in zip(gen, mb))
    n = len(rows)
    return dict(n=n, em_true=hits["true"] / n, em_swap=hits["swap"] / n, em_zero=hits["zero"] / n, em_gates_off=hits["gates_off"] / n, swap_same_answer_rows=same)


def verdict(ev):
    """Section 9 on one eval. 'pass' | 'bug' (proved wrong: a code bug) | 'not shown'. Returns (label, reason)."""
    t, s, z = ev["em_true"], ev["em_swap"], ev["em_zero"]
    if t <= WRONG_EM:
        return "bug", f"EM with true notes {100 * t:.1f}% <= {100 * WRONG_EM:.0f}% (chance is 10%)"
    if t >= PASS_EM and t - s < WRONG_SWAP_COST:
        return "bug", f"EM {100 * t:.1f}% >= 90% but the swap cost is only {100 * (t - s):.1f} points: the lesion is not swapping"
    if t >= PASS_EM and s <= PASS_LESION and z <= PASS_LESION:
        return "pass", f"EM {100 * t:.1f}%, swap {100 * s:.1f}%, zero {100 * z:.1f}%"
    return "not shown", f"EM {100 * t:.1f}%, swap {100 * s:.1f}%, zero {100 * z:.1f}% (neither the pass nor the bug rule)"


def first_ge90(evals):
    return next((e["step"] for e in evals if e["em_true"] >= PASS_EM), None)


def compare(a0, a3):
    """Gate check of section 9 from two result dicts (gate start 0 and 0.3): starvation shown if a = 0 needs more than twice the steps, or never reaches 90%."""
    s0, s3 = a0["first_ge90_step"], a3["first_ge90_step"]
    if s3 is None:
        shown, why = None, "the a = 0.3 run never reached 90%: the gate check cannot be read"
    elif s0 is None:
        shown, why = True, f"a = 0 never reached 90%; a = 0.3 did at step {s3}"
    else:
        shown, why = s0 > 2 * s3, f"first >= 90% at step {s0} (a = 0) vs {s3} (a = 0.3)"
    return dict(starvation_shown=shown, why=why, alpha0=dict(alpha_init=a0["alpha_init"], first_ge90_step=s0), alpha03=dict(alpha_init=a3["alpha_init"], first_ge90_step=s3))


# ---------------------------------------------------------------- training

def train_toy(runner, pm, board, enc, rows, eval_rows, device, args, tr):
    """Joint training (LoRA if pm, and board). Returns the abort reason or None. Logs per-group grad norms for steps <= 100 and an eval every --eval-every."""
    lora = [q for q in pm.parameters() if q.requires_grad] if pm is not None else []
    groups = K.board_groups(board) + ([dict(name="lora", params=lora, lr=K.LR, base=K.LR)] if lora else [])
    opt = torch.optim.AdamW(groups, weight_decay=0.0, betas=(0.9, 0.999))
    stream = K.batches(len(rows), args.seed + 1000, args.bsz)
    warm = min(60, max(1, args.steps // 10))
    losses, t0 = tr["step_losses"], time.time()
    train_mode = lambda on: [m.train(on) for m in ((pm,) if pm is not None else ()) + (runner.lm,)]
    train_mode(True)
    for step in range(args.steps):
        n = step + 1
        batch = [rows[i] for i in next(stream)]
        n_norm = sum(len(enc.ids(" " + r["answer"])) + 1 for r in batch)
        for g in opt.param_groups:
            g["lr"] = T.cosine_lr(step, args.steps, g["base"], warm)
        total = 0.0
        for k in range(0, len(batch), args.micro_bsz):
            mb = batch[k:k + args.micro_bsz]
            story, qside, ans = toy_inputs(runner, enc, mb, device)
            loss = toy_loss(board, runner, (story, qside), ans, args.lmax, n_norm, len(mb) / len(batch), ckpt=not args.no_lap_ckpt)
            loss.backward()
            total += loss.item()
        if not math.isfinite(total):
            return f"NaN loss at step {n}"
        gn = {g["name"]: float(torch.nn.utils.clip_grad_norm_(g["params"], 1.0)) for g in opt.param_groups}
        if not all(math.isfinite(v) for v in gn.values()):
            return f"non-finite gradient at step {n}"
        if n <= 100:
            tr["grad_norm_first100"].append(dict(step=n, **gn))
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(total)
        if n > K.GATE["window"] and K.diverged(losses):
            return f"loss diverged at step {n}: last-20 mean > {K.GATE['div']}x first-20 mean"
        if n % args.eval_every == 0 or n == args.steps:
            train_mode(False)
            ev = eval_toy(runner, board, enc, eval_rows, device, args.lmax)
            train_mode(True)
            ev.update(step=n, loss=sum(losses[-10:]) / len(losses[-10:]), alpha_abs=float(board.gate().detach().abs().mean()), refiner_grad_norm=gn["refiner"])
            tr["evals"].append(ev)
            print(f"[toy] step {n}/{args.steps} loss {ev['loss']:.4f} EM true {100 * ev['em_true']:.1f} swap {100 * ev['em_swap']:.1f} zero {100 * ev['em_zero']:.1f} "
                  f"off {100 * ev['em_gates_off']:.1f} |tanh a| {ev['alpha_abs']:.3f} gn_refiner {gn['refiner']:.4f} {time.time() - t0:.0f}s", flush=True)
    train_mode(False)
    return None


def run(args):
    t_start = time.time()
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    lm, tok = T.load_model(argparse.Namespace(smoke=args.smoke, seed=args.seed, model=args.model), device, dtype)
    enc = T.Encoder(tok, 512)
    train, evalr = make_splits(args.n_train, args.n_eval, args.seed)
    pm = None if args.no_lora else K.lora_model(lm)
    runner = T.Runner(pm.base_model.model if pm is not None else lm, loops=1)
    runner.checkpoint = False
    torch.manual_seed(args.seed)
    board = B.ThinkBoard.from_model(runner.lm, tok, K=args.k, alpha_init=args.alpha_init).to(device)
    tr = dict(step_losses=[], evals=[], grad_norm_first100=[])
    print(f"[toy] alpha_init {args.alpha_init} steps {args.steps} bsz {args.bsz} lmax {args.lmax} lora {pm is not None} train {len(train)} eval {len(evalr)} device {device}", flush=True)
    aborted = train_toy(runner, pm, board, enc, train, evalr, device, args, tr)
    result = dict(task="toy two-hop", alpha_init=args.alpha_init, seed=args.seed, steps=args.steps, bsz=args.bsz, lmax=args.lmax, k_slots=args.k, lora=pm is not None,
                  n_train=len(train), n_eval=len(evalr), model=args.model, smoke=args.smoke, device=str(device), aborted=aborted, train=tr,
                  final=tr["evals"][-1] if tr["evals"] else None, first_ge90_step=first_ge90(tr["evals"]), env=K.env_info(device, dtype), seconds=time.time() - t_start)
    result["verdict"], result["verdict_reason"] = verdict(result["final"]) if result["final"] else ("not shown", f"no eval: {aborted}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"result_toy_s{args.seed}_a{args.alpha_init:g}.json"
    path.write_text(json.dumps(result, indent=1))
    print(f"[toy] VERDICT {result['verdict'].upper()}: {result['verdict_reason']}; wrote {path}", flush=True)
    return result


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out/toy", help="dir for result_toy_s{seed}_a{alpha_init}.json")
    ap.add_argument("--alpha-init", type=float, default=0.0, help="gate start: run at 0 and at 0.3 (section 9 gate check)")
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--micro-bsz", type=int, default=4)
    ap.add_argument("--lmax", type=int, default=4, help="laps 0..lmax in the loss and the eval")
    ap.add_argument("--k", type=int, default=16, help="board slots")
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-eval", type=int, default=500)
    ap.add_argument("--eval-every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--device", default="auto", help="auto / cpu / cuda")
    ap.add_argument("--no-lora", action="store_true", help="train the board only on the frozen base model (default: a fresh LoRA trains with it, as in tj)")
    ap.add_argument("--no-lap-ckpt", action="store_true", help="keep activations instead of recomputing them in backward (more memory, same result)")
    ap.add_argument("--smoke", action="store_true", help="the tiny random qwen3_5 of think1 --smoke (for tests)")
    ap.add_argument("--compare", nargs=2, metavar=("A0_JSON", "A03_JSON"), help="read two finished runs (gate start 0, then 0.3) and print the gate check; trains nothing")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse(argv)
    if args.compare:
        a0, a3 = (json.loads(Path(f).read_text()) for f in args.compare)
        res = compare(a0, a3)
        print(json.dumps(res, indent=1))
        return 0
    run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
