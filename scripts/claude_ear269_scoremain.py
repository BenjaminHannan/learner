#!/usr/bin/env python3
"""Exp 269 -- registered scorer: 265's pipeline plus the text-level check.

Arms from GPU ear preds + recorded checker p(YES) (one file serves all ear
arms; prompt B, sealed theta 0.25):
  A      text group-owner check + 265 arm A (registered)
  A265   265's arm A exactly (brake -> 265 canon/divert -> checker -> guard)
  A261b  brake -> 261 canon -> checker(0.25) -> 261b guard (261b's A exactly)
  B      138i + 228 (statement items; report only, no bars)

Matching = sealed 235 functions with 261b's Ruling-1 narrower patch (imported
read-only). "Asks whose" = 265's sealed fixed-reply check, plus the sealed
generic ask line (same shape) when only the text check fires.

Marks, arm A:
  M1  group_owner: 0 saved TEACH frames with group-word subjects, and >= 27/30
      turns with an ask-whose reply (265's bar).
  M2  mixed: >= 12/15 turns exactly right (TEACH exact vs gold, 0 group saves,
      ask-whose reply present) (265's bar).
  M3  first_person: 0 gold TEACH hits lost vs A265.
  M4  named: 15/15 turns byte-identical to A265.
  M5  0 new wrong saves vs A261b (A wrong multiset ⊆ A261b wrong multiset).
  M6  false asks on non_owner_we + first_person + named turns <= 1 in total.
  M7  gold TEACH hits lost on non_owner_we, A vs A265, <= 1.
  M8  0 new wrong saves A vs A265 across all families.
Also reported (no bars): per-fact and per-turn wrong-save rates for A, A265,
A261b and B; per family; each wrong/diverted/text-asked frame by category
only (never quoted); panel theta curve for A.

python claude_ear269_scoremain.py --panel P --seal S --a-preds A.json --b-preds B.json --theta TH --pyes Y.json [--pyes2 ...] --out O.json [--no-sha]
python claude_ear269_scoremain.py --dev D.jsonl --a-preds A.json --b-preds B.json --theta TH --pyes Y.json --out O.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_scoremain as M261  # noqa: E402
import claude_earcheck261b_scoremain as M261b  # noqa: E402
import claude_earcheck261b_arms as BA  # noqa: E402
import claude_ear265_arms as A265  # noqa: E402
import claude_ear265_canon as C265  # noqa: E402
import claude_ear269_arms as A269  # noqa: E402
import claude_ear269_panel as P  # noqa: E402

FAMS = ["group_owner", "mixed", "first_person", "named", "non_owner_we"]

M6_FAMS = {"non_owner_we", "first_person", "named"}

_ORIG_REL_OK = S.rel_ok


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score(items, apreds, bpreds, pmap, theta):
    S.rel_ok = M261b.rel_ok_narrower
    try:
        rows = []
        for it in items:
            rec = apreds[it["id"]]
            stub = dict(id=it["id"], turn=it["turn"])
            arms261, unsure261, _, pl, cms = M261.arm_set(stub, rec, pmap, theta)
            a261_saved = arms261["A"]
            a261b_frames, a261b_held, gms261 = BA.apply_guard(a261_saved)
            kept265 = A265.kept_265(rec["raw"], it["turn"])
            saved265, unsure265, diverted, reply265 = A265.a265_split(
                kept265, pl, theta)
            a265_frames, a265_held, gms = A265.apply_guard(saved265)
            aa = A269.arm_a(kept265, pl, it["turn"], theta)
            a_frames, a_held, gms_a = A269.apply_guard(aa["saved"])
            assert a_frames == a265_frames, (
                it["id"], "arm A saves must equal A265 saves")
            ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
            ms = round(ear_ms + sum(cms) + gms_a + aa["gc_ms"], 2)
            ask = aa["ask"]
            ask265 = C265.asks_whose(reply265)
            group_saves = sum(1 for f in a_frames
                              if f.get("act") == "TEACH"
                              and C265.is_group_subject(f.get("subject", "")))
            th, tx, tn = S.match(a_frames, it["gold"], "TEACH")
            ah, ax, an = S.match(a_frames, it["gold"], "ASK")
            t265, tx265, tn265 = S.match(a265_frames, it["gold"], "TEACH")
            t261, tx261, tn261 = S.match(a261b_frames, it["gold"], "TEACH")
            wrong_new_261b = list(tx)
            for w in tx261:
                for i, c in enumerate(wrong_new_261b):
                    if c == w:
                        del wrong_new_261b[i]
                        break
            wrong_new_265 = list(tx)
            for w in tx265:
                for i, c in enumerate(wrong_new_265):
                    if c == w:
                        del wrong_new_265[i]
                        break
            saved_n = sum(1 for f in a_frames if f["act"] == "TEACH")
            teach_exact = (th == tn and not tx)
            mixed_exact = bool(teach_exact and ask and group_saves == 0)
            row = dict(id=it["id"], family=it["family"], tags=it["tags"], ms=ms,
                        gc_ms=aa["gc_ms"], reply=aa["reply"], ask=ask,
                        ask265=ask265, fires=aa["fires"],
                        reasons=aa["reasons"], diverted=len(diverted),
                        group_saves=group_saves,
                        teach=dict(hit=th, gold=tn, wrong=len(tx), saved=saved_n),
                        askm=dict(hit=ah, gold=an, extra=len(ax)),
                        teach265=dict(hit=t265, gold=tn265, wrong=len(tx265)),
                        teach261=dict(hit=t261, gold=tn261, wrong=len(tx261)),
                        wrong_new_261b=len(wrong_new_261b),
                        wrong_new_265=len(wrong_new_265),
                        a261b_frames=a261b_frames, a_frames=a_frames,
                        a265_frames=a265_frames,
                        mixed_exact=mixed_exact if it["family"] == "mixed" else None)
            if it["id"] in bpreds:
                bh, bx, bn = S.match(S.b_frames(bpreds[it["id"]]), it["gold"], "TEACH")
                bsaved = sum(1 for t in bpreds[it["id"]].get("triples", []))
                row["b"] = dict(hit=bh, gold=bn, wrong=len(bx), saved=bsaved)
            rows.append(row)

        fam = {}
        for r in rows:
            t = fam.setdefault(r["family"], dict(n=0, teach_hit=0, teach_gold=0,
                                                 wrong=0, saved=0, ask_turns=0,
                                                 ask265_turns=0, fires_turns=0,
                                                 mixed_exact=0, group_saves=0,
                                                 wrong_new_261b=0,
                                                 wrong_new_265=0, lost265=0,
                                                 lost261=0, ident265=0,
                                                 ident261=0, turns_wrong=0))
            t["n"] += 1
            t["teach_hit"] += r["teach"]["hit"]
            t["teach_gold"] += r["teach"]["gold"]
            t["wrong"] += r["teach"]["wrong"]
            t["saved"] += r["teach"]["saved"]
            t["ask_turns"] += 1 if r["ask"] else 0
            t["ask265_turns"] += 1 if r["ask265"] else 0
            t["fires_turns"] += 1 if r["fires"] else 0
            t["group_saves"] += r["group_saves"]
            t["wrong_new_261b"] += r["wrong_new_261b"]
            t["wrong_new_265"] += r["wrong_new_265"]
            if r["teach"]["wrong"]:
                t["turns_wrong"] += 1
            if r["family"] == "mixed" and r["mixed_exact"]:
                t["mixed_exact"] += 1
            t["lost265"] += max(0, r["teach265"]["hit"] - r["teach"]["hit"])
            t["lost261"] += max(0, r["teach261"]["hit"] - r["teach"]["hit"])
            if r["a_frames"] == r["a265_frames"]:
                t["ident265"] += 1
            if r["a_frames"] == r["a261b_frames"]:
                t["ident261"] += 1

        g = fam.get("group_owner", {})
        mx = fam.get("mixed", {})
        fp = fam.get("first_person", {})
        nm = fam.get("named", {})
        nw = fam.get("non_owner_we", {})
        marks = dict(
            M1_group_saves=sum(t.get("group_saves", 0) for t in fam.values()),
            M1_ask=g.get("ask_turns", 0), M1_n=g.get("n", 0),
            M1_ask265=g.get("ask265_turns", 0),
            M2_exact=mx.get("mixed_exact", 0), M2_n=mx.get("n", 0),
            M3_lost=fp.get("lost265", 0),
            M3_hit_A=fp.get("teach_hit", 0), M3_hit_265=sum(
                r["teach265"]["hit"] for r in rows if r["family"] == "first_person"),
            M3_gold=fp.get("teach_gold", 0),
            M4_ident=nm.get("ident265", 0), M4_n=nm.get("n", 0),
            M5_new=sum(t.get("wrong_new_261b", 0) for t in fam.values()),
            M6_false=sum(t.get("ask_turns", 0) for f, t in fam.items()
                         if f in M6_FAMS),
            M6_n=sum(t.get("n", 0) for f, t in fam.items() if f in M6_FAMS),
            M7_lost=nw.get("lost265", 0), M7_n=nw.get("n", 0),
            M7_hit_A=nw.get("teach_hit", 0), M7_hit_265=sum(
                r["teach265"]["hit"] for r in rows if r["family"] == "non_owner_we"),
            M8_new=sum(t.get("wrong_new_265", 0) for t in fam.values()),
        )
        verdict = dict(
            M1=(marks["M1_group_saves"] == 0 and marks["M1_ask"] >= 27),
            M2=(marks["M2_exact"] >= 12),
            M3=(marks["M3_lost"] == 0),
            M4=(marks["M4_ident"] == marks["M4_n"] and marks["M4_n"] == 15),
            M5=(marks["M5_new"] == 0),
            M6=(marks["M6_false"] <= 1),
            M7=(marks["M7_lost"] <= 1),
            M8=(marks["M8_new"] == 0),
        )
        if (marks["M1_n"] != 30 or marks["M2_n"] != 15 or marks["M4_n"] != 15
                or marks["M7_n"] != 20):
            verdict = {k: False for k in verdict}
            verdict["COUNTS"] = False
        verdict["ALL"] = all(v for v in verdict.values() if isinstance(v, bool))

        def rates(key_hit, key_gold, key_wrong, key_saved, key_turns, n):
            hit = sum(t.get(key_hit, 0) for t in fam.values())
            gold = sum(t.get(key_gold, 0) for t in fam.values())
            wrong = sum(t.get(key_wrong, 0) for t in fam.values())
            saved = sum(t.get(key_saved, 0) for t in fam.values())
            tw = sum(t.get(key_turns, 0) for t in fam.values())
            return dict(teach_hit=hit, teach_gold=gold, wrong=wrong, saved=saved,
                        per_fact_wrong=round(wrong / saved, 4) if saved else 0.0,
                        per_turn_wrong=round(tw / n, 4) if n else 0.0)

        n = len(rows)
        w265_hit = sum(r["teach265"]["hit"] for r in rows)
        w265_gold = sum(r["teach265"]["gold"] for r in rows)
        w265_wrong = sum(r["teach265"]["wrong"] for r in rows)
        w265_saved = sum(len([f for f in r["a265_frames"] if f.get("act") == "TEACH"])
                         for r in rows)
        w265_tw = sum(1 for r in rows if r["teach265"]["wrong"])
        w261_hit = sum(r["teach261"]["hit"] for r in rows)
        w261_gold = sum(r["teach261"]["gold"] for r in rows)
        w261_wrong = sum(r["teach261"]["wrong"] for r in rows)
        w261_saved = sum(len([f for f in r["a261b_frames"] if f.get("act") == "TEACH"])
                         for r in rows)
        w261_tw = sum(1 for r in rows if r["teach261"]["wrong"])
        b_hit = sum(r.get("b", {}).get("hit", 0) for r in rows)
        b_gold = sum(r.get("b", {}).get("gold", 0) for r in rows)
        b_wrong = sum(r.get("b", {}).get("wrong", 0) for r in rows)
        b_saved = sum(r.get("b", {}).get("saved", 0) for r in rows)
        b_tw = sum(1 for r in rows if r.get("b", {}).get("wrong", 0))
        summary = dict(
            A=rates("teach_hit", "teach_gold", "wrong", "saved", "turns_wrong", n),
            A265=dict(teach_hit=w265_hit, teach_gold=w265_gold, wrong=w265_wrong,
                      saved=w265_saved,
                      per_fact_wrong=round(w265_wrong / w265_saved, 4) if w265_saved else 0.0,
                      per_turn_wrong=round(w265_tw / n, 4) if n else 0.0),
            A261b=dict(teach_hit=w261_hit, teach_gold=w261_gold, wrong=w261_wrong,
                       saved=w261_saved,
                       per_fact_wrong=round(w261_wrong / w261_saved, 4) if w261_saved else 0.0,
                       per_turn_wrong=round(w261_tw / n, 4) if n else 0.0),
            B=dict(teach_hit=b_hit, teach_gold=b_gold, wrong=b_wrong, saved=b_saved,
                   per_fact_wrong=round(b_wrong / b_saved, 4) if b_saved else 0.0,
                   per_turn_wrong=round(b_tw / n, 4) if n else 0.0),
        )
        lat = [r["ms"] for r in rows if r["ms"] is not None]
        gclat = [r["gc_ms"] for r in rows if r["gc_ms"] is not None]
        details = []
        for r in rows:
            for f in r["a_frames"]:
                if f.get("act") != "TEACH":
                    continue
                h, x, _ = S.match([f], next(
                    it["gold"] for it in items if it["id"] == r["id"]), "TEACH")
                if x:
                    details.append(dict(id=r["id"], family=r["family"],
                                        status="WRONG", category="checker-guard-passed",
                                        subject=("GROUP" if C265.is_group_subject(
                                            f.get("subject", "")) else "other"),
                                        relation=str(f.get("relation", ""))))
            if r["diverted"]:
                details.append(dict(id=r["id"], family=r["family"],
                                    status="DIVERTED", category="ask-whose",
                                    n=r["diverted"], asked=r["ask265"]))
            if r["fires"] and not r["ask265"]:
                details.append(dict(id=r["id"], family=r["family"],
                                    status="TEXT_ASK", category="groupcheck-generic",
                                    reasons=r["reasons"], asked=r["ask"]))
            if r["ask"] and r["family"] in M6_FAMS:
                details.append(dict(id=r["id"], family=r["family"],
                                    status="FALSE_ASK", category="ask-on-control",
                                    reasons=r["reasons"],
                                    via_divert=bool(r["ask265"])))
            if r["wrong_new_261b"]:
                details.append(dict(id=r["id"], family=r["family"],
                                    status="NEW-WRONG-261B",
                                    category="not-in-A261b",
                                    n=r["wrong_new_261b"]))
            if r["wrong_new_265"]:
                details.append(dict(id=r["id"], family=r["family"],
                                    status="NEW-WRONG-265",
                                    category="not-in-A265",
                                    n=r["wrong_new_265"]))
        curve = []
        for ti100 in range(0, 21):
            th_ = round(ti100 * 0.05, 2)
            hit = gold = wrong = 0
            for it in items:
                rec = apreds[it["id"]]
                _, _, _, pl, _ = M261.arm_set(dict(id=it["id"], turn=it["turn"]),
                                              rec, pmap, th_)
                kept265 = A265.kept_265(rec["raw"], it["turn"])
                saved, _, _, _ = A265.a265_split(kept265, pl, th_)
                kept, _, _ = A265.apply_guard(saved)
                h, x, nn_ = S.match(kept, it["gold"], "TEACH")
                hit += h
                gold += nn_
                wrong += len(x)
            curve.append(dict(theta=th_, recall=round(hit / gold, 4) if gold else None,
                              wrong=wrong))
        out = dict(theta=theta, marks=marks, verdict=verdict, by_family=fam,
                   wrong_rates=summary,
                   median_ms=(statistics.median(lat) if lat else None),
                   p90_ms=(sorted(lat)[int(0.9 * len(lat))] if lat else None),
                   max_ms=(max(lat) if lat else None),
                   median_gc_ms=(statistics.median(gclat) if gclat else None),
                   rows=[{k: v for k, v in r.items()
                          if k not in ("a_frames", "a261b_frames", "a265_frames")}
                         for r in rows],
                   details=details, theta_curve_A=curve)
    finally:
        S.rel_ok = _ORIG_REL_OK
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--seal", default=None)
    ap.add_argument("--dev", default=None)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--theta", type=float, required=True)
    ap.add_argument("--pyes", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--no-sha", action="store_true")
    a = ap.parse_args()
    if a.dev:
        items = P.load_dev(a.dev)
    else:
        items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            # Dev keys carry the qbuild --src prefix; strip it once.
            key = str(cid)
            if a.src and key.startswith(a.src + ":"):
                key = key[len(a.src) + 1:]
            pmap[key] = (float(v["p"]), float(v.get("ms", 0.0)))
    res = score(items, apd["preds"], json.loads(Path(a.b_preds).read_text()),
                pmap, a.theta)
    res["gpu_summary"] = apd["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(theta=a.theta, marks=res["marks"],
                           verdict=res["verdict"],
                           median_ms=res["median_ms"],
                           wrong_rates=res["wrong_rates"]), indent=1))


if __name__ == "__main__":
    main()
