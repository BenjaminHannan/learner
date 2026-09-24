#!/usr/bin/env python3
"""lis-316: dev hit count and false-hold count per guard, on lis-301's dev readings (CPU).

For every dev fact that passes check_fact (the facts a wrapper could save), each guard is counted
as a catch (the fact is wrong against the per-fact gold) or a false hold (the fact is right).
Also per-fact release at T 0.995 with the guards on (guarded facts become unsure).

python3 scripts/claude_lis316_devcount.py --gold DEV --pred PRED --out FILE
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_score import match  # noqa: E402
from claude_lis302_rescore import load, pair, split_facts  # noqa: E402
from claude_lis316_guards import apply_guards, guard_fact  # noqa: E402
from claude_lis300_compiler import check_fact  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gold = load(a.gold)
    pred = {r["id"]: r for r in load(a.pred)}
    C = Counter()
    B = {"off": Counter(), "on": Counter()}
    for g in gold:
        turn, prev = g["turn"], g.get("prev_reply", "")
        G, _ = split_facts(g["frame"], turn, prev, [1.0] * 99, 0.0)
        p = pred.get(g["id"], {})
        fr, conf = p.get("frame"), p.get("conf") or []
        facts = (fr or {}).get("facts") or [] if isinstance(fr, dict) else []
        for i, f in enumerate(facts):
            if not isinstance(f, dict) or check_fact(f, turn, prev) is not None:
                continue
            right = any(match(f, gf) == "hit" for gf in G)
            C["facts"] += 1
            C["right" if right else "wrong"] += 1
            for name in guard_fact(f, turn, prev):
                C[f"{name}_{'false_hold' if right else 'catch'}"] += 1
        for mode in ("off", "on"):
            c = apply_guards(fr, conf, turn, prev)[0] if mode == "on" and isinstance(fr, dict) else conf
            auto, _ = split_facts(fr, turn, prev, c, 0.995)
            m = pair(auto, G)
            w = sum(x is None for x in m)
            B[mode]["hit"] += sum(x == "hit" for x in m)
            B[mode]["wrong_turns"] += int(w > 0)
    out = {"per_guard": dict(C), "perfact_T0.995": {k: dict(v) for k, v in B.items()}}
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
