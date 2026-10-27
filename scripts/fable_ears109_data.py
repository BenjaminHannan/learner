#!/usr/bin/env python3
"""Exp 109 PREP — real-text-supervision data builder (Muse).

    python fable_ears109_data.py --audit            # overlap + label-set + counts (no model)
    python fable_ears109_data.py --build-pool OUT.jsonl --snapshot <scibert>   # BensPC
    python fable_ears109_data.py --build-cal OUT.json                           # any machine
    python fable_ears109_data.py --write-alias OUT.json                        # any machine

Exp 47's sealed pool already mixed 60k synth + all WebRED train (PASSMARKS s6,
registered-log kept=140903 dropped=614). This builder reproduces that recipe
EXACTLY (same generator functions, same POOL_SEED+7 stream, same encoder) with
one additive filter: any WebRED train row whose normalised sentence matches the
held-out reading94 panel is dropped and counted (expect 0). Training rows come
from train.jsonl ONLY; dev.jsonl is the sealed calibration split (never
trained on); heldout.jsonl is never touched. Panel file is read for the
overlap check only — never for training, tuning, or checkpoint choice.

Additive only: fable_ears47_data / fable_listening_english are imported
read-only and never edited.
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

REPO = Path(__file__).resolve().parent.parent
WEBRED = REPO / "data" / "open" / "webred" / "frames"
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
SEEDS109 = (10901, 10902, 10903)

# The one relation-alias mapping with direct exp-107 evidence (§2: "X is a town
# in France" -> country where gold says located in ...). Sealed; identity
# fallback for every other name (alias.get(rel, rel)).
ALIAS109 = {"country": "located in the administrative territorial entity"}


def norm_sent(s: str) -> str:
    return re.sub(r"\s+", " ", s.casefold()).strip()


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def panel_sentences() -> list[str]:
    return [r["sentence"] for r in load_jsonl(PANEL)]


def audit() -> dict:
    """Overlap + label-set + counts. No tokenizer, no model, no panel scoring."""
    train = load_jsonl(WEBRED / "train.jsonl")
    dev = load_jsonl(WEBRED / "dev.jsonl")
    panel = load_jsonl(PANEL)
    assert len(panel) == 400, len(panel)
    n_gold = sum(len(r.get("triples", [])) for r in panel)
    n_nofact = sum(1 for r in panel if not r.get("triples", []))
    assert n_gold == 312, n_gold
    assert n_nofact == 245, n_nofact

    pset = {norm_sent(s) for s in panel_sentences()}
    trset = {norm_sent(r["text"]) for r in train}
    dset = {norm_sent(r["text"]) for r in dev}
    over_train = sorted(trset & pset)
    over_dev = sorted(dset & pset)
    train_dev = sorted(trset & dset)

    train_rels = sorted({r["relation"] for r in train})
    missing = [r for r in train_rels if r not in D.REL_INDEX]
    dev_pos = sum(1 for r in dev if r["positive"])
    dev_neg = sum(1 for r in dev if not r["positive"])
    train_pos = sum(1 for r in train if r["positive"])
    train_neg = sum(1 for r in train if not r["positive"])

    try:
        held_n = sum(1 for _ in open(WEBRED / "heldout.jsonl", encoding="utf-8"))
    except FileNotFoundError:
        held_n = -1
    out = {
        "panel_n": len(panel), "panel_gold_triples": n_gold,
        "panel_nofact": n_nofact,
        "webred_train_n": len(train), "webred_train_pos": train_pos,
        "webred_train_neg": train_neg,
        "webred_dev_n": len(dev), "webred_dev_pos": dev_pos,
        "webred_dev_neg": dev_neg,
        "webred_heldout_n": held_n,
        "overlap_train_panel": len(over_train),
        "overlap_dev_panel": len(over_dev),
        "overlap_train_dev": len(train_dev),
        "overlap_train_panel_examples": over_train[:5],
        "overlap_dev_panel_examples": over_dev[:5],
        "train_distinct_relations": len(train_rels),
        "train_relations_missing_from_47_classes": missing,
        "classes_47_n": D.N_REL,
    }
    print(json.dumps(out, indent=1))
    return out


def build_pool(out_path: str, snapshot: str) -> None:
    """Rebuild the 47 pool recipe with the panel-overlap filter (expect 0 rows)."""
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(D.snapshot_dir(snapshot))
    pset = {norm_sent(s) for s in panel_sentences()}
    kept = drop = excluded = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        rng = random.Random(D.POOL_SEED + 7)
        for row in D.synth_pool_rows(tok, rng):
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
        for row in D.webred_pool_rows():
            if norm_sent(row["text"]) in pset:
                excluded += 1
                continue
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
    print(f"pool kept={kept} dropped={drop} excluded_panel_overlap={excluded} "
          f"-> {out_path}")
    if excluded:
        print(f"WARNING: {excluded} WebRED train rows overlapped the panel "
              f"and were excluded")


def build_cal(out_path: str) -> None:
    """Sealed calibration split: ALL of WebRED dev with gold47 labels.

    Disjoint from training by construction (dev split; audit reports
    train∩dev overlap). Positives -> STATE with the gold Wikidata relation
    name; negatives -> NO_FACT. Char spans are kept so the scorer can build
    exact gold triples for the operating-point sweep.
    """
    dev = load_jsonl(WEBRED / "dev.jsonl")
    rows = []
    for i, r in enumerate(dev):
        rows.append({
            "n": i + 1, "source": "webred-dev", "text": r["text"],
            "positive": r["positive"], "relation": r["relation"],
            "relation_id": r.get("relation_id"),
            "subj_chars": r["subj"], "obj_chars": r["obj"],
            "family": "webred-dev." + ("pos" if r["positive"] else "neg"),
            "gold47": D.gold_from_webred(r),
        })
    pos = sum(1 for r in rows if r["positive"])
    sha = hashlib.sha256(
        json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    Path(out_path).write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"calwebred n={len(rows)} pos={pos} neg={len(rows) - pos} sha={sha} "
          f"-> {out_path}")


def write_alias(out_path: str) -> None:
    Path(out_path).write_text(json.dumps(ALIAS109, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(f"alias109 {ALIAS109} -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--build-pool", default=None)
    ap.add_argument("--build-cal", default=None)
    ap.add_argument("--write-alias", default=None)
    ap.add_argument("--snapshot", default=None)
    a = ap.parse_args()
    if a.audit:
        audit()
    if a.build_cal:
        build_cal(a.build_cal)
    if a.write_alias:
        write_alias(a.write_alias)
    if a.build_pool:
        assert a.snapshot, "--build-pool needs --snapshot"
        build_pool(a.build_pool, a.snapshot)


if __name__ == "__main__":
    main()
