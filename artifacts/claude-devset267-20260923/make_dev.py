"""make_dev.py for exp 267 dev set (DEV, tunable, not a test panel).
Holds 120 items by hand, writes dev.jsonl deterministically, runs self-checks.
Schema matches earpanel264-spec: {id, family, turn, gold, clear, notes}.
TEACH: {act, subject, relation, relation_aliases, value}
ASK: {act, subject, relation, chain, relation_aliases, chain_aliases}
Fictional names/places only. No we/us/our owners.
"""
import json
import pathlib

OUT_DIR = pathlib.Path(__file__).parent
DEV_PATH = OUT_DIR / "dev.jsonl"

CITY = ["city", "town", "lives in"]
JOB = ["job", "occupation", "works as"]
WORKPLACE = ["workplace", "works at", "work location"]
EMPLOYER = ["employer", "works for", "company"]
SCHOOL = ["school", "studies at", "college"]
LANGUAGE = ["language", "speaks"]
SISTER = ["sister", "sisters"]
BROTHER = ["brother", "brothers"]
COUSIN = ["cousin", "cousins"]
SPOUSE = ["spouse", "wife", "husband", "married to"]
BOSS = ["boss", "manager"]
PLACE_BIRTH = ["place_of_birth", "born in", "birthplace"]
HOMETOWN = ["hometown", "home town", "grew up in"]
NEIGHBOUR = ["neighbour", "neighbor"]
TEACHER = ["teacher", "instructor"]
DOCTOR = ["doctor", "physician"]
HOBBY = ["hobby", "pastime"]
FOOD = ["favourite_food", "favorite food"]
SPORT = ["favourite_sport", "favorite sport"]
INSTRUMENT = ["instrument", "plays"]
PET_DOG = ["dog", "pet", "animal", "companion"]
PET_CAT = ["cat", "pet", "animal", "companion"]
PET_RABBIT = ["rabbit", "pet", "animal", "companion"]


def T(subject, relation, aliases, value):
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": aliases, "value": value}


def A(subject, relation, aliases):
    return {"act": "ASK", "subject": subject, "relation": relation,
            "chain": None, "relation_aliases": aliases, "chain_aliases": None}


ITEMS = [
    # 50 plain teaches d267-001..050
    ("d267-001", "plain_teach", "I live in Brindleton.", [T("me", "city", CITY, "Brindleton")], True, "plain"),
    ("d267-002", "plain_teach", "I work as a baker.", [T("me", "job", JOB, "baker")], True, "plain"),
    ("d267-003", "plain_teach", "I work at Halden Works.", [T("me", "workplace", WORKPLACE, "Halden Works")], True, "plain"),
    ("d267-004", "plain_teach", "My sister Tessa Maro lives in Kellerton.", [T("Tessa Maro", "city", CITY, "Kellerton")], True, "plain"),
    ("d267-005", "plain_teach", "My brother Dain Kessler works as a carpenter.", [T("Dain Kessler", "job", JOB, "carpenter")], True, "plain"),
    ("d267-006", "plain_teach", "My cousin Petra Lonn speaks Ilvari.", [T("Petra Lonn", "language", LANGUAGE, "Ilvari")], True, "plain"),
    ("d267-007", "plain_teach", "I was born in Tarnwick.", [T("me", "place_of_birth", PLACE_BIRTH, "Tarnwick")], True, "plain"),
    ("d267-008", "plain_teach", "My hometown is Millow.", [T("me", "hometown", HOMETOWN, "Millow")], True, "plain"),
    ("d267-009", "plain_teach", "My dog is called Brisket.", [T("me", "pet", PET_DOG, "Brisket")], True, "plain pet"),
    ("d267-010", "plain_teach", "I study at Brindle College.", [T("me", "school", SCHOOL, "Brindle College")], True, "plain"),
    ("d267-011", "plain_teach", "My neighbour Kess Alda is a potter.", [T("Kess Alda", "job", JOB, "potter")], True, "plain"),
    ("d267-012", "plain_teach", "My teacher Elin Solen lives in Vennford.", [T("Elin Solen", "city", CITY, "Vennford")], True, "plain"),
    ("d267-013", "plain_teach", "My doctor Corin Pell works at Tormere Clinic.", [T("Corin Pell", "workplace", WORKPLACE, "Tormere Clinic")], True, "plain"),
    ("d267-014", "plain_teach", "I speak Kessic.", [T("me", "language", LANGUAGE, "Kessic")], True, "plain"),
    ("d267-015", "plain_teach", "My spouse Liora Venn works as a weaver.", [T("Liora Venn", "job", JOB, "weaver")], True, "plain"),
    ("d267-016", "plain_teach", "My boss Brenna Tove lives in Corravale.", [T("Brenna Tove", "city", CITY, "Corravale")], True, "plain"),
    ("d267-017", "plain_teach", "My brother Joren Kade lives in Lissarra.", [T("Joren Kade", "city", CITY, "Lissarra")], True, "plain"),
    ("d267-018", "plain_teach", "My sister Wren Hallo works at Draymouth Library.", [T("Wren Hallo", "workplace", WORKPLACE, "Draymouth Library")], True, "plain"),
    ("d267-019", "plain_teach", "My cat is called Miso.", [T("me", "pet", PET_CAT, "Miso")], True, "plain pet"),
    ("d267-020", "plain_teach", "I play the fiddle.", [T("me", "instrument", INSTRUMENT, "fiddle")], True, "plain"),
    ("d267-021", "plain_teach", "My hobby is star-charting.", [T("me", "hobby", HOBBY, "star-charting")], True, "plain"),
    ("d267-022", "plain_teach", "My favourite food is mushroom pie.", [T("me", "favourite_food", FOOD, "mushroom pie")], True, "plain"),
    ("d267-023", "plain_teach", "My favourite sport is stone-skipping.", [T("me", "favourite_sport", SPORT, "stone-skipping")], True, "plain"),
    ("d267-024", "plain_teach", "My cousin Dara Quill lives in Ostarvik.", [T("Dara Quill", "city", CITY, "Ostarvik")], True, "plain"),
    ("d267-025", "plain_teach", "My uncle Fenwick Dray works as a blacksmith.", [T("Fenwick Dray", "job", JOB, "blacksmith")], True, "plain"),
    ("d267-026", "plain_teach", "My aunt Mabel Corra speaks Drayan.", [T("Mabel Corra", "language", LANGUAGE, "Drayan")], True, "plain"),
    ("d267-027", "plain_teach", "I work for Vennford Bakery.", [T("me", "employer", EMPLOYER, "Vennford Bakery")], True, "plain"),
    ("d267-028", "plain_teach", "My sister Isolde Fenna studies at Corra School.", [T("Isolde Fenna", "school", SCHOOL, "Corra School")], True, "plain"),
    ("d267-029", "plain_teach", "My brother Soren Vessa was born in Pellwick.", [T("Soren Vessa", "place_of_birth", PLACE_BIRTH, "Pellwick")], True, "plain"),
    ("d267-030", "plain_teach", "My rabbit is called Clover.", [T("me", "pet", PET_RABBIT, "Clover")], True, "plain pet"),
    ("d267-031", "plain_teach", "I live in Zindle.", [T("me", "city", CITY, "Zindle")], True, "plain"),
    ("d267-032", "plain_teach", "My friend Harlow Lind works as a gardener.", [T("Harlow Lind", "job", JOB, "gardener")], True, "plain"),
    ("d267-033", "plain_teach", "My neighbour Osta Mere speaks Vennic.", [T("Osta Mere", "language", LANGUAGE, "Vennic")], True, "plain"),
    ("d267-034", "plain_teach", "My teacher Talon Osta works at Venn Academy.", [T("Talon Osta", "workplace", WORKPLACE, "Venn Academy")], True, "plain"),
    ("d267-035", "plain_teach", "I was born in Kestrelwick.", [T("me", "place_of_birth", PLACE_BIRTH, "Kestrelwick")], True, "plain"),
    ("d267-036", "plain_teach", "My hometown is Draymouth.", [T("me", "hometown", HOMETOWN, "Draymouth")], True, "plain"),
    ("d267-037", "plain_teach", "My sister Petra Solen works as a librarian.", [T("Petra Solen", "job", JOB, "librarian")], True, "plain"),
    ("d267-038", "plain_teach", "My brother Corin Talon lives in Tormere.", [T("Corin Talon", "city", CITY, "Tormere")], True, "plain"),
    ("d267-039", "plain_teach", "My cousin Elin Dray works for Corravale Press.", [T("Elin Dray", "employer", EMPLOYER, "Corravale Press")], True, "plain"),
    ("d267-040", "plain_teach", "I study at Lissarra School.", [T("me", "school", SCHOOL, "Lissarra School")], True, "plain"),
    ("d267-041", "plain_teach", "My dog is called Pebble.", [T("me", "pet", PET_DOG, "Pebble")], True, "plain pet"),
    ("d267-042", "plain_teach", "My cat is called Sable.", [T("me", "pet", PET_CAT, "Sable")], True, "plain pet"),
    ("d267-043", "plain_teach", "I play the tin whistle.", [T("me", "instrument", INSTRUMENT, "tin whistle")], True, "plain"),
    ("d267-044", "plain_teach", "My boss Harlow Vessa lives in Ostarvik.", [T("Harlow Vessa", "city", CITY, "Ostarvik")], True, "plain"),
    ("d267-045", "plain_teach", "My spouse Dain Solen speaks Kessic.", [T("Dain Solen", "language", LANGUAGE, "Kessic")], True, "plain"),
    ("d267-046", "plain_teach", "My sister Mabel Lind works at Tormere Clinic.", [T("Mabel Lind", "workplace", WORKPLACE, "Tormere Clinic")], True, "plain"),
    ("d267-047", "plain_teach", "My brother Fenwick Quill was born in Vennford.", [T("Fenwick Quill", "place_of_birth", PLACE_BIRTH, "Vennford")], True, "plain"),
    ("d267-048", "plain_teach", "I work as a driver.", [T("me", "job", JOB, "driver")], True, "plain"),
    ("d267-049", "plain_teach", "I live in Pellwick.", [T("me", "city", CITY, "Pellwick")], True, "plain"),
    ("d267-050", "plain_teach", "My cousin Soren Hallo lives in Corravale.", [T("Soren Hallo", "city", CITY, "Corravale")], True, "plain"),
    # 15 plural relatives R10 d267-051..065
    ("d267-051", "plural_relative", "My two sisters, Lina Maro and Tessa Venn, live in Brindleton.", [T("Lina Maro", "city", CITY, "Brindleton"), T("Tessa Venn", "city", CITY, "Brindleton")], True, "R10"),
    ("d267-052", "plural_relative", "My two brothers, Dain Kade and Joren Pell, work at Halden Works.", [T("Dain Kade", "workplace", WORKPLACE, "Halden Works"), T("Joren Pell", "workplace", WORKPLACE, "Halden Works")], True, "R10"),
    ("d267-053", "plural_relative", "Both my cousins, Petra Quill and Milo Venn, speak Ilvari.", [T("Petra Quill", "language", LANGUAGE, "Ilvari"), T("Milo Venn", "language", LANGUAGE, "Ilvari")], True, "R10"),
    ("d267-054", "plural_relative", "My two aunts, Mabel Dray and Isolde Corra, live in Kellerton.", [T("Mabel Dray", "city", CITY, "Kellerton"), T("Isolde Corra", "city", CITY, "Kellerton")], True, "R10"),
    ("d267-055", "plural_relative", "My two uncles, Fenwick Solen and Soren Lind, work as carpenters.", [T("Fenwick Solen", "job", JOB, "carpenters"), T("Soren Lind", "job", JOB, "carpenters")], True, "R10"),
    ("d267-056", "plural_relative", "My two sisters, Wren Kade and Elin Hallo, study at Brindle College.", [T("Wren Kade", "school", SCHOOL, "Brindle College"), T("Elin Hallo", "school", SCHOOL, "Brindle College")], True, "R10"),
    ("d267-057", "plural_relative", "My two brothers, Corin Dray and Talon Mere, were born in Tarnwick.", [T("Corin Dray", "place_of_birth", PLACE_BIRTH, "Tarnwick"), T("Talon Mere", "place_of_birth", PLACE_BIRTH, "Tarnwick")], True, "R10"),
    ("d267-058", "plural_relative", "Both my neighbours, Kess Quill and Osta Venn, live in Millow.", [T("Kess Quill", "city", CITY, "Millow"), T("Osta Venn", "city", CITY, "Millow")], True, "R10"),
    ("d267-059", "plural_relative", "My two cousins, Dara Solen and Harlow Talon, work for Corravale Press.", [T("Dara Solen", "employer", EMPLOYER, "Corravale Press"), T("Harlow Talon", "employer", EMPLOYER, "Corravale Press")], True, "R10"),
    ("d267-060", "plural_relative", "My two sisters, Liora Pell and Brenna Lind, speak Kessic.", [T("Liora Pell", "language", LANGUAGE, "Kessic"), T("Brenna Lind", "language", LANGUAGE, "Kessic")], True, "R10"),
    ("d267-061", "plural_relative", "My two brothers, Fenwick Hallo and Soren Quill, live in Vennford.", [T("Fenwick Hallo", "city", CITY, "Vennford"), T("Soren Quill", "city", CITY, "Vennford")], True, "R10"),
    ("d267-062", "plural_relative", "My two cousins, Isolde Venn and Mabel Hallo, play the fiddle.", [T("Isolde Venn", "instrument", INSTRUMENT, "fiddle"), T("Mabel Hallo", "instrument", INSTRUMENT, "fiddle")], True, "R10"),
    ("d267-063", "plural_relative", "Both my sisters, Petra Kade and Wren Solen, work as bakers.", [T("Petra Kade", "job", JOB, "bakers"), T("Wren Solen", "job", JOB, "bakers")], True, "R10"),
    ("d267-064", "plural_relative", "My two brothers, Dain Venn and Corin Quill, study at Venn Academy.", [T("Dain Venn", "school", SCHOOL, "Venn Academy"), T("Corin Quill", "school", SCHOOL, "Venn Academy")], True, "R10"),
    ("d267-065", "plural_relative", "My two cousins, Elin Venn and Tessa Quill, live in Ostarvik and speak Drayan.", [T("Elin Venn", "city", CITY, "Ostarvik"), T("Tessa Quill", "city", CITY, "Ostarvik"), T("Elin Venn", "language", LANGUAGE, "Drayan"), T("Tessa Quill", "language", LANGUAGE, "Drayan")], True, "R10"),
    # 15 typo or filler d267-066..080
    ("d267-066", "typo_filler", "My sister Tessa Maro lievs in Kellerton.", [T("Tessa Maro", "city", CITY, "Kellerton")], True, "R13 typo"),
    ("d267-067", "typo_filler", "My brother Dain Kessler wroks as a carpenter.", [T("Dain Kessler", "job", JOB, "carpenter")], True, "R13 typo"),
    ("d267-068", "typo_filler", "Um, my cousin Petra Lonn speaks Ilvari.", [T("Petra Lonn", "language", LANGUAGE, "Ilvari")], True, "filler"),
    ("d267-069", "typo_filler", "My neighbour Kess Alda is a potter, you know.", [T("Kess Alda", "job", JOB, "potter")], True, "filler"),
    ("d267-070", "typo_filler", "My cousin Dara Quill spoeks Drayan.", [T("Dara Quill", "language", LANGUAGE, "Drayan")], True, "R13 typo"),
    ("d267-071", "typo_filler", "Like, my brother Joren Kade lives in Lissarra.", [T("Joren Kade", "city", CITY, "Lissarra")], True, "filler"),
    ("d267-072", "typo_filler", "My sister Wren Hallo wrok at Draymouth Library.", [T("Wren Hallo", "workplace", WORKPLACE, "Draymouth Library")], True, "R13 typo"),
    ("d267-073", "typo_filler", "My brother Soren Vessa was brn in Pellwick.", [T("Soren Vessa", "place_of_birth", PLACE_BIRTH, "Pellwick")], True, "R13 typo"),
    ("d267-074", "typo_filler", "My cousin Milo Venn lieve in Ostarvik.", [T("Milo Venn", "city", CITY, "Ostarvik")], True, "R13 typo"),
    ("d267-075", "typo_filler", "You know, my aunt Mabel Corra speaks Drayan.", [T("Mabel Corra", "language", LANGUAGE, "Drayan")], True, "filler"),
    ("d267-076", "typo_filler", "My boss Brenna Tove livez in Corravale.", [T("Brenna Tove", "city", CITY, "Corravale")], True, "R13 typo"),
    ("d267-077", "typo_filler", "Um, I live in Brindleton, like.", [T("me", "city", CITY, "Brindleton")], True, "filler"),
    ("d267-078", "typo_filler", "My sister Isolde Fenna studie at Corra School.", [T("Isolde Fenna", "school", SCHOOL, "Corra School")], True, "R13 typo"),
    ("d267-079", "typo_filler", "My brother Corin Talon livve in Tormere.", [T("Corin Talon", "city", CITY, "Tormere")], True, "R13 typo"),
    ("d267-080", "typo_filler", "Like, my cousin Soren Hallo speaks Vennic, um.", [T("Soren Hallo", "language", LANGUAGE, "Vennic")], True, "filler"),
    # 10 relation traps R16 d267-081..090
    ("d267-081", "relation_trap", "I live near Tarnwick, in Millow.", [T("me", "city", CITY, "Millow")], True, "R16"),
    ("d267-082", "relation_trap", "I work with Milo Dray at Brindle Depot.", [T("me", "workplace", WORKPLACE, "Brindle Depot")], True, "R16"),
    ("d267-083", "relation_trap", "My brother Dain Kessler married Sana Rell.", [T("Dain Kessler", "spouse", SPOUSE, "Sana Rell")], True, "R16"),
    ("d267-084", "relation_trap", "I used to work at Halden Works, now I work at Brindle Depot.", [T("me", "workplace", WORKPLACE, "Brindle Depot")], True, "R16"),
    ("d267-085", "relation_trap", "I work for Vennford Bakery with Harlow Lind.", [T("me", "employer", EMPLOYER, "Vennford Bakery")], True, "R16"),
    ("d267-086", "relation_trap", "My sister Tessa Maro married Fenwick Dray.", [T("Tessa Maro", "spouse", SPOUSE, "Fenwick Dray")], True, "R16"),
    ("d267-087", "relation_trap", "I live near Kellerton, in Brindleton.", [T("me", "city", CITY, "Brindleton")], True, "R16"),
    ("d267-088", "relation_trap", "I used to live in Tarnwick, now I live in Millow.", [T("me", "city", CITY, "Millow")], True, "R16"),
    ("d267-089", "relation_trap", "My cousin's wife, Liora Pell, is a teacher.", [T("Liora Pell", "job", JOB, "teacher")], True, "R16"),
    ("d267-090", "relation_trap", "I work with Brenna Tove for Corravale Press.", [T("me", "employer", EMPLOYER, "Corravale Press")], True, "R16"),
    # 10 stale values R17 d267-091..100
    ("d267-091", "stale_value", "I moved from Kellerton to Brindleton.", [T("me", "city", CITY, "Brindleton")], True, "R17"),
    ("d267-092", "stale_value", "I live in Millow now, it used to be Tarnwick.", [T("me", "city", CITY, "Millow")], True, "R17"),
    ("d267-093", "stale_value", "I work at Brindle Depot now, I used to work at Halden Works.", [T("me", "workplace", WORKPLACE, "Brindle Depot")], True, "R17"),
    ("d267-094", "stale_value", "My sister Tessa Maro moved from Vennford to Kellerton.", [T("Tessa Maro", "city", CITY, "Kellerton")], True, "R17"),
    ("d267-095", "stale_value", "I speak Kessic now, I used to speak Ilvari.", [T("me", "language", LANGUAGE, "Kessic")], True, "R17"),
    ("d267-096", "stale_value", "My brother Dain Kessler switched from carpentry to baking, he works as a baker now.", [T("Dain Kessler", "job", JOB, "baker")], True, "R17"),
    ("d267-097", "stale_value", "I studied at Corra School, now I study at Brindle College.", [T("me", "school", SCHOOL, "Brindle College")], True, "R17"),
    ("d267-098", "stale_value", "My cousin Petra Lonn moved from Ostarvik to Vennford.", [T("Petra Lonn", "city", CITY, "Vennford")], True, "R17"),
    ("d267-099", "stale_value", "I was listed as living in Tarnwick, now I live in Millow.", [T("me", "city", CITY, "Millow")], True, "R17"),
    ("d267-100", "stale_value", "My boss is now Brenna Tove, it used to be Harlow Vessa.", [T("me", "boss", BOSS, "Brenna Tove")], True, "R17"),
    # 10 no-save d267-101..110
    ("d267-101", "no_save", "Let's say my sister lives in Kellerton.", [], True, "no_save pretend"),
    ("d267-102", "no_save", "Imagine I work as a baker in Brindleton.", [], True, "no_save pretend"),
    ("d267-103", "no_save", "Suppose my brother works at Halden Works.", [], True, "no_save pretend"),
    ("d267-104", "no_save", "I want to be a teacher, training to be a teacher in Corravale.", [], True, "no_save plan"),
    ("d267-105", "no_save", "I am going to move to Millow next spring.", [], True, "no_save plan"),
    ("d267-106", "no_save", "I plan to study at Brindle College next year.", [], True, "no_save plan"),
    ("d267-107", "no_save", "my sister lives in kellerton, right", [], True, "no_save R2 noq lower"),
    ("d267-108", "no_save", "so i live in brindleton", [], True, "no_save R2 noq lower"),
    ("d267-109", "no_save", "Pretend my cousin speaks Ilvari.", [], True, "no_save pretend"),
    ("d267-110", "no_save", "What if my brother lived in Tarnwick.", [], True, "no_save pretend"),
    # 10 questions d267-111..120
    ("d267-111", "questions", "where do i live", [A("me", "city", CITY)], True, "questions lower noq"),
    ("d267-112", "questions", "Where does Tessa Maro live?", [A("Tessa Maro", "city", CITY)], True, "questions"),
    ("d267-113", "questions", "What does Dain Kessler do for work?", [A("Dain Kessler", "job", JOB)], True, "questions"),
    ("d267-114", "questions", "Where does Petra Lonn work?", [A("Petra Lonn", "workplace", WORKPLACE)], True, "questions"),
    ("d267-115", "questions", "What language does Milo Venn speak?", [A("Milo Venn", "language", LANGUAGE)], True, "questions"),
    ("d267-116", "questions", "Where was Soren Vessa born?", [A("Soren Vessa", "place_of_birth", PLACE_BIRTH)], True, "questions"),
    ("d267-117", "questions", "Where does Wren Hallo study?", [A("Wren Hallo", "school", SCHOOL)], True, "questions"),
    ("d267-118", "questions", "Who is my boss?", [A("me", "boss", BOSS)], True, "questions"),
    ("d267-119", "questions", "What is my favourite food?", [A("me", "favourite_food", FOOD)], True, "questions"),
    ("d267-120", "questions", "where does my cousin Dara Quill live", [A("Dara Quill", "city", CITY)], True, "questions lower noq"),
]


def check():
    assert len(ITEMS) == 120, f"count {len(ITEMS)}"
    from collections import Counter
    fam = Counter(i[1] for i in ITEMS)
    assert fam["plain_teach"] == 50, fam
    assert fam["plural_relative"] == 15, fam
    assert fam["typo_filler"] == 15, fam
    assert fam["relation_trap"] == 10, fam
    assert fam["stale_value"] == 10, fam
    assert fam["no_save"] == 10, fam
    assert fam["questions"] == 10, fam
    turns = [i[2] for i in ITEMS]
    assert len(set(turns)) == 120, "duplicate turn"
    ids = [i[0] for i in ITEMS]
    assert ids == [f"d267-{n:03d}" for n in range(1, 121)], "ids must be d267-001..120 in order"
    banned = ["Ria van Doorn", "Port of Sela"]
    for _id, _fam, turn, gold, clear, notes in ITEMS:
        for b in banned:
            assert b not in turn, f"{_id} reuses spec example {b}"
        assert isinstance(clear, bool)
        assert isinstance(notes, str) and len(notes) > 0
        assert isinstance(gold, list)
        for fr in gold:
            if fr["act"] == "TEACH":
                assert set(fr.keys()) == {"act", "subject", "relation", "relation_aliases", "value"}, fr
                assert isinstance(fr["relation_aliases"], list) and len(fr["relation_aliases"]) >= 2
                if fr["relation"] == "pet":
                    low = [a.lower() for a in fr["relation_aliases"]]
                    assert "pet" in low and "animal" in low and "companion" in low, fr
                    assert any(s in low for s in ("dog", "cat", "rabbit")), fr
                if fr["subject"] != "me":
                    assert fr["subject"] in turn, f"{_id} subject missing: {fr['subject']!r} not in turn"
                assert fr["value"] in turn, f"{_id} value missing: {fr['value']!r} not in turn"
                assert "_" in fr["relation"] or fr["relation"].islower(), fr
            elif fr["act"] == "ASK":
                assert set(fr.keys()) == {"act", "subject", "relation", "chain", "relation_aliases", "chain_aliases"}, fr
                assert fr["chain"] is None and fr["chain_aliases"] is None
                if fr["subject"] != "me":
                    assert fr["subject"] in turn, f"{_id} ask subject missing"
            else:
                raise AssertionError(f"{_id} bad act")
    # no we/us/our owners
    import re
    for _id, _fam, turn, gold, clear, notes in ITEMS:
        assert not re.search(r"\b(our|ours|ourselves|we\b|us\b)", turn, flags=re.IGNORECASE), f"{_id} has we/our owner: {turn!r}"
    print("self-checks OK", dict(fam))


def main():
    check()
    with open(DEV_PATH, "w", encoding="utf-8") as f:
        for _id, _fam, turn, gold, clear, notes in ITEMS:
            obj = {"id": _id, "family": _fam, "turn": turn, "gold": gold, "clear": clear, "notes": notes}
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"wrote {DEV_PATH} ({len(ITEMS)} lines)")


if __name__ == "__main__":
    main()
