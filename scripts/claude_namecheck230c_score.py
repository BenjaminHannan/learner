#!/usr/bin/env python3
"""Exp 230c scorer (sealed with PASSMARKS).

  --schema PANEL_DIR           validate the blind-panel schema only
  --panel ROWS.json OUT.json   score M1 on rows from claude_namecheck230c_marks.py --panel
  --rt DIR                     rt136/rt143 rows in DIR vs 230b's saved rows
  --smoke NEW.json             sleep smoke vs 230b's smoke230b.json
Schema mismatch -> prints SCHEMA-MISMATCH and exits 3 (run VOID, no verdict).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent
ART230B = REPO / "artifacts" / "claude-namecheck230b-20260922"

PANEL_FIELDS = {"id", "family", "setup", "question", "expect", "gold_name",
                "note"}
BASE_FIELDS = {"id", "base_reply", "base_setup_replies", "stored",
               "base_yes"}
FAMILIES = {"mismatch", "match", "odd_mismatch", "odd_match", "untaught",
            "controls"}
EXPECTS = {"NO", "YES", "NOT_YES", "NOT_NO", "NOT_TOLD", "UNCHANGED"}
N_ITEMS = 54
_NO = re.compile(r"^No\b")


def schema_fail(msg: str) -> None:
    print(f"SCHEMA-MISMATCH: {msg}", flush=True)
    sys.exit(3)


def load_panel(panel_dir) -> tuple[list[dict], dict]:
    """Load + validate panel.jsonl and base230b.jsonl; exit 3 on mismatch."""
    d = Path(panel_dir)
    for f in ("panel.jsonl", "base230b.jsonl"):
        if not (d / f).is_file():
            schema_fail(f"missing file {f}")
    items, base = [], {}
    try:
        for ln in (d / "panel.jsonl").read_text(
                encoding="utf-8").splitlines():
            if ln.strip():
                items.append(json.loads(ln))
        brows = [json.loads(ln) for ln in (d / "base230b.jsonl").read_text(
            encoding="utf-8").splitlines() if ln.strip()]
    except json.JSONDecodeError as e:
        schema_fail(f"bad JSON: {e}")
    if len(items) != N_ITEMS:
        schema_fail(f"panel has {len(items)} items, expected {N_ITEMS}")
    ids = []
    for it in items:
        if not isinstance(it, dict) or set(it) != PANEL_FIELDS:
            schema_fail(f"panel fields {sorted(it) if isinstance(it, dict) else it}")
        if it["family"] not in FAMILIES:
            schema_fail(f"family {it['family']!r} on {it['id']}")
        if it["expect"] not in EXPECTS:
            schema_fail(f"expect {it['expect']!r} on {it['id']}")
        if not (isinstance(it["setup"], list)
                and all(isinstance(s, str) for s in it["setup"])):
            schema_fail(f"setup not a list of strings on {it['id']}")
        if not isinstance(it["question"], str):
            schema_fail(f"question not a string on {it['id']}")
        if not (it["gold_name"] is None or isinstance(it["gold_name"], str)):
            schema_fail(f"gold_name type on {it['id']}")
        if not isinstance(it["id"], str) or not it["id"].startswith("c230-"):
            schema_fail(f"id {it['id']!r}")
        ids.append(it["id"])
    if len(set(ids)) != len(ids):
        schema_fail("duplicate panel ids")
    for r in brows:
        if not isinstance(r, dict) or set(r) != BASE_FIELDS:
            schema_fail(f"base fields {sorted(r) if isinstance(r, dict) else r}")
        if not isinstance(r["base_yes"], bool):
            schema_fail(f"base_yes not bool on {r['id']}")
        if not isinstance(r["base_reply"], str):
            schema_fail(f"base_reply not a string on {r['id']}")
        if r["id"] in base:
            schema_fail(f"duplicate base id {r['id']}")
        base[r["id"]] = r
    if set(base) != set(ids):
        schema_fail("base230b ids differ from panel ids")
    return items, base


def score_panel(rows_path: str, out_path: str) -> int:
    rows = json.loads(Path(rows_path).read_text(encoding="utf-8"))
    o = {"items": len(rows), "M1a_yes_on_NO_NOTYES_NOTTOLD": 0,
         "M1b_no_on_YES_NOTNO": 0, "M1c_NO_total": 0, "M1c_NO_exact": 0,
         "M1d_YES_base_yes": 0, "M1d_YES_kept": 0, "YES_base_no_reported": 0,
         "M1e_UNCHANGED_total": 0, "M1e_UNCHANGED_identical": 0,
         "M1f_question_writes": 0, "base_file_mismatch_live230b": 0,
         "rule_ok": 0, "gold_vs_stored_mismatch": 0, "by_expect": {}}
    detail = []
    for r in rows:
        it, br = r["item"], r["base_row"]
        exp = it["expect"]
        q = r["per"][-1]
        rep = " ".join(q["r230c"]).strip()
        live = " ".join(q["r230b"]).strip()
        stored = q["stored"]
        base = br["base_reply"].strip()
        o["by_expect"][exp] = o["by_expect"].get(exp, 0) + 1
        o["base_file_mismatch_live230b"] += int(base != live)
        o["rule_ok"] += int(all(p["ok"] for p in r["per"]) and r["facts_same"])
        o["M1f_question_writes"] += q["writes230c"]
        if (it["gold_name"] or None) != (stored or None):
            o["gold_vs_stored_mismatch"] += 1
        note = ""
        if exp in ("NO", "NOT_YES", "NOT_TOLD") and rep.startswith("Yes"):
            o["M1a_yes_on_NO_NOTYES_NOTTOLD"] += 1
            note += " YES-ON-" + exp
        if exp in ("YES", "NOT_NO") and _NO.match(rep):
            o["M1b_no_on_YES_NOTNO"] += 1
            note += " NO-ON-" + exp
        if exp == "NO":
            o["M1c_NO_total"] += 1
            ok = bool(stored) and rep == "No. Your name is %s." % stored
            o["M1c_NO_exact"] += int(ok)
            note += " no-exact" if ok else " NOT-NO-EXACT"
        if exp == "YES":
            if br["base_yes"]:
                o["M1d_YES_base_yes"] += 1
                ok = rep.startswith("Yes")
                o["M1d_YES_kept"] += int(ok)
                note += " kept" if ok else " LOST-YES"
            else:
                o["YES_base_no_reported"] += 1
                note += " base_yes-false(reported)"
        if exp == "UNCHANGED":
            o["M1e_UNCHANGED_total"] += 1
            ok = rep == base
            o["M1e_UNCHANGED_identical"] += int(ok)
            note += " identical" if ok else " CHANGED"
        detail.append({"id": it["id"], "family": it["family"],
                       "expect": exp, "question": it["question"],
                       "stored": stored, "gold_name": it["gold_name"],
                       "base230b": base, "live230b": live, "r230c": rep,
                       "moved": rep != live, "note": note.strip()})
        print(f"{it['id']:<9} {it['family']:<12} {exp:<9} "
              f"{'MOVED' if rep != live else '     '} {it['question']!r} "
              f"230b={live!r} 230c={rep!r} {note.strip()}", flush=True)
    passed = {
        "M1a": o["M1a_yes_on_NO_NOTYES_NOTTOLD"] == 0,
        "M1b": o["M1b_no_on_YES_NOTNO"] == 0,
        "M1c": o["M1c_NO_exact"] == o["M1c_NO_total"],
        "M1d": o["M1d_YES_kept"] == o["M1d_YES_base_yes"],
        "M1e": o["M1e_UNCHANGED_identical"] == o["M1e_UNCHANGED_total"],
        "M1f": o["M1f_question_writes"] == 0,
    }
    o["passed"] = passed
    o["M1_PASS"] = all(passed.values())
    Path(out_path).write_text(json.dumps({"summary": o, "detail": detail},
                                         indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(o), flush=True)
    return 0


def _rows(p: Path) -> dict:
    txt = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(txt)
        rows = obj["rows"] if isinstance(obj, dict) else obj
    except json.JSONDecodeError:
        rows = [json.loads(ln) for ln in txt.splitlines() if ln.strip()]
    return {r["id"]: r for r in rows}


def score_rt(d: str) -> int:
    res = {}
    for s in ("rt136", "rt143"):
        old = _rows(ART230B / "suitediff-rt" / f"{s}-rows.json")
        new = _rows(Path(d) / f"{s}-rows.json")
        moves = [i for i in old if i not in new or any(
            old[i].get(k) != new[i].get(k)
            for k in ("reply", "verdict", "stored"))]
        res[s] = {"n": len(old), "n_new": len(new), "moves_vs_230b": moves}
    print(json.dumps(res))
    return 0


def score_smoke(path: str) -> int:
    a = json.loads((ART230B / "smoke230b.json").read_text(encoding="utf-8"))
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    skip = {"agent", "config", "label", "seconds"}
    diff = sorted(k for k in set(a) | set(b)
                  if k not in skip and a.get(k) != b.get(k))
    print(json.dumps({"smoke_identical": not diff, "differing_keys": diff}))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--schema"]:
        load_panel(a[1])
        print("schema OK")
        sys.exit(0)
    if a[:1] == ["--panel"]:
        sys.exit(score_panel(a[1], a[2]))
    if a[:1] == ["--rt"]:
        sys.exit(score_rt(a[1]))
    if a[:1] == ["--smoke"]:
        sys.exit(score_smoke(a[1]))
    print(__doc__)
    sys.exit(2)
