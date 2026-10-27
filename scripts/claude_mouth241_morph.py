#!/usr/bin/env python3
"""Exp 241 (mouth stage A) -- morphology helpers. Pure functions, no state.

Every helper here is unit-tested in scripts/claude_mouth241_test.py.
Sealed style choices (240 section 3.1):
  * a/an by SOUND, with a closed exception list;
  * no article on proper names; common-noun values (jobs) take a/an;
  * possessive X's for every singular name, including names ending in s
    ("Silas's"); callers PREFER the verb or "of" form when a name ends in
    s, x or z (ends_sxz);
  * lists "A", "A and B", "A, B and C" -- no Oxford comma;
  * counts: 0 / 1 / many with the right noun number; numbers 0-9 as words
    in running text, 10+ as digits; values, ids and dates copied verbatim;
  * pronouns: only I/me/my (self) and you/your (user); never he/she/they;
  * sentence case and final punctuation fixed once, at the end.
"""
from __future__ import annotations

import re

NUM_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
             "eight", "nine")

# ------------------------------------------------------------------ a / an
# Words that start with a vowel LETTER but a consonant SOUND take "a".
_A_EXCEPT = ("uni", "use", "usu", "uten", "uter", "util", "euro", "eu",
             "ewe", "one", "once", "ufo", "ukr", "ura", "uri", "uro")
# Words that start with a consonant LETTER but a vowel SOUND take "an".
_AN_EXCEPT = ("hour", "honest", "honor", "honour", "heir", "herb")
# Letter names that begin with a vowel sound (for acronyms: an MRI, an FBI).
_VOWEL_LETTERS = set("AEFHILMNORSX")


def a_an(word: str) -> str:
    """'a' or 'an' for the word that follows, decided by sound."""
    w = str(word).strip()
    if not w:
        return "a"
    first = w.split()[0]
    low = first.lower()
    if first[0].isdigit():
        digits = re.match(r"\d+", first).group(0)
        if digits.startswith("8") or digits in ("11", "18") or (
                len(digits) in (5, 6) and digits[:2] in ("11", "18")):
            return "an"
        return "a"
    letters = re.sub(r"[^A-Za-z]", "", first)
    if len(letters) >= 2 and letters.isupper():  # acronym: letter names
        return "an" if letters[0] in _VOWEL_LETTERS else "a"
    if any(low.startswith(p) for p in _AN_EXCEPT):
        return "an"
    if any(low.startswith(p) for p in _A_EXCEPT):
        return "a"
    return "an" if low[:1] in "aeiou" else "a"


def with_article(noun: str) -> str:
    """'a baker', 'an engineer', 'an hour', 'a university'."""
    return f"{a_an(noun)} {noun}"


# ------------------------------------------------------------ names, "the"
# Proper names that take "the" in running text (closed list).
_THE_NAMES = {
    "united kingdom", "united states", "united states of america",
    "united arab emirates", "netherlands", "philippines", "bahamas",
    "gambia", "czech republic", "dominican republic", "maldives",
    "central african republic", "solomon islands", "marshall islands",
    "faroe islands", "cayman islands", "seychelles",
}


def needs_the(name: str) -> bool:
    n = " ".join(str(name).split()).lower()
    return n in _THE_NAMES


def show_name(name: str) -> str:
    """A proper name as it should appear mid-sentence ('the Netherlands')."""
    n = " ".join(str(name).split())
    if needs_the(n):
        return "the " + n
    return n


def ends_sxz(name: str) -> bool:
    n = str(name).strip().rstrip(".")
    return bool(n) and n[-1].lower() in "sxz"


def possessive(name: str) -> str:
    """X's for any singular name, including names ending in s."""
    n = show_name(name)
    if n.endswith("'s") or n.endswith("’s"):
        return n
    return n + "'s"


# -------------------------------------------------------------- plurals
_IRREGULAR = {"child": "children", "grandchild": "grandchildren",
              "person": "people", "man": "men", "woman": "women",
              "mouse": "mice", "goose": "geese", "wife": "wives",
              "godchild": "godchildren", "stepchild": "stepchildren"}


def plural(noun: str) -> str:
    """Plural of a common noun or noun phrase (last word inflected).
    'place of birth' -> 'places of birth'; 'best friend' -> 'best friends'."""
    n = str(noun).strip()
    if " of " in n:
        head, tail = n.split(" of ", 1)
        return plural(head) + " of " + tail
    words = n.split()
    if not words:
        return n
    last = words[-1]
    low = last.lower()
    if low in _IRREGULAR:
        new = _IRREGULAR[low]
    elif re.search(r"(s|x|z|ch|sh)$", low):
        new = last + "es"
    elif re.search(r"[^aeiou]y$", low):
        new = last[:-1] + "ies"
    else:
        new = last + "s"
    return " ".join(words[:-1] + [new])


# ---------------------------------------------------------------- lists
def join_list(items) -> str:
    """'' / 'A' / 'A and B' / 'A, B and C' (no Oxford comma)."""
    xs = [str(x).strip() for x in items if str(x).strip()]
    if not xs:
        return ""
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + " and " + xs[-1]


# --------------------------------------------------------------- counts
def num_text(n: int) -> str:
    """Numbers 0-9 as words, 10+ as digits (running text only)."""
    n = int(n)
    if 0 <= n <= 9:
        return NUM_WORDS[n]
    return str(n)


def count_phrase(n: int, singular: str, plural_form: str | None = None) -> str:
    """'one fact', 'two facts', '12 facts'. 0 is the caller's job (it needs
    its own sentence); this helper still renders 'no facts' for n == 0."""
    n = int(n)
    pl = plural_form or plural(singular)
    if n == 0:
        return f"no {pl}"
    if n == 1:
        return f"one {singular}"
    return f"{num_text(n)} {pl}"


def times_phrase(n: int) -> str:
    n = int(n)
    if n == 0:
        return "never"
    if n == 1:
        return "once"
    if n == 2:
        return "twice"
    return f"{num_text(n)} times"


# ------------------------------------------------------ sentence finish
_SENT_START = re.compile(r"(^|[.!?]\)?\s+|^\()([a-z])")


_ABBREV = {"inc", "jr", "sr", "co", "corp", "ltd", "st", "dr", "mr", "mrs",
           "ms", "mt", "bros", "vs", "etc", "no", "ft", "sq", "ave", "plc"}


def _after_abbrev(before: str) -> bool:
    """True when the period just before a match ends an abbreviation or an
    initial ('Apple Inc.', 'Washington, D.C.', 'J.', 'S.p.A.'), not a
    sentence."""
    m = re.search(r"([A-Za-z.]+)\.\)?\s*$", before)
    if not m:
        return False
    tok = m.group(1)
    if tok.lower() in _ABBREV or len(tok) == 1:
        return True
    return bool(re.fullmatch(r"(?:[A-Za-z]{1,2}\.)+[A-Za-z]{0,2}", tok))


def sentence_case(text: str) -> str:
    """Capitalise the first letter of every sentence. Text after a colon
    is left alone. Names are never lower-cased. A period that ends an
    abbreviation or initial is not a sentence end."""
    text = str(text)

    def up(m):
        if m.start() > 0 and _after_abbrev(text[:m.start() + len(m.group(1))]
                                           .rstrip()):
            return m.group(0)
        return m.group(1) + m.group(2).upper()
    return _SENT_START.sub(up, text)


def finish(text: str) -> str:
    """Fix final punctuation once: collapse whitespace, drop doubled
    terminal dots ('D.C..' -> 'D.C.'), make sure the text ends with . ? !
    or a closing parenthesis/quote that follows one, then sentence case."""
    t = " ".join(str(text).split())
    if not t:
        return t
    t = re.sub(r"(?<!\.)\.\.(?!\.)", ".", t)
    # ' .' -> '.' only for real punctuation, not 'Visual Basic .NET'
    t = re.sub(r"\s+([.,?!;:])(?=\s|$|[)\"'])", r"\1", t)
    if not re.search(r"[.?!]$|[.?!][)\"']$", t):
        t = t + "."
    return sentence_case(t)


def pron(role: str, case: str = "subj") -> str:
    """Only first person (self) and second person (user)."""
    if role == "self":
        return {"subj": "I", "obj": "me", "poss": "my"}[case]
    if role == "user":
        return {"subj": "you", "obj": "you", "poss": "your"}[case]
    raise ValueError("third-party pronouns are never used (240 section 3.1)")
