#!/usr/bin/env python3
"""Exp 221 -- QUESTIONS READ THROUGH THE RELATION TABLE (writes untouched).

One stackable ears mixin, TableAsk221Mixin, meant to sit OUTERMOST on
Loop138iEars (before ChainOf174Mixin, scripts/fable_loop138i_agent.py:336).
It loads the relation table v1 READ-ONLY from
artifacts/claude-relationtable-20260922/relation_table_v1.json (design:
design/v3/30-modes/217-relationtable-design.md section 6).

It acts only on turns that end in "?", and only in three cases. In all it
emits ask or clarify actions, never teach/correct/forget, so no write path
is reachable from this stage:

(a) BASE MISS. The full 138i stack understood nothing (no actions, or
    every action a not-understood clarify; base_missed221). The turn is
    matched against the table's ask and inverse
    templates (generic families + per-relation rows; yes/no and teach rows
    are NOT used in this build). Exactly one distinct reading is required;
    zero or two-plus readings leave the base clarify byte-identical.
      forward reading -> a normal ask action {"act": "ask", "name": X,
        "relations": [key]} (X = "USER" + me166 flag for "my"), after the
        key choice in (b).
      inverse reading -> one clarify action whose text is forward-style
        sentences read from live taught facts plus "(worked out
        backwards)"; nothing is stored. No match -> an honest "I don't
        know anyone whose ..." line (fable_fix190_reverse.py:189 wording).
(b) EMPTY KEY. The base (or (a)) produced a single-hop ask on key k, the
    subject resolves, k has NO current answering row, and k belongs to a
    table group (canonical key, true alias, legacy storage key, legacy
    swapped key, or a narrower relation's keys). If exactly one other
    group key holds a current value -> the ask is re-pointed to it. If
    several keys hold the same value -> the first in table order. If they
    hold different values: multi-valued relation -> every fact listed;
    single-valued -> both listed and the user is asked which is right
    (never picks one). A key that already has a value is never touched
    (taught facts win).

(c) LIVE REVERSE REPLY. The 138i stack's own reverse stage (153,
    scripts/fable_fix153_reverse.py:118 answer_reverse) answered a
    "Whose R is Y?"-type turn from one exact key. Its answer gets the
    label " (worked out backwards)" appended (text otherwise unchanged).
    Its "I don't know anyone whose R is Y." is replaced by the table
    inverse answer ONLY if the table's key group (aliases, storage keys,
    narrower relations) finds a subject; otherwise it stays byte-identical.

Self questions (any you/your word) and turns whose slots look like
pronouns, chains ('s, "of the"), or lists are never claimed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix153_reverse as R153  # noqa: E402 (live reverse, read-only)
import fable_fix190_reverse as R190  # noqa: E402 (helpers, read-only)
import fable_loop138_agent as L138  # noqa: E402 (NOT_UNDERSTOOD, read-only)
import fable_loop90_agent as L90  # noqa: E402 (live taught triples, read-only)

ROOT = SCRIPTS.parent
TABLE_PATH221 = (ROOT / "artifacts" / "claude-relationtable-20260922"
                 / "relation_table_v1.json")
LABEL221 = "(worked out backwards)"
USER_KEY221 = "USER"  # fable_fix166_me.py:49
STAGE221 = "loop221-table"

_SELF_WORDS = frozenset({"you", "your", "yours", "yourself", "u", "ur"})
_BAD_START = frozenset({
    "he", "she", "they", "it", "this", "that", "these", "those", "him",
    "her", "them", "we", "us", "i", "me", "my", "mine", "who", "what",
    "where", "when", "which", "whose", "why", "how", "his", "their", "its",
    "our", "there", "here", "someone", "somebody", "anyone", "anybody",
    "everyone", "everybody", "nobody", "something", "anything"})
_BAD_START_LOWER_ONLY = frozenset({"the", "a", "an"})
# a slot never ENDS in one of these (catches "The Glass Orchard married
# to" in "Who is the author of The Glass Orchard married to?")
_BAD_END = frozenset({
    "to", "of", "in", "at", "for", "by", "with", "from", "on", "about",
    "into", "as", "married", "born", "called", "named", "is", "was", "are",
    "were", "be", "been", "does", "did", "do", "has", "have", "had",
    "the", "a", "an", "and", "or", "who", "whose", "which", "that"})
_BAD_INNER = frozenset({"is", "was", "are", "were", "whose", "who",
                        "which", "that", "does", "did"})
_MONTHS = ("january february march april may june july august september "
           "october november december jan feb mar apr jun jul aug sep sept "
           "oct nov dec").split()


def key221(surface: str) -> str:
    """FakeEars._relation rule (scripts/fable_agent_loop.py:151)."""
    return "_".join(str(surface).lower().split())


def disp221(key: str) -> str:
    return str(key).replace("_", " ")


def _norm(s: str) -> str:
    return " ".join(str(s).split()).strip().rstrip(".").lower()


# ------------------------------------------------------------------ table
def compile_template221(t: str) -> re.Pattern:
    """Template -> regex (same syntax as scripts/claude_relationtable_check.py
    compile_template): {SLOT} lazy named groups, (a|b) alternation,
    [word] optional word."""
    out, i = [], 0
    body = t.rstrip(" .?!")
    while i < len(body):
        ch = body[i]
        if ch == "{":
            j = body.index("}", i)
            out.append(f"(?P<{body[i + 1:j]}>.+?)")
            i = j + 1
        elif ch == "(":
            j = body.index(")", i)
            alts = [re.escape(a) for a in body[i + 1:j].split("|")]
            out.append("(?:" + "|".join(alts) + ")")
            i = j + 1
        elif ch == "[":
            j = body.index("]", i)
            word = re.escape(body[i + 1:j])
            if j + 1 < len(body) and body[j + 1] == " ":
                out.append(f"(?:{word} )?")
                i = j + 2
            else:
                out.append(f"(?:{word})?")
                i = j + 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("".join(out).replace("\\ ", " "), re.IGNORECASE)


def looks_like_date221(v: str) -> bool:
    toks = re.findall(r"[a-z]+|\d+", str(v).lower())
    if not toks:
        return False
    return all(t in _MONTHS or t.isdigit()
               or t in ("st", "nd", "rd", "th", "of", "the")
               for t in toks) and any(
        t in _MONTHS or (t.isdigit() and len(t) == 4) for t in toks)


def _guard_ok(rel: dict, value: str | None) -> bool:
    g = rel.get("value_guard") or ""
    if value is None:
        return True
    if g.startswith("value must look like a date"):
        return looks_like_date221(value)
    if g.startswith("value must NOT look like a date"):
        return not looks_like_date221(value)
    return True


class Table221:
    """Read-only view of relation_table_v1.json for the question side."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else TABLE_PATH221
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.version = data.get("version")
        self.rels: dict[str, dict] = {r["name"]: r for r in data["relations"]}
        self.order = [r["name"] for r in data["relations"]]
        gen = data["generic_patterns"]
        # key -> relation name
        self.key2rel: dict[str, str] = {}
        self.invkey2rel: dict[str, str] = {}
        for r in data["relations"]:
            for k in ([r["name"]] + [key221(a) for a in r["aliases"]]
                      + list(r.get("storage_keys", []))):
                self.key2rel.setdefault(key221(k), r["name"])
            for k in r.get("inverse_storage_keys", []):
                self.invkey2rel.setdefault(key221(k), r["name"])
        # compiled question patterns: (rel, kind, regex, template)
        self.patterns: list[tuple[str, str, re.Pattern, str]] = []
        for r in data["relations"]:
            pats: list[tuple[str, dict]] = []
            for fam in r["generic"]:
                for kind, lst in gen[fam].items():
                    if kind in ("ask", "inverse"):
                        pats += [(kind, p) for p in lst]
            for kind in ("ask", "inverse"):
                pats += [(kind, p) for p in r[kind]]
            surfaces = [r["name"].replace("_", " ")] + list(r["aliases"])
            seen = set()
            for kind, p in pats:
                t = p["t"]
                rs = surfaces if "{R}" in t else [None]
                whs = r["wh"] if "{WH}" in t else [None]
                for s in rs:
                    for wh in whs:
                        c = t
                        if s is not None:
                            c = c.replace("{R}", s)
                        if wh is not None:
                            c = c.replace("{WH}", wh)
                        if (kind, c) in seen:
                            continue
                        seen.add((kind, c))
                        self.patterns.append(
                            (r["name"], kind, compile_template221(c), c))

    def forward_keys(self, name: str, narrower: bool = True) -> list[str]:
        r = self.rels[name]
        out: list[str] = []
        for k in ([r["name"]] + [key221(a) for a in r["aliases"]]
                  + list(r.get("storage_keys", []))):
            k = key221(k)
            if k not in out:
                out.append(k)
        if narrower:
            for n in r.get("narrower", []):
                if n in self.rels:
                    for k in self.forward_keys(n, narrower=False):
                        if k not in out:
                            out.append(k)
        return out

    def inverse_keys(self, name: str) -> list[str]:
        return [key221(k) for k in
                self.rels[name].get("inverse_storage_keys", [])]


_TABLE_CACHE: dict[str, Table221] = {}


def get_table221(path: Path | str | None = None) -> Table221:
    p = str(Path(path) if path else TABLE_PATH221)
    if p not in _TABLE_CACHE:
        _TABLE_CACHE[p] = Table221(p)
    return _TABLE_CACHE[p]


# ---------------------------------------------------------------- reading
def _slot_ok(v: str) -> bool:
    v = v.strip()
    if not v or len(v.split()) > 6:
        return False
    low = v.lower()
    toks = re.findall(r"[a-z]+", low)
    if not toks:
        return not re.search(r"[?!;]", v) and bool(re.search(r"\d", v))
    if any(t in _SELF_WORDS for t in toks):
        return False
    first = v.split()[0]
    if first.lower() in _BAD_START:
        return False
    if first in _BAD_START_LOWER_ONLY:
        return False
    if "'s" in low or "’s" in low or " of the " in f" {low} ":
        return False
    words = v.split()
    if words[-1].lower() in _BAD_END:
        return False
    if any(w in _BAD_INNER for w in words[1:]):  # lowercase clause words
        return False
    if re.search(r"[?!;,]", v) or " and " in f" {low} " or " or " in f" {low} ":
        return False
    return True


def table_readings221(turn: str, table: Table221 | None = None) -> list[dict]:
    """Every distinct (relation, kind, X, Y) question reading of the turn.

    Pure function of the turn text + the table. kind is "ask" (forward) or
    "inverse". X == USER_KEY221 for "my" templates. Self questions (any
    you-word token) give no readings.
    """
    table = table or get_table221()
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return []
    if set(re.findall(r"[a-z]+", t.lower())) & _SELF_WORDS:
        return []
    body = t.rstrip(" .?!")
    out: list[dict] = []
    seen = set()
    for rel, kind, rx, tmpl in table.patterns:
        m = rx.fullmatch(body)
        if not m:
            continue
        g = {k: v.strip() for k, v in m.groupdict().items() if v}
        r = table.rels[rel]
        if kind == "ask":
            if "X" not in g:
                if re.search(r"\bmy\b", tmpl.lower()):
                    g["X"] = USER_KEY221
                else:
                    continue
            elif not _slot_ok(g["X"]):
                continue
        else:
            if "Y" not in g or not _slot_ok(g["Y"]):
                continue
            if r.get("date_rule"):
                for w in r["date_rule"]["strip_leading"]:
                    if g["Y"].lower().startswith(w + " "):
                        g["Y"] = g["Y"][len(w) + 1:]
            if not _guard_ok(r, g["Y"]):
                continue
        sig = (rel, kind, _norm(g.get("X", "")), _norm(g.get("Y", "")))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({"rel": rel, "kind": kind, "X": g.get("X"),
                    "Y": g.get("Y"), "template": tmpl})
    return out


def unique_reading221(turn: str, table: Table221 | None = None):
    rd = table_readings221(turn, table)
    return rd[0] if len(rd) == 1 else None


# ------------------------------------------------------- notebook peeks
def _resolve(nb, name: str) -> str | None:
    try:
        found = nb.resolve(name)
    except Exception:  # noqa: BLE001
        return None
    if getattr(found, "status", None) != "OK":
        return None
    return found.detail.get("entity_id")


def _values(nb, eid: str, key: str) -> list[str]:
    try:
        rows = nb.current(eid, key)
    except Exception:  # noqa: BLE001
        return []
    return [nb._show(r["value"]) for r in rows]


def _who(nb, eid: str) -> str:
    name = nb.entities.get(eid, eid)
    return "Your" if name == USER_KEY221 else f"{name}'s"


def choose_key221(nb, name: str, key: str, table: Table221 | None = None):
    """Key choice for a single-hop ask on (name, key). Read-only.

    Returns None (leave the ask alone), ("swap", new_key), or
    ("text", reply) for a multi-valued listing / single-valued conflict.
    """
    table = table or get_table221()
    k = key221(key)
    rel = table.key2rel.get(k)
    via_inverse_key = False
    if rel is None:
        rel = table.invkey2rel.get(k)
        via_inverse_key = rel is not None
    if rel is None or nb is None:
        return None
    eid = _resolve(nb, name)
    if eid is None:
        return None
    if not via_inverse_key and _values(nb, eid, k):
        return None  # the asked key already answers: taught facts win
    hits = []
    for cand in table.forward_keys(rel):
        if cand == k:
            continue
        vals = _values(nb, eid, cand)
        if vals:
            hits.append((cand, vals))
    if not hits:
        return None
    sets = {tuple(sorted(_norm(v) for v in vals)) for _c, vals in hits}
    if len(sets) == 1:
        return ("swap", hits[0][0])
    who = _who(nb, eid)
    lines = [f"{who} {disp221(c)} is {', '.join(vals)}." for c, vals in hits]
    if table.rels[rel].get("cardinality") == "multi":
        return ("text", " ".join(lines))
    return ("text", " ".join(lines) + " These disagree, so I will not "
            "pick one. Which is right?")


def inverse_answer221(nb, rel: str, value: str,
                      table: Table221 | None = None) -> str:
    """Answer-time inverse lookup over live taught facts; never stored."""
    table = table or get_table221()
    fkeys = set(table.forward_keys(rel))
    ikeys = set(table.inverse_keys(rel))
    want = _norm(value)
    lines: list[str] = []
    triples = L90.notebook_triples(nb) if nb is not None else []
    for subj, r, val in triples:
        if r in fkeys and _norm(val) == want:
            who = "Your" if subj == USER_KEY221 else f"{subj}'s"
            line = f"{who} {disp221(r)} is {str(val).strip().rstrip('.')}."
        elif r in ikeys and _norm(subj) == want:
            line = (f"{str(val).strip().rstrip('.')}'s {disp221(rel)} is "
                    f"{subj}.")
        else:
            continue
        if line not in lines:
            lines.append(line)
    if lines:
        return " ".join(lines) + " " + LABEL221
    v = str(value).strip().rstrip(".")
    if R190.is_known_name190(nb, v):
        return f"I don't know anyone whose {disp221(rel)} is {v}."
    return f"I don't know anyone called {v}."


# ------------------------------------------------------------------ mixin
def base_missed221(actions) -> bool:
    """True iff the base understood nothing: no actions, or every action a
    clarify carrying the not-understood text (the same test the self
    router's notebook_missed applies, fable_loop138_agent.py:162). A
    clarify that already answers (e.g. the 153 reverse reply) is NOT a
    miss and is left alone."""
    if not isinstance(actions, list):
        return False
    if not actions:
        return True
    return all(isinstance(a, dict) and a.get("act") == "clarify"
               and L138.NOT_UNDERSTOOD in str(a.get("text", ""))
               for a in actions)


class TableAsk221Mixin:
    """Outermost stackable ears mixin (question side only; never writes)."""

    table221_path: str | None = None

    def _table221(self) -> Table221:
        return get_table221(getattr(self, "table221_path", None))

    def _mark221(self, how: str) -> None:
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                f"{STAGE221}-{how}", 1.0)
        except AttributeError:
            pass

    def _rekey221(self, act: dict, nb, table: Table221) -> dict:
        rels = act.get("relations") or []
        if len(rels) != 1 or not act.get("name") or act.get("entity_id"):
            return act
        choice = choose_key221(nb, str(act["name"]), str(rels[0]), table)
        if choice is None:
            return act
        if choice[0] == "swap":
            new = dict(act)
            new["relations"] = [choice[1]]
            new["table221"] = f"{rels[0]}->{choice[1]}"
            return new
        return {"act": "clarify", "text": choice[1], "table221": "list"}

    def _reverse153_221(self, t: str, actions, nb, table):
        """(c): label / widen the live 153 reverse reply. None = no change."""
        if len(actions) != 1 or not isinstance(actions[0], dict) \
                or actions[0].get("act") != "clarify":
            return None
        parsed = R153.parse_reverse(t)
        if parsed is None:
            return None
        rel_s, val = R153._norm(parsed[0]), R153._norm(parsed[1]).rstrip(".")
        text = str(actions[0].get("text", ""))
        if text.startswith(f"{val} is the {rel_s} of ") \
                and LABEL221 not in text:
            self._mark221("label153")
            return [dict(actions[0], text=f"{text} {LABEL221}",
                         table221="label153")]
        if text == f"I don't know anyone whose {rel_s} is {val}.":
            rd = unique_reading221(t, table)
            if rd is None or rd["kind"] != "inverse":
                return None
            ans = inverse_answer221(nb, rd["rel"], rd["Y"], table)
            if LABEL221 not in ans:
                return None
            self._mark221("widen153")
            return [{"act": "clarify", "text": ans, "table221": "widen153"}]
        return None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        t = " ".join(str(turn).split())
        if not t.endswith("?") or not isinstance(actions, list):
            return actions
        nb = getattr(self, "nb", None)
        if nb is None:
            return actions
        table = self._table221()
        if base_missed221(actions):
            rd = unique_reading221(t, table)
            if rd is None:
                return actions
            if rd["kind"] == "inverse":
                self._mark221("inverse")
                return [{"act": "clarify", "table221": "inverse",
                         "text": inverse_answer221(nb, rd["rel"], rd["Y"],
                                                   table)}]
            act = {"act": "ask", "name": rd["X"],
                   "relations": [key221(rd["rel"])], "stage": STAGE221}
            if rd["X"] == USER_KEY221:
                act["me166"] = True
            self._mark221("ask")
            return [self._rekey221(act, nb, table)]
        rev = self._reverse153_221(t, actions, nb, table)
        if rev is not None:
            return rev
        out = []
        changed = False
        for a in actions:
            if isinstance(a, dict) and a.get("act") == "ask":
                b = self._rekey221(a, nb, table)
                if b is not a:
                    changed = True
                out.append(b)
            else:
                out.append(a)
        if changed:
            self._mark221("rekey")
            return out
        return actions


# --------------------------------------------------------------- selftest
def selftest221() -> int:
    tb = get_table221()
    checks = [
        ("Who composed Blue Rain?", ("composer", "ask", "Blue Rain", None)),
        ("What did Ada Pell compose?", ("composer", "inverse", None, "Ada Pell")),
        ("When is my birthday?", ("birthday", "ask", USER_KEY221, None)),
        ("When is Pia's birthday?", ("birthday", "ask", "Pia", None)),
        ("Who is the manager of Kim?", ("boss", "ask", "Kim", None)),
        ("What is the manager of Kim?", ("boss", "ask", "Kim", None)),
        ("Who works at Acme?", ("employer", "inverse", None, "Acme")),
        ("Who painted Tin Stars?", ("painter", "ask", "Tin Stars", None)),
        ("Who is Kim's?", None),
        ("What is your name?", None),
        ("Who made you?", None),
        ("Who is the boss of Kim's sister?", None),
        ("Kim's boss is Sam.", None),
        ("Who is the author of The Glass Orchard married to?", None),
        ("who is bram kite married to?", ("spouse", "ask", "bram kite", None)),
    ]
    ok = True
    for text, want in checks:
        rds = table_readings221(text, tb)
        got = None
        if len(rds) == 1:
            r = rds[0]
            got = (r["rel"], r["kind"], r["X"], r["Y"])
        elif len(rds) > 1:
            got = ("AMBIGUOUS", len(rds))
        flag = "OK" if got == want else "MISMATCH"
        ok = ok and got == want
        print(f"{flag}: {text!r} -> {got} (want {want})", flush=True)
    print(f"patterns={len(tb.patterns)} relations={len(tb.rels)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest221())
