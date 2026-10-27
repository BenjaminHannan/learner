#!/usr/bin/env python3
"""Prepared source-only 18k/36k experiment. No command runs on import.

Order, only when explicitly authorized later:
  seal-panels                 generate and seal fresh source-only panels
  train --arm ARM --seed SEED --budget STEPS    repeat for all 16 runs
  register                    freeze all 16 checkpoint/source hashes
  verify                      score the untouched verification and old guard

Use an already cached fp32 PyTorch runtime with MPS. No downloads, maze calls,
race execution, or modification of the original experiment are implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/claude-patch-20260927/budget-v2"
PARENT = OUT.parent
ARMS = ("patch", "loop", "loop_meta", "plain")
SEEDS = (927401, 927402)
BUDGETS = (18000, 36000)
KINDS = ("sums", "grids", "sorting", "reversing", "counting", "brackets")
BATCH, EPISODES = 64, 2000
SOURCE_GUARD_SEED = 9233000
DEV_SEED, VERIFY_SEED = 92751000, 92752000
CODE = ("scripts/claude_patch_budget.py", "scripts/claude_patch_practice.py",
        "scripts/claude_patch_data.py", "scripts/claude_patch_net.py",
        "scripts/claude_patch_checks.py", "scripts/claude_rsn358a_envs.py",
        "scripts/claude_blurt1.py")
REGISTERED = CODE + (
    "artifacts/claude-patch-20260927/budget-v2/PROTOCOL.md",
    "artifacts/claude-patch-20260927/EPISODE-RECIPE.md",
    "artifacts/claude-patch-20260927/CANDIDATE-SEAL.json",
    "artifacts/claude-patch-20260927/QUALIFIED-SEAL.json",
    "artifacts/claude-patch-20260927/ASTRA-REVIEW.md",
    "artifacts/claude-patch-20260927/PANELS.json",
    "artifacts/claude-patch-20260927/qualification/dev-raw.jsonl")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    tmp.replace(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def registration() -> dict:
    r = read(OUT / "REGISTRATION.json")
    require(r["arms"] == list(ARMS) and r["seeds"] == list(SEEDS) and
            r["budgets"] == list(BUDGETS) and r["kinds"] == list(KINDS) and
            r["batch"] == BATCH and r["episodes"] == EPISODES,
            "registration constants changed")
    require(r["source_guard_seed"] == SOURCE_GUARD_SEED and
            r["dev_seed"] == DEV_SEED and r["verify_seed"] == VERIFY_SEED,
            "panel seeds changed")
    require(set(r["sha256"]) == set(REGISTERED), "registered source inventory changed")
    for rel, digest in r["sha256"].items():
        require(sha(ROOT / rel) == digest, f"registered hash changed: {rel}")
    require(r["sha256"]["artifacts/claude-patch-20260927/CANDIDATE-SEAL.json"] ==
            read(PARENT / "QUALIFIED-SEAL.json")["candidate_seal"], "candidate/qualified link changed")
    require(read(PARENT / "QUALIFIED-SEAL.json")["kinds"] == list(KINDS) and
            read(PARENT / "QUALIFIED-SEAL.json")["eligible"], "qualified kinds changed")
    candidate = read(PARENT / "CANDIDATE-SEAL.json")
    for rel, digest in candidate["files"].items():
        require(sha(ROOT / rel) == digest, f"original candidate seal mismatch: {rel}")
    require(sha(PARENT / "qualification/dev-raw.jsonl") ==
            read(PARENT / "QUALIFIED-SEAL.json")["raw_sha256"], "qualification evidence changed")
    return r


def imports():
    # Importing the original trainer only after a runtime command avoids torch
    # initialization for help, registration inspection, and static audit.
    import claude_patch_data as D
    import claude_patch_net as N
    import claude_patch_practice as P
    import torch
    return D, N, P, torch


def panel_data():
    import claude_patch_data as D
    return D


def guard_items(D):
    """Exact source-only old_panels(9233000) construction, without maze imports."""
    E = D.E
    rng = random.Random(SOURCE_GUARD_SEED)
    sums = [E.make_sum(rng, 4) for _ in range(200)]
    grids = []
    for _ in range(200):
        it = E.latin_item(rng, *E.make_latin_base(rng, 5))
        legend = [E.SYM + n for n in it.meta["names"]]
        rng.shuffle(legend)
        grids.append(E.Item("grids", 5,
            it.tokens + [[E.BLANK] * 5, legend],
            it.slot + [[0] * 5, [0] * 5],
            it.target + [[0] * 5, [0] * 5], it.meta))
    return {"sums4": sums, "grids5": grids}


def legacy_fingerprints(D):
    """Inputs already observed by the original pilot/arms; read-only."""
    original = read(PARENT / "PANELS.json")
    require(set(original) == {"dev", "verify"}, "original panel splits changed")
    fingerprints = set()
    per_kind = {kind: set() for kind in KINDS}
    for split in ("dev", "verify"):
        require(set(original[split]) == set(KINDS), f"original {split} kinds changed")
        for kind in KINDS:
            require(len(original[split][kind]) == 300,
                    f"original {split}/{kind} count changed")
            for encoded in original[split][kind]:
                fp = D.fingerprint(D.E.Item(**encoded))
                fingerprints.add(fp)
                per_kind[kind].add(fp)
    raw = PARENT / "qualification/dev-raw.jsonl"
    for line in raw.read_text().splitlines():
        row = json.loads(line)
        kind = row["kind"]
        require(kind in KINDS, "unexpected original qualification kind")
        fp = D.fingerprint(D.E.Item(**row["input"]))
        require(fp == row["fingerprint"], "original qualification fingerprint mismatch")
        fingerprints.add(fp)
        per_kind[kind].add(fp)
    return fingerprints, {kind: len(values) for kind, values in per_kind.items()}


def encode(it):
    return {key: getattr(it, key) for key in ("env", "size", "tokens", "slot", "target", "meta")}


def panels(include_verify_items=True) -> tuple[dict, set[str]]:
    D = panel_data()
    seal = read(OUT / "PANEL-SEAL.json")
    require(seal["registration_sha256"] == sha(OUT / "REGISTRATION.json") and
            seal["panels_sha256"] == sha(OUT / "PANELS.json"), "panel seal mismatch")
    raw = read(OUT / "PANELS.json")
    require(set(raw) == {"dev", "verify", "old_guard"}, "panel split mismatch")
    legacy, legacy_counts = legacy_fingerprints(D)
    require(seal["legacy_unique_counts"] == legacy_counts,
            "original observed-panel inventory changed")
    fixed_guard = guard_items(D)
    ban = set(legacy)
    ban.update(D.fingerprint(it) for group in fixed_guard.values() for it in group)
    decoded = {}
    for split, kinds in raw.items():
        expected = ("sums4", "grids5") if split == "old_guard" else KINDS
        require(set(kinds) == set(expected), f"panel kinds changed: {split}")
        decoded[split] = {}
        for kind, encoded in kinds.items():
            n = 200 if split == "old_guard" else 300
            require(len(encoded) == n, f"panel count changed: {split}/{kind}")
            # Training sees verify inputs only for exclusion. It never turns
            # verify targets into Items or passes them to a model/scorer.
            if split == "verify" and not include_verify_items:
                items = None
                fps = [hashlib.sha256(json.dumps([item["tokens"], item["slot"]],
                        separators=(",", ":")).encode()).hexdigest() for item in encoded]
            else:
                items = [D.E.Item(**item) for item in encoded]
                fps = [D.fingerprint(item) for item in items]
            if split != "old_guard":
                require(not (ban & set(fps)), f"panel overlap with original or new split: {split}/{kind}")
            if split != "old_guard":
                require(len(set(fps)) == n, f"duplicate panel input: {split}/{kind}")
            ban.update(fps)
            decoded[split][kind] = items
    for kind, items in fixed_guard.items():
        require([encode(it) for it in items] == raw["old_guard"][kind],
                f"old guard does not match ruler: {kind}")
    require(seal["fingerprints_sha256"] == hashlib.sha256(
        "\n".join(sorted(ban)).encode()).hexdigest(), "panel fingerprint seal mismatch")
    return decoded, ban


def seal_panels() -> None:
    registration()
    require(not (OUT / "PANEL-SEAL.json").exists() and
            not (OUT / "PANELS.json").exists(), "panels already sealed; no replacement permitted")
    D = panel_data()
    old = guard_items(D)
    banned, legacy_counts = legacy_fingerprints(D)
    banned.update(D.fingerprint(it) for items in old.values() for it in items)
    raw = {"dev": {}, "verify": {}, "old_guard":
           {kind: [encode(it) for it in items] for kind, items in old.items()}}
    for i, kind in enumerate(KINDS):
        dev = D.panel(kind, DEV_SEED + i, 300, exclude=banned)
        banned.update(D.fingerprint(it) for it in dev)
        verify = D.panel(kind, VERIFY_SEED + i, 300, exclude=banned)
        banned.update(D.fingerprint(it) for it in verify)
        raw["dev"][kind] = [encode(it) for it in dev]
        raw["verify"][kind] = [encode(it) for it in verify]
    write(OUT / "PANELS.json", raw)
    write(OUT / "PANEL-SEAL.json", {"utc": utc(), "registration_sha256":
          sha(OUT / "REGISTRATION.json"), "panels_sha256": sha(OUT / "PANELS.json"),
          "fingerprints_sha256": hashlib.sha256("\n".join(sorted(banned)).encode()).hexdigest(),
          "legacy_unique_counts": legacy_counts,
          "counts": {"dev": 300, "verify": 300, "old_guard": 200}})
    panels()


def runtime(torch):
    require(torch.__version__ == "2.14.0", "expected original cached torch 2.14.0")
    require(torch.backends.mps.is_available(), "MPS unavailable; no CPU/GPU fallback")
    torch.set_num_threads(4)
    return "mps"


def torch_rng(torch):
    return {"cpu": torch.get_rng_state(), "mps": torch.mps.get_rng_state()}


def restore_torch_rng(torch, state):
    torch.set_rng_state(state["cpu"])
    torch.mps.set_rng_state(state["mps"])


def torch_save(torch, path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    torch.save(state, tmp)
    tmp.replace(path)


def run_dir(arm, seed, budget):
    return OUT / "runs" / f"{arm}-seed{seed}-s{budget}"


def chain(previous, evidence):
    encoded = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(bytes.fromhex(previous) + encoded).hexdigest()


def initial_hash(net):
    digest = hashlib.sha256()
    for name, tensor in net.state_dict().items():
        digest.update(name.encode() + b"\0")
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def episode_evidence(D, rng, ban):
    old, new = rng.sample(list(KINDS), 2)
    used = set(ban)
    supports = []
    for kind in (old, old, new, new):
        item = D.batch(kind, rng, 1, exclude=used)
        used.add(D.fingerprint(item[0]))
        supports.append(item)
    queries = []
    for kind in (new, old):
        items = D.batch(kind, rng, 8, exclude=used)
        used.update(D.fingerprint(it) for it in items)
        queries.append(items)
    return supports, queries


def train(arm, seed, budget):
    registration()
    all_panels, ban = panels(include_verify_items=False)
    D, N, P, torch = imports()
    dev = runtime(torch)
    directory = run_dir(arm, seed, budget)
    final = directory / "final.pt"
    require(not (directory / "training.json").exists(),
            "run already completed; fresh runs cannot overwrite it")
    directory.mkdir(parents=True, exist_ok=True)
    registration_hash = sha(OUT / "REGISTRATION.json")
    panel_hash = sha(OUT / "PANEL-SEAL.json")
    torch.manual_seed(seed)  # identical initial weights within each arm/seed pair
    net = N.Net("loop" if arm == "loop_meta" else arm).to(dev).float()
    initial_state_sha256 = initial_hash(net)
    patch = net.zero_patch() if arm == "patch" else None
    source_rng = random.Random(seed + 10000)
    source_round_rng = random.Random(seed + 20000)
    # Independent of source duration; fixed across all arms and both budgets.
    episode_rng = random.Random(seed + 30000)
    episode_round_rng = random.Random(seed + 40000)
    opt, sch = P.optimizer(net, budget)
    meter = P.ComputeMeter(net)
    progress = directory / "progress.pt"
    source_done = episode_done = 0
    phase = "source"
    source_chain = hashlib.sha256(b"budget-v2-source").hexdigest()
    source_prefix_18k = None
    episode_chain = hashlib.sha256(b"budget-v2-episodes").hexdigest()
    operations = {"supervised_optimizer_steps": 0, "episode_optimizer_steps": 0,
                  "supervised_examples": 0, "support_examples": 0,
                  "query_examples": 0, "support_writes": 0,
                  "inner_gradient_steps": 0}
    prior_seconds = 0.0
    if progress.exists():
        state = torch.load(progress, map_location=dev, weights_only=False)
        require(state["identity"] == (arm, seed, budget) and
                state["registration_sha256"] == registration_hash and
                state["panel_seal_sha256"] == panel_hash, "foreign/stale checkpoint")
        phase = state["phase"]
        source_done, episode_done = state["source_done"], state["episode_done"]
        require(0 <= source_done <= budget and 0 <= episode_done <= EPISODES and
                phase in ("source", "episodes"), "invalid checkpoint counters")
        if phase == "episodes":
            require(source_done == budget, "episode checkpoint before source completion")
            opt, sch = P.optimizer(net, EPISODES)
        net.load_state_dict(state["state"])
        patch = state["patch"]
        opt.load_state_dict(state["optimizer"])
        sch.load_state_dict(state["scheduler"])
        source_rng.setstate(state["source_rng"])
        source_round_rng.setstate(state["source_round_rng"])
        episode_rng.setstate(state["episode_rng"])
        episode_round_rng.setstate(state["episode_round_rng"])
        restore_torch_rng(torch, state["torch_rng"])
        operations = state["operations"]
        meter.counts = state["matrix_operations"]
        prior_seconds = state["training_seconds"]
        require(state["initial_state_sha256"] == initial_state_sha256,
                "initial state changed since checkpoint")
        source_chain = state["source_chain"]
        source_prefix_18k = state["source_prefix_18k"]
        episode_chain = state["episode_chain"]
    elif final.exists():
        raise RuntimeError("final checkpoint without own progress; cannot resume safely")
    if final.exists():
        require(source_done == budget and episode_done == EPISODES,
                "final checkpoint appeared before training completed")
        saved_final = torch.load(final, map_location=dev, weights_only=False)
        require((saved_final["arm"], saved_final["seed"], saved_final["budget"]) ==
                (arm, seed, budget) and
                saved_final["registration_sha256"] == registration_hash and
                saved_final["panel_seal_sha256"] == panel_hash,
                "final checkpoint identity/protocol mismatch")
        for name, value in net.state_dict().items():
            require(torch.equal(value, saved_final["state"][name]),
                    f"final checkpoint differs from own progress: {name}")
        if patch is None:
            require(saved_final["patch"] is None, "unexpected final patch")
        else:
            require(torch.equal(patch.A, saved_final["patch"].A) and
                    torch.equal(patch.B, saved_final["patch"].B),
                    "final patch differs from own progress")
    started = time.perf_counter()

    def checkpoint():
        P.sync(dev)
        torch_save(torch, progress, {"identity": (arm, seed, budget), "phase": phase,
            "registration_sha256": registration_hash, "panel_seal_sha256": panel_hash,
            "state": net.state_dict(), "patch": P.detached(patch),
            "optimizer": opt.state_dict(), "scheduler": sch.state_dict(),
            "source_rng": source_rng.getstate(), "source_round_rng": source_round_rng.getstate(),
            "episode_rng": episode_rng.getstate(), "episode_round_rng": episode_round_rng.getstate(),
            "torch_rng": torch_rng(torch), "source_done": source_done,
            "episode_done": episode_done, "operations": operations,
            "matrix_operations": meter.counts,
            "initial_state_sha256": initial_state_sha256,
            "source_chain": source_chain, "source_prefix_18k": source_prefix_18k,
            "episode_chain": episode_chain,
            "training_seconds": prior_seconds + time.perf_counter() - started})

    for step in range(source_done + 1, budget + 1):
        net.train()
        kind = source_rng.choice(KINDS)
        items = D.batch(kind, source_rng, BATCH, exclude=ban)
        source_chain = chain(source_chain, [kind, [D.fingerprint(it) for it in items]])
        if step == 18000:
            source_prefix_18k = source_chain
        objective = P.loss(net, items, source_round_rng, dev, patch)
        P.update(opt, sch, objective, net)
        source_done = step
        operations["supervised_optimizer_steps"] += 1
        operations["supervised_examples"] += BATCH
        if step % 250 == 0:
            print(json.dumps({"arm": arm, "seed": seed, "budget": budget,
                              "phase": "source", "step": step,
                              "loss": float(objective.detach())}), flush=True)
        if step % 1000 == 0:
            checkpoint()
    if phase == "source":
        require(source_done == budget, "source phase incomplete")
        checkpoint()  # clean source boundary before diagnostics
        training_counts = dict(meter.counts)
        meter.close()
        pre_raw = directory / "pre-episode-dev-raw.jsonl"
        pre_dev = P.evaluate(net, all_panels["dev"], dev, patch, pre_raw)
        write(directory / "pre-episode-dev.json", {"counts": pre_dev,
              "raw_sha256": sha(pre_raw), "source_steps": budget})
        meter = P.ComputeMeter(net)
        meter.counts = training_counts
        opt, sch = P.optimizer(net, EPISODES)
        phase = "episodes"
        checkpoint()

    for episode in range(episode_done + 1, EPISODES + 1):
        supports, queries = episode_evidence(D, episode_rng, ban)
        episode_chain = chain(episode_chain, [[D.fingerprint(it) for group in supports + queries
                                                for it in group]])
        net.train()
        if arm == "patch":
            for i, items in enumerate(supports):
                if i == 2:
                    patch = P.detached(patch)
                t, s, y = P.tensors(items, dev)
                free, grad = P.schedule(episode_round_rng)
                patch = net.write_support(t, s, y, patch, n_free=free, n_grad=grad)
                meter.counts["feedback_forward_macs"] += t.numel() * D.VOCAB * N.WIDTH
            objective = sum(P.loss(net, items, episode_round_rng, dev, patch) for items in queries)
            operations["support_writes"] += 4
        elif arm in ("loop_meta", "plain"):
            base = dict(net.named_parameters())
            params = dict(base)
            for i, items in enumerate(supports):
                inner = P.loss(net, items, episode_round_rng, dev, params=params)
                grads = torch.autograd.grad(inner, tuple(params.values()), create_graph=i >= 2)
                params = {name: p - 0.01 * g for (name, p), g in zip(params.items(), grads)}
                if i < 2:
                    params = {name: base[name] + (p - base[name]).detach() for name, p in params.items()}
            objective = sum(P.loss(net, items, episode_round_rng, dev, params=params) for items in queries)
            operations["inner_gradient_steps"] += 4
        else:
            objective = torch.stack([P.loss(net, items, episode_round_rng, dev)
                                     for items in supports + queries]).mean()
        P.update(opt, sch, objective, net)
        patch = P.detached(patch)
        episode_done = episode
        operations["episode_optimizer_steps"] += 1
        operations["support_examples"] += 4
        operations["query_examples"] += 16
        if episode % 100 == 0:
            print(json.dumps({"arm": arm, "seed": seed, "budget": budget,
                              "phase": "episodes", "step": episode,
                              "loss": float(objective.detach())}), flush=True)
            checkpoint()
    require(episode_done == EPISODES and source_done == budget, "incomplete run")
    checkpoint()  # own recovery point if final development scoring is interrupted
    final_raw = directory / "final-dev-raw.jsonl"
    final_dev = P.evaluate(net, all_panels["dev"], dev, patch, final_raw)
    write(directory / "final-dev.json", {"counts": final_dev, "raw_sha256": sha(final_raw)})
    P.sync(dev)
    seconds = prior_seconds + time.perf_counter() - started
    meter.close()
    if not final.exists():
        torch_save(torch, final, {"state": net.state_dict(), "patch": P.detached(patch),
                                 "arm": arm, "seed": seed, "budget": budget,
                                 "registration_sha256": registration_hash,
                                 "panel_seal_sha256": panel_hash})
    write(directory / "training.json", {"utc": utc(), "arm": arm, "seed": seed,
        "budget": budget, "batch": BATCH, "episodes": EPISODES,
        "final_sha256": sha(final), "pre_episode_dev_sha256": sha(directory / "pre-episode-dev.json"),
        "final_dev_sha256": sha(directory / "final-dev.json"),
        "registration_sha256": registration_hash, "panel_seal_sha256": panel_hash,
        "torch": torch.__version__, "device": dev, "dtype": "float32", "autocast": False,
        "training_seconds": seconds, "operations": operations,
        "initial_state_sha256": initial_state_sha256,
        "source_chain": source_chain, "source_prefix_18k": source_prefix_18k,
        "episode_chain": episode_chain,
        "source_round_state_sha256": hashlib.sha256(repr(source_round_rng.getstate()).encode()).hexdigest(),
        "episode_round_state_sha256": hashlib.sha256(repr(episode_round_rng.getstate()).encode()).hexdigest(),
        "matrix_operations": meter.counts})


def run_inventory() -> dict:
    registration()
    panels()
    runs = {}
    for seed in SEEDS:
        for arm in ARMS:
            for budget in BUDGETS:
                directory = run_dir(arm, seed, budget)
                meta = read(directory / "training.json")
                require((meta["arm"], meta["seed"], meta["budget"]) ==
                        (arm, seed, budget), "training identity mismatch")
                require(meta["registration_sha256"] == sha(OUT / "REGISTRATION.json") and
                        meta["panel_seal_sha256"] == sha(OUT / "PANEL-SEAL.json"),
                        "training provenance mismatch")
                files = {name: sha(directory / name) for name in
                         ("final.pt", "training.json", "pre-episode-dev.json",
                          "pre-episode-dev-raw.jsonl", "final-dev.json", "final-dev-raw.jsonl")}
                require(files["final.pt"] == meta["final_sha256"] and
                        files["pre-episode-dev.json"] == meta["pre_episode_dev_sha256"] and
                        files["final-dev.json"] == meta["final_dev_sha256"],
                        "training artifact mismatch")
                require(read(directory / "pre-episode-dev.json")["raw_sha256"] ==
                        files["pre-episode-dev-raw.jsonl"] and
                        read(directory / "final-dev.json")["raw_sha256"] ==
                        files["final-dev-raw.jsonl"], "development raw mismatch")
                require(meta["operations"]["supervised_optimizer_steps"] == budget and
                        meta["operations"]["episode_optimizer_steps"] == EPISODES,
                        "incomplete training operations")
                runs[directory.name] = files
    require(len(runs) == 16, "all 16 fresh checkpoints required")
    for seed in SEEDS:
        by_arm = {arm: {budget: read(run_dir(arm, seed, budget) / "training.json")
                         for budget in BUDGETS} for arm in ARMS}
        for arm, paired in by_arm.items():
            require(paired[18000]["initial_state_sha256"] == paired[36000]["initial_state_sha256"],
                    f"unmatched initial torch state: {arm}/{seed}")
            require(paired[18000]["source_chain"] == paired[36000]["source_prefix_18k"],
                    f"unmatched supervised prefix: {arm}/{seed}")
            require(paired[18000]["episode_chain"] == paired[36000]["episode_chain"] and
                    paired[18000]["episode_round_state_sha256"] ==
                    paired[36000]["episode_round_state_sha256"],
                    f"unmatched episode examples/rounds: {arm}/{seed}")
        for budget in BUDGETS:
            require(len({by_arm[arm][budget]["episode_chain"] for arm in ARMS}) == 1 and
                    len({by_arm[arm][budget]["episode_round_state_sha256"] for arm in ARMS}) == 1,
                    f"arms saw different episode evidence: {seed}/{budget}")
            require(len({by_arm[arm][budget]["source_chain"] for arm in ARMS}) == 1,
                    f"arms saw different source evidence: {seed}/{budget}")
            require(len({by_arm[arm][budget]["source_round_state_sha256"] for arm in ARMS}) == 1,
                    f"arms saw different supervised round schedules: {seed}/{budget}")
    return runs


def register_runs():
    runs = run_inventory()
    path = OUT / "RUN-REGISTRY.json"
    require(not path.exists(), "run registry already exists; immutable")
    write(path, {"utc": utc(), "registration_sha256": sha(OUT / "REGISTRATION.json"),
                 "panel_seal_sha256": sha(OUT / "PANEL-SEAL.json"), "runs": runs})


def gates(counts):
    """Pure decision rule: no threshold tuning from observed verification."""
    result = {}
    for budget in BUDGETS:
        seeds = {}
        for seed in SEEDS:
            arms = {arm: counts[f"{arm}-seed{seed}-s{budget}"] for arm in ARMS}
            absolute = {arm: {kind: arms[arm]["verify"][kind]["right"] >=
                        (285 if kind in ("sums", "grids") else 270)
                        for kind in KINDS} for arm in ARMS}
            patch_gap = {control: {kind: arms["patch"]["verify"][kind]["right"] >=
                         arms[control]["verify"][kind]["right"] - 9
                         for kind in KINDS} for control in ("loop", "loop_meta")}
            old_guard = {arm: {kind: arms[arm]["old_guard"][kind]["right"] >= 190
                         for kind in ("sums4", "grids5")} for arm in ARMS}
            passed = (all(all(v.values()) for v in absolute.values()) and
                      all(all(v.values()) for v in patch_gap.values()) and
                      all(all(v.values()) for v in old_guard.values()))
            seeds[str(seed)] = {"absolute_v2": absolute, "patch_gap_v2": patch_gap,
                                "ruler_old_guard": old_guard, "passed": passed}
        result[str(budget)] = {"seeds": seeds,
                               "passed": all(row["passed"] for row in seeds.values())}
    result["longer_budget_restores_full_eligibility"] = result["36000"]["passed"]
    result["falsified_by_any_36k_grid_failure"] = any(
        not result["36000"]["seeds"][str(seed)]["absolute_v2"][arm]["grids"]
        for seed in SEEDS for arm in ARMS)
    return result


def recount_raw(D, path, items, counts):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    expected = [(kind, D.fingerprint(it)) for kind, group in items.items() for it in group]
    require(len(rows) == len(expected), f"raw row count mismatch: {path}")
    observed = {kind: 0 for kind in items}
    for row, (kind, fingerprint) in zip(rows, expected):
        require(row["kind"] == kind and row["fingerprint"] == fingerprint and
                D.fingerprint(D.E.Item(**row["input"])) == fingerprint,
                f"raw panel identity mismatch: {path}")
        require(1 <= row["round"] <= 48, f"invalid halt round: {path}")
        right = bool(D.check(D.E.Item(**row["input"]), row["pred"]))
        require(row["right"] is right, f"raw correctness mismatch: {path}")
        observed[kind] += right
    for kind, group in items.items():
        require(counts[kind]["n"] == len(group) and
                counts[kind]["right"] == observed[kind], f"raw recount mismatch: {path}/{kind}")


def verify():
    inventory = run_inventory()
    registry = read(OUT / "RUN-REGISTRY.json")
    require(registry["registration_sha256"] == sha(OUT / "REGISTRATION.json") and
            registry["panel_seal_sha256"] == sha(OUT / "PANEL-SEAL.json") and
            registry["runs"] == inventory, "all 16 source hashes must be registered before verification")
    require(not (OUT / "VERDICT.json").exists(), "verification already finalized")
    all_panels, _ = panels()
    D, N, P, torch = imports()
    dev = runtime(torch)
    counts = {}
    for seed in SEEDS:
        for arm in ARMS:
            for budget in BUDGETS:
                directory = run_dir(arm, seed, budget)
                saved = torch.load(directory / "final.pt", map_location=dev, weights_only=False)
                require((saved["arm"], saved["seed"], saved["budget"]) ==
                        (arm, seed, budget) and
                        saved["registration_sha256"] == registry["registration_sha256"] and
                        saved["panel_seal_sha256"] == registry["panel_seal_sha256"],
                        "checkpoint identity/protocol mismatch")
                net = N.Net("loop" if arm == "loop_meta" else arm).to(dev).float()
                net.load_state_dict(saved["state"])
                patch = saved["patch"]
                raw_verify = directory / "verify-raw.jsonl"
                raw_guard = directory / "old-guard-raw.jsonl"
                verify_counts = P.evaluate(net, all_panels["verify"], dev, patch, raw_verify)
                guard_counts = P.evaluate(net, all_panels["old_guard"], dev, patch, raw_guard)
                recount_raw(D, raw_verify, all_panels["verify"], verify_counts)
                recount_raw(D, raw_guard, all_panels["old_guard"], guard_counts)
                counts[directory.name] = {"verify": verify_counts, "old_guard": guard_counts,
                    "verify_raw_sha256": sha(raw_verify), "old_guard_raw_sha256": sha(raw_guard),
                    "checkpoint_sha256": inventory[directory.name]["final.pt"]}
                write(directory / "verification.json", counts[directory.name])
                del net, saved
    decision = gates(counts)
    write(OUT / "VERDICT.json", {"utc": utc(), "run_registry_sha256":
          sha(OUT / "RUN-REGISTRY.json"), "counts": counts, "gates": decision,
          "maze_scored": False, "race_result": False,
          "interpretation": "Source-only eligibility; a failed gate remains a recorded failure."})
    print(json.dumps({"verdict": str(OUT / "VERDICT.json"),
                      "36k_eligible": decision["36000"]["passed"]}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("seal-panels", help="Later: create dev/verify/old source guard panels once")
    tr = sub.add_parser("train", help="Later: train exactly one fresh arm/seed/budget; resumes own progress")
    tr.add_argument("--arm", choices=ARMS, required=True)
    tr.add_argument("--seed", type=int, choices=SEEDS, required=True)
    tr.add_argument("--budget", type=int, choices=BUDGETS, required=True)
    sub.add_parser("register", help="Later: lock hashes only after all 16 completed runs")
    sub.add_parser("verify", help="Later: final verification after run registration")
    a = p.parse_args()
    if a.command == "seal-panels":
        seal_panels()
    elif a.command == "train":
        train(a.arm, a.seed, a.budget)
    elif a.command == "register":
        register_runs()
    else:
        verify()


if __name__ == "__main__":
    main()
