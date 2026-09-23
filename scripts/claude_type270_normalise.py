#!/usr/bin/env python3
"""Exp 270 -- THE ONE CHANGE: a rule-based text normaliser in front of 263.

Base: the 263 arm (scripts/claude_loop263_agent.py, read-only). New file only.

RULE (fixed before the seal; general knowledge + pre-seal probes on 263):
The normaliser fires only when (a) the turn has no capital letters at all,
or (b) the turn has no apostrophes and an "Xs <relation>" possessive pattern
is present. Anything else passes through byte-identical (the exact same
string object content), so clean turns behave exactly like 263.

When it fires, the pass does two things, in order:
  1. Possessive fix: "Xs <relation>" -> "X's <relation>" (for words already
     ending in s: plural-looking stems take stem + "'s", e.g. "dogs" ->
     "dog's"; other s-endings take the whole word + "'s", e.g. "james" ->
     "james's", which is the shape 263 parses). Words that are common
     English (COMMON270) or pronouns are never fixed ("his mother" stays).
     Leading wh-contractions without apostrophes ("whos", "whats", ...)
     get theirs ("who's", "what's", ...) so casual questions parse.
  2. Capitals: every word that is not common English (COMMON270) is
     capitalised, except a word matching a name already in the notebook,
     which takes the notebook's stored capitalisation (notebook names win
     over COMMON270, so a stored "Will" beats the modal "will").
     Words that are common English stay lowercase -- this matters because
     263's verb shapes need lowercase verbs ("Quillan Lives In Drennor."
     does not save, "Quillan lives in Drennor." does).

Suppression (deviation D1, pre-seal, reported): trailing confirmation-check
tails (", right", ", isn't it", ", don't you think", ", yeah/yep/yes/no",
", ok/okay", ", correct", ", you know") are NOT rewritten -- the fixed text
would save a junk triple on 263 ("Zorana's mother is vexley, right" saves),
turning a no-save trap into a wrong save. Suppressed turns pass through
unchanged and behave exactly like 263. Bare "so ..."-heads are NOT
suppressed: clean "So X." saves on 263 by design (260 opener strip), so
lowercase "so x." normalises to a save like its clean form.

Known limits (pre-seal, reported): names that are common English words
("will", "mark", "hope", ...) can never be restored when lowercase;
multi-word names fail on 263 even clean; "X is a Y" is not a shape 263
saves even clean; "our/we" owners fail even clean. None of these can be
fixed by a front normaliser.
"""

from __future__ import annotations

import re

# Words that stay lowercase. Fixed before the seal from general knowledge:
# closed-class words, auxiliaries/modals, question words, the verbs 263's
# shapes need lowercase, relation nouns (harmless either way; kept natural),
# casual openers/fillers, and pretend/plan markers (lowercase is fine --
# 263 catches "Lets say"/"Suppose" capitalised too, but raw forms already
# pass through the ear unchanged only when we do not fire... they fire on
# no-capitals; keeping markers lowercase keeps the text closest to raw).
COMMON270 = frozenset("""
a an the
i me my mine myself we us our ours ourselves you your yours
he him his she her hers it its they them their theirs
this that these those
is are was were be been being am
have has had having do does did done doing
will would can could shall should may might must ought
who whom whose what which where when why how
in at on of to for from with by about as into over after before
up down out off through during under again further then once
and but or nor yet for so
not no nor never very just also too still already even only
obviously actually really probably maybe perhaps certainly surely
live lives lived living work works worked working
know knows knew known think thinks thought want wants liked like
say says said says tell tells told ask asks asked answer
get gets got give gives gave go goes went come comes came
see sees saw take takes took make makes made
my your his her its their our
hello hi hey yo oh well btw please thanks thank sorry
um uh huh yeah yep okay ok alright right
let lets suppose imagine if
mother father sister brother wife husband son daughter
parent parents child children sibling siblings spouse cousin cousins
aunt aunts uncle uncles niece nephew nephews
grandma grandpa grandmother grandfathers grandfather grandmothers
grandson grandsons granddaughter granddaughters
friend friends buddy mate neighbor neighbours neighbour boss bosses
job jobs pet pets
city town village place home house homes school schools
team teams club clubs company store shop farm
employer employee worker name names title
today tomorrow yesterday
thing things
one two three four five six seven eight nine ten first second third
my me i we us our you your he him his she her it they them their
""".split())

# Relation nouns that mark an "Xs <relation>" possessive. Fixed pre-seal.
REL270 = frozenset("""
mother father sister brother wife husband son daughter
parent parents child children sibling siblings spouse cousin cousins
aunt aunts uncle uncles niece nephew nephews
grandma grandpa grandmother grandfather grandson granddaughter
friend friends buddy mate neighbor neighbour boss bosses
job jobs pet pets dog dogs cat cats horse horses
city town village home house school team club company store shop farm
doctor teacher nurse baker employer employee name names
car bike boat photo picture
""".split())

# Words that are never possessive-fixed even before a relation noun
# (check-tails and auxiliaries whose stem is not itself common).
_NEVER_FIX270 = frozenset("""
yes no yeah yep ok okay right was has does is are were
""".split())
_WH270 = (("whos", "who's"), ("whats", "what's"), ("wheres", "where's"),
          ("whens", "when's"), ("whys", "why's"), ("hows", "how's"))

# Trailing confirmation-check tails: never rewrite (D1). Each is a regex
# applied case-insensitively to the end of the turn.
_CHECK_TAILS270 = (
    r",\s*right\s*[.?!]*$",
    r"\sright\s*[?!.]+$",
    r",\s*isn'?t\s+it\s*[.?!]*$",
    r",\s*don'?t\s+you\s+think\s*[.?!]*$",
    r",\s*yea?h\s*[.?!]*$",
    r",\s*yep\s*[.?!]*$",
    r",\s*yes\s*[.?!]*$",
    r",\s*no\s*[.?!]*$",
    r",\s*ok(ay)?\s*[.?!]*$",
    r",\s*correct\s*[.?!]*$",
    r",\s*you\s+know\s*[.?!]*$",
)
_CHECK_RES270 = tuple(re.compile(p, re.IGNORECASE)
                      for p in _CHECK_TAILS270)

_POSS_RE270 = re.compile(r"\b([A-Za-z]+)\b")

_WORD_RE270 = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

# Word-final endings where a trailing s is usually part of the name
# (Tess, Morris, Louis, James, Miles, Charles), so the possessive adds
# "'s" to the whole word. Anything else strips one s first ("zoranas" ->
# "zorana's"). Names ending in "as"/"nes" (Thomas, Lucas, June, Anne)
# strip by this rule and stay a known residual (the core Xs-possessive
# case wins the default).
_KEEP_S270 = ("ss", "us", "is", "os", "mes", "les")


def _possessive_form270(word: str, names: dict):
    """Possessive of an s-ending word, or None when it must not be fixed."""
    wl = word.lower()
    if wl in COMMON270 or wl in _NEVER_FIX270:
        return None
    if len(word) <= 2:
        return None
    if wl in names:
        return word + "'s"
    stem = word[:-1]
    if stem.lower() in names or stem.lower() in COMMON270:
        return stem + "'s"
    if wl.endswith(_KEEP_S270):
        return word + "'s"
    return stem + "'s"


def _word_runs270(text: str):
    """Consecutive letter-word spans: (word, start, end)."""
    return [(m.group(1), m.start(1), m.end(1))
            for m in _POSS_RE270.finditer(text)]


def has_possessive270(text: str, names=None) -> bool:
    """An "Xs <relation>" pattern with no apostrophe in the turn."""
    if "'" in text or "\u2019" in text:
        return False
    runs = _word_runs270(text)
    for (w, _s, _e), (rel, _s2, _e2) in zip(runs, runs[1:]):
        if not w.lower().endswith("s"):
            continue
        if rel.lower() not in REL270:
            continue
        if _possessive_form270(w, names or {}) is None:
            continue
        return True
    return False


def fire270(text: str, names=None):
    """Why the normaliser fires, or None for passthrough."""
    t = str(text)
    if any(c.isupper() for c in t):
        if has_possessive270(t, names):
            if _suppressed270(t):
                return None
            return "possessive"
        return None
    if _suppressed270(t):
        return None
    return "lowercase"


def _suppressed270(text: str) -> bool:
    return any(r.search(text) for r in _CHECK_RES270)


def _possessive_fix270(text: str, names: dict) -> str:
    runs = _word_runs270(text)
    fixes = []
    for (w, s, e), (rel, _s2, _e2) in zip(runs, runs[1:]):
        if not w.lower().endswith("s"):
            continue
        if rel.lower() not in REL270:
            continue
        poss = _possessive_form270(w, names)
        if poss is None:
            continue
        fixes.append((s, e, poss))
    out = []
    pos = 0
    for s, e, poss in fixes:
        out.append(text[pos:s])
        out.append(poss)
        pos = e
    out.append(text[pos:])
    out = "".join(out)
    for plain, apos in _WH270:
        out = re.sub(r"\b" + plain + r"\b", apos, out,
                     flags=re.IGNORECASE)
    return out


def names_from_triples270(triples) -> dict:
    """lowercase word -> stored capitalisation (prefer a cased variant)."""
    names: dict = {}
    for t in triples or []:
        for cell in (t[0] if len(t) > 0 else "",
                     t[2] if len(t) > 2 else ""):
            for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",
                                str(cell)):
                key = w.lower()
                if any(c.isupper() for c in w):
                    names[key] = w
                else:
                    names.setdefault(key, w)
    return names


def _cap_word270(w: str, names: dict) -> str:
    key = w.lower()
    if key in names:
        return names[key]
    if key in COMMON270:
        return w
    if "'" in w:
        head, sep, tail = w.partition("'")
        if not head:
            return w
        return head[:1].upper() + head[1:] + sep + tail
    return w[:1].upper() + w[1:]


def normalise270(text: str, known_names=None) -> str:
    """Rule-based pass. Returns the input unchanged when not firing."""
    t = str(text)
    names = known_names or {}
    if fire270(t, names) is None:
        return t
    fixed = _possessive_fix270(t, names)
    fixed = _WORD_RE270.sub(lambda m: _cap_word270(m.group(0), names),
                            fixed)
    return fixed
