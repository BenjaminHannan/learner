#!/usr/bin/env python3
"""Exp 271 -- CPU-only diagnostic: does ANY cutoff on the YES/NO checker's
score separate good ear frames from wrong ones on the 267 dev set?

Reads (never writes): artifacts/claude-diag267-20260923/{c1.json,
score.json, earpreds267.json, checks/c1/manifest.json} and
artifacts/claude-devset267-20260923/dev.jsonl (+ its SEAL for the sha check).
Imports sealed scorers read-only (never reimplements matching).

Labeling (frozen in PREDICTIONS.md before this ran): base = single-frame
S.match with rel_ok_narrower (Ruling 1); then relabels (a) appositive-relative
(value == another gold frame's subject, stated in the turn) and (b) plural
either-true-name -> good. Every relabeled frame is listed in the report.

Writes (new files only): frames.csv, roc_curve.csv, REPORT.md in
artifacts/claude-diag271-20260923/.

python claude_diag271_roc.py  (run from the repo root)
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261b_scoremain as M261B  # noqa: E402
from claude_diag267_score import load_dev  # noqa: E402

DIAG = ROOT / "artifacts" / "claude-diag267-20260923"
DEV = ROOT / "artifacts" / "claude-devset267-20260923" / "dev.jsonl"
SEAL = ROOT / "artifacts" / "claude-devset267-20260923" / "SEAL.sha256.txt"
OUT = ROOT / "artifacts" / "claude-diag271-20260923"

SIBLING = {"sister", "brother", "sibling"}


def rkey(s):
    return S.rkey(s)


def main():
    items = load_dev(str(DEV), str(SEAL))
    by_turn = {it["id"]: it for it in items}
    rawdev = {}
    for line in DEV.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rawdev[d["id"]] = d
    apd = json.loads((DIAG / "earpreds267.json").read_text(encoding="utf-8"))
    c1d = json.loads((DIAG / "c1.json").read_text(encoding="utf-8"))
    man = json.loads((DIAG / "checks" / "c1" / "manifest.json").read_text(encoding="utf-8"))
    ck = c1d["checks"]
    assert len(man) == 155, f"manifest {len(man)}"
    assert len(ck) == 155, f"c1 checks {len(ck)}"
    assert set(man) == set(ck), "manifest/check id mismatch"

    S.rel_ok = M261B.rel_ok_narrower
    try:
        frames = []  # one row per kept TEACH frame
        man_mismatch = []
        for cid in sorted(man):
            turn_id, k = cid.rsplit("#t", 1)
            k = int(k)
            it = by_turn[turn_id]
            rec = apd["preds"][turn_id]
            arms0 = A261.base_arms(rec["raw"], it["turn"], rec["greedy_lp"], rec["beams"])
            kept = [f for f in arms0["kept_canon"] if f.get("act") == "TEACH"]
            f = kept[k]
            mf = man[cid]["frame"]
            for fld in ("act", "subject", "relation", "value"):
                if str(f.get(fld)) != str(mf.get(fld)):
                    man_mismatch.append((cid, fld, f.get(fld), mf.get(fld)))
            p = float(ck[cid]["p"])
            hit, extra, _ = S.match([f], it["gold"], "TEACH")
            base = "good" if hit else "wrong"
            frames.append(dict(cid=cid, turn=turn_id,
                               family=rawdev[turn_id]["family"],
                               turn_text=rawdev[turn_id]["turn"],
                               frame=f, p=p, base=base))
        # fidelity: per-turn C0 + C1@0.25 reproduce 267's published totals
        from collections import defaultdict
        per_turn = defaultdict(list)
        for r in frames:
            per_turn[r["turn"]].append(r)
        c0h = c0w = c1h = c1w = c1saved = 0
        for tid, rs in per_turn.items():
            it = by_turn[tid]
            fr_all = [r["frame"] for r in rs]
            h, x, _ = S.match(fr_all, it["gold"], "TEACH")
            c0h += h
            c0w += len(x)
            fr1 = [r["frame"] for r in rs if r["p"] >= 0.25]
            c1saved += len(fr1)
            h1, x1, _ = S.match(fr1, it["gold"], "TEACH")
            c1h += h1
            c1w += len(x1)
        fid = dict(c0_hit=c0h, c0_wrong=c0w, c1_hit=c1h, c1_wrong=c1w,
                   c1_saved=c1saved, manifest_mismatches=len(man_mismatch))

        # relabels (a) appositive-relative, (b) plural either-true-name
        rel_a, rel_b = [], []
        for r in frames:
            if r["base"] == "good":
                r["final"] = "good"
                r["why"] = "gold-hit"
                continue
            f = r["frame"]
            tid = r["turn"]
            gold_teach = [g for g in rawdev[tid]["gold"] if g["act"] == "TEACH"]
            txt = r["turn_text"].lower()
            fv = S.norm(f.get("value", ""))
            hit_a = False
            if fv:
                for g in gold_teach:
                    if S.norm(g["subject"]) == fv and S.norm(g["subject"]) != S.norm(f.get("subject", "")):
                        if fv in txt:
                            hit_a = True
                            break
            if hit_a:
                r["final"] = "good"
                r["why"] = "appositive-relative"
                rel_a.append(r["cid"])
                continue
            hit_b = False
            if rawdev[tid]["family"] == "plural_relative" and rkey(f.get("relation", "")) in SIBLING:
                sib_vals = {S.norm(g["value"]) for g in gold_teach
                            if rkey(g["relation"]) in SIBLING and S.norm(g.get("value", ""))}
                if sib_vals and fv and fv not in sib_vals and fv in txt:
                    other = any(v != fv for v in sib_vals)
                    if other:
                        hit_b = True
            if hit_b:
                r["final"] = "good"
                r["why"] = "plural-either-name"
                rel_b.append(r["cid"])
                continue
            r["final"] = "wrong"
            r["why"] = "no-match"
    finally:
        S.rel_ok = M261B._ORIG_REL_OK

    goods = [r for r in frames if r["final"] == "good"]
    wrongs = [r for r in frames if r["final"] == "wrong"]
    G, W = len(goods), len(wrongs)

    # AUC: Mann-Whitney with tie-averaged ranks (higher p = likelier good)
    order = sorted(frames, key=lambda r: r["p"])
    auc_num = 0.0
    i = 0
    rank_sum_good = 0.0
    n = len(order)
    idx = 0
    while idx < n:
        j = idx
        while j < n and order[j]["p"] == order[idx]["p"]:
            j += 1
        avg_rank = (idx + 1 + j) / 2.0  # 1-based ranks idx+1..j
        for r in order[idx:j]:
            if r["final"] == "good":
                rank_sum_good += avg_rank
        idx = j
    auc = (rank_sum_good - G * (G + 1) / 2.0) / (G * W) if G and W else None

    # cutoff grid
    thetas = sorted({r["p"] for r in frames})
    curve = []
    for t in [0.0] + thetas:
        kept = [r for r in frames if r["p"] >= t]
        kg = sum(1 for r in kept if r["final"] == "good")
        kw = sum(1 for r in kept if r["final"] == "wrong")
        curve.append(dict(t=t, kept=len(kept), kept_good=kg, kept_wrong=kw,
                          wrong_per_20=(kw / len(kept) * 20.0) if kept else None,
                          lost_good=G - kg))
    # t above max -> keep none
    curve.append(dict(t=max(thetas) + 1e-9, kept=0, kept_good=0,
                      kept_wrong=0, wrong_per_20=None, lost_good=G))
    qual = [c for c in curve if c["kept"] > 0 and c["kept_wrong"] / c["kept"] <= 0.05]
    best = None
    if qual:
        best = sorted(qual, key=lambda c: (-c["kept_good"], c["kept_wrong"], -c["t"]))[0]
    closest = sorted([c for c in curve if c["kept"] > 0],
                     key=lambda c: (c["kept_wrong"] / c["kept"], -(c["kept_good"])))[0]
    # reference: sealed theta 0.25 row
    ref = next(c for c in curve if abs(c["t"] - 0.25) < 1e-12) if any(
        abs(c["t"] - 0.25) < 1e-12 for c in curve) else None
    if ref is None:
        kept = [r for r in frames if r["p"] >= 0.25]
        ref = dict(t=0.25, kept=len(kept),
                   kept_good=sum(1 for r in kept if r["final"] == "good"),
                   kept_wrong=sum(1 for r in kept if r["final"] == "wrong"),
                   wrong_per_20=(sum(1 for r in kept if r["final"] == "wrong") / len(kept) * 20.0) if kept else None,
                   lost_good=G - sum(1 for r in kept if r["final"] == "good"))

    # by family
    fams = sorted({r["family"] for r in frames})
    famtab = []
    for fam in fams:
        fr = [r for r in frames if r["family"] == fam]
        g = [r for r in fr if r["final"] == "good"]
        w = [r for r in fr if r["final"] == "wrong"]
        # family AUC
        o = sorted(fr, key=lambda r: r["p"])
        rs = 0.0
        ii = 0
        while ii < len(o):
            jj = ii
            while jj < len(o) and o[jj]["p"] == o[ii]["p"]:
                jj += 1
            ar = (ii + 1 + jj) / 2.0
            for r in o[ii:jj]:
                if r["final"] == "good":
                    rs += ar
            ii = jj
        fAUC = ((rs - len(g) * (len(g) + 1) / 2.0) / (len(g) * len(w))
                if g and w else None)
        bt = best["t"] if best else None
        bkg = sum(1 for r in fr if r["final"] == "good" and (bt is None or r["p"] >= bt))
        bkw = sum(1 for r in fr if r["final"] == "wrong" and (bt is None or r["p"] >= bt))
        famtab.append(dict(family=fam, n=len(fr), good=len(g), wrong=len(w),
                           auc=fAUC, best_kept_good=bkg, best_kept_wrong=bkw,
                           best_lost_good=len(g) - bkg))

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "frames.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "turn", "family", "p", "base", "final", "why",
                    "subject", "relation", "value"])
        for r in sorted(frames, key=lambda r: r["cid"]):
            f = r["frame"]
            w.writerow([r["cid"], r["turn"], r["family"], f"{r['p']:.6f}",
                        r["base"], r["final"], r["why"],
                        f.get("subject"), f.get("relation"), f.get("value")])
    with open(OUT / "roc_curve.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["theta", "kept", "kept_good", "kept_wrong",
                    "wrong_per_20_saved", "lost_good"])
        for c in curve:
            w.writerow([f"{c['t']:.6f}", c["kept"], c["kept_good"],
                        c["kept_wrong"],
                        (f"{c['wrong_per_20']:.3f}" if c["wrong_per_20"] is not None else ""),
                        c["lost_good"]])

    rep = {
        "n": len(frames), "good": G, "wrong": W, "auc": auc,
        "relabeled_appositive": sorted(rel_a),
        "relabeled_plural": sorted(rel_b),
        "fidelity": fid,
        "curve": curve, "best": best, "closest": closest, "ref025": ref,
        "by_family": famtab,
        "frames": [{k: (r[k] if k != "frame" else
                        {kk: r["frame"].get(kk) for kk in ("subject", "relation", "value")})
                    for k in ("cid", "turn", "family", "p", "base", "final", "why", "frame")}
                   for r in sorted(frames, key=lambda r: -r["p"])],
    }
    (OUT / "roc.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(dict(n=len(frames), good=G, wrong=W, auc=auc,
                           rel_a=len(rel_a), rel_b=len(rel_b),
                           fidelity=fid, best=best, closest=closest,
                           ref025=ref), indent=1))


if __name__ == "__main__":
    main()
