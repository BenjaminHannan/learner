#!/usr/bin/env python3
"""Exp 267 -- diagnostic scorer: one ear run, three checkers, no guard.

Arms from the single GPU ear-preds file + recorded checker answers:
  C0 ear only (brake -> canon; shows what the checkers remove and cost)
  C1 brake -> canon -> YES/NO prompt B @0.25 (261b exactly)
  C2 brake -> canon -> QA value+owner+relation (264 exactly)
  C3 brake -> canon -> PICK-THE-READING (save iff model picks reading 1)
ASK frames never checked. Matching = 261b's sealed scorer with Ruling 1
(imported, not reimplemented). No verdict: this is a diagnostic.

python claude_diag267_score.py --dev DEV.jsonl --seal SEAL --a-preds EAR.json --pyes C1.json --qa C2.json --c3 C3.json --out O.json"""
import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261b_scoremain as M261B  # noqa: E402
import claude_earcheck264_arms as BA  # noqa: E402
import claude_diag267_c3 as C3  # noqa: E402

STATEMENT = ["plain_teach", "plural_relative", "typo_filler",
             "relation_trap", "stale_value"]
SAVE_FAMS = STATEMENT + ["no_save"]
QUESTION = ["questions"]
EXTRA = {"lower", "typo", "noq", "correction", "filler"}


def load_dev(path, seal):
    raw = Path(path).read_bytes()
    want = None
    for ln in Path(seal).read_text().splitlines():
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1].endswith("dev.jsonl"):
            want = parts[0]
    if want and hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit("DEV-SHA-MISMATCH")
    items = []
    for d in (json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()):
        assert set(d) == {"id", "family", "turn", "gold", "clear", "notes"}, set(d)
        gold = []
        for g in d["gold"]:
            if g["act"] == "ASK" and g.get("chain"):
                hops = [str(x).strip() for x in g["chain"]]
                aliases = [[str(y) for y in x] for x in g["chain_aliases"]]
            else:
                hops, aliases = [str(g["relation"]).strip()], [[str(x) for x in g["relation_aliases"]]]
            fr = dict(act=g["act"], subject=str(g["subject"]),
                      relation=hops, aliases=aliases)
            if g["act"] == "TEACH":
                fr["value"] = str(g["value"])
            gold.append(fr)
        toks = d["notes"].split()
        tags = sorted({t for t in toks if re.fullmatch(r"R\d\w*", t)} | (set(toks) & EXTRA))
        items.append(dict(id=d["id"], family=d["family"], turn=d["turn"],
                          tags=tags, gold=gold))
    return items


def c3_split(kept_canon, picks):
    """picks: {k: (text, ms)}. Returns (saved, unsure, ms_list, pick_list)."""
    saved, unsure, ms_list, pick_list = [], [], [], []
    ti = 0
    for f in kept_canon:
        if f.get("act") != "TEACH":
            saved.append(f)
            continue
        rec = picks.get(ti)
        ti += 1
        if rec is None:
            unsure.append(dict(f, why="C3_MISSING", pick=None))
            ms_list.append(0.0)
            pick_list.append(None)
            continue
        text, ms = rec
        ok, pick = C3.c3_decide(text)
        ms_list.append(float(ms))
        pick_list.append(pick)
        if ok:
            saved.append(f)
        else:
            unsure.append(dict(f, why="C3_NOT1", pick=pick))
    return saved, unsure, ms_list, pick_list


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score(items, apreds, c1map, c2map, c3map):
    S.rel_ok = M261B.rel_ok_narrower
    try:
        rows, agg = [], {}
        details = []
        for it in items:
            rec = apreds[it["id"]]
            arms0 = A261.base_arms(rec["raw"], it["turn"], rec["greedy_lp"], rec["beams"])
            kept_canon = arms0["kept_canon"]
            n_teach = sum(1 for f in kept_canon if f.get("act") == "TEACH")
            pl = [c1map.get(f"{it['id']}#t{k}", (0.0, 0.0)) for k in range(n_teach)]
            saved1, _ = A261.checker_split(kept_canon, [p for p, _ in pl], BA.THETA_261B)
            qd = {}
            for k in range(n_teach):
                parts = {}
                for q in ("value", "owner", "relation"):
                    cid = f"{it['id']}#t{k}#q{q}"
                    if cid in c2map:
                        parts[q] = c2map[cid]
                if len(parts) == 3:
                    qd[k] = (parts["value"][0], parts["owner"][0],
                             parts["relation"][0],
                             parts["value"][1] + parts["owner"][1] + parts["relation"][1])
            saved2, unsure2, ms2 = BA.qa_split(kept_canon, qd)
            p3 = {k: c3map[f"{it['id']}#t{k}"] for k in range(n_teach)
                  if f"{it['id']}#t{k}" in c3map}
            saved3, unsure3, ms3, picks3 = c3_split(kept_canon, p3)
            ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
            per = dict(
                C0=(arms0["A_brake"], 0.0, None),
                C1=(saved1, sum(m for _, m in pl), None),
                C2=(saved2, sum(ms2), [f for f in unsure2]),
                C3=(saved3, sum(ms3), picks3),
            )
            stmt = it["family"] in STATEMENT
            row = dict(id=it["id"], family=it["family"], tags=it["tags"], arms={})
            for arm, (fr, cms, extra) in per.items():
                th, tx, tn = S.match(fr, it["gold"], "TEACH")
                ah, ax, an = S.match(fr, it["gold"], "ASK")
                saved_n = sum(1 for f in fr if f["act"] == "TEACH")
                ms = round(ear_ms + cms, 2)
                row["arms"][arm] = dict(teach_hit=th, teach_gold=tn,
                                        held=(tn - th) if stmt else 0,
                                        wrong=len(tx), ask_hit=ah,
                                        ask_gold=an, ask_extra=len(ax),
                                        saved=saved_n,
                                        turns_wrong=(1 if tx and stmt else 0),
                                        ms=ms,
                                        exact=(th == tn and ah == an and not tx and not ax))
                keys = [("family", it["family"])] + [
                    ("tag", f"{t}:{'stmt' if stmt else it['family']}") for t in it["tags"]]
                for kind, key in keys:
                    tgt = agg.setdefault(arm, {}).setdefault(key, dict(
                        n=0, teach_hit=0, teach_gold=0, held=0, wrong=0,
                        saved=0, turns_wrong=0, ask_hit=0, ask_gold=0,
                        exact=0, ms=[]))
                    tgt["n"] += 1
                    tgt["teach_hit"] += th
                    tgt["teach_gold"] += tn
                    if stmt:
                        tgt["held"] += tn - th
                    tgt["wrong"] += len(tx)
                    tgt["saved"] += saved_n
                    tgt["turns_wrong"] += 1 if (tx and stmt) else 0
                    tgt["ask_hit"] += ah
                    tgt["ask_gold"] += an
                    tgt["exact"] += row["arms"][arm]["exact"]
                    tgt["ms"].append(ms)
            kept_list = [f for f in arms0["A_brake"] if f.get("act") == "TEACH"]
            for k, f in enumerate(kept_list):
                s1 = any(f == s for s in saved1)
                s2 = any(f == s for s in saved2)
                s3 = any(f == s for s in saved3)
                th1, tx1, _ = S.match([f], it["gold"], "TEACH")
                if (not s1) or (not s2) or (not s3) or tx1:
                    p = float(pl[k][0]) if k < len(pl) else None
                    h2 = next((h for h in unsure2
                               if {kk: vv for kk, vv in h.items()
                                   if kk not in ("why", "qa_failed", "a_value",
                                                 "a_owner", "a_relation")} == f), {})
                    details.append(dict(
                        id=it["id"], family=it["family"], tags=it["tags"],
                        status="WRONG" if tx1 else "HELD-some",
                        c1=("saved" if s1 else f"held p={p}"),
                        c2=("saved" if s2 else "held:" + "+".join(h2.get("qa_failed", ["?"]))),
                        c3=("saved" if s3 else f"pick={picks3[k] if k < len(picks3) else None}"),
                        gold_hit=(th1 > 0)))
            rows.append(row)

        def tot(arm, fams, key):
            return sum(agg.get(arm, {}).get(f, {}).get(key, 0) for f in fams)

        marks = {}
        for arm in ("C0", "C1", "C2", "C3"):
            hit = tot(arm, STATEMENT, "teach_hit")
            gold = tot(arm, STATEMENT, "teach_gold")
            held = tot(arm, STATEMENT, "held")
            wrong = tot(arm, SAVE_FAMS, "wrong")
            saved = tot(arm, SAVE_FAMS, "saved")
            nturns = sum(agg.get(arm, {}).get(f, {}).get("n", 0) for f in SAVE_FAMS)
            tw = tot(arm, SAVE_FAMS, "turns_wrong")
            lat = [m for f in SAVE_FAMS + QUESTION
                   for m in agg.get(arm, {}).get(f, {}).get("ms", [])]
            lat_s = sorted(lat)
            marks[arm] = dict(
                teach_hit=hit, teach_gold=gold,
                recall_pct=pct(hit, gold), held_true=held,
                held_pct=pct(held, gold), wrong_saves=wrong,
                saved_facts=saved,
                per_fact=round(wrong / saved, 4) if saved else None,
                turns_wrong=tw,
                per_turn=round(tw / nturns, 4) if nturns else None,
                ask_hit=tot(arm, QUESTION, "ask_hit"),
                ask_gold=tot(arm, QUESTION, "ask_gold"),
                ask_pct=pct(tot(arm, QUESTION, "ask_hit"),
                            tot(arm, QUESTION, "ask_gold")),
                median_ms=round(statistics.median(lat), 1) if lat else None,
                p90_ms=round(lat_s[int(0.9 * len(lat_s))], 1) if lat_s else None,
                max_ms=round(max(lat), 1) if lat else None)
        fams = {}
        for arm, d in agg.items():
            fams[arm] = {k: dict(v, ms=None) for k, v in d.items()}
        return dict(marks=marks, by_family=agg, rows=rows, details=details)
    finally:
        S.rel_ok = M261B._ORIG_REL_OK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--pyes", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--c3", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = load_dev(a.dev, a.seal)
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    c1d = json.loads(Path(a.pyes).read_text(encoding="utf-8"))
    c1map = {cid: (float(v["p"]), float(v.get("ms", 0.0)))
             for cid, v in c1d["checks"].items()}
    c2d = json.loads(Path(a.qa).read_text(encoding="utf-8"))
    c2map = {cid: (v["text"], float(v.get("ms", 0.0)))
             for cid, v in c2d["checks"].items()}
    c3d = json.loads(Path(a.c3).read_text(encoding="utf-8"))
    c3map = {cid: (v["text"], float(v.get("ms", 0.0)))
             for cid, v in c3d["checks"].items()}
    res = score(items, apd["preds"], c1map, c2map, c3map)
    res["gpu_summary"] = apd["summary"]
    res["c1_summary"] = c1d["summary"]
    res["c2_summary"] = c2d["summary"]
    res["c3_summary"] = c3d["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["marks"], indent=1))


if __name__ == "__main__":
    main()
