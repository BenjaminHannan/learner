#!/usr/bin/env python3
"""vread scorer (vector-reader thread, 2026-09-27): both arms, one code scorer, cards compared field by field.

A card is (owner, relation, value, state); state is current / correction / former. The LoRA arm's frame facts become
cards by mode (ASSERT -> current, CORRECT -> correction, FORMER -> former; other modes are no card), each with its
lis-300 confidence (lowest token probability). The vector arm writes cards directly (claude_vread_model.py read).

Save rule (both arms, per card, as the lis-318/319 panel scorers release facts):
  state current or correction, AND claude_lis300_compiler.check_fact passes (unchanged: owner "me" or a whole-word span of
  the turn or previous reply; value a whole-word span of the turn, or of an asked previous reply; relation in the
  table; owner not a pronoun), AND confidence >= the arm's save bar.
  "hist" variant (used for the backref family mark only, both arms alike): check_fact as widened by
  claude_lis319o_owner.check_fact_hist, where the owner may also be a whole-word span of the earlier turns the reader was
  shown (the last 6). The unchanged check can never save a backref fact: the lis-320 checks keep its owner out of the
  turn and the reply.
Right save: a saved card equal to an unused gold card of its row in all four fields: owner and value equal after
lower-casing and collapsing spaces, relation equal (or narrower, lis-300 table), state equal. One gold card per save.
Wrong save: any other saved card. Wrong turn: a row with at least one wrong save.

  python -B scripts/claude_vread_score.py score --rows DEV.cards.jsonl --reads READS.jsonl --arm lora|vector
         --bar T [--rule main|hist] --out OUT.json
  python -B scripts/claude_vread_score.py bar --rows CAL.cards.jsonl --reads CAL_READS.jsonl --out BAR.json
  python -B scripts/claude_vread_score.py verdict --lora L.json --vector V.json --lora-hist LH.json --vector-hist VH.json
         --out VERDICT.json
  python -B scripts/claude_vread_score.py selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis300_score import NARROWER  # noqa: E402
from claude_lis319o_owner import check_fact_hist, hist_text  # noqa: E402

HIST_TURNS = 6
MODE_STATE = {"ASSERT": "current", "CORRECT": "correction", "FORMER": "former"}
STATE_MODE = {"current": "ASSERT", "correction": "CORRECT", "former": "FORMER"}
SAVE_STATES = {"current", "correction"}
LOOK = {"question", "plan", "doubt", "someone_else", "hypothetical", "negation_only", "confirm", "ambiguous_pronoun"}
CORR = {"correct", "correct_ref"}
LORA_T = 0.995
BAR_GRID = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995, 0.998, 0.999]
BAR_MAX_WRONG_SHARE = 0.005


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(x):
    return " ".join(str(x or "").lower().split())


def lora_cards(read):
    fr = (read or {}).get("frame")
    if not isinstance(fr, dict):
        return None
    confs = list((read or {}).get("conf") or [])
    out = []
    for i, f in enumerate(fr.get("facts") or []):
        if not isinstance(f, dict) or MODE_STATE.get(f.get("mode")) is None:
            continue
        out.append({"owner": str(f.get("owner", "")), "rel": f.get("rel"), "value": str(f.get("value", "")),
                    "state": MODE_STATE[f["mode"]], "conf": confs[i] if i < len(confs) else 0.0})
    return out


def arm_cards(arm, read):
    if arm == "lora":
        return lora_cards(read)
    return None if read is None else [dict(c) for c in read.get("cards") or []]


def check(card, row, rule):
    f = {"owner": card["owner"], "rel": card["rel"], "value": card["value"], "mode": STATE_MODE[card["state"]]}
    if rule == "hist":
        return check_fact_hist(f, row["turn"], row.get("prev_reply", ""),
                               hist_text((row.get("history") or [])[-HIST_TURNS:]))
    return CMP.check_fact(f, row["turn"], row.get("prev_reply", ""))


def is_saved(card, row, bar, rule):
    return card["state"] in SAVE_STATES and card["conf"] >= bar and check(card, row, rule) is None


def same(c, g, state=True):
    rel_ok = c["rel"] == g["rel"] or c["rel"] in NARROWER.get(g["rel"], ())
    return (norm(c["owner"]) == norm(g["owner"]) and norm(c["value"]) == norm(g["value"]) and rel_ok
            and (not state or c["state"] == g["state"]))


def match_one(c, gold, used, **kw):
    for k, g in enumerate(gold):
        if k not in used and same(c, g, **kw):
            used.add(k)
            return k
    return None


def whole_word_ok(c, row):
    own_ok = c["owner"] == "me" or CMP.whole_word_span(c["owner"], row["prompt"])
    return own_ok and CMP.whole_word_span(c["value"], row["prompt"])


def score(rows, reads, arm, bar, rule="main"):
    rd = {r["id"]: r for r in reads}
    S = Counter({k: 0 for k in ("rows", "gold_cards", "gold_save_cards", "gold_savable_cards", "missing_reads",
                                "parse_fail", "saves", "right_saves", "wrong_saves", "wrong_turns", "former_as_current",
                                "cards_at_bar", "cards_text_not_whole_word", "cards_no_gold_same_rel_state",
                                "cards_words_right", "cards_owner_words_wrong", "cards_value_words_wrong")})
    fam = Counter({f"{f}:{x}": 0 for f in ("corrections", "backref", "former", "long_turns") for x in ("gold", "right")})
    fam.update({"lookalike:rows": 0, "lookalike:rows_with_save": 0, "lookalike:saves": 0, "long_turns:rows": 0})
    ms, rounds = [], []
    for row in rows:
        gold = [dict(g) for g in row["cards"]]
        read = rd.get(row["id"])
        S["rows"] += 1
        S["gold_cards"] += len(gold)
        S["gold_save_cards"] += sum(g["state"] in SAVE_STATES for g in gold)
        S["gold_savable_cards"] += sum(g["state"] in SAVE_STATES and check(dict(g, conf=1.0), row, rule) is None
                                       for g in gold)
        cards = arm_cards(arm, read)
        if read is None:
            S["missing_reads"] += 1
            cards = []
        elif cards is None:
            S["parse_fail"] += 1
            cards = []
        if read and "ms" in read:
            ms.append(read["ms"])
        if read and "rounds" in read:
            rounds.append(read["rounds"])
        long_turn = len(row["turn"].split()) > 20
        # saves
        used, wrong = set(), 0
        for c in cards:
            if not is_saved(c, row, bar, rule):
                continue
            S["saves"] += 1
            k = match_one(c, gold, used)
            if k is None:
                wrong += 1
                S["wrong_saves"] += 1
                if any(g["state"] == "former" and norm(c["owner"]) == norm(g["owner"])
                       and norm(c["value"]) == norm(g["value"]) for g in gold):
                    S["former_as_current"] += 1
                continue
            S["right_saves"] += 1
            g = gold[k]
            if g["state"] == "correction":
                fam["corrections:right"] += 1
            if row["family"] == "backref":
                fam["backref:right"] += 1
            if long_turn:
                fam["long_turns:right"] += 1
        S["wrong_turns"] += bool(wrong)
        if wrong:
            fam[f"wrong_turns_by_family:{row['family']}"] += 1
        # family denominators
        fam["corrections:gold"] += sum(g["state"] == "correction" for g in gold)
        if row["family"] == "backref":
            fam["backref:gold"] += len(gold)
        if long_turn:
            fam["long_turns:gold"] += sum(g["state"] in SAVE_STATES for g in gold)
            fam["long_turns:rows"] += 1
        if row["family"] in LOOK:
            n_saved = sum(is_saved(c, row, bar, rule) for c in cards)
            fam["lookalike:rows"] += 1
            fam["lookalike:rows_with_save"] += bool(n_saved)
            fam["lookalike:saves"] += n_saved
        # former cards (never saved; right = a card with state former equal to the gold former card, conf >= bar)
        fused = set()
        for c in cards:
            if c["state"] == "former" and c["conf"] >= bar:
                k = match_one(c, [g if g["state"] == "former" else {"owner": None, "rel": None, "value": None,
                                                                       "state": None} for g in gold], fused)
                fam["former:right"] += k is not None
        fam["former:gold"] += sum(g["state"] == "former" for g in gold)
        # pointers / copied text: every card at or above the bar, any state
        pused = set()
        for c in cards:
            if c["conf"] < bar:
                continue
            S["cards_at_bar"] += 1
            if not whole_word_ok(c, row):
                S["cards_text_not_whole_word"] += 1
            cand = [k for k, g in enumerate(gold) if k not in pused and g["rel"] == c["rel"] and g["state"] == c["state"]]
            if not cand:
                S["cards_no_gold_same_rel_state"] += 1
                continue
            k = next((k for k in cand if same(c, gold[k])), cand[0])
            pused.add(k)
            g = gold[k]
            ow, vw = norm(c["owner"]) != norm(g["owner"]), norm(c["value"]) != norm(g["value"])
            S["cards_words_right"] += not (ow or vw)
            S["cards_owner_words_wrong"] += ow
            S["cards_value_words_wrong"] += vw
    res = {"arm": arm, "bar": bar, "rule": rule, **dict(sorted(S.items())), "family": dict(sorted(fam.items()))}
    sh = {}
    for f in ("corrections", "backref", "former", "long_turns"):
        sh[f] = round(100 * fam[f"{f}:right"] / fam[f"{f}:gold"], 2) if fam[f"{f}:gold"] else None
    sh["lookalike"] = round(100 * fam["lookalike:rows_with_save"] / fam["lookalike:rows"], 2) \
        if fam["lookalike:rows"] else None
    res["family_share_pct"] = sh
    if ms:
        res["ms_median"] = round(statistics.median(ms), 2)
        res["ms_p90"] = round(sorted(ms)[int(0.9 * (len(ms) - 1))], 2)
    if rounds:
        res["rounds_mean"] = round(sum(rounds) / len(rounds), 3)
    return res


def choose_bar(rows, reads):
    """vector reader's save bar, on the calibration slice only: the lowest grid value whose wrong saves are at most
    0.5% of its saves (main rule); 0.999 if none"""
    table = []
    for t in BAR_GRID:
        s = score(rows, reads, "vector", t, "main")
        table.append({"bar": t, "saves": s.get("saves", 0), "right_saves": s.get("right_saves", 0),
                      "wrong_saves": s.get("wrong_saves", 0), "wrong_turns": s.get("wrong_turns", 0)})
    ok = [x for x in table if x["saves"] > 0 and x["wrong_saves"] <= BAR_MAX_WRONG_SHARE * x["saves"]]
    return (ok[0]["bar"] if ok else BAR_GRID[-1]), table


def verdict(L, V, LH, VH):
    """the sealed marks (PASSMARKS.md)"""
    lr, vr = L.get("right_saves", 0), V.get("right_saves", 0)
    m = {}
    m["V1"] = {"vector_right": vr, "lora_right": lr, "bar": round(0.95 * lr, 2), "met": vr >= 0.95 * lr}
    m["V2"] = {"vector_wrong_turns": V.get("wrong_turns", 0), "lora_wrong_turns": L.get("wrong_turns", 0),
               "met": V.get("wrong_turns", 0) <= L.get("wrong_turns", 0) + 2}
    v3 = {}
    for f, lo, vo in (("corrections", L, V), ("former", L, V), ("backref", LH, VH)):
        a, b = vo["family_share_pct"][f], lo["family_share_pct"][f]
        v3[f] = {"vector_pct": a, "lora_pct": b, "met": a is not None and b is not None and a >= b - 5}
    a, b = V["family_share_pct"]["lookalike"], L["family_share_pct"]["lookalike"]
    v3["lookalike"] = {"vector_pct_rows_with_save": a, "lora_pct_rows_with_save": b, "met": a <= b + 5}
    m["V3"] = {"by_family": v3, "met": all(x["met"] for x in v3.values())}
    valid = lr >= 0.5 * L.get("gold_savable_cards", 0)
    passed = m["V1"]["met"] and m["V2"]["met"] and m["V3"]["met"]
    wrong = vr < 0.80 * lr
    m["validity"] = {"lora_right": lr, "gold_savable_cards": L.get("gold_savable_cards", 0),
                     "rule": "LoRA right saves >= 50% of the savable gold cards", "met": valid}
    m["proved_wrong"] = {"rule": "vector right saves < 80% of the LoRA reader's", "hit": wrong}
    m["verdict"] = "INCONCLUSIVE" if not valid else "PASS" if passed else "FAIL (proved wrong)" if wrong else "FAIL"
    return m


def selftest():
    row = lambda i, fam, turn, prev, hist, cards: {  # noqa: E731
        "id": i, "family": fam, "turn": turn, "prev_reply": prev, "history": hist, "cards": cards,
        "prompt": " ".join([x for p in hist for x in p] + [prev, turn])}
    C = lambda o, r, v, s: {"owner": o, "rel": r, "value": v, "state": s}  # noqa: E731
    rows = [row("a", "teach", "my sister Mira is a nurse", "", [], [C("me", "sister", "Mira", "current"),
                                                                     C("Mira", "occupation", "nurse", "current")]),
            row("b", "backref", "she moved to Velbrook", "cool", [["my sister Mira is a nurse", "cool"]],
                [C("Mira", "city", "Velbrook", "current")]),
            row("c", "correct", "no wait Mira is a midwife", "ok", [], [C("Mira", "occupation", "midwife",
                                                                          "correction")]),
            row("d", "former", "Tovan used to work at Korlo Foods", "", [], [C("Tovan", "employer", "Korlo Foods",
                                                                                 "former")]),
            row("e", "plan", "im moving to Dunmere soon", "", [], [])]
    F = lambda o, r, v, m: {"owner": o, "rel": r, "value": v, "mode": m}  # noqa: E731
    lora = [{"id": "a", "frame": {"act": "STATE", "facts": [F("me", "sister", "Mira", "ASSERT"),
                                                            F("Mira", "occupation", "nurse", "ASSERT")]},
             "conf": [0.999, 0.99]},                                            # 2nd below 0.995: not saved
            {"id": "b", "frame": {"act": "STATE", "facts": [F("Mira", "city", "Velbrook", "ASSERT")]}, "conf": [1.0]},
            {"id": "c", "frame": {"act": "CORRECT", "facts": [F("Mira", "occupation", "midwife", "ASSERT")]},
             "conf": [1.0]},                                                    # state wrong -> wrong save
            {"id": "d", "frame": {"act": "STATE", "facts": [F("Tovan", "employer", "Korlo Foods", "FORMER")]},
             "conf": [1.0]},
            {"id": "e", "frame": {"act": "PLAN", "facts": [F("me", "city", "Dunmere", "ASSERT")]}, "conf": [1.0]}]
    s = score(rows, lora, "lora", LORA_T)
    assert (s["saves"], s["right_saves"], s["wrong_saves"], s["wrong_turns"]) == (3, 1, 2, 2), s
    assert s["family"]["former:right"] == 1 and s["family"]["lookalike:rows_with_save"] == 1, s
    assert s["family"].get("backref:right", 0) == 0 and s["gold_savable_cards"] == 3, s
    sh = score(rows, lora, "lora", LORA_T, "hist")
    assert sh["family"]["backref:right"] == 1 and sh["family_share_pct"]["backref"] == 100.0, sh
    lower = score(rows, [{"id": "a", "cards": [dict(C("me", "sister", "mira", "current"), conf=0.9)]}], "vector", 0.8)
    assert lower["saves"] == 0, lower                                           # value case must be as typed
    vec = [{"id": "a", "cards": [dict(C("me", "sister", "Mira", "current"), conf=0.9)], "rounds": 3, "ms": 20},
           {"id": "c", "cards": [dict(C("Mira", "occupation", "midwife", "correction"), conf=0.9)], "rounds": 2,
            "ms": 30},
           {"id": "d", "cards": [dict(C("Tovan", "employer", "Korlo", "former"), conf=0.9)], "rounds": 5, "ms": 25}]
    v = score(rows, vec, "vector", 0.8)
    assert (v["right_saves"], v["wrong_saves"], v["family"]["corrections:right"]) == (2, 0, 1), v
    assert v["family"].get("former:right", 0) == 0 and v["cards_value_words_wrong"] == 1, v
    assert v["missing_reads"] == 2 and v["parse_fail"] == 0, v
    assert v["family_share_pct"]["corrections"] == 100.0 and v["rounds_mean"] == 3.333, v
    vh = score(rows, vec, "vector", 0.8, "hist")
    m = verdict(s, v, sh, vh)
    assert m["V1"]["met"] and m["V2"]["met"] and not m["V3"]["by_family"]["former"]["met"], m
    assert not m["V3"]["by_family"]["backref"]["met"] and m["verdict"] == "INCONCLUSIVE", m   # LoRA 1 of 3 savable
    m2 = verdict(dict(s, gold_savable_cards=2), v, sh, vh)
    assert m2["verdict"] == "FAIL" and not m2["proved_wrong"]["hit"], m2
    m3 = verdict(dict(s, gold_savable_cards=2, right_saves=3), v, sh, vh)
    assert m3["verdict"] == "FAIL (proved wrong)" and not m3["V1"]["met"], m3
    bar, table = choose_bar(rows, vec)
    assert bar == 0.5 and table[0]["saves"] == 2, (bar, table)
    print("vread score selftest ok: saves, one-to-one right/wrong, state field, backref only under the hist rule, "
          "former cards, lookalike rows, pointer words, bar rule, verdict")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "bar", "verdict", "selftest"])
    ap.add_argument("--rows")
    ap.add_argument("--reads")
    ap.add_argument("--arm", choices=["lora", "vector"])
    ap.add_argument("--bar", type=float)
    ap.add_argument("--rule", choices=["main", "hist"], default="main")
    ap.add_argument("--lora")
    ap.add_argument("--vector")
    ap.add_argument("--lora-hist")
    ap.add_argument("--vector-hist")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "score":
        res = score(load(a.rows), load(a.reads), a.arm, a.bar, a.rule)
    elif a.cmd == "bar":
        bar, table = choose_bar(load(a.rows), load(a.reads))
        res = {"vector_save_bar": bar, "rule": f"lowest of {BAR_GRID} with wrong saves <= "
                                               f"{BAR_MAX_WRONG_SHARE:.1%} of saves on the calibration slice (main "
                                               "rule); 0.999 if none", "table": table}
    else:
        rd = lambda p: json.loads(Path(p).read_text())  # noqa: E731
        res = verdict(rd(a.lora), rd(a.vector), rd(a.lora_hist), rd(a.vector_hist))
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
