#!/usr/bin/env python3
"""Fixed-env rsn-358i loop baseline and learned-card candidate runner.

The inherited core, task losses and v2 stop rule come from the 358i import chain.
The candidate adds only the episode-local scratch card module. Neither variant
calls a solver at inference.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
import math
import os
import random
import struct
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i_run as I  # noqa: E402: installs narrow attention, legend, v2 stop
import codex_numbers_20260927_cards as C  # noqa: E402

R, E = I.R, I.E
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / "artifacts/codex-numbers-20260927/cache"
ROUNDS, GRAD_ROUNDS, TEST_ROUNDS = 16, 6, 48


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes(variant="baseline"):
    """Record the actual imported recipe, including its solver-backed data source."""
    modules = {"rsn358i": I, "rsn358g": I.G, "rsn358a2": I.G.V,
               "rsn358a": R, "rsn358a_envs": E, "blurt1": E.B1,
               "scratch_cards": C}
    return {name: sha256(module.__file__) for name, module in modules.items()}


def state_hash(net, core_only=False):
    """Stable hash over names, shapes, dtypes and exact initial tensor bytes."""
    digest = hashlib.sha256()
    for name, tensor in sorted(net.state_dict().items()):
        if core_only and name.startswith("cards."):
            continue
        digest.update(json.dumps([name, list(tensor.shape), str(tensor.dtype)]).encode())
        raw = tensor.detach().cpu().contiguous().view(torch.uint8).flatten().tolist()
        digest.update(bytes(raw))
    return digest.hexdigest()


def update_stream_hash(digest, items, n_free, n_grad):
    """Hash every exact input and target token plus the sampled round schedule."""
    h, w = len(items[0].tokens), len(items[0].tokens[0])
    digest.update(struct.pack("<IIIII", len(items), h, w, n_free, n_grad))
    for item in items:
        for grid in (item.tokens, item.slot, item.target):
            digest.update(bytes(v for row in grid for v in row))


class GradientAudit:
    def __init__(self, net, device, every=2500):
        self.net, self.every = net, every
        self.mats = [(name, p) for name, p in net.named_parameters()
                     if name.startswith("blocks.") and name.endswith(".weight") and p.ndim == 2]
        self.steps = self.missing = 0
        self.allzero = torch.zeros((), dtype=torch.int64, device=device)
        self.nograd = torch.zeros((), dtype=torch.int64, device=device)
        self.norms = []
        self.card_params = [(name, p) for name, p in net.named_parameters() if name.startswith("cards.")]
        self.card_multi_steps = 0
        self.card_single_steps = 0
        self.card_multi_nograd = torch.zeros((), dtype=torch.int64, device=device)
        self.card_norms = []
        self.card_counts = {name: {"missing_steps": 0,
                                   "finite_steps": torch.zeros((), dtype=torch.int64, device=device),
                                   "nonfinite_steps": torch.zeros((), dtype=torch.int64, device=device),
                                   "nonfinite_any_step": torch.zeros((), dtype=torch.int64, device=device),
                                   "nonzero_steps": torch.zeros((), dtype=torch.int64, device=device),
                                   "zero_steps": torch.zeros((), dtype=torch.int64, device=device)}
                            for name, _ in self.card_params}

    def check(self, n_grad=None):
        self.steps += 1
        present = [(name, p.grad.detach()) for name, p in self.mats if p.grad is not None]
        missing = len(self.mats) != len(present)
        self.missing += int(missing)
        if present:
            sums = torch.stack([grad.abs().sum() for _, grad in present])
            zero = sums.eq(0).any()
            self.allzero += zero
            self.nograd += zero | missing
        elif missing:
            self.nograd += 1
        if self.steps == 1 or self.steps % self.every == 0:
            per_block = {}
            for name, grad in present:
                key = f"block{name.split('.')[1]}"
                per_block.setdefault(key, []).append(grad.float().square().sum())
            self.norms.append({"step": self.steps, **{
                key: torch.stack(parts).sum().sqrt().item() for key, parts in per_block.items()}})
        if self.card_params:
            if n_grad == 1:
                self.card_single_steps += 1
                for name, p in self.card_params:
                    if p.grad is not None:
                        self.card_counts[name]["nonfinite_any_step"] += ~torch.isfinite(p.grad.detach()).all()
            if n_grad is not None and n_grad >= 2:
                self.card_multi_steps += 1
                card_grads = [p.grad for _, p in self.card_params]
                missing_card = any(g is None for g in card_grads)
                present_card = [g.detach().abs().sum() for g in card_grads if g is not None]
                zero_card = torch.stack(present_card).eq(0).any() if present_card else True
                self.card_multi_nograd += zero_card | missing_card
                for name, p in self.card_params:
                    counts = self.card_counts[name]
                    if p.grad is None:
                        counts["missing_steps"] += 1
                        continue
                    grad = p.grad.detach()
                    finite = torch.isfinite(grad).all()
                    nonzero = grad.abs().sum().gt(0)
                    counts["finite_steps"] += finite
                    counts["nonfinite_steps"] += ~finite
                    counts["nonfinite_any_step"] += ~finite
                    counts["nonzero_steps"] += nonzero & finite
                    counts["zero_steps"] += ~nonzero & finite
            if self.steps % 100 == 0:
                self.raise_on_nonfinite()
            if self.steps == 1 or self.steps % self.every == 0:
                self.card_norms.append({"step": self.steps, **{
                    name.removeprefix("cards."): 0.0 if p.grad is None else p.grad.detach().float().norm().item()
                    for name, p in self.card_params}})

    def raise_on_nonfinite(self):
        if any(int(c["nonfinite_any_step"].item()) for c in self.card_counts.values()):
            raise FloatingPointError("nonfinite card gradient detected")

    def report(self):
        self.raise_on_nonfinite()
        return {"steps_seen": self.steps, "block_linear_matrices": len(self.mats),
                "steps_block_missing": self.missing, "steps_block_allzero": int(self.allzero.item()),
                "steps_block_nograd": int(self.nograd.item()),
                "grad_norms": self.norms,
                "card_gradient_check": {
                    "parameters": len(self.card_params), "multi_grad_steps": self.card_multi_steps,
                    "single_grad_steps_exempt": self.card_single_steps,
                    "multi_grad_steps_nograd": int(self.card_multi_nograd.item()),
                    "per_parameter_counts": {name.removeprefix("cards."): {
                        key: value if isinstance(value, int) else int(value.item())
                        for key, value in counts.items()}
                        for name, counts in self.card_counts.items()},
                    "per_parameter_norms": self.card_norms}}


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

    def __init__(self, seed, latin_pool, cache_dir=DEFAULT_CACHE, dev_holdout=0, dev_seed=9276601):
        self.rng = random.Random(1000 + seed)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        hp = self.cache_dir / "number-hands-v1.json"
        if not hp.exists():
            four, three = E.number_hands()
            write_json(hp, {"four": four, "three": three})
        hands = json.loads(hp.read_text(encoding="utf-8"))
        self.four, _ = E.split_four(hands["four"])
        self.dev_four = []
        if dev_holdout:
            if not 0 < dev_holdout < len(self.four):
                raise ValueError("dev_holdout must be between 1 and the practice pool size minus 1")
            indices = list(range(len(self.four)))
            random.Random(dev_seed).shuffle(indices)
            selected = set(indices[:dev_holdout])
            self.dev_four = [row for i, row in enumerate(self.four) if i in selected]
            self.four = [row for i, row in enumerate(self.four) if i not in selected]
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


class CardNet(R.Net):
    def __init__(self):
        super().__init__("loop")
        self.cards = C.CardScratchpad(R.ARMS["loop"]["d"])


def make_net(width, layers, heads, device, variant="baseline"):
    if width % heads:
        raise ValueError("width must be divisible by heads")
    if variant not in ("baseline", "candidate"):
        raise ValueError(f"unknown variant {variant}")
    R.ARMS["loop"] = dict(d=width, layers=layers, heads=heads)
    return (CardNet() if variant == "candidate" else R.Net("loop")).to(device)


def _step_state(net, h, e, dr, dc, card_state, wipe_cards=False):
    if isinstance(net, CardNet):
        return net.cards.step(net, h, e, dr, dc, card_state, wipe_cards)
    return net.step(h, e, dr, dc), None


def run_train(net, tokens, slot, env, n_free, n_grad):
    """One state machine for both variants, preserving truncated free rounds."""
    e, (dr, dc) = net.embed(tokens, slot, env)
    h = torch.zeros_like(e)
    cards = net.cards.initial_state(e.shape[0], e.shape[1], e) if isinstance(net, CardNet) else None
    with torch.no_grad():
        for _ in range(n_free):
            h, cards = _step_state(net, h, e.detach(), dr, dc, cards)
    h = h.detach()
    if cards is not None:
        cards = tuple(x.detach() for x in cards)
    outputs = []
    for _ in range(n_grad):
        h, cards = _step_state(net, h, e, dr, dc, cards)
        outputs.append(net.read(h))
    return outputs


def run_trace(net, tokens, slot, env, rounds=TEST_ROUNDS, wipe_cards=False):
    """Return raw full-round logits and halt logits through the actual card path."""
    e, (dr, dc) = net.embed(tokens, slot, env)
    h = torch.zeros_like(e)
    cards = net.cards.initial_state(e.shape[0], e.shape[1], e) if isinstance(net, CardNet) else None
    logits, halts = [], []
    for _ in range(rounds):
        h, cards = _step_state(net, h, e, dr, dc, cards, wipe_cards)
        lg, q = net.read(h)
        logits.append(lg)
        halts.append(q)
    return torch.stack(logits, dim=1), torch.stack(halts, dim=1)


def amp_context(device):
    return (torch.autocast("cuda", dtype=torch.bfloat16, cache_enabled=False)
            if device == "cuda" else contextlib.nullcontext())


def resolve_device(name):
    if name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS is unavailable")
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return name


def peak_mps_memory(device):
    if device != "mps":
        return {"peak_mps_allocated_bytes": None, "peak_mps_memory_status": "not_mps"}
    if not hasattr(torch.mps, "max_memory_allocated"):
        return {"peak_mps_allocated_bytes": None,
                "peak_mps_memory_status": "unavailable_in_torch"}
    return {"peak_mps_allocated_bytes": int(torch.mps.max_memory_allocated()),
            "peak_mps_memory_status": "measured"}


def stop_round(preds, halts):
    return next((r for r in range(2, len(preds))
                 if halts[r] > 0.5 and preds[r] == preds[r - 1] == preds[r - 2]), len(preds) - 1)


@torch.no_grad()
def predict_at_stop(net, items, device, batch=64, details=False, wipe_cards=False):
    """Model output first, then checker and stored-answer accounting."""
    net.eval()
    valid = exact = 0
    records = []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        t, s, y, env = tensors(chunk, device)
        with amp_context(device):
            logits, raw_halts = run_trace(net, t, s, env, TEST_ROUNDS, wipe_cards)
            preds = logits.argmax(dim=-1)
            halts = torch.stack([torch.sigmoid(q.float()) for q in raw_halts.unbind(1)], dim=1)
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
                                "exact_stored": same,
                                "round_predictions": per_round,
                                "round_halt_probabilities": q,
                                "round_halts": q})
    return {"n": len(items), "valid": valid, "exact_stored": exact,
            **({"items": records} if details else {})}


def poison_test(net, item, device, wipe_cards=False):
    """All 48 logits, argmax predictions and raw halts ignore every metadata kind."""
    a = tensors([item], device)
    net.eval()
    with torch.no_grad(), amp_context(device):
        la, qa = run_trace(net, a[0], a[1], a[3], TEST_ROUNDS, wipe_cards)
        for kind in E.ENVS:
            other = copy.deepcopy(item)
            other.env = kind
            b = tensors([other], device)
            assert all(torch.equal(x, y) for x, y in zip(a, b)), "kind changed model input"
            lb, qb = run_trace(net, b[0], b[1], b[3], TEST_ROUNDS, wipe_cards)
            assert torch.equal(la, lb) and torch.equal(la.argmax(-1), lb.argmax(-1)) and torch.equal(qa, qb)
    return {"rounds": TEST_ROUNDS, "tested_kinds": E.ENVS,
            "logits_equal": True, "predictions_equal": True, "raw_halts_equal": True}


def train(args):
    device = resolve_device(args.device)
    if device == "mps" and hasattr(torch.mps, "reset_peak_memory_stats"):
        torch.mps.reset_peak_memory_stats()
    torch.manual_seed(args.seed)
    if device == "mps":
        torch.mps.manual_seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    source = Source(args.seed, args.latin_pool, args.cache_dir, args.dev_holdout, args.dev_seed)
    diagnostics = make_diagnostic_panels(source, args, out)
    net = make_net(args.width, args.layers, args.heads, device, args.variant)
    init_hash = state_hash(net)
    base_init_hash = state_hash(net, core_only=True)
    gradient_audit = GradientAudit(net, device)
    stream_digest = hashlib.sha256()
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / args.warmup) * 0.5 *
        (1 + math.cos(math.pi * min(i, args.steps) / args.steps)))
    round_rng = random.Random(9000 + args.seed)
    config = {"arm": "loop", "variant": args.variant,
              "seed": args.seed, "steps": args.steps, "batch": args.batch,
              "width": args.width, "layers": args.layers, "heads": args.heads,
              "latin_pool": args.latin_pool, "lr": args.lr, "warmup": args.warmup,
              "log_every": args.log_every,
              "train_rounds": ROUNDS, "grad_rounds": GRAD_ROUNDS, "test_rounds": TEST_ROUNDS,
              "device": device, "dtype": "bfloat16 autocast" if device == "cuda" else "float32",
              "torch": torch.__version__, "weights": nparams,
              "unused_env_rows": len(E.ENVS) - 1,
              "unused_env_weights": (len(E.ENVS) - 1) * args.width,
              "fixed_env": 0,
              "cache_hashes": source.cache_hashes,
              "dev_holdout": args.dev_holdout,
              "dev_seed": args.dev_seed if args.dev_holdout else None,
              "probe_every": args.probe_every if args.dev_holdout else None,
              "diagnostic_panel_sha256": diagnostics[1] if diagnostics else None,
              "devsplit_manifest_sha256": sha256(out / "devsplit_manifest.json") if diagnostics else None,
              "source_hashes": source_hashes(args.variant),
              "init_state_sha256": init_hash,
              "base_init_state_sha256": base_init_hash,
              "card_weights": C.extra_weights(args.width) if args.variant == "candidate" else 0,
              "autocast_cache_enabled": False if device == "cuda" else None,
              "script_sha256": sha256(__file__)}
    write_json(out / "config.json", config)
    totals = {"ce": 0.0, "halt": 0.0, "exact": 0.0, "n": 0, "kinds": {}}
    last_probe = None
    if diagnostics:
        (out / "probe_log.jsonl").write_text("", encoding="utf-8")
    with open(out / "train_log.jsonl", "w", encoding="utf-8") as log:
        for step in range(1, args.steps + 1):
            net.train()
            items = source.batch(args.batch)
            t, s, y, env = tensors(items, device)
            total = round_rng.randint(1, ROUNDS)
            k = round_rng.randint(1, min(total, GRAD_ROUNDS))
            update_stream_hash(stream_digest, items, total - k, k)
            with amp_context(device):
                outputs = run_train(net, t, s, env, total - k, k)
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
            gradient_audit.check(k)
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
            if diagnostics and (step % args.probe_every == 0 or step == args.steps):
                probe_start = time.monotonic()
                panels, _ = diagnostics
                scores = {name: predict_at_stop(net, rows, device, args.probe_batch)
                          for name, rows in panels.items()}
                probe = {"step": step, "scores": scores,
                         "minutes": (time.monotonic() - probe_start) / 60}
                last_probe = probe
                with open(out / "probe_log.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(probe, sort_keys=True) + "\n")
                print("probe " + json.dumps(probe, sort_keys=True), flush=True)
                # Recoverable local diagnostic snapshot; never selects a test answer.
                temporary = out / "latest-resume.tmp.pt"
                torch.save({"config": config, "step": step, "state": net.state_dict(),
                            "optimizer": opt.state_dict(), "scheduler": sched.state_dict(),
                            "source_rng": source.rng.getstate(), "round_rng": round_rng.getstate(),
                            "torch_rng": torch.get_rng_state(),
                            "mps_rng": torch.mps.get_rng_state() if device == "mps" else None,
                            "elapsed_minutes": (time.monotonic()-started)/60,
                            "stream_sha256_prefix": stream_digest.hexdigest(),
                            "probe": probe}, temporary)
                os.replace(temporary, out / "latest-resume.pt")
    config["stream_sha256"] = stream_digest.hexdigest()
    write_json(out / "config.json", config)
    gradient_report = gradient_audit.report()
    checkpoint = out / "final.pt"
    torch.save({"config": config, "state": net.state_dict()}, checkpoint)
    write_json(out / "train_summary.json", {**config,
               "minutes": (time.monotonic() - started) / 60,
               "gradient_check": gradient_report,
               **peak_mps_memory(device),
               "final_probe": last_probe,
               "diagnostic_gate_met": (last_probe["scores"]["train_numbers4"]["exact_stored"] /
                                       last_probe["scores"]["train_numbers4"]["n"] >= 0.95)
                                      if last_probe else None,
               "checkpoint_sha256": sha256(checkpoint)})


def load_checkpoint(path, device):
    device = resolve_device(device)
    data = torch.load(path, map_location=device, weights_only=False)
    cfg = data["config"]
    net = make_net(cfg["width"], cfg["layers"], cfg["heads"], device,
                   cfg.get("variant", "baseline"))
    net.load_state_dict(data["state"])
    return net, cfg


def read_panel(path):
    return [R.item_from_json(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def save_panel(path, items):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(R.item_to_json(item), sort_keys=True) + "\n" for item in items),
                    encoding="utf-8")
    return sha256(path)


def make_diagnostic_panels(source, args, out):
    """Only the original 1,062 practice hands participate in this dev split."""
    if not args.dev_holdout:
        return None
    train_rng, dev_rng = random.Random(args.dev_seed + 1), random.Random(args.dev_seed + 2)
    panels = {
        "train_numbers4": [E.number_item(train_rng, *row) for row in source.four],
        "dev_numbers4": [E.number_item(dev_rng, *row) for row in source.dev_four],
        "dev_sums4": [E.make_sum(random.Random(args.dev_sums_seed + i), 4) for i in range(200)],
    }
    grid_rng = random.Random(args.dev_grids_seed)
    panels["dev_grids5"] = [E.latin_item(grid_rng, *E.make_latin_base(grid_rng, 5)) for _ in range(200)]
    hashes = {name: save_panel(out / "diagnostic-panels" / f"{name}.jsonl", rows)
              for name, rows in panels.items()}
    train_keys = {tuple(row[0]) for row in source.four}
    dev_keys = {tuple(row[0]) for row in source.dev_four}
    assert train_keys.isdisjoint(dev_keys)
    manifest = {"dev_seed": args.dev_seed, "dev_holdout": args.dev_holdout,
                "dev_sums_seed": args.dev_sums_seed, "dev_grids_seed": args.dev_grids_seed,
                "train_four_count": len(source.four), "dev_four_count": len(source.dev_four),
                "train_four_hands": [row[0] for row in source.four],
                "dev_four_hands": [row[0] for row in source.dev_four],
                "panel_sha256": hashes, "practice_cache_sha256": next(
                    v for k, v in source.cache_hashes.items() if k.endswith("number-hands-v1.json"))}
    write_json(out / "devsplit_manifest.json", manifest)
    return panels, hashes


def evaluate(args):
    started = time.monotonic()
    net, config = load_checkpoint(args.ckpt, args.device)
    items = read_panel(args.panel)
    result = {"panel": str(args.panel), "panel_sha256": sha256(args.panel),
              "checkpoint": str(args.ckpt), "checkpoint_sha256": sha256(args.ckpt),
              "config": config, "scores": predict_at_stop(net, items, args.device,
                                                             args.eval_batch, args.details,
                                                             args.wipe_cards),
              "poison": poison_test(net, items[0], args.device, args.wipe_cards) if items else None,
              "wipe_cards": args.wipe_cards,
              "eval_minutes": (time.monotonic() - started) / 60}
    write_json(args.out, result)
    compact = {k: v for k, v in result.items() if k not in ("config", "scores")}
    compact["scores"] = {k: v for k, v in result["scores"].items() if k != "items"}
    print(json.dumps(compact, sort_keys=True))


def selftest():
    torch.manual_seed(1)
    large_base = make_net(256, 2, 8, "cpu", "baseline")
    torch.manual_seed(1)
    large_card = make_net(256, 2, 8, "cpu", "candidate")
    base_count = sum(p.numel() for p in large_base.parameters())
    card_count = sum(p.numel() for p in large_card.parameters())
    assert (base_count, card_count) == (1646494, 1659424)
    assert state_hash(large_base) == state_hash(large_card, core_only=True)
    del large_base, large_card

    torch.manual_seed(2)
    base = make_net(32, 2, 8, "cpu", "baseline")
    torch.manual_seed(2)
    card = make_net(32, 2, 8, "cpu", "candidate")
    item = E.make_sum(random.Random(1), 1)
    other = E.make_sum(random.Random(2), 1)
    t, s, y, env = tensors([item], "cpu")
    base.eval(); card.eval()
    inherited_train = base.loop_train(t, s, env, 3, 2)
    runner_train = run_train(base, t, s, env, 3, 2)
    assert all(torch.equal(a, b) and torch.equal(aq, bq)
               for (a, aq), (b, bq) in zip(inherited_train, runner_train)), "baseline train path drifted"
    with torch.no_grad():
        plain_logits, plain_halts = run_trace(base, t, s, env)
        inherited_preds, inherited_probs = base.loop_rounds(t, s, env, TEST_ROUNDS)
        assert torch.equal(plain_logits.argmax(-1), inherited_preds)
        assert torch.equal(torch.stack([torch.sigmoid(q.float()) for q in plain_halts.unbind(1)], dim=1),
                           inherited_probs)
        wiped_logits, wiped_halts = run_trace(card, t, s, env, wipe_cards=True)
        assert torch.equal(plain_logits, wiped_logits) and torch.equal(plain_halts, wiped_halts)
        intact1 = run_trace(card, t, s, env)
        intact2 = run_trace(card, t, s, env)
        assert all(torch.equal(a, b) for a, b in zip(intact1, intact2)), "card state leaked between calls"
        tb, sb, _, eb = tensors([item, other], "cpu")
        batch_logits, batch_halts = run_trace(card, tb, sb, eb, rounds=4)
        single_logits, single_halts = run_trace(card, t, s, env, rounds=4)
        assert torch.allclose(batch_logits[:1], single_logits, atol=1e-6, rtol=1e-5)
        assert torch.allclose(batch_halts[:1], single_halts, atol=1e-6, rtol=1e-5)
    poison = poison_test(card, item, "cpu")
    poison_wiped = poison_test(card, item, "cpu", wipe_cards=True)

    card.train()
    outputs = run_train(card, t, s, env, 2, 3)
    loss = sum(R.ce_and_exact(lg, s, y)[0] + q.float().mean() for lg, q in outputs)
    loss.backward()
    assert all(p.grad is not None and bool(p.grad.abs().sum())
               for name, p in card.named_parameters() if name.startswith("cards."))
    assert all(p.grad is not None and bool(p.grad.abs().sum())
               for name, p in card.named_parameters() if name.startswith("blocks.") and p.ndim == 2)

    blob = io.BytesIO()
    torch.save({"config": {"width": 32, "layers": 2, "heads": 8, "variant": "candidate"},
                "state": card.state_dict()}, blob)
    blob.seek(0)
    saved = torch.load(blob, map_location="cpu", weights_only=False)
    restored = make_net(32, 2, 8, "cpu", saved["config"]["variant"])
    restored.load_state_dict(saved["state"])
    restored.eval()
    with torch.no_grad():
        assert all(torch.equal(a, b) for a, b in
                   zip(run_trace(card, t, s, env, rounds=4), run_trace(restored, t, s, env, rounds=4)))
    print(json.dumps({"baseline_weights": base_count, "candidate_weights": card_count,
                      "core_init_equal": True, "inherited_baseline_equal": True,
                      "wipe_equals_same_core": True,
                      "card_and_core_gradients": True, "reset_and_batch_independence": True,
                      "reload_equal": True, "poison": poison, "poison_wiped": poison_wiped}, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--steps", type=int, default=60000)
    t.add_argument("--variant", choices=("baseline", "candidate"), default="baseline")
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
    t.add_argument("--dev-holdout", type=int, default=0)
    t.add_argument("--dev-seed", type=int, default=9276601)
    t.add_argument("--dev-sums-seed", type=int, default=9276611)
    t.add_argument("--dev-grids-seed", type=int, default=9276621)
    t.add_argument("--probe-every", type=int, default=5000)
    t.add_argument("--probe-batch", type=int, default=64)
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--panel", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--device", choices=("mps", "cpu", "cuda"), default="mps")
    e.add_argument("--eval-batch", type=int, default=64)
    e.add_argument("--details", action="store_true")
    e.add_argument("--wipe-cards", action="store_true")
    sub.add_parser("selftest")
    args = p.parse_args()
    {"train": train, "eval": evaluate, "selftest": lambda _: selftest()}[args.cmd](args)


if __name__ == "__main__":
    main()
