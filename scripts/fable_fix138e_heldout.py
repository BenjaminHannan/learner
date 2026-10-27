#!/usr/bin/env python3
"""Exp 138e T1 held-out set -- FRESH officeholder-chain questions, new names.

Written BEFORE any 138e run on it (STEP 2). Two pre-specified shapes:

  RIGHT (rewrite should fire and answer correctly): single complete
  4-hop branch through an officeholder compound; all teaches short, all
  land; relative-clause question phrasing mirroring the bench shapes the
  132 rewriter covers (director/head coach/original broadcaster +
  capital/continent/official-language).

  WRONGSHAPE (base loop138b answers confidently but wrong): two branches;
  the original branch is complete; the edit first-hop teach carries a long
  "A and B" institution value that the stacked value screen refuses
  ("split that"), leaving a dangling edit branch with a DIFFERENT holder;
  downstream edit teaches land. Mirrors 025/073/149 with new names.

Labeling ("rewrite-right" vs "would-be-wrong") is established by ONE open
run of the FROZEN base loop138b (never 138e): rewrite-right = base answers
correct through stage loop138b-rewrite; would-be-wrong = base answers wrong
through stage loop138b-rewrite. The first 16 qualifying cases per class
form the sealed T1 set (>= 15 each per the brief).

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix138e_heldout.py --write [--label]
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ART138E = ROOT / "artifacts" / "fable-officechain138e-20260922"


def T(subject, relation, sentence_en, obj, edit=False):
    d = {"subject": subject, "relation": relation,
         "sentence_en": sentence_en, "object": obj}
    if edit:
        d["edit"] = True
    return d


def case(cid, question, teaches, gold):
    return {"id": cid, "question": question, "taught": teaches,
            "gold": gold, "gold_aliases": [], "expected": "answer",
            "source": "138e-heldout-fresh"}


def build_candidates() -> list[dict]:
    out: list[dict] = []
    # ---- RIGHT candidates R01-R20: single complete branches ----
    # R01: game/developer/director/citizen/capital (025 shape, one branch)
    out.append(case(
        "138e-R01",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Starfall Odyssey?",
        [T("Starfall Odyssey", "developer",
           "Starfall Odyssey was developed by Moonlit Forge",
           "Moonlit Forge"),
         T("Moonlit Forge", "director_manager",
           "The director of Moonlit Forge is Elena Vasquez",
           "Elena Vasquez"),
         T("Elena Vasquez", "country_of_citizenship",
           "Elena Vasquez is a citizen of Alberia", "Alberia"),
         T("Alberia", "capital", "The capital of Alberia is Port Meridian",
           "Port Meridian")],
        ["Port Meridian"]))
    out.append(case(
        "138e-R02",
        "Which continent is the country in, where the director of the "
        "developer of Starfall Odyssey is a citizen?",
        [T("Starfall Odyssey", "developer",
           "Starfall Odyssey was developed by Moonlit Forge",
           "Moonlit Forge"),
         T("Moonlit Forge", "director_manager",
           "The director of Moonlit Forge is Elena Vasquez",
           "Elena Vasquez"),
         T("Elena Vasquez", "country_of_citizenship",
           "Elena Vasquez is a citizen of Alberia", "Alberia"),
         T("Alberia", "continent",
           "Alberia is located in the continent of Theros", "Theros")],
        ["Theros"]))
    out.append(case(
        "138e-R03",
        "What city is the capital of the country where the director of the "
        "creator of Paper Lanterns is a citizen?",
        [T("Paper Lanterns", "creator",
           "Paper Lanterns was created by The Velvet Cartographers",
           "The Velvet Cartographers"),
         T("The Velvet Cartographers", "director_manager",
           "The director of The Velvet Cartographers is Dmitri Okafor",
           "Dmitri Okafor"),
         T("Dmitri Okafor", "country_of_citizenship",
           "Dmitri Okafor is a citizen of Caledonia", "Caledonia"),
         T("Caledonia", "capital",
           "The capital of Caledonia is Dunhaven", "Dunhaven")],
        ["Dunhaven"]))
    out.append(case(
        "138e-R04",
        "What is the official language of the country whose citizen is the "
        "director of the performer of Glasswing Zephyr?",
        [T("Glasswing Zephyr", "performer",
           "Glasswing Zephyr was performed by Harborlight Trio",
           "Harborlight Trio"),
         T("Harborlight Trio", "director_manager",
           "The director of Harborlight Trio is Ingrid Solberg",
           "Ingrid Solberg"),
         T("Ingrid Solberg", "country_of_citizenship",
           "Ingrid Solberg is a citizen of Norvia", "Norvia"),
         T("Norvia", "official_language",
           "The official language of Norvia is Norvian", "Norvian")],
        ["Norvian"]))
    out.append(case(
        "138e-R05",
        "What is the capital of the country where the sport associated "
        "with the head coach of Eastvale Rovers was developed?",
        [T("Eastvale Rovers", "head_coach",
           "The head coach of Eastvale Rovers is Marco Bellini",
           "Marco Bellini"),
         T("Marco Bellini", "sport",
           "Marco Bellini is associated with the sport of Calcio Fiorentino",
           "Calcio Fiorentino"),
         T("Calcio Fiorentino", "country_of_origin",
           "Calcio Fiorentino was created in the country of Esteria",
           "Esteria"),
         T("Esteria", "capital",
           "The capital of Esteria is Vellano", "Vellano")],
        ["Vellano"]))
    out.append(case(
        "138e-R06",
        "Which city is the capital of the country of citizenship of the "
        "director of the original broadcaster of The Lantern Parade?",
        [T("The Lantern Parade", "original_broadcaster",
           "The origianl broadcaster of The Lantern Parade is Seaborn Network",
           "Seaborn Network"),
         T("Seaborn Network", "director_manager",
           "The director of Seaborn Network is Tomas Reyes",
           "Tomas Reyes"),
         T("Tomas Reyes", "country_of_citizenship",
           "Tomas Reyes is a citizen of Cordillera", "Cordillera"),
         T("Cordillera", "capital",
           "The capital of Cordillera is Alto Prado", "Alto Prado")],
        ["Alto Prado"]))
    out.append(case(
        "138e-R07",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Ironhold Bastion?",
        [T("Ironhold Bastion", "developer",
           "Ironhold Bastion was developed by Cinderfall Works",
           "Cinderfall Works"),
         T("Cinderfall Works", "director_manager",
           "The director of Cinderfall Works is Petra Lindqvist",
           "Petra Lindqvist"),
         T("Petra Lindqvist", "country_of_citizenship",
           "Petra Lindqvist is a citizen of Gothland", "Gothland"),
         T("Gothland", "capital",
           "The capital of Gothland is Karnholm", "Karnholm")],
        ["Karnholm"]))
    out.append(case(
        "138e-R08",
        "Which continent houses the country of the director of the "
        "performer of Copper Finch?",
        [T("Copper Finch", "performer",
           "Copper Finch was performed by Amber Ensemble",
           "Amber Ensemble"),
         T("Amber Ensemble", "director_manager",
           "The director of Amber Ensemble is Yusuf Adeyemi",
           "Yusuf Adeyemi"),
         T("Yusuf Adeyemi", "country_of_citizenship",
           "Yusuf Adeyemi is a citizen of Zambara", "Zambara"),
         T("Zambara", "continent",
           "Zambara is located in the continent of Keshara", "Keshara")],
        ["Keshara"]))
    out.append(case(
        "138e-R09",
        "What city is the capital of the country where the director of "
        "the developer of Tidecaller Voyage is a citizen?",
        [T("Tidecaller Voyage", "developer",
           "Tidecaller Voyage was developed by Breakwater Studio",
           "Breakwater Studio"),
         T("Breakwater Studio", "director_manager",
           "The director of Breakwater Studio is Aoife Gallagher",
           "Aoife Gallagher"),
         T("Aoife Gallagher", "country_of_citizenship",
           "Aoife Gallagher is a citizen of Eirland", "Eirland"),
         T("Eirland", "capital",
           "The capital of Eirland is Skerryvoe", "Skerryvoe")],
        ["Skerryvoe"]))
    out.append(case(
        "138e-R10",
        "What language is spoken in the country of citizenship of the "
        "director of the performer of Juniper Smoke?",
        [T("Juniper Smoke", "performer",
           "Juniper Smoke was performed by Foxglove Ensemble",
           "Foxglove Ensemble"),
         T("Foxglove Ensemble", "director_manager",
           "The director of Foxglove Ensemble is Rafael Duarte",
           "Rafael Duarte"),
         T("Rafael Duarte", "country_of_citizenship",
           "Rafael Duarte is a citizen of Lusitania", "Lusitania"),
         T("Lusitania", "official_language",
           "The official language of Lusitania is Lusitanian",
           "Lusitanian")],
        ["Lusitanian"]))
    out.append(case(
        "138e-R11",
        "What is the capital of the country that created the sport that "
        "the head coach of Northgate Athletic is associated with?",
        [T("Northgate Athletic", "head_coach",
           "The head coach of Northgate Athletic is Sven Dahlberg",
           "Sven Dahlberg"),
         T("Sven Dahlberg", "sport",
           "Sven Dahlberg is associated with the sport of Iskast",
           "Iskast"),
         T("Iskast", "country_of_origin",
           "Iskast was created in the country of Fjorden", "Fjorden"),
         T("Fjorden", "capital",
           "The capital of Fjorden is Isvik", "Isvik")],
        ["Isvik"]))
    out.append(case(
        "138e-R12",
        "What is the capital city of the country that the director of "
        "the original broadcaster of Willow Creek is from?",
        [T("Willow Creek", "original_broadcaster",
           "The origianl broadcaster of Willow Creek is Prairie Light",
           "Prairie Light"),
         T("Prairie Light", "director_manager",
           "The director of Prairie Light is Hannah Okonkwo",
           "Hannah Okonkwo"),
         T("Hannah Okonkwo", "country_of_citizenship",
           "Hannah Okonkwo is a citizen of Savanna", "Savanna"),
         T("Savanna", "capital",
           "The capital of Savanna is Tallgrass", "Tallgrass")],
        ["Tallgrass"]))
    out.append(case(
        "138e-R13",
        "What is the capital of the country whose citizen is the director "
        "of the creator of The Clockwork Garden?",
        [T("The Clockwork Garden", "creator",
           "The Clockwork Garden was created by Brass Sparrow",
           "Brass Sparrow"),
         T("Brass Sparrow", "director_manager",
           "The director of Brass Sparrow is Emilia Farkas",
           "Emilia Farkas"),
         T("Emilia Farkas", "country_of_citizenship",
           "Emilia Farkas is a citizen of Pannonia", "Pannonia"),
         T("Pannonia", "capital",
           "The capital of Pannonia is Vasvar", "Vasvar")],
        ["Vasvar"]))
    out.append(case(
        "138e-R14",
        "Which continent is the country in, where the director of the "
        "performer of Silent Meridian is a citizen?",
        [T("Silent Meridian", "performer",
           "Silent Meridian was performed by The Dusk Cartel",
           "The Dusk Cartel"),
         T("The Dusk Cartel", "director_manager",
           "The director of The Dusk Cartel is Kenji Mori",
           "Kenji Mori"),
         T("Kenji Mori", "country_of_citizenship",
           "Kenji Mori is a citizen of Arcadia", "Arcadia"),
         T("Arcadia", "continent",
           "Arcadia is located in the continent of Borealis", "Borealis")],
        ["Borealis"]))
    out.append(case(
        "138e-R15",
        "What is the capital of the country where the director of the "
        "developer of Emberfall Chronicles holds citizenship?",
        [T("Emberfall Chronicles", "developer",
           "Emberfall Chronicles was developed by Ashen Quill",
           "Ashen Quill"),
         T("Ashen Quill", "director_manager",
           "The director of Ashen Quill is Nadia Petrova",
           "Nadia Petrova"),
         T("Nadia Petrova", "country_of_citizenship",
           "Nadia Petrova is a citizen of Volgaria", "Volgaria"),
         T("Volgaria", "capital",
           "The capital of Volgaria is Zarechny", "Zarechny")],
        ["Zarechny"]))
    out.append(case(
        "138e-R16",
        "What is the official language of the country that the director "
        "of the performer of Honeyed Thistle is from?",
        [T("Honeyed Thistle", "performer",
           "Honeyed Thistle was performed by The Bramble Choir",
           "The Bramble Choir"),
         T("The Bramble Choir", "director_manager",
           "The director of The Bramble Choir is Lucia Ferreira",
           "Lucia Ferreira"),
         T("Lucia Ferreira", "country_of_citizenship",
           "Lucia Ferreira is a citizen of Dourada", "Dourada"),
         T("Dourada", "official_language",
           "The official language of Dourada is Douradan", "Douradan")],
        ["Douradan"]))
    out.append(case(
        "138e-R17",
        "What city is the capital of the country of citizenship of the "
        "director of the performer of Stonefield Hymn?",
        [T("Stonefield Hymn", "performer",
           "Stonefield Hymn was performed by Granite Voices",
           "Granite Voices"),
         T("Granite Voices", "director_manager",
           "The director of Granite Voices is Oskar Brandt",
           "Oskar Brandt"),
         T("Oskar Brandt", "country_of_citizenship",
           "Oskar Brandt is a citizen of Bergmark", "Bergmark"),
         T("Bergmark", "capital",
           "The capital of Bergmark is Stenhamn", "Stenhamn")],
        ["Stenhamn"]))
    out.append(case(
        "138e-R18",
        "Which continent contains the country of citizenship of the "
        "director of the entity that performed Nightjar Call?",
        [T("Nightjar Call", "performer",
           "Nightjar Call was performed by The Mottled Crew",
           "The Mottled Crew"),
         T("The Mottled Crew", "director_manager",
           "The director of The Mottled Crew is Priya Nair",
           "Priya Nair"),
         T("Priya Nair", "country_of_citizenship",
           "Priya Nair is a citizen of Malabar", "Malabar"),
         T("Malabar", "continent",
           "Malabar is located in the continent of Drupada", "Drupada")],
        ["Drupada"]))
    out.append(case(
        "138e-R19",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Frostbound Keep?",
        [T("Frostbound Keep", "developer",
           "Frostbound Keep was developed by Wintermark Forge",
           "Wintermark Forge"),
         T("Wintermark Forge", "director_manager",
           "The director of Wintermark Forge is Sanna Korhonen",
           "Sanna Korhonen"),
         T("Sanna Korhonen", "country_of_citizenship",
           "Sanna Korhonen is a citizen of Pakkas", "Pakkas"),
         T("Pakkas", "capital",
           "The capital of Pakkas is Lumisilta", "Lumisilta")],
        ["Lumisilta"]))
    out.append(case(
        "138e-R20",
        "What continent is the country located in, where the director of "
        "the developer of Sunken Atoll is a citizen?",
        [T("Sunken Atoll", "developer",
           "Sunken Atoll was developed by Reefwright Collective",
           "Reefwright Collective"),
         T("Reefwright Collective", "director_manager",
           "The director of Reefwright Collective is Diego Fuentes",
           "Diego Fuentes"),
         T("Diego Fuentes", "country_of_citizenship",
           "Diego Fuentes is a citizen of Abisal", "Abisal"),
         T("Abisal", "continent",
           "Abisal is located in the continent of Pelagia", "Pelagia")],
        ["Pelagia"]))
    # ---- WRONGSHAPE candidates W01-W20: refused edit link + dangling branch
    def wrong_pair(idx, seed, rel_word, teach_verb, orig_mid, orig_person,
                   orig_country, tail_rel, tail_val_orig, edit_mid,
                   edit_person, edit_country, tail_val_edit, question,
                   tail_sentence):
        teaches = [
            T(seed, "x", f"{seed} was {teach_verb} by {orig_mid}", orig_mid),
            T(orig_mid, "director_manager",
              f"The director of {orig_mid} is {orig_person}", orig_person),
            T(orig_person, "country_of_citizenship",
              f"{orig_person} is a citizen of {orig_country}", orig_country),
            tail_sentence(orig_country, tail_val_orig, False),
            T(seed, "x", f"{seed} was {teach_verb} by {edit_mid}", edit_mid,
              edit=True),
            T(edit_mid, "director_manager",
              f"The director of {edit_mid} is {edit_person}", edit_person,
              edit=True),
            T(edit_person, "country_of_citizenship",
              f"{edit_person} is a citizen of {edit_country}", edit_country,
              edit=True),
            tail_sentence(edit_country, tail_val_edit, True),
        ]
        return case(f"138e-W{idx:02d}", question, teaches, [tail_val_edit])

    def cap_talko(country, val, _edit):
        return T(country, "capital", f"The capital of {country} is {val}",
                 val, edit=_edit)

    def cont_talko(country, val, _edit):
        return T(country, "continent",
                 f"{country} is located in the continent of {val}", val,
                 edit=_edit)

    out.append(wrong_pair(
        1, "Glimmerhold Saga", "developer", "developed", "Pixel Loft",
        "Jonas Weber", "Helvetia", "capital", "Bernau",
        "Harbor Institute for Science and Navigation", "Amara Diallo",
        "Senegambia", "Rufisque",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Glimmerhold Saga?", cap_talko))
    out.append(wrong_pair(
        2, "Glimmerhold Saga", "developer", "developed", "Pixel Loft",
        "Jonas Weber", "Helvetia", "continent", "Europa Minor",
        "Harbor Institute for Science and Navigation", "Amara Diallo",
        "Senegambia", "Africana",
        "Which continent is the country in, where the director of the "
        "developer of Glimmerhold Saga is a citizen?", cont_talko))
    out.append(wrong_pair(
        3, "The Marble Faun", "creator", "created",
        "Ivy Quill Press", "Margaret Ellison", "Albion", "capital",
        "Camberwick",
        "National Museum for Art and Antiquities", "Kwame Mensah",
        "Ashantiland", "Kumasi",
        "What city is the capital of the country where the director of "
        "the creator of The Marble Faun is a citizen?", cap_talko))
    out.append(wrong_pair(
        4, "Honeydew Drift", "developer", "developed", "Pale Fox Games",
        "Lars Johansson", "Scandia", "capital", "Nordvik",
        "Council for Engineers and Natural Philosophers", "Zanele Khumalo",
        "Ubuntuland", "Ethekwini",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Honeydew Drift?", cap_talko))
    out.append(wrong_pair(
        5, "The Sunken Bell", "creator", "created", "Brass Bell Books",
        "Edith Harlow", "Wessex", "continent", "Atlantis Minor",
        "Society for Bells and Tower Keepers", "Ngozi Eze",
        "Biafraland", "Onitsha Province",
        "Which continent is the country in, where the director of the "
        "creator of The Sunken Bell is a citizen?", cont_talko))
    out.append(wrong_pair(
        6, "Cinder Trail", "developer", "developed", "Ember Soft",
        "Pavel Novak", "Bohemia", "capital", "Karlovy",
        "Academy for Fire and Rescue Services", "Fatima Al-Sayed",
        "Nubialand", "Dongola",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Cinder Trail?", cap_talko))
    out.append(wrong_pair(
        7, "The Gilded Wren", "creator", "created", "Wren House",
        "Beatrice Lovelace", "Cornwall", "capital", "Truro",
        "Guild for Goldsmiths and Silversmiths", "Tendai Moyo",
        "Monopotapa", "Great Zimbabwe",
        "What city is the capital of the country where the director of "
        "the creator of The Gilded Wren is a citizen?", cap_talko))
    out.append(wrong_pair(
        8, "Fogharbor Nights", "developer", "developed", "Mistral Play",
        "Henri Baudin", "Provence", "continent", "Lemuria",
        "Bureau for Lighthouses and Harbor Pilots", "Ifemelu Obi",
        "Nigerland", "Badagry Coast",
        "Which continent is the country in, where the director of the "
        "developer of Fogharbor Nights is a citizen?", cont_talko))
    out.append(wrong_pair(
        9, "The Tin Observatory", "creator", "created", "Lens & Paper",
        "Clara Oswald", "Mercia", "capital", "Tamworth",
        "Royal Observatory for Stars and Tides", "Chidi Anagonye",
        "Kanemland", "Njimi",
        "What city is the capital of the country where the director of "
        "the creator of The Tin Observatory is a citizen?", cap_talko))
    out.append(wrong_pair(
        10, "Saltmeadow Run", "developer", "developed", "Brine Shrimp",
        "Morten Vik", "Vestland", "capital", "Fjordheim",
        "College for Salt and Sea Harvesters", "Ayoola Bakare",
        "Oyo Empire", "Oyo Ile",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Saltmeadow Run?", cap_talko))
    out.append(wrong_pair(
        11, "The Copper Kettle", "creator", "created", "Kettle Black",
        "Agnes Potter", "Kent", "continent", "Doggerland",
        "Fellowship for Coppersmiths and Tinkers", "Sipho Ndlovu",
        "Mapungubwe", "Thulamela",
        "Which continent is the country in, where the director of the "
        "creator of The Copper Kettle is a citizen?", cont_talko))
    out.append(wrong_pair(
        12, "Duskwater Mill", "developer", "developed", "Millrace",
        "Otto Berger", "Alpinia", "capital", "Seetal",
        "Consortium for Mills and Grain Merchants", "Nia Thompson",
        "Joliet", "Cahokia",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Duskwater Mill?", cap_talko))
    out.append(wrong_pair(
        13, "The Velvet Badger", "creator", "created", "Sett Press",
        "Harriet Vane", "Dorset", "capital", "Dorchester",
        "Association for Naturalists and Field Clubs", "Kofi Asante",
        "Denkyira", "Abankeseso",
        "What city is the capital of the country where the director of "
        "the creator of The Velvet Badger is a citizen?", cap_talko))
    out.append(wrong_pair(
        14, "Longship Dawn", "developer", "developed", "Keel & Oar",
        "Erik Sorensen", "Jutland", "continent", "Thule",
        "Brotherhood for Shipwrights and Sailmakers", "Adaeze Nwosu",
        "Nriland", "Igbo Ukwu",
        "Which continent is the country in, where the director of the "
        "developer of Longship Dawn is a citizen?", cont_talko))
    out.append(wrong_pair(
        15, "The Porcelain Stag", "creator", "created", "Kiln House",
        "Eleanor Fairfax", "Sussex", "capital", "Lewes",
        "Company for Potters and Glaziers", "Mpho Dlamini",
        "Eswatini", "Lobamba",
        "What city is the capital of the country where the director of "
        "the creator of The Porcelain Stag is a citizen?", cap_talko))
    out.append(wrong_pair(
        16, "Foxfire Hollow", "developer", "developed", "Hollow Lantern",
        "Caspar Vogel", "Thuringia", "capital", "Eisenach",
        "Institute for Forestry and Woodland Crafts", "Zola Mbeki",
        "Azanialand", "Rhapta",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Foxfire Hollow?", cap_talko))
    out.append(wrong_pair(
        17, "The Brass Compass", "creator", "created", "North Point",
        "Phineas Fogg", "Surrey", "continent", "Mu",
        "Worshipful Company for Navigators and Cartographers",
        "Olufemi Ajayi", "Ondoland", "Akure",
        "Which continent is the country in, where the director of the "
        "creator of The Brass Compass is a citizen?", cont_talko))
    out.append(wrong_pair(
        18, "Millpond Echo", "developer", "developed", "Stillwater",
        "Hugo Brandt", "Holstein", "capital", "Gluckstadt",
        "Federation for Millers and Brewers Guilds", "Ama Serwaa",
        "Akwamuland", "Nyanoase",
        "What is the capital of the country whose citizen is the director "
        "of the developer of Millpond Echo?", cap_talko))
    out.append(wrong_pair(
        19, "The Amber Generals", "creator", "created", "Field Press",
        "Augusta Kane", "Norfolk", "capital", "Norwich",
        "Legion for Surveyors and Map Engravers", "Tunde Balogun",
        "Ife Empire", "Ife",
        "What city is the capital of the country where the director of "
        "the creator of The Amber Generals is a citizen?", cap_talko))
    out.append(wrong_pair(
        20, "Cloudbreak Ridge", "developer", "developed", "Updraft",
        "Felix Hartmann", "Tyrol", "continent", "Hyperborea",
        "Union for Mountain Guides and Porters", "Nia Washington",
        "Carolineland", "New Bern",
        "Which continent is the country in, where the director of the "
        "developer of Cloudbreak Ridge is a citizen?", cont_talko))
    return out


def run_base(item: dict, workroot: Path, cfg: dict) -> dict:
    import fable_bench121_run as B
    taught = [{"sentence_en": t["sentence_en"]} for t in item["taught"]]
    return B.run_item({"id": item["id"], "question": item["question"],
                       "taught": taught, "gold": item["gold"],
                       "gold_aliases": item.get("gold_aliases", []),
                       "expected": item.get("expected", "answer"),
                       "type": "heldout-138e"},
                      workroot, cfg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138e T1 held-out set")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--label", action="store_true",
                    help="one open BASE-loop138b run to label "
                         "rewrite-right / would-be-wrong")
    args = ap.parse_args(argv)
    cands = build_candidates()
    if args.write:
        (ART138E / "heldout138e-candidates.json").write_text(
            json.dumps(cands, indent=1, ensure_ascii=False),
            encoding="utf-8")
        print(f"wrote {len(cands)} candidates")
    if args.label:
        import fable_loop138_agent as L138
        base_cfg = copy.deepcopy(L138.DEFAULT_CONFIG138)
        base_cfg["sleep_threshold"] = 100000
        import fable_loop138b_agent as L138b
        import fable_bench121_run as B
        B.Loop121Daemon = L138b.Loop138bDaemon
        workroot = ART138E / "scratch-heldout-base"
        if workroot.exists():
            shutil.rmtree(workroot)
        workroot.mkdir(parents=True)
        rows = [run_base(it, workroot / it["id"], copy.deepcopy(base_cfg))
                for it in cands]
        (ART138E / "heldout138e-base_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        for r in rows:
            print(f"{r['id']}: {r['verdict']} stage={r['ears_stage']} "
                  f"extracted={r['extracted'][:60]!r}")
    if not args.write and not args.label:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
