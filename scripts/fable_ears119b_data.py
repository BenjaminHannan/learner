#!/usr/bin/env python3
"""Exp 119b PREP — relation-namespace remap data builder (Muse).

    python fable_ears119b_data.py --audit --snapshot <scibert>
    python fable_ears119b_data.py --length-hist OUT.json --snapshot <scibert>
    python fable_ears119b_data.py --build-pool OUT.jsonl --snapshot <scibert>   # BensPC

THE ONE CHANGE vs exp 119: training-label relation remap (doc 119d fix 1).
A closed-list WebRED-relation -> inventory-relation REMAP (below) is applied
to every training gold47 BEFORE encoding; everything else is 119 verbatim:
same MAX_LEN 192 override, same lengthening (RNG_LEN stream 11900), same
pool composition, same identity gates. The canonical table with one-line
reasons is artifacts/fable-ears119b-20260922/remap.json; the REMAP dict here
is identical to that file's "mapping" (the audit cross-checks equality).

Reading94 is untouched: the remap was built ONLY from training sources
(WebRED frames data/open/webred/frames/relations.json relation names + WebRED-train
example sentences + SimpleWiki86 training sentences for wording checks).
No reading94 sentence, triple, or count was inspected to choose any entry;
documented exclusions (citizenship, birth/death swap, capital direction,
contains-inverse) are decided on training-source evidence alone.

Additive only: fable_ears47_data / fable_ears47_encoder are imported read-only
and never edited. Two runtime overrides live in THIS file (as in 119):
D.MAX_LEN = 192 and D._wp_encode.__defaults__ = (192,).
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

MAX119 = 192
D.MAX_LEN = MAX119
D._wp_encode.__defaults__ = (MAX119,)

REPO = Path(__file__).resolve().parent.parent
WEBRED = REPO / "data" / "open" / "webred" / "frames"
SIMPLEWIKI = REPO / "data" / "open" / "simplewiki86" / "sentences.jsonl"
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
SEEDS119B = (11911, 11912, 11913)
RNG_LEN = 11900  # lengthening/target-sampling stream (deterministic, cross-machine)

# THE ONE CHANGE vs fable_ears119_data.py: this block only (see diff).
# Closed-list WebRED/synth relation -> our-inventory relation. Span-preserving
# renames only (same subject/object spans and argument order); every target is
# a registered 517-class name. Reasons live in remap.json ("entries").
REMAP = {
    "country": "located in the administrative territorial entity",
    "city": "located in the administrative territorial entity",
    "birthplace": "place of birth",
    "job": "occupation",
}


def remap_gold(gold: dict) -> dict:
    """Return gold with the relation remapped, or the same object if no entry."""
    rel = gold.get("rel")
    if rel in REMAP:
        gold = dict(gold)
        gold["rel"] = REMAP[rel]
    return gold


# Distractor clauses: locative/temporal/appositive phrases with generic nouns
# only (no person names, no relation verbs). Every clause must additionally
# pass the flags_of() equality guard in lengthen() before it is kept.
DISTRACTORS = (
    ", near the old railway station",
    ", during the summer festival",
    ", with its distinctive red roof",
    ", along the northern coast",
    ", after the annual harvest",
    ", beside the wide river",
    ", under the new administration",
    ", across the central plaza",
    ", within the historic district",
    ", between the two main roads",
    ", over the long weekend",
    ", throughout the entire region",
    ", among the local residents",
    ", behind the stone wall",
    ", beyond the city limits",
    ", beneath the tall oak trees",
    ", around the busy marketplace",
    ", following the morning session",
    ", during the winter months",
    ", near the southern border",
    ", across the open fields",
    ", within walking distance of the harbour",
    ", beside the ancient chapel",
    ", under clear blue skies",
    ", after several years of planning",
    ", which dates back to the previous century",
    ", which overlooks the valley",
    ", which spans three city blocks",
    ", which houses the municipal archive",
    ", which hosts the autumn fair",
)


def norm_sent(s: str) -> str:
    return re.sub(r"\s+", " ", s.casefold()).strip()


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def token_lens(texts: list[str], tok) -> list[int]:
    return [len(tok.encode(t, 512)[0]) for t in texts]


def webred_train_lens_sorted(tok) -> list[int]:
    return sorted(token_lens(
        [r["text"] for r in load_jsonl(WEBRED / "train.jsonl")], tok))


def lengthen(text: str, target: int, rng: random.Random, tok) -> str:
    """Append distractor clauses until token length >= target (cap MAX119-2).

    Rows already longer than target are returned unchanged. A clause is kept
    only if the 47 flags vector is unchanged, so golds never flip meaning.
    """
    base_flags = D.flags_of(text)
    cur = len(tok.encode(text, 512)[0])
    if cur >= target:
        return text
    clauses = list(DISTRACTORS)
    rng.shuffle(clauses)
    for c in clauses:
        if cur >= target:
            break
        cand = text + c
        ids = tok.encode(cand, 512)[0]
        if len(ids) > MAX119 - 2:
            break
        if D.flags_of(cand) != base_flags:
            continue
        text, cur = cand, len(ids)
    return text


def synth_pool_rows_long(tok) -> list[dict]:
    """47's exact 60k synth rows (same stream -> same facts), length-matched.

    Targets are sampled uniform-over-rows from the WebRED-train token-length
    histogram (empirical distribution), capped at MAX119-2.
    THE ONE CHANGE: gold47 relations pass through REMAP (remap_gold).
    """
    base = D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))
    assert len(base) == D.POOL_SYNTH, len(base)
    ref = webred_train_lens_sorted(tok)
    rng = random.Random(RNG_LEN)
    out = []
    for row in base:
        target = min(ref[rng.randrange(len(ref))], MAX119 - 2)
        out.append({"text": lengthen(row["text"], target, rng, tok),
                    "source": "synth", "gold47": remap_gold(row["gold47"])})
    return out


def audit(snapshot: str) -> dict:
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    train = load_jsonl(WEBRED / "train.jsonl")
    panel = load_jsonl(PANEL)
    assert len(panel) == 400 and sum(len(r.get("triples", []))
                                     for r in panel) == 312
    pset = {norm_sent(r["sentence"]) for r in panel}
    trset = {norm_sent(r["text"]) for r in train}
    wrl = sorted(token_lens([r["text"] for r in train], tok))
    swl = sorted(token_lens(
        [r["text"] for r in load_jsonl(SIMPLEWIKI)], tok))
    n = len(wrl)
    out = {
        "max_len": MAX119,
        "webred_train_n": n,
        "webred_train_med": wrl[n // 2],
        "webred_train_p99": wrl[int(0.99 * (n - 1))],
        "webred_train_le192": sum(1 for x in wrl if x <= MAX119),
        "simplewiki_n": len(swl),
        "simplewiki_le192": sum(1 for x in swl if x <= MAX119),
        "overlap_train_panel": len(trset & pset),
        "pool_synth_n": D.POOL_SYNTH,
        "pool_seed": D.POOL_SEED,
        "classes_n": D.N_REL,
    }
    print(json.dumps(out, indent=1))
    return out


def length_hist(out_path: str, snapshot: str) -> dict:
    """Before/after length histograms (tokenizer only, no training).

    before: 47 pool composition (short synth + WebRED-train) measured at 96.
    after:  length-matched synth + WebRED-train measured at 192.
    """
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    webred_texts = [r["text"] for r in load_jsonl(WEBRED / "train.jsonl")]
    wrl = token_lens(webred_texts, tok)
    swl = token_lens([r["text"] for r in load_jsonl(SIMPLEWIKI)], tok)
    base = D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))
    base_lens = token_lens([r["text"] for r in base], tok)
    long_rows = synth_pool_rows_long(tok)
    long_lens = token_lens([r["text"] for r in long_rows], tok)

    def stats(xs):
        s = sorted(xs)
        m = len(s)
        return {"n": m, "min": s[0], "med": s[m // 2],
                "p90": s[int(0.90 * (m - 1))], "p99": s[int(0.99 * (m - 1))],
                "max": s[-1],
                "le96": sum(1 for x in s if x <= 96),
                "le192": sum(1 for x in s if x <= MAX119)}

    res = {
        "max_len": MAX119,
        "webred_train": stats(wrl),
        "simplewiki86": stats(swl),
        "synth_before": stats(base_lens),
        "synth_after": stats(long_lens),
    }
    Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return res


def build_pool(out_path: str, snapshot: str) -> None:
    """Rebuild the pool with length-matched synth (runs on BensPC)."""
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot)
    kept = drop = 0
    synth_n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in synth_pool_rows_long(tok):
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
            synth_n += 1
        for row in D.webred_pool_rows():
            # THE ONE CHANGE: remap WebRED training golds before encoding.
            row = dict(row)
            row["gold47"] = remap_gold(row["gold47"])
            e = D.encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
    print(f"pool119b kept={kept} dropped={drop} synth={synth_n} "
          f"webred={kept - synth_n} -> {out_path}")
    assert synth_n == D.POOL_SYNTH, f"synth {synth_n} != 60000"
    assert kept >= 140903, f"kept {kept} < 47's 140903 (wider window must drop less)"
    assert drop <= 614, f"dropped {drop} > 47's 614"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--length-hist", default=None)
    ap.add_argument("--build-pool", default=None)
    ap.add_argument("--snapshot", default=None)
    a = ap.parse_args()
    if a.audit:
        assert a.snapshot, "--audit needs --snapshot"
        audit(a.snapshot)
    if a.length_hist:
        assert a.snapshot, "--length-hist needs --snapshot"
        length_hist(a.length_hist, a.snapshot)
    if a.build_pool:
        assert a.snapshot, "--build-pool needs --snapshot"
        build_pool(a.build_pool, a.snapshot)


if __name__ == "__main__":
    main()
