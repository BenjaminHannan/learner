"""Per-seed gate G: the six-cell paired scoring suite (Claude, 2026-09-19) -- EVAL ONLY, frozen checkpoints.

Implements the gate G frozen in reviews/astra-deep-dive-2026-09-19/report.md section 6 ("Lock the outcomes
before choosing a branch" / "Common pass marks and power") on the minimal paired suite and the state-isolation
rules of its section 3.  No training, no parameter update, no fitted probe, no GPU, no network.  Nothing outside
artifacts/claude-pairsuite-20260919/ is written, and no existing file is edited: the fresh-world generator, the
label separation, the deterministic interpreter and the native evaluation condition U are imported from
scripts/premonition_handoff_diag.py, the fetch classes from scripts/premonition_first_card_probe.py.

Six cells, all in the NATIVE condition U (= premonition_ovn_retrieval.own_fixed(..., loops=4)), standard spec
(6 people, 3 relations, 16 values, 128-token gap, held-out relation 2), ONE scored question per independently
generated world:

  1 own one-hop                      2,048 worlds   pass >= 1,969
  2 own practised two-hop (rel 0/1)  2,048 worlds   pass >= 1,969
  3 own held-out two-hop (rel 2)     2,048 worlds   pass >= 1,876
  4 held-out changed-link pair       1,024 pairs    pass >= 945 both correct
  5 held-out changed-endpoint pair   1,024 pairs    pass >= 945 both correct   (value swap, inventory preserved)
  6 held-out irrelevant-edit pair    1,024 pairs    pass >= 945 both correct and identical

G passes for a checkpoint iff all six cells pass.  The cutoffs are the smallest counts whose exact one-sided
binomial tail rejects accuracy <= 0.95 (cells 1-2) / <= 0.90 (cells 3-6) at alpha = 0.05/6; `gen` recomputes and
prints them.  Seeds, the generator source hashes and the per-set SHA-256 are written BEFORE any model is loaded.

    PY -B scripts/premonition_pair_suite.py gen
    PY -B scripts/premonition_pair_suite.py score --ckpt-dir DIR [--ckpt-dir DIR ...] [--workers 4] [--limit N]
    PY -B scripts/premonition_pair_suite.py table --group NAME=DIR [--runs NAME=RUNS_DIR] [--compare A B]
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace as dc_replace
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402
import premonition_handoff_diag as H  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402

OUT = L.ROOT / "artifacts" / "claude-pairsuite-20260919"
DATA = OUT / "data"
ROWS = OUT / "rows.jsonl"
SOURCE = Path(__file__).resolve()

LOOPS = H.LOOPS                       # 4 fixed loops, HALT ignored: at most 3 requests
REQUESTS = H.REQUESTS                 # 3
WORLDS_PER_CHUNK = 32
CONDITION = "U"                       # the native condition only; no mask is ever applied here
ALPHA = Fraction(5, 100) / 6          # Bonferroni over the six cells
STUCK_ONE_HOP = 384                   # registered rule: one-hop validation < 384/512 is a stuck run
STUCK_N = 512

# Seeds fixed here, BEFORE any model is loaded; distinct per cell.  Recorded in manifest.json.
CELLS = {
    "c1_own_one_hop": {
        "cell": 1, "seed": 20260919_1001, "n": 2048, "kind": "single", "hops": 1, "relation": "any",
        "null": Fraction(19, 20), "cutoff": 1969, "title": "own one-hop"},
    "c2_own_practised_two_hop": {
        "cell": 2, "seed": 20260919_1002, "n": 2048, "kind": "single", "hops": 2, "relation": "practised",
        "null": Fraction(19, 20), "cutoff": 1969, "title": "own practised two-hop (relations 0/1)"},
    "c3_own_heldout_two_hop": {
        "cell": 3, "seed": 20260919_1003, "n": 2048, "kind": "single", "hops": 2, "relation": "heldout",
        "null": Fraction(9, 10), "cutoff": 1876, "title": "own held-out two-hop (relation 2)"},
    "c4_changed_link": {
        "cell": 4, "seed": 20260919_1004, "n": 1024, "kind": "pair", "edit": "link", "token_diffs": 1,
        "invariant": False, "null": Fraction(9, 10), "cutoff": 945, "title": "held-out changed-link pair"},
    "c5_changed_endpoint_value": {
        "cell": 5, "seed": 20260919_1005, "n": 1024, "kind": "pair", "edit": "endpoint", "token_diffs": 2,
        "invariant": False, "null": Fraction(9, 10), "cutoff": 945,
        "title": "held-out changed-endpoint-value pair (inventory-preserving swap)"},
    "c6_irrelevant_edit": {
        "cell": 6, "seed": 20260919_1006, "n": 1024, "kind": "pair", "edit": "irrelevant", "token_diffs": 2,
        "invariant": True, "null": Fraction(9, 10), "cutoff": 945,
        "title": "held-out irrelevant-edit pair (inventory-preserving swap off the chain)"},
}
SHORTCUTS = ("question_blind_modal", "relation_only", "direct_question_subject")
SKIPPED = ["12-person, three-lookup and longer-gap stress cells", "full store wipe / restore lesion",
           "train-stream overlap reconstruction (overlap coverage: not checked)",
           "learned-halting variant (fixed four loops only)"]


# ------------------------------------------------------------------------------------------ exact statistics
def binom_tail_ge(n: int, c: int, p: Fraction) -> Fraction:
    """P(X >= c) for X ~ Binomial(n, p), exactly."""
    if c <= 0:
        return Fraction(1)
    return sum((Fraction(math.comb(n, k)) * p ** k * (1 - p) ** (n - k) for k in range(c, n + 1)), Fraction(0))


def smallest_rejecting_count(n: int, p0: Fraction, alpha: Fraction) -> int:
    """The smallest c with P(X >= c | n, p0) <= alpha: the exact one-sided cutoff rejecting accuracy <= p0."""
    total = Fraction(0)
    for c in range(n + 1, 0, -1):
        total += Fraction(math.comb(n, c - 1)) * p0 ** (c - 1) * (1 - p0) ** (n - c + 1)
        if total > alpha:
            return c
    return 0


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for [[a, b], [c, d]], probability ordering, by exact integer comparison."""
    n, row1, col1 = a + b + c + d, a + b, a + c
    if n == 0:
        return 1.0
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    weight = {k: math.comb(row1, k) * math.comb(n - row1, col1 - k) for k in range(lo, hi + 1)}
    observed = weight[a]
    return float(Fraction(sum(w for w in weight.values() if w <= observed), sum(weight.values())))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list:
    """95% Wilson score interval (z is the exact two-sided 0.95 normal quantile)."""
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def verify_cutoffs() -> dict:
    """Recompute every cell's cutoff from scratch; the frozen value is used for scoring either way."""
    out = {}
    for name, cfg in CELLS.items():
        computed = smallest_rejecting_count(cfg["n"], cfg["null"], ALPHA)
        out[name] = {"n": cfg["n"], "null_accuracy": float(cfg["null"]), "alpha": float(ALPHA),
                     "frozen_cutoff": cfg["cutoff"], "computed_cutoff": computed,
                     "agrees": computed == cfg["cutoff"],
                     "tail_at_frozen_cutoff": float(binom_tail_ge(cfg["n"], cfg["cutoff"], cfg["null"])),
                     "tail_one_below": float(binom_tail_ge(cfg["n"], cfg["cutoff"] - 1, cfg["null"]))}
    return out


# --------------------------------------------------------------------------------------- fresh paired worlds
def _target_question(lines, hops: int, mode: str, heldout: int):
    """Index of the scored question line: the first question of this kind in the visit."""
    for k, line in enumerate(lines):
        if not line.question or line.hops != hops:
            continue
        if hops == 2 and mode == "heldout" and line.relation != heldout:
            continue
        if hops == 2 and mode == "practised" and line.relation == heldout:
            continue
        return k
    return None


def _make_single(spec, rng, hops: int, mode: str):
    """One world with one scored question.  -> (lines, target line, facts, rejections)."""
    from premonition import toy_ladder
    rejections = Counter()
    while True:
        lines, world, _plan = toy_ladder.visit(spec, rng, training=False)
        k = _target_question(lines, hops, mode, spec.heldout_relation)
        if k is None:
            rejections["no_target_question"] += 1
            continue
        a, r = lines[k].ents[0], lines[k].relation
        dest = world.friend[a] if hops == 2 else -1
        holder = dest if hops == 2 else a
        return lines, k, {"subject": a, "relation": r, "dest_a": dest,
                          "value_a": world.attr[(holder, r)]}, rejections


def _make_pair(spec, rng, edit: str):
    """One independently generated world pair on a held-out two-hop question, by rejection sampling.

    link       the asked person's friend becomes another person whose target value differs (answer changes)
    endpoint   the friend's relation-2 value is SWAPPED with that of a third person, value differs (answer changes)
    irrelevant the relation-2 values of two people outside {asker, friend} are swapped (answer must not change)

    Both value edits are swaps, so the world's value inventory is identical in the two twins and an
    answer-frequency ("bag of values") strategy gains nothing.  -> (lines_a, lines_b, line, facts, rejections)
    """
    from premonition import toy_ladder
    heldout = spec.heldout_relation
    rejections = Counter()
    while True:
        lines, world, plan = toy_ladder.visit(spec, rng, training=False)
        k = _target_question(lines, 2, "heldout", heldout)
        if k is None:
            rejections["no_heldout_two_hop_question"] += 1
            continue
        a, r = lines[k].ents[0], lines[k].relation
        b = world.friend[a]
        edited = deepcopy(world)
        if edit == "link":
            options = [x for x in world.ents if x not in (a, b) and world.attr[(x, r)] != world.attr[(b, r)]]
            if not options:
                rejections["no_alternative_friend"] += 1
                continue
            new_b = rng.choice(options)
            edited.friend[a] = new_b
            dest_b, value_b, detail = new_b, world.attr[(new_b, r)], {"new_friend": new_b}
        elif edit == "endpoint":
            options = [x for x in world.ents if x not in (a, b) and world.attr[(x, r)] != world.attr[(b, r)]]
            if not options:
                rejections["no_endpoint_swap_partner"] += 1
                continue
            x = rng.choice(options)
            edited.attr[(b, r)], edited.attr[(x, r)] = world.attr[(x, r)], world.attr[(b, r)]
            dest_b, value_b, detail = b, world.attr[(x, r)], {"swapped_with": x}
        elif edit == "irrelevant":
            pool = [x for x in world.ents if x not in (a, b)]
            candidates = [(x, y) for x, y in itertools.combinations(pool, 2)
                          if world.attr[(x, r)] != world.attr[(y, r)]]
            if not candidates:
                rejections["no_irrelevant_swap_pair"] += 1
                continue
            x, y = rng.choice(candidates)
            edited.attr[(x, r)], edited.attr[(y, r)] = world.attr[(y, r)], world.attr[(x, r)]
            dest_b, value_b, detail = b, world.attr[(b, r)], {"swapped": [x, y]}
        else:
            raise ValueError(edit)
        new_lines, _, _ = toy_ladder.visit(spec, rng, training=False, world=edited, plan=plan)
        if _target_question(new_lines, 2, "heldout", heldout) != k:
            rejections["replay_moved_the_question"] += 1
            continue
        changed = new_lines[k].answer[0] != lines[k].answer[0]
        if edit == "irrelevant" and changed:
            rejections["irrelevant_edit_changed_the_answer"] += 1
            continue
        if edit != "irrelevant" and not changed:
            rejections["target_value_unchanged"] += 1
            continue
        if sorted(world.attr.values()) != sorted(edited.attr.values()):
            rejections["value_inventory_not_preserved"] += 1
            continue
        facts = {"subject": a, "relation": r, "dest_a": b, "dest_b": dest_b,
                 "value_a": world.attr[(b, r)], "value_b": value_b, "edit_detail": detail}
        return lines, new_lines, k, facts, rejections


def generate_set(name: str, *, spec=None) -> dict:
    """Build one cell.  Model-free: no checkpoint is touched and no label ever reaches a model here."""
    import torch
    from premonition import toy_ladder
    from premonition.train import label_free
    spec = spec or L.spec()
    cfg = CELLS[name]
    pair = cfg["kind"] == "pair"
    sides = ("a", "b") if pair else ("a",)
    rejections, target_values, worlds = Counter(), Counter(), []
    for i in range(cfg["n"]):
        rng = random.Random(f"premonition-pairsuite-{name}-{cfg['seed']}-{i}")
        if pair:
            lines_a, lines_b, line, facts, rej = _make_pair(spec, rng, cfg["edit"])
            target_values[facts["value_a"]] += 1
            target_values[facts["value_b"]] += 1
        else:
            lines_a, line, facts, rej = _make_single(spec, rng, cfg["hops"], cfg["relation"])
            lines_b = None
            target_values[facts["value_a"]] += 1
        rejections.update(rej)
        worlds.append((lines_a, lines_b, line, facts, i))
    chunks = []
    for start in range(0, len(worlds), WORLDS_PER_CHUNK):
        block = worlds[start:start + WORLDS_PER_CHUNK]
        rows = {"a": [w[0] for w in block]}
        if pair:
            rows["b"] = [w[1] for w in block]
        full = {s: label_free(toy_ladder.assemble(spec, rows[s], prefix=f"{name}-{s}-{start}")[0]) for s in sides}
        if pair:
            if full["a"].tokens.shape != full["b"].tokens.shape:
                raise SystemExit(f"{name}: the twins have different token shapes")
            differing = (full["a"].tokens != full["b"].tokens).sum(1).tolist()
            if differing != [cfg["token_diffs"]] * len(block):
                raise SystemExit(f"{name}: twins differ in {sorted(set(differing))} visible tokens, "
                                 f"expected {cfg['token_diffs']}")
        keep, meta = {s: [] for s in sides}, []
        for v, (_la, _lb, line, facts, index) in enumerate(block):
            row = {"index": index, "visit": v, "line": line, "hops": 1 if cfg.get("hops") == 1 else 2,
                   "cell": cfg["cell"], **facts}
            for s in sides:
                q = int(((full[s].q_visit == v) & (full[s].q_line == line)).nonzero()[0])
                keep[s].append(q)
                row[f"answer_{s}"] = full[s].answer[q][full[s].answer[q] != -100].tolist()
                row[f"gold_{s}"] = [x for x in full[s].gold_lines[q].tolist() if x >= 0]
                row[f"key_{s}"] = f"{name}|{index}|{s}"
            meta.append(row)
        chunk = {s: H._keep_questions(full[s], keep[s]) for s in sides}
        chunk["meta"] = meta
        chunks.append(chunk)
    return {"name": name, "cell": cfg["cell"], "kind": cfg["kind"], "seed": cfg["seed"], "n": cfg["n"],
            "hops": cfg.get("hops", 2), "relation": cfg.get("relation", "heldout"), "edit": cfg.get("edit"),
            "invariant": bool(cfg.get("invariant")), "chunks": chunks,
            "rejections": dict(sorted(rejections.items())),
            "target_value_counts": {str(k): v for k, v in sorted(target_values.items())},
            "worlds_per_chunk": WORLDS_PER_CHUNK}


# --------------------------------------------------------------------------------------- model-free auditing
def audit_set(dataset: dict, spec) -> dict:
    """The exact tuple interpreter (must be 100%) and the three deterministic shortcut ceilings."""
    sides = ("a", "b") if dataset["kind"] == "pair" else ("a",)
    interp = [0, 0]
    joint_interp = 0
    det = {s: [0, 0] for s in SHORTCUTS}
    exp = {s: 0.0 for s in SHORTCUTS}
    joint_det = {s: 0 for s in SHORTCUTS}
    joint_exp = {s: 0.0 for s in SHORTCUTS}
    failures = []
    for chunk in dataset["chunks"]:
        views = {s: H.FieldView(chunk[s], spec) for s in sides}
        for q, meta in enumerate(chunk["meta"]):
            both, both_det, both_exp = True, {s: True for s in SHORTCUTS}, {s: 1.0 for s in SHORTCUTS}
            for side in sides:
                target = meta[f"value_{side}"]
                got = H.interpret(views[side], q)
                interp[1] += 1
                interp[0] += int(got == target)
                if got != target:
                    failures.append({"index": meta["index"], "side": side, "got": got, "want": target})
                    both = False
                for name, (hit, rate) in H.shortcut_strategies(views[side], q, target).items():
                    det[name][1] += 1
                    det[name][0] += int(hit)
                    exp[name] += rate
                    both_det[name] &= hit
                    both_exp[name] *= rate
            joint_interp += int(both)
            for name in SHORTCUTS:
                joint_det[name] += int(both_det[name])
                joint_exp[name] += both_exp[name]
    n = dataset["n"]
    return {"interpreter": {"single_answer": interp[0], "answers": interp[1],
                            "accuracy": round(interp[0] / max(interp[1], 1), 6),
                            "scored_units_correct": joint_interp, "scored_units": n,
                            "unit_accuracy": round(joint_interp / max(n, 1), 6), "failures": failures[:8]},
            "shortcut_ceilings": {
                name: {"single_deterministic": round(det[name][0] / max(det[name][1], 1), 4),
                       "single_expected_uniform": round(exp[name] / max(det[name][1], 1), 4),
                       "unit_deterministic": round(joint_det[name] / max(n, 1), 4),
                       "unit_expected_uniform": round(joint_exp[name] / max(n, 1), 4)} for name in SHORTCUTS}}


# ------------------------------------------------------------------------------------------- gen and loading
def manifest_path() -> Path:
    return OUT / "manifest.json"


def load_manifest() -> dict:
    if not manifest_path().exists():
        raise SystemExit(f"no manifest at {manifest_path()}; run `gen` first")
    return json.loads(manifest_path().read_text())


def recorded_path(path: Path) -> str:
    """Repository-relative where possible, absolute otherwise."""
    try:
        return str(path.relative_to(L.ROOT))
    except ValueError:
        return str(path)


def resolve_recorded(recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else L.ROOT / path


def load_set(name: str, manifest: dict):
    import torch
    info = manifest["cells"][name]
    path = resolve_recorded(info["file"])
    if H.sha256_file(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the manifest freeze")
    return torch.load(path, weights_only=False)


def cmd_gen(args) -> None:
    """Fresh worlds from the seeds fixed in this file.  No checkpoint is loaded and no model is built."""
    import torch
    spec = L.spec()
    DATA.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    cutoffs = verify_cutoffs()
    print("cutoff verification (exact one-sided binomial tails, alpha = 0.05/6 = "
          f"{float(ALPHA):.6f}):")
    for name, row in cutoffs.items():
        flag = "ok" if row["agrees"] else f"DISCREPANCY (computed {row['computed_cutoff']})"
        print(f"  cell {CELLS[name]['cell']} {name:26s} n={row['n']:5d} reject acc <= "
              f"{row['null_accuracy']:.2f}  cutoff {row['frozen_cutoff']}  "
              f"P(X>=cutoff)={row['tail_at_frozen_cutoff']:.3e}  "
              f"P(X>=cutoff-1)={row['tail_one_below']:.3e}  {flag}", flush=True)
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "purpose": "per-seed gate G: six-cell paired suite, native condition U, frozen checkpoints",
        "written_before_any_model_was_loaded": True,
        "generator_sources": {
            "scripts/premonition_pair_suite.py": H.sha256_file(SOURCE),
            "scripts/premonition_handoff_diag.py": H.sha256_file(H.SOURCE),
            "scripts/premonition_first_card_probe.py": H.sha256_file(Path(P.__file__).resolve()),
            "frozen/premonition/toy_ladder.py": H.sha256_file(
                L.ARCHIVE / "frozen" / "premonition" / "toy_ladder.py")},
        "spec": {k: getattr(spec, k) for k in ("entities", "relations", "values", "fillers", "distractors",
                                               "gap", "one_hop", "two_hop", "heldout_relation")},
        "loops": LOOPS, "requests": REQUESTS, "condition": CONDITION,
        "worlds_per_chunk": WORLDS_PER_CHUNK, "alpha": float(ALPHA), "cutoff_verification": cutoffs,
        "gate": "G passes iff all six cells reach their cutoff", "skipped": SKIPPED, "cells": {}}
    for name, cfg in CELLS.items():
        t0 = time.perf_counter()
        data = generate_set(name, spec=spec)
        audit = audit_set(data, spec)
        if audit["interpreter"]["accuracy"] != 1.0:
            raise SystemExit(f"{name}: the deterministic interpreter does not answer every example "
                             f"({audit['interpreter']['single_answer']}/{audit['interpreter']['answers']}); "
                             f"first failures {audit['interpreter']['failures']}")
        path = DATA / f"{name}.pt"
        torch.save(data, path)
        manifest["cells"][name] = {
            "cell": cfg["cell"], "title": cfg["title"], "seed": cfg["seed"], "n": cfg["n"], "kind": cfg["kind"],
            "hops": data["hops"], "relation": data["relation"], "edit": data["edit"],
            "invariant": data["invariant"], "null_accuracy": float(cfg["null"]), "cutoff": cfg["cutoff"],
            "file": recorded_path(path), "sha256": H.sha256_file(path),
            "bytes": path.stat().st_size, "rejections": data["rejections"],
            "target_value_counts": data["target_value_counts"], "audit": audit,
            "seconds": round(time.perf_counter() - t0, 2)}
        print(f"{name:26s} {cfg['n']:5d} units  rejections {data['rejections']}  "
              f"interpreter {audit['interpreter']['unit_accuracy']:.4f}  "
              f"{round(time.perf_counter() - t0, 1)}s", flush=True)
    manifest["seconds"] = round(time.perf_counter() - started, 2)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(manifest, indent=1))
    print("\nwrote", manifest_path(), "sha256", H.sha256_file(manifest_path()))
    print("shortcut ceilings, both-member (pair) units:")
    for name in CELLS:
        row = manifest["cells"][name]["audit"]["shortcut_ceilings"]
        print(f"  {name:26s} " + "  ".join(
            f"{s}: det {row[s]['unit_deterministic']:.4f} / unif {row[s]['unit_expected_uniform']:.4f}"
            for s in SHORTCUTS))


# --------------------------------------------------------------------------------------------------- scoring
def _single_visit(batch, v: int, q: int):
    """A one-visit, one-question batch carved out of `batch`: the state-isolation control.

    Token width and padding are unchanged, so the only difference from the full chunk is that the other
    worlds and their questions are absent.
    """
    import torch
    return dc_replace(
        batch, tokens=batch.tokens[v:v + 1], line_of=batch.line_of[v:v + 1], card_end=batch.card_end[v:v + 1],
        lengths=batch.lengths[v:v + 1], lm_mask=batch.lm_mask[v:v + 1],
        line_is_question=batch.line_is_question[v:v + 1], line_start=batch.line_start[v:v + 1],
        line_ents=batch.line_ents[v:v + 1], q_visit=torch.zeros(1, dtype=torch.long),
        q_line=batch.q_line[q:q + 1], q_span=batch.q_span[q:q + 1], answer=batch.answer[q:q + 1],
        gold_lines=batch.gold_lines[q:q + 1], depth=batch.depth[q:q + 1],
        question_ids=[batch.question_ids[q]], names=[batch.names[v]], slices=None)


def _fetch_classes(batch, res, metas, spec) -> dict:
    """Per request: the fetch class of the card actually taken (premonition_first_card_probe.classify)."""
    counters = [Counter() for _ in range(REQUESTS)]
    requests = [0] * REQUESTS
    both_gold = 0
    store_lines = res["store_lines"]
    cards = res["cards"]
    for q, meta in enumerate(metas):
        v = int(batch.q_visit[q])
        asker, friend = meta["subject"], meta["dest_a"]
        relation_token = spec.relation(meta["relation"])
        fetched = set()
        for step in range(REQUESTS):
            line = int(cards[q, step])
            if line < 0:
                counters[step]["no_request"] += 1
                continue
            requests[step] += 1
            if line >= store_lines:
                counters[step]["null_card"] += 1
                continue
            start = int(batch.line_start[v, line])
            tokens = batch.tokens[v, start:start + 4].tolist()
            counters[step][P.classify(tokens, asker, friend, relation_token, spec.link, spec.vocab_size)] += 1
            fetched.add(line)
        gold = meta["gold_a"]
        both_gold += int(bool(gold) and all(g in fetched for g in gold))
    out = {"requests_made_per_step": requests, "requests_made": sum(requests),
           "both_gold_cards_fetched": both_gold, "questions": len(metas), "by_request": {}}
    for step, counter in enumerate(counters):
        out["by_request"][f"request{step + 1}"] = {
            "classes": dict(counter.most_common()),
            "right_person": sum(counter[c] for c in P.RIGHT_PERSON),
            "right_relation": sum(counter[c] for c in P.RIGHT_REL),
            "right_both": counter["answer"], "correct_link_card": counter["link"],
            "total_requests": requests[step]}
    return out


def score_cell(model, dataset: dict, spec, *, diagnostics: bool = False) -> dict:
    """Condition U over one cell.  State is rebuilt from scratch for every chunk, and twins never share one."""
    import torch
    sides = ("a", "b") if dataset["kind"] == "pair" else ("a",)
    correct = {s: [] for s in sides}
    produced = {s: [] for s in sides}
    diag = None
    with torch.no_grad():
        for chunk in dataset["chunks"]:
            metas = chunk["meta"]
            for side in sides:
                batch = H._strip_labels(chunk[side])          # the model only ever sees the diary
                fields = H.FieldView(batch, spec)
                keys = [m[f"key_{side}"] for m in metas]
                res = H.run_condition(model, batch, fields, CONDITION, keys)
                correct[side].append(H.correctness(res, [m[f"answer_{side}"] for m in metas]))
                produced[side].extend([res["tokens"][q, :int(res["lengths"][q])].tolist()
                                       for q in range(len(metas))])
                if diagnostics and side == "a":
                    block = _fetch_classes(batch, res, metas, spec)
                    if diag is None:
                        diag = block
                    else:
                        diag["requests_made"] += block["requests_made"]
                        diag["both_gold_cards_fetched"] += block["both_gold_cards_fetched"]
                        diag["questions"] += block["questions"]
                        diag["requests_made_per_step"] = [x + y for x, y in
                                                          zip(diag["requests_made_per_step"],
                                                              block["requests_made_per_step"])]
                        for key, value in block["by_request"].items():
                            slot = diag["by_request"][key]
                            merged = Counter(slot["classes"])
                            merged.update(value["classes"])
                            slot["classes"] = dict(merged.most_common())
                            for field in ("right_person", "right_relation", "right_both",
                                          "correct_link_card", "total_requests"):
                                slot[field] += value[field]
    ok = {s: torch.cat(correct[s]) for s in sides}
    out = {"n": dataset["n"], "single_correct": {s: int(ok[s].sum()) for s in sides}}
    if dataset["kind"] == "pair":
        identical = torch.tensor([x == y for x, y in zip(produced["a"], produced["b"])])
        both = ok["a"] & ok["b"]
        out["identical_answers"] = int(identical.sum())
        out["both_correct"] = int(both.sum())
        out["count"] = int((both & identical).sum()) if dataset["invariant"] else int(both.sum())
    else:
        out["count"] = int(ok["a"].sum())
    if diag is not None:
        out["diagnostics"] = diag
    return out


def own_fixed_parity(model, dataset: dict, spec) -> dict:
    """Condition U must reproduce premonition_ovn_retrieval.own_fixed(..., loops=4): answers AND fetched lines."""
    import torch
    chunk = dataset["chunks"][0]
    batch = chunk["a"]
    metas = chunk["meta"]
    with torch.no_grad():
        ok_hist, _gold, fetched_hist = H.traced_own_fixed(model, batch, LOOPS)
        blind = H._strip_labels(batch)
        res = H.run_condition(model, blind, H.FieldView(blind, spec), CONDITION,
                              [m["key_a"] for m in metas])
        ok_mine = H.correctness(res, [m["answer_a"] for m in metas])
    n = int(ok_hist.shape[0])
    answers = int((ok_mine == ok_hist).sum())
    fetches = int((res["cards"] == fetched_hist).all(1).sum())
    return {"questions": n, "answers_equal": answers, "fetched_lines_equal": fetches,
            "pass": answers == n and fetches == n}


def world_isolation(model, dataset: dict, spec, *, sample: int = 4) -> dict:
    """Scoring a world on its own must give the same answer and the same fetches as inside the chunk."""
    import torch
    chunk = dataset["chunks"][0]
    metas = chunk["meta"]
    blind = H._strip_labels(chunk["a"])
    same = total = 0
    with torch.no_grad():
        full = H.run_condition(model, blind, H.FieldView(blind, spec), CONDITION,
                               [m["key_a"] for m in metas])
        for q in range(min(sample, len(metas))):
            alone = _single_visit(blind, int(blind.q_visit[q]), q)
            part = H.run_condition(model, alone, H.FieldView(alone, spec), CONDITION, [metas[q]["key_a"]])
            total += 1
            same += int(full["tokens"][q].tolist() == part["tokens"][0].tolist()
                        and full["cards"][q].tolist() == part["cards"][0].tolist())
    return {"worlds": total, "identical": same, "pass": same == total}


def score_checkpoint(path: Path, manifest: dict, datasets: dict, spec) -> dict:
    """Every cell for one frozen checkpoint.  -> one JSON row."""
    name = path.stem
    started = time.perf_counter()
    digest = H.sha256_file(path)
    run_json = path.parent.parent / "runs" / f"{name}.json"
    recorded = json.loads(run_json.read_text()) if run_json.exists() else None
    model, blob = P.load_from(name, path.parent)
    before = P.fingerprint(model)
    cells, passes = {}, {}
    for cell_name, dataset in datasets.items():
        result = score_cell(model, dataset, spec, diagnostics=CELLS[cell_name]["cell"] == 3)
        cells[cell_name] = result
        passes[cell_name] = bool(result["count"] >= CELLS[cell_name]["cutoff"])
    integrity = {"own_fixed_parity": own_fixed_parity(model, datasets["c1_own_one_hop"], spec),
                 "label_perturbation": H.label_perturbation_check(
                     model, {"chunks": [datasets["c4_changed_link"]["chunks"][0]]}, spec),
                 "world_isolation": world_isolation(model, datasets["c3_own_heldout_two_hop"], spec)}
    after = P.fingerprint(model)
    integrity["weights_fingerprint"] = before
    integrity["weights_unchanged"] = bool(before == after)
    integrity["run_json"] = ("missing" if recorded is None else
                             ("sha256 matches" if recorded.get("ckpt_sha256") == digest else
                              f"sha256 MISMATCH: run json says {recorded.get('ckpt_sha256')}"))
    if not integrity["weights_unchanged"]:
        raise SystemExit(f"{name}: parameters changed during evaluation")
    return {"ckpt": str(path.resolve()), "dir": str(path.parent.resolve()), "name": name, "sha256": digest,
            "manifest_sha256": H.sha256_file(manifest_path()), "model_class": blob.get("model_class"),
            "relation_shortcut": bool(blob.get("relation_shortcut")), "key_pool": bool(blob.get("key_pool")),
            "train_seed": blob.get("seed"),
            "parameters": sum(p.numel() for p in model.parameters()),
            "counts": {k: v["count"] for k, v in cells.items()},
            "cutoffs": {k: CELLS[k]["cutoff"] for k in cells},
            "cell_pass": passes, "G": bool(all(passes.values())), "cells": cells,
            "integrity": integrity, "seconds": round(time.perf_counter() - started, 2)}


# ------------------------------------------------------------------------------------------ score subcommand
_G: dict = {}


def _init_worker(manifest_text: str) -> None:
    L.bootstrap()
    import torch
    torch.set_num_threads(1)
    manifest = json.loads(manifest_text)
    _G["manifest"] = manifest
    _G["spec"] = L.spec()
    _G["data"] = {name: load_set(name, manifest) for name in CELLS}


def _work(path_str: str) -> dict:
    try:
        return score_checkpoint(Path(path_str), _G["manifest"], _G["data"], _G["spec"])
    except Exception as error:                                     # noqa: BLE001 - reported, never silent
        return {"ckpt": str(Path(path_str).resolve()), "name": Path(path_str).stem,
                "error": f"{type(error).__name__}: {error}"}


def finished_rows() -> dict:
    """{(ckpt, sha256): row} for rows already written under the current manifest."""
    if not ROWS.exists():
        return {}
    current = H.sha256_file(manifest_path())
    out = {}
    for line in ROWS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("manifest_sha256") == current and "error" not in row:
            out[(row["ckpt"], row["sha256"])] = row
    return out


def cmd_score(args) -> None:
    manifest = load_manifest()
    manifest_text = json.dumps(manifest)
    wanted = []
    for raw in args.ckpt_dir:
        folder = Path(raw).expanduser()
        if not folder.is_absolute():
            folder = (L.ROOT / folder)
        if not folder.exists():
            print(f"missing checkpoint directory, skipped: {folder}")
            continue
        found = sorted(folder.glob("*.pt"))
        if not found:
            print(f"no *.pt in {folder}, skipped")
            continue
        wanted.extend(found)
    if not wanted:
        print("nothing to score")
        return
    done = finished_rows()
    todo = [p for p in wanted if (str(p.resolve()), H.sha256_file(p)) not in done]
    print(f"{len(wanted)} checkpoints found, {len(wanted) - len(todo)} already scored under this manifest, "
          f"{len(todo)} to do")
    if args.limit:
        todo = todo[:args.limit]
        print(f"--limit {args.limit}: scoring {len(todo)}")
    if not todo:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    workers = max(1, int(args.workers))
    completed = 0

    def record(row: dict) -> None:
        with ROWS.open("a") as handle:
            handle.write(json.dumps(row, default=str) + "\n")
        if "error" in row:
            print(f"{row['name']:24s} ERROR {row['error']}", flush=True)
            return
        counts = "  ".join(f"{CELLS[k]['cell']}:{row['counts'][k]}" for k in CELLS)
        print(f"{row['name']:24s} {counts}   G={row['G']}   {row['seconds']:.1f}s", flush=True)

    if workers == 1:
        _init_worker(manifest_text)
        for path in todo:
            record(_work(str(path)))
            completed += 1
            rate = (time.perf_counter() - started) / completed
            print(f"  [{completed}/{len(todo)}] {rate:.1f}s per checkpoint, "
                  f"{rate * (len(todo) - completed) / 60:.1f} min left", flush=True)
    else:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=workers, initializer=_init_worker, initargs=(manifest_text,)) as pool:
            for row in pool.imap_unordered(_work, [str(p) for p in todo]):
                record(row)
                completed += 1
                rate = (time.perf_counter() - started) / completed
                print(f"  [{completed}/{len(todo)}] {rate:.1f}s per checkpoint wall-clock, "
                      f"{rate * (len(todo) - completed) / 60:.1f} min left", flush=True)
    print(f"\nscored {completed} checkpoints in {time.perf_counter() - started:.1f}s "
          f"with {workers} worker(s); rows appended to {ROWS}")


# ------------------------------------------------------------------------------------------ table subcommand
def _stuck_flags(runs_dir: Path) -> dict:
    """{checkpoint name: stuck bool} from the run JSONs: one-hop validation < 384/512."""
    out = {}
    for path in sorted(runs_dir.glob("*.json")):
        try:
            blob = json.loads(path.read_text())
            one = blob["validation"]["fixed_K4"]["one_hop"]
            out[blob.get("name", path.stem)] = {"stuck": bool(one["correct"] < STUCK_ONE_HOP),
                                                "one_hop": int(one["correct"]), "n": int(one["n"])}
        except (KeyError, ValueError, TypeError):
            continue
    return out


def cmd_table(args) -> None:
    manifest = load_manifest()
    current = H.sha256_file(manifest_path())
    if not ROWS.exists():
        print(f"no rows at {ROWS}; run `score` first")
        return
    rows = [json.loads(line) for line in ROWS.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get("manifest_sha256") == current and "error" not in r]
    latest = {}
    for row in rows:
        latest[(row["ckpt"], row["sha256"])] = row
    rows = list(latest.values())
    groups, runs = {}, {}
    for raw in args.group or []:
        if "=" not in raw:
            raise SystemExit(f"--group wants NAME=DIR, got {raw!r}")
        name, folder = raw.split("=", 1)
        path = Path(folder).expanduser()
        groups[name] = (path if path.is_absolute() else L.ROOT / path).resolve()
    for raw in args.runs or []:
        if "=" not in raw:
            raise SystemExit(f"--runs wants NAME=RUNS_DIR, got {raw!r}")
        name, folder = raw.split("=", 1)
        path = Path(folder).expanduser()
        runs[name] = (path if path.is_absolute() else L.ROOT / path).resolve()
    lines, report = [], {"manifest_sha256": current, "groups": {}, "comparisons": [],
                         "stuck_rule": f"validation one-hop < {STUCK_ONE_HOP}/{STUCK_N} (fixed_K4)"}
    for name, folder in groups.items():
        if not folder.exists():
            lines.append(f"group {name}: missing directory {folder}")
        mine = sorted((r for r in rows if r["dir"] == str(folder)), key=lambda r: r["name"])
        stuck_table = {}
        if name in runs:
            if runs[name].exists():
                stuck_table = _stuck_flags(runs[name])
            else:
                lines.append(f"group {name}: missing runs directory {runs[name]}")
        block = {"dir": str(folder), "n": len(mine),
                 "cell_pass": {k: sum(int(r["cell_pass"][k]) for r in mine) for k in CELLS},
                 "G_pass": sum(int(r["G"]) for r in mine),
                 "runs_dir": str(runs.get(name, "")) or None,
                 "stuck": (sum(int(stuck_table[r["name"]]["stuck"]) for r in mine if r["name"] in stuck_table)
                           if stuck_table else None),
                 "stuck_known": sum(int(r["name"] in stuck_table) for r in mine) if stuck_table else 0,
                 "checkpoints": []}
        for r in mine:
            info = stuck_table.get(r["name"])
            held = (r["cells"]["c3_own_heldout_two_hop"].get("diagnostics") or {}).get("by_request", {})
            block["checkpoints"].append({
                "name": r["name"], "counts": r["counts"], "cell_pass": r["cell_pass"], "G": r["G"],
                "stuck": None if info is None else info["stuck"],
                "one_hop_validation": None if info is None else info["one_hop"],
                "heldout_request1": held.get("request1"), "heldout_request2": held.get("request2"),
                "heldout_requests_made": (r["cells"]["c3_own_heldout_two_hop"].get("diagnostics") or {}
                                          ).get("requests_made"),
                "heldout_both_gold_fetched": (r["cells"]["c3_own_heldout_two_hop"].get("diagnostics") or {}
                                              ).get("both_gold_cards_fetched"),
                "seconds": r["seconds"]})
        block["G_wilson95"] = wilson(block["G_pass"], block["n"])
        if block["stuck"] is not None:
            block["stuck_wilson95"] = wilson(block["stuck"], block["stuck_known"])
        report["groups"][name] = block
    head = ("group".ljust(22) + "n".rjust(4) +
            "".join(f"c{CELLS[k]['cell']}".rjust(5) for k in CELLS) + "G".rjust(5) + "stuck".rjust(7))
    lines += ["", "cells pass counts per group (c1..c6), G = all six", head]
    for name, block in report["groups"].items():
        stuck = "-" if block["stuck"] is None else f"{block['stuck']}/{block['stuck_known']}"
        lines.append(name.ljust(22) + str(block["n"]).rjust(4)
                     + "".join(str(block["cell_pass"][k]).rjust(5) for k in CELLS)
                     + str(block["G_pass"]).rjust(5) + stuck.rjust(7))
    for name, block in report["groups"].items():
        lines += ["", f"=== {name}  ({block['dir']})",
                  "checkpoint".ljust(24) + "".join(f"c{CELLS[k]['cell']}".rjust(7) for k in CELLS)
                  + "G".rjust(4) + "stuck".rjust(7) + "1hopVal".rjust(9)
                  + "r2person".rjust(10) + "r2rel".rjust(8) + "bothGold".rjust(10)]
        for row in block["checkpoints"]:
            r2 = row["heldout_request2"] or {}
            lines.append(row["name"].ljust(24)
                         + "".join(str(row["counts"][k]).rjust(7) for k in CELLS)
                         + ("Y" if row["G"] else "n").rjust(4)
                         + ("?" if row["stuck"] is None else ("Y" if row["stuck"] else "n")).rjust(7)
                         + ("?" if row["one_hop_validation"] is None else str(row["one_hop_validation"])).rjust(9)
                         + str(r2.get("right_person", "?")).rjust(10)
                         + str(r2.get("right_relation", "?")).rjust(8)
                         + str(row["heldout_both_gold_fetched"]).rjust(10))
        lines.append(f"  G pass {block['G_pass']}/{block['n']}  Wilson95 {block['G_wilson95']}"
                     + ("" if block["stuck"] is None else
                        f"   stuck {block['stuck']}/{block['stuck_known']} Wilson95 {block['stuck_wilson95']}"))
    for a, b in (args.compare or []):
        if a not in report["groups"] or b not in report["groups"]:
            lines.append(f"compare {a} vs {b}: unknown group")
            continue
        ga, gb = report["groups"][a], report["groups"][b]
        entry = {"a": a, "b": b}
        p_g = fisher_exact_two_sided(ga["G_pass"], ga["n"] - ga["G_pass"], gb["G_pass"], gb["n"] - gb["G_pass"])
        entry["G"] = {"a_pass": ga["G_pass"], "a_n": ga["n"], "b_pass": gb["G_pass"], "b_n": gb["n"],
                      "fisher_p_two_sided": round(p_g, 6),
                      "a_wilson95": ga["G_wilson95"], "b_wilson95": gb["G_wilson95"]}
        lines += ["", f"compare {a} vs {b}",
                  f"  G pass: {ga['G_pass']}/{ga['n']} {ga['G_wilson95']} vs {gb['G_pass']}/{gb['n']} "
                  f"{gb['G_wilson95']}   two-sided Fisher p = {p_g:.6f}"]
        if ga["stuck"] is not None and gb["stuck"] is not None:
            p_s = fisher_exact_two_sided(ga["stuck"], ga["stuck_known"] - ga["stuck"],
                                         gb["stuck"], gb["stuck_known"] - gb["stuck"])
            entry["stuck"] = {"a_stuck": ga["stuck"], "a_n": ga["stuck_known"], "b_stuck": gb["stuck"],
                              "b_n": gb["stuck_known"], "fisher_p_two_sided": round(p_s, 6),
                              "a_wilson95": ga["stuck_wilson95"], "b_wilson95": gb["stuck_wilson95"]}
            lines.append(f"  stuck:  {ga['stuck']}/{ga['stuck_known']} {ga['stuck_wilson95']} vs "
                         f"{gb['stuck']}/{gb['stuck_known']} {gb['stuck_wilson95']}   "
                         f"two-sided Fisher p = {p_s:.6f}")
        else:
            lines.append("  stuck:  not available (give --runs for both groups)")
        report["comparisons"].append(entry)
    text = "\n".join(lines)
    print(text)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "table.json").write_text(json.dumps(report, indent=1))
    (OUT / "table.txt").write_text(text + "\n")
    print(f"\nwrote {OUT / 'table.json'} and {OUT / 'table.txt'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen", help="build and hash the six datasets and the manifest (no model is loaded)")
    score = sub.add_parser("score", help="score every *.pt in the given directories")
    score.add_argument("--ckpt-dir", action="append", required=True)
    score.add_argument("--workers", type=int, default=4)
    score.add_argument("--limit", type=int, default=0)
    table = sub.add_parser("table", help="group table, Fisher comparisons and Wilson intervals")
    table.add_argument("--group", action="append", help="NAME=CKPT_DIR")
    table.add_argument("--runs", action="append", help="NAME=RUNS_DIR")
    table.add_argument("--compare", action="append", nargs=2, metavar=("A", "B"))
    args = parser.parse_args()
    L.bootstrap()
    import torch
    torch.set_num_threads(1 if args.cmd == "score" else 4)
    {"gen": cmd_gen, "score": cmd_score, "table": cmd_table}[args.cmd](args)


if __name__ == "__main__":
    main()
