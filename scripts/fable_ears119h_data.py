#!/usr/bin/env python3
"""Exp 119h PREP — varied-shape occupation supervision data builder (Muse).

    python fable_ears119h_data.py --audit --snapshot <scibert>
    python fable_ears119h_data.py --build-pool OUT.jsonl --snapshot <scibert>  # BensPC

THE ONE CHANGE vs exp 119g (data only; model, recipe, seeds, K/FLOOR, scorer
logic unchanged): the 5,000 synthetic occupation rows no longer use 119f's two
past-tense templates. Each generated sentence varies the shape, and EVERY fact
the sentence states is labelled, one row per fact sharing the same text:

  shape draws (deterministic RNG stream; target frequencies in TARGET_SHAPE,
  measured frequencies printed by --audit):
    is/was ............ ~50/50 overall ("was" whenever a death date is
                        present; "is" favoured 70/30 elsewhere to compensate)
    bracket ........... ~60%: "(born D Month YYYY)", "(born YYYY)",
                        "(born D Month YYYY in PLACE)",
                        "(D Month YYYY - D Month YYYY)",
                        "(YYYY-YYYY)", "(YYYY-YYYY)"
    retired/former/professional before the job ... ~15%
    nationality demonym before the job .......... ~85%
    job list "JOB1 and JOB2" / "JOB1, JOB2 and JOB3" .. ~30%
    first job single- vs multi-word ............. ~65/35
  facts per sentence (relation names are D.CLASSES names, all registered):
    occupation (always; object = FIRST job span only, deterministic target),
    country of citizenship (the demonym span; only because the pool's own
      WebRED rows label citizenship on demonyms by majority — see
      count_citizenship_convention; if WebRED never used demonyms we would
      emit no citizenship row),
    date of birth / date of death (the date spans as written),
    place of birth (PLACE, only in the "born ... in PLACE" shape).
  spans, dir and the gold47 format are exactly as in 119f occ_rows; the text
  under every span is asserted equal to the intended string at build time.

Pool mechanics are 119f verbatim: the generator returns EXACTLY 5,000 rows
which replace the same 5,000 STATE slots 1:1, so pool size, kept total and
steps (8838) are unchanged (identity gates in build_pool).

Fictional person names only (119f's FIRST x LAST banks, procedurally paired).
Jobs/demonyms/places/months are written down below (generic English words,
multi-word jobs added: film director, rugby player, television presenter,
civil engineer, ...). NO sentence, name, or value is copied from
data/open/reading94 or data/open/reading94b: the novelty check asserts zero
normalized-sentence overlap and zero name-substring hits against
data/open/reading94/panel.jsonl (the OLD panel; descriptive-only use, never
training/tuning). The registered panel data/open/reading94b/panel.jsonl is
NEVER opened here (path only). The person is taken from the gold subj span
(119f's split on " was " breaks for "is" sentences).

Additive only: fable_ears47_data / fable_ears119b_data / fable_ears119f_data
imported read-only; 119f's module is reused for everything except occ_rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402  (read-only reuse)
import fable_ears119b_data as B  # noqa: E402  (REMAP + lengthen + MAX override)
import fable_ears119f_data as F  # noqa: E402  (FIRST/LAST/DEMONYMS/PROFESSIONS)

REPO = Path(__file__).resolve().parent.parent
PANEL94 = REPO / "data" / "open" / "reading94" / "panel.jsonl"
# REGISTERED panel (labelled by another agent): referenced by path only.
PANEL94B = REPO / "data" / "open" / "reading94b" / "panel.jsonl"

N_REPLACE = F.N_REPLACE
assert N_REPLACE == 5000, N_REPLACE
RNG_OCC = 11980  # occupation-row content stream (deterministic, cross-machine)

# Target shape frequencies (design values; --audit prints the measured ones).
TARGET_SHAPE = {
    "is_was": "50/50 (was whenever a death date is present)",
    "bracket": 0.60,
    "modifier_retired_former_professional": 0.15,
    "demonym": 0.85,
    "job_list_2_or_3": 0.30,
    "multiword_first_job": 0.35,
}

OCC = "occupation"
CIT = "country of citizenship"
DOB = "date of birth"
DOD = "date of death"
POB = "place of birth"
for _r in (OCC, CIT, DOB, DOD, POB):
    assert _r in D.CLASSES["classes"], _r

# Multi-word jobs (added for 119h; generic English nouns, written down here).
JOBS_MULTI = (
    "film director", "rugby player", "television presenter", "civil engineer",
    "football player", "basketball player", "tennis player", "cricket player",
    "baseball player", "race car driver", "fashion designer", "graphic designer",
    "interior designer", "art director", "music director", "news anchor",
    "talk show host", "radio presenter", "theatre director", "stage actor",
    "voice actor", "film critic", "art critic", "book editor",
    "foreign correspondent", "war correspondent", "staff writer",
    "research scientist", "data scientist", "computer scientist",
    "social worker", "police officer", "military officer", "naval officer",
    "flight attendant", "train conductor", "bus driver", "taxi driver",
    "truck driver", "construction worker", "factory worker", "office clerk",
    "bank clerk", "opera singer", "ballet dancer", "primary teacher",
    "software engineer", "mechanical engineer", "electrical engineer",
    "general practitioner", "army officer", "fire chief",
)
JOBS_ALL = F.PROFESSIONS + JOBS_MULTI

MODIFIERS = ("retired", "former", "professional")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

# Fictional birthplaces (invented here; never panel values).
PLACES = (
    "Emberford", "Foxhollow", "Grimbleton", "Halloway", "Inkford",
    "Larkfield", "Mossgrove", "Nettleford", "Oakhollow", "Puddleford",
    "Quillford", "Ravensford", "Stoneford", "Thornford", "Umberford",
    "Vexford", "Woolford", "Yarrowford", "Ashcombe", "Brambleford",
    "Cinderford", "Dunford", "Elderford", "Fernford",
)

# Sovereign-state names (written down here; used ONLY to classify the pool's
# own WebRED citizenship objects as demonym-vs-country for the convention
# count — never for generation).
COUNTRIES = {
    "united states", "u.s.", "u.s.a.", "us", "usa", "america",
    "united kingdom", "uk", "england", "france", "germany", "spain",
    "italy", "russia", "china", "japan", "brazil", "canada", "australia",
    "ireland", "scotland", "wales", "netherlands", "holland", "sweden",
    "norway", "denmark", "finland", "poland", "greece", "turkey", "egypt",
    "nigeria", "kenya", "mexico", "argentina", "chile", "peru", "colombia",
    "korea", "south korea", "vietnam", "thailand", "indonesia", "philippines",
    "pakistan", "new zealand", "ukraine", "israel", "portugal", "belgium",
    "austria", "hungary", "czech republic", "romania", "bulgaria", "serbia",
    "croatia", "cuba", "ghana", "ethiopia", "morocco", "algeria",
    "saudi arabia", "iraq", "iran", "lebanon", "syria", "afghanistan",
    "nepal", "taiwan", "singapore", "malaysia", "cambodia", "mongolia",
    "iceland", "jamaica", "soviet union", "yugoslavia", "czechoslovakia",
}
# Common demonyms beyond 119f's 40 (same use: convention count only).
DEMONYM_EXTRA = {
    "swiss", "soviet", "guatemalan", "ukrainian", "israeli", "portuguese",
    "belgian", "austrian", "hungarian", "czech", "slovak", "romanian",
    "bulgarian", "serbian", "croatian", "cuban", "ghanaian", "ethiopian",
    "moroccan", "algerian", "saudi", "iraqi", "iranian", "lebanese",
    "syrian", "afghan", "nepali", "taiwanese", "singaporean", "malaysian",
    "cambodian", "mongolian", "icelandic", "jamaican", "slovenian",
    "lithuanian", "latvian", "estonian", "kurdish", "palestinian",
    "new zealander", "soviet",
}

_CONVENTION_CACHE: dict | None = None


def count_citizenship_convention() -> dict:
    """How the pool's own WebRED rows label country of citizenship objects.

    Reads data/open/webred/frames/train.jsonl (training data, never a reading
    panel). Objects matching demonym words vs sovereign-state names are
    counted; the majority decides the span convention for our citizenship
    rows. Cached (one pass over 81k rows per process).
    """
    global _CONVENTION_CACHE
    if _CONVENTION_CACHE is not None:
        return _CONVENTION_CACHE
    dem = {d.casefold() for d in F.DEMONYMS} | set(DEMONYM_EXTRA)
    n_dem = n_cty = n_other = 0
    ex_dem: list[str] = []
    ex_cty: list[str] = []
    for row in D.webred_pool_rows():
        if row["relation"] != CIT or not row["positive"]:
            continue
        obj = row["text"][row["obj_chars"][0]:row["obj_chars"][1]]
        key = obj.casefold().strip().rstrip(".")
        if key in dem:
            n_dem += 1
            if len(ex_dem) < 5:
                ex_dem.append(obj)
        elif key in COUNTRIES:
            n_cty += 1
            if len(ex_cty) < 5:
                ex_cty.append(obj)
        else:
            n_other += 1
    out = {"citizenship_positives": n_dem + n_cty + n_other,
           "demonym_objects": n_dem, "country_objects": n_cty,
           "other_objects": n_other, "example_demonyms": ex_dem,
           "example_countries": ex_cty,
           "on_demonym": n_dem > n_cty,
           "never_demonym": n_dem == 0}
    _CONVENTION_CACHE = out
    return out


def _article(word: str) -> str:
    return "an" if word[0] in "AEIOUaeiou" else "a"


def _pick_job(rng: random.Random, ban: set[str]) -> str:
    for _ in range(100):
        pool = JOBS_MULTI if rng.random() < TARGET_SHAPE["multiword_first_job"] \
            else F.PROFESSIONS
        job = pool[rng.randrange(len(pool))]
        if job not in ban:
            return job
    job = F.PROFESSIONS[rng.randrange(len(F.PROFESSIONS))]
    return job


def _date(rng: random.Random, year_only: bool) -> str:
    y = rng.randrange(1820, 2001)
    if year_only:
        return str(y)
    d = rng.randrange(1, 29)
    m = MONTHS[rng.randrange(len(MONTHS))]
    return f"{d} {m} {y}"


def _make_sentence(rng: random.Random, person: str,
                   stats: dict) -> tuple[str, list[tuple[str, str]]]:
    """One varied-shape sentence + its (relation, object-string) facts."""
    text = person
    facts: list[tuple[str, str, int, int]] = []  # (rel, obj, s, e)

    # Bracket (~60%) and the dates/place it states.
    dob_s = dod_s = pob_s = ""
    form = ""
    if rng.random() < TARGET_SHAPE["bracket"]:
        form = ("born_dmy", "born_y", "born_dmy_place",
                "span_dmy", "span_y_en", "span_y_hy")[rng.randrange(6)]
        stats["bracket_" + form] += 1
        stats["bracket_any"] += 1
        if form in ("born_dmy", "born_dmy_place"):
            dob_s = _date(rng, False)
            inside = f"born {dob_s}"
            if form == "born_dmy_place":
                pob_s = PLACES[rng.randrange(len(PLACES))]
                inside += f" in {pob_s}"
        elif form == "born_y":
            dob_s = _date(rng, True)
            inside = f"born {dob_s}"
        elif form == "span_dmy":
            dob_s = _date(rng, False)
            dod_s = _date(rng, False)
            while dod_s == dob_s:
                dod_s = _date(rng, False)
            inside = f"{dob_s} - {dod_s}"
        elif form == "span_y_en":
            dob_s = _date(rng, True)
            dod_s = _date(rng, True)
            while dod_s == dob_s:
                dod_s = _date(rng, True)
            inside = f"{dob_s}\u2013{dod_s}"
        else:
            dob_s = _date(rng, True)
            dod_s = _date(rng, True)
            while dod_s == dob_s:
                dod_s = _date(rng, True)
            inside = f"{dob_s}-{dod_s}"
        b0 = len(text) + 2  # after " ("
        text += f" ({inside})"
        if dob_s:
            s = b0 + inside.index(dob_s)
            facts.append((DOB, dob_s, s, s + len(dob_s)))
        if dod_s:
            s = b0 + inside.index(dod_s, inside.index(dob_s) + len(dob_s))
            facts.append((DOD, dod_s, s, s + len(dod_s)))
        if pob_s:
            s = b0 + inside.index(pob_s)
            facts.append((POB, pob_s, s, s + len(pob_s)))
    else:
        stats["bracket_none"] += 1

    # is/was: "was" whenever a death date is present; elsewhere "is" is
    # favoured 70/30 so the overall mix stays about 50/50 (death brackets
    # alone force ~30% "was").
    if dod_s:
        iswas = "was"
    else:
        iswas = "is" if rng.random() < 0.70 else "was"
    stats["is" if iswas == "is" else "was"] += 1

    # Nationality (~85%), modifier (~15%), jobs (list ~30%).
    nat = F.DEMONYMS[rng.randrange(len(F.DEMONYMS))] \
        if rng.random() < TARGET_SHAPE["demonym"] else ""
    if nat:
        stats["demonym"] += 1
    mod = MODIFIERS[rng.randrange(len(MODIFIERS))] \
        if rng.random() < TARGET_SHAPE["modifier_retired_former_professional"] \
        else ""
    if mod:
        stats["modifier"] += 1
    ban: set[str] = set()
    job1 = _pick_job(rng, ban)
    ban.add(job1)
    if " " in job1:
        stats["multiword_job1"] += 1
    jobs = [job1]
    rj = rng.random()
    if rj < TARGET_SHAPE["job_list_2_or_3"] / 2:
        jobs.append(_pick_job(rng, ban))
        stats["job_list_2"] += 1
    elif rj < TARGET_SHAPE["job_list_2_or_3"]:
        jobs.append(_pick_job(rng, ban))
        ban.add(jobs[-1])
        jobs.append(_pick_job(rng, ban))
        stats["job_list_3"] += 1
    else:
        stats["job_single"] += 1

    first_word = nat or mod or jobs[0]
    text += f" {iswas} {_article(first_word)} "
    if nat:
        s = len(text)
        text += nat + " "
        facts.append((CIT, nat, s, s + len(nat)))
    if mod:
        text += mod + " "
    if len(jobs) == 1:
        phrase = jobs[0]
    elif len(jobs) == 2:
        phrase = f"{jobs[0]} and {jobs[1]}"
    else:
        phrase = f"{jobs[0]}, {jobs[1]} and {jobs[2]}"
    s = len(text)
    text += phrase + "."
    # Occupation's object is the FIRST job span only (deterministic target).
    facts.append((OCC, job1, s, s + len(job1)))
    # Occupation row first (matches 119f row order habits), rest as stated.
    facts.sort(key=lambda t: 0 if t[0] == OCC else 1)
    return text, [(rel, text[s:e]) for rel, _o, s, e in facts]


def _rows_of_sentence(text: str, person: str,
                      facts: list[tuple[str, str]]) -> list[dict]:
    """One row per fact sharing the same text (gold47 format as 119f)."""
    subj = [0, len(person)]
    assert text[:len(person)] == person, text
    out = []
    for rel, obj in facts:
        k = text.index(obj, len(person))
        gold = {"act": "STATE", "rel": rel,
                "subj": list(subj), "obj": [k, k + len(obj)],
                "dir": D._dir_of(subj, [k, k + len(obj)]), "rep": True}
        assert gold["dir"] == D.DIR_FORWARD
        assert text[gold["subj"][0]:gold["subj"][1]] == person, text
        assert text[gold["obj"][0]:gold["obj"][1]] == obj, (text, obj)
        out.append({"text": text, "source": "synth-occ", "gold47": gold})
    return out


OCC_STATS: dict = {}


def generate(rng: random.Random | None = None) -> tuple[list[dict], dict]:
    """EXACTLY N_REPLACE rows: whole-sentence groups, padded with 1-row fills."""
    rng = rng if rng is not None else random.Random(RNG_OCC)
    conv = count_citizenship_convention()
    assert conv["on_demonym"], \
        f"pool WebRED labels citizenship on demonyms={conv['demonym_objects']} " \
        f"vs countries={conv['country_objects']}; generator needs the " \
        "demonym convention (else emit no citizenship row)"
    stats: dict = {"bracket_any": 0, "bracket_none": 0, "is": 0, "was": 0,
                   "demonym": 0, "modifier": 0, "multiword_job1": 0,
                   "job_single": 0, "job_list_2": 0, "job_list_3": 0,
                   "sentences": 0, "pad_singles": 0}
    for _f in ("born_dmy", "born_y", "born_dmy_place",
               "span_dmy", "span_y_en", "span_y_hy"):
        stats["bracket_" + _f] = 0
    pairs = [(a, b) for a in F.FIRST for b in F.LAST]
    assert len(pairs) >= N_REPLACE, "name banks too small"
    groups: list[list[dict]] = []
    total = 0
    pi = 0
    while total < N_REPLACE:
        person = f"{pairs[pi][0]} {pairs[pi][1]}"
        pi += 1
        text, facts = _make_sentence(rng, person, stats)
        facts = [(rel, obj) for rel, obj in facts
                 if not (rel == CIT and not conv["on_demonym"])]
        groups.append(_rows_of_sentence(text, person, facts))
        total += len(groups[-1])
        stats["sentences"] += 1
    while groups and total - len(groups[-1]) >= N_REPLACE:
        total -= len(groups.pop())
        stats["sentences"] -= 1
    # Exact fill with single-fact occupation-only sentences (1 row each).
    while total < N_REPLACE:
        person = f"{pairs[pi][0]} {pairs[pi][1]}"
        pi += 1
        iswas = "is" if rng.random() < 0.5 else "was"
        job = _pick_job(rng, set())
        text = f"{person} {iswas} {_article(job)} {job}."
        groups.append(_rows_of_sentence(text, person, [(OCC, job)]))
        total += 1
        stats["sentences"] += 1
        stats["pad_singles"] += 1
        stats["bracket_none"] += 1
        stats["is" if iswas == "is" else "was"] += 1
        stats["job_single"] += 1
        if " " in job:
            stats["multiword_job1"] += 1
    rows = [r for g in groups for r in g]
    assert len(rows) == N_REPLACE, len(rows)
    # Every row re-asserted: span text, forward dir, registered relation.
    for r in rows:
        g = r["gold47"]
        assert g["act"] == "STATE" and g["rep"] is True
        assert g["rel"] in D.CLASSES["classes"], g["rel"]
        assert r["text"][g["subj"][0]:g["subj"][1]]
        assert r["text"][g["obj"][0]:g["obj"][1]]
        assert g["dir"] == D.DIR_FORWARD
    per_rel: dict[str, int] = {}
    for r in rows:
        per_rel[r["gold47"]["rel"]] = per_rel.get(r["gold47"]["rel"], 0) + 1
    stats["rows"] = len(rows)
    stats["rows_per_relation"] = per_rel
    stats["citizenship_convention"] = {
        "demonym_objects": conv["demonym_objects"],
        "country_objects": conv["country_objects"],
        "other_objects": conv["other_objects"]}
    global OCC_STATS
    OCC_STATS = dict(stats)
    return rows, stats


def occ_rows(rng: random.Random | None = None) -> list[dict]:
    """Drop-in replacement for 119f occ_rows: EXACTLY N_REPLACE rows."""
    rows, _ = generate(rng)
    return rows


def rows_sha(rows: list[dict]) -> str:
    h = hashlib.sha256(b"fable-ears119h/occ-rows/1")
    for r in rows:
        h.update(json.dumps(r, sort_keys=True, ensure_ascii=False).encode())
        h.update(b"\n")
    return h.hexdigest()


def norm_sent(s: str) -> str:
    return re.sub(r"\s+", " ", s.casefold()).strip()


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def check_novelty(rows: list[dict]) -> dict:
    """Overlap check vs the OLD panel only (descriptive use, never training).

    The person is taken from the gold subj span (works for "is" and "was"
    sentences alike). Asserts: zero normalized-sentence overlap; zero
    first/last-name substring hits (casefold). The registered reading94b
    panel is NEVER opened.
    """
    panel = load_jsonl(PANEL94)
    psent = {norm_sent(r["sentence"]) for r in panel}
    blob = " ||| ".join(norm_sent(r["sentence"]) for r in panel)
    seen: dict[str, dict] = {}
    for r in rows:
        g = r["gold47"]
        person = r["text"][g["subj"][0]:g["subj"][1]]
        seen.setdefault(norm_sent(r["text"]), person)
    sent_overlap = sorted(set(seen) & psent)
    name_hits = set()
    for person in seen.values():
        if norm_sent(person) in blob:
            name_hits.add(person)
        for tok_name in person.split(" "):
            if tok_name.casefold() in blob:
                name_hits.add(tok_name)
    pvals = set()
    for r in panel:
        for t in r.get("triples", []):
            pvals.add(norm_sent(str(t.get("object", ""))))
    oval = set()
    for r in rows:
        g = r["gold47"]
        oval.add(norm_sent(r["text"][g["obj"][0]:g["obj"][1]]))
    return {"panel94_sentences": len(psent),
            "occ_sentences": len(seen),
            "occ_rows": len(rows),
            "sentence_overlap": sent_overlap,
            "name_hits": sorted(name_hits),
            "value_overlap": sorted(oval & pvals)}


def synth_pool_rows_long_119h(tok) -> list[dict]:
    """119b's exact 60k lengthened synth rows with the 119h replacement.

    First N_REPLACE STATE rows are replaced 1:1 with the varied-shape
    occupation rows, so the pool stays 60,000 synth rows (pool size, steps,
    recipe unchanged).
    """
    base = B.synth_pool_rows_long(tok)
    assert len(base) == D.POOL_SYNTH, len(base)
    state_idx = [i for i, r in enumerate(base)
                 if r["gold47"]["act"] == "STATE"]
    assert len(state_idx) >= N_REPLACE, f"only {len(state_idx)} STATE rows"
    occ = occ_rows()
    for k, i in enumerate(state_idx[:N_REPLACE]):
        base[i] = occ[k]
    return base


def audit(snapshot: str) -> dict:
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    conv = count_citizenship_convention()
    print(json.dumps({"citizenship_convention": conv}, indent=1))
    rows, stats = generate()
    assert len(rows) == N_REPLACE
    nov = check_novelty(rows)
    assert nov["sentence_overlap"] == [], nov["sentence_overlap"][:5]
    assert nov["name_hits"] == [], nov["name_hits"][:10]
    drops = flagged = 0
    for r in rows[:500]:
        e = D.encode_row(r, tok)
        if e is None:
            drops += 1
        elif any(e["flags"]):
            flagged += 1
    assert drops == 0 and flagged == 0, (drops, flagged)
    base = D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))
    assert len(base) == D.POOL_SYNTH
    n_state = sum(1 for r in base if r["gold47"]["act"] == "STATE")
    assert n_state >= N_REPLACE, n_state
    out = {
        "n_replace": N_REPLACE,
        "shape_targets": TARGET_SHAPE,
        "shape_measured": {k: v for k, v in stats.items()
                           if k != "rows_per_relation"
                           and k != "citizenship_convention"},
        "rows_per_relation": stats["rows_per_relation"],
        "rows_sha": rows_sha(rows),
        "novelty": {**nov, "sentence_overlap": [],
                     "value_overlap": nov["value_overlap"]},
        "encode_sample": {"n": 500, "drops": drops, "flagged": flagged},
        "base_state_targets": n_state,
    }
    print(json.dumps(out, indent=1))
    # 20 example sentences with their rows.
    shown = 0
    last = None
    for r in rows:
        if r["text"] != last:
            last = r["text"]
            shown += 1
            if shown > 20:
                break
            print(f"--- {last}")
        g = r["gold47"]
        print(f"    {g['rel']}: {r['text'][g['obj'][0]:g['obj'][1]]!r}")
    return out


def build_pool(out_path: str, snapshot: str) -> None:
    """Rebuild the pool with the 1:1 varied-shape replacement (runs on BensPC)."""
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    kept = drop = synth_n = occ_n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in synth_pool_rows_long_119h(tok):
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
            synth_n += 1
            occ_n += (row.get("source") == "synth-occ")
        for row in D.webred_pool_rows():
            row = dict(row)
            row["gold47"] = B.remap_gold(row["gold47"])
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
    import math as _m
    steps = 2 * _m.ceil(kept / 32)
    print(f"pool119h kept={kept} dropped={drop} synth={synth_n} occ={occ_n} "
          f"webred={kept - synth_n} steps={steps} -> {out_path}")
    assert synth_n == D.POOL_SYNTH, f"synth {synth_n} != 60000"
    assert occ_n == N_REPLACE, f"occ {occ_n} != {N_REPLACE}"
    assert kept >= 140903, f"kept {kept} < 47's 140903"
    assert drop <= 614, f"dropped {drop} > 47's 614"
    assert 141377 <= kept <= 141408, f"kept {kept} changes step count"
    assert steps == 8838, f"steps {steps} != 8838"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--build-pool", default=None)
    ap.add_argument("--snapshot", default=None)
    a = ap.parse_args()
    if a.audit:
        assert a.snapshot, "--audit needs --snapshot"
        audit(a.snapshot)
    if a.build_pool:
        assert a.snapshot, "--build-pool needs --snapshot"
        build_pool(a.build_pool, a.snapshot)


if __name__ == "__main__":
    main()
