#!/usr/bin/env python3
"""Exp 230b scorer (sealed with PASSMARKS).

  --panel                 score artifacts/claude-namecheck230b-20260922/panel-rows.json (M1)
  --smoke NEW.json        compare a sleep-smoke report with 230's smoke230.json (M4)
  --rt DIR                compare DIR/rt136-rows.json, DIR/rt143-rows.json with 230's saved rows
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent
ART = REPO / "artifacts" / "claude-namecheck230b-20260922"
ART230 = REPO / "artifacts" / "claude-yesprefix230-20260922"
YES_PREFIX = "Yes. Your name is "


def _get(d, keys, default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d:
            return d[k]
    return default


def _last_reply(r) -> str | None:
    v = _get(r, ("reply", "base_reply", "r230", "reply230", "replies",
                 "answer", "output"))
    if v is None:
        return None
    if isinstance(v, list):
        v = v[-1] if v else ""
        if isinstance(v, list):
            v = " ".join(v)
        if isinstance(v, dict):
            v = _get(v, ("reply", "text"), "")
    return str(v).strip()


def score_panel(rows_path: Path | None = None,
                score_path: Path | None = None) -> int:
    import claude_loop230b_agent as B
    rows_path = rows_path or (ART / "panel-rows.json")
    score_path = score_path or (ART / "panel-score.json")
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    out = {"items": len(rows), "false_yes": 0, "question_writes": 0,
           "NO_base_yes": 0, "NO_fixed": 0, "YES_total": 0, "YES_kept": 0,
           "UNCHANGED_total": 0, "UNCHANGED_identical": 0,
           "UNCHANGED_identical_live230": 0, "base_file_mismatch": 0,
           "rule_ok": 0, "other_labels": {}}
    detail = []
    for r in rows:
        exp = str(r["expect"]).strip().upper()
        last = r["per"][-1]
        rep = " ".join(last["r230b"]).strip()
        live230 = " ".join(last["r230"]).strip()
        base = _last_reply(r.get("base_row"))
        stored = last["stored"]
        asked = B.asked_name(last["turn"])
        fy = rep.startswith("Yes") and (
            not stored or exp == "NO"
            or (asked is not None and not B.same_name(asked, stored)))
        out["false_yes"] += int(fy)
        out["question_writes"] += sum(p["writes230b"] for p in r["per"]
                                      if p["turn"].strip().endswith("?"))
        out["rule_ok"] += int(all(p["ok"] for p in r["per"])
                              and r["facts_same"])
        if base is not None and base != live230:
            out["base_file_mismatch"] += 1
        note = ""
        if exp == "NO":
            b = base if base is not None else live230
            if b.startswith(YES_PREFIX):
                out["NO_base_yes"] += 1
                ok = rep.startswith("No.") and bool(stored) and \
                    rep == B.NO_NAME_FMT % stored
                out["NO_fixed"] += int(ok)
                note = "fixed" if ok else "NOT FIXED"
        elif exp == "YES":
            out["YES_total"] += 1
            ok = rep.startswith("Yes")
            out["YES_kept"] += int(ok)
            note = "kept" if ok else "LOST YES"
        elif exp in ("UNCHANGED", "SAME"):
            out["UNCHANGED_total"] += 1
            ok = rep == (base if base is not None else live230)
            out["UNCHANGED_identical"] += int(ok)
            out["UNCHANGED_identical_live230"] += int(rep == live230)
            note = "identical" if ok else "CHANGED"
        else:
            out["other_labels"][exp] = out["other_labels"].get(exp, 0) + 1
        detail.append({"id": r["id"], "expect": exp, "turn": last["turn"],
                       "stored": stored, "base230": base, "live230": live230,
                       "r230b": rep, "moved": rep != live230,
                       "false_yes": fy, "note": note})
    score_path.write_text(json.dumps(
        {"summary": out, "detail": detail}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    for d in detail:
        flag = "MOVED" if d["moved"] else "     "
        print(f"{d['id']:<10} {d['expect']:<10} {flag} {d['turn']!r} "
              f"230={d['live230']!r} 230b={d['r230b']!r} {d['note']}"
              + (" FALSE-YES" if d["false_yes"] else ""))
    print(json.dumps(out))
    return 0


def score_smoke(path: str) -> int:
    a = json.loads((ART230 / "smoke230.json").read_text(encoding="utf-8"))
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    skip = {"agent", "config", "label", "seconds"}
    diff = sorted(k for k in set(a) | set(b)
                  if k not in skip and a.get(k) != b.get(k))
    print(json.dumps({"smoke_identical": not diff, "differing_keys": diff}))
    return 0


def score_rt(d: str) -> int:
    res = {}
    for s in ("rt136", "rt143"):
        def load(p):
            txt = Path(p).read_text(encoding="utf-8")
            try:
                obj = json.loads(txt)
                rows = obj["rows"] if isinstance(obj, dict) else obj
            except json.JSONDecodeError:
                rows = [json.loads(ln) for ln in txt.splitlines()
                        if ln.strip()]
            return {r["id"]: r for r in rows}
        old = load(ART230 / "suitediff-rt" / f"{s}-rows.json")
        new = load(Path(d) / f"{s}-rows.json")
        moves = [i for i in old if i not in new or any(
            old[i].get(k) != new[i].get(k)
            for k in ("reply", "verdict", "stored"))]
        res[s] = {"n": len(old), "n_new": len(new), "moves_vs_230": moves}
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--panel"]:
        if len(a) == 3:  # self-test: ROWS OUT
            sys.exit(score_panel(Path(a[1]), Path(a[2])))
        sys.exit(score_panel())
    if a[:1] == ["--smoke"]:
        sys.exit(score_smoke(a[1]))
    if a[:1] == ["--rt"]:
        sys.exit(score_rt(a[1]))
    print(__doc__)
