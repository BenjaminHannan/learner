#!/usr/bin/env python3
"""lis-302: build exp-261 checker queries (sealed prompt B + sealed claim renderer, imported
read-only) for every lis-301 dev fact that would be saved per-fact at T=0.

python3 scripts/claude_lis302_checks.py --gold DEV --pred PRED --out checks.json
Writes checks.json [{id, prompt}] (the format claude_earcheck261_checker.py reads) and
checks_manifest.json {id: {row, fact, conf, claim}}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_earcheck261_canon as C  # noqa: E402 (sealed renderer, read-only)
import claude_earcheck261_promptB as PB  # noqa: E402 (sealed prompt B, read-only)
from claude_lis300_compiler import check_fact  # noqa: E402


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gold = {r["id"]: r for r in load(a.gold)}
    checks, man = [], {}
    for p in load(a.pred):
        g = gold[p["id"]]
        fr = p.get("frame")
        if not isinstance(fr, dict):
            continue
        for k, f in enumerate(fr.get("facts") or []):
            if not isinstance(f, dict) or check_fact(f, g["turn"], g.get("prev_reply", "")) is not None:
                continue
            claim = C.render_claim(f["owner"], f["rel"], f["value"])
            cid = f"{p['id']}#f{k}"
            checks.append({"id": cid, "prompt": PB.build_prompt_b(g["turn"], claim)})
            man[cid] = {"row": p["id"], "fact": f, "conf": (p.get("conf") or [0.0] * 99)[k], "claim": claim}
    out = Path(a.out)
    out.write_text(json.dumps(checks, indent=1), encoding="utf-8")
    (out.parent / "checks_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print("checks", len(checks))


if __name__ == "__main__":
    main()
