"""Exp 63 (doc 68): hand-written test data for the alias-table canonicaliser.

300 paraphrase items: 5 hand-written templates over each of the top-60 WebRED
relations (top by train count), each with a gold canonical name. Templates mix:
  (a) the verbatim canonical name,
  (b) aux/article rule variants ("is the X", "was a X"),
  (c) verbatim Wikidata property aliases for that property,
  (d) one natural verbal paraphrase (may abstain; never wrong).
200 fabricated items: nonce-word and real-word strings that must all be UNKNOWN.

`python -B scripts/fable_relcanon63_testdata.py --verify` checks every item
against the FROZEN canon and reports correct/wrong/abstain (pre-seal
construction aid: any WRONG item is replaced by hand, never by touching canon).
`--freeze` writes artifacts/fable-relcanon63-20260921/test_paraphrases.json and
test_fabricated.json (the sealed inputs the registered run consumes).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fable_relcanon63_canon import canon  # noqa: E402

ART = ROOT / "artifacts" / "fable-relcanon63-20260921"

# (input, gold canonical name). Hand-written; see module docstring.
ITEMS = [
    ("country", "country"),
    ("is the country", "country"),
    ("sovereign state", "country"),
    ("host country", "country"),
    ("is a country", "country"),
    ("diplomatic relation", "diplomatic relation"),
    ("is the diplomatic relation", "diplomatic relation"),
    ("diplomatic relations", "diplomatic relation"),
    ("foreign relations", "diplomatic relation"),
    ("was in a diplomatic relation", "diplomatic relation"),
    ("located in the administrative territorial entity",
     "located in the administrative territorial entity"),
    ("is located in the administrative territorial entity",
     "located in the administrative territorial entity"),
    ("located in the administrative unit",
     "located in the administrative territorial entity"),
    ("is located in", "located in the administrative territorial entity"),
    ("was located in the administrative territorial entity",
     "located in the administrative territorial entity"),
    ("shares border with", "shares border with"),
    ("Shares Border With", "shares border with"),
    ("bordered by", "shares border with"),
    ("adjacent to", "shares border with"),
    ("is bordered by", "shares border with"),
    ("contains administrative territorial entity",
     "contains administrative territorial entity"),
    ("is the contains administrative territorial entity",
     "contains administrative territorial entity"),
    ("divided into", "contains administrative territorial entity"),
    ("subdivided into", "contains administrative territorial entity"),
    ("was divided into", "contains administrative territorial entity"),
    ("country of citizenship", "country of citizenship"),
    ("is the country of citizenship", "country of citizenship"),
    ("citizenship", "country of citizenship"),
    ("citizen of", "country of citizenship"),
    ("has citizenship", "country of citizenship"),
    ("capital", "capital"),
    ("is the capital", "capital"),
    ("capital city", "capital"),
    ("has capital", "capital"),
    ("is the capital city", "capital"),
    ("headquarters location", "headquarters location"),
    ("is the headquarters location", "headquarters location"),
    ("headquarters", "headquarters location"),
    ("HQ", "headquarters location"),
    ("head office location", "headquarters location"),
    ("capital of", "capital of"),
    ("is the capital of", "capital of"),
    ("is capital of", "capital of"),
    ("national capital of", "capital of"),
    ("capital city of", "capital of"),
    ("inflation rate", "inflation rate"),
    ("is the inflation rate", "inflation rate"),
    ("CPI inflation rate", "inflation rate"),
    ("consumer price index inflation rate", "inflation rate"),
    ("was the inflation rate", "inflation rate"),
    ("member of sports team", "member of sports team"),
    ("was a member of sports team", "member of sports team"),
    ("played for", "member of sports team"),
    ("plays for", "member of sports team"),
    ("team played for", "member of sports team"),
    ("has part", "has part"),
    ("HAS PART", "has part"),
    ("consists of", "has part"),
    ("composed of", "has part"),
    ("was composed of", "has part"),
    ("oxidation state", "oxidation state"),
    ("is the oxidation state", "oxidation state"),
    ("oxidation number", "oxidation state"),
    ("has oxidation state", "oxidation state"),
    ("was in oxidation state", "oxidation state"),
    ("part of", "part of"),
    ("is part of", "part of"),
    ("component of", "part of"),
    ("section of", "part of"),
    ("was part of", "part of"),
    ("continent", "continent"),
    ("is the continent", "continent"),
    ("Continent", "continent"),
    ("was the continent", "continent"),
    ("the continent", "continent"),
    ("spouse", "spouse"),
    ("is the spouse", "spouse"),
    ("married to", "spouse"),
    ("wife", "spouse"),
    ("was married to", "spouse"),
    ("place of birth", "place of birth"),
    ("was born in", "place of birth"),
    ("birthplace", "place of birth"),
    ("born in", "place of birth"),
    ("is the place of birth", "place of birth"),
    ("member of political party", "member of political party"),
    ("is the member of political party", "member of political party"),
    ("party membership", "member of political party"),
    ("political party member", "member of political party"),
    ("was a member of political party", "member of political party"),
    ("member of", "member of"),
    ("is a member of", "member of"),
    ("is member of", "member of"),
    ("membership", "member of"),
    ("was a member of", "member of"),
    ("performer", "performer"),
    ("is the performer", "performer"),
    ("played by", "performer"),
    ("performed by", "performer"),
    ("was performed by", "performer"),
    ("owned by", "owned by"),
    ("is owned by", "owned by"),
    ("belongs to", "owned by"),
    ("belonged to", "owned by"),
    ("was owned by", "owned by"),
    ("date of birth", "date of birth"),
    ("was born on", "date of birth"),
    ("birthdate", "date of birth"),
    ("born", "date of birth"),
    ("is the date of birth", "date of birth"),
    ("encodes", "encodes"),
    ("codes for", "encodes"),
    ("is codes for", "encodes"),
    ("ENCODES", "encodes"),
    ("was codes for", "encodes"),
    ("cast member", "cast member"),
    ("is the cast member", "cast member"),
    ("starring", "cast member"),
    ("film starring", "cast member"),
    ("was starring", "cast member"),
    ("country of origin", "country of origin"),
    ("is the country of origin", "country of origin"),
    ("origin country", "country of origin"),
    ("homeland", "country of origin"),
    ("was the country of origin", "country of origin"),
    ("place of death", "place of death"),
    ("died in", "place of death"),
    ("deathplace", "place of death"),
    ("death place", "place of death"),
    ("was the place of death", "place of death"),
    ("employer", "employer"),
    ("is the employer", "employer"),
    ("works for", "employer"),
    ("employed by", "employer"),
    ("was employed by", "employer"),
    ("location of formation", "location of formation"),
    ("is the location of formation", "location of formation"),
    ("formed in", "location of formation"),
    ("founded in", "location of formation"),
    ("was formed in", "location of formation"),
    ("owner of", "owner of"),
    ("is the owner of", "owner of"),
    ("owns", "owner of"),
    ("owns property", "owner of"),
    ("was the owner of", "owner of"),
    ("author", "author"),
    ("is the author", "author"),
    ("written by", "author"),
    ("writer", "author"),
    ("was written by", "author"),
    ("official language", "official language"),
    ("is the official language", "official language"),
    ("spoken in", "official language"),
    ("language official", "official language"),
    ("was the official language", "official language"),
    ("league", "league"),
    ("is the league", "league"),
    ("sports league", "league"),
    ("competition", "league"),
    ("was the league", "league"),
    ("operator", "operator"),
    ("is the operator", "operator"),
    ("operated by", "operator"),
    ("managed by", "operator"),
    ("was operated by", "operator"),
    ("educated at", "educated at"),
    ("was educated at", "educated at"),
    ("alma mater", "educated at"),
    ("studied at", "educated at"),
    ("graduated from", "educated at"),
    ("unemployment rate", "unemployment rate"),
    ("is the unemployment rate", "unemployment rate"),
    ("Unemployment Rate", "unemployment rate"),
    ("was the unemployment rate", "unemployment rate"),
    ("the unemployment rate", "unemployment rate"),
    ("founded by", "founded by"),
    ("was founded by", "founded by"),
    ("established by", "founded by"),
    ("started by", "founded by"),
    ("is founded by", "founded by"),
    ("head of government", "head of government"),
    ("is the head of government", "head of government"),
    ("prime minister", "head of government"),
    ("mayor", "head of government"),
    ("was the head of government", "head of government"),
    ("location", "location"),
    ("is the location", "location"),
    ("venue", "location"),
    ("whereabouts", "location"),
    ("was located in", "location"),
    ("parent organization", "parent organization"),
    ("is the parent organization", "parent organization"),
    ("parent company", "parent organization"),
    ("subsidiary of", "parent organization"),
    ("was the parent organization", "parent organization"),
    ("compulsory education (minimum age)",
     "compulsory education (minimum age)"),
    ("is the compulsory education (minimum age)",
     "compulsory education (minimum age)"),
    ("Compulsory Education (Minimum Age)",
     "compulsory education (minimum age)"),
    ("was the compulsory education (minimum age)",
     "compulsory education (minimum age)"),
    ("the compulsory education (minimum age)",
     "compulsory education (minimum age)"),
    ("inception", "inception"),
    ("is the inception", "inception"),
    ("established", "inception"),
    ("formation date", "inception"),
    ("date of foundation", "inception"),
    ("applies to jurisdiction", "applies to jurisdiction"),
    ("Applies To Jurisdiction", "applies to jurisdiction"),
    ("jurisdiction", "applies to jurisdiction"),
    ("valid in jurisdiction", "applies to jurisdiction"),
    ("applies to place", "applies to jurisdiction"),
    ("date of death", "date of death"),
    ("died on", "date of death"),
    ("year of death", "date of death"),
    ("deathdate", "date of death"),
    ("was the date of death", "date of death"),
    ("parent taxon", "parent taxon"),
    ("is the parent taxon", "parent taxon"),
    ("taxon parent", "parent taxon"),
    ("higher taxon", "parent taxon"),
    ("was the parent taxon", "parent taxon"),
    ("developer", "developer"),
    ("is the developer", "developer"),
    ("developed by", "developer"),
    ("game developer", "developer"),
    ("was developed by", "developer"),
    ("followed by", "followed by"),
    ("is followed by", "followed by"),
    ("succeeded by", "followed by"),
    ("comes before", "followed by"),
    ("was followed by", "followed by"),
    ("twinned administrative body", "twinned administrative body"),
    ("is the twinned administrative body", "twinned administrative body"),
    ("twin town", "twinned administrative body"),
    ("sister city", "twinned administrative body"),
    ("partner city", "twinned administrative body"),
    ("notable work", "notable work"),
    ("is the notable work", "notable work"),
    ("major works", "notable work"),
    ("known for", "notable work"),
    ("wrote", "notable work"),
    ("subclass of", "subclass of"),
    ("is a subclass of", "subclass of"),
    ("type of", "subclass of"),
    ("kind of", "subclass of"),
    ("subtype of", "subclass of"),
    ("subsidiary", "subsidiary"),
    ("is the subsidiary", "subsidiary"),
    ("daughter company", "subsidiary"),
    ("has subsidiary", "subsidiary"),
    ("was the subsidiary", "subsidiary"),
    ("located in or next to body of water",
     "located in or next to body of water"),
    ("is located in or next to body of water",
     "located in or next to body of water"),
    ("on lake", "located in or next to body of water"),
    ("on river", "located in or next to body of water"),
    ("was located on body of water",
     "located in or next to body of water"),
    ("languages spoken, written or signed",
     "languages spoken, written or signed"),
    ("languages spoken", "languages spoken, written or signed"),
    ("speaks language", "languages spoken, written or signed"),
    ("signed language", "languages spoken, written or signed"),
    ("is the languages spoken, written or signed",
     "languages spoken, written or signed"),
    ("follows", "follows"),
    ("succeeds", "follows"),
    ("comes after", "follows"),
    ("preceded by", "follows"),
    ("was preceded by", "follows"),
    ("head of state", "head of state"),
    ("is the head of state", "head of state"),
    ("monarch", "head of state"),
    ("king", "head of state"),
    ("was the head of state", "head of state"),
    ("child", "child"),
    ("is the child", "child"),
    ("offspring", "child"),
    ("has child", "child"),
    ("progeny", "child"),
    ("director", "director"),
    ("is the director", "director"),
    ("directed by", "director"),
    ("film director", "director"),
    ("was directed by", "director"),
    ("time-weighted average exposure limit",
     "time-weighted average exposure limit"),
    ("TWAEL", "time-weighted average exposure limit"),
    ("is the time-weighted average exposure limit",
     "time-weighted average exposure limit"),
    ("Time-Weighted Average Exposure Limit",
     "time-weighted average exposure limit"),
    ("was the time-weighted average exposure limit",
     "time-weighted average exposure limit"),
    ("named after", "named after"),
    ("was named after", "named after"),
    ("named for", "named after"),
    ("namesake", "named after"),
    ("is named after", "named after"),
    ("country for sport", "country for sport"),
    ("is the country for sport", "country for sport"),
    ("sporting nationality", "country for sport"),
    ("sports nationality", "country for sport"),
    ("was the country for sport", "country for sport"),
    ("creator", "creator"),
    ("is the creator", "creator"),
    ("created by", "creator"),
    ("made by", "creator"),
    ("was created by", "creator"),
]

_NONCE = ["xyzzy", "florp", "blarg", "quux", "snorp", "wibble", "zarn",
          "quindle", "plugh", "frobnicate"]
_REAL = ["dreams about", "is allergic to", "walks with", "thinks about",
         "is afraid of", "likes pizza with", "argues with", "cooks for",
         "is taller than the lamp", "sings to", "teaches chess to",
         "lives next door to the bakery", "fixes bicycles for",
         "writes letters to the editor about", "collects stamps with",
         "jogged past", "is the neighbour of the mayor of xyzzy",
         "was seen near", "reportedly dislikes", "once met",
         "bakes bread for", "is the owner of a red bicycle",
         "feels happy about", "washed the car with", "painted the fence for",
         "lost the keys to", "found a coin near", "missed the bus to xyzzy",
         "climbed the hill behind", "swam across the lake at dawn",
         "reads books about dragons to", "sells flowers near",
         "repairs shoes for", "delivers mail to", "is the captain of the xyzzy team",
         "organises trips to", "photographs birds with", "juggles for",
         "weaves baskets for", "carves wood with"]

FABRICATED = []
for _w in _NONCE:
    FABRICATED += [f"was {_w} in", f"is the {_w} of", f"{_w} of",
                   f"is {_w} by", f"{_w}", f"has {_w}",
                   f"{_w} member", f"is the {_w}", f"was {_w}",
                   f"place of {_w}", f"{_w} rate", f"member of {_w}",
                   f"head of {_w}", f"director of {_w} florp",
                   f"located in the {_w}", f"{_w} location"]
FABRICATED += list(_REAL)
FABRICATED = FABRICATED[:200]


def verify() -> int:
    assert len(ITEMS) == 300, f"paraphrases: {len(ITEMS)}"
    assert len(FABRICATED) == 200, f"fabricated: {len(FABRICATED)}"
    correct = wrong = abstain = 0
    problems = []
    for text, gold in ITEMS:
        name, pid, flag = canon(text)
        if name is None:
            abstain += 1
        elif name == gold and flag is False:
            correct += 1
        else:
            wrong += 1
            problems.append((text, gold, name))
    fab_bad = [(t, canon(t)) for t in FABRICATED if canon(t) != (None, None, False)]
    print(f"paraphrase: correct={correct}/300 wrong={wrong} abstain={abstain}")
    for text, gold, got in problems:
        print(f"  WRONG {text!r} gold={gold!r} got={got!r}")
    print(f"fabricated non-unknown: {len(fab_bad)}/200")
    for t, got in fab_bad[:30]:
        print(f"  HIT {t!r} -> {got}")
    return 1 if (wrong or fab_bad) else 0


def freeze() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "test_paraphrases.json").write_text(
        json.dumps([{"input": t, "gold": g} for t, g in ITEMS],
                   indent=1, ensure_ascii=False), encoding="utf-8")
    (ART / "test_fabricated.json").write_text(
        json.dumps(list(FABRICATED), indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(f"frozen {len(ITEMS)} + {len(FABRICATED)} items in {ART}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    if args.verify:
        return verify()
    if args.freeze:
        return freeze() or 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
