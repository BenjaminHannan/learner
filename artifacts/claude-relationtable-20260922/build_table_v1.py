#!/usr/bin/env python3
"""Builds relation_table_v1.json (the deliverable) from readable Python.

Pure Python, no imports beyond json. Run from the repo root:
    python3 artifacts/claude-relationtable-20260922/build_table_v1.py

Why a builder: the generic pattern families and the file:line source
references are shared by many relations; writing them once here keeps the
JSON consistent. The JSON is the artifact; this file is its audit trail.

Template syntax (the checker enforces it):
  {X}  subject slot   (the thing the fact is ABOUT: "X's R is Y")
  {Y}  value slot     (the answer)
  {R}  relation word  (canonical surface or any alias, spaces not "_")
  {WH} question word  (filled from the relation's "wh" list)
  (a|b)   exactly one of the alternatives
  [word]  optional word(s)
Every fact is read as (X, R, Y) == "X's R is Y". Example: "Blue Rain's
composer is Ada Pell." is (Blue Rain, composer, Ada Pell).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "relation_table_v1.json"

# ---------------------------------------------------------------- sources
FA = "scripts/fable_agent_loop.py"
S = {
    "fake_stmt": f"{FA}:96 (_STATEMENT, open-vocabulary 'X's R is Y'; key rule FakeEars._relation :151)",
    "fake_q": f"{FA}:94 (_QUESTION who/what/where is X's R [ 's R2 ...])",
    "person91": f"{FA}:91 PERSON_RELATIONS",
    "b73": "scripts/fable_bench73_english_arm.py:73 STATEMENT_PATTERNS",
    "b73rev": "scripts/fable_bench73_english_arm.py:131 REV_OF_NOUNS / :139 REV_BY_VERBS",
    "b73cues": "scripts/fable_bench73_english_arm.py:153 REL_MENTION_CUES",
    "b92": "scripts/fable_bench92_english_arm.py:58 EXTRA_STATEMENT_PATTERNS",
    "b92cues": "scripts/fable_bench92_english_arm.py:72 EXTRA_REL_CUES",
    "q132": "scripts/fable_qrewrite132.py:156 (question cue words)",
    "office135": "scripts/fable_fix135_office.py:62 OFFICE_RELATIONS",
    "yn154": "scripts/fable_fix154_yesno.py:84 _ISQ_154 / :85 _OF_154",
    "single154": "scripts/fable_fix154_yesno.py:64 SINGLE_VALUED_154",
    "who154": "scripts/fable_fix154_yesno.py:89 _WHO_154",
    "multi154c": "scripts/fable_fix154c_allowlist.py:37 MULTI_VALUED_154C",
    "multi154e": "scripts/fable_fix154e_allowlist.py:27 MULTI_VALUED_154E (+language)",
    "me166": "scripts/fable_fix166_me.py:62 _ASK / :71 _SYNONYMS",
    "verb167": "scripts/fable_fix167_verb.py:63 VERB_STATEMENTS / :70 VERB_QUESTIONS",
    "verb167d": "scripts/fable_fix167d_verb.py:67 VERB_STATEMENTS_167D / :72 VERB_QUESTIONS_167D",
    "name171": "scripts/fable_fix171_nameval.py:48 NAME_KEYS",
    "chain174": "scripts/fable_fix174_chainof.py:50 REL174 / :61 _ONEHOP_RE",
    "listed139e": "scripts/fable_fix139e_tail.py:57 LISTED_RELATIONS",
    "rev153": "scripts/fable_fix153_reverse.py:75-88 (whose / is-the-R-of frames)",
    "rev190": "scripts/fable_fix190_reverse.py:69 REVERSE_RELATIONS, :103 parse_reverse190 (layer C)",
    "inv155": "scripts/fable_fix155_inverted.py:91-95 _FRAME1/2/3 (not in 138i)",
    "d158b": "scripts/fable_loop158b_agent.py:77-95 WHEN/HOW_OLD/WHERE_FROM/WHERE_LIVE (not in 138i; see fable_loop138g_agent.py:231-236)",
    "whcity158c": "scripts/fable_loop158c_agent.py:84 rewrite_whcity (live via fable_loop138g_agent.py:225)",
    "listen": "scripts/fable_listening_english.py:171 RELATION_MAP (Qwen listening path; not the 138i FakeEars path)",
    "r50": "scripts/fable_reasoner50.py:76 CORE8",
    "apos193": "scripts/fable_fix193_apos.py:64 REL193_STATIC (layer C)",
}

# ------------------------------------------------ generic pattern families
# Each family applies to every relation listing it in "generic". {R} ranges
# over the canonical surface and every alias.
GENERIC = {
    "possessive": {
        "teach": [{"t": "{X}'s {R} is {Y}.", "where": "live", "src": S["fake_stmt"]}],
        "ask": [{"t": "{WH} is {X}'s {R}?", "where": "live", "src": S["fake_q"]},
                {"t": "What's {X}'s {R}?", "where": "NEW", "src": "NEW (contraction; 158 qform only folds some)"}],
        "yesno": [{"t": "Is {X}'s {R} {Y}?", "where": "live", "src": S["yn154"]},
                  {"t": "Is {Y} {X}'s {R}?", "where": "live", "src": S["yn154"]}],
    },
    "my": {
        "teach": [{"t": "My {R} is {Y}.", "where": "live", "src": "scripts/fable_fix166_me.py (Me166Mixin; X = the user)"}],
        "ask": [{"t": "{WH} is my {R}?", "where": "live", "src": S["me166"]}],
        "yesno": [{"t": "Is my {R} {Y}?", "where": "NEW", "src": "NEW"}],
    },
    "of_form": {
        "teach": [{"t": "The {R} of {X} is {Y}.", "where": "not_live", "src": S["inv155"] + "; bench73 has it only for its own nouns"}],
        "ask": [{"t": "{WH} is the {R} of {X}?", "where": "live", "src": S["chain174"] + " (13 relation words only)"}],
        "yesno": [{"t": "Is {Y} the {R} of {X}?", "where": "live", "src": S["yn154"]}],
    },
    "inverted": {
        "teach": [{"t": "{Y} is {X}'s {R}.", "where": "not_live", "src": S["inv155"]},
                  {"t": "{Y} is the {R} of {X}.", "where": "not_live", "src": S["inv155"] + "; bench73 stores these as inverse _of keys"}],
        "ask": [], "yesno": [],
    },
    "reverse": {
        # Answer-time inverse lookup: known VALUE, unknown SUBJECT. Never stored.
        "inverse": [{"t": "Whose {R} is {Y}?", "where": "live", "src": S["rev153"] + "; widened in " + S["rev190"],
                     "never_store": True, "label": "worked out backwards"},
                    {"t": "Who has {Y} as (their|his|her) {R}?", "where": "layer_c", "src": S["rev190"],
                     "never_store": True, "label": "worked out backwards"},
                    {"t": "Who is {Y} the {R} of?", "where": "NEW", "src": "NEW",
                     "never_store": True, "label": "worked out backwards"}],
    },
}

INVERSE_LABEL = "worked out backwards"

# --------------------------------------------------------------- helpers
def P(t, where="NEW", src="NEW"):
    return {"t": t, "where": where, "src": src}


def INV(t, where="NEW", src="NEW"):
    return {"t": t, "where": where, "src": src, "never_store": True, "label": INVERSE_LABEL}


def rel(name, kind, card, *, status="known", src=(), aliases=(), storage=(), inv_storage=(),
        narrower=(), generic=("possessive", "my", "of_form", "inverted", "reverse"), wh=None,
        teach=(), ask=(), yesno=(), inverse=(), say_no=False, notes="", date_rule=None,
        value_guard=None):
    if wh is None:
        wh = {"person": ["Who", "What"], "place": ["Where", "What"], "date": ["When", "What"],
              "number": ["What"], "organization": ["Who", "What"],
              "work": ["What"], "literal": ["What"], "language": ["What"]}[kind]
    r = {
        "name": name, "status": status, "value_kind": kind, "cardinality": card,
        "yesno_can_say_no": say_no, "aliases": list(aliases),
        "storage_keys": [name] + [k for k in storage if k != name],
        "inverse_storage_keys": list(inv_storage), "narrower": list(narrower),
        "generic": list(generic), "wh": wh, "teach": list(teach), "ask": list(ask),
        "yesno": list(yesno), "inverse": list(inverse), "src": list(src),
    }
    if date_rule:
        r["date_rule"] = date_rule
    if value_guard:
        r["value_guard"] = value_guard
    if notes:
        r["notes"] = notes
    return r


DATE_RULE = {
    "strip_leading": ["in", "on"],
    "example": "\"Pia's birthday is in May.\" stores value \"May\" (today it stores \"in May\").",
    "when_question": "When is {X}'s {R}?",
    "also": "\"When is my {R}?\" asks the user's slot.",
}
DATE_GUARD = ("value must look like a date: a month name, a day+month, a year, or a full date "
              "(e.g. \"May\", \"3 May\", \"May 3\", \"1990\", \"3 May 1990\")")
NOT_DATE_GUARD = "value must NOT look like a date (else the date relation takes the sentence)"

R = []

# ================================================================ family
R += [
    rel("mother", "person", "single", say_no=True, aliases=["mom", "mum", "mommy", "mummy", "ma"],
        src=[S["person91"], S["single154"], S["name171"], S["chain174"], S["me166"], S["listed139e"], S["r50"]],
        inverse=[INV("Who are {Y}'s children?", "NEW", "NEW (collects mother and father facts)")]),
    rel("father", "person", "single", say_no=True, aliases=["dad", "daddy", "papa", "pa", "pop", "poppa"],
        src=[S["person91"], S["single154"], S["name171"], S["chain174"], S["me166"], S["listed139e"]]),
    rel("parent", "person", "multi", status="NEW", narrower=["mother", "father"],
        notes="Question-only in build 1: 'Who are X's parents?' collects mother+father facts."),
    rel("sister", "person", "multi", src=[S["person91"], S["multi154c"], S["name171"], S["chain174"]],
        notes="fable_listening_english.py:236 folds sister/brother into sibling; that is lossy and NOT adopted here."),
    rel("brother", "person", "multi", src=[S["person91"], S["multi154c"], S["name171"], S["chain174"]]),
    rel("sibling", "person", "multi", narrower=["sister", "brother"],
        src=[S["multi154c"], S["name171"], S["listed139e"], S["listen"]]),
    rel("spouse", "person", "single", say_no=True, narrower=["wife", "husband"],
        src=[S["single154"], S["name171"], S["b73"], S["listed139e"]],
        teach=[P("{X} is married to {Y}.", "live", S["b73"])],
        ask=[P("Who is {X} married to?", "NEW", "NEW (fable_fix167_verb.py:74-78 declined it: needs wife~spouse)")],
        notes="wife/husband are NARROWER, not aliases: a wife fact answers a spouse question, not the reverse."),
    rel("wife", "person", "single", say_no=True, src=[S["person91"], S["single154"], S["chain174"]]),
    rel("husband", "person", "single", say_no=True, src=[S["person91"], S["single154"], S["chain174"]]),
    rel("partner", "person", "single", src=[S["person91"], S["chain174"], S["who154"]],
        notes="Not an alias of spouse (unmarried partners)."),
    rel("child", "person", "multi", narrower=["son", "daughter"], aliases=["kid"],
        src=[S["multi154c"], S["b92"], S["who154"]],
        teach=[P("{X}'s child is {Y}.", "live", S["b92"])]),
    rel("son", "person", "multi", src=[S["multi154c"], S["name171"]]),
    rel("daughter", "person", "multi", src=[S["multi154c"], S["name171"]]),
    rel("grandchild", "person", "multi", aliases=["grand child"], narrower=["grandson", "granddaughter"],
        src=[S["multi154c"]]),
    rel("grandson", "person", "multi", aliases=["grand son"], src=[S["multi154c"]]),
    rel("granddaughter", "person", "multi", aliases=["grand daughter"], src=[S["multi154c"]]),
    rel("grandmother", "person", "multi", status="NEW", aliases=["grandma", "granny"]),
    rel("grandfather", "person", "multi", status="NEW", aliases=["grandpa"]),
    rel("cousin", "person", "multi", src=[S["multi154c"]]),
    rel("aunt", "person", "multi", src=[S["multi154c"]]),
    rel("uncle", "person", "multi", src=[S["multi154c"]]),
]

# ======================================================== social / work
R += [
    rel("friend", "person", "multi", src=[S["person91"], S["multi154c"], S["name171"], S["chain174"], S["listen"]]),
    rel("best_friend", "person", "single", aliases=["best friend"], src=[S["r50"]],
        notes="fable_listening_english.py:235 folds 'best friend' into friend (lossy); kept separate here."),
    rel("neighbour", "person", "multi", aliases=["neighbor"], src=[S["person91"], S["chain174"], S["r50"]]),
    rel("boss", "person", "single", say_no=True, aliases=["manager"],
        src=[S["person91"], S["single154"], S["name171"], S["chain174"], S["r50"]],
        inverse=[INV("Who does {Y} manage?")],
        notes=("manager = boss (true synonym for a person's line manager). boss != employer: an employer is "
               "usually a company. 'Sam is the boss of Kim.' -> (Kim, boss, Sam); today it is not understood.")),
    rel("colleague", "person", "multi", aliases=["coworker", "co-worker", "co worker"],
        storage=["co_worker", "co-worker", "coworker"], src=[S["multi154c"], S["name171"]]),
    rel("teacher", "person", "single", say_no=True, src=[S["person91"], S["single154"], S["name171"], S["chain174"], S["r50"]],
        teach=[P("{Y} teaches {X}.")], ask=[P("Who teaches {X}?")], inverse=[INV("Who does {Y} teach?")]),
    rel("coach", "person", "single", src=[S["listed139e"], S["rev190"]],
        notes="A person's coach. The office 'head coach of <team>' is head_coach."),
    rel("doctor", "person", "single", src=[S["r50"]]),
    rel("mentor", "person", "single", inv_storage=["mentor_of"], src=[S["b73"], S["b73rev"]],
        generic=("possessive", "my", "of_form", "inverted", "reverse"),
        notes="bench65 teaches 'X is the mentor of Y.' as (X, mentor_of, Y) = (Y, mentor, X)."),
    rel("apprentice", "person", "multi", inv_storage=["apprentice_of"], src=[S["b73"], S["b73rev"]]),
    rel("rival", "person", "multi", inv_storage=["rival_of"], src=[S["b73"], S["b73rev"]],
        notes="Symmetric in English, but stored one way; build 1 reads both directions only via inverse_storage_keys."),
    rel("envoy", "person", "single", inv_storage=["envoy_of"], src=[S["b73"]]),
    rel("herald", "person", "single", inv_storage=["herald_of"], src=[S["b73"]]),
    rel("keeper", "person", "single", inv_storage=["keeper_of"], src=[S["b73"]]),
    rel("scout", "person", "single", inv_storage=["scout_of"], src=[S["b73"]]),
    rel("warden", "person", "single", inv_storage=["warden_of"], src=[S["b73"]]),
    rel("owner", "person", "single", src=["sessions152 (\"Biscuit's owner is Ana.\")"],
        inverse=[INV("What does {Y} own?")]),
    rel("pet", "literal", "multi", narrower=["dog", "cat"], wh=["What", "Who"],
        src=[S["multi154c"], S["listed139e"], "scripts/fable_notebook_contract.py:480"]),
    rel("dog", "person", "multi", src=[S["multi154c"], S["name171"], S["listed139e"]]),
    rel("cat", "person", "multi", src=[S["multi154c"], S["name171"]]),
    rel("employer", "organization", "single", src=[S["verb167"], S["verb167d"], S["b92"], S["b92cues"], S["listen"]],
        teach=[P("{X} works for {Y}.", "live", S["verb167"]), P("{X} works at {Y}.", "live", S["verb167d"]),
               P("{X} is employed by {Y}.", "live", S["b92"])],
        ask=[P("Who does {X} work for?", "live", S["verb167"]), P("Where does {X} work?", "live", S["verb167d"]),
             P("Who employs {X}?")],
        inverse=[INV("Who works (at|for) {Y}?"), INV("Who does {Y} employ?")],
        value_guard="When Y is a known PERSON, 'X works for Y' means boss, not employer (NEW rule, build 2 only; build 1 never writes).",
        notes=("Ben's rule: verb facts become relations. 'Sabine works at Acme.' -> (Sabine, employer, Acme). "
               "No separate 'workplace' relation in v1: code stores employer for both 'works at' and 'works for'.")),
    rel("occupation", "literal", "single", aliases=["job", "profession"],
        src=[S["b92"], S["b92cues"]],
        teach=[P("{X} works in the field of {Y}.", "live", S["b92"]), P("{X} works as (a|an) {Y}.")],
        ask=[P("What does {X} do for (a living|work)?")],
        notes="'X is a nurse.' is NOT taught as occupation (fable_fix173b_username.py:75 treats such copulas as non-names; too ambiguous)."),
    rel("work_location", "place", "single", src=[S["b73"], S["b73cues"]],
        teach=[P("{X} worked in the city of {Y}", "live", S["b73"])]),
    rel("school", "place", "single", src=[S["listed139e"], "sessions152"],
        teach=[P("{X} goes to {Y}.")], ask=[P("Where does {X} go to school?")], inverse=[INV("Who goes to {Y}?")]),
    rel("educated_at", "place", "multi", aliases=["alma mater"], src=[S["b73"], S["b92cues"]],
        teach=[P("The univeristy where {X} was educated is {Y}", "live", S["b73"] + " (typo is in the data)"),
               P("{X} studied at {Y}.")],
        ask=[P("Where did {X} study?")]),
    rel("title", "literal", "single", src=["rt136 / sessions152 (\"Aldo's title is Dean ...\")"]),
]

# ================================================================= places
R += [
    rel("city", "place", "single", say_no=True, aliases=["town"], storage=["lives_in", "town"],
        src=[S["single154"], S["chain174"], S["verb167"], S["listed139e"], S["whcity158c"], S["listen"], S["apos193"]],
        teach=[P("{X} lives in {Y}.", "live", S["verb167"]), P("{X} moved to {Y}.", "not_live", S["listen"]),
               P("{X} resides in {Y}.", "not_live", S["listen"])],
        ask=[P("Where does {X} live?", "live", S["verb167"]), P("What (city|town) does {X} live in?", "live", S["whcity158c"])],
        yesno=[P("Does {X} live in {Y}?")],
        inverse=[INV("Who lives in {Y}?", "layer_c", S["rev190"])],
        notes=("The key 'city' means 'place X lives'. bench65 uses 'lives_in' for the same idea "
               "(fable_bench65_notebook_arm.py:161, values can be countries); read-only storage key.")),
    rel("home", "place", "single", src=[S["d158b"] + " WHERE_LIVE_CANDIDATES"],
        notes="Not aliased to city: a home can be an address or a house. 158b tried it as a where-live candidate."),
    rel("hometown", "place", "single", aliases=["home town"], storage=["home_town", "origin"],
        src=[S["listed139e"], S["d158b"], S["listen"]],
        teach=[P("{X} is from {Y}.", "not_live", S["listen"]), P("{X} comes from {Y}.", "not_live", S["listen"])],
        ask=[P("Where is {X} from?", "not_live", S["d158b"]), P("Where does {X} come from?")],
        inverse=[INV("Who is from {Y}?")],
        notes="Qwen listening stores 'origin'; FakeEars stores 'hometown'/'home_town'. Read all three at ask time."),
    rel("place_of_birth", "place", "single", say_no=True, aliases=["birthplace", "place of birth"],
        storage=["birthplace"], src=[S["single154"], S["verb167"], S["listed139e"], S["b73"], S["b92cues"], S["rev190"]],
        teach=[P("{X} was born in {Y}.", "live", S["verb167"]), P("{X} was born in the city of {Y}", "live", S["b73"])],
        ask=[P("Where was {X} born?", "live", S["verb167"])],
        inverse=[INV("Who was born in {Y}?", "layer_c", S["rev190"])],
        value_guard=NOT_DATE_GUARD,
        notes="167 stores 'place_of_birth', 138g/190/listening use 'birthplace': same meaning, both read."),
    rel("place_of_death", "place", "single", src=[S["b73"]],
        teach=[P("{X} died in the city of {Y}", "live", S["b73"]), P("{X} died in {Y}.")],
        ask=[P("Where did {X} die?")], value_guard=NOT_DATE_GUARD),
    rel("country", "place", "single", src=[S["listed139e"]],
        notes="Ambiguous (residence vs citizenship). Never aliased to either."),
    rel("country_of_citizenship", "place", "single", aliases=["nationality", "citizenship"], src=[S["b73"], S["b73cues"]],
        teach=[P("{X} is a citizen of {Y}", "live", S["b73"])], ask=[P("What country is {X} a citizen of?")]),
    rel("country_of_origin", "place", "single", src=[S["b73"]],
        teach=[P("{X} was created in the country of {Y}", "live", S["b73"])]),
    rel("capital", "place", "single", say_no=True, src=[S["single154"], S["b73"]],
        teach=[P("The capital of {X} is {Y}", "live", S["b73"])],
        inverse=[INV("What is {Y} the capital of?")]),
    rel("continent", "place", "single", src=[S["b73"]],
        teach=[P("{X} is located in the continent of {Y}", "live", S["b73"])]),
    rel("headquarters_location", "place", "single", aliases=["headquarters"], src=[S["b73"], S["b92cues"]],
        teach=[P("The headquarters of {X} is located in the city of {Y}", "live", S["b73"])],
        ask=[P("Where is {X} based?"), P("Where are {X}'s headquarters?")]),
    rel("location_of_formation", "place", "single", src=[S["b73"]],
        teach=[P("{X} was founded in the city of {Y}", "live", S["b73"])],
        value_guard="'founded in' + date is date_founded (not in v1); + place is this relation."),
]

# ========================================================== creative work
def creative(name, verb_past, verb_base, noun_work, *, status="known", storage=(), inv_storage=(),
             src=(), extra_teach=(), aliases=(), by_where="NEW", by_src="NEW", notes=""):
    return rel(
        name, "person", "multi", status=status, aliases=aliases, storage=storage, inv_storage=inv_storage, src=src,
        teach=[P(f"{{X}} was {verb_past} by {{Y}}.", by_where, by_src),
               P(f"{{Y}} {verb_past} {{X}}.")] + list(extra_teach),
        ask=[P(f"Who {verb_past} {{X}}?"), P(f"Who was {{X}} {verb_past} by?")],
        yesno=[P(f"Did {{Y}} {verb_base} {{X}}?"), P(f"Was {{X}} {verb_past} by {{Y}}?")],
        inverse=[INV(f"What did {{Y}} {verb_base}?"), INV(f"What has {{Y}} {verb_past}?"),
                 INV(f"Which {noun_work} did {{Y}} {verb_base}?")],
        notes=(notes + " " if notes else "") + (
            f"X is the work, Y the person. '{{Y}} is the {name} of {{X}}.' is the generic 'inverted' teach; "
            "bench73 stores that shape as an inverse _of key (see inverse_storage_keys)."),
    )


R += [
    creative("composer", "composed", "compose", "(song|piece|work)", storage=["composed_by"], inv_storage=["composer_of"],
             src=[S["b73"], S["b73rev"]], by_where="live", by_src=S["b73"],
             notes=("Evidence today: 'Ada Pell is the composer of Blue Rain.' saves junk (exp 215 fixing); "
                    "'Who composed Blue Rain?' misroutes to the self router; 'What did Ada Pell compose?' not understood.")),
    creative("author", "wrote", "write", "(book|work)", storage=["written_by"], inv_storage=["author_of"],
             src=[S["b73"], S["b73rev"], S["b73cues"]], by_where="live", by_src=S["b73"] + " ('was written by')",
             extra_teach=[P("The author of {X} is {Y}", "live", S["b73"])], aliases=["writer"]),
    creative("painter", "painted", "paint", "(painting|picture)", status="NEW"),
    creative("director", "directed", "direct", "(film|movie|play)", storage=["director_manager"],
             src=[S["b92"], S["office135"], S["q132"]], by_where="NEW", by_src="NEW",
             extra_teach=[P("The director of {X} is {Y}", "live", S["b92"])],
             notes=("bench92 key director_manager ('The director of X is Y') covers organisations and films alike; "
                    "read as the same storage. 'manager' is NOT an alias here (it is boss).")),
    creative("founder", "founded", "found", "(company|organisation|group)", storage=["founded_by"], inv_storage=["founder_of"],
             src=[S["b73"], S["b92cues"]], by_where="live", by_src=S["b73"]),
    creative("inventor", "invented", "invent", "(thing|machine)", storage=["invented_by"], inv_storage=["inventor_of"],
             src=[S["b73"], S["b73rev"]], by_where="live", by_src=S["b73"]),
    creative("designer", "designed", "design", "(thing|product)", status="NEW"),
    creative("discoverer", "discovered", "discover", "(thing|place)", storage=["discovered_by"], inv_storage=["discoverer_of"],
             src=[S["b73"], S["b73rev"]], by_where="live", by_src=S["b73"]),
    creative("architect", "built", "build", "(building|house)", status="NEW",
             notes="Uses 'built by' because 'designed by' belongs to designer (one template, one relation)."),
    creative("creator", "created", "create", "(thing|work)", src=[S["b73"], S["listen"]], aliases=["maker"],
             by_where="live", by_src=S["b73"] + " ('was created by')",
             notes="Also the self relation 'Who made you?' (listening path) -- the self router owns that question."),
    creative("developer", "developed", "develop", "(product|game|software)", src=[S["b73"]], by_where="live", by_src=S["b73"]),
    creative("performer", "performed", "perform", "(song|piece)", src=[S["b73"]], by_where="live", by_src=S["b73"],
             ),
    rel("manufacturer", "organization", "single", aliases=["producer"], src=[S["b73"], S["b92cues"], S["q132"]],
        teach=[P("The company that produced {X} is {Y}", "live", S["b73"]), P("{X} is made by {Y}.")],
        ask=[P("Who makes {X}?"), P("Who produced {X}?")], inverse=[INV("What does {Y} make?")]),
    rel("notable_work", "work", "multi", src=[S["multi154c"], S["b73"]],
        teach=[P("{X} is famous for {Y}", "live", S["b73"])], ask=[P("What is {X} famous for?")]),
    rel("original_broadcaster", "organization", "single", aliases=["broadcaster"], src=[S["b92"], S["office135"]],
        teach=[P("The origianl broadcaster of {X} is {Y}", "live", S["b92"] + " (typo is in the data)")]),
    rel("genre", "literal", "single", src=[S["b73"]], teach=[P("The type of music that {X} plays is {Y}", "live", S["b73"])]),
]

# ================================================================ offices
R += [
    rel("officeholder", "person", "single", src=[S["b73"], S["office135"]],
        notes="bench-only catch-all 'The (.+?) is (.+?)' (fable_bench73_english_arm.py, LAST pattern) for 'The President of Syria is ...'."),
    rel("head_of_state", "person", "single", src=[S["b73"], S["office135"]],
        teach=[P("The name of the current head of state in {X} is {Y}", "live", S["b73"])]),
    rel("head_of_government", "person", "single", src=[S["b73"], S["office135"]],
        teach=[P("The name of the current head of the {X} government is {Y}", "live", S["b73"])]),
    rel("chairperson", "person", "single", aliases=["chair"], src=[S["b73"], S["office135"]],
        teach=[P("The chairperson of {X} is {Y}", "live", S["b73"])]),
    rel("chief_executive_officer", "person", "single", aliases=["ceo", "chief executive"], src=[S["b73"], S["office135"]],
        teach=[P("The chief executive officer of {X} is {Y}", "live", S["b73"])]),
    rel("head_coach", "person", "single", aliases=["head coach"], src=[S["b92"], S["office135"]],
        teach=[P("The head coach of {X} is {Y}", "live", S["b92"])]),
    rel("dean", "person", "single", src=["sessions152 (\"who is the dean of the school of music?\")"],
        notes="Office word; 'Aldo's title is Dean of ...' is title, not dean."),
]

# ====================================================== literals / self
R += [
    rel("language", "language", "multi", storage=["languages_spoken_written_or_signed"],
        src=[S["verb167d"], S["multi154e"], S["b73"]],
        teach=[P("{X} speaks {Y}.", "live", S["verb167d"]), P("{X} speaks the language of {Y}", "live", S["b73"])],
        ask=[P("What language(s) does {X} speak?", "live", S["verb167d"])],
        yesno=[P("Does {X} speak {Y}?")], inverse=[INV("Who speaks {Y}?")]),
    rel("official_language", "language", "multi", src=[S["b73"]],
        teach=[P("The official language of {X} is {Y}", "live", S["b73"])]),
    rel("language_of_work_or_name", "language", "single", src=[S["b92"]],
        teach=[P("{X} was written in the language of {Y}", "live", S["b92"])]),
    rel("religion_or_worldview", "literal", "single", aliases=["religion"], src=[S["b73"]],
        teach=[P("{X} is affiliated with the religion of {Y}", "live", S["b73"])]),
    rel("sport", "literal", "single", src=[S["b73"]], teach=[P("{X} is associated with the sport of {Y}", "live", S["b73"])],
        ask=[P("What sport does {X} play?")]),
    rel("position_played_on_team_speciality", "literal", "single", aliases=["position"], src=[S["b73"]],
        teach=[P("{X} plays the position of {Y}", "live", S["b73"])]),
    rel("favorite_color", "literal", "single",
        aliases=["favourite colour", "favorite colour", "favourite color", "favorite color"], src=[S["listen"]],
        notes="Self router intent D1 declines 'favourite' questions about the agent; X's favourite colour is a normal fact."),
    rel("color", "literal", "single", aliases=["colour"], src=["sessions152 (\"Biscuit's color is brown.\")"]),
    rel("hobby", "literal", "multi", status="known", src=["scripts/fable_reasoner50.py:99"],
        teach=[P("{X} likes {Y}.")], notes="'likes' as a teach verb is risky (opinions); build 2 decides."),
    rel("nickname", "literal", "multi", status="NEW", teach=[P("{X} is called {Y}.")],
        notes="Risk: collides with alias teaching ('Call me Ben' / 173 username); question-only in build 1."),
    rel("code", "literal", "single", src=["rt136 (\"Tom's code is 42.\")"]),
    rel("mood", "literal", "single", src=["rt136"]),
    rel("toy", "literal", "multi", src=["sessions152 (\"Milo's toy is ball\")"]),
    rel("training_data", "literal", "single", aliases=["training data"], src=[S["listen"]],
        generic=("possessive",), notes="Self relation ('What were you trained on?'); owned by the self path."),
    rel("age", "number", "single", src=[S["listen"], S["d158b"]],
        teach=[P("{X} is {Y} years old.", "not_live", S["listen"])],
        ask=[P("How old is {X}?", "not_live", S["d158b"]), P("How old am I?", "NEW")],
        wh=["What"],
        notes="'How old are you?' about the agent stays with the self router (intent D9)."),
]

# ================================================================== dates
R += [
    rel("birthday", "date", "single", say_no=True, src=[S["d158b"], "rt136 (\"Tom's birthday is 1999.\")"],
        date_rule=DATE_RULE, value_guard=DATE_GUARD,
        ask=[P("When is {X}'s birthday?", "not_live", S["d158b"]), P("When is my birthday?", "NEW",
             "NEW (today answered 'You never taught me their age', fable_fix168_ground.py:66)"),
             P("What day is {X}'s birthday?")],
        inverse=[INV("Whose birthday is (in|on) {Y}?"), INV("Who has a birthday (in|on) {Y}?")],
        notes="Not an alias of date_of_birth: a birthday has no year; never derived from one at write time."),
    rel("anniversary", "date", "single", src=[S["d158b"]], date_rule=DATE_RULE, value_guard=DATE_GUARD,
        ask=[P("When is {X}'s anniversary?", "not_live", S["d158b"])]),
    rel("date_of_birth", "date", "single", say_no=True, aliases=["birth date", "date of birth"],
        src=[S["single154"]], date_rule=DATE_RULE, value_guard=DATE_GUARD,
        teach=[P("{X} was born (on|in) {Y}.", "NEW", "NEW (today 'was born in' always means place, fable_fix167_verb.py:92)")],
        ask=[P("When was {X} born?")],
        notes="'born in June' -> date_of_birth, 'born in Oslo' -> place_of_birth, decided by the value guard."),
    rel("date_of_death", "date", "single", status="NEW", date_rule=DATE_RULE, value_guard=DATE_GUARD,
        teach=[P("{X} died (on|in) {Y}.")], ask=[P("When did {X} die?")]),
]

# ------------------------------------------------------------------ extras
EXCLUSIONS = {
    "never_taught_rel_*": "bench65 placeholder keys for abstention tests; never a real relation",
    "cities": "plural surface of city in one rt136 turn; plurals are 162b's job",
    "friends": "plural surface of friend; plurals are 162b's job",
    "capitol": "misspelling of capital in one rt143 question (typo layer 165's job)",
    "tess": "extraction noise: \"what's tess's city?\" (a lowercase name)",
    "name": "'the name of the city where ...' question filler, not a relation",
    "head": "'the head of ...' fragment inside a longer office question",
    "current_head": "fragment of 'the current head of state/government'",
    "city_where_the_author": "fragment of a relative-clause question (132 rewriter)",
    "city_where_the_producer": "fragment of a relative-clause question",
    "company_employing_the_developer": "fragment of a relative-clause question",
    "country_that_the_founder": "fragment of a relative-clause question",
    "country_where_the_spouse": "fragment of a relative-clause question",
    "nation_whose_citizenship_is_held_by_the_wife": "fragment of a relative-clause question",
    "field": "surface inside 'works in the field of' (template of occupation)",
    "creator_country": "bench92 cue-only key (EXTRA_REL_CUES) with no taught data",
}

SELF_ROUTER_NOTE = ("Questions about the agent itself ('What is your name?', 'Who made you?', 'How old are you?') "
                    "stay with the self router (fable_loop138_agent.py:181 route127). The table reader must not claim "
                    "any turn whose subject slot is 'you'/'your'.")

table = {
    "version": "v1",
    "date": "2026-09-22",
    "purpose": ("One relation table for (a) the hand-written reader (rule table) and (b) training labels for a "
                "learned reader. Facts are (X, R, Y) read as \"X's R is Y\"."),
    "template_syntax": {
        "value_kinds": {"person": "a named individual (people and named pets; 171 NAME_KEYS)",
                        "place": "a place name", "organization": "a company or group", "work": "a title of a work",
                        "date": "month / day / year", "number": "a number", "language": "a language name",
                        "literal": "any short phrase"},
        "slots": {"X": "subject", "Y": "value", "R": "relation word (canonical or alias)", "WH": "question word from 'wh'"},
        "alternation": "(a|b)", "optional": "[word]",
        "where_values": {"live": "handled by some piece in the 138i stack today",
                         "layer_c": "handled by a layer-C piece being merged now (not yet in 138i)",
                         "not_live": "exists in repo code but not in the 138i stack",
                         "NEW": "no code handles it today"},
        "status_values": {"known": "relation name appears in code or frozen suite/bench data",
                          "NEW": "relation name appears nowhere in code or data"},
    },
    "rules": {
        "taught_facts_win": "Taught facts are never overwritten by inferences; inverse and narrower answers are read-only.",
        "inverse_never_stored": ("Inverse phrasings are answered at question time by scanning live taught facts "
                                 "(like fable_fix190_reverse.py:149 reverse_subjects190), labelled '" + INVERSE_LABEL +
                                 "', and never written."),
        "aliases_true_synonyms_only": "An alias must mean exactly the same relation (boss = manager; boss != employer).",
        "narrower_is_one_way": "A narrower fact (wife) may answer a broader question (spouse), labelled; never the reverse.",
        "storage_keys_read_all": ("Existing code has stored the same relation under several keys. At question time the "
                                  "reader looks under every storage key; if two keys give different current values it "
                                  "reports both and asks, never picks one."),
        "inverse_storage_keys": ("Legacy bench keys whose subject and value are swapped ((Ada, composer_of, Blue Rain) == "
                                 "(Blue Rain, composer, Ada)). Read-only; the table never writes them."),
        "verb_facts_are_relations": "Ben's standing decision: anything readable as a relation is (e.g. 'X works at Y' -> employer).",
        "open_vocabulary_fallback": ("Relations not in this table still work through the existing possessive path "
                                     "(FakeEars._relation snake-cases any surface). The table adds shapes; it removes nothing."),
        "self_questions": SELF_ROUTER_NOTE,
    },
    "generic_patterns": GENERIC,
    "inventory_exclusions": EXCLUSIONS,
    "relations": R,
}

OUT.write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT} ({len(R)} relations)")
