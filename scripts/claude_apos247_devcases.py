"""Exp 247: writes the dev cases artifacts/claude-apos247-20260922/dev247.jsonl.

Fictional names only. Families: fix (C1 no-apostrophe questions, must be
right), keep (forms that already work: reply byte-identical to base228),
trap (untaught facts / name gates in the C1 wording: no stored value),
outside (greeting/please/yes-no/verb variants whose APOSTROPHE twin also
fails on base228: reported, must give no wrong value and no write).
"""
import json
import sys
from pathlib import Path

S_PELL = ["Pell's city is Quellport.", "Pell's spouse is Orrin.",
          "Pell's boss is Dace.", "Pell's pet is Biscuit.",
          "Pell's employer is Quorra Mills."]
S_JOREN = ["Joren Hale's boss is Sella Voss.", "Joren Hale's city is Selwick.",
           "Joren Hale's spouse is Mirel Dun.", "Joren Hale's pet is Pip."]
S_CHAIN = ["Pell's spouse is Orrin.", "Orrin's city is Tarn."]
S_BIRTH = ["Joren Hale's place of birth is Wexmoor.", "Mira Joren's boss is Kell."]
S_QUILL = ["Quill's colour is teal.", "Quill's school is Brindle Academy.",
           "Quill's friend is Lune."]
S_ROOK = ["Anna Bel Rook's city is Farrow."]
S_BRAN = ["brannick's city is Holm.", "brannick's spouse is Tamsin."]
S_TAVI = ["Tavi's sister is Nessa.", "Tavi's hometown is Oskar Bay."]
S_JJ = ["Joren's city is Arn.", "Joren Hale's city is Selwick."]
S_TOMS = ["The Toms's city is Brask.", "Tom's city is Varn."]
S_MARI = ["Maris's city is Dunmoor.", "Mari's boss is Tev."]
S_PART = ["Pell's city is Quellport.", "Pell's spouse is Orrin."]
S_JPART = ["Joren Hale's boss is Sella Voss.", "Joren Hale's city is Selwick."]

C = []


def add(fam, setup, q, gold=None, allowed=(), note=""):
    C.append({"family": fam, "setup": list(setup), "question": q,
              "gold": gold, "allowed_mentions": list(allowed), "note": note})


# ---- fix: C1 forms (>= 30)
add("fix", S_PELL, "Who is Pells spouse?", "Orrin", note="1w spouse")
add("fix", S_PELL, "What is Pells city?", "Quellport", note="1w city")
add("fix", S_PELL, "what is pells city?", "Quellport", note="1w lower")
add("fix", S_PELL, "WHAT IS PELLS CITY?", "Quellport", note="1w upper")
add("fix", S_PELL, "What is Pells pet?", "Biscuit", note="1w pet")
add("fix", S_PELL, "Who is Pells employer?", "Quorra Mills", note="1w employer")
add("fix", S_PELL, "Where is Pells city?", "Quellport", note="where-is")
add("fix", S_PELL, "who is pells spouse?", "Orrin", note="1w lower spouse")
add("fix", S_PELL, "Who's Pells spouse?", "Orrin", note="who's contraction")
add("fix", S_PELL, "What's Pells pet?", "Biscuit", note="what's contraction")
add("fix", S_PELL, "Tell me Pells city?", "Quellport", note="tell-me")
add("fix", S_JOREN, "Who is Joren Hales boss?", "Sella Voss", note="2w boss")
add("fix", S_JOREN, "who is joren hales boss?", "Sella Voss", note="2w lower")
add("fix", S_JOREN, "What is Joren Hales city?", "Selwick", note="2w city")
add("fix", S_JOREN, "WHO IS JOREN HALES SPOUSE?", "Mirel Dun", note="2w upper")
add("fix", S_JOREN, "Who is Joren Hales spouse?", "Mirel Dun", note="2w spouse")
add("fix", S_JOREN, "What is Joren Hales pet?", "Pip", note="2w pet")
add("fix", S_JOREN, "Where is joren hales city?", "Selwick", note="2w lower where")
add("fix", S_JOREN, "What's Joren Hales city?", "Selwick", note="2w what's")
add("fix", S_CHAIN, "What is Pells spouse's city?", "Tarn", ["Orrin"],
    note="two-hop, first link no apostrophe")
add("fix", S_CHAIN, "What is Orrins city?", "Tarn", ["Orrin"], note="value-entity subject")
add("fix", S_BIRTH, "What is Joren Hales place of birth?", "Wexmoor",
    note="2w, multi-word relation")
add("fix", S_BIRTH, "Where is Joren Hales place of birth?", "Wexmoor",
    note="2w, multi-word relation, where")
add("fix", S_BIRTH, "Who is Mira Jorens boss?", "Kell", note="2w person rel")
add("fix", S_QUILL, "What is Quills colour?", "teal", note="colour (base: opinion route)")
add("fix", S_QUILL, "What is Quills school?", "Brindle Academy", note="school")
add("fix", S_QUILL, "what is quills school?", "Brindle Academy", note="school lower")
add("fix", S_ROOK, "What is Anna Bel Rooks city?", "Farrow", note="3w name")
add("fix", S_BRAN, "What is brannicks city?", "Holm", note="lower-taught name")
add("fix", S_BRAN, "Who is Brannicks spouse?", "Tamsin", note="lower-taught, asked title")
add("fix", S_TAVI, "What is Tavis hometown?", "Oskar Bay", note="hometown")
add("fix", S_JJ, "What is Joren Hales city?", "Selwick",
    note="2w name whose first word is another entity")
add("fix", S_JJ, "What is Jorens city?", "Arn", note="1w beside a 2w name")
add("fix", S_TOMS, "What is Toms city?", None,
    note="PLURAL GATE: 'The Toms' known -> must NOT rewrite; kept as keep")
C[-1]["family"] = "keep"

# ---- keep: already works on base (>= 8)
add("keep", S_PELL, "Who is Pell's spouse?", "Orrin", note="apostrophe")
add("keep", S_PELL, "What is Pell's city?", "Quellport", note="apostrophe")
add("keep", S_PELL, "Who is Pells boss?", "Dace", note="165 person rel")
add("keep", S_JOREN, "Who is Joren Hale's boss?", "Sella Voss", note="2w apostrophe")
add("keep", S_PELL, "What's Pell's pet?", "Biscuit", note="what's apostrophe")
add("keep", S_PELL, "Tell me Pell's pet?", "Biscuit", note="tell-me apostrophe")
add("keep", S_QUILL, "Who is Quills friend?", "Lune", note="165 person rel")
add("keep", S_TAVI, "Who is Tavis sister?", "Nessa", note="165 person rel")
add("keep", S_PELL, "Is Orrin Pell's spouse?", "Yes", ["Orrin"], note="154d yes/no")
add("keep", S_PELL, "Where does Pell live?", "Quellport", note="verb twin")
add("keep", S_PELL, "Who is Pells father?", None, note="165 untaught -> decline")
add("keep", S_PELL + ["Pells sister is Wren."], "Who is Pell's sister?", "Wren",
    note="165 teach repair unchanged")
add("keep", S_PELL, "What is your favourite city?", None, note="opinion route")
add("keep", S_PELL, "How many facts do you know?", None, note="self route")

# ---- traps: untaught / name gates in the C1 wording (>= 6)
add("trap", S_PART, "What is Pells pet?", note="pet untaught")
add("trap", S_JPART, "Who is Joren Hales spouse?", note="2w spouse untaught")
add("trap", S_CHAIN, "Who is Orrins boss?", allowed=["Orrin"], note="Orrin has city only (Orrin = the asked name)")
add("trap", S_PART, "Who is Orrins spouse?", note="Orrin has no facts")
add("trap", S_MARI, "Who is Maris boss?", note="Maris itself a name: no rewrite, never Tev")
add("trap", ["Joren's city is Arn."], "What is Joren Hales city?",
    note="Joren Hale unknown: never Arn")
add("trap", S_JPART, "What is Mira Hales city?", note="Mira Hale unknown: never Selwick")
add("trap", S_JPART, "What is Hales city?", note="surname only: never Selwick")
add("trap", S_PART, "What is Pells mother?", note="165 untaught person rel")
add("trap", S_PART, "Who is Dace's spouse?", note="unknown name with apostrophe")

# ---- outside: apostrophe twin also fails on base228 (reported only)
add("outside", S_PELL, "Hi! Who is Pells spouse?", "Orrin", note="greeting; twin fails")
add("outside", S_PELL, "Please, what is Pells pet?", "Biscuit", note="please; twin fails")
add("outside", S_PELL, "Who is Pells spouse, please?", "Orrin", note="please; twin garbles")
add("outside", S_PELL, "Is Orrin Pells spouse?", "Yes", note="yes/no; 154d parses text only")
add("outside", S_CHAIN, "Where does Pells spouse live?", "Tarn", ["Orrin"],
    note="verb + possessive; twin fails")

for i, c in enumerate(C, 1):
    c["id"] = "d247-%03d" % i
out = Path(sys.argv[1] if len(sys.argv) > 1 else
           "artifacts/claude-apos247-20260922/dev247.jsonl")
out.write_text("".join(json.dumps(c) + "\n" for c in C), encoding="utf-8")
from collections import Counter
print(out, len(C), Counter(c["family"] for c in C))
