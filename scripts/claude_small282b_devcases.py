#!/usr/bin/env python3
"""Exp 282b dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-small282b-20260923/devcases282b.json: a list of
dialogs {id, family, turns, expect_store, probe}.
  turns        : list of turns (fresh daemon per dialog).
  expect_store : exact final store (list of [s, r, v]); None = not checked
                 (282b-vs-282 equality is still asserted).
  probe        : for greet/thanks_close, the canonical probe class
                 ("greet" -> "Hello.", "thanks" -> "Thanks!",
                 "close" -> "Bye."); the scorer asserts the 282b arm's
                 reply equals its own arm's reply to that probe, with
                 0 writes.
Families (65 dialogs, 79 turns):
  greet         pure casual greetings (20; lowercase, slang, typos,
                extra words, emoji, opener words, assistant's name).
  thanks_close  thanks forms and closings (20; tails, typos, emoji,
                extra words).
  mixed         small talk glued to a real teach or question (15):
                282b must keep 282's every reply byte-identical, with
                equal stores.
  control       plain teaches/questions and already-working small talk
                (10): 282b must keep 282's every reply byte-identical.
Question turns must write 0 events on both arms. Scored by
scripts/claude_small282b_score.py dev. Never modelled on any panel.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-small282b-20260923/devcases282b.json")
C = []


def add(fam, turns, store, probe=None):
    C.append({"id": f"d282b-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store, "probe": probe})


# Pure casual greetings -> the head's reply to "Hello.".
GREET = [
    "hey whats up",
    "yo sup man",
    "heyyy",
    "good morninggg lol",
    "hey \U0001F44B",
    "oh hey there",
    "hiya dude how is it going",
    "well hey whats new",
    "yo whats good bro",
    "morning mate",
    "hey man thanks",
    "HELLOOO THERE",
    "sup sup sup",
    "hey so whats up",
    "howdy man",
    "hey lol whats happening",
    "good day to you",
    "yo premonition",
    "hey whats uppp",
    "hi hi hello",
]
for t in GREET:
    add("greet", [t], [], probe="greet")

# Thanks forms and closings -> "Thanks!" / "Bye.".
THANKS_CLOSE = [
    ("thanks a lot man", "thanks"),
    ("thank you so much", "thanks"),
    ("thx bye", "thanks"),
    ("bye for now", "close"),
    ("ok thanks thats it", "thanks"),
    ("cheers mate", "thanks"),
    ("many thanks \U0001F64F", "thanks"),
    ("gotta go talk later", "close"),
    ("see ya later", "close"),
    ("thanks thats all bye", "thanks"),
    ("cool thanks", "thanks"),
    ("take care bye", "close"),
    ("thankss", "thanks"),
    ("byee", "close"),
    ("okay bye for now", "close"),
    ("awesome thanks man", "thanks"),
    ("talk to you later dude", "close"),
    ("thanks ever so much", "thanks"),
    ("good night mate", "close"),
    ("well thanks and bye", "thanks"),
]
for t, p in THANKS_CLOSE:
    add("thanks_close", [t], [], probe=p)

# Mixed: small talk plus a real teach or question. 282b must equal 282.
MIXED = [
    (["Tessa's cat is Miso.", "hey, whats Tessa's cat"],
     [["Tessa", "cat", "Miso"]]),
    (["Tessa's cat is Miso.", "thanks! what is Tessa's cat?"],
     [["Tessa", "cat", "Miso"]]),
    (["Liam's boss is Petra.", "yo sup, who is Liam's boss"],
     [["Liam", "boss", "Petra"]]),
    (["Aisha lives in Porto.", "bye! where does Aisha live?"],
     [["Aisha", "city", "Porto"]]),
    (["sup Oskar lives in Riga"], None),
    (["cheers, Nils's boat is Fjord"], None),
    (["good morning, Wren's band is Willow"],
     [["Wren", "band", "Willow"]]),
    (["thanks a lot! Tessa's cat is Miso."], None),
    (["whats Tessa's city"], None),
    (["hey man, Bruno's dog is Pip"], None),
    (["Tessa's cat is Miso.", "oh hey, is Tessa's cat Miso?"],
     [["Tessa", "cat", "Miso"]]),
    (["Tessa's cat is Miso.", "see you later, what is Tessa's cat?"],
     [["Tessa", "cat", "Miso"]]),
    (["hello, my name is Zara"], None),
    (["thanks, Dara's street is Elm"], None),
    (["Tessa's cat is Miso.", "good night! who is Tessa's cat?"],
     [["Tessa", "cat", "Miso"]]),
]
for ts, store in MIXED:
    add("mixed", ts, store)

# Controls: plain teaches/questions and already-working small talk.
CONTROLS = [
    (["Tessa's cat is Miso.", "What is Tessa's cat?"],
     [["Tessa", "cat", "Miso"]]),
    (["Sanna lives in Tromso.", "Where does Sanna live?"],
     [["Sanna", "city", "Tromso"]]),
    (["thanks!"], []),
    (["bye!"], []),
    (["Hello."], []),
    (["how are you"], []),
    (["Ivo's band is Lumen.", "Hi! Who is Ivo's band?"],
     [["Ivo", "band", "Lumen"]]),
    (["good morning"], []),
    (["Kira's teacher is Owen.", "Who is Kira's teacher?"],
     [["Kira", "teacher", "Owen"]]),
    (["thank you"], []),
]
for ts, store in CONTROLS:
    add("control", ts, store)

print(f"wrote {len(C)} cases to {OUT}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
