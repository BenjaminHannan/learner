#!/usr/bin/env python3
"""Blind TEST-ONLY panel writer for exp 270 (casual typing).

Writes artifacts/claude-typepanel270-20260923/panel.jsonl deterministically
and runs self-checks. Blind: written from handoff/kit/briefs/earpanel264-spec.txt
format only ({id, family, turn, gold, clear, notes}). No code, relation tables,
training data, results, or other panels were read. Fictional names only.

Families (100 turns, ids t270-001..t270-100 in family-block order):
- casual 40: facts typed casually: all lowercase, missing possessive
  apostrophes, no final punctuation on most (8 end with a period).
  Gold TEACH frames use correctly capitalised names.
- casual_q 15: lowercase questions about facts, no "?". Gold ASK frames
  use correctly capitalised names, chain null, chain_aliases null.
- lower_trap 15: lowercase turns where a capitalised-looking word is NOT a
  name (boss, rose, may, frank, bill, grace, robin, april, hope, faith,
  mark, chase). Gold holds only the real fact, or [] when there is none.
- clean 30: normal well-typed facts (20, end ".") and questions (10, end "?").
  Control; must be unchanged (gold mirrors the turn exactly).

Gold convention: subject/value "me" stands for the speaker. Every other
subject/value is the canonical correctly-capitalised span, matched to the turn
case-insensitively (whole words) by the self-check below.
"""

import json
import os

OUT_DIR = "artifacts/claude-typepanel270-20260923"
PANEL_PATH = os.path.join(OUT_DIR, "panel.jsonl")

ALIASES = {
    "pet": ["pet", "animal", "companion"],
    "city": ["city", "town", "residence"],
    "job": ["job", "occupation", "profession"],
    "boss": ["boss", "manager", "supervisor"],
    "sister": ["sister", "sibling"],
    "brother": ["brother", "sibling"],
    "spouse": ["spouse", "wife", "husband", "partner"],
    "language": ["language", "tongue"],
    "school": ["school", "college"],
    "employer": ["employer", "company"],
    "neighbour": ["neighbour", "neighbor"],
    "hometown": ["hometown", "home town"],
    "mother": ["mother", "mum"],
    "father": ["father", "dad"],
}


def TEACH(subject, relation, value, species=None):
    aliases = list(ALIASES[relation])
    if species:
        aliases = aliases + [species]
    return {
        "act": "TEACH",
        "subject": subject,
        "relation": relation,
        "relation_aliases": aliases,
        "value": value,
    }


def ASK(subject, relation):
    return {
        "act": "ASK",
        "subject": subject,
        "relation": relation,
        "chain": None,
        "relation_aliases": list(ALIASES[relation]),
        "chain_aliases": None,
    }


# (family, turn, gold, clear, notes)
ITEMS = [
    # ---- casual 40 (t270-001..040): all lowercase, no apostrophes ----
    ("casual", "anas cat is fig", [TEACH("Ana", "pet", "Fig", "cat")], True, "casual lower no-apos noq"),
    ("casual", "benos dog is moss", [TEACH("Beno", "pet", "Moss", "dog")], True, "casual lower no-apos noq"),
    ("casual", "cara lives in kelmar", [TEACH("Cara", "city", "Kelmar")], True, "casual lower noq"),
    ("casual", "my sister is esma", [TEACH("me", "sister", "Esma")], True, "casual lower noq"),
    ("casual", "esma works as baker", [TEACH("Esma", "job", "baker")], True, "casual lower noq"),
    ("casual", "farid speaks sarian", [TEACH("Farid", "language", "Sarian")], True, "casual lower noq"),
    ("casual", "my boss is dilo", [TEACH("me", "boss", "Dilo")], True, "casual lower noq"),
    ("casual", "gretas rabbit is nib", [TEACH("Greta", "pet", "Nib", "rabbit")], True, "casual lower no-apos noq"),
    ("casual", "haki lives in ostby", [TEACH("Haki", "city", "Ostby")], True, "casual lower noq"),
    ("casual", "my wife is iria", [TEACH("me", "spouse", "Iria")], True, "casual lower noq"),
    ("casual", "joris works as driver", [TEACH("Joris", "job", "driver")], True, "casual lower noq"),
    ("casual", "keldas parrot is pebble", [TEACH("Kelda", "pet", "Pebble", "parrot")], True, "casual lower no-apos noq"),
    ("casual", "loris husband is naldo", [TEACH("Loris", "spouse", "Naldo")], True, "casual lower no-apos noq"),
    ("casual", "mira speaks kelvic", [TEACH("Mira", "language", "Kelvic")], True, "casual lower noq"),
    ("casual", "my brother is risto", [TEACH("me", "brother", "Risto")], True, "casual lower noq"),
    ("casual", "orias cat is soot", [TEACH("Oria", "pet", "Soot", "cat")], True, "casual lower no-apos noq"),
    ("casual", "pelin lives in rill", [TEACH("Pelin", "city", "Rill")], True, "casual lower noq"),
    ("casual", "quiras dog is bramble", [TEACH("Quira", "pet", "Bramble", "dog")], True, "casual lower no-apos noq"),
    ("casual", "selma works as nurse", [TEACH("Selma", "job", "nurse")], True, "casual lower noq"),
    ("casual", "tareks horse is pickle", [TEACH("Tarek", "pet", "Pickle", "horse")], True, "casual lower no-apos noq"),
    ("casual", "my neighbour is ulf", [TEACH("me", "neighbour", "Ulf")], True, "casual lower noq"),
    ("casual", "viona works as teacher", [TEACH("Viona", "job", "teacher")], True, "casual lower noq"),
    ("casual", "wrens turtle is taffy", [TEACH("Wren", "pet", "Taffy", "turtle")], True, "casual lower no-apos noq"),
    ("casual", "xan lives in tormund", [TEACH("Xan", "city", "Tormund")], True, "casual lower noq"),
    ("casual", "ysolde works as clerk", [TEACH("Ysolde", "job", "clerk")], True, "casual lower noq"),
    ("casual", "zekis goat is clover", [TEACH("Zeki", "pet", "Clover", "goat")], True, "casual lower no-apos noq"),
    ("casual", "my husband is beno", [TEACH("me", "spouse", "Beno")], True, "casual lower noq"),
    ("casual", "dilos boss is selma", [TEACH("Dilo", "boss", "Selma")], True, "casual lower no-apos noq"),
    ("casual", "my hometown is vessa", [TEACH("me", "hometown", "Vessa")], True, "casual lower noq"),
    ("casual", "farids employer is lorn mills", [TEACH("Farid", "employer", "Lorn Mills")], True, "casual lower no-apos noq"),
    ("casual", "gretas school is ostby college", [TEACH("Greta", "school", "Ostby College")], True, "casual lower no-apos noq"),
    ("casual", "my mother is kelda", [TEACH("me", "mother", "Kelda")], True, "casual lower noq"),
    ("casual", "hakis job is mason.", [TEACH("Haki", "job", "mason")], True, "casual lower no-apos final-period"),
    ("casual", "irias sister is mira.", [TEACH("Iria", "sister", "Mira")], True, "casual lower no-apos final-period"),
    ("casual", "joris speaks sarian.", [TEACH("Joris", "language", "Sarian")], True, "casual lower final-period"),
    ("casual", "my father is loris.", [TEACH("me", "father", "Loris")], True, "casual lower final-period"),
    ("casual", "keldas dog is biscuit.", [TEACH("Kelda", "pet", "Biscuit", "dog")], True, "casual lower no-apos final-period"),
    ("casual", "naldo works as pilot.", [TEACH("Naldo", "job", "pilot")], True, "casual lower final-period"),
    ("casual", "oria works as florist.", [TEACH("Oria", "job", "florist")], True, "casual lower final-period"),
    ("casual", "wren lives in marvik.", [TEACH("Wren", "city", "Marvik")], True, "casual lower final-period"),
    # ---- casual_q 15 (t270-041..055): lowercase questions, no "?" ----
    ("casual_q", "where does ana live", [ASK("Ana", "city")], True, "casual_q lower noq"),
    ("casual_q", "what does esma do", [ASK("Esma", "job")], True, "casual_q lower noq"),
    ("casual_q", "who is dilos boss", [ASK("Dilo", "boss")], True, "casual_q lower no-apos noq"),
    ("casual_q", "what language does farid speak", [ASK("Farid", "language")], True, "casual_q lower noq"),
    ("casual_q", "who is iria married to", [ASK("Iria", "spouse")], True, "casual_q lower noq"),
    ("casual_q", "where does haki live", [ASK("Haki", "city")], True, "casual_q lower noq"),
    ("casual_q", "what is joris job", [ASK("Joris", "job")], True, "casual_q lower no-apos noq"),
    ("casual_q", "who is miras sister", [ASK("Mira", "sister")], True, "casual_q lower no-apos noq"),
    ("casual_q", "where does pelin live", [ASK("Pelin", "city")], True, "casual_q lower noq"),
    ("casual_q", "what does selma do", [ASK("Selma", "job")], True, "casual_q lower noq"),
    ("casual_q", "who is loris husband", [ASK("Loris", "spouse")], True, "casual_q lower no-apos noq"),
    ("casual_q", "what school does greta go to", [ASK("Greta", "school")], True, "casual_q lower noq"),
    ("casual_q", "who is my boss", [ASK("me", "boss")], True, "casual_q lower noq"),
    ("casual_q", "what is anas cat called", [ASK("Ana", "pet")], True, "casual_q lower no-apos noq"),
    ("casual_q", "who does viona work for", [ASK("Viona", "employer")], True, "casual_q lower noq"),
    # ---- lower_trap 15 (t270-056..070): decoy word is not a name ----
    ("lower_trap", "my boss is nice", [], True, "lower_trap boss no-fact"),
    ("lower_trap", "the rose is red", [], True, "lower_trap rose no-fact"),
    ("lower_trap", "i like may", [], True, "lower_trap may-month no-fact"),
    ("lower_trap", "frank is honest", [], False, "lower_trap frank-adjective name-reading-defensible"),
    ("lower_trap", "bill is on the table", [], True, "lower_trap bill-invoice no-fact"),
    ("lower_trap", "grace is important", [], True, "lower_trap grace-noun no-fact"),
    ("lower_trap", "i saw a robin in the garden", [], False, "lower_trap robin-bird name-reading-defensible"),
    ("lower_trap", "mark my words haki is a baker", [TEACH("Haki", "job", "baker")], False, "lower_trap mark-idiom real-fact-only"),
    ("lower_trap", "my boss is nice but my cat is fig", [TEACH("me", "pet", "Fig", "cat")], True, "lower_trap boss real-fact-only"),
    ("lower_trap", "the rose is red and ana lives in kelmar", [TEACH("Ana", "city", "Kelmar")], True, "lower_trap rose real-fact-only"),
    ("lower_trap", "i like may but esma speaks sarian", [TEACH("Esma", "language", "Sarian")], True, "lower_trap may-month real-fact-only"),
    ("lower_trap", "april is cold but my dog is moss", [TEACH("me", "pet", "Moss", "dog")], True, "lower_trap april-month real-fact-only"),
    ("lower_trap", "hope is good and joris is a driver", [TEACH("Joris", "job", "driver")], True, "lower_trap hope-noun real-fact-only"),
    ("lower_trap", "faith matters but miras parrot is pebble", [TEACH("Mira", "pet", "Pebble", "parrot")], True, "lower_trap faith-noun real-fact-only"),
    ("lower_trap", "i had to chase the bus", [], True, "lower_trap chase-verb no-fact"),
    # ---- clean 30 (t270-071..100): well-typed control ----
    ("clean", "Ana's cat is Fig.", [TEACH("Ana", "pet", "Fig", "cat")], True, "clean control"),
    ("clean", "Beno's dog is Moss.", [TEACH("Beno", "pet", "Moss", "dog")], True, "clean control"),
    ("clean", "Cara lives in Kelmar.", [TEACH("Cara", "city", "Kelmar")], True, "clean control"),
    ("clean", "My sister is Esma.", [TEACH("me", "sister", "Esma")], True, "clean control"),
    ("clean", "Esma works as a baker.", [TEACH("Esma", "job", "baker")], True, "clean control"),
    ("clean", "Farid speaks Sarian.", [TEACH("Farid", "language", "Sarian")], True, "clean control"),
    ("clean", "My boss is Dilo.", [TEACH("me", "boss", "Dilo")], True, "clean control"),
    ("clean", "Haki lives in Ostby.", [TEACH("Haki", "city", "Ostby")], True, "clean control"),
    ("clean", "My wife is Iria.", [TEACH("me", "spouse", "Iria")], True, "clean control"),
    ("clean", "Joris works as a driver.", [TEACH("Joris", "job", "driver")], True, "clean control"),
    ("clean", "Mira speaks Kelvic.", [TEACH("Mira", "language", "Kelvic")], True, "clean control"),
    ("clean", "My brother is Risto.", [TEACH("me", "brother", "Risto")], True, "clean control"),
    ("clean", "Pelin lives in Rill.", [TEACH("Pelin", "city", "Rill")], True, "clean control"),
    ("clean", "Selma works as a nurse.", [TEACH("Selma", "job", "nurse")], True, "clean control"),
    ("clean", "My neighbour is Ulf.", [TEACH("me", "neighbour", "Ulf")], True, "clean control"),
    ("clean", "Viona works as a teacher.", [TEACH("Viona", "job", "teacher")], True, "clean control"),
    ("clean", "Xan lives in Tormund.", [TEACH("Xan", "city", "Tormund")], True, "clean control"),
    ("clean", "Ysolde works as a clerk.", [TEACH("Ysolde", "job", "clerk")], True, "clean control"),
    ("clean", "Naldo works as a pilot.", [TEACH("Naldo", "job", "pilot")], True, "clean control"),
    ("clean", "Oria works as a florist.", [TEACH("Oria", "job", "florist")], True, "clean control"),
    ("clean", "Where does Ana live?", [ASK("Ana", "city")], True, "clean control question"),
    ("clean", "What does Esma do?", [ASK("Esma", "job")], True, "clean control question"),
    ("clean", "Who is Dilo's boss?", [ASK("Dilo", "boss")], True, "clean control question"),
    ("clean", "What language does Farid speak?", [ASK("Farid", "language")], True, "clean control question"),
    ("clean", "Who is Iria married to?", [ASK("Iria", "spouse")], True, "clean control question"),
    ("clean", "Where does Haki live?", [ASK("Haki", "city")], True, "clean control question"),
    ("clean", "What is Joris's job?", [ASK("Joris", "job")], True, "clean control question"),
    ("clean", "Who is Mira's sister?", [ASK("Mira", "sister")], True, "clean control question"),
    ("clean", "Where does Pelin live?", [ASK("Pelin", "city")], True, "clean control question"),
    ("clean", "Who does Viona work for?", [ASK("Viona", "employer")], True, "clean control question"),
]

TRAP_WORDS = ["boss", "rose", "may", "frank", "bill", "grace", "robin",
              "april", "hope", "faith", "mark", "chase"]


def check():
    assert len(ITEMS) == 100, len(ITEMS)
    fams = {}
    for f, _, _, _, _ in ITEMS:
        fams[f] = fams.get(f, 0) + 1
    assert fams == {"casual": 40, "casual_q": 15, "lower_trap": 15, "clean": 30}, fams

    turns = [t for _, t, _, _, _ in ITEMS]
    assert len(set(turns)) == 100, "duplicate turn"

    for i, (fam, turn, gold, clear, notes) in enumerate(ITEMS):
        want = "t270-%03d" % (i + 1)
        assert isinstance(turn, str) and turn, want
        assert isinstance(gold, list), want
        assert isinstance(clear, bool), want
        assert isinstance(notes, str) and notes, want
        for fr in gold:
            assert set(fr.keys()) <= {"act", "subject", "relation",
                                      "relation_aliases", "value", "chain",
                                      "chain_aliases"}, (want, fr.keys())
            if fr["act"] == "TEACH":
                assert set(fr.keys()) == {"act", "subject", "relation",
                                          "relation_aliases", "value"}, (want, fr.keys())
                spans = [fr["subject"], fr["value"]]
            elif fr["act"] == "ASK":
                assert set(fr.keys()) == {"act", "subject", "relation", "chain",
                                          "relation_aliases", "chain_aliases"}, (want, fr.keys())
                assert fr["chain"] is None and fr["chain_aliases"] is None, want
                spans = [fr["subject"]]
            else:
                raise AssertionError((want, fr["act"]))
            assert fr["relation_aliases"] == ALIASES[fr["relation"]] or (
                fr["relation"] == "pet" and fr["relation_aliases"][:3] == ALIASES["pet"]), want
            low = " " + turn.lower() + " "
            for s in spans:
                if s == "me":
                    continue
                words = s.lower().split()
                for w in words:
                    assert (" " + w + " " in low) or (w in low), (want, s, turn)

        if fam in ("casual", "casual_q", "lower_trap"):
            assert turn == turn.lower(), (want, "must be all lowercase")
            assert "?" not in turn, (want, "no question marks in casual families")
        if fam == "casual":
            assert "'" not in turn, (want, "no apostrophes in casual")
        if fam == "clean":
            assert turn[0].isupper(), (want, "clean starts capitalised")
            if gold and gold[0]["act"] == "TEACH":
                assert turn.endswith("."), want
            if gold and gold[0]["act"] == "ASK":
                assert turn.endswith("?"), want
        if fam == "lower_trap":
            low = turn.lower()
            assert any(w in low for w in TRAP_WORDS), (want, "needs a trap word")

    casual = ITEMS[0:40]
    assert all(x[0] == "casual" for x in casual)
    nopunct = sum(1 for _, t, _, _, _ in casual if t[-1] not in ".!?")
    assert nopunct >= 30, nopunct
    assert all(x[0] == "casual_q" for x in ITEMS[40:55])
    assert all(x[0] == "lower_trap" for x in ITEMS[55:70])
    assert all(x[0] == "clean" for x in ITEMS[70:100])
    print("self-checks OK: 100 items", fams, "casual-no-punct", nopunct)


def main():
    check()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PANEL_PATH, "w") as f:
        for i, (fam, turn, gold, clear, notes) in enumerate(ITEMS):
            rec = {"id": "t270-%03d" % (i + 1), "family": fam, "turn": turn,
                   "gold": gold, "clear": clear, "notes": notes}
            f.write(json.dumps(rec) + "\n")
    print("wrote", PANEL_PATH)


if __name__ == "__main__":
    main()
