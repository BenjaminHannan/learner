#!/usr/bin/env python3
"""Exp 128 Step 1 (diagnosis, no seal): contention-robust per-turn CPU microbenchmark.

Measures time.process_time() inside the daemon process (immune to the ~12
parallel agents' wall-clock contamination) at notebook sizes 1k/5k/10k/15k
taught facts built from the seed-93 soak plan, for teach/correct/ask turns
separately. Also attributes cost to suspect functions via direct CPU timing.

O(n)-per-turn scans named with file:line (verified by reading the sealed files):
 S1 scripts/fable_notebook_contract.py:246 current() full self.facts scan (called
    by assert_fact:331 and ask:409 per hop)
 S2 scripts/fable_listening_m1.py:61 _relation() full self.nb.events scan per teach/correct
 S3 scripts/fable_loop90_agent.py:109 notebook_triples() full facts+active() scan per hear (line 133)
 S4 scripts/fable_loop90_agent.py:160 Bench73Stage._teach_action() linear facts scan per teach turn
 S5 scripts/fable_fix77_core.py:157 filtered_view77() full nb.facts scan per ask hop; :244 known() same
 S6 scripts/fable_agent_loop.py:262 _save() json.dumps+fsync of whole experience (grows with turns), 2x/turn
 S7 scripts/fable_loop102_agent.py:405 Loop102Daemon.process_file set(nb.facts)/set(nb.entities) copies per turn
 S8 scripts/fable_loop90_agent.py:334 Loop90AgentLoop._save -> advance_seal seal rewrite per save (small, O(1))

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_perf128_diag.py --out artifacts/fable-perf128-20260922/diag.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop102_agent as L102
import fable_soak108_run as S108

SIZES = (1000, 5000, 10000, 15000)
N_SAMPLE = 25

def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s)-1, max(0, int(q*len(s))))]

def cpu(fn, *a, **k):
    t0 = time.process_time()
    r = fn(*a, **k)
    return r, time.process_time()-t0

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/fable-perf128-20260922/diag.json")
    a = ap.parse_args(argv)
    out = Path(a.args_out) if hasattr(a, 'args_out') else Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    turns, meta = S108.build_plan(20000, 93)
    teaches = [t for t in turns if t["kind"]=="teach"]
    asks = [t for t in turns if t["kind"]=="ask"]
    # literal pairs for corrections: derive from plan corrections
    corrects = [t for t in turns if t["kind"]=="correct"]
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="fable_perf128_diag_"))
    daemon = L102.Loop102Daemon(tmp, cfg={"sleep_threshold": 10**9}, idle_seconds=3600.0)
    loop = daemon.loop
    # incremental build: teach first 15000 teaches in plan order
    ti = 0
    res = {"sizes": {}, "scans": {}, "meta": {"seed": 93, "samples": N_SAMPLE}}
    targets = list(SIZES)
    def n_taught():
        return sum(1 for f in loop.nb.facts.values() if f.get("source")=="taught")
    for tgt in targets:
        synth = 0
        while n_taught() < tgt:
            if ti < len(turns):
                t = turns[ti]; ti += 1
                if t["kind"] == "ask":
                    # asks are read-only; skip during build but still advance plan
                    # (teach-before-ask guaranteed, so skipping asks keeps validity)
                    continue
                loop.turn(t["text"])
            else:
                # plan exhausted (max ~14,003 taught FACTs in 20k plan); synthesize
                # extra corrections on known literal pairs (deviation, documented)
                f0 = None
                for f in loop.nb.facts.values():
                    if f.get("source")=="taught" and f.get("relation") in ("city","color","food") and loop.nb.active(f["fact_id"]):
                        if "literal" in f["value"]:
                            f0 = f; break
                nm = loop.nb.entities[f0["subject"]]
                loop.turn(f"Actually, {nm}'s {f0['relation']} is {f0['value']['literal']}x{synth}.")
                synth += 1
        nfacts = n_taught()
        # pick sample turns: fresh teaches (next pool teaches not yet taught),
        # corrections on1k known literal pairs, asks over taught prefix
        st, sc, sa = [], [], []
        # fresh teach samples: next teach texts ahead in plan order
        k = ti
        while len(st) < N_SAMPLE and k < len(turns):
            if turns[k]["kind"] == "teach":
                st.append(turns[k]["text"])
            k += 1
        for i in range(len(st), N_SAMPLE):
            st.append(f"Diag{tgt}P{i:03d}'s city is DiagCity{tgt}{i:03d}.")
        # correction samples: reuse first N_SAMPLE corrects whose (name,rel) taught?
        # safer: correct already-taught literal pairs with brand-new values
        import random
        rng = random.Random(93)
        # find taught literal pairs: scan committed teaches so far (person literal rels)
        # use loop.nb.current to find an active literal fact, then correct it
        cand_pairs = []
        for f in loop.nb.facts.values():
            if f.get("source")=="taught" and f.get("relation") in ("city","color","food") and loop.nb.active(f["fact_id"]):
                v = f["value"]
                if "literal" in v:
                    cand_pairs.append((loop.nb.entities[f["subject"]], f["relation"], str(v["literal"])))
                    if len(cand_pairs) >= 500: break
        for i in range(N_SAMPLE):
            nm, rel, base = cand_pairs[i % len(cand_pairs)]
            sc.append(f"Actually, {nm}'s {rel} is {base}rD{i}t{tgt}.")
        for i in range(N_SAMPLE):
            sa.append(asks[(tgt*7+i*13) % len(asks)]["text"] if False else None)
        # asks must reference taught facts: use plan asks that only reference
        # teaches[0:ti]; filter by trying and keeping ones that answer OK? simpler:
        # build asks from taught prefix directly
        sa = []
        got = 0; j = 0
        # use committed prefix people: ask "What is <Person>'s city?" for taught ones
        seen = []
        for f in loop.nb.facts.values():
            if f.get("source")=="taught" and loop.nb.active(f["fact_id"]):
                seen.append(f)
                if len(seen) > 2000: break
        for i in range(N_SAMPLE):
            f = seen[(i*37) % len(seen)]
            nm = loop.nb.entities[f["subject"]]
            sa.append(f"What is {nm}'s {f['relation']}?")
        def bench(texts):
            xs = []
            reps = []
            for tx in texts:
                _, dt = cpu(loop.turn, tx)
                xs.append(dt*1000.0)
                reps.append(" ".join(loop.turn.__self__.last_records[0].get("text","") for _ in [0]) if False else "")
            return xs
        # interleave kinds to avoid order bias; measure each kind block
        import itertools
        teach_ms = bench(st)
        # corrections mutate state; use unique values so each is a real supersede
        corr_ms = bench(sc)
        ask_ms = bench(sa)
        # function-level attribution at this size (5 reps each, process_time)
        nb = loop.nb
        f_teach = st[0]
        f_ask = sa[0]
        # current() cost
        eids = list(nb.entities.keys())[:1]
        import fable_notebook_contract as C
        t_cur = []
        for f in list(nb.facts.values())[:5]:
            _, dt = cpu(nb.current, f["subject"], f["relation"])
            t_cur.append(dt*1000.0)
        # notebook_triples cost
        from fable_loop90_agent import notebook_triples
        _, dt_trip = cpu(notebook_triples, nb)
        # filtered_view77 cost (one hop)
        from fable_fix77_core import filtered_view77
        rel0 = list(nb.facts.values())[0]["relation"]
        _, dt_filt = cpu(filtered_view77, nb, rel0, {})
        # _save cost (state.json dump of current experience)
        _, dt_save = cpu(loop._save)
        # _relation scan cost
        _, dt_rel = cpu(loop.listening._relation, "city")
        res["sizes"][str(tgt)] = {
            "taught_facts": nfacts, "nb_events": len(nb.events),
            "teach_ms": [round(x,3) for x in teach_ms],
            "correct_ms": [round(x,3) for x in corr_ms],
            "ask_ms": [round(x,3) for x in ask_ms],
            "p50": {k: round(pct(v,0.5),3) for k,v in
                    {"teach":teach_ms,"correct":corr_ms,"ask":ask_ms}.items()},
            "fn_ms": {"current_p50": round(pct(t_cur,0.5),4),
                      "notebook_triples": round(dt_trip*1000.0,3),
                      "filtered_view77": round(dt_filt*1000.0,3),
                      "_save": round(dt_save*1000.0,3),
                      "_relation": round(dt_rel*1000.0,4)},
        }
        print(f"size {tgt} (facts {nfacts}): teach p50 {pct(teach_ms,0.5):.2f}ms "
              f"correct p50 {pct(corr_ms,0.5):.2f}ms ask p50 {pct(ask_ms,0.5):.2f}ms | "
              f"triples {dt_trip*1000:.1f}ms filt {dt_filt*1000:.2f}ms save {dt_save*1000:.2f}ms", flush=True)
    # ratios 15k/1k per kind (p50)
    r = {}
    for k in ("teach","correct","ask"):
        r[k] = round(res["sizes"]["15000"]["p50"][k]/max(1e-9,res["sizes"]["1000"]["p50"][k]),2)
    res["ratio_15k_over_1k_p50"] = r
    res["scans"] = {
      "S1": "scripts/fable_notebook_contract.py:246 current() scans self.facts (assert_fact:331, ask:409/hop)",
      "S2": "scripts/fable_listening_m1.py:61 _relation() scans self.nb.events per teach/correct",
      "S3": "scripts/fable_loop90_agent.py:109 notebook_triples() scans facts+active() per hear (:133, every turn)",
      "S4": "scripts/fable_loop90_agent.py:160 Bench73Stage._teach_action() linear facts scan per teach turn",
      "S5": "scripts/fable_fix77_core.py:157 filtered_view77() scans nb.facts per ask hop; :244 known() same",
      "S6": "scripts/fable_agent_loop.py:262 _save() dumps whole experience 2x/turn (grows with turns)",
      "S7": "scripts/fable_loop102_agent.py:405 process_file set(nb.facts)/set(nb.entities) copies per turn",
      "S8": "scripts/fable_loop90_agent.py:334 _save->advance_seal (:87) seal rewrite per save",
    }
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("RATIOS15k/1k", r, flush=True)
    print(f"wrote {out}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
