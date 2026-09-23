#!/usr/bin/env python3
"""Exp 269 -- text-level group-owner check (the ONE change on 265's arm A).

Runs on the raw turn BEFORE the ear frames and the brake are used. It fires
iff the turn states something owned or shared by we/us/our/ours (not "I/my",
not a named person). When it fires, the turn gets 265's fixed ask-whose line
and no group-owned frame is saved; mixed turns (group fact + named or
first-person fact) still save the non-group frames through 265's pipeline
exactly (checker prompt B at theta 0.25 + 261b span guard).

Saving rule (sealed interpretation, see PASSMARKS): the check changes only
the ASK trigger. Group-subject TEACH frames never save (265's divert,
unchanged); every other frame flows through 265's arm A byte-identically, so
arm A saves are byte-identical to A265 saves by construction (M3/M4/M7/M8
guard this). When the divert already asks, its per-frame reply is used;
when only the text check fires, the generic reply below is used (it passes
265's sealed asks_whose shape check: starts "Whose ", ends with the fixed
tail).

Rules (fixed before the seal from table-v2 relation vocabulary and general
knowledge; tuned only on the builder's own dev turns, never any panel):
- P1: "our" + ownable noun within 3 words (pets, home/kin/vehicle/work/
  school/place/language words; "meeting/team/quiz/bus" etc. are not ownable).
- P2a: "we" + residence/work/school/ownership verb (live, own, reside;
  work needs at/for/in; "live to", "own up", "attend to" excluded).
- P2b: "we" + acquisition verb (have, bought, keep, adopted, raised,
  built, got, made, found, chose, rent, share, ...) with an ownable noun
  within 4 ("have lunch", "got home", "made our escape" stay out; "at
  home" never counts as the owned thing).
- P2c: "we" + study/speak with at/for, an ownable object, or a capitalized
  word nearby ("study late" stays out; "study Frisian" fires).
- P3: relative-clause ownership -- an ownable noun before "we"/"our" with
  an ownership verb within 3 after ("the boat we bought", "the school
  our cousins attend"); work needs at/for/in.
- P4: "ours" possessives -- "at/to ours" (locative); "ours is the <ownable>";
  "<ownable> of ours"; "<ownable> is ours" ("the choice/fault/win is ours"
  stays out); "ourselves" with an ownable noun nearby.
- P5a: "us two/three/.../all/both" + share/own/have/... + ownable noun
  ("us three share a car" fires; "us three share a birthday" stays out).
- P5b: transfer to us -- gave/sent/bought/got/left/brought + us + ownable
  ("left us a cottage" fires; told/asked/showed/taught + us never fires).
- N1 (quote guard): when a speech verb with a capitalized name attributes
  the turn and every ownership match sits inside "..." quotes, the check
  stays silent (somebody else's quoted "our" is not the speaker's group).
- Bare "us"/"we"/"our" with no ownership pattern never fires (covers
  "we met", "we think Ana is ...", "our meeting is at 3", "with us",
  first-person and named turns by construction).

Fictional names only in dev. Deterministic (no model calls).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ear265_canon as C265  # noqa: E402  (read-only; reply shape only)

GROUP_WORDS = frozenset({"we", "us", "our", "ours", "ourselves"})

# Everyday nouns whose "our"-possession states a saveable group fact
# (relation-table-v2 vocabulary + common synonyms; event/abstract nouns
# such as meeting, team, quiz, bus, trip, choice, fault are absent).
OWNABLE = frozenset({
    "dog", "dogs", "cat", "cats", "rabbit", "rabbits", "bunny", "bunnies",
    "bird", "birds", "parrot", "parrots", "fish", "hamster", "hamsters",
    "puppy", "puppies", "kitten", "kittens", "kitty", "foal", "calf",
    "lamb", "lambs", "chick", "chicks", "goat", "goats", "sheep", "horse",
    "horses", "pony", "ponies", "duck", "ducks", "chicken", "chickens",
    "tortoise", "turtle", "lizard", "snake", "pet", "pets", "hound", "pup",
    "house", "houses", "home", "homes", "flat", "flats", "apartment",
    "apartments", "cottage", "cottages", "cabin", "cabins", "bungalow",
    "hut", "place", "residence", "dwelling", "address", "door", "garden",
    "gardens", "yard", "yards", "land", "farm", "farms", "plot", "orchard",
    "field", "fields", "household",
    "son", "sons", "daughter", "daughters", "child", "children", "kid",
    "kids", "baby", "babies", "mother", "mothers", "father", "fathers",
    "parent", "parents", "brother", "brothers", "sister", "sisters",
    "sibling", "siblings", "cousin", "cousins", "uncle", "uncles", "aunt",
    "aunts", "nephew", "nephews", "niece", "nieces", "grandma", "grandmas",
    "grandpa", "grandpas", "grandmother", "grandfathers", "grandfather",
    "husband", "husbands", "wife", "wives", "spouse", "spouses", "partner",
    "partners", "family", "families", "twin", "twins", "bride", "groom",
    "surname", "landlord", "landlords", "neighbour", "neighbours",
    "neighbor", "neighbors", "friend", "friends", "roommate", "roommates",
    "colleague", "colleagues",
    "car", "cars", "boat", "boats", "canoe", "canoes", "bike", "bikes",
    "bicycle", "truck", "trucks", "van", "vans", "vehicle", "vehicles",
    "yacht", "ship", "kayak", "motorbike", "scooter", "trailer", "caravan",
    "boss", "bosses", "teacher", "teachers", "professor", "employer",
    "workplace", "office", "offices", "school", "schools", "college",
    "university", "bakery", "shop", "shops", "store", "stores", "firm",
    "company", "business", "studio", "clinic", "hospital", "library",
    "restaurant", "cafe", "hotel", "doctor", "lawyers", "lawyer", "dentist",
    "vet", "priest", "vicar", "principal",
    "city", "cities", "town", "towns", "village", "villages", "country",
    "hometown", "island", "neighborhood", "neighbourhood",
    "language", "languages", "tongue",
})

# "we" + verb with no object check (residence/ownership verbs).
WE_TIER_A = frozenset({
    "live", "lives", "lived", "reside", "resides", "resided", "own", "owns",
    "owned", "work", "works", "worked", "attend", "attends", "attended",
})
# "we" + verb needing an ownable noun within 4 words after.
WE_TIER_B = frozenset({
    "share", "shares", "shared", "rent", "rents", "rented",
    "have", "has", "bought", "buy", "buys", "buying", "keep", "keeps",
    "kept", "keeping", "adopted", "adopt", "adopts", "raised", "raise",
    "raises", "build", "builds", "built", "building", "got", "get", "gets",
    "getting", "made", "make", "makes", "making", "found", "find", "finds",
    "chose", "choose", "picks", "picked", "pick",
})
# "we" + study/speak with a guarded object check (see study_speak_fires).
WE_STUDY_SPEAK = frozenset({
    "study", "studies", "studied", "speak", "speaks", "spoke", "spoken",
})
# Ownership verbs for the relative-clause pattern.
REL_VERBS = WE_TIER_A | WE_TIER_B | WE_STUDY_SPEAK | frozenset({
    "named", "names", "name", "called", "call", "calls", "calling",
    "drive", "drives", "sail", "sails", "sailed", "grew", "grow", "grows",
    "carved", "carve",
})
# Transfer-to-us verbs ("told/asked/showed/taught" are NOT here).
TRANSFER_VERBS = frozenset({
    "gave", "give", "gives", "given", "sent", "send", "sends", "bought",
    "buy", "buys", "got", "get", "gets", "left", "leave", "leaves",
    "brought", "bring", "brings",
})
COLLECTIVE = frozenset({"two", "three", "four", "five", "six", "all", "both"})
COLLECTIVE_VERBS = frozenset({
    "share", "shares", "own", "owns", "have", "has", "bought", "keep",
    "keeps", "live", "lives", "rent", "rents",
})
SPEECH_VERBS = frozenset({
    "said", "says", "say", "told", "tells", "tell", "asked", "asks", "ask",
    "replied", "reply", "replies", "shouted", "whispered", "wrote",
    "write", "writes", "calls", "called",
})
LOC_PREP = frozenset({"at", "to"})
WORK_PREP = frozenset({"at", "for", "in"})
BE_WORDS = frozenset({"is", "are", "was", "were", "become", "became"})

GENERIC_ASK = "Whose is it? Tell me whose, and I'll remember it."


def toks(turn):
    out = []
    for m in re.finditer(r"[A-Za-z']+", turn):
        w = m.group(0)
        out.append({"raw": w, "low": w.lower(), "start": m.start(),
                    "end": m.end()})
    return out


def base(wlow):
    if wlow in OWNABLE:
        return wlow
    if wlow.endswith("'s"):
        wlow = wlow[:-2]
        if wlow in OWNABLE:
            return wlow
    if wlow.endswith("'"):
        wlow = wlow[:-1]
        if wlow in OWNABLE:
            return wlow
    if wlow.endswith("s") and len(wlow) > 3 and wlow[:-1] in OWNABLE:
        return wlow[:-1]
    if wlow.endswith("es") and len(wlow) > 4 and wlow[:-2] in OWNABLE:
        return wlow[:-2]
    return None


def quoted_spans(turn):
    return [(m.start(), m.end())
            for m in re.finditer(r'"[^"]*"', turn)]


def in_spans(pos, spans):
    return any(s <= pos < e for s, e in spans)


def has_speech_attribution(tokens):
    lows = [t["low"] for t in tokens]
    for i, w in enumerate(lows):
        if w in SPEECH_VERBS:
            lo, hi = max(0, i - 6), min(len(tokens), i + 7)
            for j in range(lo, hi):
                if re.fullmatch(r"[A-Z][a-z]{2,}", tokens[j]["raw"]):
                    return True
    return False


def nxt_next_is(lows, vi, n, word):
    return vi + 1 < n and lows[vi + 1] == word


def is_locative_home(lows, i):
    return lows[i] == "home" and i >= 1 and lows[i - 1] == "at"


def check(turn):
    """Return (fires, reasons). Fires iff the raw turn states something
    owned or shared by we/us/our/ours. Deterministic; no model calls."""
    tokens = toks(turn)
    lows = [t["low"] for t in tokens]
    n = len(tokens)
    if not any(w in GROUP_WORDS for w in lows):
        return False, ["no-group-word"]
    spans = quoted_spans(turn)
    attributed = has_speech_attribution(tokens)
    hits = []

    def ownable_at(i):
        if 0 <= i < n:
            if is_locative_home(lows, i):
                return False
            return base(lows[i]) is not None
        return False

    def ownable_within(lo, hi):
        for i in range(max(0, lo), min(n, hi)):
            if is_locative_home(lows, i):
                continue
            if base(lows[i]) is not None:
                return i
        return None

    def is_cap(i):
        return bool(re.fullmatch(r"[A-Z][A-Za-z']*", tokens[i]["raw"]))

    def study_speak_fires(i):
        for k in range(i + 1, min(n, i + 3)):
            if lows[k] in ("at", "for"):
                return True
        if ownable_within(i + 1, i + 5) is not None:
            return True
        for k in range(i + 1, min(n, i + 4)):
            if is_cap(k):
                return True
        return False

    def p3_scan(i):
        if ownable_within(i - 5, i) is None:
            return
        for k in range(i + 1, min(n, i + 4)):
            if lows[k] in REL_VERBS:
                if lows[k] in ("work", "works", "worked") and not any(
                        lows[t] in WORK_PREP
                        for t in range(k + 1, min(n, k + 3))):
                    continue
                if lows[k] in ("attend", "attends", "attended") and nxt_next_is(lows, k, n, "to"):
                    continue
                if not any(h[0] == i and h[1].startswith("P3") for h in hits):
                    hits.append((i, f"P3 {lows[k]}"))
                break

    for i, w in enumerate(lows):
        if w == "our":
            j = ownable_within(i + 1, i + 4)
            if j is not None:
                hits.append((i, f"P1 our+{lows[j]}"))
            p3_scan(i)
        elif w == "we":
            nxt = lows[i + 1] if i + 1 < n else ""
            if nxt in WE_TIER_A:
                if nxt in ("live", "lives", "lived") and nxt_next_is(
                        lows, i + 1, n, "to"):
                    pass
                elif nxt in ("own", "owns", "owned") and nxt_next_is(
                        lows, i + 1, n, "up"):
                    pass
                elif nxt in ("work", "works", "worked") and not any(
                        lows[k] in WORK_PREP
                        for k in range(i + 2, min(n, i + 4))):
                    pass
                elif nxt in ("attend", "attends", "attended") and nxt_next_is(
                        lows, i + 1, n, "to"):
                    pass
                else:
                    hits.append((i, f"P2a we+{nxt}"))
            elif nxt in WE_TIER_B:
                if nxt in ("got", "get", "gets", "getting") and i + 2 < n and lows[i + 2] == "home":
                    pass
                else:
                    j = ownable_within(i + 2, i + 6)
                    if j is not None:
                        hits.append((i, f"P2b we+{nxt}+{lows[j]}"))
            elif nxt in WE_STUDY_SPEAK:
                if study_speak_fires(i):
                    hits.append((i, f"P2c we+{nxt}"))
            p3_scan(i)
        elif w == "us":
            if i + 1 < n and lows[i + 1] in COLLECTIVE:
                for k in range(i + 2, min(n, i + 7)):
                    if lows[k] in COLLECTIVE_VERBS:
                        j = ownable_within(k + 1, k + 7)
                        if j is not None:
                            hits.append((i, f"P5a us+{lows[i+1]}+{lows[k]}+{lows[j]}"))
                        break
        elif w == "ours":
            if i >= 1 and lows[i - 1] in LOC_PREP:
                hits.append((i, f"P4 {lows[i-1]}-ours"))
            else:
                if i + 1 < n and lows[i + 1] in BE_WORDS:
                    j = ownable_within(i + 2, i + 6)
                    if j is not None:
                        hits.append((i, f"P4 ours-is+{lows[j]}"))
                hit = False
                for k in range(max(0, i - 3), i):
                    if ownable_at(k):
                        hits.append((i, f"P4 {lows[k]}-of-ours"))
                        hit = True
                        break
                if not hit and i >= 1 and lows[i - 1] in BE_WORDS:
                    j = ownable_within(i - 5, i - 1)
                    if j is not None:
                        hits.append((i, f"P4 {lows[j]}-is-ours"))
        elif w == "ourselves":
            j = ownable_within(i - 4, i)
            if j is None:
                j = ownable_within(i + 1, i + 5)
            if j is not None:
                hits.append((i, f"P4 ourselves+{lows[j]}"))

    for i, w in enumerate(lows):
        if w in TRANSFER_VERBS:
            for u in range(i + 1, min(n, i + 5)):
                if lows[u] == "us":
                    j = ownable_within(u + 1, u + 7)
                    if j is not None:
                        hits.append((u, f"P5b {w}-us+{lows[j]}"))
                    break

    if not hits:
        return False, ["no-ownership-pattern"]
    if attributed and spans:
        outside = [h for h in hits
                   if not in_spans(tokens[h[0]]["start"], spans)]
        if not outside:
            return False, ["quoted-attributed"]
    return True, sorted({r for _, r in hits})


def turn_reply(fires, divert_reply):
    """Arm-A reply: 265's diverted reply when it asks, else the generic
    ask line when only the text check fires, else ''."""
    if divert_reply and C265.asks_whose(divert_reply):
        return divert_reply
    if fires:
        return GENERIC_ASK
    return ""


assert C265.asks_whose(GENERIC_ASK), "generic reply must pass the ask check"
