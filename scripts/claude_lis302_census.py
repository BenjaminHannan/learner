#!/usr/bin/env python3
"""lis-302 report-only: score the two GPU measurements (no model, CPU only).

1. Field-level confidence census. lis-300's per-fact confidence is the minimum token probability
   over the act AND the whole fact JSON (punctuation and key names included). Here a fact's
   confidence is recomputed from tokprobs.jsonl (teacher-forced probs of the reader's own raw
   output) over ONLY the tokens that overlap the owner / rel / value / mode value strings.
   Arm B (per-fact release) is then swept with the old and the new confidence.
2. Exp-261 read-back checker. pyes.json holds P(YES) for every dev fact that passes check_fact.
   Each fact is marked right/wrong against the per-fact gold (same rule as the rescore), then
   counted by P(YES) < theta (checker veto).

python3 scripts/claude_lis302_census.py --gold DEV --pred PRED --tok TOKPROBS --pyes PYES \
    --manifest MANIFEST --out DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_score import match  # noqa: E402
from claude_lis302_rescore import GRID, pair, split_facts  # noqa: E402

FIELDS = ("owner", "rel", "value", "mode")
THETAS = [0.1, 0.25, 0.4, 0.5]


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def fact_objects(raw):
    """Char spans of each top-level object inside the "facts" list of the raw output."""
    i = raw.find('"facts"')
    if i < 0:
        return []
    i = raw.find("[", i)
    spans, depth, start, instr, esc = [], 0, None, False, False
    for j in range(i + 1, len(raw)):
        ch = raw[j]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = j
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                spans.append((start, j + 1))
        elif ch == "]" and depth == 0:
            break
    return spans


def field_spans(raw, s, e):
    """Char spans of the value strings of owner/rel/value/mode inside one fact object."""
    out = []
    for f in FIELDS:
        m = re.compile(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % f).search(raw, s, e)
        if m:
            out.append((m.start(1), m.end(1)))
    return out


def field_conf(tokens, spans):
    ps = [p for (a, b, p) in tokens for (x, y) in spans if a < y and b > x]
    return min(ps) if ps else None


def census(gold_rows, pred, tok):
    per = {}  # row id -> list of field confs (None when unavailable)
    C = Counter()
    for g in gold_rows:
        p = pred.get(g["id"], {})
        raw, fr = p.get("raw") or "", p.get("frame")
        facts = (fr or {}).get("facts") or [] if isinstance(fr, dict) else []
        objs = fact_objects(raw)
        t = tok.get(g["id"])
        confs = []
        for k in range(len(facts)):
            if t is None or k >= len(objs):
                confs.append(None)
                C["no_field_conf"] += 1
                continue
            confs.append(field_conf(t["tokens"], field_spans(raw, *objs[k])))
            C["field_conf"] += 1
        per[g["id"]] = confs
    return per, dict(C)


def sweep_b(gold_rows, pred, confs_of):
    res = []
    for T in GRID:
        S = Counter()
        for g in gold_rows:
            turn, prev = g["turn"], g.get("prev_reply", "")
            G, _ = split_facts(g["frame"], turn, prev, [1.0] * 99, 0.0)
            p = pred.get(g["id"], {})
            auto, _ = split_facts(p.get("frame"), turn, prev, confs_of(g["id"], p), T)
            m = pair(auto, G)
            w = sum(x is None for x in m)
            S["gold"] += len(G)
            S["hit"] += sum(x == "hit" for x in m)
            S["wrong_facts"] += w
            S["wrong_turns"] += int(w > 0)
        res.append(dict(S, T=T))
    return res


def checker(gold, pyes, man, pred):
    rows = []
    for cid, m in man.items():
        g = gold[m["row"]]
        G, _ = split_facts(g["frame"], g["turn"], g.get("prev_reply", ""), [1.0] * 99, 0.0)
        right = any(match(m["fact"], gf) == "hit" for gf in G)
        rows.append({"id": cid, "row": m["row"], "right": right, "conf": m["conf"],
                     "p": pyes[cid]["p"]})
    out = {"facts": len(rows), "right": sum(r["right"] for r in rows),
           "wrong": sum(not r["right"] for r in rows), "by_theta": {}}
    for th in THETAS:
        out["by_theta"][str(th)] = {
            "wrong_vetoed": sum((not r["right"]) and r["p"] < th for r in rows),
            "right_vetoed": sum(r["right"] and r["p"] < th for r in rows)}
    # checker as a second gate on top of per-fact release at T (veto facts with p < 0.25)
    for T in (0.0, 0.9, 0.995):
        kept = [r for r in rows if r["conf"] >= T]
        wrong_turns = {r["row"] for r in kept if not r["right"]}
        wrong_turns_chk = {r["row"] for r in kept if not r["right"] and r["p"] >= 0.25}
        out[f"T{T}"] = {"saved_right": sum(r["right"] for r in kept),
                        "saved_right_after_veto": sum(r["right"] and r["p"] >= 0.25 for r in kept),
                        "wrong_turns": len(wrong_turns), "wrong_turns_after_veto": len(wrong_turns_chk)}
    return out, rows


def main():
    ap = argparse.ArgumentParser()
    for k in ("gold", "pred", "tok", "pyes", "manifest", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    gold_rows = load(a.gold)
    gold = {r["id"]: r for r in gold_rows}
    pred = {r["id"]: r for r in load(a.pred)}
    tok = {r["id"]: r for r in load(a.tok)}
    per, cc = census(gold_rows, pred, tok)

    def old(rid, p):
        return p.get("conf") or []

    def new(rid, p):
        return [0.0 if c is None else c for c in per.get(rid, [])]

    res = {"census_counts": cc, "B_old_conf": sweep_b(gold_rows, pred, old),
           "B_field_conf": sweep_b(gold_rows, pred, new)}
    pyes = json.loads(Path(a.pyes).read_text(encoding="utf-8"))["checks"]
    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    res["checker"], rows = checker(gold, pyes, man, pred)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "census.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for name in ("B_old_conf", "B_field_conf"):
        print(name)
        for r in res[name]:
            print(f"  T={r['T']:.3f} hit {r['hit']}/{r['gold']} wrong_facts {r['wrong_facts']} "
                  f"wrong_turns {r['wrong_turns']}")
    print(json.dumps(res["checker"], indent=1))
    print(json.dumps(cc))


if __name__ == "__main__":
    main()
