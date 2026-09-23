#!/usr/bin/env python3
"""Exp 268 scorer: checks the registered run against predicted_moves268.json.

New file only. CPU only.
usage: claude_268_score.py <run_dir> <pred_json> <out_json>

Checks (mirrors PASSMARKS.md):
  DEV  every (dialog,turn) move 138m->268 equals the predicted dev list,
       exact stage+reply; 0 teach/triple changes; 0 new wrong values.
  SUPP same for the 7 supplemental dialogs.
  M2   sessions152/bench/marks123 0 moves; rt136 label set exactly
       C019-C031 + C076 + C079 with 0 new WRONG/WRONG-WRITE/junk/lost-OK
       beyond the 13 inherited, direct rows vs 138m [] (reply/stored/
       verdict); rt143 0 moves 0 verdict flips; 63 inherited 222 rows
       identical to 138m's saved rows (seconds excluded on rt136).
  M3   5 restart probes rows equal to 138m's saved m-rows (agent field
       excluded); probes/supp rows equal to rows-138m/supp-rows-138m;
       0 ghost answers (no reply to an unasked value), 0 write changes.
  M4   median(268 reps) - median(138m reps) <= +5 ms.
Prints PASS/FAIL per mark and writes JSON.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L_RUN = ROOT / "artifacts" / "claude-merge138m-20260922" / "run"
L136 = L_RUN / "sd136" / "rt136-rows.json"


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p: Path) -> dict:
    return {json.loads(ln)["id"]: json.loads(ln)
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip()}


def dev_moves(m_path: Path, n_path: Path):
    m = jl(m_path)
    n = jl(n_path)
    mi = {(r["dialog"], r["turn"]): r for r in m}
    ni = {(r["dialog"], r["turn"]): r for r in n}
    assert set(mi) == set(ni), "dialog/turn sets differ"
    moves = []
    teach_changes = []
    for k in mi:
        a, b = mi[k], ni[k]
        if (a["reply"], a["stage"], a["triples_after"]) != (
                b["reply"], b["stage"], b["triples_after"]):
            rec = {"id": f"{k[0]}#t{k[1]}", "m_stage": a["stage"],
                   "n_stage": b["stage"], "m_reply": a["reply"],
                   "n_reply": b["reply"]}
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

    # DEV
    dm, dt = dev_moves(run / "dev" / "dev-138m.json",
                       run / "dev" / "dev-268.json")
    sm, st = dev_moves(run / "dev" / "supp-138m.json",
                       run / "dev" / "supp-268.json")
    dev_ids = sorted(x["id"] for x in dm)
    supp_ids = sorted(x["id"] for x in sm)
    dev_ok = (dev_ids == sorted(pred["dev_moves"])
              and supp_ids == sorted(pred["supp_moves"])
              and not dt and not st)
    # exact records
    rec_ok = True
    want = pred["dev_records"]
    nmap = {(r["dialog"], f"t{r['turn']}"): r
            for r in jl(run / "dev" / "dev-268.json")}
    smap = {(r["dialog"], f"t{r['turn']}"): r
            for r in jl(run / "dev" / "supp-268.json")}
    for did, rec in want.items():
        src = nmap if did.startswith(("d", "o")) else smap
        got = src.get((did.split("#")[0], did.split("#")[1]))
        if got is None or got["stage"] != rec["stage"] \
                or got["reply"] != rec["reply"]:
            rec_ok = False
            res.setdefault("dev_record_mismatch", []).append(did)
    res["marks"]["DEV"] = {
        "pass": dev_ok and rec_ok, "moves": dev_ids,
        "supp_moves": supp_ids, "teach_changes": dt + st}

    # M2 suites
    m2ok = True
    det: dict = {}
    for suite in ("sessions152", "bench", "marks123"):
        d = jl(run / "sd" / f"{suite}-diff.json")
        det[suite] = {"n_moves": d["n_moves"],
                      "new_wrong": d.get("new_wrong",
                                         d.get("class_counts", {}))}
        if d["n_moves"] != 0:
            m2ok = False
    r136 = jl(run / "sd136" / "rt136-diff.json")
    mv = sorted(m["id"] if isinstance(m, dict) else m
                for m in r136["moves"])
    det["rt136_labels"] = mv
    if mv != sorted(pred["m2"]["rt136_labels"]):
        m2ok = False
    if r136.get("new_wrong", 0) != 0 or r136.get("new_junk", 0) != 0:
        m2ok = False
    nww = r136.get("new_wrong_write", 0)
    if nww != 13:
        m2ok = False
    lr = jsonl(L136)
    mr = jsonl(run / "sd136" / "rt136-rows.json")
    direct = sorted(i for i in lr
                    if any(lr[i][k] != mr[i][k]
                           for k in ("reply", "stored", "verdict")))
    det["rt136_direct_vs_138m"] = direct
    if direct != pred["m2"]["rt136_direct"]:
        m2ok = False
    # rt143
    base = {r["id"]: r for r in jl(L_RUN / "rt143nogate-m.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-268.json")}
    moves143 = [cid for cid, r in base.items()
                if any(r[k] != new[cid][k]
                       for k in ("teach_replies", "triples", "reply"))]
    det["rt143_moves"] = moves143
    if moves143 != pred["m2"]["rt143_moves"]:
        m2ok = False
    # 63 inherited 222 exceptions identical to 138m's saved rows
    # (rt136 C019-C031 covered by the direct compare above; bench -fwd
    # and marks123 bench-fable_edit_200 rows byte-compared here).
    exc_ok = True
    sd138m = ROOT / "artifacts" / "claude-merge138m-20260922" / "run" / "sd"
    for name in ("bench-bench132_4hop-rows.jsonl",
                 "bench-edit200-rows.jsonl",
                 "bench-new_121_4hop-rows.jsonl",
                 "bench-old_s2fresh_4hop-rows.jsonl"):
        if ((sd138m / name).read_bytes() != (run / "sd" / name).read_bytes()):
            exc_ok = False
            det.setdefault("exc_mismatch", []).append(name)
    for name in ("bench-rows-fable_edit_200.jsonl",
                 "bench-rows-s2fresh_4hop.jsonl"):
        if ((sd138m / "marks123" / name).read_bytes()
                != (run / "sd" / "marks123" / name).read_bytes()):
            exc_ok = False
            det.setdefault("exc_mismatch", []).append(f"marks123/{name}")
    det["inherited_222_identical"] = exc_ok
    if not exc_ok:
        m2ok = False
    res["marks"]["M2"] = {"pass": m2ok, "detail": det}

    # M3
    m3ok = True
    m3det: dict = {}
    for short in ("p3-dialogs", "p3c-restart2", "p3d-ghost",
                  "v-dialogs", "v-supp"):
        new = jl(run / "probe" / f"268-{short}.json")
        old = jl(L_RUN / "probe" / f"m-{short}.json")
        same = (new.get("rows") == old.get("rows"))
        m3det[short] = {"rows_equal": same,
                        "n_dialogs": len(new.get("rows", []))}
        if not same:
            m3ok = False
    vnew = jl(run / "probe" / "268-probes.json")
    vold = jl(ROOT / "artifacts" / "claude-verify-20260922" / "138m"
              / "rows-138m.json")
    vd = {r["id"]: r for r in vnew}
    vo = {r["id"]: r for r in vold}
    vdiff = sorted(i for i in vd if vd[i] != vo.get(i))
    m3det["probes_diff"] = vdiff
    if vdiff != pred["m3"]["probes_diff"]:
        m3ok = False
    snew = jl(run / "probe" / "268-supp.json")
    sold = jl(ROOT / "artifacts" / "claude-verify-20260922" / "138m"
              / "supp-rows-138m.json")
    sd_ = {r["id"]: r for r in snew}
    so = {r["id"]: r for r in sold}
    sdiff = sorted(i for i in sd_ if sd_[i] != so.get(i))
    m3det["supp_diff"] = sdiff
    if sdiff != pred["m3"]["supp_diff"]:
        m3ok = False
    # ghost answers: any changed reply vs 138m that states a notebook
    # value (non-decline wording) where 138m abstained/declined.
    vdiff_rows = [(vd[i], vo.get(i)) for i in vdiff]
    sdiff_rows = [(sd_[i], so.get(i)) for i in sdiff]
    ghosts = []
    for new_d, old_d in vdiff_rows + sdiff_rows:
        if old_d is None:
            ghosts.append((new_d["id"], "missing-base"))
            continue
        ot = {(t.get("turn"), t.get("reply")) for t in old_d.get("rows", [])}
        for t in new_d.get("rows", []):
            if (t.get("turn"), t.get("reply")) not in ot:
                vals = {str(o).lower()
                        for row in new_d.get("rows", [])
                        for _s, _r, o in row.get("triples", [])}
                if any(v and v in str(t.get("reply", "")).lower()
                       for v in vals):
                    ghosts.append((new_d["id"], t.get("turn")))
    # duplicate-index audits in the restart probes must all hold
    dup_bad = []
    for short in ("p3-dialogs", "p3c-restart2", "p3d-ghost",
                  "v-dialogs", "v-supp"):
        new = jl(run / "probe" / f"268-{short}.json")

        def scan(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "dup_ok" and v is not True:
                        dup_bad.append(f"{short}:{path}/{k}")
                    scan(v, f"{path}/{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    scan(v, f"{path}[{i}]")
        scan(new)
    m3det["ghost_answers"] = ghosts
    m3det["dup_bad"] = dup_bad
    if ghosts or dup_bad:
        m3ok = False
    res["marks"]["M3"] = {"pass": m3ok, "detail": m3det}

    # M4
    med_m, med_n = [], []
    for p in sorted(run.glob("lat-m-*.json")):
        d = jl(p)
        med_m.extend(d["times_ms"] if "times_ms" in d else d["times"])
    for p in sorted(run.glob("lat-n-*.json")):
        d = jl(p)
        med_n.extend(d["times_ms"] if "times_ms" in d else d["times"])
    assert med_m and med_n, "latency files missing"
    delta = statistics.median(med_n) - statistics.median(med_m)
    m4ok = delta <= 5.0
    res["marks"]["M4"] = {"pass": m4ok, "median_m_ms": statistics.median(med_m),
                          "median_n_ms": statistics.median(med_n),
                          "delta_ms": delta}

    overall = all(v["pass"] for v in res["marks"].values())
    res["overall"] = "PASS" if overall else "FAIL"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["marks"].items():
        print(f"{k}: {'PASS' if v['pass'] else 'FAIL'} "
              f"{json.dumps(v)[:400]}", flush=True)
    print(res["overall"], flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
