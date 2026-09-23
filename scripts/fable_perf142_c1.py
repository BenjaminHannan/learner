#!/usr/bin/env python3
"""Exp 142 S1 (REGISTERED): per-turn CPU (process_time) at 1k vs 15k facts.

--agent loop142|loop134 (default loop142). Same estimator as exp-128 C1
(seed-93 plan, 25 samples/kind, process_time in-process).

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \\
  --python 3.12 --with torch --with numpy python -B \\
  scripts/fable_perf142_c1.py --agent loop142 \\
  --out artifacts/fable-perf142-20260922/c1-142.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_soak108_run as S108

N_SAMPLE = 25

def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s)-1, max(0, int(q*len(s))))]

def build(agent: str, state_dir: str):
    cfg = {"sleep_threshold": 10**9, "state_dir": state_dir}
    if agent == "loop142":
        import fable_loop142_agent as M
        return M.build_agent142(cfg)
    import fable_loop134_agent as M
    return M.build_agent134(cfg)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="loop142", choices=["loop142", "loop134"])
    ap.add_argument("--out", default="artifacts/fable-perf142-20260922/c1-142.json")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    turns, _ = S108.build_plan(20000, 93)
    import tempfile
    loop = build(a.agent, tempfile.mkdtemp(prefix=f"fable_perf142_c1_{a.agent}_"))
    def ntaught():
        return sum(1 for f in loop.nb.facts.values() if f.get("source") == "taught")
    ti = 0
    res = {"agent": a.agent, "sizes": {}}
    for tgt in (1000, 15000):
        synth = 0
        while ntaught() < tgt:
            if ti < len(turns):
                t = turns[ti]; ti += 1
                if t["kind"] == "ask":
                    continue
                loop.turn(t["text"])
            else:
                f0 = next(f for f in loop.nb.facts.values()
                          if f.get("source") == "taught" and f.get("relation") in ("city", "color", "food")
                          and loop.nb.active(f["fact_id"]) and "literal" in f["value"])
                nm = loop.nb.entities[f0["subject"]]
                loop.turn(f"Actually, {nm}'s {f0['relation']} is {f0['value']['literal']}x{synth}.")
                synth += 1
        st = []
        k = ti
        while len(st) < N_SAMPLE and k < len(turns):
            if turns[k]["kind"] == "teach":
                st.append(turns[k]["text"])
            k += 1
        for i in range(len(st), N_SAMPLE):
            st.append(f"C1Diag{tgt}P{i:03d}'s city is C1City{tgt}{i:03d}.")
        cand = [f for f in loop.nb.facts.values()
                if f.get("source") == "taught" and f.get("relation") in ("city", "color", "food")
                and loop.nb.active(f["fact_id"]) and "literal" in f["value"]][:N_SAMPLE]
        sc = []
        for i, f in enumerate(cand):
            nm = loop.nb.entities[f["subject"]]
            sc.append(f"Actually, {nm}'s {f['relation']} is {f['value']['literal']}c1{i}t{tgt}.")
        seen = [f for f in loop.nb.facts.values()
                if f.get("source") == "taught" and loop.nb.active(f["fact_id"])][:2000]
        sa = []
        for i in range(N_SAMPLE):
            f = seen[(i*37) % len(seen)]
            sa.append(f"What is {loop.nb.entities[f['subject']]}'s {f['relation']}?")
        def bench(texts):
            xs = []
            for tx in texts:
                u0 = time.process_time()
                loop.turn(tx)
                xs.append((time.process_time()-u0)*1000.0)
            return xs
        tm, cm, am = bench(st), bench(sc), bench(sa)
        res["sizes"][str(tgt)] = {"taught_facts": ntaught(),
            "p50": {"teach": round(pct(tm,.5),3), "correct": round(pct(cm,.5),3),
                    "ask": round(pct(am,.5),3)},
            "teach_ms": [round(x,2) for x in tm],
            "correct_ms": [round(x,2) for x in cm],
            "ask_ms": [round(x,2) for x in am]}
        print(f"C1 {a.agent} size {tgt}: {res['sizes'][str(tgt)]['p50']}", flush=True)
    r = {k: round(res["sizes"]["15000"]["p50"][k]/max(1e-9, res["sizes"]["1000"]["p50"][k]), 3)
         for k in ("teach", "correct", "ask")}
    res["ratio_15k_over_1k_p50"] = r
    res["pass"] = all(v <= 1.5 for v in r.values())
    res["seconds"] = round(time.time()-t0, 1)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("C1", a.agent, "PASS" if res["pass"] else "FAIL", r, f"({res['seconds']}s)", flush=True)
    return 0 if res["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
