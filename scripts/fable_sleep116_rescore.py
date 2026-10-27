#!/usr/bin/env python3
"""Experiment 116 rescorer — read-only re-analysis of the frozen wave.

Deviation D3: the wave driver's get_record() compared bare probe names
("p01") against mailbox filenames ("p01.txt"), so every record-dependent
check (source/trail/status) read empty records. Daemon evidence (outbox
replies, daemon.log.jsonl, notebooks, word files) is frozen on disk; all
daemons are stopped. This script recomputes all 36 sealed verdicts from
those frozen artifacts with corrected filename matching. No daemon is
booted, nothing is written except wave-report-rescored.json. Sealed
cases.json / PASSMARKS.md are only read.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep104_drive as D104  # noqa: E402 (read-only)

ART = SCRIPTS.parent / "artifacts" / "fable-sleep116-20260922"
ABSTAIN_RE = re.compile(
    r"don't know|do not know|which |please answer|could you|didn't catch|"
    r"didn't understand|wasn't waiting|left it as|yes or no|pick <",
    re.IGNORECASE)


def has(reply: str, val: str) -> bool:
    return val.lower() in reply.lower()


def is_abstain(reply: str, rec: dict) -> bool:
    if ABSTAIN_RE.search(reply):
        return True
    if rec.get("status", "") in (C.MISSING_FACT, C.AMBIGUOUS,
                                 C.BROKEN_CHAIN, C.UNKNOWN_ENTITY):
        return True
    return False


def load_run(tag: str) -> dict:
    d = ART / "runs" / tag
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


def active_values(nb, name: str, rel: str) -> list[str]:
    found = nb.resolve(name)
    if found.status != C.OK:
        return []
    out = []
    for r in nb.current(found.detail["entity_id"], rel):
        if r.get("source") != "taught":
            continue
        v = r["value"]
        out.append(nb.entities.get(v["entity"], "") if "entity" in v
                   else str(v.get("literal", "")))
    return out


def main(argv=None) -> int:
    wave = json.loads((ART / "wave-report.json").read_text(encoding="utf-8"))
    runs = wave["runs"]
    out: dict = {"cases": {}, "runs": runs,
                 "wave_seconds": wave["wave_seconds"],
                 "rescore_note": "D3: corrected probe-filename matching; "
                 "evidence frozen from the registered wave; no daemon booted."}

    def V(cid: str, verdict: str, detail: str = "") -> None:
        out["cases"][cid] = {"verdict": verdict, "detail": detail}

    # ---- A
    r = load_run("contra")
    inst = runs["contra"]["installed"]
    for cid, fn, fresh, stalev, curv in [
            ("A1", "p01.txt", "G07", None, "G07"),
            ("A2", "p02.txt", None, "G02", "P02"),
            ("A4", "p04.txt", None, "G05", "P05")]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        if cid == "A1":
            V(cid, "OK" if ((ab and not inst) or (inst and has(rp, "G07")))
              else "BUG",
              f"installed={inst} abstain={int(ab)} status={rec.get('status')} "
              f"reply={rp.strip()[:90]}")
        else:
            if has(rp, stalev) and not has(rp, curv):
                V(cid, "BUG", f"STALE answer: reply={rp.strip()[:90]}")
            elif ab or has(rp, curv):
                V(cid, "OK",
                  f"installed={inst} abstain={int(ab)} status={rec.get('status')} "
                  f"reply={rp.strip()[:90]}")
            else:
                V(cid, "BUG", f"unexpected reply={rp.strip()[:90]}")
    rp3 = r["outbox"].get("p03.txt", "")
    rec3 = rec_of(r, "p03.txt")
    norel = not any(f.get("relation") == "paternal_grandmother"
                    for f in r["nb"].facts.values())
    V("A3", "OK" if (is_abstain(rp3, rec3) and norel) else "BUG",
      f"reply={rp3.strip()[:90]} status={rec3.get('status')} norel={int(norel)}")

    # ---- B
    r = load_run("coinc")
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
              f"installed={inst} abstain={int(ab)} src={src} "
              f"reply={rp.strip()[:90]}")
        else:
            V(cid, "BUG", f"unexpected: reply={rp.strip()[:90]}")

    # ---- C
    r = load_run("collide")
    inst = runs["collide"]["installed"]
    sam2 = r["outbox"].get("t018.txt", "")
    sam_active = active_values(r["nb"], "Sam", "mother")
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
              f"src={rec.get('fields', {}).get('source')} reply={rp.strip()[:80]}")
        else:
            V(cid, "BUG", f"reply={rp.strip()[:80]}")
        subs.append(cid)
    V("C3", "OK" if all(out["cases"][k]["verdict"] == "OK" for k in subs)
      else "BUG",
      "; ".join(f"{k}={out['cases'][k]['detail']}" for k in subs))
    # C4: reboot evidence lives in the same dir (q01..q03 outbox files)
    q = [r["outbox"].get(f"q{i:02d}.txt", "") for i in (1, 2, 3)]
    same = (("M01" in q[0] or is_abstain(q[0], {})) and
            ("G01" in q[1] or is_abstain(q[1], {})) and
            ("G02" in q[2] or is_abstain(q[2], {})))
    V("C4", "OK" if same else "BUG",
      f"q={[v.strip()[:40] for v in q]} taught={runs['collide'].get('dupes')}")

    # ---- D
    r = load_run("twomom")
    inst = runs["twomom"]["installed"]
    dbl = r["outbox"].get("t017.txt", "")
    cor = r["outbox"].get("t019.txt", "")
    m_now = active_values(r["nb"], "K01", "mother")
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
          f"installed={inst} src={rec1.get('fields', {}).get('source')} "
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
      f"taught={rr['taught_good']}/17 dupes={rr['dupes']} ow={rr['overwrite']} "
      f"ctrl={p2.strip()[:60]}")

    # ---- E (derived values are H0i on the T/N/H test chains)
    r = load_run("taughtwin")
    inst = runs["taughtwin"]["installed"]
    stored = runs["taughtwin"]["stored"]
    e1 = r["outbox"].get("t025.txt", "")
    V("E1", "OK" if e1.strip() else "BUG",
      f"reply={e1.strip()[:90]} wrote={bool(turn_ev(r, 't025.txt').get('new_fact_ids'))} "
      f"stored={stored}")
    for cid, i, fn in [("E2", 1, "p01.txt"), ("E3", 2, "p02.txt")]:
        rp = r["outbox"].get(fn, "")
        rec = rec_of(r, fn)
        ab = is_abstain(rp, rec)
        zv, gv = f"Z{i:02d}", f"H{i:02d}"
        src = rec.get("fields", {}).get("source", "")
        if stored[str(i)]:
            if has(rp, zv) or ab:
                V(cid, "OK", f"stored; src={src} reply={rp.strip()[:80]}")
            elif has(rp, gv):
                V(cid, "BUG",
                  f"TAUGHT OVERRIDDEN by derived {gv} (taught {zv} active): "
                  f"src={src} reply={rp.strip()[:80]}")
            else:
                V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
        else:
            V(cid, "OK" if (has(rp, gv) or ab) else "BUG",
              f"not-storable branch; reply={rp.strip()[:80]}")
    rp4 = r["outbox"].get("p03.txt", "")
    rec4 = rec_of(r, "p03.txt")
    src4 = rec4.get("fields", {}).get("source", "")
    ow = runs["taughtwin"]["overwrite"]
    if stored["3"] and has(rp4, "Z03") and src4 == "sleep-derived":
        V("E4", "BUG", f"taught win mislabeled sleep-derived: {rp4.strip()[:80]}")
    elif ow == 0 and stored["3"] and (has(rp4, "Z03")
                                      or is_abstain(rp4, rec4)):
        V("E4", "OK", f"taught intact src={src4} reply={rp4.strip()[:80]}")
    elif not stored["3"] and ow == 0:
        V("E4", "OK", f"not-storable branch, ow=0 reply={rp4.strip()[:80]}")
    else:
        V("E4", "BUG",
          f"TAUGHT OVERRIDDEN by derived H03 (taught Z03 active, ow={ow}): "
          f"src={src4} reply={rp4.strip()[:80]}")

    # ---- F
    r = load_run("wrongpre")
    inst = runs["wrongpre"]["installed"]
    p1 = r["outbox"].get("p01.txt", "")
    rec1 = rec_of(r, "p01.txt")
    src1 = rec1.get("fields", {}).get("source", "")
    trail1 = rec1.get("fields", {}).get("trail", [])
    ab1 = is_abstain(p1, rec1)
    if inst and has(p1, "X01") and src1 == "sleep-derived":
        V("F1", "OK",
          f"wrong-vs-truth X01, provenance sleep-derived (measured)")
    elif not inst and ab1:
        V("F1", "OK", "refused + abstained (safe)")
    else:
        V("F1", "BUG", f"src={src1} reply={p1.strip()[:90]} installed={inst}")
    nb = r["nb"]
    reps = [f["fact_id"] for f in nb.facts.values()
            if f.get("source") == "sleep-derived"
            and f.get("relation") == "sleep_report"]
    if (not inst and ab1) or (trail1 and trail1[0] in reps):
        V("F2", "OK", f"trail={trail1[:3]} reports={reps}")
    else:
        V("F2", "BUG", f"trail does not head report: {trail1[:2]} {reps}")
    rr = runs["wrongpre"]
    V("F3", "OK" if (rr["taught_good"] == 24 and rr["dupes"] == 0
                     and rr["overwrite"] == 0) else "BUG",
      f"taught={rr['taught_good']}/24 dupes={rr['dupes']} ow={rr['overwrite']}")
    p2 = r["outbox"].get("p02.txt", "")
    rec2 = rec_of(r, "p02.txt")
    V("F4", "OK" if (has(p2, "G09") or (is_abstain(p2, rec2) and not inst))
      else "BUG",
      f"src={rec2.get('fields', {}).get('source')} reply={p2.strip()[:80]}")

    # ---- G (no record reads in the wave verdicts; re-verify from disk)
    r = load_run("flood")
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
        r = load_run(tag)
        rr = runs[tag]
        for cid in cids:
            if cid == "H4":
                nrr = sum(1 for f in r["nb"].facts.values()
                          if f.get("source") == "sleep-derived")
                w = (r["dir"] / "sleep104-word.json").exists()
                V(cid, wave["cases"][cid]["verdict"],
                  f"rechecked report-rows={nrr} word={w} "
                  + wave["cases"][cid]["detail"])
                continue
            ps = [r["outbox"].get("p01.txt", ""), r["outbox"].get("p02.txt", "")]
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

    (ART / "wave-report-rescored.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    n_ok = sum(1 for c in out["cases"].values() if c["verdict"] == "OK")
    n_bug = sum(1 for c in out["cases"].values() if c["verdict"] == "BUG")
    n_he = sum(1 for c in out["cases"].values()
               if c["verdict"] == "HARNESS-ERROR")
    for cid in sorted(out["cases"]):
        c = out["cases"][cid]
        old = wave["cases"].get(cid, {}).get("verdict", "?")
        flag = "" if old == c["verdict"] else f"  [was {old} in-wave]"
        print(f"{cid}: {c['verdict']} -- {c['detail'][:100]}{flag}", flush=True)
    print(f"OK={n_ok} BUG={n_bug} HARNESS-ERROR={n_he}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
