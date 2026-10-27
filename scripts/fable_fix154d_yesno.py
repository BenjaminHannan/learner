#!/usr/bin/env python3
"""Experiment 154d -- THE ONE CHANGE: grounded yes/no on loop138f (additive).

Director probe on loop138f: after "Zuri's sister is Bela.", both
"Is Bela Zuri's sister?" and "Is Ama Zuri's sister?" fall back to the base
abstain. The old 154 yes/no stage (scripts/fable_fix154_yesno.py) is OFF on
loop138f for cause: it answered Is-questions on didn't-understand turns via
a wh-run, saying "Yes -- Norland's capital is Aldport" where abstain is
sealed (redteam143 M3). Its own suggested fix (design doc 138f): answer
yes/no only on single-mention grounded frames.

THE RULE (a yes/no stage that runs ONLY when the forward path did not
understand): when the unchanged forward path returns the single
"didn't understand" clarify for a turn shaped EXACTLY like one of

  "Is V X's R?" / "Is X's R V?"

(one "'s", single-token capitalised V and X, lowercase relation surface,
no "or"/"and", trailing "?"), look the frame up in the NOTEBOOK directly
(never the wh-run):

  X resolves to exactly one taught subject AND the notebook holds at
  least one current fact for (X, R):
    some stored display value equals V (loop normalisation: whitespace
    collapse + exp-129 sentence-punctuation strip, case-SENSITIVE) ->
      "Yes, X's R is V."
    otherwise AND R is single-valued per SINGLE_VALUED_154 (imported
    read-only from scripts/fable_fix154_yesno.py -- never the mixin) ->
      "No, X's R is W."  (W = stored display value)
    otherwise (multi-valued relation) ->
      "Not that I know of. I have W as X's R."  (never "No")
  anything else (unknown subject, relation not stored, ambiguous X, any
  other shape: of-forms, two-hop, hypotheticals, statements, lowercase
  names, "or"-questions, ...) -> the base reply UNCHANGED (delegate to
  super(), byte-identical).

The stage never writes: it only calls nb.resolve / nb.current (reads),
and the final record is a clarify the mouth renders verbatim. No teach /
correct / forget / alias path is reachable.

Cooperative MIXIN (YesNo154dMixin, loop level): _listening_tick peeks at
the inbox head, runs the base ears hear first, and only diverts when the
base returns exactly the didn't-understand clarify AND the turn parses
AND the notebook grounds it. All other turns delegate byte-identical to
super(). No existing file edited.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (LISTENING mode + FakeEars map, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_notebook_contract as C  # noqa: E402 (OK status, read-only)
from fable_fix154_yesno import SINGLE_VALUED_154  # noqa: E402 (code table only)

# The forward path's total-miss reply (same text the old 154 stage keyed
# on). The stage fires ONLY on this.
DIDNT_UNDERSTAND_154D = "didn't understand that"

_ISQ_154D = re.compile(r"^\s*Is\s+(.+?)\s*\?+\s*$")
_POSS_154D = re.compile(r"['\u2019]s\b")
_NAME_154D = re.compile(r"^[A-Z][A-Za-z\-]*$")
_REL_154D = re.compile(r"^[a-z]+(?:[ \-][a-z]+)*$")
_ORAND_154D = re.compile(r"(?i)\b(or|and)\b")


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def norm_value154d(span: str) -> str:
    """The loop's own value normalisation: collapse + 129 strip (case kept)."""
    return P129.strip_sentence_punct(_collapse(span))


def relation_key154d(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def show_value154d(nb, value: dict) -> str:
    """Notebook display for a stored value (mirrors Notebook._show, read)."""
    if isinstance(value, dict) and "entity" in value:
        return str(nb.entities.get(value["entity"], value["entity"]))
    if isinstance(value, dict) and "literal" in value:
        return str(value["literal"])
    return str(value)


def join_and154d(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f" and {values[-1]}"


def parse_yesno154d(turn: str) -> dict | None:
    """Parse the two sealed shapes -> {v, x, rel, key, owner} | None."""
    m = _ISQ_154D.match(_collapse(turn))
    if not m:
        return None
    body = m.group(1).strip()
    if not body or _ORAND_154D.search(body):
        return None
    parts = _POSS_154D.split(body)
    if len(parts) != 2:  # exactly one "'s": no of-forms, no two-hop
        return None
    left, right = parts[0].strip(), parts[1].strip()
    if not left or not right:
        return None
    lt, rt = left.split(), right.split()
    if len(lt) == 2 and len(rt) >= 1:
        # "Is V X's R?"
        v, x, rel = lt[0], lt[1], " ".join(rt)
    elif len(lt) == 1 and len(rt) >= 2:
        # "Is X's R V?" (V is one trailing token by sealed rule)
        x, rel, v = lt[0], " ".join(rt[:-1]), rt[-1]
    else:
        return None
    if not _NAME_154D.match(v) or not _NAME_154D.match(x):
        return None  # lowercase / multi-word names fall through
    if not _REL_154D.match(rel):
        return None
    key = relation_key154d(rel)
    if not key:
        return None
    return {"v": v, "x": x, "rel": rel, "key": key,
            "owner": f"{x}'s {rel}"}


def ground_yesno154d(nb, parsed: dict) -> str | None:
    """Notebook lookup for a parsed frame -> reply text | None (no write)."""
    try:
        resolved = nb.resolve(parsed["x"])
    except Exception:
        return None
    if resolved is None or getattr(resolved, "status", None) != C.OK:
        return None  # unknown / ambiguous subject: base reply unchanged
    try:
        eid = (resolved.detail or {}).get("entity_id")
        rows = nb.current(eid, parsed["key"])
    except Exception:
        return None
    if not rows:
        return None  # relation not stored: base reply unchanged
    displays = [show_value154d(nb, r.get("value")) for r in rows]
    want = norm_value154d(parsed["v"])
    if any(norm_value154d(d) == want for d in displays):
        return f"Yes, {parsed['owner']} is {parsed['v']}."
    shown = join_and154d(displays)
    if parsed["key"] in SINGLE_VALUED_154:
        return f"No, {parsed['owner']} is {shown}."
    return f"Not that I know of. I have {shown} as {parsed['owner']}."


def is_miss154d(actions) -> bool:
    """True iff the forward path did not understand (single clarify)."""
    return (isinstance(actions, list) and len(actions) == 1
            and isinstance(actions[0], dict)
            and actions[0].get("act") == "clarify"
            and DIDNT_UNDERSTAND_154D in str(actions[0].get("text", "")))


class YesNo154dMixin:
    """Stackable loop-level mixin: grounded yes/no only on the miss.

    Cooperative (super() first on every other turn): _listening_tick peeks
    at the inbox head through the unchanged ears hear; non-miss turns,
    non-yes/no shapes and ungrounded frames delegate byte-identical to
    super(). Grounded frames answer from notebook reads only (resolve +
    current); the final record is a clarify rendered verbatim by the
    mouth. Counters, last_records, experience and the event shape match
    the parent exactly. This path provably never writes.
    """

    def _listening_tick(self):  # type: ignore[no-redef]
        text = self.inbox[0] if getattr(self, "inbox", None) else None
        if text is not None:
            try:
                base = self.ears.hear(text)  # type: ignore[attr-defined]
            except Exception:
                base = None
            if base is not None and is_miss154d(base):
                parsed = parse_yesno154d(text)
                if parsed is not None:
                    try:
                        reply = ground_yesno154d(
                            self.nb, parsed)  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001 -- never raise
                        reply = None
                    if reply is not None:
                        return self._answer_yesno(text, reply)
        return super()._listening_tick()  # type: ignore[misc]

    def _answer_yesno(self, text: str, reply: str) -> dict:
        self.inbox.pop(0)  # type: ignore[attr-defined]
        self.counters["turns"] += 1  # type: ignore[attr-defined]
        self.counters["clarifications"] += 1  # type: ignore[attr-defined]
        try:
            stage = str(getattr(self.ears,  # type: ignore[attr-defined]
                                "last_stage", ""))
        except Exception:  # noqa: BLE001 -- stage tag is cosmetic only
            stage = ""
        try:
            self.ears.last_stage = (  # type: ignore[attr-defined]
                f"loop154d-yesno+{stage}")
        except Exception:  # noqa: BLE001 -- stage tag is cosmetic only
            pass
        record = {"kind": "clarify", "text": reply}
        self.last_records = [record]  # type: ignore[attr-defined]
        said = [line for line in
                (self.mouth.say(record)  # type: ignore[attr-defined]
                 for record in [record]) if line]
        self.experience.append(  # type: ignore[attr-defined]
            {"tick": self.tick, "kind": "turn", "text": text,  # type: ignore[attr-defined]
             "statuses": [r.get("status", r["kind"]) for r in [record]]})
        return self._event(A.LISTENING,  # type: ignore[attr-defined]
                           {"turn": text, "records": [record]}, said)
