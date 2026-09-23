#!/usr/bin/env python3
"""Exp 257 -- relation table v2 = relation table v1 (unchanged rows) + the rows / aliases the
v4 training data needs. Written from general knowledge of everyday personal facts; nothing is
taken from any panel.

  python claude_smolear257_table.py            # (re)writes artifacts/claude-smolear257-20260922/relation_table_v2.json
  import claude_smolear257_table as TB; TB.install()
      -> rebinds claude_smolear235_model._TABLE/_CANON/RELATIONS to v2, so the UNCHANGED
         brake (E.brake), E.canon_rel and everything built on them (235b gate, 235 scorer's
         rel_ok) use table v2. No code of 235/235b is edited.

Rules kept from v1: an alias must be a true synonym (same relation); compound relatives are
their own relations and are never aliases of the plain relation.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "artifacts/claude-relationtable-20260922/relation_table_v1.json"
V2 = ROOT / "artifacts/claude-smolear257-20260922/relation_table_v2.json"

# new relations: name -> (value_kind, aliases)
NEW = {
    # compound relatives (class 2) -- own relations, never shortened
    "stepfather": ("person", ["stepdad", "step dad", "step-father", "step father"]),
    "stepmother": ("person", ["stepmum", "stepmom", "step mum", "step mom", "step-mother", "step mother"]),
    "stepbrother": ("person", ["step brother", "step-brother"]),
    "stepsister": ("person", ["step sister", "step-sister"]),
    "stepson": ("person", ["step son", "step-son"]),
    "stepdaughter": ("person", ["step daughter", "step-daughter"]),
    "half_brother": ("person", ["half brother", "half-brother"]),
    "half_sister": ("person", ["half sister", "half-sister"]),
    "mother_in_law": ("person", ["mother in law", "mother-in-law"]),
    "father_in_law": ("person", ["father in law", "father-in-law"]),
    "sister_in_law": ("person", ["sister in law", "sister-in-law"]),
    "brother_in_law": ("person", ["brother in law", "brother-in-law"]),
    "son_in_law": ("person", ["son in law", "son-in-law"]),
    "daughter_in_law": ("person", ["daughter in law", "daughter-in-law"]),
    "great_grandmother": ("person", ["great grandmother", "great-grandmother", "great grandma",
                                      "great-grandma", "great granny", "great-granny"]),
    "great_grandfather": ("person", ["great grandfather", "great-grandfather", "great grandpa",
                                      "great-grandpa"]),
    "great_aunt": ("person", ["great aunt", "great-aunt"]),
    "great_uncle": ("person", ["great uncle", "great-uncle"]),
    "second_cousin": ("person", ["second cousin"]),
    "niece": ("person", []),
    "nephew": ("person", []),
    "godmother": ("person", ["god mother"]),
    "godfather": ("person", ["god father"]),
    "godson": ("person", []),
    "goddaughter": ("person", []),
    "fiance": ("person", ["fiancé", "fiancée", "fiancee"]),
    "ex_wife": ("person", ["ex-wife", "ex wife"]),
    "ex_husband": ("person", ["ex-husband", "ex husband"]),
    # everyday people (class 6)
    "roommate": ("person", ["flatmate", "housemate", "room mate", "flat mate", "house mate"]),
    "classmate": ("person", []),
    "teammate": ("person", ["team mate"]),
    "tutor": ("person", []),
    "landlord": ("person", ["landlady"]),
    "dentist": ("person", []),
    "vet": ("person", ["veterinarian"]),
    "babysitter": ("person", ["childminder"]),
    "therapist": ("person", []),
    # everyday things (class 6)
    "instrument": ("thing", ["musical instrument"]),
    "favorite_food": ("thing", ["favourite food"]),
    "favorite_drink": ("thing", ["favourite drink"]),
    "favorite_sport": ("thing", ["favourite sport"]),
    "favorite_book": ("thing", ["favourite book"]),
    "favorite_film": ("thing", ["favourite film", "favorite movie", "favourite movie"]),
    "favorite_animal": ("thing", ["favourite animal"]),
    "favorite_season": ("thing", ["favourite season"]),
    "favorite_subject": ("thing", ["favourite subject"]),
    "allergy": ("thing", []),
    "car": ("thing", []),
    "rabbit": ("pet", []),
    "hamster": ("pet", []),
    "parrot": ("pet", []),
    "horse": ("pet", ["pony"]),
}
# informal true-synonym aliases added to EXISTING v1 rows (class 7 first hops, class 6)
EXTRA_ALIASES = {
    "husband": ["hubby"],
    "wife": ["missus"],
    "brother": ["bro"],
    "sister": ["sis"],
    "mother": ["mam", "mama"],
    "grandmother": ["nan", "nana", "gran", "grannie"],
    "grandfather": ["grandad", "granddad", "gramps"],
    "best_friend": ["bestie", "bff"],
    # the panel-257 README judgement call (read before the seal, as allowed): a girlfriend /
    # boyfriend is `partner`. v4 follows it: these words are partner aliases, not own relations.
    "partner": ["girlfriend", "boyfriend", "gf", "bf"],
    # brief class 1 names the target "workplace/employer"; the panel spec lists `workplace` as a
    # gold relation name. v1 had no `workplace` key, so it is an employer alias (scoring/brake only;
    # the v4 data never emits it).
    "employer": ["workplace", "place of work"],
}


def build_v2():
    t = json.loads(V1.read_text())
    t2 = copy.deepcopy(t)
    t2["version"] = "v2"
    t2["purpose"] = t["purpose"] + " v2 (exp 257): v1 rows unchanged except added informal aliases; new rows appended."
    keys = {}
    for r in t2["relations"]:
        for k in [r["name"]] + r.get("aliases", []):
            keys[E._rkey(k)] = r["name"]
    for name, al in EXTRA_ALIASES.items():
        row = next(r for r in t2["relations"] if r["name"] == name)
        for a in al:
            assert E._rkey(a) not in keys, (a, keys.get(E._rkey(a)))
            keys[E._rkey(a)] = name
            row.setdefault("aliases", []).append(a)
    for name, (kind, al) in NEW.items():
        for k in [name] + al:
            assert E._rkey(k) not in keys or keys[E._rkey(k)] == name, (k, keys.get(E._rkey(k)))
            keys[E._rkey(k)] = name
        t2["relations"].append(dict(name=name, status="new_v2", value_kind=kind, cardinality="multi",
                                    yesno_can_say_no=False, aliases=list(al), storage_keys=[name],
                                    inverse_storage_keys=[], narrower=[], generic=["possessive", "my"],
                                    wh=["Who"] if kind == "person" else ["What"], teach=[], ask=[],
                                    yesno=[], inverse=[], src=["NEW exp 257 (general knowledge)"]))
    return t2


def install(path=V2):
    """Point the unchanged 235 brake / canon_rel at table v2."""
    d = json.loads(Path(path).read_text())
    canon = {}
    for r in d["relations"]:
        canon[E._rkey(r["name"])] = r["name"]
        for a in r.get("aliases", []):
            canon.setdefault(E._rkey(a), r["name"])
    E._TABLE, E._CANON = d, canon
    E.RELATIONS = sorted({r["name"] for r in d["relations"]})
    return d


if __name__ == "__main__":
    t2 = build_v2()
    V2.parent.mkdir(parents=True, exist_ok=True)
    V2.write_text(json.dumps(t2, indent=1, ensure_ascii=False))
    print("v2 relations", len(t2["relations"]), "new", len(NEW))
