#!/usr/bin/env python3
"""Exp 226 sealed case writer: fresh fictional names, expected replies for
every source turn written by hand-rule BEFORE any run.

Writes artifacts/fable-source226-20260922/cases226.json: a list of sessions
{id, type, turns: [{text, expect|null}]}; "<RESTART>" = rebuild daemon on the
same directory. expect=null marks a non-source turn (judged by P2 against
138i, not by a fixed string).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "fable-source226-20260922" / "cases226.json"

NO = "I'm not sure what \"that\" means — I haven't just told you a fact."
Q = ["Who told you that?", "How do you know that?", "Where did you learn that?",
     "Where did you get that?", "Who said that?", "How do you know?",
     "What's your source?", "Says who?", "who told you that", "Where did that come from?",
     "What is your source?", "How did you learn that?"]
P = ["Orla", "Tavin", "Brisk", "Quenby", "Senna", "Havel", "Ilka", "Maro",
     "Pell", "Vesna", "Dorn", "Elwin", "Fenna", "Garrow", "Hesper", "Isko",
     "Jory", "Kestra", "Lorn", "Mavi", "Nerys", "Odo", "Perrin", "Rook",
     "Sabel", "Tamsin", "Ulla", "Varn", "Wenna", "Yorick", "Zelda", "Arno",
     "Bexley", "Corin", "Dagny", "Eames", "Fitch", "Gildas", "Hollis", "Ivo"]
C = ["Velmora", "Tarsk", "Ondral", "Brisca", "Quellin", "Morvath", "Estrel",
     "Pyrra", "Dunmere", "Kalvik", "Soren", "Thule", "Varnik", "Wexmoor"]


def s(n):
    return P[n % len(P)]


def c(n):
    return C[n % len(C)]


def main() -> int:
    sess = []
    k = [0]

    def add(typ, turns):
        sess.append({"id": f"S{len(sess)+1:02d}", "type": typ, "turns": [
            {"text": t, "expect": e} for t, e in turns]})

    def q():
        k[0] += 1
        return Q[k[0] % len(Q)]

    # saved (city / person / employer / language / sister / correction)
    for i in range(6):
        a, x = s(i), c(i)
        add("saved-city", [(f"{a} lives in {x}.", None),
                           (q(), f"You did — you just told me {a}'s city is {x}.")])
    for i in range(6, 10):
        a, b = s(i), s(i + 10)
        add("saved-boss", [(f"{a}'s boss is {b}.", None),
                           (q(), f"You did — you just told me {a}'s boss is {b}.")])
    for i, comp in zip(range(10, 13), ["Zentrix", "Harrowgate", "Plumline"]):
        a = s(i)
        add("saved-employer", [(f"{a} works at {comp}.", None),
                               (q(), f"You did — you just told me {a}'s employer is {comp}.")])
    for i, lang in zip(range(13, 15), ["Basque", "Welsh"]):
        a = s(i)
        add("saved-language", [(f"{a} speaks {lang}.", None),
                               (q(), f"You did — you just told me {a}'s language is {lang}.")])
    for i in range(15, 18):
        a, x, y = s(i), c(i), c(i + 3)
        add("saved-correction", [(f"{a} lives in {x}.", None), (f"Actually, {a} lives in {y}.", None),
                                 (q(), f"You did — you just told me {a}'s city is {y}.")])
    # one-fact answers
    for i in range(18, 26):
        a, x = s(i), c(i)
        add("answer-1", [(f"{a} lives in {x}.", None), (f"Where does {a} live?", None),
                         (q(), f"You told me: {a}'s city is {x}.")])
    for i in range(26, 29):
        a, b = s(i), s(i + 5)
        add("answer-1-boss", [(f"{a}'s boss is {b}.", None), (f"Who is {a}'s boss?", None),
                              (q(), f"You told me: {a}'s boss is {b}.")])
    # two-hop chain
    for i in range(0, 7):
        a, b, x = s(i + 1), s(i + 20), c(i + 5)
        add("chain-2", [(f"{a}'s boss is {b}.", None), (f"{b} lives in {x}.", None),
                        (f"What city does {a}'s boss live in?", None),
                        (q(), f"I put together things you told me: {a}'s boss is {b}. {b}'s city is {x}.")])
    # three-hop chain
    for i in range(0, 3):
        a, b, d, x = s(i + 2), s(i + 12), s(i + 30), c(i + 8)
        add("chain-3", [(f"{a}'s boss is {b}.", None), (f"{b}'s boss is {d}.", None),
                        (f"{d} lives in {x}.", None),
                        (f"What city does {a}'s boss's boss live in?", None),
                        (q(), f"I put together things you told me: {a}'s boss is {b}. {b}'s boss is {d}. {d}'s city is {x}.")])
    # worked out backwards (153 reverse frames)
    for i in range(0, 5):
        a, b = s(i + 4), s(i + 24)
        frame = [f"Whose boss is {b}?", f"Who is {b} the boss of?"][i % 2]
        add("backwards", [(f"{a}'s boss is {b}.", None), (frame, None),
                          (q(), f"Nobody told me directly; I worked it out backwards from what you told me: {a}'s boss is {b}.")])
    # multi-valued answer
    for i in range(0, 2):
        a, b, d = s(i + 7), s(i + 17), s(i + 27)
        add("answer-multi", [(f"{a}'s sister is {b}.", None), (f"{a}'s sister is {d}.", None),
                             (f"Who is {a}'s sister?", None),
                             (q(), f"You told me: {a}'s sister is {b}. {a}'s sister is {d}.")])
    # grounded yes/no
    for i in range(0, 3):
        a, x, y = s(i + 9), c(i + 2), c(i + 9)
        v = x if i != 1 else y
        add("yesno", [(f"{a} lives in {x}.", None), (f"Is {a}'s city {v}?", None),
                      (q(), f"You told me: {a}'s city is {x}.")])
    # me facts
    for i, nm in enumerate(["Juniper", "Talwyn"]):
        add("me-name", [(f"My name is {nm}.", None), (q(), f"You did — you just told me your name is {nm}."),
                        ("What is my name?", None), (q(), f"You told me: your name is {nm}.")])
    # no-fact cases
    add("nofact-first", [(q(), NO)])
    add("nofact-first", [(q(), NO), (f"{s(33)} lives in {c(1)}.", None)])
    add("nofact-smalltalk", [(f"{s(34)} lives in {c(2)}.", None), ("Hello!", None), (q(), NO)])
    add("nofact-smalltalk", [(f"{s(35)} lives in {c(3)}.", None), ("Thanks!", None), (q(), NO)])
    add("nofact-decline", [(f"{s(36)} lives in {c(4)}.", None), (f"What does {s(36)} speak?", None), (q(), NO)])
    add("nofact-missing", [(f"{s(37)} lives in {c(5)}.", None), (f"Who is {s(37)}'s boss?", None), (q(), NO)])
    add("nofact-forget", [(f"{s(38)} lives in {c(6)}.", None), (f"Forget {s(38)}'s city.", None), (q(), NO)])
    add("nofact-reverse-none", [(f"{s(39)}'s boss is {s(3)}.", None), (f"Whose boss is {s(13)}?", None), (q(), NO)])
    add("nofact-capability", [(f"{s(0)} lives in {c(7)}.", None), ("What can you do?", None), (q(), NO)])
    add("nofact-restart", [(f"{s(1)} lives in {c(8)}.", None), ("<RESTART>", None), (q(), NO)])
    # restart between the answer and the source question
    for i in range(0, 3):
        a, x = s(i + 21), c(i + 11)
        add("restart-after-answer", [(f"{a} lives in {x}.", None), (f"Where does {a} live?", None),
                                     ("<RESTART>", None), (q(), NO)])
    add("restart-after-chain", [(f"{s(5)}'s boss is {s(15)}.", None), (f"{s(15)} lives in {c(12)}.", None),
                                (f"What city does {s(5)}'s boss live in?", None), ("<RESTART>", None), (q(), NO)])
    # asked twice / context moves on
    a, x = s(25), c(13)
    add("twice", [(f"{a} lives in {x}.", None), (f"Where does {a} live?", None),
                  (q(), f"You told me: {a}'s city is {x}."), (q(), f"You told me: {a}'s city is {x}.")])
    a, b, x = s(29), s(9), c(0)
    add("moves-on", [(f"{a}'s boss is {b}.", None), (q(), f"You did — you just told me {a}'s boss is {b}."),
                     (f"{b} lives in {x}.", None), (f"What city does {a}'s boss live in?", None),
                     (q(), f"I put together things you told me: {a}'s boss is {b}. {b}'s city is {x}."),
                     ("Hello!", None), (q(), NO)])
    OUT.write_text(json.dumps(sess, indent=1, ensure_ascii=False), encoding="utf-8")
    n_src = sum(1 for x in sess for t in x["turns"] if t["expect"] is not None)
    n_non = sum(1 for x in sess for t in x["turns"] if t["expect"] is None and t["text"] != "<RESTART>")
    print(f"sessions={len(sess)} source_turns={n_src} non_source_turns={n_non}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
