#!/usr/bin/env python3
"""Exp 310 -- plug the lis-300 listener into the chat agent (291 base).

310 = 291 (scripts/claude_loop291_agent.py: build_agent291 + DEFAULT_CONFIG291
     + Loop291Daemon, builder-outbox, read-only) + the listener turn wrapper.

The listener is the fine-tuned MiniCPM5-1B from lis-300:
  scripts/claude_lis300_read.py: Reader(model_dir).read(turn, prev_reply)
    -> (frame, confs, raw, ms)
  scripts/claude_lis300_compiler.py: compile_frame(frame, turn, prev,
    conf, threshold) -> {write, ask_whose, ask_back, held, question, act}
The frame format is design/v3/60-listener/frame-spec.md.

Behaviour on each user turn (turn310, installed OUTSIDE turn291, so the 291
chain is untouched and every class/file stays frozen):
  1. Reader reads the turn with prev_reply = the assistant's previous reply.
     Compiled with cfg threshold (lis-300 THRESHOLD.txt; default 0.99 -- no
     THRESHOLD.txt exists on origin/main as of 2026-09-23, so 0.99 stands).
  2. `write` non-empty: save exactly those facts through the notebook's
     normal teach/correct doorway, i.e. the same loop._act(structured ...)
     path structured teaches take in
     fable_loop90_agent.Loop90AgentLoop._act. Owner "me" is stored as the
     subject "USER" -- exactly how the base stores "my" facts (probed:
     build_agent291 turn "My sister is Mira." stores triple
     ('USER','sister','Mira') and says "Saved: your sister is Mira.").
     Before the doorway, each fact passes the base's own screens: 209's
     screen_action209 (named/called strip, empty-value, date-literal) and
     252b's value_ok252b value screen. Any screen rejection blocks the whole
     turn (nothing saved). Reply = the base mouth's normal save confirmation
     (mouth.say on each write record, joined).
  3. `ask_whose` non-empty: save nothing. Reply
     "Whose <rel> is <value>, yours or someone else's?" (first fact).
  4. `ask_back` non-empty: save nothing. Reply
     "Just to check: is <owner>'s <rel> <value>?" ("your" for me). A plain
     "yes" (yes/yes. only) on the next turn saves exactly that (first) fact
     through the step-2 doorway; any other answer drops it ("no" replies
     "Okay, I won't save that.").
  5. act NEGATE/SUPPOSE/PLAN, or every fact held (REPORTED, UNCLEAR, CHECK
     modes): nothing is saved by anyone. The turn goes to the base with
     TEACH/CORRECT writes blocked (loop._act wrapper). Base reply is used
     when the base attempted no write; otherwise
     "Okay, I won't save that since it isn't a plain fact."
     CHAT acts take the same blocked-base path.
  6. act ASK/CHECK: same blocked-base pass (the base's question chain:
     n-hop, reverse, yes/no), TEACH/CORRECT writes blocked on that turn.
  7. Unparsed reader output: save nothing, reply
     "Sorry, I didn't catch that. Could you say it another way?"

RULE: while lis-310 is on, the base's rule chain NEVER writes. Every write
comes from step 2 or the step-4 "yes". The blocked-base pass wraps loop._act
and swallows teach/correct actions (returned as silent note records).

Every turn is appended to <state_dir>/lis310_log.jsonl with the reader frame,
confs, decision, blocked count and ms.

New file only; no existing file is edited. Subclass/wrap like 291 wraps 260.

CPU build. Unit tests use a StubReader (no weights). The real weights come
later from lis-300: pass cfg lis310.model_dir (or a Reader as
lis310.reader); Loop310Daemon reads both from its cfg.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop291_agent as B291  # noqa: E402 (base, read-only)
import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)
import fable_loop209_agent as W209  # noqa: E402 (209 screen, read-only)
import fable_loop166_agent as L166  # noqa: E402 (me render, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import claude_fix252_correct as F252  # noqa: E402 (252b screen fn, read-only)

# ---------------------------------------------------------------- constants

DEFAULT_THRESHOLD310 = 0.99  # lis-300 THRESHOLD.txt default until published
USER_SUBJECT310 = "USER"  # how the base stores "my" facts (see docstring)
LOG_NAME310 = "lis310_log.jsonl"

WHOSE_FMT310 = "Whose {rel} is {value}, yours or someone else's?"
ASKBACK_FMT310 = "Just to check: is {owner} {rel} {value}?"
UNPARSED310 = "Sorry, I didn't catch that. Could you say it another way?"
NOT_PLAIN310 = "Okay, I won't save that since it isn't a plain fact."
DROPPED310 = "Okay, I won't save that."
BLOCKED_ACTS310 = ("teach", "correct")

YES310 = {"yes"}
NO310 = {"no"}


def _norm_yesno(text: str) -> str:
    return str(text or "").strip().lower().rstrip(".").strip()


def _owner_display310(owner: str) -> str:
    if str(owner) == "me":
        return "your"
    return "%s's" % owner


def _display310(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def _decide_teach_correct310(loop, name: str, rel: str, val: str,
                             is_person: bool) -> str:
    """Mirror Bench73Stage._teach_action: correct iff (subject, rel) already
    holds a different taught value, else teach."""
    nb = loop.nb
    try:
        found = nb.resolve(name)
        eid = found.detail.get("entity_id") if found.status == C.OK else None
    except Exception:  # noqa: BLE001 -- doorway decides; default to teach
        return "teach"
    if eid is None:
        return "teach"
    try:
        for fact in nb.facts.values():
            if (fact.get("subject") == eid and fact.get("relation") == rel
                    and fact.get("source") == "taught"
                    and nb.active(fact["fact_id"])):
                if _display310(nb, fact["value"]) != val:
                    return "correct"
                return "teach"
    except Exception:  # noqa: BLE001
        return "teach"
    return "teach"


def save_fact310(loop, owner: str, rel: str, val: str, turn: str = ""):
    """One listener fact through the notebook doorway.

    Returns (status, text): status "saved" (text = base mouth confirmation,
    with the base's own Me166 me-render so USER reads as your),
    "screen209" or "screen252b" (text None) when a base screen rejects it.
    Screens: 209 screen_action209, then 252b value_ok252 (installed screen).
    """
    name = USER_SUBJECT310 if str(owner) == "me" else str(owner)
    is_person = str(rel) in A.PERSON_RELATIONS
    act = _decide_teach_correct310(loop, name, str(rel), str(val), is_person)
    action = {"act": act, "name": name, "relation": str(rel),
              "value": str(val), "is_person": is_person, "structured": True}
    screened = W209.screen_action209(dict(action))
    if screened is not None and screened.get("act") == "clarify":
        return "screen209", None
    if screened is not None:
        action = screened
    try:
        ok = F252.value_ok252(action.get("value", ""))
    except Exception:  # noqa: BLE001 -- a broken screen must not save
        return "screen252b", None
    if not ok:
        return "screen252b", None
    rec = loop._act(action)
    try:
        text = loop.mouth.say(rec)
    except Exception:  # noqa: BLE001
        text = ""
    try:
        text = L166.rewrite_me166_reply(text or "", turn)
    except Exception:  # noqa: BLE001
        pass
    return "saved", (text or "")


def _save_all310(loop, facts: list[dict], turn: str = ""):
    """All-or-nothing doorway save of compiled write facts.

    Returns (wrote_list, reply_text, screen_hit): wrote_list of (s,r,v);
    on any screen rejection nothing is saved and screen_hit names it.
    """
    for f in facts:
        probe_owner = str(f.get("owner", ""))
        probe_name = USER_SUBJECT310 if probe_owner == "me" else probe_owner
        is_person = str(f.get("rel")) in A.PERSON_RELATIONS
        probe = {"act": "teach", "name": probe_name,
                 "relation": str(f.get("rel")), "value": str(f.get("value")),
                 "is_person": is_person, "structured": True}
        screened = W209.screen_action209(dict(probe))
        if screened is not None and screened.get("act") == "clarify":
            return [], "", "screen209"
        try:
            ok = F252.value_ok252(
                (screened or probe).get("value", ""))
        except Exception:  # noqa: BLE001
            return [], "", "screen252b"
        if not ok:
            return [], "", "screen252b"
    wrote, texts = [], []
    for f in facts:
        st, text = save_fact310(loop, str(f.get("owner", "")),
                                str(f.get("rel")), str(f.get("value")),
                                turn)
        if st != "saved":
            continue  # probe above passed; keep going
        wrote.append([str(f.get("owner", "")), str(f.get("rel")),
                      str(f.get("value"))])
        if text:
            texts.append(text)
    return wrote, " ".join(texts), None


def _log310(loop, row: dict) -> None:
    try:
        with open(loop.lis310_log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _would_write310(loop, action: dict) -> bool:
    """True if a teach/correct action would mutate the notebook.

    A teach/correct of the exact triple already actively taught is a no-op
    (the base answers "I already have that." with 0 events); it may run.
    Anything that would add, change or create (new subject, new relation,
    different value) is swallowed. Conservative: on any doubt, swallow.
    """
    try:
        name = str(action.get("name", ""))
        rel = str(action.get("relation", ""))
        val = str(action.get("value", ""))
        if not name or not rel:
            return True
        found = loop.nb.resolve(name)
        if found.status == C.AMBIGUOUS:
            return False  # doorway clarifies; no write
        if found.status != C.OK:
            return True  # unknown subject: doorway creates -> writes
        eid = found.detail.get("entity_id")
        for fact in loop.nb.facts.values():
            if (fact.get("subject") == eid and fact.get("relation") == rel
                    and fact.get("source") == "taught"
                    and loop.nb.active(fact["fact_id"])):
                return _display310(loop.nb, fact["value"]) != val
        return True  # new (subject, relation): doorway writes
    except Exception:  # noqa: BLE001
        return True


def _base_pass_blocked310(loop, text: str):
    """Run the base turn chain with TEACH/CORRECT writes blocked.

    Returns (reply_list, blocked_actions, events_delta). A teach/correct
    that would mutate the notebook is swallowed as a silent note record so
    the mouth says nothing for it; a no-op teach/correct (fact already
    stored) runs so the base's own "already have" reply survives.
    """
    blocked: list = []
    events0 = len(loop.nb.events)
    orig_act = loop._act

    def blocking_act(action, _a=orig_act):
        if isinstance(action, dict) and action.get("act") in BLOCKED_ACTS310:
            if _would_write310(loop, action):
                blocked.append(action)
                return {"kind": "note", "text": ""}
        return _a(action)

    loop._act = blocking_act
    try:
        reply = loop.turn310_inner(text)
    finally:
        loop._act = orig_act
    if not isinstance(reply, list):
        reply = [str(reply)]
    return reply, blocked, len(loop.nb.events) - events0


def _compile310(frame, turn: str, prev: str, confs, threshold: float) -> dict:
    import claude_lis300_compiler as CMP  # noqa: E402 (lis-300, read-only)

    return CMP.compile_frame(frame, turn, prev, confs, threshold)


def install_turn310(loop, reader, threshold: float = DEFAULT_THRESHOLD310,
                    log_path=None) -> None:
    """Install the outermost listener turn wrapper on a built 291 loop."""
    inner_turn = loop.turn
    loop.turn310_inner = inner_turn
    loop.lis310_reader = reader
    loop.lis310_threshold = float(threshold)
    loop.lis310_prev = ""
    loop.lis310_pending: dict | None = None
    try:
        state_dir = Path(loop.dir)
    except Exception:  # noqa: BLE001
        state_dir = Path(".")
    loop.lis310_log_path = str(log_path or (state_dir / LOG_NAME310))
    if not hasattr(loop, "lis310_stats"):
        loop.lis310_stats = {"turns": 0, "writes": 0, "blocked": 0}

    def turn310(text: str):  # type: ignore[no-untyped-def]
        t = str(text)
        prev = loop.lis310_prev or ""
        t0 = time.perf_counter()

        def finish(reply, row):
            if isinstance(reply, str):
                reply = [reply]
            loop.lis310_prev = " ".join(reply)
            row.update({"ms_total": round((time.perf_counter() - t0) * 1000, 1),
                        "reply": reply})
            _log310(loop, row)
            loop.lis310_stats["turns"] += 1
            return reply

        # -- pending ask-back: a plain yes/no answers it, anything else drops
        pend = loop.lis310_pending
        if pend is not None:
            yn = _norm_yesno(t)
            if yn in YES310:
                loop.lis310_pending = None
                fact = pend["fact"]
                wrote, say, _screen = _save_all310(loop, [fact], t)
                loop.lis310_stats["writes"] += len(wrote)
                return finish(say or NOT_PLAIN310,
                              {"turn": t, "prev": prev, "frame": None,
                               "confs": None, "decision": "pending-yes",
                               "wrote": wrote, "blocked": 0})
            if yn in NO310:
                loop.lis310_pending = None
                return finish(DROPPED310,
                              {"turn": t, "prev": prev, "frame": None,
                               "confs": None, "decision": "pending-no",
                               "wrote": [], "blocked": 0})
            loop.lis310_pending = None  # any other answer drops it, then
            # fall through and process this turn normally.
        # -- reader + compiler
        frame, confs, _raw, ms = reader.read(t, prev)
        try:
            conf_list = list(confs) if confs is not None else []
        except TypeError:
            conf_list = []
        dec = _compile310(frame, t, prev, conf_list,
                          loop.lis310_threshold)
        base_row = {"turn": t, "prev": prev, "frame": frame,
                    "confs": conf_list, "ms": round(ms, 1)}
        if not isinstance(frame, dict):
            return finish(UNPARSED310, dict(base_row, decision="unparsed",
                                            wrote=[], blocked=0))
        if dec.get("write"):
            wrote, say, screen = _save_all310(loop, list(dec["write"]), t)
            loop.lis310_stats["writes"] += len(wrote)
            if screen is not None:
                return finish(NOT_PLAIN310,
                              dict(base_row, decision="screen-" + screen,
                                   wrote=[], blocked=0))
            return finish(say or NOT_PLAIN310,
                          dict(base_row, decision="write", wrote=wrote,
                               blocked=0))
        if dec.get("ask_whose"):
            f0 = dec["ask_whose"][0]
            return finish(WHOSE_FMT310.format(rel=f0.get("rel"),
                                              value=f0.get("value")),
                          dict(base_row, decision="ask-whose", wrote=[],
                               blocked=0))
        if dec.get("ask_back"):
            f0 = dec["ask_back"][0]
            fact = f0.get("fact", f0) if isinstance(f0, dict) else {}
            loop.lis310_pending = {"fact": fact,
                                   "conf": f0.get("conf") if isinstance(
                                       f0, dict) else None}
            owner = fact.get("owner", "") if isinstance(fact, dict) else ""
            return finish(ASKBACK_FMT310.format(
                owner=_owner_display310(owner), rel=fact.get("rel", ""),
                value=fact.get("value", "")),
                dict(base_row, decision="ask-back", wrote=[], blocked=0))
        act = dec.get("act") or (frame.get("act") if isinstance(
            frame, dict) else None)
        if act in ("NEGATE", "SUPPOSE", "PLAN") or dec.get("held"):
            reply, blocked, _d = _base_pass_blocked310(loop, t)
            loop.lis310_stats["blocked"] += len(blocked)
            out = [l for l in reply if l] or []
            if blocked or not out:
                return finish(NOT_PLAIN310,
                              dict(base_row, decision="held-" + str(act),
                                   wrote=[], blocked=len(blocked)))
            return finish(out, dict(base_row, decision="held-" + str(act),
                                    wrote=[], blocked=0))
        # ASK, CHECK, CHAT, STATE-with-nothing, CORRECT-with-nothing,
        # UNCLEAR: base handles, writes blocked.
        reply, blocked, _d = _base_pass_blocked310(loop, t)
        loop.lis310_stats["blocked"] += len(blocked)
        out = [l for l in reply if l] or []
        if blocked or not out:
            return finish(NOT_PLAIN310,
                          dict(base_row, decision="base-" + str(act),
                               wrote=[], blocked=len(blocked)))
        return finish(out, dict(base_row, decision="base-" + str(act),
                                wrote=[], blocked=0))

    turn310.__name__ = "turn310"
    loop.turn = turn310
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("lis310" in n for n in notes):
        notes.append("lis310: 291 + listener turn310 (reader + compiler; "
                     "base rule chain never writes; writes only via the "
                     "teach/correct doorway; me stored as USER)")
    return loop


def _reader_from_cfg310(cfg: dict):
    liscfg = (cfg or {}).get("lis310", {}) or {}
    if liscfg.get("reader") is not None:
        return liscfg["reader"], float(liscfg.get("threshold",
                                                  DEFAULT_THRESHOLD310))
    model_dir = liscfg.get("model_dir")
    if model_dir:
        import claude_lis300_read as READ  # noqa: E402 (needs weights)

        return READ.Reader(model_dir), float(liscfg.get(
            "threshold", DEFAULT_THRESHOLD310))
    raise RuntimeError("lis-310 needs a reader: set cfg['lis310']['reader'] "
                       "or cfg['lis310']['model_dir']")


def build_agent310(cfg: dict | None = None):
    """291 base + the listener turn wrapper. cfg['lis310'] keys: reader (a
    StubReader in tests, a lis-300 Reader in production), model_dir,
    threshold (default 0.99)."""
    cfg = dict(DEFAULT_CONFIG310, **(cfg or {}))
    loop = B291.build_agent291(cfg)
    reader, threshold = _reader_from_cfg310(cfg)
    liscfg = cfg.get("lis310", {}) or {}
    install_turn310(loop, reader,
                    threshold=liscfg.get("threshold", threshold))
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn310":
        raise RuntimeError("310: turn310 not installed")
    if getattr(loop.turn310_inner, "__name__", "") != "turn291":
        raise RuntimeError("310: turn291 not under turn310")
    return loop


class Classes310Mixin:
    """Daemon mixin: 291 daemon init, then the 310 listener wrapper."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = kwargs.get("cfg", None)
        if cfg is None and len(args) >= 2:
            cfg = args[1]
        reader, threshold = _reader_from_cfg310(dict(cfg or {}))
        liscfg = (dict(cfg or {}).get("lis310", {}) or {})
        install_turn310(self.loop, reader,
                        threshold=liscfg.get("threshold", threshold))


class Loop310Daemon(Classes310Mixin, B291.Loop291Daemon):
    """Loop291Daemon with the lis-300 listener turn wrapper installed."""


assert Classes310Mixin.__mro__[0].__name__ == "Classes310Mixin"

DEFAULT_CONFIG310: dict = copy.deepcopy(B291.DEFAULT_CONFIG291)
DEFAULT_CONFIG310["daemon"]["module"] = (
    "Loop310Daemon (scripts/claude_lis310_agent.py) over Loop291Daemon "
    "with the lis-300 listener turn wrapper (reader + write compiler)")
DEFAULT_CONFIG310["lis310"] = {
    "base": "loop291 (scripts/claude_loop291_agent.py, builder-outbox)",
    "reader": None,
    "model_dir": None,
    "threshold": DEFAULT_THRESHOLD310,
    "threshold_note": ("lis-300 THRESHOLD.txt default until published; "
                       "no THRESHOLD.txt on origin/main as of 2026-09-23"),
    "me_subject": ("owner 'me' is stored as subject USER, exactly how the "
                   "base stores 'my' facts (probed: ('USER','sister','Mira'))"),
    "hook": "turn310 outside turn291 (outermost instance wrapper)",
    "log": LOG_NAME310,
}
DEFAULT_CONFIG310["merge310"] = {
    "base": "loop291 (scripts/claude_loop291_agent.py)",
    "added": ["lis-300 reader (MiniCPM5-1B, lis300_read.py) + write "
              "compiler (lis300_compiler.py), outermost turn310 wrapper"],
    "instance": ["turn310(turn291(turn260(turn224c(turn224(class turn))))"],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lis-310 agent (291+listener)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD310)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG310)
        out.pop("lis310", None)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG310)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.model:
        cfg["lis310"] = dict(cfg.get("lis310", {}), model_dir=args.model,
                             threshold=args.threshold)
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop310Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent310(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
