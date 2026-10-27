"""A3-teacher-delay-v2 evaluator (Claude, 2026-09-19) -- EVAL ONLY, additive, frozen checkpoints.

Implements design/v3/12-teacher-delay-contract.md, "Revised CONTRACT -- untested: roster, primary and power"
and "... safeguards and stage status", plus parity requirement 4 ("Evaluation integrity and reuse") and 09's
complete reuse identity.  No training, no parameter update, no fitted probe, no GPU, no network, no test split.
Nothing outside the plan directory given on the command line is ever written; no existing file is edited and
the historical suite in artifacts/claude-pairsuite-20260919/ is never touched or regenerated.

Everything substantive is imported from the existing, already-executed source:

  scripts/premonition_pair_suite.py      fresh-world generators (`_make_single`, `_make_pair`), cell configs,
                                         cutoffs, twin counting, the fetch-class diagnostics and the
                                         own_fixed / world-isolation integrity checks
  scripts/premonition_handoff_diag.py    label stripping, the visible-field view, the native condition U
                                         (4 fixed loops, ASK gate, at most 3 requests, HALT ignored) and the
                                         label-perturbation check
  scripts/premonition_ovn_retrieval.py   `gold_read(..., loops=2)`: the READS metric (gold_read_K2_no_fetch)
  scripts/premonition_first_card_probe.py  checkpoint loader (`load_from`) and weight fingerprint

Seven per-pair panels, all freshly generated from that pair's `eval_seed`, shared by the pair's two arms and
independent across pairs (one scored question per independently generated world):

  c1 own one-hop                      2,048 worlds   pass >= 1,969     L_train
  c2 own practised two-hop            2,048 worlds   pass >= 1,969     L_train
  c3 own held-out two-hop             2,048 worlds   pass >= 1,876
  c4 held-out changed-link pair       1,024 twins    pass >=  945  (both twins correct)
  c5 held-out changed-endpoint pair   1,024 twins    pass >=  945  (both twins correct)
  c6 held-out irrelevant-edit pair    1,024 twins    pass >=  945  (both correct AND identical outputs)
  reads practised two-hop, both gold cards preloaded, 2 loops, no fetching      512 worlds

  L_train = c1 >= 1969 and c2 >= 1969;  G_pair = all six cutoffs;  c1-stuck = c1 < 1536.

    PY -B scripts/premonition_teacher_delay_eval.py panels --plan DIR/plan.json --pair 0
    PY -B scripts/premonition_teacher_delay_eval.py score  --plan DIR/plan.json --job p000-control [--workers N]

READS on fresh worlds: the historical number is `evaluate(...)["gold_read_K2_no_fetch"]["two_hop_trained_rel"]`
over the saved validation split.  Here the same inference (`premonition_ovn_retrieval.gold_read`, 2 loops, both
gold cards preloaded, no further fetch) is run over 512 freshly generated worlds, each contributing its first
practised two-hop question, and `reads_parity_gold_read_K2` in every result checks this evaluator's label-free
path against the frozen `gold_read` itself on the first chunk.  READS_DIFFERENCES below lists every difference
from the historical construction.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace as dc_replace
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402
import premonition_handoff_diag as H  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pair_suite as PS  # noqa: E402

SOURCE = Path(__file__).resolve()
EXPERIMENT_ID = "A3-teacher-delay-v2"
EVALUATOR_VERSION = "premonition-teacher-delay-eval-v1"
SELECTOR_POLICY = "not_applicable"          # legacy request route: 09 section 3b
RNG_NAMESPACE = "premonition-teacher-delay-v2-panel"

LOOPS = PS.LOOPS                            # 4 fixed loops (HALT ignored)
REQUESTS = PS.REQUESTS                      # at most 3 requests
CONDITION = PS.CONDITION                    # "U": native hard top-1 retrieval with the ASK gate, no mask
READS_LOOPS = 2                             # gold_read_K2_no_fetch
WORLDS_PER_CHUNK = PS.WORLDS_PER_CHUNK

CELL_SOURCE = {"c1": "c1_own_one_hop", "c2": "c2_own_practised_two_hop", "c3": "c3_own_heldout_two_hop",
               "c4": "c4_changed_link", "c5": "c5_changed_endpoint_value", "c6": "c6_irrelevant_edit"}
CELLS = tuple(CELL_SOURCE)                                     # c1..c6, in order
PANELS = CELLS + ("reads",)
CUTOFF = {short: PS.CELLS[name]["cutoff"] for short, name in CELL_SOURCE.items()}   # 1969/1969/1876/945/945/945
FULL_N = {short: PS.CELLS[name]["n"] for short, name in CELL_SOURCE.items()}        # 2048 x3, 1024 x3
FULL_N["reads"] = 512
L_TRAIN_CELLS = ("c1", "c2")
STUCK_CUTOFF = 1536                          # c1 < 1536/2048 is a fresh stuck run (12, safeguard 2)

PANEL_CONFIG = {short: {k: PS.CELLS[name].get(k) for k in
                        ("cell", "kind", "hops", "relation", "edit", "invariant", "token_diffs", "title")}
                for short, name in CELL_SOURCE.items()}
PANEL_CONFIG["reads"] = {"cell": 7, "kind": "single", "hops": 2, "relation": "practised", "edit": None,
                         "invariant": False, "token_diffs": None,
                         "title": "practised two-hop with both gold cards preloaded (READS, K=2, no fetch)"}

READS_DIFFERENCES = [
    "historical READS = premonition_ovn_retrieval.evaluate(...)['gold_read_K2_no_fetch']"
    "['two_hop_trained_rel'] over the saved 16-batch validation split; this panel is 512 freshly generated "
    "worlds from the pair's eval_seed, so the worlds, their number and their generator call differ",
    "historical worlds come from toy_ladder.make(spec, 16 visits, training=False) and EVERY practised two-hop "
    "question of every visit is scored; here each world is one toy_ladder.visit(...) and exactly its FIRST "
    "practised two-hop question is scored, so one world = one unit (matching the six G_pair cells)",
    "the inference itself is unchanged: premonition_ovn_retrieval.gold_read's computation, 2 fixed loops, both "
    "gold cards preloaded via store.gold + _insert, no further fetch, greedy answer compared to the held ids",
    "labels: the evaluator holds the answer ids outside the batch (as in the six cells); the gold LINE ids stay "
    "in the batch because supplying both gold cards is the definition of this metric -- they are an input, "
    "not an answer label",
]
SKIPPED = [
    "the secondary escape-timing statistic (training-log side; not an evaluation panel)",
    "the paired bootstrap, exact primary test and roster accounting (premonition_teacher_delay_report.py)",
    "12-person / three-lookup / longer-gap stress cells and the learned-halting variant (as in the pair suite)",
]


# ----------------------------------------------------------------------------------------------- utilities
def sha256_file(path: Path) -> str:
    return H.sha256_file(Path(path))


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def frozen_source(name: str) -> Path:
    return L.ARCHIVE / "frozen" / "premonition" / name


def evaluator_source_hashes() -> dict:
    """Every source file this evaluation actually executes, outside the loader closure."""
    out = {"scripts/premonition_teacher_delay_eval.py": sha256_file(SOURCE),
           "scripts/premonition_pair_suite.py": sha256_file(Path(PS.__file__).resolve()),
           "scripts/premonition_handoff_diag.py": sha256_file(H.SOURCE),
           "scripts/premonition_ovn_retrieval.py": sha256_file(Path(R.__file__).resolve()),
           "scripts/premonition_ovn_ladder.py": sha256_file(Path(L.__file__).resolve())}
    for name in ("model.py", "store.py", "toy_ladder.py", "train.py", "answer_path.py", "config.py",
                 "batch.py", "flops.py"):
        out[f"frozen/premonition/{name}"] = sha256_file(frozen_source(name))
    return out


def loader_source_hashes() -> dict:
    """The checkpoint-loading closure (premonition_first_card_probe.load_from and what it builds)."""
    out = {"scripts/premonition_first_card_probe.py": sha256_file(Path(P.__file__).resolve()),
           "scripts/premonition_ovn_retrieval.py": sha256_file(Path(R.__file__).resolve())}
    for name in ("answer_path.py", "config.py", "model.py"):
        out[f"frozen/premonition/{name}"] = sha256_file(frozen_source(name))
    return out


def execution_config(spec=None) -> dict:
    """Hardware/numerics and the resolved retrieval policy: 09 section 3c's `execution_config`."""
    import torch
    spec = spec or L.spec()
    return {"device": "cpu", "torch_version": torch.__version__, "python": sys.version.split()[0],
            "platform": platform.platform(), "machine": platform.machine(),
            "torch_num_threads_per_worker": 1, "default_dtype": str(torch.get_default_dtype()),
            "grad": "torch.no_grad", "model_mode": "eval",
            "policy": {"condition": CONDITION, "loops": LOOPS, "max_requests": REQUESTS,
                       "retrieval": "hard top-1 (store.top, model.config.top_k)", "ask_gate": "native (ask > 0)",
                       "halt": "ignored", "supplied_evidence": "none in c1..c6; both gold cards in READS",
                       "selector_policy": SELECTOR_POLICY, "reads_loops": READS_LOOPS},
            "cutoffs": dict(CUTOFF), "stuck_cutoff": STUCK_CUTOFF,
            "spec": {k: getattr(spec, k) for k in ("entities", "relations", "values", "fillers", "distractors",
                                                   "gap", "one_hop", "two_hop", "heldout_relation")},
            "evaluator_version": EVALUATOR_VERSION}


# ------------------------------------------------------------------------------------ fresh panel generation
def panel_rng(cell: str, eval_seed: int, index: int) -> random.Random:
    """The panel's world RNG.  Content is a pure function of (cell, eval_seed, index): no pair id, no path."""
    return random.Random(f"{RNG_NAMESPACE}|{eval_seed}|{cell}|{index}")


def build_panel(cell: str, eval_seed: int, n: int, spec=None) -> dict:
    """One fresh panel.  Model-free: no checkpoint is touched and no label ever reaches a model here.

    The worlds come from premonition_pair_suite's own generators (`_make_single` / `_make_pair`); only the RNG
    namespace (this experiment's, keyed by eval_seed) and the panel size differ from the historical suite.
    """
    from premonition import toy_ladder
    from premonition.train import label_free
    spec = spec or L.spec()
    cfg = PANEL_CONFIG[cell]
    pair = cfg["kind"] == "pair"
    sides = ("a", "b") if pair else ("a",)
    rejections, target_values, worlds = Counter(), Counter(), []
    for i in range(int(n)):
        rng = panel_rng(cell, eval_seed, i)
        if pair:
            lines_a, lines_b, line, facts, rej = PS._make_pair(spec, rng, cfg["edit"])
            target_values[facts["value_a"]] += 1
            target_values[facts["value_b"]] += 1
        else:
            lines_a, line, facts, rej = PS._make_single(spec, rng, cfg["hops"], cfg["relation"])
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
        full = {s: label_free(toy_ladder.assemble(spec, rows[s], prefix=f"{cell}-{s}-{start}")[0]) for s in sides}
        if pair:
            if full["a"].tokens.shape != full["b"].tokens.shape:
                raise SystemExit(f"{cell}: the twins have different token shapes")
            differing = (full["a"].tokens != full["b"].tokens).sum(1).tolist()
            if differing != [cfg["token_diffs"]] * len(block):
                raise SystemExit(f"{cell}: twins differ in {sorted(set(differing))} visible tokens, "
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
                row[f"key_{s}"] = f"{cell}|{index}|{s}"
            meta.append(row)
        chunk = {s: H._keep_questions(full[s], keep[s]) for s in sides}
        chunk["meta"] = meta
        chunks.append(chunk)
    return {"name": cell, "cell": cfg["cell"], "kind": cfg["kind"], "eval_seed": int(eval_seed), "n": int(n),
            "hops": cfg.get("hops"), "relation": cfg.get("relation"), "edit": cfg.get("edit"),
            "invariant": bool(cfg.get("invariant")), "scoring": "reads" if cell == "reads" else "native_U",
            "chunks": chunks, "rejections": dict(sorted(rejections.items())),
            "target_value_counts": {str(k): v for k, v in sorted(target_values.items())},
            "worlds_per_chunk": WORLDS_PER_CHUNK, "rng_namespace": RNG_NAMESPACE}


def panels_dir(plan_path: Path, pair_id: int) -> Path:
    return Path(plan_path).resolve().parent / "panels" / f"p{int(pair_id):03d}"


def panels_manifest_path(plan_path: Path, pair_id: int) -> Path:
    return panels_dir(plan_path, pair_id) / "manifest.json"


def generate_panels(plan_path: Path, pair_id: int, *, sizes: dict | None = None, quiet: bool = False) -> dict:
    """Write this pair's seven panels and their manifest.  Refuses to touch an existing directory."""
    import torch
    plan_path = Path(plan_path).resolve()
    plan = read_json(plan_path)
    pair = find_pair(plan, pair_id)
    folder = panels_dir(plan_path, pair_id)
    if folder.exists():
        raise SystemExit(f"refusing to overwrite existing panels: {folder}")
    sizes = dict(FULL_N) if sizes is None else dict(sizes)
    spec = L.spec()
    eval_seed = int(pair["eval_seed"])
    started = time.perf_counter()
    folder.mkdir(parents=True)
    manifest = {"experiment_id": plan.get("experiment_id", EXPERIMENT_ID), "evaluator_version": EVALUATOR_VERSION,
                "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "written_before_any_model_was_loaded": True,
                "pair_id": int(pair_id), "eval_seed": eval_seed,
                "init_seed": pair.get("init_seed"), "data_seed": pair.get("data_seed"),
                "shared_by": sorted((pair.get("jobs") or {})),
                "rng_namespace": RNG_NAMESPACE,
                "panel_content_is_a_pure_function_of": ["cell", "eval_seed", "n"],
                "generator_sources": {
                    "scripts/premonition_teacher_delay_eval.py": sha256_file(SOURCE),
                    "scripts/premonition_pair_suite.py": sha256_file(Path(PS.__file__).resolve()),
                    "scripts/premonition_handoff_diag.py": sha256_file(H.SOURCE),
                    "frozen/premonition/toy_ladder.py": sha256_file(frozen_source("toy_ladder.py"))},
                "spec": {k: getattr(spec, k) for k in ("entities", "relations", "values", "fillers",
                                                       "distractors", "gap", "one_hop", "two_hop",
                                                       "heldout_relation")},
                "loops": LOOPS, "requests": REQUESTS, "condition": CONDITION, "reads_loops": READS_LOOPS,
                "selector_policy": SELECTOR_POLICY, "worlds_per_chunk": WORLDS_PER_CHUNK,
                "cutoffs": dict(CUTOFF), "stuck_cutoff": STUCK_CUTOFF, "full_sizes": dict(FULL_N),
                "full_size": all(int(sizes.get(k, -1)) == v for k, v in FULL_N.items()),
                "reads_construction": READS_DIFFERENCES, "skipped": SKIPPED, "panels": {}}
    for cell in PANELS:
        t0 = time.perf_counter()
        data = build_panel(cell, eval_seed, int(sizes[cell]), spec=spec)
        audit = PS.audit_set(data, spec)
        if audit["interpreter"]["accuracy"] != 1.0:
            raise SystemExit(f"{cell}: the deterministic interpreter does not answer every example "
                             f"({audit['interpreter']['single_answer']}/{audit['interpreter']['answers']}); "
                             f"first failures {audit['interpreter']['failures']}")
        path = folder / f"{cell}.pt"
        torch.save(data, path)
        manifest["panels"][cell] = {
            "cell": data["cell"], "title": PANEL_CONFIG[cell]["title"], "kind": data["kind"], "n": data["n"],
            "hops": data["hops"], "relation": data["relation"], "edit": data["edit"],
            "invariant": data["invariant"], "scoring": data["scoring"],
            "cutoff": CUTOFF.get(cell), "file": path.name, "sha256": sha256_file(path),
            "bytes": path.stat().st_size, "rejections": data["rejections"],
            "target_value_counts": data["target_value_counts"], "audit": audit,
            "seconds": round(time.perf_counter() - t0, 2)}
        if not quiet:
            print(f"{cell:6s} {data['n']:5d} units  interpreter "
                  f"{audit['interpreter']['unit_accuracy']:.4f}  rejections {data['rejections']}  "
                  f"{time.perf_counter() - t0:.1f}s", flush=True)
    manifest["panel_content_sha256"] = sha256_json(
        {cell: manifest["panels"][cell]["sha256"] for cell in PANELS})
    manifest["seconds"] = round(time.perf_counter() - started, 2)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if not quiet:
        print(f"wrote {folder}/manifest.json  sha256 {sha256_file(folder / 'manifest.json')}  "
              f"content {manifest['panel_content_sha256'][:16]}  {manifest['seconds']}s", flush=True)
    return manifest


def load_panel(cell: str, folder: Path, manifest: dict):
    import torch
    info = manifest["panels"][cell]
    path = Path(folder) / info["file"]
    if sha256_file(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the panel manifest was written")
    return torch.load(path, weights_only=False)


# ---------------------------------------------------------------------------------------------- unit rules
def combine_units(ok_a, ok_b=None, identical=None, *, invariant: bool = False) -> list:
    """One world unit per entry.  A twin pair counts only if BOTH twins are correct; the output-invariance
    cell (c6) additionally requires identical generated outputs.  -> list of 0/1 ints in world order."""
    if ok_b is None:
        return [int(bool(x)) for x in ok_a]
    if invariant:
        if identical is None:
            raise ValueError("the output-invariance cell needs the identical-output flags")
        return [int(bool(a) and bool(b) and bool(s)) for a, b, s in zip(ok_a, ok_b, identical)]
    return [int(bool(a) and bool(b)) for a, b in zip(ok_a, ok_b)]


def gate_flags(counts: dict) -> dict:
    """L_train, G_pair and the fresh c1-stuck flag from the six cell counts, at the frozen cutoffs."""
    cell_pass = {cell: bool(int(counts[cell]) >= CUTOFF[cell]) for cell in CELLS}
    return {"cell_pass": cell_pass,
            "L_train": bool(all(cell_pass[cell] for cell in L_TRAIN_CELLS)),
            "G_pair": bool(all(cell_pass.values())),
            "c1_stuck": bool(int(counts["c1"]) < STUCK_CUTOFF)}


# -------------------------------------------------------------------------------------------------- scoring
def score_native_panel(model, dataset: dict, spec, *, diagnostics: bool = True) -> dict:
    """Native condition U over one panel: 4 fixed loops, ASK gate, hard top-1, at most 3 requests, no mask.

    Identical in substance to premonition_pair_suite.score_cell; it additionally returns the per-unit vector
    the paired bootstrap needs, in world order.
    """
    import torch
    sides = ("a", "b") if dataset["kind"] == "pair" else ("a",)
    correct = {s: [] for s in sides}
    produced = {s: [] for s in sides}
    diag = None
    with torch.no_grad():
        for chunk in dataset["chunks"]:
            metas = chunk["meta"]
            for side in sides:
                batch = H._strip_labels(chunk[side])         # the model only ever sees the diary
                fields = H.FieldView(batch, spec)
                keys = [m[f"key_{side}"] for m in metas]
                res = H.run_condition(model, batch, fields, CONDITION, keys)
                correct[side].append(H.correctness(res, [m[f"answer_{side}"] for m in metas]))
                produced[side].extend([res["tokens"][q, :int(res["lengths"][q])].tolist()
                                       for q in range(len(metas))])
                if diagnostics and side == "a":
                    diag = _merge_fetch_classes(diag, PS._fetch_classes(batch, res, metas, spec))
    ok = {s: torch.cat(correct[s]).tolist() for s in sides}
    if dataset["kind"] == "pair":
        identical = [x == y for x, y in zip(produced["a"], produced["b"])]
        per_unit = combine_units(ok["a"], ok["b"], identical, invariant=bool(dataset["invariant"]))
        out = {"per_unit": per_unit, "count": int(sum(per_unit)), "n": int(dataset["n"]),
               "single_correct": {s: int(sum(ok[s])) for s in sides},
               "both_correct": int(sum(int(a and b) for a, b in zip(ok["a"], ok["b"]))),
               "identical_answers": int(sum(identical))}
    else:
        per_unit = combine_units(ok["a"])
        out = {"per_unit": per_unit, "count": int(sum(per_unit)), "n": int(dataset["n"]),
               "single_correct": {"a": int(sum(ok["a"]))}}
    if len(per_unit) != int(dataset["n"]):
        raise SystemExit(f"{dataset['name']}: {len(per_unit)} units scored, expected {dataset['n']}")
    if diag is not None:
        out["diagnostics"] = _summarise_fetch_classes(diag)
    return out


def _merge_fetch_classes(diag, block):
    if diag is None:
        return block
    diag["requests_made"] += block["requests_made"]
    diag["both_gold_cards_fetched"] += block["both_gold_cards_fetched"]
    diag["questions"] += block["questions"]
    diag["requests_made_per_step"] = [x + y for x, y in
                                      zip(diag["requests_made_per_step"], block["requests_made_per_step"])]
    for key, value in block["by_request"].items():
        slot = diag["by_request"][key]
        merged = Counter(slot["classes"])
        merged.update(value["classes"])
        slot["classes"] = dict(merged.most_common())
        for field in ("right_person", "right_relation", "right_both", "correct_link_card", "total_requests"):
            slot[field] += value[field]
    return diag


def _summarise_fetch_classes(diag: dict) -> dict:
    """The suite's by_request diagnostics plus the rates the contract names, over ALL questions."""
    questions = max(int(diag["questions"]), 1)
    first = diag["by_request"]["request1"]["classes"]
    out = dict(diag)
    out["first_request_class_rates"] = {name: round(count / questions, 6)
                                        for name, count in sorted(first.items())}
    out["first_request_asker_same_rel"] = int(first.get("asker_same_rel", 0))
    out["first_request_asker_same_rel_rate"] = round(first.get("asker_same_rel", 0) / questions, 6)
    out["first_link_card"] = int(first.get("link", 0))
    out["first_link_card_rate_all_questions"] = round(first.get("link", 0) / questions, 6)
    out["first_any_link_rate_all_questions"] = round(
        (first.get("link", 0) + first.get("other_link", 0)) / questions, 6)
    out["denominator"] = "every question in the panel, including questions with no request"
    return out


def _reads_strip(batch):
    """READS label rule: answers, depths, ids and slices are removed; the gold LINE ids stay, because supplying
    both gold cards is the definition of this metric (they are an input, not an answer label)."""
    import torch
    from learnlab.core import IGNORE_INDEX
    return dc_replace(batch, answer=torch.full_like(batch.answer, IGNORE_INDEX),
                      depth=torch.zeros_like(batch.depth),
                      question_ids=[f"blind-{i}" for i in range(batch.q_visit.shape[0])], slices=None)


def _gold_read_tokens(model, batch, loops: int):
    """premonition_ovn_retrieval.gold_read's inference, with the answer ids held outside the batch."""
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    if store is not None:
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        width = min(gold.shape[1], 2)
        preload = torch.where(gold, torch.arange(gold.shape[1]),
                              torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
        model._insert(episode, store, everyone, preload)
    for step in range(loops):
        model._step(episode, everyone, step, store)
    return model._greedy(batch, episode, mentions, None)


def score_reads_panel(model, dataset: dict, spec) -> dict:
    """READS: both gold cards preloaded, READS_LOOPS fixed loops, NO fetching (gold_read_K2_no_fetch)."""
    import torch
    per_unit = []
    with torch.no_grad():
        for chunk in dataset["chunks"]:
            metas = chunk["meta"]
            batch = _reads_strip(chunk["a"])
            tokens, lengths = _gold_read_tokens(model, batch, READS_LOOPS)
            for q, meta in enumerate(metas):
                per_unit.append(int(tokens[q, :int(lengths[q])].tolist() == meta["answer_a"]))
    if len(per_unit) != int(dataset["n"]):
        raise SystemExit(f"reads: {len(per_unit)} units scored, expected {dataset['n']}")
    return {"per_unit": per_unit, "count": int(sum(per_unit)), "n": int(dataset["n"])}


def reads_parity(model, dataset: dict) -> dict:
    """This evaluator's label-free READS path must equal the frozen `gold_read(..., 2)` on the first chunk."""
    import torch
    chunk = dataset["chunks"][0]
    metas = chunk["meta"]
    with torch.no_grad():
        ok_hist, _all_gold = R.gold_read(model, chunk["a"], READS_LOOPS)
        batch = _reads_strip(chunk["a"])
        tokens, lengths = _gold_read_tokens(model, batch, READS_LOOPS)
    mine = [int(tokens[q, :int(lengths[q])].tolist() == metas[q]["answer_a"]) for q in range(len(metas))]
    equal = int(sum(int(a) == int(b) for a, b in zip(mine, ok_hist.tolist())))
    return {"units": len(mine), "equal": equal, "pass": bool(equal == len(mine)),
            "frozen_function": "premonition_ovn_retrieval.gold_read(model, batch, 2)"}


# -------------------------------------------------------------------------------------- plan and job records
def find_pair(plan: dict, pair_id: int) -> dict:
    for pair in plan.get("pairs", []):
        if int(pair["pair_id"]) == int(pair_id):
            return pair
    raise SystemExit(f"plan has no pair {pair_id}")


def find_job(plan: dict, job_id: str) -> tuple:
    for pair in plan.get("pairs", []):
        for arm, job in (pair.get("jobs") or {}).items():
            if str(job.get("job_id")) == str(job_id):
                return pair, arm, job
    raise SystemExit(f"plan has no job {job_id!r}")


def job_dir(plan_path: Path, job_id: str) -> Path:
    return Path(plan_path).resolve().parent / "jobs" / str(job_id)


def reuse_key(checkpoint: Path, checkpoint_sha: str, manifest_sha: str, config_sha: str) -> dict:
    """09 section 3c's complete reuse identity."""
    return {"checkpoint_path": str(Path(checkpoint).resolve()), "checkpoint_sha256": checkpoint_sha,
            "evaluation_manifest_sha256": manifest_sha, "evaluator_source_hashes": evaluator_source_hashes(),
            "loader_source_hashes": loader_source_hashes(), "selector_policy": SELECTOR_POLICY,
            "execution_config_sha256": config_sha}


def reuse_allowed(existing: dict, key: dict) -> tuple:
    """(bool, reason).  Every field of the key must match and the saved row must be a complete success."""
    if not isinstance(existing, dict):
        return False, "existing eval.json is not an object"
    if existing.get("status") != "complete":
        return False, f"existing status is {existing.get('status')!r}, not 'complete'"
    old = existing.get("reuse_key")
    if not isinstance(old, dict):
        return False, "existing eval.json has no reuse_key"
    for field, value in key.items():
        if field not in old:
            return False, f"missing reuse-key field {field}"
        if old[field] != value:
            return False, f"reuse-key field {field} differs"
    if not (existing.get("integrity") or {}).get("all_pass"):
        return False, "the existing integrity record did not pass"
    return True, "every reuse-key field matches and the saved evaluation is complete"


def failed_record(job_id, pair_id, arm, reason: str, *, sizes=None, extra=None) -> dict:
    """A failure never fabricates counts: no `counts` and no `per_unit` field is written."""
    out = {"experiment_id": EXPERIMENT_ID, "evaluator_version": EVALUATOR_VERSION, "job_id": job_id,
           "pair_id": pair_id, "arm": arm, "status": "failed", "reason": reason,
           "selector_policy": SELECTOR_POLICY, "n": dict(sizes or FULL_N),
           "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out.update(extra or {})
    return out


# ----------------------------------------------------------------------------------------- scoring workers
_G: dict = {}


def _init_worker(payload: str) -> None:
    L.bootstrap()
    import torch
    torch.set_num_threads(1)
    info = json.loads(payload)
    _G["folder"] = Path(info["folder"])
    _G["manifest"] = info["manifest"]
    _G["spec"] = L.spec()
    model, blob = P.load_from(Path(info["checkpoint"]).stem, Path(info["checkpoint"]).parent)
    model.eval()
    _G["model"] = model
    _G["parameters"] = int(sum(p.numel() for p in model.parameters()))


def _work(cell: str) -> dict:
    """One panel, in a worker: its per-unit vector, its diagnostics and the integrity checks pinned to it."""
    model, spec = _G["model"], _G["spec"]
    started = time.perf_counter()
    before = P.fingerprint(model)
    data = load_panel(cell, _G["folder"], _G["manifest"])
    integrity = {}
    if cell == "reads":
        result = score_reads_panel(model, data, spec)
        integrity["reads_parity_gold_read_K2"] = reads_parity(model, data)
    else:
        result = score_native_panel(model, data, spec, diagnostics=True)
        if cell == "c1":
            integrity["own_fixed_parity"] = PS.own_fixed_parity(model, data, spec)
        if cell == "c3":
            integrity["world_isolation"] = PS.world_isolation(model, data, spec)
        if cell == "c4":
            integrity["label_perturbation"] = H.label_perturbation_check(
                model, {"chunks": [data["chunks"][0]]}, spec)
    after = P.fingerprint(model)
    return {"cell": cell, "result": result, "integrity": integrity, "parameters": _G["parameters"],
            "fingerprint_before": before, "fingerprint_after": after,
            "seconds": round(time.perf_counter() - started, 2)}


def _work_guarded(cell: str) -> dict:
    try:
        return _work(cell)
    except Exception as error:                                  # noqa: BLE001 - reported, never silent
        return {"cell": cell, "error": f"{type(error).__name__}: {error}"}


# ------------------------------------------------------------------------------------------ score subcommand
def score_job(plan_path: Path, job_id: str, *, workers: int = 1, quiet: bool = False) -> dict:
    import torch
    plan_path = Path(plan_path).resolve()
    plan = read_json(plan_path)
    pair, arm, job = find_job(plan, job_id)
    pair_id = int(pair["pair_id"])
    folder = job_dir(plan_path, job_id)
    out_path = folder / "eval.json"
    started = time.perf_counter()

    def finish(record: dict) -> dict:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record["seconds"] = round(time.perf_counter() - started, 2)
        out_path.write_text(json.dumps(record, indent=1, default=str))
        if not quiet:
            if record["status"] == "complete":
                print(f"{job_id}  " + "  ".join(f"{c}:{record['counts'][c]}" for c in PANELS)
                      + f"   L_train={record['L_train']}  G_pair={record['G_pair']}  "
                      f"stuck={record['c1_stuck']}   {record['seconds']}s", flush=True)
            else:
                print(f"{job_id}  FAILED: {record['reason']}", flush=True)
        return record

    # ---- the panels this pair's two arms share
    manifest_path = panels_manifest_path(plan_path, pair_id)
    if not manifest_path.exists():
        return finish(failed_record(job_id, pair_id, arm,
                                    f"no panels for pair {pair_id}; run `panels --pair {pair_id}` first"))
    manifest = read_json(manifest_path)
    sizes = {cell: int(manifest["panels"][cell]["n"]) for cell in PANELS}
    manifest_sha = sha256_file(manifest_path)

    # ---- the job's own training record and checkpoint
    result_path = folder / "result.json"
    checkpoint = folder / "model.pt"
    if not result_path.exists():
        return finish(failed_record(job_id, pair_id, arm, f"missing {result_path}", sizes=sizes))
    record = read_json(result_path)
    if record.get("status") != "complete":
        return finish(failed_record(job_id, pair_id, arm,
                                    f"training record status is {record.get('status')!r}, not 'complete'",
                                    sizes=sizes, extra={"training_status": record.get("status"),
                                                        "training_reason": record.get("reason")}))
    if not checkpoint.exists():
        return finish(failed_record(job_id, pair_id, arm, f"missing {checkpoint}", sizes=sizes))
    checkpoint_sha = sha256_file(checkpoint)
    recorded_sha = record.get("ckpt_sha256") or record.get("checkpoint_sha256")
    if recorded_sha and recorded_sha != checkpoint_sha:
        return finish(failed_record(job_id, pair_id, arm,
                                    f"checkpoint sha256 {checkpoint_sha} != result.json {recorded_sha}",
                                    sizes=sizes))

    config = execution_config()
    key = reuse_key(checkpoint, checkpoint_sha, manifest_sha, sha256_json(config))
    if out_path.exists():
        existing = read_json(out_path)
        allowed, why = reuse_allowed(existing, key)
        if allowed:
            if not quiet:
                print(f"{job_id}  reusing the existing evaluation: {why}", flush=True)
            return dict(existing, reused=True)
        raise SystemExit(f"{out_path} already exists and cannot be reused ({why}); refusing to overwrite it")

    blob = torch.load(checkpoint, weights_only=False)
    for field, expected in (("experiment_id", plan.get("experiment_id", EXPERIMENT_ID)),
                            ("job_id", job_id), ("arm_name", arm)):
        if field in blob and str(blob[field]) != str(expected):
            return finish(failed_record(job_id, pair_id, arm,
                                        f"checkpoint {field} is {blob[field]!r}, expected {expected!r}",
                                        sizes=sizes))
    if "pair_id" in blob and int(blob["pair_id"]) != pair_id:
        return finish(failed_record(job_id, pair_id, arm,
                                    f"checkpoint pair_id is {blob['pair_id']}, expected {pair_id}", sizes=sizes))

    payload = json.dumps({"folder": str(panels_dir(plan_path, pair_id)), "manifest": manifest,
                          "checkpoint": str(checkpoint)})
    workers = max(1, int(workers))
    pieces = {}
    if workers == 1:
        _init_worker(payload)
        for cell in PANELS:
            pieces[cell] = _work_guarded(cell)
    else:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=min(workers, len(PANELS)), initializer=_init_worker,
                      initargs=(payload,)) as pool:
            for piece in pool.imap_unordered(_work_guarded, list(PANELS)):
                pieces[piece["cell"]] = piece
    broken = {cell: piece["error"] for cell, piece in pieces.items() if "error" in piece}
    if broken:
        return finish(failed_record(job_id, pair_id, arm, f"panel scoring failed: {broken}", sizes=sizes))

    counts = {cell: pieces[cell]["result"]["count"] for cell in PANELS}
    per_unit = {cell: pieces[cell]["result"]["per_unit"] for cell in PANELS}
    flags = gate_flags(counts)
    integrity = {}
    for cell in PANELS:
        integrity.update(pieces[cell]["integrity"])
    prints = {cell: (pieces[cell]["fingerprint_before"], pieces[cell]["fingerprint_after"]) for cell in PANELS}
    fingerprint = prints["c1"][0]
    integrity["weights_fingerprint"] = fingerprint
    integrity["weights_unchanged"] = bool(all(b == a == fingerprint for b, a in prints.values()))
    integrity["label_perturbation_identical"] = bool(integrity["label_perturbation"]["pass"])
    integrity["world_isolation_pass"] = bool(integrity["world_isolation"]["pass"])
    integrity["checkpoint_sha256"] = checkpoint_sha
    integrity["panels_manifest_sha256"] = manifest_sha
    integrity["panels_content_sha256"] = manifest.get("panel_content_sha256")
    integrity["panels_full_size"] = bool(manifest.get("full_size"))
    integrity["evaluator_source_hashes"] = key["evaluator_source_hashes"]
    integrity["loader_source_hashes"] = key["loader_source_hashes"]
    integrity["execution_config_sha256"] = key["execution_config_sha256"]
    integrity["execution_config"] = config
    integrity["all_pass"] = bool(integrity["weights_unchanged"] and integrity["label_perturbation_identical"]
                                 and integrity["world_isolation_pass"]
                                 and integrity["own_fixed_parity"]["pass"]
                                 and integrity["reads_parity_gold_read_K2"]["pass"])
    if not integrity["all_pass"]:
        reason = ("parameters changed during evaluation" if not integrity["weights_unchanged"]
                  else "an integrity check failed")
        return finish(failed_record(job_id, pair_id, arm, reason, sizes=sizes,
                                    extra={"integrity": integrity}))
    out = {"experiment_id": plan.get("experiment_id", EXPERIMENT_ID), "evaluator_version": EVALUATOR_VERSION,
           "job_id": job_id, "pair_id": pair_id, "arm": arm, "status": "complete",
           "selector_policy": SELECTOR_POLICY,
           "eval_seed": int(pair["eval_seed"]), "init_seed": pair.get("init_seed"),
           "data_seed": pair.get("data_seed"),
           "counts": counts, "n": sizes, "per_unit": per_unit,
           "accuracy": {cell: round(counts[cell] / max(sizes[cell], 1), 6) for cell in PANELS},
           "cutoffs": dict(CUTOFF), "stuck_cutoff": STUCK_CUTOFF,
           "cell_pass": flags["cell_pass"], "c1_stuck": flags["c1_stuck"],
           "L_train": flags["L_train"], "G_pair": flags["G_pair"],
           "full_size_panels": bool(manifest.get("full_size")),
           "stage_valid": bool(manifest.get("full_size")),
           "unit_order": "world index 0..n-1 of each panel; a twin pair is ONE unit; identical across the two "
                         "arms of a pair because both arms score the same panel files",
           "panels": {"dir": str(panels_dir(plan_path, pair_id)), "manifest_sha256": manifest_sha,
                      "content_sha256": manifest.get("panel_content_sha256"),
                      "files": {cell: manifest["panels"][cell]["sha256"] for cell in PANELS}},
           "checkpoint": {"path": str(checkpoint.resolve()), "sha256": checkpoint_sha,
                          "model_class": blob.get("model_class"), "arm_name": blob.get("arm_name"),
                          "parameters": pieces["c1"]["parameters"]},
           "diagnostics": {cell: pieces[cell]["result"].get("diagnostics") for cell in CELLS},
           "cells": {cell: {k: v for k, v in pieces[cell]["result"].items() if k != "per_unit"}
                     for cell in PANELS},
           "reads_construction": READS_DIFFERENCES,
           "integrity": integrity, "reuse_key": key,
           "panel_seconds": {cell: pieces[cell]["seconds"] for cell in PANELS},
           "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    return finish(out)


# ------------------------------------------------------------------------------------------------- commands
def cmd_panels(args) -> None:
    sizes = None
    if args.testing_panel_size:
        sizes = {cell: int(args.testing_panel_size) for cell in PANELS}
        print(f"TESTING panel size {args.testing_panel_size}: these panels are NOT the registered sizes "
              f"{FULL_N} and cannot support stage acceptance", flush=True)
    generate_panels(Path(args.plan), int(args.pair), sizes=sizes)


def cmd_score(args) -> None:
    score_job(Path(args.plan), args.job, workers=args.workers)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    panels = sub.add_parser("panels", help="generate one pair's seven fresh panels from its eval_seed")
    panels.add_argument("--plan", required=True)
    panels.add_argument("--pair", type=int, required=True)
    panels.add_argument("--testing-panel-size", type=int, default=0, help=argparse.SUPPRESS)
    score = sub.add_parser("score", help="score one job's checkpoint on its pair's panels")
    score.add_argument("--plan", required=True)
    score.add_argument("--job", required=True)
    score.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    L.bootstrap()
    import torch
    torch.set_num_threads(1)
    {"panels": cmd_panels, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
