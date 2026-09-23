#!/usr/bin/env python3
"""Experiment 92, ENGLISH arm (template ears, N-hop) on S1-S3.

Feeds ONLY English strings of data/open/bench92 S1-S3 through template
ears, then the same notebook + reasoner + scoring as the structured arm
(exp-65 code imported read-only via exp-73's runner; exp-73's module itself
is imported read-only and never edited).

Why a new file instead of reusing exp 73's ears verbatim:
  1. Four cloze relations appear in 3/4-hop items that exp 73 never saw
     (employer, occupation, language of work or name, child) — extra
     statement patterns live here.
  2. Exp 73's compose_question() walks exactly 2 hops (it returns after
     hop 2, which would be a confident WRONG answer on 3/4-hop items) —
     the N-hop chain walk compose_n_hop() lives here.
  3. Question wording on longer chains needs extra mention cues
     (recall-biased; extras are harmless — the walk order comes from the
     taught chain, the cues are only a coverage gate).

Anything unparseable -> triple skipped / frame None -> structural
abstention (MISS on answer items), never a guess.

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench92_english_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench92_english_arm.py --run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (read-only)
import fable_notebook_contract as C  # noqa: E402 (read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench92-20260921"
DATA = ROOT / "data" / "open" / "bench92"

SPLITS = ["fable_edit92_s1_3hop", "fable_edit92_s2_4hop",
          "fable_edit92_s3_multiedit"]

# Extra taught-sentence patterns (tried AFTER exp-73's; fullmatch).
EXTRA_STATEMENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(.+?) is employed by (.+?)"), "employer"),
    (re.compile(r"(.+?) works in the field of (.+?)"), "occupation"),
    (re.compile(r"(.+?) was written in the language of (.+?)"),
     "language_of_work_or_name"),
    (re.compile(r"(.+?)'s child is (.+?)"), "child"),
    (re.compile(r"The head coach of (.+?) is (.+?)"), "head_coach"),
    (re.compile(r"The origianl broadcaster of (.+?) is (.+?)"),
     "original_broadcaster"),
    (re.compile(r"The director of (.+?) is (.+?)"), "director_manager"),
]

# Extra question mention cues, merged OVER a copy of exp-73's map
# (the original dict is never mutated).
EXTRA_REL_CUES: dict[str, list[str]] = {
    "manufacturer": ["producer", "produced", "company that produced",
                     "manufacturer", "maker", "made", "produc"],
    "location_of_formation": ["founded", "location of formation",
                              "city located where", "city where",
                              "was founded", "founding city", "house"],
    "country_of_origin": ["country of origin", "originat", "created",
                          "developed", "birthplace of the sport",
                          "was created", "where", "birthplace", "gave birth",
                          "origin", "home to", "is from", "is home",
                          "credited with creating", "creating"],
    "head_of_state": ["head of state", "current leader", "leader",
                      "president"],
    "head_of_government": ["head of the government", "head of government",
                           "current leader", "leader", "prime minister",
                           "mayor", "governor", "head of", "leads",
                           "government of"],
    "notable_work": ["renowned", "famous", "notable work", "thing that",
                     "made", "popular", "known for", "fame", "creation"],
    "creator": ["creat", "maker", "made", "develop"],
    "developer": ["develop", "developer", "company that developed"],
    "headquarters_location": ["headquarters", "headquarter", "main office",
                              "office", "situated", "located"],
    "official_language": ["official language", "officially spoken",
                          "native tongue", "language", "tongue"],
    "country_of_citizenship": ["country of citizenship", "citizenship",
                               "citizen", "nationality", "birthplace of",
                               "is from", "holds citizenship", "country of"],
    "employer": ["employ", "employer", "works for", "company that employs"],
    "occupation": ["occupation", "field", "works in", "job", "profession"],
    "language_of_work_or_name": ["language", "written in", "tongue"],
    "child": ["child", "son", "daughter", "kid", "offspring"],
    "genre": ["genre", "music", "music style", "type of music"],
    "performer": ["performer", "performed", "performs"],
    "place_of_birth": ["birthplace", "place of birth", "born",
                       "originate from in terms of city", "gave birth",
                       "city of birth", "birth of", "birth", "originate"],
    "place_of_death": ["die", "died", "death", "pass away", "passed away"],
    "sport": ["sport", "played", "plays", "position played"],
    "capital": ["capital", "seat of government"],
    "continent": ["continent", "located in"],
    "author": ["author", "wrote", "written"],
    "spouse": ["spouse", "married", "husband", "wife", "partner"],
    "founder": ["founder", "found"],
    "founded_by": ["found", "founder", "establish"],
    "educated_at": ["educated", "education", "university where",
                    "studied", "school", "alma mater", "attend"],
    "work_location": ["had a job", "worked", "job", "work location", "work",
                      "workplace", "operate", "based"],
    "religion_or_worldview": ["religion", "affiliated", "belief",
                              "religious affiliation", "affiliation"],
    "chairperson": ["chairperson", "chair"],
    "officeholder": ["president of", "president", "officeholder",
                     "individual who is", "referred to as"],
    "director_manager": ["director", "manager", "coach"],
    "head_coach": ["head coach", "coach"],
    "original_broadcaster": ["broadcaster", "broadcast", "aired"],
    "chief_executive_officer": ["chief executive officer", "ceo",
                                "chief executive"],
    "creator_country": ["created"],
}

REL_CUES92: dict[str, list[str]] = {k: list(v)
                                    for k, v in B73.REL_MENTION_CUES.items()}
for k, v in EXTRA_REL_CUES.items():
    seen = set(REL_CUES92.get(k, []))
    REL_CUES92.setdefault(k, [])
    for cue in v:
        if cue not in seen:
            REL_CUES92[k].append(cue)
            seen.add(cue)


def _entity_mentions92(question: str, entities: list[str]) -> list[str]:
    """Longest-match-first variant of exp-73's mention finder.

    Exp-73 keeps the SHORTEST span on ties (e.g. 'Lu' shadows
    'Lucrezia Borgia'); here the longest span wins, so a mid-chain
    substring cannot masquerade as a second mentioned entity.
    """
    q = question.lower()
    spans: list[tuple[int, int, str]] = []
    for e in sorted(set(entities), key=len, reverse=True):
        el = e.lower()
        start = 0
        while True:
            i = q.find(el, start)
            if i < 0:
                break
            spans.append((i, i + len(el), e))
            start = i + 1
    # longest first: a kept span blocks any span it contains
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def hear_teach92(sentence: str) -> tuple[str, str, str] | None:
    got = B73.hear_teach_template(sentence)
    if got is not None:
        return got
    s = " ".join(str(sentence).split())
    if not s:
        return None
    for pat, rel in EXTRA_STATEMENT_PATTERNS:
        m = pat.fullmatch(s)
        if m:
            subj, obj = m.group(1).strip(), m.group(2).strip()
            if subj and obj:
                return (subj, rel, obj)
    return None


def _relation_mentions92(question: str) -> set[str]:
    q = question.lower()
    return {rel for rel, cues in REL_CUES92.items()
            if any(cue in q for cue in cues)}


def compose_n_hop(question: str, triples: list[tuple[str, str, str]]
                  ) -> tuple[str, list[str]] | None:
    """English question + parsed taught triples -> (name, relations).

    N-hop generalisation of exp-73's 2-hop walk: the question must name
    exactly one taught entity (the chain start); from there follow the
    single-outgoing-relation chain (post-edit object at each step) to the
    sink; every walked relation must be mentioned in the question
    (coverage gate, else None rather than a guess).
    """
    q = " ".join(str(question).split())
    if not q:
        return None
    ents: list[str] = []
    for s, _, o in triples:
        ents.extend([s, o])
    ment = _entity_mentions92(q, ents)
    if len(ment) != 1:
        return None
    start = ment[0]
    rels: list[str] = []
    cur = start
    seen_objs: set[str] = set()
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) != 1:
            break
        r1 = uniq[0]
        mid = [o for (r, o) in outs if r == r1][-1]
        if mid in seen_objs:
            return None
        seen_objs.add(mid)
        rels.append(r1)
        cur = mid
        if len(rels) > 6:
            return None
    if not rels:
        return None
    mentioned = _relation_mentions92(q)
    if any(r not in mentioned for r in rels):
        return None
    return (start, rels)


class TemplateEars92:
    kind = "template92"

    def hear_teach(self, sentence: str):
        return hear_teach92(sentence)

    def hear_question(self, question: str, triples):
        return compose_n_hop(question, triples)


def cmd_run(_args) -> int:
    ears = TemplateEars92()
    ART.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch92en"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary = {}
    for stem in SPLITS:
        items = B65.load_items(DATA / f"{stem}.jsonl")
        rows = [B73.english_run_item(it, ears, scratch / stem)
                for it in items]
        table = B65.score(rows)
        (run_dir / f"bench92_{stem.split('_')[2]}_en_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        summary[stem] = table
        print(f"{stem} (english): items={len(rows)}")
        for typ, cell in sorted(table.items()):
            print(f"    {typ}: {cell}")
        unp = sum(r.get("n_unparsed_teach", 0) for r in rows)
        print(f"    unparsed_teach_total={unp}")
        for r in [x for x in rows
                  if x["verdict"] in ("WRONG", "MISS")][:5]:
            print("    FAIL:", json.dumps(r, ensure_ascii=False)[:300])
    (run_dir / "bench92_english_summary.json").write_text(
        json.dumps({"seconds": round(time.time() - t0, 1),
                    "summary": summary}, indent=1), encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag)
        if not cond:
            fails.append(tag)

    check(hear_teach92("Lewis Carroll is employed by University of Oxford")
          == ("Lewis Carroll", "employer", "University of Oxford"),
          "employer")
    check(hear_teach92("Red Ryder works in the field of cowboy")
          == ("Red Ryder", "occupation", "cowboy"), "occupation")
    check(hear_teach92("Paradise Lost was written in the language of English")
          == ("Paradise Lost", "language_of_work_or_name", "English"),
          "lang-of-work")
    check(hear_teach92("Jack Elway's child is John Elway")
          == ("Jack Elway", "child", "John Elway"), "child")
    check(hear_teach92("The capital of Poland is Warsaw")
          == ("Poland", "capital", "Warsaw"), "base-patterns-intact")
    check(hear_teach92("Blorpt zzz wobble.") is None, "garbled-None")
    mq3 = [("Cobalt", "manufacturer", "Chev"),
           ("Chev", "location_of_formation", "Detroit"),
           ("Detroit", "head_of_government", "Duggan")]
    check(compose_n_hop(
        "Who is the head of the government of the city where the producer "
        "of Cobalt was founded?", mq3)
        == ("Cobalt", ["manufacturer", "location_of_formation",
                       "head_of_government"]), "3hop-walk")
    check(compose_n_hop("Who is the mayor of Detroit?", mq3)
          == ("Detroit", ["head_of_government"]), "onehop-subwalk")
    check(compose_n_hop("Blorpt zzz?", mq3) is None, "garbled-q-None")
    with tempfile.TemporaryDirectory() as tmp:
        it = {"id": "e1", "type": "mquake-s1-3hop", "expected": "answer",
              "taught": [
                  {"sentence_en": "Cobalt was produced by Chev."},
                  {"sentence_en": "Chev was founded in the city of Detroit."},
                  {"sentence_en": "Nobody knows Blorpt zzz."}],
              "question": "Who leads Detroit?", "gold": [], "gold_aliases": []}
        row = B73.english_run_item(it, TemplateEars92(), Path(tmp))
        check(row["verdict"] == "MISS" and row["status"] != C.OK,
              "unparseable->MISS-never-WRONG")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 92 English arm (S1-S3)")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
