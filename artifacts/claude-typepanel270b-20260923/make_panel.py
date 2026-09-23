"""Blind TEST-ONLY panel 270b: casual typing, ear line (director brief 2026-09-23).

100 turns, fictional names. Families: casual 40 / casual_q 15 / lower_trap 15 / clean 30.
Schema follows earpanel264-spec (id, family, turn, gold, clear, notes).

Gold uses the exact raw spans from the turn (same case), so every subject and
value (other than "me") appears word for word in its turn. Possessives without
an apostrophe keep their raw stem in gold (e.g. "jamess" in "jamess dog is tyto");
the scorer normalises. "me" stands for the speaker.
"""

import json
import os
import sys

ALIAS = {
    "city": ["city", "town", "place"],
    "hometown": ["hometown", "home town", "city"],
    "job": ["job", "occupation", "profession", "work"],
    "employer": ["employer", "company", "firm"],
    "workplace": ["workplace", "work", "office"],
    "boss": ["boss", "manager", "supervisor"],
    "sister": ["sister", "sibling"],
    "brother": ["brother", "sibling"],
    "cousin": ["cousin", "relative"],
    "mother": ["mother", "mum", "mom"],
    "school": ["school", "college", "academy"],
    "language": ["language", "languages", "tongue"],
    "friend": ["friend", "buddy", "pal"],
    "neighbour": ["neighbour", "neighbor", "next-door"],
}


def pet_alias(species):
    return [species, "pet", "animal", "companion"]


def T(subject, relation, value, aliases):
    return {
        "act": "TEACH",
        "subject": subject,
        "relation": relation,
        "relation_aliases": aliases,
        "value": value,
    }


def A(subject, relation, aliases):
    return {
        "act": "ASK",
        "subject": subject,
        "relation": relation,
        "chain": None,
        "relation_aliases": aliases,
        "chain_aliases": None,
    }


# (family, turn, gold, clear, notes)
ITEMS = [
    # ---- casual 40: lowercase TEACH (u270-001..040) ----
    ("casual", "my dog is pip", [T("me", "pet", "pip", pet_alias("dog"))], True, "casual lower plain-pet"),
    ("casual", "jamess dog is tyto", [T("jamess", "pet", "tyto", pet_alias("dog"))], True, "casual lower no-apos s-owner"),
    ("casual", "iris cat is mimi", [T("iris", "pet", "mimi", pet_alias("cat"))], True, "casual lower s-name-owner"),
    ("casual", "martas sister is elsa", [T("martas", "sister", "elsa", ALIAS["sister"])], True, "casual lower no-apos"),
    ("casual", "louiss brother is theo", [T("louiss", "brother", "theo", ALIAS["brother"])], True, "casual lower no-apos s-owner"),
    ("casual", "my cat is luni", [T("me", "pet", "luni", pet_alias("cat"))], True, "casual lower plain-pet"),
    ("casual", "i live in branfield", [T("me", "city", "branfield", ALIAS["city"])], True, "casual lower plain-city"),
    ("casual", "nora lives in kelsow", [T("nora", "city", "kelsow", ALIAS["city"])], True, "casual lower plain-fact"),
    ("casual", "pavel works as a baker", [T("pavel", "job", "baker", ALIAS["job"])], True, "casual lower plain-job"),
    ("casual", "my boss is selma", [T("me", "boss", "selma", ALIAS["boss"])], True, "casual lower plain-boss"),
    ("casual", "tesss rabbit is bobo", [T("tesss", "pet", "bobo", pet_alias("rabbit"))], True, "casual lower no-apos s-owner"),
    ("casual", "marcuss cousin is alba", [T("marcuss", "cousin", "alba", ALIAS["cousin"])], True, "casual lower no-apos s-owner"),
    ("casual", "priyas job is nurse", [T("priyas", "job", "nurse", ALIAS["job"])], True, "casual lower no-apos"),
    ("casual", "my sister is livia", [T("me", "sister", "livia", ALIAS["sister"])], True, "casual lower plain-relative"),
    ("casual", "darios dog is kiko", [T("darios", "pet", "kiko", pet_alias("dog"))], True, "casual lower no-apos"),
    ("casual", "i speak spanish at home", [T("me", "language", "spanish", ALIAS["language"])], True, "casual lower plain-language"),
    ("casual", "samir works at halden", [T("samir", "employer", "halden", ALIAS["employer"])], True, "casual lower plain-employer"),
    ("casual", "ines studies at northfield", [T("ines", "school", "northfield", ALIAS["school"])], True, "casual lower plain-school"),
    ("casual", "my brother is renzo", [T("me", "brother", "renzo", ALIAS["brother"])], True, "casual lower plain-relative"),
    ("casual", "kostas fish is nino", [T("kostas", "pet", "nino", pet_alias("fish"))], True, "casual lower s-name-owner"),
    ("casual", "my parrot is saba", [T("me", "pet", "saba", pet_alias("parrot"))], True, "casual lower plain-pet"),
    ("casual", "tariks employer is veldt", [T("tariks", "employer", "veldt", ALIAS["employer"])], True, "casual lower no-apos"),
    ("casual", "jorunns cat is tiko", [T("jorunns", "pet", "tiko", pet_alias("cat"))], True, "casual lower no-apos s-owner"),
    ("casual", "my hometown is durnham", [T("me", "hometown", "durnham", ALIAS["hometown"])], True, "casual lower plain-hometown"),
    ("casual", "caspers horse is bruno", [T("caspers", "pet", "bruno", pet_alias("horse"))], True, "casual lower no-apos"),
    ("casual", "milenas boss is helga", [T("milenas", "boss", "helga", ALIAS["boss"])], True, "casual lower no-apos"),
    ("casual", "my neighbour is boris", [T("me", "neighbour", "boris", ALIAS["neighbour"])], True, "casual lower plain-neighbour"),
    ("casual", "oskars dog is mox", [T("oskars", "pet", "mox", pet_alias("dog"))], True, "casual lower no-apos s-owner"),
    ("casual", "zelda works at peldon college", [T("zelda", "workplace", "peldon college", ALIAS["workplace"])], True, "casual lower plain-workplace"),
    ("casual", "my cousin is tanja", [T("me", "cousin", "tanja", ALIAS["cousin"])], True, "casual lower plain-relative"),
    ("casual", "viktors sister is nadia", [T("viktors", "sister", "nadia", ALIAS["sister"])], True, "casual lower no-apos"),
    ("casual", "my hamster is pippa", [T("me", "pet", "pippa", pet_alias("hamster"))], True, "casual lower plain-pet"),
    ("casual", "felixs turtle is otto", [T("felixs", "pet", "otto", pet_alias("turtle"))], True, "casual lower no-apos s-owner"),
    ("casual", "jonass mother is greta", [T("jonass", "mother", "greta", ALIAS["mother"])], True, "casual lower no-apos s-owner"),
    ("casual", "my friend is emil", [T("me", "friend", "emil", ALIAS["friend"])], True, "casual lower plain-friend"),
    ("casual", "adeles cat is suki", [T("adeles", "pet", "suki", pet_alias("cat"))], True, "casual lower no-apos"),
    ("casual", "i work as a mason", [T("me", "job", "mason", ALIAS["job"])], True, "casual lower plain-job"),
    ("casual", "brunoss dog is wuff", [T("brunoss", "pet", "wuff", pet_alias("dog"))], True, "casual lower no-apos s-owner"),
    ("casual", "my employer is kessler", [T("me", "employer", "kessler", ALIAS["employer"])], True, "casual lower plain-employer"),
    ("casual", "sanne speaks dutch daily", [T("sanne", "language", "dutch", ALIAS["language"])], True, "casual lower plain-language"),
    # ---- casual_q 15: lowercase questions, gold ASK (u270-041..055) ----
    ("casual_q", "where does nora live", [A("nora", "city", ALIAS["city"])], True, "casual_q lower no-qmark where"),
    ("casual_q", "who is martas sister", [A("martas", "sister", ALIAS["sister"])], True, "casual_q lower no-qmark who no-apos"),
    ("casual_q", "what does pavel do?", [A("pavel", "job", ALIAS["job"])], True, "casual_q lower what-job"),
    ("casual_q", "who is my boss", [A("me", "boss", ALIAS["boss"])], True, "casual_q lower no-qmark who"),
    ("casual_q", "what language does sanne speak?", [A("sanne", "language", ALIAS["language"])], True, "casual_q lower what-language"),
    ("casual_q", "who is louiss brother", [A("louiss", "brother", ALIAS["brother"])], True, "casual_q lower no-qmark who s-owner"),
    ("casual_q", "where does dario work?", [A("dario", "employer", ALIAS["employer"])], True, "casual_q lower where-work"),
    ("casual_q", "what school does ines attend", [A("ines", "school", ALIAS["school"])], True, "casual_q lower no-qmark what-school"),
    ("casual_q", "who is selmas boss?", [A("selmas", "boss", ALIAS["boss"])], True, "casual_q lower who no-apos"),
    ("casual_q", "which city does theo live in", [A("theo", "city", ALIAS["city"])], True, "casual_q lower no-qmark which-city"),
    ("casual_q", "who is my neighbour?", [A("me", "neighbour", ALIAS["neighbour"])], True, "casual_q lower who"),
    ("casual_q", "what does tarik do for work", [A("tarik", "job", ALIAS["job"])], True, "casual_q lower no-qmark what-job"),
    ("casual_q", "who is jonass mother?", [A("jonass", "mother", ALIAS["mother"])], True, "casual_q lower who s-owner"),
    ("casual_q", "where did sanne grow up", [A("sanne", "hometown", ALIAS["hometown"])], True, "casual_q lower no-qmark where-hometown"),
    ("casual_q", "who is my cousin?", [A("me", "cousin", ALIAS["cousin"])], True, "casual_q lower who"),
    # ---- lower_trap 15: lowercase, name-like word is not a name, gold [] (u270-056..070) ----
    ("lower_trap", "april is my busiest month", [], True, "lower_trap lower month-name"),
    ("lower_trap", "my rose bush finally bloomed", [], True, "lower_trap lower flower-name"),
    ("lower_trap", "i hope it will rain tomorrow", [], True, "lower_trap lower verb-name"),
    ("lower_trap", "the bill came to twelve dollars", [], True, "lower_trap lower noun-name"),
    ("lower_trap", "my june deadline is really tight", [], True, "lower_trap lower month-name"),
    ("lower_trap", "hunter is a tough job in winter", [], True, "lower_trap lower profession-name"),
    ("lower_trap", "mark my words, the bus is late", [], True, "lower_trap lower verb-name"),
    ("lower_trap", "to be frank, i overslept again", [], True, "lower_trap lower adverb-name"),
    ("lower_trap", "the ruby glass on the shelf is red", [], True, "lower_trap lower gem-name"),
    ("lower_trap", "my iris patch by the fence is blooming", [], True, "lower_trap lower flower-name"),
    ("lower_trap", "grace is what i need most today", [], True, "lower_trap lower noun-name"),
    ("lower_trap", "the chase after the bus was wild", [], True, "lower_trap lower noun-name"),
    ("lower_trap", "may is always hectic at work", [], True, "lower_trap lower month-name"),
    ("lower_trap", "reed beds line the old canal", [], True, "lower_trap lower plant-name"),
    ("lower_trap", "pearl buttons suit the blue coat", [], True, "lower_trap lower material-name"),
    # ---- clean 30: normal typing control, TEACH (u270-071..100) ----
    ("clean", "My dog is Pip.", [T("me", "pet", "Pip", pet_alias("dog"))], True, "clean control plain-pet"),
    ("clean", "Nora lives in Kelsow.", [T("Nora", "city", "Kelsow", ALIAS["city"])], True, "clean control plain-city"),
    ("clean", "Pavel works as a baker.", [T("Pavel", "job", "baker", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "My sister is Livia.", [T("me", "sister", "Livia", ALIAS["sister"])], True, "clean control plain-relative"),
    ("clean", "Kiko is my dog.", [T("me", "pet", "Kiko", pet_alias("dog"))], True, "clean control plain-pet"),
    ("clean", "I speak Spanish at home.", [T("me", "language", "Spanish", ALIAS["language"])], True, "clean control plain-language"),
    ("clean", "Elsa is a nurse.", [T("Elsa", "job", "nurse", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "My boss is Selma.", [T("me", "boss", "Selma", ALIAS["boss"])], True, "clean control plain-boss"),
    ("clean", "Tessa has a rabbit, Bobo.", [T("Tessa", "pet", "Bobo", pet_alias("rabbit"))], True, "clean control plain-pet"),
    ("clean", "Samir works at Halden.", [T("Samir", "employer", "Halden", ALIAS["employer"])], True, "clean control plain-employer"),
    ("clean", "Ines studies at Northfield.", [T("Ines", "school", "Northfield", ALIAS["school"])], True, "clean control plain-school"),
    ("clean", "My brother is Renzo.", [T("me", "brother", "Renzo", ALIAS["brother"])], True, "clean control plain-relative"),
    ("clean", "The cat Luni is mine.", [T("me", "pet", "Luni", pet_alias("cat"))], True, "clean control plain-pet"),
    ("clean", "Tarik works for Veldt.", [T("Tarik", "employer", "Veldt", ALIAS["employer"])], True, "clean control plain-employer"),
    ("clean", "My hometown is Durnham.", [T("me", "hometown", "Durnham", ALIAS["hometown"])], True, "clean control plain-hometown"),
    ("clean", "Casper owns a horse, Bruno.", [T("Casper", "pet", "Bruno", pet_alias("horse"))], True, "clean control plain-pet"),
    ("clean", "Milena is my boss.", [T("me", "boss", "Milena", ALIAS["boss"])], True, "clean control plain-boss"),
    ("clean", "My neighbour is Boris.", [T("me", "neighbour", "Boris", ALIAS["neighbour"])], True, "clean control plain-neighbour"),
    ("clean", "Oskar is a driver.", [T("Oskar", "job", "driver", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "Zelda works at Peldon College.", [T("Zelda", "workplace", "Peldon College", ALIAS["workplace"])], True, "clean control plain-workplace"),
    ("clean", "My cousin is Tanja.", [T("me", "cousin", "Tanja", ALIAS["cousin"])], True, "clean control plain-relative"),
    ("clean", "Viktor is a pilot.", [T("Viktor", "job", "pilot", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "My hamster is Pippa.", [T("me", "pet", "Pippa", pet_alias("hamster"))], True, "clean control plain-pet"),
    ("clean", "Felix is a singer.", [T("Felix", "job", "singer", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "My friend is Emil.", [T("me", "friend", "Emil", ALIAS["friend"])], True, "clean control plain-friend"),
    ("clean", "Adele is a mason.", [T("Adele", "job", "mason", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "I work as a clerk.", [T("me", "job", "clerk", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "Bruno is a dentist.", [T("Bruno", "job", "dentist", ALIAS["job"])], True, "clean control plain-job"),
    ("clean", "My employer is Kessler.", [T("me", "employer", "Kessler", ALIAS["employer"])], True, "clean control plain-employer"),
    ("clean", "Sanne speaks Dutch daily.", [T("Sanne", "language", "Dutch", ALIAS["language"])], True, "clean control plain-language"),
]

FAMILIES = ["casual", "casual_q", "lower_trap", "clean"]
COUNTS = {"casual": 40, "casual_q": 15, "lower_trap": 15, "clean": 30}
TRAP_WORDS = ["april", "rose", "will", "bill", "june", "hunter", "mark", "frank",
              "ruby", "iris", "grace", "chase", "may", "reed", "pearl"]


def check():
    assert len(ITEMS) == 100, f"want 100 items, have {len(ITEMS)}"
    got = {}
    for fam, _, _, _, _ in ITEMS:
        got[fam] = got.get(fam, 0) + 1
    assert got == COUNTS, f"family counts {got} != {COUNTS}"
    # family-block order
    fams = [f for f, _, _, _, _ in ITEMS]
    assert fams == ["casual"] * 40 + ["casual_q"] * 15 + ["lower_trap"] * 15 + ["clean"] * 30, "family-block order broken"
    turns = [t for _, t, _, _, _ in ITEMS]
    assert len(set(turns)) == 100, "duplicate turn"
    # fictional-name guard: spec/task examples must not appear verbatim
    banned = ["ria van doorn", "port of sela", "jamess dog is rex", "iris cat is bo"]
    for t in turns:
        for b in banned:
            assert b not in t.lower(), f"banned wording in turn: {t}"
    s_owner = 0
    no_q = 0
    for fam, turn, gold, clear, notes in ITEMS:
        assert isinstance(clear, bool), f"clear not bool: {turn}"
        assert isinstance(notes, str) and notes, f"notes empty: {turn}"
        if fam in ("casual", "casual_q", "lower_trap"):
            assert turn == turn.lower(), f"not lowercase: {turn}"
        else:
            assert turn != turn.lower(), f"clean turn has no capitals: {turn}"
        if fam in ("casual", "clean"):
            assert gold, f"empty gold: {turn}"
            for fr in gold:
                assert set(fr) == {"act", "subject", "relation", "relation_aliases", "value"}, f"TEACH keys: {fr}"
                assert fr["act"] == "TEACH"
                assert fr["subject"] == "me" or fr["subject"] in turn, f"subject not in turn: {fr} :: {turn}"
                assert fr["value"] in turn, f"value not in turn: {fr} :: {turn}"
                if fr["relation"] == "pet":
                    assert fr["relation_aliases"][0] in turn, f"species not in turn: {fr} :: {turn}"
                    for w in ("pet", "animal", "companion"):
                        assert w in fr["relation_aliases"], f"pet alias missing {w}: {turn}"
                else:
                    assert fr["relation_aliases"] == ALIAS[fr["relation"]], f"alias list drift: {turn}"
            if "s-owner" in notes or "s-name-owner" in notes:
                s_owner += 1
        elif fam == "casual_q":
            assert gold, f"empty gold: {turn}"
            for fr in gold:
                assert set(fr) == {"act", "subject", "relation", "chain", "relation_aliases", "chain_aliases"}, f"ASK keys: {fr}"
                assert fr["act"] == "ASK"
                assert fr["chain"] is None and fr["chain_aliases"] is None
                assert fr["subject"] == "me" or fr["subject"] in turn, f"ASK subject not in turn: {fr} :: {turn}"
                assert fr["relation_aliases"] == ALIAS[fr["relation"]] or (
                    fr["relation"] == "pet"), f"alias drift: {turn}"
            if "?" not in turn:
                no_q += 1
        else:
            assert gold == [], f"trap gold not empty: {turn}"
            assert any(w in turn for w in TRAP_WORDS), f"trap word missing: {turn}"
    assert s_owner >= 6, f"s-owner items {s_owner} < 6"
    assert no_q >= 5, f"casual_q without '?' {no_q} < 5"
    print(f"SELF-CHECK PASS: 100 items {COUNTS}; s-owner {s_owner}; casual_q no-qmark {no_q}")
    print(f"lowercase turns: 70/70 casual-family; clean capitalised: 30/30")


def main():
    check()
    outdir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "panel.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for i, (fam, turn, gold, clear, notes) in enumerate(ITEMS, start=1):
            rec = {"id": f"u270-{i:03d}", "family": fam, "turn": turn,
                   "gold": gold, "clear": clear, "notes": notes}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"WROTE {out} ({len(ITEMS)} lines)")


if __name__ == "__main__":
    sys.exit(main())
