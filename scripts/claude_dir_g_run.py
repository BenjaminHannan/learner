#!/usr/bin/env python3
"""dir-g (test G, "search inside the thought"; builder thread, 2026-09-28): the sealed loop with ONE change, K = 4 learned start states.

Design and marks (sealed, not edited here): artifacts/claude-dir-g-search-20260928/{DESIGN,PASSMARKS}.md; this build's
addendum: artifacts/claude-dir-g-build-20260928/ADDENDUM-1.md.

The change (DESIGN.md section 3). The sealed loop starts every puzzle's thought from zeros. Here the loop starts from K = 4 learned
vectors s_1..s_4 (each [d], broadcast over cells), i.e. four streams sharing every other weight (K x d = 2,048 extra weights).
  train: the K streams run as K copies of the batch through the same rounds (same total, same k). Per item the stream with the
         lowest mean graded-round token CE (selection detached; ties go to the lowest index) gets its token CE at weight 1, the
         other three at weight 0.05 each. Halt BCE is applied to all K streams against each stream's own exactness (weight 0.5,
         averaged over streams). Everything else (data, steps, batch, lr, schedule, rounds, wd, stop rule) is the sealed recipe,
         imported from claude_dir_h2_run.py (the pool H2 built; --pool old gives the 1,062 target-24 hands instead).
  test:  each stream stops by the sealed v2 stop rule; the answer is the stream whose halt probability at its stop is highest
         (ties: lowest index). Reported: S_pick (right), S_rand (stream 0 right; also the mean over the 4), S_any (oracle),
         D (mean number of distinct final answers among the 4 streams, compared on the blank cells).
K = 1 with start zeros reproduces the sealed loop exactly (V2, `selftest`, CPU fp32).

Implementation choices the design left open (each is listed in ADDENDUM-1.md; none is a mark):
  * start init: N(0, 1.0) per entry. The loop's own state is a LayerNorm output (unit scale per cell), so 1.0 is "the size of a
    state"; a much smaller std would make the four streams nearly identical at round 1. Flag --start-std.
  * the sealed loop detaches after its free (no-grad) rounds, so the start vectors get gradient only on steps with no free round
    (total == k, about 15% of steps). Kept, so that nothing but the starts and the loss weights changes.
  * the start vectors are in their own AdamW group with weight decay 0 (the sealed recipe's 0.1 decay would pull the four starts
    toward zero, i.e. toward each other). Everything else keeps wd 0.1.
  * --serial-streams runs the K streams one after another (a no-grad pass picks the winners, then one forward/backward per stream)
    to cut memory ~4x with the same gradient; `selftest` checks the two modes agree. Default: all K streams at once.

  python -B scripts/claude_dir_g_run.py train --seed S --out DIR [--pool h2|old] [--K 4] [--serial-streams]     (defaults = the run)
  python -B scripts/claude_dir_g_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_dir_g_run.py poison --ckpt DIR/final.pt --out F
  python -B scripts/claude_dir_g_run.py timing [--steps 200] [--out F]     (real training steps on the real pool, then a projection)
  python -B scripts/claude_dir_g_run.py selftest | check-mask
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h2_run as H2  # noqa: E402  (imports the sealed 358u chain: fixed env 0, autocast cache off, grad checks, stop rule v2)

U = H2.U
R, E = U.R, U.E
I2 = U.I2
stop_round = I2.I.G.V.stop_round
OldSource = H2.WideSource.__mro__[1]           # the sealed 1,062-hand practice stream, before H2 swapped it out
K_DEFAULT, START_STD, LEAK = 4, 1.0, 0.05
HALT_W = 0.5
NUMBERS_PRACTICE_DEV = 200


# ---------------- model ----------------
class GNet(R.Net):
    """the sealed loop net plus K learned start states (the only new weights)"""

    def __init__(self, K=K_DEFAULT, start_std=START_STD, zero_start=False):
        super().__init__("loop")
        self.K = K
        d = R.ARMS["loop"]["d"]
        init = torch.zeros(K, d) if zero_start else torch.randn(K, d) * start_std
        self.starts = nn.Parameter(init)

    def h0(self, ks, B, T):
        """start states for the streams in ks, stream-major rows [len(ks) * B, T, d]"""
        return self.starts[list(ks)].repeat_interleave(B, 0)[:, None, :].expand(-1, T, -1)

    def train_rounds(self, tokens, slot, env, n_free, n_grad, ks):
        """like R.Net.loop_train for the streams ks; rows are stream-major (row = j * B + i for ks[j], item i)"""
        e, (dr, dc) = self.embed(tokens, slot, env)
        B, T, _ = e.shape
        eK = e.repeat(len(ks), 1, 1)
        h = self.h0(ks, B, T)
        if n_free:
            with torch.no_grad():
                for _ in range(n_free):
                    h = self.step(h, eK.detach(), dr, dc)
            h = h.detach()                                   # as sealed: gradient only through the last n_grad rounds
        outs = []
        for _ in range(n_grad):
            h = self.step(h, eK, dr, dc)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def stream_rounds(self, tokens, slot, env, n):
        """all K streams, n rounds: preds [K, B, n, T], halt probs [K, B, n]"""
        e, (dr, dc) = self.embed(tokens, slot, env)
        B, T, _ = e.shape
        eK = e.repeat(self.K, 1, 1)
        h = self.h0(range(self.K), B, T)
        preds, qs = [], []
        for _ in range(n):
            h = self.step(h, eK, dr, dc)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        K = self.K
        return (torch.stack(preds, 1).view(K, B, n, T), torch.stack(qs, 1).view(K, B, n))


# ---------------- loss ----------------
def per_row(outs, s, y, n_streams):
    """per graded round and per row: summed token CE over the row's blank cells, exactness, halt BCE.
    Returns tokce [R, rows], exact [R, rows], bce [R, rows]; rows = n_streams * B, stream-major."""
    B = s.shape[0]
    sb = s.view(B, -1).bool().repeat(n_streams, 1)
    yb = y.view(B, -1).repeat(n_streams, 1)
    tokce, exact, bce = [], [], []
    for lg, q in outs:
        ce = F.cross_entropy(lg.float().reshape(-1, lg.shape[-1]), yb.reshape(-1), reduction="none").view(sb.shape)
        tokce.append((ce * sb).sum(1))
        ex = ((lg.argmax(-1) == yb) | ~sb).all(1).float()
        exact.append(ex)
        bce.append(F.binary_cross_entropy_with_logits(q.float(), ex, reduction="none"))
    return torch.stack(tokce), torch.stack(exact), torch.stack(bce)


def select_weights(score, leak=LEAK):
    """score [K, B] (lower is better) -> weights [K, B]: 1 for the lowest (first on ties), leak for the others"""
    w = torch.full_like(score, leak)
    w.scatter_(0, score.argmin(0, keepdim=True), 1.0)
    return w


def stream_scores(tokce, n_slot, n_streams):
    """mean over graded rounds of the per-item mean token CE, detached: [K, B]"""
    per_item = (tokce / n_slot.repeat(n_streams)).mean(0)
    return per_item.detach().view(n_streams, -1)


def g_loss(net, t, s, y, env, n_free, n_grad, serial=False):
    """(loss to backprop -- or None when serial, where backward is done inside --, stats dict).
    Loss = mean over graded rounds of  sum_items sum_k w[k,i] * tokCE[k,i,r] / N_slot   +   0.5 * mean over rounds/streams/items of halt BCE.
    With K = 1 this is exactly the sealed loop's loss."""
    K, B = net.K, s.shape[0]
    n_slot = s.view(B, -1).bool().sum(1).float()
    N = n_slot.sum()
    if not serial:
        outs = net.train_rounds(t, s, env, n_free, n_grad, range(K))
        tokce, exact, bce = per_row(outs, s, y, K)
        w = select_weights(stream_scores(tokce, n_slot, K))
        ce = (tokce * w.view(1, -1)).sum(1).div(N).mean()
        hl = bce.mean()
        loss = ce + HALT_W * hl
        return loss, {"ce": ce.detach(), "halt": hl.detach(), "exact_last": exact[-1].view(K, B), "w": w}
    with torch.no_grad():                                     # pass 1: who wins each item
        outs = net.train_rounds(t, s, env, n_free, n_grad, range(K))
        tokce, exact, _ = per_row(outs, s, y, K)
        w = select_weights(stream_scores(tokce, n_slot, K))
    ex_last = []
    ce_tot = hl_tot = 0.0
    for k in range(K):                                        # pass 2: one stream at a time (same numbers, one stream of memory)
        outs = net.train_rounds(t, s, env, n_free, n_grad, [k])
        tk, ex, bc = per_row(outs, s, y, 1)
        ce_k = (tk * w[k].view(1, -1)).sum(1).div(N).mean()
        hl_k = bc.mean() / K
        (ce_k + HALT_W * hl_k).backward()
        ce_tot += float(ce_k.detach()); hl_tot += float(hl_k.detach())
        ex_last.append(ex[-1].detach())
    return None, {"ce": torch.tensor(ce_tot), "halt": torch.tensor(hl_tot), "exact_last": torch.stack(ex_last), "w": w}


# ---------------- evaluation ----------------
def flat_slot(it):
    return [x for row in it.slot for x in row]


@torch.no_grad()
def g_evaluate(net, items, device, bs=100):
    net.eval()
    n, K = R.TEST_ROUNDS, net.K
    right = rand0 = any_ = any_round_all = any_round_s0 = 0
    rand_mean = 0.0
    dsum = 0
    right_by_stream = [0] * K
    stop_rounds = [[] for _ in range(K)]
    pick_hist = [0] * K
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds, qs = net.stream_rounds(t, s, env, n)
        preds, qs = preds.tolist(), qs.tolist()
        for b, it in enumerate(chunk):
            fs = flat_slot(it)
            ok, qstop, keys = [], [], []
            for k in range(K):
                p, q = preds[k][b], qs[k][b]
                stop = stop_round(p, q, n)
                stop_rounds[k].append(stop + 1)
                ok.append(bool(E.check(it, R.grid_of(p[stop], it))))
                qstop.append(q[stop])
                keys.append(tuple(a for a, sl in zip(p[stop], fs) if sl))
            pick = max(range(K), key=lambda k: qstop[k])         # first maximum: ties go to the lowest index
            right += ok[pick]
            pick_hist[pick] += 1
            rand0 += ok[0]
            rand_mean += sum(ok) / K
            any_ += any(ok)
            dsum += len(set(keys))
            for k in range(K):
                right_by_stream[k] += ok[k]
            hit_any_round = [any(E.check(it, R.grid_of(preds[k][b][r], it)) for r in range(n)) for k in range(K)]
            any_round_all += any(hit_any_round)
            any_round_s0 += hit_any_round[0]
    N = len(items)
    return {"n": N, "right": right, "S_pick": right, "S_rand0": rand0, "S_rand_mean": round(rand_mean, 2), "S_any": any_,
            "D_mean_distinct_answers": round(dsum / N, 3), "right_by_stream": right_by_stream, "pick_hist": pick_hist,
            "mean_rounds_by_stream": [round(sum(r) / len(r), 2) for r in stop_rounds],
            "right_at_any_round_stream0": any_round_s0, "right_at_any_round_any_stream": any_round_all}


# ---------------- io ----------------
def g_load(ckpt, device):
    d = torch.load(ckpt, map_location=device)
    net = GNet(d["K"], zero_start=True).to(device)
    net.load_state_dict(d["state"])
    return net


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = g_load(a.ckpt, device)
    tests = R.load_tests(a.tests, a.limit)
    res = {"arm": "loop-g", "K": net.K, "ckpt": str(a.ckpt), "tests": {}}
    for name, env, size, seed, role in R.TESTS:
        r = g_evaluate(net, tests[name], device)
        r["role"] = role
        res["tests"][name] = r
        print(name, json.dumps(r), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


@torch.no_grad()
def poison_predictions(net, items, device):
    net.eval()
    t, s, _, env = R.tensors(items, device)
    return list(net.stream_rounds(t, s, env, R.TEST_ROUNDS))


def poison(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = g_load(a.ckpt, device)
    items = U.poison_items()
    out, same_all = {}, True
    for kind in ("sums", "grids", "numbers"):
        batch = [it for it in items if it.env == kind]
        swapped = [E.Item("sums" if kind == "numbers" else "numbers", it.size, it.tokens, it.slot, it.target, it.meta) for it in batch]
        p, q = poison_predictions(net, batch, device), poison_predictions(net, swapped, device)
        same = all(torch.equal(x, y) for x, y in zip(p, q))
        same_all &= same
        out[kind] = {"n": len(batch), "identical": same}
    res = {"arm": "loop-g", "K": net.K, "ckpt": str(a.ckpt), "V1_identical": same_all, "by_kind": out}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


# ---------------- training ----------------
def train(a):
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    Src = H2.WideSource if a.pool == "h2" else OldSource
    src = Src(a.seed, latin_pool=a.latin_pool)
    dev_rng = random.Random(7000 + a.seed)
    dev = {f"{env}{size}": [E.make_sum(dev_rng, size) if env == "sums" else
                            E.latin_item(dev_rng, *E.make_latin_base(dev_rng, size)) for _ in range(200)]
           for env, size in (("sums", 4), ("grids", 5))}
    practice, _ = H2.pools() if a.pool == "h2" else (E.split_four(E.number_hands()[0])[0], None)
    npr = random.Random(7100 + a.seed)                          # its own rng: never touches the practice stream
    dev["numbers4practice"] = [E.number_item(npr, h, t, s) for h, t, s in npr.sample(practice, NUMBERS_PRACTICE_DEV)]
    net = GNet(a.K, a.start_std).to(device)
    nparams = sum(p.numel() for p in net.parameters())
    decay = [p for n, p in net.named_parameters() if n != "starts"]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": 0.1}, {"params": [net.starts], "weight_decay": 0.0}],
                            lr=a.lr, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    round_rng = random.Random(9000 + a.seed)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    I2._STATS.update(steps=0, steps_block_nograd=0, grad_norms=[])
    run = {"ce": 0.0, "exact": 0.0, "any": 0.0, "halt": 0.0, "n": 0, "by_kind": {}}
    step_times = []
    print(f"loop-g K={a.K} pool={a.pool} seed {a.seed}: {nparams} weights ({a.K * R.ARMS['loop']['d']} new), data ready in "
          f"{time.time() - t0:.0f}s on {device}", flush=True)
    for step in range(1, a.steps + 1):
        ts = time.time()
        net.train()
        items = src.batch(a.batch)
        t, s, y, env = R.tensors(items, device)
        total = round_rng.randint(1, R.TRAIN_ROUNDS)
        k = round_rng.randint(1, min(total, R.GRAD_ROUNDS))
        opt.zero_grad(set_to_none=True)
        with amp:
            loss, st = g_loss(net, t, s, y, env, total - k, k, serial=a.serial_streams)
        if loss is not None:
            loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        ex = st["exact_last"]                                   # [K, B], last graded round
        ce_v = st["ce"].item()
        run["ce"] += ce_v; run["halt"] += st["halt"].item(); run["n"] += 1
        run["exact"] += ex.mean().item()
        run["any"] += ex.max(0).values.mean().item()
        kind = run["by_kind"].setdefault(f"{items[0].env}{items[0].size}", [0.0, 0.0, 0, [0.0] * a.K])
        kind[0] += ex.mean().item(); kind[1] += ex.max(0).values.mean().item(); kind[2] += 1
        for j, v in enumerate(ex.mean(1).tolist()):
            kind[3][j] += v
        step_times.append(time.time() - ts)
        if step % a.log_every == 0 or step == a.steps:
            n = run["n"]
            rec = {"step": step, "ce": round(run["ce"] / n, 4), "exact": round(run["exact"] / n, 4),
                   "exact_any_stream": round(run["any"] / n, 4), "halt_bce": round(run["halt"] / n, 4),
                   "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 1),
                   "exact_by_kind": {k_: round(v[0] / v[2], 3) for k_, v in sorted(run["by_kind"].items())},
                   "exact_any_by_kind": {k_: round(v[1] / v[2], 3) for k_, v in sorted(run["by_kind"].items())},
                   "exact_stream_by_kind": {k_: [round(x / v[2], 3) for x in v[3]] for k_, v in sorted(run["by_kind"].items())}}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                rec["dev"] = {}
                for k_, v in dev.items():
                    r = g_evaluate(net, v, device)
                    rec["dev"][k_] = {"pick": r["S_pick"], "any": r["S_any"], "D": r["D_mean_distinct_answers"]}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "exact": 0.0, "any": 0.0, "halt": 0.0, "n": 0, "by_kind": {}}
    torch.save({"arm": "loop", "K": a.K, "seed": a.seed, "state": net.state_dict()}, out / "final.pt")
    warm = step_times[20:] or step_times
    summary = {"arm": "loop-g", "K": a.K, "pool": a.pool, "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": a.batch,
               "lr": a.lr, "warmup": a.warmup, "latin_pool": a.latin_pool, "start_std": a.start_std, "leak": LEAK,
               "serial_streams": a.serial_streams, "minutes": round((time.time() - t0) / 60, 1), "device": device,
               "sec_per_step_mean_after_20": round(sum(warm) / len(warm), 4),
               "peak_cuda_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if device == "cuda" else None,
               "torch": torch.__version__, "cuda": torch.version.cuda, "python": platform.python_version(),
               "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None, "autocast_cache": False,
               "steps_seen": I2._STATS["steps"], "steps_block_nograd": I2._STATS["steps_block_nograd"],
               "grad_norms": I2._STATS["grad_norms"], "start_norms": net.starts.detach().float().norm(dim=1).tolist()}
    (out / "train_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def timing(a):
    """the 200-step timing run: real training steps on the real pool with the real batch (256), K and rounds, then a projection.
    (The 200-step schedule is a short warm-up plus cosine over 200 steps; step time does not depend on it.) Writes seconds, memory and
    a few counts only; no test file is touched and no checkpoint is kept."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    ns = argparse.Namespace(seed=a.seed, out=tmp, pool=a.pool, K=a.K, start_std=a.start_std, serial_streams=a.serial_streams,
                            latin_pool=20000, lr=3e-4, warmup=1000, batch=256, steps=a.steps, log_every=a.log_every)
    s = train(ns)
    sec = s["sec_per_step_mean_after_20"]
    d = json.loads((tmp / "train_log.jsonl").read_text().splitlines()[-1])
    res = {"steps": a.steps, "K": a.K, "pool": a.pool, "serial_streams": a.serial_streams, "sec_per_step_mean_after_20": sec,
           "projected_minutes_per_net_60000_steps_alone": round(sec * 60000 / 60, 1), "peak_cuda_gb": s["peak_cuda_gb"],
           "gpu": s["gpu"], "torch": s["torch"], "cuda": s["cuda"], "steps_block_nograd": s["steps_block_nograd"],
           "start_norms": [round(x, 3) for x in s["start_norms"]], "last_log_line": d,
           "note": "projection = mean seconds per step after step 20, times 60000; one net alone on the GPU; the round count per step is random (1-16), so 200 steps is a rough mean"}
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("TIMING " + json.dumps(res))


# ---------------- selftest (V2 and friends) ----------------
def _fixed_batches():
    """8 fixed batches: sums4, grids5 and numbers4 (practice hands), 2 batches of 3, 3, 2 items ... small and CPU-cheap"""
    rs, rg, rn = random.Random(20260928), random.Random(20260929), random.Random(20260930)
    practice, _ = E.split_four(E.number_hands()[0])
    batches = []
    for i in range(3):
        batches.append([E.make_sum(rs, 4) for _ in range(4)])
    for i in range(3):
        batches.append([E.latin_item(rg, *E.make_latin_base(rg, 5)) for _ in range(4)])
    for i in range(2):
        batches.append([E.number_item(rn, h, t, s) for h, t, s in rn.sample(practice, 4)])
    return batches


def selftest():
    torch.manual_seed(0)
    dev = "cpu"
    assert torch.autocast is I2.NoCacheAutocast
    # --- V2: K = 1, start zeros == the sealed loop (logits, CE loss, halt loss) on 8 fixed batches ---
    sealed = R.Net("loop")
    g1 = GNet(1, zero_start=True)
    missing = g1.load_state_dict(sealed.state_dict(), strict=False)
    assert missing.missing_keys == ["starts"] and not missing.unexpected_keys, missing
    worst = {"logits": 0.0, "halt_logit": 0.0, "ce": 0.0, "halt_loss": 0.0}
    rr = random.Random(5)
    for items in _fixed_batches():
        t, s, y, env = R.tensors(items, dev)
        total = rr.randint(1, R.TRAIN_ROUNDS)
        k = rr.randint(1, min(total, R.GRAD_ROUNDS))
        outs_s = sealed.loop_train(t, s, env, total - k, k)
        ces, hls = [], []
        for lg, q in outs_s:                                     # the sealed loss, as claude_rsn358a_run.py:294-299
            c_, ex = R.ce_and_exact(lg, s, y)
            ces.append(c_)
            hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
        ce_s, hl_s = torch.stack(ces).mean(), torch.stack(hls).mean()
        outs_g = g1.train_rounds(t, s, env, total - k, k, [0])
        assert len(outs_g) == len(outs_s)
        for (lg_s, q_s), (lg_g, q_g) in zip(outs_s, outs_g):
            worst["logits"] = max(worst["logits"], float((lg_s - lg_g).abs().max()))
            worst["halt_logit"] = max(worst["halt_logit"], float((q_s - q_g).abs().max()))
        loss_g, st = g_loss(g1, t, s, y, env, total - k, k)
        worst["ce"] = max(worst["ce"], abs(float(ce_s) - float(st["ce"])))
        worst["halt_loss"] = max(worst["halt_loss"], abs(float(hl_s) - float(st["halt"])))
        assert abs(float(loss_g) - float(ce_s + HALT_W * hl_s)) <= 1e-5
    assert all(v <= 1e-5 for v in worst.values()), worst
    print(f"[V2] K=1 zero start vs sealed loop on 8 fixed batches: max abs diff {worst} (bar 1e-5) ok")
    # --- test-time K=1 equals the sealed test path (same rounds, preds, halt probs) ---
    items = _fixed_batches()[6]
    t, s, y, env = R.tensors(items, dev)
    p_s, q_s = sealed.eval().loop_rounds(t, s, env, 6)
    p_g, q_g = g1.eval().stream_rounds(t, s, env, 6)
    assert torch.equal(p_s, p_g[0]) and float((q_s - q_g[0]).abs().max()) <= 1e-5
    print("[V2b] K=1 stream_rounds == sealed loop_rounds (predictions equal, halt probs within 1e-5) ok")
    # --- K = 4: selection, weights, parallel == serial gradients, starts get gradient when there is no free round ---
    g4 = GNet(4, 1.0)
    g4.train()
    items = _fixed_batches()[6]
    t, s, y, env = R.tensors(items, dev)
    score = torch.tensor([[0.5, 0.2, 0.9], [0.1, 0.2, 0.3], [0.1, 0.9, 0.3], [0.7, 0.2, 0.1]])
    w = select_weights(score)
    assert w[:, 0].argmax().item() == 1 and w[:, 1].argmax().item() == 0 and w[:, 2].argmax().item() == 3, w   # ties: lowest index (item 1: 0 vs 1)
    assert abs(w.sum(0)[0].item() - (1 + 3 * LEAK)) < 1e-6
    gr = {}
    for serial in (False, True):
        for prm in g4.parameters():
            prm.grad = None
        loss, st = g_loss(g4, t, s, y, env, 2, 3, serial=serial)
        if loss is not None:
            loss.backward()
        gr[serial] = ({n: p.grad.detach().clone() for n, p in g4.named_parameters() if p.grad is not None},
                      float(st["ce"]), float(st["halt"]))
    assert abs(gr[False][1] - gr[True][1]) < 1e-5 and abs(gr[False][2] - gr[True][2]) < 1e-5, (gr[False][1:], gr[True][1:])
    diffs = {n: float((gr[False][0][n] - gr[True][0][n]).abs().max()) for n in gr[False][0] if n in gr[True][0]}
    scale = max(float(v.abs().max()) for v in gr[False][0].values())
    assert set(gr[False][0]) == set(gr[True][0]) and max(diffs.values()) <= 1e-4 * max(scale, 1.0), (max(diffs.values()), scale)
    assert "starts" not in gr[False][0], "starts must get no gradient when there are free rounds (the sealed detach)"
    for prm in g4.parameters():
        prm.grad = None
    loss, _ = g_loss(g4, t, s, y, env, 0, 3)
    loss.backward()
    assert g4.starts.grad is not None and float(g4.starts.grad.abs().sum()) > 0, "starts get gradient when n_free = 0"
    assert all(float(g4.starts.grad[k].abs().sum()) > 0 for k in range(4))
    print(f"[K4] winner weights ok (ties to the lowest index, 1 + 3 x {LEAK} per item); parallel == serial (loss diff "
          f"{abs(gr[False][1] - gr[True][1]):.1e}, max grad diff {max(diffs.values()):.1e} of scale {scale:.2f}); "
          "starts: no gradient with free rounds, gradient on all 4 without ok")
    # --- eval: pick = highest halt prob at own stop, ties lowest index; D counts distinct blank-cell answers ---
    g4.eval()
    batch = _fixed_batches()[6]
    r = g_evaluate(g4, batch, dev)
    assert r["n"] == 4 and 1.0 <= r["D_mean_distinct_answers"] <= 4.0 and sum(r["pick_hist"]) == 4, r
    assert r["S_any"] >= r["S_pick"] and r["S_any"] >= r["S_rand0"] and len(r["right_by_stream"]) == 4
    print("[eval] g_evaluate runs on 4 items: keys", sorted(r)[:5], "... ok")
    # --- weight decay group and size ---
    n_new = sum(p.numel() for n, p in g4.named_parameters() if n == "starts")
    n_base = sum(p.numel() for p in sealed.parameters())
    assert n_new == 4 * 512 and n_new / n_base < 0.0005, (n_new, n_base)
    print(f"[size] {n_new} new weights on {n_base} ({100 * n_new / n_base:.3f}%) ok")
    # --- the sealed gradient check still passes through this file's patches ---
    I2.selftest()                                              # the sealed gradient check (no block weight without gradient)
    print("selftest ok (torch", torch.__version__, "CPU fp32)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--seed", type=int, required=True); p.add_argument("--out", required=True)
    q = p
    if True:
        q.add_argument("--pool", choices=["h2", "old"], default="h2"); q.add_argument("--K", type=int, default=K_DEFAULT)
        q.add_argument("--start-std", type=float, default=START_STD); q.add_argument("--serial-streams", action="store_true")
        q.add_argument("--steps", type=int, default=60000); q.add_argument("--batch", type=int, default=256)
        q.add_argument("--lr", type=float, default=3e-4); q.add_argument("--warmup", type=int, default=1000)
        q.add_argument("--latin-pool", type=int, default=20000); q.add_argument("--log-every", type=int, default=500)
    p = sub.add_parser("eval")
    p.add_argument("--ckpt", required=True); p.add_argument("--tests", required=True); p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=None)
    p = sub.add_parser("poison"); p.add_argument("--ckpt", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("timing")
    p.add_argument("--steps", type=int, default=200); p.add_argument("--seed", type=int, default=13)
    p.add_argument("--pool", choices=["h2", "old"], default="h2"); p.add_argument("--K", type=int, default=K_DEFAULT)
    p.add_argument("--start-std", type=float, default=START_STD); p.add_argument("--serial-streams", action="store_true")
    p.add_argument("--log-every", type=int, default=50); p.add_argument("--out", default=None)
    sub.add_parser("selftest")
    sub.add_parser("check-mask")
    a = ap.parse_args()
    {"train": train, "eval": run_eval, "poison": poison, "timing": timing,
     "selftest": lambda _: selftest(), "check-mask": lambda _: I2.I.check_mask()}[a.cmd](a)


if __name__ == "__main__":
    main()
