"""Exp 252 THE ONE CHANGE: corrections and denials (safety first).

The gap (reproduced on 138k, see design/v3/30-modes/252-correct-opus.md):
"X doesn't work at Y.", "Y isn't X's boss.", "That's wrong." and
"No, it's Z." all get the generic shape decline and the disputed fact stays
stored, so the next question repeats the value the user refused.

What this mixin does (outermost on the loop's inner ears, plus a small loop
mixin that remembers the previous reply and routes one new action):

1. Denial of a named fact ("X doesn't work at Y.", "X no longer lives in Y.",
   "Y isn't X's boss.", "That's not true, X doesn't ..."). The negation is
   stripped (and "Y is X's R" is turned round to "X's R is Y"); the positive
   sentence is then parsed by the EXISTING ears (super().hear) -- no new
   sentence grammar decides the name, relation or value. If exactly that
   (X, R, Y) is a stored taught fact, it is removed through 154f's own
   retraction path (Negate154fActMixin._act_negate_one138j -> nb.retract,
   the path "X's boss is not Y." uses), so the notebook and the 220 index
   stay right. Otherwise nothing is written and the reply says so.
2. Contextual denial ("That's wrong.", "No, that's not right."): acts only
   when the previous reply stated exactly ONE stored taught fact, the
   previous turn wrote nothing, and no question is pending. Otherwise it
   writes nothing and asks which fact is wrong.
3. Contextual correction ("No, it's Z.", "No, she lives in Z now."): same
   one-fact condition, plus the relation has exactly that one value, and Z
   passes a strict value screen here AND the base's own screens. The change
   is made by handing the canonical sentence "No, S's R is Z." to the base
   ears (super().hear) and returning the base's own correction action only
   if it parsed back to exactly (S, R, Z). Nothing here writes the notebook.
4. Explicit correction ("Actually, X lives in Z, not Y.", "X doesn't work
   at Y, X works at Z.", "I was wrong, X speaks Z."): the same canonical
   hand-off, only when (X, R, Y) is stored as the relation's one value.
   If the base already turns the sentence into a correction, the base
   actions are returned unchanged. Otherwise the base behaviour stands.
5. Questions never reach any of this (anything ending "?" or opening with
   an auxiliary / wh-word falls straight through to the base).
6. Inferred replies (answers built from 2+ relations) are never stored:
   the reply says it was worked out from other facts and asks which taught
   fact is wrong. 7. The user's own facts ("my ...", USER) are never
   touched: the base confirm flow stays. 8. Removal is a notebook
   retraction, so reverse lookups and restarts follow the notebook.

No existing file is edited. Installed per instance (class swap), like 251.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_valueguard as V139B  # noqa: E402 (read-only)
import fable_fix154b_multival as M154  # noqa: E402 (read-only)
import fable_fix154f_negate as N154F  # noqa: E402 (read-only)
import fable_loop189b_agent as L189B  # noqa: E402 (read-only)
import fable_notebook_contract as C  # noqa: E402 (read-only)

STAGE252 = "correct252"
ACT252 = "negate252"

# ------------------------------------------------------------ word lists
_AUX = (r"is|isn't|was|wasn't|are|aren't|were|weren't|do|does|did|don't|"
        r"doesn't|didn't|can|can't|could|couldn't|will|won't|would|"
        r"wouldn't|should|shouldn't|has|hasn't|have|haven't|had|hadn't|"
        r"who|whom|whose|what|where|when|why|how|which")
_QLEAD = re.compile(
    rf"^\s*(?:(?:so|and|but|wait|hmm+|um+|ok|okay|well|hey|hi)\s*[,.]?\s+)*"
    rf"(?:{_AUX}|is it true|tell me)\b", re.IGNORECASE)

# Prefixes that say "the fact is wrong" (a denial signal).
_DENY = [
    r"that'?s not (?:true|right|correct|it|so)",
    r"that is not (?:true|right|correct|it|so)",
    r"that isn'?t (?:true|right|correct|it|so)",
    r"that'?s (?:wrong|incorrect|false|untrue|a mistake|an error|"
    r"out of date|outdated|no longer true|not true anymore|not the case)",
    r"that is (?:wrong|incorrect|false|untrue|a mistake|an error|"
    r"out of date|outdated|no longer true|not the case)",
    r"this is (?:wrong|incorrect|not right|not true)",
    r"(?:it'?s|it is) not (?:true|right|correct)",
    r"(?:it|that) was never true",
    r"you'?re wrong", r"you are wrong", r"you'?re mistaken",
    r"you'?ve got (?:that|it) wrong", r"you have (?:that|it) wrong",
    r"you got (?:that|it) wrong", r"you have it wrong",
    r"not true", r"not right", r"not correct", r"untrue",
    r"wrong", r"incorrect", r"false", r"not (?:true )?anymore",
    r"no longer true", r"not the case",
]
# Prefixes that only mark a correction (no denial on their own).
_CORR = [
    r"no", r"nope", r"nah", r"actually", r"sorry", r"correction",
    r"small correction", r"quick correction", r"oops", r"whoops", r"wait",
    r"hmm+", r"um+", r"uh+", r"well", r"oh", r"ah", r"not quite",
    r"not really", r"not exactly", r"my mistake", r"my bad",
    r"i was wrong", r"i made a mistake", r"i misspoke", r"i meant to say",
    r"i meant", r"scratch that", r"let me correct (?:that|myself)",
    r"update", r"to correct that", r"fix that", r"in fact",
]
_PREFIX_RX = re.compile(
    r"^\s*(?P<p>" + "|".join(sorted(_DENY + _CORR, key=len, reverse=True))
    + r")\b\s*(?:[,.:;!—–-]+\s*|\s+|$)", re.IGNORECASE)
_DENY_RX = re.compile(r"^(?:" + "|".join(_DENY) + r")$", re.IGNORECASE)
_FILLER_CORR = {"wait", "well", "oh", "ah", "hmm", "um", "uh", "in fact"}

_STOP = set("""
the a an not no yes it that this there here he she they him her them his
their its i you we me my your our us wrong right true false correct
incorrect sure know don't dont idea thanks thank fine ok okay never mind
nothing something anything someone somebody nobody everyone problem
worries sorry maybe good great cool what who where when why how which is
was are were be been do does did and or but so to in at of on for from
with now anymore instead actually really just still also too very one
else different other another same exactly wait hmm um please lol haha
nope nah yeah yep true unknown none nowhere somewhere elsewhere
""".split())

_TAIL_RX = re.compile(
    r"(?:\s*,?\s*(?:now|instead|these days|nowadays|actually|then|"
    r"anymore|any more|any longer|at all|though|please))+\s*$",
    re.IGNORECASE)
_NOT_TAIL_RX = re.compile(
    r"^(?P<body>.+?)\s*(?:,\s*|\s+)(?:and\s+)?(?:not|rather than|"
    r"instead of)\s+(?P<w>[^,]+?)\s*$", re.IGNORECASE)
_PRON = {"he", "she", "they"}
_POSS_PRON = {"his", "her", "their"}
_ME_RX = re.compile(r"\b(?:my|i|me|mine|i'm|myself)\b", re.IGNORECASE)


def _norm(text: str) -> str:
    t = str(text).replace("’", "'").replace("‘", "'")
    return " ".join(t.split())


def _strip_end(text: str) -> str:
    return text.strip().rstrip(".!").strip()


def is_question252(text: str) -> bool:
    t = _norm(text)
    return t.endswith("?") or bool(_QLEAD.match(t))


def strip_prefixes252(text: str) -> tuple[str, list[str]]:
    """Peel leading denial/correction phrases -> (rest, prefixes)."""
    rest, seen = _norm(text), []
    for _ in range(6):
        m = _PREFIX_RX.match(rest)
        if not m:
            break
        seen.append(m.group("p").lower())
        rest = rest[m.end():].strip()
    return _strip_end(rest), seen


def has_deny252(prefixes: list[str]) -> bool:
    return any(_DENY_RX.match(p) for p in prefixes)


def has_corr_signal252(prefixes: list[str]) -> bool:
    return any(p not in _FILLER_CORR and not re.fullmatch(r"(?:hmm+|um+|uh+)", p)
               for p in prefixes)


def value_ok252(z: str) -> bool:
    """Strict value screen (stricter than the base; failing = ask)."""
    z = _norm(z)
    toks = z.split()
    if not 1 <= len(toks) <= 4:
        return False
    for t in toks:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'\-.]*", t):
            return False
        if t.lower().strip(".") in _STOP:
            return False
    if V139B.screen_value_139b(z) is not None:
        return False
    return True


def _third(verb: str) -> str:
    v = verb.lower()
    irregular = {"have": "has", "do": "does", "go": "goes", "be": "is"}
    if v in irregular:
        out = irregular[v]
    elif re.search(r"(?:s|sh|ch|x|z|o)$", v):
        out = v + "es"
    elif re.search(r"[^aeiou]y$", v):
        out = v[:-1] + "ies"
    else:
        out = v + "s"
    return out if verb.islower() else out.capitalize() if verb[:1].isupper() else out


_NEG_DO = re.compile(
    r"^(?P<x>.+?)\s+(?:doesn't|does not|don't|do not|didn't|did not)\s+"
    r"(?P<v>[A-Za-z]+)\b\s*(?P<rest>.*)$", re.IGNORECASE)
_NEG_LONGER = re.compile(
    r"^(?P<x>.+?)\s+(?:no longer|never)\s+(?P<v>[A-Za-z]+)\b\s*(?P<rest>.*)$",
    re.IGNORECASE)
_NEG_BE = re.compile(
    r"^(?P<x>.+?)\s+(?P<be>isn't|is not|wasn't|was not|is no longer|"
    r"was never|is never)\s+(?P<rest>.+)$", re.IGNORECASE)
_REV_POSS = re.compile(
    r"^(?P<a>[^']+?)\s+(?:is|was)\s+(?P<b>[^']+?)'s\s+(?P<r>[^']+)$",
    re.IGNORECASE)


def positive_of252(clause: str) -> str | None:
    """Strip ONE negation from a statement clause -> positive sentence.

    Only moves words: the result is parsed by the base ears, which decide
    name, relation and value. None when the clause is not negated.
    """
    c = _TAIL_RX.sub("", _strip_end(_norm(clause)))
    m = _NEG_DO.match(c)
    if m:
        verb = m.group("v")
        pos = f"{m.group('x')} {_third(verb)} {m.group('rest')}".strip()
    else:
        m = _NEG_LONGER.match(c)
        if m:
            pos = f"{m.group('x')} {m.group('v')} {m.group('rest')}".strip()
        else:
            m = _NEG_BE.match(c)
            if not m:
                return None
            be = "was" if m.group("be").lower().startswith("was") else "is"
            pos = f"{m.group('x')} {be} {m.group('rest')}".strip()
    rp = _REV_POSS.match(pos)
    if rp and not re.search(r"\b(?:born|from|in|at|of)\b", rp.group("b"),
                            re.IGNORECASE):
        pos = f"{rp.group('b')}'s {rp.group('r')} is {rp.group('a')}"
    return pos + "."


def _rel_surface(key: str) -> str:
    return str(key).replace("_", " ")


def _ww(needle: str, hay: str) -> bool:
    if not needle:
        return False
    return re.search(r"(?<![\w])" + re.escape(needle) + r"(?![\w])", hay,
                     re.IGNORECASE) is not None


# ------------------------------------------------------------ notebook reads
def _taught_triples(nb) -> list[tuple[str, str, str, str]]:
    out = []
    for fid, fact in nb.facts.items():
        if fact.get("source") != "taught" or not nb.active(fid):
            continue
        subj = str(nb.entities.get(fact.get("subject"), fact.get("subject")))
        out.append((fid, subj, str(fact.get("relation")),
                    M154.display154b(nb, fact.get("value", {}))))
    return out


def stated_facts252(nb, prev: dict | None):
    """-> ("none"|"one"|"many"|"inferred", facts) for the previous reply."""
    if not prev or prev.get("wrote") or not prev.get("reply"):
        return "none", []
    for rec in prev.get("records", []):
        if (isinstance(rec, dict) and rec.get("kind") == "answer"
                and rec.get("status") == C.OK):
            rels = rec.get("relations") or []
            src = (rec.get("fields") or {}).get("source", "taught")
            if len(rels) >= 2 or src != "taught":
                trail = (rec.get("fields") or {}).get("trail") or []
                facts = []
                for fid in trail:
                    f = nb.facts.get(fid)
                    if f is not None:
                        facts.append((str(nb.entities.get(f["subject"], f["subject"])),
                                      str(f["relation"]),
                                      M154.display154b(nb, f.get("value", {}))))
                return "inferred", facts
    reply = prev["reply"]
    low = reply.lower()
    hits = []
    for fid, s, r, v in _taught_triples(nb):
        if v.lower() in low and s.lower() in low and _ww(v, reply) \
                and _ww(s, reply) and s != "USER":
            hits.append((fid, s, r, v))
    if not hits:
        return "none", []
    if len(hits) == 1:
        return "one", hits
    return "many", hits


# ------------------------------------------------------------ ears mixin
class Correct252EarsMixin:
    """Outermost on the inner ears. Unclaimed turns -> super().hear()."""

    def _mark252(self, tag: str) -> None:
        try:
            self.last_stage, self.last_score = f"{STAGE252}-{tag}", 1.0
        except AttributeError:
            pass

    def _pending252(self) -> bool:
        loop = getattr(self, "_loop252", None)
        if getattr(self, "pending_replace154g", None):
            return True
        if loop is None:
            return True
        if getattr(getattr(loop, "listening", None), "pending", None) is not None:
            return True
        if getattr(loop, "question_pending", None) is not None:
            return True
        return False

    # -- parse a positive sentence with the base ears (no side effects kept)
    def _read252(self, sentence: str):
        saved = (getattr(self, "last_stage", None), getattr(self, "last_score", None))
        try:
            acts = super().hear(sentence)  # type: ignore[misc]
        finally:
            try:
                self.last_stage, self.last_score = saved
            except AttributeError:
                pass
        if not (isinstance(acts, list) and len(acts) == 1
                and isinstance(acts[0], dict)
                and acts[0].get("act") in ("teach", "correct")):
            return None
        a = acts[0]
        name, rel, val = (str(a.get("name", "")), str(a.get("relation", "")),
                          str(a.get("value", "")))
        if not name or not rel or not val:
            return None
        return name, rel, val

    def _resolve252(self, name: str):
        nb = self.nb
        res = nb.resolve(name)
        if res.status != C.OK:
            return None
        eid = res.detail["entity_id"]
        return eid, str(nb.entities[eid])

    def _values252(self, eid: str, key: str) -> list[str]:
        return M154.current_values154b(self.nb, eid, key)

    # -- canonical hand-off to the base teach/replacement path
    def _canon252(self, subj: str, key: str, new: str):
        canon = f"No, {subj}'s {_rel_surface(key)} is {new}."
        saved = (getattr(self, "last_stage", None), getattr(self, "last_score", None))
        acts = super().hear(canon)  # type: ignore[misc]
        if not (isinstance(acts, list) and len(acts) == 1
                and isinstance(acts[0], dict)):
            self.last_stage, self.last_score = saved
            return None
        a = acts[0]
        kind = a.get("act")
        if kind == "correct":
            ok = (str(a.get("name", "")).lower() == subj.lower()
                  and str(a.get("relation", "")) == key
                  and str(a.get("value", "")).lower() == new.lower())
        elif kind == "correct_single154g":
            ok = (str(a.get("name", "")).lower() == subj.lower()
                  and str(a.get("rel_key", "")) == key
                  and str(a.get("new", "")).lower() == new.lower())
        else:
            ok = False
        if not ok:
            self.last_stage, self.last_score = saved
            return None
        self._mark252("replace")
        return acts

    def _ask252(self, text: str, tag: str) -> list[dict]:
        self._mark252(tag)
        return [{"act": "clarify", "text": text, "correct252": tag}]

    def _remove252(self, eid, subj, key, val, raw) -> list[dict]:
        self._mark252("remove")
        return [{"act": ACT252, "name": subj, "entity_id": eid,
                 "relation": key, "rel_key": key, "value": val, "raw": raw}]

    def _deny_named252(self, pos: str, raw: str):
        """Rule 1 on a positive sentence -> actions or None (not parsed)."""
        got = self._read252(pos)
        if got is None:
            return None
        name, key, val = got
        if name.upper() == "USER" or _ME_RX.search(name):
            return None
        r = self._resolve252(name)
        if r is None:
            return self._ask252(
                f"I don't have anything saved about {name}, so I didn't "
                "change anything.", "unknown")
        eid, subj = r
        for v in self._values252(eid, key):
            if v.lower() == val.lower():
                return self._remove252(eid, subj, key, v, raw)
        return self._ask252(
            f"I don't have {val} as {subj}'s {_rel_surface(key)}, so I "
            "didn't change anything.", "unstored")

    def _ctx252(self):
        loop = getattr(self, "_loop252", None)
        return stated_facts252(self.nb, getattr(loop, "_prev252", None))

    def _ask_which252(self, kind: str, facts) -> list[dict]:
        if kind == "inferred":
            listed = " and ".join(f"{s}'s {_rel_surface(r)} is {v}"
                                  for s, r, v in facts)
            extra = f" from: {listed}" if listed else " from other facts"
            return self._ask252(
                f"I worked that out{extra}. Which of those facts is wrong?",
                "inferred")
        return self._ask252(
            "Which fact is wrong? Please say it like \"Kim's boss is not "
            "Lee.\"", "which")

    def _ctx_correct252(self, z: str, w: str | None, raw: str,
                        pron: str | None = None):
        kind, facts = self._ctx252()
        if kind != "one":
            if kind == "inferred":
                return self._ask_which252(kind, facts)
            return self._ask252(
                "Which fact should I change? Please say it like \"Kim's "
                "boss is Lee.\"", "which-fix")
        _fid, subj, key, old = facts[0]
        return self._fix252(subj, key, old, z, w, raw)

    def _fix252(self, subj, key, old, z, w, raw):
        z = _strip_end(_TAIL_RX.sub("", _strip_end(z)))
        r = self._resolve252(subj)
        if r is None:
            return self._ask252("Which fact should I change?", "which-fix")
        eid, subj = r
        values = self._values252(eid, key)
        if values != [old] and not (len(values) == 1
                                    and values[0].lower() == old.lower()):
            return self._ask252(
                f"Which {_rel_surface(key)} of {subj}'s should I change? "
                f"Please say it like \"{subj}'s {_rel_surface(key)} is "
                f"{z}, not {values[0] if values else old}.\"", "multi")
        old = values[0]
        if w is not None and w.lower() != old.lower():
            return self._ask252(
                f"I have {subj}'s {_rel_surface(key)} as {old}, not {w}. "
                "Which fact should I change?", "mismatch")
        if not value_ok252(z):
            return self._ask252(
                f"What should {subj}'s {_rel_surface(key)} be? Please say "
                f"it like \"{subj}'s {_rel_surface(key)} is Lee.\"", "badvalue")
        if z.lower() == old.lower():
            return self._ask252(
                f"I already have {subj}'s {_rel_surface(key)} as {old}.",
                "same")
        acts = self._canon252(subj, key, z)
        if acts is None:
            return self._ask252(
                f"I couldn't change that. Please say it like \"{subj}'s "
                f"{_rel_surface(key)} is {z}.\"", "refused")
        return acts

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        try:
            out = self._hear252(turn)
        except Exception:  # noqa: BLE001 -- never break the base path
            out = None
        if out is not None:
            return out
        return super().hear(turn)  # type: ignore[misc]

    def _hear252(self, turn: str):
        nb = getattr(self, "nb", None)
        if nb is None or self._pending252():
            return None
        text = _norm(turn)
        if not text or is_question252(text):
            return None
        # The base 154f path already owns "X's R is not Y." (one-word X).
        parsed = N154F.parse_negate154f(text)
        if parsed is not None and nb.resolve(parsed["name"]).status == C.OK:
            return None
        rest, prefixes = strip_prefixes252(text)
        rest = rest.strip()
        low = rest.lower()
        # ---- rule 2: whole turn is a denial phrase
        if not rest or low in ("at all", "anymore", "any more"):
            if has_deny252(prefixes):
                kind, facts = self._ctx252()
                if kind == "one":
                    _fid, subj, key, val = facts[0]
                    r = self._resolve252(subj)
                    if r is not None:
                        return self._remove252(r[0], r[1], key, val, turn)
                return self._ask_which252(kind, facts)
            return None
        if _ME_RX.search(rest):
            return None  # the user's own facts: base confirm flow (rule 7)
        # ---- pronoun substitution needs exactly one stated fact
        first = low.split()[0]
        subj_ctx = None
        if first in _PRON or first in _POSS_PRON:
            kind, facts = self._ctx252()
            if kind != "one":
                if kind == "inferred":
                    return self._ask_which252(kind, facts)
                if prefixes or positive_of252(rest) is not None:
                    return self._ask252(
                        "Who do you mean? Please say the name, like "
                        "\"Kim's boss is not Lee.\"", "who")
                return None
            subj_ctx = facts[0]
        # ---- two clauses: denial + positive (rule 4)
        parts = re.split(r"\s*(?:,\s*but\s+|;\s*|,\s*|\.\s+|\s+but\s+)\s*",
                         rest, maxsplit=1)
        if len(parts) == 2 and positive_of252(parts[0]) is not None \
                and positive_of252(parts[1]) is None:
            neg, posc = parts
            got = self._two252(neg, posc, subj_ctx, turn)
            if got is not None:
                return got
        # ---- single negated clause (rule 1)
        pos = positive_of252(rest)
        if pos is not None:
            if subj_ctx is not None:
                _fid, subj, key, val = subj_ctx
                pos = self._subst252(pos, subj)
                got = None
                if re.search(r"\s+(?:there|that|it)\.$", pos, re.IGNORECASE):
                    for prep in ("in ", "at ", "for ", ""):
                        cand = re.sub(r"\s+(?:there|that|it)\.$",
                                      f" {prep}{val}.", pos,
                                      flags=re.IGNORECASE)
                        got = self._read252(cand)
                        if got is not None:
                            pos = cand
                            break
                else:
                    got = self._read252(pos)
                if got is None or got[1] != key:
                    return self._ask252(
                        "Which fact is wrong? Please say it like \"Kim's "
                        "boss is not Lee.\"", "which")
                if got[2].lower() != val.lower():
                    return self._deny_named252(pos, turn)
                r = self._resolve252(subj)
                return self._remove252(r[0], r[1], key, val, turn) if r else None
            return self._deny_named252(pos, turn)
        # ---- positive clause with ", not W" (explicit, rule 4)
        m = _NOT_TAIL_RX.match(rest)
        body, w = (m.group("body"), _strip_end(m.group("w"))) if m else (rest, None)
        body = _strip_end(_TAIL_RX.sub("", body))
        # ---- contextual correction: "it's Z" / bare Z / pronoun clause
        cz = re.match(
            r"^(?:it'?s|it is|it was|its|that'?s|that is|that should be|"
            r"it should be|should be|the answer is|the (?:right|correct|real) "
            r"(?:answer|one) is|correct answer is|make (?:that|it)|change "
            r"(?:that|it) to|it'?s actually|it is actually|actually it'?s|"
            r"it'?s really|it is really)\s+(?P<z>.+)$", body, re.IGNORECASE)
        if cz and subj_ctx is None:
            z = cz.group("z")
            strong = bool(prefixes and has_corr_signal252(prefixes)) \
                or w is not None
            # no correction word ("It's Tuesday.", "Oh, it's Z.") = not
            # sure it is a correction: leave the turn to the base.
            if strong:
                return self._ctx_correct252(z, w, turn)
            return None
        mnot = re.match(r"^not\s+(?P<w>[^,]+?)\s*(?:,\s*(?:but\s+)?|\s+but\s+)"
                        r"(?:it'?s\s+|it is\s+)?(?P<z>.+)$", rest, re.IGNORECASE)
        if mnot and subj_ctx is None:
            return self._ctx_correct252(mnot.group("z"),
                                        _strip_end(mnot.group("w")), turn)
        if subj_ctx is not None:
            _fid, subj, key, val = subj_ctx
            if not (prefixes and has_corr_signal252(prefixes)) and w is None \
                    and not re.search(r"\b(?:now|instead)\b", low):
                return None
            got = self._read252(self._subst252(body + ".", subj))
            if got is None or got[1] != key:
                return self._ask252(
                    "Which fact should I change? Please say it like \"Kim's "
                    "boss is Lee.\"", "which-fix")
            return self._fix252(subj, key, val, got[2], w, turn)
        # bare value after a correction prefix: "No, Aldgate." / "Nope - Z"
        if prefixes and has_corr_signal252(prefixes) and value_ok252(body) \
                and self._read252(body + ".") is None \
                and len(body.split()) <= 3:
            # "No, Kira." / "That's wrong, Kim." could be a new value or
            # just a name said to me: never write, ask (safety first).
            kind, facts = self._ctx252()
            if kind == "one" and w is None:
                _fid, subj, key, _old = facts[0]
                return self._ask252(
                    f"I didn't change anything. If {subj}'s "
                    f"{_rel_surface(key)} should be {_strip_end(body)}, "
                    f"please say \"No, it's {_strip_end(body)}.\"", "bare")
            return self._ctx_correct252(body, w, turn)
        # ---- explicit named correction (rule 4)
        if not (prefixes and has_corr_signal252(prefixes)) and w is None:
            return None
        # "no Vera's city is Quito" (no comma): "no" may not be a
        # correction word here (sessions152 K146) -- leave it to the base.
        if w is None and re.match(
                r"^\s*(?:no|nope|nah)\s+(?!(?:wait|actually|sorry|"
                r"correction|wrong)\b)[^\s,.:;!\-]", turn, re.IGNORECASE):
            return None
        got = self._read252(body + ".")
        if got is None:
            return None
        name, key, z = got
        r = self._resolve252(name)
        if r is None:
            return None
        eid, subj = r
        values = self._values252(eid, key)
        if len(values) != 1:
            return None
        if w is None:
            base = super().hear(turn)  # type: ignore[misc]
            if (isinstance(base, list) and len(base) == 1
                    and isinstance(base[0], dict)
                    and base[0].get("act") in ("correct", "correct_single154g",
                                               "replace_one154g",
                                               "ask_replace154g")):
                return base
        elif w.lower() != values[0].lower():
            return None
        if not value_ok252(z) or z.lower() == values[0].lower():
            return None
        acts = self._canon252(subj, key, z)
        return acts

    def _subst252(self, sentence: str, subj: str) -> str:
        s = sentence
        m = re.match(r"^(he|she|they)\s+(\S+)(.*)$", s, re.IGNORECASE)
        if m:
            verb = m.group(2)
            if m.group(1).lower() == "they" and not verb.lower().endswith("s") \
                    and verb.lower() not in ("are", "were"):
                verb = _third(verb)
            if m.group(1).lower() == "they" and verb.lower() == "are":
                verb = "is"
            return f"{subj} {verb}{m.group(3)}"
        m = re.match(r"^(his|her|their)\s+(.*)$", s, re.IGNORECASE)
        if m:
            return f"{subj}'s {m.group(2)}"
        return s

    def _two252(self, neg: str, posc: str, subj_ctx, raw: str):
        pos_neg = positive_of252(neg)
        if subj_ctx is not None:
            pos_neg = self._subst252(pos_neg, subj_ctx[1])
        a = self._read252(pos_neg)
        if a is None:
            return None
        posc = _strip_end(_TAIL_RX.sub("", _strip_end(posc)))
        posc = re.sub(r"^(?:it'?s|it is)\s+", "", posc, flags=re.IGNORECASE)
        posc = self._subst252(posc + ".", a[0])
        b = self._read252(posc)
        if b is None:
            # "X doesn't live in Y, Z." -> Z is the new value
            z = _strip_end(posc)
            if not value_ok252(z):
                return None
            b = (a[0], a[1], z)
        if b[0].lower() != a[0].lower() or b[1] != a[1]:
            return None
        r = self._resolve252(a[0])
        if r is None:
            return None
        eid, subj = r
        values = self._values252(eid, a[1])
        if not (len(values) == 1 and values[0].lower() == a[2].lower()):
            return None  # (X, R, Y) not stored as the one value: base stays
        if not value_ok252(b[2]) or b[2].lower() == values[0].lower():
            return None
        return self._canon252(subj, a[1], b[2])


# ------------------------------------------------------------ loop mixin
class Correct252LoopMixin:
    """Remembers the previous reply (in memory only) and runs negate252
    through 154f's own retraction path (_act_negate_one138j)."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-redef]
        if L189B.is_repeat189b(text):
            return super().turn(text)  # type: ignore[misc]  # state kept
        before = len(self.nb.events)  # type: ignore[attr-defined]
        said = super().turn(text)  # type: ignore[misc]
        try:
            self._prev252 = {
                "reply": " ".join(said) if said else "",
                "records": list(getattr(self, "last_records", []) or []),
                "wrote": len(self.nb.events) != before,  # type: ignore[attr-defined]
            }
        except Exception:  # noqa: BLE001
            self._prev252 = None
        return said

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == ACT252:
            key, val = action["rel_key"], action["value"]
            rec = self._act_negate_one138j({  # type: ignore[attr-defined]
                "act": "negate_one154f", "name": action["name"],
                "relation": key, "rel_key": key, "value": val,
                "raw": action.get("raw", "")})
            if rec.get("kind") == "write" and rec.get("wrote"):
                nb = self.nb  # type: ignore[attr-defined]
                res = nb.resolve(action["name"])
                subj = action["name"]
                rest = []
                if res.status == C.OK:
                    eid = res.detail["entity_id"]
                    subj = str(nb.entities[eid])
                    rest = M154.current_values154b(nb, eid, key)
                text = f"OK, I removed {val} as {subj}'s {_rel_surface(key)}"
                if rest:
                    text += f", and I still have {M154.join_and154b(rest)}."
                else:
                    text += "."
                rec = dict(rec)
                rec["text"] = text
            return rec
        return super()._act(action)  # type: ignore[misc]


def install_correct252(loop) -> None:
    """Class-swap the loop and its inner ears (idempotent)."""
    if not isinstance(loop, Correct252LoopMixin):
        cls = loop.__class__
        loop.__class__ = type(f"Correct252_{cls.__name__}",
                              (Correct252LoopMixin, cls), {})
        loop._prev252 = None
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        ears = getattr(loop, "ears", None)
        inner = getattr(ears, "inner", None) or ears
    if inner is not None and not isinstance(inner, Correct252EarsMixin):
        cls = inner.__class__
        inner.__class__ = type(f"Correct252_{cls.__name__}",
                               (Correct252EarsMixin, cls), {})
    if inner is not None:
        inner._loop252 = loop
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("fix252" in n for n in notes):
        notes.append("fix252: Correct252EarsMixin outermost on inner ears + "
                     "Correct252LoopMixin on the loop")
