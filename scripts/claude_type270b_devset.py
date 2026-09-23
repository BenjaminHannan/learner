#!/usr/bin/env python3
"""Exp 270b dev set: the builder's own casual turns, traps and s-names.

Deterministic generator. All names fictional, all wording the builder's own.
No panels were read, copied or rebuilt (270's registered FAIL is known only
at the category level: 3 keep-s near-miss stems Beno/Dilo/Haki + verb-shape
and exotic-pet vocabulary gaps on the loop line).

Families: casual (64 TEACH), casual_q (16 ASK), lower_trap (24, expect no
wrong saves), clean (24, byte-identical passthrough + A==A261b frames),
sname (16 TEACH on s-ending names: 8 real s-names that keep, 8 fictional
stems that strip), seen (4 multi-turn seen-name memory items).

Item: {id, family, setup[], turn, gold[{act,subject,relation[],aliases[],
value?}], note}. Gold relations are table-v2 names; aliases [[]] unless
noted. Usage: python -B scripts/claude_type270b_devset.py <out.jsonl>
"""
import json
import sys

PEOPLE = ["Beno", "Dilo", "Haki", "Zorana", "Sarella", "Vanno",
          "Kessa", "Rurik", "Isolde", "Fenwick", "Senna", "Quillan"]
PLACES = ["Aldermere", "Brackenholme", "Cinderfell", "Duskwater", "Emberlyn"]
JOBS = ["cooper", "fletcher", "tanner", "miller", "saddler"]
PETS = ["dog", "cat", "horse"]


def T(subj, rel, val, aliases=None):
    return {"act": "TEACH", "subject": subj, "relation": [rel],
            "aliases": [aliases or []], "value": val}


def A(subj, rel):
    return {"act": "ASK", "subject": subj, "relation": [rel],
            "aliases": [[]]}


def main(out):
    items = []

    def add(fam, turn, gold, setup=None, note=""):
        items.append({"id": f"d270b-{len(items) + 1:03d}", "family": fam,
                      "setup": setup or [], "turn": turn, "gold": gold,
                      "note": note})

    # ---- casual 1-16: possessive, no apostrophe, all lowercase ----
    rels = ["mother", "father", "sister", "brother", "friend", "boss"]
    for i in range(16):
        n, rel = PEOPLE[i % 12], rels[i % 6]
        v = PEOPLE[(i + 5) % 12]
        add("casual", f"{n.lower()}s {rel} is {v}.", [T(n, rel, v)],
            note="noapos")
    # ---- casual 17-24: possessive with apostrophe, all lowercase ----
    for i in range(8):
        n, rel = PEOPLE[(i + 3) % 12], rels[(i + 2) % 6]
        v = PEOPLE[(i + 7) % 12]
        add("casual", f"{n.lower()}'s {rel} is {v.lower()}.",
            [T(n, rel, v)], note="apos-lower")
    # ---- casual 25-34: lives, lowercase slots ----
    for i in range(10):
        n, p = PEOPLE[(i + 1) % 12], PLACES[i % 5]
        add("casual", f"{n.lower()} lives in {p.lower()}.", [T(n, "city", p)],
            note="lives")
    # ---- casual 35-42: works, lowercase slots ----
    for i in range(8):
        n, p = PEOPLE[(i + 6) % 12], PLACES[(i + 2) % 5]
        add("casual", f"{n.lower()} works at {p.lower()}.",
            [T(n, "employer", p)], note="works")
    # ---- casual 43-50: my-shapes, lowercase ----
    mys = [("mother", PEOPLE[4]), ("father", PEOPLE[9]), ("dog", "Rex"),
           ("cat", "Mittens"), ("boss", PEOPLE[2]), ("friend", PEOPLE[6]),
           ("brother", PEOPLE[1]), ("horse", "Bramble")]
    for rel, v in mys:
        if rel in ("dog", "cat", "horse"):
            add("casual", f"my {rel} is {str(v).lower()}.",
                [T("me", "pet", v, aliases=[rel])], note="my-pet")
        else:
            add("casual", f"my {rel} is {v.lower()}.", [T("me", rel, v)],
                note="my-shape")
    # ---- casual 51-60: opener-led casual teaches ----
    openers = ["hey", "yo,", "so", "well,", "oh,", "btw,", "listen,",
               "look,", "yes,", "okay,"]
    for i, op in enumerate(openers):
        n, rel = PEOPLE[(i + 8) % 12], rels[(i + 1) % 6]
        v = PEOPLE[(i + 2) % 12]
        add("casual", f"{op} {n.lower()}s {rel} is {v}.",
            [T(n, rel, v)], note="opener")
    # ---- casual 61-64: occupation values, lowercase ----
    for i in range(4):
        n, j = PEOPLE[(i + 2) % 12], JOBS[i % 5]
        add("casual", f"{n.lower()} works as {j}.", [T(n, "occupation", j)],
            note="occupation")

    # ---- casual_q 16: lowercase questions, no "?" ----
    # Gold ASK subject = the questioned name (the ear's ASK convention on the
    # builder's dev wave: ASK (Beno, mother) for "who is Beno's mother";
    # asker-me only for my-shapes). Fixed pre-seal from own dev evidence.
    q = [("who", "Beno", "mother"), ("who", "Dilo", "boss"),
         ("who", "Haki", "brother"), ("what", "Zorana", "friend"),
         ("who", "Sarella", "father"), ("who", "Vanno", "sister"),
         ("what", "Kessa", "mother"), ("who", "Rurik", "friend"),
         ("where", "Isolde", "city"), ("who", "Fenwick", "boss"),
         ("who", "Senna", "sister"), ("what", "Quillan", "friend"),
         ("who", "me", "mother"), ("where", "me", "city"),
         ("whos", "Beno", "boss"), ("whats", "Dilo", "friend")]
    for w, n, rel in q:
        if w == "where" and n == "me":
            add("casual_q", "where do i live", [A("me", "city")],
                note="q-where-me")
        elif w == "where":
            add("casual_q", f"where does {n.lower()} live",
                [A(n, "city")], note="q-where")
        elif w == "whos":
            add("casual_q", f"whos {n.lower()}s {rel}",
                [A(n, rel)], note="q-whos")
        elif w == "whats":
            add("casual_q", f"whats {n.lower()}s {rel}",
                [A(n, rel)], note="q-whats")
        elif n == "me":
            add("casual_q", f"{w} is my {rel}", [A("me", rel)],
                note="q-my")
        else:
            add("casual_q", f"{w} is {n.lower()}s {rel}", [A(n, rel)],
                note="q-who")

    # ---- lower_trap 24: expect no wrong saves ----
    traps = [
        ("lets say benos mother is senna.", []),
        ("suppose dilo lives in aldermere.", []),
        ("imagine hakis boss is quillan.", []),
        ("what if zoranas brother is vanno.", []),
        ("i want sarellas mother to be kessa.", []),
        ("vanno will live in brackenholme.", []),
        ("kessas sister will be senna.", []),
        ("i am training to be cooper.", []),
        ("rurik is going to be miller.", []),
        ("benos mother is senna, right.", []),
        ("dilo lives in aldermere, isn't it.", []),
        ("hakis boss is quillan, don't you think.", []),
        ("zoranas brother is vanno, yeah.", []),
        ("so sarellas friend is kessa.", []),
        ("so vanno works at cinderfell.", []),
        ("benos mother is not senna.", []),
        ("dilo does not live in aldermere.", []),
        ("hakis boss was never quillan.", []),
        ("does kessa live in duskwater.", []),
        ("is benos mother senna.", []),
        ("do you know dilo.", []),
        ("zorana is a cooper.", []),
        ("my boss was quillan.", []),
        ("hakis mother used to be senna.", []),
    ]
    for t, g in traps:
        add("lower_trap", t, g, note="trap")

    # ---- clean 24: passthrough + frame identity ----
    cleans = [
        ("Rurik lives in Aldermere.", [T("Rurik", "city", "Aldermere")]),
        ("Dilo's mother is Senna.", [T("Dilo", "mother", "Senna")]),
        ("Beno works at Cinderfell.", [T("Beno", "employer", "Cinderfell")]),
        ("My friend is Zorana.", [T("me", "friend", "Zorana")]),
        ("James's sister is Kessa.", [T("James", "sister", "Kessa")]),
        ("Morris's boss is Rurik.", [T("Morris", "boss", "Rurik")]),
        ("Sarella's dog is Rex.", [T("Sarella", "pet", "Rex", aliases=["dog"])]),
        ("Vanno's father is Fenwick.", [T("Vanno", "father", "Fenwick")]),
        ("Kessa works as Cooper.", [T("Kessa", "occupation", "Cooper")]),
        ("Haki's brother is Quillan.", [T("Haki", "brother", "Quillan")]),
        ("Isolde lives in Emberlyn.", [T("Isolde", "city", "Emberlyn")]),
        ("My mother is Senna.", [T("me", "mother", "Senna")]),
        ("Who is Beno's mother?", [A("Beno", "mother")]),
        ("Where does Dilo live?", [A("Dilo", "city")]),
        ("Who's Haki's boss?", [A("Haki", "boss")]),
        ("What is Zorana's friend?", [A("Zorana", "friend")]),
        ("Who is my sister?", [A("me", "sister")]),
        ("Where's Sarella's boss?", [A("Sarella", "boss")]),
        ("Let's say Beno's mother is Senna.", []),
        ("Dilo will live in Aldermere.", []),
        ("Haki's boss is Quillan, right?", []),
        ("I am training to be cooper.", []),
        ("Suppose Zorana lives in Duskwater.", []),
        ("Vanno's mother is not Kessa.", []),
    ]
    for t, g in cleans:
        add("clean", t, g, note="clean")

    # ---- sname 16: s-ending names (8 keep, 8 strip) ----
    keeps = [("morris", "Morris", "mother", "Senna"),
             ("tess", "Tess", "boss", "Rurik"),
             ("james", "James", "sister", "Kessa"),
             ("thomas", "Thomas", "brother", "Quillan"),
             ("charles", "Charles", "father", "Fenwick"),
             ("louis", "Louis", "friend", "Vanno"),
             ("dennis", "Dennis", "mother", "Isolde"),
             ("miles", "Miles", "boss", "Dilo")]
    for raw, want, rel, v in keeps:
        add("sname", f"{raw} {rel} is {v.lower()}.", [T(want, rel, v)],
            note="keep-s")
    strips = [("benos", "Beno"), ("dilos", "Dilo"), ("hakis", "Haki"),
              ("zoranas", "Zorana"), ("sarellas", "Sarella"),
              ("vannos", "Vanno"), ("kessas", "Kessa"),
              ("ruriks", "Rurik")]
    for raw, want in strips:
        rel = ["mother", "boss", "brother", "friend"][len(want) % 4]
        v = PEOPLE[(len(want) + 3) % 12]
        add("sname", f"{raw} {rel} is {v.lower()}.", [T(want, rel, v)],
            note="strip-s")

    # ---- seen 4: multi-turn seen-name memory ----
    add("seen", "benos dog is rex.", [T("Beno", "pet", "Rex", aliases=["dog"])],
        setup=["Beno lives in Aldermere."], note="seen-strip")
    add("seen", "jamess sister is senna.", [T("James", "sister", "Senna")],
        setup=["James works at Cinderfell."], note="seen-keep-double-s")
    add("seen", "dilos boss is quillan.", [T("Dilo", "boss", "Quillan")],
        setup=["Dilo lives in Brackenholme."], note="seen-strip")
    add("seen", "hakis mother is senna.", [T("Haki", "mother", "Senna")],
        setup=["Haki lives in Duskwater."], note="seen-strip")

    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    fams = {}
    for it in items:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    print(len(items), "turns", fams)


if __name__ == "__main__":
    main(sys.argv[1])
