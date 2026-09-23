#!/usr/bin/env python3
"""Exp 241b sealed scorer: M1 (grammar, from the independent grader) and M4
(naturalness, from the independent pairwise judge).

241b vs 241's scorer: pair key label "241b"; LOWERCASE_NAME_ECHO now also
covers the CONFLICT new value (A v2 capitalises all-lowercase name values
there too; particle-initial values exempt); five new mechanical sub-marks
for the style sheet v2 clarifications and brief items c-e (each must be 0):
  C ENTITY_CODE              an internal "(E1234)" code in the text
  C REPEATED_LIST_ITEM       a list value said twice in one reply
  C SOMEONE_NON_PERSON       "someone"/"who is not" after a non-person value
  C TITLE_THE_LOWERED        a work title's "The" written "the" mid-sentence
  C VALUE_SUBJECT_AGREEMENT  a plural-looking common value + " is "
241 text follows.

Inputs (all jsonl):
  --sweep      sweep.jsonl         {id, act, text}
  --frames     sweep-frames.jsonl  {id, act, cls, frame, ...}  (sub-marks)
  --grades     grader output       {id, grammatical: bool, reason: str}
  --pairs-key  pairs-key.jsonl     {pair_id, act, X: base|241b, Y: base|241b}
  --judge      judge output        {pair_id, pick: X|Y|tie,
                                    meaning_change: bool, note: str}
  --out        summary json path
Either block may be scored alone (--grades without --judge or the reverse).

Schema contract: exactly the listed keys with the right types, every
sweep id / pair id exactly once, no unknown ids. Otherwise the scorer
prints SCHEMA-MISMATCH with the first problems and exits 3.

Bars (240 section 6, sealed in PASSMARKS.md):
  M1  grammatical >= 99.0 % overall AND >= 97 % in every act stratum, AND
      every mechanical sub-mark below at 0 on the sweep text.
  M4  241b wins >= 70 % of non-tie pairs AND loses <= 10 % of all pairs.
      meaning_change flags are listed (investigated under M2, no bar here).
Exit 0 = every scored mark passes, 1 = a mark fails, 3 = schema mismatch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
SAY_TABLE = REPO / "artifacts/claude-mouth241b-20260922/say_forms.json"
NOTE = "(I dropped my earlier question.) "

# closed list of names that take 'the' (same list the grader's style sheet
# names; copied here so the scorer does not import A's code)
THE_NAMES = {
    "united kingdom", "united states", "united states of america",
    "united arab emirates", "netherlands", "philippines", "bahamas",
    "gambia", "czech republic", "dominican republic", "maldives",
}

PLURAL_NAME_WORDS = {
    "Works", "Books", "Brothers", "Industries", "Systems", "Records",
    "Partners", "Labs", "Studios", "Games", "Sons", "Mills", "Gardens",
    "Islands", "Isles", "States", "Emirates", "Netherlands", "Philippines",
    "Bahamas", "Maldives", "Beatles", "Stones", "Arms", "Springs", "Falls",
}

NUM_SMALL = ["zero", "one", "two", "three", "four", "five", "six", "seven",
             "eight", "nine"]
SING_UNITS = ["person", "fact", "turn", "question", "row", "web row", "time"]
PLUR_UNITS = ["people", "facts", "turns", "questions", "rows", "web rows",
              "times"]
_A_CONS_SOUND = re.compile(r"^(uni|use|usu|uti|ure|uro|eu|ewe|one|once|u[bcfgklmnprstvz][aeiou])",
                           re.I)
_AN_SILENT_H = re.compile(r"^(hour|honest|honou?r|heir)", re.I)


def _jsonl(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def schema_mismatch(msgs: list[str]) -> int:
    print("SCHEMA-MISMATCH")
    for m in msgs[:20]:
        print("  ", m)
    return 3


def check_grades(grades, ids) -> list[str]:
    bad, seen = [], Counter()
    for k, g in enumerate(grades):
        if not isinstance(g, dict):
            bad.append(f"row {k}: not an object")
            continue
        if not isinstance(g.get("id"), str):
            bad.append(f"row {k}: id missing / not a string")
            continue
        if set(g) != {"id", "grammatical", "reason"}:
            bad.append(f"{g['id']}: fields {sorted(g)} != "
                       f"['grammatical', 'id', 'reason']")
        if not isinstance(g.get("grammatical"), bool):
            bad.append(f"{g['id']}: grammatical not a bool")
        if not isinstance(g.get("reason"), str):
            bad.append(f"{g['id']}: reason not a string")
        seen[g["id"]] += 1
    for i in ids:
        if seen[i] != 1:
            bad.append(f"{i}: graded {seen[i]} times")
    for i in seen:
        if i not in ids:
            bad.append(f"{i}: unknown id")
    return bad


def check_judge(judge, pids) -> list[str]:
    bad, seen = [], Counter()
    for k, j in enumerate(judge):
        if not isinstance(j, dict) or not isinstance(j.get("pair_id"), str):
            bad.append(f"row {k}: pair_id missing / not a string")
            continue
        if set(j) != {"pair_id", "pick", "meaning_change", "note"}:
            bad.append(f"{j['pair_id']}: fields {sorted(j)} != "
                       f"['meaning_change', 'note', 'pair_id', 'pick']")
        if j.get("pick") not in ("X", "Y", "tie"):
            bad.append(f"{j['pair_id']}: pick {j.get('pick')!r}")
        if not isinstance(j.get("meaning_change"), bool):
            bad.append(f"{j['pair_id']}: meaning_change not a bool")
        if not isinstance(j.get("note"), str):
            bad.append(f"{j['pair_id']}: note not a string")
        seen[j["pair_id"]] += 1
    for i in pids:
        if seen[i] != 1:
            bad.append(f"{i}: judged {seen[i]} times")
    for i in seen:
        if i not in pids:
            bad.append(f"{i}: unknown pair_id")
    return bad


# ------------------------------------------------------------ sub-marks
def _frame_strings(fr: dict) -> list[str]:
    out = []
    s = fr.get("subject") or {}
    if s.get("text") and s.get("role") != "user":
        out.append(s["text"])
    for k in ("values", "also_have", "choices", "subjects", "names"):
        out += [str(v) for v in fr.get(k) or [] if v != "USER"]
    for k in ("old_value", "new_value"):
        if fr.get(k):
            out.append(str(fr[k]))
    return out


def _mask(text: str, fr: dict) -> str:
    t = text
    for s in sorted(set(_frame_strings(fr)), key=len, reverse=True):
        t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9])",
                   " SLOT ", t, flags=re.I)
    return t


def _body(text: str) -> str:
    while text.startswith(NOTE):
        text = text[len(NOTE):]
    return text


def _article_bad(art: str, word: str) -> bool:
    w = word.strip("\"'(")
    if not w or not w[0].isalpha():
        return False
    if re.match(r"(?i)herb", w):
        return False  # 'a herbalist' (UK) and 'an herbalist' (US) both ok
    vowel = w[0].lower() in "aeiou"
    if w.isupper() and len(w) > 1:  # initialism: 'an MBA', 'a UN post'
        vowel = w[0].upper() in "AEFHILMNORSX"
    elif vowel and _A_CONS_SOUND.match(w):
        vowel = False
    elif not vowel and _AN_SILENT_H.match(w):
        vowel = True
    return (art.lower() == "a") == vowel


def _verb_row_for_act(row: dict, act: str, user: bool) -> bool:
    if act in ("SAVED", "CONFLICT", "FORGOTTEN_ONE"):
        t = (row.get("user") if user else row.get("affirm")) or [""]
        t = t[0] if isinstance(t, list) else t
    elif act == "ABSTAIN_MISSING":
        t = row.get("abstain_user" if user else "abstain_missing") or ""
    elif act == "FORGOTTEN":
        t = row.get("forgotten_user" if user else "forgotten") or ""
    else:
        return False
    return bool(t) and "{NP}" not in t and "{R}" not in t


def _template_has_noun(row: dict, act: str, user: bool, nouns) -> bool:
    """The verb template itself names the noun ('what school {S} goes
    to'): the noun in the text is then the verb form, not a fallback."""
    if act in ("SAVED", "CONFLICT", "FORGOTTEN_ONE"):
        t = (row.get("user") if user else row.get("affirm")) or [""]
        t = t[0] if isinstance(t, list) else t
    elif act == "ABSTAIN_MISSING":
        t = row.get("abstain_user" if user else "abstain_missing") or ""
    else:
        t = row.get("forgotten_user" if user else "forgotten") or ""
    tl = t.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", tl)
               for n in nouns if n)


PARTICLES = {"van", "von", "de", "da", "di", "du", "der", "la", "le",
             "bin", "al"}
_SING_S_END = ("ss", "us", "is", "ics", "ous", "ws")


def _plural_looking(v: str) -> bool:
    w = v.split()[-1].lower() if v.split() else ""
    return (len(w) > 3 and w.isalpha() and w.endswith("s")
            and not w.endswith(_SING_S_END))


def _repeated_item(body: str, fr: dict) -> bool:
    """A list value (values / also_have / subjects / names / choices) said
    twice in the reply. Longer strings are masked first so a value inside
    a longer one ('Pip' in 'Pip Stone') is not double-counted. A value that
    is also the subject, or a BROKEN_CHAIN value (said once as the answer,
    once as 'nothing saved about V'), is not a list item."""
    items = []
    for k in ("values", "also_have", "subjects", "names", "choices"):
        items += [str(v) for v in fr.get(k) or [] if v != "USER"]
    if fr.get("act") == "BROKEN_CHAIN" or len(items) < 2:
        return False
    others = [s for s in _frame_strings(fr) if s not in items]
    t = body
    for s in sorted(set(items + others), key=len, reverse=True):
        rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(s)
                        + r"(?![A-Za-z0-9])", re.I)
        n = len(rx.findall(t))
        t = rx.sub(" SLOT ", t)
        if s in items and n > 1:
            return True
    return False


def submarks(sweep: dict, frames: dict, table: dict) -> dict:
    """name -> list of (id, text) hits. Every list must be empty."""
    hits = defaultdict(list)
    rows = table.get("rows", {})
    surf2row = {}
    for r in rows.values():
        for s in r.get("surfaces") or []:
            surf2row.setdefault(s.lower(), r)
    for i, text in sweep.items():
        f = frames[i]
        fr = f["frame"]
        act = fr["act"]
        body = _body(text)
        m = _mask(body, fr)
        low = body.lower()
        path = fr.get("path") or []
        subj = fr.get("subject") or {}
        user = subj.get("role") == "user"
        row = surf2row.get(path[-1].lower()) if path else None

        # --- 240 section 6 required zeros
        # a lower-case noun ending in s + "'s" ('friends's'); singular -ss /
        # -us / -is / -os / -as nouns ('boss's') are correct and not counted
        for w in re.findall(r"\b([a-z]+s)'s\b", m):
            if not re.search(r"(ss|us|is|os|as)$", w):
                hits["S1 s's on a plural common noun"].append((i, text))
                break
        # on the unmasked body, so an article before a slot is judged by
        # the slot's own first word
        for art, w in re.findall(
                r"(?<![A-Za-z'.])(a|an|A|An)\s+([A-Za-z\"'(][\w'-]*)", body):
            if _article_bad(art, w):
                hits["S2 a/an by sound"].append((i, text))
                break
        if re.search(r":\s*[.,;]|,\s*[,.]|\band\s*[.,]", body):
            hits["S3 empty list slot"].append((i, text))
        if re.search(r"(?<![\w.,])0 [A-Za-z]", m):
            hits["S4 bare '0 X' count"].append((i, text))
        if re.search(r"_|\bUSER\b|[<>{}]", body):
            hits["S5 raw underscore / key"].append((i, text))
        if "worked out backwards" in low:
            hits["S6 dangling '(worked out backwards)'"].append((i, text))

        # --- 238 classes covered by A (each must be 0)
        # PLURAL_NAME_POSSESSIVE: a name ending in s/x/z gets "'s"
        # (a plural-looking name + "'s": 'Juniper Lane Books's',
        # 'Netherlands's'; singular names ending in s take "'s" by the
        # style sheet and are not counted)
        for s in _frame_strings(fr):
            last = s.split()[-1] if s.split() else ""
            if (last in PLURAL_NAME_WORDS or s.lower() in THE_NAMES) and \
                    re.search(re.escape(s) + r"'s\b", body, flags=re.I):
                hits["C PLURAL_NAME_POSSESSIVE"].append((i, text))
                break
        # VALUE_LIST_AGREEMENT
        vals = [str(v) for v in fr.get("values") or []]
        # 241b: distinct values (an exact repeat is said once, brief d)
        if act in ("ANSWER_LIST", "YESNO_NO") and \
                len({v.casefold() for v in vals}) > 1:
            if " are " not in body or re.search(
                    r" is " + re.escape(vals[0]) + r"\b", body):
                hits["C VALUE_LIST_AGREEMENT"].append((i, text))
        # NO_ARTICLE_JOB
        if row and row.get("name") == "occupation" and vals:
            if re.search(r"\b(?:is|as|am|are) " + re.escape(vals[0]) + r"\b",
                         body):
                hits["C NO_ARTICLE_JOB"].append((i, text))
        # NUMBER_AGREEMENT (and numbers 0-9 as words)
        if act.startswith("SELF"):
            ones = r"(?:1|one)"
            if re.search(r"\b" + ones + r" (?:" + "|".join(PLUR_UNITS) + r")\b",
                         low):
                hits["C NUMBER_AGREEMENT"].append((i, text))
            elif re.search(r"\b(?:[2-9]|\d{2,}|two|three|four|five|six|seven|"
                           r"eight|nine) (?:" + "|".join(
                               u for u in SING_UNITS) + r")\b", low):
                hits["C NUMBER_AGREEMENT"].append((i, text))
        if re.search(r"(?<![\w.,/:-])[0-9](?![\w.,/:-])", m):
            hits["C NUMBERS_0_9_AS_WORDS"].append((i, text))
        # EMPTY_LIST / BARE_NAME_LIST (SELF_PEOPLE)
        if act == "SELF_PEOPLE":
            names = fr.get("names") or []
            if len(names) >= 2 and " and " not in body:
                hits["C BARE_NAME_LIST"].append((i, text))
            if "USER" in names and not re.search(r"\byou\b", body):
                hits["C SELF_PEOPLE_USER_AS_YOU"].append((i, text))
            if re.search(r"people:\s*\.", body):
                hits["C EMPTY_LIST"].append((i, text))
        # COLON_LABEL
        if body.startswith("Forgotten:"):
            hits["C COLON_LABEL"].append((i, text))
        # LOWERCASE_START / LOWERCASE_NAME_ECHO
        if re.search(r"(^|[.?!]\s+)[a-z]", m.strip()):
            hits["C LOWERCASE_START"].append((i, text))
        echo = []
        if subj.get("text") and not user and subj["text"][:1].islower() \
                and act not in ("UNKNOWN_ENTITY",):
            echo.append(subj["text"])
        if row and row.get("value_kind") in ("person", "place",
                                             "organization"):
            echo += [v for v in vals if v[:1].islower()]
            if fr.get("old_value") and str(fr["old_value"])[:1].islower():
                echo.append(str(fr["old_value"]))
            # 241b: the new value is capitalised too (brief b)
            if fr.get("new_value") and str(fr["new_value"])[:1].islower():
                echo.append(str(fr["new_value"]))
        echo = [e for e in echo
                if e.split()[0].lower() not in PARTICLES]
        for s in echo:
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(s)
                         + r"(?![A-Za-z0-9])", body):
                hits["C LOWERCASE_NAME_ECHO"].append((i, text))
                break
        if act == "UNKNOWN_ENTITY" and subj.get("text", "")[:1].islower() \
                and not re.match(r"(my|your|the|a|an)\b", subj["text"]):
            if re.search(r"called " + re.escape(subj["text"]) + r"\b", body):
                hits["C LOWERCASE_NAME_ECHO"].append((i, text))
        # DOUBLE_TERMINAL_PUNCT
        if re.search(r"(?<!\.)[.?!]\s?[.?!](?!\.)", body):
            hits["C DOUBLE_TERMINAL_PUNCT"].append((i, text))
        # MISSING_ARTICLE_THE
        for s in _frame_strings(fr):
            if s.lower() in THE_NAMES:
                for mm in re.finditer(re.escape(s), body, flags=re.I):
                    pre = body[:mm.start()].lower()
                    if not pre.endswith("the "):
                        hits["C MISSING_ARTICLE_THE"].append((i, text))
                        break
        # STACKED_POSSESSIVE (3+ hops): the whole chain as 's / your stack
        if len(path) >= 3:
            n = len(re.findall(r"'s\b", m)) + (1 if re.match(r"(?i)your\b",
                                                             body) else 0)
            if n >= len(path):
                hits["C STACKED_POSSESSIVE"].append((i, text))
        # --- 241b new sub-marks
        if re.search(r"\(E\d+\)", body):
            hits["C ENTITY_CODE"].append((i, text))
        if _repeated_item(body, fr):
            hits["C REPEATED_LIST_ITEM"].append((i, text))
        vk = row.get("value_kind") if row else None
        if re.search(r"\bsomeone\b|\bwho is not\b", low) and \
                act not in ("UNKNOWN_ENTITY",) and vk != "person":
            hits["C SOMEONE_NON_PERSON"].append((i, text))
        for s in _frame_strings(fr):
            if s.startswith("The ") and len(s) > 4:
                if re.search(r"(?<=[a-z,] )the " + re.escape(s[4:])
                             + r"(?![A-Za-z0-9])", body):
                    hits["C TITLE_THE_LOWERED"].append((i, text))
                    break
        if vk not in ("person", "place", "organization", "language", "work",
                      "date", "number"):
            for v in [str(x) for x in vals] + [str(fr.get(k) or "") for k in
                                               ("old_value", "new_value")]:
                if v and _plural_looking(v) and re.search(
                        r"(?<![A-Za-z0-9])" + re.escape(v) + r" is\b",
                        body, flags=re.I):
                    hits["C VALUE_SUBJECT_AGREEMENT"].append((i, text))
                    break
        # WORKED_BACKWARDS_TAG
        if "(worked out backwards)" in body:
            hits["C WORKED_BACKWARDS_TAG"].append((i, text))
        # BAD_RELATION_PHRASE: a verb-phrase relation used as a noun
        if re.search(r"\b(?:\w+ed|by|at|in|of|on|for) ?'s\b|\b\w+ed (?:by|at|"
                     r"in|on|for)(?: is|'s| of)\b|the \w+ed (?:by|at|in|on|"
                     r"for) of\b", m):
            hits["C BAD_RELATION_PHRASE"].append((i, text))
        # RELATION_NOT_VERB: rows with a verb form must use it (1 hop)
        # 241b: a number-kind CONFLICT uses the noun clause on purpose
        # ("X's age is 6. ... change it to 72?": the old and new value in
        # the same unit; 241's grader flagged "6 years old ... to 72")
        if row and len(path) == 1 and _verb_row_for_act(row, act, user) \
                and not (act == "CONFLICT"
                         and row.get("value_kind") == "number"):
            ml = m.lower()
            nouns = {path[-1].lower(), str(row.get("noun", "")).lower()}
            if not _template_has_noun(row, act, user, nouns) and any(re.search(r"(?<![a-z])" + re.escape(nn) + r"(?![a-z])",
                             ml) for nn in nouns if nn):
                hits["C RELATION_NOT_VERB"].append((i, text))
    return hits


SUBMARK_NAMES = [
    "S1 s's on a plural common noun", "S2 a/an by sound",
    "S3 empty list slot", "S4 bare '0 X' count", "S5 raw underscore / key",
    "S6 dangling '(worked out backwards)'",
    "C RELATION_NOT_VERB", "C PLURAL_NAME_POSSESSIVE",
    "C VALUE_LIST_AGREEMENT", "C NO_ARTICLE_JOB", "C NUMBER_AGREEMENT",
    "C NUMBERS_0_9_AS_WORDS", "C EMPTY_LIST", "C BARE_NAME_LIST",
    "C SELF_PEOPLE_USER_AS_YOU", "C COLON_LABEL", "C LOWERCASE_START",
    "C LOWERCASE_NAME_ECHO", "C DOUBLE_TERMINAL_PUNCT",
    "C MISSING_ARTICLE_THE", "C STACKED_POSSESSIVE",
    "C WORKED_BACKWARDS_TAG", "C BAD_RELATION_PHRASE",
    # 241b
    "C ENTITY_CODE", "C REPEATED_LIST_ITEM", "C SOMEONE_NON_PERSON",
    "C TITLE_THE_LOWERED", "C VALUE_SUBJECT_AGREEMENT",
]


# ------------------------------------------------------------ marks
def score_m1(sweep_rows, frames, grades, out) -> bool:
    sweep = {r["id"]: r["text"] for r in sweep_rows}
    act = {r["id"]: r["act"] for r in sweep_rows}
    g = {x["id"]: x for x in grades}
    per = defaultdict(lambda: [0, 0])
    bad = []
    for i in sweep:
        per[act[i]][1] += 1
        if g[i]["grammatical"]:
            per[act[i]][0] += 1
        else:
            bad.append((i, act[i], sweep[i], g[i]["reason"]))
    ok_n = sum(v[0] for v in per.values())
    n = len(sweep)
    overall = ok_n / n if n else 0.0
    act_ok = {a: v[0] / v[1] >= 0.97 for a, v in per.items()}
    table = json.loads(SAY_TABLE.read_text(encoding="utf-8"))
    hits = submarks(sweep, frames, table)
    sub_ok = all(not hits.get(k) for k in SUBMARK_NAMES)
    passed = overall >= 0.99 and all(act_ok.values()) and sub_ok
    print(f"M1 grammar: {ok_n}/{n} = {100 * overall:.2f}% (bar >= 99.0%)")
    for a in sorted(per):
        v = per[a]
        print(f"  {a:16s} {v[0]:4d}/{v[1]:<4d} {100 * v[0] / v[1]:6.2f}% "
              f"{'ok' if act_ok[a] else 'BELOW 97%'}")
    print("M1 sub-marks (each must be 0):")
    for k in SUBMARK_NAMES:
        print(f"  {k:40s} {len(hits.get(k, []))}")
        for i, t in hits.get(k, [])[:5]:
            print(f"      {i}: {t}")
    print("M1 ungrammatical replies (grader):")
    for x in bad:
        print(f"  {x[0]} [{x[1]}] {x[2]!r} -- {x[3]}")
    print("M1", "PASS" if passed else "FAIL")
    out["M1"] = {"pass": passed, "grammatical": ok_n, "n": n,
                 "overall_pct": round(100 * overall, 3),
                 "per_act": {a: {"ok": v[0], "n": v[1],
                                 "pct": round(100 * v[0] / v[1], 3),
                                 "pass": act_ok[a]} for a, v in per.items()},
                 "submarks": {k: len(hits.get(k, [])) for k in SUBMARK_NAMES},
                 "submark_hits": {k: hits[k] for k in SUBMARK_NAMES
                                  if hits.get(k)},
                 "ungrammatical": bad}
    return passed


def score_m4(key_rows, judge, out) -> bool:
    key = {k["pair_id"]: k for k in key_rows}
    win = lose = tie = 0
    per = defaultdict(Counter)
    flags = []
    for j in judge:
        k = key[j["pair_id"]]
        if j["pick"] == "tie":
            res = "tie"
        else:
            res = "win" if k[j["pick"]] == "241b" else "lose"
        win += res == "win"
        lose += res == "lose"
        tie += res == "tie"
        per[k["act"]][res] += 1
        if j["meaning_change"]:
            flags.append((j["pair_id"], k["act"], j["pick"], res, j["note"]))
    n = len(judge)
    nt = win + lose
    wr = win / nt if nt else 0.0
    lr = lose / n if n else 1.0
    passed = wr >= 0.70 and lr <= 0.10
    print(f"M4 naturalness: {n} pairs; 241b wins {win}, loses {lose}, ties "
          f"{tie}; win rate of non-tie {win}/{nt} = {100 * wr:.1f}% (bar >= "
          f"70%); loss rate {lose}/{n} = {100 * lr:.1f}% (bar <= 10%)")
    for a in sorted(per):
        c = per[a]
        print(f"  {a:16s} win {c['win']:3d} lose {c['lose']:3d} tie "
              f"{c['tie']:3d}")
    print(f"M4 meaning-change flags: {len(flags)} (each investigated under M2)")
    for f in flags:
        print("  ", f)
    print("M4", "PASS" if passed else "FAIL")
    out["M4"] = {"pass": passed, "n": n, "win": win, "lose": lose, "tie": tie,
                 "win_rate_non_tie_pct": round(100 * wr, 3),
                 "loss_rate_pct": round(100 * lr, 3),
                 "per_act": {a: dict(c) for a, c in per.items()},
                 "meaning_flags": flags}
    return passed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep")
    ap.add_argument("--frames")
    ap.add_argument("--grades")
    ap.add_argument("--pairs-key")
    ap.add_argument("--judge")
    ap.add_argument("--out", required=True)
    ap.add_argument("--submarks-only", action="store_true",
                    help="builder self-check of the mechanical sub-marks "
                         "on a PILOT sweep (no grader file)")
    a = ap.parse_args(argv)
    out: dict = {}
    ok = True
    if a.submarks_only:
        sweep_rows = _jsonl(a.sweep)
        frames = {f["id"]: f for f in _jsonl(a.frames)}
        table = json.loads(SAY_TABLE.read_text(encoding="utf-8"))
        hits = submarks({r["id"]: r["text"] for r in sweep_rows}, frames,
                        table)
        for k in SUBMARK_NAMES:
            print(f"  {k:40s} {len(hits.get(k, []))}")
            for i, t in hits.get(k, [])[:6]:
                print(f"      {i}: {t}")
        return 0 if all(not hits.get(k) for k in SUBMARK_NAMES) else 1
    if a.grades:
        sweep_rows = _jsonl(a.sweep)
        frames = {f["id"]: f for f in _jsonl(a.frames)}
        try:
            grades = _jsonl(a.grades)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return schema_mismatch([f"grades not jsonl: {e}"])
        bad = check_grades(grades, {r["id"] for r in sweep_rows})
        if bad:
            return schema_mismatch(bad)
        ok &= score_m1(sweep_rows, frames, grades, out)
    if a.judge:
        key_rows = _jsonl(a.pairs_key)
        try:
            judge = _jsonl(a.judge)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return schema_mismatch([f"judge not jsonl: {e}"])
        bad = check_judge(judge, {k["pair_id"] for k in key_rows})
        if bad:
            return schema_mismatch(bad)
        ok &= score_m4(key_rows, judge, out)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
