#!/usr/bin/env python3
"""Exp 256 scorer -- the loop-panel-254 rules (looppanel254-spec.txt), used for
both the dev cases and (after the seal) panel 254.

Rules (spec + the panel writer's settled details):
* entities: case-insensitive after trimming edge punctuation and a leading
  the/a/an; {i, me, my, myself, mine, user} is one entity.
* relations: equal to gold or any relation_aliases after lower-casing and
  treating _ - space alike; PLUS (256 addition, applied to both arms) the
  canonical mapping of relation_table_v1 (name + aliases + storage_keys ->
  table name): stored and gold match if they map to the same table relation.
  --no-canon turns the addition off.
* store_ok, answer_ok, wrong_value (whole word, turn or followup reply),
  followup_write (store after followup != store after turn; computed from
  each arm's own run), right; no_save; control (+ byte-identical replies to
  base138l). Dev-only families: "fixed" (right = every reply byte-identical to
  the base arm AND the store after turn and followup identical to the base
  arm's), "restart" (T or A by note prefix, as casual).
* casual/control/restart T vs A: note starts with "T:" or "A:".
* strict schema check: exact fields in cases and rows, ids equal and in the
  same order; with --panel254 also the 8 families x exact counts (160).
  Any mismatch -> prints SCHEMA-MISMATCH, exit 3, no verdict.

usage: claude_ear256_score.py --cases C.jsonl --arm A.jsonl --base B.jsonl [--panel254] [--out S.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / "artifacts/claude-relationtable-20260922/relation_table_v1.json"

CASE_FIELDS = {"id", "family", "setup", "turn", "followup", "gold_store", "gold_answer", "must_not", "note"}
BASE254_FIELDS = {"id", "setup_replies", "stored_after_setup", "turn_reply", "stored_after_turn",
                  "followup_reply", "base_right", "base_wrong_value"}
ARM_FIELDS = {"id", "setup_replies", "stored_after_setup", "turn_reply", "stored_after_turn",
              "followup_reply", "stored_after_followup"}
FAM254 = {"teach_varied": 30, "ask_varied": 30, "both_varied": 20, "casual": 20, "backwards": 15,
          "chain": 15, "no_save": 20, "control": 10}
T_FAMS = {"teach_varied"}
A_FAMS = {"ask_varied", "backwards", "chain"}
FIRST = {"i", "me", "my", "myself", "mine", "user"}


def mismatch(msg):
    print("SCHEMA-MISMATCH:", msg)
    sys.exit(3)


def ent(x):
    s = str(x).strip().strip(".,;:!?\"'()[]").strip().lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return "me" if s in FIRST else s


def rnorm(r):
    return re.sub(r"[\s_\-]+", " ", str(r).lower()).strip()


def load_canon():
    t = json.loads(TABLE.read_text())
    m = {}
    for r in t["relations"]:
        for k in [r["name"]] + list(r.get("aliases", [])) + list(r.get("storage_keys", [])):
            m.setdefault(rnorm(k), r["name"])
    return m


def rel_ok(stored, gold, aliases, canon):
    s = rnorm(stored)
    if s in {rnorm(gold)} | {rnorm(a) for a in aliases}:
        return True
    if canon is not None:
        cs = canon.get(s)
        return cs is not None and any(cs == canon.get(rnorm(g)) for g in [gold] + list(aliases))
    return False


def fact_ok(tr, g, canon):
    s, r, v = tr
    return ent(s) == ent(g["subject"]) and ent(v) == ent(g["value"]) and \
        rel_ok(r, g["relation"], g.get("relation_aliases", []), canon)


def has_word(text, w):
    return bool(text) and re.search(r"(?<![\w])" + re.escape(w.lower()) + r"(?![\w])", text.lower()) is not None


def kind(it):
    f = it["family"]
    if f in T_FAMS:
        return "T"
    if f in A_FAMS:
        return "A"
    if f == "both_varied":
        return "B"
    if f == "no_save":
        return "N"
    if f == "fixed":
        return "F"
    n = it["note"].strip()
    if n.startswith("T:"):
        return "T"
    if n.startswith("A:"):
        return "A"
    return "?"


def score_item(it, row, base, canon):
    k = kind(it)
    tset = lambda xs: {tuple(x) for x in xs}  # noqa: E731
    s_setup, s_turn = tset(row["stored_after_setup"]), tset(row["stored_after_turn"])
    s_fu = tset(row["stored_after_followup"])
    tr, fr = row["turn_reply"] or "", row["followup_reply"] or ""
    wrong = any(has_word(tr, m) or has_word(fr, m) for m in it["must_not"])
    fu_write = s_fu != s_turn
    det = dict(kind=k, wrong_value=wrong, followup_write=fu_write)
    if k == "F":
        same = (row["setup_replies"] == base["setup_replies"] and tr == base["turn_reply"]
                and (row["followup_reply"] or None) == (base["followup_reply"] or None)
                and s_turn == tset(base["stored_after_turn"]))
        det.update(byte_identical=same, right=same)
        return det
    if k == "N":
        det["right"] = (s_turn == s_setup) and not wrong
        return det
    gold = it["gold_store"]
    have = all(any(fact_ok(t, g, canon) for t in s_turn) for g in gold)
    junk = [list(t) for t in s_turn - s_setup if not any(fact_ok(t, g, canon) for g in gold)]
    store_ok = have and not junk
    scored = fr if k == "T" else tr
    if it["gold_answer"] is not None:
        low = scored.lower()
        answer_ok = all(p.strip().lower() in low for p in it["gold_answer"].split(";")) and \
            not low.startswith(("i don't know", "i do not know"))
    else:
        answer_ok = not any(has_word(scored, m) for m in it["must_not"])
    right = store_ok and answer_ok and not wrong and not fu_write
    if it["family"] == "control":
        same = row["setup_replies"] == base["setup_replies"] and tr == base["turn_reply"] and \
            (row["followup_reply"] or None) == (base["followup_reply"] or None)
        det["byte_identical"] = same
        right = right and same
    det.update(store_ok=store_ok, answer_ok=answer_ok, junk=junk, right=right)
    return det


def load_jsonl(p, fields, what):
    try:
        rows = [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    except Exception as e:  # noqa: BLE001
        mismatch(f"{what}: {e!r}")
    for r in rows:
        if not fields <= set(r) or (what == "cases" and set(r) != fields):
            mismatch(f"{what} {r.get('id')}: fields {sorted(set(r) ^ fields)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--base", required=True, help="base arm rows (own run of 138l)")
    ap.add_argument("--base254", default=None, help="the sealed base138l.jsonl (schema + byte check)")
    ap.add_argument("--panel254", action="store_true")
    ap.add_argument("--no-canon", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    for p in [a.cases, a.arm, a.base] + ([a.base254] if a.base254 else []):
        if not Path(p).exists():
            mismatch(f"missing {p}")
    cases = load_jsonl(a.cases, CASE_FIELDS, "cases")
    arm = load_jsonl(a.arm, ARM_FIELDS, "arm")
    base = load_jsonl(a.base, ARM_FIELDS, "base")
    ids = [c["id"] for c in cases]
    for name, rows in (("arm", arm), ("base", base)):
        if [r["id"] for r in rows] != ids:
            mismatch(f"{name} ids differ from cases")
    if a.base254:
        b254 = load_jsonl(a.base254, BASE254_FIELDS, "base254")
        if any(set(r) != BASE254_FIELDS for r in b254) or [r["id"] for r in b254] != ids:
            mismatch("base138l.jsonl fields/ids")
        for r, own in zip(b254, base):
            if r["turn_reply"] != own["turn_reply"]:
                print("NOTE base138l.jsonl vs own base run differ on", r["id"])
    if a.panel254:
        cnt = defaultdict(int)
        for c in cases:
            cnt[c["family"]] += 1
        if dict(cnt) != FAM254 or len(cases) != 160:
            mismatch(f"family counts {dict(cnt)}")
        if ids != [f"l254-{i:03d}" for i in range(1, 161)]:
            mismatch("ids")
    canon = None if a.no_canon else load_canon()
    res = {"arm": {}, "base": {}}
    for c, ra, rb in zip(cases, arm, base):
        res["arm"][c["id"]] = score_item(c, ra, rb, canon)
        res["base"][c["id"]] = score_item(c, rb, rb, canon)
    fams = defaultdict(lambda: [0, 0, 0, 0, 0])  # n, arm right, base right, arm wrong_value, base wrong_value
    for c in cases:
        f = fams[c["family"]]
        f[0] += 1
        f[1] += res["arm"][c["id"]]["right"]
        f[2] += res["base"][c["id"]]["right"]
        f[3] += res["arm"][c["id"]]["wrong_value"]
        f[4] += res["base"][c["id"]]["wrong_value"]
    tot = [sum(f[i] for f in fams.values()) for i in range(5)]
    summ = dict(by_family={k: dict(n=v[0], arm_right=v[1], base_right=v[2], arm_wrong=v[3], base_wrong=v[4])
                           for k, v in fams.items()},
                total=dict(n=tot[0], arm_right=tot[1], base_right=tot[2], arm_wrong=tot[3], base_wrong=tot[4]),
                arm_fu_writes=sum(r["followup_write"] for r in res["arm"].values()),
                base_fu_writes=sum(r["followup_write"] for r in res["base"].values()),
                gained=[i for i in ids if res["arm"][i]["right"] and not res["base"][i]["right"]],
                lost=[i for i in ids if res["base"][i]["right"] and not res["arm"][i]["right"]],
                canon=not a.no_canon)
    print(json.dumps(summ, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(summary=summ, items=res), indent=1))


if __name__ == "__main__":
    main()
