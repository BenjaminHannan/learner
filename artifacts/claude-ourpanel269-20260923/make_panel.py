"""Blind panel 269 (follow-up to 265): group-word owners and non-owner we/us/our.

Writer: build/verification agent, 2026-09-23. Read only the 265 spec (plus the
264 spec for field/frame format, OPUS-RULES.txt, and the schema + judgement
sections of the 235 README). Never opened panel 265, any builder code, any
other panel's items, or any relation table. All names/places/wordings new.

Layout (100 items, family-block order, ids o269-001 .. o269-100):
  group_owner  30  our/we/us + owned thing; gold [] (agent must ask whose)
  mixed        15  group-owner clause + first-person/named fact; gold = other
  first_person 20  I/me/my facts, subject "me"
  named        15  third-person facts (controls)
  non_owner_we 20  we/us/our with no ownership; gold = the other fact(s)

Line schema: exactly {id, family, turn, gold, clear, notes, ask_whose}.
TEACH frame: exactly {act, subject, relation, relation_aliases, value}.
ask_whose is true iff the turn has a we/us/our/ours/ourselves owner or
subject (group_owner + mixed families); false for first_person, named, and
non_owner_we (the group word there owns nothing, so there is nothing to ask
whose about). subject/value are exact spans from the turn ("me" = speaker).

Run from the repo root:
  /usr/bin/python3 -B artifacts/claude-ourpanel269-20260923/make_panel.py
Rewrites panel.jsonl deterministically and runs all self-checks first.
"""

import json
import os
import re

OUT_DIR = os.path.join("artifacts", "claude-ourpanel269-20260923")
PANEL_PATH = os.path.join(OUT_DIR, "panel.jsonl")

GROUP_RE = re.compile(r"\b(we|us|our|ours|ourselves)\b", re.IGNORECASE)

# One fixed alias list per relation (pet lists gain the species word per item).
ALIASES = {
    "pet": ["pet", "animal", "companion"],
    "city": ["city", "town"],
    "hometown": ["hometown", "home town"],
    "place_of_birth": ["place_of_birth", "birthplace"],
    "job": ["job", "occupation", "profession"],
    "employer": ["employer", "company"],
    "workplace": ["workplace", "work"],
    "school": ["school", "college"],
    "language": ["language", "tongue"],
    "sister": ["sister"],
    "brother": ["brother"],
    "mother": ["mother"],
    "son": ["son"],
    "cousin": ["cousin"],
    "boss": ["boss"],
    "spouse": ["spouse", "partner"],
    "car": ["car", "vehicle"],
    "home": ["home", "house"],
}


def teach(subject, relation, value, species=None):
    aliases = list(ALIASES[relation])
    if relation == "pet":
        assert species, "pet frames need the species word"
        aliases = aliases + [species]
    return {
        "act": "TEACH",
        "subject": subject,
        "relation": relation,
        "relation_aliases": aliases,
        "value": value,
    }


def item(iid, family, turn, gold, clear, notes, ask_whose):
    return {
        "id": iid,
        "family": family,
        "turn": turn,
        "gold": gold,
        "clear": clear,
        "notes": notes,
        "ask_whose": ask_whose,
    }


def build():
    items = []
    # ---- group_owner: o269-001 .. o269-030 (gold [], ask_whose true) ----
    group = [
        ("Our dog Biscuit is three years old.", "group-owner owner-start pet"),
        ("We live in Kallmouth now.", "group-owner owner-start city"),
        ("The cabin we rented for winter is in Eskervale.", "group-owner owner-mid city"),
        ("Our mother is visiting next week.", "group-owner owner-start relative"),
        ("The dog staying at ours is a beagle.", "group-owner owner-mid ours pet"),
        ("Us three share a van, and it is a Kelso.", "group-owner owner-start car"),
        ("The van us three share is a Merritt.", "group-owner owner-mid car"),
        ("Our car is an Ostland.", "group-owner owner-start car"),
        ("The flat we rent is on Mill Lane.", "group-owner owner-mid home"),
        ("our cat Miso sleeps on the porch all day.", "group-owner owner-start lower pet"),
        ("we speak Kellish at home.", "group-owner owner-start lower language"),
        ("That boat is ours.", "group-owner owner-mid ours"),
        ("The school we picked for the kids is Alder School.", "group-owner owner-mid school"),
        ("Our workplace is Halden Mills.", "group-owner owner-start workplace"),
        ("The garage we work at is Copperline Garage.", "group-owner owner-mid workplace"),
        ("Our hometown is Dunshelf.", "group-owner owner-start hometown"),
        ("The town we grew up in is Fenmere.", "group-owner owner-mid hometown"),
        ("We keep rabbits; Pebble is the oldest.", "group-owner owner-start pet"),
        ("The parrot living at ours is a macaw.", "group-owner owner-mid ours pet"),
        ("our house is Thistle Cottage.", "group-owner owner-start lower home"),
        ("We bought a Kelso last spring.", "group-owner owner-start car"),
        ("The cottage we bought is Bramble House.", "group-owner owner-mid home"),
        ("Our sister lives in Gullhaven.", "group-owner owner-start relative"),
        ("The cousins we visit every summer live in Solmar.", "group-owner owner-mid relative"),
        ("Our boss is on holiday.", "group-owner owner-start boss"),
        ("The bakery we run is Frostwick Bakery.", "group-owner owner-mid workplace"),
        ("Our language at home is Tormic.", "group-owner owner-start language"),
        ("The car at ours needs new brakes.", "group-owner owner-mid ours car"),
        ("Our cat had kittens yesterday.", "group-owner owner-start pet"),
        ("The pony we own is stabled in Tindale.", "group-owner owner-mid pet"),
    ]
    for k, (turn, notes) in enumerate(group, start=1):
        items.append(item("o269-%03d" % k, "group_owner", turn, [], True, notes, True))

    # ---- mixed: o269-031 .. o269-045 (gold = the other fact) ----
    mixed = [
        ("Our dog is Biscuit, and I work as a nurse.",
         [teach("me", "job", "nurse")], True, "mixed other-first-person"),
        ("I live in Kallmouth, but our cat rules the house.",
         [teach("me", "city", "Kallmouth")], True, "mixed other-first-person"),
        ("We speak Vessic at home, and my sister is Petra.",
         [teach("me", "sister", "Petra")], True, "mixed other-first-person"),
        ("My brother is Osric, and our van is a Kelso.",
         [teach("me", "brother", "Osric")], True, "mixed other-first-person"),
        ("Our house is Bramble House, while Joren lives in Tindale.",
         [teach("Joren", "city", "Tindale")], True, "mixed other-named"),
        ("Donal works at Juniper Press, though we share one laptop.",
         [teach("Donal", "workplace", "Juniper Press")], True, "mixed other-named"),
        ("We keep chickens, and my hometown is Eskervale.",
         [teach("me", "hometown", "Eskervale")], True, "mixed other-first-person"),
        ("My boss is Ansel, but our office moved to Marshgate.",
         [teach("me", "boss", "Ansel")], False, "mixed other-first-person office-move"),
        ("our parrot is Clover, and I speak Drannic.",
         [teach("me", "language", "Drannic")], True, "mixed lower other-first-person"),
        ("Iona's cat is Tansy, and our dog ate the cake.",
         [teach("Iona", "pet", "Tansy", species="cat")], True, "mixed other-named"),
        ("We rent on Mill Lane, while my cousin is Bellamy.",
         [teach("me", "cousin", "Bellamy")], True, "mixed other-first-person"),
        ("My workplace is Vexley Shipping, and we carpool daily.",
         [teach("me", "workplace", "Vexley Shipping")], True, "mixed other-first-person"),
        ("Our mother bakes bread, and I teach at Alder School.",
         [teach("me", "workplace", "Alder School")], True, "mixed other-first-person"),
        ("Torvald speaks Kellish, though our radio is broken.",
         [teach("Torvald", "language", "Kellish")], True, "mixed other-named"),
        ("We own a Merritt, and my son is Pello.",
         [teach("me", "son", "Pello")], True, "mixed other-first-person"),
    ]
    for k, (turn, gold, clear, notes) in enumerate(mixed, start=31):
        items.append(item("o269-%03d" % k, "mixed", turn, gold, clear, notes, True))

    # ---- first_person: o269-046 .. o269-065 (subject "me") ----
    first = [
        ("I live in Gullhaven.", [teach("me", "city", "Gullhaven")], True, "first-person"),
        ("I work as a pilot.", [teach("me", "job", "pilot")], True, "first-person"),
        ("My dog is Bramble.", [teach("me", "pet", "Bramble", species="dog")], True, "first-person"),
        ("I speak Tormic.", [teach("me", "language", "Tormic")], True, "first-person"),
        ("My sister is Liora.", [teach("me", "sister", "Liora")], True, "first-person"),
        ("I studied at Marshgate College.", [teach("me", "school", "Marshgate College")], True, "first-person"),
        ("My hometown is Vessport.", [teach("me", "hometown", "Vessport")], True, "first-person"),
        ("I work at Frostwick Bakery.", [teach("me", "workplace", "Frostwick Bakery")], True, "first-person"),
        ("My boss is Coralie.", [teach("me", "boss", "Coralie")], True, "first-person"),
        ("My cat is Tansy.", [teach("me", "pet", "Tansy", species="cat")], True, "first-person"),
        ("I was born in Perrin Bay.", [teach("me", "place_of_birth", "Perrin Bay")], True, "first-person"),
        ("My brother is Caspian.", [teach("me", "brother", "Caspian")], True, "first-person"),
        ("My employer is Juniper Press.", [teach("me", "employer", "Juniper Press")], True, "first-person"),
        ("i drive a Kelso.", [teach("me", "car", "Kelso")], True, "first-person lower"),
        ("My cousin is Delphine.", [teach("me", "cousin", "Delphine")], True, "first-person"),
        ("I teach at Kestrel Academy.", [teach("me", "workplace", "Kestrel Academy")], True, "first-person"),
        ("My mother is Sorrel.", [teach("me", "mother", "Sorrel")], True, "first-person"),
        ("My spouse is Wendelin.", [teach("me", "spouse", "Wendelin")], True, "first-person"),
        ("My city is Larkholm.", [teach("me", "city", "Larkholm")], True, "first-person"),
        ("My rabbit is Pebble.", [teach("me", "pet", "Pebble", species="rabbit")], True, "first-person"),
    ]
    for k, (turn, gold, clear, notes) in enumerate(first, start=46):
        items.append(item("o269-%03d" % k, "first_person", turn, gold, clear, notes, False))

    # ---- named: o269-066 .. o269-080 (controls) ----
    named = [
        ("Gregor lives in Dunshelf.", [teach("Gregor", "city", "Dunshelf")], True, "named"),
        ("Haldor works as a blacksmith.", [teach("Haldor", "job", "blacksmith")], True, "named"),
        ("Fenna's hamster is Nutmeg.", [teach("Fenna", "pet", "Nutmeg", species="hamster")], True, "named"),
        ("Maddox speaks Vessic.", [teach("Maddox", "language", "Vessic")], True, "named"),
        ("Nerys teaches at Alder School.", [teach("Nerys", "workplace", "Alder School")], True, "named"),
        ("Quillon's sister is Ysolde.", [teach("Quillon", "sister", "Ysolde")], True, "named"),
        ("Rowan's boss is Tadeo.", [teach("Rowan", "boss", "Tadeo")], True, "named"),
        ("Sella was born in Solmar.", [teach("Sella", "place_of_birth", "Solmar")], True, "named"),
        ("Ulfred's hometown is Kestrel Bay.", [teach("Ulfred", "hometown", "Kestrel Bay")], True, "named"),
        ("Vesper works at Copperline Garage.", [teach("Vesper", "workplace", "Copperline Garage")], True, "named"),
        ("Zevan's mother is Ondine.", [teach("Zevan", "mother", "Ondine")], True, "named"),
        ("Marisol's employer is Vexley Shipping.", [teach("Marisol", "employer", "Vexley Shipping")], True, "named"),
        ("Emeric's parrot is Clover.", [teach("Emeric", "pet", "Clover", species="parrot")], True, "named"),
        ("Doria's cousin is Kessa.", [teach("Doria", "cousin", "Kessa")], True, "named"),
        ("Tilda's spouse is Bram.", [teach("Tilda", "spouse", "Bram")], True, "named"),
    ]
    for k, (turn, gold, clear, notes) in enumerate(named, start=66):
        items.append(item("o269-%03d" % k, "named", turn, gold, clear, notes, False))

    # ---- non_owner_we: o269-081 .. o269-100 (group word, no ownership) ----
    nonowner = [
        ("We met at the harbour cafe, and Liora lives in Kestrel Bay.",
         [teach("Liora", "city", "Kestrel Bay")], True, "non-owner-we met-at"),
        ("Our meeting is at three, and I am a pilot.",
         [teach("me", "job", "pilot")], True, "non-owner-we meeting-time"),
        ("Donal told us his sister is Petra.",
         [teach("Donal", "sister", "Petra")], True, "non-owner-we told-us"),
        ("The notice said our doors open at nine, and my workplace is Juniper Press.",
         [teach("me", "workplace", "Juniper Press")], True, "non-owner-we quoted sign"),
        ("The three of us went hiking, and my hometown is Marshgate.",
         [teach("me", "hometown", "Marshgate")], True, "non-owner-we us-group"),
        ("Between us, Mara speaks Kellish.",
         [teach("Mara", "language", "Kellish")], True, "non-owner-we between-us"),
        ("We all know that Eskil is a blacksmith.",
         [teach("Eskil", "job", "blacksmith")], False, "non-owner-we generic-we"),
        ("The chalkboard says our special is soup, and Fenna's brother is Hadrian.",
         [teach("Fenna", "brother", "Hadrian")], True, "non-owner-we quoted sign"),
        ("The news reached us late, but Petra's workplace is Halden Mills.",
         [teach("Petra", "workplace", "Halden Mills")], True, "non-owner-we reached-us"),
        ("Our best shot is Friday, says the coach, and I live in Solmar.",
         [teach("me", "city", "Solmar")], True, "non-owner-we fixed-phrase quoted"),
        ("We cheered when Kessa won, and Kessa teaches at Kestrel Academy.",
         [teach("Kessa", "workplace", "Kestrel Academy")], True, "non-owner-we cheered"),
        ("Our garden grows the best plums, boasted the neighbour, and my cousin is Liv.",
         [teach("me", "cousin", "Liv")], True, "non-owner-we quoted our"),
        ("With us today is guest speaker Tadeo, who lives in Vessport.",
         [teach("Tadeo", "city", "Vessport")], True, "non-owner-we with-us"),
        ("The two of us split the bill, and Iona's hometown is Gullhaven.",
         [teach("Iona", "hometown", "Gullhaven")], True, "non-owner-we us-group"),
        ("Our paths crossed in Eskervale, where Bennic lives now.",
         [teach("Bennic", "city", "Eskervale")], True, "non-owner-we fixed-phrase"),
        ("Nobody told us the store closes early, and Sella was born in Marshgate.",
         [teach("Sella", "place_of_birth", "Marshgate")], True, "non-owner-we told-us"),
        ("We laughed all evening, and Ulfred speaks Drannic.",
         [teach("Ulfred", "language", "Drannic")], True, "non-owner-we laughed"),
        ("Our old joke about Mondays came up again, and Vesper's boss is Liv.",
         [teach("Vesper", "boss", "Liv")], True, "non-owner-we fixed-phrase"),
        ("The driver dropped us at midnight, and Zevan's spouse is Iona.",
         [teach("Zevan", "spouse", "Iona")], True, "non-owner-we dropped-us"),
        ("We waited an hour, and my ferret is Fennel.",
         [teach("me", "pet", "Fennel", species="ferret")], True, "non-owner-we waited"),
    ]
    for k, (turn, gold, clear, notes) in enumerate(nonowner, start=81):
        items.append(item("o269-%03d" % k, "non_owner_we", turn, gold, clear, notes, False))
    return items


def self_check(items):
    assert len(items) == 100, "want 100 items, have %d" % len(items)
    counts = {}
    for it in items:
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    assert counts == {"group_owner": 30, "mixed": 15, "first_person": 20,
                      "named": 15, "non_owner_we": 20}, counts
    # ids in family-block order
    assert [it["id"] for it in items] == ["o269-%03d" % n for n in range(1, 101)]
    # no duplicate turns
    turns = [it["turn"] for it in items]
    assert len(set(turns)) == 100, "duplicate turn found"
    # schema exactness
    for it in items:
        assert set(it.keys()) == {"id", "family", "turn", "gold", "clear",
                                  "notes", "ask_whose"}, it["id"]
        assert isinstance(it["clear"], bool) and isinstance(it["ask_whose"], bool)
        assert isinstance(it["gold"], list) and isinstance(it["notes"], str) and it["notes"]
        for fr in it["gold"]:
            assert set(fr.keys()) == {"act", "subject", "relation",
                                      "relation_aliases", "value"}, it["id"]
            assert fr["act"] == "TEACH"
            assert isinstance(fr["relation_aliases"], list) and len(fr["relation_aliases"]) >= 1
            if fr["subject"] != "me":
                assert fr["subject"] in it["turn"], (it["id"], fr["subject"])
            assert fr["value"] in it["turn"], (it["id"], fr["value"])
            base = list(ALIASES[fr["relation"]])
            if fr["relation"] == "pet":
                assert fr["relation_aliases"][:3] == base, it["id"]
                assert len(fr["relation_aliases"]) == 4, it["id"]
            else:
                assert fr["relation_aliases"] == base, it["id"]
    # ask_whose rule: true iff group_owner or mixed
    for it in items:
        want = it["family"] in ("group_owner", "mixed")
        assert it["ask_whose"] == want, it["id"]
    # group word present where required, absent elsewhere
    for it in items:
        has = bool(GROUP_RE.search(it["turn"]))
        if it["family"] in ("group_owner", "mixed", "non_owner_we"):
            assert has, it["id"]
        else:
            assert not has, it["id"]
    # group_owner: gold always [] (pure group-owned facts)
    for it in items:
        if it["family"] == "group_owner":
            assert it["gold"] == [], it["id"]
    # non_owner_we: every turn carries a named/first-person fact to save
    for it in items:
        if it["family"] == "non_owner_we":
            assert len(it["gold"]) >= 1, it["id"]
    # widened owner placement: >= 10 group_owner turns with owner away from start
    mid = [it["id"] for it in items if it["family"] == "group_owner"
           and "owner-mid" in it["notes"].split()]
    assert len(mid) >= 10, "owner-mid only %d" % len(mid)
    # mechanical cross-check of the tags: first word is not a group word
    for iid in mid:
        first = re.sub(r"^[^A-Za-z]+", "", next(it["turn"] for it in items if it["id"] == iid))
        first = first.split()[0].lower()
        assert first not in ("we", "us", "our", "ours", "ourselves"), iid
    print("self-check OK: 100 items, owner-mid=%d, clear=false=%d" %
          (len(mid), sum(1 for it in items if not it["clear"])))


def main():
    items = build()
    self_check(items)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PANEL_PATH, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=True) + "\n")
    print("wrote %s" % PANEL_PATH)


if __name__ == "__main__":
    main()
