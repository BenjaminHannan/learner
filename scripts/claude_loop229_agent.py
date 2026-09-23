#!/usr/bin/env python3
"""Experiment 229 -- relation-table build 2: TEACHES (on loop138i).

loop229 = loop138i + ONE change: TableTeach229Mixin sits OUTERMOST on the
138i ears stack. It acts only on STATEMENTS (turns not ending in "?") that
the full 138i stack did not understand at all (every action a
not-understood clarify; same test as fable_fix221_tableask.base_missed221).
Everything the base already understands -- saves, refusals, hearsay,
questions -- passes through byte-identical.

On such a miss the turn is matched against teach templates:
  (T) the relation table's own teach rows (relation_table_v1.json, 217;
      read-only) and its not-live generic teach families "of_form"
      ("The R of X is Y.") and "inverted" ("Y is X's R.", "Y is the R of
      X."), with {R} over the canonical word and every alias;
  (E) a small sealed extension (EXT229 below; NEW shapes, not in v1):
      occupation "X is a/an J." (J from a closed job list, OCC229),
      "Y is a/an R of X." (ONLY relations the table marks multi-valued),
      "Y is my R.", "X has a/an R called/named Y." (multi only),
      first-person "I live in Y." etc., and a few verb forms
      ("Y coaches X.", "Y owns X.", "X studies at Y.", "X was written by
      Y.", "X grew up in Y.", "X is based in Y.").
A reading proposes (subject, relation, value). Inverse readings are never
stored: every template maps to the forward fact (X, R, Y) = "X's R is Y".

Checks, in order (any failure -> nothing saved, and the reply says so):
  1. exactly one distinct reading;
  2. subject shape (a capitalised name, or the user) and the table's value
     kind + value guard for the relation (person / place / organization /
     work / language / literal / number / date);
  3. the reading is rewritten as the canonical sentence "X's R is Y."
     ("My R is Y." for the user) and passed through the FULL 138i ears
     (super().hear), so every base screen (167b, 171/171b, 139b, 150,
     173b, 172b re-teach, 154e multi, typo 165) sees it exactly like a
     typed possessive teach; the result must be teach/correct actions on
     (X, a key of R's table group, Y);
  4. the 209 write screen (screen_turn209, imported read-only) must pass.
The accepted actions then go through the base's normal _act save path
(confirm / re-teach ask / multi-valued add unchanged). If the base's
answer to the canonical sentence is its own clarify (a screen refusal or
a confirmation), that clarify is returned, prefixed "I did not save that
yet." so the reply is plain about it.

Out of scope (no template; counted as known misses): pronouns,
appositives, two facts in one sentence, negation, tense / "used to".

New files only; 138i and every earlier piece are read-only.
Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop229_agent.py --daemon --dir DIR \\
    --config artifacts/claude-tableteach229-20260922/loop229-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only)
import fable_loop138_agent as L138  # noqa: E402 (NOT_UNDERSTOOD, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (read-only)
from fable_fix221_tableask import (  # noqa: E402 (read-only helpers)
    TABLE_PATH221, compile_template221, key221, looks_like_date221)
from fable_loop209_agent import screen_turn209  # noqa: E402 (read-only)

WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134

USER229 = "USER"  # fable_fix166_me.USER_KEY
STAGE229 = "loop229-table-teach"
NOT_SAVED229 = "I did not save that"

# ------------------------------------------------------------ lexicons
OCC229 = frozenset("""
accountant actor actress architect artist astronaut athlete author baker
banker barber barista beekeeper biologist blacksmith bookkeeper builder
butcher captain carpenter cashier chef chemist cleaner clerk coach cook
courier dancer dentist designer detective developer diplomat director
doctor driver economist editor electrician engineer farmer firefighter
fisherman florist gardener geologist guard guide hairdresser historian
illustrator inspector janitor jeweller jeweler journalist judge labourer
laborer lawyer lecturer librarian lifeguard linguist locksmith machinist
manager mechanic midwife miner musician novelist nurse optician painter
paramedic pharmacist philosopher photographer physician physicist
physiotherapist pilot plumber poet politician porter postman potter
priest principal producer professor programmer psychologist publisher
radiologist ranger receptionist reporter researcher sailor salesman
saleswoman scientist sculptor secretary shepherd shopkeeper singer
soldier solicitor student surgeon surveyor tailor teacher technician
therapist translator tutor veterinarian vet waiter waitress weaver welder
writer zookeeper analyst archivist curator conductor composer
""".split()) | frozenset([
    "software engineer", "civil engineer", "bus driver", "taxi driver",
    "truck driver", "lorry driver", "police officer", "fire fighter",
    "flight attendant", "social worker", "web developer", "data scientist",
    "dental nurse", "head teacher", "estate agent", "real estate agent",
    "graphic designer", "sous chef", "train driver", "air traffic controller",
    "shop assistant", "care worker", "nurse practitioner", "art teacher",
    "music teacher", "primary school teacher", "school teacher",
    "tour guide", "park ranger", "lab technician", "vet nurse",
    "construction worker", "factory worker", "farm worker"])

_FUNC_START = frozenset("""
he she they it this that these those him her them we us i me my mine who
what where when which whose why how his their its our there here someone
somebody anyone anybody everyone everybody nobody noone something anything
everything nothing if maybe perhaps apparently suppose supposedly
although though because since yesterday today tomorrow now also and but
so then actually probably possibly hopefully sadly luckily once
everyone's nobody's all some many most few both each every either
neither no not never please thanks thank yes yeah ok okay well oh hi
hello dear sure really just still even only
""".split())
# connector words allowed INSIDE a name (lower case)
_CONNECT = frozenset({"of", "the", "de", "da", "van", "von", "der", "den",
                      "du", "la", "le", "del", "upon"})
# titles of works may also contain these
_CONNECT_WORK = _CONNECT | frozenset({"on", "in", "a", "an", "at", "for",
                                      "to", "from", "by"})
_NEG_RE = re.compile(
    r"\b(not|never|no longer|anymore|any more|used to|formerly|former|"
    r"ex|isn't|wasn't|aren't|doesn't|didn't|won't|n't|nobody|no one|"
    r"if|would|could|might|may be|maybe|perhaps|probably|thinks?|said|"
    r"says|heard|believes?)\b",
    re.IGNORECASE)
# name-like words (Hope, Wish, ...) only count in lower case
_NEG_LOWER_RE = re.compile(r"\b(wish|wishes|hope|hopes|pretend|pretends|"
                           r"imagine|imagines|suppose|supposes|will)\b")


def _toks(s: str) -> list[str]:
    return str(s).split()


def name_shape229(s: str, max_tokens: int = 6,
                  connectors: bool = True, work: bool = False,
                  digits: bool = True) -> bool:
    """A capitalised name: every token capitalised (or a digit token), except
    small lower-case connector words inside (only when connectors=True;
    titles of works (work=True) allow a few more, including "and")."""
    s = str(s).strip()
    if not s or re.search(r"[,;:!?\"()]", s) or "'s" in s or "\u2019s" in s:
        return False
    words = _toks(s)
    if len(words) > max_tokens:
        return False
    if words[0].lower() in _FUNC_START:
        return False
    if not digits and re.search(r"\d", s):
        return False
    if not (words[0][:1].isupper() or words[0][:1].isdigit()):
        return False
    if not (words[-1][:1].isupper() or words[-1][:1].isdigit()):
        return False
    conn = _CONNECT_WORK if work else _CONNECT
    for w in words[1:-1]:
        if w[:1].isupper() or w[:1].isdigit():
            continue
        if connectors and w.lower() in conn:
            continue
        return False
    if any(w.lower() in ("and", "or", "with", "&") for w in words):
        return False  # two things at once: out of scope
    return True


def person_shape229(s: str) -> bool:
    return name_shape229(s, max_tokens=4, connectors=False) or \
        name_shape229(s, max_tokens=4, connectors=True) and \
        all(w.lower() in {"de", "da", "van", "von", "der", "den", "du",
                          "la", "le", "del"} or w[:1].isupper()
            for w in _toks(s))


def lower_phrase229(s: str, max_tokens: int = 3) -> bool:
    s = str(s).strip()
    words = _toks(s)
    if not words or len(words) > max_tokens:
        return False
    if re.search(r"[,;:!?\"()']", s):
        return False
    if any(w.lower() in _FUNC_START or w.lower() in {"and", "or", "with"}
           for w in words):
        return False
    return all(re.fullmatch(r"[a-z][a-z\-]*", w) for w in words)


def value_ok229(rel: dict, value: str, how: str) -> str | None:
    """Table value-type check. None = ok, else a short reason."""
    kind = rel.get("value_kind")
    name = rel["name"]
    v = str(value).strip()
    if not v:
        return "there is no value"
    g = rel.get("value_guard") or ""
    if g.startswith("value must look like a date") and \
            not looks_like_date221(v):
        return f"{v} does not look like a date"
    if g.startswith("value must NOT look like a date") and \
            looks_like_date221(v):
        return f"{v} looks like a date, not a place"
    if kind == "person":
        if v.lower() in OCC229:
            return f"{v} is a job, not a name"
        return None if person_shape229(v) else f"{v} does not look like a name"
    if kind == "place":
        return None if name_shape229(v, max_tokens=5, digits=False) \
            else f"{v} does not look like a place name"
    if kind == "organization":
        return None if name_shape229(v, max_tokens=6) \
            else f"{v} does not look like a name"
    if kind == "work":
        return None if name_shape229(v, max_tokens=8, work=True) \
            else f"{v} does not look like a title"
    if kind == "language":
        return None if name_shape229(v, max_tokens=2, connectors=False) \
            else f"{v} does not look like a language"
    if kind == "number":
        return None if re.fullmatch(r"\d{1,3}", v) and int(v) <= 130 \
            else f"{v} is not a number"
    if kind == "date":
        return None if looks_like_date221(v) else f"{v} is not a date"
    # literal
    if name == "occupation":
        if v.lower() in OCC229 or (how == "works_as" and lower_phrase229(v)):
            return None
        return f"{v} is not a job I know"
    if name in ("hobby",):
        return None if lower_phrase229(v) else f"{v} does not look like a hobby"
    if name == "nickname":
        return None if name_shape229(v, max_tokens=3, connectors=False) \
            else f"{v} does not look like a name"
    if lower_phrase229(v, 4) or name_shape229(v, 4):
        return None
    return f"{v} does not look like a value for {name.replace('_', ' ')}"


def subject_ok229(x: str) -> str | None:
    """Subjects may be people, places, organisations or titles of works."""
    if x == USER229:
        return None
    return None if name_shape229(x, max_tokens=8, work=True) \
        else f"{x} does not look like a name"


# ------------------------------------------------------------ templates
# Extension templates (NEW, not in table v1). Each: (template, relation,
# how, multi_only). {X} = subject, {Y} = value, {R} = relation surface,
# {J} = job word (value), {ME} = the user as subject.
EXT229 = [
    ("{X} is (a|an) {J}.", "occupation", "is_a", False),
    ("{ME} am (a|an) {J}.", "occupation", "is_a", False),
    ("{ME} work as (a|an) {Y}.", "occupation", "works_as", False),
    ("{Y} is (a|an) {R} of {X}.", None, "a_r_of", True),
    ("{Y} is my {R}.", None, "is_my", False),
    ("{X} has (a|an) {R} (called|named) {Y}.", None, "has_a", True),
    ("{ME} have (a|an) {R} (called|named) {Y}.", None, "has_a", True),
    ("{ME} live in {Y}.", "city", "me", False),
    ("{ME} moved to {Y}.", "city", "me", False),
    ("{ME} am from {Y}.", "hometown", "me", False),
    ("{ME} come from {Y}.", "hometown", "me", False),
    ("{ME} grew up in {Y}.", "hometown", "me", False),
    ("{ME} was born in {Y}.", "place_of_birth", "me", False),
    ("{ME} was born (in|on) {Y}.", "date_of_birth", "me", False),
    ("{ME} work (at|for) {Y}.", "employer", "me", False),
    ("{ME} speak {Y}.", "language", "me", False),
    ("{ME} am {Y} years old.", "age", "me", False),
    ("{ME} studied at {Y}.", "educated_at", "me", False),
    ("{ME} study at {Y}.", "educated_at", "me", False),
    ("{ME} go to {Y}.", "school", "me", False),
    ("{ME} am married to {Y}.", "spouse", "me", False),
    ("{Y} coaches {X}.", "coach", "verb", False),
    ("{Y} owns {X}.", "owner", "verb", False),
    ("{X} is owned by {Y}.", "owner", "verb", False),
    ("{X} studies at {Y}.", "educated_at", "verb", False),
    ("{X} was written by {Y}.", "author", "verb", False),
    ("{X} grew up in {Y}.", "hometown", "verb", False),
    ("{X} is based in {Y}.", "headquarters_location", "verb", False),
    ("{X} was born on {Y}.", "date_of_birth", "verb", False),
]

_TABLE229: dict = {}
OF_FAMILIES229 = ("inverted",)
_QSTART229 = frozenset("""what who whom where when which whose why how is are
am was were do does did can could will would should shall may might must
has have had""".split())


def _surfaces(rel: dict) -> list[str]:
    out = [rel["name"].replace("_", " ")] + list(rel.get("aliases", []))
    seen, res = set(), []
    for s in out:
        if s.lower() not in seen:
            seen.add(s.lower())
            res.append(s)
    return res


def _compile(t: str) -> re.Pattern:
    t = t.replace("{ME}", "I").replace("{J}", "{Y}")
    return compile_template221(t)


def load_table229(path: str | Path | None = None) -> dict:
    tpath = str(path or TABLE_PATH221)
    if tpath in _TABLE229:
        return _TABLE229[tpath]
    data = json.loads(Path(tpath).read_text(encoding="utf-8"))
    rels = {r["name"]: r for r in data["relations"]}
    key2rel: dict[str, str] = {}
    for r in data["relations"]:
        for k in ([r["name"]] + [key221(a) for a in r["aliases"]]
                  + list(r.get("storage_keys", []))):
            key2rel.setdefault(key221(k), r["name"])
    gen = data["generic_patterns"]
    pats: list[tuple] = []  # (rel, how, regex, template, user_subject)
    seen = set()

    def add(rel_name, how, tmpl, user):
        if (rel_name, tmpl) in seen:
            return
        seen.add((rel_name, tmpl))
        pats.append((rel_name, how, _compile(tmpl), tmpl, user))

    for r in data["relations"]:
        for row in r.get("teach", []):
            t = row["t"]
            how = "works_as" if "works as" in t else "table"
            add(r["name"], how, t, False)
        for fam in r.get("generic", []):
            # possessive / my are live in the base. of_form ("The R of X is
            # Y.") is CUT from this build: the frozen rt136 suite marks
            # "The mother of Ann is Sue." etc. as nowrite (pilot: 4 new
            # WRONG-WRITE), so it is a counted known miss.
            if fam not in OF_FAMILIES229:
                continue
            for row in gen[fam].get("teach", []):
                for s in _surfaces(r):
                    add(r["name"], fam, row["t"].replace("{R}", s), False)
    for tmpl, rel_name, how, multi_only in EXT229:
        user = "{ME}" in tmpl or how == "is_my"
        targets = [rel_name] if rel_name else [
            r["name"] for r in data["relations"]
            if "inverted" in r.get("generic", [])
            and (not multi_only or r.get("cardinality") == "multi")]
        for rn in targets:
            r = rels[rn]
            if "{R}" in tmpl:
                for s in _surfaces(r):
                    add(rn, how, tmpl.replace("{R}", s), user)
            else:
                add(rn, how, tmpl, user)
    # first-word index: literal first token (lowercase) or None (slot first)
    index: dict[str | None, list[tuple]] = {}
    for pat in pats:
        first = pat[3].split()[0]
        key = None if re.search(r"[{(\[]", first) else first.lower()
        if first == "{ME}":
            key = "i"
        index.setdefault(key, []).append(pat)
    out = {"rels": rels, "key2rel": key2rel, "patterns": pats,
           "index": index, "path": tpath}
    _TABLE229[tpath] = out
    return out


def group_keys229(tb: dict, rel_name: str) -> set[str]:
    r = tb["rels"][rel_name]
    return {key221(k) for k in ([r["name"]] + list(r.get("aliases", []))
                                + list(r.get("storage_keys", [])))}


def _norm(s: str) -> str:
    return " ".join(str(s).split()).strip().rstrip(".").lower()


def table_teach_readings229(turn: str, tb: dict | None = None) -> list[dict]:
    """Distinct (rel, X, Y) teach readings of a statement turn."""
    tb = tb or load_table229()
    t = " ".join(str(turn).split()).strip()
    if not t or t.endswith("?"):
        return []
    body = t.rstrip(" .!")
    if not body or re.search(r"[.!?;]", body):
        return []  # more than one sentence
    if _NEG_RE.search(body) or _NEG_LOWER_RE.search(body):
        return []  # negation / tense / hearsay / hypothetical: out of scope
    words = re.findall(r"[A-Za-z]+", body)
    if len(words) >= 2 and not re.search(r"[a-z]", body):
        return []  # shouted all-caps turn: rt136 treats it as nowrite
    first = body.split()[0].lower()
    if first in _QSTART229:
        return []  # question-shaped turn without "?": not a teach
    cands = list(tb["index"].get(first, [])) + list(tb["index"].get(None, []))
    out, seen = [], set()
    for rel_name, how, rx, tmpl, user in cands:
        m = rx.fullmatch(body)
        if not m:
            continue
        g = {k: v.strip() for k, v in m.groupdict().items() if v is not None}
        x = USER229 if user else g.get("X")
        y = g.get("Y")
        if x is None or y is None:
            continue
        r = tb["rels"][rel_name]
        if r.get("date_rule"):
            for w in r["date_rule"].get("strip_leading", []):
                if y.lower().startswith(w + " "):
                    y = y[len(w) + 1:].strip()
        # occupation "is a J": only a job word counts as a reading at all
        if how == "is_a" and y.lower() not in OCC229:
            continue
        # date vs place guards decide between readings silently
        g_ = r.get("value_guard") or ""
        if g_.startswith("value must look like a date") and \
                not looks_like_date221(y):
            continue
        if g_.startswith("value must NOT look like a date") and \
                looks_like_date221(y):
            continue
        sig = (rel_name, _norm(x), _norm(y))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({"rel": rel_name, "X": x, "Y": y, "how": how,
                    "template": tmpl})
    return out


def canonical_sentence229(x: str, rel_name: str, y: str) -> str:
    rd = rel_name.replace("_", " ")
    if x == USER229:
        return f"My {rd} is {y}."
    return f"{x}'s {rd} is {y}."


def base_missed229(actions) -> bool:
    if not isinstance(actions, list):
        return False
    if not actions:
        return True
    return all(isinstance(a, dict) and a.get("act") == "clarify"
               and L138.NOT_UNDERSTOOD in str(a.get("text", ""))
               for a in actions)


class TableTeach229Mixin:
    """Outermost ears mixin: table teaches on base-missed statements."""

    table229_path: str | None = None

    def _mark229(self, how: str) -> None:
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                f"{STAGE229}-{how}", 1.0)
        except AttributeError:
            pass

    def _nosave229(self, why: str) -> list[dict]:
        self._mark229("nosave")
        return [{"act": "clarify", "table229": "nosave",
                 "text": f"{NOT_SAVED229}: {why}."}]

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        t = " ".join(str(turn).split())
        if not t or t.endswith("?") or not base_missed229(actions):
            return actions
        if getattr(self, "nb", None) is None:
            return actions
        tb = load_table229(getattr(self, "table229_path", None))
        rds = table_teach_readings229(t, tb)
        if not rds:
            return actions
        checked = []
        for r_ in rds:
            why_ = subject_ok229(r_["X"]) or value_ok229(
                tb["rels"][r_["rel"]], r_["Y"], r_["how"])
            checked.append((r_, why_))
        passing = [r_ for r_, w_ in checked if w_ is None]
        if len(passing) > 1:
            return self._nosave229("I could read it more than one way")
        if not passing:
            r_, w_ = checked[0]
            who_ = "your" if r_["X"] == USER229 else f"{r_['X']}'s"
            return self._nosave229(
                f"I read it as {who_} {r_['rel'].replace('_', ' ')} is "
                f"{r_['Y']}, but {w_}")
        rd = passing[0]
        x, y = rd["X"], rd["Y"]
        if rd["rel"] == "occupation" and y.lower() in OCC229:
            y = y.lower()
        rdisp = rd["rel"].replace("_", " ")
        who = "your" if x == USER229 else f"{x}'s"
        cand = canonical_sentence229(x, rd["rel"], y)
        base = super().hear(cand)  # type: ignore[misc]
        screened = screen_turn209(base)
        teaches = [a for a in screened if isinstance(a, dict)
                   and a.get("act") in ("teach", "correct")]
        keys = group_keys229(tb, rd["rel"])
        if teaches:
            ok = all(_norm(a.get("name", "")) == _norm(x)
                     and key221(str(a.get("relation", ""))) in keys
                     and _norm(a.get("value", "")) == _norm(y)
                     for a in teaches)
            others = [a for a in screened if a not in teaches]
            if ok and not others:
                self._mark229(rd["how"])
                return [dict(a, table229=rd["rel"]) for a in screened]
            return self._nosave229(f"I read it as {who} {rdisp} is {y}, "
                                   "but I could not store it that way")
        if base_missed229(screened) or not screened:
            return self._nosave229(f"I read it as {who} {rdisp} is {y}, "
                                   "but I could not store it that way")
        # the base's own clarify for the canonical sentence (a screen
        # refusal or a confirmation question): keep it, say plainly.
        self._mark229("baseclarify")
        out = []
        for a in screened:
            if isinstance(a, dict) and a.get("act") == "clarify":
                a = dict(a, text=f"{NOT_SAVED229} yet. "
                         + str(a.get("text", "")))
            out.append(a)
        return out


# ------------------------------------------------------------ agent
class Loop229Ears(TableTeach229Mixin, L138I.Loop138iEars):
    name = "loop229-tableteach"


class Loop229AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop unchanged (renamed for logs)."""


DEFAULT_CONFIG229: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG229["ears"]["stand_in"] = (
    L138I.DEFAULT_CONFIG138I["ears"]["stand_in"]
    + "; 229 table teaches outermost on base-missed statements (relation "
    "table v1 read-only + sealed EXT229; 209 write screen)")
DEFAULT_CONFIG229["daemon"]["module"] = "Loop229Daemon (this file)"
DEFAULT_CONFIG229["table229_path"] = str(TABLE_PATH221)


def build_agent229(cfg: dict | None = None) -> Loop229AgentLoop:
    """build_agent138i with only the inner ears class swapped."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG229, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    sleeper = L138I.HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop229Ears(Loop96Ears(chain))
    inner_ears.table229_path = cfg.get("table229_path") or None
    loop = Loop229AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    L138I.patch_chain142(chain)
    L138I.patch_loop121_teach(inner_ears)
    thinker, thinker_module = L138I.L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = L138I.D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop229: loop138i + TableTeach229Mixin outermost "
                      "(table teaches on base-missed statements)")
    return loop


class Loop229Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 229 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138I.D141.SETTLE_GRACE_S) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent229(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon229(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop229Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 229 table teaches")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--readings", default=None,
                        help="print table teach readings of TEXT and exit")
    args = parser.parse_args(argv)
    if args.readings:
        for r in table_teach_readings229(args.readings):
            print(r)
        return 0
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG229)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG229)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon229(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent229(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
