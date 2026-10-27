#!/usr/bin/env python3
"""Build the dev-only report after the registered V3 early stop."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "claude-fewex-20260927"
RUNS = ROOT / "runs"
ARMS = ("loop", "plain")
SEEDS = (0, 1)
INITS = ("pre", "fresh")
RUNGS = ("0", "1", "4", "16", "64", "256", "1024", "4096", "16384", "65536")
FEW = ("1", "4", "16", "64")


def read(p):
    return json.loads(p.read_text())


def result(arm, seed, init):
    root = RUNS / f"{arm}-s{seed}-{init}"
    f = root / "adapt.json"
    return read(f) if f.exists() else read(root / "partial.json")


def score(r, rung, size=9):
    if "rungs" in r:
        return r["rungs"][rung][str(size)]
    if size == 9:
        return r["dev9_rungs"][rung]
    return None


def cell(r, rung, size):
    try:
        s = score(r, rung, size)
        return f'{s["right"]} of {s["n"]}' if s is not None else "—"
    except KeyError:
        return "not run"


def old(r, stage, kind):
    if "rungs" in r:
        if stage == "sleep64":
            return r["sleep"]["64"]["old"][kind]["right"]
        if stage == "sleep64k":
            return r["sleep"]["64k"]["old"][kind]["right"]
        return r["old"][stage][kind]["right"]
    return r["old"][stage][kind]["right"]


def main():
    src = {(a, s): read(RUNS / f"qual-{a}-s{s}" / "source.json") for a in ARMS for s in SEEDS}
    data = {(a, s, i): result(a, s, i) for a in ARMS for s in SEEDS for i in INITS}
    v1 = all(x["old"][k]["right"] >= 190 for x in src.values() for k in ("sums4", "grids5"))
    v2 = all(x["gradient_check"]["nonzero_all"] for x in src.values())
    v3_rows = []
    for key, r in data.items():
        present = [k for k in RUNGS[1:] if k in (r["rungs"] if "rungs" in r else r["dev9_rungs"])]
        inside = [k for k in present if 30 < score(r, k)["right"] < 270]
        missing = 9 - len(present)
        v3_rows.append((key, inside, missing))
    assert all(len(inside) + missing < 3 for _, inside, missing in v3_rows)
    assert v1 and v2
    stamp = subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()
    lines = ["# Few-example ruler: INCONCLUSIVE", "",
             f"Written {stamp}. **Shown: V1 and V2 passed; V3 failed, so the 9×9 holdout was never opened.** The registered stop rule ended the two remaining loop seed-1 streams after 16,384 examples. No architecture wins or design-race verdict follow from this ruler.", "",
             "Original pass-mark seal: `3acb5d18a`. Execution seal after three pre-maze addenda: `aeb524cd0`. The original 6,000-step plain source runs failed V1. ADDENDUM-3 qualified both architectures with 12,000 matched source batches before any maze score; the source guard below uses a fresh 200/200 panel.", "",
             "## Validity", "", "| Check | Result | Evidence |", "|---|---|---|"]
    lines += ["| V1 | PASS | Every qualified net ≥190/200 on sums and grids separately. |",
              "| V2 | PASS | Every two-dimensional weight matrix had a nonzero fp32 CPU gradient on sums or grids. |",
              "| V3 | FAIL | No arm can have three dev 9×9 rungs strictly between 10% and 90%, even if the two missing 65,536-example scores were in range. |", "",
              "| Arm | Seed | 4-digit sums | 5×5 grids | Live matrices | Weights / persistent coefficients | Source minutes |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        for s in SEEDS:
            x = src[(a, s)]
            lines.append(f"| {a} | {s} | {x['old']['sums4']['right']} of 200 | {x['old']['grids5']['right']} of 200 | {x['gradient_check']['matrix_count']} of {x['gradient_check']['matrix_count']} | {x['weights']:,} / {x['persistent_coefficients']:,} | {x['train_seconds']/60:.1f} |")
    lines += ["", "Each qualified source model saw 12,000 × 64 = 768,000 code-made source examples; training minutes are wall time under concurrent CPU load. No maze appeared in source training, tuning, or validation.", "",
              "| Dev arm | Seed | Intermediate rungs | More rungs possible | Maximum intermediate rungs |",
              "|---|---:|---|---:|---:|"]
    for (a, s, i), inside, missing in v3_rows:
        lines.append(f"| {i} {a} | {s} | {', '.join(inside) or 'none'} | {missing} | {len(inside)+missing} |")
    lines += ["", "The final two loop seed-1 processes were stopped by exact PIDs 21678 and 21679 with SIGTERM at 2026-09-28 01:37 UTC. Their saved checkpoints were recounted without training. All six completed streams had 65,536 distinct 9×9 layouts and zero overlap with panels or supports; each support had 64 distinct 9×9 layouts. Possible layouts: 7×7 192, 9×9 100,352, 11×11 557,568,000. Panel layouts were all distinct: dev 24/300/300 and untouched holdout 48/300/300 for 7×7/9×9/11×11.", "",
              "## Dev ladder", "", "Counts below are development scores. ‘not run’ means the registered V3 stop ended the two loop seed-1 streams before 65,536. The 7×7 dev panel has 24 mazes; 9×9 and 11×11 have 300 each.", "",
              "| Arm | Seed | Examples | 7×7 | 9×9 | 11×11 | Fixed-depth 9×9 | Mean rounds | Cap hits | Stop failure |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for a in ARMS:
        for s in SEEDS:
            for i in INITS:
                r = data[(a, s, i)]
                for k in RUNGS:
                    try:
                        z = score(r, k)
                        fixed = f'{z["fixed_right"]} of 300'
                        rounds = f'{z["mean_rounds"]:.1f}'
                        caps = f'{z["cap_hits"]} of 300'
                        stop_fail = "YES" if a == "loop" and z["fixed_right"] - z["right"] > 6 else "no"
                    except KeyError:
                        fixed = rounds = caps = stop_fail = "—"
                    lines.append(f"| {i} {a} | {s} | {k} | {cell(r,k,7)} | {cell(r,k,9)} | {cell(r,k,11)} | {fixed} | {rounds} | {caps} | {stop_fail} |")
    lines += ["", "## Descriptive dev scores", "", "The registered primary `F_all` requires the unopened holdout, so no primary score exists. These dev values describe the observed runs only. `F_all` uses nine positive rungs; it is unavailable for the two stopped runs.", "",
              "| Arm | Seed | Dev F_all | Dev F_few | Dev cold | Dev F_few − cold | 65,536 dev | Adaptation job minutes |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        for s in SEEDS:
            for i in INITS:
                r = data[(a, s, i)]
                val = lambda k: score(r, k)["right"] / 3
                ffew = sum(val(k) for k in FEW) / 4
                cold = val("0")
                full = "rungs" in r
                fall = f"{sum(val(k) for k in RUNGS[1:])/9:.2f}" if full else "—"
                last = cell(r, "65536", 9)
                mins = f'{r["training_seconds"]/60:.1f}' if full else "stopped"
                lines.append(f"| {i} {a} | {s} | {fall} | {ffew:.2f} | {cold:.2f} | {ffew-cold:+.2f} | {last} | {mins} |")
    lines += ["", "## Old kinds and sleep", "", "Every old-kind count is of 200. This retention panel is separate from the fresh V1 source guard above. Each arm's replay allowance was the same 128 stored sums and 128 stored grids; each sleep update used four sums, four grids, and eight of that branch's own mazes. `D = before − after sleep` in percentage points; negative means improvement. The 65,536-example sleep did not run for loop seed 1.", "",
              "| Arm | Seed | Kind | Before | After 64 | Sleep after 64 | D64 | After 65,536 | Sleep after 65,536 | D65,536 |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        for s in SEEDS:
            for i in INITS:
                r = data[(a, s, i)]
                full = "rungs" in r
                for kind in ("sums4", "grids5"):
                    b = old(r, "before", kind)
                    a64 = old(r, "after_64", kind)
                    s64 = old(r, "sleep64", kind)
                    a64k = f'{old(r,"after_64k",kind)} of 200' if full else "not run"
                    s64k = f'{old(r,"sleep64k",kind)} of 200' if full else "not run"
                    d64k = f'{(b-old(r,"sleep64k",kind))/2:+.1f}' if full else "—"
                    lines.append(f"| {i} {a} | {s} | {kind} | {b} of 200 | {a64} of 200 | {s64} of 200 | {(b-s64)/2:+.1f} | {a64k} | {s64k} | {d64k} |")
    lines += ["", "| Arm | Seed | Sleep branch | Dev 9×9 after sleep | Updates | Minutes |",
              "|---|---:|---|---:|---:|---:|"]
    for a in ARMS:
        for s in SEEDS:
            for i in INITS:
                r = data[(a, s, i)]
                if "rungs" in r:
                    for branch in ("64", "64k"):
                        sl = r["sleep"][branch]
                        lines.append(f"| {i} {a} | {s} | {branch} | {sl['maze_dev']['9']['right']} of 300 | {sl['updates']} | {sl['seconds']/60:.1f} |")
                else:
                    lines.append(f"| {i} {a} | {s} | 64 | {r['sleep64_dev9']['right']} of 300 | 512 | recorded only for completed arms |")
    lines += ["", "**Shown (dev only):** source practice improves maze learning around 4,096–16,384 examples in both architectures; 64 unique examples remain near zero. At 4,096, the practiced loop solved 82/300 versus practiced plain 76/300 in seed 0, and 46/300 versus 42/300 in seed 1. At 16,384, loop solved 271/300 versus plain 190/300 in seed 0, and 282/300 versus 225/300 in seed 1. The loop was ahead at those rungs. These are descriptive development findings, not a valid holdout comparison. After 65,536, seed-0 loop solved 300/300 versus plain 279/300; seed 1's loop stopped before that rung. **Suggested:** the registered ladder is too sparse around the transition to provide three intermediate rungs. **Untested:** whether the same gaps hold on the unopened holdout or whether any of the three designs beats these baselines.", "",
              "**For Ben:** Practice helped these small nets start solving new mazes sooner in the dev test. Learning began to show clearly around 4,096 different mazes, not 64. The loop was ahead of the same-size plain net at 4,096 and 16,384 in both seeds. But the test's own rule says it must catch at least three middle steps of learning; it caught at most two. We stopped and did not peek at the final exam. The three design chats should read PROTOCOL.md, PASSMARKS.md, RACE-PASSMARKS.md, and ADDENDUM-3.md first; this ruler is not yet ready to judge their claims.", "",
              "The independent blind recount is in BLIND-RECOUNT.md. Raw JSON is under `runs/`; local checkpoints were retained for audit and are not committed as model weights.", ""]
    (ROOT / "RESULTS.md").write_text("\n".join(lines))
    print(json.dumps({"V1": v1, "V2": v2, "V3": False,
                      "arms": len(data), "full_streams": sum("rungs" in r for r in data.values())}))


if __name__ == "__main__":
    main()
