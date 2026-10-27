#!/usr/bin/env python3
"""Read-only AR1 replay-allocation grader; writes new Markdown and JSON reports.

This module does not train models or inspect individual puzzle contents. The caller
must supply results produced under a separately committed PASSMARKS document.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Mapping


HERE = Path(__file__).resolve().parent
SEEDS = tuple(range(41, 47))
ARMS = ("baseline", "late_replay")
KINDS = ("grids", "sums", "mazes")
PANELS = ("grids5", "sums4", "maze7")
PARAMETERS = 1_646_750
PHASES = {
    "baseline": {
        "A": (2500, {"grids": 2500, "sums": 0, "mazes": 0}),
        "B": (2500, {"grids": 250, "sums": 2250, "mazes": 0}),
        "C": (1500, {"grids": 75, "sums": 75, "mazes": 1350}),
    },
    "late_replay": {
        "A": (2500, {"grids": 2500, "sums": 0, "mazes": 0}),
        "B": (2500, {"grids": 125, "sums": 2375, "mazes": 0}),
        "C": (1500, {"grids": 200, "sums": 75, "mazes": 1225}),
    },
}


def result_paths(root: Path) -> dict[tuple[str, int], Path]:
    """Construct all 12 paths without creating files or directories."""
    return {(arm, seed): root / f"{arm}-s{seed}" / "result.json"
            for arm in ARMS for seed in SEEDS}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _integer(value, lo=None, hi=None):
    return type(value) is int and (lo is None or value >= lo) and (hi is None or value <= hi)


def _validate(data, arm: str, seed: int) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["top level must be a JSON object"]
    if data.get("seed") != seed or type(data.get("seed")) is not int:
        errors.append(f"seed must be {seed}")
    if data.get("arm") != arm:
        errors.append(f"arm must be {arm}")
    if data.get("complete") is not True:
        errors.append("complete must be true")
    if not _integer(data.get("parameters")) or data["parameters"] != PARAMETERS:
        errors.append(f"parameters must be {PARAMETERS}")
    if data.get("device") != "mps":
        errors.append("device must be mps")
    if not _integer(data.get("batch_size")) or data["batch_size"] != 64:
        errors.append("batch_size must be 64")
    if data.get("precision") != "float32":
        errors.append("precision must be float32")
    if not isinstance(data.get("software_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", data["software_commit"]):
        errors.append("software_commit must be a full lowercase Git SHA")
    minutes = data.get("minutes")
    if type(minutes) not in (int, float) or not math.isfinite(minutes) or minutes <= 0:
        errors.append("minutes must be finite and positive")
    m4 = data.get("m4")
    if not isinstance(m4, dict) or m4.get("pass") is not True or m4.get("failures") != []:
        errors.append("m4.pass must be true and m4.failures must be []")
    final_m4 = data.get("m4_final")
    if not isinstance(final_m4, dict) or final_m4.get("pass") is not True or final_m4.get("failures") != []:
        errors.append("m4_final.pass must be true and m4_final.failures must be []")
    for name, check in (("m4", m4), ("m4_final", final_m4)):
        if isinstance(check, dict) and check.get("public_request_fields") != ["tokens", "slot"]:
            errors.append(f"{name}.public_request_fields must be tokens, slot only")

    phases = data.get("phases")
    if not isinstance(phases, dict):
        return errors + ["phases must be an object with A, B, C"]
    for phase_name, (expected_steps, expected_batches) in PHASES[arm].items():
        phase = phases.get(phase_name)
        if not isinstance(phase, dict):
            errors.append(f"phase {phase_name} missing")
            continue
        if not _integer(phase.get("steps")) or phase["steps"] != expected_steps:
            errors.append(f"{phase_name}.steps must be {expected_steps}")
        batches = phase.get("kind_batches")
        if (not isinstance(batches, dict) or set(batches) != set(KINDS) or
                any(not _integer(batches.get(kind)) or batches[kind] != expected_batches[kind]
                    for kind in KINDS)):
            errors.append(f"{phase_name}.kind_batches must be {expected_batches}")
        scores = phase.get("score")
        if not isinstance(scores, dict):
            errors.append(f"{phase_name}.score must contain all three panels")
            continue
        for panel in PANELS:
            item = scores.get(panel)
            if (not isinstance(item, dict) or not _integer(item.get("right"), 0, 200) or
                    not _integer(item.get("n")) or item["n"] != 200):
                errors.append(f"{phase_name}.score.{panel} needs integer right 0..200 and n=200")

    # These are redundant with exact phase counts, but make the budget invariant explicit.
    if all(isinstance(phases.get(p), dict) and _integer(phases[p].get("steps")) for p in ("A", "B", "C")):
        if sum(phases[p]["steps"] for p in ("A", "B", "C")) != 6500:
            errors.append("total steps must be 6500")
    if all(isinstance(phases.get(p), dict) and isinstance(phases[p].get("kind_batches"), dict)
           for p in ("B", "C")):
        b, c = phases["B"]["kind_batches"], phases["C"]["kind_batches"]
        if all(_integer(x.get(k)) for x, k in ((b, "grids"), (c, "grids"), (c, "sums"))):
            if b["grids"] + c["grids"] + c["sums"] != 400:
                errors.append("total replay batches must be 400")
    return errors


def _right(data: dict, phase: str, panel: str) -> int:
    return data["phases"][phase]["score"][panel]["right"]


def grade(paths: Mapping[tuple[str, int], Path]) -> dict:
    """Grade exactly six paired seeds using integer sums for every mean threshold."""
    expected = {(arm, seed) for arm in ARMS for seed in SEEDS}
    if set(paths) != expected:
        raise ValueError("paths must map exactly baseline and late_replay for seeds 41..46")
    records, missing, incomplete, invalid = {}, [], [], []
    for arm in ARMS:
        for seed in SEEDS:
            path = Path(paths[(arm, seed)])
            label = f"{arm}-s{seed}"
            if not path.is_file():
                missing.append(str(path))
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                                  parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid {x}")))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                invalid.append(f"{label}: unreadable/malformed JSON: {exc}")
                continue
            if isinstance(data, dict) and data.get("complete") is False:
                incomplete.append(label)
                continue
            problems = _validate(data, arm, seed)
            if problems:
                invalid.extend(f"{label}: {problem}" for problem in problems)
            else:
                records[(arm, seed)] = data

    report = {"status": None, "files": {f"{a}-s{s}": str(paths[(a, s)])
                                         for a in ARMS for s in SEEDS},
              "missing": missing, "incomplete": incomplete, "invalid": invalid,
              "criteria": {}, "per_seed": []}
    if missing or incomplete:
        report["status"] = "INCOMPLETE"
        return report
    if invalid:
        report["status"] = "INVALID"
        return report
    software = {data["software_commit"] for data in records.values()}
    if len(software) != 1:
        report["invalid"].append("all 12 runs must share one software_commit")
        report["status"] = "INVALID"
        return report
    report["software_commit"] = next(iter(software))

    totals = {arm: {"G_A": 0, "S_B": 0, "G_C": 0, "S_C": 0, "M_C": 0, "T_C": 0}
              for arm in ARMS}
    positive_t_gaps = 0
    for seed in SEEDS:
        row = {"seed": seed, "arms": {}}
        for arm in ARMS:
            data = records[(arm, seed)]
            scores = {"G_A": _right(data, "A", "grids5"),
                      "S_B": _right(data, "B", "sums4"),
                      "G_C": _right(data, "C", "grids5"),
                      "S_C": _right(data, "C", "sums4"),
                      "M_C": _right(data, "C", "maze7")}
            scores["T_C"] = scores["G_C"] + scores["S_C"] + scores["M_C"]
            row["arms"][arm] = {"scores": scores, "minutes": data["minutes"]}
            routing = data.get("routing_report_only")
            if (isinstance(routing, dict) and _integer(routing.get("agreement"), 0, 600)
                    and routing.get("n") == 600):
                row["arms"][arm]["routing_agreement"] = routing["agreement"]
            for key, value in scores.items():
                totals[arm][key] += value
        row["T_gap"] = row["arms"]["late_replay"]["scores"]["T_C"] - row["arms"]["baseline"]["scores"]["T_C"]
        positive_t_gaps += row["T_gap"] > 0
        report["per_seed"].append(row)

    base, cand = totals["baseline"], totals["late_replay"]
    m1_mean = cand["G_C"] >= 180 * 6
    m1_floor = all(row["arms"]["late_replay"]["scores"]["G_C"] >= 160 for row in report["per_seed"])
    m2_sums = cand["S_B"] >= 195 * 6
    m2_maze = cand["M_C"] >= base["M_C"] - 10 * 6
    m3_total = cand["T_C"] >= base["T_C"] + 40 * 6
    m3_wins = positive_t_gaps >= 5
    proved_wrong_t = cand["T_C"] <= base["T_C"]
    proved_wrong_g = cand["G_C"] <= base["G_C"]
    report["totals"] = totals
    report["criteria"] = {
        "M1_mean_grid_C_ge_180": m1_mean,
        "M1_every_grid_C_ge_160": m1_floor,
        "M2_mean_sums_B_ge_195": m2_sums,
        "M2_mean_maze_C_within_10": m2_maze,
        "M3_mean_T_C_plus_40": m3_total,
        "M3_positive_T_gap_at_least_5_of_6": m3_wins,
        "M4_all_runs_pass_and_exact_budget_device_size": True,
        "positive_T_gaps": positive_t_gaps,
        "proved_wrong_T_no_better": proved_wrong_t,
        "proved_wrong_grid_no_better": proved_wrong_g,
    }
    if proved_wrong_t or proved_wrong_g:
        report["status"] = "PROVED WRONG"
    elif all((m1_mean, m1_floor, m2_sums, m2_maze, m3_total, m3_wins)):
        report["status"] = "PASS"
    else:
        report["status"] = "FAIL (not proved wrong)"
    return report


def _mean(total: int) -> str:
    return f"{total / len(SEEDS):.2f}"


def render_report(report: dict) -> str:
    """Render a reviewable Markdown report without changing the grade."""
    lines = ["# Replay allocation result", "", f"**Verdict: {report['status']}.**", "",
             "## Shown", ""]
    if report["status"] in ("INCOMPLETE", "INVALID"):
        lines.append("The declared 12-run evidence set is not gradeable. No score verdict is assigned.")
        lines.append("")
        for label in ("missing", "incomplete", "invalid"):
            if report[label]:
                lines.extend((f"{label.title()}:", ""))
                lines.extend(f"- {item}" for item in report[label])
                lines.append("")
    else:
        lines.extend((
            "Each score is exact items correct out of 200 at the model's own stopping rule. "
            "T is grids5 + sums4 + maze7 after C, out of 600. All threshold decisions used integer sums.",
            "",
            "| Seed | A grids base / late | B sums base / late | C grids base / late | "
            "C sums base / late | C maze base / late | T base / late | ΔT | Minutes base / late |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ))
        for row in report["per_seed"]:
            b = row["arms"]["baseline"]["scores"]
            c = row["arms"]["late_replay"]["scores"]
            lines.append(f"| {row['seed']} | {b['G_A']} / {c['G_A']} | {b['S_B']} / {c['S_B']} | "
                         f"{b['G_C']} / {c['G_C']} | {b['S_C']} / {c['S_C']} | "
                         f"{b['M_C']} / {c['M_C']} | {b['T_C']} / {c['T_C']} | {row['T_gap']:+d} | "
                         f"{row['arms']['baseline']['minutes']:.2f} / "
                         f"{row['arms']['late_replay']['minutes']:.2f} |")
        b, c = report["totals"]["baseline"], report["totals"]["late_replay"]
        base_minutes = sum(row["arms"]["baseline"]["minutes"] for row in report["per_seed"]) / len(SEEDS)
        late_minutes = sum(row["arms"]["late_replay"]["minutes"] for row in report["per_seed"]) / len(SEEDS)
        lines.extend((
            "",
            f"Mean C grids: **{_mean(b['G_C'])} baseline / {_mean(c['G_C'])} late**; "
            f"mean B sums: **{_mean(b['S_B'])} / {_mean(c['S_B'])}**; "
            f"mean C mazes: **{_mean(b['M_C'])} / {_mean(c['M_C'])}**; "
            f"mean C T: **{_mean(b['T_C'])} / {_mean(c['T_C'])}**. "
            f"Late replay won T on **{report['criteria']['positive_T_gaps']}/6** seeds.",
            f"Mean recorded minutes: **{base_minutes:.2f} baseline / {late_minutes:.2f} late**.",
            "",
            "| Registered check | Pass | Exact integer comparison |",
            "| --- | --- | --- |",
            f"| M1 mean grid C ≥180 | {report['criteria']['M1_mean_grid_C_ge_180']} | {c['G_C']} ≥ 1080 |",
            f"| M1 every grid C ≥160 | {report['criteria']['M1_every_grid_C_ge_160']} | Per-seed rows above |",
            f"| M2 mean sums B ≥195 | {report['criteria']['M2_mean_sums_B_ge_195']} | {c['S_B']} ≥ 1170 |",
            f"| M2 maze within 10 | {report['criteria']['M2_mean_maze_C_within_10']} | "
            f"{c['M_C']} ≥ {b['M_C']} − 60 |",
            f"| M3 T +40 | {report['criteria']['M3_mean_T_C_plus_40']} | "
            f"{c['T_C']} ≥ {b['T_C']} + 240 |",
            f"| M3 T wins ≥5/6 | {report['criteria']['M3_positive_T_gap_at_least_5_of_6']} | "
            f"{report['criteria']['positive_T_gaps']} ≥ 5 |",
            "| M4 integrity, MPS, precision, size and exact budgets | True | All 12 run files validated |",
            "",
            "Phase counts checked in every file: baseline B 250 grids/2250 sums, C 75 grids/75 sums/1350 mazes; "
            "late B 125 grids/2375 sums, C 200 grids/75 sums/1225 mazes; A 2500 grids in both. "
            "Each arm used 6500 steps and 400 replay batches per seed, with batch 64 and 1,646,750 "
            "parameters on float32 MPS. All 12 runs report software commit "
            f"`{report['software_commit']}` and passing initial/final M4 controls.",
            "",
        ))
        if all("routing_agreement" in row["arms"][arm]
               for row in report["per_seed"] for arm in ARMS):
            lines.extend((
                "Report-only learned-context agreement (diagnostic-majority map applied to final inputs; "
                "correct kind / 600): " + ", ".join(
                    f"s{row['seed']} {row['arms']['baseline']['routing_agreement']} / "
                    f"{row['arms']['late_replay']['routing_agreement']}"
                    for row in report["per_seed"]) + ".",
                "",
            ))
    lines.extend((
        "## Suggested", "",
        "A score difference may suggest that moving a fixed replay budget later changes retention. "
        "The registered checks determine whether it did so without the specified learning cost; "
        "they do not identify a general optimal replay schedule.", "",
        "## Untested", "",
        "Other replay allocations, other tasks, larger models, language-model behavior, "
        "and ambiguous or reformatted requests are outside this grade. Both arms use learned "
        "context and mixed single-request inference, but its causal benefit versus oracle or "
        "other routing is not isolated. The grader relies on saved scores and M4 audits; "
        "an independent prediction recount is a separate check.", "",
        "## Plain words", "",
        "The two models got the same amount of practice. One moved some old grid practice from the "
        "middle stage to the last stage. The table shows whether that helped it remember grids while "
        "still learning sums and mazes. The verdict follows the rules fixed before training.", "",
    ))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE / "run",
                        help="directory containing baseline-s41..46 and late_replay-s41..46")
    parser.add_argument("--out", type=Path, required=True, help="new Markdown report path inside this artifact folder")
    args = parser.parse_args()
    out = args.out.resolve()
    json_out = out.with_suffix(".json")
    if out.suffix.lower() != ".md" or not out.is_relative_to(HERE) or json_out == out:
        parser.error("--out must be a .md file inside artifacts/codex-autoroute-20260927")
    if out.exists() or json_out.exists():
        parser.error(f"refusing to overwrite {out} or {json_out}")
    if not out.parent.is_dir():
        parser.error("output parent directory must already exist")
    report = grade(result_paths(args.root))
    markdown = render_report(report)
    with json_out.open("x", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    with out.open("x", encoding="utf-8") as fh:
        fh.write(markdown)
    print(f"{report['status']}: {out} and {json_out}")


if __name__ == "__main__":
    main()
