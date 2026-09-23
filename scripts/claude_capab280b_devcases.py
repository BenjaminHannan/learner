#!/usr/bin/env python3
"""Exp 280b dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-capab280b-20260923/devcases280b.json: a list of
dialogs {id, family, turns, expect_store, checks}.
Families:
  general  : general ability questions in varied wording (slang, typos,
             long/short, tell-me/list forms, what-it-is-for). Two carry a
             setup teach first (stored names must not block the rule).
  canyou   : "Can you <specific thing>?" turns (must keep 280's reply).
  nearmiss : NOT ability questions (person-ability questions, teaches
             with "can", name/negation probes; must keep 280's reply).
  control  : plain teaches and asks (must keep 280's reply).
  ability  : small save/ask/correct/forget sanity slice (byte-identical).
Question turns must write 0 events.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-capab280b-20260923/devcases280b.json")
C = []


def add(fam, turns, store, checks=(), note=""):
    C.append({"id": f"d280b-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "note": note})


# ---- general: varied wordings, all must get CAN280 on 280b ----
G = [
    "What can you do?",
    "what can u do",
    "What are you good at?",
    "wat r u good at",
    "Tell me what you are able to do",
    "list your skills",
    "List your abilities please",
    "What are your skills?",
    "what stuff are u capable of",
    "How can you help me?",
    "how can u help",
    "What do you do?",
    "what do u do",
    "What are you for?",
    "what r u for exactly",
    "So tell me about yourself, what can you do?",
    "hey, what are you able to do?",
    "Please describe all your abilities",
    "whut can you do?",
    "What are u good at??",
    "Tell me everything you can do for me",
    "what help can you give me",
    "List everything you're capable of doing",
    "i want to know what you do",
    "What is your purpose?",
    "hey please tell me your skills",
]
for t in G:
    add("general", [t], [], [])
# general after a setup teach (stored names must not block the rule)
add("general", ["Vessa's boss is Kipp.", "Wren's city is Dalby.",
                "so what can u do nowadays"],
    [["Vessa", "boss", "Kipp"], ["Wren", "city", "Dalby"]], [],
    note="setup teach then general")
add("general", ["Bexley's dog is Pip.",
                "Tell me, what are all your abilities?"],
    [["Bexley", "dog", "Pip"]], [], note="setup teach then general")

# ---- canyou: must keep 280's reply byte-identical ----
Y = [
    "Can you forget a fact?",
    "Can you correct a fact for me?",
    "Can you answer a two-step question?",
    "Can you remember things after a restart?",
    "Can you do math?",
    "Can you look things up on the web?",
    "Can you feel happy?",
    "Can you translate into another language?",
    "Can you tell me where a fact came from?",
    "Can you keep a secret?",
    "Could you forget everything about Sella?",
    "can u tell me who is Joren's boss",
]
for t in Y:
    add("canyou", [t], [], [])

# ---- nearmiss: NOT ability questions, keep 280's reply ----
N = [
    ["Zara's boss is Skye.", "What can Zara do?"],
    ["Tomas lives in Corra.", "What is Tomas good at?"],
    ["Ana can swim.", "Ana can swim."],
    ["Mira's cat is Soot.", "What does Mira do for work?"],
    ["What is your name?"],
    ["What can't you do?"],
    ["What can you not do?"],
    ["Pell's teacher is Mara.", "Who is Pell's teacher?"],
    ["Joss can juggle.", "Can Joss juggle?"],
    ["Nils's boss is Ada.", "Where does Nils's boss live?"],
    ["Quinn's cat is Tom.", "Forget Quinn's cat."],
    ["Rhea's city is Ulm.", "Who told you Rhea's city is Ulm?"],
]
for ts in N:
    add("nearmiss", ts, None, [])

# ---- control: plain teaches and asks ----
add("control", ["Rina's boss is Skye."], [["Rina", "boss", "Skye"]],
    [(0, "has", "Saved")])
add("control", ["Tavish lives in Corra."], [["Tavish", "city", "Corra"]],
    [(0, "has", "Saved")])
add("control", ["Rina's boss is Skye.", "Who is Rina's boss?"], None,
    [(1, "has", "Skye")])
add("control", ["Tavish lives in Corra.", "Where does Tavish live?"], None,
    [(1, "has", "Corra")])
add("control", ["Wren's job is mason.", "What is Wren's job?"], None,
    [(1, "has", "mason")])
add("control", ["Sable's cat is Mink.", "What is Sable's cat?"], None,
    [(1, "has", "Mink")])
add("control", ["Isolde's brother is Perrin.",
                "Who is Isolde's brother?"], None,
    [(1, "has", "Perrin")])
add("control", ["Casper was born in Vexley.",
                "Where was Casper born?"], None,
    [(1, "has", "Vexley")])
add("control", ["Odette's sister is Faye.",
                "Who is Odette's sister?"], None,
    [(1, "has", "Faye")])
add("control", ["Hollis works at Amberline.",
                "Where does Hollis work?"], None,
    [(1, "has", "Amberline")])

# ---- ability sanity slice (byte-identical 280b vs 280) ----
add("ability", ["Elke's city is Bonn.", "No, Elke's city is Mainz."],
    None, [], note="correct No-shape")
add("ability", ["Yara's cat is Moss.", "Yara's cat is Fig, not Moss."],
    None, [], note="contrast shape")
add("ability", ["Iris's city is Pavia.", "Forget Iris's city."],
    None, [], note="forget direct")
add("ability", ["Kira's boss is Loth.", "Forget everything about Kira."],
    None, [], note="forget everything-wording")
add("ability", ["Quill's boss is Dara.", "Dara's city is Nessa.",
                "Where does Quill's boss live?"], None, [],
    note="mixed twohop")
add("ability", ["Nils's boss is Ada.", "Ada's boss is Cleo.",
                "Who is Nils's boss's boss?"], None, [],
    note="boss-chain twohop")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"Wrote {OUT} ({len(C)} dialogs)")
    print(Counter(c["family"] for c in C))


if __name__ == "__main__":
    main()
