#!/usr/bin/env python3
"""Make commapanel263 panel.jsonl (60 items). Deterministic, no RNG.

Families: unlisted_opener_teach 20, appositive_subject 10,
comma_value_ok 8, question 8, control 14. Fictional names only.
IDs c263-001 .. c263-060. 10 panel fields exactly:
id, family, setup, turn, followup, stated_facts, expect_store,
gold, plain_turn, note.
run_base.py appends the base outcome marker to note (" | base: ...").
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "panel.jsonl"

ITEMS = []


def add(family, setup, turn, followup, stated, expect, gold, plain, note):
    n = len(ITEMS) + 1
    ITEMS.append({
        "id": f"c263-{n:03d}",
        "family": family,
        "setup": setup,
        "turn": turn,
        "followup": followup,
        "stated_facts": stated,
        "expect_store": expect,
        "gold": gold,
        "plain_turn": plain,
        "note": note,
    })


def teach(opener, subj, rel, val, q, fam="unlisted_opener_teach",
          how="unlisted opener + comma before a plain teach"):
    """opener includes the trailing comma, e.g. 'Yo,'."""
    plain = f"{subj}'s boss is {val}." if rel == "boss" else \
            f"{subj}'s job is {val}." if rel == "job" else \
            f"{subj} lives in {val}." if rel == "city" else \
            f"{subj} works at {val}."
    stated = [[subj, rel, val]]
    add(fam, [], f"{opener} {plain}", q, stated, [list(stated[0])],
        val, plain, f"{how}; stored subject must be the name alone")


# --- unlisted_opener_teach x20 (possessive/job/verb teaches) ---
U = "unlisted_opener_teach"
teach("Yo,", "Zelvick", "boss", "Marwick", "Who is Zelvick's boss?")
teach("Oi,", "Quarwick", "boss", "Holtwick", "Who is Quarwick's boss?")
teach("Heyo,", "Brellwick", "boss", "Grannick", "Who is Brellwick's boss?")
teach("Ayo,", "Harwick", "boss", "Pallwick", "Who is Harwick's boss?")
teach("Whoa,", "Pellwick", "boss", "Stannick", "Who is Pellwick's boss?")
teach("Wow,", "Torvick", "boss", "Wrenwick", "Who is Torvick's boss?")
teach("Eh,", "Selvick", "boss", "Yannick", "Who is Selvick's boss?")
teach("Huh,", "Norvick", "boss", "Zannick", "Who is Norvick's boss?")
teach("Yikes,", "Kelvick", "boss", "Drannick", "Who is Kelvick's boss?")
teach("Dude,", "Delvick", "boss", "Frannick", "Who is Delvick's boss?")
teach("Bro,", "Rullwick", "boss", "Clannick", "Who is Rullwick's boss?")
teach("Ugh,", "Jannick", "boss", "Blannick", "Who is Jannick's boss?")
teach("Psst,", "Tollwick", "boss", "Vrannick", "Who is Tollwick's boss?")
teach("Nah,", "Vesswick", "boss", "Krannick", "Who is Vesswick's boss?")
teach("Fam,", "Bramwick", "job", "fisher", "What is Bramwick's job?")
teach("Pals,", "Collwick", "job", "baker", "What is Collwick's job?")
teach("Get this,", "Desswick", "boss", "Trannick",
      "Who is Desswick's boss?")
teach("Real talk,", "Ellwick", "boss", "Shannick",
      "Who is Ellwick's boss?")
teach("Yo,", "Frannick", "city", "Tollan", "Where does Frannick live?")
teach("Guess what,", "Gennick", "boss", "Quannick",
      "Who is Gennick's boss?")

# --- appositive_subject x10: base stores nothing; expect_store [] ---
A = "appositive_subject"
APPOS = [
    ("Zandwick", "brother", "city", None, "Fenwick", "works",
     "Where does Zandwick work?", "employer"),
    ("Quellwick", "sister", "city", None, "Brindle", "works",
     "Where does Quellwick work?", "employer"),
    ("Brannwick", "cousin", "city", None, "Rook", "works",
     "Where does Brannwick work?", "employer"),
    ("Harllwick", "friend", "city", None, "Ashwick", "works",
     "Where does Harllwick work?", "employer"),
    ("Pellwick", "aunt", "city", None, "Tollan", "works",
     "Where does Pellwick work?", "employer"),
    ("Selwick", "brother", "Tollan", None, None, "lives",
     "Where does Selwick live?", "city"),
    ("Norwick", "sister", "Vesk", None, None, "lives",
     "Where does Norwick live?", "city"),
    ("Kelwick", "cousin", "Brindle", None, None, "lives",
     "Where does Kelwick live?", "city"),
    ("Delwick", "friend", "Ashwick", None, None, "lives",
     "Where does Delwick live?", "city"),
    ("Rullwick", "aunt", "Rook", None, None, "lives",
     "Where does Rullwick live?", "city"),
]
for subj, reln, place, _x, work, kind, q, rel in APPOS:
    if kind == "works":
        turn = f"{subj}, my {reln}, works at {work}."
        stated = [[subj, "employer", work]]
        gold = work
    else:
        turn = f"{subj}, who is my {reln}, lives in {place}."
        stated = [[subj, "city", place]]
        gold = place
    add(A, [], turn, q, stated, [],
        gold, "",
        "appositive subject; gold stores nothing with a comma subject")


def cvteach(subj, rel, val, q):
    plain = f"{subj} lives in {val}." if rel == "city" else \
            f"{subj} works at {val}." if rel == "employer" else \
            f"{subj}'s job is {val}." if rel == "job" else \
            f"{subj}'s boss is {val}."
    stated = [[subj, rel, val]]
    add("comma_value_ok", [], plain, q, stated, [list(stated[0])],
        val, "",
        "comma belongs in the value; subject must stay clean")


# --- comma_value_ok x8 ---
cvteach("Harbwick", "city", "Tollan, Vesk", "Where does Harbwick live?")
cvteach("Marbwick", "city", "Brindle, Rook Ward",
        "Where does Marbwick live?")
cvteach("Darbwick", "employer", "Fenwick, Rook",
        "Where does Darbwick work?")
cvteach("Farbwick", "employer", "Brindle, Tollan Branch",
        "Where does Farbwick work?")
cvteach("Garbwick", "job", "lantern lighter, harbor ward",
        "What is Garbwick's job?")
cvteach("Larbwick", "job", "ferry runner, night shift",
        "What is Larbwick's job?")
cvteach("Narbwick", "boss", "Marwick, Warden of Holt",
        "Who is Narbwick's boss?")
cvteach("Parbwick", "boss", "Grannick, Warden of Vesk",
        "Who is Parbwick's boss?")


def ques(setup, turn, plain, gold):
    add("question", setup, turn, "", [], [], gold, plain,
        "unlisted opener + comma on a question; 0 writes")


# --- question x8 (setup plain teach, opener question, no followup) ---
ques(["Zorwick lives in Tollan."], "Honestly, where does Zorwick live?",
     "Where does Zorwick live?", "Tollan")
ques(["Korwick's boss is Marwick."], "Guess what, who is Korwick's boss?",
     "Who is Korwick's boss?", "Marwick")
ques(["Lorwick works at Fenwick."], "Listen, where does Lorwick work?",
     "Where does Lorwick work?", "Fenwick")
ques(["Morwick's job is weaver."], "Guess what, what is Morwick's job?",
     "What is Morwick's job?", "weaver")
ques(["Sorwick lives in Vesk."], "Yo, where does Sorwick live?",
     "Where does Sorwick live?", "Vesk")
ques(["Torwick's boss is Holtwick."], "Get this, who is Torwick's boss?",
     "Who is Torwick's boss?", "Holtwick")
ques(["Vorwick works at Brindle."], "Real talk, where does Vorwick work?",
     "Where does Vorwick work?", "Brindle")
ques(["Worwick's job is mason."], "Yo, what is Worwick's job?",
     "What is Worwick's job?", "mason")


def cteach(subj, rel, val, q):
    plain = f"{subj}'s boss is {val}." if rel == "boss" else \
            f"{subj} lives in {val}." if rel == "city" else \
            f"{subj} works at {val}." if rel == "employer" else \
            f"{subj}'s job is {val}."
    stated = [[subj, rel, val]]
    add("control", [], plain, q, stated, [list(stated[0])],
        val, "", "plain control teach; base must be right")


def cques(setup, turn, gold):
    add("control", setup, turn, "", [], [], gold, "",
        "plain control question; base must be right")


# --- control x14 (7 teaches + 7 questions, no commas anywhere) ---
cteach("Yarvick", "boss", "Zannick", "Who is Yarvick's boss?")
cteach("Zanwick", "city", "Brindle", "Where does Zanwick live?")
cteach("Xanwick", "employer", "Rook", "Where does Xanwick work?")
cteach("Wanwick", "job", "carter", "What is Wanwick's job?")
cteach("Vanwick", "boss", "Prannick", "Who is Vanwick's boss?")
cteach("Uanwick", "city", "Ashwick", "Where does Uanwick live?")
cteach("Tanwick", "employer", "Tollan", "Where does Tanwick work?")
cques(["Sanwick lives in Vesk."], "Where does Sanwick live?", "Vesk")
cques(["Ranwick's boss is Klannick."], "Who is Ranwick's boss?",
      "Klannick")
cques(["Qanwick works at Ashwick."], "Where does Qanwick work?",
      "Ashwick")
cques(["Panwick's job is dyer."], "What is Panwick's job?", "dyer")
cques(["Oanwick lives in Rook."], "Where does Oanwick live?", "Rook")
cques(["Nanwick's boss is Dlannick."], "Who is Nanwick's boss?",
      "Dlannick")
cques(["Manwick works at Brindle."], "Where does Manwick work?",
      "Brindle")


def main():
    assert len(ITEMS) == 60, len(ITEMS)
    from collections import Counter
    counts = Counter(i["family"] for i in ITEMS)
    assert counts["unlisted_opener_teach"] == 20, counts
    assert counts["appositive_subject"] == 10, counts
    assert counts["comma_value_ok"] == 8, counts
    assert counts["question"] == 8, counts
    assert counts["control"] == 14, counts
    assert len({i["id"] for i in ITEMS}) == 60
    assert len({i["turn"] for i in ITEMS}) == 60, "duplicate turns"
    ids = [i["id"] for i in ITEMS]
    assert ids == [f"c263-{n:03d}" for n in range(1, 61)]
    for i in ITEMS:
        assert set(i) == {"id", "family", "setup", "turn", "followup",
                          "stated_facts", "expect_store", "gold",
                          "plain_turn", "note"}, set(i)
    with open(OUT, "w", encoding="utf-8") as f:
        for i in ITEMS:
            f.write(json.dumps(i, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(ITEMS)} items)")


if __name__ == "__main__":
    main()
