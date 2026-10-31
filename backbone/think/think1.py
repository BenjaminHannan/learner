"""Think-1 harness (backbone/think/PREREG.md, IMPL-SPEC.md section 3): every arm, training, evaluation, result JSON.

Arms:  a      LoRA on the village rows (stage 1, 418 steps)         b      a + layers 8-11 run 3 times (stage 1)
       aplus  a's adapter, LoRA trained 1,254 more steps            bplus  b's adapter, LoRA trained 1,254 more steps
       t      a's adapter frozen, only the ThinkBoard (board.py) trains, laps 0..8 or 12
       t1     as t but L_max = 1                                    tw     as t1 with K=144 slots
       tj     joint: a's adapter AND the board train together (1,254 steps), loss = aplus loss + board loss at fixed L_max = --lmax (4)
       tf     "forced, then released": as tj, but with probability p_blind(step) a micro-batch's board loss uses BLIND answer passes (answer tokens see no
              prompt, only the board read); p_blind falls linearly from --blind-p (0.5) to 0 at --blind-until (0.6) of training. Eval adds blind{L}
       tc     control for tj: tj's exact loop and loss with the thinking block off: lmax forced to 0 (laps 0..0), alpha frozen at 0, no board parameter trained
              (optimizer: the "lora" group only), so the LoRA gets the aplus loss + the lap-0 board-path answer CE with a closed board. Gate check skipped.
       ws     written steps (codi-plan P1): as aplus (LoRA only, a's adapter, 1,254 steps), but every row of a batch appears twice, once as the direct
              example and once as "Step 1: <line>. Step 2: ... The answer is: X" (chain order; " [steps]" ends the prompt instead of " [answer]")
       wsham  as ws with each row's step text replaced by the same number of filler tokens (" ." dot by dot)
       tsd    tj plus a step decoder that reads only the notes (codi-plan P2b, steps.py): lap k's notes -> written step k (later laps -> the answer)
       tsd1   control for tsd: the refiner runs once and its lap-1 notes feed all four decoder passes (same parameters, decoder passes and targets)
`--smoke` runs every village arm end to end on a tiny random qwen3_5 on CPU (into OUT/smoke/) and then summarize.py.
The village `test` split is never read. Step counts are per-arm defaults, not flags to change in the prereg run.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import train as T  # noqa: E402
import board as B  # noqa: E402
import steps as S  # noqa: E402
from xent import fixed_cross_entropy  # noqa: E402

ARMS = ("a", "b", "aplus", "bplus", "t", "t1", "tw", "tj", "tf", "tc", "ws", "wsham", "tsd", "tsd1", "br", "aplong", "hplain", "hloop", "hloopi", "hloopd", "hplains", "hloops")
STAGE1, STAGE2 = ("a", "b"), ("aplus", "bplus", "t", "t1", "tw", "tj", "tf", "tc", "ws", "wsham", "tsd", "tsd1", "br", "aplong")
BOARD = ("t", "t1", "tw", "tj", "tf", "tc", "tsd", "tsd1")  # BOARD arms build a ThinkBoard; only tj / tf / tc / tsd / tsd1 also train the LoRA (tc: board shut and frozen)
JOINT = ("tj", "tf", "tc", "tsd", "tsd1")
WRITTEN, SD = ("ws", "wsham"), ("tsd", "tsd1")  # P1 arms (LoRA only, no board); P2b arms (joint + step decoder)
STEPS1, STEPS2 = 418, 1254
LR, LR_ALPHA, LR_BOARD, LAMBDA = 2e-4, 3e-3, 5e-4, 0.01
GATE = dict(alpha=0.02, div=2.0, window=20)  # PREREG mechanics gate: only the gates-shut check at step 150 and NaN / divergence abort; board cosine and clamp share are logs
HEAD = 2000  # L16 / L24 are scored on the first 2,000 validation rows only
FMT_ROWS = 500  # P1 format check: gold steps as input, on the first 500 validation rows that have steps
MAX_NEW_STEPS = 384  # P1: tokens a model may write for its steps and answer
BR_EVAL_LOOPS = (1, 2, 3, 4, 6, 8)  # arm br (Addendum F): validation is scored at each of these loop counts of the repeated block; "main" is BR_MAIN
BR_MAIN, BR_TRAIN_MAX, BR_RAMP = 4, 6, 0.75  # training loop counts: 1 + Poisson(m - 1), capped at 6, with the mean m ramped 1 -> 4 over the first 75% of steps
# Addendum G, the hops bed (build_hops.py data): every arm is a fresh LoRA (no stage-1 adapter) on the same batch stream.
#   hloop = br's recipe (random loop counts, no injection, final-pass loss); hplain = plain LoRA given hloop's extra layer passes as extra steps.
#   hloopi = hloop + Inject. hloopd = Inject, and each row runs depth + U{0..HOPS_EXTRA} loops (capped at BR_TRAIN_MAX), final-pass loss.
#   hloops = hloopd + one more answer read at a random earlier loop k, trained to name hop k (row["hops_path"]): the recipe of Shapiro 2026
#   (arXiv 2608.11233: re-injection, loops = hops, every loop graded), as a positive control. hplains = plain LoRA given hloops' extra layer passes.
HOPS = ("hplain", "hloop", "hloopi", "hloopd", "hplains", "hloops")
HOPS_LOOPED = ("hloop", "hloopi", "hloopd", "hloops")
HOPS_PLAN = ("hloopd", "hloops", "hplains")  # arms whose loop counts come from hops_plan (per row) rather than loop_schedule (per step)
HOPS_STEPS, HOPS_MAIN, HOPS_EXTRA = 4000, 6, 2
HOPS_EVAL_LOOPS = tuple(range(1, 13))  # validation loop counts of the looped hops arms (r = depth and depth + 1 for every depth 1-10, so the
#   answer-stable rule can stop at depth + 1); dev at HOPS_MAIN only


def loop_schedule(steps, seed, top=BR_MAIN, cap=BR_TRAIN_MAX, ramp=BR_RAMP):
    """Arm br: the block's loop count for every step (Huginn / McLeish-style random depth with a ramped mean), from Random(seed): a fixed list, so
    the compute-matched control can be sized from it before training."""
    rng, out = random.Random(seed), []
    for step in range(steps):
        m = 1 + (top - 1) * min(1.0, step / max(1.0, ramp * steps))
        k, prod, lim = 0, rng.random(), math.exp(-(m - 1))  # Knuth's Poisson(m - 1)
        while prod > lim:
            k += 1
            prod *= rng.random()
        out.append(min(cap, 1 + k))
    return out


def hops_plan(rows, steps, order_seed, bsz, seed, extra=HOPS_EXTRA, cap=BR_TRAIN_MAX):
    """Arms hloopd / hloops: {row index: loop count} for every step's batch (the stream train_lora draws with order_seed), loop count =
    depth + U{0..extra} from Random(seed), capped. A fixed list, so the compute-matched control can be sized before training."""
    rng, stream = random.Random(seed), batches(len(rows), order_seed, bsz)
    return [{i: min(cap, int(rows[i]["depth"]) + rng.randint(0, extra)) for i in next(stream)} for _ in range(steps)]


def plan_ratio(plan, n_layers, size, coda=0):
    """Layer passes per row of a hops_plan over those of one plain pass. coda: layers run again for hloops' extra read (rows with >= 2 loops)."""
    rs = [r for st in plan for r in st.values()]
    return sum(n_layers + size * (r - 1) + coda * (r >= 2) for r in rs) / (len(rs) * n_layers)


def hop_target(row, k):
    """The name hloops is trained to give after loop k: hop k of the chain, or the place once the chain has ended."""
    path = row["hops_path"]
    return path[min(k, len(path)) - 1]


def compute_ratio(loops, n_layers, size):
    """Layer passes per step of a loop schedule over those of one plain pass."""
    return sum(n_layers + size * (r - 1) for r in loops) / (len(loops) * n_layers)


def halting_readout(rows, preds, hits, loops=BR_EVAL_LOOPS):
    """Training-free halting (Addendum F / E): stop at the first loop count whose answer equals the previous one's (else the largest). preds / hits:
    {r: list per row}. Returns accuracy, mean loops, mean loops by depth, and the Spearman correlation of depth (1-6) with the loops used."""
    chosen = []
    for i in range(len(rows)):
        r_use = loops[-1]
        for a, b in zip(loops, loops[1:]):
            if preds[b][i] == preds[a][i]:
                r_use = b
                break
        chosen.append(r_use)
    acc = sum(hits[r][i] == "1" for i, r in enumerate(chosen)) / max(len(rows), 1)
    by = {}
    for d in sorted({r.get("depth") for r in rows}, key=lambda x: (x is None, x)):
        idx = [i for i, r in enumerate(rows) if r.get("depth") == d]
        by[str(d)] = dict(n=len(idx), mean_loops=sum(chosen[i] for i in idx) / len(idx), acc=sum(hits[chosen[i]][i] == "1" for i in idx) / len(idx))
    deep = [(r["depth"], chosen[i]) for i, r in enumerate(rows) if isinstance(r.get("depth"), int) and r["depth"] >= 1]
    return dict(acc=acc, mean_loops=sum(chosen) / max(len(chosen), 1), by_depth=by, spearman_depth_loops=spearman([d for d, _ in deep], [c for _, c in deep]),
                rule="first r in %s whose answer equals the previous r's; else %d" % (list(loops[1:]), loops[-1]))


def by_depth_loops(rows, chosen, hits):
    """{depth: n, mean loops, accuracy} for one chosen loop count per row."""
    by = {}
    for d in sorted({r.get("depth") for r in rows}, key=lambda x: (x is None, x)):
        idx = [i for i, r in enumerate(rows) if r.get("depth") == d]
        by[str(d)] = dict(n=len(idx), mean_loops=sum(chosen[i] for i in idx) / len(idx), acc=sum(hits[chosen[i]][i] == "1" for i in idx) / len(idx))
    return by


def halting_conf(rows, logps, hits, loops):
    """Max-confidence halting (Fan et al. 2024, Addendum G): for each row, the loop count whose greedy answer has the highest summed log-probability
    (ties: the fewest loops). Same fields as halting_readout."""
    chosen = [max(loops, key=lambda r: (logps[r][i], -r)) for i in range(len(rows))]
    deep = [(r["depth"], chosen[i]) for i, r in enumerate(rows) if isinstance(r.get("depth"), int) and r["depth"] >= 1]
    return dict(acc=sum(hits[r][i] == "1" for i, r in enumerate(chosen)) / max(len(rows), 1), mean_loops=sum(chosen) / max(len(chosen), 1),
                by_depth=by_depth_loops(rows, chosen, hits), spearman_depth_loops=spearman([d for d, _ in deep], [c for _, c in deep]),
                rule="the r in %s whose greedy answer has the highest summed log-probability" % (list(loops),))


def oracle_depth(rows, hits):
    """Accuracy when each row gets r = its depth (when that r was scored): the loop count hloopd was trained to use. No pass mark."""
    idx = [i for i, r in enumerate(rows) if isinstance(r.get("depth"), int) and r["depth"] in hits]
    by = {}
    for i in idx:
        g = by.setdefault(str(rows[i]["depth"]), [0, 0])
        g[0], g[1] = g[0] + (hits[rows[i]["depth"]][i] == "1"), g[1] + 1
    return dict(acc=sum(hits[rows[i]["depth"]][i] == "1" for i in idx) / max(len(idx), 1), n=len(idx),
                by_depth={d: dict(n=n, acc=k / n) for d, (k, n) in sorted(by.items(), key=lambda kv: int(kv[0]))})


def spearman(x, y):
    """Spearman rank correlation with average ranks for ties (None if either side is constant)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r, i = [0.0] * len(v), 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(x) < 2:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx, sy = math.sqrt(sum((a - mx) ** 2 for a in rx)), math.sqrt(sum((b - my) ** 2 for b in ry))
    return sxy / (sx * sy) if sx and sy else None


# ---------------------------------------------------------------- data

def batches(n, seed, bsz):
    """Row-index batches exactly as train.py draws them: shuffle with Random(seed), pop from the end, reshuffle when empty."""
    rng, idx = random.Random(seed), []
    while True:
        if not idx:
            idx = list(range(n))
            rng.shuffle(idx)
        yield [idx.pop() for _ in range(min(bsz, len(idx)))]


def synth_rows(split, n=20):
    rng = random.Random(7)
    names, places = ["Saku", "Taho", "Nuto", "Sali"], ["mill", "cave", "hut", "pond", "harbour"]
    rows = []
    for i in range(n):
        v, ctx, loc = i // 4, [], {}
        for nm in names:
            loc[nm] = rng.choice(places)
            ctx.append(f"[world] In the {loc[nm]}, {nm} is present.")
        who = names[i % 4]
        k = i % 3  # 0: no steps (not told), 1: one step, 2: two steps (the line, then the same line again as a second, harmless step)
        rows.append(dict(id=f"{split}-{v}:q{i % 4}", visit_id=f"{split}-{v}", split=split, context="\n".join(ctx),
                         question=f"[question] Where is {who}?", answer=f"the {loc[who]}", qtype="Q1", base_qtype="Q1",
                         bank="q.where_now" if i % 2 else "q.where_before", depth=i % 7, template=f"syn-{i % 3}",
                         steps=[ctx[names.index(who)]] * k, steps_src="chain" if k else "none_told"))
    return rows


def smoke_data(src, out, n=20):
    """n rows of each split (spread over the first 10*n rows so that several stories appear), written to OUT/data; synthetic if src is missing."""
    d = Path(out) / "data"
    d.mkdir(parents=True, exist_ok=True)
    for s in ("train", "dev", "validation"):
        f = Path(src) / f"{s}.jsonl"
        rows = T.read_jsonl(f, limit=10 * n)[::10][:n] if f.exists() else synth_rows(s, n)
        (d / f"{s}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return d


def load_data(args):
    d = Path(args.data)
    train, dev, val = (T.read_jsonl(d / f"{s}.jsonl") for s in ("train", "dev", "validation"))
    if args.limit_eval:
        dev, val = dev[:args.limit_eval], val[:args.limit_eval]
    return train, dev, val


def encode_batch(enc, rows, ids):
    return [enc.train_example(rows[i]) for i in ids]


# ---------------------------------------------------------------- stage 1 / aplus / bplus (LoRA)

def answer_loss_fixed(runner, batch, device):
    """train.answer_loss_sum with the fixed cross-entropy in fp32: same hidden-state positions, same targets."""
    ids, mask = T.right_pad([p + a for p, a in batch])
    ids, mask = ids.to(device), mask.to(device)
    h = runner.hidden(ids, mask, (mask.cumsum(1) - 1).clamp(min=0))
    sb = torch.tensor([b for b, (_, a) in enumerate(batch) for _ in a], device=device)
    st = torch.tensor([len(p) + k - 1 for p, a in batch for k in range(len(a))], device=device)
    tgt = torch.tensor([t for _, a in batch for t in a], device=device)
    logits = runner.logits(h[sb, st]).float()
    return fixed_cross_entropy(logits, tgt, reduction="sum"), len(tgt)


def answer_loss_read(runner, batch, r, k, tgt, device):
    """Arm hloops: answer_loss_fixed with the block run r times, plus (k not None) cross-entropy of the first answer position read after loop k
    against tgt (one token id per row). Returns (summed loss, number of targets)."""
    ids, mask = T.right_pad([p + a for p, a in batch])
    ids, mask = ids.to(device), mask.to(device)
    hs = runner.hidden_multi(ids, mask, (mask.cumsum(1) - 1).clamp(min=0), r, {r} | ({k} if k else set()))
    sb = torch.tensor([b for b, (_, a) in enumerate(batch) for _ in a], device=device)
    st = torch.tensor([len(p) + j - 1 for p, a in batch for j in range(len(a))], device=device)
    t = torch.tensor([x for _, a in batch for x in a], device=device)
    s, n = fixed_cross_entropy(runner.logits(hs[r][sb, st]).float(), t, reduction="sum"), len(t)
    if k:
        rb, pb = torch.arange(len(batch), device=device), torch.tensor([len(p) - 1 for p, _ in batch], device=device)
        s = s + fixed_cross_entropy(runner.logits(hs[k][rb, pb]).float(), torch.tensor(tgt, device=device), reduction="sum")
        n += len(batch)
    return s, n


def lora_model(lm, adapter=None):
    from peft import LoraConfig, PeftModel, get_peft_model
    if adapter:
        return PeftModel.from_pretrained(lm, str(adapter), is_trainable=True)
    return get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=T.LORA_TARGETS, bias="none"))


def train_lora(runner, pm, enc, rows, device, args, steps, warmup, order_seed, tr, written=None, loops=None, extra=(), main=BR_MAIN, plan=None, read=None):
    """written (arms ws / wsham): "gold" or "sham". Every row of a batch is then also added as a written example (steps_of / filler text, " [steps]"
    prompt), after the direct examples; the rows, their order and the optimizer are those of aplus, and the loss is normalised by all target tokens.
    extra: more trainable parameters in the same optimizer and clip (arm hloopi's Inject). main: the loop count the runner is left at after a looped run.
    plan (arms hloopd / hloops): hops_plan's list of {row index: loop count}. The batch's rows are then split into micro-batches of one loop count
    each (same rows; loops is ignored). read (arm hloops): a Random; every micro-batch run r >= 2 times also reads its answer after a loop
    k = read.randint(1, r - 1), trained to name hop_target(row, k); the step's loss is normalised by all answer tokens plus those reads."""
    params = [p for p in pm.parameters() if p.requires_grad] + list(extra)
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0, betas=(0.9, 0.999))
    stream = batches(len(rows), order_seed, args.bsz)
    pm.train()
    runner.lm.train()
    t0, window = time.time(), []
    for step in range(steps):
        ids = next(stream)
        batch = encode_batch(enc, rows, ids)
        if loops is not None:  # arm br: this step's loop count of the repeated block
            runner.loops = loops[step]
        if written:
            batch += [S.written_example(enc, rows[i], sham=written == "sham") for i in ids]
            cw = tr.setdefault("written_cut", dict(rows=0, cut_for_target=0))  # rows drawn, and of them those whose prompt lost context to make room for the written target
            cw["rows"] += len(ids)
            cw["cut_for_target"] += sum(S.cut_for_target(enc, rows[i], written == "sham") for i in ids)
        if plan is not None:
            groups = {}
            for i, ex in zip(ids, batch):
                groups.setdefault(plan[step][i], []).append((i, ex))
            chunks = [(r, g[k:k + args.micro_bsz]) for r, g in sorted(groups.items()) for k in range(0, len(g), args.micro_bsz)]
            hist = tr.setdefault("loops_hist_rows", {})
            for r, g in groups.items():
                hist[str(r)] = hist.get(str(r), 0) + len(g)
        else:
            chunks = [(None, [(None, ex) for ex in batch[k:k + args.micro_bsz]]) for k in range(0, len(batch), args.micro_bsz)]  # written rows included
        reads = [read.randint(1, r - 1) if read is not None and r >= 2 else None for r, _ in chunks]
        n_ans = sum(len(a) for _, a in batch) + sum(len(ch) for (_, ch), k in zip(chunks, reads) if k)
        for g in opt.param_groups:
            g["lr"] = T.cosine_lr(step, steps, LR, warmup)
        total = 0.0
        for (r, ch), k in zip(chunks, reads):
            if r is not None:
                runner.loops = r
            exs = [ex for _, ex in ch]
            if read is not None:
                s, _ = answer_loss_read(runner, exs, r, k, [enc.ids(" " + hop_target(rows[i], k))[0] for i, _ in ch] if k else None, device)
            else:
                s, _ = answer_loss_fixed(runner, exs, device)
            (s / n_ans).backward()
            total += s.item()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        tr["step_losses"].append(total / n_ans)
        window.append(total / n_ans)
        if (step + 1) % 10 == 0 or step + 1 == steps:
            tr["loss_curve"].append([step + 1, sum(window) / len(window)])
            window = []
            if (step + 1) % 50 == 0 or step + 1 == steps:
                print(f"[train] step {step + 1}/{steps} loss {tr['loss_curve'][-1][1]:.4f} {time.time() - t0:.0f}s", flush=True)
    tr["seconds"] = time.time() - t0
    if loops is not None:
        tr["loops_hist"] = {str(r): loops.count(r) for r in sorted(set(loops))}
    if loops is not None or plan is not None:
        runner.loops = main
    if written:
        print(f"[written] prompts cut to make room for the written target: {tr['written_cut']['cut_for_target']} of {tr['written_cut']['rows']} drawn rows", flush=True)
    pm.eval()
    runner.lm.eval()


def entry(hits):
    s = "".join(hits)
    return {"acc": s.count("1") / len(s) if s else 0.0, "n": len(s), "hits": s, "row_offset": 0}


@torch.no_grad()
def eval_greedy(runner, enc, rows, device, args, order=None, reverse=False, name="", board_path=False, keep_preds=False, keep_logp=False):
    """Greedy exact-match hits for arms a/b/aplus/bplus. Batches are built in descending length order, or ascending if reverse
    (different batch composition: used for the eval-noise rerun). Returns the entry with hits in file order.
    board_path (arms a, aplus): decode with board.prefill of prompt[:-1] + board.decode with no board read, the code eval_board runs on the same batches (same two segments), so S(8) and
    A_ref are measured by identical code; otherwise (b, bplus: they need the looped runner) T.greedy. --no-cache keeps T.greedy for the check."""
    board_path = board_path and not args.no_cache
    order = order or runner.order
    prompts = [enc.prompt(r)[0] for r in rows]
    hit, t0, nb, done = ["0"] * len(rows), time.time(), 0, 0
    preds, logps = [""] * len(rows), [0.0] * len(rows)
    h = min(HEAD, len(rows))  # board path: two separately sorted segments (rows < HEAD, rest) and no chunk across the boundary, exactly eval_board's batches
    segs = (range(h), range(h, len(rows))) if board_path and not reverse else (range(len(rows)),)
    for seg in segs:
        idx = sorted(seg, key=lambda i: len(prompts[i]), reverse=not reverse)
        k = 0
        while k < len(idx):
            if reverse:  # ascending: the longest row of a batch is its last one
                j = k + 1
                while j < len(idx) and j - k < args.eval_bsz and (j - k + 1) * len(prompts[idx[j]]) <= args.eval_tokens:
                    j += 1
                chunk = idx[k:j]
            else:
                chunk = idx[k:k + max(1, min(args.eval_bsz, args.eval_tokens // len(prompts[idx[k]])))]
            ps = [prompts[i] for i in chunk]
            if board_path:
                C, mask, p = B.prefill(runner, ps)
                gen = B.decode(runner, None, C, mask, p, B.last_ids(ps, device), None, eos=enc.eos)
            else:
                lp = [] if keep_logp else None
                gen = T.greedy(runner, ps, device, enc.eos, cache=not args.no_cache, order=order, logp=lp)
                if keep_logp:
                    for i, v in zip(chunk, lp):
                        logps[i] = round(v, 5)
            for i, g in zip(chunk, gen):
                preds[i] = T.normalise(enc.tok.decode(g, skip_special_tokens=True))
                hit[i] = "1" if preds[i] == T.normalise(rows[i]["answer"]) else "0"
            k += len(chunk)
            done += len(chunk)
            nb += 1
            if nb % 20 == 0:
                print(f"[eval {name}] {done}/{len(rows)} {time.time() - t0:.0f}s", flush=True)
    return entry(hit) | (dict(preds=preds) if keep_preds else {}) | (dict(logp=logps) if keep_logp and not board_path else {})


@torch.no_grad()
def eval_written(runner, enc, rows, device, args, sham=False, gold=False, name=""):
    """Arms ws / wsham, greedy on the steps prompt (" [steps]"). gold=False (T): the model writes its steps and then "The answer is: X"; the text after the last
    "The answer is:" is scored (a missing marker is a miss). gold=True (format check, no pass mark): the gold steps (filler for wsham) and "The answer is:" are
    the input and the next tokens are scored. Same batches as eval_greedy's (descending prompt length, same decode as the board-free path).
    The entry adds mean_gen_tokens (generated tokens per row, EOS not counted) and marker_rate (rows that wrote "The answer is:"; T only)."""
    prompts = [S.gold_prompt(enc, r, sham) if gold else S.written_example(enc, r, sham)[0] for r in rows]  # T: the prompt exactly as in training (room reserved for the gold target length)
    max_new = T.MAX_NEW if gold else args.max_new_steps
    hit, ntok, marked, t0, nb, capped = ["0"] * len(rows), [0] * len(rows), 0, time.time(), 0, 0
    idx, k = sorted(range(len(rows)), key=lambda i: len(prompts[i]), reverse=True), 0
    while k < len(idx):
        chunk = idx[k:k + max(1, min(args.eval_bsz, args.eval_tokens // (len(prompts[idx[k]]) + max_new)))]
        ps = [prompts[i] for i in chunk]
        C, mask, p = B.prefill(runner, ps)
        gen = B.decode(runner, None, C, mask, p, B.last_ids(ps, device), None, max_new=max_new, eos=enc.eos)
        for i, g in zip(chunk, gen):
            text = enc.tok.decode(g, skip_special_tokens=True)
            ntok[i] = len(g)
            capped += len(g) >= max_new
            ans = text if gold else S.parse_answer(text)
            marked += ans is not None
            if ans is not None:  # score what eval_greedy would see: at most MAX_NEW answer tokens (long plan answers are cut there too)
                ans = enc.tok.decode(enc.ids(ans)[:T.MAX_NEW], skip_special_tokens=True)
            if ans is not None and T.normalise(ans) == T.normalise(rows[i]["answer"]):
                hit[i] = "1"
        k += len(chunk)
        nb += 1
        if nb % 20 == 0:
            print(f"[eval {name}] {k}/{len(rows)} {time.time() - t0:.0f}s", flush=True)
    e = entry(hit)
    e.update(mean_gen_tokens=sum(ntok) / max(len(rows), 1), marker_rate=None if gold else marked / max(len(rows), 1), hit_max_new=capped)
    if not gold:
        print(f"[eval {name}] {capped} of {len(rows)} generations hit the {max_new}-token limit", flush=True)
    return e


# ---------------------------------------------------------------- board arms: training

def micro_inputs(runner, mb, device):
    prompts = [p for p, _ in mb]
    C, mask, p = B.prefill(runner, prompts)
    return C, mask, p, B.last_ids(prompts, device), [a for _, a in mb]


def board_groups(board):
    ref = [p for n, p in board.named_parameters() if n not in ("alpha", "e0_hat", "eta")]
    return [dict(name="alpha", params=[board.alpha], lr=LR_ALPHA, base=LR_ALPHA),
            dict(name="e0eta", params=[board.e0_hat, board.eta], lr=LR_BOARD, base=LR_BOARD),
            dict(name="refiner", params=ref, lr=LR_BOARD, base=LR_BOARD)]


def probe_summary(sts, board, step, loss):
    """Gate-log entry from think(stats=True) runs on the micro-batches of one optimizer step (boards concatenated: 'across' = same slot, different questions).
    cos_*: final boards; cos_update_*: their updates e_L - e_0 (all boards start from the same e_0, so the update is what can differ between questions)."""
    e = torch.cat([s["e"][-1] for s in sts])
    within, across = B._cos(e)
    uw, ua = B._cos(torch.cat([s["e"][-1] - s["e"][0] for s in sts]))
    mean = lambda f: float(torch.stack([f(s) for s in sts]).mean())
    gate = board.gate().detach().abs()
    return dict(step=step, loss=loss, alpha_mean=float(gate.mean()), alpha_abs=[[round(float(x), 5) for x in r] for r in gate],
                step_rms=[round(float(x), 5) for x in torch.stack([torch.stack(s["step"]) for s in sts]).mean(0)],
                cos_within=float(within), cos_across=float(across), cos_update_within=float(uw), cos_update_across=float(ua),
                clamp=mean(lambda s: s["clamp"][-1]), clamp5=mean(lambda s: s["clamp5"][-1]))


def gate_reason(g):
    """Step-150 mechanics gate (PREREG): abort only if the gates never opened. Board cosine and clamp share (g['cos_across'], g['clamp5'], ...) are logged, never abort."""
    if g["alpha_mean"] < GATE["alpha"]:
        return f"mean |tanh alpha| {g['alpha_mean']:.4f} < {GATE['alpha']}"
    return None


def diverged(losses):
    """Loss guard: the last 20-step mean exceeds 2x the first 20-step mean (checked at every step after step 20)."""
    w = GATE["window"]
    return len(losses) > w and sum(losses[-w:]) / w > GATE["div"] * sum(losses[:w]) / w


def train_board(runner, board, enc, rows, quick_rows, device, args, steps, tr):
    """Trains the ThinkBoard only. Returns the abort reason or None."""
    opt = torch.optim.AdamW(board_groups(board), weight_decay=0.0, betas=(0.9, 0.999))
    stream = batches(len(rows), args.seed + 1000, args.bsz)  # same stage-2 order for every arm of a seed
    lrng = random.Random(args.seed + 2000)
    warm = 2 if args.smoke else 60
    probe_L = 1 if args.arm in ("t1", "tw") else 8
    enforce = args.gate_enforce or not args.smoke
    t0, window, losses, gn = time.time(), [], tr["step_losses"], {}
    for step in range(steps):
        n = step + 1
        batch = encode_batch(enc, rows, next(stream))
        n_norm = sum(len(a) for _, a in batch)
        L_max = 1 if args.arm in ("t1", "tw") else (8 if lrng.random() < 0.8 else 12)
        for g in opt.param_groups:
            g["lr"] = T.cosine_lr(step, steps, g["base"], warm)
        probe = n % 10 == 0 or n in (args.gate_step, steps)
        total, sts = 0.0, []
        for k in range(0, len(batch), args.micro_bsz):
            mb = batch[k:k + args.micro_bsz]
            C, mask, p, lt, ans = micro_inputs(runner, mb, device)
            loss, _ = B.train_loss(board, runner, C, mask, p, lt, ans, L_max, n_norm=n_norm, row_frac=len(mb) / len(batch), lam=LAMBDA,
                                   ckpt=not args.no_lap_ckpt)
            loss.backward()
            total += loss.item()
            if probe:
                with torch.no_grad():
                    sts.append(B.think(board, runner, C, mask, p, probe_L, keep=(), stats=True)[1])
        if not math.isfinite(total):
            return f"NaN loss at step {n}"
        gn = {g["name"]: float(torch.nn.utils.clip_grad_norm_(g["params"], 1.0)) for g in opt.param_groups}  # clip 1.0 per group
        if not all(math.isfinite(v) for v in gn.values()):
            return f"non-finite gradient at step {n}"
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(total)
        window.append(total)
        if n % 10 == 0 or n == steps:
            tr["loss_curve"].append([n, sum(window) / len(window)])
            window = []
        if probe:
            g = probe_summary(sts, board, n, tr["loss_curve"][-1][1] if tr["loss_curve"] else total)
            g["grad_norm"], g["L_max"] = gn, L_max
            tr["gate_log"].append(g)
            print(f"[gate] step {n} loss {g['loss']:.4f} |tanh a| {g['alpha_mean']:.4f} cos_across {g['cos_across']:.3f} cos_within {g['cos_within']:.3f} "
                  f"cos_upd_across {g['cos_update_across']:.3f} cos_upd_within {g['cos_update_within']:.3f} "
                  f"clamp {g['clamp']:.2f} clamp5 {g['clamp5']:.2f} step_rms {g['step_rms'][-1]:.3f} gn {gn['refiner']:.3f}", flush=True)
            if n == args.gate_step:
                reason = gate_reason(g)
                tr["gate_check"] = dict(step=n, enforced=enforce, reason=reason)
                if reason and enforce:
                    return f"mechanics gate at step {n}: {reason}"
        if n > GATE["window"] and diverged(losses):
            msg = f"loss diverged at step {n}: last-20 mean > {GATE['div']}x first-20 mean"
            if enforce:
                return msg
            print(f"[warn] {msg} (smoke: not enforced)", flush=True)
        if n % args.log_every == 0:
            tr["dev_log"].append(quick_eval(runner, board, enc, quick_rows, device, args, n, gn))
            print(f"[dev] step {n} {tr['dev_log'][-1]['acc']} ce {tr['dev_log'][-1]['ce']}", flush=True)
        if n % 50 == 0 or n == steps:
            print(f"[train] step {n}/{steps} loss {tr['loss_curve'][-1][1]:.4f} {time.time() - t0:.0f}s", flush=True)
    return None


def p_blind(step, steps, args):
    """Arm tf: chance that a micro-batch's board loss is blind at (0-based) step: blind_p, falling linearly to 0 at blind_until * steps, then 0."""
    return args.blind_p * max(0.0, 1 - step / (args.blind_until * steps))


def sd_micro_loss(sd, pm, runner, info, dts, n_lap):
    """Step loss of one micro-batch for arms tsd / tsd1: mean over the four decoder passes of (summed CE over the micro-batch's lap-k targets / the
    optimizer-step batch's lap-k target tokens). info["e"] = the boards of the same think() run as the answer loss; dts = decoder_targets of its rows."""
    notes = S.lap_notes(info["e"], len(info["e"]) - 1)
    ce = [sd.step_ce(pm, runner, notes[k], [(d[k][0], d[k][1]) for d in dts])[0] / n_lap[k] for k in range(S.SD_LAPS)]
    return torch.stack(ce).mean()


def train_joint(runner, pm, board, enc, rows, quick_rows, device, args, steps, tr, sd=None):
    """Arm tj: LoRA (a's adapter, trainable) and ThinkBoard train together at fixed L_max = args.lmax. Per micro-batch the loss is the aplus loss
    (full teacher-forced pass through the LoRA model, no board read) + the board loss (prefill under the current LoRA, no grad; slot and answer passes
    carry gradient to the board AND, through the checkpointed closures, to the LoRA). The two are backpropagated one after the other (same summed gradient).
    Arm tf: per micro-batch, with chance p_blind(step) (own Random(seed + 3000)) the board loss uses blind answer passes (board.answer_logits); the aplus loss never does.
    Arms tsd / tsd1 (sd = the StepDecoder): the board loss is joined by 1.0 x the step loss (sd_micro_loss), backpropagated together with it through the same
    boards; the decoder's own LoRA ("dec") and Linear train in their own optimizer groups.
    Returns the abort reason or None."""
    lora = [p for n, p in pm.named_parameters() if p.requires_grad and ".dec." not in n]
    closed = args.arm == "tc"  # control: no thinking block. lmax 0 (laps 0..0), alpha frozen at 0, no board parameter trained, only the "lora" group
    if closed:
        for q in board.parameters():
            q.requires_grad_(False)
        assert float(board.alpha.abs().max()) == 0.0, "tc needs closed gates"
    groups = ([] if closed else board_groups(board)) + [dict(name="lora", params=lora, lr=LR, base=LR)]
    if sd is not None:
        groups += [dict(name="declora", params=[p for n, p in pm.named_parameters() if ".dec." in n], lr=LR, base=LR),
                   dict(name="decproj", params=list(sd.parameters()), lr=LR_BOARD, base=LR_BOARD)]
    opt = torch.optim.AdamW(groups, weight_decay=0.0, betas=(0.9, 0.999))
    stream = batches(len(rows), args.seed + 1000, args.bsz)  # same stage-2 order as aplus / t
    warm = 2 if args.smoke else 60
    L_max = probe_L = 0 if closed else args.lmax
    brng, forced = random.Random(args.seed + 3000), args.arm == "tf"
    tr["blind_steps"] = []  # tf: 0/1 per micro-batch, in order
    tr["sd_losses"] = []  # tsd / tsd1: the step loss of each optimizer step
    tr["sd_data"] = dict(rows=0, file_order=0, over_laps=0)  # tsd / tsd1: rows drawn, of them with steps_src file_order, and with more steps than decoder laps (steps beyond lap 4 are never targets)
    enforce = (args.gate_enforce or not args.smoke) and sd is None  # P2b (tsd / tsd1) must survive a closed gate: the check is recorded, never an abort
    t0, window, losses, gn = time.time(), [], tr["step_losses"], {}
    pm.train()
    runner.lm.train()
    for step in range(steps):
        n = step + 1
        ids = next(stream)
        batch = encode_batch(enc, rows, ids)
        n_norm = sum(len(a) for _, a in batch)
        if sd is not None:
            dts = [S.decoder_targets(enc, rows[i]) for i in ids]
            tr["sd_data"]["rows"] += len(ids)
            tr["sd_data"]["file_order"] += sum(rows[i].get("steps_src") == "file_order" for i in ids)
            tr["sd_data"]["over_laps"] += sum(len(S.steps_of(rows[i])) > S.SD_LAPS for i in ids)
            n_lap = [sum(len(d[k][1]) for d in dts) for k in range(S.SD_LAPS)]
        for g in opt.param_groups:
            g["lr"] = T.cosine_lr(step, steps, g["base"], warm)
        probe = n % 10 == 0 or n in (args.gate_step, steps)
        total, sts, nb, sd_total = 0.0, [], 0, 0.0
        for k in range(0, len(batch), args.micro_bsz):
            mb = batch[k:k + args.micro_bsz]
            blind = forced and brng.random() < p_blind(step, steps, args)
            tr["blind_steps"].append(int(blind))
            nb += blind
            la, _ = answer_loss_fixed(runner, mb, device)  # (a) aplus loss
            (la / n_norm).backward()
            C, mask, p, lt, ans = micro_inputs(runner, mb, device)
            lb, info = B.train_loss(board, runner, C, mask, p, lt, ans, L_max, n_norm=n_norm, row_frac=len(mb) / len(batch), lam=LAMBDA,
                                    ckpt=not args.no_lap_ckpt, blind=blind)  # (b) board loss
            if sd is not None:  # (c) step loss on the same boards
                ls = sd_micro_loss(sd, pm, runner, info, dts[k:k + args.micro_bsz], n_lap)
                (lb + ls).backward()
                sd_total += ls.item()
            else:
                lb.backward()
            total += la.item() / n_norm + lb.item()
            if probe and not closed:
                with torch.no_grad():
                    sts.append(B.think(board, runner, C, mask, p, probe_L, keep=(), stats=True)[1])
        total += sd_total  # tsd / tsd1: the step loss counts in the loss curve and in the divergence guard
        if not math.isfinite(total):
            return f"NaN loss at step {n}"
        gn = {g["name"]: float(torch.nn.utils.clip_grad_norm_(g["params"], 1.0)) for g in opt.param_groups}  # clip 1.0 per group
        if not all(math.isfinite(v) for v in gn.values()):
            return f"non-finite gradient at step {n}"
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(total)
        window.append(total)
        if sd is not None:
            tr["sd_losses"].append(sd_total)
        if n % 10 == 0 or n == steps:
            tr["loss_curve"].append([n, sum(window) / len(window)])
            window = []
        if probe and closed:  # no board to probe: loss, the (zero) gate and the LoRA grad norm only
            tr["gate_log"].append(dict(step=n, loss=tr["loss_curve"][-1][1] if tr["loss_curve"] else total, alpha_mean=float(board.gate().detach().abs().mean()),
                                       grad_norm=gn, L_max=L_max))
            print(f"[gate] step {n} loss {tr['gate_log'][-1]['loss']:.4f} |tanh a| {tr['gate_log'][-1]['alpha_mean']:.4f} gn_lora {gn['lora']:.3f}", flush=True)
            if n == args.gate_step:
                tr["gate_check"] = dict(step=n, enforced=False, reason="skipped (tc)")  # the gates stay shut by design
        elif probe:
            g = probe_summary(sts, board, n, tr["loss_curve"][-1][1] if tr["loss_curve"] else total)
            g["grad_norm"], g["L_max"] = gn, L_max
            tr["gate_log"].append(g)
            print(f"[gate] step {n} loss {g['loss']:.4f} |tanh a| {g['alpha_mean']:.4f} cos_across {g['cos_across']:.3f} cos_within {g['cos_within']:.3f} "
                  f"cos_upd_across {g['cos_update_across']:.3f} cos_upd_within {g['cos_update_within']:.3f} "
                  f"clamp {g['clamp']:.2f} clamp5 {g['clamp5']:.2f} step_rms {g['step_rms'][-1]:.3f} gn {gn['refiner']:.3f} gn_lora {gn['lora']:.3f}"
                  + (f" blind {nb}/{-(-len(batch) // args.micro_bsz)} p_blind {p_blind(step, steps, args):.3f}" if forced else "")
                  + (f" sd {sd_total:.3f}" if sd is not None else ""), flush=True)
            if n == args.gate_step:
                reason = gate_reason(g)
                tr["gate_check"] = dict(step=n, enforced=enforce, reason=reason, gate_closed=reason is not None)
                if reason and enforce:
                    return f"mechanics gate at step {n}: {reason}"
        if n > GATE["window"] and diverged(losses):
            msg = f"loss diverged at step {n}: last-20 mean > {GATE['div']}x first-20 mean"
            if enforce:
                return msg
            print(f"[warn] {msg} (smoke: not enforced)", flush=True)
        if n % args.log_every == 0:
            pm.eval()
            runner.lm.eval()
            tr["dev_log"].append(quick_eval(runner, board, enc, quick_rows, device, args, n, gn, laps=(0, 0) if closed else (1, L_max)))
            pm.train()
            runner.lm.train()
            print(f"[dev] step {n} {tr['dev_log'][-1]['acc']} ce {tr['dev_log'][-1]['ce']}", flush=True)
        if n % 50 == 0 or n == steps:
            print(f"[train] step {n}/{steps} loss {tr['loss_curve'][-1][1]:.4f} {time.time() - t0:.0f}s", flush=True)
    pm.eval()
    runner.lm.eval()
    return None


# ---------------------------------------------------------------- board arms: evaluation

def tags_for(arm, split, lmax=4):
    P = lambda L, n=None: ("plain", L, n)
    if arm == "tc":  # control, thinking block off: lap 0 with shut gates (= no read, ref0); dev L0 only
        return {"L0": P(0)} if split == "dev" else {"L0": P(0), "ref0": ("none", 0, None)}
    if arm in ("tsd", "tsd1"):  # (literal names: test_from_label compiles this function alone) tsd / tsd1 (lmax 4 / 1): as tj, plus the random-notes and zero-notes lesions
        L = lmax
        if split == "dev":
            return {f"L{L}": P(L)}
        return {"L0": P(0), "L1": P(1), f"L{L}": P(L), f"swap{L}": ("swap", L, None), f"random{L}": ("random", L, None), f"zero{L}": ("zero", L, None),
                f"gatesoff{L}": ("off", L, None), "ref0": ("none", L, None)}
    if arm in ("tj", "tf"):  # L = lmax: validation L0, L1, L, swap lesion, gates off (= the jointly trained LoRA alone), no-read reference; dev L only
        L = lmax  # tf adds blind{L}: the answer sees no prompt, only the notes, on the first HEAD validation rows
        if split == "dev":
            return {f"L{L}": P(L)}
        return {"L0": P(0), "L1": P(1), f"L{L}": P(L), f"swap{L}": ("swap", L, None), f"gatesoff{L}": ("off", L, None), "ref0": ("none", L, None),
                **({f"blind{L}": ("blind", L, HEAD)} if arm == "tf" else {})}
    if arm == "t":
        if split == "dev":
            return {f"L{L}": P(L) for L in (0, 1, 8)}
        return {**{f"L{L}": P(L) for L in (0, 1, 2, 4, 8, 12)}, "L16": P(16, HEAD), "L24": P(24, HEAD), "swap8": ("swap", 8, None),
                "mean8": ("mean", 8, None), "rep1_8": ("rep", 8, None), "gatesoff8": ("off", 8, None),
                "ref0": ("none", 8, None)}
    if arm == "t1":
        return {f"L{L}": P(L) for L in ((0, 1, 8) if split == "validation" else (1,))}
    return {"L1": P(1)} if split == "validation" else {}


def random_notes_kv(runner, e, C, mask, p, seed):
    """The random lesion: notes drawn from a Gaussian and rescaled to the real notes' per-slot norm, run through the slot pass on the row's own prompt cache
    (so only the content of the notes differs from the real board's read). e [B,K,d] = the real final notes."""
    r = torch.randn(e.shape, generator=torch.Generator().manual_seed(seed)).to(e.device, e.dtype)
    r = r * (e.pow(2).mean(-1, keepdim=True).sqrt() / r.pow(2).mean(-1, keepdim=True).sqrt())
    return B.slot_pass(runner, r, C, mask, p)[1]


@torch.no_grad()
def swap_store(runner, board, rows, prompts, Ls, args):
    """Pre-pass for the swap lesion: the final slot K/V of every row at each lap in Ls, on cpu ({L: [per row: [(k, v) per full-attention layer]]}). Row i then reads
    the board of B.swap_partners(rows)[i] (same depth, another story): the partner is anywhere in the set, so every row's board must exist before any is read."""
    store = {L: [None] * len(rows) for L in Ls}
    order, k = sorted(range(len(rows)), key=lambda i: -len(prompts[i])), 0
    while k < len(order):
        chunk = order[k:k + max(1, min(args.eval_bsz, args.eval_tokens // len(prompts[order[k]])))]
        k += len(chunk)
        C, mask, p = B.prefill(runner, [prompts[i] for i in chunk])
        kv, _ = B.think(board, runner, C, mask, p, max(Ls), keep=set(Ls), stats=False)
        for L in Ls:
            for b, i in enumerate(chunk):
                store[L][i] = [(a[b].cpu(), v[b].cpu()) for a, v in kv[L]]
    return store


@torch.no_grad()
def eval_board(runner, board, enc, rows, tags, args, device, name="eval"):
    """tags: {tag: (kind, L, nmax)}, kind in plain / swap / mean / rep / off / none / blind (plain, decoded with no prompt in the answer cache) / zero / random (tsd arms). Each batch is prefilled once, think() runs to the largest L and
    records the slot K/V at every L needed, and every tag is decoded on its own cache clone. Returns {tag: entry} with hits in file order."""
    if not tags:
        return {}
    n = len(rows)
    prompts = [enc.prompt(r)[0] for r in rows]
    visits = [r.get("visit_id") for r in rows]
    hits = {t: ["0"] * (n if lim is None else min(lim, n)) for t, (_, _, lim) in tags.items()}
    zero, t0, nb = torch.zeros_like(board.alpha), time.time(), 0
    swaps = {t: v[1] for t, v in tags.items() if v[0] == "swap"}
    if swaps:
        partner, same_story = B.swap_partners(rows)
        store = swap_store(runner, board, rows, prompts, sorted(set(swaps.values())), args)
    head = min(HEAD, n)
    for ids, active in ((range(head), list(tags)), (range(head, n), [t for t in tags if tags[t][2] is None])):
        if len(ids) == 0 or not active:
            continue
        order = sorted(ids, key=lambda i: -len(prompts[i]))
        keep = {tags[t][1] for t in active if tags[t][0] != "rep"}
        k = 0
        while k < len(order):
            chunk = order[k:k + max(1, min(args.eval_bsz, args.eval_tokens // len(prompts[order[k]])))]
            k += len(chunk)
            ps, vs = [prompts[i] for i in chunk], [visits[i] for i in chunk]
            C, mask, p = B.prefill(runner, ps)
            lt = B.last_ids(ps, device)
            kv, st = B.think(board, runner, C, mask, p, max(keep, default=0), keep=keep, stats=False)
            rep = {}
            for t in active:
                kind, L, lim = tags[t]
                gates = None
                blind = kind == "blind"
                if kind in ("plain", "blind"):
                    skv = kv[L]
                elif kind == "off":
                    skv, gates = kv[L], zero
                elif kind == "none":  # reference: no board read at all, same batches and path as every other tag; gatesoff8 must equal it row for row
                    skv = None
                elif kind == "mean":
                    skv = B.mean_kv(kv[L])
                elif kind == "zero":  # all-zero notes on an empty cache (B.zero_notes_kv): the notes' read without the notes or the story
                    skv = B.zero_notes_kv(runner, board, p)
                elif kind == "random":
                    skv = random_notes_kv(runner, st["e"][L], C, mask, p, args.seed + 4000 + nb)
                elif kind == "swap":
                    src = [partner[i] if partner[i] is not None else i for i in chunk]  # no same-depth partner: the row's own board (counted in swap_no_partner_rows)
                    skv = [(torch.stack([store[L][j][l][0] for j in src]).to(device), torch.stack([store[L][j][l][1] for j in src]).to(device)) for l in range(len(kv[L]))]
                else:
                    if L not in rep:
                        rep[L] = B.think(board, runner, C, mask, p, L, keep={L}, repeat_delta1=True, stats=False)[0][L]
                    skv = rep[L]
                gen = B.decode(runner, board, C, mask, p, lt, skv, eos=enc.eos, gates=gates, blind=blind)
                for i, g in zip(chunk, gen):
                    if lim is None or i < lim:
                        hits[t][i] = "1" if T.normalise(enc.tok.decode(g, skip_special_tokens=True)) == T.normalise(rows[i]["answer"]) else "0"
            nb += 1
            if nb % 20 == 0:
                print(f"[eval {name}] {k}/{len(order)} batches {nb} {time.time() - t0:.0f}s", flush=True)
    out = {t: entry(h) for t, h in hits.items()}
    for t in swaps:
        out[t]["swap_same_story_rows"] = same_story  # partners from the same story (no same-depth row of another story exists)
        out[t]["swap_no_partner_rows"] = sum(x is None for x in partner)  # alone at their depth: they read their own board
    return out


def build_decoder(pm, runner, board, device, seed):
    """Arms tsd / tsd1: add the decoder's own LoRA adapter "dec" (r=16, as the main one; trainable, inactive until a decoder pass) to pm and build the Linear."""
    from peft import LoraConfig
    torch.manual_seed(seed + 5000)
    pm.add_adapter("dec", LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=T.LORA_TARGETS, bias="none"))
    for n, p in pm.named_parameters():
        if ".dec." in n:
            p.requires_grad_(True)  # add_adapter leaves a new adapter frozen
    return S.StepDecoder(board.e0_hat.shape[1], runner.lm.config.hidden_size).to(device)


@torch.no_grad()
def eval_decoder(runner, pm, board, sd, enc, rows, args, device, lmax, n=HEAD):
    """Step-token accuracy (teacher-forced argmax, percent of step tokens) of the step decoder when it reads the true notes of each lap and when it reads the
    notes of another story's row (the nearest following row of a different visit with the same number of step laps; any other-visit row if none).
    Rows: the first n validation rows that have at least one step. Only laps that have a step target count. The P2b pass mark is gap = true - swapped >= 10."""
    rows = [r for r in rows if S.steps_of(r)][:n]
    if not rows:
        return None
    N, prompts = len(rows), [enc.prompt(r)[0] for r in rows]
    order, notes, k = sorted(range(N), key=lambda i: -len(prompts[i])), None, 0
    while k < N:  # the notes of every lap, on cpu
        chunk = order[k:k + max(1, min(args.eval_bsz, args.eval_tokens // len(prompts[order[k]])))]
        k += len(chunk)
        ps = [prompts[i] for i in chunk]
        C, mask, p = B.prefill(runner, ps)
        ln = S.lap_notes(B.think(board, runner, C, mask, p, lmax, keep=(), stats=False)[1]["e"], lmax)
        notes = notes or [torch.zeros(N, *x.shape[1:]) for x in ln]
        for j, x in enumerate(ln):
            notes[j][chunk] = x.float().cpu()
    visits, key = [r.get("visit_id") for r in rows], [min(len(S.steps_of(r)), S.SD_LAPS) for r in rows]
    partner, other_depth, same = [], 0, 0
    for i in range(N):
        cand = [(i + d) % N for d in range(1, N)]
        j = next((j for j in cand if visits[j] != visits[i] and key[j] == key[i]), None)
        if j is None:
            j = next((j for j in cand if visits[j] != visits[i]), None)
            other_depth += j is not None
        if j is None:
            j, same = (i + 1) % N, same + 1
        partner.append(j)
    dts = [S.decoder_targets(enc, r) for r in rows]
    hit = {"true": [0] * S.SD_LAPS, "swap": [0] * S.SD_LAPS}
    cnt = [0] * S.SD_LAPS
    for c in range(0, N, args.eval_bsz):
        ids = list(range(c, min(c + args.eval_bsz, N)))
        for lap in range(S.SD_LAPS):
            use = [i for i in ids if dts[i][lap][2]]
            if not use:
                continue
            seqs = [(dts[i][lap][0], dts[i][lap][1]) for i in use]
            for name, src in (("true", use), ("swap", [partner[i] for i in use])):
                h, m = sd.token_hits(pm, runner, notes[lap][src].to(device), seqs)
                hit[name][lap] += h
            cnt[lap] += m
    tot = max(sum(cnt), 1)
    acc = {nm: 100 * sum(h) / tot for nm, h in hit.items()}
    return dict(true=acc["true"], swap=acc["swap"], gap=acc["true"] - acc["swap"], tokens=sum(cnt), rows=N,
                by_lap={str(lap + 1): dict(true=100 * hit["true"][lap] / max(cnt[lap], 1), swap=100 * hit["swap"][lap] / max(cnt[lap], 1), tokens=cnt[lap])
                        for lap in range(S.SD_LAPS)},
                partner_other_depth_rows=other_depth, partner_same_story_rows=same)


@torch.no_grad()
def board_ce(runner, board, enc, rows, Ls, device, bsz):
    """Mean fixed answer cross-entropy per answer token at each lap count in Ls (teacher-forced, rows as in training)."""
    sums, cnt = {L: 0.0 for L in Ls}, 0
    for k in range(0, len(rows), bsz):
        C, mask, p, lt, ans = micro_inputs(runner, [enc.train_example(r) for r in rows[k:k + bsz]], device)
        kv, _ = B.think(board, runner, C, mask, p, max(Ls), keep=Ls, stats=False)
        for L in Ls:
            s, c = B.answer_ce(runner, board, C, mask, p, lt, ans, kv[L])
            sums[L] += s.item()
        cnt += c
    return {f"L{L}": sums[L] / max(cnt, 1) for L in Ls}


def quick_eval(runner, board, enc, rows, device, args, step, gn, laps=(1, 8)):
    """The every-250-steps log on the first 256 dev rows: answer CE and greedy accuracy at the two laps (1 and 8; tj: 1 and lmax), swap lesion at the second, |tanh alpha| per layer, refiner grad norm."""
    lo, hi = laps
    tags = {f"L{lo}": ("plain", lo, None)} if lo == hi else {f"L{lo}": ("plain", lo, None), f"L{hi}": ("plain", hi, None), f"swap{hi}": ("swap", hi, None)}  # lo == hi (tc, lap 0): no swap lesion
    ev = eval_board(runner, board, enc, rows, tags, args, device, "quick")
    return dict(step=step, n=len(rows), acc={k: round(100 * v["acc"], 2) for k, v in ev.items()},
                ce={k: round(v, 4) for k, v in board_ce(runner, board, enc, rows, tuple(dict.fromkeys(laps)), device, args.micro_bsz).items()},
                alpha_abs=[round(float(x), 5) for x in board.gate().detach().abs().mean(1)], refiner_grad_norm=gn.get("refiner"))


# ---------------------------------------------------------------- one arm

def label_nums(ev):
    """Short keys -> percent, for label_report.py: v = validation main, d = dev main, p1 = 1-pass lesion, vr = main_repeat, L8 / dL8 = laps on validation / dev."""
    names = {"main": "v", "pass1": "p1", "main_repeat": "vr"}
    out = {}
    for split in ("validation", "dev"):
        for tag, e in ev.get(split, {}).items():
            out[names.get(tag, tag) if split == "validation" else "d" + ("" if tag == "main" else names.get(tag, tag))] = round(100 * e["acc"], 2)
    return out


def adapter_sha(d):
    """sha256 of an adapter's weights file (None if there is none): ties every stage-2 result to the exact stage-1 adapter it started from."""
    f = Path(d) / "adapter_model.safetensors"
    if not f.exists():
        return None
    h, buf = hashlib.sha256(), memoryview(bytearray(1 << 20))
    with open(f, "rb") as fh:
        while n := fh.readinto(buf):
            h.update(buf[:n])
    return h.hexdigest()


def env_info(device, dtype):
    """Where and how a result was made: GPU name (or cpu), dtype, library versions (None if absent)."""
    from importlib.metadata import PackageNotFoundError, version
    def ver(name):
        try:
            return version(name)
        except PackageNotFoundError:
            return None
    return dict(gpu=torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu", dtype=str(dtype).replace("torch.", ""),
                torch=torch.__version__, transformers=ver("transformers"), peft=ver("peft"), flash_linear_attention=ver("flash-linear-attention"))


def default_adapter(args, arm):
    return Path(args.out).parent / f"{arm}_s{args.seed}" / "adapter"


def run_arm(args):
    arm, t_start = args.arm, time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    stage2 = arm in STAGE2
    steps = args.steps or (STEPS2 if stage2 else HOPS_STEPS if arm in HOPS else STEPS1)
    k_slots = (args.k or (144 if arm == "tw" else 16)) if arm in BOARD else 0
    src = None
    if arm in ("aplus", "t", "t1", "tw", "tj", "tf", "tc", *WRITTEN, *SD, "br", "aplong"):
        src = Path(args.a_adapter) if args.a_adapter else default_adapter(args, "a")
    elif arm == "bplus":
        src = Path(args.b_adapter) if args.b_adapter else default_adapter(args, "b")
    if src is not None and not (src / "adapter_config.json").exists():
        raise SystemExit(f"[think1] {arm} needs the stage-1 adapter {src} (run arm {'b' if arm == 'bplus' else 'a'} first)")
    lm, tok = T.load_model(args, device, dtype)
    train_rows, dev_rows, val_rows = load_data(args)
    if arm in (*WRITTEN, *SD) and not all("steps" in r for r in train_rows[:1000] + val_rows[:1000]):
        raise SystemExit(f"[think1] {arm} needs rows with a 'steps' field: rebuild {args.data} with backbone/build_data.py (rows are otherwise byte-identical to the old ones)")
    enc = T.Encoder(tok, args.max_len)
    runner = T.Runner(lm, loops=3 if arm in ("b", "bplus") else 1)
    runner.checkpoint = not args.no_grad_ckpt
    tr = dict(loss_curve=[], seconds=0.0, gate_log=[], dev_log=[], step_losses=[])
    result = dict(arm=arm, seed=args.seed, model=args.model, smoke=args.smoke, steps_stage1=args.steps1, steps_stage2=steps if stage2 else 0,
                  k_slots=k_slots, alpha_init=args.alpha_init, params_trainable=0, train=tr, aborted=None, eval={"validation": {}, "dev": {}}, label_nums={},
                  bsz=args.bsz, micro_bsz=args.micro_bsz, max_len=args.max_len, stage1_adapter=str(src) if src else None,
                  loops=runner.loops, loop_block=[runner.start, runner.start + runner.size] if runner.loops > 1 else None,
                  stage1_adapter_sha=adapter_sha(src) if src else None, adapter_sha=None,
                  env=env_info(device, dtype))
    if not stage2:
        result["steps_stage1"] = steps
    aborted = None
    if arm == "tc":
        if args.alpha_init:
            raise SystemExit("[think1] tc is the closed-block control: --alpha-init must be 0")
        args.lmax = 0  # one lap, laps 0..0 (also what the result records and the tags use)
    if arm == "tsd1":
        args.lmax = 1  # the refiner runs once: laps 0..1, and the lap-1 notes feed all four decoder passes
    if arm == "tsd" and args.lmax != S.SD_LAPS:
        raise SystemExit(f"[think1] tsd decodes {S.SD_LAPS} laps: --lmax must be {S.SD_LAPS}")
    sd = None
    if arm in JOINT:  # joint: a's adapter trainable, plus the board (built as in arm t)
        pm = lora_model(lm, src)
        runner.lm = pm.base_model.model
        torch.manual_seed(args.seed)
        board = B.ThinkBoard.from_model(runner.lm, tok, K=k_slots, alpha_init=args.alpha_init).to(device)
        n_board, n_lora = sum(p.numel() for p in board.parameters()), sum(p.numel() for p in pm.parameters() if p.requires_grad)
        result["params_trainable"], result["lmax"] = (n_lora if arm == "tc" else n_board + n_lora), args.lmax  # tc: LoRA only (the board is shut and frozen)
        if arm in SD:
            sd = build_decoder(pm, runner, board, device, args.seed)
            n_dec, n_proj = sum(p.numel() for n, p in pm.named_parameters() if ".dec." in n), sum(p.numel() for p in sd.parameters())
            result["params_trainable"] += n_dec + n_proj
            result["sd_params"] = dict(board=n_board, lora=n_lora, dec_lora=n_dec, proj=n_proj)
            print(f"[sd] arm {arm}: decoder LoRA params {n_dec:,}, Linear {n_proj:,}; decoder passes {S.SD_LAPS} over laps 1..{args.lmax}", flush=True)
        if arm == "tf":
            result["blind"] = dict(p=args.blind_p, until=args.blind_until, seed=args.seed + 3000)
        print(f"[joint] arm {arm} K={k_slots} lmax {args.lmax} board params {n_board:,}{' (frozen, shut)' if arm == 'tc' else ''} lora params {n_lora:,} rho {float(board.rho):.5f}", flush=True)
        t0 = time.time()
        aborted = train_joint(runner, pm, board, enc, train_rows, dev_rows[:256], device, args, steps, tr, sd=sd)
        tr["seconds"] = time.time() - t0
        if sd is not None:
            result["gate_closed"] = (tr.get("gate_check") or {}).get("gate_closed")  # mean |tanh a| < 0.02 at the gate step; P2b goes on either way
            print(f"[sd] gate_closed {result['gate_closed']}; decoder-target data over {tr['sd_data']['rows']} drawn rows: {tr['sd_data']['file_order']} file_order source, "
                  f"{tr['sd_data']['over_laps']} with more than {S.SD_LAPS} steps (kept: lap k decodes step k, later steps are not targets)", flush=True)
        torch.save(dict(state_dict=board.state_dict(), K=k_slots, arm=arm, seed=args.seed, alpha_init=args.alpha_init,
                        **(dict(decoder=sd.state_dict()) if sd is not None else {})), out / "think_block.pt")
        pm.save_pretrained(out / "adapter", **(dict(selected_adapters=["default", "dec"]) if sd is not None else {}))  # the main adapter at the top, the decoder's in adapter/dec
        result["adapter_sha"] = adapter_sha(out / "adapter")
    elif arm in BOARD:
        from peft import PeftModel
        pm = PeftModel.from_pretrained(lm, str(src))  # frozen: not trainable
        for p in pm.parameters():
            p.requires_grad_(False)
        pm.eval()
        runner = T.Runner(pm.base_model.model, loops=1)
        torch.manual_seed(args.seed)
        board = B.ThinkBoard.from_model(runner.lm, tok, K=k_slots, alpha_init=args.alpha_init).to(device)
        result["params_trainable"] = sum(p.numel() for p in board.parameters())
        print(f"[board] arm {arm} K={k_slots} params {result['params_trainable']:,} rho {float(board.rho):.5f}", flush=True)
        t0 = time.time()
        aborted = train_board(runner, board, enc, train_rows, dev_rows[:256], device, args, steps, tr)
        tr["seconds"] = time.time() - t0
        torch.save(dict(state_dict=board.state_dict(), K=k_slots, arm=arm, seed=args.seed, alpha_init=args.alpha_init), out / "think_block.pt")
    else:
        pm = lora_model(lm, src)
        runner.lm = pm.base_model.model
        result["params_trainable"] = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        print(f"[lora] trainable params {result['params_trainable']:,}", flush=True)
        warm = min(100, steps // 10 or 1) if not stage2 else (2 if args.smoke else 60)
        loops, extra, plan = None, (), None
        coda = runner.n - runner.start - runner.size
        if arm in HOPS_PLAN:  # Addendum G: loop counts per row (depth + U{0..2}); hplains is sized from hloops' plan
            plan = hops_plan(train_rows, steps, args.seed, args.bsz, args.seed + 6000)
            ratio = plan_ratio(plan, runner.n, runner.size, coda if arm in ("hloops", "hplains") else 0)
            rs = [r for st_ in plan for r in st_.values()]
            result["loop_schedule"] = dict(seed=args.seed + 6000, plan="depth + U{0..%d}, cap %d" % (HOPS_EXTRA, BR_TRAIN_MAX), mean=sum(rs) / len(rs),
                                           compute_ratio=ratio, block=[runner.start, runner.start + runner.size], eval_loops=list(HOPS_EVAL_LOOPS), main=HOPS_MAIN,
                                           read_k=arm == "hloops", coda_counted=arm in ("hloops", "hplains"))
            if arm == "hplains":
                steps, plan = round(steps * ratio), None
                result["steps_stage1"] = steps
        elif arm in ("br", "aplong", *HOPS):  # Addendum F / G: br (hloop, hloopi) trains with random loop counts of the block; aplong (hplain) is plain LoRA
            loops = loop_schedule(steps, args.seed + 5000)  # given those extra layer passes as extra steps
            ratio = compute_ratio(loops, runner.n, runner.size)
            result["loop_schedule"] = dict(seed=args.seed + 5000, mean=sum(loops) / len(loops), compute_ratio=ratio, block=[runner.start, runner.start + runner.size],
                                           eval_loops=list(HOPS_EVAL_LOOPS if arm in HOPS else BR_EVAL_LOOPS), main=HOPS_MAIN if arm in HOPS else BR_MAIN)
            if arm in ("aplong", "hplain"):
                steps, loops = round(steps * ratio), None
                result["steps_stage2" if stage2 else "steps_stage1"] = steps
        if "loop_schedule" in result:
            if arm in ("hloopi", "hloopd", "hloops"):
                runner.inject = T.Inject(runner.cfg.hidden_size).to(device)
                extra = list(runner.inject.parameters())
                result["params_trainable"] += sum(p.numel() for p in extra)
            print(f"[loop] arm {arm}: loop counts mean {result['loop_schedule']['mean']:.2f}, compute ratio {ratio:.3f}; this run trains {steps} steps", flush=True)
        if arm in WRITTEN:
            with_steps = sum(bool(S.steps_of(r)) for r in train_rows)
            result["written"] = dict(tail=S.STEPS_TAIL, sham=arm == "wsham", max_new=args.max_new_steps, train_rows=len(train_rows), train_rows_with_steps=with_steps)
            print(f"[written] arm {arm}: {with_steps:,} of {len(train_rows):,} train rows have steps; each row is trained twice per batch", flush=True)
        train_lora(runner, pm, enc, train_rows, device, args, steps, warm, args.seed + 1000 if stage2 else args.seed, tr,
                   written={"ws": "gold", "wsham": "sham"}.get(arm), loops=loops, extra=extra, main=HOPS_MAIN if arm in HOPS else BR_MAIN,
                   plan=plan, read=random.Random(args.seed + 7000) if arm == "hloops" else None)
        pm.save_pretrained(out / "adapter")
        result["adapter_sha"] = adapter_sha(out / "adapter")
        if runner.inject is not None:  # hloopi: W is saved beside the adapter, and read back (the eval below runs on the reloaded copy)
            torch.save(runner.inject.state_dict(), out / "inject.pt")
            back = T.Inject(runner.cfg.hidden_size).to(device)
            back.load_state_dict(torch.load(out / "inject.pt", map_location=device))
            same = all(torch.equal(a, b) for a, b in zip(runner.inject.state_dict().values(), back.state_dict().values()))
            runner.inject = back
            result["inject"] = dict(weight_norm=float(back.proj.weight.detach().norm()), roundtrip_equal=same)
            print(f"[inject] |W| {result['inject']['weight_norm']:.4f}; save / load round trip equal: {same}", flush=True)
    runner.checkpoint = False
    if aborted:
        result["aborted"] = aborted
        print(f"[abort] {aborted}", flush=True)
    else:
        ev = result["eval"]
        if arm in BOARD:
            for split, rows in (("dev", dev_rows), ("validation", val_rows)):
                ev[split] = eval_board(runner, board, enc, rows, tags_for(arm, split, args.lmax), args, device, split)
            if sd is not None:
                result["decoder"] = eval_decoder(runner, pm, board, sd, enc, val_rows, args, device, args.lmax)
                print(f"[result] {arm} s{args.seed} decoder step-token accuracy: {result['decoder']}", flush=True)
        else:
            for split, rows in (("dev", dev_rows), ("validation", val_rows)):
                if arm in WRITTEN:  # T: writes its steps, then the answer is scored; C1: the same weights answering directly (arm aplus's eval path)
                    sham = arm == "wsham"
                    ev[split]["T"] = eval_written(runner, enc, rows, device, args, sham, name=f"{split} T")
                    ev[split]["C1"] = eval_greedy(runner, enc, rows, device, args, name=f"{split} C1", board_path=True)
                    if split == "validation":
                        idx = [i for i, r in enumerate(rows) if S.steps_of(r)][:FMT_ROWS]
                        ev[split]["fmt"] = dict(eval_written(runner, enc, [rows[i] for i in idx], device, args, sham, gold=True, name="format check"), row_idx=idx)
                    continue
                if arm in ("br", *HOPS_LOOPED):  # every loop count on validation (with the answers, for the halting readout); dev at the main count only
                    ls, main = (HOPS_EVAL_LOOPS, HOPS_MAIN) if arm in HOPS else (BR_EVAL_LOOPS, BR_MAIN)
                    rs = ls if split == "validation" else (main,)
                    for r in rs:
                        ev[split][f"r{r}"] = eval_greedy(runner, enc, rows, device, args, order=T.block_order(runner.n, runner.start, r, runner.size),
                                                         name=f"{split} r{r}", keep_preds=split == "validation", keep_logp=split == "validation" and arm in HOPS)
                    ev[split]["main"] = {k: v for k, v in ev[split][f"r{main}"].items() if k != "preds"}
                    if split == "validation" and runner.inject is not None:  # hloopi's lesion: the same weights with W = 0 (no injection), at the main count
                        inj, runner.inject = runner.inject, None
                        ev[split][f"r{main}_w0"] = eval_greedy(runner, enc, rows, device, args, order=T.block_order(runner.n, runner.start, main, runner.size),
                                                               name=f"{split} r{main} W=0")
                        runner.inject = inj
                    if split == "validation":
                        result["halting"] = halting_readout(rows, {r: ev[split][f"r{r}"]["preds"] for r in rs}, {r: ev[split][f"r{r}"]["hits"] for r in rs}, loops=ls)
                        if arm in HOPS:
                            result["halting_conf"] = halting_conf(rows, {r: ev[split][f"r{r}"]["logp"] for r in rs}, {r: ev[split][f"r{r}"]["hits"] for r in rs}, loops=ls)
                            result["oracle_depth"] = oracle_depth(rows, {r: ev[split][f"r{r}"]["hits"] for r in rs})
                        print(f"[halt] br answer-stable halting: {result['halting']['acc'] * 100:.2f}% at mean {result['halting']['mean_loops']:.2f} loops; "
                              f"Spearman(depth, loops) {result['halting']['spearman_depth_loops']}", flush=True)
                    continue
                bp = arm in ("a", "aplus", "aplong")
                ev[split]["main"] = eval_greedy(runner, enc, rows, device, args, name=f"{split} main", board_path=bp)
                if arm == "b":
                    ev[split]["pass1"] = eval_greedy(runner, enc, rows, device, args, order=T.block_order(runner.n, runner.start, 1, runner.size), name=f"{split} pass1")
                if arm == "a" and split == "validation" and args.seed == 0:
                    ev[split]["main_repeat"] = eval_greedy(runner, enc, rows, device, args, reverse=True, name="validation repeat", board_path=bp)
        for split in ev:
            for tag, e in ev[split].items():
                print(f"[result] {arm} s{args.seed} {split} {tag} acc {100 * e['acc']:.2f} (n={e['n']})", flush=True)
        result["label_nums"] = label_nums(ev)
    result["wall_seconds"] = time.time() - t_start
    if device.type == "cuda":
        result["peak_gpu_mem_gb"] = torch.cuda.max_memory_allocated() / 2**30
    path = out / f"result_{arm}_s{args.seed}.json"
    path.write_text(json.dumps(result, indent=1))
    print(f"[done] wrote {path}", flush=True)
    return 3 if aborted else 0


# ---------------------------------------------------------------- smoke

def run_summarize(root, data):
    s = HERE / "summarize.py"
    if not s.exists():
        print("[smoke] summarize.py not found; skipped", flush=True)
        return None
    r = subprocess.run([sys.executable, str(s), str(root), "--data", str(data)], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode:
        print(r.stderr, file=sys.stderr)
    return r


def smoke_args(args, arm, root, data):
    """Args of one smoke arm: tiny sizes, 6 steps per stage, own dir OUT/smoke/{arm}_s{seed} (so the stage-1 adapters are found by default)."""
    a = copy.copy(args)
    a.arm, a.out, a.data = arm, str(Path(root) / f"{arm}_s{args.seed}"), str(data)
    a.steps, a.max_len, a.bsz, a.micro_bsz = args.steps or 6, min(args.max_len, 256), min(args.bsz, 8), min(args.micro_bsz, 4)
    a.steps1 = 6
    return a


def smoke(args):
    """Every arm in sequence (a, b, then aplus, bplus, t, t1, tw, tj, tf, tc taking the stage-1 adapters) into OUT/smoke/, then summarize."""
    root = Path(args.out) / "smoke"
    data = smoke_data(args.data, root)
    rcs, t0 = {}, time.time()
    arms = [args.arm] if args.arm else [a for a in ARMS if a not in HOPS]  # the hops arms need the hops bed (--arm with --data HOPS_DIR)
    if args.arm in (*JOINT, *WRITTEN, "br", "aplong") and not args.a_adapter and not (root / f"a_s{args.seed}" / "adapter" / "adapter_config.json").exists():
        arms.insert(0, "a")  # tj / tf / tc start from a's adapter: train a first
    for arm in arms:
        print(f"== smoke arm {arm} {time.time() - t0:.0f}s", flush=True)
        rcs[arm] = run_arm(smoke_args(args, arm, root, data))
    r = run_summarize(root, data)
    print(f"== smoke done {time.time() - t0:.0f}s exit codes {rcs}" + (f" summarize {r.returncode}" if r else ""), flush=True)
    return 1 if any(rcs.values()) or (r is not None and r.returncode) else 0


# ---------------------------------------------------------------- main

def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--arm", choices=ARMS, help="required unless --smoke (which runs every arm)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default="out/data", help="dir with train.jsonl dev.jsonl validation.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--micro-bsz", type=int, default=4)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--limit-eval", type=int, default=None)
    ap.add_argument("--eval-bsz", type=int, default=64)
    ap.add_argument("--eval-tokens", type=int, default=32768)
    ap.add_argument("--no-cache", action="store_true", help="cache-free T.greedy decoding for arms a/b/aplus/bplus (slow; for checking; arms a, aplus then skip the board decode path)")
    ap.add_argument("--no-grad-ckpt", action="store_true")
    ap.add_argument("--no-lap-ckpt", action="store_true", help="board arms: keep every slot / answer pass's activations instead of recomputing them in backward (more memory, same result)")
    ap.add_argument("--a-adapter", default=None, help="stage-1 arm a adapter for aplus/t/t1/tw/tj/tf/tc (default: <out parent>/a_s{seed}/adapter)")
    ap.add_argument("--b-adapter", default=None, help="stage-1 arm b adapter for bplus (default: <out parent>/b_s{seed}/adapter)")
    ap.add_argument("--steps", type=int, default=None, help="override the per-arm step count (not for the prereg run: 418 stage 1, 1,254 stage 2)")
    ap.add_argument("--k", type=int, default=None, help="board slots (default 16; 144 for tw)")
    ap.add_argument("--gate-step", type=int, default=150, help="step of the mechanics gate")
    ap.add_argument("--gate-enforce", action="store_true", help="abort on the gate in --smoke too (always enforced otherwise)")
    ap.add_argument("--lmax", type=int, default=4, help="arms tj / tf: fixed L_max of the board loss, and the lap count scored (L{lmax}, swap, gates-off, quick eval)")
    ap.add_argument("--alpha-init", type=float, default=0.0, help="board arms: every gate pre-activation alpha starts here (tanh(0.3) = 0.291 is plan step P2a); 0 = shut gates, as in all earlier runs")
    ap.add_argument("--max-new-steps", type=int, default=MAX_NEW_STEPS, help="arms ws / wsham: most tokens a model may write for its steps and answer in the T evaluation")
    ap.add_argument("--blind-p", type=float, default=0.5, help="arm tf: initial chance that a micro-batch's board loss uses blind answer passes")
    ap.add_argument("--blind-until", type=float, default=0.6, help="arm tf: fraction of training at which that chance has fallen linearly to 0")
    ap.add_argument("--log-every", type=int, default=250, help="dev-subset log interval for t/t1/tw/tj")
    args = ap.parse_args(argv)
    if not args.arm and not args.smoke:
        ap.error("--arm is required unless --smoke")
    args.steps1 = STEPS1
    if args.smoke:
        args.gate_step, args.log_every = min(args.gate_step, 4), min(args.log_every, 3)
    return args


def main(argv=None):
    args = parse(argv)
    return smoke(args) if args.smoke else run_arm(args)


if __name__ == "__main__":
    sys.exit(main())
