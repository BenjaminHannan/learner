"""Build the per-seed table for the loop-step-embedding screen (Claude, 2026-09-19).

Reads the 10 run JSONs (artifacts/claude-seeds-20260919/runs) and the first-card probe JSON, and prints a
markdown table plus the predeclared pass/fail counts. Eval-only; writes nothing but stdout / --json.

    PY -B scripts/premonition_seed_screen_report.py --dir artifacts/claude-seeds-20260919 --probe <probe.json>

Extended 2026-09-19 (screen 2) to take more than one arm / directory, each with its own probe JSON:

    PY -B scripts/premonition_seed_screen_report.py \
        --arm baseline:base:artifacts/claude-seeds-20260919 --probe artifacts/.../first_card_probe.json \
        --arm ordered:ordered:artifacts/claude-ordered-20260919 --probe artifacts/.../probe_ordered.json

`--arm label:prefix:dir` names an arm, the run-name prefix (<prefix>-s<seed>-4000lr) and the run directory;
each --probe is merged into one checkpoint lookup. With no --arm the original two-arm default is used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

CRIT = {"READS": ("gold_both_K2", "practised", 307, 341),
        "PRACTISED": ("own_K4", "practised", 171, 341),
        "HELDOUT": ("own_K4", "heldout", 86, 171)}


def first_fetch(probe, cond, group):
    f = probe[cond][group]["fetches"].get("own_fetch1")
    return (0, 0, 0, 0) if f is None else (f["right_both"], f["right_relation"], f["right_person"], f["total"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=None)
    p.add_argument("--probe", action="append", required=True)
    p.add_argument("--arm", action="append", default=None,
                   help="label:prefix:dir (repeatable); default = baseline:base:--dir and no-step-emb:nostep:--dir")
    p.add_argument("--json", default=None)
    p.add_argument("--fractions", default=None,
                   help="screen 4: READS,PRACTISED,HELDOUT pass marks as FRACTIONS of each condition's own n "
                        "(e.g. 0.90,0.50,0.50). Default: the absolute screen-1/2 marks above.")
    p.add_argument("--steps-tag", default="4000lr", help="run-name suffix after -s<seed>- (default 4000lr)")
    a = p.parse_args()
    fractions = None
    if a.fractions:
        values = [float(x) for x in a.fractions.split(",")]
        if len(values) != 3:
            raise SystemExit("--fractions needs three comma-separated numbers")
        fractions = dict(zip(("READS", "PRACTISED", "HELDOUT"), values))
    if a.arm:
        arms = []
        for spec in a.arm:
            parts = spec.split(":")
            label, prefix = parts[0], parts[1]
            arms.append((label, prefix, Path(parts[2]) if len(parts) > 2 else Path(a.dir)))
    else:
        arms = [("baseline", "base", Path(a.dir)), ("no-step-emb", "nostep", Path(a.dir))]
    probes = {}
    for path in a.probe:
        probes.update(json.loads(Path(path).read_text())["checkpoints"])
    rows = []
    for arm, prefix, root in arms:
        for seed in range(5):
            name = f"{prefix}-s{seed}-{a.steps_tag}"
            rj = root / "runs" / (name + ".json")
            if not rj.exists() or name not in probes:
                rows.append({"arm": arm, "seed": seed, "name": name, "missing": True})
                continue
            run = json.loads(rj.read_text())
            pr = probes[name]
            r = {"arm": arm, "seed": seed, "name": name, "missing": False,
                 "no_step_emb": run.get("no_step_emb"),
                 "ordered_evidence": run.get("ordered_evidence"),
                 "step_emb_absmax": run.get("step_emb_absmax_after_training"),
                 "one_hop_K4": run["validation"]["fixed_K4"]["one_hop"]["correct"],
                 "one_hop_n": run["validation"]["fixed_K4"]["one_hop"]["n"]}
            for cond in ("gold_both_K2", "own_K4", "forced_first_K4", "preload_link_K4"):
                for group in ("practised", "heldout"):
                    r[f"{cond}_{group}"] = pr[cond][group]["correct"]
                    r[f"{cond}_{group}_n"] = pr[cond][group]["n"]
            for cond in ("forced_first_K4", "preload_link_K4"):
                for group in ("practised", "heldout"):
                    both, rel, per, tot = first_fetch(pr, cond, group)
                    r[f"{cond}_{group}_f1"] = {"both": both, "rel": rel, "person": per, "total": tot}
            for crit, (cond, group, need, n) in CRIT.items():
                if fractions is not None:
                    need = fractions[crit] * r[f"{cond}_{group}_n"]
                r[crit] = r[f"{cond}_{group}"] >= need
                r[f"{crit}_need"] = need
            r["gap_practised"] = (r["forced_first_K4_practised_f1"]["both"]
                                  - r["preload_link_K4_practised_f1"]["both"])
            r["gap_heldout"] = (r["forced_first_K4_heldout_f1"]["both"]
                                - r["preload_link_K4_heldout_f1"]["both"])
            r["acc_gap_practised"] = r["forced_first_K4_practised"] - r["preload_link_K4_practised"]
            r["acc_gap_heldout"] = r["forced_first_K4_heldout"] - r["preload_link_K4_heldout"]
            rows.append(r)

    head = ("| arm | seed | 1-hop own K4 | gold_both prac | gold_both held | own_K4 prac | own_K4 held | "
            "forced_first K4 prac | forced_first K4 held | ff first fetch prac (both/rel/person of n) | "
            "ff first fetch held | preload K4 prac | preload K4 held | pre first fetch prac | pre first fetch held | "
            "READS | PRACTISED | HELD-OUT |")
    print(head)
    print("|" + "---|" * 18)
    for r in rows:
        if r["missing"]:
            print(f"| {r['arm']} | {r['seed']} | RUN MISSING |" + " |" * 16)
            continue
        def ff(k):
            d = r[k]
            return f"{d['both']}/{d['rel']}/{d['person']} of {d['total']}"
        print("| {arm} | {seed} | {oh}/{ohn} | {gbp}/{gbpn} | {gbh}/{gbhn} | {op}/{opn} | {oh2}/{ohn2} | "
              "{ffp}/{ffpn} | {ffh}/{ffhn} | {ff1} | {ff2} | {plp}/{plpn} | {plh}/{plhn} | {pf1} | {pf2} | "
              "{R} | {P} | {H} |".format(
                  arm=r["arm"], seed=r["seed"], oh=r["one_hop_K4"], ohn=r["one_hop_n"],
                  gbp=r["gold_both_K2_practised"], gbpn=r["gold_both_K2_practised_n"],
                  gbh=r["gold_both_K2_heldout"], gbhn=r["gold_both_K2_heldout_n"],
                  op=r["own_K4_practised"], opn=r["own_K4_practised_n"],
                  oh2=r["own_K4_heldout"], ohn2=r["own_K4_heldout_n"],
                  ffp=r["forced_first_K4_practised"], ffpn=r["forced_first_K4_practised_n"],
                  ffh=r["forced_first_K4_heldout"], ffhn=r["forced_first_K4_heldout_n"],
                  ff1=ff("forced_first_K4_practised_f1"), ff2=ff("forced_first_K4_heldout_f1"),
                  plp=r["preload_link_K4_practised"], plpn=r["preload_link_K4_practised_n"],
                  plh=r["preload_link_K4_heldout"], plhn=r["preload_link_K4_heldout_n"],
                  pf1=ff("preload_link_K4_practised_f1"), pf2=ff("preload_link_K4_heldout_f1"),
                  R="PASS" if r["READS"] else "FAIL", P="PASS" if r["PRACTISED"] else "FAIL",
                  H="PASS" if r["HELDOUT"] else "FAIL"))
    print()
    for arm, _prefix, _root in arms:
        got = [r for r in rows if r["arm"] == arm and not r["missing"]]
        if not got:
            print(arm, "runs 0")
            continue
        ff_both = [r["forced_first_K4_practised_f1"]["both"] for r in got]
        ff_held = [r["forced_first_K4_heldout_f1"]["both"] for r in got]
        ff_held_n = got[0]["forced_first_K4_heldout_f1"]["total"]
        print(arm, "runs", len(got),
              "READS", sum(r["READS"] for r in got),
              "PRACTISED", sum(r["PRACTISED"] for r in got),
              "HELDOUT", sum(r["HELDOUT"] for r in got),
              "| forced_first K4 practised fully-right next request", ff_both,
              "median", statistics.median(ff_both),
              "| forced_first K4 HELD-OUT fully-right next request", ff_held,
              "median", statistics.median(ff_held), "of", ff_held_n,
              "(median fraction {:.4f})".format(statistics.median(ff_held) / max(ff_held_n, 1)),
              "| gaps practised", [r["gap_practised"] for r in got],
              "| gaps heldout", [r["gap_heldout"] for r in got],
              "| acc gap practised", [r["acc_gap_practised"] for r in got])
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
