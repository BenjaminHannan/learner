"""Exp 251 scorer.

  dev   --cases dev251.jsonl --mine ROWS --base ROWS           -> M2
  panel --panel-dir artifacts/claude-askpanel243-20260922
        --mine ROWS --base ROWS (same-session base228 arm)     -> M1a-f, M5
  panel --schema-only                                          -> schema check only

Panel scoring implements askpanel243-schema.txt exactly:
  right (ANSWER): every gold part ("A; B") appears in the reply
    (case-insensitive) AND the reply does not start with "I don't know" /
    "I do not know".
  wrong value: the reply contains a value from stated_facts (third element)
    that is neither a gold part nor in allowed_mentions (ABSTAIN items: any
    stated value); case-insensitive whole words.
  question write: stored after the question != stored after the setup.
  control: reply byte-identical to base228.jsonl base_reply.
Schema check on load: every file present, exactly the listed fields, the 10
families with exact counts, the exact expect label per family, 124 ids
matching across both files in the same order (plus the gold / twin /
allowed_mentions null-or-list rules the schema states). Any mismatch ->
prints SCHEMA-MISMATCH and exits 3 with no verdict (VOID).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

LABEL = "(worked out backwards)"
PANEL_FIELDS = {"id", "family", "setup", "question", "twin_question", "gold",
                "expect", "stated_facts", "note", "allowed_mentions"}
BASE_FIELDS = {"id", "base_setup_replies", "stored_after_setup", "base_reply",
               "stored_after_question", "twin_reply", "base_right",
               "twin_right"}
FAMILY_COUNTS = {"compose": 16, "no_apos": 16, "whats": 12,
                 "first_person": 12, "verb_subject": 12, "my_relation": 16,
                 "direction": 10, "combo": 8, "control": 12, "untaught": 10}
FAMILY_EXPECT = {"compose": "ANSWER", "no_apos": "ANSWER", "whats": "ANSWER",
                 "first_person": "ANSWER", "verb_subject": "ANSWER",
                 "my_relation": "ANSWER", "combo": "ANSWER",
                 "direction": "ABSTAIN", "untaught": "ABSTAIN",
                 "control": "UNCHANGED"}
NULL_TWIN = {"direction", "control", "untaught"}
NULL_GOLD = {"direction", "untaught"}
ANSWER_GUARD = ("compose", "no_apos", "whats", "first_person",
                "verb_subject", "my_relation")


def _has(reply: str, value: str) -> bool:
    v = str(value).strip()
    if not v:
        return False
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])",
                     reply, re.IGNORECASE) is not None


def _declines(reply: str) -> bool:
    r = reply.lstrip().lower()
    return r.startswith("i don't know") or r.startswith("i do not know")


def _gold_parts(gold) -> list[str]:
    if gold is None:
        return []
    if isinstance(gold, list):
        return [str(g).strip() for g in gold if str(g).strip()]
    return [p.strip() for p in str(gold).split(";") if p.strip()]


def wrong_values(reply: str, facts, gold_parts, allowed, abstain: bool):
    ok = {g.lower() for g in gold_parts} | {a.lower() for a in allowed}
    out = []
    for f in facts:
        v = str(f[2])
        if not abstain and v.lower() in ok:
            continue
        if _has(reply, v) and v not in out:
            out.append(v)
    return out


def right_answer(reply: str, gold_parts) -> bool:
    return (all(g.lower() in reply.lower() for g in gold_parts)
            and not _declines(reply))


def _load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _rows(path: str) -> dict:
    return {r["id"]: r for r in _load(Path(path))}


# ------------------------------------------------------------ schema check
def schema_check(pdir: Path):
    errs = []
    for name in ("panel.jsonl", "base228.jsonl", "README.md",
                 "SEAL.sha256.txt"):
        if not (pdir / name).is_file():
            errs.append(f"missing file {name}")
    if errs:
        return None, None, errs
    try:
        panel = _load(pdir / "panel.jsonl")
        base = _load(pdir / "base228.jsonl")
    except Exception as e:  # noqa: BLE001
        return None, None, [f"unreadable jsonl: {e}"]
    if len(panel) != 124:
        errs.append(f"panel.jsonl has {len(panel)} lines, want 124")
    if len(base) != 124:
        errs.append(f"base228.jsonl has {len(base)} lines, want 124")
    want_ids = [f"q243-{i:03d}" for i in range(1, 125)]
    if [p.get("id") for p in panel] != want_ids:
        errs.append("panel ids are not q243-001..q243-124 in order")
    if [b.get("id") for b in base] != [p.get("id") for p in panel]:
        errs.append("base228 ids do not match panel ids in order")
    counts: dict[str, int] = {}
    for p in panel:
        if set(p) != PANEL_FIELDS:
            errs.append(f"{p.get('id')}: panel fields {sorted(set(p))}")
            continue
        fam = p["family"]
        counts[fam] = counts.get(fam, 0) + 1
        if fam not in FAMILY_EXPECT:
            errs.append(f"{p['id']}: unknown family {fam!r}")
            continue
        if p["expect"] != FAMILY_EXPECT[fam]:
            errs.append(f"{p['id']}: expect {p['expect']!r} for {fam}")
        if not isinstance(p["setup"], list) or not p["setup"]:
            errs.append(f"{p['id']}: setup not a non-empty list")
        if not isinstance(p["question"], str) \
                or not p["question"].rstrip().endswith("?"):
            errs.append(f"{p['id']}: question not a '?' string")
        if fam in NULL_TWIN and p["twin_question"] is not None:
            errs.append(f"{p['id']}: twin_question must be null for {fam}")
        if fam in NULL_GOLD:
            if p["gold"] is not None:
                errs.append(f"{p['id']}: gold must be null for {fam}")
            if p["allowed_mentions"] != []:
                errs.append(f"{p['id']}: allowed_mentions must be [] for "
                            f"{fam}")
        elif not isinstance(p["gold"], str) or not p["gold"].strip():
            errs.append(f"{p['id']}: gold must be a string for {fam}")
        if not isinstance(p["stated_facts"], list) or any(
                not isinstance(f, list) or len(f) != 3
                for f in p["stated_facts"]):
            errs.append(f"{p['id']}: stated_facts not a list of triples")
        if not isinstance(p["allowed_mentions"], list):
            errs.append(f"{p['id']}: allowed_mentions not a list")
    if counts != FAMILY_COUNTS:
        errs.append(f"family counts {counts} != {FAMILY_COUNTS}")
    for b in base:
        if set(b) != BASE_FIELDS:
            errs.append(f"{b.get('id')}: base228 fields {sorted(set(b))}")
        elif not isinstance(b["base_right"], bool):
            errs.append(f"{b['id']}: base_right not bool")
    return panel, base, errs


# ------------------------------------------------------------------- panel
def score_panel(pdir: Path, mine_p: str | None, base_p: str | None,
                schema_only: bool) -> int:
    panel, base, errs = schema_check(pdir)
    if errs:
        print("SCHEMA-MISMATCH")
        for e in errs[:40]:
            print("  " + e)
        return 3
    print("schema check OK (124 items, 10 families, labels, ids)")
    if schema_only:
        return 0
    mine, arm0 = _rows(mine_p), _rows(base_p)
    ids = [p["id"] for p in panel]
    if set(mine) != set(ids) or set(arm0) != set(ids):
        print("ROWS-INCOMPLETE: arm rows do not cover the 124 panel ids")
        return 4
    b228 = {b["id"]: b for b in base}
    fam_n: dict[str, list[int]] = {}
    wrong_items, qwrites, ctrl_bad, guard_bad, unt_bad = [], [], [], [], []
    dir_rows, combo_rows, deltas, arm0_diff = [], [], [], []
    lines = []
    for p in panel:
        i, fam = p["id"], p["family"]
        r = mine[i]
        reply = r["reply"]
        gp = _gold_parts(p["gold"])
        abstain = p["expect"] == "ABSTAIN"
        wv = wrong_values(reply, p["stated_facts"], gp,
                          p["allowed_mentions"], abstain)
        qw = r["stored_after_question"] != r["stored_after_setup"]
        if p["expect"] == "ANSWER":
            ok = right_answer(reply, gp) and not wv
        elif p["expect"] == "ABSTAIN":
            ok = not wv
        else:
            ok = reply == b228[i]["base_reply"]
        ok = ok and not qw
        c = fam_n.setdefault(fam, [0, 0])
        c[0] += int(ok)
        c[1] += 1
        if wv:
            wrong_items.append((i, fam, wv))
        if qw:
            qwrites.append(i)
        if fam == "control" and reply != b228[i]["base_reply"]:
            ctrl_bad.append(i)
        if fam in ANSWER_GUARD and b228[i]["base_right"] and not ok:
            guard_bad.append((i, fam))
        if fam == "untaught" and wv:
            unt_bad.append(i)
        if fam == "direction":
            dir_rows.append((i, ok, wv, reply))
        if fam == "combo":
            combo_rows.append((i, ok, wv, reply))
        if arm0[i]["reply"] != b228[i]["base_reply"]:
            arm0_diff.append(i)
        deltas.append(r["q_ms"] - arm0[i]["q_ms"])
        lines.append(f"{i} {fam:12s} {'RIGHT' if ok else 'miss '}"
                     f"{' WRONG=' + '|'.join(wv) if wv else ''}"
                     f"{' QWRITE' if qw else ''}  {reply!r}")
    print("\n".join(lines))
    print("\nper family (mine right / n; base228.jsonl base_right):")
    for fam in FAMILY_COUNTS:
        br = sum(1 for p in panel if p["family"] == fam
                 and b228[p["id"]]["base_right"])
        print(f"  {fam:12s} {fam_n[fam][0]:3d}/{fam_n[fam][1]:3d}   "
              f"base {br}/{fam_n[fam][1]}")
    d_ok = sum(1 for _i, ok, _w, _r in dir_rows if ok)
    med = statistics.median(deltas)
    marks = {
        "M1a direction right, no leak (bar 10/10)": (d_ok, 10, d_ok == 10),
        "M1b wrong values, all 124 (bar 0)": (len(wrong_items), 0,
                                              not wrong_items),
        "M1c question writes, all 124 (bar 0)": (len(qwrites), 0,
                                                 not qwrites),
        "M1d control byte-identical (bar 12/12)": (12 - len(ctrl_bad), 12,
                                                   not ctrl_bad),
        "M1e other families base_right->not right (bar 0)":
            (len(guard_bad), 0, not guard_bad),
        "M1e untaught no stored value (bar 10/10)": (10 - len(unt_bad), 10,
                                                     not unt_bad),
    }
    print("\nMARKS")
    for k, (got, bar, ok) in marks.items():
        print(f"  {k}: {got}  {'PASS' if ok else 'FAIL'}")
    m5 = med <= 5.0
    print(f"  M5 median added ms/question (bar <= +5): {med:+.2f}  "
          f"{'PASS' if m5 else 'FAIL'}")
    print(f"\nwrong-value items: {wrong_items}")
    print(f"question writes: {qwrites}")
    print(f"control not identical: {ctrl_bad}")
    print(f"guard (base_right -> not right): {guard_bad}")
    print("M1f combo (no bar): " + "; ".join(
        f"{i} {'RIGHT' if ok else 'miss'}{' WRONG=' + '|'.join(w) if w else ''}"
        for i, ok, w, _r in combo_rows))
    print(f"same-session base arm replies differing from base228.jsonl: "
          f"{len(arm0_diff)} {arm0_diff}")
    allok = all(ok for _g, _b, ok in marks.values()) and m5
    print(f"\nM1+M5 VERDICT: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1


# --------------------------------------------------------------------- dev
def score_dev(cases_p: str, mine_p: str, base_p: str) -> int:
    cases = _load(Path(cases_p))
    mine, arm0 = _rows(mine_p), _rows(base_p)
    by: dict[str, list[int]] = {}
    misses, qws, setup_mm = [], [], []
    for c in cases:
        i, k = c["id"], c["kind"]
        r = mine[i]
        reply = r["reply"]
        gp = _gold_parts(c["gold"])
        abstain = k in ("direction", "trap")
        wv = wrong_values(reply, c["stated_facts"], gp,
                          c["allowed_mentions"], abstain)
        wv += [f for f in c.get("forbid", []) if _has(reply, f)]
        qw = r["stored_after_question"] != r["stored_after_setup"]
        if sorted(map(tuple, c["stated_facts"])) != sorted(
                map(tuple, arm0[i]["stored_after_setup"])):
            setup_mm.append(i)
        if k in ("direction", "trap"):
            ok = not wv
        elif k == "inverse":
            ok = right_answer(reply, gp) and LABEL in reply and not wv
        else:  # mustnot
            ok = (reply == arm0[i]["reply"] and right_answer(reply, gp)
                  and not wv)
        ok = ok and not qw
        if qw:
            qws.append(i)
        b = by.setdefault(k, [0, 0])
        b[0] += int(ok)
        b[1] += 1
        base_wv = wrong_values(arm0[i]["reply"], c["stated_facts"], gp,
                               c["allowed_mentions"], abstain)
        print(f"{i} {k:9s} {'RIGHT' if ok else 'MISS '}"
              f"{' WRONG=' + '|'.join(wv) if wv else ''}"
              f"{' QWRITE' if qw else ''} | {c['question']!r} -> {reply!r}"
              f"   [base: {arm0[i]['reply'][:70]!r}"
              f"{' LEAK' if abstain and base_wv else ''}]")
        if not ok:
            misses.append(i)
    print("\nM2 dev marks:")
    for k, (a, n) in by.items():
        print(f"  {k:9s} {a}/{n}")
    print(f"  question writes: {len(qws)} {qws}")
    print(f"  setup stored != stated_facts: {len(setup_mm)} {setup_mm}")
    ok = not misses and not qws and not setup_mm
    print(f"M2 VERDICT: {'PASS' if ok else 'FAIL'} (misses {misses})")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "panel"])
    ap.add_argument("--cases")
    ap.add_argument("--panel-dir",
                    default="artifacts/claude-askpanel243-20260922")
    ap.add_argument("--mine")
    ap.add_argument("--base")
    ap.add_argument("--schema-only", action="store_true")
    a = ap.parse_args(argv)
    if a.mode == "dev":
        return score_dev(a.cases, a.mine, a.base)
    return score_panel(Path(a.panel_dir), a.mine, a.base, a.schema_only)


if __name__ == "__main__":
    sys.exit(main())
