#!/usr/bin/env python3
"""Exp 252 scorer (corrpanel252 schema, S/briefs/corrpanel252-schema.txt).

Panel mode (schema check FIRST; any mismatch -> prints SCHEMA-MISMATCH,
exits 3, no verdict = VOID):
  claude_corr252_score.py panel --panel-dir artifacts/claude-corrpanel252-20260922
      --mine rows252.jsonl --base rows138k.jsonl --out score.json
Dev mode (same scoring rules on dev252.jsonl; extra/restart checks too):
  claude_corr252_score.py dev --cases dev252.jsonl --mine A --base B --out S

Scoring rules (identical to the schema text; triples compared
case-insensitively on all three parts):
  store_ok    = expect_store <= S_turn, no expect_gone in S_turn,
                S_turn <= S_setup | expect_store  (no junk writes)
  followup_ok = gold set: every ";"-part in followup_reply (ci) and the
                reply does not start with "I don't know"/"I do not know";
                gold null: no expect_gone value in reply (whole word, ci)
  wrong value = followup_reply contains an expect_gone value (whole word)
  followup write = S_followup != S_turn
  right = store_ok and followup_ok and not followup write; control items
          also need turn_reply and followup_reply byte-identical to
          base138k's.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FAMILIES = {"verb_denial": 14, "possessive_denial": 10,
            "contextual_denial": 12, "contextual_correction": 14,
            "explicit_correction": 12, "unstored_denial": 8, "ambiguous": 6,
            "question_trap": 12, "control": 12}
PANEL_FIELDS = ["id", "family", "setup", "turn", "followup", "stated_facts",
                "expect_gone", "expect_store", "gold_followup", "note"]
BASE_FIELDS = ["id", "setup_replies", "stored_after_setup", "turn_reply",
               "stored_after_turn", "followup_reply",
               "stored_after_followup", "base_right", "base_wrong_value"]
FILES = ["panel.jsonl", "base138k.jsonl", "README.md", "SEAL.sha256.txt"]
BARS = {"verb_denial": 13, "possessive_denial": 9, "contextual_denial": 11,
        "contextual_correction": 13, "explicit_correction": 11}


class SchemaMismatch(Exception):
    pass


def _is_triple_list(x) -> bool:
    return isinstance(x, list) and all(
        isinstance(t, list) and len(t) == 3
        and all(isinstance(p, str) for p in t) for t in x)


def _load_jsonl(path: Path, fields: list[str]) -> list[dict]:
    rows = []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    for n, ln in enumerate(lines, 1):
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError as e:
            raise SchemaMismatch(f"{path.name} line {n}: not JSON ({e})")
        if not isinstance(obj, dict):
            raise SchemaMismatch(f"{path.name} line {n}: not an object")
        if sorted(obj) != sorted(fields):
            missing = sorted(set(fields) - set(obj))
            extra = sorted(set(obj) - set(fields))
            raise SchemaMismatch(f"{path.name} line {n}: fields missing "
                                 f"{missing} unexpected {extra}")
        rows.append(obj)
    return rows


def check_schema(panel_dir: Path) -> tuple[list[dict], list[dict], list[str]]:
    notes = []
    for f in FILES:
        if not (panel_dir / f).is_file():
            raise SchemaMismatch(f"missing file {f}")
    panel = _load_jsonl(panel_dir / "panel.jsonl", PANEL_FIELDS)
    base = _load_jsonl(panel_dir / "base138k.jsonl", BASE_FIELDS)
    if len(panel) != 100 or len(base) != 100:
        raise SchemaMismatch(f"line counts panel={len(panel)} "
                             f"base={len(base)} (need 100 each)")
    want_ids = [f"c252-{i:03d}" for i in range(1, 101)]
    if [p["id"] for p in panel] != want_ids:
        raise SchemaMismatch("panel ids are not c252-001..c252-100 in order")
    if [b["id"] for b in base] != want_ids:
        raise SchemaMismatch("base138k ids do not match panel ids/order")
    counts: dict[str, int] = {}
    for p in panel:
        fam = p["family"]
        if fam not in FAMILIES:
            raise SchemaMismatch(f"{p['id']}: unexpected family {fam!r}")
        counts[fam] = counts.get(fam, 0) + 1
        if not (isinstance(p["setup"], list) and p["setup"]
                and all(isinstance(s, str) for s in p["setup"])):
            raise SchemaMismatch(f"{p['id']}: setup must be a non-empty "
                                 "list of strings")
        for k in ("turn", "followup", "note"):
            if not isinstance(p[k], str):
                raise SchemaMismatch(f"{p['id']}: {k} must be a string")
        for k in ("stated_facts", "expect_gone", "expect_store"):
            if not _is_triple_list(p[k]):
                raise SchemaMismatch(f"{p['id']}: {k} must be a list of "
                                     "[s, r, v] strings")
        if not (p["gold_followup"] is None
                or isinstance(p["gold_followup"], str)):
            raise SchemaMismatch(f"{p['id']}: gold_followup must be "
                                 "string or null")
        if fam in ("question_trap", "unstored_denial", "ambiguous") \
                and p["expect_gone"] != []:
            raise SchemaMismatch(f"{p['id']}: expect_gone must be [] "
                                 f"for {fam}")
    if counts != FAMILIES:
        raise SchemaMismatch(f"family counts {counts} != {FAMILIES}")
    for b in base:
        for k in ("setup_replies",):
            if not (isinstance(b[k], list)
                    and all(isinstance(s, str) for s in b[k])):
                raise SchemaMismatch(f"{b['id']}: {k} must be list of str")
        for k in ("turn_reply", "followup_reply"):
            if not isinstance(b[k], str):
                raise SchemaMismatch(f"{b['id']}: {k} must be a string")
        for k in ("stored_after_setup", "stored_after_turn",
                  "stored_after_followup"):
            if not _is_triple_list(b[k]):
                raise SchemaMismatch(f"{b['id']}: {k} must be triples")
        for k in ("base_right", "base_wrong_value"):
            if not isinstance(b[k], bool):
                raise SchemaMismatch(f"{b['id']}: {k} must be bool")
    # family-block order: informational only (not in the listed checks)
    order = list(FAMILIES)
    fam_seq = [p["family"] for p in panel]
    blocks = [f for i, f in enumerate(fam_seq) if i == 0 or fam_seq[i - 1] != f]
    if blocks != order:
        notes.append(f"family blocks not in schema order: {blocks}")
    return panel, base, notes


# ------------------------------------------------------------------ scoring
def T(t) -> tuple:
    return tuple(str(x).strip().lower() for x in t)


def TS(x) -> set:
    return {T(t) for t in x}


def ww(needle: str, hay: str) -> bool:
    needle = str(needle).strip()
    if not needle:
        return False
    return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", hay,
                     re.IGNORECASE) is not None


def score_item(item: dict, row: dict, base_row: dict | None = None) -> dict:
    s_setup = TS(row["stored_after_setup"])
    s_turn = TS(row["stored_after_turn"])
    s_follow = TS(row["stored_after_followup"])
    exp_store, exp_gone = TS(item["expect_store"]), TS(item["expect_gone"])
    junk = sorted(s_turn - (s_setup | exp_store))
    store_ok = (exp_store <= s_turn and not (exp_gone & s_turn)
                and not junk)
    reply = row["followup_reply"]
    gone_vals = [t[2] for t in item["expect_gone"]]
    wrong_value = any(ww(v, reply) for v in gone_vals)
    gold = item["gold_followup"]
    if gold is not None:
        parts = [p.strip() for p in gold.split(";") if p.strip()]
        lead = reply.lstrip().lower().replace("’", "'")
        followup_ok = (all(p.lower() in reply.lower() for p in parts)
                       and not lead.startswith("i don't know")
                       and not lead.startswith("i do not know"))
    else:
        followup_ok = not wrong_value
    follow_write = s_follow != s_turn
    right = store_ok and followup_ok and not follow_write
    ident = None
    if item["family"] == "control":
        ident = (base_row is not None
                 and row["turn_reply"] == base_row["turn_reply"]
                 and row["followup_reply"] == base_row["followup_reply"])
        right = right and ident
    extra_ok = True
    for q, rep in zip(item.get("extra", []), row.get("extra_replies", [])):
        _question, must_not, must = (list(q) + [[], []])[:3]
        if any(ww(v, rep) for v in (must_not or [])):
            extra_ok = False
        if any(not ww(v, rep) for v in (must or [])):
            extra_ok = False
        if rep.lstrip().lower().startswith("crash"):
            extra_ok = False
    if item.get("extra"):
        end = TS(row.get("stored_end", row["stored_after_followup"]))
        if end != s_follow:
            extra_ok = False
        right = right and extra_ok
    return {"id": item["id"], "family": item["family"], "right": right,
            "store_ok": store_ok, "followup_ok": followup_ok,
            "wrong_value": wrong_value, "followup_write": follow_write,
            "junk": [list(t) for t in junk], "junk_write": bool(junk),
            "store_unchanged": s_turn == s_setup, "identical": ident,
            "extra_ok": extra_ok if item.get("extra") else None}


def score_arm(items, rows, base_rows) -> dict:
    by_id = {r["id"]: r for r in rows}
    base_by = {r["id"]: r for r in base_rows} if base_rows else {}
    per = [score_item(it, by_id[it["id"]], base_by.get(it["id"]))
           for it in items]
    fams: dict[str, list[int]] = {}
    for p in per:
        f = fams.setdefault(p["family"], [0, 0])
        f[0] += int(p["right"])
        f[1] += 1
    return {"per_item": per, "families": fams,
            "right": sum(p["right"] for p in per), "n": len(per),
            "wrong_values": sum(p["wrong_value"] for p in per),
            "junk_writes": sum(p["junk_write"] for p in per),
            "followup_writes": sum(p["followup_write"] for p in per)}


def trap_ok(arm: dict, fam: str) -> tuple[int, int]:
    xs = [p for p in arm["per_item"] if p["family"] == fam]
    return sum(p["right"] and p["store_unchanged"] for p in xs), len(xs)


def load_rows(path: str) -> list[dict]:
    return [json.loads(ln) for ln in
            Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["panel", "dev", "schema"])
    ap.add_argument("--panel-dir")
    ap.add_argument("--cases")
    ap.add_argument("--mine")
    ap.add_argument("--base")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    notes: list[str] = []
    if args.mode in ("panel", "schema"):
        try:
            items, base_panel, notes = check_schema(Path(args.panel_dir))
        except SchemaMismatch as e:
            print(f"SCHEMA-MISMATCH: {e}")
            return 3
        print("schema OK" + (f" (notes: {notes})" if notes else ""))
        if args.mode == "schema":
            return 0
        ref_rows = base_panel  # control identity is against base138k.jsonl
    else:
        items = load_rows(args.cases)
        ref_rows = load_rows(args.base)
        base_panel = None
    mine = score_arm(items, load_rows(args.mine), ref_rows)
    base = score_arm(items, load_rows(args.base), ref_rows)
    out = {"mode": args.mode, "schema_notes": notes, "mine": mine,
           "base": base}
    if base_panel is not None:
        # the writer's rows scored with the same function
        writer = score_arm(items, base_panel, base_panel)
        out["writer_base"] = {k: writer[k] for k in
                              ("families", "right", "wrong_values",
                               "junk_writes", "followup_writes")}
        out["writer_base_right_agrees"] = sum(
            p["right"] == b["base_right"]
            for p, b in zip(writer["per_item"], base_panel))
        out["writer_wrong_value_agrees"] = sum(
            p["wrong_value"] == b["base_wrong_value"]
            for p, b in zip(writer["per_item"], base_panel))
        out["my138k_vs_writer_identical_replies"] = sum(
            r["turn_reply"] == b["turn_reply"]
            and r["followup_reply"] == b["followup_reply"]
            and r["setup_replies"] == b["setup_replies"]
            for r, b in zip(load_rows(args.base), base_panel))
    if args.mode == "panel":
        m1a = {f: [mine["families"][f][0], mine["families"][f][1], bar,
                   mine["families"][f][0] >= bar] for f, bar in BARS.items()}
        qt, ab, un = (trap_ok(mine, "question_trap"),
                      trap_ok(mine, "ambiguous"),
                      trap_ok(mine, "unstored_denial"))
        ctl = mine["families"]["control"]
        marks = {
            "M1a": m1a,
            "M1a_pass": all(v[3] for v in m1a.values()),
            "M1b_wrong_values_mine": mine["wrong_values"],
            "M1b_wrong_values_base": base["wrong_values"],
            "M1b_pass": mine["wrong_values"] == 0,
            "M1c_junk_writes": mine["junk_writes"],
            "M1c_followup_writes": mine["followup_writes"],
            "M1c_question_trap": list(qt), "M1c_ambiguous": list(ab),
            "M1c_unstored_denial": list(un),
            "M1c_pass": (mine["junk_writes"] == 0
                         and mine["followup_writes"] == 0
                         and qt == (12, 12) and ab == (6, 6)
                         and un == (8, 8)),
            "M1d_control": ctl, "M1d_pass": ctl == [12, 12],
        }
        marks["M1_pass"] = all(marks[k] for k in
                               ("M1a_pass", "M1b_pass", "M1c_pass",
                                "M1d_pass"))
        out["marks"] = marks
        print(json.dumps(marks, indent=1))
    else:
        traps = [p for p in mine["per_item"] if p["family"] in
                 ("question_trap", "ambiguous", "unstored_denial")]
        m2 = {"right": mine["right"], "n": mine["n"],
              "junk_writes": mine["junk_writes"],
              "followup_writes": mine["followup_writes"],
              "wrong_values": mine["wrong_values"],
              "trap_writes": sum(not p["store_unchanged"] for p in traps),
              "restart_right": [sum(p["right"] for p in mine["per_item"]
                                    if p["family"] == "restart"),
                                sum(1 for p in mine["per_item"]
                                    if p["family"] == "restart")]}
        m2["M2_pass"] = (m2["right"] == m2["n"] and m2["junk_writes"] == 0
                         and m2["trap_writes"] == 0)
        out["marks"] = m2
        print(json.dumps(m2, indent=1))
    print("families mine:", json.dumps(mine["families"]))
    print("families base:", json.dumps(base["families"]))
    for p in mine["per_item"]:
        if not p["right"]:
            print("  MISS mine", json.dumps(p))
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1,
                                             ensure_ascii=False),
                                  encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
