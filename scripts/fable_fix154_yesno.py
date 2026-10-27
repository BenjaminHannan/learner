#!/usr/bin/env python3
"""Experiment 154 -- THE ONE CHANGE: a yes/no stage on loop150 (additive).

Director probe on loop150: after "Ann's mother is Rita.", both
"Is Rita Ann's mother?" and "Is Bob Tom's boss?" get "I didn't understand
that". The forward path only answers who/what/where questions, so every
"Is ...?" turn falls through to the ChainEars total miss.

THE RULE (a yes/no stage that runs ONLY when the forward path did not
understand): when the unchanged forward path returns the single
"didn't understand" clarify for a turn shaped like one of

  "Is V X's R?" / "Is V the R of X?" / "Is X's R V?" /
  "Is X's R1's R2 V?"

rewrite it into the wh-question the loop already answers
("Who is X's R?" / "Who is X's R1's R2?"), run THAT through the UNCHANGED
forward path (same ears hear + same _act/_ask, read-only), and compare the
answered value with V (exact, after the loop's own normalisation:
whitespace collapse + the exp-129 sentence-punctuation strip on both sides,
relation keys via FakeEars._relation as the loop itself maps them):

  same value -> "Yes -- <owner> is <answer>."
  different value AND the last hop is single-valued per SINGLE_VALUED_154
    below -> "No -- <owner> is <answer>."
  different value on a multi-valued relation (friend, child, sibling,
    sister, brother, notable_work, ...) -> "I only know that <owner> is
    <answer>." (never "No")
  the forward path does not know / abstains (MISSING_FACT, UNKNOWN_ENTITY,
    AMBIGUOUS, BROKEN_CHAIN, any non-OK) -> its own honest reply (never
    "No"; e.g. "I don't know ...").

The stage never writes: the wh run only ever executes ask/clarify actions
(any teach/correct/forget/person/alias/quote/answer action aborts back to
the base clarify), and the final record is a clarify the mouth renders
verbatim. Anything that is not one of the four shapes (e.g. "Is Bob a
doctor?") passes through untouched.

Cooperative MIXIN (YesNo154Mixin, loop level): _listening_tick peeks at the
inbox head, runs the base ears hear first, and only diverts when the base
returns exactly the didn't-understand clarify AND the turn parses. All
other turns delegate byte-identical to super(). No existing file edited.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (LISTENING mode, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_notebook_contract as C  # noqa: E402 (OK status, read-only)

# Sealed code table: last-hop relations on which a differing answered value
# licenses a "No". One line of reason each (single active slot; a correction
# supersedes, so a second value for the same slot is impossible, not merely
# unknown). Every other relation is multi-valued: a different known value
# does not falsify V ("I only know that ...", never "No").
SINGLE_VALUED_154 = frozenset({
    "mother",          # one mother slot; a correction supersedes her
    "father",          # one father slot; same supersession rule
    "capital",         # one capital per country by definition
    "place_of_birth",  # born in exactly one city
    "date_of_birth",   # born on exactly one date
    "city",            # one current city per person in this loop
    "spouse",          # one active spouse; corrections supersede
    "wife",            # same as spouse (surface variant)
    "husband",         # same as spouse (surface variant)
    "boss",            # one current boss per person in this loop
    "teacher",         # one current teacher per person in this loop
})

# The forward path's total-miss reply (ChainEars miss at
# scripts/fable_loop90_agent.py:291-292, same text as FakeEars' final
# clarify at scripts/fable_agent_loop.py:148). The stage fires ONLY on this.
DIDNT_UNDERSTAND_154 = "didn't understand that"

_POSS_154 = re.compile(r"['\u2019]s\b")
_ISQ_154 = re.compile(r"(?i)^\s*is\s+(.+?)\s*\?+\s*[!.]*\s*$")
_OF_154 = re.compile(r"(?i)^(.+?)\s+the\s+(.+?)\s+of\s+(.+?)$")

# Person relations get a "Who" rewrite, everything else "What" (both take
# the identical FakeEars possessive path; the word choice is cosmetic).
_WHO_154 = frozenset({
    "mother", "father", "sister", "brother", "sibling", "child", "friend",
    "boss", "teacher", "wife", "husband", "spouse", "partner", "neighbour",
    "neighbor",
})


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def norm_value154(span: str) -> str:
    """The loop's own value normalisation: collapse + 129 strip."""
    return P129.strip_sentence_punct(_collapse(span))


def relation_key154(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def parse_yesno154(turn: str) -> dict | None:
    """Parse the four sealed shapes -> {v, name, relations, owner} | None."""
    t = _collapse(turn)
    m = _ISQ_154.match(t)
    if not m:
        return None
    body = m.group(1).strip()
    if not body:
        return None
    of = _OF_154.match(body)
    if of is not None:
        v, rel, name = (of.group(1).strip(), of.group(2).strip(),
                        of.group(3).strip())
        if not v or not rel or not name:
            return None
        if _POSS_154.search(name) or _POSS_154.search(v):
            return None
        return {"v": v, "name": name, "relations": [rel],
                "owner": f"{name}'s {rel}"}
    parts = _POSS_154.split(body)
    if len(parts) == 2:
        left, right = parts[0].strip(), parts[1].strip()
        lt, rt = left.split(), right.split()
        if len(lt) == 1 and len(rt) >= 2:
            # "Is X's R V?" (V is one trailing token by sealed rule)
            return {"v": rt[-1], "name": left,
                    "relations": [" ".join(rt[:-1])],
                    "owner": f"{left}'s {' '.join(rt[:-1])}"}
        if len(rt) == 1 and len(lt) >= 2:
            # "Is V X's R?" (X is one leading token by sealed rule)
            return {"v": " ".join(lt[:-1]), "name": lt[-1],
                    "relations": [right],
                    "owner": f"{lt[-1]}'s {right}"}
        return None
    if len(parts) == 3:
        # "Is X's R1's R2 V?" (two-hop, sealed shape only)
        name, rel1, rest = (parts[0].strip(), parts[1].strip(),
                            parts[2].strip())
        rt = rest.split()
        if not name or not rel1 or len(rt) < 2:
            return None
        rel2, v = " ".join(rt[:-1]), rt[-1]
        return {"v": v, "name": name, "relations": [rel1, rel2],
                "owner": f"{name}'s {rel1}'s {rel2}"}
    return None


def rewrite_wh154(parsed: dict) -> str:
    """The wh-question the loop already answers (possessive FakeEars path)."""
    last_key = relation_key154(parsed["relations"][-1])
    qword = "Who" if last_key in _WHO_154 else "What"
    chain = "'s ".join([parsed["name"]] + list(parsed["relations"]))
    return f"{qword} is {chain}?"


def is_miss154(actions) -> bool:
    """True iff the forward path did not understand (single clarify)."""
    return (isinstance(actions, list) and len(actions) == 1
            and isinstance(actions[0], dict)
            and actions[0].get("act") == "clarify"
            and DIDNT_UNDERSTAND_154 in str(actions[0].get("text", "")))


class YesNo154Mixin:
    """Stackable loop-level mixin: yes/no only on the didn't-understand miss.

    Cooperative (super() first on every other turn): _listening_tick peeks
    at the inbox head through the unchanged ears hear; non-miss turns and
    non-yes/no shapes delegate byte-identical to super(). The wh run uses
    the same ears hear and the same _act (read-only ask path); any
    write-shaped wh action aborts back to the base clarify. Counters,
    last_records, experience and the event shape match the parent exactly.
    """

    def _listening_tick(self):  # type: ignore[no-redef]
        text = self.inbox[0] if getattr(self, "inbox", None) else None
        if text is not None:
            try:
                base = self.ears.hear(text)  # type: ignore[attr-defined]
            except Exception:
                base = None
            if base is not None and is_miss154(base):
                parsed = parse_yesno154(text)
                if parsed is not None:
                    return self._yesno_tick(text, base, parsed)
        return super()._listening_tick()  # type: ignore[misc]

    def _yesno_tick(self, text: str, base: list[dict], parsed: dict) -> dict:
        self.inbox.pop(0)  # type: ignore[attr-defined]
        self.counters["turns"] += 1  # type: ignore[attr-defined]
        wh = rewrite_wh154(parsed)
        try:
            wh_actions = self.ears.hear(wh)  # type: ignore[attr-defined]
            try:
                self.ears.last_stage = (  # type: ignore[attr-defined]
                    f"loop154-yesno+{self.ears.last_stage}")  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 -- stage tag is cosmetic only
                pass
        except Exception:  # noqa: BLE001 -- never raise out of a turn
            wh_actions = [{"act": "clarify",
                           "text": ("I didn't understand that. Could you "
                                    "say it another way?")}]
        if not (isinstance(wh_actions, list) and len(wh_actions) == 1
                and isinstance(wh_actions[0], dict)
                and wh_actions[0].get("act") in ("ask", "clarify")):
            # Write-shaped wh action (teach/correct/forget/...): abort to
            # the base clarify. This path provably never writes.
            records = [self._act(a) for a in base]  # type: ignore[misc]
            return self._finish_yesno(text, records)
        if wh_actions[0].get("act") == "clarify":
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            record = {"kind": "clarify",
                      "text": wh_actions[0].get("text", "")}
            return self._finish_yesno(text, [record])
        ask = dict(wh_actions[0])
        wh_record = self._act(ask)  # type: ignore[misc]  # read-only ask
        if wh_record.get("status") != C.OK:
            # The forward path does not know: its own honest reply, never No.
            return self._finish_yesno(text, [wh_record])
        answer = str((wh_record.get("fields") or {}).get("answer", ""))
        owner = parsed["owner"]
        if norm_value154(answer) == norm_value154(parsed["v"]):
            reply = f"Yes \u2014 {owner} is {answer}."
        elif relation_key154(parsed["relations"][-1]) in SINGLE_VALUED_154:
            reply = f"No \u2014 {owner} is {answer}."
        else:
            reply = f"I only know that {owner} is {answer}."
        self.counters["clarifications"] += 1  # type: ignore[attr-defined]
        final = {"kind": "clarify", "text": reply}
        self.last_records = [wh_record, final]  # type: ignore[attr-defined]
        said = [line for line in
                (self.mouth.say(r) for r in [final])  # type: ignore[attr-defined]
                if line]
        self.experience.append(  # type: ignore[attr-defined]
            {"tick": self.tick, "kind": "turn", "text": text,  # type: ignore[attr-defined]
             "statuses": [r.get("status", r["kind"]) for r in [final]]})
        return self._event(A.LISTENING,  # type: ignore[attr-defined]
                           {"turn": text, "records": [wh_record, final]}, said)

    def _finish_yesno(self, text: str, records: list[dict]) -> dict:
        self.last_records = list(records)  # type: ignore[attr-defined]
        said = [line for line in
                (self.mouth.say(r) for r in records)  # type: ignore[attr-defined]
                if line]
        self.experience.append(  # type: ignore[attr-defined]
            {"tick": self.tick, "kind": "turn", "text": text,  # type: ignore[attr-defined]
             "statuses": [r.get("status", r["kind"]) for r in records]})
        return self._event(A.LISTENING,  # type: ignore[attr-defined]
                           {"turn": text, "records": records}, said)
