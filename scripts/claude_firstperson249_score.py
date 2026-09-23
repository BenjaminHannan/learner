#!/usr/bin/env python3
"""Exp 249 scorer (dev249 + ask panel 243), rules from askpanel243-schema.

right (ANSWER): every gold part ("A; B" -> A and B) appears in the reply
  (case-insensitive) AND the reply does not start with "I don't know" /
  "I do not know".
wrong value: the reply contains a stated value (whole word, case-insensitive)
  that is neither a gold part nor in allowed_mentions; for ABSTAIN items any
  stated value.
question write: active triples after the question != after the setup.
control: reply byte-identical to base228.jsonl base_reply.

Panel mode checks the 243 schema BEFORE scoring anything; any mismatch ->
prints SCHEMA-MISMATCH and exits 3 (VOID, no verdict).

Usage:
  python -B scripts/claude_firstperson249_score.py dev --cases dev249.jsonl --rows rows.jsonl
  python -B scripts/claude_firstperson249_score.py panel --panel-dir DIR --rows rows.jsonl
  python -B scripts/claude_firstperson249_score.py schema --panel-dir DIR
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12,
                 "first_person": 12, "verb_subject": 12, "my_relation": 16,
                 "direction": 10, "combo": 8, "control": 12, "untaught": 10}
FAMILY_ORDER = list(FAMILY_COUNTS)
EXPECT = {f: "ANSWER" for f in ("compose", "no_apos", "whats", "first_person",
                                "verb_subject", "my_relation", "combo")}
EXPECT.update({"direction": "ABSTAIN", "untaught": "ABSTAIN",
               "control": "UNCHANGED"})
PANEL_FIELDS = {"id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"}
BASE_FIELDS = {"id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"}
PANEL_FILES = ("panel.jsonl", "base228.jsonl", "README.md",
               "SEAL.sha256.txt")
MY_FAMILY = "first_person"


def _mismatch(msg: str):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def _load_jsonl(path: Path) -> list[dict]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(),
                             1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            _mismatch(f"{path.name} line {n} is not JSON ({exc})")
        if not isinstance(obj, dict):
            _mismatch(f"{path.name} line {n} is not an object")
        out.append(obj)
    return out


def check_panel_schema_or_exit(panel_dir) -> tuple[list[dict], list[dict]]:
    pdir = Path(panel_dir)
    for name in PANEL_FILES:
        if not (pdir / name).is_file():
            _mismatch(f"missing file {name}")
    panel = _load_jsonl(pdir / "panel.jsonl")
    base = _load_jsonl(pdir / "base228.jsonl")
    if len(panel) != 124 or len(base) != 124:
        _mismatch(f"line counts panel={len(panel)} base228={len(base)} "
                  "(need 124 each)")
    counts: dict[str, int] = {}
    last_block = -1
    for k, it in enumerate(panel):
        if set(it) != PANEL_FIELDS:
            _mismatch(f"panel item {k + 1} fields {sorted(it)}")
        want_id = f"q243-{k + 1:03d}"
        if it["id"] != want_id:
            _mismatch(f"panel item {k + 1} id {it['id']!r} != {want_id}")
        fam = it["family"]
        if fam not in FAMILY_COUNTS:
            _mismatch(f"{it['id']} unknown family {fam!r}")
        block = FAMILY_ORDER.index(fam)
        if block < last_block:
            _mismatch(f"{it['id']} family blocks out of order")
        last_block = block
        counts[fam] = counts.get(fam, 0) + 1
        if it["expect"] != EXPECT[fam]:
            _mismatch(f"{it['id']} expect {it['expect']!r} for {fam}")
        if (not isinstance(it["setup"], list) or not it["setup"]
                or not all(isinstance(s, str) for s in it["setup"])):
            _mismatch(f"{it['id']} setup must be a non-empty list of str")
        if (not isinstance(it["question"], str)
                or not it["question"].rstrip().endswith("?")):
            _mismatch(f"{it['id']} question must be a str ending in '?'")
        tq = it["twin_question"]
        if fam in ("direction", "control", "untaught"):
            if tq is not None:
                _mismatch(f"{it['id']} twin_question must be null for {fam}")
        elif not isinstance(tq, str):
            _mismatch(f"{it['id']} twin_question must be a str for {fam}")
        gold = it["gold"]
        if fam in ("direction", "untaught"):
            if gold is not None:
                _mismatch(f"{it['id']} gold must be null for {fam}")
        elif not isinstance(gold, str) or not gold.strip():
            _mismatch(f"{it['id']} gold must be a non-empty str for {fam}")
        sf = it["stated_facts"]
        if not isinstance(sf, list) or not all(
                isinstance(t, list) and len(t) == 3
                and all(isinstance(x, str) for x in t) for t in sf):
            _mismatch(f"{it['id']} stated_facts must be [[s,r,v],...]")
        if not isinstance(it["note"], str):
            _mismatch(f"{it['id']} note must be a str")
        am = it["allowed_mentions"]
        if not isinstance(am, list) or not all(isinstance(x, str)
                                               for x in am):
            _mismatch(f"{it['id']} allowed_mentions must be a list of str")
        if fam in ("direction", "untaught") and am:
            _mismatch(f"{it['id']} allowed_mentions must be [] for {fam}")
    if counts != FAMILY_COUNTS:
        _mismatch(f"family counts {counts} != {FAMILY_COUNTS}")
    for k, (it, b) in enumerate(zip(panel, base)):
        if set(b) != BASE_FIELDS:
            _mismatch(f"base228 line {k + 1} fields {sorted(b)}")
        if b["id"] != it["id"]:
            _mismatch(f"base228 line {k + 1} id {b['id']!r} != {it['id']!r}")
        if not isinstance(b["base_reply"], str):
            _mismatch(f"{b['id']} base_reply must be a str")
        if not isinstance(b["base_right"], bool):
            _mismatch(f"{b['id']} base_right must be bool")
        if b["twin_right"] is not None and not isinstance(b["twin_right"],
                                                          bool):
            _mismatch(f"{b['id']} twin_right must be bool or null")
        if (b["twin_reply"] is None) != (it["twin_question"] is None):
            _mismatch(f"{b['id']} twin_reply null-ness != twin_question")
        for fld in ("base_setup_replies", "stored_after_setup",
                    "stored_after_question"):
            if not isinstance(b[fld], list):
                _mismatch(f"{b['id']} {fld} must be a list")
    return panel, base


# ------------------------------------------------------------ scoring rules
def gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def _has_word(reply: str, value: str) -> bool:
    v = value.strip().rstrip(".")
    if not v:
        return False
    return re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", reply,
                     re.IGNORECASE) is not None


def is_decline(reply: str) -> bool:
    r = reply.lstrip().lower().replace("’", "'")
    return r.startswith("i don't know") or r.startswith("i do not know")


def is_right(reply: str, gold) -> bool:
    parts = gold_parts(gold)
    return (bool(parts) and all(p.lower() in reply.lower() for p in parts)
            and not is_decline(reply))


def wrong_values(reply: str, stated_values, gold, allowed, expect) -> list:
    ok = set()
    if expect != "ABSTAIN":
        ok = {p.lower() for p in gold_parts(gold)}
        ok |= {a.strip().lower() for a in (allowed or [])}
    out = []
    for v in sorted(set(stated_values)):
        if v.strip().lower() in ok:
            continue
        if _has_word(reply, v):
            out.append(v)
    return out


def q_write(rec: dict) -> bool:
    a = sorted(map(tuple, rec.get("stored_after_setup") or []))
    b = sorted(map(tuple, rec.get("stored_after_question") or []))
    return a != b


def _med(xs):
    return statistics.median(xs) if xs else float("nan")


# ------------------------------------------------------------------ panel
def score_panel(panel_dir, rows_path) -> int:
    panel, base = check_panel_schema_or_exit(panel_dir)
    rows = {r["id"]: r for r in _load_jsonl(Path(rows_path))}
    missing = [it["id"] for it in panel if it["id"] not in rows]
    if missing:
        print(f"ROWS-INCOMPLETE: {len(missing)} missing, e.g. {missing[:3]}")
        return 4
    per = []
    fam_right: dict[str, list[int]] = {}
    wrong_all, writes_all, ctrl_same = [], [], 0
    m1e_bad, leaks_new, leaks_old, untaught_ok = [], [], [], 0
    base_repro = 0
    diffs = []
    for it, b in zip(panel, base):
        r = rows[it["id"]]
        mine, arm_b = r["loop249"], r["base228"]
        reply = mine["reply"]
        fam, exp = it["family"], it["expect"]
        stated = [t[2] for t in it["stated_facts"]]
        wv = wrong_values(reply, stated, it["gold"], it["allowed_mentions"],
                          exp)
        wr = q_write(mine)
        right = (is_right(reply, it["gold"]) if exp == "ANSWER"
                 else (reply == b["base_reply"]) if exp == "UNCHANGED"
                 else not wv)
        if arm_b["reply"] == b["base_reply"]:
            base_repro += 1
        diffs.append(mine["q_ms"] - arm_b["q_ms"])
        if wv:
            wrong_all.append((it["id"], wv))
        if wr:
            writes_all.append(it["id"])
        fam_right.setdefault(fam, [0, 0])
        fam_right[fam][1] += 1
        fam_right[fam][0] += int(right)
        if fam == "control" and reply == b["base_reply"]:
            ctrl_same += 1
        if fam == "untaught" and not wv:
            untaught_ok += 1
        if fam == "direction":
            bleak = wrong_values(b["base_reply"], stated, None, [], "ABSTAIN")
            new = [v for v in wv if v not in bleak]
            if new:
                leaks_new.append((it["id"], new))
            if bleak:
                leaks_old.append((it["id"], bleak))
        if fam not in (MY_FAMILY, "combo", "control") and b["base_right"]:
            if exp == "ANSWER" and not right:
                m1e_bad.append((it["id"], "lost right answer"))
            if exp == "ABSTAIN" and wv and fam != "direction":
                m1e_bad.append((it["id"], "now gives a value"))
        per.append({"id": it["id"], "family": fam, "question": it["question"],
                    "gold": it["gold"], "base_right": b["base_right"],
                    "right": right, "wrong_values": wv, "q_write": wr,
                    "same_as_base228": reply == b["base_reply"],
                    "reply": reply, "base228_reply": b["base_reply"],
                    "q_ms": round(mine["q_ms"], 2),
                    "base_ms": round(arm_b["q_ms"], 2)})
    fr = fam_right.get(MY_FAMILY, [0, 0])
    m1a = fr[0] * 10 >= 9 * fr[1] and fr[1] == 12
    m1b = not wrong_all
    m1c = not writes_all
    m1d = ctrl_same == 12
    m1e = (not m1e_bad) and untaught_ok == 10 and not leaks_new
    m5_val = _med(diffs)
    m5 = m5_val <= 5.0
    print("PANEL 243 (schema OK)")
    for fam in FAMILY_ORDER:
        rr = fam_right.get(fam, [0, 0])
        print(f"  family {fam:13s} right {rr[0]:3d}/{rr[1]}")
    print(f"M1a {MY_FAMILY} right {fr[0]}/{fr[1]} (bar >= 90%): "
          f"{'PASS' if m1a else 'FAIL'}")
    print(f"M1b wrong values {len(wrong_all)} {wrong_all}: "
          f"{'PASS' if m1b else 'FAIL'}")
    print(f"M1c question writes {len(writes_all)} {writes_all}: "
          f"{'PASS' if m1c else 'FAIL'}")
    print(f"M1d control byte-identical {ctrl_same}/12: "
          f"{'PASS' if m1d else 'FAIL'}")
    print(f"M1e base_right->wrong/decline {len(m1e_bad)} {m1e_bad}; "
          f"untaught no value {untaught_ok}/10; direction new leaks "
          f"{leaks_new}; base228 leaks (listed, not counted) {leaks_old}: "
          f"{'PASS' if m1e else 'FAIL'}")
    combo = [(p["id"], p["right"], p["wrong_values"]) for p in per
             if p["family"] == "combo"]
    print(f"M1f combo per item (no bar): {combo}")
    print(f"M5 median(loop249 - base228) question ms = {m5_val:.2f} "
          f"(bar <= +5): {'PASS' if m5 else 'FAIL'}")
    print(f"info: own base228 arm reply == base228.jsonl base_reply "
          f"{base_repro}/124")
    moves = [p for p in per if not p["same_as_base228"]]
    print(f"moves vs base228.jsonl: {len(moves)}")
    for p in moves:
        print(f"  MOVE {p['id']} [{p['family']}] {p['question']!r}: "
              f"{p['base228_reply']!r} -> {p['reply']!r}")
    for p in per:
        if p["family"] == MY_FAMILY and not p["right"]:
            print(f"  MISS {p['id']} {p['question']!r} -> {p['reply']!r}")
    out = Path(rows_path).with_name("panel-scored.jsonl")
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n"
                           for p in per), encoding="utf-8")
    ok = m1a and m1b and m1c and m1d and m1e and m5
    print(f"PANEL MARKS: {'PASS' if ok else 'FAIL'}")
    return 0


# -------------------------------------------------------------------- dev
def score_dev(cases_path, rows_path) -> int:
    cases = _load_jsonl(Path(cases_path))
    rows = {r["id"]: r for r in _load_jsonl(Path(rows_path))}
    counts = {}
    bad = []
    writes = 0
    diffs = []
    for c in cases:
        r = rows[c["id"]]
        mine, b = r["loop249"], r["base228"]
        reply = mine["reply"]
        stated = [t[2] for t in b.get("all_after_setup") or []]
        stated += [t[2] for t in mine.get("all_after_setup") or []]
        wv = wrong_values(reply, stated, c["gold"], [], c["expect"])
        wr = q_write(mine)
        writes += int(wr)
        if c["expect"] == "ANSWER":
            ok = is_right(reply, c["gold"]) and not wv
        elif c["expect"] == "UNCHANGED":
            ok = reply == b["reply"] and not wv
        else:
            ok = not wv
        ok = ok and not wr
        fam = c["family"]
        counts.setdefault(fam, [0, 0])
        counts[fam][1] += 1
        counts[fam][0] += int(ok)
        diffs.append(mine["q_ms"] - b["q_ms"])
        moved = reply != b["reply"]
        tag = "ok " if ok else "BAD"
        print(f"{tag} {c['id']} [{fam}] {c['question']!r} -> {reply!r}"
              + (f"  (base228: {b['reply']!r})" if moved else "  (same)")
              + (f" WRONG={wv}" if wv else ""))
        if not ok:
            bad.append(c["id"])
    for fam, (a, n) in counts.items():
        print(f"dev {fam}: {a}/{n}")
    print(f"dev question writes: {writes}")
    print(f"dev median(loop249 - base228) question ms: {_med(diffs):.2f}")
    ok = not bad and writes == 0
    print(f"M2 DEV: {'PASS' if ok else 'FAIL'} (bad: {bad})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "panel", "schema"])
    ap.add_argument("--cases", default=None)
    ap.add_argument("--rows", default=None)
    ap.add_argument("--panel-dir", default=None)
    a = ap.parse_args(argv)
    if a.mode == "schema":
        check_panel_schema_or_exit(a.panel_dir)
        print("SCHEMA OK")
        return 0
    if a.mode == "panel":
        return score_panel(a.panel_dir, a.rows)
    return score_dev(a.cases, a.rows)


if __name__ == "__main__":
    sys.exit(main())
