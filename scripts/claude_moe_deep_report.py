#!/usr/bin/env python3
"""Scores and words for the deep sparse-MoE loop test, from raw JSON only (no torch needed).

Marks: artifacts/claude-moe-deep-20260929/PASSMARKS.md (sealed before any run). This script applies them;
it never changes a threshold. Numbers: 9x9 learned-stop `right` of 300 per rung.
  F_eq  = mean over k = 1 ... 16,384 of 100 * right / 300
  F_few = mean over k = 1, 4, 16, 64 of 100 * right / 300

  python3 -B scripts/claude_moe_deep_report.py dev       # dev tables: phase 1, scaling, attribution (report-only)
  python3 -B scripts/claude_moe_deep_report.py final     # holdout verdict (needs the four holdout.json files)
Writes REPORT-dev.json / VERDICT.json next to PASSMARKS.md and prints markdown tables.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-moe-deep-20260929"
BASE = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FEW = RUNGS[:4]
MAIN = "L8-E64"
SEEDS = (0, 1)
# fixed in PASSMARKS.md
BAR_WIN, BAR_NOISE, BAR_FEW = 10.0, 8.0, 10.5
NOISE_SD = 3.96                      # all-starts F_eq SD, artifacts/claude-dir-lr-20260928/NOISE.md
DEPTH = ("L2-E64", "L4-E64", "L8-E64", "L16-E64")
EXPERTS = ("L8-E16", "L8-E32", "L8-E64", "L8-E128")


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def counts(rec, split):
    if rec is None:
        return None
    if split == "dev":
        return [rec["rungs"][str(k)]["9"]["right"] for k in RUNGS]
    return [rec["scores"][str(k)]["9"]["right"] for k in RUNGS]


def f_eq(c):
    return None if c is None else sum(c) / len(c) / 3


def f_few(c):
    return None if c is None else sum(c[:4]) / 4 / 3


def r2(x):
    return None if x is None else round(x, 2)


def run(cfg, seed, init="pre", split="dev"):
    d = ART / "eq-runs" / f"{cfg}-{init}-s{seed}"
    return load(d / ("adapt.json" if split == "dev" else "holdout.json"))


def base(arm, seed, init, split):
    d = BASE / f"{arm}-s{seed}-{init}"
    return load(d / ("adapt.json" if split == "dev" else "holdout.json"))


def weights(cfg, seed):
    q = load(ART / "runs" / f"{cfg}-s{seed}" / "qualified.json")
    if not q or not q.get("folder"):
        return None, None
    s = load(ROOT / q["folder"] / "source.json")
    return s["weights"], s.get("active_per_cell_round")


def row(name, c):
    cells = " | ".join("-" if c is None else f"{x}" for x in (c or [None] * 8))
    return f"| {name} | {cells} | {r2(f_eq(c))} | {r2(f_few(c))} |"


def stop_failures(rec, split):
    if rec is None:
        return None
    src = rec["rungs"] if split == "dev" else rec["scores"]
    return [k for k in RUNGS if src[str(k)]["9"]["right"] < src[str(k)]["9"]["fixed_right"] - 6]


def word(deltas, bar, up, down, flat="NOT SEPARABLE"):
    ds = [d for d in deltas if d is not None]
    if not ds:
        return "NOT RUN"
    if len(ds) < len(deltas):
        tag = " (one seed only: suggested)"
    else:
        tag = ""
    if all(d >= bar for d in ds):
        return up + tag
    if all(d <= -bar for d in ds):
        return down + tag
    return flat + tag


def slope(points):
    """Least-squares slope of F_eq against log2(stored weights): points per doubling."""
    pts = [(math.log2(w), f) for w, f in points if w and f is not None]
    if len(pts) < 2:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else None


def curve(names, split="dev"):
    out = {}
    for s in SEEDS:
        pts = []
        for cfg in names:
            w, a = weights(cfg, s)
            c = counts(run(cfg, s, "pre", split), split)
            pts.append({"cfg": cfg, "stored": w, "active": a, "F_eq": r2(f_eq(c)), "F_few": r2(f_few(c)),
                        "use_gain_64_to_16384": None if c is None else r2((c[7] - c[3]) / 3)})
        done = [p for p in pts if p["F_eq"] is not None]
        delta = (done[-1]["F_eq"] - done[0]["F_eq"]) if len(done) >= 2 and done[0] is pts[0] and done[-1] is pts[-1] else None
        sl = slope([(p["stored"], p["F_eq"]) for p in done])
        if delta is None:
            w = "NOT RUN (needs the smallest and the largest point)"
        elif delta >= BAR_NOISE and sl is not None and sl > 0:
            w = "UP"
        elif delta <= -BAR_NOISE:
            w = "DOWN"
        elif abs(delta) < BAR_NOISE:
            w = "FLAT"
        else:
            w = "MIXED"
        out[str(s)] = {"points": pts, "largest_minus_smallest": r2(delta), "slope_per_doubling": r2(sl), "word": w}
    ws = [out[str(s)]["word"] for s in SEEDS if not out[str(s)]["word"].startswith("NOT RUN")]
    if not ws:
        out["word"] = "NOT RUN"
    elif len(ws) == 1:
        out["word"] = f"SCALES {ws[0]} (one seed only: suggested)"
    elif ws[0] == ws[1]:
        out["word"] = f"SCALES {ws[0]}"
    else:
        out["word"] = "MIXED"
    return out


def cmd_dev():
    rep = {"split": "dev", "note": "report-only rows; the verdict is on the holdout (final)"}
    lines = ["| row | " + " | ".join(f"k={k}" for k in RUNGS) + " | F_eq | F_few |", "|---" * 11 + "|"]
    table = {}
    for s in SEEDS:
        for name, rec in ((f"loop (recorded CPU) s{s}", base("loop", s, "pre", "dev")),
                          (f"plain (recorded CPU) s{s}", base("plain", s, "pre", "dev")),
                          (f"loop control (same GPU) s{s}", run("loopctl", s)),
                          (f"MoE {MAIN} s{s}", run(MAIN, s)),
                          (f"MoE {MAIN} fresh s{s}", run(MAIN, s, "fresh")),
                          (f"dense-act s{s}", run("L8-dense-act", s)),
                          (f"dense-tot s{s}", run("L8-dense-tot", s)),
                          (f"plain-big s{s}", run("plain-big", s))):
            c = counts(rec, "dev")
            table[name] = {"right9": c, "F_eq": r2(f_eq(c)), "F_few": r2(f_few(c)),
                           "stop_failures": stop_failures(rec, "dev")}
            lines.append(row(name, c))
    rep["rows"] = table

    def fe(cfg, s, init="pre"):
        return f_eq(counts(run(cfg, s, init), "dev"))

    def d(a, b):
        return None if a is None or b is None else a - b
    attrib = {}
    for key, pair in (("A1_experts_equal_active", (MAIN, "L8-dense-act")), ("A2_experts_equal_total", (MAIN, "L8-dense-tot")),
                      ("A3_loop_equal_total", ("L8-dense-tot", "plain-big")), ("A5_practice", (MAIN, MAIN))):
        if key == "A5_practice":
            ds = [d(fe(MAIN, s), fe(MAIN, s, "fresh")) for s in SEEDS]
        else:
            ds = [d(fe(pair[0], s), fe(pair[1], s)) for s in SEEDS]
        attrib[key] = {"deltas": [r2(x) for x in ds], "word": word(ds, BAR_NOISE, "HELPS", "HURTS")}
    ds = [d(fe("L8-dense-act", s), f_eq(counts(base("loop", s, "pre", "dev"), "dev"))) for s in SEEDS]
    attrib["A4_dense_depth_vs_loop (2.76x weights, confounded)"] = {"deltas": [r2(x) for x in ds],
                                                                   "word": word(ds, BAR_NOISE, "HELPS", "HURTS")}
    rep["attribution"] = attrib
    rep["scaling"] = {"depth_at_64_experts": curve(DEPTH), "experts_at_8_layers": curve(EXPERTS)}
    rep["routes"] = {}
    for p in sorted((ART / "eq-runs").glob("*/routes.json")) if (ART / "eq-runs").exists() else []:
        r = load(p)
        last = r.get("k16384") or r.get(sorted(r)[-1])
        rep["routes"][p.parent.name] = {"dead_total": last["dead_total"], "experts_total": last["experts_total"],
                                        "worst_max_over_mean": r2(last["worst_max_over_mean"]),
                                        "min_load_entropy": last["min_load_entropy"]}
    (ART / "REPORT-dev.json").write_text(json.dumps(rep, indent=2) + "\n")
    print("\n".join(lines))
    print(json.dumps({"attribution": attrib, "scaling_words": {k: v["word"] for k, v in rep["scaling"].items()}}, indent=1))


def cmd_final():
    v = {"split": "holdout"}
    loops = {s: f_eq(counts(base("loop", s, "pre", "holdout"), "holdout")) for s in SEEDS}
    loops_few = {s: f_few(counts(base("loop", s, "pre", "holdout"), "holdout")) for s in SEEDS}
    ctl = {s: counts(run("loopctl", s, "pre", "holdout"), "holdout") for s in SEEDS}
    comp = max([*loops.values()] + [f_eq(c) for c in ctl.values() if c])
    comp_few = max([*loops_few.values()] + [f_few(c) for c in ctl.values() if c])
    smoke = load(ART / "SMOKE-gpu.json")
    if smoke is not None and not smoke["PASS"]:
        # PASSMARKS 'Machine': a failed CPU/GPU smoke makes the same-GPU loop control the only comparator
        if not any(ctl.values()):
            raise SystemExit("SMOKE FAILED and no same-GPU loop control: no valid comparator; verdict NOT SHOWN")
        comp = max(f_eq(c) for c in ctl.values() if c)
        comp_few = max(f_few(c) for c in ctl.values() if c)
    v.update({"comparator_F_eq": r2(comp), "comparator_F_few": r2(comp_few),
              "recorded_loop_F_eq": {str(s): r2(x) for s, x in loops.items()},
              "same_gpu_loop_F_eq": {str(s): r2(f_eq(c)) for s, c in ctl.items()},
              "smoke_pass": None if smoke is None else smoke["PASS"]})
    per = {}
    for s in SEEDS:
        c = counts(run(MAIN, s, "pre", "holdout"), "holdout")
        per[str(s)] = {"right9": c, "F_eq": r2(f_eq(c)), "F_few": r2(f_few(c)),
                       "gap": r2(None if c is None else f_eq(c) - comp),
                       "gap_in_noise_sd": r2(None if c is None else (f_eq(c) - comp) / NOISE_SD),
                       "few_gap": r2(None if c is None else f_few(c) - comp_few),
                       "G1": None if c is None else f_eq(c) >= comp + BAR_WIN,
                       "stop_failures": stop_failures(run(MAIN, s, "pre", "holdout"), "holdout")}
        pl = counts(base("plain", s, "pre", "holdout"), "holdout")
        per[str(s)]["plain_recorded"] = {"F_eq": r2(f_eq(pl)), "F_few": r2(f_few(pl))}
    v["seeds"] = per
    ran = [per[str(s)] for s in SEEDS if per[str(s)]["F_eq"] is not None]
    quals = [load(ART / "runs" / f"{MAIN}-s{s}" / "qualified.json") for s in SEEDS]
    if any(q is not None and not q["qualified"] for q in quals):
        verdict = "DID NOT TRAIN"
    elif len(ran) < len(SEEDS):
        verdict = "NOT SHOWN (a seed has no holdout: see DID NOT TRAIN / not run)"
    elif all(p["G1"] for p in ran):
        verdict = "PASS"
    elif all(p["F_eq"] <= comp for p in ran):
        verdict = "PROVED WRONG" + (" (HURTS)" if all(p["F_eq"] <= comp - BAR_NOISE for p in ran) else "")
    else:
        verdict = "NOT SHOWN"
    v["verdict"] = verdict
    fg = [per[str(s)]["few_gap"] for s in SEEDS]
    v["F_few_word"] = word(fg, BAR_FEW, "HELPS", "HURTS")
    (ART / "VERDICT.json").write_text(json.dumps(v, indent=2) + "\n")
    print(json.dumps(v, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dev"
    {"dev": cmd_dev, "final": cmd_final}[cmd]()
