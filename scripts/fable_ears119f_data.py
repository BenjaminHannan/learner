#!/usr/bin/env python3
"""Exp 119f PREP — panel-shaped occupation supervision data builder (Muse).

    python fable_ears119f_data.py --audit --snapshot <scibert>
    python fable_ears119f_data.py --build-pool OUT.jsonl --snapshot <scibert>  # BensPC

THE ONE CHANGE vs exp 119b (plan: design/v3/30-modes/119f-ears-plan-muse.md):
training-data only. N_REPLACE lengthened synth rows whose gold act is STATE
are REPLACED (not added) 1:1 with panel-shaped occupation rows:
  "PERSON was a/an DEMONYM PROFESSION."
  "PERSON (YYYY-YYYY) was a/an DEMONYM PROFESSION and PROFESSION2."
gold = (STATE, occupation, person-span, profession-span). The demonym is a
distractor by construction (never the gold value). Everything else is 119b
verbatim: same REMAP, same MAX_LEN 192, same lengthening stream (RNG_LEN
11900), same WebRED rows, same pool size, same steps, same recipe.

Fictional person names only (FIRST x LAST banks below, procedurally paired).
Professions/demonyms come from the closed lists below, written down here.
NO sentence, name, or value is copied from data/open/reading94 or
data/open/reading94b: --audit asserts zero normalized-sentence overlap and
zero name-substring overlap against data/open/reading94/panel.jsonl
(DESCRIPTIVE-ONLY use: overlap check, never training/tuning). The registered
panel data/open/reading94b/panel.jsonl is NEVER opened here (path only).

Additive only: fable_ears47_data / fable_ears119b_data imported read-only.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402  (read-only reuse)
import fable_ears119b_data as B  # noqa: E402  (REMAP + lengthen + MAX override)

REPO = Path(__file__).resolve().parent.parent
PANEL94 = REPO / "data" / "open" / "reading94" / "panel.jsonl"
# REGISTERED panel (being labelled by another agent): referenced by path only.
PANEL94B = REPO / "data" / "open" / "reading94b" / "panel.jsonl"

N_REPLACE = 5000
RNG_OCC = 11950  # occupation-row content stream (deterministic, cross-machine)

# Closed profession list: bare-noun panel shapes (~60). Written down here;
# generic English nouns, never multi-word panel values.
PROFESSIONS = (
    "singer", "writer", "scholar", "lawyer", "painter", "poet",
    "actor", "doctor", "teacher", "farmer", "sailor", "soldier",
    "baker", "weaver", "tailor", "smith", "clerk", "nurse",
    "pilot", "dancer", "sculptor", "composer", "novelist", "journalist",
    "historian", "philosopher", "scientist", "chemist", "physicist", "astronomer",
    "biologist", "engineer", "architect", "judge", "mayor", "governor",
    "senator", "merchant", "banker", "chef", "gardener", "fisher",
    "miner", "carpenter", "potter", "cobbler", "shepherd", "hunter",
    "guard", "monk", "priest", "professor", "lecturer", "tutor",
    "musician", "violinist", "pianist", "guitarist", "photographer", "filmmaker",
    "director", "editor", "librarian", "curator", "translator", "diplomat",
    "detective", "officer", "captain",
)

# Closed demonym list (~40): distractors only, never the gold value.
DEMONYMS = (
    "American", "Indian", "French", "British", "German", "Italian",
    "Spanish", "Russian", "Chinese", "Japanese", "Brazilian", "Canadian",
    "Australian", "Irish", "Scottish", "Welsh", "Dutch", "Swedish",
    "Norwegian", "Danish", "Finnish", "Polish", "Greek", "Turkish",
    "Egyptian", "Nigerian", "Kenyan", "Mexican", "Argentine", "Chilean",
    "Peruvian", "Colombian", "Korean", "Vietnamese", "Thai", "Indonesian",
    "Filipino", "Pakistani", "Arab", "Persian",
)

# Fictional person-name banks (procedurally paired FIRST[i] + LAST[j]).
FIRST = (
    "Aldric", "Anselm",     "Beatrix", "Bramwell", "Casimir", "Cressida",
    "Corvin", "Delmar", "Delphine", "Dunstan", "Edric", "Elowen",
    "Emrys", "Fenwick",     "Garrick", "Godric", "Halvor", "Hestia",
    "Isolde", "Jorunn", "Kelda", "Kenelm", "Leofric", "Liora",
    "Maren", "Merritt", "Nerys", "Osric", "Oswin", "Perrin",
    "Quenby", "Ragnhild", "Roderick", "Rosalind", "Swithin", "Tancred",
    "Ulric", "Verity", "Wenna", "Wilmot", "Ysolde", "Zephyrin",
    "Aelfric", "Baldrick", "Celadine", "Diggory", "Eadric", "Fabiana",
    "Griselda", "Hadrian", "Imogen", "Jocelyn", "Kester", "Lavinia",
    "Mirabel", "Nathaniel", "Ottilie", "Pomeline", "Quiller", "Rowena",
    "Septimus", "Tilda", "Ursula", "Vesper", "Wulfric", "Xanthe",
)
LAST = (
    "Ashdown", "Blackmoor", "Broadbent", "Candlewick", "Deepwell", "Elmsworth",
    "Fairholm", "Grimshaw", "Hazelwood", "Ironmonger", "Kettleburn", "Larkspur",
    "Millbrook", "Netherfield", "Oxenham", "Plumstead", "Quickfall", "Ravenscar",
    "Stonebridge", "Thistledown", "Underbough", "Vexley", "Woolmer", "Yardley",
    "Zinckfield", "Appledore", "Barrowfield", "Cinderford", "Dunmore", "Eelmarsh",
    "Foxglove", "Gorsefield", "Heatherwick", "Inkwell", "Juniper", "Kestrel",
    "Lovelace", "Marshwood", "Nettlebed", "Oakhanger", "Piddlewick", "Quarrendon",
    "Rushmoor", "Saltmarsh", "Twigworth", "Umberleigh", "Vinehall", "Windrush",
    "Yaffle", "Zouch", "Aldercroft", "Brambletye", "Cuckmere", "Ditchling",
    "Emberley", "Firle", "Glynde", "Horsted", "Iford", "Jevington",
    "Kingston", "Litlington", "Milton", "Norton", "Offham", "Patcham",
    "Rottingdean", "Stanmer", "Telscombe", "Uckfield", "Wivelsfield", "Yapton",
    "Alciston", "Berwick", "Chalvington", "Denton", "Eastdean", "Folkington",
    "Heighton", "Isfield",
)

assert len(PROFESSIONS) >= 60, len(PROFESSIONS)
assert len(DEMONYMS) >= 40, len(DEMONYMS)
assert len(FIRST) * len(LAST) >= N_REPLACE, "name banks too small"


def _article(word: str) -> str:
    return "an" if word[0] in "AEIOUaeiou" else "a"


def occ_rows(rng: random.Random | None = None) -> list[dict]:
    """N_REPLACE panel-shaped occupation rows (deterministic)."""
    rng = rng if rng is not None else random.Random(RNG_OCC)
    pairs = [(a, b) for a in FIRST for b in LAST][:N_REPLACE]
    assert len(pairs) == N_REPLACE
    out = []
    for a, b in pairs:
        person = f"{a} {b}"
        dem = DEMONYMS[rng.randrange(len(DEMONYMS))]
        prof = PROFESSIONS[rng.randrange(len(PROFESSIONS))]
        if rng.random() < 0.30:
            prof2 = PROFESSIONS[rng.randrange(len(PROFESSIONS))]
            while prof2 == prof:
                prof2 = PROFESSIONS[rng.randrange(len(PROFESSIONS))]
            y1 = rng.randrange(1820, 1951)
            y2 = min(y1 + rng.randrange(25, 81), 2020)
            text = (f"{person} ({y1}-{y2}) was {_article(dem)} {dem} {prof}"
                    f" and {prof2}.")
        else:
            text = f"{person} was {_article(dem)} {dem} {prof}."
        subj = [0, len(person)]
        k = text.index(prof, len(person))
        obj = [k, k + len(prof)]
        gold = {"act": "STATE", "rel": "occupation",
                "subj": subj, "obj": obj,
                "dir": D._dir_of(subj, obj), "rep": True}
        assert gold["dir"] == D.DIR_FORWARD
        out.append({"text": text, "source": "synth-occ", "gold47": gold})
    return out


def norm_sent(s: str) -> str:
    return re.sub(r"\s+", " ", s.casefold()).strip()


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def check_novelty(rows: list[dict]) -> dict:
    """Overlap check vs the OLD panel only (descriptive use, never training).

    Asserts: zero normalized-sentence overlap; zero first/last-name substring
    overlap (casefold). The registered reading94b panel is NEVER opened.
    """
    panel = load_jsonl(PANEL94)
    psent = {norm_sent(r["sentence"]) for r in panel}
    blob = " ||| ".join(norm_sent(r["sentence"]) for r in panel)
    osent = {norm_sent(r["text"]) for r in rows}
    sent_overlap = sorted(osent & psent)
    name_hits = set()
    for r in rows:
        person = r["text"].split(" (")[0].split(" was ")[0]
        for tok_name in person.split(" "):
            if tok_name.casefold() in blob:
                name_hits.add(tok_name)
    # value check: gold value strings (bare professions) that appear as a full
    # panel gold object are reported (single common nouns; not a FAIL by itself).
    pvals = set()
    for r in panel:
        for t in r.get("triples", []):
            pvals.add(norm_sent(str(t.get("object", ""))))
    oval = {norm_sent(r["text"][r["gold47"]["obj"][0]:r["gold47"]["obj"][1]])
            for r in rows}
    val_overlap = sorted(oval & pvals)
    return {"panel94_sentences": len(psent),
            "occ_sentences": len(osent),
            "sentence_overlap": sent_overlap,
            "name_hits": sorted(name_hits),
            "value_overlap_single_nouns": val_overlap}


def synth_pool_rows_long_119f(tok) -> list[dict]:
    """119b's exact 60k lengthened synth rows with the ONE-CHANGE replacement.

    First N_REPLACE STATE rows are replaced 1:1 with occupation rows, so the
    pool stays 60,000 synth rows (pool size, steps, recipe unchanged).
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
    occ = occ_rows()
    assert len(occ) == N_REPLACE
    nov = check_novelty(occ)
    assert nov["sentence_overlap"] == [], nov["sentence_overlap"][:5]
    assert nov["name_hits"] == [], nov["name_hits"][:10]
    # encode sample: zero drops, zero flags (no hearsay/negation/hypo leak).
    drops = flagged = 0
    for r in occ[:500]:
        e = D.encode_row(r, tok)
        if e is None:
            drops += 1
        elif any(e["flags"]):
            flagged += 1
    assert drops == 0 and flagged == 0, (drops, flagged)
    # replacement targets exist (on the unlengthened base; lengthen keeps golds).
    base = D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))
    assert len(base) == D.POOL_SYNTH
    n_state = sum(1 for r in base if r["gold47"]["act"] == "STATE")
    assert n_state >= N_REPLACE, n_state
    out = {
        "n_replace": N_REPLACE,
        "professions": len(PROFESSIONS),
        "demonyms": len(DEMONYMS),
        "name_pairs": f"{len(FIRST)}x{len(LAST)}",
        "novelty": {**nov, "sentence_overlap": [],
                     "value_overlap_single_nouns": nov["value_overlap_single_nouns"]},
        "encode_sample": {"n": 500, "drops": drops, "flagged": flagged},
        "base_state_targets": n_state,
        "example": occ[0]["text"],
    }
    print(json.dumps(out, indent=1))
    return out


def build_pool(out_path: str, snapshot: str) -> None:
    """Rebuild the pool with the 1:1 occupation replacement (runs on BensPC)."""
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    kept = drop = synth_n = occ_n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in synth_pool_rows_long_119f(tok):
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
    print(f"pool119f kept={kept} dropped={drop} synth={synth_n} occ={occ_n} "
          f"webred={kept - synth_n} steps={steps} -> {out_path}")
    assert synth_n == D.POOL_SYNTH, f"synth {synth_n} != 60000"
    assert occ_n == N_REPLACE, f"occ {occ_n} != {N_REPLACE}"
    assert kept >= 140903, f"kept {kept} < 47's 140903"
    assert drop <= 614, f"dropped {drop} > 47's 614"
    # pool size, steps and recipe unchanged vs 119b (kept 141398 -> 8838 steps).
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
