#!/usr/bin/env python3
"""Experiment 145 rescorer -- read-only re-analysis of the frozen 145 wave.

Mirrors scripts/fable_sleep131_rescore.py (imported read-only; its ART131
path is redirected process-locally to the 145 artifact dir -- no file is
edited). Corrections applied on top, all read-only from frozen evidence
(no daemon is booted):

  D1 (same checker bug as 116-D3 / 131-D1): the reused 116 driver looks up
      turn records by bare probe name ("p01") while logs store mailbox
      names ("p01.txt"). Rescored with the corrected .txt lookup.
  D2 (145-only): serving files are sleep145-words.json / sleep145-SLEEPING
      (renamed by design so 145 state never touches sealed files), so the
      raw stop-run G5 verdict reads BUG (marker never sighted under the old
      name). Rescored on sleep evidence: exit 0 + stopped event + recipe
      attempted in the frozen log. H4 is rechecked against the 145 word
      path as well.

Outputs (all under artifacts/fable-sleep145-20260922/):
  wave-report-116-rescored.json, t4-rescored.json, t6-rescored.json,
  m1-compare.json, t-marks.json (T1/T2/T3/T4/T6/M1/M4 verdicts).
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
import fable_sleep130_drive as D130  # noqa: E402 (read-only)
import fable_sleep131_rescore as R131  # noqa: E402 (read-only)
import fable_sleep145_agent as S145  # noqa: E402 (this exp's agent)

ART145 = SCRIPTS.parent / "artifacts" / "fable-sleep145-20260922"
ART131 = SCRIPTS.parent / "artifacts" / "fable-sleep131-20260922"
ART130 = SCRIPTS.parent / "artifacts" / "fable-sleep130-20260922"
ART104 = SCRIPTS.parent / "artifacts" / "fable-sleep104-20260921"
ART116 = SCRIPTS.parent / "artifacts" / "fable-sleep116-20260922"

# Process-local redirect: 131's rescore functions read the 145 frozen wave.
R131.ART131 = ART145

has = D116.has
is_abstain = D116.is_abstain


def rescore_e116() -> dict:
    r116 = R131.rescore_116()
    # ---- D2: stop-run G5 on sleep evidence (marker renamed by design)
    wave = json.loads((ART145 / "wave-report-116.json").read_text(
        encoding="utf-8"))
    stop_run = wave["runs"].get("stop", {})
    log = [json.loads(l) for l in
           (ART145 / "runs-116" / "stop" / "daemon.log.jsonl").read_text(
               encoding="utf-8").splitlines() if l.strip()]
    attempted = any((e.get("recipe", {}) or {}).get("attempted")
                    for e in log if e.get("event") == "sleep")
    stopped = any(e.get("event") == "stopped" for e in log)
    if stop_run.get("exit") == 0 and stopped and attempted:
        r116["cases"]["G5"] = {
            "verdict": "OK",
            "detail": (f"D2 rescore: exit=0 stopped=1 recipe-attempted=1 "
                       f"(raw saw-marker=0 is the renamed {S145.MARKER145}; "
                       f"frozen evidence, no daemon booted)")}
    # ---- H4 rechecked against the 145 word path
    h4dir = ART145 / "runs-116" / "few5"
    h4log = [json.loads(l) for l in
             (h4dir / "daemon.log.jsonl").read_text(
                 encoding="utf-8").splitlines() if l.strip()]
    nrep = sum(1 for f in C.Notebook(h4dir / "notebook").facts.values()
               if f.get("source") == "sleep-derived")
    no145 = not (h4dir / S145.WORD_FILE145).exists()
    no104 = not (h4dir / "sleep104-word.json").exists()
    if nrep == 0 and no145 and no104:
        r116["cases"]["H4"] = {
            "verdict": "OK",
            "detail": (f"D2 recheck: report-rows=0, no 145/104 word file, "
                       f"frozen evidence")}
    r116["rescore_note"] += (" D2: stop-G5 on sleep evidence (145 marker "
                             "rename); H4 rechecked on the 145 word path.")
    (ART145 / "wave-report-116-rescored.json").write_text(
        json.dumps(r116, indent=1, sort_keys=True), encoding="utf-8")
    return r116


def marks_t1_t2_m4(r116: dict) -> dict:
    ref131 = json.loads((ART131 / "wave-report-116-rescored.json").read_text(
        encoding="utf-8"))
    # T1: E-family taught wins with source taught
    esrc = r116.get("e_sources", {})
    e_ok = all(r116["cases"][c]["verdict"] == "OK"
               for c in ("E1", "E2", "E3", "E4"))
    src_ok = all(esrc.get(c) == "taught" for c in ("E2", "E3", "E4"))
    t1 = {"E_verdicts": {c: r116["cases"][c]["verdict"]
                         for c in ("E1", "E2", "E3", "E4")},
          "E_sources": esrc,
          "T1": "PASS" if (e_ok and src_ok) else "FAIL"}
    # T2: 34 non-E verdicts identical to 131
    diffs = []
    n_none = 0
    for cid, c in r116["cases"].items():
        if cid.startswith("E"):
            continue
        n_none += 1
        o = ref131["cases"].get(cid)
        if not o or o["verdict"] != c["verdict"]:
            diffs.append(
                f"{cid}: 145={c['verdict']} 131={o['verdict'] if o else None}")
    t2 = {"compared": n_none, "diffs": diffs,
          "T2": "PASS" if not diffs else "FAIL"}
    # M4: no case worse than on 131 (worse = 131 OK, 145 not OK)
    worse = []
    for cid, c in r116["cases"].items():
        o = ref131["cases"].get(cid)
        if o and o["verdict"] == "OK" and c["verdict"] != "OK":
            worse.append(f"{cid}: 131=OK 145={c['verdict']}")
    m4 = {"compared": len(r116["cases"]), "worse": worse,
          "M4": "PASS" if not worse else "FAIL"}
    return {"T1": t1, "T2": t2, "M4": m4}


def rescore_t4() -> dict:
    t4 = R131.rescore_t4()
    (ART145 / "t4-rescored.json").write_text(
        json.dumps(t4, indent=1, sort_keys=True), encoding="utf-8")
    return t4


def rescore_t6() -> dict:
    d = ART145 / "runs-t6" / "grownafter"
    log = [json.loads(l) for l in (d / "daemon.log.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    outbox = {p.name: p.read_text(encoding="utf-8")
              for p in (d / "outbox").glob("*.txt")}
    nb = C.Notebook(d / "notebook")

    def rec(fname: str) -> dict:
        for e in log:
            if e.get("event") == "turn" and e.get("file") == fname:
                recs = e.get("records", [])
                return recs[0] if recs else {}
        return {}

    raw = json.loads((ART145 / "t6.json").read_text(encoding="utf-8"))
    rec_t, rec_c = rec("p01.txt"), rec("p02.txt")
    src_t = rec_t.get("fields", {}).get("source", "")
    src_c = rec_c.get("fields", {}).get("source", "")
    trail_t = rec_t.get("fields", {}).get("trail", [])
    trail_c = rec_c.get("fields", {}).get("trail", [])
    taught_rows = [f for f in nb.facts.values()
                   if f.get("relation") == "boss_of_father"
                   and f.get("source") == "taught"
                   and nb.active(f["fact_id"])]
    reps = [f["fact_id"] for f in nb.facts.values()
            if f.get("source") == "sleep-derived"
            and f.get("relation") == "sleep_report"]
    ow = D104.sleep_overwrites(nb)
    p_t = outbox.get("p01.txt", "")
    p_c = outbox.get("p02.txt", "")
    sleeps = [e for e in log if e.get("event") == "sleep"]
    grew = any(w.get("word") == "boss_of_father" and w.get("grew_slot")
               for s in sleeps
               for w in (s.get("recipe", {}) or {}).get("words", []))
    ta_ok = bool(raw["installed"] and grew and raw["stored_taught"]
                 and has(p_t, "Z01") and not has(p_t, "CK01")
                 and src_t == "taught"
                 and trail_t == [f["fact_id"] for f in taught_rows][:1]
                 and ow == 0)
    tb_ok = bool(raw["installed"] and has(p_c, "CK02")
                 and src_c == "sleep-derived"
                 and bool(trail_c) and trail_c[0] in reps)
    t6 = {"installed": raw["installed"], "attempted": raw["attempted"],
          "episodes": raw["episodes"], "oof": raw["oof"],
          "agree": raw["agree"], "grew_slot": grew,
          "teach_reply": raw["teach_reply"],
          "stored_taught": raw["stored_taught"],
          "probe_taught": p_t.strip()[:120],
          "probe_taught_source": src_t, "probe_taught_trail": trail_t,
          "taught_rows": [f["fact_id"] for f in taught_rows],
          "probe_control": p_c.strip()[:120],
          "probe_control_source": src_c, "probe_control_trail": trail_c,
          "report_rows": reps, "overwrite": ow,
          "taught_good": raw["taught_good"],
          "taught_total": raw["taught_total"],
          "taught_dupes": raw["taught_dupes"],
          "TA_taught_wins": "PASS" if ta_ok else "FAIL",
          "TB_control_derived": "PASS" if tb_ok else "FAIL",
          "T6": "PASS" if (ta_ok and tb_ok) else "FAIL",
          "rescore_note": "re-derived from frozen evidence with .txt "
          "record names; no daemon booted."}
    (ART145 / "t6-rescored.json").write_text(
        json.dumps(t6, indent=1, sort_keys=True), encoding="utf-8")
    return t6


def compare_m1() -> dict:
    """M1: 145 G1/G3 reps equal 130's wave JSONs (timing excluded)."""
    out: dict = {"g1": {}, "g3": {}, "M1": "PASS"}
    for seed in ("1", "2"):
        ref = json.loads((ART130 / f"wave-g1s{seed}.json").read_text(
            encoding="utf-8"))["registered"]["G1"]["seeds"][seed]
        mine_full = json.loads((ART145 / f"wave-g1s{seed}.json").read_text(
            encoding="utf-8"))["registered"]["G1"]["seeds"][seed]
        mine = {k: v for k, v in mine_full.items()
                if k not in ("seconds", "replies", "dir", "rung")}
        theirs = {k: v for k, v in ref.items()
                  if k not in ("seconds", "dir", "thresholds")}
        for s in mine.get("sleeps", []):
            s.pop("sleep_seconds", None)
        for s in theirs.get("sleeps", []):
            s.pop("sleep_seconds", None)
        diffs = []
        if mine.get("sleeps") != theirs.get("sleeps"):
            diffs.append("sleeps differ")
        if mine.get("per_word") != theirs.get("per_word"):
            diffs.append("per_word differ")
        for key in ("installed_words", "n_sleeps",
                    "report_rows_sleep_derived", "taught_good",
                    "taught_total", "taught_dupes", "sleep_overwrote_taught",
                    "teaches_saved", "teaches_total", "turns"):
            if mine.get(key) != theirs.get(key):
                diffs.append(f"{key}: 145={mine.get(key)} 130={theirs.get(key)}")
        g1 = D130.g1_pass({**mine_full})
        g2 = D130.g2_pass({**mine_full})
        ok = not diffs and g1 and g2
        out["g1"][seed] = {"diffs": diffs, "g1_pass": g1, "g2_pass": g2,
                           "match": "PASS" if ok else "FAIL"}
        if not ok:
            out["M1"] = "FAIL"
    ref3 = json.loads((ART130 / "wave-g3.json").read_text(encoding="utf-8"))
    mine3 = json.loads((ART145 / "wave-g3.json").read_text(encoding="utf-8"))
    for rung, refkey in (("G3-L1", "L1"), ("G3-L2", "L2"), ("G3-L3", "L3")):
        per_seed = {}
        for seed in ("1", "2", "3"):
            ok, note = D130.g3_identical(
                {**mine3["registered"][rung]["seeds"][seed]},
                ref3["registered"][rung]["seeds"][seed], refkey)
            per_seed[seed] = {"identical": ok, "note": note}
        run_ok = all(v["identical"] for v in per_seed.values())
        out["g3"][rung] = {"seeds": per_seed,
                           "match": "PASS" if run_ok else "FAIL"}
        if not run_ok:
            out["M1"] = "FAIL"
    (ART145 / "m1-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    return out


def main(argv=None) -> int:
    r116 = rescore_e116()
    t12m4 = marks_t1_t2_m4(r116)
    t4 = rescore_t4()
    t3 = R131.compare_t3()
    t6 = rescore_t6()
    m1 = compare_m1()
    marks = {
        "T1": t12m4["T1"]["T1"], "T1_detail": t12m4["T1"],
        "T2": t12m4["T2"]["T2"], "T2_detail": t12m4["T2"],
        "T3": t3["T3"], "T3_detail": t3,
        "T4": t4["T4"],
        "T4_detail": {k: t4[k] for k in
                      ("TA_taught_wins", "TB_control_derived",
                       "probe_taught_source", "probe_control_source",
                       "overwrite")},
        "T6": t6["T6"],
        "T6_detail": {k: t6[k] for k in
                      ("TA_taught_wins", "TB_control_derived",
                       "probe_taught_source", "probe_control_source",
                       "overwrite", "grew_slot")},
        "M1": m1["M1"], "M1_detail": m1,
        "M4": t12m4["M4"]["M4"], "M4_detail": t12m4["M4"],
    }
    (ART145 / "t-marks.json").write_text(
        json.dumps(marks, indent=1, sort_keys=True), encoding="utf-8")
    n_ok = sum(1 for c in r116["cases"].values() if c["verdict"] == "OK")
    print(f"rescored 116-rerun: OK={n_ok}/{len(r116['cases'])}", flush=True)
    for cid in sorted(r116["cases"]):
        c = r116["cases"][cid]
        print(f"{cid}: {c['verdict']} -- {c['detail'][:100]}", flush=True)
    print(f"T1 {marks['T1']} src={t12m4['T1']['E_sources']}", flush=True)
    print(f"T2 {marks['T2']} diffs={t12m4['T2']['diffs']}", flush=True)
    print(f"T3 {marks['T3']} diffs={t3['diffs']}", flush=True)
    print(f"T4 {marks['T4']} TA={t4['TA_taught_wins']} "
          f"src={t4['probe_taught_source']} TB={t4['TB_control_derived']} "
          f"src={t4['probe_control_source']} ow={t4['overwrite']}",
          flush=True)
    print(f"T6 {marks['T6']} TA={t6['TA_taught_wins']} "
          f"src={t6['probe_taught_source']} TB={t6['TB_control_derived']} "
          f"src={t6['probe_control_source']} grew={t6['grew_slot']} "
          f"ow={t6['overwrite']}", flush=True)
    print(f"M1 {marks['M1']}", flush=True)
    print(f"M4 {marks['M4']} worse={t12m4['M4']['worse']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
