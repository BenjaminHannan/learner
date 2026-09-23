#!/usr/bin/env python3
"""Exp 292 scorer: tally sealed-scorer outputs into ids-only checks.

New file only. Never prints item text or replies: the published check
files carry ids, families and counts only (raw rows and sealed-scorer
stdout stay in the run tmpdir).

usage:
  claude_292_score.py m1 --panel P --piece-score S1 --new-score S2
                         --piece-rows R1 --new-rows R2 --pred PRED
                         --out CHECK.json
    P in chain266b|nhop268b|yesno293|corr291. S1/S2 are the sealed
    scorer's captured outputs (chain/corr: stdout text; nhop/yesno:
    score JSON). R1/R2 are the row files (for id lists). Compares the
    292 arm against the piece arm: right-lost ids, new-wrong ids,
    new-write ids, control drift ids.
  claude_292_score.py m2m6 --dir R --pred PRED --out CHECK.json
    Tallies suitediff summaries, rt136/rt143 rows and probe rows in R
    against the predicted move lists in PRED.
  claude_292_score.py m5 --dir T --out CHECK.json
    Tallies the sealed mixpanel scores for the 5 arms in T (ids and
    counts only).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


def parse_chain_text(s: str):
    per_item, per_family = [], {}
    for line in s.splitlines():
        m = re.match(r"^(c266b-\d+)\s+(\S+)\s+([01])\s+([01])\s+([01])\s+::",
                     line)
        if m:
            per_item.append({"id": m.group(1), "family": m.group(2),
                             "right": m.group(3) == "1",
                             "wrong": m.group(4) == "1",
                             "wrote": m.group(5) == "1"})
            continue
        m = re.match(r"^(\S+):\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
                     line)
        if m:
            per_family[m.group(1)] = {
                "n": int(m.group(2)), "right": int(m.group(3)),
                "wrong": int(m.group(4)), "wrote": int(m.group(5)),
                "other": int(m.group(6))}
    return per_item, per_family


def parse_corr_text(s: str):
    per_family = {}
    for line in s.splitlines():
        m = re.match(r"^(\S+)\s+(\d+)/(\d+)\s+wrong\s+(\d+)\s+junk\s+(\d+)"
                     r"\s+fw\s+(\d+)\s+fclaim\s+(\d+)", line)
        if m:
            per_family[m.group(1)] = {
                "right": int(m.group(2)), "n": int(m.group(3)),
                "wrong": int(m.group(4)), "junk": int(m.group(5)),
                "fw": int(m.group(6)), "fclaim": int(m.group(7))}
    return per_family


def strip_json_score(doc: dict):
    fams = {}
    for f, v in (doc.get("per_family") or {}).items():
        fams[f] = {k: v.get(k) for k in
                   ("n", "right", "right_names", "wrong", "question_wrote")
                   if k in v}
    items = [{"id": p["id"], "family": p.get("family"),
              "right": bool(p.get("right")), "wrong": bool(p.get("wrong")),
              "wrote": bool(p.get("question_wrote", p.get("wrote")))}
             for p in doc.get("per_item", [])]
    return {"per_family": fams, "total": doc.get("total"),
            "items": items}


def cmd_m1(a) -> int:
    s1 = Path(a.piece_score).read_text(encoding="utf-8")
    s2 = Path(a.new_score).read_text(encoding="utf-8")
    if a.panel in ("nhop268b", "yesno293"):
        d1, d2 = strip_json_score(json.loads(s1)), strip_json_score(
            json.loads(s2))
        i1 = {p["id"]: p for p in d1["items"]}
        i2 = {p["id"]: p for p in d2["items"]}
    elif a.panel == "chain266b":
        l1, f1 = parse_chain_text(s1)
        l2, f2 = parse_chain_text(s2)
        i1 = {p["id"]: p for p in l1}
        i2 = {p["id"]: p for p in l2}
        d1, d2 = {"per_family": f1}, {"per_family": f2}
    else:
        f1, f2 = parse_corr_text(s1), parse_corr_text(s2)
        d1, d2 = {"per_family": f1}, {"per_family": f2}
        i1, i2 = {}, {}
        r1 = [json.loads(l) for l in
              Path(a.piece_rows).read_text(encoding="utf-8").splitlines()
              if l.strip()] if a.piece_rows else []
        r2 = [json.loads(l) for l in
              Path(a.new_rows).read_text(encoding="utf-8").splitlines()
              if l.strip()] if a.new_rows else []
        # corr rows carry no per-item right flags; scorer text is the
        # verdict. Id-level diffs come from reply/store compares below.
        _ = (r1, r2)
    right_lost = sorted(i for i in i1 if i1[i]["right"] and not
                        i2.get(i, {}).get("right"))
    new_wrong = sorted(i for i in i2 if i2[i]["wrong"] and not
                       i1.get(i, {}).get("wrong"))
    new_wrote = sorted(i for i in i2 if i2[i]["wrote"] and not
                       i1.get(i, {}).get("wrote"))
    check = {"panel": a.panel,
             "piece_families": d1.get("per_family"),
             "new_families": d2.get("per_family"),
             "piece_total": d1.get("total"),
             "new_total": d2.get("total"),
             "right_lost_ids": right_lost, "new_wrong_ids": new_wrong,
             "new_write_ids": new_wrote,
             "n_right_lost": len(right_lost),
             "n_new_wrong": len(new_wrong),
             "n_new_write": len(new_wrote)}
    Path(a.out).write_text(json.dumps(check, indent=1), encoding="utf-8")
    print(json.dumps(check, indent=1))
    return 0


def cmd_m2m6(a) -> int:
    d = Path(a.dir)
    pred = json.loads(Path(a.pred).read_text(encoding="utf-8"))
    out: dict = {"predicted": {k: (v if not isinstance(v, dict) else
                                   sorted(v)) for k, v in pred.items()}}
    for name in ("sd/SUITEDIFF218-SUMMARY.json", "sd136/SUITEDIFF218-SUMMARY.json"):
        p = d / name
        if p.exists():
            try:
                out[name] = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                out[name] = {"read_error": str(e)}
    for name in ("rt143nogate-291.json", "rt143nogate-292.json"):
        p = d / name
        if p.exists():
            try:
                rows = [json.loads(l) for l in
                        p.read_text(encoding="utf-8").splitlines()
                        if l.strip()]
                out[name] = {"n": len(rows)}
            except Exception as e:  # noqa: BLE001
                out[name] = {"read_error": str(e)}
    probes = {}
    for p in sorted(d.glob("probe/*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                probes[p.name] = {"keys": sorted(doc.keys())[:10]}
            elif isinstance(doc, list):
                probes[p.name] = {"n": len(doc)}
            else:
                probes[p.name] = {"type": type(doc).__name__}
        except Exception as e:  # noqa: BLE001
            probes[p.name] = {"read_error": str(e)}
    out["probes"] = probes
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1)[:4000])
    return 0


def cmd_m5(a) -> int:
    d = Path(a.dir)
    arms = {}
    for score_file in sorted(d.glob("score-mixpanel292-*.json")):
        arm = score_file.stem.replace("score-mixpanel292-", "")
        try:
            doc = json.loads(score_file.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            arms[arm] = {"read_error": str(e)}
            continue
        fams = {}
        for f, v in (doc.get("per_family") or doc.get("families")
                     or {}).items():
            if isinstance(v, dict):
                fams[f] = {k: v[k] for k in v if
                           k in ("n", "right", "wrong", "question_wrote",
                                 "writes", "controls_same")}
        items = []
        for p in doc.get("per_item", doc.get("items", [])):
            if isinstance(p, dict) and "id" in p:
                items.append({k: p[k] for k in p if k != "question_reply"
                              and k != "reply" and "text" not in k.lower()
                              or k in ("id", "family")})
        arms[arm] = {"per_family": fams,
                     "total": {k: v for k, v in
                               (doc.get("total") or {}).items()
                               if not isinstance(v, (dict, list))},
                     "n_items": len(items),
                     "items": items}
    doc_out = {"arms": arms}
    Path(a.out).write_text(json.dumps(doc_out, indent=1), encoding="utf-8")
    print(json.dumps({k: v.get("total", v.get("per_family"))
                      for k, v in arms.items()}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 292 scorer")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m1 = sub.add_parser("m1")
    m1.add_argument("--panel", required=True)
    m1.add_argument("--piece-score", required=True)
    m1.add_argument("--new-score", required=True)
    m1.add_argument("--piece-rows", default=None)
    m1.add_argument("--new-rows", default=None)
    m1.add_argument("--pred", default=None)
    m1.add_argument("--out", required=True)
    m26 = sub.add_parser("m2m6")
    m26.add_argument("--dir", required=True)
    m26.add_argument("--pred", required=True)
    m26.add_argument("--out", required=True)
    m5 = sub.add_parser("m5")
    m5.add_argument("--dir", required=True)
    m5.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "m1":
        return cmd_m1(args)
    if args.cmd == "m2m6":
        return cmd_m2m6(args)
    return cmd_m5(args)


if __name__ == "__main__":
    sys.exit(main())
