#!/usr/bin/env python3
"""Exp 232 scorer (one scorer for dev and panel, both agents).

Usage:
  python -B scripts/claude_fullname232_score.py --cases C.jsonl \
      --base rows138i.jsonl --new rows232.jsonl [--base2 ... --new2 ...] \
      --out score.json

Per item (fresh notebook each item; rows from claude_fullname232_run.py):
  * wrong writes = active taught triples after the last turn that match no
    expect_writes entry, plus any triple first written on the question turn
    that matches no expect_writes entry.
  * trap writes (items with expect_nowrite truthy): bool -> every taught fact
    ever written (active or not) that matches no expect_writes entry;
    list -> every fact ever written that matches a listed entry.
  * right: gold value(s) appear in the question reply (case-insensitive,
    whole words) and no OTHER value does. Other values (never the gold,
    never text that appears in the question):
      answer items -> values of expect_nowrite entries, plus values of
        expected/written triples whose relation (alias map) is a relation
        some gold value is expected/written under (competing answers);
      abstain items (gold empty / an abstain token) -> values of every
        expected/forbidden/written triple plus capitalised setup words not
        in the question and not in a closed stop-list.
Triple match: subject and value equal after case/space/period normalising,
relation equal after the alias map (city/lives_in, employer/works_at/
works_for, language/speaks, place_of_birth/born_in; others as-is).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

REL_ALIAS = {
    "city": "city", "lives_in": "city", "live_in": "city", "lives": "city",
    "residence": "city", "home": "city", "home_city": "city",
    "employer": "employer", "works_at": "employer", "works_for": "employer",
    "work": "employer", "works": "employer", "employed_by": "employer",
    "workplace": "employer",
    "language": "language", "languages": "language", "speaks": "language",
    "speak": "language",
    "place_of_birth": "place_of_birth", "born_in": "place_of_birth",
    "born": "place_of_birth", "birthplace": "place_of_birth",
}
ABSTAIN_TOKENS = {"", "ABSTAIN", "NONE", "UNKNOWN", "NO ANSWER", "NO_ANSWER",
                  "DONT_KNOW", "IDK", "NULL", "N/A"}
STOP = {"Maybe", "Perhaps", "Probably", "Possibly", "Likely", "I", "Actually",
        "No", "Yes", "My", "The", "A", "An", "Someone", "Rumor", "Rumour",
        "Honestly", "So", "Well", "Ok", "Okay", "Oh", "Also", "Btw", "By",
        "Everyone", "They", "People", "Word", "According", "Apparently",
        "Reportedly", "Frankly", "Anyway", "He", "She", "It", "We", "You",
        "If", "When", "And", "But", "Or", "Who", "What", "Where", "Why",
        "How", "Does", "Do", "Is", "Was", "Saved", "Please", "Hi", "Hello",
        "Tell", "Say"}


def norm(s) -> str:
    s = " ".join(str(s).split()).strip()
    while s.endswith("."):
        s = s[:-1].rstrip()
    return s.casefold()


def canon_rel(r) -> str:
    k = norm(r).replace(" ", "_").replace("-", "_")
    return REL_ALIAS.get(k, k)


def parse_entry(e):
    """-> (subject, relation|None, value) or raise."""
    if isinstance(e, (list, tuple)):
        if len(e) == 3:
            return (e[0], e[1], e[2])
        if len(e) == 2:
            return (e[0], None, e[1])
    if isinstance(e, dict):
        def pick(*keys):
            for k in keys:
                if k in e and e[k] is not None:
                    return e[k]
            return None
        s = pick("s", "subject", "name", "head", "subj")
        r = pick("r", "relation", "rel", "predicate", "key")
        v = pick("o", "value", "object", "tail", "obj", "val")
        if s is not None and v is not None:
            return (s, r, v)
    if isinstance(e, str):
        for sep in ("|", "\t", ","):
            parts = [p.strip() for p in e.split(sep)]
            if len(parts) == 3 and all(parts):
                return tuple(parts)
    raise ValueError(f"unparseable triple entry: {e!r}")


def matches(fact, entry) -> bool:
    s, r, v = entry
    if norm(fact[0]) != norm(s) or norm(fact[2]) != norm(v):
        return False
    return r is None or canon_rel(fact[1]) == canon_rel(r)


def entries(x) -> list:
    if not x or isinstance(x, bool):
        return []
    if isinstance(x, (list, tuple)):
        return [parse_entry(e) for e in x]
    if isinstance(x, dict):
        return [parse_entry(x)]
    return []


def nowrite_mode(x):
    if isinstance(x, bool):
        return "all" if x else None
    if isinstance(x, (list, tuple, dict)):
        return "list" if x else None
    if isinstance(x, str):
        return "all" if x.strip().lower() in ("true", "yes", "1") else None
    return None


def gold_list(item) -> list[str]:
    g = item.get("gold")
    if g is None:
        return []
    if isinstance(g, (list, tuple)):
        return [str(x) for x in g if str(x).strip().upper()
                not in ABSTAIN_TOKENS]
    g = str(g)
    return [] if g.strip().upper() in ABSTAIN_TOKENS else [g]


def has_word(text: str, phrase: str, cs: bool = False) -> bool:
    flags = 0 if cs else re.IGNORECASE
    return re.search(r"(?<![\w'])" + re.escape(phrase.strip()) + r"(?![\w])",
                     text, flags) is not None


def judge_item(item, row) -> dict:
    turns = row["turns"]
    exp = entries(item.get("expect_writes"))
    q_turn = turns[-1] if turns and turns[-1].get("is_question") else None
    final_active = turns[-1]["active"] if turns else []
    ever = turns[-1]["all"] if turns else []
    wrong = [f for f in final_active if not any(matches(f, e) for e in exp)]
    if q_turn is not None and len(turns) >= 2:
        before = {tuple(x) for x in turns[-2]["all"]}
        for f in q_turn["all"]:
            if tuple(f) not in before and not any(matches(f, e) for e in exp) \
                    and f not in wrong:
                wrong.append(f)
    elif q_turn is not None:
        for f in q_turn["all"]:
            if not any(matches(f, e) for e in exp) and f not in wrong:
                wrong.append(f)
    mode = nowrite_mode(item.get("expect_nowrite"))
    trap = []
    if mode == "all":
        trap = [f for f in ever if not any(matches(f, e) for e in exp)]
    elif mode == "list":
        forb = entries(item.get("expect_nowrite"))
        trap = [f for f in ever if any(matches(f, e) for e in forb)]
    missing = [list(e) for e in exp
               if not any(matches(f, e) for f in final_active)]
    golds = gold_list(item)
    reply = q_turn["reply"] if q_turn else ""
    question = item.get("question") or ""
    golds_n = {norm(g) for g in golds}
    forb = entries(item.get("expect_nowrite"))
    pool = [(e[0], e[1], e[2]) for e in exp] + [tuple(f) for f in ever]
    others = {str(e[2]) for e in forb}
    use_caps = not golds
    if golds:
        gold_rels = {canon_rel(t[1]) for t in pool
                     if t[1] is not None and norm(t[2]) in golds_n}
        for t in pool:
            if t[1] is not None and canon_rel(t[1]) in gold_rels:
                others.add(str(t[2]))
    else:
        for t in pool:
            others.add(str(t[2]))
    setup_caps = set()
    if use_caps:
        for t in item.get("setup") or []:
            for w in re.findall(r"[A-Z][\w'\-]*", t):
                w = re.sub(r"'s$", "", w)
                if w not in STOP:
                    setup_caps.add(w)
    gold_words = {w.casefold() for g in golds for w in g.split()}
    others_hit = []
    for o in sorted(others):
        if norm(o) in golds_n or not o.strip():
            continue
        if has_word(question, o):
            continue
        if has_word(reply, o):
            others_hit.append(o)
    for w in sorted(setup_caps):
        if w.casefold() in gold_words or has_word(question, w, cs=True):
            continue
        if any(norm(w) == norm(o) for o in others_hit):
            continue
        if has_word(reply, w, cs=True):
            others_hit.append(w)
    gold_ok = all(has_word(reply, g) for g in golds)
    right = bool(q_turn) and gold_ok and not others_hit
    return {"id": item.get("id"), "right": right, "gold_ok": gold_ok,
            "others_hit": others_hit, "wrong_writes": wrong,
            "trap_writes": trap, "missing": missing, "reply": reply,
            "replies": [t["reply"] for t in turns],
            "abstain_item": not golds}


def load_rows(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def ms_list(rows) -> list[float]:
    return [t["ms"] for r in rows.values() for t in r["turns"]]


def is_multi(item) -> bool:
    try:
        return int(item.get("name_words") or 0) >= 2
    except (TypeError, ValueError):
        return False


def is_one(item) -> bool:
    try:
        return int(item.get("name_words") or 0) == 1
    except (TypeError, ValueError):
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--base2", default=None)
    ap.add_argument("--new2", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    items = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    base, new = load_rows(args.base), load_rows(args.new)
    res = {"base": {}, "new": {}}
    for it in items:
        res["base"][it["id"]] = judge_item(it, base[it["id"]])
        res["new"][it["id"]] = judge_item(it, new[it["id"]])
    paired = [it for it in items if it.get("pair") not in (None, "")]
    multi = [it for it in paired if is_multi(it)]
    one = [it for it in paired if is_one(it)]

    def cnt(side, group, key="right"):
        return sum(1 for it in group if res[side][it["id"]][key])

    s = {}
    s["n_items"] = len(items)
    s["n_multi"], s["n_one"] = len(multi), len(one)
    for side in ("base", "new"):
        s[f"{side}_right_all"] = cnt(side, items)
        s[f"{side}_right_multi"] = cnt(side, multi)
        s[f"{side}_right_one"] = cnt(side, one)
        s[f"{side}_wrong_writes"] = sum(
            len(res[side][it["id"]]["wrong_writes"]) for it in items)
        s[f"{side}_trap_writes"] = sum(
            len(res[side][it["id"]]["trap_writes"]) for it in items)
        s[f"{side}_missing_writes"] = sum(
            len(res[side][it["id"]]["missing"]) for it in items)
        s[f"{side}_pass_items"] = sum(
            1 for it in items if res[side][it["id"]]["right"]
            and not res[side][it["id"]]["wrong_writes"]
            and not res[side][it["id"]]["trap_writes"]
            and not res[side][it["id"]]["missing"])
    s["lost_right"] = [it["id"] for it in items if res["base"][it["id"]]
                       ["right"] and not res["new"][it["id"]]["right"]]
    s["one_word_reply_diffs"] = [
        it["id"] for it in one
        if res["base"][it["id"]]["replies"] != res["new"][it["id"]]["replies"]]
    s["trap_reply_diffs_vs_base"] = [
        it["id"] for it in items if it.get("pair") in (None, "")
        and res["base"][it["id"]]["replies"] != res["new"][it["id"]]["replies"]]
    s["trap_setup_reply_diffs_vs_base"] = [
        it["id"] for it in items if it.get("pair") in (None, "")
        and [t["reply"] for t in base[it["id"]]["turns"]
             if not t.get("is_question")] !=
        [t["reply"] for t in new[it["id"]]["turns"]
         if not t.get("is_question")]]
    s["M1_wrong0"] = s["new_wrong_writes"] == 0
    s["M1_trap0"] = s["new_trap_writes"] == 0
    s["M1_multi_vs_one"] = s["new_right_multi"] >= s["new_right_one"] - 2
    s["M1_multi_gain"] = s["new_right_multi"] >= s["base_right_multi"] + 20
    s["M1_no_lost"] = not s["lost_right"]
    s["M1_one_identical"] = not s["one_word_reply_diffs"]
    s["M1"] = all(s[k] for k in ("M1_wrong0", "M1_trap0", "M1_multi_vs_one",
                                 "M1_multi_gain", "M1_no_lost",
                                 "M1_one_identical"))
    s["new_pass_rate"] = s["new_pass_items"] / max(1, len(items))
    # Latency (pooled per-turn medians, all runs given).
    b_ms, n_ms = ms_list(base), ms_list(new)
    rep = {}
    if args.base2 and args.new2:
        b2, n2 = load_rows(args.base2), load_rows(args.new2)
        b_ms += ms_list(b2)
        n_ms += ms_list(n2)
        rep["base_rerun_identical"] = all(
            [t["reply"] for t in b2[k]["turns"]] ==
            [t["reply"] for t in base[k]["turns"]] for k in base)
        rep["new_rerun_identical"] = all(
            [t["reply"] for t in n2[k]["turns"]] ==
            [t["reply"] for t in new[k]["turns"]] for k in new)
        rep["base_rerun_diff_ids"] = [
            k for k in base if [t["reply"] for t in b2[k]["turns"]] !=
            [t["reply"] for t in base[k]["turns"]]]
        rep["new_rerun_diff_ids"] = [
            k for k in new if [t["reply"] for t in n2[k]["turns"]] !=
            [t["reply"] for t in new[k]["turns"]]]
    s.update(rep)
    s["base_median_ms"] = statistics.median(b_ms) if b_ms else None
    s["new_median_ms"] = statistics.median(n_ms) if n_ms else None
    s["base_mean_ms"] = statistics.fmean(b_ms) if b_ms else None
    s["new_mean_ms"] = statistics.fmean(n_ms) if n_ms else None
    if b_ms and n_ms:
        s["M5_delta_median_ms"] = s["new_median_ms"] - s["base_median_ms"]
        s["M5"] = s["M5_delta_median_ms"] <= 5.0
    out = {"summary": s, "items": res}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(s, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
