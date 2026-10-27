#!/usr/bin/env python3
"""AR2 local runner. Do not run until PASSMARKS.md is pushed and registered."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import platform
import random
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn.functional as F

# Reuse the single unchanged AR1 model class; this nested runner owns no model copy.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from auto_model import AutoNet, PuzzleRequest, E, M, R, EXPECTED_PARAMS

REPO = HERE.parents[2]
REGISTRATION = "542f61b8c63e505ed02b881eb2216d57001ed1c7"
SEEDS = tuple(range(61, 67))
ARMS = ("baseline", "hard_grid_replay")
PHASES = ("A", "B", "C")
STEPS = (2500, 2500, 1500)
KINDS = ("grids", "sums", "mazes")
SCORE_KEY = {"grids": "grids5", "sums": "sums4", "mazes": "maze7"}
SIZE_KEYS = ("grids4", "grids5", "sums1", "sums2", "sums3", "sums4", "mazes5", "mazes7")
STOP_REQUESTED = False


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(tokens, slot):
    return hashlib.sha256(json.dumps([tokens, slot], separators=(",", ":")).encode()).hexdigest()


def encode(it):
    row = {key: getattr(it, key) for key in ("env", "size", "tokens", "slot", "target", "meta")}
    row["id"] = fingerprint(it.tokens, it.slot)
    return row


def decode(row):
    return E.Item(*(row[key] for key in ("env", "size", "tokens", "slot", "target", "meta")))


def request(row):
    # This is the entire public request. Nothing else crosses into inference.
    return PuzzleRequest(tokens=row["tokens"], slot=row["slot"])


def generate_item(rng, kind, size, pool=None):
    if kind == "grids":
        base = E.make_latin_base(rng, size) if pool is None else rng.choice(pool[size])
        item = E.latin_item(rng, *(base if pool is None else E.augment_latin(rng, *base)))
    elif kind == "sums":
        item = E.make_sum(rng, size)
    else:
        item = M.make_maze(rng, size)
    assert E.check(item, item.target), "code-generated training/panel answer failed its checker"
    return item


def panels(seed):
    path = HERE / "panels" / f"seed{seed}.json"
    if path.exists():
        data = json.loads(path.read_text())
        validate_panels(data, seed)
        return data
    final_seed, diagnostic_seed = 927206481000 + seed, 927206482000 + seed
    seen = set()
    sets, rejections = {}, {}
    for name, pseed, n in (("final", final_seed, 200), ("diagnostic", diagnostic_seed, 100)):
        rng, rows, rejected = random.Random(pseed), [], 0
        for kind, size in (("grids", 5), ("sums", 4), ("mazes", 7)):
            accepted = 0
            while accepted < n:
                row = encode(generate_item(rng, kind, size))
                if row["id"] in seen:
                    rejected += 1
                    continue
                seen.add(row["id"])
                rows.append(row)
                accepted += 1
        rng.shuffle(rows)
        sets[name], rejections[name] = rows, rejected
    data = dict(seed=seed, panel_seed=final_seed, diagnostic_seed=diagnostic_seed,
                duplicate_rejections=rejections, **sets)
    validate_panels(data, seed)
    path.parent.mkdir(exist_ok=True)
    write_json(path, data)
    return data


def validate_panels(data, seed):
    assert data["seed"] == seed
    assert data["panel_seed"] == 927206481000 + seed
    assert data["diagnostic_seed"] == 927206482000 + seed
    ids = set()
    for name, n in (("final", 200), ("diagnostic", 100)):
        rows = data[name]
        assert len(rows) == n * 3
        assert Counter(row["env"] for row in rows) == {kind: n for kind in KINDS}
        for row in rows:
            assert row["size"] == {"grids": 5, "sums": 4, "mazes": 7}[row["env"]]
            assert row["id"] == fingerprint(row["tokens"], row["slot"])
            assert row["id"] not in ids, "duplicate or cross-panel visible input"
            ids.add(row["id"])
            item = decode(row)
            assert E.check(item, item.target), "cached panel target failed checker"


def scheduled_kind(arm, phase, step):
    if arm not in ARMS or phase not in PHASES:
        raise ValueError("unknown arm or phase")
    if phase == "A":
        return "grids"
    n = 2500 if phase == "B" else 1500
    replay = 250 if phase == "B" else 150
    j, previous = step * replay // n, (step - 1) * replay // n
    if j == previous:
        return "sums" if phase == "B" else "mazes"
    if phase == "B":
        return "grids"
    return "sums" if (j * 75 + replay - 1) // replay > ((j - 1) * 75 + replay - 1) // replay else "grids"


def training_batch(rng, kind, pool, blocked, rejects, arm="baseline", phase="A", size_batches=None):
    """Consume the ordinary size draw, then override only candidate B/C grids."""
    if arm not in ARMS or phase not in PHASES:
        raise ValueError("unknown arm or phase")
    size = rng.choice({"grids": [4, 5], "sums": [1, 2, 3, 4], "mazes": M.SIZES_PRACTICE}[kind])
    if arm == "hard_grid_replay" and phase in ("B", "C") and kind == "grids":
        size = 5
    items = []
    while len(items) < 64:
        it = generate_item(rng, kind, size, pool)
        if fingerprint(it.tokens, it.slot) in blocked:
            rejects[kind] += 1
            continue
        items.append(it)
    if size_batches is not None:
        key = f"{kind}{size}"
        if key not in SIZE_KEYS:
            raise RuntimeError(f"unexpected training size: {key}")
        size_batches[key] += 1
    return tuple(torch.tensor([getattr(it, key) for it in items], device="mps", dtype=torch.long)
                 for key in ("tokens", "slot", "target"))


def infer_one(net, req):
    # A single request: no kind bucketing, neighboring items, or target tensor.
    tokens = torch.tensor([req.tokens], dtype=torch.long, device="mps")
    slots = torch.tensor([req.slot], dtype=torch.long, device="mps")
    with torch.no_grad():
        preds, qs, contexts = net.infer(tokens, slots, rounds=48)
    return {"predictions": preds[0].cpu().tolist(), "stop_probabilities": qs[0].cpu().tolist(),
            "context_probabilities": contexts[0].cpu().tolist()}


def stop_round(predictions, probabilities):
    return next((r for r in range(2, 48) if probabilities[r] > .5 and
                 predictions[r] == predictions[r - 1] == predictions[r - 2]), 47)


def score_rows(rows, predictions):
    score = {k: dict(right=0, n=0, fixed16=0, any48=0, stopping_rounds_sum=0) for k in SCORE_KEY.values()}
    for row, pred in zip(rows, predictions, strict=True):
        assert row["id"] == pred["id"]
        it = decode(row)
        p, q = pred["predictions"], pred["stop_probabilities"]
        chosen = stop_round(p, q)
        good = [bool(E.check(it, R.grid_of(tokens, it))) for tokens in p]
        out = score[SCORE_KEY[row["env"]]]
        out["n"] += 1
        out["right"] += int(good[chosen])
        out["fixed16"] += int(good[15])
        out["any48"] += int(any(good))
        out["stopping_rounds_sum"] += chosen + 1
    return score


def evaluate(net, rows, path):
    net.eval()
    requests = [(row["id"], request(row)) for row in rows]
    predictions = []
    started = time.monotonic()
    with path.open("w") as handle:
        for ident, req in requests:
            pred = dict(id=ident, **infer_one(net, req))
            predictions.append(pred)
            handle.write(json.dumps(pred, separators=(",", ":")) + "\n")
    # No oracle/checker has been consulted during the whole mixed stream.
    return score_rows(rows, predictions), predictions, (time.monotonic() - started) / 60


def integrity_controls(net, rows, checkpoint=None):
    selected = []
    for kind in KINDS:
        selected.extend([row for row in rows if row["env"] == kind][:2])
    original = {row["id"]: infer_one(net, request(row)) for row in selected}
    # Changing hidden fields cannot affect the tokens+slot request or result.
    failures = []
    for row in reversed(selected):
        poisoned = dict(row, env="POISON", size=-1, target=None, meta={"poison": True}, phase="other")
        if infer_one(net, request(poisoned)) != original[row["id"]]:
            failures.append("metadata/order invariance")
        if infer_one(net, request(row)) != original[row["id"]]:
            failures.append("repeated request invariance")
    if checkpoint:
        # Reload into the same object: no second model answers any request.
        net.load_state_dict(torch.load(checkpoint, map_location="mps", weights_only=True))
        for row in selected:
            if infer_one(net, request(row)) != original[row["id"]]:
                failures.append("save/reload invariance")
    if sum(p.numel() for p in net.parameters()) != EXPECTED_PARAMS:
        failures.append("parameter count")
    if not all(p.requires_grad for p in net.parameters()):
        failures.append("frozen parameter")
    return {"pass": not failures, "failures": failures, "requests": 6,
            "public_request_fields": [f.name for f in dataclasses.fields(PuzzleRequest)]}


def source_hashes():
    files = set(HERE.glob("*.py"))
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path:
            path = Path(path).resolve()
            if path.suffix == ".py" and path.is_relative_to(REPO) and path.is_file():
                files.add(path)
    return {str(path.relative_to(REPO)): sha(path) for path in sorted(files)}


def request_stop(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True


def run(arm, seed, resume=False):
    if REGISTRATION == "PENDING_REGISTRATION":
        raise RuntimeError("AR2 marks must be committed and pushed before any run")
    assert arm in ARMS
    assert seed in SEEDS
    assert torch.backends.mps.is_available(), "MPS required by registration"
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    out = HERE / "run" / f"{arm}-s{seed}"
    if out.exists() and not resume:
        raise RuntimeError(f"Refusing to overwrite {out}")
    out.mkdir(parents=True, exist_ok=True)
    start, started = utc(), time.monotonic()
    panel = panels(seed)
    blocked = {row["id"] for name in ("final", "diagnostic") for row in panel[name]}
    rng, rr = random.Random(5800 + seed), random.Random(5900 + seed)
    pool = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = AutoNet().to("mps")
    net.eval()
    assert sum(p.numel() for p in net.parameters()) == EXPECTED_PARAMS
    manifest = dict(start_utc=start, machine=platform.node(), architecture=platform.machine(),
                    pid=os.getpid(), command=sys.argv, registration_commit=REGISTRATION,
                    software_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                    source_hashes=source_hashes(), panel_sha256=sha(HERE / "panels" / f"seed{seed}.json"),
                    torch=torch.__version__, device="mps", precision="float32", cpu_threads=4)
    saved = None
    if resume:
        saved = torch.load(out / "interruption.pt", map_location="cpu", weights_only=False)
        assert saved["manifest"]["source_hashes"] == manifest["source_hashes"]
        assert saved["manifest"]["panel_sha256"] == manifest["panel_sha256"]
        assert saved["manifest"]["registration_commit"] == manifest["registration_commit"]
        assert saved["manifest"]["torch"] == manifest["torch"]
        net.load_state_dict(saved["model"])
        rng.setstate(saved["rng"])
        rr.setstate(saved["round_rng"])
        torch.set_rng_state(saved["torch_rng"])
        torch.mps.set_rng_state(saved["mps_rng"])
        res = saved["result"]
        res["resumes"] = res.get("resumes", []) + [manifest]
    else:
        write_json(out / "manifest.json", manifest)
        with (out / "RUN-NOTE.md").open("x") as handle:
            handle.write(f"# {arm}, seed {seed}\n\nStart (`date -u`): {start}\n\nMachine: {platform.node()} ({platform.machine()}); PID {os.getpid()}.\n\nRegistration: {REGISTRATION}\n\nSoftware: {manifest['software_commit']}\n\nCommand: `{' '.join(sys.argv)}`\n")
        res = dict(seed=seed, arm=arm, complete=False, parameters=EXPECTED_PARAMS, device="mps", precision="float32",
                   batch_size=64, software_commit=manifest["software_commit"], phases={}, minutes=0,
                   practice_panel_rejections={k: 0 for k in KINDS}, m4=integrity_controls(net, panel["final"]))
        assert res["m4"]["pass"], res["m4"]
    accumulated_minutes = res["minutes"]
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    with (out / "progress.jsonl").open("a", buffering=1) as log:
        for phase, n in zip(PHASES, STEPS):
            if phase in res["phases"]:
                continue
            opt = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.1, betas=(.9, .95))
            sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda i, n=n: min(1, (i + 1) / 100) * .5 * (1 + math.cos(math.pi * min(i, n) / n)))
            counts, size_batches, first = Counter({k: 0 for k in KINDS}), Counter({k: 0 for k in SIZE_KEYS}), 1
            training_seconds = 0.
            if saved and saved["phase"] == phase:
                opt.load_state_dict(saved["optimizer"])
                sch.load_state_dict(saved["scheduler"])
                counts, first = Counter(saved["counts"]), saved["step"] + 1
                size_batches = Counter(saved["size_batches"])
                training_seconds = saved["training_seconds"]
            for step in range(first, n + 1):
                update_started = time.monotonic()
                kind = scheduled_kind(arm, phase, step)
                tokens, slots, targets = training_batch(
                    rng, kind, pool, blocked, res["practice_panel_rejections"],
                    arm=arm, phase=phase, size_batches=size_batches)
                total = rr.randint(1, 16)
                grad = rr.randint(1, min(total, 6))
                net.train()
                losses = []
                for logits, q in net.train_rounds(tokens, slots, total - grad, grad):
                    ce, exact = R.ce_and_exact(logits, slots, targets)
                    losses.append(ce + .5 * F.binary_cross_entropy_with_logits(q.float(), exact))
                loss = torch.stack(losses).mean()
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), 1.)
                opt.step()
                sch.step()
                counts[kind] += 1
                torch.mps.synchronize()
                training_seconds += time.monotonic() - update_started
                if step % 100 == 0 or step == n:
                    row = dict(phase=phase, step=step, kind_batches=dict(counts),
                               size_batches=dict(size_batches), loss=float(loss.detach().cpu()),
                               minutes=accumulated_minutes + (time.monotonic() - started) / 60)
                    log.write(json.dumps(row) + "\n")
                    print(json.dumps(dict(arm=arm, seed=seed, **row)), flush=True)
                if STOP_REQUESTED or (HERE / "STOP").exists():
                    res["minutes"] = accumulated_minutes + (time.monotonic() - started) / 60
                    res["interrupted"] = dict(phase=phase, step=step, utc=utc())
                    torch.save(dict(model=net.state_dict(), optimizer=opt.state_dict(), scheduler=sch.state_dict(),
                                    phase=phase, step=step, counts=dict(counts),
                                    size_batches=dict(size_batches), training_seconds=training_seconds,
                                    rng=rng.getstate(), round_rng=rr.getstate(), torch_rng=torch.get_rng_state(),
                                    mps_rng=torch.mps.get_rng_state(), result=res, manifest=manifest), out / "interruption.pt")
                    write_json(out / "result.json", res)
                    return 20
            for batch_kind in KINDS:
                assert sum(size_batches[key] for key in SIZE_KEYS if key.startswith(batch_kind)) == counts[batch_kind]
            assert sum(counts.values()) == n
            if arm == "hard_grid_replay" and phase in ("B", "C"):
                assert size_batches["grids4"] == 0
                assert size_batches["grids5"] == (250 if phase == "B" else 75)
            score, predictions, eval_minutes = evaluate(net, panel["final"], out / f"{phase}.jsonl")
            res["phases"][phase] = dict(steps=n, kind_batches=dict(counts), size_batches=dict(size_batches), score=score,
                                        training_minutes=training_seconds / 60, evaluation_minutes=eval_minutes,
                                        predictions_sha256=sha(out / f"{phase}.jsonl"))
            res["minutes"] = accumulated_minutes + (time.monotonic() - started) / 60
            write_json(out / "result.json", res)
            print(json.dumps(dict(arm=arm, seed=seed, phase=phase, score=score)), flush=True)
        net.eval()
        torch.save(net.state_dict(), out / "final.pt")
        res["m4_final"] = integrity_controls(net, panel["final"], out / "final.pt")
        res["m4"]["pass"] &= res["m4_final"]["pass"]
        res["m4"]["failures"] += res["m4_final"]["failures"]
        diagnostic = [dict(id=row["id"], **infer_one(net, request(row))) for row in panel["diagnostic"]]
        with (out / "diagnostic.jsonl").open("w") as handle:
            for row in diagnostic:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        context_counts = {i: Counter({k: 0 for k in KINDS}) for i in range(4)}
        for row, pred in zip(panel["diagnostic"], diagnostic, strict=True):
            context = max(range(4), key=lambda i: pred["context_probabilities"][i])
            context_counts[context][row["env"]] += 1
        mapping = {i: max(KINDS, key=lambda k: context_counts[i][k]) for i in range(4)}
        final_predictions = [json.loads(line) for line in (out / "C.jsonl").read_text().splitlines()]
        agreement = sum(mapping[max(range(4), key=lambda i: pred["context_probabilities"][i])] == row["env"]
                        for row, pred in zip(panel["final"], final_predictions, strict=True))
        res["routing_report_only"] = dict(mapping=mapping, calibration_counts=context_counts, agreement=agreement, n=600)
        res["complete"], res["end_utc"] = True, utc()
        res["minutes"] = accumulated_minutes + (time.monotonic() - started) / 60
        res["final_sha256"] = sha(out / "final.pt")
        write_json(out / "result.json", res)
        print(json.dumps(dict(arm=arm, seed=seed, complete=True, minutes=res["minutes"])), flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS, required=True)
    ap.add_argument("--seed", type=int, choices=SEEDS, required=True)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    return run(a.arm, a.seed, a.resume)


if __name__ == "__main__":
    raise SystemExit(main())
