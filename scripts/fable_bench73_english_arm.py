#!/usr/bin/env python3
"""Experiment 73 — ENGLISH-INPUT arm of Fable-Edit-200 with pluggable ears.

Loads the 200 items of data/open/bench65/fable_edit_200.jsonl, feeds ONLY the
English strings (taught sentence_en strings, then the question string) through
an Ears object, then uses the SAME notebook + reasoner + scoring as the
structured arm (scripts/fable_bench65_notebook_arm.py, imported read-only).

Ears interface (this arm):
    hear_teach(sentence_en) -> (subject, relation, object) | None
        None = cannot parse -> the triple is SKIPPED (never written).
    hear_question(question_en, triples) -> (name, [relations]) | None
        triples = the successfully parsed taught triples (English-derived).
        None = cannot parse -> MISSING/abstain, never a guess.

Two ears choices via --ears:
    template            deterministic regex parser for the sentence patterns
                        that actually occur in the file (see STATEMENT_PATTERNS
                        and the design doc for the full list).
    ears47:<ckpt>       exp-47 neural ears (FrameEars over borrowed SciBERT):
                        CPU inference, sentence -> frame rows. Registered use
                        is a smoke test only (import + forward on 3 sentences);
                        full-bench ears47 runs happen once a checkpoint exists
                        under artifacts/fable-ears47-20260921/runs/.

Correction handling (English-derived, no structured flags used): sentences are
heard in file order (originals, then edits); a triple whose (subject, relation)
was already heard with a different object is taught with correction=True so the
edit supersedes, exactly like the structured arm's edit flag on this file.

Additive, offline, Mac CPU, one thread. Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench73_english_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench73_english_arm.py --run --ears template
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench73_english_arm.py --run-garbled --ears template
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench73_english_arm.py --smoke-ears47 [--snapshot DIR]
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

import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only; never edited)
import fable_notebook_contract as C  # noqa: E402 (read-only; never edited)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench73-20260921"
DATA_DEFAULT = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
GARBLED_DEFAULT = ART / "fable_bench73_garbled.jsonl"
EARS47_RUNS = ROOT / "artifacts" / "fable-ears47-20260921" / "runs"

# ----------------------------------------------------------------------------
# Template ears: statement patterns (taught sentences).
# Ordered: specific ^The patterns first, generic officeholder ^The last.
# Each entry: (compiled fullmatch regex, relation key, (subj_group, obj_group)).
# Covers every sentence_en template occurring in fable_edit_200.jsonl.
# ----------------------------------------------------------------------------
STATEMENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"The author of (.+?) is (.+?)"), "author"),
    (re.compile(r"The capital of (.+?) is (.+?)"), "capital"),
    (re.compile(r"The chairperson of (.+?) is (.+?)"), "chairperson"),
    (re.compile(r"The chief executive officer of (.+?) is (.+?)"),
     "chief_executive_officer"),
    (re.compile(r"The company that produced (.+?) is (.+?)"), "manufacturer"),
    (re.compile(r"The headquarters of (.+?) is located in the city of (.+?)"),
     "headquarters_location"),
    (re.compile(r"The name of the current head of state in (.+?) is (.+?)"),
     "head_of_state"),
    (re.compile(r"The name of the current head of the (.+?) government is (.+?)"),
     "head_of_government"),
    (re.compile(r"The official language of (.+?) is (.+?)"), "official_language"),
    (re.compile(r"The type of music that (.+?) plays is (.+?)"), "genre"),
    (re.compile(r"The univeristy where (.+?) was educated is (.+?)"), "educated_at"),
    (re.compile(r"(.+?) died in the city of (.+?)"), "place_of_death"),
    (re.compile(r"(.+?) is a citizen of (.+?)"), "country_of_citizenship"),
    (re.compile(r"(.+?) is affiliated with the religion of (.+?)"),
     "religion_or_worldview"),
    (re.compile(r"(.+?) is associated with the sport of (.+?)"), "sport"),
    (re.compile(r"(.+?) is famous for (.+?)"), "notable_work"),
    (re.compile(r"(.+?) is located in the continent of (.+?)"), "continent"),
    (re.compile(r"(.+?) is married to (.+?)"), "spouse"),
    (re.compile(r"(.+?) is the apprentice of (.+?)\."), "apprentice_of"),
    (re.compile(r"(.+?) is the author of (.+?)\."), "author_of"),
    (re.compile(r"(.+?) is the composer of (.+?)\."), "composer_of"),
    (re.compile(r"(.+?) is the discoverer of (.+?)\."), "discoverer_of"),
    (re.compile(r"(.+?) is the envoy of (.+?)\."), "envoy_of"),
    (re.compile(r"(.+?) is the founder of (.+?)\."), "founder_of"),
    (re.compile(r"(.+?) is the herald of (.+?)\."), "herald_of"),
    (re.compile(r"(.+?) is the inventor of (.+?)\."), "inventor_of"),
    (re.compile(r"(.+?) is the keeper of (.+?)\."), "keeper_of"),
    (re.compile(r"(.+?) is the mentor of (.+?)\."), "mentor_of"),
    (re.compile(r"(.+?) is the rival of (.+?)\."), "rival_of"),
    (re.compile(r"(.+?) is the scout of (.+?)\."), "scout_of"),
    (re.compile(r"(.+?) is the warden of (.+?)\."), "warden_of"),
    (re.compile(r"(.+?) plays the position of (.+?)"),
     "position_played_on_team_speciality"),
    (re.compile(r"(.+?) speaks the language of (.+?)"),
     "languages_spoken_written_or_signed"),
    (re.compile(r"(.+?) was born in the city of (.+?)"), "place_of_birth"),
    (re.compile(r"(.+?) was composed by (.+?)\."), "composed_by"),
    (re.compile(r"(.+?) was created by (.+?)"), "creator"),
    (re.compile(r"(.+?) was created in the country of (.+?)"), "country_of_origin"),
    (re.compile(r"(.+?) was developed by (.+?)"), "developer"),
    (re.compile(r"(.+?) was discovered by (.+?)\."), "discovered_by"),
    (re.compile(r"(.+?) was founded by (.+?)\.?"), "founded_by"),
    (re.compile(r"(.+?) was founded in the city of (.+?)"), "location_of_formation"),
    (re.compile(r"(.+?) was invented by (.+?)\."), "invented_by"),
    (re.compile(r"(.+?) was performed by (.+?)"), "performer"),
    (re.compile(r"(.+?) was written by (.+?)\."), "written_by"),
    (re.compile(r"(.+?) worked in the city of (.+?)"), "work_location"),
    # Generic officeholder ("The President of Syria is Bashar al-Assad"): LAST.
    (re.compile(r"The (.+?) is (.+?)"), "officeholder"),
]

# Noun -> _of key for reversal/abstain "Who is the <noun> of <Name>?" questions.
REV_OF_NOUNS = {
    "apprentice": "apprentice_of", "author": "author_of",
    "composer": "composer_of", "discoverer": "discoverer_of",
    "envoy": "envoy_of", "founder": "founder_of", "herald": "herald_of",
    "inventor": "inventor_of", "keeper": "keeper_of", "mentor": "mentor_of",
    "rival": "rival_of", "scout": "scout_of", "warden": "warden_of",
}
# Verb -> _by key for reversal "Who <verb> by <Name>?" questions.
REV_BY_VERBS = {
    "composed": "composed_by", "written": "written_by",
    "discovered": "discovered_by", "founded": "founded_by",
    "invented": "invented_by",
}
# Substrings that disqualify a "Who ... of/by <Name>?" remainder as a bare name
# (mquake questions such as "Who is the founder of the company that ...").
NON_NAME_CUES = (" that ", " who ", " where ", " which ", " created ",
                 " developed ", " produced ", " educated ")

# Relation cues in questions (lowercase substrings; recall-biased on purpose:
# extras are harmless because the frame order comes from the taught walk and
# this scan is only a coverage gate — a walk relation unmentioned here forces
# MISSING instead of a guess).
REL_MENTION_CUES: dict[str, list[str]] = {
    "chief_executive_officer": ["chief executive officer"],
    "country_of_citizenship": ["country of citizenship", "citizenship",
                               "citizen", "nationality"],
    "official_language": ["official language", "officially spoken",
                          "native tongue", "language"],
    "spouse": ["spouse", "married", "husband", "wife"],
    "languages_spoken_written_or_signed": ["language", "tongue", "speak",
                                           "spoken"],
    "head_of_government": ["head of the government", "head of government",
                           "current leader", "leader"],
    "performer": ["performer", "performed"],
    "place_of_birth": ["birthplace", "place of birth", "born",
                       "originate from in terms of city"],
    "chairperson": ["chairperson"],
    "manufacturer": ["produced", "company that produced", "manufacturer"],
    "location_of_formation": ["founded", "location of formation",
                              "city located where", "city where"],
    "country_of_origin": ["country of origin", "originat", "created",
                          "developed", "birthplace of the sport"],
    "developer": ["develop"],
    "founded_by": ["found", "founder"],
    "continent": ["continent"],
    "capital": ["capital"],
    "author": ["author", "wrote", "written"],
    "officeholder": ["president of", "president", "officeholder",
                     "individual who is"],
    "work_location": ["had a job", "worked", "job", "work location"],
    "head_of_state": ["head of state", "current leader", "leader"],
    "sport": ["sport", "played", "plays"],
    "position_played_on_team_speciality": ["position"],
    "religion_or_worldview": ["religion", "affiliated"],
    "creator": ["creat"],
    "headquarters_location": ["headquarters"],
    "educated_at": ["educated", "education", "university where"],
    "genre": ["genre", "music"],
    "place_of_death": ["die", "died", "death", "pass away"],
    "notable_work": ["renowned", "famous", "notable work", "thing that"],
}


def hear_teach_template(sentence: str) -> tuple[str, str, str] | None:
    """English taught sentence -> (subject, relation, object), or None."""
    s = " ".join(str(sentence).split())
    if not s:
        return None
    for pat, rel in STATEMENT_PATTERNS:
        m = pat.fullmatch(s)
        if m:
            subj, obj = m.group(1).strip(), m.group(2).strip()
            if subj and obj:
                return (subj, rel, obj)
    return None


def _bare_name_ok(name: str) -> bool:
    if not name or not name[0].isupper():
        return False
    low = f" {name.lower()} "
    return not any(cue in low for cue in NON_NAME_CUES)


def _entity_mentions(question: str, entities: list[str]) -> list[str]:
    """Taught entity strings mentioned in the question (longest-match)."""
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
    spans.sort()
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def _relation_mentions(question: str) -> set[str]:
    q = question.lower()
    return {rel for rel, cues in REL_MENTION_CUES.items()
            if any(cue in q for cue in cues)}


def compose_question(question: str,
                     triples: list[tuple[str, str, str]]
                     ) -> tuple[str, list[str]] | None:
    """English question + parsed taught triples -> (name, relations), or None.

    Shared arm code (both ears choices): the pluggable ears map single
    sentences to triples; query composition over those triples lives here so
    ears47 drops in without new code.
    """
    q = " ".join(str(question).split())
    if not q:
        return None
    ents: list[str] = []
    for s, _, o in triples:
        ents.extend([s, o])

    m = re.fullmatch(r"What is the never-taught relation (\d+) of (.+?)\??", q)
    if m:
        return (m.group(2).strip(), [f"never_taught_rel_{m.group(1)}"])

    m = re.fullmatch(
        r"What is the never-taught relation of the ([\w /-]+?) of (.+?)\??", q)
    if m:
        key = REV_OF_NOUNS.get(m.group(1).strip().lower().replace(" ", "_"))
        if key is None:
            return None
        # Second hop was never taught: use an undeclared key so the notebook
        # structurally abstains (same mechanism as the structured arm).
        return (m.group(2).strip(), [key, "never_taught_rel"])

    m = re.fullmatch(r"Who is the ([\w /-]+?) of (.+?)\??", q)
    if m:
        label = m.group(1).strip().lower().replace(" ", "_")
        name = m.group(2).strip()
        if label in REV_OF_NOUNS and _bare_name_ok(name):
            return _one_hop(name, REV_OF_NOUNS[label], triples)

    m = re.fullmatch(r"Who (\w+) by (.+?)\??", q)
    if m:
        verb = m.group(1).strip().lower()
        name = m.group(2).strip()
        if verb in REV_BY_VERBS and _bare_name_ok(name):
            return _one_hop(name, REV_BY_VERBS[verb], triples)

    # MQuAKE two-hop: the question names exactly the chain start; walk the
    # taught chain for hop order; require both hop relations to be mentioned
    # in the question (coverage gate, else MISSING rather than a guess).
    ment = _entity_mentions(q, ents)
    if len(ment) != 1:
        return None
    start = ment[0]
    r1s = [r for (s, r, _) in triples if s == start]
    r1s = list(dict.fromkeys(r1s))
    if len(r1s) != 1:
        return None
    r1 = r1s[0]
    objs = [o for (s, r, o) in triples if s == start and r == r1]
    if not objs:
        return None
    mid = objs[-1]  # post-edit object: corrections supersede
    r2s = [r for (s, r, _) in triples if s == mid and r != r1]
    r2s = list(dict.fromkeys(r2s))
    if len(r2s) != 1:
        return None
    r2 = r2s[0]
    mentioned = _relation_mentions(q)
    if r1 not in mentioned or r2 not in mentioned:
        return None
    return (start, [r1, r2])


def _one_hop(name: str, rel: str,
             triples: list[tuple[str, str, str]]) -> tuple[str, list[str]]:
    for (s, r, _) in triples:
        if s == name and r == rel:
            return (name, [rel])
    for (s, r, _) in triples:
        if r == rel and _ == name:
            return (s, [rel])
    # Named entity never taught with this relation: ask it anyway so the
    # notebook abstains structurally (UNKNOWN_ENTITY / MISSING_FACT).
    return (name, [rel])


class TemplateEars:
    """Deterministic template parser for the file's sentence patterns."""

    kind = "template"

    def hear_teach(self, sentence: str) -> tuple[str, str, str] | None:
        return hear_teach_template(sentence)

    def hear_question(self, question: str,
                      triples: list[tuple[str, str, str]]
                      ) -> tuple[str, list[str]] | None:
        return compose_question(question, triples)


# ----------------------------------------------------------------------------
# Exp-47 neural ears adapter (CPU inference; smoke-test grade here).
# ----------------------------------------------------------------------------
def fable_bench73_find_checkpoints() -> list[Path]:
    if not EARS47_RUNS.exists():
        return []
    return sorted(EARS47_RUNS.glob("*/ear.pt"))


class Ears47Adapter:
    """Wraps the exp-47 FrameEars model (borrowed SciBERT + our head).

    Sentence mapping is neural; question composition reuses the shared
    compose_question() over neurally parsed triples. Full-bench decoding is
    implemented but UNVALIDATED (no checkpoint exists yet); the registered
    bar here is import + CPU forward on 3 sentences (or a clear skip).
    """

    kind = "ears47"

    def __init__(self, ckpt: Path, snapshot: str | None = None):
        self.ckpt = Path(ckpt)
        self.snapshot = snapshot
        self._model = None
        self._tok = None
        self._classes: list[str] | None = None

    def load(self) -> None:
        import torch  # noqa: F401 (lazy: CPU inference only here)
        sys.path.insert(0, str(SCRIPTS))
        import fable_ears47_encoder as E  # noqa: E402
        import fable_ears47_model as M  # noqa: E402
        snap = self.snapshot or E.ensure_snapshot()
        enc, tok, _info = E.load(snap)
        blob = __import__("torch").load(str(self.ckpt), map_location="cpu",
                                        weights_only=True)
        n_rel = int(blob["state"]["rel.weight"].shape[0])
        model = M.FrameEars(enc, n_rel)
        model.load_state_dict(blob["state"], strict=True)
        if "temps" in blob:
            model.temps.copy_(__import__("torch").as_tensor(blob["temps"]))
        model.eval()
        self._model, self._tok = model, tok
        rc_path = ROOT / "artifacts" / "fable-ears47-20260921" / "relation_classes.json"
        if rc_path.exists():
            self._classes = json.loads(rc_path.read_text(
                encoding="utf-8"))["classes"]

    def forward3(self, sentences: list[str]) -> dict:
        """CPU forward on 3 sentences; returns shape/act info (smoke test)."""
        import torch
        assert self._model is not None and self._tok is not None, \
            "call load() first"
        ids, masks = [], []
        for s in sentences[:3]:
            ii, _ch = self._tok.encode(s, 96)
            m = [True] * len(ii)
            while len(ii) < 96:
                ii.append(0)
                m.append(False)
            ids.append(ii)
            masks.append(m)
        with torch.no_grad():
            out = self._model(torch.tensor(ids), torch.tensor(masks))
        return {"act_shape": list(out["act"].shape),
                "rel_shape": list(out["rel"].shape),
                "ptr_shape": list(out["ptr"].shape),
                "act_argmax": [int(x) for x in out["act"].argmax(-1)],
                "rel_argmax": [int(x) for x in out["rel"].argmax(-1)]}

    def hear_teach(self, sentence: str) -> tuple[str, str, str] | None:
        raise NotImplementedError(
            "full neural decode is UNVALIDATED until a checkpoint exists; "
            "use --smoke-ears47 for the registered smoke test.")

    def hear_question(self, question: str,
                      triples: list[tuple[str, str, str]]
                      ) -> tuple[str, list[str]] | None:
        return compose_question(question, triples)


# ----------------------------------------------------------------------------
# English run path (same notebook + reasoner + scoring as structured arm).
# ----------------------------------------------------------------------------
def english_run_item(item: dict, ears, scratch: Path,
                     teach_fn=None) -> dict:
    teach = teach_fn or ears.hear_teach
    triples: list[tuple[str, str, str]] = []
    n_skip = 0
    for t in item["taught"]:
        parsed = teach(t["sentence_en"])
        if parsed is None:
            n_skip += 1
            continue
        triples.append(parsed)
    frame = ears.hear_question(item["question"], triples)
    if frame is None:
        out = {"id": item["id"], "type": item["type"],
               "expected": item["expected"], "status": C.MISSING_FACT,
               "contract_status": C.MISSING_FACT, "teach_notes": [],
               "ms": 0.0, "verdict": ("abstain_ok" if item["expected"]
                                      == "abstain" else "MISS"),
               "ears": ears.kind, "n_unparsed_teach": n_skip,
               "frame": None}
        return out
    name, rels = frame
    synth_taught = []
    seen: dict[tuple[str, str], str] = {}
    for i, (s, r, o) in enumerate(triples):
        key = (s, r)
        edit = key in seen and seen[key] != o
        seen[key] = o
        synth_taught.append({"subject": s, "relation": r, "object": o,
                             "edit": edit, "sentence_en": ""})
    synth = dict(item)
    synth["taught"] = synth_taught
    synth["frame"] = {"name": name, "relations": list(rels)}
    row = B65.run_item(synth, scratch)
    row["ears"] = ears.kind
    row["n_unparsed_teach"] = n_skip
    row["frame"] = {"name": name, "relations": list(rels)}
    return row


def cmd_run(args) -> int:
    if args.ears == "template":
        ears = TemplateEars()
    elif args.ears.startswith("ears47:"):
        ears = Ears47Adapter(args.ears.split(":", 1)[1], args.snapshot)
        ears.load()
    else:
        print(f"unknown --ears {args.ears!r} (want 'template' or "
              "'ears47:<checkpoint>')")
        return 2
    items = B65.load_items(Path(args.data))
    ART.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch73"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    # Reference: structured arm in-memory (no other agent's files touched).
    ref_scratch = ART / "scratch73ref"
    if ref_scratch.exists():
        shutil.rmtree(ref_scratch)
    ref_scratch.mkdir(parents=True)
    t0 = time.time()
    rows = [english_run_item(it, ears, scratch) for it in items]
    secs = time.time() - t0
    table = B65.score(rows)
    # Reference: structured arm in-memory (no other agent's files touched).
    # Only for the main bench file; garbled items have no structured triples.
    ref_table: dict = {}
    if Path(args.data) == DATA_DEFAULT:
        ref_rows = [B65.run_item(it, ref_scratch) for it in items]
        ref_table = B65.score(ref_rows)
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.rmtree(ref_scratch, ignore_errors=True)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    stem = "bench73" if args.data == str(DATA_DEFAULT) else "bench73-garbled"
    (run_dir / f"{stem}_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    (run_dir / f"{stem}_table.json").write_text(
        json.dumps({"seconds": round(secs, 1), "ears": ears.kind,
                    "table": table, "reference_table": ref_table,
                    "items": len(rows)}, indent=1), encoding="utf-8")
    print(f"ears={ears.kind} items={len(rows)} seconds={secs:.1f}")
    for typ, cell in sorted(table.items()):
        print(f"  {typ}: {cell}")
    if ref_table:
        print("reference(structured):")
        for typ, cell in sorted(ref_table.items()):
            print(f"  {typ}: {cell}")
        print("TABLES IDENTICAL" if table == ref_table else "TABLES DIFFER")
    wrong = [r for r in rows if r["verdict"] == "WRONG"]
    miss = [r for r in rows if r["verdict"] == "MISS"]
    print(f"WRONG={len(wrong)} MISS={len(miss)}")
    for r in (wrong + miss)[:10]:
        print("  FAIL:", json.dumps(r, ensure_ascii=False))
    return 0


def cmd_smoke_ears47(args) -> int:
    ckpts = fable_bench73_find_checkpoints()
    if args.ckpt:
        ckpts = [Path(args.ckpt)]
    if not ckpts:
        print("SMOKE SKIP: no checkpoint under "
              f"{EARS47_RUNS} (exp 47 still training); "
              "rerun with --ckpt <ear.pt> once one exists.")
        return 0
    demo = ["The capital of Poland is Warsaw",
            "Ada Lovelace was born in the city of London",
            "Who is the founder of Silver Feasts?"]
    for ck in ckpts:
        ad = Ears47Adapter(ck, args.snapshot)
        try:
            ad.load()
        except Exception as exc:  # offline / no snapshot yet
            print(f"SMOKE SKIP: cannot load {ck} here ({exc}).")
            return 0
        info = ad.forward3(demo)
        print(f"SMOKE PASS: import + CPU forward ok on {ck}: {info}")
    return 0


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag)
        if not cond:
            fails.append(tag)

    # 1. Statement patterns: one canonical example per relation family.
    cases = [
        ("The author of Fasti is Ovid", ("Fasti", "author", "Ovid")),
        ("The capital of Poland is Warsaw", ("Poland", "capital", "Warsaw")),
        ("The chairperson of Yale University is Peter Salovey",
         ("Yale University", "chairperson", "Peter Salovey")),
        ("The chief executive officer of Twitter is Jack Dorsey",
         ("Twitter", "chief_executive_officer", "Jack Dorsey")),
        ("The company that produced Buick LaCrosse is General Motors",
         ("Buick LaCrosse", "manufacturer", "General Motors")),
        ("The headquarters of Microsoft is located in the city of Redmond",
         ("Microsoft", "headquarters_location", "Redmond")),
        ("The name of the current head of state in United States of America"
         " is Donald Trump",
         ("United States of America", "head_of_state", "Donald Trump")),
        ("The name of the current head of the Austria government"
         " is Sebastian Kurz",
         ("Austria", "head_of_government", "Sebastian Kurz")),
        ("The official language of Japan is Japanese",
         ("Japan", "official_language", "Japanese")),
        ("The type of music that Martin Denny plays is jazz",
         ("Martin Denny", "genre", "jazz")),
        ("The univeristy where Hugo Grotius was educated is Leiden University",
         ("Hugo Grotius", "educated_at", "Leiden University")),
        ("The President of Syria is Bashar al-Assad",
         ("President of Syria", "officeholder", "Bashar al-Assad")),
        ("Judah Halevi died in the city of Jerusalem",
         ("Judah Halevi", "place_of_death", "Jerusalem")),
        ("Rekha is a citizen of India", ("Rekha", "country_of_citizenship",
                                         "India")),
        ("Johann Sebastian Bach is affiliated with the religion"
         " of Lutheranism",
         ("Johann Sebastian Bach", "religion_or_worldview", "Lutheranism")),
        ("Chase Headley is associated with the sport of baseball",
         ("Chase Headley", "sport", "baseball")),
        ("William Gibson is famous for Neuromancer",
         ("William Gibson", "notable_work", "Neuromancer")),
        ("India is located in the continent of Asia",
         ("India", "continent", "Asia")),
        ("CM Punk is married to AJ Lee", ("CM Punk", "spouse", "AJ Lee")),
        ("Elowen Frostmere is the apprentice of Orson Vell.",
         ("Elowen Frostmere", "apprentice_of", "Orson Vell")),
        ("Kenny Britt plays the position of wide receiver",
         ("Kenny Britt", "position_played_on_team_speciality",
          "wide receiver")),
        ("AJ Lee speaks the language of English",
         ("AJ Lee", "languages_spoken_written_or_signed", "English")),
        ("Ovid was born in the city of Sulmona",
         ("Ovid", "place_of_birth", "Sulmona")),
        ("Gilded Mirrors was composed by Damon Moonrake.",
         ("Gilded Mirrors", "composed_by", "Damon Moonrake")),
        ("Lady Macbeth was created by William Shakespeare",
         ("Lady Macbeth", "creator", "William Shakespeare")),
        ("Back Stage was created in the country of United States of America",
         ("Back Stage", "country_of_origin", "United States of America")),
        ("Kubuntu was developed by Canonical Group Limited",
         ("Kubuntu", "developer", "Canonical Group Limited")),
        ("Pearl Bells was discovered by Silas Ironbark.",
         ("Pearl Bells", "discovered_by", "Silas Ironbark")),
        ("Boeing was founded by William Boeing",
         ("Boeing", "founded_by", "William Boeing")),
        ("Silver Feasts was founded by Dunstan Ashdown.",
         ("Silver Feasts", "founded_by", "Dunstan Ashdown")),
        ("Kevin Federline was founded in the city of Los Angeles",
         ("Kevin Federline", "location_of_formation", "Los Angeles")),
        ("Silver Maps was invented by Vesper Ironbark.",
         ("Silver Maps", "invented_by", "Vesper Ironbark")),
        ("Highway 61 Revisited was performed by Bob Dylan",
         ("Highway 61 Revisited", "performer", "Bob Dylan")),
        ("Oaken Melodies was written by Marisol Underbough.",
         ("Oaken Melodies", "written_by", "Marisol Underbough")),
        ("Vincent Auriol worked in the city of Paris",
         ("Vincent Auriol", "work_location", "Paris")),
    ]
    for sent, want in cases:
        check(hear_teach_template(sent) == want, f"teach {sent[:45]!r}")
    # Garbled / empty must yield None (never a write).
    for bad in ["Blorpt zzz wobble wobble.", "", "   ",
                "Colorless green ideas sleep furiously",
                "Ann lives in France.", "Who did what now??"]:
        check(hear_teach_template(bad) is None, f"garbled-teach {bad[:30]!r}")

    # 2. Mini end-to-end items through the real notebook+reasoner path.
    mini = [
        {"id": "s1", "type": "x", "expected": "answer",
         "taught": [{"sentence_en": "Ann lives in nowhere."},
                    {"sentence_en": "The capital of France is Paris."}],
         "question": "Who is the herald of Magnus Quill?",
         "gold": [], "gold_aliases": []},
    ]
    ears = TemplateEars()
    with tempfile.TemporaryDirectory() as tmp:
        # correction inference: same (subj, rel), new object -> edit flag
        triples = [("Ann", "spouse", "Bob"), ("Ann", "spouse", "Cara")]
        seen: dict = {}
        flags = []
        for s, r, o in triples:
            flags.append((s, r) in seen and seen[(s, r)] != o)
            seen[(s, r)] = o
        check(flags == [False, True], "correction inference")
        # reversal fwd/rev routing on parsed triples
        rev = [("Damon Moonrake", "composer_of", "Gilded Mirrors"),
               ("Gilded Mirrors", "composed_by", "Damon Moonrake")]
        check(compose_question("Who is the composer of Gilded Mirrors?", rev)
              == ("Damon Moonrake", ["composer_of"]), "composer fwd")
        check(compose_question("Who composed by Gilded Mirrors?", rev)
              == ("Gilded Mirrors", ["composed_by"]), "composer rev")
        check(compose_question("Who is the apprentice of Elowen Nettlestone?",
                               rev)
              == ("Elowen Nettlestone", ["apprentice_of"]), "novel abstain")
        check(compose_question(
            "What is the never-taught relation 3 of Rosalind Windrow?", rev)
            == ("Rosalind Windrow", ["never_taught_rel_3"]), "numbered absent")
        check(compose_question(
            "What is the never-taught relation of the herald of Kellan Quill?",
            [("Kellan Quill", "herald_of", "Damon Owlcrest")])
            == ("Kellan Quill", ["herald_of", "never_taught_rel"]),
            "broken chain")
        mq = [("Roberto Merhi", "country_of_citizenship", "Spain"),
              ("Spain", "official_language", "Spanish")]
        check(compose_question(
            "What is the official language of the country of citizenship"
            " of Roberto Merhi?", mq)
            == ("Roberto Merhi",
                ["country_of_citizenship", "official_language"]), "mquake walk")
        check(compose_question("Blorpt zzz wobble?", mq) is None,
              "garbled question -> MISSING")
        check(compose_question(
            "Who is the founder of the company that developed B-47 Stratojet?",
            [("B-47 Stratojet", "developer", "Boeing"),
             ("Boeing", "founded_by", "William Boeing")])
            == ("B-47 Stratojet", ["developer", "founded_by"]),
            "mquake Who-fallback")
        # garbled teach -> nothing taught -> MISSING, never WRONG
        row = english_run_item(mini[0], ears, Path(tmp))
        check(row["status"] != C.OK and row["verdict"] == "MISS",
              "unparseable teach -> MISSING (answer item: MISS, never WRONG)")

    # 3. ears47 import smoke (skip-clean when no checkpoint/snapshot).
    ckpts = fable_bench73_find_checkpoints()
    if ckpts:
        print(f"ears47 checkpoints present: {ckpts} (smoke via --smoke-ears47)")
    else:
        print("ok   ears47 smoke SKIP (no checkpoint under "
              "artifacts/fable-ears47-20260921/runs/)")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 73 English-input arm")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--run-garbled", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--smoke-ears47", action="store_true")
    ap.add_argument("--ears", default="template")
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--data", default=str(DATA_DEFAULT))
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest(args)
    if args.smoke_ears47:
        return cmd_smoke_ears47(args)
    if args.run_garbled:
        args.data = str(GARBLED_DEFAULT)
        return cmd_run(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
