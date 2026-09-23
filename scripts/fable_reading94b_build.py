#!/usr/bin/env python3
"""Exp 94b helpers: validate 400-row panel (heldout rows 400-799), blind-80 agreement.

Mirrors scripts/fable_reading94_build.py (frozen exp-94 procedure) with row range
400-799 and seed 9402. Data build only: no training, no notebook writes, Mac CPU only.
Usage:
  python -B scripts/fable_reading94b_build.py --validate
  python -B scripts/fable_reading94b_build.py --agree
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELD = ROOT / "data" / "open" / "simplewiki86" / "heldout.jsonl"
OUTDIR = ROOT / "data" / "open" / "reading94b"
ART = ROOT / "artifacts" / "fable-reading94b-20260922"
SEED80 = 9402
ROW_LO, ROW_HI = 400, 800

ALLOWED_NF = {"fragment", "relation-not-in-inventory", "opinion",
              "vague-pronoun-subject", "list-or-table"}


def _load(p: Path):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def validate() -> None:
    held = _load(HELD)[ROW_LO:ROW_HI]
    scaf = _load(OUTDIR / "scaffold400.jsonl")
    assert len(scaf) == 400, len(scaf)
    assert [r["id"] for r in scaf] == [r["id"] for r in held], "scaffold != heldout 400-799"
    p1 = []
    for i in (1, 2, 3, 4):
        p1 += _load(OUTDIR / f"fable_reading94b_pass1_labels_p{i}.jsonl")
    assert len(p1) == 400, len(p1)
    assert [r["id"] for r in p1] == [r["id"] for r in scaf], "pass1 ids != scaffold order"
    samp = json.load(open(ART / "fable_reading94b_sample80_ids.json", encoding="utf-8"))
    assert samp["seed"] == SEED80, samp["seed"]
    p2 = _load(OUTDIR / "pass2.jsonl")
    assert len(p2) == 80, len(p2)
    assert [r["id"] for r in p2] == samp["ids"], "pass2 ids != sealed sample order"
    inv = set(json.load(open(ROOT / "artifacts" / "fable-ears47-20260921"
                             / "relation_classes.json", encoding="utf-8"))["classes"])
    sent = {r["id"]: r["sentence"] for r in scaf}
    n_rel = 0
    for tag, rows in (("p1", p1), ("p2", p2)):
        for r in rows:
            tr = r.get("triples") or []
            nf = r.get("no_fact_reason")
            if tr and nf is not None:
                raise AssertionError(f"{tag} {r['id']}: fact + reason")
            if not tr and nf not in ALLOWED_NF:
                raise AssertionError(f"{tag} {r['id']}: bad no_fact_reason {nf!r}")
            for t in tr:
                n_rel += 1
                if t.get("relation") not in inv:
                    raise AssertionError(f"{tag} {r['id']}: relation not in inventory: {t.get('relation')!r}")
                for k in ("subject", "object"):
                    v = t.get(k, "")
                    if v and v not in sent[r["id"]]:
                        raise AssertionError(f"{tag} {r['id']}: {k} not verbatim: {v!r}")
                for qk in (t.get("qualifiers") or {}):
                    if qk not in ("time", "place"):
                        raise AssertionError(f"{tag} {r['id']}: bad qualifier {qk!r}")
    print(f"validate OK: scaffold 400 == heldout[400:800]; pass1 400 in order; "
          f"pass2 80 == sealed sample (seed {SEED80}); {n_rel} triples all in inventory, spans verbatim")


def _norm_triple(t: dict):
    q = t.get("qualifiers") or {}
    return (t.get("subject", "").strip(), t.get("relation", "").strip(),
            t.get("object", "").strip(),
            q.get("time", "") or "", q.get("place", "") or "")


def agree() -> None:
    p1 = []
    for i in (1, 2, 3, 4):
        p1 += _load(OUTDIR / f"fable_reading94b_pass1_labels_p{i}.jsonl")
    p2 = _load(OUTDIR / "pass2.jsonl")
    m1 = {r["id"]: r for r in p1}
    exact = 0
    nf_agree = 0
    a = b = c = d = 0  # a=FF b=FNF c=NFF d=NN
    for r in p2:
        o = m1[r["id"]]
        t1 = sorted(_norm_triple(t) for t in (o.get("triples") or []))
        t2 = sorted(_norm_triple(t) for t in (r.get("triples") or []))
        if t1 == t2:
            exact += 1
        f1 = len(t1) > 0
        f2 = len(t2) > 0
        nf1 = o.get("no_fact_reason")
        nf2 = r.get("no_fact_reason")
        if (nf1 is None) == (nf2 is None) and (nf1 == nf2 or (f1 and f2)):
            nf_agree += 1
        if f1 and f2:
            a += 1
        elif f1 and not f2:
            b += 1
        elif not f1 and f2:
            c += 1
        else:
            d += 1
    n = len(p2)
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"n={n} exact_triple_match={exact}/{n}={exact/n:.3f}")
    print(f"nofact_agree={nf_agree}/{n}={nf_agree/n:.3f}")
    print(f"fact_table FF={a} FN={b} NF={c} NN={d} kappa={kappa:.4f}")
    with open(ART / "agreement94b.json", "w", encoding="utf-8") as fh:
        json.dump({"n": n, "exact": exact, "nofact_agree": nf_agree,
                   "FF": a, "FN": b, "NF": c, "NN": d, "kappa": round(kappa, 4)},
                  fh, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--agree", action="store_true")
    x = ap.parse_args()
    if x.validate:
        validate()
    if x.agree:
        agree()
    if not (x.validate or x.agree):
        ap.print_help()


if __name__ == "__main__":
    main()
