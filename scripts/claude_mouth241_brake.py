#!/usr/bin/env python3
"""Exp 241 (mouth stage A) -- brake v2 (240 section 4), run on A's own output.

check(frame, text, names=()) -> (ok, fails)   fails = [(rule, detail), ...]

Rules 1-8 as in 240 section 4, plus rule 9 (registered in PASSMARKS): the
text must keep every frozen-scorer anchor the legacy line had, i.e. equal
values of
  * fable_decline224.is_decline                        (224a shared detector)
  * any redteam143 abstain marker                      (rt143)
  * any bench121 ABSTAIN_PHRASES regex                 (bench)
  * any sessions152 CLARIFY_BITS                       (sessions152)
  * teach_accepted ("Saved:" prefix / "I already have that.")  (rt143/bench)
  * for value acts: whether " is "/" are " occurs, and the value read after
    the last one (bench121/rt143 extract_answer, normalised as bench's norm,
    ignoring "and"/commas so a list join fix is not a change).
Scorer modules are imported read-only; nothing is edited.
"""
from __future__ import annotations

import json
import re
import string
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241_morph as M  # noqa: E402
import claude_mouth241_reader as RD  # noqa: E402
import claude_mouth241_say as SAY  # noqa: E402
import fable_bench121_run as B121  # noqa: E402
import fable_decline224 as D224  # noqa: E402
import fable_redteam143_run as R143  # noqa: E402
import fable_session152_run as S152  # noqa: E402
from fable_mouth53_mouth import FUNCTION_WORDS as FW53  # noqa: E402

RT143_MARKERS = [m.lower() for m in json.loads(
    Path(R143.CASES_PATH).read_text(encoding="utf-8"))["abstain_markers"]]

# ------------------------------------------------------------ word lists
CONTENT_LIKE = {"taught", "online", "saved", "missing", "pending", "answer",
                "question", "fact", "name", "person", "work", "told", "read",
                "said", "found", "finding", "finds", "yesterday", "later",
                "soon", "sorry", "thanks", "thank", "hello", "hi", "goodbye",
                "bye", "hey", "maybe", "perhaps", "likely", "thought", "thinks",
                "knew", "became", "become", "becomes", "becoming", "came",
                "went", "turned"}
THIRD_PRONOUNS = {"he", "he'd", "he'll", "he's", "her", "hers", "herself",
                  "him", "himself", "his", "she", "she'd", "she'll", "she's",
                  "they", "they'd", "they'll", "they're", "they've", "their",
                  "theirs", "them", "themselves"}
FUNCTION_WORDS = frozenset(set(FW53) - CONTENT_LIKE - THIRD_PRONOUNS)

NUM_WORD = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
    "twenty".split())}
NUM_WORD.update({"once": 1, "twice": 2, "none": 0})
VAGUE = {"several", "many", "few", "couple"}
IDIOMS = ("more than one", "which one", "no one", "one fact at a time")
NEGATORS = {"not", "no", "never", "nobody", "nothing", "none", "neither",
            "nor", "cannot", "without"}
BANNED = ("i think", "probably", "i remember", "i guess", "maybe",
          "as everyone knows", "you told me")
BACKWARDS = ("worked out backwards", "worked that out backwards",
             "worked it out backwards")

_CNT = set(M.NUM_WORDS) | {"no", "any", "yet", "haven't"}
ACT_LEX = {
    "ANSWER": set(), "ANSWER_LIST": set(), "REVERSE": set(),
    "YESNO_YES": {"yes"}, "YESNO_NO": {"no"},
    "YESNO_NOTKNOWN": {"not", "that", "know", "of", "have", "as"},
    "ABSTAIN_MISSING": {"don't", "know", "yet"},
    "UNKNOWN_ENTITY": {"don't", "know", "anyone", "called"},
    "BROKEN_CHAIN": {"which", "not", "someone", "can", "look", "up"},
    "AMBIGUOUS": {"know", "more", "than", "one", "which", "mean"},
    "SAVED": {"saved", "also", "have"},
    "DUPLICATE": {"already", "have", "that"},
    "CONFLICT": {"my", "notes", "say", "have", "as", "do", "you", "want",
                 "me", "change", "it", "to"},
    "CONFIRM_RESULT": {"okay", "left", "it", "as", "was"},
    "FORGOTTEN": {"ok", "i've", "forgotten"},
    "FORGOTTEN_ONE": {"ok", "i've", "forgotten", "that"},
    "NOT_HAD": {"don't", "have", "as", "so", "there", "was", "nothing",
                "forget", "note"},
    "SELF_PEOPLE": {"know", "person", "people", "you", "haven't", "told",
                    "about", "anyone", "yet"} | _CNT,
    "SELF_FACTS": {"you", "have", "haven't", "taught", "fact", "facts",
                   "hold", "web", "row", "rows", "also", "which", "believe",
                   "not", "do"} | _CNT,
    "SELF_SLEPT": {"yes", "no", "slept", "haven't", "yet", "once", "twice",
                   "times"} | _CNT,
    "SELF_TURNS": {"we", "have", "had", "haven't", "turn", "turns"} | _CNT,
    "SELF_ANSWERED": {"answered", "haven't", "question", "questions"} | _CNT,
}
ACT_FAMILY = {
    "ANSWER": "answer", "ANSWER_LIST": "answer", "REVERSE": "answer",
    "YESNO_YES": "yesno", "YESNO_NO": "yesno", "YESNO_NOTKNOWN": "yesno",
    "ABSTAIN_MISSING": "abstain", "UNKNOWN_ENTITY": "abstain",
    "BROKEN_CHAIN": "abstain", "NOT_HAD": "abstain",
    "AMBIGUOUS": "clarify", "SAVED": "saved", "DUPLICATE": "duplicate",
    "CONFLICT": "conflict", "CONFIRM_RESULT": "confirm",
    "FORGOTTEN": "forgotten", "FORGOTTEN_ONE": "forgotten",
    "SELF_PEOPLE": "self", "SELF_FACTS": "self", "SELF_SLEPT": "self",
    "SELF_TURNS": "self", "SELF_ANSWERED": "self",
}
VALUE_ACTS = {"ANSWER", "ANSWER_LIST", "REVERSE", "YESNO_YES", "YESNO_NO",
              "YESNO_NOTKNOWN", "BROKEN_CHAIN"}
TRIPLE_ACTS = {"ANSWER", "ANSWER_LIST", "YESNO_YES", "YESNO_NO", "SAVED",
               "CONFLICT", "FORGOTTEN_ONE", "REVERSE"}

_WORD = re.compile(r"[A-Za-z0-9']+")


def _norm_apos(t: str) -> str:
    return str(t).replace("’", "'").replace("‘", "'")


def words(t: str) -> list[str]:
    return _WORD.findall(_norm_apos(t))


def _strip_poss(w: str) -> str:
    lw = w.lower()
    if lw.endswith("'s"):
        return lw[:-2]
    return lw.rstrip("'")


# ------------------------------------------------------------ frame slots
def frame_strings(fr: dict) -> list[str]:
    """Every content string the frame carries (for coverage and masking)."""
    out = []
    s = fr.get("subject") or {}
    if s.get("text") and s.get("role") != "user":
        out.append(SAY.cap_name(s["text"]) if fr["act"] != "UNKNOWN_ENTITY"
                   else s["text"])
    for k in ("values", "also_have", "choices", "subjects"):
        for v in fr.get(k) or []:
            out.append(str(v))
    for k in ("old_value", "new_value"):
        if fr.get(k):
            out.append(str(fr[k]))
    for n in fr.get("names") or []:
        if n != RD.USER:
            out.append(str(n))
    return out


def required_slots(fr: dict) -> list[str]:
    a = fr["act"]
    req = []
    s = fr.get("subject") or {}
    if a not in ("REVERSE", "DUPLICATE", "CONFIRM_RESULT") and \
            not a.startswith("SELF") and s:
        if s.get("role") == "user":
            req.append("you|your")
        elif s.get("text"):
            req.append(s["text"])
    for k in ("values", "also_have", "subjects"):
        req.extend(str(v) for v in fr.get(k) or [])
    for c in fr.get("choices") or []:
        m = re.match(r"(.+?) \((E\d+)\)$", c)
        req.extend([m.group(1), m.group(2)] if m else [c])
    for k in ("old_value", "new_value"):
        if fr.get(k):
            req.append(str(fr[k]))
    for n in fr.get("names") or []:
        req.append("you" if n == RD.USER else n)
    return req


def _has_slot(text: str, slot: str) -> bool:
    for alt in slot.split("|") if slot == "you|your" else [slot]:
        rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(_norm_apos(alt))
                        + r"(?:'s|')?(?![A-Za-z0-9])", re.I)
        if rx.search(_norm_apos(text)):
            return True
    return False


def _mask(text: str, fr: dict) -> str:
    t = _norm_apos(text)
    for s in sorted(set(frame_strings(fr)), key=len, reverse=True):
        if s:
            t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(_norm_apos(s))
                       + r"(?![A-Za-z0-9])", " XSLOT ", t, flags=re.I)
    return t


def _slot_ends_period(body: str, masked: str, pos: int, fr: dict) -> bool:
    """The word at masked[pos] follows a masked slot; True when the same
    word in the body follows a frame string that ends with '.'."""
    nxt = masked[pos:]
    tail = nxt.split()[0] if nxt.split() else ""
    for s in frame_strings(fr):
        s = _norm_apos(s)
        if s.endswith(".") and re.search(re.escape(s) + r"\s+" + re.escape(tail),
                                         body, flags=re.I):
            return True
    return False


def row_lexicon(row: dict | None) -> set[str]:
    if not row:
        return set()
    lex = set()
    for s in row["surfaces"]:
        for w in words(s):
            lex.add(w.lower())
        for w in words(M.plural(s)):
            lex.add(w.lower())
    for key in ("affirm", "user", "abstain_missing", "abstain_user",
                "forgotten", "forgotten_user"):
        vals = row.get(key)
        vals = vals if isinstance(vals, list) else [vals]
        for t in vals:
            if t:
                for w in words(re.sub(r"\{[A-Za-z]+\}", " ", t)):
                    lex.add(w.lower())
    lex |= {"a", "an", "on", "in"}
    return lex


# ------------------------------------------------------------ anchors
def _canon_extract(reply: str) -> str:
    v = B121.norm(B121.extract_answer(reply))
    return " ".join(t for t in v.split() if t != "and")


# bench v3 driver (scripts/fable_fix172b_benchv3.py, read-only): it answers
# "yes" only when the text after this needle, stripped of '?.! ', occurs
# verbatim in the taught sentence -> the new value must stay byte-equal
NEEDLE172B = "Do you want me to change it to"


def confirm_value172b(reply: str) -> str:
    if NEEDLE172B not in (reply or ""):
        return ""
    tail = (reply or "").split(NEEDLE172B, 1)[1].strip()
    return tail.rstrip("?.!. ").strip()


def anchors(text: str, value_act: bool) -> dict:
    low = _norm_apos(text).lower()
    out = {
        "confirm172b": confirm_value172b(text),
        "decline224": D224.is_decline(text),
        "rt143": any(m in low for m in RT143_MARKERS),
        "bench_abstain": any(rx.search(low) for rx in B121._ABSTAIN_RES),
        "clarify152": S152.is_clarify(text),
        "teach_accepted": R143.teach_accepted(text),
    }
    if value_act:
        out["has_is_are"] = (" is " in low) or (" are " in low)
        out["extract"] = _canon_extract(text) if out["has_is_are"] else None
    return out


# ------------------------------------------------------------ rules
def _sentences(masked: str) -> int:
    t = masked.strip()
    parts = [p for p in re.split(r"(?<=[.?!])\)?\s+", t) if p.strip()]
    return len(parts)


def expected_negative(fr: dict) -> bool:
    a = fr["act"]
    if a in ("ABSTAIN_MISSING", "UNKNOWN_ENTITY", "BROKEN_CHAIN", "NOT_HAD",
             "YESNO_NO", "YESNO_NOTKNOWN", "SELF_FACTS"):
        return True
    if a.startswith("SELF") and int(fr.get("count", 1)) == 0:
        return True
    return False


def frame_numbers(fr: dict) -> set[int]:
    nums = set()
    for k in ("count", "count2"):
        if fr.get(k) is not None and int(fr[k]) != 0:
            nums.add(int(fr[k]))
    for s in frame_strings(fr):
        for d in re.findall(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])", s):
            nums.add(int(d))
    return nums


def classify(text: str) -> str:
    t = _norm_apos(text).strip()
    low = t.lower()
    if low.startswith("saved:"):
        return "saved"
    if t == "I already have that.":
        return "duplicate"
    if "do you want me to change it to" in low:
        return "conflict"
    if "left it as it was" in low:
        return "confirm"
    if low.startswith("ok, i've forgotten") or low.startswith("forgotten:"):
        return "forgotten"
    if "which one do you mean" in low:
        return "clarify"
    if re.match(r"^(yes|no), ", low) and not re.match(
            r"^(yes|no), (i have|i haven't|we )", low):
        return "yesno"
    if low.startswith("not that i know of"):
        return "yesno"
    if re.match(r"^(i know (one|two|three|four|five|six|seven|eight|nine|"
                r"\d+) (person|people)|you haven't told me about anyone|"
                r"you have taught me|you haven't taught me|"
                r"(yes|no), i (have|haven't) slept|we have had|"
                r"we haven't had|i have answered|i haven't answered)", low):
        return "self"
    if ("don't know" in low or "do not know" in low
            or "not someone i can look up" in low
            or low.startswith("i don't have ")):
        return "abstain"
    if " is " in low or " are " in low:
        return "answer"
    return "other"


def statements_for_rule7(fr: dict, text: str) -> list[tuple[str, str, str]]:
    """(statement, X, Y) pairs to read back. Empty = rule 7 skipped."""
    a = fr["act"]
    path = fr.get("path") or []
    if a not in TRIPLE_ACTS or (a != "REVERSE" and len(path) != 1):
        return []
    s = fr.get("subject") or {}
    X = RD.USER if s.get("role") == "user" else s.get("text", "")
    vals = fr.get("values") or []
    t = _norm_apos(text)
    if a == "ANSWER":
        return [(t, X, vals[0])]
    if a == "ANSWER_LIST":
        out = []
        for v in vals:
            one = dict(fr, act="ANSWER", values=[v])
            c = SAY.candidates(one)
            out.append((c[-1], X, v))
        return out
    if a == "YESNO_YES":
        return [(re.sub(r"^Yes, ", "", t), X, vals[0])]
    if a == "YESNO_NO":
        if len(vals) != 1:
            return []
        return [(re.sub(r"^No, ", "", t), X, vals[0])]
    if a == "SAVED":
        body = re.sub(r"^Saved: ", "", t)
        body = re.sub(r" \(I also have .+\.\)$", "", body)
        return [(body, X, vals[0])]
    if a == "CONFLICT":
        m = re.match(r"^My notes say (.+?\.) Do you want me", t)
        if m:
            return [(m.group(1), X, fr["old_value"])]
        m = re.match(r"^I have (.+) as (.+?)\. Do you want me", t)
        if m:
            return [(f"{m.group(1)} is {m.group(2)}.", X, fr["old_value"])]
        return [("", X, fr["old_value"])]
    if a == "FORGOTTEN_ONE":
        return [(re.sub(r"^OK, I've forgotten that ", "", t), X, vals[0])]
    if a == "REVERSE":
        subs = fr.get("subjects") or []
        if len(subs) == 1:
            return [(t, subs[0], vals[0])]
        noun = path[-1]
        return [(f"{vals[0]} is the {noun} of {x}.", x, vals[0])
                for x in subs]
    return []


def check(fr: dict, text: str, names=(), legacy: str | None = None
          ) -> tuple[bool, list]:
    """Brake v2 on one candidate. `names` = the notebook's entity names
    (read-only). `legacy` = the base line (rule 9)."""
    fails = []
    a = fr["act"]
    row = fr.get("_row")
    body = _norm_apos(text)
    masked = _mask(body, fr)
    mwords = words(masked)
    low = body.lower()

    # 1 shape
    ns = _sentences(masked)
    if not (1 <= ns <= 2):
        fails.append((1, f"{ns} sentences"))
    if len([w for w in mwords if w != "XSLOT"]) > 40:
        fails.append((1, "over 40 words"))
    lw = [w.lower() for w in mwords]
    chain = {"the", "of", "s"} | {w.lower() for p in fr.get("path") or []
                                  for q in (p, SAY.display_noun(p, SAY.row_for(p)))
                                  for w in words(q)}
    grams = [tuple(lw[i:i + 3]) for i in range(len(lw) - 2)
             if "xslot" not in lw[i:i + 3]  # masked slots are not wording
             and not set(lw[i:i + 3]) <= chain]  # 'the friend of the friend of'

    if len(grams) != len(set(grams)):
        fails.append((1, "repeated 3-gram"))
    if "_" in body or "<" in body or re.search(r"\bUSER\b", body):
        fails.append((1, "raw key / underscore / marker"))
    if a != "AMBIGUOUS" and re.search(r"\bE\d{3,}\b", masked):
        fails.append((1, "raw entity id"))

    # 2 slot coverage
    for slot in required_slots(fr):
        if not _has_slot(body, slot):
            fails.append((2, f"missing slot {slot!r}"))

    # 3 no extra content
    content = set()
    for s in frame_strings(fr):
        content |= {_strip_poss(w) for w in words(s)}
    for p in fr.get("path") or []:
        for q in dict.fromkeys([p, SAY.display_noun(p, SAY.row_for(p))]):
            content |= {w.lower() for w in words(q)}
            content |= {w.lower() for w in words(M.plural(q))}
    if (fr.get("subject") or {}).get("role") == "user" or \
            RD.USER in (fr.get("names") or []):
        content |= {"you", "your"}
    lex = FUNCTION_WORDS | ACT_LEX.get(a, set()) | row_lexicon(row)
    for w in words(body):
        lw_ = _strip_poss(w)
        if w.isdigit() and int(w) in frame_numbers(fr):
            continue  # frame counts in digits (10+); rule 4 checks them
        if w in ("'s", "'"):
            continue  # clitic split off after a period ('Apple Inc.'s')
        if lw_ in content or w.lower() in lex or lw_ in lex:
            continue
        fails.append((3, f"extra word {w!r}"))
    # capitalised tokens not at a sentence start must be in the frame
    for m in re.finditer(r"[A-Za-z0-9']+", masked):
        w = m.group(0)
        if not w[:1].isupper() or w in ("XSLOT", "I", "I've", "I'm"):
            continue
        before = masked[:m.start()].rstrip()
        if before == "" or before[-1] in ".?!:(":
            continue
        if before.endswith("XSLOT") and _slot_ends_period(body, masked,
                                                          m.start(), fr):
            continue  # 'Washington, D.C. Do you want ...': the slot's own
            # final period also ends the sentence
        fails.append((3, f"capitalised {w!r} not in frame"))
    frame_low = {s.lower() for s in frame_strings(fr)}
    for n in names or ():
        n = str(n)
        if n.lower() in frame_low or n == RD.USER or len(n) < 2:
            continue
        if any(n.lower() in f for f in frame_low):
            continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])",
                     masked):
            fails.append((3, f"notebook name {n!r} not in frame"))

    # 4 numbers
    mlow = masked.lower()
    for idi in IDIOMS:
        mlow = mlow.replace(idi, " ")
    got = set()
    for w in words(mlow):
        wl = w.lower()
        if wl.isdigit():
            got.add(int(wl))
        elif wl in NUM_WORD:
            got.add(NUM_WORD[wl])
        elif wl in VAGUE:
            fails.append((4, f"vague quantifier {wl!r}"))
    # value digits were masked out above; they are required slots (rule 2),
    # so they are added back from the frame here
    want = frame_numbers(fr)
    got |= {int(d) for s in frame_strings(fr)
            for d in re.findall(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])", s)}
    if got != want:
        fails.append((4, f"numbers {sorted(got)} != frame {sorted(want)}"))

    # 5 polarity
    toks = [w.lower() for w in words(masked) if w != "XSLOT"]
    neg = any(t in NEGATORS or t.endswith("n't") for t in toks)
    if neg != expected_negative(fr):
        fails.append((5, f"polarity {'neg' if neg else 'aff'}"))
    if a in ("YESNO_YES", "YESNO_NO"):
        first = (words(body) or [""])[0]
        if first != ("Yes" if a == "YESNO_YES" else "No"):
            fails.append((5, "yes/no first word"))

    # 6 act anchor
    fam = classify(body)
    if fam != ACT_FAMILY.get(a):
        fails.append((6, f"reads as {fam}, frame is {ACT_FAMILY.get(a)}"))

    # 7 round trip
    extra = SAY.reader_extra(row) if row else None
    rel = row["name"] if row else None
    for stmt, X, Y in statements_for_rule7(fr, body):
        ok, why = RD.round_trip_ok(stmt, rel, X, Y, extra)
        if not ok:
            fails.append((7, f"{stmt!r}: {why}"))

    # 8 banned claims
    for b in BANNED:
        if b in low:
            fails.append((8, f"banned {b!r}"))
    if "i saved" in low and a != "SAVED":
        fails.append((8, "'I saved' outside SAVED"))
    if any(b in low for b in BACKWARDS):
        fails.append((8, "backwards anchor without inverse provenance"))

    # 9 scorer anchors kept (registered in PASSMARKS)
    if legacy is not None:
        va = a in VALUE_ACTS
        an, al = anchors(body, va), anchors(legacy, va)
        if a == "REVERSE" and an.get("extract") and al.get("extract"):
            # 'V is the R of S': the extract is 'the R of S'; only the
            # relation words may differ ('educated at' -> 'alma mater'),
            # the names in it must stay the same
            p = (fr.get("path") or [""])[-1]
            rel_words = {w.lower() for q in (p, SAY.display_noun(p, row))
                         for w in words(q)}
            an["extract"] = " ".join(w for w in an["extract"].split()
                                     if w not in rel_words)
            al["extract"] = " ".join(w for w in al["extract"].split()
                                     if w not in rel_words)
        for k in al:
            if an.get(k) != al.get(k):
                fails.append((9, f"anchor {k}: {al.get(k)!r} -> {an.get(k)!r}"))
    return (not fails), fails
