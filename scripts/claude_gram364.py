#!/usr/bin/env python3
"""gram-364: fill-in finisher v2 (grammar thread, 2026-09-25).

Why: after gram-360 a blind strict grader still flagged 41 of 234 DEV fill-in lines (DEV runs of 330a/330c/lis
arms, rendered by gram-360; scratchpad g364). About 24 of them carry nonsense the reader stored ("allergy is
talking", "granddaughter is this"); the finisher cannot repair meaning and leaves those alone (reading thread).
The rest are rendering misses gram-360 made or left:
  1. the catch-all relation "other" said as "V goes with O" reads as garbled (7 lines); now
     'your note about O says "V"' / 'does your note about O say "V"?';
  2. a value "you" in question order ("is Saoirse's child you?") should turn round ("are you Saoirse's child?");
  3. a pet's name under an animal relation stays lowercase when it is also a common word ("hamster sprout");
  4. a lowercase owner that is an animal noun gets a capital as if it were a name ("Hamster"): now "the hamster";
  5. short acronyms inside a value stay lowercase ("er nurse");
  6. a thing value misses "a"/"an" when its first word ends in -ed/-ing ("bearded dragon") or the relation is
     "employer" ("warehouse").

What (one change): realise364 replaces gram-360's realise inside the same layer (install_gram364 records and
installs exactly as gram-360 does). Every slot's letters and every scorer marker ("Saved:", "Just to check",
"is that right?", "yours or someone else's") are kept, so no notebook write, confirm or score can change.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gram360 as G  # noqa: E402

ANIMAL_HEADS = set("""
pet dog puppy cat kitten hamster gerbil parrot cockatiel budgie rabbit bunny horse pony fish goldfish lizard
gecko snake turtle tortoise ferret bird chicken hen goat cow dragon pig
""".split())
ACRONYMS = {"er": "ER", "icu": "ICU", "hr": "HR", "nhs": "NHS", "ceo": "CEO", "cfo": "CFO", "cto": "CTO",
            "ups": "UPS", "nasa": "NASA", "ui": "UI", "ux": "UX", "qa": "QA", "pe": "PE", "gp": "GP"}
THING_RELS364 = G.THING_RELS | {"employer", "workplace", "job"}
# Words that describe an animal's state, not its name ("is your dog limping?", "is your cat sick?").
STATES = set("""
sick ill old young fine ok okay better worse sleepy hungry tired happy sad lost missing dead alive healthy
pregnant blind deaf shy friendly grumpy lazy fat small big tiny huge
""".split())


def _acronyms(v: str) -> str:
    ws = v.split(" ")
    if len(ws) < 2:
        return v
    return " ".join(ACRONYMS.get(w, w) for w in ws)


def _article364(v: str, rel: str) -> str:
    ws = v.split()
    if (rel.replace("_", " ").lower() in THING_RELS364 and 0 < len(ws) <= 2 and v == v.lower()
            and all(w in G.LOWER and w not in G.NOT_NAMES for w in ws)
            and not ws[-1].endswith(("ing", "ed", "ly", "s")) and ws[0] not in G.CAPS):
        return ("an " if ws[0][0] in "aeiou" else "a ") + v
    return v


def _animal(rel: str) -> bool:
    ws = rel.replace("_", " ").replace("-", " ").lower().split()
    return bool(ws) and ws[-1] in ANIMAL_HEADS and ws[-1] != "pet"


def render_value(v: str, rel: str, seen: set[str]) -> tuple[str, bool]:
    s = v.strip()
    if (G._wordy(s) and len(s.split()) == 1 and _animal(rel) and s not in G.NOT_NAMES and s not in STATES
            and not (s in G.LOWER and s.endswith(("ing", "ed", "ly")))):
        return G.cap_name(s), False                   # "your hamster is sprout": an animal's name
    out, plural = G.render_value(v, rel, seen)
    if out == G.cap_always(s) or out == s:            # not a name: acronyms and articles
        out = _article364(_acronyms(out), rel)
    return out, plural


def render_owner(o: str, seen: set[str]) -> tuple[str, bool]:
    low = o.lower()
    if low in G.PRONOUN_OWNER:
        return G.PRONOUN_OWNER[low], True
    if o == low and low in ANIMAL_HEADS and o not in seen:
        return "the " + o + "'s", False                # "hamster's other" -> "the hamster's"
    if o == low and re.fullmatch(r"[^\W\d_][^\W\d_'\-]*", o):
        o = G.cap_name(o)
    return o + "'s", False


def _phrase(owner: str | None, rel: str, val: str, seen: set[str], form: str) -> str:
    v, plural = render_value(val, rel, seen)
    o = "your" if owner is None else render_owner(owner, seen)[0]
    if rel.replace("_", " ").lower() == "other":
        note = "your note" if o == "your" else "your note about " + (o[:-2] if o.endswith("'s") else o)
        return f'does {note} say "{v}"' if form == "q" else f'{note} says "{v}"'
    r = G.rel_words(rel)
    if v == "you" and not plural:                    # "is Saoirse's child you?" -> "are you Saoirse's child?"
        return f"are you {o} {r}" if form == "q" else f"you are {o} {r}"
    verb = "are" if plural else "is"
    return f"{verb} {o} {r} {v}" if form == "q" else f"{o} {r} {verb} {v}"


def _sub(m: re.Match, form: str, seen: set[str]) -> str:
    g = m.groupdict()
    pre, post = g["pre"], g["post"]
    if form == "whose":
        v, plural = render_value(g["val"], g["rel"], seen)
        return f"{pre}{G.rel_words(g['rel'])} {'are' if plural else 'is'} {v}{post}"
    owner = None if g.get("your") else g.get("own")
    if form == "q":
        rel, val = G._split_rel_val(g["rest"])
        if not val:
            return m.group(0)
        body = _phrase(owner, rel, val, seen, "q")
    else:
        body = _phrase(owner, g["rel"], g["val"], seen, "is")
    return pre + body + post


def realise364(part: str, seen: set[str] | None = None) -> str:
    """gram-360's realise with the v2 slot rendering. Pure function."""
    seen = seen or set()
    s = part
    for pat, form in G.PATTERNS:
        s = pat.sub(lambda m, f=form: _sub(m, f, seen), s)
    s = G._counts(s)
    s = G._questions(s)
    s = G._caps(s)
    return s


record_inner364 = G.record_inner360


def install_gram364(loop) -> None:
    """As install_gram360, rendering the rule agent's parts with realise364."""
    inner = loop.turn
    loop.gram360_stats = {"turns": 0, "parts_seen": 0, "parts_changed": 0}
    seen: set[str] = set()

    def turn_gram(text: str) -> list[str]:
        loop.gram360_inner = []
        seen.update(G.names_seen(text))
        parts = inner(text)
        rule = set(getattr(loop, "gram360_inner", []) or [])
        loop.gram360_stats["turns"] += 1
        out, log = [], []
        for p in parts or []:
            if p and p in rule:
                loop.gram360_stats["parts_seen"] += 1
                q = realise364(p, seen)
                if q != p:
                    loop.gram360_stats["parts_changed"] += 1
                out.append(q)
                log.append({"rule": True, "raw": p, "final": q})
            else:
                out.append(p)
                log.append({"rule": False, "raw": p, "final": p})
        path = os.environ.get("GRAM360_LOG")
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"dir": str(getattr(loop, "dir", "")), "text": text, "parts": log},
                                   ensure_ascii=False) + "\n")
        return out

    turn_gram.__name__ = "turn_gram364"
    loop.turn = turn_gram
