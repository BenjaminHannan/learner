#!/usr/bin/env python3
"""Sealed source practice only. Never imports or generates maze examples.

Commands: seal, qualify, train, all. Run with existing cached fp32 PyTorch.
The race is deliberately not enabled by this script: it requires external marks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.func import functional_call

import claude_patch_data as D
import claude_patch_net as N

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/claude-patch-20260927"
STEPS, EPISODES, BATCH = 18000, 2000, 64
SEEDS = (927401, 927402)
ARMS = ("patch", "loop", "loop_meta", "plain")


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


def device():
    return "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


def sync(dev):
    if dev == "mps":
        torch.mps.synchronize()
    elif dev == "cuda":
        torch.cuda.synchronize()


def encode(it):
    return {k: getattr(it, k) for k in ("env", "size", "tokens", "slot", "target", "meta")}


def decode(it):
    return D.E.Item(**it)


def tensors(items, dev):
    return tuple(torch.tensor([getattr(it, k) for it in items], device=dev)
                 for k in ("tokens", "slot", "target"))


def detached(patch):
    return None if patch is None else patch.detach()


def loss_outputs(outputs, s, y):
    mask = s.flatten(1).bool()
    target = y.flatten(1)
    losses = []
    for logits, halt in outputs:
        ce = F.cross_entropy(logits[mask], target[mask])
        if halt is not None:
            exact = ((logits.argmax(-1) == target) | ~mask).all(1).float()
            ce = ce + 0.5 * F.binary_cross_entropy_with_logits(halt, exact)
        losses.append(ce)
    return torch.stack(losses).mean()


def schedule(rng):
    total = rng.randint(1, 16)
    grad = rng.randint(1, min(total, 6))
    return total - grad, grad


def loss(net, items, rr, dev, patch=None, params=None):
    t, s, y = tensors(items, dev)
    free, grad = schedule(rr)
    kwargs = dict(n_free=free, n_grad=grad, patch=patch)
    outputs = net(t, s, **kwargs) if params is None else functional_call(net, params, (t, s), kwargs)
    return loss_outputs(outputs, s, y)


def optimizer(net, steps):
    opt = torch.optim.AdamW(net.parameters(), lr=0.001, betas=(0.9, 0.95), weight_decay=0.1)
    sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) *
        0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    return opt, sch


class ComputeMeter:
    """Actual forward dense-matrix multiply-add counts, excluding scalar ops.

    Backward and second derivatives are deliberately not guessed from a fixed
    multiplier. Their optimizer/inner-step counts are recorded separately.
    """
    def __init__(self, net):
        self.counts = {"linear_forward_macs": 0, "attention_forward_macs": 0,
                       "patch_forward_macs": 0, "feedback_forward_macs": 0,
                       "block_calls": 0, "block_examples": 0}
        self.handles = []
        for module in net.modules():
            if isinstance(module, torch.nn.Linear):
                self.handles.append(module.register_forward_hook(self.linear))
            if isinstance(module, N.Block):
                self.handles.append(module.register_forward_hook(self.block))
        if net.arm == "patch":
            self.handles.append(net.gate.register_forward_hook(self.patch))

    def patch(self, module, args, output):
        b, t, _ = args[0].shape
        self.counts["patch_forward_macs"] += 2 * b * t * N.WIDTH * N.RANK

    def linear(self, module, args, output):
        self.counts["linear_forward_macs"] += output.numel() * module.in_features

    def block(self, module, args, output):
        b, t, d = args[0].shape
        self.counts["attention_forward_macs"] += 2 * b * t * t * d
        self.counts["block_calls"] += 1
        self.counts["block_examples"] += b

    def close(self):
        for handle in self.handles:
            handle.remove()


def update(opt, sch, objective, net):
    opt.zero_grad(set_to_none=True)
    if not torch.isfinite(objective):
        raise RuntimeError("non-finite objective; no continuation authorized")
    objective.backward()
    norm = torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0, error_if_nonfinite=True)
    opt.step()
    sch.step()
    return float(norm)


def read_panels(out):
    raw = json.loads((out / "PANELS.json").read_text())
    panels = {split: {kind: [decode(it) for it in items] for kind, items in kinds.items()}
              for split, kinds in raw.items()}
    ban = {D.fingerprint(it) for kinds in panels.values() for items in kinds.values() for it in items}
    return panels, ban


def verify_seal(out):
    sealed = json.loads((out / "CANDIDATE-SEAL.json").read_text())
    for rel, digest in sealed["files"].items():
        if sha(ROOT / rel) != digest:
            raise RuntimeError(f"seal mismatch: {rel}; no training permitted")
    return sealed


def seal(out):
    if (out / "CANDIDATE-SEAL.json").exists():
        verify_seal(out)
        return
    checks = json.loads((out / "checks.json").read_text())
    if not checks.get("passed", False):
        raise RuntimeError("construction checks must pass before sealing")
    panels = {"dev": {}, "verify": {}}
    for i, kind in enumerate(D.KINDS):
        first = D.panel(kind, 92731000 + i, 300)
        second = D.panel(kind, 92732000 + i, 300, exclude={D.fingerprint(it) for it in first})
        panels["dev"][kind] = [encode(it) for it in first]
        panels["verify"][kind] = [encode(it) for it in second]
    save(out / "PANELS.json", panels)
    # Freeze every code dependency that can change practice. Independent
    # recount/report tools do not affect examples, optimization, or predictions.
    files = [ROOT / "scripts" / f"claude_patch_{name}.py" for name in ("data", "net", "practice", "checks")]
    files += [ROOT / "scripts" / name for name in D.generator_hashes()]
    files += [out / "EPISODE-RECIPE.md", out / "PANELS.json", out / "checks.json"]
    generator_sources = D.generator_hashes()
    kind_hashes = {kind: hashlib.sha256(json.dumps({"kind": kind, "sources": generator_sources},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest() for kind in D.KINDS}
    save(out / "CANDIDATE-SEAL.json", {
        "utc": utc(), "kinds": list(D.KINDS), "qualification_steps": STEPS,
        "batch": BATCH, "episode_steps": EPISODES, "seeds": SEEDS,
        "files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))},
        "generator_hashes": generator_sources, "kind_generator_sha256": kind_hashes,
        "kind_hash_definition": "SHA256 of canonical JSON {kind, sources}; sources covers complete generator and imported dependency code",
        "torch": torch.__version__,
        "device": device(), "dtype": "float32", "autocast": False,
    })


@torch.no_grad()
def evaluate(net, panels, dev, patch, raw_path):
    net.eval()
    result = {}
    with raw_path.open("w") as raw:
        for kind, items in panels.items():
            count, rounds, fixed = 0, [], {r: 0 for r in (4, 8, 16, 32, 48)}
            sync(dev)
            started = time.perf_counter()
            for start in range(0, len(items), 20):
                chunk = items[start:start + 20]
                t, s, _ = tensors(chunk, dev)
                if net.arm == "plain":
                    preds = net(t, s)[0][0].argmax(-1).unsqueeze(1).cpu().tolist()
                    qs = [[1.0] for _ in chunk]
                else:
                    p, q = net.loop_rounds(t, s, 48, patch=patch)
                    preds, qs = p.cpu().tolist(), q.cpu().tolist()
                for it, pred, q in zip(chunk, preds, qs):
                    stop = 0 if net.arm == "plain" else next((r for r in range(2, 48)
                        if q[r] > 0.5 and pred[r] == pred[r-1] == pred[r-2]), 47)
                    right = bool(D.check(it, pred[stop]))
                    count += right
                    rounds.append(stop + 1)
                    fp = {str(r): pred[min(r - 1, len(pred) - 1)] for r in fixed}
                    for r in fixed:
                        fixed[r] += D.check(it, fp[str(r)])
                    raw.write(json.dumps({"kind": kind, "input": encode(it), "fingerprint": D.fingerprint(it),
                        "pred": pred[stop], "right": right, "round": stop + 1,
                        "fixed_pred": fp}) + "\n")
            sync(dev)
            result[kind] = {"right": count, "n": len(items), "mean_rounds": sum(rounds) / len(rounds),
                "cap_hits": sum(r == 48 for r in rounds), "fixed_right": fixed,
                "seconds_full_depth_evaluation": time.perf_counter() - started}
    return result


@torch.no_grad()
def inference_timing(net, panels, dev, patch, path):
    """Batch-one end-to-end forward latency, physically stopping at the halt.

    No answers are read here. The first 30 sealed verification inputs per kind
    are fixed before training; results are timing-only, not another accuracy set.
    """
    net.eval()
    rows = []
    for kind, items in panels.items():
        for it in items[:30]:
            t = torch.tensor([it.tokens], device=dev)
            s = torch.tensor([it.slot], device=dev)
            sync(dev)
            start = time.perf_counter()
            if net.arm == "plain":
                net.plain_forward(t, s).argmax(-1)
                used = 1
            else:
                emb, (dr, dc) = net.embed(t, s)
                h = torch.zeros_like(emb)
                history = []
                for used in range(1, 49):
                    h = net.step(h, emb, dr, dc, patch)
                    logits, halt = net.read(h)
                    history.append(logits.argmax(-1))
                    if used >= 3 and float(halt.sigmoid()) > 0.5 and \
                            torch.equal(history[-1], history[-2]) and torch.equal(history[-1], history[-3]):
                        break
            sync(dev)
            rows.append({"kind": kind, "fingerprint": D.fingerprint(it), "rounds": used,
                         "seconds": time.perf_counter() - start})
    save(path, {"batch_size": 1, "includes_host_halt_decisions": True, "rows": rows})
    return {kind: {"n": sum(row["kind"] == kind for row in rows),
                   "mean_seconds": sum(row["seconds"] for row in rows if row["kind"] == kind) / 30}
            for kind in panels}


def train_source(arm, seed, kinds, panels, ban, runout, dev):
    if (runout / "result.json").exists():
        return json.loads((runout / "result.json").read_text())
    runout.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    net = N.Net("loop" if arm in ("pilot", "loop_meta") else arm).to(dev).float()
    patch = net.zero_patch() if arm == "patch" else None
    rng, rr = random.Random(seed + 10000), random.Random(seed + 20000)
    opt, sch = optimizer(net, STEPS)
    meter = ComputeMeter(net)
    sync(dev)
    started = time.perf_counter()
    log = (runout / "train.jsonl").open("a", buffering=1)
    operations = {"supervised_optimizer_steps": 0, "episode_optimizer_steps": 0,
        "supervised_examples": 0, "support_examples": 0, "query_examples": 0,
        "support_writes": 0, "inner_gradient_steps": 0}
    source_done, episode_done, prior_seconds = 0, 0, 0.0
    progress = runout / "progress.pt"
    if progress.exists():
        # This file is our own local checkpoint, not external model input.
        state = torch.load(progress, map_location=dev, weights_only=False)
        if state["arm"] != arm or state["seed"] != seed:
            raise RuntimeError("checkpoint identity mismatch")
        net.load_state_dict(state["state"])
        patch = state["patch"]
        source_done, episode_done = state["source_done"], state["episode_done"]
        if state["phase"] == "episodes":
            opt, sch = optimizer(net, EPISODES)
        opt.load_state_dict(state["optimizer"])
        sch.load_state_dict(state["scheduler"])
        rng.setstate(state["rng"])
        rr.setstate(state["round_rng"])
        operations = state["operations"]
        meter.counts = state["matrix_operations"]
        prior_seconds = state["training_seconds"]

    def checkpoint(phase, source_done, episode_done):
        sync(dev)
        tmp = progress.with_suffix(".tmp")
        torch.save({"state": net.state_dict(), "patch": detached(patch),
            "source_done": source_done, "episode_done": episode_done, "phase": phase,
            "arm": arm, "seed": seed, "optimizer": opt.state_dict(), "scheduler": sch.state_dict(),
            "rng": rng.getstate(), "round_rng": rr.getstate(), "operations": operations,
            "matrix_operations": meter.counts,
            "training_seconds": prior_seconds + time.perf_counter() - started}, tmp)
        tmp.replace(progress)

    for step in range(source_done + 1, STEPS + 1):
        net.train()
        kind = rng.choice(kinds)
        items = D.batch(kind, rng, BATCH, exclude=ban)
        objective = loss(net, items, rr, dev, patch)
        update(opt, sch, objective, net)
        operations["supervised_optimizer_steps"] += 1
        operations["supervised_examples"] += len(items)
        if step % 250 == 0:
            rec = {"phase": "source", "step": step, "loss": float(objective.detach()),
                   "elapsed_seconds": time.perf_counter() - started}
            log.write(json.dumps(rec) + "\n")
            print(json.dumps(rec), flush=True)
        if step % 1000 == 0:
            checkpoint("source", step, 0)
    if arm != "pilot":
        if episode_done == 0:
            opt, sch = optimizer(net, EPISODES)
        for episode in range(episode_done + 1, EPISODES + 1):
            old, new = rng.sample(list(kinds), 2)
            used = set(ban)
            supports = []
            for kind in (old, old, new, new):
                it = D.batch(kind, rng, 1, exclude=used)
                used.add(D.fingerprint(it[0]))
                supports.append(it)
            queries = []
            for kind in (new, old):
                items = D.batch(kind, rng, 8, exclude=used)
                used.update(D.fingerprint(it) for it in items)
                queries.append(items)
            net.train()
            if arm == "patch":
                for i, items in enumerate(supports):
                    if i == 2:
                        patch = detached(patch)
                    t, s, y = tensors(items, dev)
                    free, grad = schedule(rr)
                    patch = net.write_support(t, s, y, patch, n_free=free, n_grad=grad)
                    meter.counts["feedback_forward_macs"] += t.numel() * D.VOCAB * N.WIDTH
                objective = sum(loss(net, items, rr, dev, patch) for items in queries)
                operations["support_writes"] += 4
            elif arm in ("loop_meta", "plain"):
                base = dict(net.named_parameters())
                params = dict(base)
                for i, items in enumerate(supports):
                    inner = loss(net, items, rr, dev, params=params)
                    grads = torch.autograd.grad(inner, tuple(params.values()), create_graph=i >= 2)
                    params = {name: p - 0.01 * g for (name, p), g in zip(params.items(), grads)}
                    if i < 2:
                        params = {name: base[name] + (p - base[name]).detach() for name, p in params.items()}
                objective = sum(loss(net, items, rr, dev, params=params) for items in queries)
                operations["inner_gradient_steps"] += 4
            else:
                # Same evidence; ordinary reference receives supervised practice.
                objective = torch.stack([loss(net, items, rr, dev) for items in supports + queries]).mean()
            update(opt, sch, objective, net)
            patch = detached(patch)
            operations["episode_optimizer_steps"] += 1
            operations["support_examples"] += 4
            operations["query_examples"] += 16
            if episode % 100 == 0:
                rec = {"phase": "episodes", "step": episode, "loss": float(objective.detach()),
                       "elapsed_seconds": time.perf_counter() - started}
                log.write(json.dumps(rec) + "\n")
                print(json.dumps(rec), flush=True)
                checkpoint("episodes", STEPS, episode)
    sync(dev)
    seconds = prior_seconds + time.perf_counter() - started
    meter.close()
    log.close()
    torch.save({"state": net.state_dict(), "patch": patch, "arm": arm, "seed": seed}, runout / "final.pt")
    if arm == "patch":
        subprocess.run([sys.executable, "-B", str(ROOT / "scripts/claude_patch_checks.py"),
            "--device", dev, "--checkpoint", str(runout / "final.pt"),
            "--out", str(runout / "trained-checks.json")], check=True)
    result = {"utc": utc(), "arm": arm, "seed": seed, "torch": torch.__version__, "device": dev,
        "dtype": "float32", "autocast": False, "training_seconds": seconds, "operations": operations,
        "matrix_operations": meter.counts,
        "operation_note": "Forward matrix multiply-adds only; excludes elementwise ops and backward/second derivatives. Optimizer and inner-step counts recorded separately.",
        "dev": evaluate(net, {k: panels["dev"][k] for k in kinds}, dev, patch, runout / "dev-raw.jsonl")}
    result["fixed_depth"] = max((4, 8, 16, 32, 48), key=lambda r:
        sum(row["fixed_right"][r] for row in result["dev"].values()))
    if arm != "pilot":
        result["verify"] = evaluate(net, {k: panels["verify"][k] for k in kinds}, dev, patch, runout / "verify-raw.jsonl")
        result["inference_timing"] = inference_timing(net, {k: panels["verify"][k] for k in kinds},
            dev, patch, runout / "inference-timing.json")
    save(runout / "result.json", result)
    return result


def qualify(out, dev):
    verify_seal(out)
    panels, ban = read_panels(out)
    result = train_source("pilot", 927301, D.KINDS, panels, ban, out / "qualification", dev)
    retained = [k for k, row in result["dev"].items() if row["right"] >= (285 if k in ("sums", "grids") else 270)]
    eligible = all(k in retained for k in ("sums", "grids")) and len(retained) >= 6
    record = {"utc": utc(), "eligible": eligible, "kinds": retained,
        "dropped": [k for k in D.KINDS if k not in retained], "counts": result["dev"],
        "candidate_seal": sha(out / "CANDIDATE-SEAL.json"),
        "raw_sha256": sha(out / "qualification/dev-raw.jsonl")}
    save(out / "QUALIFIED-SEAL.json", record)
    return record


def train_all(out, dev):
    verify_seal(out)
    q = json.loads((out / "QUALIFIED-SEAL.json").read_text())
    if q["candidate_seal"] != sha(out / "CANDIDATE-SEAL.json") or \
            q["raw_sha256"] != sha(out / "qualification/dev-raw.jsonl"):
        raise RuntimeError("qualification provenance hash mismatch")
    counts = {k: {"right": 0, "n": 0} for k in D.KINDS}
    for line in (out / "qualification/dev-raw.jsonl").read_text().splitlines():
        row = json.loads(line)
        counts[row["kind"]]["n"] += 1
        counts[row["kind"]]["right"] += D.check(decode(row["input"]), row["pred"])
    if any(row["n"] != 300 or row["right"] != q["counts"][k]["right"] for k, row in counts.items()):
        raise RuntimeError("qualification raw recount mismatch")
    retained = [k for k, row in counts.items() if row["right"] >= (285 if k in ("sums", "grids") else 270)]
    eligible = all(k in retained for k in ("sums", "grids")) and len(retained) >= 6
    if retained != q["kinds"] or eligible != q["eligible"]:
        raise RuntimeError("qualification seal contradicts registered marks")
    if not eligible:
        raise RuntimeError("qualification failed; no arm training or race")
    panels, ban = read_panels(out)
    for seed in SEEDS:
        for arm in ARMS:
            train_source(arm, seed, q["kinds"], panels, ban, out / f"{arm}-{seed}", dev)
    gates = {}
    for seed in SEEDS:
        paired = {arm: json.loads((out / f"{arm}-{seed}/result.json").read_text()) for arm in ARMS}
        absolute = {arm: {k: row["right"] >= (285 if k in ("sums", "grids") else 270)
            for k, row in r["verify"].items()} for arm, r in paired.items()}
        gap = {control: {k: paired["patch"]["verify"][k]["right"] >=
               paired[control]["verify"][k]["right"] - 9 for k in q["kinds"]}
               for control in ("loop", "loop_meta")}
        gates[str(seed)] = {"absolute": absolute, "patch_within_three_points": gap,
            "passed": all(all(v.values()) for v in absolute.values()) and all(all(v.values()) for v in gap.values())}
    save(out / "PRACTICE-GATES.json", {"utc": utc(), "seeds": gates, "passed": all(r["passed"] for r in gates.values())})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("seal", "qualify", "train", "all"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    torch.set_num_threads(4)
    try:
        save(args.out / "STATUS.json", {"utc": utc(), "status": "running", "command": args.command,
                                      "pid": os.getpid(), "device": device()})
        if args.command in ("seal", "all"):
            seal(args.out)
        if args.command in ("qualify", "all"):
            q = qualify(args.out, device())
            if not q["eligible"]:
                save(args.out / "STATUS.json", {"utc": utc(), "status": "qualification_failed", "race_run": False})
                print("Qualification failed; see QUALIFIED-SEAL.json. Race not run.", flush=True)
                return
        if args.command in ("train", "all"):
            train_all(args.out, device())
        save(args.out / "STATUS.json", {"utc": utc(), "status": "completed_" + args.command, "race_run": False})
    except Exception as exc:
        save(args.out / "STATUS.json", {"utc": utc(), "status": "failed", "error": repr(exc), "race_run": False})
        raise


if __name__ == "__main__":
    main()
