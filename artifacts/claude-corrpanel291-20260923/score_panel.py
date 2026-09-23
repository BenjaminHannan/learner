#!/usr/bin/env python3
"""Scorer for corrpanel291. Implements 252 scoring + false_claim. Used unchanged by builders."""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

FAMILIES = {"verb_denial":8,"possessive_denial":8,"contextual_denial":8,"contextual_correction":8,"explicit_correction":8,"tail_denial":8,"opener_teach":8,"opener_correction":8,"unstored_denial":6,"ambiguous":6,"question_trap":8,"control":12}
PANEL_FIELDS = ["id","family","setup","turn","followup","stated_facts","expect_gone","expect_store","gold_followup","note"]
BASE_FIELDS = ["id","setup_replies","stored_after_setup","turn_reply","stored_after_turn","followup_reply","stored_after_followup","base_right","base_wrong_value","base_false_claim"]

def T(ts):
    return {tuple(str(p).lower() for p in t) for t in (ts or [])}

def ww(v,t):
    return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)', t or '', re.I) is not None

def score_one(p, r, base_row=None):
    sas, sat, saf = T(r["stored_after_setup"]), T(r["stored_after_turn"]), T(r["stored_after_followup"])
    es, eg = T(p["expect_store"]), T(p["expect_gone"])
    junk = not sat <= (sas | es)
    store_ok = (es <= sat) and (not (eg & sat)) and (not junk)
    fr = r["followup_reply"] or ""
    if p["gold_followup"]:
        parts = [x.strip() for x in p["gold_followup"].split(";")]
        fok = all(x.lower() in fr.lower() for x in parts) and not re.match(r"\s*i (don't|do not) know", fr, re.I)
    else:
        gone_vals=[g[2] for g in p["expect_gone"]]
        fok = not any(ww(v,fr) for v in gone_vals)
    gone_vals=[g[2] for g in p["expect_gone"]]
    wrong = any(ww(v,fr) for v in gone_vals)
    fw = (saf != sat)
    still = sas & sat
    tr = r["turn_reply"] or ""
    claim_word = ("don't have" in tr.lower() or "do not have" in tr.lower() or "removed" in tr.lower() or "updated" in tr.lower() or "deleted" in tr.lower() or "changed" in tr.lower())
    fclaim=False
    if claim_word:
        for t in still:
            if ww(list(t)[2], tr):
                fclaim=True; break
    right = bool(store_ok and fok and (not fw) and (not fclaim))
    if p["family"]=="control" and base_row is not None:
        right = bool(right and r["turn_reply"]==base_row["turn_reply"] and r["followup_reply"]==base_row["followup_reply"])
    return {"right":right,"wrong":wrong,"junk":junk,"fw":fw,"fclaim":fclaim,"store_ok":store_ok,"fok":fok}

def load_jsonl(p):
    return [json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]

def main():
    if len(sys.argv)!=3:
        print("usage: score_panel.py panel.jsonl rows.jsonl"); sys.exit(2)
    pp, rp = Path(sys.argv[1]), Path(sys.argv[2])
    # schema check
    try:
        P = load_jsonl(pp); R = {r["id"]:r for r in load_jsonl(rp)}
    except Exception as e:
        print("SCHEMA-MISMATCH"); sys.exit(3)
    if len(P)!=96:
        print("SCHEMA-MISMATCH"); sys.exit(3)
    c = Counter(p["family"] for p in P)
    for f,n in FAMILIES.items():
        if c[f]!=n:
            print("SCHEMA-MISMATCH"); sys.exit(3)
    if [p["id"] for p in P]!=[f"c291-{i:03d}" for i in range(1,97)]:
        print("SCHEMA-MISMATCH"); sys.exit(3)
    for p in P:
        if list(p.keys())!=PANEL_FIELDS:
            print("SCHEMA-MISMATCH"); sys.exit(3)
        if p["id"] not in R:
            print("SCHEMA-MISMATCH"); sys.exit(3)
    for rid,r in R.items():
        if list(r.keys())!=BASE_FIELDS:
            print("SCHEMA-MISMATCH"); sys.exit(3)
    # base rows for control byte-identical: use rp itself as reference when scoring base; builders pass base file separately? Here control checks self-consistency only.
    # For builder use: they pass their rows; control additionally compared to sealed base file if --base given? Keep simple: control right requires store/followup only here; builder harness compares byte-identical separately via base file.
    # To enforce byte-identical in builder runs, load sealed base if present alongside panel.
    sealed_base = pp.parent / "base138nb.jsonl"
    B = None
    if sealed_base.exists() and str(sealed_base.resolve())!=str(rp.resolve()):
        try: B = {r["id"]:r for r in load_jsonl(sealed_base)}
        except Exception: B=None
    per=defaultdict(Counter); tot=Counter()
    for p in P:
        r=R[p["id"]]
        b = (B[p["id"]] if B and p["id"] in B else None)
        s=score_one(p,r,b)
        f=p["family"]
        per[f]["n"]+=1; per[f]["right"]+=s["right"]; per[f]["wrong"]+=s["wrong"]; per[f]["junk"]+=s["junk"]; per[f]["fw"]+=s["fw"]; per[f]["fclaim"]+=s["fclaim"]
        tot["n"]+=1; tot["right"]+=s["right"]; tot["wrong"]+=s["wrong"]; tot["junk"]+=s["junk"]; tot["fw"]+=s["fw"]; tot["fclaim"]+=s["fclaim"]
    for f in FAMILIES:
        print(f"{f:22s} {per[f]['right']:2d}/{per[f]['n']:2d} wrong {per[f]['wrong']} junk {per[f]['junk']} fw {per[f]['fw']} fclaim {per[f]['fclaim']}")
    print(f"TOTAL right {tot['right']}/{tot['n']} wrong {tot['wrong']} junk {tot['junk']} fw {tot['fw']} fclaim {tot['fclaim']}")

if __name__=="__main__":
    main()
