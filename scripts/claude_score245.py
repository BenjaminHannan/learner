#!/usr/bin/env python3
"""Exp 245 scorer: dev cases (M2) and the ask panel 243 (M1a-M1f, M5).

  dev:   python -B scripts/claude_score245.py dev  --cases DEV.jsonl --rows ROWS.jsonl
  panel: python -B scripts/claude_score245.py panel --panel-dir artifacts/claude-askpanel243-20260922 --rows ROWS.jsonl
  check: python -B scripts/claude_score245.py check --panel-dir artifacts/claude-askpanel243-20260922

ROWS.jsonl comes from scripts/claude_run245.py (both arms: base228, fix245).
Panel rules = askpanel243-schema.txt. Schema check runs on load; any
mismatch prints SCHEMA-MISMATCH and exits 3 with no verdict (VOID).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

PANEL_FIELDS = {"id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"}
BASE_FIELDS = {"id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"}
FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12, "first_person": 12,
                 "verb_subject": 12, "my_relation": 16, "direction": 10,
                 "combo": 8, "control": 12, "untaught": 10}
EXPECT = {f: "ANSWER" for f in ("compose", "no_apos", "whats", "first_person",
                                "verb_subject", "my_relation", "combo")}
EXPECT.update({"direction": "ABSTAIN", "untaught": "ABSTAIN",
               "control": "UNCHANGED"})
FILES = ("panel.jsonl", "base228.jsonl", "README.md", "SEAL.sha256.txt")
MY_FAMILY = "my_relation"


# ------------------------------------------------------------ shared rules
def gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def is_decline(reply: str) -> bool:
    r = reply.strip().lower()
    return r.startswith("i don't know") or r.startswith("i do not know") \
        or r.startswith("i don’t know")


def is_right(reply: str, gold) -> bool:
    parts = gold_parts(gold)
    if not parts:
        return False
    low = reply.lower()
    return all(p.lower() in low for p in parts) and not is_decline(reply)


def has_word(reply: str, value: str) -> bool:
    v = str(value).strip()
    if not v:
        return False
    return re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", reply,
                     re.IGNORECASE) is not None


def wrong_values(reply: str, facts, gold, allowed, abstain: bool) -> list[str]:
    ok = set() if abstain else {p.lower() for p in gold_parts(gold)}
    ok |= {str(a).lower() for a in (allowed or [])} if not abstain else set()
    out = []
    for f in facts:
        v = str(f[2])
        if v.lower() in ok:
            continue
        if has_word(reply, v) and v not in out:
            out.append(v)
    return out


def wrote(row) -> bool:
    return sorted(map(tuple, row["stored_after_setup"])) != sorted(
        map(tuple, row["stored_after_question"]))


def load_rows(path) -> dict:
    rows: dict = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows.setdefault(r["arm"], {})[r["id"]] = r
    return rows


# ------------------------------------------------------------ schema check
def schema_mismatch(msg: str):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load_panel(pdir: Path):
    for f in FILES:
        if not (pdir / f).is_file():
            schema_mismatch(f"missing file {f}")
    try:
        panel = [json.loads(x) for x in (pdir / "panel.jsonl").read_text()
                 .splitlines() if x.strip()]
        base = [json.loads(x) for x in (pdir / "base228.jsonl").read_text()
                .splitlines() if x.strip()]
    except Exception as exc:  # noqa: BLE001
        schema_mismatch(f"unreadable jsonl ({exc})")
    if len(panel) != 124 or len(base) != 124:
        schema_mismatch(f"line counts {len(panel)}/{len(base)} != 124")
    for i, (p, b) in enumerate(zip(panel, base), 1):
        if set(p) != PANEL_FIELDS:
            schema_mismatch(f"panel line {i} fields {sorted(set(p) ^ PANEL_FIELDS)}")
        if set(b) != BASE_FIELDS:
            schema_mismatch(f"base228 line {i} fields {sorted(set(b) ^ BASE_FIELDS)}")
        if p["id"] != f"q243-{i:03d}" or b["id"] != p["id"]:
            schema_mismatch(f"id mismatch at line {i}: {p['id']} / {b['id']}")
        fam = p["family"]
        if fam not in FAMILY_COUNTS:
            schema_mismatch(f"unknown family {fam!r} at {p['id']}")
        if p["expect"] != EXPECT[fam]:
            schema_mismatch(f"expect {p['expect']!r} for family {fam} at {p['id']}")
        if not isinstance(p["setup"], list) or not p["setup"]:
            schema_mismatch(f"empty setup at {p['id']}")
        if not str(p["question"]).endswith("?"):
            schema_mismatch(f"question without '?' at {p['id']}")
        if EXPECT[fam] == "ANSWER" and not gold_parts(p["gold"]):
            schema_mismatch(f"ANSWER item without gold at {p['id']}")
        if not isinstance(p["stated_facts"], list) or not isinstance(
                p["allowed_mentions"], list):
            schema_mismatch(f"stated_facts/allowed_mentions not lists at {p['id']}")
        if not isinstance(b["base_right"], bool):
            schema_mismatch(f"base_right not bool at {p['id']}")
    counts = Counter(p["family"] for p in panel)
    if dict(counts) != FAMILY_COUNTS:
        schema_mismatch(f"family counts {dict(counts)}")
    return panel, base


# ------------------------------------------------------------ panel scoring
def score_panel(pdir: Path, rows_path: str) -> int:
    panel, base = load_panel(pdir)
    rows = load_rows(rows_path)
    fix, b228 = rows.get("fix245", {}), rows.get("base228", {})
    missing = [p["id"] for p in panel if p["id"] not in fix or p["id"] not in b228]
    if missing:
        print(f"ROWS-INCOMPLETE: {len(missing)} ids missing, e.g. {missing[:3]}")
        return 4
    bb = {b["id"]: b for b in base}
    fam_right = Counter()
    wrong_items, writes, ctrl_diff, m1e_bad, leaks_new, leaks_old = \
        [], [], [], [], [], []
    untaught_ok = 0
    items_out = []
    for p in panel:
        r = fix[p["id"]]
        reply = r["reply"]
        fam, exp = p["family"], p["expect"]
        abstain = exp == "ABSTAIN"
        wv = wrong_values(reply, p["stated_facts"], p["gold"],
                          p["allowed_mentions"], abstain)
        right = is_right(reply, p["gold"]) if exp == "ANSWER" else None
        b = bb[p["id"]]
        base_wv = wrong_values(b["base_reply"], p["stated_facts"], p["gold"],
                               p["allowed_mentions"], abstain)
        rec = {"id": p["id"], "family": fam, "question": p["question"],
               "reply": reply, "base_reply": b["base_reply"],
               "base_right": b["base_right"], "right": right,
               "wrong_values": wv, "wrote": wrote(r),
               "changed": reply != b["base_reply"]}
        if exp == "ANSWER" and right:
            fam_right[fam] += 1
        if wrote(r):
            writes.append(p["id"])
        if fam == "direction" and wv:
            if base_wv:
                leaks_old.append(p["id"])  # base228 already leaks: listed
            else:
                leaks_new.append(p["id"])
                wrong_items.append(p["id"])
        elif wv:
            wrong_items.append(p["id"])
        if fam == "control" and reply != b["base_reply"]:
            ctrl_diff.append(p["id"])
        if fam == "untaught" and not wv:
            untaught_ok += 1
        if fam not in (MY_FAMILY, "control", "combo") and b["base_right"]:
            if exp == "ANSWER" and (not right):
                m1e_bad.append(p["id"])
            if abstain and wv and not (fam == "direction" and base_wv):
                m1e_bad.append(p["id"])
        items_out.append(rec)
    n_my = FAMILY_COUNTS[MY_FAMILY]
    need = -(-9 * n_my // 10)  # ceil(0.9 * n)
    fq = [fix[p["id"]]["q_ms"] for p in panel]
    bq = [b228[p["id"]]["q_ms"] for p in panel]
    added = statistics.median([a - c for a, c in zip(fq, bq)])
    base_repro = sum(1 for p in panel
                     if b228[p["id"]]["reply"] == bb[p["id"]]["base_reply"])
    marks = {
        "M1a": (fam_right[MY_FAMILY] >= need,
                f"{MY_FAMILY} right {fam_right[MY_FAMILY]}/{n_my} (bar {need})"),
        "M1b": (not wrong_items, f"wrong-value items {len(wrong_items)}/124 {wrong_items}"),
        "M1c": (not writes, f"question writes {len(writes)}/124 {writes}"),
        "M1d": (not ctrl_diff, f"control byte-identical {12 - len(ctrl_diff)}/12 {ctrl_diff}"),
        "M1e": (not m1e_bad and untaught_ok == 10 and not leaks_new,
                f"other-family regressions {len(m1e_bad)} {m1e_bad}; untaught no-value "
                f"{untaught_ok}/10; new direction leaks {len(leaks_new)} {leaks_new}; "
                f"base228 leaks listed {len(leaks_old)} {leaks_old}"),
        "M5": (added <= 5.0, f"median added ms/question {added:+.2f} (bar +5.00)"),
    }
    print("PER-FAMILY right (ANSWER families), fix245 / base228.jsonl base_right:")
    for fam in FAMILY_COUNTS:
        if EXPECT[fam] == "ANSWER":
            br = sum(1 for p in panel if p["family"] == fam and bb[p["id"]]["base_right"])
            print(f"  {fam:13s} {fam_right[fam]:3d}/{FAMILY_COUNTS[fam]}   base {br}/{FAMILY_COUNTS[fam]}")
    print("M1f combo items (no bar):")
    for rec in items_out:
        if rec["family"] == "combo":
            print(f"  {rec['id']} right={rec['right']} wrong={rec['wrong_values']} "
                  f"{rec['question']!r} -> {rec['reply']!r}")
    print("CHANGED replies vs base228.jsonl:")
    for rec in items_out:
        if rec["changed"]:
            print(f"  {rec['id']} [{rec['family']}] {rec['question']!r}\n"
                  f"     base: {rec['base_reply']!r}\n     245 : {rec['reply']!r}"
                  f"  right={rec['right']} wrong={rec['wrong_values']}")
    print(f"base228 arm reproduced base228.jsonl base_reply: {base_repro}/124")
    for k, (ok, msg) in marks.items():
        print(f"{k} {'PASS' if ok else 'FAIL'}: {msg}")
    verdict = all(ok for ok, _ in marks.values())
    print(f"PANEL VERDICT (M1a-M1e, M5): {'PASS' if verdict else 'FAIL'}")
    out = Path(rows_path).with_suffix(".scored.json")
    out.write_text(json.dumps({"items": items_out,
                               "marks": {k: [ok, m] for k, (ok, m) in marks.items()}},
                              indent=1))
    return 0


# ------------------------------------------------------------ dev scoring
def score_dev(cases_path: str, rows_path: str) -> int:
    cases = [json.loads(x) for x in Path(cases_path).read_text().splitlines()
             if x.strip()]
    rows = load_rows(rows_path)
    fix, b228 = rows.get("fix245", {}), rows.get("base228", {})
    tally = Counter()
    bad = []
    writes = 0
    for c in cases:
        r, b = fix[c["id"]], b228[c["id"]]
        reply = r["reply"]
        facts = r["stored_after_setup"]
        if wrote(r):
            writes += 1
        if c["kind"] == "fix":
            wv = wrong_values(reply, facts, c["gold"], c["allowed_mentions"], False)
            ok = is_right(reply, c["gold"]) and not wv
        elif c["kind"] == "keep":
            wv = []
            ok = reply == b["reply"]
        else:
            wv = wrong_values(reply, facts, None, [], True)
            ok = not wv
        tally[(c["kind"], ok)] += 1
        flag = "ok " if ok else "BAD"
        print(f"{flag} {c['id']} {c['question']!r}\n    base: {b['reply']!r}\n"
              f"    245 : {reply!r} wrong={wv} wrote={wrote(r)}")
        if not ok:
            bad.append(c["id"])
    for kind in ("fix", "keep", "trap"):
        n = tally[(kind, True)] + tally[(kind, False)]
        print(f"{kind}: {tally[(kind, True)]}/{n}")
    print(f"question writes: {writes}")
    verdict = not bad and writes == 0
    print(f"DEV VERDICT (M2): {'PASS' if verdict else 'FAIL'} {bad}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "panel", "check"])
    ap.add_argument("--cases")
    ap.add_argument("--rows")
    ap.add_argument("--panel-dir", default="artifacts/claude-askpanel243-20260922")
    args = ap.parse_args(argv)
    if args.mode == "dev":
        return score_dev(args.cases, args.rows)
    if args.mode == "check":
        load_panel(Path(args.panel_dir))
        print("SCHEMA-OK")
        return 0
    return score_panel(Path(args.panel_dir), args.rows)


if __name__ == "__main__":
    sys.exit(main())
