#!/usr/bin/env python3
"""Locked few-example baseline harness; see artifacts/claude-fewex-20260927/PROTOCOL.md.

All inference and learning use fp32 CPU, with no autocast or puzzle-kind input.
Raw JSON records and checkpoints make the one-time holdout audit reproducible.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_data as D
import claude_fewex_net as N
import claude_rsn358a_envs as E
import claude_rsn358m_maze as M

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-fewex-20260927"
SOURCE_STEPS, SOURCE_BATCH = 6000, 64
MAZE_BATCH, UPDATES = 32, 4
FEW = (1, 4, 16, 64)
STREAM = (256, 1024, 4096, 16384, 65536)
DEPTHS = (8, 16, 32, 48)
MAX_ROUNDS = 48
SLEEP_STEPS, SLEEP_BATCH = 512, 16
PLAIN_LRS = (5e-4, 1e-3, 2e-3)


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def load_model(path, arm):
    net = N.Net(arm)
    net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    return net


def exact(item, pred):
    return M.check_maze(item, pred) if item.env == "mazes" else E.check(item, pred)


@torch.no_grad()
def score(net, items, fixed_depth=48, batch=32):
    """Exact puzzle correctness, learned stop, fixed-depth control and stop usage."""
    net.eval()
    right = fixed = rounds = caps = 0
    for i in range(0, len(items), batch):
        chunk = items[i:i + batch]
        t, s, _ = N.tensors(chunk)
        h, w = t.shape[1:]
        if net.arm == "plain":
            cells, _ = net.forward(t, s)
            pred = cells[-1].argmax(-1).tolist()
            selected, forced = pred, pred
            rr = [1] * len(chunk)
        else:
            if hasattr(net, "infer_rounds"):
                ps, qs = net.infer_rounds(t, s, MAX_ROUNDS)
                ps, qs = ps.tolist(), qs.tolist()
            else:
                cells, stops = net.forward(t, s)
                if len(cells) != MAX_ROUNDS or len(stops) != MAX_ROUNDS:
                    raise ValueError("plugin must return 48 cell and stop logits")
                ps = torch.stack([x.argmax(-1) for x in cells], 1).tolist()
                qs = torch.stack([x.float().sigmoid() for x in stops], 1).tolist()
            rr = [next((r + 1 for r in range(2, MAX_ROUNDS)
                        if q[r] > .5 and p[r] == p[r - 1] == p[r - 2]), MAX_ROUNDS)
                  for p, q in zip(ps, qs)]
            selected = [p[r - 1] for p, r in zip(ps, rr)]
            forced = [p[fixed_depth - 1] for p in ps]
        for it, a, f, r in zip(chunk, selected, forced, rr):
            aa = [a[j * w:(j + 1) * w] for j in range(h)]
            ff = [f[j * w:(j + 1) * w] for j in range(h)]
            right += int(exact(it, aa))
            fixed += int(exact(it, ff))
            rounds += r
            caps += int(r == MAX_ROUNDS and net.arm == "loop")
    return {"right": right, "n": len(items), "fixed_right": fixed,
            "mean_rounds": rounds / len(items), "cap_hits": caps}


def source_scores(net, fixed_depth):
    old = D.old_panels()
    return {name: score(net, items, fixed_depth) for name, items in old.items()}


def gradient_check(net, seed):
    net.train()
    rng = random.Random(9242700 + seed)
    bad = []
    for batch in ([E.make_sum(rng, 4) for _ in range(32)],
                  [D.latin_legend(rng, 5) for _ in range(32)]):
        net.zero_grad(set_to_none=True)
        N.train_loss(net, batch, rng).backward()
        bad.append([name for name, p in net.named_parameters() if p.ndim == 2 and
                    (p.grad is None or not bool(torch.any(p.grad != 0)))])
    net.zero_grad(set_to_none=True)
    return {"matrix_count": sum(p.ndim == 2 for p in net.parameters()),
            "nonzero_all": not set(bad[0]) & set(bad[1]),
            "missing_both": sorted(set(bad[0]) & set(bad[1]))}


def source_plain_lr_sweep(net, seed):
    """Pick a learning rate from source puzzles only, before viewing any maze."""
    dev = D.old_panels(D.SOURCE_SEED + 100)
    candidates = {}
    for lr in PLAIN_LRS:
        clone = copy.deepcopy(net)
        opt = torch.optim.AdamW(clone.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        rng = random.Random(9252700 + seed)
        for _ in range(64):
            clone.train()
            loss = N.train_loss(clone, D.source_batch(rng, 32), rng)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(clone.parameters(), 1.)
            opt.step()
        vals = [score(clone, items, 1)["right"] for items in dev.values()]
        candidates[str(lr)] = vals
    chosen = max(PLAIN_LRS, key=lambda lr: (sum(candidates[str(lr)]), -lr))
    return {"chosen": chosen, "source_dev_counts": candidates}


def source_job(arm, seed, out):
    t0 = time.monotonic()
    torch.manual_seed(seed)
    rng = random.Random(7000000 + seed)
    p = N.Practice(arm, seed, SOURCE_STEPS)
    for step in range(1, SOURCE_STEPS + 1):
        p.step(D.source_batch(rng, SOURCE_BATCH))
        if step % 500 == 0:
            print(json.dumps({"phase": "source", "arm": arm, "seed": seed,
                              "step": step, "seconds": round(time.monotonic() - t0)}), flush=True)
    net = p.net
    # Fixed depth is selected on *source* dev; the holdout maze panel is untouched.
    if arm == "loop":
        old = D.old_panels(D.SOURCE_SEED + 100)
        fixed_counts = {}
        for depth in DEPTHS:
            fixed_counts[str(depth)] = sum(score(net, v, depth)["fixed_right"] for v in old.values())
        fixed_depth = max(DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
        sweep = None
    else:
        fixed_counts, fixed_depth = {}, 1
        sweep = source_plain_lr_sweep(net, seed)
    res = {"arm": arm, "seed": seed, "source_steps": SOURCE_STEPS, "source_batch": SOURCE_BATCH,
           "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
           "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts,
           "plain_lr_sweep": sweep, "gradient_check": gradient_check(net, seed),
           "old": source_scores(net, fixed_depth), "train_seconds": time.monotonic() - t0}
    out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), out / "source.pt")
    dump(out / "source.json", res)
    print(json.dumps({"phase": "source_done", "arm": arm, "seed": seed,
                      "old": {k: v["right"] for k, v in res["old"].items()},
                      "seconds": round(res["train_seconds"])}), flush=True)


class Learner:
    def __init__(self, net, lr):
        self.net = net
        self.opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))
        self.steps = 0

    def update(self, loss):
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.steps += 1

    def maze_batch(self, items):
        self.net.train()
        if self.net.arm == "plain":
            for _ in range(UPDATES):
                t, s, y = N.tensors(items)
                self.update(N.ce_and_exact(self.net.plain_forward(t, s), s, y)[0])
            return
        t, s, y = N.tensors(items)
        h = None
        for _ in range(UPDATES):
            e, (dr, dc) = self.net.embed(t, s)
            if h is None:
                h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(3):
                    h = self.net.step(h, e.detach(), dr, dc)
            h = h.detach()
            ces = []
            for _ in range(2):
                h = self.net.step(h, e, dr, dc)
                ces.append(N.ce_and_exact(self.net.read(h)[0], s, y)[0])
            self.update(torch.stack(ces).mean())  # no maze stop-head loss
            h = h.detach()

    def sleep(self, mazes, seed, old):
        rng = random.Random(9262700 + seed)
        t0 = time.monotonic()
        for _ in range(SLEEP_STEPS):
            old_a = rng.sample(old["sums4"], 4)
            old_b = rng.sample(old["grids5"], 4)
            new = rng.choices(mazes, k=8)
            losses = []
            for items in (old_a, old_b, new):
                t, s, y = N.tensors(items)
                if self.net.arm == "plain":
                    loss = N.ce_and_exact(self.net.plain_forward(t, s), s, y)[0]
                else:
                    rr = rng.randint(1, N.TRAIN_ROUNDS)
                    grad = rng.randint(1, min(rr, N.GRAD_ROUNDS))
                    loss = torch.stack([N.ce_and_exact(lg, s, y)[0]
                                        for lg, _ in self.net.loop_train(t, s, rr - grad, grad)]).mean()
                losses.append(loss)
            self.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
        return time.monotonic() - t0


def maze_scores(net, panels, fixed_depth):
    return {str(s): score(net, panels[s], fixed_depth) for s in (7, 9, 11)}


def save_stage(net, out, name):
    torch.save(net.state_dict(), out / f"{name}.pt")


def adapt_job(arm, seed, init, source_dir, out):
    t0 = time.monotonic()
    src = json.loads((source_dir / "source.json").read_text())
    if src["arm"] != arm or src["seed"] != seed:
        raise ValueError("source checkpoint identity mismatch")
    fixed_depth = src["fixed_depth"]
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    panel, banned = D.panels()
    support, support_keys = D.supports(seed, banned)
    out.mkdir(parents=True, exist_ok=True)
    if init == "pre":
        base = load_model(source_dir / "source.pt", arm)
    else:
        torch.manual_seed(900000 + seed)
        base = N.Net(arm)
    old = D.old_panels()
    old_replay = D.replay_old()
    res = {"arm": arm, "seed": seed, "init": init, "weights": base.weight_count(),
           "persistent_coefficients": base.weight_count(), "fixed_depth": fixed_depth,
           "lr": lr, "panel_layouts": {sp: {str(s): len({D.layout_key(it) for it in p[s]})
                                               for s in p} for sp, p in panel.items()},
           "support_unique_layouts": len(support_keys), "rungs": {}, "old": {}, "sleep": {}}
    res["rungs"]["0"] = maze_scores(base, panel["dev"], fixed_depth)
    res["old"]["before"] = {k: score(base, v, fixed_depth) for k, v in old.items()}
    save_stage(base, out, "k0")
    for k in FEW:
        learner = getattr(N, "Learner", Learner)(copy.deepcopy(base), lr)
        rng = random.Random(9272700 + seed + k)
        for _ in range(8):
            order = support[:k]
            rng.shuffle(order)
            for i in range(0, k, MAZE_BATCH):
                learner.maze_batch(order[i:i + MAZE_BATCH])
        net = learner.net
        res["rungs"][str(k)] = maze_scores(net, panel["dev"], fixed_depth)
        save_stage(net, out, f"k{k}")
        if k == 64:
            res["old"]["after_64"] = {a: score(net, v, fixed_depth) for a, v in old.items()}
            sleep = getattr(N, "Learner", Learner)(copy.deepcopy(net), lr)
            seconds = sleep.sleep(support, seed + 64, old_replay)
            res["sleep"]["64"] = {"seconds": seconds, "updates": sleep.steps,
                                     "old": {a: score(sleep.net, v, fixed_depth) for a, v in old.items()},
                                     "maze_dev": maze_scores(sleep.net, panel["dev"], fixed_depth)}
            save_stage(sleep.net, out, "sleep64")
        print(json.dumps({"phase": "few", "arm": arm, "seed": seed, "init": init,
                          "k": k, "right9": res["rungs"][str(k)]["9"]["right"],
                          "seconds": round(time.monotonic() - t0)}), flush=True)
    learner = getattr(N, "Learner", Learner)(copy.deepcopy(base), lr)
    seen_items = []
    source_stream = D.stream(seed, banned, support_keys)
    for batch_idx in range(STREAM[-1] // MAZE_BATCH):
        items = [next(source_stream) for _ in range(MAZE_BATCH)]
        seen_items.extend(items)
        learner.maze_batch(items)
        count = (batch_idx + 1) * MAZE_BATCH
        if count in STREAM:
            res["rungs"][str(count)] = maze_scores(learner.net, panel["dev"], fixed_depth)
            save_stage(learner.net, out, f"k{count}")
            print(json.dumps({"phase": "stream", "arm": arm, "seed": seed, "init": init,
                              "k": count, "right9": res["rungs"][str(count)]["9"]["right"],
                              "seconds": round(time.monotonic() - t0)}), flush=True)
    res["old"]["after_64k"] = {a: score(learner.net, v, fixed_depth) for a, v in old.items()}
    sleep = getattr(N, "Learner", Learner)(copy.deepcopy(learner.net), lr)
    seconds = sleep.sleep(seen_items, seed + 65536, old_replay)
    res["sleep"]["64k"] = {"seconds": seconds, "updates": sleep.steps,
                               "old": {a: score(sleep.net, v, fixed_depth) for a, v in old.items()},
                               "maze_dev": maze_scores(sleep.net, panel["dev"], fixed_depth)}
    save_stage(sleep.net, out, "sleep64k")
    res["stream_unique_layouts"] = len({D.layout_key(it) for it in seen_items})
    res["stream_panel_overlap"] = sum(D.layout_key(it) in banned for it in seen_items)
    res["stream_support_overlap"] = sum(D.layout_key(it) in support_keys for it in seen_items)
    res["optimizer_updates"] = {"stream": learner.steps, "sleep64k": sleep.steps}
    res["training_seconds"] = time.monotonic() - t0
    dump(out / "adapt.json", res)
    print(json.dumps({"phase": "adapt_done", "arm": arm, "seed": seed, "init": init,
                      "seconds": round(res["training_seconds"])}), flush=True)


def holdout_job(arm, seed, init, out):
    """Run once after every baseline and V3 decision; no training or model selection."""
    if (out / "holdout.json").exists():
        raise FileExistsError("holdout already evaluated")
    res = json.loads((out / "adapt.json").read_text())
    if (res["arm"], res["seed"], res["init"]) != (arm, seed, init):
        raise ValueError("adapt identity mismatch")
    panel, _ = D.panels()
    scores = {}
    for name in ("0",) + tuple(map(str, FEW + STREAM)) + ("sleep64", "sleep64k"):
        ckname = f"k{name}" if name[0].isdigit() else name
        net = load_model(out / f"{ckname}.pt", arm)
        scores[name] = maze_scores(net, panel["holdout"], res["fixed_depth"])
    dump(out / "holdout.json", {"arm": arm, "seed": seed, "init": init, "scores": scores})


def selftest():
    torch.set_num_threads(1)
    panel, banned = D.panels()
    support, support_keys = D.supports(0, banned)
    assert len(banned) == sum(sum(v) for v in D.PANEL_SIZES.values())
    assert len(support_keys) == 64 and not support_keys & banned
    for split in panel:
        for s, items in panel[split].items():
            assert len(items) == len({D.layout_key(x) for x in items})
            assert all(M.check_maze(x, x.target) for x in items)
    for arm in ("loop", "plain"):
        net = N.Net(arm)
        gc = gradient_check(net, 0)
        assert gc["nonzero_all"], gc
        if arm == "loop":
            assert abs(net.weight_count() - N.Net("plain").weight_count()) / net.weight_count() <= .02
    print(json.dumps({"selftest": "ok", "panel_layouts": {sp: {str(s): len(x) for s, x in p.items()}
                                                           for sp, p in panel.items()},
                      "weights": {arm: N.Net(arm).weight_count() for arm in ("loop", "plain")}}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "source", "adapt", "holdout"))
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--init", choices=("pre", "fresh"))
    p.add_argument("--out", type=Path)
    p.add_argument("--source", type=Path)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--plugin", default="claude_fewex_net",
                   help="importable model module implementing PROTOCOL.md interface")
    a = p.parse_args()
    N = importlib.import_module(a.plugin)
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "source":
        source_job(a.arm, a.seed, a.out)
    elif a.cmd == "adapt":
        adapt_job(a.arm, a.seed, a.init, a.source, a.out)
    else:
        holdout_job(a.arm, a.seed, a.init, a.out)
