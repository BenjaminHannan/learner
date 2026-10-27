#!/usr/bin/env python3
"""lis-314 -- confirm-at-use, one wrapper (turn314), outermost in the listener stack.

Why: at a safe threshold the reader auto-saves too few facts (lis-301 recall 35% on its panel).
Asking "Just to check ...?" right away for every unsure fact costs Ben's attention on facts he
may never need. On lis-301's dev readings, holding unsure facts and confirming them only when
they are needed keeps 743/771 facts (96%), for 217 questions
(artifacts/claude-lis302-20260924/RESULTS.md).

The one change: a fact that passes every structural check but is below T (an "unsure" fact) is
not asked back. It goes to a pending store instead.
  - The pending store NEVER answers a question and never counts as known.
  - When the user asks a question (reader act ASK, not inverse) that the notebook cannot answer
    and a pending fact matches it (same owner and relation; newest wins), the reply is Ben's
    approved wording (02:07 UTC 2026-09-24): "I think you told me X, is that right?"
  - The next turn: a plain "yes" saves that fact through turn310's doorway (screens included)
    and replies with the save line. "no" drops it ("Okay, I won't save that."). Anything else
    leaves it pending and the turn is handled normally.
  - A newer saved fact or a newer pending fact for the same (owner, rel) replaces an older
    pending one.
The rest of the turn is handed on unchanged, except that the unsure facts are removed from the
frame that the inner layers see (MemoReader.override). A turn whose only facts were unsure gets
the reply "Okay." and saves nothing.
Structural failures, "we" facts and held modes are untouched (inner layers handle them as before).

The store is kept in <state_dir>/lis314_pending.json so it survives a restart.
New file only; no existing file is edited. Writes only through turn310's _save_all310.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_lis300_compiler as CMP  # noqa: E402 (read-only)
import claude_lis310_agent as L310  # noqa: E402 (read-only)
import claude_lis313_agent as L313  # noqa: E402 (read-only lookup helper)

LOG_NAME314 = "lis314_log.jsonl"
STORE_NAME314 = "lis314_pending.json"
CONFIRM_FMT314 = "I think you told me {claim}, is that right?"
ACK314 = "Okay."


def claim314(f):
    owner = str(f.get("owner", ""))
    head = "your" if owner == "me" else "%s's" % owner
    return "%s %s is %s" % (head, str(f.get("rel", "")).replace("_", " "), f.get("value", ""))


def _key(owner, rel):
    return (str(owner or "").strip().lower(), str(rel or ""))


def _log314(loop, row):
    try:
        with open(loop.lis314_log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _save_store(loop):
    try:
        Path(loop.lis314_store_path).write_text(json.dumps(loop.lis314_store, ensure_ascii=False),
                                                encoding="utf-8")
    except OSError:
        pass


def _load_store(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict)]
    except (OSError, ValueError):
        return []


def _drop_key(loop, owner, rel):
    k = _key(owner, rel)
    before = len(loop.lis314_store)
    loop.lis314_store = [p for p in loop.lis314_store if _key(p["owner"], p["rel"]) != k]
    return before - len(loop.lis314_store)


def install_turn314(loop, memo, threshold=L310.DEFAULT_THRESHOLD310, log_path=None,
                    store_path=None):
    """Install turn314 outside the current loop.turn (turn310, turn313 or turn315, on memo)."""
    inner = loop.turn
    if getattr(inner, "__name__", "") not in ("turn310", "turn313", "turn315"):
        raise RuntimeError("314: needs turn310, turn313 or turn315 inside")
    loop.turn314_inner = inner
    loop.lis314_threshold = float(threshold)
    folder = Path(loop.lis310_log_path).parent
    loop.lis314_log_path = str(log_path or (folder / LOG_NAME314))
    try:
        sdir = Path(loop.dir)
    except Exception:  # noqa: BLE001
        sdir = folder
    loop.lis314_store_path = str(store_path or (sdir / STORE_NAME314))
    loop.lis314_store = _load_store(loop.lis314_store_path)
    loop.lis314_confirming = None
    st = loop.lis314_stats = {"turns": 0, "held": 0, "ack_only": 0, "confirm_asked": 0,
                              "confirmed_yes": 0, "confirmed_no": 0, "confirm_dropped": 0,
                              "replaced": 0}

    def finish(t, prev, reply, row):
        loop.lis310_prev = " ".join(reply)
        _log314(loop, dict(row, turn=t, prev=prev, reply=reply,
                           store=len(loop.lis314_store)))
        return reply

    def triples_now():
        try:
            import fable_loop90_agent as L90
            return set(L90.notebook_triples(loop.nb))
        except Exception:  # noqa: BLE001
            return set()

    def after_inner(ev0, before):
        """A newly saved fact replaces pending facts with the same (owner, rel)."""
        if len(loop.nb.events) == ev0 or not loop.lis314_store:
            return
        new = triples_now() - before
        changed = 0
        for p in list(loop.lis314_store):
            subj = L310.USER_SUBJECT310 if p["owner"] == "me" else p["owner"]
            if any(s.lower() == subj.lower() and r == p["rel"] for (s, r, _v) in new):
                changed += _drop_key(loop, p["owner"], p["rel"])
        if changed:
            st["replaced"] += changed
            _save_store(loop)

    def run_inner(t):
        before = triples_now() if loop.lis314_store else set()
        ev0 = len(loop.nb.events)
        reply = loop.turn314_inner(t)
        after_inner(ev0, before)
        return reply

    def turn314(text):  # type: ignore[no-untyped-def]
        t = str(text)
        st["turns"] += 1
        prev = loop.lis310_prev or ""
        # 1. answer to our own confirm question
        conf = loop.lis314_confirming
        if conf is not None:
            loop.lis314_confirming = None
            yn = L310._norm_yesno(t)
            if yn in L310.YES310:
                ev0 = len(loop.nb.events)
                wrote, say, screen = L310._save_all310(loop, [conf], t)
                _drop_key(loop, conf["owner"], conf["rel"])
                _save_store(loop)
                st["confirmed_yes"] += 1
                loop.lis310_stats["writes"] += len(wrote)
                return finish(t, prev, [say or L310.NOT_PLAIN310],
                              {"decision": "confirm-yes", "fact": conf, "wrote": wrote,
                               "screen": screen, "events": len(loop.nb.events) - ev0})
            if yn in L310.NO310:
                _drop_key(loop, conf["owner"], conf["rel"])
                _save_store(loop)
                st["confirmed_no"] += 1
                return finish(t, prev, [L310.DROPPED310], {"decision": "confirm-no", "fact": conf})
            st["confirm_dropped"] += 1  # any other answer: fact stays pending, turn goes on
        # 2. turn310's own pending ask-back gets a plain yes/no: pass through, no read
        if loop.lis310_pending is not None and L310._norm_yesno(t) in (L310.YES310 | L310.NO310):
            return run_inner(t)
        read = memo.read(t, prev)
        frame = read[0] if isinstance(read, (tuple, list)) and read else None
        if not isinstance(frame, dict):
            return loop.turn314_inner(t)
        try:
            confs = list(read[1]) if read[1] is not None else []
        except TypeError:
            confs = []
        facts = frame.get("facts") or []
        # 3. a question the notebook can't answer, matching a pending fact -> confirm
        ask = frame.get("ask")
        if (frame.get("act") == "ASK" and isinstance(ask, dict) and not ask.get("inverse")
                and not ask.get("via") and loop.lis314_store):
            k = _key(ask.get("owner"), ask.get("rel"))
            match = [p for p in loop.lis314_store if _key(p["owner"], p["rel"]) == k]
            if match:
                ev0 = len(loop.nb.events)
                look = L313._lookup313(loop.nb, ask)
                assert len(loop.nb.events) == ev0, "314: lookup wrote"
                if look["value"] is None:
                    fact = match[-1]
                    loop.lis314_confirming = fact
                    loop.lis310_pending = None
                    st["confirm_asked"] += 1
                    return finish(t, prev, [CONFIRM_FMT314.format(claim=claim314(fact))],
                                  {"decision": "confirm-ask", "fact": fact, "frame": frame})
        # 4. unsure facts go to the pending store; the inner layers see the rest of the frame
        unsure, keep, keep_conf = [], [], []
        for i, f in enumerate(facts):
            c = confs[i] if i < len(confs) else 0.0
            if (isinstance(f, dict) and CMP.check_fact(f, t, prev) is None
                    and c < loop.lis314_threshold):
                unsure.append({"owner": str(f.get("owner", "")), "rel": str(f.get("rel", "")),
                               "value": str(f.get("value", "")), "mode": f.get("mode"),
                               "conf": c})
            else:
                keep.append(f)
                keep_conf.append(c)
        if not unsure:
            return run_inner(t)
        for u in unsure:
            st["replaced"] += _drop_key(loop, u["owner"], u["rel"])
            loop.lis314_store.append(u)
            st["held"] += 1
        _save_store(loop)
        if not keep and frame.get("act") in ("STATE", "CORRECT", None):
            st["ack_only"] += 1
            return finish(t, prev, [ACK314], {"decision": "held-ack", "held": unsure,
                                              "frame": frame})
        edited = dict(frame, facts=keep)
        memo.override(t, prev, (edited, keep_conf) + tuple(read[2:]))
        reply = run_inner(t)
        _log314(loop, {"turn": t, "decision": "held+inner", "held": unsure, "reply": reply,
                       "store": len(loop.lis314_store)})
        return reply

    turn314.__name__ = "turn314"
    loop.turn = turn314
    return loop
