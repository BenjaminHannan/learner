#!/usr/bin/env python3
"""Experiment 131 rescorer — read-only re-analysis of the frozen 131 wave.

Deviation D1: scripts/fable_sleep116_drive.py (reused read-only by the 131
driver) looks up turn records with bare probe names ("p01") while the
daemon logs mailbox filenames ("p01.txt"), so every record-dependent
check (source/trail/status) read empty records: F1/F2 auto-BUG in the raw
131 report, and empty src= in E/T4 details. This is the same checker bug
as exp-116's deviation D3, handled the same way: daemon evidence
(outbox replies, daemon.log.jsonl, notebooks, word files) is frozen on
disk and all daemons are stopped. This script recomputes every verdict
from those frozen artifacts with corrected filename matching, using the
same case logic as scripts/fable_sleep116_rescore.py. No daemon is
booted. Outputs (all under artifacts/fable-sleep131-20260922/):
  wave-report-116-rescored.json, t4-rescored.json, t-marks.json.
Nothing else is written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep104_drive as D104  # noqa: E402 (read-only)
import fable_sleep116_drive as D116  # noqa: E402 (read-only)

ART131 = SCRIPTS.parent / "artifacts" / "fable-sleep131-20260922"
ART116 = SCRIPTS.parent / "artifacts" / "fable-sleep116-20260922"
ART104 = SCRIPTS.parent / "artifacts" / "fable-sleep104-20260921"


def load_run(d: Path) -> dict:
    log = [json.loads(l) for l in (d / "daemon.log.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    outbox = {}
    for p in (d / "outbox").glob("*.txt"):
        outbox[p.name] = p.read_text(encoding="utf-8")
    nb = C.Notebook(d / "notebook")
    return {"dir": d, "log": log, "outbox": outbox, "nb": nb}


def rec_of(run: dict, fname: str) -> dict:
    for e in run["log"]:
        if e.get("event") == "turn" and e.get("file") == fname:
            recs = e.get("records", [])
            return recs[0] if recs else {}
    return {}


def turn_ev(run: dict, fname: str) -> dict:
    for e in run["log"]:
        if e.get("event") == "turn" and e.get("file") == fname:
            return e
    return {}


has = D116.has
is_abstain = D116.is_abstain


def rescore_116() -> dict:
    wave = json.loads((ART131 / "wave-report-116.json").read_text(
        encoding="utf-8"))
    runs = wave["runs"]
    out: dict = {"cases": {}, "runs": runs,
                 "wave_seconds": wave["wave_seconds"],
                 "rescore_note": "D1: corrected probe-filename matching "
                 "(.txt); evidence frozen from the 131 registered wave; "
                 "no daemon booted."}

    def V(cid: str, verdict: str, detail: str = "") -> None:
        out["cases"][cid] = {"verdict": verdict, "detail": detail}

    # ---- A (same logic as the 116 rescore)
    r = load_run(ART131 / "runs-116" / "contra")
    inst = runs["contra"]["installed"]
    for cid, fn, curv, stalev in [("A1", "p01.txt", "G07", None),
                                  ("A2", "p02.txt", "P02", "G02"),
                                  ("A4", "p04.txt", "P05", "G05")]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        if cid == "A1":
            ok = (ab and not inst) or (inst and has(rp, "G07"))
            bad = has(rp, "P07") and "G07" not in rp.lower()
            V(cid, "OK" if (ok and not bad) else "BUG",
              f"installed={int(inst)} abstain={int(ab)} "
              f"status={rec.get('status')} reply={rp.strip()[:90]}")
        else:
            if stalev and has(rp, stalev) and not has(rp, curv):
                V(cid, "BUG", f"STALE answer: reply={rp.strip()[:90]}")
            elif ab or has(rp, curv):
                V(cid, "OK",
                  f"installed={int(inst)} abstain={int(ab)} "
                  f"status={rec.get('status')} reply={rp.strip()[:90]}")
            else:
                V(cid, "BUG", f"unexpected reply={rp.strip()[:90]}")
    rp3 = r["outbox"].get("p03.txt", "")
    rec3 = rec_of(r, "p03.txt")
    norel = not any(f.get("relation") == "paternal_grandmother"
                    for f in r["nb"].facts.values())
    V("A3", "OK" if (is_abstain(rp3, rec3) and norel) else "BUG",
      f"reply={rp3.strip()[:90]} status={rec3.get('status')} "
      f"norel={int(norel)}")

    # ---- B
    r = load_run(ART131 / "runs-116" / "coinc")
    inst = runs["coinc"]["installed"]
    for cid, fn, tv, av in [("B1", "p01.txt", "H01", "Z01"),
                            ("B2", "p02.txt", "H02", "Z02"),
                            ("B3", "p03.txt", "H03", None),
                            ("B4", "p04.txt", "H04", None)]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        src = rec.get("fields", {}).get("source", "")
        if av and has(rp, av) and not has(rp, tv):
            V(cid, "BUG", f"AUNT-LATCH: reply={rp.strip()[:90]}")
        elif cid == "B4" and inst and not (has(rp, tv) or ab):
            V(cid, "BUG", f"control failed: reply={rp.strip()[:90]}")
        elif has(rp, tv) or (ab and not inst) or (ab and inst):
            V(cid, "OK",
              f"installed={int(inst)} abstain={int(ab)} src={src} "
              f"reply={rp.strip()[:90]}")
        else:
            V(cid, "BUG", f"unexpected: reply={rp.strip()[:90]}")

    # ---- C
    r = load_run(ART131 / "runs-116" / "collide")
    inst = runs["collide"]["installed"]
    sam2 = r["outbox"].get("t018.txt", "")
    sam_active = D116.active_values(r["nb"], "Sam", "mother")
    wrote = bool(turn_ev(r, "t018.txt").get("new_fact_ids"))
    V("C1", "OK" if (sam2.strip() and sam_active == ["M01"] and not wrote)
      else "BUG",
      f"reply={sam2.strip()[:90]} active={sam_active} wrote={int(wrote)}")
    p1 = r["outbox"].get("p01.txt", "")
    rec1 = rec_of(r, "p01.txt")
    ans1 = rec1.get("fields", {}).get("answer", "")
    V("C2", "OK" if (is_abstain(p1, rec1) or ans1 == "M01"
                     or has(p1, "M01")) else "BUG",
      f"reply={p1.strip()[:90]} status={rec1.get('status')} answer={ans1}")
    subs = []
    for cid, fn, gv in [("C3a", "p02.txt", "G01"), ("C3b", "p03.txt", "G02")]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        if (inst and has(rp, gv)) or (not inst and ab) or (ab and inst):
            V(cid, "OK",
              f"src={rec.get('fields', {}).get('source')} "
              f"reply={rp.strip()[:80]}")
        else:
            V(cid, "BUG", f"reply={rp.strip()[:80]}")
        subs.append(cid)
    V("C3", "OK" if all(out["cases"][k]["verdict"] == "OK" for k in subs)
      else "BUG",
      "; ".join(f"{k}={out['cases'][k]['detail']}" for k in subs))
    q = [r["outbox"].get(f"q{i:02d}.txt", "") for i in (1, 2, 3)]
    same = (("M01" in q[0] or is_abstain(q[0], {})) and
            ("G01" in q[1] or is_abstain(q[1], {})) and
            ("G02" in q[2] or is_abstain(q[2], {})))
    V("C4", "OK" if same else "BUG",
      f"q={[v.strip()[:40] for v in q]}")

    # ---- D
    r = load_run(ART131 / "runs-116" / "twomom")
    inst = runs["twomom"]["installed"]
    dbl = r["outbox"].get("t017.txt", "")
    cor = r["outbox"].get("t019.txt", "")
    m_now = D116.active_values(r["nb"], "K01", "mother")
    t017wrote = bool(turn_ev(r, "t017.txt").get("new_fact_ids"))
    V("D1", "OK" if (m_now == ["M01b"] and not t017wrote) else "BUG",
      f"double-teach={dbl.strip()[:80]} wrote={int(t017wrote)} final={m_now}")
    V("D2", "OK" if (m_now == ["M01b"] and cor.strip()) else "BUG",
      f"correction={cor.strip()[:80]} active={m_now}")
    p1 = r["outbox"].get("p01.txt", "")
    rec1 = rec_of(r, "p01.txt")
    ab1 = is_abstain(p1, rec1)
    if has(p1, "G01b") or ab1:
        V("D3", "OK",
          f"installed={int(inst)} src={rec1.get('fields', {}).get('source')} "
          f"reply={p1.strip()[:90]}")
    elif has(p1, "G01") and "G01b" not in p1:
        V("D3", "BUG", f"STALE via superseded M01: {p1.strip()[:90]}")
    else:
        V("D3", "BUG", f"unexpected: {p1.strip()[:90]}")
    p2 = r["outbox"].get("p02.txt", "")
    rec2 = rec_of(r, "p02.txt")
    rr = runs["twomom"]
    d4ok = (rr["taught_good"] == 17 and rr["dupes"] == 0
            and rr["overwrite"] == 0
            and (has(p2, "G02") or is_abstain(p2, rec2)))
    V("D4", "OK" if d4ok else "BUG",
      f"taught={rr['taught_good']}/17 dupes={rr['dupes']} "
      f"ow={rr['overwrite']} ctrl={p2.strip()[:60]}")

    # ---- E (on 131 the taught Z must win with source taught)
    r = load_run(ART131 / "runs-116" / "taughtwin")
    inst = runs["taughtwin"]["installed"]
    stored = {str(k): bool(v) for k, v in runs["taughtwin"]["stored"].items()}
    e1 = r["outbox"].get("t025.txt", "")
    V("E1", "OK" if e1.strip() else "BUG",
      f"reply={e1.strip()[:90]} "
      f"wrote={bool(turn_ev(r, 't025.txt').get('new_fact_ids'))} "
      f"stored={stored}")
    esrc = {}
    for cid, i, fn in [("E2", 1, "p01.txt"), ("E3", 2, "p02.txt")]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        zv, gv = f"Z{i:02d}", f"H{i:02d}"
        src = rec.get("fields", {}).get("source", "")
        esrc[cid] = src
        if stored[str(i)]:
            if has(rp, zv) or ab:
                V(cid, "OK",
                  f"stored; installed={int(inst)} abstain={int(ab)} "
                  f"src={src} reply={rp.strip()[:80]}")
            elif has(rp, gv):
                V(cid, "BUG",
                  f"TAUGHT OVERRIDDEN by derived {gv}: src={src} "
                  f"reply={rp.strip()[:80]}")
            else:
                V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
        else:
            V(cid, "OK" if (has(rp, gv) or ab) else "BUG",
              f"not-storable branch; reply={rp.strip()[:80]}")
    rp4 = r["outbox"].get("p03.txt", "")
    rec4 = rec_of(r, "p03.txt")
    src4 = rec4.get("fields", {}).get("source", "")
    esrc["E4"] = src4
    ow = runs["taughtwin"]["overwrite"]
    if stored["3"] and has(rp4, "Z03") and src4 == "sleep-derived":
        V("E4", "BUG",
          f"taught win mislabeled sleep-derived: {rp4.strip()[:80]}")
    elif ow == 0 and stored["3"] and (has(rp4, "Z03")
                                     or is_abstain(rp4, rec4)):
        V("E4", "OK", f"taught intact src={src4} reply={rp4.strip()[:80]}")
    elif not stored["3"] and ow == 0:
        V("E4", "OK", f"not-storable branch, ow=0 reply={rp4.strip()[:80]}")
    else:
        V("E4", "BUG",
          f"ow={ow} stored={stored} src={src4} reply={rp4.strip()[:80]}")
    out["e_sources"] = esrc

    # ---- F
    r = load_run(ART131 / "runs-116" / "wrongpre")
    inst = runs["wrongpre"]["installed"]
    p1 = r["outbox"].get("p01.txt", "")
    rec1 = rec_of(r, "p01.txt")
    src1 = rec1.get("fields", {}).get("source", "")
    trail1 = rec1.get("fields", {}).get("trail", [])
    ab1 = is_abstain(p1, rec1)
    if inst and has(p1, "X01") and src1 == "sleep-derived":
        V("F1", "OK", "wrong-vs-truth X01, provenance sleep-derived "
                      "(measured)")
    elif not inst and ab1:
        V("F1", "OK", "refused + abstained (safe)")
    else:
        V("F1", "BUG",
          f"src={src1} reply={p1.strip()[:90]} installed={int(inst)}")
    reps = [f["fact_id"] for f in r["nb"].facts.values()
            if f.get("source") == "sleep-derived"
            and f.get("relation") == "sleep_report"]
    if (not inst and ab1) or (trail1 and trail1[0] in reps):
        V("F2", "OK", f"trail-head={trail1[:1]} reports={reps}")
    else:
        V("F2", "BUG",
          f"trail does not head report: {trail1[:2]} reports={reps}")
    rr = runs["wrongpre"]
    V("F3", "OK" if (rr["taught_good"] == 24 and rr["dupes"] == 0
                     and rr["overwrite"] == 0) else "BUG",
      f"taught={rr['taught_good']}/24 dupes={rr['dupes']} "
      f"ow={rr['overwrite']}")
    p2 = r["outbox"].get("p02.txt", "")
    rec2 = rec_of(r, "p02.txt")
    V("F4", "OK" if (has(p2, "G09") or (is_abstain(p2, rec2) and not inst))
      else "BUG",
      f"src={rec2.get('fields', {}).get('source')} "
      f"reply={p2.strip()[:80]}")

    # ---- G (reply counts from frozen outbox; G2/G3/G5-G8 carried)
    r = load_run(ART131 / "runs-116" / "flood")
    n200 = sum(1 for i in range(1, 201)
               if r["outbox"].get(f"z{i:03d}.txt", "").strip())
    V("G1", "OK" if n200 == 200 else "BUG", f"replies={n200}/200")
    aims = {40: "M01", 80: "M02", 120: "M03", 160: "M04", 200: "M05"}
    ok4 = all(has(r["outbox"].get(f"z{i:03d}.txt", ""), m)
              for i, m in aims.items())
    V("G4", "OK" if ok4 else "BUG",
      "; ".join(f"z{i:03d}={r['outbox'].get(f'z{i:03d}.txt', '').strip()[:40]}"
                for i in aims))
    for cid in ("G2", "G3", "G5", "G6", "G7", "G8"):
        V(cid, wave["cases"][cid]["verdict"],
          wave["cases"][cid]["detail"] + " [carried; no record read]")

    # ---- H
    for tag, cids in [("few5", ["H1", "H4"]), ("few10", ["H2"]),
                      ("few15", ["H3"])]:
        r = load_run(ART131 / "runs-116" / tag)
        rr = runs[tag]
        for cid in cids:
            if cid == "H4":
                nrr = sum(1 for f in r["nb"].facts.values()
                          if f.get("source") == "sleep-derived")
                w = (r["dir"] / "sleep104-word.json").exists()
                V(cid, "OK" if (nrr == 0 and not w
                                and rr.get("taught_good", 10) == 10)
                  else "BUG",
                  f"rechecked report-rows={nrr} word={w}")
                continue
            ps = [r["outbox"].get("p01.txt", ""),
                  r["outbox"].get("p02.txt", "")]
            ab = [is_abstain(ps[0], rec_of(r, "p01.txt")),
                  is_abstain(ps[1], rec_of(r, "p02.txt"))]
            wrong = [not (a or has(p, "G01" if i == 0 else "G02"))
                     for i, (p, a) in enumerate(zip(ps, ab))]
            if tag == "few5":
                V(cid, "OK" if (not rr["attempted"] and not rr["installed"]
                                and all(ab) and not any(wrong)) else "BUG",
                  f"attempted={rr['attempted']} installed={rr['installed']} "
                  f"abstain={ab} replies={[p.strip()[:50] for p in ps]}")
            else:
                V(cid, "OK" if not any(wrong) else "BUG",
                  f"attempted={rr['attempted']} installed={rr['installed']} "
                  f"abstain={ab} replies={[p.strip()[:50] for p in ps]}")
    return out


def rescore_t4() -> dict:
    r = load_run(ART131 / "runs-t4" / "teachafter")
    raw = json.loads((ART131 / "t4.json").read_text(encoding="utf-8"))
    rec_t = rec_of(r, "p01.txt")
    rec_c = rec_of(r, "p02.txt")
    src_t = rec_t.get("fields", {}).get("source", "")
    src_c = rec_c.get("fields", {}).get("source", "")
    trail_t = rec_t.get("fields", {}).get("trail", [])
    trail_c = rec_c.get("fields", {}).get("trail", [])
    taught_rows = [f for f in r["nb"].facts.values()
                   if f.get("relation") == "maternal_grandmother"
                   and f.get("source") == "taught"
                   and r["nb"].active(f["fact_id"])]
    reps = [f["fact_id"] for f in r["nb"].facts.values()
            if f.get("source") == "sleep-derived"
            and f.get("relation") == "sleep_report"]
    ow = D104.sleep_overwrites(r["nb"])
    p_t = r["outbox"].get("p01.txt", "")
    p_c = r["outbox"].get("p02.txt", "")
    ta_ok = bool(raw["installed"] and raw["stored_taught"]
                 and has(p_t, "Z01") and not has(p_t, "H01")
                 and src_t == "taught" and trail_t == [
                     f["fact_id"] for f in taught_rows][:1] and ow == 0)
    tb_ok = bool(raw["installed"] and has(p_c, "H02")
                 and src_c == "sleep-derived"
                 and bool(trail_c) and trail_c[0] in reps)
    return {"installed": raw["installed"], "attempted": raw["attempted"],
            "episodes": raw["episodes"], "oof": raw["oof"],
            "agree": raw["agree"],
            "teach_reply": raw["teach_reply"],
            "stored_taught": raw["stored_taught"],
            "probe_taught": p_t.strip()[:120],
            "probe_taught_source": src_t, "probe_taught_trail": trail_t,
            "taught_rows": [f["fact_id"] for f in taught_rows],
            "probe_control": p_c.strip()[:120],
            "probe_control_source": src_c, "probe_control_trail": trail_c,
            "report_rows": reps, "overwrite": ow,
            "TA_taught_wins": "PASS" if ta_ok else "FAIL",
            "TB_control_derived": "PASS" if tb_ok else "FAIL",
            "T4": "PASS" if (ta_ok and tb_ok) else "FAIL",
            "rescore_note": "D1: records re-read with .txt names from "
            "frozen evidence; no daemon booted."}


SEED_FIELDS = ["installed", "episodes_at_install", "recipe_attempted",
               "probes_correct", "probes_abstain", "probes_wrong",
               "probe_sources_sleep_derived", "report_rows_sleep_derived",
               "taught_good", "taught_total", "taught_dupes",
               "sleep_overwrote_taught", "wrong_install"]


def compare_t3() -> dict:
    sealed = json.loads((ART104 / "wave-report.json").read_text(
        encoding="utf-8"))
    mine = json.loads((ART131 / "wave-report-104.json").read_text(
        encoding="utf-8"))
    diffs = []
    for seed in ("1", "2", "3"):
        for f in SEED_FIELDS:
            a, b = sealed["seeds"][seed].get(f), mine["seeds"][seed].get(f)
            if a != b:
                diffs.append(f"seed{seed}.{f}: 104={a} 131={b}")
    zfields = [("boot_ok", True), ("probes_correct", 5),
               ("probes_abstain", 0), ("probes_wrong", 0),
               ("taught_asks_correct", 200), ("taught_asks_wrong", 0),
               ("taught_dupes", 0), ("sleep_overwrote_taught", 0)]
    for f, _ in zfields:
        a, b = sealed["z4"].get(f), mine["z4"].get(f)
        if a != b:
            diffs.append(f"z4.{f}: 104={a} 131={b}")
    for f in ("pass",):
        if sealed["z4"].get(f) != mine["z4"].get(f):
            diffs.append(f"z4.{f} differs")
    rs, rm = sealed["z4"]["restore"], mine["z4"]["restore"]
    for f in ("correct", "abstain", "wrong", "pass"):
        if rs.get(f) != rm.get(f):
            diffs.append(f"z4.restore.{f}: 104={rs.get(f)} 131={rm.get(f)}")
    if ((sealed["z4"]["word_file"] in ("valid", "absent"))
            != (mine["z4"]["word_file"] in ("valid", "absent"))):
        diffs.append("z4.word_file differs")
    for key in ("noise4", "noise8"):
        for f in ("installed", "probes_correct", "probes_abstain",
                  "probes_wrong", "wrong_install"):
            a = sealed["z5"][key].get(f)
            b = mine["z5"][key].get(f)
            if a != b:
                diffs.append(f"z5.{key}.{f}: 104={a} 131={b}")
    return {"diffs": diffs, "T3": "PASS" if not diffs else "FAIL"}


def main(argv=None) -> int:
    r116 = rescore_116()
    (ART131 / "wave-report-116-rescored.json").write_text(
        json.dumps(r116, indent=1, sort_keys=True), encoding="utf-8")
    old116 = json.loads((ART116 / "wave-report-rescored.json").read_text(
        encoding="utf-8"))
    t2diffs = []
    for cid, c in r116["cases"].items():
        if cid.startswith("E"):
            continue
        o = old116["cases"].get(cid)
        if not o or o["verdict"] != c["verdict"]:
            t2diffs.append(
                f"{cid}: 131={c['verdict']} 116={o['verdict'] if o else None}")
    n_none = sum(1 for k in r116["cases"] if not k.startswith("E"))
    t2 = {"compared": n_none, "diffs": t2diffs,
          "T2": "PASS" if not t2diffs else "FAIL"}

    esrc = r116.get("e_sources", {})
    e_ok = all(r116["cases"][c]["verdict"] == "OK"
               for c in ("E1", "E2", "E3", "E4"))
    src_ok = all(esrc.get(c) == "taught" for c in ("E2", "E3", "E4"))
    t1 = {"E_verdicts": {c: r116["cases"][c]["verdict"]
                         for c in ("E1", "E2", "E3", "E4")},
          "E_sources": esrc,
          "T1": "PASS" if (e_ok and src_ok) else "FAIL"}

    t4 = rescore_t4()
    (ART131 / "t4-rescored.json").write_text(
        json.dumps(t4, indent=1, sort_keys=True), encoding="utf-8")

    t3 = compare_t3()

    marks = {"T1": t1["T1"], "T1_detail": t1,
             "T2": t2["T2"], "T2_detail": t2,
             "T3": t3["T3"], "T3_detail": t3,
             "T4": t4["T4"],
             "T4_detail": {k: t4[k] for k in
                           ("TA_taught_wins", "TB_control_derived",
                            "probe_taught_source", "probe_control_source",
                            "overwrite")}}
    (ART131 / "t-marks.json").write_text(
        json.dumps(marks, indent=1, sort_keys=True), encoding="utf-8")
    n_ok = sum(1 for c in r116["cases"].values() if c["verdict"] == "OK")
    print(f"rescored 116-rerun: OK={n_ok}/37", flush=True)
    for cid in sorted(r116["cases"]):
        c = r116["cases"][cid]
        print(f"{cid}: {c['verdict']} -- {c['detail'][:100]}", flush=True)
    print(f"T1 {t1['T1']} src={esrc}", flush=True)
    print(f"T2 {t2['T2']} compared={n_none} diffs={t2diffs}", flush=True)
    print(f"T3 {t3['T3']} diffs={t3['diffs']}", flush=True)
    print(f"T4 {t4['T4']} TA={t4['TA_taught_wins']} src={t4['probe_taught_source']} "
          f"TB={t4['TB_control_derived']} src={t4['probe_control_source']} "
          f"ow={t4['overwrite']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
