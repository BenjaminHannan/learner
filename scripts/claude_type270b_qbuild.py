#!/usr/bin/env python3
"""Exp 270b -- checker-query builder (sealed).

Thin wrapper over 261's sealed query path (same brake -> canon -> prompt B),
run once per arm with that arm's turn text:
  arm A:     ear preds on NORMALISED turns (<id>-norm), prompts on fixed text
  arm A261b: ear preds on RAW turns (<id>-raw), prompts on raw text
             (261b's A exactly).

Reads: --dev DEV.jsonl, --preds EARPREDS.json, --normmanifest NORM.json.
Writes: DIR/checks.json [{id: "<devid>#t<k>", prompt}] + DIR/manifest.json
{cid: {row, k, turn, claim, canon: True}} (261's sealed check-id shape, so the
sealed split aligns by construction).

python -B scripts/claude_type270b_qbuild.py --dev D --preds P --normmanifest N --arm A --prompt B --out DIR
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_earcheck261_arms as A  # noqa: E402 (read-only)
import claude_earcheck261_promptB as PB  # noqa: E402 (read-only, prompt B)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--normmanifest", required=True)
    ap.add_argument("--arm", choices=["A", "A261b"], required=True)
    ap.add_argument("--prompt", choices=["B"], default="B")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = [json.loads(x) for x in Path(a.dev).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    preds = json.loads(Path(a.preds).read_text(encoding="utf-8"))["preds"]
    nman = json.loads(Path(a.normmanifest).read_text(encoding="utf-8"))
    suffix = "-norm" if a.arm == "A" else "-raw"
    checks, manif = [], {}
    for it in items:
        turn = nman[it["id"]]["fixed"] if a.arm == "A" else it["turn"]
        p = preds[it["id"] + suffix]
        arms = A.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], turn)):
            cid = f"{it['id']}#t{k}"
            checks.append({"id": cid,
                           "prompt": PB.build_prompt_b(turn, q["claim"])})
            manif[cid] = {"row": it["id"], "k": k, "turn": turn,
                          "frame": q["frame"], "claim": q["claim"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1),
                                     encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manif, indent=1),
                                       encoding="utf-8")
    print(f"arm {a.arm}: {len(items)} items -> {len(checks)} checks")


if __name__ == "__main__":
    main()
