#!/usr/bin/env python3
"""Independent Test A raw audit. No Net, inference, training, or lead verdict imports.

uv run --offline --python 3.12 --with torch --with numpy python -B \
    scripts/claude_patch_race_recount.py --self-test
Later: same command without --self-test, optionally --checkpoints.
Only an explicit audit CLI run writes BLIND-RACE-RECOUNT.json and .md in --out.
Missing evidence means untested; a failed V3 means inconclusive.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts/claude-patch-20260927"
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384, 65536)
STAGES = tuple(f"k{k}" for k in (0,) + RUNGS) + ("sleep64", "sleep64k")
WIDE_STAGES = ("k0", "k64", "k65536", "sleep64", "sleep64k")
KINDS = ("sums", "grids", "sorting", "reversing", "counting", "brackets")
ARMS = ("patch", "loop_meta", "plain", "loop")
SIZES = {7: 48, 9: 300, 11: 300}
# Upstream ADDENDUM-3 (aeb524cd0); our wider source budget stays separate.
BASELINE_SOURCE = dict(source_steps=12000, source_batch=64, source_guard_seed=9233000)
OWN_SOURCE = dict(source_steps=18000, source_batch=64, source_guard_seed=9233000)
FORBIDDEN = {"RESULTS.md", "CHECKS.md", "RACE-RESULTS.json", "claude_patch_race_report.py"}


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def key(tokens, slot):
    return hashlib.sha256(json.dumps([tokens, slot], separators=(",", ":")).encode()).hexdigest()


def flat(pred):
    if not isinstance(pred, list):
        raise ValueError("prediction must be a list")
    result = [v for row in pred for v in row] if pred and isinstance(pred[0], list) else pred
    if any(type(v) is not int for v in result):
        raise ValueError("prediction must contain integer tokens")
    return result


def rows(pred, item):
    values = flat(pred)
    h, w = len(item.tokens), len(item.tokens[0])
    if len(values) != h * w:
        raise ValueError("prediction length differs from sealed input")
    return [values[i*w:(i+1)*w] for i in range(h)]


def identity(path):
    match = re.fullmatch(r"(patch|loop_meta|plain|loop)-seed([01])-(pre|fresh)", path.name)
    if not match:
        raise ValueError(f"unrecognized run directory {path.name}")
    arm, seed, init = match.groups()
    return arm, int(seed), init


class Audit:
    def __init__(self):
        self.errors, self.missing, self.limitations = [], [], []
        self.inputs = {}

    def read(self, path, optional=False, jsonl=False):
        if path.name in FORBIDDEN:
            raise ValueError(f"refused forbidden input {path.name}")
        if not path.is_file():
            if not optional:
                self.missing.append(str(path))
            return None
        self.inputs[str(path)] = sha(path)
        try:
            if jsonl:
                opener = gzip.open if path.suffix == ".gz" else open
                with opener(path, "rt", encoding="utf-8") as handle:
                    return [json.loads(line) for line in handle if line.strip()]
            return json.loads(path.read_text())
        except (ValueError, OSError, EOFError) as exc:
            self.errors.append(f"{path}: unreadable: {exc}")
            return None

    def compare(self, actual, expected, where):
        if isinstance(actual, dict):
            for name, value in actual.items():
                self.compare(value, expected.get(name) if isinstance(expected, dict) else None,
                             f"{where}/{name}")
        elif isinstance(actual, float):
            if not isinstance(expected, (int, float)) or not math.isfinite(expected) or not math.isclose(actual, expected, abs_tol=1e-9):
                self.errors.append(f"{where}: raw {actual!r} != reported {expected!r}")
        elif actual != expected:
            self.errors.append(f"{where}: raw {actual!r} != reported {expected!r}")


def stage_rows(raw, audit, where):
    """Use the plugin's final HOLDOUT_PHASES order, construction IDs 1..12."""
    by_stage = defaultdict(list)
    ids = {r.get("model_id") for r in raw}
    complete_ids = ids == set(range(1, 13))
    for r in raw:
        stage = r.get("phase")
        mid = r.get("model_id")
        if stage not in STAGES:
            if stage not in (None, "unassigned") or type(mid) is not int or not 1 <= mid <= 12:
                audit.errors.append(f"{where}: ambiguous/invalid phase {stage!r}, ID {mid!r}")
                continue
            stage = STAGES[mid - 1]
        elif type(mid) is not int or not 1 <= mid <= 12 or STAGES[mid - 1] != stage:
            audit.errors.append(f"{where}: phase/ID disagreement {stage}/{mid}")
        by_stage[stage].append(r)
    if not complete_ids:
        audit.errors.append(f"{where}: expected exactly 12 construction IDs (1..12)")
    return by_stage


def grade_panel(raw, items, grader, arm, fixed_depth, audit, where, wide=False):
    """Grade predictions against sealed Items, never raw targets or right flags."""
    expected = {key(it.tokens, it.slot): it for it in items}
    if len(expected) != len(items):
        audit.errors.append(f"{where}: sealed inputs are not unique")
    seen, right, fixed, rounds, caps = Counter(), 0, defaultdict(int), [], 0
    for number, row in enumerate(raw):
        try:
            inp = row.get("input", row)
            fingerprint = key(inp["tokens"], inp["slot"])
            seen[fingerprint] += 1
            if fingerprint not in expected:
                raise ValueError("input absent from sealed panel")
            item = expected[fingerprint]
            if not wide and any(k in row for k in ("target", "targets")):
                raise ValueError("holdout telemetry contains targets")
            prediction = row["pred" if wide else "selected_pred"]
            good = bool(grader(item, rows(prediction, item)))
            right += good
            if wide:
                if type(row.get("right")) is not bool or row["right"] != good:
                    raise ValueError("right flag differs from independent grade")
                for depth in (4, 8, 16, 32, 48):
                    fixed[str(depth)] += bool(grader(item, rows(row["fixed_pred"][str(depth)], item)))
                rr = row["round"]
            else:
                fixed["selected"] += bool(grader(item, rows(row["fixed_pred"], item)))
                rr = row["chosen_round"]
                if row["fixed_depth"] != fixed_depth:
                    raise ValueError("fixed depth differs from source-selected depth")
                if row.get("core") != ("loop" if arm == "loop_meta" else arm):
                    raise ValueError("core differs from directory identity")
            if type(rr) is not int or (rr != 1 if arm == "plain" else not 3 <= rr <= 48):
                raise ValueError("invalid chosen round")
            rounds.append(rr)
            caps += rr == 48 and arm != "plain"
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            audit.errors.append(f"{where} row {number+1}: {exc}")
    if seen != Counter({fp: 1 for fp in expected}):
        audit.errors.append(f"{where}: panel mismatch: missing={len(expected.keys()-seen.keys())}, "
                            f"extra={len(seen.keys()-expected.keys())}, duplicates={sum(v-1 for v in seen.values())}")
    return {"right": right, "n": len(raw), "fixed_right": dict(fixed) if wide else fixed["selected"],
            "mean_rounds": sum(rounds)/len(rounds) if rounds else None, "cap_hits": caps}


def curve(scores):
    counts = [scores[f"k{k}"]["9"]["right"] for k in RUNGS]
    if any(scores[f"k{k}"]["9"]["n"] != 300 for k in RUNGS):
        raise ValueError("F requires 300 examples at every positive rung")
    few = sum(counts[:4]) / 12
    return {"F_all": sum(counts)/27, "F_few": few,
            "F_few_minus_cold": few - scores["k0"]["9"]["right"]/3,
            "right9_by_rung": dict(zip(map(str, RUNGS), counts)),
            "k64_at_least_50_percent_report_only": counts[3] >= 150}


def v3(adaptations):
    return any(sum(30 < r["rungs"][str(k)]["9"]["right"] < 270
                   and r["rungs"][str(k)]["9"]["n"] == 300 for k in RUNGS) >= 3
               for r in adaptations)


def own_v3(adaptations):
    """Only the eight registered primary runs can establish a usable ladder."""
    required = [f"{arm}-seed{seed}-{init}" for seed in (0, 1)
                for arm, init in (("patch", "pre"), ("patch", "fresh"),
                                  ("loop_meta", "pre"), ("plain", "pre"))]
    if any(adaptations.get(name) is None for name in required):
        return None
    return v3([adaptations[name] for name in required])


def verify_manifest(manifest, audit):
    if not manifest:
        return
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        audit.errors.append("seal lacks a nonempty files/digest manifest")
        return
    for name, wanted in manifest.get("files", {}).items():
        path = ROOT / name
        if path.name in FORBIDDEN:
            audit.limitations.append(f"Forbidden lead file not read or hashed: {name}")
            continue
        if not path.is_file():
            audit.missing.append(str(path))
        else:
            actual = sha(path)
            audit.inputs[str(path)] = actual
            audit.compare(actual, wanted, f"manifest/{name}")


def source_checks(raw):
    old, gc = raw.get("old", {}), raw.get("gradient_check", {})
    return {
        "V1": all(old.get(k, {}).get("n") == 200 and old[k].get("right", -1) >= 190
                  for k in ("sums4", "grids5")),
        "V2": gc.get("nonzero_all") is True and gc.get("missing_both") == []
              and gc.get("matrix_count", 0) > 0}


def baseline_records(records, audit):
    """Select qualified sources by metadata, retaining original failures separately."""
    sources, adaptations = {}, {}
    source_paths = defaultdict(list)
    ambiguous_sources, ambiguous_adaptations = set(), set()
    originals, rejected = [], []
    for name, raw in records:
        ident = (raw.get("arm"), raw.get("seed"))
        if ident not in {(a, s) for a in ("loop", "plain") for s in (0, 1)}:
            audit.errors.append(f"unexpected baseline identity {ident!r}: {name}")
            continue
        if Path(name).name == "source.json":
            metadata = {k: raw.get(k) for k in BASELINE_SOURCE}
            if metadata != BASELINE_SOURCE:
                evidence = {"path": name, "arm": ident[0], "seed": ident[1],
                            "metadata": metadata, "checks": source_checks(raw), "old": raw.get("old"),
                            "excluded_fields": [k for k in BASELINE_SOURCE if metadata[k] != BASELINE_SOURCE[k]]}
                (originals if raw.get("source_steps") == 6000 else rejected).append(evidence)
                continue
            source_paths[ident].append(name)
            if ident in sources and sources[ident] != raw:
                ambiguous_sources.add(ident)
                audit.errors.append(f"conflicting qualified baseline sources for {ident!r}: {source_paths[ident]}")
            else:
                sources.setdefault(ident, raw)
        else:
            ident += (raw.get("init"),)
            if ident[-1] not in ("pre", "fresh"):
                audit.errors.append(f"unexpected baseline adaptation identity {ident!r}: {name}")
                continue
            if ident in adaptations and adaptations[ident] != raw:
                ambiguous_adaptations.add(ident)
                audit.errors.append(f"conflicting baseline adaptations for {ident!r}: {name}")
            else:
                adaptations.setdefault(ident, raw)
    for ident in ambiguous_sources:
        sources.pop(ident, None)
    for ident in ambiguous_adaptations:
        adaptations.pop(ident, None)
    need_src = {(a, s) for a in ("loop", "plain") for s in (0, 1)}
    need_adapt = {(a, s, i) for a, s in need_src for i in ("pre", "fresh")}
    source_complete = need_src <= sources.keys()
    adapt_complete = need_adapt <= adaptations.keys()
    if not source_complete:
        audit.missing.append("baseline qualified 12000-step/64-batch/9233000-guard source inventory incomplete or ambiguous")
    if not adapt_complete:
        audit.missing.append("baseline raw adaptation inventory incomplete or ambiguous")
    return {
        "V1": all(source_checks(sources[x])["V1"] for x in need_src) if source_complete else None,
        "V2": all(source_checks(sources[x])["V2"] for x in need_src) if source_complete else None,
        "V3": v3([adaptations[x] for x in need_adapt]) if adapt_complete else None,
        "required_source_metadata": BASELINE_SOURCE,
        "qualified_source_paths": {f"{a}-seed{s}": sorted(source_paths[(a, s)]) for a, s in sorted(sources)},
        "superseded_originals": sorted(originals, key=lambda r: r["path"]),
        "unqualified_source_records": sorted(rejected, key=lambda r: r["path"])}


def baseline(out, audit):
    record = audit.read(out / "BASELINE-VALIDITY.json")
    if record is None:
        return None
    records = []
    for name, digest in record.get("raw_sha256", {}).items():
        path = ROOT / name
        if path.name not in ("source.json", "adapt.json"):
            audit.errors.append(f"unexpected baseline raw path {name}")
            continue
        raw = audit.read(path)
        if raw is not None:
            audit.compare(sha(path), digest, f"baseline hash/{name}")
            records.append((name, raw))
    result = baseline_records(records, audit)
    audit.compare({k: result[k] for k in ("V1", "V2", "V3")}, record, "baseline validity")
    return result


def checkpoint_audit(folder, source, audit):
    import torch

    def load(path):
        if not path.exists():
            audit.missing.append(str(path))
            return None
        audit.inputs[str(path)] = sha(path)
        value = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(value, dict) or not all(isinstance(v, torch.Tensor) for v in value.values()):
            raise ValueError(f"{path}: expected tensor-only state_dict")
        return value

    arm, _, init = identity(folder)
    base = load(folder / "k0.pt")
    if base is None:
        return None
    count = sum(math.prod(v.shape) for v in base.values())
    audit.compare(count, source["weights"], f"{folder.name}/state coefficients")
    result = {"state_coefficients": count, "ordinary_frozen": None, "sleep_patch_zero": None}
    if arm != "patch":
        return result
    patch_names = {"patch_A", "patch_B"}
    if not patch_names <= base.keys():
        audit.errors.append(f"{folder}: missing fast patch buffers")
        return result
    frozen, sleep_zero = [], []
    if init == "pre":
        for stage in ("k1", "k4", "k16", "k64"):
            state = load(folder / f"{stage}.pt")
            if state is not None:
                good = state.keys() == base.keys() and all(torch.equal(v, state[name])
                            for name, v in base.items() if name not in patch_names)
                frozen.append(good)
                if not good:
                    audit.errors.append(f"{folder.name}/{stage}: ordinary weights changed")
    for stage in ("sleep64", "sleep64k"):
        state = load(folder / f"{stage}.pt")
        if state is not None:
            good = all(name in state and torch.count_nonzero(state[name]).item() == 0 for name in patch_names)
            sleep_zero.append(good)
            if not good:
                audit.errors.append(f"{folder.name}/{stage}: patch not zero")
    result.update(ordinary_frozen=all(frozen) if len(frozen) == 4 else None,
                  sleep_patch_zero=all(sleep_zero) if len(sleep_zero) == 2 else None)
    return result


def gates(jobs, sources):
    """Pure arithmetic, per seed. None never becomes a successful verdict."""
    result = {}
    for seed in (0, 1):
        try:
            p = jobs[f"patch-seed{seed}-pre"]
            lm = jobs[f"loop_meta-seed{seed}-pre"]
            plain = jobs[f"plain-seed{seed}-pre"]
            fresh = jobs[f"patch-seed{seed}-fresh"]
            loop = jobs[f"loop-seed{seed}-pre"]
            ps = sources[f"patch-seed{seed}"]
            ls = sources[f"loop_meta-seed{seed}"]
            f = p["curve"]["F_all"]
            margins = {"loop_meta": f-lm["curve"]["F_all"],
                       "plain": f-plain["curve"]["F_all"], "fresh": f-fresh["curve"]["F_all"]}
            source_gate = all(sources[f"{a}-seed{seed}"]["old"][k]["n"] == 200
                              and sources[f"{a}-seed{seed}"]["old"][k]["right"] >= 190
                              for a in ARMS for k in ("sums4", "grids5")) and all(
                                  ps["old"][k]["right"] >= ls["old"][k]["right"]-6 for k in ("sums4", "grids5"))
            wide_source = all(j["wide"]["k0"][k]["n"] == 300 and
                              j["wide"]["k0"][k]["right"] >= (285 if k in ("sums", "grids") else 270)
                              for j in (p, lm, plain, loop) for k in KINDS) and all(
                                  p["wide"]["k0"][k]["right"] >= r["wide"]["k0"][k]["right"]-9
                                  for r in (lm, loop) for k in KINDS)
            old_sleep = all(p["adapt"]["sleep"][b]["old"][k]["n"] == 200
                            and lm["adapt"]["sleep"][b]["old"][k]["n"] == 200
                            and p["adapt"]["sleep"][b]["old"][k]["right"] >=
                            lm["adapt"]["sleep"][b]["old"][k]["right"]-6
                            for b in ("64", "64k") for k in ("sums4", "grids5"))
            wide_sleep = all(p["wide"][s][k]["n"] == lm["wide"][s][k]["n"] == 300 and
                             p["wide"][s][k]["right"] >= lm["wide"][s][k]["right"]-9
                             for s in ("sleep64", "sleep64k") for k in KINDS)
            budget = abs(ps["weights"]-ls["weights"])/ls["weights"] <= .02
            stop = all(value["fixed_right"]-value["right"] <= value["n"]*.02 + 1e-9
                       for panel in p["scores"].values() for value in panel.values())
            support = p.get("support_fit")
            support_improved = (support["before64"]["n"] == support["after64"]["n"] == 64 and
                                support["after64"]["right"] > support["before64"]["right"]) if support else None
            # Learned-stop gaps are reported diagnostics, not promotion bars.
            common = source_gate and wide_source and old_sleep and wide_sleep and budget
            result[str(seed)] = {"margins_pp": margins, "original_source_gate": source_gate,
                "wide_source_gate": wide_source, "original_postsleep_gate": old_sleep,
                "wide_postsleep_gate": wide_sleep, "coefficient_budget": budget,
                "stop_within_two_points": stop, "support_fit_improved_reported": support_improved,
                "test_a_bars": common and margins["loop_meta"] >= 10-1e-9 and
                margins["plain"] >= 5-1e-9 and margins["fresh"] >= 5-1e-9,
                "old_gate_broken": not (source_gate and wide_source and old_sleep and wide_sleep)}
        except (KeyError, TypeError, ZeroDivisionError):
            result[str(seed)] = {"test_a_bars": None, "limitation": "missing per-seed gate inputs"}
    negative = None
    if all("margins_pp" in x for x in result.values()):
        if all(x["support_fit_improved_reported"] is not None for x in result.values()):
            negative = all(x["support_fit_improved_reported"] and x["margins_pp"]["loop_meta"] <= 0
                           for x in result.values())
    return {"seeds": result, "registered_support_improvement_negative": negative,
            "maze_gain_with_old_gate_break": any(x.get("margins_pp", {}).get("loop_meta", 0) > 0
                                                   and x.get("old_gate_broken", False) for x in result.values())}


def run(out, checkpoints=False):
    audit = Audit()
    seal = audit.read(out / "RACE-SEAL.json")
    verify_manifest(seal, audit)
    # The candidate seal binds PANELS.json and the independent old-kind checker.
    candidate = audit.read(out / "CANDIDATE-SEAL.json")
    verify_manifest(candidate, audit)
    audit.read(out / "PRACTICE-GATES.json")  # provenance only; recompute from raw panels below
    validity = baseline(out, audit)
    result = {"baseline": validity, "jobs": {}, "sources": {}}
    # Do not even regenerate holdout panels if the ruler is known invalid.
    if validity and any(validity.get(k) is False for k in ("V1", "V2", "V3")):
        result["status"] = "inconclusive"
        return finish(out, audit, result)
    folders = [out / "race" / f"{a}-seed{s}-{i}" for s in (0, 1)
               for a, i in [(a, "pre") for a in ARMS] + [("patch", "fresh")]]
    adaptations = {f.name: audit.read(f / "adapt.json") for f in folders}
    result["own_V3"] = own_v3(adaptations)
    if result["own_V3"] is False:
        result["status"] = "inconclusive"
        return finish(out, audit, result)
    if not any((f / "holdout-predictions.jsonl.gz").exists() for f in folders):
        audit.missing.append("no holdout prediction telemetry; no panel generated or model run")
        result["status"] = "untested"
        return finish(out, audit, result)
    # Imports below contain generators/checkers only. No harness or model imports.
    sys.path.insert(0, str(ROOT / "scripts"))
    import claude_fewex_data as F
    import claude_patch_data as D
    import claude_rsn358a_envs as E
    import claude_rsn358m_maze as M

    panels, _ = F.panels()
    holdout = panels["holdout"]
    result["sealed_holdout_sizes"] = {}
    for size, n in SIZES.items():
        audit.compare(len(holdout[size]), n, f"sealed holdout/{size}")
        audit.compare(len({F.layout_key(it) for it in holdout[size]}), n, f"sealed layouts/{size}")
        result["sealed_holdout_sizes"][str(size)] = {"n": len(holdout[size]),
            "unique_layouts": len({F.layout_key(it) for it in holdout[size]})}
    panel_file = audit.read(out / "PANELS.json")
    if panel_file is None:
        result["status"] = "untested"
        return finish(out, audit, result)
    wide = {k: [E.Item(**it) for it in panel_file["verify"][k]] for k in KINDS}
    for arm in ARMS:
        for seed in (0, 1):
            name = f"{arm}-seed{seed}"
            path = out / "race/sources" / name
            source = audit.read(path / "source.json")
            if source is not None:
                result["sources"][name] = source
                audit.compare(OWN_SOURCE, source, f"{name}/own source metadata")
                if source.get("fixed_depth") not in ((1,) if arm == "plain" else (8, 16, 32, 48)):
                    audit.errors.append(f"{name}: invalid source-selected depth")
                gc = source.get("gradient_check", {})
                if gc.get("nonzero_all") is not True or gc.get("missing_both") != [] or gc.get("matrix_count", 0) <= 0:
                    audit.errors.append(f"{name}: source matrix-gradient validity failed or missing")
                if arm != "plain":
                    depth_counts = source.get("fixed_source_dev", {})
                    if all(str(d) in depth_counts for d in (8, 16, 32, 48)):
                        chosen = max((8, 16, 32, 48), key=lambda d: (depth_counts[str(d)], -d))
                        audit.compare(chosen, source["fixed_depth"], f"{name}/source depth selection")
                    else:
                        audit.missing.append(f"{name}: source fixed-depth selection counts")
                if (path / "source.pt").exists():
                    audit.compare(sha(path / "source.pt"), source.get("export_sha256"), f"{name}/export sha")
    for folder in folders:
        arm, seed, init = identity(folder)
        source = result["sources"].get(f"{arm}-seed{seed}")
        harness = audit.read(folder / "holdout.json")
        adapt = adaptations[folder.name]
        raw = audit.read(folder / "holdout-predictions.jsonl.gz", jsonl=True)
        if source is None or harness is None or adapt is None or raw is None:
            continue
        for row in raw:
            if row.get("init") != init:
                audit.errors.append(f"{folder.name}: telemetry init disagrees with folder")
        grouped = stage_rows(raw, audit, folder.name)
        job = {"scores": {}, "wide": {}, "adapt": adapt,
               "support_fit": audit.read(folder / "support-fit.json", optional=True)}
        job["original_old_forgetting_pp"] = {
            b: {k: (adapt["old"]["before"][k]["right"]-adapt["sleep"][b]["old"][k]["right"])/2
                for k in ("sums4", "grids5")} for b in ("64", "64k")}
        for stage in STAGES:
            job["scores"][stage] = {}
            groups = defaultdict(list)
            for row in grouped[stage]:
                size = len(row.get("tokens", []))
                if size not in SIZES:
                    audit.errors.append(f"{folder.name}/{stage}: unexpected size {size}")
                groups[size].append(row)
            for size in SIZES:
                value = grade_panel(groups[size], holdout[size], M.check_maze, arm,
                                    source["fixed_depth"], audit, f"{folder.name}/{stage}/{size}")
                job["scores"][stage][str(size)] = value
                harness_key = stage[1:] if stage.startswith("k") else stage
                audit.compare(value, harness.get("scores", {}).get(harness_key, {}).get(str(size)),
                              f"{folder.name}/holdout/{stage}/{size}")
        try:
            job["curve"] = curve(job["scores"])
        except ValueError as exc:
            audit.errors.append(f"{folder.name}: {exc}")
        wide_summary = audit.read(folder / "wide-old.json")
        for stage in WIDE_STAGES:
            wide_raw = audit.read(folder / f"{stage}-wide-raw.jsonl", jsonl=True)
            if wide_raw is None:
                continue
            by_kind = defaultdict(list)
            for row in wide_raw:
                by_kind[row.get("kind")].append(row)
            if set(by_kind) != set(KINDS):
                audit.errors.append(f"{folder.name}/{stage}: wide kind inventory differs")
            job["wide"][stage] = {}
            for kind in KINDS:
                value = grade_panel(by_kind[kind], wide[kind],
                                    lambda it, pred: D.check(it, flat(pred)), arm, None, audit,
                                    f"{folder.name}/{stage}/{kind}", wide=True)
                audit.compare(value["n"], 300, f"{folder.name}/{stage}/{kind}/panel size")
                job["wide"][stage][kind] = value
                audit.compare(value, (wide_summary or {}).get(stage, {}).get(kind),
                              f"{folder.name}/wide-old/{stage}/{kind}")
        # Original 200-example scores are in adapt.json. Telemetry may also log
        # them; phases few64 and k65536 identify immediate old-kind rows.
        dev_raw = audit.read(folder / "adapt-predictions.jsonl.gz", optional=True, jsonl=True)
        if dev_raw is None:
            audit.limitations.append(f"{folder.name}: original 200 old-kind gates use adapt.json counts; "
                                     "no adapt-predictions.jsonl.gz for independent regrade")
        else:
            old_panels = F.old_panels()
            for phase, destination in (("k0", adapt["old"]["before"]),
                    ("few64", adapt["old"]["after_64"]), ("k65536", adapt["old"]["after_64k"]),
                    ("sleep64", adapt["sleep"]["64"]["old"]), ("sleep64k", adapt["sleep"]["64k"]["old"])):
                for kind, items in old_panels.items():
                    wanted = {key(it.tokens, it.slot) for it in items}
                    selected = [r for r in dev_raw if r.get("phase") == phase and
                                key(r["tokens"], r["slot"]) in wanted]
                    value = grade_panel(selected, items, E.check, arm, source["fixed_depth"], audit,
                                        f"{folder.name}/old200/{phase}/{kind}")
                    audit.compare(value, destination[kind], f"{folder.name}/adapt/{phase}/{kind}")
        if checkpoints:
            job["checkpoint_audit"] = checkpoint_audit(folder, source, audit)
        result["jobs"][folder.name] = job
    result["gates"] = gates(result["jobs"], result["sources"])
    if not checkpoints:
        audit.limitations.append("Checkpoint coefficient totals, frozen ordinary weights, and zero post-sleep patch untested; use --checkpoints.")
    audit.limitations.append("Source 200-example guards, V2 gradient flags and optional support fit use recorded counts; no model rerun.")
    result["status"] = "untested" if audit.missing or any(
        s["test_a_bars"] is None for s in result["gates"]["seeds"].values()) else (
        "audit_discrepancy" if audit.errors else "bars_met" if all(
            s["test_a_bars"] for s in result["gates"]["seeds"].values()) else "bars_not_met")
    return finish(out, audit, result)


def finish(out, audit, result):
    result.update(utc=subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip(),
                  errors=audit.errors, missing=audit.missing, limitations=audit.limitations,
                  input_sha256=audit.inputs)
    out.mkdir(parents=True, exist_ok=True)
    (out / "BLIND-RACE-RECOUNT.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    lines = ["# Independent blind race recount", "", f"UTC: {result['utc']}", "",
             f"Status: **{result['status']}**. No model inference or training was performed.", ""]
    for name, job in result["jobs"].items():
        if "curve" in job:
            c = job["curve"]
            lines.append(f"- {name}: F_all {c['F_all']:.6f}; F_few {c['F_few']:.6f}; "
                         + ", ".join(f"k{k}: {n} of 300" for k, n in c["right9_by_rung"].items()))
    for title, values in (("Discrepancies", audit.errors), ("Untested / missing", audit.missing),
                          ("Limits of evidence", audit.limitations)):
        if values:
            lines.extend(["", f"**{title}**", ""] + [f"- {v}" for v in values])
    (out / "BLIND-RACE-RECOUNT.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"status": result["status"], "errors": len(audit.errors), "missing": len(audit.missing)}))
    return 1 if audit.errors else 0


def self_test():
    """Synthetic Items and mock graders only; does not import puzzle generators."""
    import copy
    import unittest

    class Tests(unittest.TestCase):
        def test_raw_counts_and_duplicates(self):
            item = SimpleNamespace(tokens=[[7]], slot=[[1]])
            row = dict(tokens=item.tokens, slot=item.slot, selected_pred=[8], fixed_pred=[8],
                       chosen_round=48, fixed_depth=16, core="patch")
            audit = Audit()
            score = grade_panel([row], [item], lambda it, p: p == [[8]], "patch", 16, audit, "mock")
            self.assertEqual(score, dict(right=1, n=1, fixed_right=1, mean_rounds=48., cap_hits=1))
            self.assertEqual(audit.errors, [])
            grade_panel([row, row], [item], lambda it, p: True, "patch", 16, audit, "mock")
            self.assertTrue(any("duplicates=1" in e for e in audit.errors))

        def test_wide_uses_sealed_item(self):
            item = SimpleNamespace(tokens=[[1]], slot=[[1]], answer=5)
            row = dict(input=dict(tokens=[[1]], slot=[[1]], target=[[999]]), pred=[5], right=True,
                       round=1, fixed_pred={str(d): [5] for d in (4, 8, 16, 32, 48)})
            audit = Audit()
            result = grade_panel([row], [item], lambda it, p: p == [[it.answer]], "plain", None, audit, "mock", True)
            self.assertEqual(result["right"], 1)
            self.assertFalse(audit.errors)
            row["right"] = False
            grade_panel([row], [item], lambda it, p: True, "plain", None, audit, "mock", True)
            self.assertTrue(audit.errors)

        def test_stage_mapping_and_fresh_identity(self):
            audit = Audit()
            data = [dict(model_id=i+1, phase=s) for i, s in enumerate(STAGES)]
            self.assertEqual(set(stage_rows(data, audit, "mock")), set(STAGES))
            self.assertFalse(audit.errors)
            data[0]["phase"] = "k64"
            stage_rows(data, audit, "mock")
            self.assertTrue(audit.errors)
            zero_based = Audit()
            stage_rows([dict(model_id=i, phase=s) for i, s in enumerate(STAGES)], zero_based, "mock")
            self.assertTrue(zero_based.errors)
            self.assertEqual(identity(Path("loop_meta-seed1-fresh")), ("loop_meta", 1, "fresh"))

        def test_f_and_v3_boundaries(self):
            scores = {s: {"9": dict(right=150, n=300)} for s in STAGES}
            self.assertEqual(curve(scores)["F_all"], 50)
            self.assertEqual(curve(scores)["F_few"], 50)
            a = {"rungs": {str(k): {"9": dict(right=30, n=300)} for k in RUNGS}}
            self.assertFalse(v3([a]))
            for k in RUNGS[:3]:
                a["rungs"][str(k)]["9"]["right"] = 31
            self.assertTrue(v3([a]))
            a["rungs"]["1"]["9"]["right"] = 270
            self.assertFalse(v3([a]))

        def test_comparison_rejects_missing_and_wrong_mean(self):
            audit = Audit()
            audit.compare(dict(right=4, mean_rounds=3.5), dict(right=4, mean_rounds=4), "mock")
            self.assertEqual(len(audit.errors), 1)
            audit.compare(dict(fixed_right=3), {}, "mock")
            self.assertEqual(len(audit.errors), 2)

        def baseline_fixture(self):
            records = []
            for arm in ("loop", "plain"):
                for seed in (0, 1):
                    source = dict(arm=arm, seed=seed, source_steps=12000,
                                  source_batch=64, source_guard_seed=9233000,
                                  old={k: dict(n=200, right=195) for k in ("sums4", "grids5")},
                                  gradient_check=dict(nonzero_all=True, missing_both=[], matrix_count=10))
                    records.append((f"mock/qualified-{arm}-{seed}/source.json", source))
                    for init in ("pre", "fresh"):
                        records.append((f"mock/{arm}-{seed}-{init}/adapt.json",
                            dict(arm=arm, seed=seed, init=init, rungs={str(k): {
                                "9": dict(right=150, n=300)} for k in RUNGS})))
            return records

        def test_baseline_preserves_original_failures_without_override(self):
            records = self.baseline_fixture()
            originals = []
            for name, row in records:
                if name.endswith("source.json"):
                    old = copy.deepcopy(row)
                    old.update(source_steps=6000, source_guard_seed=9232700)
                    old["old"]["grids5"]["right"] = 189
                    originals.append((name.replace("qualified", "original"), old))
            for ordered in (records + originals, originals + records):
                audit = Audit()
                result = baseline_records(ordered, audit)
                self.assertTrue(all(result[k] for k in ("V1", "V2", "V3")))
                self.assertEqual(len(result["qualified_source_paths"]), 4)
                self.assertEqual(len(result["superseded_originals"]), 4)
                self.assertTrue(all(r["checks"]["V1"] is False for r in result["superseded_originals"]))
                self.assertFalse(audit.errors or audit.missing)

        def test_baseline_requires_exact_qualified_metadata(self):
            for field, value in (("source_steps", 6000), ("source_steps", 18000),
                                 ("source_batch", 32), ("source_guard_seed", 9232700),
                                 ("source_guard_seed", None)):
                with self.subTest(field=field, value=value):
                    records = self.baseline_fixture()
                    records[0][1][field] = value
                    if value is None:
                        del records[0][1][field]
                    audit = Audit()
                    result = baseline_records(records, audit)
                    self.assertIsNone(result["V1"])
                    self.assertIsNone(result["V2"])
                    self.assertEqual(len(result["qualified_source_paths"]), 3)
                    self.assertTrue(audit.missing)

        def test_baseline_qualified_failure_and_duplicate_are_not_hidden(self):
            records = self.baseline_fixture()
            records[0][1]["old"]["grids5"]["right"] = 189
            records[0][1]["gradient_check"]["nonzero_all"] = False
            result = baseline_records(records, Audit())
            self.assertIs(result["V1"], False)
            self.assertIs(result["V2"], False)
            duplicate = copy.deepcopy(records[0][1])
            duplicate["old"]["grids5"]["right"] = 200
            duplicate["gradient_check"]["nonzero_all"] = True
            other = [("mock/duplicate/source.json", duplicate)]
            for ordered in (records + other, other + records):
                audit = Audit()
                result = baseline_records(ordered, audit)
                self.assertIsNone(result["V1"])
                self.assertIsNone(result["V2"])
                self.assertTrue(any("conflicting qualified" in e for e in audit.errors))

        def test_ordinary_loop_cannot_rescue_own_v3(self):
            data = {}
            for seed in (0, 1):
                for arm, init in (("patch", "pre"), ("patch", "fresh"),
                                  ("loop_meta", "pre"), ("plain", "pre"), ("loop", "pre")):
                    data[f"{arm}-seed{seed}-{init}"] = {"rungs": {
                        str(k): {"9": dict(right=150 if arm == "loop" else 0, n=300)}
                        for k in RUNGS}}
            self.assertTrue(v3(list(data.values())))
            self.assertIs(own_v3(data), False)
            for k in RUNGS[:3]:
                data["patch-seed1-fresh"]["rungs"][str(k)]["9"]["right"] = 31
            self.assertIs(own_v3(data), True)
            del data["loop-seed0-pre"]
            self.assertIs(own_v3(data), True)
            del data["plain-seed0-pre"]
            self.assertIsNone(own_v3(data))

        def gate_fixture(self):
            jobs, sources = {}, {}
            old = {k: dict(n=200, right=195) for k in ("sums4", "grids5")}
            wide = {s: {k: dict(n=300, right=290) for k in KINDS} for s in WIDE_STAGES}
            for seed in (0, 1):
                for arm in ARMS:
                    sources[f"{arm}-seed{seed}"] = dict(old=copy.deepcopy(old), weights=1000)
                for arm, init, f in (("patch", "pre", 60), ("loop_meta", "pre", 50),
                                     ("loop", "pre", 50), ("plain", "pre", 55), ("patch", "fresh", 55)):
                    jobs[f"{arm}-seed{seed}-{init}"] = dict(curve=dict(F_all=f), wide=copy.deepcopy(wide),
                        adapt=dict(sleep={b: dict(old=copy.deepcopy(old)) for b in ("64", "64k")}),
                        scores={s: {"9": dict(right=150, fixed_right=150, n=300)} for s in STAGES},
                        support_fit=dict(before64=dict(n=64, right=2), after64=dict(n=64, right=3)))
            return jobs, sources

        def test_stop_gap_is_report_only(self):
            jobs, sources = self.gate_fixture()
            before = gates(jobs, sources)["seeds"]
            for seed in (0, 1):
                jobs[f"patch-seed{seed}-pre"]["scores"]["k64"]["9"]["fixed_right"] = 200
            after = gates(jobs, sources)["seeds"]
            for seed in ("0", "1"):
                self.assertIs(before[seed]["stop_within_two_points"], True)
                self.assertIs(after[seed]["stop_within_two_points"], False)
                self.assertIs(before[seed]["test_a_bars"], True)
                self.assertEqual(before[seed]["test_a_bars"], after[seed]["test_a_bars"])

        def test_both_seeds_and_old_gates(self):
            jobs, sources = self.gate_fixture()
            self.assertTrue(all(v["test_a_bars"] for v in gates(jobs, sources)["seeds"].values()))
            for seed in (0, 1):
                jobs[f"patch-seed{seed}-pre"]["curve"]["F_all"] = 50
            self.assertTrue(gates(jobs, sources)["registered_support_improvement_negative"])
            for seed in (0, 1):
                jobs[f"patch-seed{seed}-pre"]["curve"]["F_all"] = 60
            jobs["patch-seed1-pre"]["wide"]["sleep64"]["sorting"]["right"] = 280
            self.assertFalse(gates(jobs, sources)["seeds"]["1"]["test_a_bars"])
            self.assertTrue(gates(jobs, sources)["seeds"]["0"]["test_a_bars"])
            del jobs["patch-seed1-fresh"]
            self.assertIsNone(gates(jobs, sources)["seeds"]["1"]["test_a_bars"])

    return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--checkpoints", action="store_true", help="read tensor state_dicts on CPU; no model construction")
    parser.add_argument("--self-test", action="store_true", help="synthetic tests only; writes no evidence")
    args = parser.parse_args()
    raise SystemExit(self_test() if args.self_test else run(args.out.resolve(), args.checkpoints))
