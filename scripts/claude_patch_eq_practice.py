#!/usr/bin/env python3
"""Source practice for the patch race on the equal-practice ruler (DESIGN.md, PASSMARKS.md).

Two arms, logical seeds 0 and 1:
  patch   - claude_patch_eq_plugin.Net (sealed patch core, A/B in buffers)
  loop_ep - the ruler's loop (claude_patch_net.Net('loop'): same parameter names and shapes as
            claude_fewex_net.Net('loop'), explicit attention so second derivatives exist)

Phase 1, the ruler's qualified recipe (ADDENDUM-3, as claude_fewex_source_qualify.main):
12,000 batches of 64 sums or grids from claude_fewex_data.source_batch with RNG 7000000+seed,
torch seed = seed, AdamW 1e-3 (0.9, 0.95) decay 0.1, 200-step warm-up then cosine, clip 1.0,
1-16 rounds with gradient through the last 1-min(6, rounds), stop loss 0.5 x BCE, round RNG
9000+seed. The patch is zero throughout (as in the sealed recipe).

Phase 2, the sealed 2,000 episodes (claude-patch-20260927/EPISODE-RECIPE.md) on sums and grids
only: fresh AdamW, same settings, own 200-step warm-up and cosine over 2,000. Each episode
samples an order (A, B) of the two kinds; supports A, A, B, B (one puzzle each, all different);
then 8 B queries and 8 A queries, all different from the supports; objective = B-query loss +
A-query loss. patch: a write after each support; detach before the third write; the last two
writes are differentiated through the query losses; the patch is carried, detached, into the
next episode and never reset. loop_ep: functional SGD at lr 0.01 on each support; the first
two steps' history is detached (identity derivative kept), the last two are differentiated;
restart from the current outer weights every episode. Episode puzzles use the ruler's own
generators (sums 1-4 digits, 4x4/5x5 Latin grids with legend; one size per draw) and never
repeat an input of the ruler's source panels (SOURCE_SEED, +1 replay, +100 dev, +300 guard).
Episode data RNG 7500000+seed and episode round RNG 9500000+seed are shared by both arms,
which draw exactly six round schedules per episode in the same order, so both see identical
episodes and schedules.

Then, as the ruler: fixed depth from 8/16/32/48 on source dev SOURCE_SEED+100; guard on
SOURCE_SEED+300 (200 4-digit sums, 200 5x5 grids); the harness's one-step fp32 gradient
check. No maze is generated or scored here. fp32 CPU, no autocast.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.func import functional_call

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as FN  # noqa: E402
import claude_patch_data as PD  # noqa: E402  (fingerprint only)
import claude_patch_eq_plugin as P  # noqa: E402
import claude_patch_net as C  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

ARMS = ("patch", "loop_ep")
STEPS, EPISODES, BATCH = 12000, 2000, 64
INNER_LR = 0.01
GUARD_SEED = D.SOURCE_SEED + 300
EPISODE_DATA_SEED, EPISODE_ROUND_SEED = 7500000, 9500000
KINDS = ("sums", "grids")


def make_net(arm):
    return P.Net("loop") if arm == "patch" else C.Net("loop")


def optimizer(net, steps):
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    return opt, sched


def update(opt, sched, net, objective):
    if not torch.isfinite(objective):
        raise RuntimeError("non-finite objective")
    opt.zero_grad(set_to_none=True)
    objective.backward()
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0, error_if_nonfinite=True)
    opt.step()
    sched.step()


def outputs_loss(outputs, s, y):
    ces, hls = [], []
    for lg, q in outputs:
        c_, ex = FN.ce_and_exact(lg, s, y)
        ces.append(c_)
        hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
    return torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean()


def schedule(rr):
    total = rr.randint(1, FN.TRAIN_ROUNDS)
    grad = rr.randint(1, min(total, FN.GRAD_ROUNDS))
    return total - grad, grad


def run_loss(net, items, rr, patch=None, params=None):
    t, s, y = FN.tensors(items)
    free, grad = schedule(rr)
    if params is None:
        outs = net.loop_train(t, s, free, grad, patch)
    else:
        outs = functional_call(net, params, (t, s), dict(n_free=free, n_grad=grad, patch=None))
    return outputs_loss(outs, s, y)


def banned_inputs():
    panels = [D.old_panels(), D.replay_old(), D.old_panels(D.SOURCE_SEED + 100), D.old_panels(GUARD_SEED)]
    return {PD.fingerprint(it) for p in panels for items in p.values() for it in items}


def draw(kind, rng, n, used):
    size = rng.choice((1, 2, 3, 4)) if kind == "sums" else rng.choice((4, 5))
    out = []
    while len(out) < n:
        it = E.make_sum(rng, size) if kind == "sums" else D.latin_legend(rng, size)
        fp = PD.fingerprint(it)
        if fp in used:
            continue
        used.add(fp)
        out.append(it)
    return out


def episode_items(rng, ban):
    a, b = rng.sample(KINDS, 2)
    used = set(ban)
    supports = [draw(kind, rng, 1, used) for kind in (a, a, b, b)]
    queries = [draw(kind, rng, 8, used) for kind in (b, a)]
    return (a, b), supports, queries


def episode(arm, net, patch, ep_rng, ep_rr, ban, ops):
    """One sealed support-then-query episode; returns the objective and the (live) patch.

    Both arms draw one episode from ep_rng and exactly six round schedules from ep_rr
    (four supports, then the B and A query groups), in the same order."""
    order, supports, queries = episode_items(ep_rng, ban)
    ops["episode_orders"]["%s>%s" % order] += 1
    if arm == "patch":
        for i, items in enumerate(supports):
            if i == 2:
                patch = patch.detach()
            t, s, y = FN.tensors(items)
            free, grad = schedule(ep_rr)
            patch = net.write_support(t, s, y, patch, free, grad)
        objective = sum(run_loss(net, items, ep_rr, patch=patch) for items in queries)
        ops["support_writes"] += 4
    else:
        base = dict(net.named_parameters())
        params = dict(base)
        for i, items in enumerate(supports):
            inner = run_loss(net, items, ep_rr, params=params)
            grads = torch.autograd.grad(inner, tuple(params.values()), create_graph=i >= 2)
            params = {name: p - INNER_LR * g for (name, p), g in zip(params.items(), grads)}
            if i < 2:
                params = {name: base[name] + (p - base[name]).detach() for name, p in params.items()}
        objective = sum(run_loss(net, items, ep_rr, params=params) for items in queries)
        ops["inner_gradient_steps"] += 4
    return objective, patch


def new_ops():
    return {"supervised_updates": 0, "supervised_examples": 0, "episode_updates": 0,
            "support_examples": 0, "query_examples": 0, "support_writes": 0, "inner_gradient_steps": 0,
            "episode_orders": {"sums>grids": 0, "grids>sums": 0}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def train(arm, seed, out, steps=STEPS, episodes=EPISODES, log_every=500):
    out.mkdir(parents=True, exist_ok=True)
    ck = out / "resume.pt"
    torch.manual_seed(seed)
    net = make_net(arm)
    opt, sched = optimizer(net, steps)
    data_rng, round_rng = random.Random(7000000 + seed), random.Random(9000 + seed)
    ep_rng, ep_rr = random.Random(EPISODE_DATA_SEED + seed), random.Random(EPISODE_ROUND_SEED + seed)
    patch = net.stored_patch() if arm == "patch" else None
    ops = new_ops()
    done_sup, done_ep, prior, extra = 0, 0, 0.0, {}
    if ck.exists():
        st = torch.load(ck, map_location="cpu", weights_only=False)
        if (st["arm"], st["seed"]) != (arm, seed):
            raise RuntimeError("resume identity mismatch")
        net.load_state_dict(st["net"])
        if st["phase"] == "episodes":
            opt, sched = optimizer(net, episodes)
        opt.load_state_dict(st["opt"])
        sched.load_state_dict(st["sched"])
        data_rng.setstate(st["data_rng"]); round_rng.setstate(st["round_rng"])
        ep_rng.setstate(st["ep_rng"]); ep_rr.setstate(st["ep_rr"])
        patch = st["patch"]
        done_sup, done_ep, prior, ops, extra = st["done_sup"], st["done_ep"], st["seconds"], st["ops"], st["extra"]
    t0 = time.monotonic()

    def save_resume(phase):
        tmp = ck.with_suffix(".tmp")
        torch.save({"arm": arm, "seed": seed, "phase": phase, "net": net.state_dict(),
                    "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "data_rng": data_rng.getstate(), "round_rng": round_rng.getstate(),
                    "ep_rng": ep_rng.getstate(), "ep_rr": ep_rr.getstate(),
                    "patch": None if patch is None else patch.detach(),
                    "done_sup": done_sup, "done_ep": done_ep, "ops": ops, "extra": extra,
                    "seconds": prior + time.monotonic() - t0}, tmp)
        tmp.replace(ck)

    losses = []
    for step in range(done_sup + 1, steps + 1):
        net.train()
        items = D.source_batch(data_rng, BATCH)
        t, s, y = FN.tensors(items)
        total = round_rng.randint(1, FN.TRAIN_ROUNDS)
        k = round_rng.randint(1, min(total, FN.GRAD_ROUNDS))
        objective = outputs_loss(net.loop_train(t, s, total - k, k, patch), s, y)
        update(opt, sched, net, objective)
        losses.append(objective.item())
        ops["supervised_updates"] += 1
        ops["supervised_examples"] += len(items)
        done_sup = step
        if step % log_every == 0 or step == steps:
            save_resume("supervised")
            print(json.dumps({"phase": "supervised", "arm": arm, "seed": seed, "step": step,
                              "loss_mean_last": sum(losses) / len(losses),
                              "seconds": round(prior + time.monotonic() - t0)}), flush=True)
            losses = []
    if "after_supervised_guard" not in extra and episodes:
        # Report only: learned-stop guard counts before the episodes (no choice depends on it).
        extra["after_supervised_guard"] = guard_counts(arm, net)
        extra["after_supervised_seconds"] = prior + time.monotonic() - t0
        if done_ep == 0:
            opt, sched = optimizer(net, episodes)
        save_resume("episodes")
    ban = banned_inputs() if episodes else set()
    losses = []
    for ep in range(done_ep + 1, episodes + 1):
        net.train()
        objective, patch = episode(arm, net, patch, ep_rng, ep_rr, ban, ops)
        update(opt, sched, net, objective)
        if patch is not None:
            patch = patch.detach()
        losses.append(objective.item())
        ops["episode_updates"] += 1
        ops["support_examples"] += 4
        ops["query_examples"] += 16
        done_ep = ep
        if ep % 100 == 0 or ep == episodes:
            save_resume("episodes")
            print(json.dumps({"phase": "episodes", "arm": arm, "seed": seed, "episode": ep,
                              "loss_mean_last": sum(losses) / len(losses),
                              "seconds": round(prior + time.monotonic() - t0)}), flush=True)
            losses = []
    if arm == "patch":
        net.store_patch(patch)
    torch.save(net.state_dict(), out / "source.pt")
    return ops, extra, prior + time.monotonic() - t0


def eval_net(arm, state):
    """The net the race uses: the plug-in's patch net, or the ruler's own loop class."""
    if arm == "patch":
        B.N = P
        net = P.Net("loop")
    else:
        B.N = FN
        net = FN.Net("loop")
    net.load_state_dict(state)
    return net


def guard_counts(arm, net):
    state = {k: v.detach().clone() for k, v in net.state_dict().items()}
    ev = eval_net(arm, state)
    return {k: B.score(ev, v, 48)["right"] for k, v in D.old_panels(GUARD_SEED).items()}


def qualify(arm, seed, out, ops, extra, train_seconds):
    net = eval_net(arm, torch.load(out / "source.pt", map_location="cpu", weights_only=True))
    source_dev = D.old_panels(D.SOURCE_SEED + 100)
    fixed_counts = {str(d): sum(B.score(net, v, d)["fixed_right"] for v in source_dev.values())
                    for d in B.DEPTHS}
    fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
    old = {k: B.score(net, v, fixed_depth) for k, v in D.old_panels(GUARD_SEED).items()}
    grad = B.gradient_check(net, seed)
    result = {"arm": "loop", "design": {"patch": "clip-on patch (claude_patch_eq_plugin)",
                                        "loop_ep": "loop with episodes (claude_fewex_net loop)"}[arm],
              "practice_arm": arm, "seed": seed, "source_steps": STEPS, "source_batch": BATCH,
              "episodes": EPISODES, "source_guard_seed": GUARD_SEED,
              "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
              "parameters": sum(p.numel() for p in net.parameters()),
              "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts, "plain_lr_sweep": None,
              "gradient_check": grad, "old": old,
              "guard_pass": all(v["right"] >= 190 for v in old.values()) and grad["nonzero_all"],
              "operations": ops, "report_only": extra, "train_seconds": train_seconds,
              "device": "cpu", "dtype": "float32", "autocast": False, "torch": torch.__version__,
              "threads": torch.get_num_threads(), "finished_utc": utc(),
              "source_pt_sha256": sha(out / "source.pt")}
    if arm == "patch":
        result["patch_fro_norms"] = {"A": float(net.patch_a.norm()), "B": float(net.patch_b.norm())}
    B.dump(out / "source.json", result)
    print(json.dumps({"phase": "guard", "arm": arm, "seed": seed, "fixed_depth": fixed_depth,
                      "old": {k: v["right"] for k, v in old.items()},
                      "live": f'{grad["matrix_count"] - len(grad["missing_both"])} of {grad["matrix_count"]}',
                      "guard_pass": result["guard_pass"]}), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", choices=ARMS, required=True)
    ap.add_argument("--seed", type=int, choices=(0, 1), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    if (a.out / "source.json").exists():
        raise FileExistsError("practice already complete")
    ops, extra, seconds = train(a.arm, a.seed, a.out)
    qualify(a.arm, a.seed, a.out, ops, extra, seconds)


if __name__ == "__main__":
    main()
