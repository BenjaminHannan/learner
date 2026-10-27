"""Milestone 3 (run m03-20260919-071009): memory-card writer controls and the optional H1 paired objective.

Declared diagnostic on the synthetic-vocabulary toy ladder (premonition/toy_ladder.py; exception to the v2-tokenizer
rule), legacy toy label-free rule, supplied gold-evidence cards / evidence-supervised L_ask where stated (privileged).
full_verdict: false. Local CPU. ONE hard ledger of 1800 s for everything this milestone executes: tests, data,
reuse checks, calibration, training, evaluation, probes, test scoring, failures.

Stage 1, a separately switchable WRITER (premonition/card_pools.py):
  original  one learned softmax pool per line (D)
  mean      uniform mean of the SAME contextual reader states over the SAME line positions (no learned pool)
  two       separate key and value pools (pool_value starts as a copy of pool)
  answer     answer-only supplied-card choosing, nothink+qread, 600 gold-only of 2000 steps: original vs mean.
             A separate key pool is unused by the decoder there, so it is not an arm.
  retrieval  evidence-supervised retrieval, D-card-bypass reader, top-1, no teacher distractors, max 4 loops, D's
             default curriculum and every loss: original vs mean vs two. The ORIGINAL arm's FLOP fit and budget
             drive every arm's curriculum and stop, so examples, phases and updates are identical.
Stage 2, a separately switchable OBJECTIVE (default off): H1 on verified triplets (premonition/ladder_triplets.py,
premonition/paired_objectives.py); grouped CE vs grouped CE + H1 on IDENTICAL triplet minibatches and card orders,
fine-tuned from the selected answer checkpoint, only if the predeclared gate (GATE) passes.

Reused (not rerun): answer-original-s0 = overnight exp1 nothink+qread-s0-cur600-2000; retrieval-original-s0 =
overnight exp2 bypass-k1-s0-1500 (same frozen code path; `reuse` replays their first logged steps).

    PY -B scripts/premonition_pool_controls.py freeze | data | reuse | gate | compare | summary
    PY -B scripts/premonition_pool_controls.py check --tests tests.test_premonition_card_pools ...
    PY -B scripts/premonition_pool_controls.py answer --writer mean --seed 0
    PY -B scripts/premonition_pool_controls.py retrieval --writer two --seed 0
    PY -B scripts/premonition_pool_controls.py eval --ckpt answer-mean-s0
    PY -B scripts/premonition_pool_controls.py h1 --seed 0 --objective h1
    PY -B scripts/premonition_pool_controls.py test --ckpt answer-mean-s0
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = "m03-20260919-071009"
OUT = ROOT / "artifacts" / f"opus-{RUN}"
ARCHIVE = ROOT / "archive" / f"opus-{RUN}"
OVN = "ovn-20260918-235851"
OVN_OUT = ROOT / "artifacts" / f"opus-{OVN}"
OVN_ARCHIVE = ROOT / "archive" / f"opus-{OVN}"
CAP_SECONDS = 1800.0
NEW_MODULES = ("premonition/card_pools.py", "premonition/ladder_triplets.py", "premonition/paired_objectives.py")
HARNESSES = ("scripts/premonition_ovn_ladder.py", "scripts/premonition_ovn_retrieval.py",
             "scripts/premonition_pool_controls.py")
THREADS = 8

ANSWER = {"steps": 2000, "gold_steps": 600, "lr": 1e-3, "warmup": 100, "eval_every": 400, "eval_batches": 4,
          "estimate_seconds": 165.0}
RETRIEVAL = {"arm": "bypass-k1", "steps": 1500, "lr": 1e-3, "warmup": 100, "gold_until": 0.05,
             "teacher_until": 0.30, "ramp_until": 0.60, "estimate_seconds": 245.0}
H1_RUN = {"steps": 600, "per_batch": 5, "lr": 1e-3, "warmup": 100, "js_weight": 1.0, "margin_weight": 1.0,
          "margin": 1.0, "estimate_seconds": 70.0}
TRIPLET_SEEDS = {"train": 2101, "validation": 2202, "test": 2303}
TRIPLETS_EVAL = 256
TRIPLETS_EVAL_BATCH = 8
REUSED = {"answer-original-s0": ("answer", OVN_OUT / "exp1", "nothink+qread-s0-cur600-2000"),
          "retrieval-original-s0": ("retrieval", OVN_OUT / "exp2", "bypass-k1-s0-1500")}
# Predeclared (2026-09-19 07:1x, before any milestone-3 training): H1 trains only if, for the selected answer writer
# (higher mean validation choose:one_hop over the screened seeds), on EVERY screened seed: gold-only 1-hop reading
# >= 486/512, and the one-sided 99% visit-clustered lower bound of 1-hop choosing exceeds the best measured
# question-blind shortcut (0.5371, overnight manifest) -- i.e. person AND relation are behaviourally used -- and on
# at least one seed choosing is still below 0.95.
GATE = {"reading_one_hop_min": 486, "choose_lower_bound_above": 0.5371, "choose_point_below_on_some_seed": 0.95,
        "alpha": 0.01, "resamples": 10000}
L = R = None                     # overnight harness modules (imported after bootstrap)


# ----------------------------------------------------------------------------- identity, ledger
def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger_rows() -> list:
    path = OUT / "ledger.jsonl"
    return [] if not path.exists() else [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def ledger_seconds() -> float:
    return sum(row["seconds"] for row in ledger_rows())


def ledger_add(kind: str, name: str, seconds: float, **extra) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    row = {"kind": kind, "name": name, "seconds": round(seconds, 2),
           "at": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "command": " ".join(sys.argv[1:]), **extra}
    with (OUT / "ledger.jsonl").open("a") as handle:
        handle.write(json.dumps(row) + "\n")


def require(estimate: float, reserve: float = 30.0) -> float:
    """Refuse to start work that cannot finish under the cap; returns the seconds left before the reserve."""
    left = CAP_SECONDS - ledger_seconds() - reserve
    if left < estimate:
        raise SystemExit(f"refused: needs ~{estimate:.0f} s, only {left:.0f} s left before the {reserve:.0f} s reserve"
                         f" (ledger {ledger_seconds():.1f} / {CAP_SECONDS:.0f} s)")
    return left


def freeze() -> None:
    """archive/opus-<RUN>/frozen = the overnight frozen snapshot (byte-identical, so reused original arms keep
    their code path) + the milestone's new modules + the harnesses; FROZEN.SHA256SUMS over all of it."""
    bad = [name for digest, name in (line.split(None, 1) for line in
                                     (OVN_ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines())
           if sha256(OVN_ARCHIVE / "frozen" / name) != digest]
    if bad:
        raise SystemExit(f"overnight snapshot changed: {bad}")
    frozen = ARCHIVE / "frozen"
    if frozen.exists():
        shutil.rmtree(frozen)
    shutil.copytree(OVN_ARCHIVE / "frozen", frozen)
    for rel in NEW_MODULES + HARNESSES:
        (frozen / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, frozen / rel)
    for rel in HARNESSES[:2]:
        if sha256(ROOT / rel) != sha256(OVN_ARCHIVE / "scripts" / Path(rel).name):
            raise SystemExit(f"{rel} differs from the overnight archive copy")
    names = sorted(str(p.relative_to(frozen)) for p in frozen.rglob("*") if p.is_file())
    (ARCHIVE / "FROZEN.SHA256SUMS").write_text("".join(f"{sha256(frozen / n)}  ./{n}\n" for n in names))
    live_diff = [n for n in names if (ROOT / n).exists() and sha256(ROOT / n) != sha256(frozen / n)]
    (ARCHIVE / "FROZEN-NOTES.json").write_text(json.dumps({
        "run": RUN, "files": len(names), "base": f"archive/opus-{OVN}/frozen (byte-identical copy)",
        "added": list(NEW_MODULES + HARNESSES), "live_differs_from_frozen": live_diff,
        "note": "live_differs_from_frozen lists files another worker changed after the overnight freeze; the "
                "frozen (overnight) bytes are what every milestone-3 command imports"}, indent=1))
    print(f"frozen {len(names)} files; live differs: {live_diff}")


def bootstrap() -> None:
    global L, R
    frozen = ARCHIVE / "frozen"
    sums = (ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines()
    bad = [name for digest, name in (line.split(None, 1) for line in sums) if sha256(frozen / name) != digest]
    if bad:
        raise SystemExit(f"frozen source changed: {bad}")
    for rel in NEW_MODULES + HARNESSES:
        if sha256(ROOT / rel) != sha256(frozen / rel):
            raise SystemExit(f"live {rel} differs from the frozen copy: re-freeze (and journal it) first")
    sys.path.insert(0, str(frozen))
    import premonition
    import learnlab
    for module in (premonition, learnlab):
        if not Path(module.__file__).resolve().is_relative_to(frozen.resolve()):
            raise SystemExit(f"{module.__name__} imported from {module.__file__}")
    sys.path.insert(1, str(ROOT / "scripts"))
    import premonition_ovn_ladder as ladder
    import premonition_ovn_retrieval as retrieval
    L, R = ladder, retrieval
    import torch
    torch.set_num_threads(THREADS)


# ----------------------------------------------------------------------------- models
def answer_config():
    from premonition.config import MiniConfig
    return MiniConfig.preset("D", "tiny", vocab_size=L.spec().vocab_size, window=64)


def model_class(kind: str, writer: str):
    from premonition import answer_path, card_pools, ovn_qread
    if kind == "answer":
        if writer == "original":
            return ovn_qread.QReadMini
        if writer == "mean":
            return type("MeanPoolQReadMini", (ovn_qread.QReadMixin, card_pools.MeanPoolMini),
                        {"variant_name": "D+qread+mean-pool"})
        raise SystemExit("answer-only arms are original and mean (a separate key pool is unused by the decoder)")
    return {"original": answer_path.CardBypassMini, "mean": card_pools.MeanPoolBypassMini,
            "two": card_pools.TwoPoolBypassMini}[writer]


def config_for(kind: str):
    return answer_config() if kind == "answer" else R.config_for(RETRIEVAL["arm"])


def build(kind: str, writer: str, seed: int):
    """The overnight construction order (seeded base, then the variant class, then base weights), so the original
    writer is bit-identical to L.build / R.build and every writer shares its initial weights and random stream."""
    import torch
    from premonition.model import PremonitionMini
    config = config_for(kind)
    torch.manual_seed(seed)
    base = PremonitionMini(config)
    model = model_class(kind, writer)(config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if unexpected or not set(missing) <= {"writer.pool_value.weight", "writer.pool_value.bias"}:
        raise RuntimeError(f"{kind}/{writer}: state mismatch {missing} {unexpected}")
    if writer == "two":
        model.writer.pool_value.load_state_dict(model.writer.pool.state_dict())
    model._nothink = kind == "answer"
    return model


def arm_string(kind: str, writer: str) -> str:
    base = "nothink+qread" if kind == "answer" else RETRIEVAL["arm"]
    return base if writer == "original" else f"{base}+{writer}pool"


def identity(kind: str, writer: str, model) -> dict:
    from premonition import card_pools
    ident = {"kind": kind, "writer": writer, "arm": arm_string(kind, writer), "class": type(model).__name__,
             "purpose": "diagnostic", "privilege": ("supplied gold-evidence cards" if kind == "answer" else
                                                    "L_ask trained on oracle evidence lines (as D)"),
             "vocabulary": "toy synthetic ids (declared exception to the v2 tokenizer rule)",
             "label_free": "premonition.train.label_free (legacy toy rule)",
             "parameters_allocated": sum(p.numel() for p in model.parameters())}
    if writer != "original":
        variant = {("answer", "mean"): card_pools.MEAN_POOL, ("retrieval", "mean"): card_pools.MEAN_POOL_BYPASS,
                   ("retrieval", "two"): card_pools.TWO_POOL_BYPASS}[(kind, writer)]
        ident["writer_identity"] = card_pools.identity(variant, model.config)
    if writer == "mean":
        ident["parameters_unused"] = sum(p.numel() for p in model.writer.pool.parameters())
    return ident


def ckpt_file(name: str) -> Path:
    if name in REUSED:
        kind, folder, stem = REUSED[name]
        return folder / "ckpt" / f"{stem}.pt"
    return OUT / "ckpt" / f"{name}.pt"


def save(name: str, model, kind: str, writer: str, seed: int, **extra) -> Path:
    import torch
    path = OUT / "ckpt" / f"{name}.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "kind": kind, "writer": writer,
                "seed": seed, "identity": identity(kind, writer, model), **extra}, path)
    return path


def load(name: str):
    import torch
    from premonition.config import MiniConfig
    path = ckpt_file(name)
    blob = torch.load(path, weights_only=False)
    if name in REUSED:
        kind, writer = REUSED[name][0], "original"
    else:
        kind, writer = blob["kind"], blob["writer"]
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    if asdict(config) != asdict(config_for(kind)):
        raise SystemExit(f"{name}: checkpoint config differs from the {kind} protocol")
    model = model_class(kind, writer)(config)
    model.load_state_dict(blob["state_dict"])
    model._nothink = kind == "answer"
    model.eval()
    return model, {"kind": kind, "writer": writer, "seed": blob.get("seed"), "sha256": sha256(path),
                   "file": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
                   "reused": name in REUSED}


# ----------------------------------------------------------------------------- statistics
def cluster_bootstrap(values, clusters, *, resamples: int = 10000, alpha: float = 0.01, seed: int = 0) -> dict:
    """Mean of `values` with one-sided (1 - alpha) bounds from a bootstrap over whole clusters (visits/triplets)."""
    import torch
    values, clusters = torch.as_tensor(values, dtype=torch.float64), torch.as_tensor(clusters)
    ids, inverse = torch.unique(clusters, return_inverse=True)
    sums = torch.zeros(len(ids), dtype=torch.float64).index_add_(0, inverse, values)
    counts = torch.zeros(len(ids), dtype=torch.float64).index_add_(0, inverse, torch.ones_like(values))
    pick = torch.randint(len(ids), (resamples, len(ids)), generator=torch.Generator().manual_seed(seed))
    stats = sums[pick].sum(1) / counts[pick].sum(1)
    return {"point": round(float(values.mean()), 4), "lower": round(float(torch.quantile(stats, alpha)), 4),
            "upper": round(float(torch.quantile(stats, 1 - alpha)), 4), "clusters": len(ids), "items": len(values),
            "one_sided": 1 - alpha}


def paired_bootstrap(a, b, clusters, **kw) -> dict:
    """Mean of a - b (same items, paired) with cluster-bootstrap one-sided bounds."""
    import torch
    diff = torch.as_tensor(a, dtype=torch.float64) - torch.as_tensor(b, dtype=torch.float64)
    return cluster_bootstrap(diff, clusters, **kw)


def bits(tensor) -> str:
    return "".join("1" if bool(x) else "0" for x in tensor.tolist())


def unbits(text: str):
    import torch
    return torch.tensor([c == "1" for c in text])


# ----------------------------------------------------------------------------- triplet data (H1)
def triplet_item(item_meta):
    item, meta = item_meta
    return L.label_free_item(item), meta


def triplet_digest(item_meta) -> str:
    item, meta = item_meta
    digest = hashlib.sha256(L.batch_digest(item).encode())
    for field in ("x_q", "u_q", "v_q", "a", "b", "rows"):
        digest.update(getattr(meta, field).numpy().tobytes())
    digest.update(repr((meta.kind_u, meta.kind_v)).encode())
    return digest.hexdigest()


def triplet_set(split: str) -> list:
    from premonition import ladder_triplets
    stream = ladder_triplets.triplet_batches(L.spec(), TRIPLET_SEEDS[split], per_batch=TRIPLETS_EVAL_BATCH,
                                             training=False, prefix=f"t{TRIPLET_SEEDS[split]}")
    return [triplet_item(next(stream)) for _ in range(TRIPLETS_EVAL // TRIPLETS_EVAL_BATCH)]


def triplet_train_stream():
    from premonition import ladder_triplets
    stream = ladder_triplets.triplet_batches(L.spec(), TRIPLET_SEEDS["train"], per_batch=H1_RUN["per_batch"],
                                             training=True, prefix=f"t{TRIPLET_SEEDS['train']}")
    return (triplet_item(x) for x in stream)


def checked_triplet_train():
    digests = json.loads((OUT / "data" / "triplet-train-digests.json").read_text())
    for i, item_meta in enumerate(triplet_train_stream()):
        if i < len(digests) and triplet_digest(item_meta) != digests[i]:
            raise SystemExit(f"triplet train batch {i} differs from the frozen digest")
        yield item_meta


def load_triplets(split: str) -> list:
    import torch
    info = json.loads((OUT / "data" / "manifest.json").read_text())["splits"][split]
    path = ROOT / info["file"]
    if sha256(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the data freeze")
    return torch.load(path, weights_only=False)


def cmd_data(args) -> None:
    import torch
    from collections import Counter
    started = time.perf_counter()
    out = OUT / "data"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"run": RUN, "task": "toy ladder triplets for H1 (premonition/ladder_triplets.py v1)",
                "q_star": "first 1-hop question of each visit; single-token answers",
                "seeds": TRIPLET_SEEDS, "triplets_per_eval_batch": TRIPLETS_EVAL_BATCH,
                "label_free": "premonition.train.label_free (legacy toy rule), applied after assembly",
                "privilege": "supplied gold-evidence cards (4 per 1-hop, 6 per 2-hop question)",
                "metadata": "roles, kinds, q* indices and answers are loss/eval-side only; visit rows shuffled",
                "splits": {}}
    ladder_prints = {p for split in ("validation", "test") for item in L.load_split(split) for p in L.prints(item)}
    for split in ("validation", "test"):
        items = triplet_set(split)
        path = out / f"triplets-{split}.pt"
        torch.save(items, path)
        prints = {p for item, _ in items for p in L.prints(item)}
        kinds_u = Counter(k for _, m in items for k in m.kind_u)
        kinds_v = Counter(k for _, m in items for k in m.kind_v)
        manifest["splits"][split] = {"seed": TRIPLET_SEEDS[split], "triplets": sum(len(m.a) for _, m in items),
                                     "visits": sum(int(i[0].tokens.shape[0]) for i, _ in items),
                                     "kinds_u": dict(kinds_u), "kinds_v": dict(kinds_v),
                                     "overlap_with_ladder_val_test_visits": len(prints & ladder_prints),
                                     "file": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    digests, stream = [], triplet_train_stream()
    for _ in range(H1_RUN["steps"]):
        digests.append(triplet_digest(next(stream)))
    (out / "triplet-train-digests.json").write_text(json.dumps(digests))
    manifest["splits"]["train"] = {"seed": TRIPLET_SEEDS["train"], "batches_digested": len(digests),
                                   "per_batch": H1_RUN["per_batch"], "training_visits": True,
                                   "digest_of_digests": hashlib.sha256("".join(digests).encode()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    ledger_add("data", "triplet sets + train digests", time.perf_counter() - started)
    print(json.dumps(manifest, indent=1))


# ----------------------------------------------------------------------------- forward helpers
def episode_with_order(model, item, order):
    """L.episode(cards="all") with a GIVEN supplied-card order; runs the model's passes. Returns (episode, rows)."""
    import torch
    batch, supplied, hops = item
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    ep = model._start(batch, hidden, store, model._mentions(batch))
    model._insert(ep, store, torch.arange(len(hops)), supplied.gather(1, order))
    everyone = torch.arange(len(hops))
    passes = 0 if getattr(model, "_nothink", False) else L.LOOPS
    rows = [model._step(ep, everyone, step, store)[0] for step in range(passes)]
    return ep, rows


def answer_forward(model, item, order):
    """(answer CE exactly as L.loss_of, [Q, V] first-answer-position logits of the final pass)."""
    import torch.nn.functional as F
    from learnlab.core import IGNORE_INDEX
    ep, rows = episode_with_order(model, item, order)
    batch = item[0]
    targets, inputs = L.targets_inputs(model, batch)
    first = 0
    if getattr(model, "qread", False):
        inputs, first = model.qread_inputs(batch, targets)
    keep = targets != IGNORE_INDEX
    decoded = [model._decode_logits(ep.x, ep.valid, inputs)] if not rows else \
        [model._decode_logits(r, ep.valid, inputs) for r in rows]
    decoded = [h[:, first:] for h in decoded]
    terms = [F.cross_entropy(F.linear(h[keep], model.embed.weight).float(), targets[keep]) for h in decoded]
    first_logits = F.linear(decoded[-1][:, 0], model.embed.weight).float()
    return sum(terms) / len(terms), first_logits


def first_tokens(model, item, order):
    ep, _ = episode_with_order(model, item, order)
    tokens, _ = model._greedy(item[0], ep, model._mentions(item[0]), None)
    return tokens[:, 0]


def optimizer_for(model):
    import torch
    params = list(model.parameters())
    return params, torch.optim.AdamW([{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
                                      {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
                                     lr=1e-3, betas=(0.9, 0.99), eps=1e-8)


# ----------------------------------------------------------------------------- training loops
def answer_loop(model, arm: str, seed: int, *, steps: int, deadline: float) -> tuple:
    """L.cmd_train's loop verbatim (same data stream, optimizer, schedule, loss, card-order generator)."""
    import torch
    p = ANSWER
    params, optimizer = optimizer_for(model)
    validation = L.load_split("validation")[:p["eval_batches"]]
    gen = torch.Generator().manual_seed(5000 + seed)
    history, stopped = [], "steps"
    stream = L.checked_train()
    started = time.perf_counter()
    for step in range(steps):
        if time.perf_counter() > deadline:
            stopped = "ledger cap"
            break
        for group in optimizer.param_groups:
            group["lr"] = p["lr"] * min(1.0, (step + 1) / p["warmup"])
        loss = L.loss_of(model, next(stream), arm, gen, cards="gold" if step < p["gold_steps"] else "all")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite = all(q.grad is None or bool(torch.isfinite(q.grad).all()) for q in params)
        norm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        optimizer.step()
        if (step + 1) % p["eval_every"] == 0 or step + 1 == steps:
            scores = L.ladder_scores(model, validation)
            entry = {"step": step + 1, "loss": round(float(loss.detach()), 4), "grad_norm": round(norm, 3),
                     "finite": finite, "seconds": round(time.perf_counter() - started, 1),
                     **{k: f"{v['correct']}/{v['n']}" for k, v in scores.items()}}
            history.append(entry)
            print(json.dumps(entry), flush=True)
            if not finite:
                stopped = "non-finite gradient"
                break
    return history, stopped


def reference_schedule(seed: int) -> dict:
    """The ORIGINAL writer's FLOP fit and budget (R.cmd_train's calibration) for this seed."""
    from premonition.train import Curriculum, MiniTrainer, budget_for_steps, mini_train_config
    model = build("retrieval", "original", seed)
    trainer = MiniTrainer(model, mini_train_config(lr=RETRIEVAL["lr"], warmup_steps=RETRIEVAL["warmup"],
                                                   log_every=50, eval_every=0), "cpu", flop_budget=1.0, seed=seed,
                          curriculum=Curriculum(RETRIEVAL["gold_until"], RETRIEVAL["teacher_until"],
                                                RETRIEVAL["ramp_until"]))
    stream = (item[0] for item in L.checked_train())
    head = [next(stream) for _ in range(2)]
    fit = trainer.calibrate(head)
    return {"fit": fit, "budget": budget_for_steps(trainer, head, RETRIEVAL["steps"]),
            "a": fit.a, "b": fit.b}


def retrieval_loop(model, seed: int, schedule: dict, *, deadline: float, max_steps=None) -> dict:
    """R.cmd_train, except the curriculum/stop use `schedule` (the original writer's fit and budget)."""
    import torch
    from premonition.train import Curriculum, MiniTrainer, budget_for_steps, mini_train_config
    trainer = MiniTrainer(model, mini_train_config(lr=RETRIEVAL["lr"], warmup_steps=RETRIEVAL["warmup"],
                                                   log_every=50, eval_every=0), "cpu", flop_budget=1.0, seed=seed,
                          curriculum=Curriculum(RETRIEVAL["gold_until"], RETRIEVAL["teacher_until"],
                                                RETRIEVAL["ramp_until"]))
    stream = (item[0] for item in L.checked_train())
    head = [next(stream) for _ in range(2)]
    own = trainer.calibrate(head)                       # consumes the trainer generator exactly as overnight
    own_budget = budget_for_steps(trainer, head, RETRIEVAL["steps"])
    generator_digest = hashlib.sha256(trainer.generator.get_state().numpy().tobytes()).hexdigest()
    trainer.fit, trainer.flop_budget = schedule["fit"], schedule["budget"]
    curve = []
    report = trainer.train(itertools.chain(head, stream), max_seconds=max(deadline - time.perf_counter(), 1.0),
                           max_steps=max_steps, on_log=lambda e: curve.append({k: e.get(k) for k in (
                               "step", "phase", "p_own", "loss", "lm", "ask", "ans", "halt", "gold_recall_at_4",
                               "answer_acc", "loops_per_question", "halt_rate")}))
    return {"report": {k: v for k, v in report.items() if isinstance(v, (int, float, str, bool, type(None)))},
            "phases": report.get("phases"), "curve": curve, "generator_after_calibration": generator_digest,
            "own_fit": {"a": own.a, "b": own.b}, "own_budget_for_steps": own_budget,
            "schedule": {"a": schedule["a"], "b": schedule["b"], "budget": schedule["budget"]}}


def h1_loop(model, objective: str, seed: int, *, deadline: float) -> tuple:
    """Fine-tune on the frozen triplet stream. `ce` and `h1` see identical minibatches, card orders, optimizer and
    schedule; `h1` adds js_weight * JS(p_x, p_u) + margin_weight * max(0, margin - delta) on each triplet's q*."""
    import torch
    from premonition.paired_objectives import H1Config, h1_terms
    p = H1_RUN
    config = H1Config(enabled=objective == "h1", js_weight=p["js_weight"], margin_weight=p["margin_weight"],
                      margin=p["margin"])
    params, optimizer = optimizer_for(model)
    gen = torch.Generator().manual_seed(7000 + seed)
    stream = checked_triplet_train()
    history, stopped, window = [], "steps", []
    started = time.perf_counter()
    from premonition.ladder_triplets import shared_order
    model.train()
    for step in range(p["steps"]):
        if time.perf_counter() > deadline:
            stopped = "ledger cap"
            break
        for group in optimizer.param_groups:
            group["lr"] = p["lr"] * min(1.0, (step + 1) / p["warmup"])
        item, meta = next(stream)
        order = shared_order(meta, len(item[2]), gen)
        ce, logits = answer_forward(model, item, order)
        terms = h1_terms(logits[meta.x_q], logits[meta.u_q], logits[meta.v_q], meta.a, meta.b, config)
        loss = ce + terms["loss"]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite = all(q.grad is None or bool(torch.isfinite(q.grad).all()) for q in params)
        norm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        optimizer.step()
        window.append([float(ce.detach()), float(terms["js"].mean()), float(terms["delta"].mean()),
                       float(terms["hinge"].mean()), terms["active_margin"] / len(meta.a)])
        if (step + 1) % 100 == 0 or step + 1 == p["steps"] or not finite:
            means = [round(sum(col) / len(col), 4) for col in zip(*window)]
            entry = {"step": step + 1, "ce": means[0], "js": means[1], "delta": means[2], "hinge": means[3],
                     "margin_active_share": means[4], "grad_norm": round(norm, 3), "finite": finite,
                     "seconds": round(time.perf_counter() - started, 1)}
            history.append(entry)
            window = []
            print(json.dumps(entry), flush=True)
            if not finite:
                stopped = "non-finite gradient"
                break
    return history, stopped, config


# ----------------------------------------------------------------------------- evaluation (read-only callers)
def scored(vector, clusters) -> dict:
    boot = cluster_bootstrap(vector.float(), clusters, resamples=GATE["resamples"], alpha=GATE["alpha"])
    return {"correct": int(vector.sum()), "n": int(vector.numel()), **boot, "bits": bits(vector)}


def ladder_readout(model, items, seed0: int) -> dict:
    """Per-question supplied-card reading (gold cards only) and choosing/combining (all shuffled supplied cards),
    exactly L.ladder_scores' calls, with visit-clustered bounds. Question slices as in the overnight harness."""
    import torch
    oks = {"gold": [], "all": []}
    hops, held, visits = [], [], []
    for i, item in enumerate(items):
        for cards in oks:
            oks[cards].append(L.predictions(model, item, cards=cards, seed=seed0 + i)[1])
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
        visits.append(item[0].q_visit + i * int(item[0].tokens.shape[0]))
    hop, held, visit = torch.cat(hops), torch.cat(held), torch.cat(visits)
    out = {}
    for cards, ok in oks.items():
        ok = torch.cat(ok)
        for name, mask in (("one_hop", hop == 1), ("two_hop_trained_rel", (hop == 2) & ~held),
                           ("two_hop_heldout_rel", (hop == 2) & held)):
            label = "read" if cards == "gold" else ("choose" if name == "one_hop" else "combine")
            out[f"{label}:{name}"] = scored(ok[mask], visit[mask])
    return out


def triplet_readout(model, triplets) -> dict:
    """H1 behavioural metrics on frozen triplets; one cluster per triplet (x, u, v siblings together)."""
    import torch
    from premonition.ladder_triplets import shared_order
    from premonition.paired_objectives import triplet_metrics
    per, kinds_u, kinds_v, cluster = {}, [], [], []
    for j, (item, meta) in enumerate(triplets):
        order = shared_order(meta, len(item[2]), torch.Generator().manual_seed(9100 + j))
        first = first_tokens(model, item, order)
        for key, value in triplet_metrics(first[meta.x_q], first[meta.u_q], first[meta.v_q], meta.a,
                                          meta.b).items():
            per.setdefault(key, []).append(value)
        kinds_u += list(meta.kind_u)
        kinds_v += list(meta.kind_v)
        cluster += [j * 1000 + t for t in range(len(meta.a))]
    cluster = torch.tensor(cluster)
    out = {key: scored(torch.cat(values), cluster) for key, values in per.items()}
    for key, kinds in (("invariant_both_correct", kinds_u), ("relevant_both_correct", kinds_v)):
        vector = torch.cat(per[key])
        for kind in sorted(set(kinds)):
            mask = torch.tensor([k == kind for k in kinds])
            out[f"{key}:{kind}"] = {"correct": int(vector[mask].sum()), "n": int(mask.sum())}
    return out


def causal_pairs(model, *, own_loops=None) -> dict:
    """The overnight paired 2-hop interventions (validation-side seed): answer-only models read all 6 supplied cards
    (L.cmd_causal); retrieval models retrieve on their own for `own_loops` loops (R.cmd_eval --causal)."""
    out = {}
    for kind, pairs in L.paired_two_hop(256).items():
        n = both = moved = 0
        for i, (a, b, firsts) in enumerate(pairs):
            if own_loops is None:
                pa, pb = (L.predictions(model, x, cards="all", seed=300 + i)[0][firsts] for x in (a, b))
            else:
                pa, pb = (R.own_first_token(model, x[0], own_loops)[firsts] for x in (a, b))
            ta, tb = a[0].answer[firsts, 0], b[0].answer[firsts, 0]
            n += len(firsts)
            both += int(((pa == ta) & (pb == tb)).sum())
            moved += int((pa != pb).sum())
        out[kind] = {"pairs": n, "both_correct": both, "prediction_changed": moved,
                     "expected": "stay" if kind == "tempting" else "change"}
    return out


def own_retrieval_trace(model, batch, loops: int = 4):
    """Own retrieval for `loops` fixed loops (HALT ignored), top-k per positive ASK; fetched cards per step."""
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    steps = []
    for step in range(loops):
        _, _, ask, scores = model._step(episode, everyone, step, store)
        if step + 1 < loops:
            cards = store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
            steps.append(cards.clone())
            model._insert(episode, store, everyone, cards)
    return steps, store


def second_fetch(model, items) -> dict:
    """What the 2nd own fetch of each 2-hop question "a LINK r?" retrieves (overnight hop2_miss classes), plus
    per-question right-relation / right-person-and-relation vectors, split practised vs held-out relation."""
    import torch
    s = L.spec()
    out = {}
    for i, item in enumerate(items):
        batch, _, hops = item
        steps, store = own_retrieval_trace(model, batch)
        held = batch.slices["heldout"]
        for q in range(len(hops)):
            if int(hops[q]) != 2:
                continue
            v = int(batch.q_visit[q])
            ask = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
            a, r = ask[1] - s.vocab_size, ask[3]
            link = int(batch.gold_lines[q, 0])
            b = int(batch.tokens[v, int(batch.line_start[v, link]) + 3]) - s.vocab_size
            group = out.setdefault("heldout" if bool(held[q]) else "practised",
                                   {"classes": {}, "right_relation": [], "right_person_relation": [],
                                    "first_is_link": [], "cluster": []})
            line = int(steps[1][q, 0]) if steps[1].shape[1] else -1
            if line < 0 or line >= store.lines:
                kind = "none"
            else:
                tokens = batch.tokens[v, int(batch.line_start[v, line]):int(batch.line_start[v, line]) + 4].tolist()
                subject, middle = tokens[1] - s.vocab_size, tokens[2]
                if middle == s.link:
                    kind = "link" if subject == a else "other_link"
                elif subject == b:
                    kind = "answer" if middle == r else "friend_other_rel"
                elif subject == a:
                    kind = "asker_same_rel" if middle == r else "asker_other_rel"
                else:
                    kind = "other_same_rel" if middle == r else "other_other_rel"
            group["classes"][kind] = group["classes"].get(kind, 0) + 1
            group["right_relation"].append(kind in ("answer", "asker_same_rel", "other_same_rel"))
            group["right_person_relation"].append(kind == "answer")
            first = int(steps[0][q, 0])
            group["first_is_link"].append(first == link)
            group["cluster"].append(i * 1000 + v)
    for group in out.values():
        cluster = torch.tensor(group.pop("cluster"))
        for key in ("right_relation", "right_person_relation", "first_is_link"):
            group[key] = scored(torch.tensor(group[key]), cluster)
    return out


def own_fixed_readout(model, items, loops: int, *, no_cards: bool = False) -> dict:
    import torch
    oks, gots, hops, held, visits = [], [], [], [], []
    for i, item in enumerate(items):
        ok, got = R.own_fixed(model, item[0], loops, no_cards=no_cards)
        oks.append(ok)
        gots.append(got)
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
        visits.append(item[0].q_visit + i * int(item[0].tokens.shape[0]))
    ok, got, hop, held, visit = (torch.cat(x) for x in (oks, gots, hops, held, visits))
    out = {}
    for name, mask in (("one_hop", hop == 1), ("two_hop_trained_rel", (hop == 2) & ~held),
                       ("two_hop_heldout_rel", (hop == 2) & held)):
        out[name] = {**scored(ok[mask], visit[mask]), "all_gold_fetched": scored(got[mask], visit[mask])}
    return out


def gold_read_readout(model, items) -> dict:
    import torch
    oks, hops, held, visits = [], [], [], []
    for i, item in enumerate(items):
        oks.append(R.gold_read(model, item[0], 2)[0])
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
        visits.append(item[0].q_visit + i * int(item[0].tokens.shape[0]))
    ok, hop, held, visit = (torch.cat(x) for x in (oks, hops, held, visits))
    return {name: scored(ok[mask], visit[mask]) for name, mask in (
        ("one_hop", hop == 1), ("two_hop_trained_rel", (hop == 2) & ~held), ("two_hop_heldout_rel", (hop == 2) & held))}


def pool_mass(model, items) -> dict:
    """Mean softmax mass of each learned pool on [marker, person, relation, value, fillers+newline] of attribute
    lines (no fitted probe). The mean writer is uniform by construction."""
    import torch
    s = L.spec()
    pools = {"pool": getattr(model.writer, "pool", None), "pool_value": getattr(model.writer, "pool_value", None)}
    if type(model.writer).__name__ == "MeanPoolCardWriter":
        return {"writer": "mean (uniform by construction)"}
    out = {}
    for name, pool in pools.items():
        if pool is None:
            continue
        mass, lines = torch.zeros(5), 0
        for batch, _, _ in items[:4]:
            hidden = model.read(batch).float()
            score = pool(hidden).squeeze(-1).float()
            for v in range(batch.line_start.shape[0]):
                for l in range(batch.line_start.shape[1]):
                    start = int(batch.line_start[v, l])
                    if start < 0 or bool(batch.line_is_question[v, l]):
                        continue
                    if not s.relation(0) <= int(batch.tokens[v, start + 2]) < s.relation(0) + s.relations:
                        continue
                    pos = (batch.line_of[v] == l).nonzero().squeeze(1)
                    mass += torch.zeros(5).index_add(0, (pos - start).clamp_max(4), torch.softmax(score[v, pos], 0))
                    lines += 1
        out[name] = [round(float(m) / max(lines, 1), 3) for m in mass]
    out["lines"] = lines
    return out


def evaluate_answer(model, split: str) -> dict:
    items = L.load_split(split)
    out = {"ladder": ladder_readout(model, items, 99 if split == "validation" else 7),
           "triplets": triplet_readout(model, load_triplets(split))}
    if split == "validation":
        out["causal_two_hop_all_supplied"] = causal_pairs(model)
        out["pool_mass"] = pool_mass(model, items)
    return out


def evaluate_retrieval(model, split: str) -> dict:
    from premonition.train import validate
    items = L.load_split(split)
    out = {"own_fixed_K4": own_fixed_readout(model, items, 4), "gold_read_K2_no_fetch": gold_read_readout(model, items),
           "second_fetch": second_fetch(model, items)}
    if split == "validation":
        out["own_fixed_K3"] = own_fixed_readout(model, items, 3)
        out["own_fixed_K3_cards_removed"] = own_fixed_readout(model, items, 3, no_cards=True)
        out["supplied_card_readout"] = {"caveat": "trained with top-1 and no teacher distractors: decoy sets are a "
                                                  "distribution shift", **ladder_readout(model, items, 99)}
        v = validate(model, [item[0] for item in items], gold_cards=True)
        out["learned_halting"] = {k: v.get(k) for k in ("questions", "accuracy", "accuracy_gold_cards",
                                                         "gold_recall_at_4", "gold_any_at_4", "asked_rate",
                                                         "loops_mean", "halt_rate")}
        out["causal_two_hop_own_K3"] = causal_pairs(model, own_loops=3)
        out["pool_mass"] = pool_mass(model, items)
    return out


# ----------------------------------------------------------------------------- commands
def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=str))


def cmd_check(args) -> None:
    started = time.perf_counter()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    run = subprocess.run([sys.executable, "-B", "-m", "unittest", *args.tests], cwd=ROOT, env=env,
                         capture_output=True, text=True)
    seconds = time.perf_counter() - started
    log = OUT / "checks" / f"{time.strftime('%H%M%S')}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"$ unittest {' '.join(args.tests)}\n{run.stdout}{run.stderr}")
    tail = (run.stdout + run.stderr).strip().splitlines()[-3:]
    ledger_add("check", " ".join(args.tests), seconds, returncode=run.returncode, log=str(log.relative_to(ROOT)),
               result=" | ".join(tail))
    print("\n".join(tail))
    if run.returncode:
        raise SystemExit(run.returncode)


def cmd_reuse(args) -> None:
    """Replay the start of each reused overnight arm through this harness and compare with its saved log."""
    import torch
    started = time.perf_counter()
    report = {}
    mine, theirs = build("answer", "original", 0).state_dict(), L.build("nothink+qread", 0).state_dict()
    report["answer_init_identical"] = all(torch.equal(mine[k], theirs[k]) for k in theirs) and mine.keys() == theirs.keys()
    overnight = json.loads((OVN_OUT / "exp1" / "runs" / "nothink+qread-s0-cur600-2000.json").read_text())
    model = build("answer", "original", 0)
    history, _ = answer_loop(model, "nothink+qread", 0, steps=ANSWER["eval_every"],
                             deadline=time.perf_counter() + require(60))
    want = {k: v for k, v in overnight["history"][0].items() if k != "seconds"}
    got = {k: v for k, v in history[0].items() if k != "seconds"}
    report["answer_step400"] = {"overnight": want, "replayed": got, "match": want == got}
    mine, theirs = build("retrieval", "original", 0).state_dict(), R.build("bypass-k1", 0).state_dict()
    report["retrieval_init_identical"] = all(torch.equal(mine[k], theirs[k]) for k in theirs)
    overnight = json.loads((OVN_OUT / "exp2" / "runs" / "bypass-k1-s0-1500.json").read_text())
    schedule = reference_schedule(0)
    report["retrieval_budget"] = {"overnight": overnight["train_report"]["flop_budget"], "replayed": schedule["budget"],
                                  "match": overnight["train_report"]["flop_budget"] == schedule["budget"]}
    result = retrieval_loop(build("retrieval", "original", 0), 0, schedule,
                            deadline=time.perf_counter() + require(30), max_steps=50)
    report["retrieval_step50"] = {"overnight": overnight["curve"][0], "replayed": result["curve"][0],
                                  "match": overnight["curve"][0] == result["curve"][0]}
    for name in REUSED:
        _, info = load(name)                                  # refuses a config mismatch
        report[f"{name}_config_matches_protocol"] = True
        report[f"{name}_sha256"] = info["sha256"]
    report["reusable"] = all(v is True or (isinstance(v, dict) and v.get("match", True)) for v in report.values()
                             if not isinstance(v, str))
    write_json(OUT / "reuse.json", report)
    ledger_add("reuse-check", "answer 400 steps + retrieval 50 steps replay", time.perf_counter() - started,
               reusable=report["reusable"])
    print(json.dumps({k: (v["match"] if isinstance(v, dict) else v) for k, v in report.items()}, indent=1))


def cmd_answer(args) -> None:
    name = f"answer-{args.writer}-s{args.seed}"
    if name in REUSED or ckpt_file(name).exists():
        raise SystemExit(f"{name} already exists (reused or trained): no rerun")
    left = require(ANSWER["estimate_seconds"])
    started = time.perf_counter()
    model = build("answer", args.writer, args.seed)
    history, stopped = answer_loop(model, arm_string("answer", args.writer), args.seed, steps=ANSWER["steps"],
                                   deadline=started + left)
    seconds = time.perf_counter() - started
    path = save(name, model, "answer", args.writer, args.seed, steps_done=history[-1]["step"] if history else 0)
    write_json(OUT / "runs" / f"{name}.json", {
        "name": name, "protocol": ANSWER, "arm": arm_string("answer", args.writer), "seed": args.seed,
        "stopped": stopped, "seconds": round(seconds, 2), "history": history, "identity": identity(
            "answer", args.writer, model), "ckpt": str(path.relative_to(ROOT)), "ckpt_sha256": sha256(path),
        "command": " ".join(sys.argv)})
    ledger_add("train", name, seconds, stopped=stopped)
    print(f"done {name}: {seconds:.1f} s, stopped={stopped}; ledger {ledger_seconds():.1f} / {CAP_SECONDS:.0f}")


def cmd_retrieval(args) -> None:
    name = f"retrieval-{args.writer}-s{args.seed}"
    if name in REUSED or ckpt_file(name).exists():
        raise SystemExit(f"{name} already exists (reused or trained): no rerun")
    left = require(RETRIEVAL["estimate_seconds"])
    started = time.perf_counter()
    schedule = reference_schedule(args.seed)             # before the arm's build: its seeded state comes last
    model = build("retrieval", args.writer, args.seed)
    result = retrieval_loop(model, args.seed, schedule, deadline=started + left)
    seconds = time.perf_counter() - started
    path = save(name, model, "retrieval", args.writer, args.seed, schedule=result["schedule"])
    write_json(OUT / "runs" / f"{name}.json", {
        "name": name, "protocol": RETRIEVAL, "arm": arm_string("retrieval", args.writer), "seed": args.seed,
        **result, "seconds": round(seconds, 2), "identity": identity("retrieval", args.writer, model),
        "ckpt": str(path.relative_to(ROOT)), "ckpt_sha256": sha256(path), "command": " ".join(sys.argv)})
    ledger_add("train", name, seconds, stopped=result["report"].get("stop"), steps=result["report"].get("steps"))
    print(f"done {name}: {seconds:.1f} s, steps={result['report'].get('steps')} stop={result['report'].get('stop')};"
          f" ledger {ledger_seconds():.1f} / {CAP_SECONDS:.0f}")


def cmd_eval(args, split: str = "validation") -> None:
    from learnlab.readonly import read_only
    folder = "eval" if split == "validation" else "tests"
    path = OUT / folder / f"{args.ckpt}.json"
    if split == "test" and path.exists():
        raise SystemExit("already scored on the test split")
    require(20, reserve=5)
    started = time.perf_counter()
    model, info = load(args.ckpt)
    # D-card-bypass keeps `_reading`, a transient pointer to the episode being decoded (set by _step/_greedy
    # before every decode, never learned state); it is the only change the guard may accept.
    allow = ["_reading"] if hasattr(model, "_reading") else []
    try:
        with read_only(model, allow_changes=allow):
            scores = (evaluate_answer if info["kind"] == "answer" else evaluate_retrieval)(model, split)
    except BaseException as error:
        ledger_add("failed-" + ("test-eval" if split == "test" else "eval"), args.ckpt, time.perf_counter() - started,
                   error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    write_json(path, {"ckpt": args.ckpt, **info, "split": split, "read_only": "learnlab.readonly.read_only",
                      "read_only_allow_changes": allow,
                      "scores": scores, "seconds": round(seconds, 2)})
    ledger_add("test-eval" if split == "test" else "eval", args.ckpt, seconds)
    print(summary_line(args.ckpt, scores), f"({seconds:.1f} s)")


def summary_line(name: str, scores: dict) -> str:
    pick = lambda d: f"{d['correct']}/{d['n']} [{d.get('lower', '-')}, {d.get('upper', '-')}]"
    if "ladder" in scores:
        lad, tri = scores["ladder"], scores["triplets"]
        return (f"{name}: read1 {pick(lad['read:one_hop'])} choose1 {pick(lad['choose:one_hop'])} comb2 "
                f"{pick(lad['combine:two_hop_trained_rel'])} | triplets x {pick(tri['x_correct'])} relevant-both "
                f"{pick(tri['relevant_both_correct'])} invariant-both {pick(tri['invariant_both_correct'])}")
    k4, gold = scores["own_fixed_K4"], scores["gold_read_K2_no_fetch"]
    sf = scores["second_fetch"]
    return (f"{name}: K4 1-hop {pick(k4['one_hop'])} 2-hop {pick(k4['two_hop_trained_rel'])} held "
            f"{pick(k4['two_hop_heldout_rel'])} | pure read1 {pick(gold['one_hop'])} | 2nd fetch right rel "
            + " ".join(f"{g} {pick(v['right_relation'])}" for g, v in sf.items()))


def cmd_gate(args) -> None:
    evals = {}
    for writer in ("original", "mean"):
        for seed in (0, 1, 2):
            path = OUT / "eval" / f"answer-{writer}-s{seed}.json"
            if path.exists():
                evals.setdefault(writer, {})[seed] = json.loads(path.read_text())["scores"]["ladder"]
    seeds = sorted(set.intersection(*(set(v) for v in evals.values())))
    mean_choose = {w: sum(evals[w][s]["choose:one_hop"]["point"] for s in seeds) / len(seeds) for w in evals}
    selected = max(mean_choose, key=lambda w: (mean_choose[w], w == "mean"))
    per_seed = {s: {"read1": evals[selected][s]["read:one_hop"]["correct"],
                    "choose_point": evals[selected][s]["choose:one_hop"]["point"],
                    "choose_lower": evals[selected][s]["choose:one_hop"]["lower"]} for s in seeds}
    reading = all(v["read1"] >= GATE["reading_one_hop_min"] for v in per_seed.values())
    identity_path = all(v["choose_lower"] > GATE["choose_lower_bound_above"] for v in per_seed.values())
    weak = any(v["choose_point"] < GATE["choose_point_below_on_some_seed"] for v in per_seed.values())
    gate = {"rule": GATE, "screened_seeds": seeds, "mean_choose_by_writer": mean_choose, "selected_writer": selected,
            "per_seed": per_seed, "reading_ok": reading, "identity_path_ok": identity_path,
            "choosing_still_weak": weak, "h1_activated": reading and identity_path and weak}
    write_json(OUT / "gate.json", gate)
    ledger_add("gate", "predeclared H1 gate", 0.0)
    print(json.dumps(gate, indent=1))


def cmd_h1(args) -> None:
    gate = json.loads((OUT / "gate.json").read_text())
    if not gate["h1_activated"]:
        raise SystemExit("H1 gate not passed: training comparison not activated")
    if args.seed not in gate["screened_seeds"]:
        raise SystemExit("seed not screened by the gate")
    init = f"answer-{gate['selected_writer']}-s{args.seed}"
    name = f"h1-{args.objective}-s{args.seed}"
    if ckpt_file(name).exists():
        raise SystemExit(f"{name} exists: no rerun")
    left = require(H1_RUN["estimate_seconds"])
    started = time.perf_counter()
    model, info = load(init)
    history, stopped, config = h1_loop(model, args.objective, args.seed, deadline=started + left)
    seconds = time.perf_counter() - started
    path = save(name, model, "answer", gate["selected_writer"], args.seed, init=init, init_sha256=info["sha256"],
                objective=args.objective, h1=config.identity())
    write_json(OUT / "runs" / f"{name}.json", {
        "name": name, "init": init, "init_sha256": info["sha256"], "objective": args.objective,
        "h1": config.identity(), "protocol": H1_RUN, "seed": args.seed, "stopped": stopped,
        "seconds": round(seconds, 2), "history": history, "ckpt": str(path.relative_to(ROOT)),
        "ckpt_sha256": sha256(path), "command": " ".join(sys.argv)})
    ledger_add("train", name, seconds, stopped=stopped)
    print(f"done {name}: {seconds:.1f} s; ledger {ledger_seconds():.1f} / {CAP_SECONDS:.0f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("freeze", "data", "reuse", "gate"):
        sub.add_parser(name)
    check = sub.add_parser("check")
    check.add_argument("--tests", nargs="+", required=True)
    for name, writers in (("answer", ("original", "mean")), ("retrieval", ("original", "mean", "two"))):
        p = sub.add_parser(name)
        p.add_argument("--writer", choices=writers, required=True)
        p.add_argument("--seed", type=int, required=True)
    for name in ("eval", "test"):
        sub.add_parser(name).add_argument("--ckpt", required=True)
    h1 = sub.add_parser("h1")
    h1.add_argument("--seed", type=int, required=True)
    h1.add_argument("--objective", choices=("ce", "h1"), required=True)
    args = parser.parse_args()
    if args.cmd == "freeze":
        return freeze()
    if args.cmd == "check":
        return cmd_check(args)
    bootstrap()
    {"data": cmd_data, "reuse": cmd_reuse, "answer": cmd_answer, "retrieval": cmd_retrieval, "eval": cmd_eval,
     "test": lambda a: cmd_eval(a, "test"), "gate": cmd_gate, "h1": cmd_h1}[args.cmd](args)


if __name__ == "__main__":
    main()
