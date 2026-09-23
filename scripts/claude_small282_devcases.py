#!/usr/bin/env python3
"""Exp 282 dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-small282-20260923/devcases282.json: a list of
dialogs {id, family, turns, expect_store, probe}.
  turns        : list of turns (fresh daemon per dialog).
  expect_store : exact final store (list of [s, r, v]); None = not checked
                 (mixed/control equality with 260 is still asserted).
  probe        : for greet/thanks_close, the canonical probe class
                 ("greet" -> "Hello.", "thanks" -> "Thanks!",
                 "close" -> "Bye."); the scorer asserts the 282 arm's reply
                 equals its own arm's reply to that probe, with 0 writes.
Families (44 dialogs):
  greet         pure casual greetings (12; lowercase, slang, caps, runs,
                punctuation variants).
  thanks_close  thanks forms and closings with tails (12).
  mixed         small talk glued to a real teach or question (12): 282 must
                keep 260's every reply byte-identical, with equal stores.
  control       plain teaches/questions and already-working small talk (8):
                282 must keep 260's every reply byte-identical.
Question turns must write 0 events on both arms. Scored by
scripts/claude_small282_score.py dev. Never modelled on any panel.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-small282-20260923/devcases282.json")
C = []


def add(fam, turns, store, probe=None):
    C.append({"id": f"d282-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store, "probe": probe})


# Pure casual greetings -> the head's reply to "Hello.".
GREET = [
    "hey whats up",
    "whats up",
    "wassup",
    "sup",
    "HEY WHATS UP",
    "heyyy whats uppp",
    "hey whats new",
    "whats good",
    "yo sup",
    "hey there whats up",
    "good day",
    "hey... whats up?",
]
for t in GREET:
    add("greet", [t], [], probe="greet")

# Thanks forms and closings (with tails, or pure) -> "Thanks!" / "Bye.".
THANKS_CLOSE = [
    ("Thanks, that's all!", "thanks"),
    ("thanks thats all", "thanks"),
    ("that's it", "close"),
    ("thanks, bye for now", "thanks"),
    ("bye for now", "close"),
    ("many thanks", "thanks"),
    ("cheers", "thanks"),
    ("talk later", "close"),
    ("gotta go", "close"),
    ("Thanks, that's all, bye!", "thanks"),
    ("ok thanks, that's it", "thanks"),
    ("take care", "close"),
]
for t, p in THANKS_CLOSE:
    add("thanks_close", [t], [], probe=p)

# Mixed: small talk plus a real teach or question. 282 must equal 260.
MIXED = [
    (["Viggo's cat is Simba.", "hey, whats Viggo's cat"],
     [["Viggo", "cat", "Simba"]]),
    (["Viggo's cat is Simba.", "thanks! what is Viggo's cat?"],
     [["Viggo", "cat", "Simba"]]),
    (["Viggo's boss is Holm.", "hey whats up, who is Viggo's boss"],
     [["Viggo", "boss", "Holm"]]),
    (["Viggo's cat is Simba.", "Thanks, that's all. Who is Viggo's cat?"],
     [["Viggo", "cat", "Simba"]]),
    (["Nora lives in Oslo.", "bye! where does Nora live?"],
     [["Nora", "city", "Oslo"]]),
    (["sup Ana lives in Quito"], None),
    (["cheers, Skye's boat is Fjord"], None),
    (["good morning, Petra's band is Willow"],
     [["Petra", "band", "Willow"]]),
    (["Ivo's band is Lumen.", "see ya, what is Ivo's band?"],
     [["Ivo", "band", "Lumen"]]),
    (["Viggo's cat is Simba.", "hey, tell me what Viggo's cat is"],
     [["Viggo", "cat", "Simba"]]),
    (["thanks a lot! Viggo's cat is Simba."], None),
    (["whats Ana's city"], None),
]
for ts, store in MIXED:
    add("mixed", ts, store)

# Controls: plain teaches/questions and already-working small talk.
CONTROLS = [
    (["Viggo's cat is Simba.", "What is Viggo's cat?"],
     [["Viggo", "cat", "Simba"]]),
    (["Sanna lives in Tromso.", "Where does Sanna live?"],
     [["Sanna", "city", "Tromso"]]),
    (["thanks!"], []),
    (["bye!"], []),
    (["Hello."], []),
    (["how are you"], []),
    (["Pell's boss is Rhoda.", "Hi! Who is Pell's boss?"],
     [["Pell", "boss", "Rhoda"]]),
    (["good morning"], []),
]
for ts, store in CONTROLS:
    add("control", ts, store)

print(f"wrote {len(C)} cases to {OUT}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
