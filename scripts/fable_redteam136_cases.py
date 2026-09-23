#!/usr/bin/env python3
"""Exp 136 -- teach-frame red-team case file (Muse). Sealed BEFORE any run.

Each case: one message through a FRESH loop129b daemon dir. Expected outcome
is fixed here, before running: either an exact triple [subject, relation,
object] or "nowrite". Nothing in this file is edited after sealing; the
runner reads cases136.json (the frozen copy) read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam136-20260922"

# (id, group, text, expectation: list triple or "nowrite")
CASES: list[tuple[str, str, str, object]] = [
    # ---- ordinary teaches: every bench73 STATEMENT_PATTERNS family ----
    ("C001", "cover", "The author of Dune is Herbert.", ["Dune", "author", "Herbert"]),
    ("C002", "cover", "The capital of Peru is Lima.", ["Peru", "capital", "Lima"]),
    ("C003", "cover", "The chairperson of Acme is Dana.", ["Acme", "chairperson", "Dana"]),
    ("C004", "cover", "The chief executive officer of Initech is Eve.", ["Initech", "chief_executive_officer", "Eve"]),
    ("C005", "cover", "The company that produced Widget is Initech.", ["Widget", "manufacturer", "Initech"]),
    ("C006", "cover", "The headquarters of Initech is located in the city of Reno.", ["Initech", "headquarters_location", "Reno"]),
    ("C007", "cover", "The name of the current head of state in Peru is Sol.", ["Peru", "head_of_state", "Sol"]),
    ("C008", "cover", "The name of the current head of the Peruvian government is Luz.", ["Peruvian", "head_of_government", "Luz"]),
    ("C009", "cover", "The official language of Peru is Spanish.", ["Peru", "official_language", "Spanish"]),
    ("C010", "cover", "The type of music that Mira plays is Jazz.", ["Mira", "genre", "Jazz"]),
    ("C011", "cover", "The univeristy where Tom was educated is Yale.", ["Tom", "educated_at", "Yale"]),
    ("C012", "cover", "Elvis died in the city of Memphis.", ["Elvis", "place_of_death", "Memphis"]),
    ("C013", "cover", "Kip Dune is a citizen of Peru.", ["Kip Dune", "country_of_citizenship", "Peru"]),
    ("C014", "cover", "Tom is affiliated with the religion of Buddhism.", ["Tom", "religion_or_worldview", "Buddhism"]),
    ("C015", "cover", "Tom is associated with the sport of Tennis.", ["Tom", "sport", "Tennis"]),
    ("C016", "cover", "Mira is famous for Belonging.", ["Mira", "notable_work", "Belonging"]),
    ("C017", "cover", "Peru is located in the continent of Atlantis.", ["Peru", "continent", "Atlantis"]),
    ("C018", "cover", "Tom is married to Ann.", ["Tom", "spouse", "Ann"]),
    ("C019", "cover", "Mira is the apprentice of Bob.", ["Mira", "apprentice_of", "Bob"]),
    ("C020", "cover", "Mira is the author of Belonging.", ["Mira", "author_of", "Belonging"]),
    ("C021", "cover", "Mira is the composer of Requiem.", ["Mira", "composer_of", "Requiem"]),
    ("C022", "cover", "Mira is the discoverer of Xray.", ["Mira", "discoverer_of", "Xray"]),
    ("C023", "cover", "Mira is the envoy of Peru.", ["Mira", "envoy_of", "Peru"]),
    ("C024", "cover", "Mira is the founder of Initech.", ["Mira", "founder_of", "Initech"]),
    ("C025", "cover", "Mira is the herald of Dawn.", ["Mira", "herald_of", "Dawn"]),
    ("C026", "cover", "Mira is the inventor of Phone.", ["Mira", "inventor_of", "Phone"]),
    ("C027", "cover", "Mira is the keeper of Keys.", ["Mira", "keeper_of", "Keys"]),
    ("C028", "cover", "Mira is the mentor of Tom.", ["Mira", "mentor_of", "Tom"]),
    ("C029", "cover", "Mira is the rival of Sue.", ["Mira", "rival_of", "Sue"]),
    ("C030", "cover", "Mira is the scout of Reno.", ["Mira", "scout_of", "Reno"]),
    ("C031", "cover", "Mira is the warden of Yale.", ["Mira", "warden_of", "Yale"]),
    ("C032", "cover", "Tom plays the position of Goalie.", ["Tom", "position_played_on_team_speciality", "Goalie"]),
    ("C033", "cover", "Tom speaks the language of French.", ["Tom", "languages_spoken_written_or_signed", "French"]),
    ("C034", "cover", "Tom was born in the city of Lyon.", ["Tom", "place_of_birth", "Lyon"]),
    ("C035", "cover", "Requiem was composed by Mozart.", ["Requiem", "composed_by", "Mozart"]),
    ("C036", "cover", "Mug was created by Ann.", ["Mug", "creator", "Ann"]),
    ("C037", "cover", "Chess was created in the country of India.", ["Chess", "country_of_origin", "India"]),
    ("C038", "cover", "Engine was developed by Initech.", ["Engine", "developer", "Initech"]),
    ("C039", "cover", "Xray was discovered by Curie.", ["Xray", "discovered_by", "Curie"]),
    ("C040", "cover", "Initech was founded by Dana.", ["Initech", "founded_by", "Dana"]),
    ("C041", "cover", "Band was founded in the city of Reno.", ["Band", "location_of_formation", "Reno"]),
    ("C042", "cover", "Phone was invented by Bell.", ["Phone", "invented_by", "Bell"]),
    ("C043", "cover", "Song was performed by Mira.", ["Song", "performer", "Mira"]),
    ("C044", "cover", "Novel was written by Hugo.", ["Novel", "written_by", "Hugo"]),
    ("C045", "cover", "Tom worked in the city of Reno.", ["Tom", "work_location", "Reno"]),
    ("C046", "cover", "The President of Peru is Sol.", ["President of Peru", "officeholder", "Sol"]),
    # ---- ordinary teaches: every bench92 EXTRA_STATEMENT_PATTERNS family ----
    ("C047", "cover", "Tom is employed by Initech.", ["Tom", "employer", "Initech"]),
    ("C048", "cover", "Tom works in the field of Medicine.", ["Tom", "occupation", "Medicine"]),
    ("C049", "cover", "Novel was written in the language of French.", ["Novel", "language_of_work_or_name", "French"]),
    ("C050", "cover", "Ann's child is Bob.", ["Ann", "child", "Bob"]),
    ("C051", "cover", "The head coach of Reno is Pat.", ["Reno", "head_coach", "Pat"]),
    ("C052", "cover", "The origianl broadcaster of Show is Nbc.", ["Show", "original_broadcaster", "Nbc"]),
    ("C053", "cover", "The director of Film is Ava.", ["Film", "director_manager", "Ava"]),
    # ---- possessive frame + natural phrasing variants (expect write) ----
    ("C054", "cover", "Mira's city is Lisbon.", ["Mira", "city", "Lisbon"]),
    ("C055", "cover", "Tom's pet is Rex", ["Tom", "pet", "Rex"]),
    ("C056", "cover", "  Tom's   city   is   Rome.  ", ["Tom", "city", "Rome"]),
    ("C057", "cover", "Dune's author is Herbert.", ["Dune", "author", "Herbert"]),
    ("C058", "cover", "Tom\u2019s city is Oslo.", ["Tom", "city", "Oslo"]),
    ("C059", "cover", "Zo\u00eb's city is Lyon.", ["Zo\u00eb", "city", "Lyon"]),
    ("C060", "cover", "Tom's city is Rome!", ["Tom", "city", "Rome"]),
    ("C061", "cover", "Tom was born in the city of Lyon in 1999.", ["Tom", "place_of_birth", "Lyon"]),
    ("C062", "cover", "Tom's city is Rome since 1999.", ["Tom", "city", "Rome"]),
    # ---- chit-chat and opinions (must NOT write) ----
    ("C063", "chit", "The weather is nice.", "nowrite"),
    ("C064", "chit", "I think Tom is tired.", "nowrite"),
    ("C065", "chit", "Ann is happy today.", "nowrite"),
    ("C066", "chit", "Tom is tired.", "nowrite"),
    ("C067", "chit", "The movie was great.", "nowrite"),
    ("C068", "chit", "I like pizza.", "nowrite"),
    ("C069", "chit", "Tom is the best.", "nowrite"),
    ("C070", "chit", "The meeting is at noon.", "nowrite"),
    # ---- negations (must NOT write) ----
    ("C071", "neg", "Tom is not a citizen of Peru.", "nowrite"),
    ("C072", "neg", "Mira's city is not Lisbon.", "nowrite"),
    ("C073", "neg", "Tom was not born in Lyon.", "nowrite"),
    ("C074", "neg", "Ann is never late.", "nowrite"),
    ("C075", "neg", "The capital of Peru is not Lima.", "nowrite"),
    # ---- questions phrased like statements (must NOT write) ----
    ("C076", "q", "Is Tom French?", "nowrite"),
    ("C077", "q", "Tom's boss is Bob?", "nowrite"),
    ("C078", "q", "Who is Tom's boss", "nowrite"),
    ("C079", "q", "What is the capital of Peru.", "nowrite"),
    ("C080", "q", "Tom is French, isn't he.", "nowrite"),
    # ---- hedges (must NOT write) ----
    ("C081", "hedge", "Maybe Tom's boss is Ann.", "nowrite"),
    ("C082", "hedge", "Tom's boss is probably Ann.", "nowrite"),
    ("C083", "hedge", "I think Tom's city is Rome.", "nowrite"),
    ("C084", "hedge", "Tom might be French.", "nowrite"),
    ("C085", "hedge", "Perhaps the capital of Peru is Lima.", "nowrite"),
    ("C086", "hedge", "Tom's city is maybe Rome.", "nowrite"),
    # ---- hypotheticals (must NOT write) ----
    ("C087", "hyp", "If Tom were French, Ann would be happy.", "nowrite"),
    ("C088", "hyp", "If Mira's city were Lisbon, Tom would visit.", "nowrite"),
    ("C089", "hyp", "Suppose Tom's boss is Ann.", "nowrite"),
    ("C090", "hyp", "Imagine the capital of Peru is Lima.", "nowrite"),
    ("C091", "hyp", "What if Tom's city is Rome.", "nowrite"),
    # ---- plural / compound subjects (must NOT write) ----
    ("C092", "plur", "Tom and Ann are citizens of Peru.", "nowrite"),
    ("C093", "plur", "Tom's cities are Rome and Paris.", "nowrite"),
    ("C094", "plur", "Mira's city is Lisbon and Tom's pet is Rex.", "nowrite"),
    ("C095", "plur", "Tom's boss is Bob and Ann's boss is Sue.", "nowrite"),
    ("C096", "plur", "The capital of Peru is Lima; the capital of Chile is Santiago.", "nowrite"),
    ("C097", "plur", "Tom, Ann and Sue are friends.", "nowrite"),
    # ---- reported speech (must NOT write) ----
    ("C098", "rep", "Ann said Tom's boss is Bob.", "nowrite"),
    ("C099", "rep", "Tom's boss is Bob, Ann said.", "nowrite"),
    ("C100", "rep", "According to Ann, Tom's city is Rome.", "nowrite"),
    ("C101", "rep", "I heard Tom's city is Rome.", "nowrite"),
    ("C102", "rep", "Apparently Tom is French.", "nowrite"),
    ("C103", "rep", "Tom's teacher is Ann, reportedly.", "nowrite"),
    # ---- corrections (expect write) ----
    ("C104", "corr", "No, Tom's city is Rome.", ["Tom", "city", "Rome"]),
    ("C105", "corr", "Actually, the capital of Peru is Lima.", ["Peru", "capital", "Lima"]),
    ("C106", "corr", "Sorry, I meant Mira's pet is Rex.", ["Mira", "pet", "Rex"]),
    ("C107", "corr", "Correction: Ann is married to Bob.", ["Ann", "spouse", "Bob"]),
    # ---- numbers / dates / names as values (expect write) ----
    ("C108", "val", "Tom's code is 42.", ["Tom", "code", "42"]),
    ("C109", "val", "Tom's birthday is 1999.", ["Tom", "birthday", "1999"]),
    ("C110", "val", "Tom's title is King of Rome.", ["Tom", "title", "King of Rome"]),
    ("C111", "val", "Tom's city is rome.", ["Tom", "city", "rome"]),
    ("C112", "val", "The headquarters of Initech is located in the city of Washington, D.C..", ["Initech", "headquarters_location", "Washington, D.C."]),
    ("C113", "val", "Mary Ann's child is Bob.", ["Mary Ann", "child", "Bob"]),
    # ---- lower-case entry (expect write: case must not break a teach) ----
    ("C114", "low", "tom's city is rome.", ["tom", "city", "rome"]),
    ("C115", "low", "the capital of peru is lima.", ["peru", "capital", "lima"]),
    ("C116", "low", "mira is married to bob.", ["mira", "spouse", "bob"]),
    # ---- trailing emoji (expect CLEAN triple: emoji is not part of the value) ----
    ("C117", "emo", "Tom's city is Rome \U0001f600", ["Tom", "city", "Rome"]),
    ("C118", "emo", "The capital of Peru is Lima \U0001f389", ["Peru", "capital", "Lima"]),
    ("C119", "emo", "Mira is married to Bob \u2764\ufe0f", ["Mira", "spouse", "Bob"]),
    # ---- multiple sentences in one message (must NOT write) ----
    ("C120", "multi", "Tom's city is Rome. Ann's city is Paris.", "nowrite"),
    ("C121", "multi", "The capital of Peru is Lima. It is sunny.", "nowrite"),
    ("C122", "multi", "Hi. Tom's boss is Ann.", "nowrite"),
    ("C123", "multi", "Tom's city is Rome. Thanks!", "nowrite"),
    # ---- already-known bugs: one case each to confirm (excluded from novelty) ----
    ("C124", "known", "The mother of Ann is Sue.", "nowrite"),
    ("C125", "known", "Dara Fenn's city is Lyon.", ["Dara Fenn", "city", "Lyon"]),
    ("C126", "known", "Kip Dune is a citizen of Peru.\"", ["Kip Dune", "country_of_citizenship", "Peru"]),
    # ---- misc adversarial ----
    ("C127", "misc", "The father of Bob is Ted.", "nowrite"),
    ("C128", "misc", "The CEO of Initech is Eve.", "nowrite"),
    ("C129", "misc", "The boss of Tom is Ann.", "nowrite"),
    ("C130", "misc", "Mary Kay's pet is Rex.", ["Mary Kay", "pet", "Rex"]),
    ("C131", "misc", "\"The capital of Peru is Lima.\"", ["Peru", "capital", "Lima"]),
    ("C132", "misc", "Tom's city is 'Rome'.", ["Tom", "city", "Rome"]),
    ("C133", "misc", "Tom's boss's boss is Ann.", "nowrite"),
    ("C134", "misc", "Dune's author is Herbert.", ["Dune", "author", "Herbert"]),
    ("C135", "misc", "Tom is a citizen of Peru and Ann.", "nowrite"),
    ("C136", "misc", "Tom's boss is Ann and Sue.", "nowrite"),
    ("C137", "misc", "Tom's city is.", "nowrite"),
    ("C138", "misc", "Tom's mood is ...", "nowrite"),
    ("C139", "misc", "   ", "nowrite"),
    ("C140", "misc", "Tom's city is Washington, D.C..", ["Tom", "city", "Washington, D.C."]),
    ("C141", "misc", "Tom's friends are Ann and Sue.", "nowrite"),
    ("C142", "misc", "THE CAPITAL OF PERU IS LIMA.", "nowrite"),
    ("C143", "misc", "Tom's city is Rome!!!", ["Tom", "city", "Rome"]),
    ("C144", "misc", "Tom's boss is Ann and Sue are friends.", "nowrite"),
    ("C145", "misc", "Ann's child is Bob!", ["Ann", "child", "Bob"]),
]


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    rows = [{"id": cid, "group": grp, "text": txt,
             "expect": exp} for cid, grp, txt, exp in CASES]
    assert len(rows) >= 120, len(rows)
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), "duplicate case ids"
    out = ART / "cases136.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {out} ({len(rows)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
