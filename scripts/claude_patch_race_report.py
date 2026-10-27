#!/usr/bin/env python3
"""Aggregate existing Test A JSON; never import models, generate or score puzzles.

Usage: python3 -B scripts/claude_patch_race_report.py --out ARTIFACT_ROOT
Writes only RACE-RESULTS.json and RESULTS.md when invoked. The verdict is
provisional until the separate blind recount. Missing/invalid required records
cannot produce a promotion or rejection. Optional telemetry and support fit
are disclosed without invented values. BASELINE-VALIDITY accepts the locked
report's V1/V2/V3 booleans at the top level or under `gate`/`validity`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "artifacts/claude-patch-20260927"
ARMS = ("patch", "loop_meta", "plain", "loop")
KINDS = ("sums", "grids", "sorting", "reversing", "counting", "brackets")
FEW = ("1", "4", "16", "64")
POSITIVE = FEW + ("256", "1024", "4096", "16384", "65536")
RUNGS = ("0",) + POSITIVE
STAGES = ("k0", "k64", "k65536", "sleep64", "sleep64k")
OLD = ("sums4", "grids5")
LAYOUTS = {"dev": {"7": 24, "9": 300, "11": 300},
           "holdout": {"7": 48, "9": 300, "11": 300}}


def at(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def integer(x):
    return isinstance(x, int) and not isinstance(x, bool)


def pct(row):
    return Fraction(100 * row["right"], row["n"])


def counts(row):
    return f'{row["right"]} of {row["n"]}' if row else "untested"


def number(x):
    return "untested" if x is None else f"{float(x):.3f}"


class Report:
    def __init__(self, out):
        self.out = Path(out)
        self.issues = []
        self.inputs = {}
        self.gates = {}
        self.jobs = {}
        self.sources = {}

    def read(self, relative, optional=False):
        path = self.out / relative
        if not path.exists():
            if not optional:
                self.issues.append(f"missing: {relative}")
            return None
        try:
            raw = path.read_bytes()
            self.inputs[str(relative)] = hashlib.sha256(raw).hexdigest()
            return json.loads(raw)
        except (OSError, ValueError) as exc:
            self.issues.append(f"invalid: {relative}: {exc}")
            return None

    def score(self, row, n, label, *, wide=False):
        if not isinstance(row, dict) or not integer(row.get("right")) or row.get("n") != n \
                or not 0 <= row["right"] <= n:
            self.issues.append(f"missing/invalid score ({n} expected): {label}")
            return None
        for key in ("fixed_right", "cap_hits"):
            if key == "fixed_right" and wide and isinstance(row.get(key), dict):
                depths = row[key]
                if not depths or any(str(d) not in ("4", "8", "16", "32", "48")
                                     or not integer(count) or not 0 <= count <= n
                                     for d, count in depths.items()):
                    self.issues.append(f"invalid fixed_right depth counts: {label}")
                    return None
                continue
            if key in row and (not integer(row[key]) or not 0 <= row[key] <= n):
                self.issues.append(f"invalid {key}: {label}")
                return None
        return row

    def read_telemetry(self, relative):
        path = self.out / relative
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
            self.inputs[relative] = hashlib.sha256(raw).hexdigest()
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            if any(not isinstance(row, dict) for row in rows):
                raise ValueError("telemetry events must be objects")
            return rows
        except (ValueError, OSError) as exc:
            self.issues.append(f"invalid telemetry: {relative}: {exc}")
            return None

    def inference_totals(self, rows, label):
        """Sum only plugin inference_batch deltas, never controller snapshots.

        These are actual executed forwards, including full-depth harness scoring;
        they are not estimates of latency with physical learned-stop execution.
        """
        events = [row for row in (rows or ()) if row.get("event") == "inference_batch"]
        if not events:
            return None
        for row in events:
            seconds, macs = row.get("seconds_delta"), row.get("forward_macs_delta")
            if (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
                    or not math.isfinite(seconds) or seconds < 0
                    or not integer(macs) or macs < 0):
                self.issues.append(f"invalid inference_batch delta: {label}")
                return None
        return {"inference_batches": len(events),
                "seconds": math.fsum(row["seconds_delta"] for row in events),
                "forward_macs": sum(row["forward_macs_delta"] for row in events),
                "scope": "executed inference forwards only; cumulative snapshots excluded"}

    def learner_resources(self, rows, label):
        """Keep the last cumulative snapshot per sequence/learner ordinal.

        A sequence reset may reuse ordinals, so both identify a learner within
        one command's telemetry file. Replay memory is preserved verbatim:
        packed tensors, Python object graphs and working-state estimates are
        different representations, not quantities to add or call peak memory.
        """
        final = {}
        memory = []
        for row in rows or ():
            if row.get("event") == "replay_memory":
                memory.append(row)
            if row.get("event") not in ("learner_created", "batch_complete", "sleep_complete_patch_removed"):
                continue
            ordinal, sequence = row.get("ordinal"), row.get("sequence")
            if (not integer(ordinal) or ordinal < 0 or not integer(sequence) or sequence < 0
                    or not isinstance(row.get("counters"), dict)):
                self.issues.append(f"invalid learner snapshot identity/counters: {label}")
                continue
            final[(sequence, ordinal)] = row
        snapshots = [final[key] for key in sorted(final)]
        fields = ("training_seconds", "support_seconds", "training_matrix_macs",
                  "optimizer_steps", "writes", "differentiable_writes",
                  "support_predictions", "support_rounds", "forward_round_examples",
                  "gradient_round_examples", "sleep_examples", "sleep_sums",
                  "sleep_grids", "sleep_branch")
        totals = {}
        for field in fields:
            values = [row["counters"].get(field) for row in snapshots]
            if not values or any(v is None for v in values):
                totals[field] = None
                continue
            if any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or v < 0
                   or (not field.endswith("_seconds") and not integer(v)) for v in values):
                self.issues.append(f"invalid cumulative {field}: {label}")
                totals[field] = None
                continue
            totals[field] = math.fsum(values) if field.endswith("_seconds") else sum(values)
        return {"final_learner_snapshots": snapshots or None,
                "training_totals": totals,
                "timing_note": "training_seconds includes support_seconds; do not add them",
                "aggregation_note": "last observed snapshot per sequence/ordinal; global cumulative copies excluded; no inference counters summed here",
                "replay_memory_events": memory or None,
                "memory_note": "recorded snapshots/estimates only; no peak memory measured or inferred; representations are not additive"}

    def gate(self, name, value):
        self.gates[name] = value
        return value

    def compare(self, name, a, b, allowance):
        return self.gate(name, None if a is None or b is None else
                         pct(a) >= pct(b) - allowance)

    def load(self):
        self.seal = self.read("RACE-SEAL.json")
        if not isinstance(self.seal, dict) or not self.seal:
            self.issues.append("missing/invalid race seal object")
        self.validity = self.read("BASELINE-VALIDITY.json")
        self.practice = self.read("PRACTICE-GATES.json")
        self.race_v3 = self.read("RACE-V3.json")
        race_passed = at(self.race_v3, "passed")
        if type(race_passed) is not bool:
            self.issues.append("missing/invalid own race V3 passed boolean")
            race_passed = None
        self.gate("race_V3", race_passed)
        validity = self.validity
        if isinstance(validity, dict):
            validity = validity.get("gate", validity.get("validity", validity))
        for key in ("V1", "V2", "V3"):
            value = at(validity, key)
            if type(value) is not bool:
                self.issues.append(f"missing/invalid baseline {key} boolean")
                value = None
            self.gate(key, value)
        passed = at(self.practice, "passed")
        if type(passed) is not bool:
            self.issues.append("missing/invalid practice passed boolean")
            passed = None
        self.gate("practice", passed)
        for seed in (0, 1):
            for arm in ARMS:
                label = f"{arm}-seed{seed}"
                src = self.read(f"race/sources/{label}/source.json")
                self.sources[label] = src
                if src is not None and (at(src, "arm") != ("plain" if arm == "plain" else "loop")
                                        or at(src, "seed") != seed):
                    self.issues.append(f"source identity mismatch: {label}")
                for init in (("pre", "fresh") if arm == "patch" else ("pre",)):
                    name = f"{label}-{init}"
                    folder = f"race/{name}"
                    job = {k: self.read(f"{folder}/{filename}", optional=optional)
                           for k, filename, optional in (
                               ("adapt", "adapt.json", False), ("holdout", "holdout.json", False),
                               ("wide", "wide-old.json", False), ("fit", "support-fit.json", True))}
                    for k in ("adapt", "holdout"):
                        row = job[k]
                        if row is not None and (at(row, "arm") != ("plain" if arm == "plain" else "loop")
                                                or at(row, "seed") != seed or at(row, "init") != init):
                            self.issues.append(f"{name}/{k}: identity mismatch")
                    job["telemetry"] = {phase: self.read_telemetry(f"{folder}/{phase}-telemetry.jsonl")
                                        for phase in ("adapt", "holdout")}
                    self.jobs[name] = job

    def analyze_job(self, name, job):
        adapt, hold, wide = job["adapt"], job["holdout"], job["wide"]
        result = {"curves": {}, "wide_old": {}, "old": {}, "sleep_D": {}}
        if adapt is not None:
            if at(adapt, "panel_layouts") != LAYOUTS:
                self.issues.append(f"panel layout counts do not match locked panels: {name}")
            for k, expected in (("support_unique_layouts", 64), ("stream_unique_layouts", 65536),
                                ("stream_panel_overlap", 0), ("stream_support_overlap", 0)):
                if at(adapt, k) != expected:
                    self.issues.append(f"invalid/missing {k}: {name}")
        for stage in RUNGS + ("sleep64", "sleep64k"):
            curve = {}
            for split in ("dev", "holdout"):
                sizes = {}
                for size, n in LAYOUTS[split].items():
                    if split == "holdout":
                        row = at(hold, "scores", stage, size)
                    elif stage.startswith("sleep"):
                        row = at(adapt, "sleep", stage[5:], "maze_dev", size)
                    else:
                        row = at(adapt, "rungs", stage, size)
                    row = self.score(row, n, f"{name}/{split}/{stage}/{size}")
                    sizes[size] = row
                    if row is not None:
                        if "fixed_right" not in row:
                            self.issues.append(f"missing fixed-depth score: {name}/{split}/{stage}/{size}")
                        row = dict(row)
                        row["stop_loss_pp"] = (100 * (row["fixed_right"] - row["right"]) / n
                                               if "fixed_right" in row else None)
                        row["stop_failure_report_only"] = (100 * (row["fixed_right"] - row["right"]) > 2 * n
                                                          if "fixed_right" in row else None)
                        sizes[size] = row
                curve[split] = sizes
            result["curves"][stage] = curve
        main = {k: result["curves"][k]["holdout"]["9"] for k in RUNGS}
        f_all = sum((pct(main[k]) for k in POSITIVE), Fraction()) / 9 if all(main[k] for k in POSITIVE) else None
        f_few = sum((pct(main[k]) for k in FEW), Fraction()) / 4 if all(main[k] for k in FEW) else None
        cold = pct(main["0"]) if main["0"] else None
        result["metrics"] = {"F_all": f_all, "F_few": f_few, "cold": cold,
                             "F_few_minus_cold": f_few - cold if f_few is not None and cold is not None else None,
                             "k64_ge_50_report_only": pct(main["64"]) >= 50 if main["64"] else None}
        for stage in STAGES:
            result["wide_old"][stage] = {kind: self.score(at(wide, stage, kind), 300, f"{name}/{stage}/{kind}", wide=True)
                                         for kind in KINDS}
        for stage, path in (("k0", ("old", "before")), ("k64", ("old", "after_64")),
                            ("k65536", ("old", "after_64k")),
                            ("sleep64", ("sleep", "64", "old")), ("sleep64k", ("sleep", "64k", "old"))):
            result["old"][stage] = {kind: self.score(at(adapt, *path, kind), 200, f"{name}/{stage}/{kind}")
                                    for kind in OLD}
        for stage in ("sleep64", "sleep64k"):
            result["sleep_D"][stage] = {}
            for family in ("old", "wide_old"):
                result["sleep_D"][stage][family] = {
                    kind: float(pct(before) - pct(result[family][stage][kind]))
                    if before and result[family][stage][kind] else None
                    for kind, before in result[family]["k0"].items()}
        fit = job["fit"]
        result["support_fit_improved"] = None
        if fit is not None:
            before = self.score(at(fit, "before64"), 64, name + "/support-before64")
            after = self.score(at(fit, "after64"), 64, name + "/support-after64")
            if before and after:
                result["support_fit_improved"] = after["right"] > before["right"]
        result["resources"] = {k: at(adapt, k) for k in (
            "weights", "persistent_coefficients", "fixed_depth", "optimizer_updates", "training_seconds",
            "panel_layouts", "support_unique_layouts", "stream_unique_layouts", "stream_panel_overlap",
            "stream_support_overlap", "raw_memory_bytes")}
        result["resources"]["sleep"] = {branch: {k: v for k, v in row.items()
                if k not in ("old", "maze_dev")} for branch, row in (at(adapt, "sleep") or {}).items()}
        result["resources"]["additional_metadata"] = {k: v for k, v in (adapt or {}).items()
            if k not in ("rungs", "old", "sleep") and k not in result["resources"]}
        result["telemetry"] = job["telemetry"]
        result["resources"]["inference_deltas"] = {
            phase: self.inference_totals(rows, f"{name}/{phase}")
            for phase, rows in job["telemetry"].items()}
        result["resources"]["learner_resources"] = {
            phase: self.learner_resources(rows, f"{name}/{phase}")
            for phase, rows in job["telemetry"].items()}
        result["support_fit"] = fit
        return result

    def decide(self, jobs):
        comparisons = {}
        old_gates = []
        old_by_seed = {}
        for seed in (0, 1):
            old_start = len(old_gates)
            p = jobs[f"patch-seed{seed}-pre"]
            primary = jobs[f"loop_meta-seed{seed}-pre"]
            pscore = p["metrics"]["F_all"]
            comparisons[str(seed)] = {}
            for arm, init, threshold in (("loop_meta", "pre", 10), ("plain", "pre", 5), ("patch", "fresh", 5)):
                other = jobs[f"{arm}-seed{seed}-{init}"]["metrics"]["F_all"]
                delta = pscore - other if pscore is not None and other is not None else None
                key = f"seed{seed}/F_all_vs_{arm}_{init}"
                self.gate(key, delta >= threshold if delta is not None else None)
                comparisons[str(seed)][f"vs_{arm}_{init}"] = delta
            for arm in ARMS:
                src = self.sources[f"{arm}-seed{seed}"]
                gc = at(src, "gradient_check", "nonzero_all")
                self.gate(f"seed{seed}/{arm}/live_gradients", gc if type(gc) is bool else None)
                depth = at(src, "fixed_depth")
                if depth not in ((1,) if arm == "plain" else (8, 16, 32, 48)):
                    self.issues.append(f"missing/invalid source-selected depth: {arm}/seed{seed}")
                for kind in OLD:
                    row = self.score(at(src, "old", kind), 200, f"source/{arm}/{seed}/{kind}")
                    self.gate(f"seed{seed}/{arm}/source/{kind}", row["right"] >= 190 if row else None)
                    if arm == "patch":
                        control = self.score(at(self.sources[f"loop_meta-seed{seed}"], "old", kind), 200,
                                             f"source/loop_meta/{seed}/{kind}")
                        key = f"seed{seed}/old/source/{kind}"
                        self.compare(key, row, control, 3)
                        old_gates.extend((key, f"seed{seed}/{arm}/source/{kind}"))
                if arm == "patch":
                    weights = at(src, "persistent_coefficients")
                    control_weights = at(self.sources[f"loop_meta-seed{seed}"], "persistent_coefficients")
                    good = integer(weights) and integer(control_weights) and weights > 0 and control_weights > 0
                    self.gate(f"seed{seed}/weight_budget", abs(weights-control_weights)*100 <= 2*control_weights if good else None)
                    if not good:
                        self.issues.append(f"missing persistent coefficient counts: seed{seed}")
            for kind in KINDS:
                for arm in ARMS:
                    row = jobs[f"{arm}-seed{seed}-pre"]["wide_old"]["k0"][kind]
                    key = f"seed{seed}/{arm}/wide_source/{kind}"
                    self.gate(key, row["right"] >= (285 if kind in ("sums", "grids") else 270) if row else None)
                    if arm == "patch":
                        old_gates.append(key)
                for control in ("loop_meta", "loop"):
                    key = f"seed{seed}/old/wide_source_vs_{control}/{kind}"
                    self.compare(key, p["wide_old"]["k0"][kind],
                                 jobs[f"{control}-seed{seed}-pre"]["wide_old"]["k0"][kind], 3)
                    old_gates.append(key)
            for stage in ("sleep64", "sleep64k"):
                for family, kinds in (("old", OLD), ("wide_old", KINDS)):
                    for kind in kinds:
                        key = f"seed{seed}/old/{stage}/{family}/{kind}"
                        self.compare(key, p[family][stage][kind], primary[family][stage][kind], 3)
                        old_gates.append(key)
            old_by_seed[seed] = old_gates[old_start:]
        improvements = [jobs[f"patch-seed{s}-pre"]["support_fit_improved"] for s in (0, 1)]
        deltas = [comparisons[str(s)]["vs_loop_meta_pre"] for s in (0, 1)]
        no_gain = all(d is not None and d <= 0 for d in deltas)
        support_negative = (no_gain and all(v is True for v in improvements)) if all(v is not None for v in improvements) and all(d is not None for d in deltas) else None
        # Attribute the maze gain and old-kind failure to the same paired seed.
        retention_by_seed = {str(seed): (deltas[seed] > 0 and
            any(self.gates[k] is False for k in old_by_seed[seed]))
            if deltas[seed] is not None and all(self.gates[k] is not None for k in old_by_seed[seed]) else None
            for seed in (0, 1)}
        retention_negative = (True if any(v is True for v in retention_by_seed.values()) else
                              None if any(v is None for v in retention_by_seed.values()) else False)
        if any(self.gates[k] is False for k in ("V1", "V2", "V3", "race_V3")):
            verdict = "inconclusive"
        elif self.issues or any(v is None for v in self.gates.values()):
            verdict = "incomplete/untested"
        elif not self.gates["practice"]:
            verdict = "inconclusive"
        elif all(self.gates.values()):
            verdict = "promotion_thresholds_met_pending_blind_recount"
        elif support_negative or retention_negative:
            verdict = "registered_negative_pending_blind_recount"
        else:
            verdict = "no_promotion"
        return verdict, comparisons, {"support_improved_both_and_F_all_no_higher_both": support_negative,
                                      "maze_gain_with_same_seed_old_gate_breach": retention_negative,
                                      "retention_negative_by_seed": retention_by_seed}

    def build(self):
        self.load()
        jobs = {name: self.analyze_job(name, job) for name, job in self.jobs.items()}
        verdict, comparisons, negative = self.decide(jobs)
        return {"utc": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip(),
                "verdict": verdict, "blind_recount": "untested; separate agent required",
                "gates": self.gates, "negative_criteria": negative, "paired_differences_pp": comparisons,
                "issues": sorted(set(self.issues)), "jobs": jobs, "sources": self.sources,
                "race_seal": self.seal, "baseline_validity": self.validity, "practice_gates": self.practice,
                "race_v3": self.race_v3,
                "input_sha256": self.inputs,
                "causal_wider_practice_help": "untested: no own narrow-practice control",
                "execution_note": "Addendum permits local GPU fp32; baseline protocol specifies CPU. Use recorded telemetry for actual execution."}


def markdown(report):
    lines = ["# Test A results", "", f"Shown: {report['verdict']}.",
             "Results are provisional until the separate blind recount.",
             "Untested: whether wider practice caused an improvement; no own narrow-practice control.",
             "Ordinary wide-practice versus ruler comparisons are descriptive: budgets and initial seeds differ.",
             "Stopping gaps and the 50%-after-64 line are report-only.",
             "Untested here: checkpoint-level patch removal; post-sleep inputs must follow the addendum.",
             f"Recorded {report['utc']}. Required-data issues: {len(report['issues'])}.", "",
             "## Paired main scores", "", "| Job | F_all | F_few | Cold | F_few − cold | k64 ≥50% (report only) |",
             "|---|---:|---:|---:|---:|---|"]
    for name, job in report["jobs"].items():
        m = job["metrics"]
        lines.append(f"| {name} | " + " | ".join(number(m[k]) for k in ("F_all", "F_few", "cold", "F_few_minus_cold")) + f" | {m['k64_ge_50_report_only']} |")
    lines += ["", "## Paired differences (percentage points)", "", "| Seed | Patch − meta loop | Patch − plain | Patch − fresh patch |", "|---|---:|---:|---:|"]
    for seed, row in report["paired_differences_pp"].items():
        lines.append(f"| {seed} | " + " | ".join(number(v) for v in row.values()) + " |")
    lines += ["", "## Complete curves", "", "7×7 is secondary: dev 24, holdout 48. 9×9 main and 11×11 secondary each use 300.",
              "", "| Job | Stage | Split | Size | Correct | Fixed | Mean rounds | Cap hits | Stop loss pp | >2 pp (report only) |", "|---|---|---|---:|---|---|---:|---:|---:|---|"]
    for name, job in report["jobs"].items():
        for stage, splits in job["curves"].items():
            for split, sizes in splits.items():
                for size, row in sizes.items():
                    r = row or {}
                    fixed = f"{r['fixed_right']} of {r['n']}" if "fixed_right" in r else "untested"
                    lines.append(f"| {name} | {stage} | {split} | {size} | {counts(row)} | {fixed} | {r.get('mean_rounds', 'untested')} | {r.get('cap_hits', 'untested')} | {number(r.get('stop_loss_pp'))} | {r.get('stop_failure_report_only', 'untested')} |")
    lines += ["", "## Old kinds, before and after sleep", "", "| Job | Stage | Panel | Kind | Correct | D from cold (pp) |", "|---|---|---|---|---|---:|"]
    for name, job in report["jobs"].items():
        for family in ("old", "wide_old"):
            for stage, kinds in job[family].items():
                for kind, row in kinds.items():
                    d = at(job, "sleep_D", stage, family, kind)
                    lines.append(f"| {name} | {stage} | {family} | {kind} | {counts(row)} | {number(d)} |")
    lines += ["", "## Gates", "", "| Gate | Result |", "|---|---|"]
    lines += [f"| {key} | {'untested' if value is None else 'pass' if value else 'fail'} |" for key, value in report["gates"].items()]
    lines += ["", "## Registered negative criteria", "", "```json", json.dumps(report["negative_criteria"], indent=2), "```",
              "", "## Recorded sizes, time, operations and layout counts", "", "Missing resource fields remain untested. Forward-only MAC counters are not total training operations.", ""]
    for label, src in report["sources"].items():
        lines += [f"### Source {label}", "", "```json", json.dumps(src, indent=2), "```", ""]
    for name, job in report["jobs"].items():
        lines += [f"### {name}", "", "```json", json.dumps(job["resources"], indent=2), "```",
                  "Telemetry records by phase (preserved in RACE-RESULTS.json): " +
                  ", ".join(f"{phase}: {'untested' if rows is None else len(rows)}"
                            for phase, rows in job["telemetry"].items()) + ".", ""]
    lines += ["## Seal and missing evidence", "", "```json", json.dumps(report["race_seal"], indent=2), "```", ""]
    lines += [f"- {issue}" for issue in report["issues"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT)
    args = ap.parse_args()
    report = Report(args.out).build()
    # Convert exact rational metrics only after decisions, preserving threshold equality.
    report = json.loads(json.dumps(report, default=lambda v: float(v) if isinstance(v, Fraction) else str(v)))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "RACE-RESULTS.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (args.out / "RESULTS.md").write_text(markdown(report))
    print(report["verdict"])


if __name__ == "__main__":
    main()
