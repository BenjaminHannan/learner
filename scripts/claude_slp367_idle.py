#!/usr/bin/env python3
"""slp-367: IDLE SLEEP ("sleep pressure"; Fix-sleep thread, 2026-09-25; roadmap 365 step 3).

Ben, 00:32 UTC: "The model won't always be active, and while it isn't, it should be doing something."
In 0.1 sleep is only due after 100000 turns, so the daemon's idle ticks (fable_daemon74_run.py:196-205, one
loop.step() every idle_seconds without mail) run THINKING, which does nothing; the 336 harness forced one sleep
per day instead.

ONE CHANGE: install_idle367(loop) replaces loop.sleep_due with a pressure rule:
  - never inside a user turn (loop.turn is wrapped and sets a flag), so a reply is never delayed by sleep;
  - on an idle step, due when at least MIN_NEW367 new experience rows arrived since the last sleep, or when at
    least one new row arrived and LONG_IDLE367 seconds passed since the last sleep.
Limit, stated: a message that arrives while a sleep is already running waits until it ends (~1.5 min on CPU for
today's sleeper). Interrupting a running sleep needs the sleep in a separate process; that is a later step.
"""
from __future__ import annotations

import time

MIN_NEW367 = 10
LONG_IDLE367 = 30 * 60


def install_idle367(loop, min_new: int = MIN_NEW367, long_idle: float = LONG_IDLE367, clock=time.time):
    loop.idle367 = {"in_turn": 0, "last_sleep_t": clock(), "sleeps": 0, "blocked_in_turn": 0,
                    "min_new": int(min_new), "long_idle": float(long_idle)}
    st = loop.idle367

    def new_rows() -> int:
        return len(loop.experience) - int(loop.sleep_mark)

    def sleep_due367() -> bool:
        n = new_rows()
        if n <= 0:
            return False
        if st["in_turn"]:
            if n >= st["min_new"]:
                st["blocked_in_turn"] += 1
            return False
        return n >= st["min_new"] or (clock() - st["last_sleep_t"]) >= st["long_idle"]

    loop.sleep_due = sleep_due367
    inner_turn = loop.turn

    def turn367(text):
        st["in_turn"] += 1
        try:
            return inner_turn(text)
        finally:
            st["in_turn"] -= 1

    turn367.__name__ = "turn367"
    loop.turn = turn367
    inner_sleep = loop._sleep_tick

    def sleep367():
        event = inner_sleep()
        st["sleeps"] += 1
        st["last_sleep_t"] = clock()
        return event

    loop._sleep_tick = sleep367
    loop.notes.append(f"slp-367: sleeps on idle steps when >= {min_new} new turns (or any after "
                      f"{int(long_idle)} s); never inside a turn")
    return st
