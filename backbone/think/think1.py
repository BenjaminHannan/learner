"""Think-1 harness (backbone/think/PREREG.md, IMPL-SPEC.md section 3): every arm, training, evaluation, result JSON.

Arms:  a      LoRA on the village rows (stage 1, 418 steps)         b      a + layers 8-11 run 3 times (stage 1)
       aplus  a's adapter, LoRA trained 1,254 more steps            bplus  b's adapter, LoRA trained 1,254 more steps
       t      a's adapter frozen, only the ThinkBoard (board.py) trains, laps 0..8 or 12
       t1     as t but L_max = 1                                    tw     as t1 with K=144 slots
`--smoke` runs every arm end to end on a tiny random qwen3_5 on CPU (into OUT/smoke/) and then summarize.py.
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
from xent import fixed_cross_entropy  # noqa: E402

ARMS = ("a", "b", "aplus", "bplus", "t", "t1", "tw")
STAGE1, STAGE2, BOARD = ("a", "b"), ("aplus", "bplus", "t", "t1", "tw"), ("t", "t1", "tw")
STEPS1, STEPS2 = 418, 1254
LR, LR_ALPHA, LR_BOARD, LAMBDA = 2e-4, 3e-3, 5e-4, 0.01
GATE = dict(alpha=0.02, div=2.0, window=20)  # PREREG mechanics gate: only the gates-shut check at step 150 and NaN / divergence abort; board cosine and clamp share are logs
HEAD = 2000  # L16 / L24 are scored on the first 2,000 validation rows only


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
        rows.append(dict(id=f"{split}-{v}:q{i % 4}", visit_id=f"{split}-{v}", split=split, context="\n".join(ctx),
                         question=f"[question] Where is {who}?", answer=f"the {loc[who]}", qtype="Q1", base_qtype="Q1",
                         bank="q.where_now" if i % 2 else "q.where_before", depth=i % 7, template=f"syn-{i % 3}"))
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


def lora_model(lm, adapter=None):
    from peft import LoraConfig, PeftModel, get_peft_model
    if adapter:
        return PeftModel.from_pretrained(lm, str(adapter), is_trainable=True)
    return get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=T.LORA_TARGETS, bias="none"))


def train_lora(runner, pm, enc, rows, device, args, steps, warmup, order_seed, tr):
    params = [p for p in pm.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0, betas=(0.9, 0.999))
    stream = batches(len(rows), order_seed, args.bsz)
    pm.train()
    runner.lm.train()
    t0, window = time.time(), []
    for step in range(steps):
        batch = encode_batch(enc, rows, next(stream))
        n_ans = sum(len(a) for _, a in batch)
        for g in opt.param_groups:
            g["lr"] = T.cosine_lr(step, steps, LR, warmup)
        total = 0.0
        for k in range(0, len(batch), args.micro_bsz):
            s, _ = answer_loss_fixed(runner, batch[k:k + args.micro_bsz], device)
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
    pm.eval()
    runner.lm.eval()


def entry(hits):
    s = "".join(hits)
    return {"acc": s.count("1") / len(s) if s else 0.0, "n": len(s), "hits": s, "row_offset": 0}


@torch.no_grad()
def eval_greedy(runner, enc, rows, device, args, order=None, reverse=False, name="", board_path=False):
    """Greedy exact-match hits for arms a/b/aplus/bplus. Batches are built in descending length order, or ascending if reverse
    (different batch composition: used for the eval-noise rerun). Returns the entry with hits in file order.
    board_path (arms a, aplus): decode with board.prefill of prompt[:-1] + board.decode with no board read, the code eval_board runs on the same batches (same two segments), so S(8) and
    A_ref are measured by identical code; otherwise (b, bplus: they need the looped runner) T.greedy. --no-cache keeps T.greedy for the check."""
    board_path = board_path and not args.no_cache
    order = order or runner.order
    prompts = [enc.prompt(r)[0] for r in rows]
    hit, t0, nb, done = ["0"] * len(rows), time.time(), 0, 0
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
                gen = T.greedy(runner, ps, device, enc.eos, cache=not args.no_cache, order=order)
            for i, g in zip(chunk, gen):
                hit[i] = "1" if T.normalise(enc.tok.decode(g, skip_special_tokens=True)) == T.normalise(rows[i]["answer"]) else "0"
            k += len(chunk)
            done += len(chunk)
            nb += 1
            if nb % 20 == 0:
                print(f"[eval {name}] {done}/{len(rows)} {time.time() - t0:.0f}s", flush=True)
    return entry(hit)


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


# ---------------------------------------------------------------- board arms: evaluation

def tags_for(arm, split):
    P = lambda L, n=None: ("plain", L, n)
    if arm == "t":
        if split == "dev":
            return {f"L{L}": P(L) for L in (0, 1, 8)}
        return {**{f"L{L}": P(L) for L in (0, 1, 2, 4, 8, 12)}, "L16": P(16, HEAD), "L24": P(24, HEAD), "swap8": ("swap", 8, None),
                "mean8": ("mean", 8, None), "rep1_8": ("rep", 8, None), "gatesoff8": ("off", 8, None),
                "ref0": ("none", 8, None)}
    if arm == "t1":
        return {f"L{L}": P(L) for L in ((0, 1, 8) if split == "validation" else (1,))}
    return {"L1": P(1)} if split == "validation" else {}


def swap_kv_for(kv, visits, prev):
    """Row i reads the board of a row of another story: in this batch if it has two stories, else from the previous batch.
    Returns (kv, number of rows left with a same-story board). prev = (visits, kv) of the previous batch or None."""
    idx = B.swap_index(visits)
    if idx is not None:
        return B.swap_kv(kv, idx), 0
    if prev is None:  # first batch has one story and there is nothing to borrow: roll inside the batch (counted)
        return B.swap_kv(kv, torch.arange(1, len(visits) + 1) % len(visits)), len(visits)
    pv, pkv = prev
    pool = [(torch.cat([k, pk]), torch.cat([v, pv_])) for (k, v), (pk, pv_) in zip(kv, pkv)]
    n, idx, same = len(visits), [], 0
    for i in range(n):
        cand = [n + (i + s) % len(pv) for s in range(len(pv))]
        j = next((j for j in cand if pv[j - n] != visits[i]), None)
        if j is None:
            j, same = cand[0], same + 1
        idx.append(j)
    return B.swap_kv(pool, torch.tensor(idx)), same


@torch.no_grad()
def eval_board(runner, board, enc, rows, tags, args, device, name="eval"):
    """tags: {tag: (kind, L, nmax)}, kind in plain / swap / mean / rep / off / none. Each batch is prefilled once, think() runs to the largest L and
    records the slot K/V at every L needed, and every tag is decoded on its own cache clone. Returns {tag: entry} with hits in file order."""
    if not tags:
        return {}
    n = len(rows)
    prompts = [enc.prompt(r)[0] for r in rows]
    visits = [r.get("visit_id") for r in rows]
    hits = {t: ["0"] * (n if lim is None else min(lim, n)) for t, (_, _, lim) in tags.items()}
    zero, prev, same, t0, nb = torch.zeros_like(board.alpha), {}, {t: 0 for t in tags}, time.time(), 0
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
            kv, _ = B.think(board, runner, C, mask, p, max(keep, default=0), keep=keep, stats=False)
            rep = {}
            for t in active:
                kind, L, lim = tags[t]
                gates = None
                if kind == "plain":
                    skv = kv[L]
                elif kind == "off":
                    skv, gates = kv[L], zero
                elif kind == "none":  # reference: no board read at all, same batches and path as every other tag; gatesoff8 must equal it row for row
                    skv = None
                elif kind == "mean":
                    skv = B.mean_kv(kv[L])
                elif kind == "swap":
                    skv, bad = swap_kv_for(kv[L], vs, prev.get(t))
                    same[t] += bad
                    prev[t] = (vs, kv[L])
                else:
                    if L not in rep:
                        rep[L] = B.think(board, runner, C, mask, p, L, keep={L}, repeat_delta1=True, stats=False)[0][L]
                    skv = rep[L]
                gen = B.decode(runner, board, C, mask, p, lt, skv, eos=enc.eos, gates=gates)
                for i, g in zip(chunk, gen):
                    if lim is None or i < lim:
                        hits[t][i] = "1" if T.normalise(enc.tok.decode(g, skip_special_tokens=True)) == T.normalise(rows[i]["answer"]) else "0"
            nb += 1
            if nb % 20 == 0:
                print(f"[eval {name}] {k}/{len(order)} batches {nb} {time.time() - t0:.0f}s", flush=True)
    out = {t: entry(h) for t, h in hits.items()}
    for t, s in same.items():
        if s:
            out[t]["swap_same_story_rows"] = s
    return out


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


def quick_eval(runner, board, enc, rows, device, args, step, gn):
    """The every-250-steps log on the first 256 dev rows: answer CE and greedy accuracy at L=1 and 8, swap lesion at 8, |tanh alpha| per layer, refiner grad norm."""
    ev = eval_board(runner, board, enc, rows, {"L1": ("plain", 1, None), "L8": ("plain", 8, None), "swap8": ("swap", 8, None)}, args, device, "quick")
    return dict(step=step, n=len(rows), acc={k: round(100 * v["acc"], 2) for k, v in ev.items()},
                ce={k: round(v, 4) for k, v in board_ce(runner, board, enc, rows, (1, 8), device, args.micro_bsz).items()},
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
    steps = args.steps or (STEPS2 if stage2 else STEPS1)
    k_slots = (args.k or (144 if arm == "tw" else 16)) if arm in BOARD else 0
    src = None
    if arm in ("aplus", "t", "t1", "tw"):
        src = Path(args.a_adapter) if args.a_adapter else default_adapter(args, "a")
    elif arm == "bplus":
        src = Path(args.b_adapter) if args.b_adapter else default_adapter(args, "b")
    if src is not None and not (src / "adapter_config.json").exists():
        raise SystemExit(f"[think1] {arm} needs the stage-1 adapter {src} (run arm {'b' if arm == 'bplus' else 'a'} first)")
    lm, tok = T.load_model(args, device, dtype)
    train_rows, dev_rows, val_rows = load_data(args)
    enc = T.Encoder(tok, args.max_len)
    runner = T.Runner(lm, loops=3 if arm in ("b", "bplus") else 1)
    runner.checkpoint = not args.no_grad_ckpt
    tr = dict(loss_curve=[], seconds=0.0, gate_log=[], dev_log=[], step_losses=[])
    result = dict(arm=arm, seed=args.seed, model=args.model, smoke=args.smoke, steps_stage1=args.steps1, steps_stage2=steps if stage2 else 0,
                  k_slots=k_slots, params_trainable=0, train=tr, aborted=None, eval={"validation": {}, "dev": {}}, label_nums={},
                  bsz=args.bsz, micro_bsz=args.micro_bsz, max_len=args.max_len, stage1_adapter=str(src) if src else None,
                  loops=runner.loops, loop_block=[runner.start, runner.start + runner.size] if runner.loops > 1 else None,
                  stage1_adapter_sha=adapter_sha(src) if src else None, adapter_sha=None,
                  env=env_info(device, dtype))
    if not stage2:
        result["steps_stage1"] = steps
    aborted = None
    if arm in BOARD:
        from peft import PeftModel
        pm = PeftModel.from_pretrained(lm, str(src))  # frozen: not trainable
        for p in pm.parameters():
            p.requires_grad_(False)
        pm.eval()
        runner = T.Runner(pm.base_model.model, loops=1)
        torch.manual_seed(args.seed)
        board = B.ThinkBoard.from_model(runner.lm, tok, K=k_slots).to(device)
        result["params_trainable"] = sum(p.numel() for p in board.parameters())
        print(f"[board] arm {arm} K={k_slots} params {result['params_trainable']:,} rho {float(board.rho):.5f}", flush=True)
        t0 = time.time()
        aborted = train_board(runner, board, enc, train_rows, dev_rows[:256], device, args, steps, tr)
        tr["seconds"] = time.time() - t0
        torch.save(dict(state_dict=board.state_dict(), K=k_slots, arm=arm, seed=args.seed), out / "think_block.pt")
    else:
        pm = lora_model(lm, src)
        runner.lm = pm.base_model.model
        result["params_trainable"] = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        print(f"[lora] trainable params {result['params_trainable']:,}", flush=True)
        warm = min(100, steps // 10 or 1) if not stage2 else (2 if args.smoke else 60)
        train_lora(runner, pm, enc, train_rows, device, args, steps, warm, args.seed + 1000 if stage2 else args.seed, tr)
        pm.save_pretrained(out / "adapter")
        result["adapter_sha"] = adapter_sha(out / "adapter")
    runner.checkpoint = False
    if aborted:
        result["aborted"] = aborted
        print(f"[abort] {aborted}", flush=True)
    else:
        ev = result["eval"]
        if arm in BOARD:
            for split, rows in (("dev", dev_rows), ("validation", val_rows)):
                ev[split] = eval_board(runner, board, enc, rows, tags_for(arm, split), args, device, split)
        else:
            for split, rows in (("dev", dev_rows), ("validation", val_rows)):
                bp = arm in ("a", "aplus")
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
    """Every arm in sequence (a, b, then aplus, bplus, t, t1, tw taking the stage-1 adapters) into OUT/smoke/, then summarize."""
    root = Path(args.out) / "smoke"
    data = smoke_data(args.data, root)
    rcs, t0 = {}, time.time()
    for arm in [args.arm] if args.arm else ARMS:
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
    ap.add_argument("--a-adapter", default=None, help="stage-1 arm a adapter for aplus/t/t1/tw (default: <out parent>/a_s{seed}/adapter)")
    ap.add_argument("--b-adapter", default=None, help="stage-1 arm b adapter for bplus (default: <out parent>/b_s{seed}/adapter)")
    ap.add_argument("--steps", type=int, default=None, help="override the per-arm step count (not for the prereg run: 418 stage 1, 1,254 stage 2)")
    ap.add_argument("--k", type=int, default=None, help="board slots (default 16; 144 for tw)")
    ap.add_argument("--gate-step", type=int, default=150, help="step of the mechanics gate")
    ap.add_argument("--gate-enforce", action="store_true", help="abort on the gate in --smoke too (always enforced otherwise)")
    ap.add_argument("--log-every", type=int, default=250, help="dev-subset log interval for t/t1/tw")
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
