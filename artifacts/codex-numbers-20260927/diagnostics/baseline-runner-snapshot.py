#!/usr/bin/env python3
"""Fixed-env rsn-358i loop baseline for the small puzzle experiment.

Only data preparation and the runner live here. The network, losses, and v2 stop
rule come from the 358i import chain. This file never calls a solver at inference.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i_run as I  # noqa: E402: installs narrow attention, legend, v2 stop

R, E = I.R, I.E
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / "artifacts/codex-numbers-20260927/cache"
ROUNDS, GRAD_ROUNDS, TEST_ROUNDS = 16, 6, 48


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def as_tuple(value):
    return tuple(as_tuple(x) for x in value) if isinstance(value, list) else value


class Source:
    """The original 358i stream, with deterministic generated pools cached on disk."""

    def __init__(self, seed, latin_pool, cache_dir=DEFAULT_CACHE):
        self.rng = random.Random(1000 + seed)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        hp = self.cache_dir / "number-hands-v1.json"
        if not hp.exists():
            four, three = E.number_hands()
            write_json(hp, {"four": four, "three": three})
        hands = json.loads(hp.read_text(encoding="utf-8"))
        self.four, self.held = E.split_four(hands["four"])
        self.three = hands["three"]
        lp = self.cache_dir / f"latin-v1-seed{seed}-pool{latin_pool}.json"
        if not lp.exists():
            latin = {str(s): [E.make_latin_base(self.rng, s) for _ in range(latin_pool)]
                     for s in E.TRAIN_SIZES["grids"]}
            write_json(lp, {"latin": latin, "rng_state": self.rng.getstate()})
        data = json.loads(lp.read_text(encoding="utf-8"))
        self.latin = {int(s): pairs for s, pairs in data["latin"].items()}
        self.rng.setstate(as_tuple(data["rng_state"]))
        self.cache_hashes = {str(hp): sha256(hp), str(lp): sha256(lp)}

    def item(self, env, size):
        if env == "sums":
            return E.make_sum(self.rng, size)
        if env == "grids":
            sol, puz = E.augment_latin(self.rng, *self.rng.choice(self.latin[size]))
            return E.latin_item(self.rng, sol, puz)
        hand, target, solution = self.rng.choice(self.four if size == 4 else self.three)
        return E.number_item(self.rng, hand, target, solution)

    def batch(self, n):
        env = self.rng.choice(E.ENVS)
        size = self.rng.choice(E.TRAIN_SIZES[env])
        return [self.item(env, size) for _ in range(n)]


def tensors(items, device):
    """Metadata kind is intentionally never read to construct a model input."""
    t = torch.tensor([it.tokens for it in items], device=device)
    s = torch.tensor([it.slot for it in items], device=device)
    y = torch.tensor([it.target for it in items], device=device)
    env = torch.zeros(len(items), dtype=torch.long, device=device)
    return t, s, y, env


def make_net(width, layers, heads, device):
    if width % heads:
        raise ValueError("width must be divisible by heads")
    R.ARMS["loop"] = dict(d=width, layers=layers, heads=heads)
    return R.Net("loop").to(device)


def amp_context(device):
    return (torch.autocast("cuda", dtype=torch.bfloat16, cache_enabled=False)
            if device == "cuda" else contextlib.nullcontext())


def resolve_device(name):
    if name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS is unavailable")
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return name


def stop_round(preds, halts):
    return next((r for r in range(2, len(preds))
                 if halts[r] > 0.5 and preds[r] == preds[r - 1] == preds[r - 2]), len(preds) - 1)


@torch.no_grad()
def predict_at_stop(net, items, device, batch=64, details=False):
    """Model output first, then checker and stored-answer accounting."""
    net.eval()
    valid = exact = 0
    records = []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        t, s, y, env = tensors(chunk, device)
        with amp_context(device):
            preds, halts = net.loop_rounds(t, s, env, TEST_ROUNDS)
        preds, halts = preds.tolist(), halts.tolist()
        mask, targets = s.view(len(chunk), -1).tolist(), y.view(len(chunk), -1).tolist()
        for j, (item, per_round, q) in enumerate(zip(chunk, preds, halts)):
            r = stop_round(per_round, q)
            chosen = per_round[r]
            grid = R.grid_of(chosen, item)
            good = bool(E.check(item, grid))
            same = all(a == b for a, b, write in zip(chosen, targets[j], mask[j]) if write)
            valid += good
            exact += same
            if details:
                records.append({"index": start + j, "kind": item.env, "size": item.size,
                                "stop": r + 1, "prediction": chosen, "valid": good,
                                "exact_stored": same})
    return {"n": len(items), "valid": valid, "exact_stored": exact,
            **({"items": records} if details else {})}


def poison_test(net, item, device):
    """All 48 logits, argmax predictions and halt values ignore metadata kind."""
    other = copy.deepcopy(item)
    other.env = next(k for k in E.ENVS if k != item.env)
    a = tensors([item], device)
    b = tensors([other], device)
    assert all(torch.equal(x, y) for x, y in zip(a, b)), "kind changed model input"
    net.eval()
    with torch.no_grad(), amp_context(device):
        def trace(args):
            t, s, _, env = args
            emb, (dr, dc) = net.embed(t, s, env)
            h = torch.zeros_like(emb)
            logits, halts = [], []
            for _ in range(TEST_ROUNDS):
                h = net.step(h, emb, dr, dc)
                lg, q = net.read(h)
                logits.append(lg)
                halts.append(q)
            return torch.stack(logits), torch.stack(halts)
        la, qa = trace(a)
        lb, qb = trace(b)
    assert torch.equal(la, lb) and torch.equal(la.argmax(-1), lb.argmax(-1)) and torch.equal(qa, qb)
    return {"rounds": TEST_ROUNDS, "logits_equal": True, "predictions_equal": True,
            "halts_equal": True}


def train(args):
    device = resolve_device(args.device)
    torch.manual_seed(args.seed)
    if device == "mps":
        torch.mps.manual_seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    source = Source(args.seed, args.latin_pool, args.cache_dir)
    net = make_net(args.width, args.layers, args.heads, device)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / args.warmup) * 0.5 *
        (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    round_rng = random.Random(9000 + args.seed)
    config = {"arm": "loop", "seed": args.seed, "steps": args.steps, "batch": args.batch,
              "width": args.width, "layers": args.layers, "heads": args.heads,
              "latin_pool": args.latin_pool, "lr": args.lr, "warmup": args.warmup,
              "train_rounds": ROUNDS, "grad_rounds": GRAD_ROUNDS, "test_rounds": TEST_ROUNDS,
              "device": device, "dtype": "bfloat16 autocast" if device == "cuda" else "float32",
              "torch": torch.__version__, "weights": nparams,
              "unused_env_rows": len(E.ENVS) - 1,
              "unused_env_weights": (len(E.ENVS) - 1) * args.width,
              "cache_hashes": source.cache_hashes,
              "script_sha256": sha256(__file__)}
    write_json(out / "config.json", config)
    totals = {"ce": 0.0, "halt": 0.0, "exact": 0.0, "n": 0, "kinds": {}}
    with open(out / "train_log.jsonl", "w", encoding="utf-8") as log:
        for step in range(1, args.steps + 1):
            net.train()
            items = source.batch(args.batch)
            t, s, y, env = tensors(items, device)
            total = round_rng.randint(1, ROUNDS)
            k = round_rng.randint(1, min(total, GRAD_ROUNDS))
            with amp_context(device):
                outputs = net.loop_train(t, s, env, total - k, k)
                ces, hls = [], []
                for logits, q in outputs:
                    ce, ex = R.ce_and_exact(logits, s, y)
                    ces.append(ce)
                    hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
                ce = torch.stack(ces).mean()
                hl = torch.stack(hls).mean()
                loss = ce + 0.5 * hl
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            sched.step()
            totals["ce"] += ce.item()
            totals["halt"] += hl.item()
            totals["exact"] += ex.mean().item()
            totals["n"] += 1
            key = f"{items[0].env}{items[0].size}"
            v = totals["kinds"].setdefault(key, [0.0, 0])
            v[0] += ex.mean().item()
            v[1] += 1
            if step % args.log_every == 0 or step == args.steps:
                n = totals["n"]
                row = {"step": step, "ce": totals["ce"] / n, "halt_bce": totals["halt"] / n,
                       "exact": totals["exact"] / n,
                       "exact_by_kind": {key: val[0] / val[1] for key, val in totals["kinds"].items()},
                       "lr": sched.get_last_lr()[0], "minutes": (time.monotonic() - started) / 60}
                log.write(json.dumps(row, sort_keys=True) + "\n")
                log.flush()
                print(json.dumps(row, sort_keys=True), flush=True)
                totals = {"ce": 0.0, "halt": 0.0, "exact": 0.0, "n": 0, "kinds": {}}
    checkpoint = out / "final.pt"
    torch.save({"config": config, "state": net.state_dict()}, checkpoint)
    write_json(out / "train_summary.json", {**config,
               "minutes": (time.monotonic() - started) / 60,
               "checkpoint_sha256": sha256(checkpoint)})


def load_checkpoint(path, device):
    device = resolve_device(device)
    data = torch.load(path, map_location=device, weights_only=False)
    cfg = data["config"]
    net = make_net(cfg["width"], cfg["layers"], cfg["heads"], device)
    net.load_state_dict(data["state"])
    return net, cfg


def read_panel(path):
    return [R.item_from_json(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def evaluate(args):
    net, config = load_checkpoint(args.ckpt, args.device)
    items = read_panel(args.panel)
    result = {"panel": str(args.panel), "panel_sha256": sha256(args.panel),
              "checkpoint": str(args.ckpt), "checkpoint_sha256": sha256(args.ckpt),
              "config": config, "scores": predict_at_stop(net, items, args.device,
                                                             args.eval_batch, args.details),
              "poison": poison_test(net, items[0], args.device) if items else None}
    write_json(args.out, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("config",)}, sort_keys=True))


def selftest():
    torch.manual_seed(1)
    net = make_net(32, 2, 8, "cpu")
    item = E.make_sum(random.Random(1), 1)
    print(json.dumps(poison_test(net, item, "cpu"), sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--steps", type=int, default=60000)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--width", type=int, default=128)
    t.add_argument("--layers", type=int, default=2)
    t.add_argument("--heads", type=int, default=8)
    t.add_argument("--seed", type=int, required=True)
    t.add_argument("--latin-pool", type=int, default=20000)
    t.add_argument("--lr", type=float, default=3e-4)
    t.add_argument("--warmup", type=int, default=1000)
    t.add_argument("--log-every", type=int, default=500)
    t.add_argument("--out", required=True)
    t.add_argument("--device", choices=("mps", "cpu", "cuda"), default="mps")
    t.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--panel", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--device", choices=("mps", "cpu", "cuda"), default="mps")
    e.add_argument("--eval-batch", type=int, default=64)
    e.add_argument("--details", action="store_true")
    sub.add_parser("selftest")
    args = p.parse_args()
    {"train": train, "eval": evaluate, "selftest": lambda _: selftest()}[args.cmd](args)


if __name__ == "__main__":
    main()
