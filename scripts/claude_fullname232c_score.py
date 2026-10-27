#!/usr/bin/env python3
"""Exp 232c scorer (dev and blind panel; one scorer, both agents).

Usage:
  python -B scripts/claude_fullname232c_score.py --cases panel.jsonl \
      --base rows138i.jsonl --new rows232c.jsonl [--base2 R --new2 R] \
      [--base-panel base138i.jsonl] [--expect-counts multi=36,one=36,...] \
      --out score.json

SCHEMA CHECK FIRST (OPUS-RULES "Panel schema contract"): on any missing /
unexpected file, field, family or label, print "SCHEMA-MISMATCH: <why>" and
exit 3 with no verdict. Contract (director's 232c brief):
  panel line fields, exactly: id, family, pair, name_words, setup, question,
    gold, expect, stated_facts, note
  family in {multi, one, trap, stated_extra}; expect in {ANSWER, ABSTAIN,
    NO_WRITE}; pair "pNN" on multi/one (each pair = exactly one multi + one
    one), null otherwise; name_words int; setup list of str; question str or
    null; gold str or null (non-empty str when expect == ANSWER);
    stated_facts list of [str, str, str]; note str; trap stated_facts == [].
  base panel file (if given) fields, exactly: id, base_reply,
    base_setup_replies, stored; same id set as the panel.
  run rows (from claude_fullname232_run.py): same id set as the panel.

Per item:
  * wrong writes (non-trap items): every triple stored at any point in the
    item (last turn's cumulative `all`) that matches no stated_facts entry.
    Match: subject and value equal case-insensitively (spaces collapsed,
    trailing periods dropped); relation equal after the alias map
    (REL_ALIAS of the sealed 232 scorer + EXTRA_ALIAS below).
  * trap writes (family trap): every stored triple.
  * right (items with a question): 232's sealed rule with gold = the gold
    for ANSWER items and "" (abstain) otherwise: gold value(s) in the reply
    and no other value (other values: stated values + capitalised setup
    words not in the question, minus a stop list, as in 232).
    Items with no question: right = n/a.
  * stated_extra: value_answer = not right (a stated value or other setup
    name/value appears in the reply); saved = the stated fact was stored
    (reported, not scored).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_fullname232_score as S232  # noqa: E402 (sealed, read-only)

EXTRA_ALIAS = {
    "lives_in": "city", "live_in": "city", "living_in": "city",
    "works_at": "employer", "work_at": "employer", "works_for": "employer",
    "work_for": "employer", "speaks": "language", "speak": "language",
    "was_born_in": "place_of_birth", "born_in": "place_of_birth",
    "place_of_birth": "place_of_birth",
}
S232.REL_ALIAS.update(EXTRA_ALIAS)

PANEL_FIELDS = {"id", "family", "pair", "name_words", "setup", "question",
                "gold", "expect", "stated_facts", "note"}
BASE_FIELDS = {"id", "base_reply", "base_setup_replies", "stored"}
FAMILIES = {"multi", "one", "trap", "stated_extra"}
EXPECTS = {"ANSWER", "ABSTAIN", "NO_WRITE"}
PAIR_RE = re.compile(r"^p\d{2}$")


class SchemaMismatch(Exception):
    pass


def _need(cond: bool, why: str) -> None:
    if not cond:
        raise SchemaMismatch(why)


def read_jsonl(path: str, what: str) -> list[dict]:
    p = Path(path)
    _need(p.is_file(), f"{what}: file missing: {path}")
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise SchemaMismatch(f"{what}: line {i + 1} not JSON ({e})")
        _need(isinstance(row, dict), f"{what}: line {i + 1} not an object")
        out.append(row)
    _need(bool(out), f"{what}: empty")
    return out


def _is_str(x) -> bool:
    return isinstance(x, str)


def validate_panel(items: list[dict], counts: dict | None) -> None:
    ids = set()
    pairs: dict[str, list[str]] = {}
    fam_n = {f: 0 for f in FAMILIES}
    for it in items:
        keys = set(it)
        _need(keys == PANEL_FIELDS,
              f"panel item {it.get('id')!r}: fields missing "
              f"{sorted(PANEL_FIELDS - keys)} unexpected "
              f"{sorted(keys - PANEL_FIELDS)}")
        iid = it["id"]
        _need(_is_str(iid) and iid and iid not in ids,
              f"panel: bad or duplicate id {iid!r}")
        ids.add(iid)
        fam = it["family"]
        _need(fam in FAMILIES, f"{iid}: unexpected family {fam!r}")
        fam_n[fam] += 1
        _need(it["expect"] in EXPECTS,
              f"{iid}: unexpected expect {it['expect']!r}")
        _need(isinstance(it["name_words"], int)
              and not isinstance(it["name_words"], bool),
              f"{iid}: name_words not int")
        _need(isinstance(it["setup"], list)
              and all(_is_str(s) for s in it["setup"]),
              f"{iid}: setup not a list of strings")
        _need(it["question"] is None or _is_str(it["question"]),
              f"{iid}: question not str/null")
        _need(it["gold"] is None or _is_str(it["gold"]),
              f"{iid}: gold not str/null")
        if it["expect"] == "ANSWER":
            _need(_is_str(it["gold"]) and it["gold"].strip() != "",
                  f"{iid}: ANSWER item without gold")
            _need(_is_str(it["question"]),
                  f"{iid}: ANSWER item without question")
        _need(_is_str(it["note"]), f"{iid}: note not str")
        sf = it["stated_facts"]
        _need(isinstance(sf, list) and all(
            isinstance(t, list) and len(t) == 3 and all(_is_str(x) for x in t)
            for t in sf), f"{iid}: stated_facts not a list of 3 strings")
        if fam == "trap":
            _need(sf == [], f"{iid}: trap item states facts")
        if fam in ("multi", "one"):
            _need(_is_str(it["pair"]) and PAIR_RE.match(it["pair"]),
                  f"{iid}: {fam} item with bad pair {it['pair']!r}")
            pairs.setdefault(it["pair"], []).append(fam)
        else:
            _need(it["pair"] is None, f"{iid}: {fam} item with a pair")
    for pid, fams in pairs.items():
        _need(sorted(fams) == ["multi", "one"],
              f"pair {pid}: families {fams} (need one multi + one one)")
    if counts:
        for fam, n in counts.items():
            _need(fam in FAMILIES, f"--expect-counts: unknown family {fam}")
            _need(fam_n[fam] == n,
                  f"family {fam}: {fam_n[fam]} items, contract says {n}")
        _need(sum(fam_n.values()) == sum(counts.values()),
              f"panel has {sum(fam_n.values())} items, contract "
              f"{sum(counts.values())}")


def validate_base_panel(rows: list[dict], ids: set) -> None:
    seen = set()
    for r in rows:
        keys = set(r)
        _need(keys == BASE_FIELDS,
              f"base panel {r.get('id')!r}: fields missing "
              f"{sorted(BASE_FIELDS - keys)} unexpected "
              f"{sorted(keys - BASE_FIELDS)}")
        _need(r["id"] not in seen, f"base panel: duplicate id {r['id']}")
        seen.add(r["id"])
    _need(seen == ids, f"base panel ids differ from panel ids "
          f"(missing {sorted(ids - seen)[:5]}, extra {sorted(seen - ids)[:5]})")


def load_rows(path: str, ids: set, what: str) -> dict:
    rows = {r.get("id"): r for r in read_jsonl(path, what)}
    _need(set(rows) == ids, f"{what}: ids differ from panel ids")
    for k, r in rows.items():
        _need(isinstance(r.get("turns"), list), f"{what} {k}: no turns")
    return rows


def judge(it: dict, row: dict) -> dict:
    shim = {"id": it["id"], "setup": it["setup"],
            "question": it["question"] or "",
            "expect_writes": it["stated_facts"], "expect_nowrite": False,
            "gold": it["gold"] if it["expect"] == "ANSWER" else ""}
    base = S232.judge_item(shim, row)
    turns = row["turns"]
    ever = turns[-1]["all"] if turns else []
    stated = [tuple(t) for t in it["stated_facts"]]
    has_q = bool(it["question"]) and bool(turns) and \
        bool(turns[-1].get("is_question"))
    res = {"id": it["id"], "family": it["family"],
           "right": base["right"] if has_q else None,
           "others_hit": base["others_hit"], "reply": base["reply"],
           "replies": base["replies"]}
    if it["family"] == "trap":
        res["trap_writes"] = [list(f) for f in ever]
        res["wrong_writes"] = []
    else:
        res["trap_writes"] = []
        res["wrong_writes"] = [list(f) for f in ever if not any(
            S232.matches(f, e) for e in stated)]
    if it["family"] == "stated_extra":
        res["value_answer"] = bool(has_q and not base["right"])
        final = turns[-1]["active"] if turns else []
        res["stated_saved"] = all(any(S232.matches(f, e) for f in final)
                                  for e in stated)
    res["pass"] = (res["right"] is not False and not res["wrong_writes"]
                   and not res["trap_writes"])
    return res


def ms_list(rows) -> list[float]:
    return [t["ms"] for r in rows.values() for t in r["turns"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--base2", default=None)
    ap.add_argument("--new2", default=None)
    ap.add_argument("--base-panel", default=None)
    ap.add_argument("--expect-counts", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        items = read_jsonl(args.cases, "panel")
        counts = None
        if args.expect_counts:
            counts = {}
            for part in args.expect_counts.split(","):
                k, v = part.split("=")
                counts[k.strip()] = int(v)
        validate_panel(items, counts)
        ids = {it["id"] for it in items}
        if args.base_panel:
            validate_base_panel(read_jsonl(args.base_panel, "base panel"),
                                ids)
        base = load_rows(args.base, ids, "base rows")
        new = load_rows(args.new, ids, "new rows")
        b2 = load_rows(args.base2, ids, "base2 rows") if args.base2 else None
        n2 = load_rows(args.new2, ids, "new2 rows") if args.new2 else None
    except SchemaMismatch as e:
        print(f"SCHEMA-MISMATCH: {e}", flush=True)
        return 3
    res = {"base": {}, "new": {}}
    for it in items:
        res["base"][it["id"]] = judge(it, base[it["id"]])
        res["new"][it["id"]] = judge(it, new[it["id"]])
    fam = {f: [it for it in items if it["family"] == f] for f in FAMILIES}
    withq = [it for it in items if res["new"][it["id"]]["right"] is not None
             or res["base"][it["id"]]["right"] is not None]

    def cnt(side, group):
        return sum(1 for it in group if res[side][it["id"]]["right"])

    s = {"n_items": len(items)}
    s.update({f"n_{f}": len(v) for f, v in fam.items()})
    for side in ("base", "new"):
        s[f"{side}_right_multi"] = cnt(side, fam["multi"])
        s[f"{side}_right_one"] = cnt(side, fam["one"])
        s[f"{side}_right_all"] = cnt(side, items)
        s[f"{side}_wrong_writes"] = sum(
            len(res[side][it["id"]]["wrong_writes"]) for it in items)
        s[f"{side}_trap_writes"] = sum(
            len(res[side][it["id"]]["trap_writes"]) for it in items)
        s[f"{side}_stated_extra_value_answers"] = sum(
            1 for it in fam["stated_extra"]
            if res[side][it["id"]]["value_answer"])
        s[f"{side}_stated_extra_saved"] = sum(
            1 for it in fam["stated_extra"]
            if res[side][it["id"]]["stated_saved"])
        s[f"{side}_pass_items"] = sum(1 for it in items
                                      if res[side][it["id"]]["pass"])
    s["lost_right"] = [it["id"] for it in withq
                       if res["base"][it["id"]]["right"]
                       and not res["new"][it["id"]]["right"]]
    s["gained_right"] = [it["id"] for it in withq
                         if res["new"][it["id"]]["right"]
                         and not res["base"][it["id"]]["right"]]
    s["one_word_reply_diffs"] = [
        it["id"] for it in fam["one"]
        if res["base"][it["id"]]["replies"] != res["new"][it["id"]]["replies"]]
    s["reply_diffs_nonpair"] = [
        it["id"] for it in fam["trap"] + fam["stated_extra"]
        if res["base"][it["id"]]["replies"] != res["new"][it["id"]]["replies"]]
    s["new_misses"] = [it["id"] for it in items
                       if not res["new"][it["id"]]["pass"]]
    s["M1a_wrong0"] = s["new_wrong_writes"] == 0
    s["M1b_trap0"] = s["new_trap_writes"] == 0
    s["M1c_multi_vs_one"] = s["new_right_multi"] >= s["new_right_one"] - 2
    s["M1d_multi_gain"] = s["new_right_multi"] >= s["base_right_multi"] + 20
    s["M1e_no_lost"] = not s["lost_right"]
    s["M1f_one_identical"] = not s["one_word_reply_diffs"]
    s["M1g_extra_no_value"] = s["new_stated_extra_value_answers"] == 0
    s["M1"] = all(s[k] for k in (
        "M1a_wrong0", "M1b_trap0", "M1c_multi_vs_one", "M1d_multi_gain",
        "M1e_no_lost", "M1f_one_identical", "M1g_extra_no_value"))
    s["new_pass_rate"] = s["new_pass_items"] / max(1, len(items))
    b_ms, n_ms = ms_list(base), ms_list(new)
    if b2 is not None and n2 is not None:
        b_ms += ms_list(b2)
        n_ms += ms_list(n2)
        s["base_rerun_diff_ids"] = [
            k for k in base if [t["reply"] for t in b2[k]["turns"]] !=
            [t["reply"] for t in base[k]["turns"]]]
        s["new_rerun_diff_ids"] = [
            k for k in new if [t["reply"] for t in n2[k]["turns"]] !=
            [t["reply"] for t in new[k]["turns"]]]
        s["reruns_identical"] = not (s["base_rerun_diff_ids"]
                                     or s["new_rerun_diff_ids"])
    s["base_median_ms"] = statistics.median(b_ms)
    s["new_median_ms"] = statistics.median(n_ms)
    s["M5_delta_median_ms"] = s["new_median_ms"] - s["base_median_ms"]
    s["M5"] = s["M5_delta_median_ms"] <= 5.0
    Path(args.out).write_text(json.dumps({"summary": s, "items": res},
                                         indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(s, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
