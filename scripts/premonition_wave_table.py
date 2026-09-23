"""Per-seed table and pass counts from run JSONs (Claude, 2026-09-19). Validation numbers only; no model is loaded.

    python3 scripts/premonition_wave_table.py <runs_dir> [<runs_dir> ...]

Pass marks (fixed in advance): STUCK = one-hop < 384/512; READS = gold-read practised two-hop >= 307/341;
PRACTISED = own two-hop >= 171/341; HELD-OUT = own held-out two-hop >= 86/171. "own" = fixed_K4.
"""
import glob, json, re, sys


def load(runs_dir):
    rows = []
    for path in glob.glob(runs_dir.rstrip("/") + "/*.json"):
        d = json.load(open(path))
        v = d["validation"]
        own, gold = v["fixed_K4"], v["gold_read_K2_no_fetch"]
        rows.append({"name": d["name"], "seed": d["seed"], "one": own["one_hop"]["correct"],
                     "prac": own["two_hop_trained_rel"]["correct"], "held": own["two_hop_heldout_rel"]["correct"],
                     "reads": gold["two_hop_trained_rel"]["correct"], "reads_held": gold["two_hop_heldout_rel"]["correct"],
                     "steps": (d.get("curve") or [{}])[-1].get("step"), "gpu": d.get("gpu_name")})
    return sorted(rows, key=lambda r: r["seed"])


def summary(rows):
    n = len(rows)
    stuck = [r for r in rows if r["one"] < 384]
    live = [r for r in rows if r["one"] >= 384]
    return {"n": n, "stuck": len(stuck), "stuck_seeds": [r["seed"] for r in stuck],
            "reads_pass": sum(r["reads"] >= 307 for r in rows),
            "practised_pass": sum(r["prac"] >= 171 for r in rows),
            "heldout_pass": sum(r["held"] >= 86 for r in rows),
            "heldout_pass_of_learned": [sum(r["held"] >= 86 for r in live), len(live)],
            # the original three marks: READS, PRACTISED, HELD-OUT (one-hop is the separate STUCK rule)
            "all_three": sum(r["reads"] >= 307 and r["prac"] >= 171 and r["held"] >= 86 for r in rows),
            "all_four": sum(r["one"] >= 384 and r["reads"] >= 307 and r["prac"] >= 171 and r["held"] >= 86
                            for r in rows)}


if __name__ == "__main__":
    for runs_dir in sys.argv[1:]:
        rows = load(runs_dir)
        print(f"\n== {runs_dir}  ({len(rows)} runs; {sorted(set(r['gpu'] for r in rows))})")
        print("seed  one/512  prac/341  held/171  reads/341  steps")
        for r in rows:
            flag = "  STUCK" if r["one"] < 384 else ""
            print(f"{r['seed']:>4}  {r['one']:>7}  {r['prac']:>8}  {r['held']:>8}  {r['reads']:>9}  {r['steps']}{flag}")
        print(json.dumps(summary(rows)))
