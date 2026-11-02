"""results/recallread/REPORT.md: the pass-mark table, accuracy per arm and split, diagnostics, and the R-vs-D3 ledger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import stats


def md_table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows])


def build(resdir: Path) -> str:
    data = stats.load(resdir)
    S = stats.summary(data)
    pm = S["pass_marks"]
    L = ["# Recall-then-read, stage 1: results", "", "Scope: K2-Horizon-3.7B, Week-2 world only. Not the village model, not the card experiments. Mac latency (pass mark 5) was not run.", ""]
    L += ["## Pass marks", "", md_table(["mark", "rule", "result", "numbers"], [
        [k, v.get("name"), v["status"], ", ".join(f"{a}={v[a]}" for a in ("R", "rival", "rival_acc", "R_minus_rival", "p", "D0", "per_seed_diff") if a in v)]
        for k, v in pm.items() if isinstance(v, dict) and "status" in v]), ""]
    L += [f"- Proves-wrong rule ({pm['proves_wrong']['rule']}): triggered = {pm['proves_wrong']['triggered']}", f"- Marks 1-4: {pm['accuracy_marks_1_to_4']}"]
    bd = S["bridge_diagnostic"]
    L += [f"- Bridge diagnostic: R names the right bridge on {bd['bridge_named_pct']}% of natural two-hop items; R two-hop accuracy {bd['R_twohop_acc']}%. "
          f"Reader bottleneck (>80% named but <50% right): {bd['reader_bottleneck']}", ""]
    sp = ("twohop_nat", "twohop_gap", "W_nat", "onehop", "never")
    L += ["## Accuracy (%, pooled over both seeds; never = 'don't know' rate)", "", md_table(["arm", *sp], [[a, *[S["accuracy_pct"][a][s] for s in sp]] for a in S["accuracy_pct"]]), ""]
    L += ["## Bridge named % and hit@3 (fused ranking) per hop", "", md_table(["arm", "split", "bridge_named", "hit3_hop1", "hit3_hop2"],
          [[a, s, d["bridge_named"], d["hit3_hop1"], d["hit3_hop2"]] for a, v in S["diagnostics"].items() for s, d in v.items()]), ""]
    L += ["## Secondary paired comparisons (a = first arm, b = second; pooled and per seed)", ""]
    for k, v in S["secondary"].items():
        L.append(f"- {k}: pooled {v['pooled']}; per seed {v['per_seed']}")
    led = sorted((resdir / "results" / "recallread").glob("ledger_R_vs_D3_*.json"))
    L += ["", "## Ledger (R vs D3, equal-compute check passed when these files exist)", ""] + [f"- {f.name}: {f.read_text()}" for f in led]
    gs = resdir / "results" / "recallread" / "grade_summary.json"
    if gs.exists():
        L += ["", f"## Grader agreement", "", gs.read_text()]
    L += ["", "Labels: everything above is measured on one world and two LoRA seeds; read claims as 'shown' only for the marks that pass with the stated p. "
          "Pooled tests stack two seeds and baseline arms are seed-free, so pooled p is optimistic; the per-seed rows are the conservative check."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="dir that holds results/recallread/graded/")
    a = ap.parse_args()
    res = Path(a.results)
    out = res / "results" / "recallread" / "REPORT.md"
    out.write_text(build(res))
    (res / "results" / "recallread" / "summary.json").write_text(json.dumps(stats.summary(stats.load(res)), indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
