"""Real-width source-initialized DEVELOPMENT experiments; not a sealed race.

Authentic source checkpoints, generated development-only panels, equal support
and maze-update schedules. No original puzzle holdout is opened. Stop-trained
arms include a dense control so a learning-rule fix is not credited to MoE.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import torch
from torch.nn import functional as F

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_fewex_net as N
import claude_fewex_data as D
import claude_rsn358a_envs as E
from sleep_moe import SleepMoE


def sync(device):
    if str(device).startswith("mps"):
        torch.mps.synchronize()


def tensor_batch(items, device):
    return tuple(x.to(device) for x in N.tensors(items))


def make_development(seed, n=64, family="maze"):
    rng = random.Random(73929000)
    panel = {"sums4": [E.make_sum(rng, 4) for _ in range(n)],
             "grids5": [D.latin_legend(rng, 5) for _ in range(n)],
             }
    banned = set()
    if family == "maze":
        for size in (9, 11):
            panel[f"mazes{size}"] = [D.unique_maze(rng, size, set(), banned) for _ in range(n)]
        make_support = lambda r, seen: D.unique_maze(r, 9, banned, seen)
        key = D.layout_key
    else:
        import breadth_dev_kinds as K
        sizes = (14, 16) if family == "graph" else (9, 10)
        for size in sizes:
            panel[f"{family}{size}"] = [K.unique_item(family, rng, size, set(), banned) for _ in range(n)]
        make_support = lambda r, seen: K.unique_item(family, r, sizes[0], banned, seen)
        key = K.item_key
    support_rng = random.Random(73939000 + seed)
    seen = set()
    support = [make_support(support_rng, seen) for _ in range(64)]
    old_rng = random.Random(73949000 + seed)
    replay = {"sums4": [E.make_sum(old_rng, 4) for _ in range(128)],
              "grids5": [D.latin_legend(old_rng, 5) for _ in range(128)]}
    assert not seen & banned
    digest = hashlib.sha256("\n".join(key(x) for x in support).encode()).hexdigest()
    return panel, support, replay, digest


@torch.no_grad()
def evaluate(net, panels, device, batch=16, cap=48):
    net.eval()
    result = {}
    for name, items in panels.items():
        hits = {"learned": 0, "fixed16": 0, "fixed32": 0, "fixed48": 0}
        used = caps = cell_hits = cell_n = 0
        sync(device)
        start = time.monotonic()
        for begin in range(0, len(items), batch):
            t, s, y = tensor_batch(items[begin:begin + batch], device)
            mask = s.reshape(s.shape[0], -1).bool()
            y = y.reshape(y.shape[0], -1)
            ps, qs = net.loop_rounds(t, s, cap)
            # Identical published rule: full prediction stable for 3 rounds,
            # learned q > .5, minimum 3 rounds. Nothing checks query answers.
            stable = (ps[:, 2:] == ps[:, 1:-1]).all(-1) & (ps[:, 1:-1] == ps[:, :-2]).all(-1)
            fire = stable & (qs[:, 2:] > .5)
            rr = torch.where(fire.any(1), fire.long().argmax(1) + 3,
                             torch.full((len(t),), cap, device=t.device))
            picked = ps[torch.arange(len(t), device=t.device), rr - 1]
            for key, pred in (("learned", picked), ("fixed16", ps[:, 15]),
                              ("fixed32", ps[:, 31]), ("fixed48", ps[:, 47])):
                if name == "sums4":
                    # Original checker permits leading zero digits with the
                    # correct numeric value; canonical target equality is a
                    # stricter training label, not the scoring definition.
                    chunk = items[begin:begin + batch]
                    rows = pred.reshape_as(t).tolist()
                    hits[key] += sum(int(E.check(it, row)) for it, row in zip(chunk, rows))
                else:
                    hits[key] += int(((pred == y) | ~mask).all(1).sum())
            cell_hits += int(((picked == y) & mask).sum())
            cell_n += int(mask.sum())
            used += int(rr.sum())
            caps += int((rr == cap).sum())
        sync(device)
        result[name] = {**hits, "n": len(items), "mean_rounds": used / len(items),
                        "cap_hits": caps, "cell_accuracy": cell_hits / cell_n,
                        "full_cap_eval_seconds": time.monotonic() - start}
    return result


def detach_halt_input(module, inputs):
    return tuple(x.detach() for x in inputs)


class Learner:
    def __init__(self, net, device, stop_loss=False, fresh=False, lr=1e-3, gradient_window=2,
                 halt_weight=.5, detach_halt=False):
        self.net, self.device, self.stop_loss, self.fresh = net, device, stop_loss, fresh
        self.opt = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad],
                                     lr=lr, weight_decay=.1, betas=(.9, .95))
        self.lr, self.steps = lr, 0
        self.gradient_window = gradient_window
        self.halt_weight = halt_weight
        if detach_halt:
            # Recalibrate stopping without forcing shared reasoning features
            # to optimize an early, overwhelmingly negative exact-solve label.
            net.halt.register_forward_pre_hook(detach_halt_input)
            if hasattr(net, "delta_halt"):
                net.delta_halt.register_forward_pre_hook(detach_halt_input)
            if getattr(net, "halt_residual", None) is not None:
                net.halt_residual.register_forward_pre_hook(detach_halt_input)
        if gradient_window != 2 and not fresh:
            raise ValueError("longer gradients require the fresh-prefix lane")
        self.losses = []
        self.day_replay = None
        self.day_replay_weight = 0.
        self.day_replay_rng = random.Random(0)
        self.anchor_every = 0

    def update(self, loss):
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite objective")
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        for group in self.opt.param_groups:
            group["lr"] = self.lr * min(1., (self.steps + 1) / 50)
        self.opt.step()
        self.steps += 1
        self.losses.append(float(loss.detach()))

    def output_loss(self, lg, q, s, y):
        ce, exact = N.ce_and_exact(lg, s, y)
        if self.stop_loss:
            ce = ce + self.halt_weight * F.binary_cross_entropy_with_logits(q.float(), exact.detach())
        if hasattr(self.net, "auxiliary"):
            ce = ce + self.net.auxiliary()
        return ce

    def maze_batch(self, items):
        self.net.train()
        t, s, y = tensor_batch(items, self.device)
        h = None
        for update in range(4):
            e, (dr, dc) = self.net.embed(t, s)
            anchored = self.anchor_every > 0 and (self.steps + 1) % self.anchor_every == 0
            if h is None or self.fresh or anchored:
                h = torch.zeros_like(e)
            # Published schedule = carry a state across 4 optimizer steps,
            # each with 3 detached rounds then 2 supervised rounds.
            # Fresh control preserves total round counts 5,10,15,20, rerunning
            # the prefix with the current parameters; extra compute is charged.
            grad = min((update + 1) * 5, 12 if anchored else self.gradient_window) if self.fresh or anchored else 2
            free = (update + 1) * 5 - grad if self.fresh or anchored else 3
            with torch.no_grad():
                for _ in range(free):
                    h = self.net.step(h, e.detach(), dr, dc)
            h = h.detach()
            losses = []
            for differentiated in range(grad):
                h = self.net.step(h, e, dr, dc)
                # Keep exactly the original last-two-round supervision while
                # varying how far its gradient can travel through the loop.
                if differentiated >= grad - 2:
                    losses.append(self.output_loss(*self.net.read(h), s, y))
            loss = torch.stack(losses).mean()
            if self.day_replay is not None and self.day_replay_weight > 0:
                old_losses = []
                for old_kind in ("sums4", "grids5"):
                    old_items = self.day_replay_rng.sample(self.day_replay[old_kind], 4)
                    ot, os, oy = tensor_batch(old_items, self.device)
                    # Replay a fresh source trajectory under current weights.
                    # Extra presentations and forward/backward work are charged.
                    old_out = self.net.loop_train(ot, os, 6, 2)
                    old_losses.append(torch.stack([self.output_loss(lg, q, os, oy)
                                                    for lg, q in old_out]).mean())
                loss = loss + self.day_replay_weight * torch.stack(old_losses).mean()
            self.update(loss)
            h = h.detach()

    def sleep(self, supports, replay, seed, steps):
        rng = random.Random(73959000 + seed)
        depth_rng = random.Random(73969000 + seed)
        for _ in range(steps):
            losses = []
            groups = (rng.sample(replay["sums4"], 4), rng.sample(replay["grids5"], 4),
                      rng.choices(supports, k=8))
            for items in groups:
                t, s, y = tensor_batch(items, self.device)
                total = depth_rng.randint(1, 16)
                grad = depth_rng.randint(1, min(total, 6))
                outs = self.net.loop_train(t, s, total - grad, grad)
                losses.append(torch.stack([self.output_loss(lg, q, s, y) for lg, q in outs]).mean())
            self.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])


def load(arm, seed, device):
    src = ROOT / f"artifacts/claude-fewex-20260927/runs/qual-loop-s{seed}/source.pt"
    net = N.Net("loop")
    net.load_state_dict(torch.load(src, map_location="cpu", weights_only=True))
    if arm.startswith("moe_counts"):
        from count_workspace import CountWorkspaceMoE
        net = CountWorkspaceMoE(net, freeze_shared="plastic" not in arm)
    elif arm.startswith("moe"):
        net = SleepMoE(net, local="symbols" if "symbols" in arm else
                       "operators" if "operators" in arm else
                       "manual" if "manual" in arm else "local" in arm,
                       freeze_shared="plastic" not in arm,
                       experts=2 if "all2" in arm else 4 if "symbols" in arm else 8, active=2)
    elif arm.startswith("adapter"):
        from fast_adapters import attach
        net = attach(net, adapt_qkv="qkv" in arm, mode="readout_only" if "readout" in arm else "adapters")
    elif arm.startswith("relation"):
        from gated_relation import attach
        net = attach(net, freeze_shared="plastic" not in arm)
    return net.to(device), src


def run(args):
    torch.set_num_threads(args.threads)
    torch.manual_seed(73979000 + args.seed)
    net, src = load(args.arm, args.seed, args.device)
    panel, supports, replay, digest = make_development(args.seed, args.panel, args.family)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    root_started = time.monotonic()
    result = {"arm": args.arm, "seed": args.seed, "source": str(src),
              "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
              "development_only": True, "official_holdout_opened": False,
              "scorer": "original checker; canonical equality for unique grid/maze and graph/rank",
              "support_sha256": digest, "support_pool": 64, "device": args.device,
              "new_family": args.family,
              "threads": args.threads, "updates_per_rung": args.updates,
              "torch_version": torch.__version__,
              "code_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                for name in ("real_screen.py", "sleep_moe.py", "fast_adapters.py",
                                             "gated_relation.py", "fast_depthwise.py",
                                             "breadth_dev_kinds.py", "relational_expert.py",
                                             "symbol_transport.py", "count_workspace.py")},
              "stored": net.weight_count(),
              "trainable": sum(p.numel() for p in net.parameters() if p.requires_grad),
              "stop_loss": args.arm != "loop_legacy" and args.halt_weight > 0,
              "halt_weight": args.halt_weight, "detach_halt": args.detach_halt,
              "fresh_prefix": "fresh" in args.arm,
              "gradient_window": args.grad,
              "day_replay_weight": args.day_replay_weight,
              "anchor_every": args.anchor_every, "eval_every": args.eval_every,
              "rungs": {}}
    if hasattr(net, "counts"):
        result["architecture_counts"] = net.counts()
    result["source_development"] = evaluate(net, panel, args.device)
    print(json.dumps({"phase": "source", "arm": args.arm, "seed": args.seed,
                      "scores": result["source_development"]}), flush=True)
    if any(result["source_development"][key]["learned"] < .95 * args.panel
           for key in ("sums4", "grids5")):
        raise RuntimeError("source qualification below 95% on independent development puzzles")
    base = copy.deepcopy(net)
    for k in args.rungs:
        learner = Learner(copy.deepcopy(base), args.device, result["stop_loss"],
                          "fresh" in args.arm, args.lr, args.grad, args.halt_weight, args.detach_halt)
        rng = random.Random(73989000 + args.seed + k)
        learner.anchor_every = args.anchor_every
        if args.day_replay_weight:
            learner.day_replay, learner.day_replay_weight = replay, args.day_replay_weight
            learner.day_replay_rng = random.Random(73999000 + args.seed + k)
        order, pos = list(range(k)), k
        sync(args.device)
        started = time.monotonic()
        frontier = []
        for batch_index in range(args.updates // 4):
            items = []
            while len(items) < 32:
                if pos == k:
                    rng.shuffle(order)
                    pos = 0
                take = min(32 - len(items), k - pos)
                items.extend(supports[j] for j in order[pos:pos + take])
                pos += take
            learner.maze_batch(items)
            if args.eval_every and learner.steps % args.eval_every == 0:
                sync(args.device)
                elapsed = time.monotonic() - started
                scores = evaluate(learner.net, panel, args.device)
                frontier.append({"updates": learner.steps, "elapsed_seconds_before_eval": elapsed,
                                 "scores": scores})
                print(json.dumps({"phase": "frontier", "arm": args.arm, "seed": args.seed,
                                  "k": k, "updates": learner.steps,
                                  "seconds": elapsed, "scores": scores}), flush=True)
            if (batch_index + 1) % 32 == 0:
                print(json.dumps({"phase": "adapt", "arm": args.arm, "seed": args.seed,
                                  "k": k, "updates": learner.steps,
                                  "loss": sum(learner.losses[-32:]) / 32,
                                  "seconds": time.monotonic() - started}), flush=True)
        sync(args.device)
        record = {"adapt_seconds": time.monotonic() - started,
                  "updates": learner.steps, "distinct_supports": k,
                  "presentations": args.updates // 4 * 32,
                  "additional_old_presentations": args.updates * 8 if args.day_replay_weight else 0,
                  "last32_loss": sum(learner.losses[-32:]) / min(32, len(learner.losses)),
                  "frontier": frontier,
                  "after_adapt": evaluate(learner.net, panel, args.device)}
        if k == max(args.rungs) and args.sleep:
            sleeper = Learner(copy.deepcopy(learner.net), args.device, result["stop_loss"],
                              False, args.lr, halt_weight=args.halt_weight,
                              detach_halt=args.detach_halt)
            sync(args.device)
            started = time.monotonic()
            sleeper.sleep(supports[:k], replay, args.seed, args.sleep)
            sync(args.device)
            record["sleep_seconds"] = time.monotonic() - started
            record["sleep_updates"] = args.sleep
            record["after_sleep"] = evaluate(sleeper.net, panel, args.device)
            torch.save(sleeper.net.state_dict(), out.with_suffix(f".k{k}.sleep.pt"))
        torch.save(learner.net.state_dict(), out.with_suffix(f".k{k}.pt"))
        result["rungs"][str(k)] = record
        result["elapsed_seconds"] = time.monotonic() - root_started
        out.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"phase": "rung_done", "arm": args.arm, "seed": args.seed,
                          "k": k, "record": record}), flush=True)
    print(json.dumps({"phase": "done", "arm": args.arm, "seed": args.seed,
                      "elapsed_seconds": result["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--family", choices=["maze", "graph", "rank"], default="maze")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--updates", type=int, default=512)
    parser.add_argument("--sleep", type=int, default=128)
    parser.add_argument("--rungs", type=int, nargs="+", default=[64])
    parser.add_argument("--panel", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--grad", type=int, choices=[2, 6, 12], default=2)
    parser.add_argument("--halt-weight", type=float, default=.5)
    parser.add_argument("--detach-halt", action="store_true")
    parser.add_argument("--day-replay-weight", type=float, default=0.)
    parser.add_argument("--anchor-every", type=int, default=0)
    parser.add_argument("--eval-every", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    assert args.updates % 4 == 0 and args.updates > 0
    assert all(1 <= k <= 64 for k in args.rungs)
    run(args)
