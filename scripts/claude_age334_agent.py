#!/usr/bin/env python3
"""334 sleep agenda (month-end line; plan design/v3/30-modes/330-month-end-plan.md, day 3).

One change on top of the listener stack (needs lis-314's pending store, turn314 outermost):
  - SLEEP picks the agenda. install_agenda334 wraps loop._sleep_tick. After the inner sleep,
    it picks at most MAX_PER_DAY334 = 2 pending facts, oldest first, that were never on an
    agenda before, and stores them in <state_dir>/agenda334.json (survives a restart).
  - The next day, after an ordinary reply that does not already end with a question (and not on
    the turn that answers a confirm question), it adds
    ONE agenda item in Ben's approved wording: "By the way, I think you told me X, is that
    right?" and hands that fact to turn314's confirm step (loop.lis314_confirming), so the
    user's plain "yes" saves it as taught and "no" drops it, exactly as in lis-314.
  - An agenda fact that is no longer pending (saved, replaced or dropped since) is skipped.
Nothing is saved by this layer; every write still goes through turn314 -> turn310's doorway.
"""
from __future__ import annotations

import json
from pathlib import Path

MAX_PER_DAY334 = 2
AGENDA_NAME334 = "agenda334.json"
PREFIX334 = "By the way, I think you told me {claim}, is that right?"


def _key(p: dict) -> tuple:
    return (str(p.get("owner", "")).lower(), str(p.get("rel", "")), str(p.get("value", "")))


def install_agenda334(loop, max_per_day: int = MAX_PER_DAY334) -> None:
    import claude_lis314_agent as L314
    if getattr(loop.turn, "__name__", "") != "turn314" and not hasattr(loop, "lis314_store"):
        raise RuntimeError("334: needs lis-314's pending store (install turn314 first)")
    path = Path(loop.dir) / AGENDA_NAME334
    state = {"agenda": [], "ever": []}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    loop.age334_stats = {"sleeps": 0, "picked": 0, "asked": 0, "skipped_stale": 0}

    def save() -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    inner_sleep = loop._sleep_tick

    def sleep334():
        event = inner_sleep()
        loop.age334_stats["sleeps"] += 1
        ever = {tuple(x) for x in state["ever"]}
        picks = [p for p in list(loop.lis314_store) if _key(p) not in ever][:max_per_day]
        state["agenda"] = [dict(p) for p in picks]
        state["ever"] += [list(_key(p)) for p in picks]
        loop.age334_stats["picked"] += len(picks)
        save()
        return event

    loop._sleep_tick = sleep334
    inner_turn = loop.turn

    def turn334(text):
        was_confirming = getattr(loop, "lis314_confirming", None) is not None
        reply = inner_turn(text)
        parts = list(reply) if isinstance(reply, (list, tuple)) else [str(reply)]
        if was_confirming or not state["agenda"] or getattr(loop, "lis314_confirming", None) is not None:
            return parts                          # at most one confirm question in flight
        if " ".join(parts).rstrip().endswith("?"):
            return parts
        while state["agenda"]:
            item = state["agenda"].pop(0)
            live = [p for p in loop.lis314_store if _key(p) == _key(item)]
            if not live:
                loop.age334_stats["skipped_stale"] += 1
                continue
            loop.lis314_confirming = live[-1]
            loop.age334_stats["asked"] += 1
            save()
            return parts + [PREFIX334.format(claim=L314.claim314(live[-1]))]
        save()
        return parts

    turn334.__name__ = "turn334"
    loop.turn = turn334
