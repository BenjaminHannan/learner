"""Ear panel 261b writer. Holds all 150 items by hand, writes panel.jsonl
deterministically, and runs self-checks (family counts, dedup, span check,
R1-R14 quotas, lower/typo/noq counts, schema exactness).

Run from the repo root:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-earpanel261b-20260923/make_panel.py
"""

import json
import os

OUT_DIR = os.path.join("artifacts", "claude-earpanel261b-20260923")

ALIASES = {
    "city": ["city", "town", "lives in", "residence"],
    "employer": ["employer", "company", "works for", "firm"],
    "workplace": ["workplace", "works at", "employer", "office"],
    "job": ["job", "occupation", "profession", "role"],
    "boss": ["boss", "manager", "supervisor"],
    "sister": ["sister", "sis", "sibling"],
    "brother": ["brother", "bro", "sibling"],
    "spouse": ["spouse", "husband", "wife", "partner"],
    "language": ["language", "speaks", "tongue"],
    "hometown": ["hometown", "grew up in", "home town"],
    "place_of_birth": ["place_of_birth", "born in", "birthplace"],
    "school": ["school", "studies at", "college", "university"],
    "neighbour": ["neighbour", "neighbor", "next door"],
    "cousin": ["cousin", "cous"],
    "mother": ["mother", "mum", "mom", "parent"],
    "husband": ["husband", "spouse", "partner"],
    "step_sister": ["step_sister", "step sister", "stepsister"],
    "half_brother": ["half_brother", "half brother", "half-brother"],
    "mother_in_law": ["mother_in_law", "mother-in-law"],
    "grandfather": ["grandfather", "grandpa", "grandad"],
    "great_aunt": ["great_aunt", "great aunt", "grandaunt"],
    "housemate": ["housemate", "roommate", "lives with"],
    "instrument": ["instrument", "plays", "plays instrument"],
    "favourite_food": ["favourite_food", "favourite dish", "loves to eat"],
    "hobby": ["hobby", "pastime", "does for fun"],
    "teacher": ["teacher", "tutor", "instructor"],
    "doctor": ["doctor", "physician", "GP"],
    "friend": ["friend", "buddy", "pal"],
    "uncle": ["uncle", "unc"],
    "son": ["son", "boy", "child"],
}

PET_ALIASES = {
    "dog": ["dog", "pet", "animal", "companion"],
    "cat": ["cat", "pet", "animal", "companion"],
}

RELATIVES = {
    "sister", "brother", "cousin", "mother", "father", "husband", "wife",
    "son", "uncle", "great_aunt", "grandfather", "grandmother",
    "step_sister", "half_brother", "mother_in_law", "spouse",
}


def T(subject, relation, value, species=None):
    if relation == "pet":
        assert species in PET_ALIASES, species
        aliases = PET_ALIASES[species]
    else:
        aliases = ALIASES[relation]
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": aliases, "value": value}


def Q(subject, relation, species=None):
    if relation == "pet":
        assert species in PET_ALIASES, species
        aliases = PET_ALIASES[species]
    else:
        aliases = ALIASES[relation]
    return {"act": "ASK", "subject": subject, "relation": relation,
            "chain": None, "relation_aliases": aliases, "chain_aliases": None}


def Q2(subject, first, second):
    aliases2 = ALIASES[second]
    return {"act": "ASK", "subject": subject, "relation": second,
            "chain": [first, second], "relation_aliases": aliases2,
            "chain_aliases": [ALIASES[first], aliases2]}


def it(i, family, turn, gold, clear, notes):
    return {"id": "e261b-%03d" % i, "family": family, "turn": turn,
            "gold": gold, "clear": clear, "notes": notes}


ITEMS = [
    # plain_teach 001-025
    it(1, "plain_teach", "Lara lives in Vexford near the old cannery.",
       [T("Lara", "city", "Vexford")], True, "plain"),
    it(2, "plain_teach", "Bram works for Copperline Press as a driver.",
       [T("Bram", "employer", "Copperline Press")], True, "plain"),
    it(3, "plain_teach", "Caspian is a night-shift baker who loves rye bread.",
       [T("Caspian", "job", "baker")], True, "plain"),
    it(4, "plain_teach", "Dara speaks Korean at home with her parents.",
       [T("Dara", "language", "Korean")], True, "plain"),
    it(5, "plain_teach", "Juno was born in Tarnwick during the harbor festival.",
       [T("Juno", "place_of_birth", "Tarnwick")], True, "plain"),
    it(6, "plain_teach", "Essie adopted a rescue dog named Biscuit last spring.",
       [T("Essie", "pet", "Biscuit", species="dog")], True, "plain"),
    it(7, "plain_teach", "Imogen teaches pottery at Wexley Community School.",
       [T("Imogen", "workplace", "Wexley Community School")], True, "R3"),
    it(8, "plain_teach", "Niko coaches juniors at the Marrowgate Rowing Club.",
       [T("Niko", "workplace", "Marrowgate Rowing Club")], True, "R3"),
    it(9, "plain_teach", "My stepsister is Lara and she lives in Vexford.",
       [T("me", "step_sister", "Lara"), T("Lara", "city", "Vexford")], True, "R4"),
    it(10, "plain_teach", "My housemate is Juno and she works at Copperline Press.",
       [T("me", "housemate", "Juno"), T("Juno", "workplace", "Copperline Press")], True, "R5"),
    it(11, "plain_teach", "Niko plays the cello in a weekend quartet.",
       [T("Niko", "instrument", "cello")], True, "R5"),
    it(12, "plain_teach", "My neighbour Kella shares her ladder with me.",
       [T("me", "neighbour", "Kella")], True, "R5"),
    it(13, "plain_teach", "Our dog Biscuit sleeps on the porch every afternoon.",
       [T("me", "pet", "Biscuit", species="dog")], True, "R7"),
    it(14, "plain_teach", "We rent a bright room in Pellwick above the bakery.",
       [T("me", "city", "Pellwick")], True, "R7"),
    it(15, "plain_teach", "My two sisters, Lara and Nia, both live in Vexford.",
       [T("me", "sister", "Lara"), T("me", "sister", "Nia"),
        T("Lara", "city", "Vexford"), T("Nia", "city", "Vexford")], True, "R10"),
    it(16, "plain_teach", "My cousin Dara lives in Zellmoor.",
       [T("me", "cousin", "Dara"), T("Dara", "city", "Zellmoor")], True, "R11"),
    it(17, "plain_teach", "Petra's friend Jona drives for Kessar Transit.",
       [T("Petra", "friend", "Jona"), T("Jona", "employer", "Kessar Transit")], True, "R11"),
    it(18, "plain_teach", "My friend Jona livs in Dunmere near the mill.",
       [T("me", "friend", "Jona"), T("Jona", "city", "Dunmere")], True, "R13 typo"),
    it(19, "plain_teach", "Essie werks at Fernway Clinic as a receptionist.",
       [T("Essie", "workplace", "Fernway Clinic")], True, "R13 typo"),
    it(20, "plain_teach", "marlo lives in dunmere with his brother.",
       [T("marlo", "city", "dunmere")], True, "R14 lower"),
    it(21, "plain_teach", "essie adopted a stray cat named mochi.",
       [T("essie", "pet", "mochi", species="cat")], True, "R14 lower"),
    it(22, "plain_teach", "I grew up in Sember in a house full of cousins.",
       [T("me", "hometown", "Sember")], False, "plain"),
    it(23, "plain_teach", "Willa studies physics at Brackle College.",
       [T("Willa", "school", "Brackle College")], True, "R3"),
    it(24, "plain_teach", "Petra married Soren last spring in Tarnwick.",
       [T("Petra", "spouse", "Soren")], True, "plain"),
    it(25, "plain_teach", "Petra's brother is Niko and he works at Halden Mills.",
       [T("Petra", "brother", "Niko"), T("Niko", "workplace", "Halden Mills")], True, "R12"),
    # varied_teach 026-055
    it(26, "varied_teach", "My sister is Lara and she lives in Vexford.",
       [T("me", "sister", "Lara"), T("Lara", "city", "Vexford")], True, "R1"),
    it(27, "varied_teach", "My brother is Bram and he drives for Kessar Transit.",
       [T("me", "brother", "Bram"), T("Bram", "employer", "Kessar Transit")], True, "R1"),
    it(28, "varied_teach", "My cousin is Dara and she speaks Korean at home.",
       [T("me", "cousin", "Dara"), T("Dara", "language", "Korean")], True, "R1"),
    it(29, "varied_teach", "My neighbour is Kella and she lives in Zellmoor.",
       [T("me", "neighbour", "Kella"), T("Kella", "city", "Zellmoor")], True, "R1"),
    it(30, "varied_teach", "My boss is Petra and she lives in Bramwell.",
       [T("me", "boss", "Petra"), T("Petra", "city", "Bramwell")], True, "R1"),
    it(31, "varied_teach", "My mother is Odette and she teaches pottery at Loomfield Studio.",
       [T("me", "mother", "Odette"), T("Odette", "workplace", "Loomfield Studio")], True, "R1 R3"),
    it(32, "varied_teach", "Why we settled in Zellmoor is a long story, but our home is on Alder Street.",
       [T("me", "city", "Zellmoor")], True, "R2"),
    it(33, "varied_teach", "How we ended up in Pellwick is a long story, but we rent a room on Mill Lane.",
       [T("me", "city", "Pellwick")], True, "R2"),
    it(34, "varied_teach", "Who knows why we left, but I was born in Tarnwick and love it.",
       [T("me", "place_of_birth", "Tarnwick")], True, "R2"),
    it(35, "varied_teach", "I study physics at Brackle College and love the night bus home.",
       [T("me", "school", "Brackle College")], True, "R3"),
    it(36, "varied_teach", "I teach night classes at Wexley Community School and bike there daily.",
       [T("me", "workplace", "Wexley Community School")], True, "R3"),
    it(37, "varied_teach", "My half-brother Soren livs in Kessar near the depot.",
       [T("me", "half_brother", "Soren"), T("Soren", "city", "Kessar")], True, "R4 R13 typo"),
    it(38, "varied_teach", "My mother-in-law is Celine and she lives in Drellin.",
       [T("me", "mother_in_law", "Celine"), T("Celine", "city", "Drellin")], True, "R4"),
    it(39, "varied_teach", "My guitar teacher is Niko and he lives in Sember.",
       [T("me", "teacher", "Niko"), T("Niko", "city", "Sember")], True, "R1 R5"),
    it(40, "varied_teach", "My doctor is Farrah and she works at Fernway Clinic.",
       [T("me", "doctor", "Farrah"), T("Farrah", "workplace", "Fernway Clinic")], True, "R1 R5"),
    it(41, "varied_teach", "Our cat Miso rules the warm dryer every evening.",
       [T("me", "pet", "Miso", species="cat")], True, "R7"),
    it(42, "varied_teach", "We just moved to Loomfield and our street has the best bakery.",
       [T("me", "city", "Loomfield")], True, "R7"),
    it(43, "varied_teach", "Our neighbour Joss collects our mail when we travel.",
       [T("me", "neighbour", "Joss")], True, "R7"),
    it(44, "varied_teach", "I am training to be a pilot, but right now I load bags at Kessar Transit.",
       [T("me", "workplace", "Kessar Transit")], True, "R8"),
    it(45, "varied_teach", "Caspian wants to be a chef, but he unloads trucks at Kessar Transit.",
       [T("Caspian", "workplace", "Kessar Transit")], True, "R8"),
    it(46, "varied_teach", "I plan to move to Zellmoor next spring; for now I rent a room in Pellwick.",
       [T("me", "city", "Pellwick")], True, "R8"),
    it(47, "varied_teach", "My two brothers, Soren and Tovan, both drive for Kessar Transit.",
       [T("me", "brother", "Soren"), T("me", "brother", "Tovan"),
        T("Soren", "employer", "Kessar Transit"), T("Tovan", "employer", "Kessar Transit")], True, "R10"),
    it(48, "varied_teach", "Both my cousins, Dara and Willa, study physics at Brackle College.",
       [T("me", "cousin", "Dara"), T("me", "cousin", "Willa"),
        T("Dara", "school", "Brackle College"), T("Willa", "school", "Brackle College")], True, "R10"),
    it(49, "varied_teach", "My uncle Raynor repairs engines at Voss Harbor.",
       [T("me", "uncle", "Raynor"), T("Raynor", "workplace", "Voss Harbor")], True, "R11"),
    it(50, "varied_teach", "My sister Lara manages the night shift at Vexford Cannery.",
       [T("me", "sister", "Lara"), T("Lara", "workplace", "Vexford Cannery")], True, "R11"),
    it(51, "varied_teach", "My neighbour Kella arranges flowers at the Tarnwick market.",
       [T("me", "neighbour", "Kella"), T("Kella", "workplace", "Tarnwick market")], True, "R11"),
    it(52, "varied_teach", "Rima's brother is Joss and he works at Halden Mills.",
       [T("Rima", "brother", "Joss"), T("Joss", "workplace", "Halden Mills")], True, "R12"),
    it(53, "varied_teach", "Essie's sister is Lara and she lives in Vexford.",
       [T("Essie", "sister", "Lara"), T("Lara", "city", "Vexford")], True, "R12"),
    it(54, "varied_teach", "My friend Essie bron in Tarnwick during the festival.",
       [T("me", "friend", "Essie"), T("Essie", "place_of_birth", "Tarnwick")], True, "R13 typo"),
    it(55, "varied_teach", "my sister lara lives in vexford with her dog.",
       [T("me", "sister", "lara"), T("lara", "city", "vexford")], True, "R14 lower"),
    # full_names 056-070
    it(56, "full_names", "marlo drayden hale lives in dunmere near the mill.",
       [T("marlo drayden hale", "city", "dunmere")], True, "R14 lower"),
    it(57, "full_names", "Petra Loomis Vane teahces at Wexley Community School.",
       [T("Petra Loomis Vane", "workplace", "Wexley Community School")], True, "R3 R13 typo"),
    it(58, "full_names", "My teacher is Imogen Hartley Vale and she lives in Sember.",
       [T("me", "teacher", "Imogen Hartley Vale"), T("Imogen Hartley Vale", "city", "Sember")], True, "R1"),
    it(59, "full_names", "My doctor is Caspian Reed Nolan and he works at Fernway Clinic.",
       [T("me", "doctor", "Caspian Reed Nolan"),
        T("Caspian Reed Nolan", "workplace", "Fernway Clinic")], True, "R1"),
    it(60, "full_names", "My neighbour is Odette Larkspur Bell and she lives in Zellmoor.",
       [T("me", "neighbour", "Odette Larkspur Bell"),
        T("Odette Larkspur Bell", "city", "Zellmoor")], True, "R1"),
    it(61, "full_names", "My boss is Lennox Granger Pike and he lives in Bramwell.",
       [T("me", "boss", "Lennox Granger Pike"), T("Lennox Granger Pike", "city", "Bramwell")], True, "R1"),
    it(62, "full_names", "My great-aunt is Mabel Cornflower Hart and she lives in Drellin.",
       [T("me", "great_aunt", "Mabel Cornflower Hart"),
        T("Mabel Cornflower Hart", "city", "Drellin")], True, "R4"),
    it(63, "full_names", "My housemate Juno Baxter Reed livs in Pellwick above the bakery.",
       [T("me", "housemate", "Juno Baxter Reed"), T("Juno Baxter Reed", "city", "Pellwick")], True, "R5 R13 typo"),
    it(64, "full_names", "Our family doctor is Farrah Noor Aziz at Fernway Clinic.",
       [T("me", "doctor", "Farrah Noor Aziz")], False, "R7"),
    it(65, "full_names", "My two sisters, Yvette Calloway Hart and Odette Larkspur Bell, both live in Zellmoor.",
       [T("me", "sister", "Yvette Calloway Hart"), T("me", "sister", "Odette Larkspur Bell"),
        T("Yvette Calloway Hart", "city", "Zellmoor"),
        T("Odette Larkspur Bell", "city", "Zellmoor")], True, "R10"),
    it(66, "full_names", "Both my cousins, Raynor Cade Holt and Soren Vale Holt, study physics at Brackle College.",
       [T("me", "cousin", "Raynor Cade Holt"), T("me", "cousin", "Soren Vale Holt"),
        T("Raynor Cade Holt", "school", "Brackle College"),
        T("Soren Vale Holt", "school", "Brackle College")], True, "R10"),
    it(67, "full_names", "My cousin Dara Linden Vale packs crates at Vexford Cannery.",
       [T("me", "cousin", "Dara Linden Vale"),
        T("Dara Linden Vale", "workplace", "Vexford Cannery")], True, "R11"),
    it(68, "full_names", "My uncle Raynor Cade Holt repairs engines at Voss Harbor.",
       [T("me", "uncle", "Raynor Cade Holt"), T("Raynor Cade Holt", "workplace", "Voss Harbor")], True, "R11"),
    it(69, "full_names", "Petra's son is Caspian Reed Nolan and he studies physics at Brackle College.",
       [T("Petra", "son", "Caspian Reed Nolan"),
        T("Caspian Reed Nolan", "school", "Brackle College")], True, "R12"),
    it(70, "full_names", "petra's son is caspian reed nolan and he studies at brackle college.",
       [T("petra", "son", "caspian reed nolan"),
        T("caspian reed nolan", "school", "brackle college")], True, "R12 R14 lower"),
    # questions 071-095
    it(71, "questions", "Where does Lara live?",
       [Q("Lara", "city")], True, "plain"),
    it(72, "questions", "Where does Bram work?",
       [Q("Bram", "workplace")], True, "plain"),
    it(73, "questions", "What does Caspian do for work?",
       [Q("Caspian", "job")], False, "plain"),
    it(74, "questions", "What language does Dara speak?",
       [Q("Dara", "language")], True, "plain"),
    it(75, "questions", "Who does Bram work for?",
       [Q("Bram", "employer")], True, "plain"),
    it(76, "questions", "Who is Petra married to?",
       [Q("Petra", "spouse")], True, "plain"),
    it(77, "questions", "Does Essie have a dog?",
       [Q("Essie", "pet", species="dog")], False, "plain"),
    it(78, "questions", "Where does Willa study?",
       [Q("Willa", "school")], True, "plain"),
    it(79, "questions", "Who is Tovan's boss?",
       [Q("Tovan", "boss")], True, "plain"),
    it(80, "questions", "Does Rima have a sister?",
       [Q("Rima", "sister")], False, "plain"),
    it(81, "questions", "Who is Celine's mother-in-law?",
       [Q("Celine", "mother_in_law")], True, "R4"),
    it(82, "questions", "Who does Juno live with?",
       [Q("Juno", "housemate")], True, "R5"),
    it(83, "questions", "Who is Marlo's doctor?",
       [Q("Marlo", "doctor")], True, "R5"),
    it(84, "questions", "where does kella live",
       [Q("kella", "city")], True, "lower noq"),
    it(85, "questions", "what language does dara speak",
       [Q("dara", "language")], True, "lower noq"),
    it(86, "questions", "who does juno live with",
       [Q("juno", "housemate")], True, "R5 lower noq"),
    it(87, "questions", "does essie have a dog",
       [Q("essie", "pet", species="dog")], True, "lower noq"),
    it(88, "questions", "Where was Juno born?",
       [Q("Juno", "place_of_birth")], True, "plain"),
    it(89, "questions", "Where did Raynor grow up?",
       [Q("Raynor", "hometown")], False, "plain"),
    it(90, "questions", "Who is Niko's guitar teacher?",
       [Q("Niko", "teacher")], True, "R5"),
    it(91, "questions", "Who lives next door to Kella?",
       [Q("Kella", "neighbour")], True, "R5"),
    it(92, "questions", "What does Odette do for fun?",
       [Q("Odette", "hobby")], True, "R5"),
    it(93, "questions", "What is Bram's favourite dish?",
       [Q("Bram", "favourite_food")], True, "R5"),
    it(94, "questions", "What instrument does Niko play?",
       [Q("Niko", "instrument")], True, "R5"),
    it(95, "questions", "Who is Soren's grandfather?",
       [Q("Soren", "grandfather")], True, "R4"),
    # chain_questions 096-110
    it(96, "chain_questions", "Where does Lara's sister live?",
       [Q2("Lara", "sister", "city")], True, "R6"),
    it(97, "chain_questions", "Where does Bram's brother work?",
       [Q2("Bram", "brother", "workplace")], True, "R6"),
    it(98, "chain_questions", "What language does Dara's cousin speak?",
       [Q2("Dara", "cousin", "language")], True, "R6"),
    it(99, "chain_questions", "Who is Rima's mother's doctor?",
       [Q2("Rima", "mother", "doctor")], True, "R6"),
    it(100, "chain_questions", "Where does Caspian's husband work?",
       [Q2("Caspian", "husband", "workplace")], True, "R6"),
    it(101, "chain_questions", "Which school does Willa's sister attend?",
       [Q2("Willa", "sister", "school")], True, "R6"),
    it(102, "chain_questions", "Who is Tovan's brother's boss?",
       [Q2("Tovan", "brother", "boss")], True, "R6"),
    it(103, "chain_questions", "Where does Tovan's boss live?",
       [Q2("Tovan", "boss", "city")], True, "plain"),
    it(104, "chain_questions", "What language does Niko's teacher speak?",
       [Q2("Niko", "teacher", "language")], True, "plain"),
    it(105, "chain_questions", "Where does Kella's neighbour work?",
       [Q2("Kella", "neighbour", "workplace")], True, "plain"),
    it(106, "chain_questions", "Who is Petra's boss married to?",
       [Q2("Petra", "boss", "spouse")], True, "plain"),
    it(107, "chain_questions", "What does Juno's housemate do for work?",
       [Q2("Juno", "housemate", "job")], False, "plain"),
    it(108, "chain_questions", "where does lara's sister live",
       [Q2("lara", "sister", "city")], True, "R6 lower noq"),
    it(109, "chain_questions", "who is tovan's boss married to",
       [Q2("tovan", "boss", "spouse")], True, "lower noq"),
    it(110, "chain_questions", "Where was Essie's brother born?",
       [Q2("Essie", "brother", "place_of_birth")], True, "R6"),
    # no_save 111-135
    it(111, "no_save", "Lara lives in Vexford, right?", [], False, "R2"),
    it(112, "no_save", "Bram works at Copperline Press, isn't he?", [], False, "R2"),
    it(113, "no_save", "So Dara speaks Korean?", [], False, "R2"),
    it(114, "no_save", "Kella lives in Zellmoor, right?", [], False, "R2"),
    it(115, "no_save", "so lara lives in vexford", [], False, "R2 lower noq"),
    it(116, "no_save", "bram works at copperline press, right", [], False, "R2 lower noq"),
    it(117, "no_save", "kella lives in zellmoor, isnt that so", [], False, "R2 lower noq"),
    it(118, "no_save", "so dara speaks korean", [], False, "R2 lower noq"),
    it(119, "no_save", "tovan's boss lives in bramwell, right", [], False, "R2 lower noq"),
    it(120, "no_save", "I am training to be a pilot and I start flight school next spring.", [], True, "R8"),
    it(121, "no_save", "My little girl wants to be a chef when she grows up.", [], True, "R8"),
    it(122, "no_save", "We plan to move to Zellmoor in the spring.", [], True, "R8"),
    it(123, "no_save", "I will start at Copperline Press next month and I cannot wait.", [], True, "R8"),
    it(124, "no_save", "Let's say my sister lives in Vexford, where would I send the gift?", [], True, "R9"),
    it(125, "no_save", "Imagine I owned a bakery in Bramwell, what would I bake first?", [], True, "R9"),
    it(126, "no_save", "Suppose my cousin won the lottery, should she share it with me?", [], True, "R9"),
    it(127, "no_save", "Pretend our dog could talk, what would he say about Mondays?", [], True, "R9"),
    it(128, "no_save", "What if my neighbour painted her house blue, would that be odd?", [], True, "R9"),
    it(129, "no_save", "Say that my brother worked at Halden Mills, would the commute be long?", [], True, "R9"),
    it(130, "no_save", "Joss is the best boss ever and everyone loves working with him.", [], True, "opinion"),
    it(131, "no_save", "Apparently Petra moved to Bramwell last week.", [], False, "hearsay"),
    it(132, "no_save", "Did you know Vexford Cannery is closing next month?", [], False, "news"),
    it(133, "no_save", "Hello there, how is your day going?", [], True, "greeting"),
    it(134, "no_save", "Rima used to live in Drellin years ago.", [], False, "past"),
    it(135, "no_save", "The night market in Bramwell has the best noodles around.", [], True, "opinion"),
    # corrections 136-150
    it(136, "corrections", "Not Vexford, Lara lives in Zellmoor now.",
       [T("Lara", "city", "Zellmoor")], True, "correction"),
    it(137, "corrections", "Not Halden Mills, Bram works at Copperline Press now.",
       [T("Bram", "workplace", "Copperline Press")], True, "correction"),
    it(138, "corrections", "Not Spanish, Dara speaks Korean now.",
       [T("Dara", "language", "Korean")], True, "correction"),
    it(139, "corrections", "Not my sister, my stepsister Lara lives in Vexford.",
       [T("me", "step_sister", "Lara"), T("Lara", "city", "Vexford")], True, "R4 correction"),
    it(140, "corrections", "Not Soren, my half-brother is Tovan and he lives in Kessar.",
       [T("me", "half_brother", "Tovan"), T("Tovan", "city", "Kessar")], True, "R4 correction"),
    it(141, "corrections", "Not the violin, Niko plays the cello now.",
       [T("Niko", "instrument", "cello")], True, "R5 correction"),
    it(142, "corrections", "Not that clinic, my doctor is Farrah now.",
       [T("me", "doctor", "Farrah")], True, "R5 correction"),
    it(143, "corrections", "Not a student, I teach evening classes at Wexley Community School now.",
       [T("me", "workplace", "Wexley Community School")], True, "R3 correction"),
    it(144, "corrections", "Not his dog, our dog Miso sleeps on the porch now.",
       [T("me", "pet", "Miso", species="dog")], True, "R7 correction"),
    it(145, "corrections", "No, Jona livs in Zellmoor now, not Dunmere.",
       [T("Jona", "city", "Zellmoor")], True, "R13 typo correction"),
    it(146, "corrections", "No, Essie werks at Fernway Clinic now, not Halden Mills.",
       [T("Essie", "workplace", "Fernway Clinic")], True, "R13 typo correction"),
    it(147, "corrections", "no, lara lives in zellmoor now, not vexford.",
       [T("lara", "city", "zellmoor")], True, "R14 lower correction"),
    it(148, "corrections", "not copperline, bram works at halden mills now.",
       [T("bram", "workplace", "halden mills")], True, "R14 lower correction"),
    it(149, "corrections", "Not Kessar Transit, Tovan drives for Prindle Foods now.",
       [T("Tovan", "employer", "Prindle Foods")], True, "correction"),
    it(150, "corrections", "Not engaged, Petra married Soren last spring.",
       [T("Petra", "spouse", "Soren")], True, "correction"),
]


def tags(notes):
    return set(notes.split())


def check():
    fams = ["plain_teach", "varied_teach", "full_names", "questions",
            "chain_questions", "no_save", "corrections"]
    want = {"plain_teach": 25, "varied_teach": 30, "full_names": 15,
            "questions": 25, "chain_questions": 15, "no_save": 25,
            "corrections": 15}
    assert len(ITEMS) == 150, len(ITEMS)
    by_fam = {f: [x for x in ITEMS if x["family"] == f] for f in fams}
    for f in fams:
        assert len(by_fam[f]) == want[f], (f, len(by_fam[f]))
    # ids in family-block order
    expect = []
    for f in fams:
        expect += [x["id"] for x in by_fam[f]]
    assert [x["id"] for x in ITEMS] == expect, "id order"
    assert expect == ["e261b-%03d" % i for i in range(1, 151)], "id names"
    # no duplicate turn
    turns = [x["turn"] for x in ITEMS]
    assert len(set(turns)) == 150, "duplicate turn"
    # schema exactness + span check
    for x in ITEMS:
        assert set(x.keys()) == {"id", "family", "turn", "gold", "clear", "notes"}, x["id"]
        assert isinstance(x["clear"], bool), x["id"]
        assert isinstance(x["notes"], str), x["id"]
        assert isinstance(x["gold"], list), x["id"]
        for fr in x["gold"]:
            if fr["act"] == "TEACH":
                assert set(fr.keys()) == {"act", "subject", "relation",
                                          "relation_aliases", "value"}, (x["id"], fr)
                if fr["subject"] != "me":
                    assert fr["subject"] in x["turn"], (x["id"], "subject span", fr)
                assert fr["value"] in x["turn"], (x["id"], "value span", fr)
                if fr["relation"] == "pet":
                    sp = None
                    for s in PET_ALIASES:
                        if s in x["turn"].lower().split() or s in x["turn"].lower():
                            if s in ("dog", "cat"):
                                # species word must be in the turn
                                pass
                    # find species by alias match
                    for s, al in PET_ALIASES.items():
                        if list(fr["relation_aliases"]) == al:
                            sp = s
                    assert sp is not None, (x["id"], "pet aliases")
                    assert sp in x["turn"].lower(), (x["id"], "species in turn")
                    for w in ("pet", "animal", "companion"):
                        assert w in fr["relation_aliases"], (x["id"], w)
                else:
                    assert list(fr["relation_aliases"]) == ALIASES[fr["relation"]], (x["id"], fr)
            elif fr["act"] == "ASK":
                assert set(fr.keys()) == {"act", "subject", "relation", "chain",
                                          "relation_aliases", "chain_aliases"}, (x["id"], fr)
                assert fr["subject"] in x["turn"], (x["id"], "ask subject", fr)
                if fr["chain"] is None:
                    assert fr["chain_aliases"] is None, x["id"]
                    if fr["relation"] == "pet":
                        ok = [al for al in PET_ALIASES.values()
                              if list(fr["relation_aliases"]) == al]
                        assert ok, (x["id"], "pet ask aliases")
                    else:
                        assert list(fr["relation_aliases"]) == ALIASES[fr["relation"]], x["id"]
                else:
                    assert len(fr["chain"]) == 2, x["id"]
                    assert fr["relation"] == fr["chain"][1], x["id"]
                    assert list(fr["chain_aliases"]) == [ALIASES[fr["chain"][0]],
                                                         ALIASES[fr["chain"][1]]], x["id"]
                    assert list(fr["chain_aliases"][1]) == list(fr["relation_aliases"]), x["id"]
            else:
                raise AssertionError((x["id"], "bad act"))
    # R1: pronoun items across varied_teach + full_names
    r1 = [x for x in ITEMS if "R1" in tags(x["notes"])
          and x["family"] in ("varied_teach", "full_names")]
    assert len(r1) >= 8, len(r1)
    # R2: no_save statement-questions gold [] >= 8, >=5 no question mark;
    #     varied_teach question-word TEACH >= 3
    r2ns = [x for x in ITEMS if "R2" in tags(x["notes"])
            and x["family"] == "no_save" and x["gold"] == []]
    assert len(r2ns) >= 8, len(r2ns)
    assert sum(1 for x in r2ns if "?" not in x["turn"]) >= 5, "R2 no-mark"
    r2v = [x for x in ITEMS if "R2" in tags(x["notes"])
           and x["family"] == "varied_teach"
           and any(f["act"] == "TEACH" for f in x["gold"])]
    assert len(r2v) >= 3, len(r2v)
    # R3: verb decides relation
    r3 = [x for x in ITEMS if "R3" in tags(x["notes"])]
    assert len(r3) >= 6, len(r3)
    for x in r3:
        words = t = x["turn"].lower().split()
        t = x["turn"].lower()
        rels = [f["relation"] for f in x["gold"]]
        if "teach" in t or "coach" in t:
            assert "workplace" in rels, (x["id"], "R3 teach->workplace")
        if "study" in t or "studies" in t:
            assert "school" in rels, (x["id"], "R3 study->school")
    # R4 compound relations
    r4 = [x for x in ITEMS if "R4" in tags(x["notes"])]
    assert len(r4) >= 6, len(r4)
    # R5 everyday relations
    r5 = [x for x in ITEMS if "R5" in tags(x["notes"])]
    assert len(r5) >= 8, len(r5)
    # R6: chain first hop is a relative
    r6 = [x for x in ITEMS if "R6" in tags(x["notes"])
          and x["family"] == "chain_questions"]
    assert len(r6) >= 5, len(r6)
    for x in r6:
        assert x["gold"] and x["gold"][0]["chain"][0] in RELATIVES, x["id"]
    # R7: plural owners, gold subject me
    r7 = [x for x in ITEMS if "R7" in tags(x["notes"])]
    assert len(r7) >= 6, len(r7)
    for x in r7:
        t = x["turn"].lower()
        assert ("our" in t or "we" in t or "us" in t), (x["id"], "R7 owner")
        assert any(f.get("subject") == "me" for f in x["gold"]), x["id"]
    # R8: plans; varied>=3 with real fact gold; no_save>=3 gold []
    r8 = [x for x in ITEMS if "R8" in tags(x["notes"])]
    assert len(r8) >= 6, len(r8)
    assert sum(1 for x in r8 if x["family"] == "varied_teach" and x["gold"] != []) >= 3
    assert sum(1 for x in r8 if x["family"] == "no_save" and x["gold"] == []) >= 3
    # R9 pretend no_save
    r9 = [x for x in ITEMS if "R9" in tags(x["notes"]) and x["family"] == "no_save"]
    assert len(r9) >= 5, len(r9)
    assert all(x["gold"] == [] for x in r9)
    # R10 plural relatives
    r10 = [x for x in ITEMS if "R10" in tags(x["notes"])]
    assert len(r10) >= 4, len(r10)
    # R11 appositives: relative frame + other fact
    r11 = [x for x in ITEMS if "R11" in tags(x["notes"])]
    assert len(r11) >= 6, len(r11)
    for x in r11:
        assert len(x["gold"]) >= 2, (x["id"], "R11 two frames")
    # R12 pronoun refers to B
    r12 = [x for x in ITEMS if "R12" in tags(x["notes"])]
    assert len(r12) >= 4, len(r12)
    # R13 typo next to a name, teach items
    r13 = [x for x in ITEMS if "R13" in tags(x["notes"])]
    assert len(r13) >= 8, len(r13)
    assert all(any(f["act"] == "TEACH" for f in x["gold"]) for x in r13)
    # R14 all-lowercase names, teach items
    r14 = [x for x in ITEMS if "R14" in tags(x["notes"])]
    assert len(r14) >= 6, len(r14)
    for x in r14:
        assert x["turn"] == x["turn"].lower(), (x["id"], "R14 lower turn")
        assert any(f["act"] == "TEACH" for f in x["gold"])
    # lowercase/typo chat >= 15
    lt = [x for x in ITEMS if "lower" in tags(x["notes"]) or "typo" in tags(x["notes"])]
    assert len(lt) >= 15, len(lt)
    # questions + chain_questions: >=5 lowercase or no-"?"
    qq = [x for x in ITEMS if x["family"] in ("questions", "chain_questions")]
    qlow = [x for x in qq if "lower" in tags(x["notes"]) or "noq" in tags(x["notes"])
            or "?" not in x["turn"] or x["turn"] == x["turn"].lower()]
    assert len(qlow) >= 5, len(qlow)
    return {
        "R1": len(r1), "R2ns": len(r2ns),
        "R2ns_noq": sum(1 for x in r2ns if "?" not in x["turn"]),
        "R2v": len(r2v), "R3": len(r3), "R4": len(r4), "R5": len(r5),
        "R6": len(r6), "R7": len(r7), "R8": len(r8), "R9": len(r9),
        "R10": len(r10), "R11": len(r11), "R12": len(r12),
        "R13": len(r13), "R14": len(r14), "lower_typo": len(lt),
        "qq_low_noq": len(qlow),
        "clear_false": sum(1 for x in ITEMS if x["clear"] is False),
        "noq_total": sum(1 for x in ITEMS if "noq" in tags(x["notes"])),
    }


def main():
    counts = check()
    path = os.path.join(OUT_DIR, "panel.jsonl")
    with open(path, "w") as f:
        for x in ITEMS:
            f.write(json.dumps(x, sort_keys=True) + "\n")
    print("wrote %s (%d items)" % (path, len(ITEMS)))
    print(json.dumps(counts, sort_keys=True, indent=1))


if __name__ == "__main__":
    main()
