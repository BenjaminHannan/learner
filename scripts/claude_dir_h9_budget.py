#!/usr/bin/env python3
"""H9 arithmetic only (no torch, standard library): the F_eq+10 calibration and the weight budgets.

Reads the equal-practice ruler's own table (artifacts/claude-fewex-20260927/RESULTS-EQ.md, "Main 9x9 scores"),
recomputes F_eq for the loop and plain rows, checks it against the printed F_eq, and asks what +10 means.
Also recounts the loop's and the plain net's stored weights from the layer shapes in
scripts/claude_fewex_net.py and adds each H9 candidate's extra weights, so the "within about 1% of the loop"
claim in REPORT.md can be re-run. Writes calibration.json and budget.json next to REPORT.md.

  python3 scripts/claude_dir_h9_budget.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts" / "claude-fewex-20260927" / "RESULTS-EQ.md"
OUT = ROOT / "artifacts" / "claude-dir-h9-novelty-20260928"
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)


def main_table():
    """rows[(arm, seed)] = (counts of 300 at the 8 rungs, printed F_eq); only the first table after the heading."""
    text = RESULTS.read_text().split("## Main 9×9 scores", 1)[1].split("The full dev 9×9 curves", 1)[0]
    rows = {}
    for line in text.splitlines():
        m = re.match(r"\| (practised loop|fresh loop|practised plain|fresh plain) \| (\d) \|(.*)\|", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(3).split("|")]
        counts = [int(c.split(" of ")[0]) for c in cells[:8]]
        rows[(m.group(1), int(m.group(2)))] = (counts, float(cells[8].rstrip("%")))
    return rows


def feq(counts):
    return 100.0 * sum(counts) / (300 * len(counts))


def calibration():
    rows = main_table()
    assert len(rows) == 8, rows.keys()
    out = {"source": str(RESULTS.relative_to(ROOT)), "rungs": list(RUNGS), "seeds": {}}
    for seed in (0, 1):
        loop, printed = rows[("practised loop", seed)]
        plain, printed_plain = rows[("practised plain", seed)]
        assert abs(feq(loop) - printed) < 0.006 and abs(feq(plain) - printed_plain) < 0.006
        target = feq(loop) + 10
        # scenarios, all on the loop's own row; counts are of 300
        scen = {
            "perfect_from_k64_up_k16_and_below_unchanged": loop[:3] + [300] * 5,
            "k64_at_235_and_k256_up_perfect": loop[:3] + [235] + [300] * 4,
            "only_k256_up_perfect_k64_and_below_unchanged": loop[:4] + [300] * 4,
            "curve_shifted_left_one_rung_4x_fewer_examples": loop[1:] + [loop[-1]],
            "curve_shifted_left_two_rungs_16x_fewer_examples": loop[2:] + [loop[-1]] * 2,
        }
        out["seeds"][str(seed)] = {
            "loop_counts": loop, "loop_F_eq": round(feq(loop), 2), "plain_F_eq": round(feq(plain), 2),
            "F_eq_plus_10_target": round(target, 2),
            "extra_correct_counts_needed_summed_over_rungs_each_of_300": round((target - feq(loop)) / 100 * 300 * 8, 1),
            "contribution_points_by_rung": [round(100 * c / (300 * 8), 2) for c in loop],
            "scenarios_F_eq": {k: round(feq(v), 2) for k, v in scen.items()},
        }
    return out


# ---- weight counts, from the layer shapes in scripts/claude_fewex_net.py -------------------------------------------
VOCAB, CLIP = 125, 4            # claude_rsn358a_envs.VOCAB; claude_fewex_net.CLIP


def linear(i, o, bias=True):
    return i * o + (o if bias else 0)


def block(d, heads, mult=4):
    ln = 2 * (2 * d)
    qkv, out = linear(d, 3 * d), linear(d, d)
    mlp = linear(d, mult * d) + linear(mult * d, d)
    rel = 2 * heads * (2 * CLIP + 1)                     # br and bc
    return ln + qkv + out + mlp + rel


def net(arm):
    d, layers, heads = (256, 2, 8) if arm == "loop" else (128, 8, 8)
    n = VOCAB * d + 2 * d + layers * block(d, heads) + 2 * d + linear(d, VOCAB)   # tok, slot, blocks, ln_out, head
    if arm == "loop":
        n += 2 * d + linear(d, 1)                                                 # ln_state, halt
    return n


def budget():
    loop, plain = net("loop"), net("plain")
    text = RESULTS.read_text()
    assert f"{loop:,} / {loop:,}" in text and f"{plain:,} / {plain:,}" in text, "recount disagrees with RESULTS-EQ.md"
    d = 256
    designs = {
        # each entry: list of (what, extra weights)
        "1 refill loop (echo gain; reveal training adds none)": [("echo gain s", 1)],
        "2 twin-stream conflict stop (noise size fixed, not learned)": [("conflict weight kappa", 1)],
        "3 reach channel": [("LayerNorm before the link and source projections", 2 * d),
                            ("link projections Wq,Wk rank 8, no bias", 2 * d * 8),
                            ("link offset table 9x9 + bias", 81 + 1),
                            ("source-ness and target-ness vectors + biases", 2 * (d + 1)),
                            ("discount gamma", 1),
                            ("4 reach features -> width 256", linear(4, d))],
        "4 soft-D4 loop (isotropic table 15/head + separable residual 18/head, minus old 18/head)":
            [("extra table entries", 2 * 8 * (15 + 18 - 18))],
    }
    rows = {}
    for name, parts in designs.items():
        extra = sum(n for _, n in parts)
        rows[name] = {"parts": parts, "extra": extra, "stored": loop + extra,
                      "vs_loop_pct": round(100 * extra / loop, 4),
                      "within_1pct": abs(extra) <= 0.01 * loop, "within_2pct": abs(extra) <= 0.02 * loop}
    return {"loop_stored": loop, "plain_stored": plain, "band_1pct": [round(loop * 0.99), round(loop * 1.01)],
            "band_2pct": [round(loop * 0.98), round(loop * 1.02)], "designs": rows}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cal, bud = calibration(), budget()
    (OUT / "calibration.json").write_text(json.dumps(cal, indent=2) + "\n")
    (OUT / "budget.json").write_text(json.dumps(bud, indent=2) + "\n")
    print(json.dumps({"calibration": cal, "budget": bud}, indent=1))
