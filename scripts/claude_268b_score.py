#!/usr/bin/env python3
"""Exp 268b scorer: checks the registered run against predicted_moves268b.json.

New file only. CPU only.
usage: claude_268b_score.py <run_dir> <pred_json> <out_json>

Checks (mirrors PASSMARKS.md):
  DEV  every (dialog,turn) move 138nb->268b equals the predicted list
       (70 rerun + 7 supp + 46 new in one dev file), exact stage+reply;
       0 teach/triple changes; 0 new wrong values.
  M2   invpanel138nb (sealed score_panel.py outputs in run/work):
       moves 268b vs 138nb rows == [] predicted; 0 new wrong on 268b;
       every item right on 138nb stays right on 268b; 0 question writes.
       Writes stripped summaries (ids/families/counts only, no reply
       text) to run/inv/*-stripped.json for the push.
  M3   sessions152/bench/marks123 0 moves, GATE clean; rt136 label set
       exactly predicted with 0 new WRONG/WRONG-WRITE/junk beyond the
       inherited 13, direct rows vs 138nb [] ; rt143 0 moves 0 flips vs
       138nb's saved rows; 7 restart/verifier probes rows equal to
       138nb's saved nb-rows (agent field excluded); 0 ghosts, dup ok.
  M4   median(268b reps) - median(138nb reps) <= +5 ms.
Prints PASS/FAIL per mark and writes JSON.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L_RUN = ROOT / "artifacts" / "claude-merge138nb-20260923" / "run"
L136 = L_RUN / "sd136" / "rt136-rows.json"
INVP = ROOT / "artifacts" / "claude-invpanel138nb-20260923"


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p: Path) -> dict:
    return {json.loads(ln)["id"]: json.loads(ln)
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip()}


def dev_moves(b_path: Path, n_path: Path):
    b = jl(b_path)
    n = jl(n_path)
    bi = {(r["dialog"], r["turn"]): r for r in b}
    ni = {(r["dialog"], r["turn"]): r for r in n}
    assert set(bi) == set(ni), "dialog/turn sets differ"
    moves = []
    teach_changes = []
    for k in bi:
        a, c = bi[k], ni[k]
        if (a["reply"], a["stage"], a["triples_after"]) != (
                c["reply"], c["stage"], c["triples_after"]):
            rec = {"id": f"{k[0]}#t{k[1]}", "b_stage": a["stage"],
                   "n_stage": c["stage"], "b_reply": a["reply"],
                   "n_reply": c["reply"]}
            if not a["input"].rstrip().endswith("?"):
                teach_changes.append(rec)
            else:
                moves.append(rec)
    return moves, teach_changes


def main() -> int:
    run = Path(sys.argv[1])
    pred = jl(Path(sys.argv[2]))
    out = Path(sys.argv[3])
    res: dict = {"marks": {}}

    # DEV (one file holds rerun 70 + supp 7 + new 46)
    dm, dt = dev_moves(run / "dev" / "dev-138nb.json",
                       run / "dev" / "dev-268b.json")
    dev_ids = sorted(x["id"] for x in dm)
    dev_ok = (dev_ids == sorted(pred["dev_moves"]) and not dt)
    rec_ok = True
    want = pred["dev_records"]
    nmap = {(r["dialog"], f"t{r['turn']}"): r
            for r in jl(run / "dev" / "dev-268b.json")}
    for did, rec in want.items():
        got = nmap.get((did.split("#")[0], did.split("#")[1]))
        if got is None or got["stage"] != rec["stage"] \
                or got["reply"] != rec["reply"]:
            rec_ok = False
            res.setdefault("dev_record_mismatch", []).append(did)
    # 0 new wrong values on any dev turn
    newwrong = []
    bmap = {(r["dialog"], r["turn"]): r
            for r in jl(run / "dev" / "dev-138nb.json")}
    for (d, t), c in nmap.items():
        a = bmap[(d, t)]
        if c["reply"] != a["reply"] and f"{d}#t{t}" not in want:
            newwrong.append(f"{d}#t{t}")
    res["marks"]["DEV"] = {
        "pass": dev_ok and rec_ok and not newwrong, "moves": dev_ids,
        "teach_changes": dt, "unpredicted_reply_changes": newwrong}

    # M2 invpanel (full scores live in run/work; stripped copies pushed)
    m2ok = True
    m2det: dict = {}
    bscore = {r["id"]: r for r in jl(run / "work" / "inv-138nb-score.json")}
    nscore = {r["id"]: r for r in jl(run / "work" / "inv-268b-score.json")}
    assert set(bscore) == set(nscore), "invpanel id sets differ"
    moves2 = sorted(i for i in bscore
                    if (bscore[i]["right"], bscore[i]["wrong"],
                        bscore[i]["question_wrote"]) !=
                    (nscore[i]["right"], nscore[i]["wrong"],
                     nscore[i]["question_wrote"]))
    m2det["moves_138nb_to_268b"] = moves2
    if moves2 != pred["m2"]["moves"]:
        m2ok = False
    nwrong = sorted(i for i in nscore if nscore[i]["wrong"])
    bwrong = sorted(i for i in bscore if bscore[i]["wrong"])
    new_wrong = sorted(set(nwrong) - set(bwrong))
    m2det["wrong_138nb"] = bwrong
    m2det["wrong_268b"] = nwrong
    m2det["new_wrong"] = new_wrong
    if new_wrong:
        m2ok = False
    lost = sorted(i for i in bscore
                  if bscore[i]["right"] and not nscore[i]["right"])
    m2det["lost_right"] = lost
    if lost:
        m2ok = False
    qwrote = sorted(i for i in nscore if nscore[i]["question_wrote"])
    m2det["question_wrote_268b"] = qwrote
    if qwrote != pred["m2"]["question_wrote"]:
        m2ok = False
    bright = sum(1 for i in bscore if bscore[i]["right"])
    nright = sum(1 for i in nscore if nscore[i]["right"])
    m2det["right_counts"] = {"138nb": bright, "268b": nright,
                             "n_items": len(bscore)}
    for arm, sc in (("138nb", bscore), ("268b", nscore)):
        stripped = [{"id": r["id"], "family": r["family"],
                     "right": r["right"],
                     "right_names": r.get("right_names"),
                     "wrong": r["wrong"],
                     "question_wrote": r["question_wrote"]}
                    for r in sc.values()]
        (run / "inv" / f"inv-{arm}-stripped.json").write_text(
            json.dumps(stripped, indent=1), encoding="utf-8")
    res["marks"]["M2"] = {"pass": m2ok, "detail": m2det}

    # M3 suites
    m3ok = True
    det: dict = {}
    for suite in ("sessions152", "bench", "marks123"):
        d = jl(run / "sd" / f"{suite}-diff.json")
        det[suite] = {"n_moves": d["n_moves"]}
        if d["n_moves"] != 0:
            m3ok = False
    summ = json.loads((run / "sd" / "SUITEDIFF218-SUMMARY.json")
                      .read_text(encoding="utf-8"))
    det["gate"] = summ.get("gate")
    if summ.get("gate") != "GATE: clean":
        m3ok = False
    r136 = jl(run / "sd136" / "rt136-diff.json")
    mv = sorted(m["id"] if isinstance(m, dict) else m
                for m in r136["moves"])
    det["rt136_labels"] = mv
    if mv != sorted(pred["m3"]["rt136_labels"]):
        m3ok = False
    if r136.get("new_wrong", 0) != 0 or r136.get("new_junk", 0) != 0:
        m3ok = False
    if r136.get("new_wrong_write", 0) != 13:
        m3ok = False
    lr = jsonl(L136)
    mr = jsonl(run / "sd136" / "rt136-rows.json")
    direct = sorted(i for i in lr
                    if any(lr[i][k] != mr[i][k]
                           for k in ("reply", "stored", "verdict")))
    det["rt136_direct_vs_138nb"] = direct
    if direct != pred["m3"]["rt136_direct"]:
        m3ok = False
    base = {r["id"]: r for r in jl(L_RUN / "rt143nogate-nb.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-268b.json")}
    moves143 = [cid for cid, r in base.items()
                if any(r[k] != new[cid][k]
                       for k in ("teach_replies", "triples", "reply"))]
    det["rt143_moves"] = moves143
    if moves143 != pred["m3"]["rt143_moves"]:
        m3ok = False
    # inherited bench/marks123 row files byte-identical to 138nb's
    exc_ok = True
    sd138nb = L_RUN / "sd"
    for name in ("bench-bench132_4hop-rows.jsonl",
                 "bench-edit200-rows.jsonl",
                 "bench-new_121_4hop-rows.jsonl",
                 "bench-old_s2fresh_4hop-rows.jsonl"):
        if ((sd138nb / name).read_bytes()
                != (run / "sd" / name).read_bytes()):
            exc_ok = False
            det.setdefault("exc_mismatch", []).append(name)
    det["inherited_rows_identical"] = exc_ok
    if not exc_ok:
        m3ok = False
    # probes vs 138nb's saved nb rows (agent field excluded)
    pmap = {"p3-dialogs": "nb-p3-dialogs",
            "p3c-restart2": "nb-p3c-restart2",
            "p3d-ghost": "nb-p3d-ghost",
            "v-dialogs": "nb-v-dialogs",
            "v-supp": "nb-v-supp",
            "v138m-probes-dialogs": "nb-v138m-probes-dialogs",
            "v138m-probes-supp-dialogs": "nb-v138m-probes-supp-dialogs"}
    pdiff_all = []
    for short, saved in pmap.items():
        newp = jl(run / "probe" / f"268b-{short}.json")
        oldp = jl(L_RUN / "probe" / f"{saved}.json")
        same = (newp.get("rows") == oldp.get("rows"))
        det.setdefault("probes", {})[short] = {
            "rows_equal": same, "n_dialogs": len(newp.get("rows", []))}
        if not same:
            m3ok = False
            pdiff_all.append(short)
    det["probe_diffs"] = pdiff_all
    if pdiff_all != pred["m3"]["probe_diffs"]:
        m3ok = False
    # ghost answers + duplicate audits
    ghosts = []
    for short in pmap:
        newp = jl(run / "probe" / f"268b-{short}.json")
        oldp = jl(L_RUN / "probe" / f"{pmap[short]}.json")
        vo = {r.get("id", i): r
              for i, r in enumerate(oldp.get("rows", []))}
        for r in newp.get("rows", []):
            o = vo.get(r.get("id"))
            if o is None:
                continue
            ot = {(t.get("turn"), t.get("reply")) for t in o.get("rows", [])}
            for t in r.get("rows", []):
                if (t.get("turn"), t.get("reply")) not in ot:
                    vals = {str(x).lower() for row in r.get("rows", [])
                            for x in row.get("triples", [])}
                    if any(v and v in str(t.get("reply", "")).lower()
                           for v in vals):
                        ghosts.append((r.get("id"), t.get("turn")))
    dup_bad = []
    for short in pmap:
        newp = jl(run / "probe" / f"268b-{short}.json")

        def scan(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "dup_ok" and v is not True:
                        dup_bad.append(f"{short}:{path}/{k}")
                    scan(v, f"{path}/{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    scan(v, f"{path}[{i}]")
        scan(newp)
    det["ghost_answers"] = ghosts
    det["dup_bad"] = dup_bad
    if ghosts or dup_bad:
        m3ok = False
    res["marks"]["M3"] = {"pass": m3ok, "detail": det}

    # M4
    med_b, med_n = [], []
    for p in sorted(run.glob("lat-b-*.json")):
        d = jl(p)
        med_b.extend(d["times_ms"] if "times_ms" in d else d["times"])
    for p in sorted(run.glob("lat-n-*.json")):
        d = jl(p)
        med_n.extend(d["times_ms"] if "times_ms" in d else d["times"])
    assert med_b and med_n, "latency files missing"
    delta = statistics.median(med_n) - statistics.median(med_b)
    m4ok = delta <= 5.0
    res["marks"]["M4"] = {"pass": m4ok,
                          "median_138nb_ms": statistics.median(med_b),
                          "median_268b_ms": statistics.median(med_n),
                          "delta_ms": delta}

    overall = all(v["pass"] for v in res["marks"].values())
    res["overall"] = "PASS" if overall else "FAIL"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["marks"].items():
        print(f"{k}: {'PASS' if v['pass'] else 'FAIL'} "
              f"{json.dumps(v)[:500]}", flush=True)
    print(res["overall"], flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
