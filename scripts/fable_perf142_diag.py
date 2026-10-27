#!/usr/bin/env python3
"""Exp 142 diag (UNREGISTERED profiling): 128's diag approach on loop134.

Builds 1k/5k/10k/15k taught facts from the seed-93 soak plan through the
loop134 daemon, benching teach/correct/ask per-turn CPU (process_time) plus
function-level attribution, and names every O(n)-per-turn scan with file:line.

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \\
  --python 3.12 --with torch --with numpy python -B \\
  scripts/fable_perf142_diag.py --out artifacts/fable-perf142-20260922/diag134.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop134_agent as L134
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
    ap.add_argument("--out", default="artifacts/fable-perf142-20260922/diag134.json")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    turns, _ = S108.build_plan(20000, 93)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="fable_perf142_diag134_"))
    daemon = L134.Loop134Daemon(tmp, cfg={"sleep_threshold": 10**9},
                                idle_seconds=3600.0)
    loop = daemon.loop
    ti = 0
    res = {"sizes": {}, "scans": {}, "meta": {"seed": 93, "samples": N_SAMPLE,
                                              "agent": "loop134"}}
    def n_taught():
        return sum(1 for f in loop.nb.facts.values() if f.get("source")=="taught")
    for tgt in SIZES:
        synth = 0
        while n_taught() < tgt:
            if ti < len(turns):
                t = turns[ti]; ti += 1
                if t["kind"] == "ask":
                    continue
                loop.turn(t["text"])
            else:
                f0 = next(f for f in loop.nb.facts.values()
                          if f.get("source")=="taught" and f.get("relation") in ("city","color","food")
                          and loop.nb.active(f["fact_id"]) and "literal" in f["value"])
                nm = loop.nb.entities[f0["subject"]]
                loop.turn(f"Actually, {nm}'s {f0['relation']} is {f0['value']['literal']}x{synth}.")
                synth += 1
        nfacts = n_taught()
        st = []
        k = ti
        while len(st) < N_SAMPLE and k < len(turns):
            if turns[k]["kind"] == "teach":
                st.append(turns[k]["text"])
            k += 1
        for i in range(len(st), N_SAMPLE):
            st.append(f"Diag{tgt}P{i:03d}'s city is DiagCity{tgt}{i:03d}.")
        cand = [f for f in loop.nb.facts.values()
                if f.get("source")=="taught" and f.get("relation") in ("city","color","food")
                and loop.nb.active(f["fact_id"]) and "literal" in f["value"]][:N_SAMPLE]
        sc = []
        for i, f in enumerate(cand):
            nm = loop.nb.entities[f["subject"]]
            sc.append(f"Actually, {nm}'s {f['relation']} is {f['value']['literal']}rD{i}t{tgt}.")
        seen = [f for f in loop.nb.facts.values()
                if f.get("source")=="taught" and loop.nb.active(f["fact_id"])][:2000]
        sa = []
        for i in range(N_SAMPLE):
            f = seen[(i*37) % len(seen)]
            sa.append(f"What is {loop.nb.entities[f['subject']]}'s {f['relation']}?")
        def bench(texts):
            xs = []
            for tx in texts:
                _, dt = cpu(loop.turn, tx)
                xs.append(dt*1000.0)
            return xs
        teach_ms = bench(st)
        corr_ms = bench(sc)
        ask_ms = bench(sa)
        nb = loop.nb
        t_cur = []
        for f in list(nb.facts.values())[:5]:
            _, dt = cpu(nb.current, f["subject"], f["relation"])
            t_cur.append(dt*1000.0)
        from fable_loop90_agent import notebook_triples
        _, dt_trip = cpu(notebook_triples, nb)
        from fable_fix77_core import filtered_view77
        rel0 = list(nb.facts.values())[0]["relation"]
        _, dt_filt = cpu(filtered_view77, nb, rel0, {})
        _, dt_save = cpu(loop._save)
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
    r = {}
    for k in ("teach","correct","ask"):
        r[k] = round(res["sizes"]["15000"]["p50"][k]/max(1e-9,res["sizes"]["1000"]["p50"][k]),2)
    res["ratio_15k_over_1k_p50"] = r
    res["scans"] = {
      "S1": "scripts/fable_notebook_contract.py:244 current() scans self.facts",
      "S2": "scripts/fable_listening_m1.py:61 _relation() scans self.nb.events",
      "S5": "scripts/fable_fix77_core.py:157 filtered_view77() scans nb.facts per hop; :244 known() same",
      "S6": "scripts/fable_agent_loop.py:262 _save() dumps whole experience 2x/turn",
      "S7": "scripts/fable_loop102_agent.py:405 process_file set(facts)/set(entities) copies",
      "T1": "scripts/fable_loop90_agent.py:109 notebook_triples() per hear (:133; :76/:182 on ? via 113b/113)",
      "T2": "scripts/fable_bench92_english_arm.py:198 compose_n_hop() per ? turn (:211 ents, :145 mentions, :222 walks)",
      "T3": "scripts/fable_loop113_agent.py:109 _walk_nodes() + :123 compound_subject_hit() per ? frame",
      "T4": "scripts/fable_bench73_english_arm.py:246 compose_question() MQuAKE section per ? turn",
      "T5": "scripts/fable_loop90_agent.py:160 _teach_action() per teach (chain :146 + loop121 :150)",
      "T6": "scripts/fable_loop102_agent.py:204 _resolve_forget_name() prefix scan per forget turn (kept)",
    }
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("RATIOS15k/1k", r, flush=True)
    print(f"wrote {out}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
