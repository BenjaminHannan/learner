#!/usr/bin/env python3
"""lis-313b -- lis-313 plus one fix found on the month-end DEV bank (2026-09-24): the wrapper
answers only when the question word fits the relation it looked up. "Where does my sister live?"
misread as ask(me, sister) was answered "Your sister is Tuva." (true, but not what was asked).
Now a where-question needs a place relation, a when-question a date relation, and a who-question
a person relation; otherwise the rule reply is kept (decision "type-mismatch-keep-rule").

lis-313 -- answer-agreement for questions, on top of the lis-310 listener.

313 = install_turn310 (scripts/claude_lis310_agent.py, read-only import)
      + ONE outermost wrapper, turn313.

Why: turn310 throws away the reader's reading of a question (act ASK) and
hands the turn to the old rule chain. When the rule chain cannot parse the
question it abstains ("I don't know ..."), even when the notebook holds the
answer the reader pointed at. turn313 looks the reader's question up in the
notebook itself and uses that answer ONLY when the rule chain gave no answer.

Per user turn:
  1. The reader is called once. turn313 calls reader.read(turn, prev) itself
     (prev = loop.lis310_prev, exactly what turn310 uses), caches the result
     and turn310 is installed with a proxy whose .read returns that cached
     result. (When turn310 has a pending ask-back and the turn is a plain
     yes/no, turn310 never reads; turn313 then does not read either.)
  2. act ASK, ask is a dict, inverse false: lookup
       subject   = "USER" if owner == "me" else owner as typed
                   (then the capitalised form if the exact one misses)
       relations = [via, rel] if via else [rel]
     through fable_reasoner50.contract_answer (Notebook.ask; read-only).
     The inner turn310 runs as usual and gives the rule reply R. Then:
       lookup found V, R contains V          -> keep R            (agree)
       lookup found V, R is abstain/clarify  -> plain sentence    (reader_answered)
            "Your sister is Mira." / "Mira's dog is Pip."
            yes/no ask: "Yes, <sentence>" if V == asked value
            (case-insensitive), else "No, <sentence>"
       lookup found V, R names something else -> keep R           (disagree)
       lookup found nothing                   -> keep R           (reader_miss)
     The wrapper's own logic never writes: the notebook event count is
     asserted unchanged across the lookup and the reply choice.
  3. Inverse asks ("Whose dog is Pip?") and CHECK turns keep R (counters only).

Counters: loop.lis313_stats {asks, agree, reader_answered, disagree,
reader_miss, inverse_skipped, check_seen, inner_wrote}. Each ASK/CHECK
decision is appended to lis313_log.jsonl in the same folder as turn310's log.

New file only; no existing file is edited.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_lis310_agent as L310  # noqa: E402 (read-only)
import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_reasoner50 as R50  # noqa: E402 (contract_answer, read-only)

LOG_NAME313 = "lis313_log.jsonl"
USER_SUBJECT313 = L310.USER_SUBJECT310  # "USER"

# Copied from scripts/claude_convf0_score.py (builder-outbox): CLARIFY_MARKERS
# and ABSTAIN_EXTRA, lowercase substrings. A rule reply containing any of
# them counts as an abstain/clarify line.
CLARIFY_MARKERS313 = (
    "didn't understand",
    "don't know that shape",
    "well enough to save",
    "don't know that yet",
    "do not know that from what you taught me",
    "couldn't save that as a fact",
    "couldn't read that message",
    "please say it like",
    "do not understand that question",
)
ABSTAIN_EXTRA313 = (
    "don't know",
    "do not know",
    "haven't told me",
    "no record",
    "will not guess",
    "won't guess",
)
# turn310's own no-answer lines (claude_lis310_agent.py). They name no value,
# so on an ASK turn they are treated like an abstain as well.
NO_ANSWER_LINES313 = (L310.NOT_PLAIN310, L310.UNPARSED310)


def is_abstain313(reply: str) -> bool:
    text = str(reply or "").strip()
    if not text:
        return True
    low = text.lower()
    if any(m in low for m in CLARIFY_MARKERS313):
        return True
    if any(m in low for m in ABSTAIN_EXTRA313):
        return True
    return text in NO_ANSWER_LINES313


class CachedReaderProxy313:
    """What turn310 sees as its reader: .read returns turn313's cached read.

    If nothing is cached (should not happen) it falls through to the real
    reader so turn310 still works; that call is counted in fallback_reads.
    """

    def __init__(self, reader):
        self.reader = reader
        self.cached = None
        self.fallback_reads = 0

    def read(self, turn, prev_reply=""):
        if self.cached is not None:
            out, self.cached = self.cached, None
            return out
        self.fallback_reads += 1
        return self.reader.read(turn, prev_reply)


def _rel_words(rel: str) -> str:
    return str(rel or "").replace("_", " ").strip()


def _lookup313(nb, ask: dict) -> dict:
    """Read-only notebook lookup for a non-inverse ask. Returns
    {subject, relations, status, value (str|None), values (list)}."""
    owner = str(ask.get("owner") or "")
    rel = str(ask.get("rel") or "")
    via = ask.get("via")
    relations = [str(via), rel] if via else [rel]
    tried = []
    if owner == "me":
        tried.append(USER_SUBJECT313)
    else:
        tried.append(owner)
        cap = owner[:1].upper() + owner[1:]
        if cap != owner:
            tried.append(cap)
    res = None
    subject = tried[0]
    for name in tried:
        if not name or not rel:
            break
        subject = name
        try:
            res = R50.contract_answer({"name": name, "relations": relations},
                                      nb)
        except Exception as exc:  # noqa: BLE001 -- a broken lookup is a miss
            res = {"status": "ERROR", "fields": {"error": repr(exc)}}
        if res.get("status") == C.OK:
            break
    status = (res or {}).get("status", "NO_LOOKUP")
    value = None
    values: list = []
    if status == C.OK:
        ans = (res.get("fields") or {}).get("answer")
        if ans is not None and str(ans).strip():
            value = str(ans)
            if (res.get("fields") or {}).get("multi"):
                values = [v.strip() for v in value.split(",") if v.strip()]
            else:
                values = [value]
    return {"subject": subject, "relations": relations, "status": status,
            "value": value, "values": values}


def _sentence313(ask: dict, value: str) -> str:
    owner = str(ask.get("owner") or "")
    head = "Your" if owner == "me" else "%s's" % owner
    rels = [ask.get("via"), ask.get("rel")] if ask.get("via") else [
        ask.get("rel")]
    path = "'s ".join(_rel_words(r) for r in rels)
    return "%s %s is %s." % (head, path, value)


def _answer313(ask: dict, values: list, value: str) -> str:
    sent = _sentence313(ask, value)
    if "value" in ask and ask.get("value") is not None:
        asked = str(ask.get("value")).strip().lower()
        yes = any(asked == str(v).strip().lower() for v in values)
        body = "your" + sent[4:] if sent.startswith("Your ") else sent
        return ("Yes, " if yes else "No, ") + body
    return sent


PLACE_RELS313 = {"city", "home", "hometown", "place_of_birth", "place_of_death", "country",
                 "country_of_citizenship", "country_of_origin", "capital", "continent",
                 "headquarters_location", "location_of_formation", "work_location", "school",
                 "educated_at", "employer"}
DATE_RELS313 = {"birthday", "anniversary", "date_of_birth", "date_of_death", "age"}
QWORD313 = re.compile(r"\b(where|when|who|whom|whose)\b", re.I)


def type_ok313(turn: str, ask: dict) -> bool:
    """False when the question word clearly needs another kind of relation."""
    m = QWORD313.search(str(turn or ""))
    if not m:
        return True
    rel = str(ask.get("rel") or "")
    w = m.group(1).lower()
    if w == "where":
        return rel in PLACE_RELS313
    if w == "when":
        return rel in DATE_RELS313
    return rel in A.PERSON_RELATIONS or rel not in PLACE_RELS313 | DATE_RELS313


def _log313(loop, row: dict) -> None:
    try:
        with open(loop.lis313_log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def install_turn313(loop, reader, threshold: float = L310.DEFAULT_THRESHOLD310,
                    log_path=None, log_path310=None):
    """Install turn310 (with a caching reader proxy) and turn313 outside it.

    log_path310: turn310's own log path (default: its default); log_path:
    this wrapper's log (default: lis313_log.jsonl in turn310's log folder).
    """
    proxy = CachedReaderProxy313(reader)
    L310.install_turn310(loop, proxy, threshold=threshold,
                         log_path=log_path310)
    if getattr(vars(loop).get("turn"), "__name__", "") != "turn310":
        raise RuntimeError("313: turn310 not installed")
    inner = loop.turn
    loop.turn313_inner = inner
    loop.lis313_reader = reader
    loop.lis313_proxy = proxy
    loop.lis313_log_path = str(
        log_path or (Path(loop.lis310_log_path).parent / LOG_NAME313))
    loop.lis313_stats = {"turns": 0, "reads": 0, "asks": 0, "agree": 0,
                         "reader_answered": 0, "disagree": 0,
                         "reader_miss": 0, "inverse_skipped": 0,
                         "check_seen": 0, "inner_wrote": 0}
    st = loop.lis313_stats

    def turn313(text: str):  # type: ignore[no-untyped-def]
        t = str(text)
        st["turns"] += 1
        prev = loop.lis310_prev or ""
        # turn310 answers a pending ask-back yes/no without reading.
        if (loop.lis310_pending is not None
                and L310._norm_yesno(t) in (L310.YES310 | L310.NO310)):
            proxy.cached = None
            return inner(t)
        read = reader.read(t, prev)
        st["reads"] += 1
        proxy.cached = read
        frame = read[0] if isinstance(read, (tuple, list)) and read else None
        act = frame.get("act") if isinstance(frame, dict) else None
        ask = frame.get("ask") if isinstance(frame, dict) else None
        if act == "CHECK":
            st["check_seen"] += 1
            reply = inner(t)
            _log313(loop, {"turn": t, "frame": frame, "act": act,
                           "lookup": None, "decision": "check-keep-rule",
                           "reply": reply})
            return reply
        if act != "ASK" or not isinstance(ask, dict):
            return inner(t)
        st["asks"] += 1
        if ask.get("inverse"):
            st["inverse_skipped"] += 1
            reply = inner(t)
            _log313(loop, {"turn": t, "frame": frame, "act": act,
                           "lookup": None, "decision": "inverse-keep-rule",
                           "reply": reply})
            return reply
        ev0 = len(loop.nb.events)
        look = _lookup313(loop.nb, ask)
        assert len(loop.nb.events) == ev0, "313: lookup wrote to the notebook"
        ev_inner0 = len(loop.nb.events)
        rule = inner(t)
        inner_delta = len(loop.nb.events) - ev_inner0
        if not isinstance(rule, list):
            rule = [str(rule)]
        rule_text = " ".join(str(x) for x in rule if x)
        ev1 = len(loop.nb.events)
        reply = rule
        if inner_delta:
            st["inner_wrote"] += 1
            decision = "inner-wrote-keep-rule"
        elif look["value"] is None:
            st["reader_miss"] += 1
            decision = "miss-keep-rule"
        elif all(v in rule_text for v in look["values"]):
            st["agree"] += 1
            decision = "agree"
        elif is_abstain313(rule_text) and not type_ok313(t, ask):
            st["type_mismatch"] = st.get("type_mismatch", 0) + 1
            decision = "type-mismatch-keep-rule"
        elif is_abstain313(rule_text):
            st["reader_answered"] += 1
            decision = "reader-answered"
            reply = [_answer313(ask, look["values"], look["value"])]
            loop.lis310_prev = " ".join(reply)
        else:
            st["disagree"] += 1
            decision = "disagree-keep-rule"
        assert len(loop.nb.events) == ev1, "313: wrapper wrote to the notebook"
        _log313(loop, {"turn": t, "frame": frame, "act": act,
                       "lookup": look, "decision": decision,
                       "rule_reply": rule, "reply": reply,
                       "inner_events": inner_delta})
        return reply

    turn313.__name__ = "turn313"
    loop.turn = turn313
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("lis313" in n for n in notes):
        notes.append("lis313: turn310 + answer-agreement (reader's ASK "
                     "looked up read-only; used only when the rule chain "
                     "abstains)")
    return loop
