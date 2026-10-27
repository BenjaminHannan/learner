"""Probe-3 verdict with Addendum 1 applied. Reads the decision run (OUT/report.json: tuned K2, --wrong-at 37.5) and the MLX-BASE report (OUT/mlx_base/report.json) and writes OUT/VERDICT.md.
Addendum 1: if MLX-BASE alone reaches the P1 mark (>= SELF + 5 points = 39.4%), a pass of the tuned arm is not credited to training and the verdict is INCONCLUSIVE.
Usage: summarize.py OUT"""
import json, os, sys

EPS = 1e-9


def combine(tuned, base):
    """-> (final verdict, note). tuned/base: report.json dicts (base may be None)."""
    v = tuned["verdict"]
    p1 = tuned["p1_needs"]
    t = tuned["metrics"]["pick_rate"].get("PROBE-S", {}).get("all")
    b = None if base is None else base["metrics"]["pick_rate"].get("PROBE-S", {}).get("all")
    if base is None:
        return v, "MLX-BASE report missing: the Addendum 1 backend control has not been run, so the verdict is provisional."
    if b is not None and b >= p1 - EPS:
        note = f"MLX-BASE (untuned K2 on the MLX stack) alone reaches the P1 mark: {b:.1f}% >= {p1:.1f}%. "
        return ("INCONCLUSIVE", note + (f"The tuned arm's {v} is not credited to training." if v == "PASS" else f"Tuned arm alone said {v}; overridden to INCONCLUSIVE by Addendum 1."))
    return v, f"MLX-BASE PROBE-S {b:.1f}% is below the P1 mark {p1:.1f}%, so the tuned verdict stands." if b is not None else "MLX-BASE has no PROBE-S rate."


def main():
    out = sys.argv[1]
    tuned = json.load(open(os.path.join(out, "report.json")))
    bp = os.path.join(out, "mlx_base", "report.json")
    base = json.load(open(bp)) if os.path.exists(bp) else None
    final, note = combine(tuned, base)
    row = lambda r, n: f"| {n} | {r['pick_rate'].get('PROBE-S', {}).get('all', float('nan')):.1f} | {r['auroc'].get('PROBE-S', float('nan')):.3f} | {r['pick_rate'].get('SELF', {}).get('all', float('nan')):.1f} |"  # noqa
    L = ["# Probe-3 (MLX, Addendum 1) verdict", "", f"**{final}**", "", note, "",
         "| arm | PROBE-S pick rate (%) | AUROC | SELF (%) |", "|---|---|---|---|", row(tuned["metrics"], "tuned K2 (MLX)")]
    if base:
        L.append(row(base["metrics"], "MLX-BASE (untuned, MLX)"))
    L += ["", f"Tuned-arm marks: P1 needs >= {tuned['p1_needs']:.1f}%, P2 AUROC >= 0.75, PROVED WRONG <= {tuned['wrong_at']:.1f}%; tuned-arm verdict before the control: {tuned['verdict']} ({tuned['checks']}).",
          "Diagnostics (tuned): " + json.dumps({k: (round(x, 3) if isinstance(x, float) else x) for k, x in (tuned["diagnostics"].get("k2") or {}).items()
                                                  if k in ("validity_rate", "reference_agreement", "all_tie_rate", "unparsable_samples", "samples_with_no_valid")})]
    if base:
        L.append("Diagnostics (MLX-BASE): " + json.dumps({k: (round(x, 3) if isinstance(x, float) else x) for k, x in (base["diagnostics"].get("k2") or {}).items()
                                                        if k in ("validity_rate", "reference_agreement", "all_tie_rate", "unparsable_samples", "samples_with_no_valid")}))
    open(os.path.join(out, "VERDICT.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
