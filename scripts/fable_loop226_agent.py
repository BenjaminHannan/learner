#!/usr/bin/env python3
"""Experiment 226 -- THE ONE CHANGE: source questions about the last reply.

loop226 = loop138i + one outer layer (this file only; no existing file
edited, nothing new stored in the notebook).

(1) After every non-source turn the loop records WHICH notebook facts its
    reply stated or used, read from what the pipeline actually did:
      SAVED      a write record with wrote=True and >= 1 new active taught
                 fact appended during this turn (the fact ids come from
                 the notebook diff before/after the turn);
      ANSWER     exactly one OK answer record from the ask path; the fact
                 ids are the reasoner's own ``trail`` (the notebook path it
                 followed), accepted only when the trail is consistent with
                 the record (hop count, relations, final value / multi
                 values) -- otherwise UNTRACED;
      namecheck  the reasoner record captured inside _answer_namecheck;
      yes/no     the 154d stage produced the reply (confirmed by re-running
                 its pure ground function on the same notebook and matching
                 the reply exactly): the nb.current rows it read;
      BACKWARDS  the 153 reverse stage produced the reply (confirmed the
                 same way) with >= 1 subject: the live taught rows 153's
                 reverse_subjects scanned (never stored; computed at
                 answer time);
      NOFACT     the base DECLINE route, an answer record with an empty
                 trail, a forget write, or any other path whose reply
                 mentions no stored entity name and no stored value;
      UNTRACED   anything else (the reply might state notebook content
                 but the pipeline left no trace this layer can read).
    The record lives in memory only (a restart clears it).

(2) A source question -- one of the sealed normalised templates in
    SOURCE_TEMPLATES226, matched exactly after normalisation, never by
    keywords -- is intercepted at the start of the listening tick (before
    the ears, so it can never write) and answered from the recorded facts'
    stored source / provenance. The record is left unchanged, so asking
    twice gives the same answer.

Everything else runs the 138i code path byte-identically.
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
import fable_loop138i_agent as L138I  # noqa: E402 (base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (_display, read-only)
import fable_fix153_reverse as R153  # noqa: E402 (reverse parse, read-only)
import fable_fix154d_yesno as Y154D  # noqa: E402 (yes/no parse, read-only)
import fable_fix166_me as M166  # noqa: E402 (USER key, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_self105 as S105  # noqa: E402 (intent sets, read-only)

# ----------------------------------------------------------- sealed templates
SOURCE_TEMPLATES226 = frozenset({
    "who told you that",
    "who told you",
    "who taught you that",
    "how do you know that",
    "how do you know",
    "how do you know this",
    "how did you know that",
    "how did you learn that",
    "where did you learn that",
    "where did you get that",
    "where did you get that from",
    "where did you hear that",
    "where did that come from",
    "who said that",
    "what's your source",
    "what is your source",
    "what's your source for that",
    "what is your source for that",
    "says who",
})

NO_THAT226 = ("I'm not sure what \"that\" means — I haven't just told "
              "you a fact.")
UNTRACED226 = ("I can't say where that came from — I didn't keep track "
               "of which notes that reply used, so I won't guess.")


def normalise226(text: object) -> str:
    t = str(text).replace("’", "'").replace("‘", "'")
    t = " ".join(t.split()).lower()
    t = re.sub(r"[\s?.!]+$", "", t)
    return t.strip()


def is_source_question226(text: object) -> bool:
    return normalise226(text) in SOURCE_TEMPLATES226


# ------------------------------------------------------------ fact rendering
def _name226(nb, eid: str) -> str:
    return str(nb.entities.get(eid, eid))


def fact_sentence226(nb, fid: str) -> str:
    fact = nb.facts[fid]
    subj = _name226(nb, fact["subject"])
    rel = str(fact["relation"]).replace("_", " ")
    value = fact.get("value") or {}
    if "entity" in value and value["entity"] in nb.entities and \
            _name226(nb, value["entity"]) == M166.USER_KEY:
        val = "you"
    else:
        val = L90._display(nb, value)
    if subj == M166.USER_KEY:
        return f"your {rel} is {val}"
    return f"{subj}'s {rel} is {val}"


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _sentences226(nb, fids: list[str]) -> str:
    parts = [fact_sentence226(nb, f) for f in fids]
    out = [parts[0] + "."] + [_cap(p) + "." for p in parts[1:]]
    return " ".join(out)


def _taught(nb, fid: str) -> bool:
    f = nb.facts.get(fid) or {}
    return f.get("source") == "taught" and f.get("actor") == "listening"


def _provenance_note226(nb, fid: str) -> str | None:
    """Stored provenance of a non-taught fact, or None if none is held."""
    f = nb.facts.get(fid) or {}
    prov = f.get("provenance") or {}
    src = f.get("source")
    urls: list[str] = []
    if isinstance(prov, dict):
        if prov.get("url"):
            urls.append(str(prov["url"]))
        for ev in prov.get("evidence") or []:
            if isinstance(ev, dict) and ev.get("url"):
                urls.append(str(ev["url"]))
    sent = _cap(fact_sentence226(nb, fid))
    if src in ("web-verified", "web-quarantine") and urls:
        return f"{sent} — I read that on the web ({', '.join(urls)})."
    if src == "sleep-derived":
        return (f"{sent} — my notebook marks this as worked out "
                f"during sleep, not told to me by you.")
    if src == "inferred" and f.get("deps"):
        deps = [d for d in f["deps"] if d in nb.facts]
        if deps and all(_taught(nb, d) for d in deps):
            return (f"{sent} — I inferred it from what you told me: "
                    f"{_sentences226(nb, deps)}")
    return None


def source_reply226(nb, state: dict | None) -> str:
    if not state or state.get("kind") == "NOFACT":
        return NO_THAT226
    kind = state.get("kind")
    fids = [f for f in state.get("fids", []) if f in nb.facts]
    if kind == "UNTRACED" or not fids or len(fids) != len(state.get("fids", [])):
        return UNTRACED226
    if not all(_taught(nb, f) for f in fids):
        notes = []
        for f in fids:
            if _taught(nb, f):
                notes.append(f"{_cap(fact_sentence226(nb, f))} — you "
                             f"told me that.")
            else:
                n = _provenance_note226(nb, f)
                if n is None:
                    return UNTRACED226
                notes.append(n)
        return " ".join(notes)
    body = _sentences226(nb, fids)
    if kind == "SAVED":
        joined = " and ".join(fact_sentence226(nb, f) for f in fids)
        return f"You did — you just told me {joined}."
    if kind == "BACKWARDS":
        return ("Nobody told me directly; I worked it out backwards from "
                f"what you told me: {body}")
    if kind == "ANSWER":
        if len(fids) == 1 or state.get("multi"):
            return f"You told me: {body}"
        return f"I put together things you told me: {body}"
    return UNTRACED226


# ------------------------------------------------------- what the turn used
def _norm_val(s: object) -> str:
    return " ".join(str(s).split()).rstrip(".").lower()


def _answer_state226(nb, rec: dict) -> dict:
    fields = rec.get("fields") or {}
    trail = list(fields.get("trail") or [])
    rels = list(rec.get("relations") or [])
    if not trail or any(f not in nb.facts for f in trail):
        return {"kind": "UNTRACED"}
    if any(k.startswith("screen") for k in fields):
        return {"kind": "UNTRACED"}
    answer = fields.get("answer")
    if fields.get("multi"):
        if len(rels) != 1:
            return {"kind": "UNTRACED"}
        if any(nb.facts[f]["relation"] != rels[0] for f in trail):
            return {"kind": "UNTRACED"}
        low = _norm_val(answer)
        vals = [_norm_val(L90._display(nb, nb.facts[f]["value"]))
                for f in trail]
        if not vals or any(v not in low for v in vals):
            return {"kind": "UNTRACED"}
        # the answer must list exactly these values (count of " and "/",")
        n_listed = len(re.split(r",\s*|\s+and\s+", low))
        if n_listed != len(vals):
            return {"kind": "UNTRACED"}
        order = sorted(range(len(trail)), key=lambda i: low.find(vals[i]))
        return {"kind": "ANSWER", "fids": [trail[i] for i in order],
                "multi": True}
    if len(trail) != len(rels):
        return {"kind": "UNTRACED"}
    for f, r in zip(trail, rels):
        if nb.facts[f]["relation"] != r:
            return {"kind": "UNTRACED"}
    for a, b in zip(trail, trail[1:]):  # chain links: value of a = subject of b
        if (nb.facts[a].get("value") or {}).get("entity") != \
                nb.facts[b]["subject"]:
            return {"kind": "UNTRACED"}
    last = L90._display(nb, nb.facts[trail[-1]]["value"])
    if answer is None or _norm_val(last) != _norm_val(answer):
        return {"kind": "UNTRACED"}
    return {"kind": "ANSWER", "fids": trail}


def _mentions_notebook226(nb, reply: str) -> bool:
    low = f" {reply.lower()} "
    names = set(str(n) for n in nb.entities.values())
    for f in nb.facts.values():
        names.add(L90._display(nb, f.get("value") or {}))
    for n in names:
        n = str(n).strip()
        if not n:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(n.lower())
                     + r"(?![a-z0-9])", low):
            return True
    return False


class Source226Mixin:
    """Outermost loop layer: record the last reply's facts; answer source
    questions from them without touching the ears or the notebook."""

    _src226_state: dict | None = None
    _src226_hit: bool = False
    _src226_namecheck: dict | None = None

    # (2) interception, before every other tick layer (no ears, no write)
    def _listening_tick(self):  # type: ignore[no-untyped-def]
        text = self.inbox[0] if getattr(self, "inbox", None) else None
        if text is not None and is_source_question226(text):
            self.inbox.pop(0)
            self.counters["turns"] += 1
            self.counters["clarifications"] += 1
            reply = source_reply226(self.nb, self._src226_state)
            record = {"kind": "clarify", "text": reply}
            self.last_records = [record]
            self.experience.append(
                {"tick": self.tick, "kind": "turn", "text": text,
                 "statuses": ["clarify"]})
            self._src226_hit = True
            return self._event(A.LISTENING,
                               {"turn": text, "records": [record]}, [reply])
        return super()._listening_tick()  # type: ignore[misc]

    def _answer_namecheck(self, action: dict) -> dict:  # type: ignore[no-untyped-def]
        captured: list = []
        reasoner = self.reasoner
        had = "answer" in vars(reasoner)
        orig = reasoner.answer

        def _cap_answer(q, nb):
            r = orig(q, nb)
            captured.append(r)
            return r

        reasoner.answer = _cap_answer
        try:
            out = super()._answer_namecheck(action)  # type: ignore[misc]
        finally:
            if had:
                reasoner.answer = orig
            else:
                del reasoner.answer
        if (isinstance(out, dict) and out.get("kind") == "note"
                and len(captured) == 1 and isinstance(captured[0], dict)
                and captured[0].get("status") == C.OK):
            self._src226_namecheck = captured[0]
        return out

    # (1) what the last reply stated or used
    def turn(self, text: str) -> list[str]:
        nb = self.nb
        before = set(nb.facts)
        n_log = len(getattr(self, "self_turn_log", []))
        self._src226_hit = False
        self._src226_namecheck = None
        said = super().turn(text)  # type: ignore[misc]
        if self._src226_hit:
            return said
        try:
            self._src226_state = self._classify226(text, said, before, n_log)
        except Exception:  # noqa: BLE001 -- never break the base reply
            self._src226_state = {"kind": "UNTRACED"}
        return said

    def _classify226(self, text: str, said: list[str], before: set,
                     n_log: int) -> dict:
        nb = self.nb
        reply = " ".join(said)
        records = list(getattr(self, "last_records", []) or [])
        log = getattr(self, "self_turn_log", [])
        routed = getattr(self, "last_routed", None)
        new = [f for f in nb.facts if f not in before]
        if routed:
            intent = routed.get("intent")
            if intent == "DECLINE":
                return {"kind": "NOFACT"}
            if (intent in S105.PROCESS_INTENTS
                    and not _mentions_notebook226(nb, reply)):
                return {"kind": "NOFACT"}
            return {"kind": "UNTRACED"}
        # SAVED
        writes = [r for r in records if r.get("kind") == "write"]
        if writes and all(r.get("wrote") for r in writes):
            if all(str(r.get("line", "")).startswith("forget")
                   for r in writes) and not new:
                return {"kind": "NOFACT"}
            saved = [f for f in new if nb.active(f) and _taught(nb, f)]
            if saved and len(saved) == len(new) and len(records) == len(writes):
                return {"kind": "SAVED", "fids": saved}
            return {"kind": "UNTRACED"}
        if new:
            return {"kind": "UNTRACED"}
        # namecheck (note) -- captured reasoner record
        if self._src226_namecheck is not None and len(records) == 1 and \
                records[0].get("kind") == "note":
            return _answer_state226(nb, self._src226_namecheck)
        # ask path
        answers = [r for r in records if r.get("kind") == "answer"]
        if answers and len(answers) == len(records):
            if len(answers) != 1:
                return {"kind": "UNTRACED"}
            rec = answers[0]
            if rec.get("status") == C.OK:
                return _answer_state226(nb, rec)
            trail = (rec.get("fields") or {}).get("trail")
            if trail == [] and rec.get("status") in (
                    C.MISSING_FACT, C.UNKNOWN_ENTITY):
                return {"kind": "NOFACT"}
            return {"kind": "UNTRACED"}
        # 153 reverse stage (answered at ask time, never stored)
        # (the ears' last_stage tag can be stale -- 154d sets it on the
        # outer ears wrapper -- so each stage is confirmed by re-running its
        # own pure function on the same notebook and matching the reply)
        parsed = R153.parse_reverse(text)
        if parsed is not None and records and all(
                r.get("kind") == "clarify" for r in records):
            rel_surface, value = parsed
            rel_key = A.FakeEars._relation(rel_surface)
            subjects = R153.reverse_subjects(nb, rel_key, value)
            if reply != R153.answer_reverse(rel_surface, value, subjects):
                return self._fallback226(nb, reply)
            if not subjects:
                return {"kind": "NOFACT"}
            want = " ".join(value.split()).rstrip(".")
            fids = []
            for subj in subjects:
                hit = [fid for fid, f in nb.facts.items()
                       if f.get("source") == "taught" and nb.active(fid)
                       and f["relation"] == rel_key
                       and _name226(nb, f["subject"]) == subj
                       and " ".join(L90._display(nb, f["value"]).split()
                                    ).rstrip(".") == want]
                if not hit:
                    return {"kind": "UNTRACED"}
                fids.append(hit[0])
            return {"kind": "BACKWARDS", "fids": fids}
        # 154d grounded yes/no
        parsed = Y154D.parse_yesno154d(text)
        if parsed is not None and records and all(
                r.get("kind") == "clarify" for r in records):
            if reply != Y154D.ground_yesno154d(nb, parsed):
                return self._fallback226(nb, reply)
            resolved = nb.resolve(parsed["x"])
            if getattr(resolved, "status", None) != C.OK:
                return {"kind": "UNTRACED"}
            rows = nb.current(resolved.detail["entity_id"], parsed["key"])
            fids = [r["fact_id"] for r in rows]
            if not fids:
                return {"kind": "UNTRACED"}
            return {"kind": "ANSWER", "fids": fids, "multi": len(fids) > 1}
        return self._fallback226(nb, reply)

    @staticmethod
    def _fallback226(nb, reply: str) -> dict:
        if not _mentions_notebook226(nb, reply):
            return {"kind": "NOFACT"}
        return {"kind": "UNTRACED"}


class Loop226AgentLoop(Source226Mixin, L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + the Source226 outer layer."""


DEFAULT_CONFIG226: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG226["daemon"]["module"] = "Loop226Daemon (this file)"
DEFAULT_CONFIG226["source226"] = (
    "Source226Mixin: last-reply fact record from the pipeline (write diff, "
    "reasoner trail, 153/154d stage re-reads); sealed source templates "
    "answered from stored source/provenance; never writes")


_BUILD138I = L138I.build_agent138i  # the original builder, bound at import


def build_agent226(cfg: dict | None = None) -> Loop226AgentLoop:
    """build_agent138i with the loop class swapped for Loop226AgentLoop."""
    orig = L138I.Loop138iAgentLoop
    L138I.Loop138iAgentLoop = Loop226AgentLoop  # type: ignore[misc]
    try:
        loop = _BUILD138I(cfg)
    finally:
        L138I.Loop138iAgentLoop = orig  # type: ignore[misc]
    assert isinstance(loop, Loop226AgentLoop)
    loop.notes.append("loop226: loop138i + source questions about the "
                      "last reply (Source226Mixin)")
    return loop


class Loop226Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 226 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None, **kw) -> None:
        orig = _BUILD138I
        L138I.build_agent138i = build_agent226  # type: ignore[assignment]
        try:
            super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                             sleep_threshold=sleep_threshold, **kw)
        finally:
            L138I.build_agent138i = orig  # type: ignore[assignment]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 226 source questions")
    parser.add_argument("--config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG226)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or args.dir:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return Loop226Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
