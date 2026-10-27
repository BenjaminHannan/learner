#!/usr/bin/env python3
"""gram-360: finish the fixed fill-in lines so they read as proper English (grammar thread, 2026-09-25).

Why: in 336 (VERIFY-336.md, M7) and 338 (VERIFY-338.md) the 1B's own replies were ~97% grammatical, but the
rule agent's fill-in lines ("Saved: ...", "Just to check: is ...?", "I think you told me ..., is that right?",
"Whose ... is ..., yours or someone else's?", "X's R is V.") were ~82%: they paste the stored slots in raw,
so replies carry lowercase names ("your city is vancouver"), relation keys with underscores ("running_buddy"),
pronoun owners ("is she's age 84?"), Python lists ("['Sten', 'Viggo']") and "0 web row".

What (one change): install_gram360(loop) is the outermost reply layer before the nb-323 turn log. It rewrites
ONLY the parts the rule agent itself produced (recorded by record_inner360, installed right after 330a_334), so
the 1B's chat, creative and think replies are never touched. Inside those parts it only renders slots:
  1. relation keys: underscores become spaces, "mother_in_law" becomes "mother-in-law";
  2. a pronoun owner becomes a possessive ("she's age" -> "her age", "Her's father" -> "her father");
  3. a lowercase owner name is capitalised ("wyatt's age" -> "Wyatt's age");
  4. a lowercase value is capitalised only when it names someone or somewhere: the relation holds a person,
     animal, place, organisation, language or nickname (relation table v1 value kinds, plus the relation's
     head noun), or the word was seen capitalised earlier in the chat;
  5. a Python list value becomes "A and B" and its "is" becomes "are";
  6. the reader's catch-all relation "other" is said as "V goes with O" instead of "O's other is V";
  7. every sentence starts with a capital, and "0 web row" / "1 facts" agree in number;
  8. a request sentence ("Could you say it another way, like ...") ends with "?";
  9. a lowercase common noun as the value of a thing relation (pet, car, other, ...) takes "a"/"an".
Wording, markers ("Saved:", "Just to check", "is that right?", "yours or someone else's") and every slot's
letters are kept (the scorers compare lowercase), so no notebook write, confirm or score can change.
Nothing reads or writes the notebook.
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "artifacts" / "claude-relationtable-20260922" / "relation_table_v1.json"

NAME_KINDS = {"person", "place", "organization", "language"}
# Head nouns of relations that hold a name, for relation keys the reader makes up ("running_buddy",
# "climbing_gym"). General English nouns for people, animals, places and organisations.
NAME_HEADS = set("""
buddy mate pal friend bestie roommate flatmate housemate twin partner fiance fiancee fiancé fiancée girlfriend
boyfriend spouse wife husband nephew niece grandson granddaughter grandma grandpa nan nana gran granny stepmother
stepfather stepson stepdaughter stepsister stepbrother law godmother godfather godson goddaughter classmate
teammate bandmate coworker colleague neighbour neighbor landlord landlady tenant tutor therapist dentist vet
nurse doctor coach teacher boss manager supervisor mentor student pupil baby kid child son daughter sister brother
mother father mom mum dad parent aunt uncle cousin crush ex
pet dog puppy cat kitten hamster gerbil parrot cockatiel budgie rabbit bunny horse pony fish goldfish lizard
gecko snake turtle tortoise ferret guinea pig bird chicken hen goat cow bee
city town village country state county hometown home school college university campus gym studio clinic
hospital bakery cafe café restaurant shop store library church team club company employer office workplace
firm band garden park street neighbourhood neighborhood island
nickname name language
""".split())
PRONOUN_OWNER = {"she": "her", "her": "her", "he": "his", "him": "his", "his": "his", "they": "their",
                 "them": "their", "their": "their", "it": "its", "i": "your", "me": "your", "my": "your",
                 "you": "your", "your": "your"}
# Words that are never capitalised as a value even under a name relation.
NOT_NAMES = set("""
me you him her them us it this that these those none nobody someone something anyone he she they i we
my your his their our its a an the yes no not unknown kids kid children child dad mum mom mother father
parents sister brother baby
""".split())
SMALL = {"of", "the", "and", "de", "da", "van", "von", "la", "le", "du", "del", "on", "upon", "in"}


def _load_kinds() -> dict[str, str]:
    kinds: dict[str, str] = {}
    try:
        t = json.loads(TABLE.read_text(encoding="utf-8"))
    except OSError:
        return kinds
    for r in t.get("relations", []):
        for n in [r["name"]] + list(r.get("aliases", [])) + list(r.get("storage_keys", [])):
            kinds[n.replace("_", " ").lower()] = r["value_kind"]
    kinds["nickname"] = "person"                     # a nickname is a name
    return kinds


KINDS = _load_kinds()


def rel_words(rel: str) -> str:
    """'running_buddy' -> 'running buddy'; 'mother_in_law' / 'mother in law' -> 'mother-in-law'."""
    r = rel.replace("_", " ").strip()
    r = re.sub(r"\b(\w+) in law\b", r"\1-in-law", r)
    return re.sub(r"\s+", " ", r)


def name_relation(rel: str) -> bool:
    r = rel.replace("_", " ").replace("-", " ").lower().strip()
    if KINDS.get(r) in NAME_KINDS:
        return True
    if r in KINDS:
        return r == "nickname"
    words = r.split()
    return bool(words) and (words[-1] in NAME_HEADS or r in NAME_HEADS)


WORDS = ROOT / "artifacts" / "claude-gram360-20260925"


def _words(name: str) -> set[str]:
    try:
        return set((WORDS / name).read_text(encoding="utf-8").split())
    except OSError:
        return set()


# Debian's wamerican 2020.12.07-2 word list, split once: words English writes in lowercase, and words it
# writes with a capital (names, places, days). A word only in the second list is always capitalised.
LOWER, CAPS = _words("words_lower.txt"), _words("words_cap.txt")


def _wordy(v: str) -> bool:
    ws = v.split()
    return (0 < len(ws) <= 4 and v == v.lower()
            and all(re.fullmatch(r"[^\W\d_][^\W\d_'\-.]*", w) for w in ws))


def _can_be_name(w: str) -> bool:
    """Not an ordinary lowercase English word, or a word English also writes as a name ("Rose", "Young")."""
    return w not in NOT_NAMES and (w not in LOWER or w in CAPS)


def _cap_word(w: str) -> str:
    return "-".join(p[:1].upper() + p[1:] for p in w.split("-"))


def cap_name(v: str) -> str:
    ws = v.split()
    return " ".join(w if (i > 0 and w in SMALL) else _cap_word(w) for i, w in enumerate(ws))


def cap_always(v: str) -> str:
    """Capitalise the words English always writes with a capital ("saturday", "toronto")."""
    return " ".join(_cap_word(w) if (len(w) > 2 and w in CAPS and w not in LOWER) else w for w in v.split(" "))


THING_RELS = {"pet", "car", "bike", "vehicle", "instrument", "other"}


def _article(v: str, rel: str) -> str:
    """A lowercase common noun as the value of a thing relation takes "a"/"an" ("pet is a gerbil")."""
    ws = v.split()
    if (rel.replace("_", " ").lower() in THING_RELS and 0 < len(ws) <= 2 and v == v.lower()
            and all(w in LOWER and w not in NOT_NAMES and not w.endswith(("ing", "ed", "ly", "s")) for w in ws)
            and not (ws[0] in CAPS)):
        return ("an " if ws[0][0] in "aeiou" else "a ") + v
    return v


def render_value(v: str, rel: str, seen: set[str]) -> tuple[str, bool]:
    """(text, plural). Lists joined; a lowercase name in a name slot capitalised; always-capital words capitalised."""
    s = v.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            items = ast.literal_eval(s)
        except (ValueError, SyntaxError):
            items = None
        if isinstance(items, (list, tuple)) and items and all(isinstance(x, str) for x in items):
            items = [render_value(x, rel, seen)[0] for x in items]
            joined = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
            return joined, len(items) > 1
    if s.lower() in ("me", "i"):
        return "you", False
    if not _wordy(s):
        return s, False
    ws = s.split()
    if not any(w in NOT_NAMES for w in ws) and (s in seen or (name_relation(rel) and _can_be_name(ws[0]))):
        return cap_name(s), False
    return _article(cap_always(s), rel), False


def render_owner(o: str) -> tuple[str, bool]:
    """(owner phrase including possessive, is_pronoun). 'she' -> 'her'; 'wyatt' -> "Wyatt's"."""
    low = o.lower()
    if low in PRONOUN_OWNER:
        return PRONOUN_OWNER[low], True
    if o == low and re.fullmatch(r"[^\W\d_][^\W\d_'\-]*", o):
        o = cap_name(o)
    return o + "'s", False


def _split_rel_val(rest: str) -> tuple[str, str]:
    """'occupation pastry chef' -> ('occupation', 'pastry chef'): the longest known relation prefix,
    else the first word (the reader's own keys are one token with underscores)."""
    ws = rest.split()
    for k in range(len(ws) - 1, 0, -1):
        cand = " ".join(ws[:k])
        c = cand.replace("_", " ").lower()
        if c in KINDS:
            return cand, " ".join(ws[k:])
    return ws[0], " ".join(ws[1:])


def _phrase(owner: str | None, rel: str, val: str, seen: set[str], form: str) -> str:
    """form: 'is' -> "<O> <rel> is <V>"; 'q' -> "is <O> <rel> <V>" (question order)."""
    v, plural = render_value(val, rel, seen)
    if owner is None:
        o = "your"
    else:
        o, _ = render_owner(owner)
    if rel.replace("_", " ").lower() == "other":
        who = "you" if o == "your" else (o[:-2] if o.endswith("'s") else o)
        v2 = v if v[:1].isupper() or v == "you" else v
        return f"does {v2} go with {who}" if form == "q" else f"{v2} goes with {who}"
    r = rel_words(rel)
    verb = "are" if plural else "is"
    return f"{verb} {o} {r} {v}" if form == "q" else f"{o} {r} {verb} {v}"


OWNER = r"(?:(?P<own>[^\s']+)'s|(?P<your>[Yy]our))"
PATTERNS = [
    # "I think you told me X's R is V, is that right?"
    (re.compile(r"(?P<pre>I think you told me )" + OWNER + r" (?P<rel>\S+(?: \S+)*?) is (?P<val>[^,]+?)"
                r"(?P<post>, is that right\?)"), "is"),
    # "Saved: X's R is V."
    (re.compile(r"(?P<pre>Saved: )" + OWNER + r" (?P<rel>\S+(?: \S+)*?) is (?P<val>.+?)(?P<post>\.)(?=\s|$)"),
     "is"),
    # "Whose R is V, yours or someone else's?"
    (re.compile(r"(?P<pre>Whose )(?P<rel>\S+(?: \S+)*?) is (?P<val>[^,]+?)(?P<post>, yours or someone else's\?)"),
     "whose"),
    # "Just to check: is X's R V?"
    (re.compile(r"(?P<pre>Just to check: )is " + OWNER + r" (?P<rest>[^?]+?)(?P<post>\?)"), "q"),
    # answer lines at a sentence start: "X's R is V." / "Your R is V."
    (re.compile(r"(?P<pre>(?:^|(?<=[.!?] )))" + OWNER + r" (?P<rel>\S+(?: \S+)*?) is (?P<val>[^.?!]+?)"
                r"(?P<post>\.)(?=\s|$)"), "is"),
]


def _sub(m: re.Match, form: str, seen: set[str]) -> str:
    g = m.groupdict()
    pre, post = g["pre"], g["post"]
    if form == "whose":
        v, plural = render_value(g["val"], g["rel"], seen)
        return f"{pre}{rel_words(g['rel'])} {'are' if plural else 'is'} {v}{post}"
    owner = None if g.get("your") else g.get("own")
    if form == "q":
        rel, val = _split_rel_val(g["rest"])
        if not val:
            return m.group(0)
        body = _phrase(owner, rel, val, seen, "q")
    else:
        body = _phrase(owner, g["rel"], g["val"], seen, "is")
    return pre + body + post


def _counts(s: str) -> str:
    s = re.sub(r"\b1 (fact|row|web row)s\b", r"1 \1", s)
    return re.sub(r"\b(\d+) (web row|row|fact)\b", lambda m: m.group(0) if m.group(1) == "1"
                  else f"{m.group(1)} {m.group(2)}s", s)


def _questions(s: str) -> str:
    """A request sentence ("Could you ...", "Can you ...", "Would you ...") ends with "?" not ".";
    a closing quote keeps its words: 'like "Kim's boss is Lee."' -> 'like "Kim's boss is Lee"?'."""
    def fix(m: re.Match) -> str:
        body = m.group(0)
        if body.endswith('."'):
            return body[:-2] + '"?'
        return body[:-1] + "?"
    return re.sub(r'(?:(?<=^)|(?<=[.!?] ))(?:Could|Can|Would|Will) you [^?]*?(?:\.\"|\.)(?=\s|$)', fix, s)


def _caps(s: str) -> str:
    """Capitalise the first letter of every sentence."""
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), s)


def realise(part: str, seen: set[str] | None = None) -> str:
    """Render the slots of one rule-agent reply part. Pure function."""
    seen = seen or set()
    s = part
    for pat, form in PATTERNS:
        s = pat.sub(lambda m, f=form: _sub(m, f, seen), s)
    s = _counts(s)
    s = _questions(s)
    s = _caps(s)
    return s


def names_seen(text: str) -> set[str]:
    """Lowercase forms of words the user wrote capitalised mid-sentence (evidence that a word is a name)."""
    out = set()
    for m in re.finditer(r"(?<=[\w,;:'\"] )([A-Z][^\W\d_]+(?: [A-Z][^\W\d_]+)*)", text):
        out.add(m.group(1).lower())
        for w in m.group(1).split():
            out.add(w.lower())
    return out


def record_inner360(loop) -> None:
    """Install right after 330a_334: remembers the rule agent's own parts for this turn. Changes nothing."""
    inner = loop.turn

    def turn_rec(text: str) -> list[str]:
        parts = inner(text)
        loop.gram360_inner = [p for p in (parts or []) if p]
        return parts

    turn_rec.__name__ = "turn_rec360"
    loop.turn = turn_rec


def install_gram360(loop) -> None:
    """Install after vary330c and before the turn log. Only parts the rule agent produced are rendered."""
    inner = loop.turn
    loop.gram360_stats = {"turns": 0, "parts_seen": 0, "parts_changed": 0}
    seen: set[str] = set()

    def turn_gram(text: str) -> list[str]:
        loop.gram360_inner = []
        seen.update(names_seen(text))
        parts = inner(text)
        rule = set(getattr(loop, "gram360_inner", []) or [])
        loop.gram360_stats["turns"] += 1
        out, log = [], []
        for p in parts or []:
            if p and p in rule:
                loop.gram360_stats["parts_seen"] += 1
                q = realise(p, seen)
                if q != p:
                    loop.gram360_stats["parts_changed"] += 1
                out.append(q)
                log.append({"rule": True, "raw": p, "final": q})
            else:
                out.append(p)
                log.append({"rule": False, "raw": p, "final": p})
        path = os.environ.get("GRAM360_LOG")
        if path:                                     # report-only sidecar: which parts were rule-agent parts
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"dir": str(getattr(loop, "dir", "")), "text": text, "parts": log},
                                   ensure_ascii=False) + "\n")
        return out

    turn_gram.__name__ = "turn_gram360"
    loop.turn = turn_gram
