#!/usr/bin/env python3
"""Exp 94 helpers: extract first-400 panel scaffold, draw blind 80-sample, score agreement.

Additive-only helper (own prefix). No training, no notebook writes, Mac CPU only.
Usage:
  python -B scripts/fable_reading94_build.py --scaffold
  python -B scripts/fable_reading94_build.py --sample80
  python -B scripts/fable_reading94_build.py --agree
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELD = ROOT / "data" / "open" / "simplewiki86" / "heldout.jsonl"
OUTDIR = ROOT / "data" / "open" / "reading94"
ART = ROOT / "artifacts" / "fable-reading94-20260921"
SEED80 = 94


def scaffold() -> None:
    rows = [json.loads(l) for l in open(HELD, encoding="utf-8")][:400]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(OUTDIR / "scaffold400.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"id": r["id"], "page": r["page"],
                                 "sentence": r["text"]}, ensure_ascii=False) + "\n")
    print(f"scaffold 400 -> {OUTDIR / 'scaffold400.jsonl'}")


def sample80() -> None:
    rows = [json.loads(l) for l in open(HELD, encoding="utf-8")][:400]
    rng = random.Random(SEED80)
    idx = sorted(rng.sample(range(400), 80))
    ART.mkdir(parents=True, exist_ok=True)
    with open(ART / "fable_reading94_sample80_ids.json", "w", encoding="utf-8") as fh:
        json.dump({"seed": SEED80, "idx": idx,
                   "ids": [rows[i]["id"] for i in idx]}, fh, indent=1)
    print(f"sample80 seed={SEED80} -> {ART / 'fable_reading94_sample80_ids.json'}")
    print("ids:", ",".join(str(i) for i in idx[:20]), "...")


def _norm_triple(t: dict):
    q = t.get("qualifiers") or {}
    return (t.get("subject", "").strip(), t.get("relation", "").strip(),
            t.get("object", "").strip(),
            q.get("time", "") or "", q.get("place", "") or "")


def agree() -> None:
    p1 = [json.loads(l) for l in open(OUTDIR / "panel.jsonl", encoding="utf-8")]
    p2 = [json.loads(l) for l in open(OUTDIR / "pass2.jsonl", encoding="utf-8")]
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
            # NO_FACT agreement: same reason, or both have facts
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
    print(f"fact_table FF={a} FN={b} NF={c} NN={d} kappa={kappa:.3f}")
    with open(ART / "fable_reading94_agreement.json", "w", encoding="utf-8") as fh:
        json.dump({"n": n, "exact": exact, "nofact_agree": nf_agree,
                   "FF": a, "FN": b, "NF": c, "NN": d, "kappa": round(kappa, 4)},
                  fh, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scaffold", action="store_true")
    ap.add_argument("--sample80", action="store_true")
    ap.add_argument("--agree", action="store_true")
    x = ap.parse_args()
    if x.scaffold:
        scaffold()
    if x.sample80:
        sample80()
    if x.agree:
        agree()
    if not (x.scaffold or x.sample80 or x.agree):
        ap.print_help()


if __name__ == "__main__":
    main()
