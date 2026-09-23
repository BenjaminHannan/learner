#!/usr/bin/env python3
"""Merge 138k scorer: K1-K8 from the registered run folder.

usage: claude_merge138k_score.py <run dir> <predicted_moves138k.json> <out.json>

Run-dir layout (written by the registered commands in PASSMARKS.md):
  probe/{j,k}-{p3-dialogs,p3c-restart2,p3d-ghost}.json   (claude_merge138k_probe.py)
  m220/r1-fixed.json r2-fixed.json r3-fixed.json         (claude_merge138k_marks220.py)
  sd/SUITEDIFF218-SUMMARY.json + *-diff.json              (fable_suitediff218.py, 5 suites)
  rt143nogate-k.json                                      (claude_merge138k_rt143nogate.py)
  smoke-{j,k}.json                                        (fable_sleepsmoke206.py)
  mk-{j,k}/soak-report.json, p2-report.json, soak-tmp/daemon/notebook
  lat-{j,k}-{1,2,3}.json                                  (claude_merge138k_latency.py)
  bench{1,2,3}/bench-*-rows.jsonl                         (fable_suitediff218.py --only bench)
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

VER = ROOT / "artifacts/claude-verify-20260922/138j"
J138 = ROOT / "artifacts/fable-agent138j-20260922"


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def taught_set(nbdir: Path) -> list:
    """Active taught triples from the log alone (plain contract notebook)."""
    import fable_loop90_agent as L90
    import fable_notebook_contract as C
    nb = C.Notebook(nbdir)
    return sorted(tuple(t) for t in L90.notebook_triples(nb))


def main() -> int:
    run, predp, outp = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    pred = jl(predp)
    marks: dict = {}
    moves: list = []

    # ---------------- K1 ghost + duplicates after every restart
    kg = jl(run / "probe/k-p3d-ghost.json")["rows"][0]
    kc = jl(run / "probe/k-p3c-restart2.json")["rows"]
    ghost_replies = [t["reply"] for t in kg["turns"]
                     if t["reply"].startswith("Oriel's boss is ")]
    ghost_stored = [s for s in kg["stored"] if s[0] == "Oriel"]
    audits = [a for r in [kg] + kc for a in r["audits"]]
    k1_dup_ok = sum(1 for a in audits if a["dup_ok"])
    marks["K1"] = {"ghost_positive_replies": len(ghost_replies),
                   "ghost_stored": len(ghost_stored),
                   "audits_ok": k1_dup_ok, "audits": len(audits),
                   "pass": (not ghost_replies and not ghost_stored
                            and k1_dup_ok == len(audits))}

    # ---------------- K2 220's own marks at 220's level
    r1 = jl(run / "m220/r1-fixed.json")
    r2 = jl(run / "m220/r2-fixed.json")
    r3 = jl(run / "m220/r3-fixed.json")
    marks["K2"] = {"R1": f"{r1['equal']}/{r1['comparisons']}",
                   "R2": f"{r2['pass']}/{r2['n_cases']}",
                   "R3": f"{r3['histories_identical']}/{r3['n_histories']}",
                   "pass": (r1["equal"] == r1["comparisons"] == 60
                            and r2["pass"] == r2["n_cases"] == 11
                            and r3["histories_identical"]
                            == r3["n_histories"] == 20)}

    # ---------------- K3 frozen suites vs 138j rows (+ rt143 no-gate)
    summ = jl(run / "sd/SUITEDIFF218-SUMMARY.json")
    sd_moves = {}
    bad = 0
    for s in ("rt136", "rt143", "sessions152", "bench", "marks123"):
        d = jl(run / f"sd/{s}-diff.json")
        sd_moves[s] = d["n_moves"]
        bad += d["new_wrong"] + d["new_wrong_write"] + d["new_junk"]
        for m in d.get("moves", []):
            moves.append({"mark": "K3", "suite": s, "move": m})
    ng_base = jl(VER / "rt143-138j-g1.json")
    ng_k = jl(run / "rt143nogate-k.json")
    ng_moves = [b["id"] for b, k in zip(ng_base, ng_k) if b != k]
    for i in ng_moves:
        moves.append({"mark": "K3", "suite": "rt143-nogate", "move": i})
    k3_pred = set(pred.get("K3", {}).keys())
    k3_unpred = [m for m in moves if m["mark"] == "K3"
                 and str(m["move"] if isinstance(m["move"], str)
                         else m["move"].get("id")) not in k3_pred]
    marks["K3"] = {"moves": sd_moves, "rt143_nogate_moves": len(ng_moves),
                   "rt143_nogate_n": len(ng_k), "gate": summ["gate"],
                   "skipped": summ.get("skipped", {}),
                   "new_bad": bad, "unpredicted": len(k3_unpred),
                   "pass": (bad == 0 and summ["gate"] == "GATE: clean"
                            and not summ.get("skipped")
                            and not k3_unpred)}

    # ---------------- K4 15 fresh dialogs vs 138j (same driver)
    pj = jl(run / "probe/j-p3-dialogs.json")["rows"]
    pk = jl(run / "probe/k-p3-dialogs.json")["rows"]
    rep_moves, ev_moves, stored_moves = [], [], []
    for a, b in zip(pj, pk):
        for n, (ta, tb) in enumerate(zip(a["turns"], b["turns"])):
            if ta["reply"] != tb["reply"]:
                rep_moves.append(f"d{a['dialog']:02d}t{n:02d}")
            if ta["events"] != tb["events"]:
                ev_moves.append(f"d{a['dialog']:02d}t{n:02d}")
        if a["stored"] != b["stored"]:
            stored_moves.append(f"d{a['dialog']:02d}")
        # a "bad write" = a stored triple in 138k that 138j does not hold
        # at all (set difference), or a changed per-turn event count.
    bad_writes = sum(1 for a, b in zip(pj, pk)
                     for t in b["stored"] if t not in a["stored"]) \
        + len(ev_moves)
    p4 = pred.get("K4", {})
    unpred4 = ([m for m in rep_moves if m not in p4]
               + [m for m in stored_moves if m not in p4])
    for m in rep_moves:
        moves.append({"mark": "K4", "move": m, "kind": "reply"})
    for m in stored_moves:
        moves.append({"mark": "K4", "move": m, "kind": "stored"})
    marks["K4"] = {"reply_moves": rep_moves, "stored_moves": stored_moves,
                   "event_count_moves": ev_moves, "bad_writes": bad_writes,
                   "unpredicted": unpred4, "n_dialogs": len(pk),
                   "pass": bad_writes == 0 and not unpred4}
    # K1/K4 side: p3c/p3d moves vs 138j (listed, predicted in K1 block)
    for tag in ("p3c-restart2", "p3d-ghost"):
        aj = jl(run / f"probe/j-{tag}.json")["rows"]
        ak = jl(run / f"probe/k-{tag}.json")["rows"]
        for a, b in zip(aj, ak):
            for n, (ta, tb) in enumerate(zip(a["turns"], b["turns"])):
                if ta["reply"] != tb["reply"]:
                    moves.append({"mark": "K1", "move":
                                  f"{tag}:d{a['dialog']:02d}t{n:02d}",
                                  "kind": "reply", "j": ta["reply"],
                                  "k": tb["reply"]})
            if a["stored"] != b["stored"]:
                moves.append({"mark": "K1", "move":
                              f"{tag}:d{a['dialog']:02d}", "kind": "stored",
                              "j": a["stored"], "k": b["stored"]})
    p1 = pred.get("K1", {})
    unpred1 = [m["move"] for m in moves if m["mark"] == "K1"
               and m["move"] not in p1]
    marks["K1"]["unpredicted"] = unpred1
    marks["K1"]["pass"] = marks["K1"]["pass"] and not unpred1

    # ---------------- K5 sleep smoke, same marks as 138j
    sj, sk = jl(run / "smoke-j.json"), jl(run / "smoke-k.json")
    drop = {"label", "agent", "config", "root", "seconds", "elapsed",
            "wall_s", "report", "started", "finished", "pid"}

    def core(d):
        return {k: v for k, v in d.items() if k not in drop}
    diff5 = sorted(k for k in set(core(sj)) | set(core(sk))
                   if core(sj).get(k) != core(sk).get(k))
    marks["K5"] = {"differing_fields": diff5, "pass": not diff5}

    # ---------------- K6 soak (3 kill-9 restarts) + p2 vs 138j
    mj, mk = J138 / "marks138j", run / "mk-k"
    soj, sok = jl(mj / "soak-report.json"), jl(mk / "soak-report.json")
    keys = ("completed", "kill9s", "lost", "wrong", "doubled_replies",
            "audit_lost_pairs", "audit_dup_pairs", "audit_wrong_pairs")
    soak_diff = [k for k in keys if soj.get(k) != sok.get(k)]
    nbj = taught_set(mj / "soak-tmp/daemon/notebook")
    nbk = taught_set(mk / "soak-tmp/daemon/notebook")
    p2j, p2k = jl(mj / "p2-report.json"), jl(mk / "p2-report.json")
    p2_moves = [a.get("id", i) for i, (a, b) in
                enumerate(zip(p2j.get("rows", []), p2k.get("rows", [])))
                if a != b]
    marks["K6"] = {"soak_field_diffs": soak_diff,
                   "soak_counts_k": {k: sok.get(k) for k in keys},
                   "soak_nb_triples_j": len(nbj),
                   "soak_nb_triples_k": len(nbk),
                   "soak_nb_identical": nbj == nbk,
                   "p2_row_moves": p2_moves,
                   "pass": (not soak_diff and nbj == nbk
                            and not p2_moves)}

    # ---------------- K7 latency
    lj = [x for i in (1, 2, 3)
          for x in jl(run / f"lat-j-{i}.json")["times_ms"]]
    lk = [x for i in (1, 2, 3)
          for x in jl(run / f"lat-k-{i}.json")["times_ms"]]
    mdj, mdk = statistics.median(lj), statistics.median(lk)
    marks["K7"] = {"median_j_ms": round(mdj, 3), "median_k_ms": round(mdk, 3),
                   "delta_ms": round(mdk - mdj, 3), "n_j": len(lj),
                   "n_k": len(lk), "pass": (mdk - mdj) <= 5.0}

    # ---------------- K8 bench byte-identical x3
    names = sorted(p.name for p in (run / "bench1").glob("bench-*-rows.jsonl"))
    same = 0
    for nm in names:
        blobs = [(run / f"bench{i}" / nm).read_bytes() for i in (1, 2, 3)]
        same += int(blobs[0] == blobs[1] == blobs[2])
    marks["K8"] = {"files": len(names), "identical": same,
                   "rows": sum((run / "bench1" / nm).read_text().count("\n")
                               for nm in names),
                   "pass": len(names) == 4 and same == 4}

    verdict = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    res = {"verdict": verdict, "marks": marks, "moves": moves}
    Path(outp).write_text(json.dumps(res, indent=1, ensure_ascii=False),
                          encoding="utf-8")
    print(f"VERDICT {verdict}")
    for k, v in marks.items():
        print(k, "PASS" if v["pass"] else "FAIL",
              json.dumps({a: b for a, b in v.items() if a != "pass"},
                         ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
