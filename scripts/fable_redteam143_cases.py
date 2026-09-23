#!/usr/bin/env python3
"""Exp 143 -- QUESTION-side red team vs loop132: sealed case generator.

Writes artifacts/fable-redteam143-20260922/fable_redteam143_cases.json
(122 FRESH cases + 2 confirm cases, all invented names, expectations from
first principles -- never probed against the code).

Each case: 2-6 teach sentences in supported frames (no trailing periods,
Title-Case values, no qualifiers/hearsay) + one question + expected outcome
("abstain" or the exact answer string).

Confirm cases (excluded from the novelty count): A (doc124 finding 1,
broken-chain prefix), B (doc124 finding 2, qualifier passthrough).

Run (prep only; the registered RUN happens after sealing):
  python3 scripts/fable_redteam143_cases.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam143-20260922"

ABSTAIN_MARKERS = [
    "don't know",
    "not someone",
    "which one do you mean",
    "didn't understand",
    "could you say",
    "was that a question?",
    "split that",
    "only follow",
    "do you know that yourself",
    "didn't catch",
    "please say it like",
    "couldn't read",
    "only handle one-word",
    "could not use that",
    "didn't get the value",
    "not allowed",
    "do you want me to change",
    "i didn't catch anything",
    "i can take one fact at a time",
    "i only save facts",
    "i wasn't waiting for an answer",
]

CASES: list[dict] = []


def case(cid, family, teaches, question, expected, note="", confirm=False):
    CASES.append({
        "id": cid, "family": family, "teaches": list(teaches),
        "question": question, "expected": expected, "note": note,
        "confirm": bool(confirm),
    })


# ---- A/B: confirm cases (excluded from novelty count) ----
case("A1", "confirm-broken-prefix",
     ["Bram Kite is a citizen of Norland",
      "Tomas Reed is associated with the sport of curling"],
     "What is the official language of the country of citizenship of Bram Kite?",
     "abstain", "doc124 finding 1: walked prefix Norland must not be answered",
     confirm=True)
case("B1", "confirm-qualifier",
     ["Cora Lind is a citizen of Norland",
      "The official language of Norland is Meridian"],
     "What is the official language of the country of citizenship of Cora Lind as of 2020?",
     "abstain", "doc124 finding 2: qualifier must block the composer",
     confirm=True)

# ---- C: 1-hop canonical + basic (expected answers) ----
case("C1", "one-hop", ["Bram Kite is married to Cora Lind"],
     "Who is Bram Kite married to?", "Cora Lind")
case("C2", "one-hop", ["The capital of Norland is Aldport"],
     "What's the capital of Norland?", "Aldport")
case("C3", "one-hop", ["Cora Lind is a citizen of Norland"],
     "What country is Cora Lind a citizen of?", "Norland")
case("C4", "one-hop", ["The author of The Glass Orchard is Bram Kite"],
     "Who wrote The Glass Orchard?", "Bram Kite")
case("C5", "one-hop", ["Bram Kite is famous for The Glass Orchard"],
     "What is Bram Kite famous for?", "The Glass Orchard")
case("C6", "one-hop", ["Bram Kite was born in the city of Dunmere"],
     "Where was Bram Kite born?", "Dunmere")

# ---- D: 2-hop possessive chains (12) ----
case("D1", "two-hop", ["Cora Lind is a citizen of Norland",
                       "The capital of Norland is Aldport"],
     "What is the capital of the country Cora Lind is a citizen of?", "Aldport")
case("D2", "two-hop", ["Cora Lind is a citizen of Norland",
                       "The capital of Norland is Aldport"],
     "What is Cora Lind's country's capital?", "Aldport",
     note="possessive country's: 'country of' cue absent, coverage probe")
case("D3", "two-hop", ["Cora Lind is a citizen of Norland",
                       "The capital of Norland is Aldport"],
     "Which city is the capital of the nation Cora Lind holds citizenship in?",
     "Aldport")
case("D4", "two-hop", ["The author of The Glass Orchard is Bram Kite",
                       "Bram Kite is married to Cora Lind"],
     "Who is the author of The Glass Orchard married to?", "Cora Lind")
case("D5", "two-hop", ["Tomas Reed is employed by Harborline",
                       "The headquarters of Harborline is located in the city of Dunmere"],
     "Where is the headquarters of the company that employs Tomas Reed located?",
     "Dunmere")
case("D6", "two-hop", ["Nadia Frost is employed by Harborline",
                       "Harborline was founded in the city of Dunmere"],
     "Where was the company that employs Nadia Frost founded?", "Dunmere")
case("D7", "two-hop", ["Bram Kite's child is Cora Lind",
                       "Cora Lind is a citizen of Norland"],
     "What country is the child of Bram Kite a citizen of?", "Norland")
case("D8", "two-hop", ["The type of music that Harborlight Choir plays is choral music",
                       "choral music was created in the country of Veldoria"],
     "What country was the music played by Harborlight Choir created in?",
     "Veldoria")
case("D9", "two-hop", ["Tomas Reed is associated with the sport of curling",
                       "curling was created in the country of Veldoria"],
     "What country was the sport associated with Tomas Reed created in?",
     "Veldoria")
case("D10", "two-hop", ["Bram Kite died in the city of Dunmere",
                        "Dunmere is located in the continent of Australis"],
     "What continent is the city where Bram Kite died located in?", "Australis")
case("D11", "two-hop", ["Bram Kite was born in the city of Dunmere",
                        "Dunmere is located in the continent of Australis"],
     "What continent was Bram Kite born in?", "Australis")
case("D12", "two-hop", ["Sunmosaic was created by Yara Haddad",
                        "Yara Haddad is married to Zev Carlton"],
     "Who is the creator of Sunmosaic married to?", "Zev Carlton")

# ---- E: 3-hop (8) ----
E3 = ["Bram Kite is married to Cora Lind",
      "Cora Lind is a citizen of Norland",
      "The capital of Norland is Aldport"]
case("E1", "three-hop", E3,
     "What is the capital of the country of citizenship of the person married to Bram Kite?",
     "Aldport")
case("E2", "three-hop", E3,
     "What is the capital of the country of citizenship of Bram Kite's spouse?",
     "Aldport")
case("E3", "three-hop", E3,
     "Which city is the capital of the nation whose citizenship is held by the wife of Bram Kite?",
     "Aldport", note="whose present but chain intact: answer expected")
case("E4", "three-hop", ["Moonchant was performed by Petra Voss",
                         "Petra Voss is a citizen of Veldoria",
                         "The capital of Veldoria is Dunmere"],
     "What is the capital of the country of citizenship of the performer of Moonchant?",
     "Dunmere")
case("E5", "three-hop", ["HarborOS was developed by Ivo Brandt",
                         "Ivo Brandt is employed by Harborline",
                         "The headquarters of Harborline is located in the city of Dunmere"],
     "Where is the headquarters of the company employing the developer of HarborOS located?",
     "Dunmere")
case("E6", "three-hop", ["Harborline was founded by Ada Wren",
                         "Ada Wren is married to Nils Berger",
                         "Nils Berger is a citizen of Ostmark"],
     "What country is the spouse of the founder of Harborline a citizen of?",
     "Ostmark")
case("E7", "three-hop", ["The company that produced Seaglider is Harborline",
                         "Harborline was founded in the city of Dunmere",
                         "Dunmere is located in the continent of Australis"],
     "What continent is the city where the producer of Seaglider was founded located in?",
     "Australis")
case("E8", "three-hop", ["The univeristy where Ivo Brandt was educated is Harbor Academy",
                         "Harbor Academy was founded in the city of Dunmere",
                         "Dunmere is located in the continent of Australis"],
     "What continent is the city where the university where Ivo Brandt was educated was founded located in?",
     "Australis")

# ---- F: 4-hop (6) ----
F1W = ["The author of The Glass Orchard is Yara Haddad",
       "Yara Haddad is married to Nils Berger",
       "Nils Berger is a citizen of Ostmark",
       "The capital of Ostmark is Norhaven"]
case("F1", "four-hop", F1W,
     "What is the capital of the country of citizenship of the spouse of the author of The Glass Orchard?",
     "Norhaven")
case("F2", "four-hop", F1W,
     "What is the capital of the country where the spouse of the author of The Glass Orchard holds citizenship?",
     "Norhaven")
case("F3", "four-hop", F1W,
     "The author of The Glass Orchard married whom, and what is the capital of the country of citizenship of that spouse?",
     "Norhaven")
case("F4", "four-hop", ["Bram Kite is married to Cora Lind",
                        "Cora Lind's child is Emil Sorrel",
                        "Emil Sorrel is a citizen of Norland",
                        "The capital of Norland is Aldport"],
     "What is the capital of the country of citizenship of the child of the spouse of Bram Kite?",
     "Aldport")
case("F5", "four-hop", ["Moonchant was performed by Harborlight Choir",
                        "The director of Harborlight Choir is Petra Voss",
                        "Petra Voss is a citizen of Veldoria",
                        "The capital of Veldoria is Dunmere"],
     "What is the capital of the country of citizenship of the director of the performer of Moonchant?",
     "Dunmere", note="compound officeholder island: needs the loop132 rewriter")
case("F6", "four-hop-island-prefix", ["Moonchant was performed by Harborlight Choir",
                                      "The director of Harborlight Choir is Petra Voss"],
     "Who is the director of the performer of Moonchant?",
     "abstain", note="island boundary: walked prefix must not answer the director question")

# ---- G: of-the-of phrasing (6), expected answers ----
case("G1", "of-phrasing", ["Cora Lind is a citizen of Norland",
                           "The official language of Norland is Meridian"],
     "What is the official language of the country of citizenship of Cora Lind?",
     "Meridian")
case("G2", "of-phrasing", ["The author of The Glass Orchard is Bram Kite",
                           "Bram Kite is married to Cora Lind"],
     "Who is the spouse of the author of The Glass Orchard?", "Cora Lind")
case("G3", "of-phrasing", ["Bram Kite died in the city of Dunmere",
                           "Dunmere is located in the continent of Australis"],
     "What is the continent of the city where Bram Kite died?", "Australis")
case("G4", "of-phrasing", ["The company that produced Seaglider is Harborline",
                           "Harborline was founded by Ada Wren"],
     "Who is the founder of the company that produced Seaglider?", "Ada Wren")
case("G5", "of-phrasing", ["The author of The Glass Orchard is Bram Kite",
                           "Bram Kite speaks the language of Meridian"],
     "What language does the author of The Glass Orchard speak?", "Meridian")
case("G6", "of-phrasing", ["The name of the current head of state in Norland is Ivo Brandt",
                           "Ivo Brandt is married to Lena Marsh"],
     "Who is the head of state of Norland married to?", "Lena Marsh")

# ---- H: relative clauses (8) ----
case("H1", "relative-clause", E3,
     "What is the capital of the country where the person who is married to Bram Kite holds citizenship?",
     "Aldport")
case("H2", "relative-clause", ["Bram Kite is famous for The Glass Orchard",
                               "The author of The Glass Orchard is Yara Haddad"],
     "Who is the person that wrote the book that Bram Kite is famous for?",
     "Yara Haddad")
case("H3", "relative-clause", ["Harborline was founded by Ada Wren",
                               "Ada Wren is a citizen of Ostmark"],
     "What is the name of the country where the woman who founded Harborline lives?",
     "Ostmark", note="lives is not a citizenship cue: coverage probe")
case("H4", "relative-clause", ["The company that produced Seaglider is Harborline",
                               "Harborline was founded by Ada Wren",
                               "Ada Wren is a citizen of Ostmark",
                               "The capital of Ostmark is Norhaven"],
     "Which city is the capital of the country that the founder of the company that produced Seaglider calls home?",
     "Norhaven", note="calls home needs the rewriter evidence map")
case("H5", "relative-clause", ["Cora Lind is a citizen of Norland",
                               "The official language of Norland is Meridian",
                               "Bram Kite is married to Cora Lind"],
     "What is the official language of the country that Cora Lind, who is married to Bram Kite, is a citizen of?",
     "abstain", note="two mentioned entities: single-start walk cannot run")
case("H6", "relative-clause", ["Cora Lind is a citizen of Norland",
                               "The capital of Norland is Aldport"],
     "What is the capital of the country of citizenship of the man who is married to Cora Lind?",
     "Aldport", note="reverse description, same sink from the mentioned entity")
case("H7", "relative-clause", ["HarborOS was developed by Ivo Brandt",
                               "The univeristy where Ivo Brandt was educated is Harbor Academy"],
     "Where was the developer of HarborOS educated?", "Harbor Academy")
case("H8", "relative-clause", ["The author of The Glass Orchard is Bram Kite",
                               "Bram Kite was born in the city of Dunmere"],
     "What is the name of the city where the author of The Glass Orchard was born?",
     "Dunmere")

# ---- I: passive (5), expected answers ----
case("I1", "passive", ["The author of The Glass Orchard is Bram Kite"],
     "By whom was The Glass Orchard written?", "Bram Kite")
case("I2", "passive", ["Moonchant was performed by Petra Voss"],
     "By whom was Moonchant performed?", "Petra Voss")
case("I3", "passive", ["Harborline was founded by Ada Wren"],
     "By whom was Harborline founded?", "Ada Wren")
case("I4", "passive", ["Bram Kite was born in the city of Dunmere"],
     "In which city was Bram Kite born?", "Dunmere")
case("I5", "passive", ["Sunmosaic was created in the country of Veldoria"],
     "In which country was Sunmosaic created?", "Veldoria")

# ---- J: robust phrasing (12) ----
case("J1", "robust", ["The capital of Norland is Aldport"],
     "What's the capital of Norland?", "Aldport")
case("J2", "robust", ["The capital of Norland is Aldport"],
     "Tell me the capital of Norland, please?", "Aldport")
case("J3", "robust", ["Bram Kite is married to Cora Lind"],
     "Do you know who Bram Kite is married to?", "Cora Lind")
case("J4", "robust", ["Bram Kite is married to Cora Lind"],
     "who is bram kite married to?", "Cora Lind")
case("J5", "robust", ["The capital of Norland is Aldport"],
     "What is the capital of Norland", "Aldport",
     note="no question mark: teach path, likely MISSED")
case("J6", "robust", ["The capital of Norland is Aldport"],
     "What   is  the capital   of Norland?", "Aldport")
case("J7", "robust", ["The capital of Norland is Aldport"],
     "Please tell me, what is the capital of Norland?", "Aldport")
case("J8", "robust", ["The capital of Norland is Aldport"],
     "What is the capital of Norlanb?", "Aldport",
     note="one-letter entity typo: mention miss, likely MISSED")
case("J9", "robust", ["The capital of Norland is Aldport"],
     "What is the capitol of Norland?", "Aldport",
     note="relation typo: cue miss, likely MISSED")
case("J10", "robust", ["Bram Kite is married to Cora Lind"],
     "Tell me who Bram Kite is married to", "Cora Lind",
     note="tell-me without question mark: likely MISSED")
case("J11", "robust", ["Cora Lind is a citizen of Norland"],
     "Could you please tell me what country Cora Lind is a citizen of?", "Norland")
case("J12", "robust", ["The capital of Norland is Aldport"],
     "WHAT IS THE CAPITAL OF NORLAND?", "Aldport")

# ---- K: answer never taught (10), expect abstain ----
case("K1", "never-taught", ["Bram Kite is married to Cora Lind"],
     "What country is Bram Kite a citizen of?", "abstain")
case("K2", "never-taught", ["Cora Lind is a citizen of Norland",
                            "The capital of Norland is Aldport"],
     "What is the official language of Norland?", "abstain")
case("K3", "never-taught", ["The author of The Glass Orchard is Bram Kite"],
     "What is Bram Kite famous for?", "abstain")
case("K4", "never-taught", ["Cora Lind is a citizen of Norland"],
     "Who is Cora Lind married to?", "abstain")
case("K5", "never-taught", ["Bram Kite is married to Cora Lind"],
     "Where was Bram Kite born?", "abstain")
case("K6", "never-taught", ["HarborOS was created in the country of Veldoria"],
     "Who developed HarborOS?", "abstain",
     note="developed cues origin too: wh-word/relation mismatch hunt")
case("K7", "never-taught", ["Ada Wren is married to Nils Berger"],
     "What did Ada Wren found?", "abstain")
case("K8", "never-taught", ["The author of The Glass Orchard is Bram Kite"],
     "Who is the spouse of the author of The Glass Orchard?", "abstain",
     note="Bram is a chain-end sink: prefix hunt")
case("K9", "never-taught", ["The capital of Norland is Aldport"],
     "What is the capital of Ostmark?", "abstain")
case("K10", "never-taught", ["Sunmosaic was created by Yara Haddad"],
     "What country was Sunmosaic created in?", "abstain",
     note="created cues creator too: answer-type mismatch hunt")

# ---- L: unknown relations (6), expect abstain ----
case("L1", "unknown-relation", ["Bram Kite is married to Cora Lind"],
     "What is Bram Kite's occupation?", "abstain")
case("L2", "unknown-relation", ["Cora Lind is a citizen of Norland"],
     "Who employs Cora Lind?", "abstain")
case("L3", "unknown-relation", ["Tomas Reed is associated with the sport of curling"],
     "What team does Tomas Reed play for?", "abstain")
case("L4", "unknown-relation", ["Bram Kite is married to Cora Lind"],
     "Who employs the person married to Bram Kite?", "abstain",
     note="doc124-U3 shape: employs never taught, spouse walk covered")
case("L5", "unknown-relation", ["Bram Kite is married to Cora Lind"],
     "What is the religion of Bram Kite?", "abstain")
case("L6", "unknown-relation", ["Bram Kite is married to Cora Lind"],
     "When was Bram Kite born?", "abstain")

# ---- M: yes/no (6) ----
case("M1", "yes-no", ["Bram Kite is married to Cora Lind"],
     "Is Bram Kite married to Sella Marne?", "Cora Lind",
     note="false premise, Sella untaught: best response states the fact")
case("M2", "yes-no", ["Bram Kite is a citizen of Norland"],
     "Is Bram Kite a citizen of Veltria?", "Norland",
     note="false premise, Veltria untaught: best response states the fact")
case("M3", "yes-no", ["Cora Lind is a citizen of Norland",
                      "The capital of Norland is Aldport"],
     "Is Aldport the capital of Norland?", "abstain",
     note="two mentioned entities: no yes/no frame, must abstain")
case("M4", "yes-no", ["Bram Kite is married to Cora Lind"],
     "Is Bram Kite a citizen of Norland?", "abstain",
     note="citizenship never taught, Norland untaught")
case("M5", "yes-no", ["Bram Kite is married to Cora Lind"],
     "Is Bram Kite married to Cora Lind?", "abstain",
     note="true premise but two mentions: no yes/no frame, must abstain")
case("M6", "yes-no", ["Bram Kite is married to Cora Lind"],
     "Is Vera Quinn married to Jonas Pike?", "abstain",
     note="neither entity taught")

# ---- N: negated (5), expect abstain ----
case("N1", "negated", ["Bram Kite is married to Cora Lind"],
     "Who is not married to Bram Kite?", "abstain",
     note="no negation frame: not must block")
case("N2", "negated", ["Cora Lind is a citizen of Norland"],
     "Which country is Cora Lind not a citizen of?", "abstain")
case("N3", "negated", ["The capital of Norland is Aldport"],
     "What is not the capital of Norland?", "abstain")
case("N4", "negated", ["Cora Lind is a citizen of Norland",
                       "The capital of Norland is Aldport"],
     "What is not the capital of the country Cora Lind is a citizen of?",
     "abstain")
case("N5", "negated", ["The author of The Glass Orchard is Bram Kite"],
     "Who is not the author of The Glass Orchard?", "abstain")

# ---- O: unknown entity (5), expect abstain ----
case("O1", "unknown-entity", E3,
     "What is the capital of the country Vera Quinn is a citizen of?", "abstain")
case("O2", "unknown-entity", ["Bram Kite is married to Cora Lind"],
     "Who is Jonas Pike married to?", "abstain")
case("O3", "unknown-entity", ["The capital of Norland is Aldport"],
     "What is the capital of Norlandia?", "abstain",
     note="Norland is a substring of Norlandia: entity-resolution hunt")
case("O4", "unknown-entity", ["Bram Kite is married to Cora Lind"],
     "What country is Vera Quinn a citizen of?", "abstain")
case("O5", "unknown-entity", ["Bram Kite is married to Cora Lind"],
     "Is Dunmere the capital of Ostmark?", "abstain")

# ---- P: look-alike names (5) ----
PW = ["Dara Fenn is a citizen of Litora",
      "The capital of Litora is Fellport",
      "Dara Fenner is a citizen of Cardova",
      "The capital of Cardova is Port Riva"]
case("P1", "look-alike", PW,
     "What country is Dara Fenn a citizen of?", "Litora")
case("P2", "look-alike", PW,
     "What country is Dara Fenner a citizen of?", "Cardova")
case("P3", "look-alike", PW,
     "What is the capital of the country Dara Fenn is a citizen of?", "Fellport")
case("P4", "look-alike", PW,
     "What is the capital of the country Dara Fenner is a citizen of?", "Port Riva")
case("P5", "look-alike", PW,
     "Who is Dara Fenner?", "abstain",
     note="bare who-is with no relation cue: must abstain")

# ---- Q: post-correction (7) ----
QAW = ["Joren Hale is married to Sella Marne",
       "Sella Marne is a citizen of Tormeil",
       "The capital of Tormeil is Northgate",
       "Actually, Joren Hale is married to Petra Voss",
       "Petra Voss is a citizen of Veldoria",
       "The capital of Veldoria is Dunmere"]
case("Q1", "post-correction", QAW,
     "Who is Joren Hale married to?", "Petra Voss")
case("Q2", "post-correction", QAW,
     "What country is Sella Marne a citizen of?", "Tormeil",
     note="correction of Joren must not erase Sella's own fact")
case("Q3", "post-correction", QAW,
     "What is the capital of the country of citizenship of the person married to Joren Hale?",
     "Dunmere", note="2-hop through the corrected value")
case("Q4", "post-correction", QAW,
     "What is the capital of the country of citizenship of Sella Marne?",
     "Northgate")
case("Q5", "post-correction", ["Tomas Reed is married to Hana Okafor",
                               "No, Tomas Reed is married to Greta Moss"],
     "Who is Tomas Reed married to?", "Greta Moss",
     note="No-prefix correction")
case("Q6", "post-correction", ["Tomas Reed is married to Hana Okafor",
                               "Correction: Tomas Reed is married to Greta Moss"],
     "Who is Tomas Reed married to?", "Greta Moss",
     note="Correction-prefix correction")
case("Q7", "post-correction", ["Tomas Reed is married to Hana Okafor",
                               "Actually, Tomas Reed is married to Greta Moss"],
     "Who is Hana Okafor married to?", "abstain",
     note="old object has no outgoing facts")

# ---- S: ambiguity / branch / loop (5) ----
case("S1", "ambiguity", ["Bram Kite is married to Cora Lind",
                         "Bram Kite is a citizen of Norland",
                         "The capital of Norland is Aldport"],
     "What is the capital of the country Bram Kite is a citizen of?", "abstain",
     note="Bram has two outgoing relations: walk must stop")
case("S2", "ambiguity", ["Mira Sol is married to Cora Lind",
                         "Mira Solis is married to Petra Voss"],
     "Who is Mira Sol married to?", "Cora Lind")
case("S3", "ambiguity", ["Mira Sol is married to Cora Lind",
                         "Mira Solis is married to Petra Voss"],
     "Who is Mira Solis married to?", "Petra Voss",
     note="Mira Sol is a substring: longest match must win")
case("S4", "ambiguity", ["Mira Sol is married to Cora Lind",
                         "Cora Lind is a citizen of Norland",
                         "Mira Solis is married to Petra Voss",
                         "Petra Voss is a citizen of Veldoria"],
     "What is the capital of the country of citizenship of the person married to Mira Solis?",
     "abstain", note="capital never taught: prefix Veldoria must not answer")
case("S5", "ambiguity", ["Bram Kite is married to Cora Lind",
                         "Cora Lind is married to Bram Kite"],
     "Who is Bram Kite married to?", "abstain",
     note="2-cycle: loop guard must abstain, not spin or prefix-answer")

# ---- T: qualifier / whose / extra relation (5), expect abstain ----
case("T1", "qualifier", ["Bram Kite is married to Cora Lind"],
     "Who is Bram Kite married to in 2019?", "abstain")
case("T2", "qualifier", ["Cora Lind is a citizen of Norland",
                         "The capital of Norland is Aldport"],
     "Whose capital is Aldport, the capital of the country Cora Lind is a citizen of?",
     "abstain", note="two mentions plus whose: must abstain")
case("T3", "qualifier", E3,
     "What is the occupation of the person married to Bram Kite?", "abstain",
     note="occupation never taught and blocks the gate")
case("T4", "qualifier", ["Bram Kite is married to Cora Lind"],
     "Who employs the person married to Bram Kite?", "abstain",
     note="employs never taught but gate-covered: U3-shape hunt")
case("T5", "qualifier", ["Bram Kite is married to Cora Lind"],
     "Who is Bram Kite married to as of last Tuesday?", "abstain")

# ---- U: chain-end missing (5), expect abstain ----
case("U1", "chain-end", ["Bram Kite is married to Cora Lind"],
     "What country is the spouse of Bram Kite a citizen of?", "abstain")
case("U2", "chain-end", ["Bram Kite is a citizen of Norland"],
     "What is the capital of the country Bram Kite is a citizen of?", "abstain")
case("U3", "chain-end", ["Bram Kite is married to Cora Lind",
                         "Cora Lind is a citizen of Norland"],
     "What is the official language of the country of citizenship of the spouse of Bram Kite?",
     "abstain")
case("U4", "chain-end", ["Bram Kite is married to Cora Lind",
                         "The capital of Norland is Aldport"],
     "What is the capital of the country of citizenship of the person married to Bram Kite?",
     "abstain", note="middle hop never taught: gap prefix hunt")
case("U5", "chain-end", ["Bram Kite is married to Cora Lind",
                         "Cora Lind is a citizen of Norland"],
     "What is the capital of the country of citizenship of the person married to Bram Kite?",
     "abstain")


def main() -> int:
    # Pad single-teach worlds to the brief's 2-5 sentences with a disconnected
    # fact whose entities appear in no question and no other teach.
    PAD = "Wren Padder worked in the city of Millhaven"
    for c in CASES:
        if len(c["teaches"]) == 1:
            c["teaches"].append(PAD)
    fresh = [c for c in CASES if not c["confirm"]]
    assert len(fresh) >= 120, f"only {len(fresh)} fresh cases"
    assert len(CASES) == len(fresh) + 2
    # sanity: every teach non-empty, no trailing ?, question ends with ? except J5/J10
    for c in CASES:
        assert 2 <= len(c["teaches"]) <= 6, c["id"]
        for t in c["teaches"]:
            assert t and not t.rstrip().endswith("?"), c["id"]
            assert t == " ".join(t.split()), c["id"]
        if c["id"] not in ("J5", "J10"):
            assert c["question"].rstrip().endswith("?"), c["id"]
    ART.mkdir(parents=True, exist_ok=True)
    out = {"abstain_markers": ABSTAIN_MARKERS, "cases": CASES,
           "n_fresh": len(fresh), "n_confirm": len(CASES) - len(fresh)}
    (ART / "fable_redteam143_cases.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(CASES)} cases ({len(fresh)} fresh + 2 confirm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
