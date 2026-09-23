#!/usr/bin/env python3
"""nb-320 workload generator (report-only baseline, seed 3200).

Writes /tmp/nb320/workload-<N>.jsonl. Deterministic: random.Random(3200).

N = total operations: 85% teach, 10% correction, 5% forget (in that phase
order). FACT writes (assert_fact calls) = 95% of N. Relation/entity setup
events are extra. No agent code is touched; this file only writes data.

Raw sentences come from the o0b generator rows (builder-outbox branch):
family "tell", act "STATE", count 1, one fact, mode "ASSERT", owner_kind
"NAME". The row's turn text is reused with the owner span and value span
spliced out for this operation's subject name and value text. Templates are
grouped by relation; each op uses a template of its own relation.

Line format: header line first, then one line per op.
  header: {"type":"header","seed":3200,"N":N,"sizes":{...},
           "functional":[...30],"multivalued":[...47],
           "names":[...N/10...],
           "o0b":{"files":[...],"filter":"tell/STATE/count1/1fact/ASSERT/ownerNAME",
                  "templates":3754,"sha256":{...}}}
  op: {"type":"op","i":idx,"kind":"teach|correct|forget",
       "subject":name_idx,"relation":rel,
       "value":{"entity":name_idx}|{"literal":text},
       "raw":sentence,"correction":bool,"event_id":str,
       "target":opidx|null}

Corrections/forgets reference the taught fact by op index ("target"); the
replayer maps op index -> backend fact_id, so the file is backend-agnostic.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

SEED = 3200

# 30 functional relations (attribute-like, one value per subject).
FUNCTIONAL = [
    "title", "occupation", "employer", "capital", "place_of_birth",
    "work_location", "school", "country", "city", "hometown",
    "home", "favorite_book", "hobby", "color", "car",
    "favorite_season", "favorite_sport", "instrument", "favorite_food",
    "favorite_color", "nickname", "favorite_subject", "allergy", "boss",
    "landlord", "coach", "doctor", "dentist", "vet", "mentor",
]

# Fictional name syllables (invented; no real people).
_FIRST_A = ["Tal", "Bren", "Cor", "Dal", "Fen", "Gal", "Har", "Jel",
            "Kel", "Lor", "Mal", "Nel", "Pel", "Ral", "Sel", "Tor",
            "Vel", "Wen", "Yar", "Zel", "Bram", "Drus", "Frel", "Grim",
            "Hald", "Keth", "Marn", "Rusk", "Sarn", "Teth", "Varn",
            "Drel", "Galt", "Hesk", "Jor", "Karn", "Leth", "Mald",
            "Norr", "Prent", "Quil", "Rath", "Seld", "Tren", "Vosk",
            "Wren", "Yeld", "Zarn", "Belm", "Cal", "Dorn", "Eld", "Farn"]
_FIRST_B = ["vo", "a", "i", "or", "en", "is", "al", "eth"]
_LAST_A = ["Bren", "Corv", "Dall", "Fenn", "Garr", "Hall", "Jenn",
           "Kell", "Lann", "Merr", "Nall", "Perr", "Renn", "Sell",
           "Tann", "Vell", "Warr", "Yell", "Zann", "Dorr", "Foll",
           "Genn", "Harr", "Joll", "Karr", "Lorr", "Moll", "Nerr",
           "Poll", "Rall", "Serr", "Toll"]
_LAST_B = ["ick", "or", "en", "ath", "ow", "ey", "is", "an", "er",
           "ald", "eth", "in", "os", "un", "ark", "elm", "il", "urn",
           "ash", "oom"]

# Fictional literal words (place/thing-like).
_LIT_A = ["Brel", "Tor", "Sal", "Kel", "Mar", "Fen", "Gal", "Har",
          "Del", "Nor", "Pel", "Ril", "Sul", "Vel", "Wyn", "Thal",
          "Brin", "Cor", "Drin", "El", "Fal", "Gren", "Hol", "Ith"]
_LIT_B = ["mar", "holm", "way", "ford", "mere", "bank", "field",
          "wick", "stead", "moor", "dale", "brook"]

CORRECTION_OPENERS = [
    "Actually, ", "No wait, ", "Sorry, ", "Let me fix that: ",
    "Correction: ", "Hmm, actually ", "I misspoke, ", "To be exact, ",
    "Scratch that, ", "Rather, ",
]


def build_names(count: int) -> list[str]:
    firsts = [a + b for a in _FIRST_A for b in _FIRST_B]
    lasts = [a + b for a in _LAST_A for b in _LAST_B]
    assert len(firsts) * len(lasts) >= count, "name pool too small"
    names, seen = [], set()
    for f in firsts:
        for l in lasts:
            name = f"{f} {l}"
            if name not in seen:
                seen.add(name)
                names.append(name)
            if len(names) >= count:
                return names
    return names


def build_literals() -> list[str]:
    return [a + b for a in _LIT_A for b in _LIT_B]


def load_templates(paths: list[str]) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Return ({relation: [template,...]}, {path: sha256})."""
    by_rel: dict[str, list[dict]] = defaultdict(list)
    sums = {}
    for path in paths:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        sums[path] = h.hexdigest()
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("family") != "tell":
                    continue
                if row.get("act") != "STATE" or row.get("count") != 1:
                    continue
                facts = row.get("facts", [])
                if len(facts) != 1 or facts[0].get("mode") != "ASSERT":
                    continue
                world_facts = row.get("world", {}).get("facts", [])
                if not world_facts or world_facts[0].get("owner_kind") != "NAME":
                    continue
                fact = facts[0]
                if "owner" not in fact or "value_span" not in fact:
                    continue
                by_rel[fact["relation"]].append({
                    "turn": row["turn"],
                    "owner": tuple(fact["owner"]),
                    "value_span": tuple(fact["value_span"]),
                })
    return dict(by_rel), sums


def splice(turn: str, owner: tuple[int, int], vspan: tuple[int, int],
           subject: str, value: str) -> str:
    """Replace owner/value spans with subject/value text (any span order)."""
    reps = sorted([(owner[0], owner[1], subject),
                   (vspan[0], vspan[1], value)], key=lambda r: -r[0])
    out = turn
    for start, end, text in reps:
        out = out[:start] + text + out[end:]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="nb-320 workload generator")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--o0b", nargs=2, required=True, metavar="GZ",
                        help="two o0b train .jsonl.gz files")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    n = args.n
    rng = random.Random(SEED)
    templates, sums = load_templates(list(args.o0b))
    n_templates = sum(len(v) for v in templates.values())
    print(f"templates kept: {n_templates} over {len(templates)} relations",
          flush=True)
    assert len(FUNCTIONAL) == 30
    assert set(FUNCTIONAL) <= set(templates), "functional rel missing templates"
    multivalued = sorted(set(templates) - set(FUNCTIONAL))
    relations = sorted(templates)

    n_people = n // 10
    names = build_names(n_people)
    assert len(set(names)) == n_people, "names must be unique"
    literals = build_literals()

    n_teach = int(0.85 * n)
    n_correct = int(0.10 * n)
    n_forget = n - n_teach - n_correct

    ops = []
    # live ground truth at generation time (mirrors replay)
    active: dict[int, dict] = {}          # opidx -> fact info
    func_pair: dict[tuple[int, str], int] = {}  # (subj,rel) -> opidx (functional)
    pair_ever: dict[tuple[int, str], set[str]] = defaultdict(set)

    def fresh_value(subj: int, rel: str, is_entity: bool) -> tuple[dict, str]:
        for _ in range(100):
            if is_entity:
                other = rng.randrange(n_people)
                if other == subj:
                    continue
                text = names[other]
                val = {"entity": other}
            else:
                text = rng.choice(literals)
                val = {"literal": text}
            if text not in pair_ever[(subj, rel)]:
                return val, text
        raise RuntimeError("value pool exhausted")

    def pick_template(rel: str) -> dict:
        return rng.choice(templates[rel])

    # ---- phase 1: teaches ----
    for i in range(n_teach):
        for _ in range(200):
            subj = rng.randrange(n_people)
            rel = rng.choice(relations)
            if rel in FUNCTIONAL and (subj, rel) in func_pair:
                continue
            break
        else:
            raise RuntimeError("pair pool exhausted")
        is_entity = rng.random() < 0.5
        val, text = fresh_value(subj, rel, is_entity)
        tpl = pick_template(rel)
        raw = splice(tpl["turn"], tpl["owner"], tpl["value_span"],
                     names[subj], text)
        op = {"type": "op", "i": len(ops), "kind": "teach",
              "subject": subj, "relation": rel, "value": val,
              "raw": raw, "correction": False,
              "event_id": f"nb320-{n}-op{len(ops):07d}", "target": None}
        pair_ever[(subj, rel)].add(text)
        active[len(ops)] = {"subject": subj, "relation": rel,
                            "text": text, "is_entity": is_entity,
                            "corrected": False}
        if rel in FUNCTIONAL:
            func_pair[(subj, rel)] = len(ops)
        ops.append(op)

    # ---- phase 2: corrections (active functional facts, new value) ----
    func_active = [oi for oi, f in active.items()
                   if f["relation"] in FUNCTIONAL]
    assert len(func_active) >= n_correct, "not enough functional facts"
    for _ in range(n_correct):
        oi = rng.choice(func_active)
        func_active.remove(oi)
        old = active.pop(oi)
        subj, rel = old["subject"], old["relation"]
        val, text = fresh_value(subj, rel, old["is_entity"])
        tpl = pick_template(rel)
        raw = (rng.choice(CORRECTION_OPENERS)
               + splice(tpl["turn"], tpl["owner"], tpl["value_span"],
                        names[subj], text))
        op = {"type": "op", "i": len(ops), "kind": "correct",
              "subject": subj, "relation": rel, "value": val,
              "raw": raw, "correction": True,
              "event_id": f"nb320-{n}-op{len(ops):07d}", "target": oi}
        pair_ever[(subj, rel)].add(text)
        active[len(ops)] = {"subject": subj, "relation": rel,
                            "text": text, "is_entity": old["is_entity"],
                            "corrected": True}
        func_pair[(subj, rel)] = len(ops)
        ops.append(op)

    # ---- phase 3: forgets (retract an active fact) ----
    live = list(active)
    assert len(live) >= n_forget, "not enough active facts"
    for _ in range(n_forget):
        oi = rng.choice(live)
        live.remove(oi)
        old = active.pop(oi)
        if old["relation"] in FUNCTIONAL:
            func_pair.pop((old["subject"], old["relation"]), None)
        ops.append({"type": "op", "i": len(ops), "kind": "forget",
                    "subject": old["subject"], "relation": old["relation"],
                    "value": None, "raw": None, "correction": False,
                    "event_id": f"nb320-{n}-op{len(ops):07d}",
                    "target": oi})

    assert len(ops) == n
    header = {"type": "header", "seed": SEED, "N": n,
              "sizes": {"teach": n_teach, "correct": n_correct,
                        "forget": n_forget, "fact_writes": n_teach + n_correct,
                        "people": n_people},
              "functional": FUNCTIONAL, "multivalued": multivalued,
              "names": names,
              "o0b": {"filter": "tell/STATE/count1/1fact/ASSERT/ownerNAME",
                      "templates": n_templates,
                      "sha256": {Path(p).name: s for p, s in sums.items()}}}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + "\n")
        for op in ops:
            fh.write(json.dumps(op, ensure_ascii=False) + "\n")

    kinds: dict[str, int] = defaultdict(int)
    for op in ops:
        kinds[op["kind"]] += 1
    print(f"wrote {out}: N={n} " + " ".join(f"{k}={v}" for k, v in sorted(kinds.items())),
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
