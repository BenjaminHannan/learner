#!/usr/bin/env python3
"""Experiment 247 -- THE ONE CHANGE (cause C1 of diagnosis 243): a wider
missing-apostrophe repair for QUESTION turns.

Today (138i + 228 guard) scripts/fable_fix165_typo.py:147 repairs
"Who is Xs R?" only when R is a person relation (REL165, line 50) and X is
one word (_ASK165, line 57). So "Who is Pells spouse?", "What is Pells
city?" and "Who is Joren Hales boss?" all get the glued decline (or
"I have no opinions.").

Apos247Mixin ports the token logic of 138j's fix193
(scripts/fable_fix193_apos.py) and widens it, for turns ending in "?" only:

  * a word token W ending in "s" (no apostrophe in W), optionally preceded
    by up to two plain words, forms a candidate "P1 P2 W";
  * the stem ("P1 P2 W-minus-s", longest first) must resolve (nb.resolve)
    to exactly ONE entity already in the notebook whose DISPLAY name equals
    the stem ignoring case (alias-only matches never fire, as in 193);
  * name gate ("both could be names"): the unstripped candidate
    ("P1 P2 W") must NOT resolve (neither OK nor AMBIGUOUS), and W itself
    must not be a known alias (165 gate b);
  * the 165 plural gate (b2) is kept: W must not equal the final word of a
    known multi-word entity ("The Toms");
  * the words right after W must spell a relation ALREADY STORED for that
    entity (any live fact with that entity as subject; "_" read as a
    space; the relation's last word may carry "'s", so "Xs boss's city"
    works);
  * then "P1 P2 W" is replaced by "<Display>'s" and the rewritten turn goes
    to the unchanged base hear(). The rewrite is kept ONLY if the base
    then emits an "ask" act whose name is one of the rewritten entities;
    otherwise the ORIGINAL turn goes to the base hear() unchanged (so the
    base owns every turn this fix cannot answer, byte-identical).

No teach turn is touched (165 keeps its own teach repair). Question turns
never write. No existing file is edited; base modules are imported
read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_TOK247 = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]*)?")
_MAX_PRE247 = 2  # up to three-word names


def _norm247(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def _resolve247(nb, name: str):
    try:
        return nb.resolve(name)
    except Exception:
        return None


def _status247(found) -> str | None:
    return None if found is None else getattr(found, "status", None)


def _canonical247(nb, stem: str):
    """(entity_id, display) when stem names exactly one entity by display."""
    found = _resolve247(nb, stem)
    if _status247(found) != "OK":
        return None
    eid = (getattr(found, "detail", None) or {}).get("entity_id")
    if not eid:
        return None
    try:
        canon = (getattr(nb, "entities", {}) or {}).get(eid)
    except Exception:
        return None
    if not canon or _norm247(canon) != _norm247(stem):
        return None
    return eid, str(canon)


def _name_blocked247(nb, full: str, w: str) -> bool:
    """True when the unstripped words could themselves be a name."""
    st = _status247(_resolve247(nb, full))
    if st != "UNKNOWN_ENTITY":
        return True  # OK / AMBIGUOUS / resolve error: could be a name
    wn = _norm247(w)
    try:
        aliases = getattr(nb, "aliases", {}) or {}
    except Exception:
        aliases = {}
    if wn in aliases or _norm247(full) in aliases:
        return True
    # 165 gate (b2): W is the final word of a known multi-word entity.
    try:
        displays = list((getattr(nb, "entities", {}) or {}).values())
    except Exception:
        displays = []
    for display in displays:
        toks = _norm247(display).split()
        if len(toks) > 1 and toks[-1] == wn:
            return True
    return False


def _stored_relations247(nb, eid: str) -> list[list[str]]:
    """Relations of live facts whose subject is eid, as word lists."""
    out: set[tuple[str, ...]] = set()
    try:
        facts = nb.facts
        active = nb.active
    except Exception:
        return []
    for fid, fact in list(facts.items()):
        try:
            if fact.get("subject") != eid or not active(fid):
                continue
        except Exception:
            continue
        words = tuple(str(fact.get("relation", "")).lower()
                      .replace("_", " ").split())
        if words:
            out.add(words)
    return sorted((list(w) for w in out), key=len, reverse=True)


def _strip_s247(word: str) -> str:
    low = word.lower()
    for suf in ("'s", "’s"):
        if low.endswith(suf) and len(word) > len(suf):
            return low[:-len(suf)]
    return low


def _rel_follows247(toks, j: int, text: str, rels) -> bool:
    """Tokens from j on (whitespace-adjacent) begin with a stored relation."""
    for rel in rels:
        n = len(rel)
        if j + n > len(toks):
            continue
        ok = True
        for k in range(n):
            word, s, _e = toks[j + k]
            if k > 0 and not re.fullmatch(r"\s+", text[toks[j + k - 1][2]:s]):
                ok = False
                break
            low = word.lower()
            if k < n - 1:
                if low != rel[k]:
                    ok = False
                    break
            elif low != rel[k] and _strip_s247(word) != rel[k]:
                ok = False
                break
        if ok:
            return True
    return False


def rewrite_apos247(turn: str, nb):
    """-> (rewritten turn, [entity displays]) or None. Question turns only."""
    text = str(turn)
    if nb is None or not text.strip().endswith("?"):
        return None
    toks = [(m.group(0), m.start(), m.end()) for m in _TOK247.finditer(text)]
    if len(toks) < 2:
        return None
    edits: list[tuple[int, int, str]] = []
    names: list[str] = []
    for i, (w, _s, _e) in enumerate(toks):
        if not re.fullmatch(r"[A-Za-z]+[sS]", w) or len(w) < 3:
            continue
        if i + 1 >= len(toks):
            continue
        if not re.fullmatch(r"\s+", text[toks[i][2]:toks[i + 1][1]]):
            continue
        if edits and toks[i][1] < edits[-1][1]:
            continue
        hit = None
        for k in range(min(_MAX_PRE247, i), -1, -1):
            pre = toks[i - k:i]
            if any(not p[0].isalpha() for p in pre):
                continue
            gaps_ok = all(
                re.fullmatch(r" ", text[toks[m][2]:toks[m + 1][1]])
                for m in range(i - k, i))
            if not gaps_ok:
                continue
            stem = " ".join([p[0] for p in pre] + [w[:-1]])
            full = " ".join([p[0] for p in pre] + [w])
            canon = _canonical247(nb, stem)
            if canon is None:
                continue
            if _name_blocked247(nb, full, w):
                break  # "Xs" could itself be a name: never rewrite
            rels = _stored_relations247(nb, canon[0])
            if not rels or not _rel_follows247(toks, i + 1, text, rels):
                break
            hit = (toks[i - k][1], toks[i][2], canon[1])
            break
        if hit is None:
            continue
        if edits and hit[0] < edits[-1][1]:
            continue
        edits.append((hit[0], hit[1], "%s's" % hit[2]))
        names.append(hit[2])
    if not edits:
        return None
    out: list[str] = []
    pos = 0
    for s, e, rep in edits:
        out.append(text[pos:s])
        out.append(rep)
        pos = e
    out.append(text[pos:])
    return "".join(out), names


def _claims247(acts, names) -> bool:
    want = {_norm247(n) for n in names}
    for act in acts or []:
        if isinstance(act, dict) and act.get("act") == "ask" \
                and _norm247(act.get("name", "")) in want:
            return True
    return False


class Apos247Mixin:
    """Stackable, outermost: question-only missing-apostrophe repair.

    Cooperative: a rewrite is kept only when the base then reads it as an
    ask about the rewritten entity; every other turn (and every rewrite the
    base does not read) goes to super().hear() with the original text.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            try:
                got = rewrite_apos247(turn, nb)
            except Exception:
                got = None
            if got is not None:
                fixed, names = got
                acts = super().hear(fixed)  # type: ignore[misc]
                if _claims247(acts, names):
                    log = getattr(self, "apos247_log", None)
                    if log is None:
                        log = []
                        try:
                            self.apos247_log = log
                        except Exception:
                            pass
                    log.append({"turn": turn, "rewritten": fixed})
                    return acts
        return super().hear(turn)  # type: ignore[misc]
