#!/usr/bin/env python3
"""Exp 237b: build relation_table_v1_2.json = table v1.1 (read-only) + a
SYSTEMATIC category-by-category enumeration of everyday relations.

Source of every row: general English knowledge, organised by category
(family, partners, friends, work, school, health and services, home and
places, contact details, identity, possessions/vehicles/pets,
organisations, creative works, sports and hobbies, dates and events).
Nothing here was read from any panel.

Rules (217/237, restated in design/v3/30-modes/237b-tablev12-opus.md):
  * aliases = TRUE synonyms only (same relation, same person/thing);
    every answer uses the STORED relation word, so it stays true;
  * near-synonyms that are different relations get their own rows and are
    never linked (boss/employer, hometown/birthplace, girlfriend/wife,
    landlord/owner, tutor/teacher, counsellor/therapist, ...);
  * the only new cross-relation link is birthday <-> date of birth (the
    reply always names the stored word: "X's birthday is May 3.");
  * inverse entries are answer-time only and labelled "(worked out
    backwards)" by the 221 reader; inverse storage keys are always also
    rows of their own, so an ask on that word never jumps groups.
Writes artifacts/claude-table237b-20260922/relation_table_v1_2.json and
lists every addition in its "v1_2_additions" block. v1.1 is not edited.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V11 = ROOT / "artifacts/claude-table237-20260922/relation_table_v1_1.json"
OUT = ROOT / "artifacts/claude-table237b-20260922/relation_table_v1_2.json"
SRC = "NEW in v1.2 (exp 237b; category enumeration, general English)"

t = copy.deepcopy(json.loads(V11.read_text(encoding="utf-8")))
t["version"] = "v1.2"
t["based_on"] = ("relation_table_v1_1.json (unchanged; this file = v1.1 + "
                 "the 237b category enumeration)")
rels = {r["name"]: r for r in t["relations"]}
log: list[str] = []

DATE_GUARD = rels["birthday"]["value_guard"]
DATE_RULE = rels["birthday"]["date_rule"]
PERSON_GEN = ["possessive", "my", "of_form", "inverted", "reverse"]


def key(s: str) -> str:
    return "_".join(s.lower().split())


def p(tmpl: str) -> dict:
    return {"t": tmpl, "where": "NEW", "src": SRC}


def all_surfaces() -> dict[str, str]:
    out = {}
    for r in t["relations"]:
        for s in [r["name"]] + [key(a) for a in r["aliases"]] + list(
                r.get("storage_keys", [])):
            out.setdefault(key(s), r["name"])
    return out


def add_alias(cat: str, rel: str, *als: str) -> None:
    surf = all_surfaces()
    for a in als:
        k = key(a)
        if k in surf and surf[k] != rel:
            sys.exit(f"alias collision: {a!r} already in {surf[k]}")
        if a not in rels[rel]["aliases"]:
            rels[rel]["aliases"].append(a)
        if k not in rels[rel]["storage_keys"] and k != rel:
            rels[rel]["storage_keys"].append(k)
    log.append(f"[{cat}] alias {rel}: +{list(als)}")


def add_ask(cat: str, rel: str, *tmpls: str, kind: str = "ask") -> None:
    have = {x["t"] for x in rels[rel][kind]}
    for s in tmpls:
        if s not in have:
            rels[rel][kind].append(p(s))
    log.append(f"[{cat}] {kind} template {rel}: +{list(tmpls)}")


def replace_ask(cat: str, rel: str, old: str, new: str) -> None:
    for x in rels[rel]["ask"]:
        if x["t"] == old:
            x["t"] = new
            x["src"] = SRC + f" (was {old!r})"
            log.append(f"[{cat}] ask template {rel}: {old!r} -> {new!r}")
            return
    sys.exit(f"replace_ask: {old!r} not in {rel}")


def new_rel(cat: str, name: str, aliases=(), wh=None,
            card="single", vk="person", ask=(), inverse=(), storage=(),
            date=False, inv_keys=()) -> None:
    if name in rels:
        sys.exit(f"new_rel: {name} exists")
    if wh is None:  # default question words by value type
        wh = {"person": ("Who",), "organization": ("Who", "What")}.get(
            vk, ("What",))
    surf = all_surfaces()
    for s in [name] + [key(a) for a in aliases] + list(storage):
        if key(s) in surf:
            sys.exit(f"new_rel {name}: surface {s!r} already in "
                     f"{surf[key(s)]}")
    keys = [name] + [s for s in storage if s != name] + [
        key(a) for a in aliases]
    seen: list[str] = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    r = {"name": name, "aliases": list(aliases), "storage_keys": seen,
         "inverse_storage_keys": list(inv_keys), "generic": list(PERSON_GEN),
         "wh": list(wh), "cardinality": card, "narrower": [],
         "value_kind": vk, "status": "NEW", "src": SRC, "category": cat,
         "teach": [], "ask": [p(s) for s in ask],
         "inverse": [p(s) for s in inverse], "yesno": [],
         "yesno_can_say_no": False}
    if date:
        r["value_guard"] = DATE_GUARD
        r["date_rule"] = DATE_RULE
        r["wh"] = ["When", "What"]
        r["value_kind"] = "date"
    r["generic"] = list(GEN_BY_KIND[r["value_kind"]])
    t["relations"].append(r)
    rels[name] = r
    log.append(f"[{cat}] new relation {name} (aliases {list(aliases)})")


# helpers for the common row shapes
def people(cat, names, card="single"):
    for n in names:
        if isinstance(n, tuple):
            new_rel(cat, n[0], aliases=n[1], card=card)
        else:
            new_rel(cat, n, card=card)


WHAT = ("What",)
WHERE = ("Where", "What")
WHICH = ("What", "Which")

# ======================================================================
# 0. GENERIC ask wordings (apply to every row that uses the family)
# ======================================================================
g = t["generic_patterns"]
# v1.1 rows: add the "the R for X" form (and "What's the R of X").
g["of_form"]["ask"] += [
    p("{WH} is the {R} for {X}?"), p("Who's the {R} for {X}?"),
    p("What's the {R} of {X}?"), p("What's the {R} for {X}?")]
log.append("[generic] of_form: 'the R for X' (WH is / Who's / What's) and "
           "\"What's the R of X\"")
# New rows: typed generic families, so each row only carries wordings that
# fit its value type (no "When's X's dentist?", no "Who is X's postcode?").
# This keeps the pattern count, and so the reading time, small.
g["p_person"] = {"ask": [p("{WH} is {X}'s {R}?"), p("Who's {X}'s {R}?"),
                         p("What is the name of {X}'s {R}?"),
                         p("What's the name of {X}'s {R}?")]}
g["my_person"] = {"ask": [p("{WH} is my {R}?"), p("Who's my {R}?"),
                          p("What is my {R}'s name?"),
                          p("What's my {R}'s name?"),
                          p("What is the name of my {R}?")]}
g["of_person"] = {"ask": [p("{WH} is the {R} of {X}?"),
                          p("Who's the {R} of {X}?"),
                          p("{WH} is the {R} for {X}?"),
                          p("Who's the {R} for {X}?")]}
g["p_thing"] = {"ask": [p("{WH} is {X}'s {R}?"), p("What's {X}'s {R}?")]}
g["my_thing"] = {"ask": [p("{WH} is my {R}?"), p("What's my {R}?")]}
g["of_thing"] = {"ask": [p("{WH} is the {R} of {X}?"),
                         p("What's the {R} of {X}?"),
                         p("{WH} is the {R} for {X}?"),
                         p("What's the {R} for {X}?")]}
g["p_date"] = {"ask": [p("{WH} is {X}'s {R}?"), p("When's {X}'s {R}?"),
                       p("What's {X}'s {R}?"), p("When was {X}'s {R}?")]}
g["my_date"] = {"ask": [p("{WH} is my {R}?"), p("When's my {R}?"),
                        p("What's my {R}?")]}
g["of_date"] = {"ask": [p("{WH} is the {R} of {X}?"),
                        p("When was the {R} of {X}?"),
                        p("What's the {R} of {X}?")]}
log.append("[generic] new typed families p_/my_/of_ x person/thing/date "
           "for the new rows")
GEN_BY_KIND = {
    "person": ["p_person", "my_person", "of_person", "inverted", "reverse"],
    "date": ["p_date", "my_date", "of_date"],
    "literal": ["p_thing", "my_thing", "of_thing"],
    "number": ["p_thing", "my_thing", "of_thing"],
    "language": ["p_thing", "my_thing", "of_thing"],
    "place": ["p_thing", "my_thing", "of_thing", "reverse"],
    "organization": ["p_thing", "my_thing", "of_thing", "reverse"],
    "work": ["p_thing", "my_thing", "of_thing", "reverse"],
}

# ======================================================================
# 1. FAMILY AND HOUSEHOLD
# ======================================================================
C = "family"
add_alias(C, "mother", "mama", "momma", "mam")
add_alias(C, "father", "pappa")
add_alias(C, "grandmother", "gran", "nan", "nana", "nanna", "grandmom")
add_alias(C, "grandfather", "granddad", "grandad", "gramps", "grandpop")
add_alias(C, "aunt", "auntie", "aunty")
people(C, [("grandparent", ["grand parent"])], card="multi")
people(C, [("stepbrother", ["step-brother", "step brother"]),
           ("stepsister", ["step-sister", "step sister"]),
           ("half_brother", ["half-brother", "half brother"]),
           ("half_sister", ["half-sister", "half sister"]),
           ("stepson", ["step-son"]), ("stepdaughter", ["step-daughter"]),
           ("stepchild", ["step-child"]), "twin",
           ("great_grandmother", ["great-grandmother", "great grandma",
                                  "great-grandma"]),
           ("great_grandfather", ["great-grandfather", "great grandpa",
                                  "great-grandpa"]),
           ("godchild", ["god child"]), "godson", "goddaughter",
           ("godparent", ["god parent"])], card="multi")
people(C, [("mother_in_law", ["mother-in-law", "mother in law"]),
           ("father_in_law", ["father-in-law", "father in law"]),
           ("stepparent", ["step-parent"]), "guardian",
           ("foster_mother", ["foster mother", "foster mom", "foster mum"]),
           ("foster_father", ["foster father", "foster dad"])])
people(C, [("brother_in_law", ["brother-in-law", "brother in law"]),
           ("sister_in_law", ["sister-in-law", "sister in law"]),
           ("son_in_law", ["son-in-law", "son in law"]),
           ("daughter_in_law", ["daughter-in-law", "daughter in law"])],
       card="multi")
people(C, [("tenant", [])], card="multi")   # inverse partner of landlord
people(C, ["lodger", "housekeeper", ("au_pair", ["au pair"])])

# ======================================================================
# 2. PARTNERS
# ======================================================================
C = "partners"
new_rel(C, "fiancee", aliases=["fiancée"])
people(C, [("ex_wife", ["ex-wife", "former wife"]),
           ("ex_husband", ["ex-husband", "former husband"]),
           ("ex_girlfriend", ["ex-girlfriend"]),
           ("ex_boyfriend", ["ex-boyfriend"]),
           ("ex_partner", ["ex-partner", "former partner"]),
           ("ex", [])])
add_alias(C, "partner", "life partner")
add_ask(C, "spouse", "Who is {X} married to now?", "Who's {X} married to?")

# ======================================================================
# 3. FRIENDS AND SOCIAL
# ======================================================================
C = "social"
add_alias(C, "best_friend", "bestie", "BFF", "best mate", "bff")
add_alias(C, "friend", "pal", "buddy")
people(C, [("pen_pal", ["pen pal", "penpal", "pen friend", "pen-pal"]),
           ("childhood_friend", ["childhood friend"]),
           "acquaintance", "enemy", "idol", ("role_model", ["role model"])],
       card="multi")
people(C, [("hero", [])])

# ======================================================================
# 4. WORK AND BUSINESS
# ======================================================================
C = "work"
add_ask(C, "boss", "Who does {X} report to?", "Who manages {X}?")
people(C, [("employee", ["staff member"]), "client", "customer",
           ("business_partner", ["business partner"]),
           ("direct_report", ["direct report"]), "intern", "trainee"],
       card="multi")
people(C, [("assistant", ["personal assistant"]), "secretary",
           "deputy", ("agent", ["talent agent"]),
           ("literary_agent", ["literary agent"]), "receptionist"])
add_alias(C, "work_location", "workplace", "place of work")
add_ask(C, "occupation", "What does {X} do?", "What does {X} work as?",
        "What does {X} do for work now?")
new_rel(C, "job_title", aliases=["job title"], wh=WHAT, vk="literal")
new_rel(C, "salary", wh=WHAT, vk="literal")
new_rel(C, "office", aliases=["office location"], wh=WHERE, vk="place")
new_rel(C, "department", aliases=["dept"], wh=WHICH, vk="literal",
        ask=["What department does {X} work in?",
             "Which department does {X} work in?"])
new_rel(C, "industry", aliases=["sector"], wh=WHAT, vk="literal",
        ask=["What industry is {X} in?"])

# ======================================================================
# 5. SCHOOL AND LEARNING
# ======================================================================
C = "school"
people(C, [("student", ["pupil"])], card="multi")
people(C, [("headmaster", ["head master"]),
           ("headmistress", ["head mistress"]),
           ("form_teacher", ["form teacher", "form tutor"]),
           ("homeroom_teacher", ["homeroom teacher"]),
           ("advisor", ["adviser", "academic advisor", "academic adviser"]),
           ("supervisor_academic", ["thesis supervisor", "PhD supervisor",
                                    "thesis advisor", "thesis adviser"]),
           ("professor", ["prof"]), "lecturer",
           ("teaching_assistant", ["teaching assistant"]),
           ("study_partner", ["study partner", "study buddy"]),
           ("lab_partner", ["lab partner"])])
new_rel(C, "university", aliases=["uni"], wh=WHERE, vk="organization",
        ask=["Where does {X} go to university?",
             "What university does {X} go to?",
             "Which university does {X} go to?",
             "What university does {X} attend?",
             "Which university does {X} attend?"])
new_rel(C, "college", wh=WHERE, vk="organization",
        ask=["Where does {X} go to college?",
             "What college does {X} go to?",
             "Which college does {X} go to?",
             "What college does {X} attend?"])
add_ask(C, "school", "What school does {X} go to?",
        "Which school does {X} go to?", "What school does {X} attend?",
        "Which school does {X} attend?", "Where did {X} go to school?")
new_rel(C, "degree", aliases=["qualification"], wh=WHAT, vk="literal")
new_rel(C, "grade", aliases=["school year", "year group"], wh=WHAT,
        vk="literal", ask=["What grade is {X} in?",
                           "What year is {X} in at school?"])
new_rel(C, "favorite_subject", aliases=["favourite subject",
                                        "favorite school subject",
                                        "favourite school subject"],
        wh=WHAT, vk="literal")
new_rel(C, "thesis", aliases=["dissertation"], wh=WHAT, vk="work")
add_ask(C, "teacher", "Who is {X} taught by?")

# ======================================================================
# 6. HEALTH AND SERVICES
# ======================================================================
C = "services"
people(C, [("optician", []), "optometrist", "ophthalmologist",
           ("eye_doctor", ["eye doctor"]),
           ("dietitian", ["dietician"]),
           ("physiotherapist", ["physio", "physical therapist"]),
           "chiropractor", "surgeon",
           ("paediatrician", ["pediatrician"]),
           "psychiatrist", "psychologist",
           ("counsellor", ["counselor"]), "midwife",
           ("carer", ["caregiver", "care giver"]),
           ("social_worker", ["social worker"]),
           ("dental_hygienist", ["dental hygienist", "hygienist"]),
           "orthodontist", "dermatologist", "cardiologist",
           ("hairdresser", ["hair stylist", "hairstylist"]),
           "electrician", "builder", "gardener", "cleaner", "handyman",
           ("personal_trainer", ["personal trainer"]),
           ("driving_instructor", ["driving instructor"]),
           ("swimming_instructor", ["swimming instructor",
                                    "swim instructor"]),
           ("music_teacher", ["music teacher"]),
           ("piano_teacher", ["piano teacher"]),
           ("guitar_teacher", ["guitar teacher"]),
           ("violin_teacher", ["violin teacher"]),
           ("singing_teacher", ["singing teacher", "voice teacher"]),
           ("drum_teacher", ["drum teacher", "drums teacher"]),
           ("dance_teacher", ["dance teacher"]),
           ("art_teacher", ["art teacher"]),
           ("maths_teacher", ["math teacher", "maths teacher",
                              "mathematics teacher"]),
           ("english_teacher", ["English teacher"]),
           ("science_teacher", ["science teacher"]),
           ("yoga_teacher", ["yoga teacher", "yoga instructor"]),
           ("estate_agent", ["estate agent", "realtor",
                             "real estate agent"]),
           ("financial_advisor", ["financial advisor",
                                  "financial adviser"]),
           ("insurance_agent", ["insurance agent"]),
           "solicitor", "notary", "banker",
           ("tax_advisor", ["tax advisor", "tax adviser"]),
           ("dog_walker", ["dog walker"]),
           ("pet_sitter", ["pet sitter"]), "childminder",
           ("postman", ["mail carrier", "mailman"]),
           "priest", "minister", "rabbi", "imam", "vicar", "chaplain",
           "caretaker", "chef", "cook", "driver", "chauffeur",
           "bodyguard", "butler"])
people(C, ["landlady"])
people(C, [("patient", [])], card="multi")   # inverse partner of doctor
# inverse storage keys (answer-time only, labelled; each is also a row)
rels["landlord"]["inverse_storage_keys"].append("tenant")
rels["teacher"]["inverse_storage_keys"].append("student")
rels["doctor"]["inverse_storage_keys"].append("patient")
log.append("[services] inverse storage keys: landlord<-tenant, "
           "teacher<-student, doctor<-patient (inverse questions only, "
           "labelled; tenant/student/patient are rows of their own)")
add_ask(C, "doctor", "Who treats {X}?")
add_ask(C, "tutor", "Who is {X} tutored by?")

# ======================================================================
# 7. HOME AND PLACES
# ======================================================================
C = "places"
add_ask(C, "city", "Where does {X} live (now|these days|nowadays|currently"
        "|at the moment|at present)?",
        "Where do I live (now|these days|nowadays|currently)?",
        "Where is {X} living (now|these days|nowadays|currently)?",
        "Where is {X} living?", "Which city does {X} live in?",
        "Which town does {X} live in?", "What city is {X} living in?")
add_ask(C, "hometown", "Where did {X} grow up?", "Where does {X} hail from?")
new_rel(C, "country_of_residence", aliases=["country of residence"],
        wh=WHERE, vk="place",
        ask=["What country does {X} live in?",
             "Which country does {X} live in?",
             "What country is {X} living in?"])
new_rel(C, "neighbourhood", aliases=["neighborhood"], wh=WHERE,
        vk="place", ask=["What neighbourhood does {X} live in?",
                         "What neighborhood does {X} live in?"])
new_rel(C, "postcode", aliases=["post code", "zip code", "zipcode",
                                "postal code", "ZIP"], wh=WHAT,
        vk="literal")
new_rel(C, "state", aliases=["home state"], wh=WHERE, vk="place",
        ask=["What state does {X} live in?",
             "Which state does {X} live in?"])
new_rel(C, "county", wh=WHERE, vk="place")
new_rel(C, "region", wh=WHERE, vk="place")
new_rel(C, "province", wh=WHERE, vk="place")
new_rel(C, "location", wh=WHERE, vk="place",
        ask=["Where is {X} located?"])
new_rel(C, "house", wh=WHAT, vk="literal")
new_rel(C, "flat", aliases=["apartment"], wh=WHERE, vk="literal")
new_rel(C, "holiday_home", aliases=["holiday home", "vacation home"],
        wh=WHERE, vk="place")
new_rel(C, "favorite_place", aliases=["favourite place"], wh=WHERE,
        vk="place")
new_rel(C, "favorite_restaurant", aliases=["favourite restaurant"],
        wh=WHERE, vk="place")
new_rel(C, "local_pub", aliases=["local pub"], wh=WHERE,
        vk="place")
new_rel(C, "gym", wh=WHERE, vk="place")
new_rel(C, "church", wh=WHERE, vk="place")
new_rel(C, "hospital", wh=WHERE, vk="place")
new_rel(C, "place_of_burial", aliases=["place of burial", "burial place",
                                       "resting place"],
        wh=WHERE, vk="place", ask=["Where is {X} buried?"])

# ======================================================================
# 8. CONTACT DETAILS
# ======================================================================
C = "contact"
add_alias(C, "phone_number", "telephone number", "contact number",
          "phone no", "tel number")
add_alias(C, "email", "e-mail", "e-mail address", "email id")
add_alias(C, "address", "home address", "street address")
new_rel(C, "mobile_number", aliases=["mobile number", "mobile phone number",
                                     "cell number", "cell phone number",
                                     "cellphone number", "mobile no"],
        wh=WHAT, vk="literal")
new_rel(C, "landline", aliases=["landline number", "home phone number",
                                "home phone"], wh=WHAT, vk="literal")
new_rel(C, "work_phone", aliases=["work phone", "work number",
                                  "office number", "work phone number"],
        wh=WHAT, vk="literal")
new_rel(C, "work_email", aliases=["work email", "work email address",
                                  "office email"], wh=WHAT, vk="literal")
new_rel(C, "website", aliases=["web site", "web address"], wh=WHAT,
        vk="literal")
new_rel(C, "username", aliases=["user name"], wh=WHAT, vk="literal")
new_rel(C, "fax_number", aliases=["fax number", "fax"], wh=WHAT,
        vk="literal")
new_rel(C, "mailing_address", aliases=["mailing address",
                                       "postal address"], wh=WHAT,
        vk="literal")
new_rel(C, "work_address", aliases=["work address", "office address"],
        wh=WHAT, vk="literal")
add_ask(C, "phone_number", "What is {X}'s number?")
add_ask(C, "address", "What address does {X} live at?")

# ======================================================================
# 9. IDENTITY
# ======================================================================
C = "identity"
new_rel(C, "surname", aliases=["last name", "family name"], wh=WHAT,
        vk="literal")
new_rel(C, "first_name", aliases=["first name", "given name", "forename"],
        wh=WHAT, vk="literal")
new_rel(C, "middle_name", aliases=["middle name"], wh=WHAT, vk="literal")
new_rel(C, "maiden_name", aliases=["maiden name"], wh=WHAT, vk="literal")
new_rel(C, "full_name", aliases=["full name"], wh=WHAT, vk="literal")
new_rel(C, "stage_name", aliases=["stage name"], wh=WHAT, vk="literal")
new_rel(C, "pen_name", aliases=["pen name", "pseudonym", "nom de plume"],
        wh=WHAT, vk="literal")
add_alias(C, "nickname", "nick name", "nick-name")
add_alias(C, "date_of_birth", "birthdate", "DOB", "dob", "date born")
add_alias(C, "country_of_citizenship", "country of citizenship")
add_ask(C, "country_of_citizenship", "What nationality is {X}?",
        "What citizenship does {X} hold?")
add_ask(C, "date_of_birth", "When was {X} born again?")
add_ask(C, "age", "What age is {X}?", "How old is {X} now?")
add_alias(C, "religion_or_worldview", "faith")
new_rel(C, "birth_year", aliases=["year of birth", "birth year"],
        wh=WHAT, vk="literal",
        ask=["What year was {X} born?", "What year was {X} born in?",
             "In what year was {X} born?", "In which year was {X} born?"])
new_rel(C, "star_sign", aliases=["star sign", "zodiac sign",
                                 "astrological sign", "sign of the zodiac"],
        wh=WHAT, vk="literal")
new_rel(C, "blood_type", aliases=["blood type", "blood group"], wh=WHAT,
        vk="literal")
new_rel(C, "height", wh=WHAT, vk="literal", ask=["How tall is {X}?"])
new_rel(C, "weight", wh=WHAT, vk="literal")
new_rel(C, "shoe_size", aliases=["shoe size"], wh=WHAT, vk="literal")
new_rel(C, "eye_colour", aliases=["eye color", "eye colour"], wh=WHAT,
        vk="literal", ask=["What colour are {X}'s eyes?",
                           "What color are {X}'s eyes?"])
new_rel(C, "hair_colour", aliases=["hair color", "hair colour"], wh=WHAT,
        vk="literal", ask=["What colour is {X}'s hair?",
                           "What color is {X}'s hair?"])
new_rel(C, "gender", wh=WHAT, vk="literal")
new_rel(C, "pronouns", wh=WHAT, vk="literal")
new_rel(C, "ethnicity", wh=WHAT, vk="literal")
new_rel(C, "accent", wh=WHAT, vk="literal")
new_rel(C, "second_language", aliases=["second language"], wh=WHAT,
        vk="language")
new_rel(C, "home_country",
        aliases=["home country"], wh=WHERE,
        vk="place")
new_rel(C, "country_of_birth", aliases=["country of birth",
                                        "birth country"], wh=WHERE,
        vk="place", ask=["What country was {X} born in?",
                         "Which country was {X} born in?"])

# ======================================================================
# 10. POSSESSIONS, VEHICLES AND PETS
# ======================================================================
C = "possessions"
add_alias(C, "car", "automobile", "motor car", "motorcar")
add_ask(C, "car", "What car does {X} drive?", "What car does {X} have?",
        "What does {X} drive?", "What kind of car does {X} drive?",
        "What car do I drive?")
new_rel(C, "vehicle", wh=WHAT, vk="literal")
new_rel(C, "motorbike", aliases=["motorcycle", "motor bike"], wh=WHAT,
        vk="literal")
new_rel(C, "bicycle", aliases=["push bike", "pushbike"], wh=WHAT,
        vk="literal")
new_rel(C, "bike", wh=WHAT, vk="literal")
new_rel(C, "van", wh=WHAT, vk="literal")
new_rel(C, "truck", aliases=["lorry"], wh=WHAT, vk="literal")
new_rel(C, "boat", wh=WHAT, vk="literal")
new_rel(C, "number_plate", aliases=["number plate", "license plate",
                                    "licence plate", "registration number",
                                    "registration plate"], wh=WHAT,
        vk="literal")
new_rel(C, "phone", aliases=["mobile phone", "cell phone", "smartphone"],
        wh=WHAT, vk="literal")
new_rel(C, "laptop", wh=WHAT, vk="literal")
new_rel(C, "computer", aliases=["PC"], wh=WHAT, vk="literal")
new_rel(C, "watch", aliases=["wristwatch"], wh=WHAT, vk="literal")
new_rel(C, "guitar", wh=WHAT, vk="literal")
new_rel(C, "piano", wh=WHAT, vk="literal")
new_rel(C, "horse", wh=("Who", "What"), card="multi", vk="person")
new_rel(C, "pony", wh=("Who", "What"), card="multi", vk="person")
new_rel(C, "rabbit", aliases=["bunny"], wh=("Who", "What"), card="multi")
new_rel(C, "hamster", wh=("Who", "What"), card="multi")
new_rel(C, "guinea_pig", aliases=["guinea pig"], wh=("Who", "What"),
        card="multi")
new_rel(C, "parrot", wh=("Who", "What"), card="multi")
new_rel(C, "budgie", aliases=["budgerigar"], wh=("Who", "What"),
        card="multi")
new_rel(C, "bird", wh=("Who", "What"), card="multi")
new_rel(C, "fish", wh=("Who", "What"),
        card="multi")
new_rel(C, "goldfish", wh=("Who", "What"), card="multi")
new_rel(C, "tortoise", wh=("Who", "What"), card="multi")
new_rel(C, "turtle", wh=("Who", "What"), card="multi")
new_rel(C, "snake", wh=("Who", "What"), card="multi")
new_rel(C, "lizard", wh=("Who", "What"), card="multi")
new_rel(C, "puppy", wh=("Who", "What"), card="multi")
new_rel(C, "kitten", wh=("Who", "What"), card="multi")
new_rel(C, "mouse", wh=("Who", "What"), card="multi")
new_rel(C, "ferret", wh=("Who", "What"), card="multi")
add_ask(C, "pet", "What pet does {X} have?", "What pets does {X} have?")
add_ask(C, "dog", "What dog does {X} have?")
# favourites (films = movies are the same thing)
for base_, extra in [("film", ["movie"]), ("tv_show", ["TV show",
                     "TV programme", "TV program", "television show"]),
                     ("sport", []), ("team", []), ("band", []),
                     ("singer", []), ("game", []), ("drink", []),
                     ("fruit", []), ("flower", []), ("season", []),
                     ("number", []), ("author", ["writer"]),
                     ("actor", []), ("dessert", []),
                     ("meal", []), ("holiday", []),
                     ("city", []), ("word", []), ("artist", []),
                     ("cartoon", []), ("snack", []), ("vegetable", []),
                     ("sweet", []), ("shop", ["store"]),
                     ("day", []), ("month", []), ("toy", []),
                     ("album", []), ("painting", []), ("poem", []),
                     ("musician", []), ("board_game", ["board game"]),
                     ("video_game", ["video game"])]:
    words = [base_.replace("_", " ")] + extra
    als = []
    for w in words:
        for f in ("favourite", "favorite"):
            als.append(f"{f} {w}")
    name = "favorite_" + base_
    new_rel(C, name, aliases=[a for a in als if key(a) != name], wh=WHAT,
            vk="literal")

# ======================================================================
# 11. ORGANISATIONS
# ======================================================================
C = "organisations"
add_alias(C, "headquarters_location", "HQ", "head office", "main office",
          "headquarters location")
add_ask(C, "headquarters_location", "Where is {X} headquartered?",
        "Where is {X}'s head office?", "Where is {X}'s HQ?")
add_alias(C, "chief_executive_officer", "chief executive officer",
          "CEO")
add_ask(C, "founder", "Who started {X}?", "Who set up {X}?",
        "Who established {X}?")
add_ask(C, "owner", "Who is {X} owned by?", "Who does {X} belong to?")
new_rel(C, "co_founder", aliases=["co-founder", "cofounder"])
new_rel(C, "president", card="single")
new_rel(C, "vice_president", aliases=["vice president", "vice-president",
                                      "VP"])
new_rel(C, "managing_director", aliases=["managing director"])
new_rel(C, "chief_financial_officer", aliases=["chief financial officer",
                                               "CFO"])
new_rel(C, "chief_technology_officer", aliases=[
    "chief technology officer", "CTO"])
new_rel(C, "chief_operating_officer", aliases=[
    "chief operating officer", "COO"])
new_rel(C, "treasurer")
new_rel(C, "general_manager", aliases=["general manager"])
new_rel(C, "head_chef", aliases=["head chef", "executive chef"])
new_rel(C, "parent_company", aliases=["parent company", "parent firm",
                                      "parent organisation",
                                      "parent organization"],
        vk="organization")
new_rel(C, "subsidiary", card="multi", vk="organization")
new_rel(C, "motto", wh=WHAT, vk="literal")
new_rel(C, "slogan", aliases=["tagline"], wh=WHAT, vk="literal")
new_rel(C, "mascot", wh=WHAT, vk="literal")
new_rel(C, "logo", wh=WHAT, vk="literal")
new_rel(C, "number_of_employees", aliases=["number of employees",
                                           "headcount", "staff count"],
        wh=WHAT, vk="number", ask=["How many employees does {X} have?",
                                   "How many people work at {X}?"])
new_rel(C, "registered_name",
        aliases=["registered name", "legal name"], wh=WHAT, vk="literal")
new_rel(C, "ticker", aliases=["ticker symbol",
                                                    "stock symbol"],
        wh=WHAT, vk="literal")
new_rel(C, "product", card="multi", wh=WHAT, vk="literal",
        ask=["What does {X} sell?"])
new_rel(C, "competitor", card="multi", vk="organization")
new_rel(C, "investor", card="multi")
new_rel(C, "sponsor", card="multi")
new_rel(C, "opening_hours", aliases=["opening hours", "opening times",
                                     "business hours"], wh=WHAT,
        vk="literal")

# ======================================================================
# 12. CREATIVE WORKS
# ======================================================================
C = "creative"
new_rel(C, "publisher", card="single", vk="organization",
        ask=["Who published {X}?", "Who was {X} published by?"],
        inverse=["What did {Y} publish?", "What has {Y} published?"])
new_rel(C, "illustrator", card="multi",
        ask=["Who illustrated {X}?", "Who was {X} illustrated by?"],
        inverse=["What did {Y} illustrate?"])
new_rel(C, "translator", card="multi",
        ask=["Who translated {X}?", "Who was {X} translated by?"])
new_rel(C, "editor", card="multi",
        ask=["Who edited {X}?", "Who was {X} edited by?"])
new_rel(C, "narrator", card="multi",
        ask=["Who narrated {X}?", "Who was {X} narrated by?"])
new_rel(C, "singer", card="multi", aliases=["vocalist"],
        ask=["Who sang {X}?", "Who sings {X}?"],
        inverse=["What did {Y} sing?"])
new_rel(C, "lyricist", card="multi",
        ask=["Who wrote the lyrics (to|for|of) {X}?"])
new_rel(C, "songwriter", aliases=["song writer"], card="multi")
new_rel(C, "sculptor", card="multi",
        ask=["Who sculpted {X}?", "Who was {X} sculpted by?"],
        inverse=["What did {Y} sculpt?"])
new_rel(C, "photographer", card="multi",
        ask=["Who photographed {X}?", "Who was {X} photographed by?"])
new_rel(C, "screenwriter", aliases=["scriptwriter", "script writer",
                                    "screen writer"], card="multi")
new_rel(C, "film_producer",
        aliases=["film producer", "movie producer"], card="multi")
new_rel(C, "record_producer", aliases=["record producer",
                                       "music producer"], card="multi")
new_rel(C, "record_label", aliases=["record label"],
        vk="organization")
new_rel(C, "lead_actor", aliases=["lead actor", "leading actor"],
        card="multi")
new_rel(C, "main_character", aliases=["main character", "protagonist"],
        card="multi")
new_rel(C, "villain", aliases=["antagonist"], card="multi")
new_rel(C, "setting", wh=WHERE, vk="place")
new_rel(C, "sequel", wh=WHAT, vk="work")
new_rel(C, "prequel", wh=WHAT, vk="work")
new_rel(C, "theme_tune",
        aliases=["theme tune", "theme song"], wh=WHAT, vk="work")
new_rel(C, "band", wh=WHICH, vk="organization",
        ask=["What band is {X} in?", "Which band is {X} in?"])
new_rel(C, "album", card="multi", wh=WHAT, vk="work")
new_rel(C, "debut_album", aliases=["debut album", "first album"],
        wh=WHAT, vk="work")
new_rel(C, "debut_novel",
        aliases=["debut novel", "first novel"], wh=WHAT, vk="work")
new_rel(C, "catchphrase", aliases=["catch phrase"], wh=WHAT, vk="literal")
new_rel(C, "channel", aliases=["TV channel"], wh=WHAT, vk="organization")

# ======================================================================
# 13. SPORTS AND HOBBIES
# ======================================================================
C = "sports"
add_ask(C, "team", "Who does {X} play for?", "Which team does {X} play for?",
        "What team is {X} on?", "Which team is {X} on?")
add_ask(C, "position_played_on_team_speciality", "What position does {X} "
        "play?")
add_alias(C, "hobby", "pastime")
add_ask(C, "hobby", "What does {X} do for fun?", "What are {X}'s hobbies?")
new_rel(C, "stadium", aliases=["home ground", "home stadium"],
        wh=WHERE, vk="place", ask=["Where does {X} play home games?",
                                   "Where does {X} play its home games?"])
new_rel(C, "league", wh=WHICH, vk="organization",
        ask=["What league does {X} play in?",
             "Which league does {X} play in?"])
new_rel(C, "shirt_number", aliases=["shirt number", "jersey number",
                                    "squad number", "kit number"],
        wh=WHAT, vk="number")
new_rel(C, "rival_club", aliases=["rival club",
                                                      "rival team"],
        card="multi", vk="organization")
new_rel(C, "training_partner",
        aliases=["training partner", "gym buddy"], card="multi")
new_rel(C, "dance_partner", aliases=["dance partner"])
new_rel(C, "tennis_partner", aliases=["tennis partner"])
new_rel(C, "doubles_partner", aliases=["doubles partner"])
new_rel(C, "trainer", aliases=[], ask=[])
new_rel(C, "instructor", aliases=[])
new_rel(C, "belt", aliases=["belt colour", "belt color", "belt grade"],
        wh=WHAT, vk="literal")
new_rel(C, "handicap", wh=WHAT, vk="number")
new_rel(C, "personal_best", aliases=["personal best", "PB",
                                     "personal record"],
        wh=WHAT, vk="literal")
new_rel(C, "collection", wh=WHAT, vk="literal",
        ask=["What does {X} collect?"])
new_rel(C, "book_club", aliases=["book club", "reading group"],
        wh=WHICH, vk="organization")
new_rel(C, "choir", wh=WHICH, vk="organization")
new_rel(C, "orchestra", wh=WHICH, vk="organization")
new_rel(C, "favorite_hobby", aliases=[
    "favourite hobby", "favourite pastime", "favorite pastime"], wh=WHAT, vk="literal")

# ======================================================================
# 14. DATES AND EVENTS
# ======================================================================
C = "dates"
# the "open" fix (see design note): one template with an optional
# "first", so "Copperleaf Garage first" can never be read as the name.
replace_ask(C, "opening_date", "When did {X} open?", "When did {X} [first] open?")
replace_ask(C, "opening_date", "When was {X} opened?",
            "When was {X} [first] opened?")
replace_ask(C, "opening_date", "What year did {X} open?",
            "What year did {X} [first] open?")
add_ask(C, "opening_date", "When did {X} open its doors?",
        "When did {X} [first] open for business?",
        "What year was {X} [first] opened?")
add_alias(C, "opening_date", "opening day")
add_ask(C, "date_founded", "What year was {X} established?",
        "When was {X} formed?", "What year was {X} formed?",
        "When was {X} started?", "What year was {X} set up?",
        "When was {X} first founded?", "In what year was {X} founded?")
add_alias(C, "date_founded", "date of founding", "year of founding",
          "establishment date", "date established", "year established")
add_ask(C, "date_of_death", "When did {X} pass away?")
add_alias(C, "date_of_death", "date of death", "death date")
add_ask(C, "graduation_date", "When did {X} graduate from (school|college"
        "|university|uni)?", "When did {X} finish (school|college"
        "|university|uni)?")
add_alias(C, "graduation_date", "graduation day")
add_ask(C, "birthday", "When does {X} celebrate (his|her|their) birthday?")
new_rel(C, "wedding_date", aliases=["wedding date", "wedding day",
                                    "date of marriage", "marriage date",
                                    ], date=True,
        ask=["When did {X} get married?", "When was {X} married?",
             "When did I get married?"])
new_rel(C, "release_date", aliases=["release date", "date of release",
                                    "release year"], date=True,
        ask=["When was {X} released?", "When did {X} come out?",
             "What year was {X} released?", "What year did {X} come out?"])
new_rel(C, "publication_date", aliases=["publication date",
                                        "date of publication",
                                        "publication year",
                                        "year of publication"], date=True,
        ask=["When was {X} published?", "What year was {X} published?",
             "When was {X} first published?"])
new_rel(C, "construction_date",
        aliases=["construction date", "date built", "year built",
                 "build date"], date=True,
        ask=["When was {X} built?", "What year was {X} built?",
             "When was {X} constructed?"])
new_rel(C, "closing_date", aliases=["closing date", "closure date",
                                    "date closed", "year closed"],
        date=True, ask=["When did {X} close?", "When did {X} close down?",
                        "When was {X} closed?", "What year did {X} close?"])
new_rel(C, "retirement_date", aliases=["retirement date",
                                       "date of retirement",
                                       "retirement year"], date=True,
        ask=["When did {X} retire?", "What year did {X} retire?"])
new_rel(C, "launch_date", aliases=["launch date", "date of launch",
                                   "launch year"], date=True,
        ask=["When was {X} launched?", "When did {X} launch?"])
new_rel(C, "start_date", aliases=["start date", "starting date",
                                  "date started"], date=True,
        ask=["When did {X} start work?", "When did {X} start the job?"])
new_rel(C, "moving_date", aliases=["moving date",
                                                         "move date"],
        date=True, ask=["When did {X} move house?"])
new_rel(C, "engagement_date", aliases=["engagement date",
                                       "date of engagement"], date=True,
        ask=["When did {X} get engaged?"])
new_rel(C, "due_date", aliases=["due date"], date=True,
        ask=["When is {X} due?"])
new_rel(C, "name_day", aliases=["name day"], date=True)
new_rel(C, "exam_date", aliases=["exam date"],
        date=True)
new_rel(C, "premiere_date", aliases=["premiere date"],
        date=True, ask=["When did {X} premiere?", "When was {X} first shown?"])
new_rel(C, "debut_date",
        aliases=["debut date"], date=True,
        ask=["When did {X} debut?", "When did {X} make (his|her|their)"
             " debut?"])
# birthday <-> date of birth: linked both ways; the reply always names the
# stored word ("X's birthday is May 3."), never re-labels it.
rels["birthday"].setdefault("narrower", []).append("date_of_birth")
rels["date_of_birth"]["broader"] = ["birthday"]
log.append("[dates] link birthday <-> date_of_birth (narrower + broader; "
           "reply uses the stored word)")

t["v1_2_additions"] = log
t["v1_2_note"] = ("Enumerated from general English knowledge, organised by "
                  "category, before any testing; not from any panel.")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"wrote {OUT} relations={len(t['relations'])} additions={len(log)}")
