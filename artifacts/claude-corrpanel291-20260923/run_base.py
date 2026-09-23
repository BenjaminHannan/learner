#!/usr/bin/env python3
"""Run base 138nb once over corrpanel291. CPU only, one process."""
import copy, json, re, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_loop138nb_agent as NB
import fable_loop90_agent as L90

PANEL = Path(__file__).resolve().parent / "panel.jsonl"
OUT = Path(__file__).resolve().parent / "base138nb.jsonl"
CFG = ROOT / "artifacts" / "claude-merge138nb-20260923" / "loop138nb-config.json"

def active(nb):
    return sorted(list(map(str, x)) for x in L90.notebook_triples(nb))

def T(ts):
    return {tuple(str(p).lower() for p in t) for t in (ts or [])}

def ww(v, t):
    return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)', t or '', re.I) is not None

def score_item(p, stored_setup, stored_turn, stored_follow, turn_reply, follow_reply):
    sas, sat, saf = T(stored_setup), T(stored_turn), T(stored_follow)
    es, eg = T(p["expect_store"]), T(p["expect_gone"])
    junk = not sat <= (sas | es)
    store_ok = (es <= sat) and (not (eg & sat)) and (not junk)
    fr = follow_reply or ""
    if p["gold_followup"]:
        parts = [x.strip() for x in p["gold_followup"].split(";")]
        fok = all(x.lower() in fr.lower() for x in parts) and not re.match(r"\s*i (don't|do not) know", fr, re.I)
    else:
        gone_vals = [g[2] for g in p["expect_gone"]]
        fok = not any(ww(v, fr) for v in gone_vals)
    gone_vals = [g[2] for g in p["expect_gone"]]
    wrong = any(ww(v, fr) for v in gone_vals)
    fw = (saf != sat)
    # false_claim as in corrtail258, adapted: still-stored value + claim of removal/change
    still = sas & sat
    tr = turn_reply or ""
    claim_word = ("don't have" in tr.lower() or "do not have" in tr.lower() or "removed" in tr.lower() or "updated" in tr.lower() or "deleted" in tr.lower() or "changed" in tr.lower())
    false_claim = False
    if claim_word:
        for t in still:
            v = list(t)[2]
            if ww(v, tr):
                false_claim = True
                break
    right = bool(store_ok and fok and (not fw) and (not false_claim))
    return right, wrong, false_claim, junk

def main():
    panel = [json.loads(l) for l in open(PANEL, encoding="utf-8")]
    base_cfg = copy.deepcopy(NB.DEFAULT_CONFIG138NB)
    base_cfg.update(json.loads(open(CFG, encoding="utf-8").read()))
    rows = []
    for p in panel:
        cfg = copy.deepcopy(base_cfg)
        sd = Path(tempfile.mkdtemp(prefix="c291base-"))
        cfg["state_dir"] = str(sd)
        cfg["sleep_threshold"] = 100000
        loop = NB.build_agent138nb(cfg)
        setup_replies, seq = [], []
        for t in p["setup"]:
            rep = " ".join(loop.turn(t))
            setup_replies.append(rep)
        stored_setup = active(loop.nb)
        turn_reply = " ".join(loop.turn(p["turn"]))
        stored_turn = active(loop.nb)
        follow_reply = " ".join(loop.turn(p["followup"]))
        stored_follow = active(loop.nb)
        right, wrong, fclaim, junk = score_item(p, stored_setup, stored_turn, stored_follow, turn_reply, follow_reply)
        rows.append({"id":p["id"],"setup_replies":setup_replies,"stored_after_setup":stored_setup,"turn_reply":turn_reply,"stored_after_turn":stored_turn,"followup_reply":follow_reply,"stored_after_followup":stored_follow,"base_right":right,"base_wrong_value":wrong,"base_false_claim":fclaim})
        shutil.rmtree(sd, ignore_errors=True)
        print(f"{p['id']} {p['family']} right={right} wrong={wrong} fclaim={fclaim} junk={junk}", flush=True)
    with open(OUT,"w",encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")
    print(f"WROTE {OUT} {len(rows)} rows")

if __name__=="__main__":
    main()
