#!/usr/bin/env python3
"""lis-300 scorer: grades the listener + write compiler against gold frames.

Both gold and predicted frames go through the SAME compiler (gold with confidence 1).
A predicted write counts as:
  hit     same owner and value (case-insensitive), and the same relation or a narrower one
          (Ruling 1, 261b-decision.md; pet also covers rabbit/hamster/parrot/horse);
  broader same owner and value, and the predicted relation is broader than the gold one
          (true but vague: not a wrong save, not a recall hit);
  wrong   anything else.

python claude_lis300_score.py --gold GOLD.jsonl --pred PRED.jsonl [--turns TURNS.jsonl]
        [--threshold T | --sweep] [--out OUT.json]
GOLD rows: {"id","frame"[, "turn","prev_reply","family"]}; TURNS supplies turn/prev_reply
if GOLD lacks them. PRED rows: {"id","frame","conf","ms"} from claude_lis300_read.py.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_compiler import compile_frame  # noqa: E402

NARROWER = {"parent": {"mother", "father"}, "sibling": {"sister", "brother"},
            "spouse": {"wife", "husband"}, "child": {"son", "daughter"},
            "grandchild": {"grandson", "granddaughter"},
            "pet": {"dog", "cat", "rabbit", "hamster", "parrot", "horse"}}


def norm(x):
    return " ".join(str(x or "").lower().split())


def match(p, g):
    if norm(p.get("owner")) != norm(g.get("owner")) or norm(p.get("value")) != norm(g.get("value")):
        return None
    pr, gr = p.get("rel"), g.get("rel")
    if pr == gr or pr in NARROWER.get(gr, ()):
        return "hit"
    if gr in NARROWER.get(pr, ()):
        return "broader"
    return None


def ask_ok(p, g):
    if not isinstance(p, dict) or not isinstance(g, dict):
        return False
    via_g = g.get("via") or g.get("then")
    rel_ok = p.get("rel") == g.get("rel") or p.get("rel") in NARROWER.get(g.get("rel"), ())
    return (norm(p.get("owner")) == norm(g.get("owner")) and rel_ok
            and bool(p.get("inverse")) == bool(g.get("inverse"))
            and norm(p.get("via")) == norm(via_g if isinstance(via_g, str) else ""))


def load(p):
    return {r["id"]: r for r in (json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip())}


def score(gold, pred, turns, threshold):
    S = Counter()
    fam_wrong = Counter()
    ms = []
    for i, g in gold.items():
        t = turns.get(i, g)
        turn, prev = t.get("turn", ""), t.get("prev_reply", "")
        gd = compile_frame(g["frame"], turn, prev)
        p = pred.get(i, {})
        pf = p.get("frame")
        S["turns"] += 1
        if pf is None:
            S["parse_fail"] += 1
        if "ms" in p:
            ms.append(p["ms"])
        pd = compile_frame(pf, turn, prev, conf=p.get("conf"), threshold=threshold)
        G, W = gd["write"], pd["write"]
        S["gold_writes"] += len(G)
        S["pred_writes"] += len(W)
        wrong = 0
        used = set()
        for w in W:
            lvl = None
            for k, gf in enumerate(G):
                if k not in used:
                    lvl = match(w, gf)
                    if lvl:
                        used.add(k)
                        break
            if lvl == "hit":
                S["hits"] += 1
            elif lvl == "broader":
                S["broader"] += 1
            else:
                wrong += 1
        S["wrong_facts"] += wrong
        if wrong:
            S["wrong_turns"] += 1
            fam_wrong[g.get("family", "?")] += 1
            if not G:
                S["wrong_turns_on_nosave_turns"] += 1
        if G:
            S["gold_write_turns"] += 1
            S["turn_exact"] += int(wrong == 0 and len(used) == len(G) and len(W) == len(G))
            S["held_back_facts"] += sum(1 for k, gf in enumerate(G) if k not in used) if pd["ask_back"] else 0
        if gd["ask_whose"]:
            S["we_turns"] += 1
            S["we_asked"] += int(bool(pd["ask_whose"]))
        ga = g["frame"].get("ask") if g["frame"].get("act") == "ASK" else None
        if ga:
            S["ask_turns"] += 1
            S["ask_ok"] += int(isinstance(pf, dict) and pf.get("act") == "ASK" and ask_ok(pf.get("ask"), ga))
    res = dict(S)
    res["threshold"] = threshold
    res["recall_exact"] = S["hits"] / max(1, S["gold_writes"])
    res["ask_acc"] = S["ask_ok"] / max(1, S["ask_turns"])
    res["we_ask_rate"] = S["we_asked"] / max(1, S["we_turns"])
    res["wrong_turns_by_family"] = dict(fam_wrong)
    if ms:
        ms.sort()
        res["ms_median"] = statistics.median(ms)
        res["ms_p90"] = ms[int(0.9 * (len(ms) - 1))]
        res["ms_max"] = ms[-1]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--turns")
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    gold, pred = load(a.gold), load(a.pred)
    turns = load(a.turns) if a.turns else {}
    if a.sweep:
        grid = [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995]
        res = [score(gold, pred, turns, t) for t in grid]
        for r in res:
            print(f"t={r['threshold']:.3f} wrong_turns={r.get('wrong_turns', 0)} "
                  f"recall={r.get('hits', 0)}/{r['gold_writes']} ask={r.get('ask_ok', 0)}/{r.get('ask_turns', 0)} "
                  f"we={r.get('we_asked', 0)}/{r.get('we_turns', 0)}")
    else:
        res = score(gold, pred, turns, a.threshold)
        print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
