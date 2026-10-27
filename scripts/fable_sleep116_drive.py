#!/usr/bin/env python3
"""Experiment 116 -- RED TEAM of the live sleep inside the daemon (exp 104).

Sealed exp-104 files are never edited; this driver imports them read-only
(`fable_sleep104_drive` mailbox helpers, `Sleep104Daemon` subprocess) and
runs 11 mailbox-only attack runs covering the 32 sealed cases in
artifacts/fable-sleep116-20260922/cases.json (8 families x 4).

Run (Mac CPU, offline; only AFTER cases.json + PASSMARKS.md are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep116_drive.py --root ART --report REP
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep104_drive as D104  # noqa: E402 (mailbox helpers, read-only)

ART = SCRIPTS.parent / "artifacts" / "fable-sleep116-20260922"
FILLERS = ["Hi, how are you?", "Thanks, that helps.",
           "What is the weather like today?", "Tell me a joke.",
           "Good morning!"]
ABSTAIN_RE = re.compile(
    r"don't know|do not know|which |please answer|could you|didn't catch|"
    r"didn't understand|wasn't waiting|left it as|yes or no|pick <",
    re.IGNORECASE)


def has(reply: str, val: str) -> bool:
    return val.lower() in reply.lower()


def is_abstain(reply: str, rec: dict) -> bool:
    if ABSTAIN_RE.search(reply):
        return True
    st = rec.get("status", "")
    if st in (C.MISSING_FACT, C.AMBIGUOUS, C.BROKEN_CHAIN, C.UNKNOWN_ENTITY):
        return True
    return False


def get_record(log: list[dict], fname: str) -> dict:
    for e in log:
        if e.get("event") == "turn" and e.get("file") == fname:
            recs = e.get("records", [])
            return recs[0] if recs else {}
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


def taught_pair_ok(nb, name: str, rel: str, want: str) -> bool:
    return active_values(nb, name, rel) == [want]


def pre_sleep(turns: list[str]) -> int:
    return len(turns)


def drive_run(root: Path, tag: str, seed: int, pre: list[str]) -> dict:
    """Boot a real Sleep104Daemon, submit pre-sleep turns, return handles."""
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = D104.spawn(d, seed, threshold=pre_sleep(pre))
    replies = {}
    for i, text in enumerate(pre, 1):
        name = f"t{i:03d}"
        D104.submit(d, name, text)
        replies[name] = D104.wait_outbox(
            d, name, timeout=900.0 if i == len(pre) else 120.0)
    return {"dir": d, "proc": proc, "replies": replies}


def ask(d: Path, replies: dict, name: str, text: str,
        timeout: float = 120.0) -> str:
    D104.submit(d, name, text)
    replies[name] = D104.wait_outbox(d, name, timeout=timeout)
    return replies[name]


def sleep_info(d: Path) -> dict:
    log = D104.read_log(d)
    sleeps = [e for e in log if e.get("event") == "sleep"]
    first = sleeps[0] if sleeps else {}
    recipe = first.get("recipe", {}) if isinstance(first, dict) else {}
    words = recipe.get("words", [])
    wrec = next((w for w in words if w.get("word") == "maternal_grandmother"),
                {})
    return {"log": log, "sleeps": sleeps, "first": first, "recipe": recipe,
            "installed": bool(recipe.get("installed")),
            "attempted": bool(recipe.get("attempted")),
            "episodes": sum(w.get("episodes", 0) for w in words),
            "oof": wrec.get("oof_best"), "agree": wrec.get("refit_agreement")}


def report_rows(nb) -> list[dict]:
    return [f for f in nb.facts.values()
            if f.get("source") == "sleep-derived"]


def finish(d: Path, proc) -> None:
    try:
        D104.stop_daemon(proc, d, timeout=60.0)
    except RuntimeError:
        proc.kill()
        raise


# ------------------------------------------------------------- run builders
def b_contra() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 13):
        k, m, g, f, dp = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}", f"D{i:02d}", f"P{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
        pre.append(f"{k}'s father is {f}."); truth[(k, "father")] = f
        pre.append(f"{f}'s mother is {dp}."); truth[(f, "mother")] = dp
    for i in range(1, 13):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    for i in range(1, 7):
        pre.append(f"Actually, M{i:02d}'s mother is P{i:02d}.")
        truth[(f"M{i:02d}", "mother")] = f"P{i:02d}"
    pre.extend(FILLERS[:4])
    return pre, {"truth": truth,
                 "stale": {f"K{i:02d}": f"G{i:02d}" for i in range(1, 7)},
                 "current": {f"K{i:02d}": f"P{i:02d}" for i in range(1, 7)}}


def b_coinc() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 13):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
        pre.append(f"{k}'s aunt is {g}."); truth[(k, "aunt")] = g
    for i in range(1, 13):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(FILLERS[:4])
    post = []
    for i in range(1, 5):
        t, n, h = f"T{i:02d}", f"N{i:02d}", f"H{i:02d}"
        post.append(f"{t}'s mother is {n}."); truth[(t, "mother")] = n
        post.append(f"{n}'s mother is {h}."); truth[(n, "mother")] = h
    post.append("T01's aunt is Z01."); truth[("T01", "aunt")] = "Z01"
    post.append("T02's aunt is Z02."); truth[("T02", "aunt")] = "Z02"
    post.append("T04's aunt is H04."); truth[("T04", "aunt")] = "H04"
    return pre, {"truth": truth, "post": post}


def b_collide() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 9):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
    pre.append("Sam's mother is M01."); truth[("Sam", "mother")] = "M01"
    pre.append("Sam's mother is M02.")
    for i in range(1, 9):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.append("Who is Sam's maternal grandmother?")
    pre.append("Who is Sam's maternal grandmother?")
    pre.extend(FILLERS[:4])
    return pre, {"truth": truth}


def b_twomom() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 9):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
    pre.append("K01's mother is M01b.")
    pre.append("M01b's mother is G01b."); truth[("M01b", "mother")] = "G01b"
    pre.append("Actually, K01's mother is M01b.")
    truth[("K01", "mother")] = "M01b"
    for i in range(1, 9):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(FILLERS[:4])
    return pre, {"truth": truth}


def b_taughtwin() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 9):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
    for i in range(1, 5):
        t, n, h = f"T{i:02d}", f"N{i:02d}", f"H{i:02d}"
        pre.append(f"{t}'s mother is {n}."); truth[(t, "mother")] = n
        pre.append(f"{n}'s mother is {h}."); truth[(n, "mother")] = h
    for i in range(1, 5):
        pre.append(f"T{i:02d}'s maternal grandmother is Z{i:02d}.")
        truth[(f"T{i:02d}", "maternal_grandmother")] = f"Z{i:02d}"
    for i in range(1, 9):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(FILLERS[:4])
    return pre, {"truth": truth}


def b_wrongpre() -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, 13):
        k, m = f"K{i:02d}", f"M{i:02d}"
        g2 = f"X{i:02d}" if i <= 8 else f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g2}."); truth[(m, "mother")] = g2
    for i in range(1, 13):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(FILLERS[:4])
    return pre, {"truth": truth}


def b_few(n: int) -> tuple[list[str], dict]:
    pre, truth = [], {}
    for i in range(1, n + 1):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}."); truth[(k, "mother")] = m
        pre.append(f"{m}'s mother is {g}."); truth[(m, "mother")] = g
    for i in range(1, n + 1):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(FILLERS[:2])
    return pre, {"truth": truth}


def flood_fillers() -> list[tuple[str, str]]:
    out = []
    ask_at = {40: ("K01", "M01"), 80: ("K02", "M02"), 120: ("K03", "M03"),
              160: ("K04", "M04"), 200: ("K05", "M05")}
    for i in range(1, 201):
        if i in ask_at:
            k, _ = ask_at[i]
            out.append((f"z{i:03d}", f"Who is {k}'s mother?"))
        else:
            out.append((f"z{i:03d}",
                        f"Just thinking out loud, note number {i}."))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 116 redteam wave")
    ap.add_argument("--root", default=str(ART / "runs"))
    ap.add_argument("--report", default=str(ART / "wave-report.json"))
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None
    t0 = time.time()
    out: dict = {"cases": {}, "runs": {}}

    def want(*names: str) -> bool:
        return only is None or any(n in only for n in names)

    def V(cid: str, verdict: str, detail: str = "", **kw) -> None:
        out["cases"][cid] = {"verdict": verdict, "detail": detail, **kw}

    # ---- A: contradictory episodes
    if want("contra"):
        pre, info = b_contra()
        r = drive_run(root, "contra", 11, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        si = sleep_info(d)
        probes = {}
        for j, (q, cases) in enumerate(
                [("Who is K07's maternal grandmother?", ["A1"]),
                 ("Who is K02's maternal grandmother?", ["A2"]),
                 ("Who is K03's paternal grandmother?", ["A3"]),
                 ("Who is K05's maternal grandmother?", ["A4"])]):
            name = f"p{j + 1:02d}"
            probes[q] = ask(d, replies, name, q)
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        good, dupes = D104.taught_ok(nb, info["truth"])
        inst = si["installed"]
        log = si["log"]
        cur, stale = info["current"], info["stale"]
        for cid, q, key in [("A1", "Who is K07's maternal grandmother?", "K07"),
                            ("A2", "Who is K02's maternal grandmother?", "K02"),
                            ("A4", "Who is K05's maternal grandmother?", "K05")]:
            rp = probes[q]
            rec = get_record(log, [k for k in replies if replies[k] == rp
                                   and k.startswith("p")][0])
            ab = is_abstain(rp, rec)
            if cid == "A1":
                ok = (ab and not inst) or (inst and has(rp, "G07"))
                bad = has(rp, "P07") and "G07" not in rp.lower()
                V(cid, "OK" if (ok and not bad) else "BUG",
                  f"installed={int(inst)} abstain={int(ab)} reply={rp.strip()[:90]}")
            else:
                wantv = cur[key]
                stalev = stale[key]
                if has(rp, stalev) and not has(rp, wantv):
                    V(cid, "BUG",
                      f"STALE answer: installed={int(inst)} reply={rp.strip()[:90]}")
                elif ab or has(rp, wantv):
                    V(cid, "OK",
                      f"installed={int(inst)} abstain={int(ab)} reply={rp.strip()[:90]}")
                else:
                    V(cid, "BUG",
                      f"unexpected reply: installed={int(inst)} reply={rp.strip()[:90]}")
        rp3 = probes["Who is K03's paternal grandmother?"]
        rec3 = get_record(log, "p03")
        norel = not any(f.get("relation") == "paternal_grandmother"
                        for f in nb.facts.values())
        V("A3", "OK" if (is_abstain(rp3, rec3) and norel) else "BUG",
          f"reply={rp3.strip()[:90]} status={rec3.get('status')} norel={int(norel)}")
        out["runs"]["contra"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "taught_good": good, "taught_total": len(info["truth"]),
            "dupes": dupes, "overwrite": D104.sleep_overwrites(nb)}

    # ---- B: coincidental aunt pattern
    if want("coinc"):
        pre, info = b_coinc()
        r = drive_run(root, "coinc", 12, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        for j, text in enumerate(info["post"], 1):
            ask(d, replies, f"s{j:02d}", text)
        si = sleep_info(d)
        inst = si["installed"]
        probs = ["Who is T01's maternal grandmother?",
                 "Who is T02's maternal grandmother?",
                 "Who is T03's maternal grandmother?",
                 "Who is T04's maternal grandmother?"]
        got = {}
        for j, q in enumerate(probs, 1):
            got[q] = ask(d, replies, f"p{j:02d}", q)
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = si["log"]
        good, dupes = D104.taught_ok(nb, info["truth"])
        exp = {"B1": ("H01", "Z01"), "B2": ("H02", "Z02"),
               "B3": ("H03", None), "B4": ("H04", None)}
        for j, (cid, q) in enumerate(zip(["B1", "B2", "B3", "B4"], probs), 1):
            rp = got[q]
            rec = get_record(log, f"p{j:02d}")
            ab = is_abstain(rp, rec)
            tv, av = exp[cid]
            if av and has(rp, av) and not has(rp, tv):
                V(cid, "BUG", f"AUNT-LATCH: reply={rp.strip()[:90]}")
            elif cid == "B4" and inst and not (has(rp, tv) or ab):
                V(cid, "BUG", f"control failed: reply={rp.strip()[:90]}")
            elif has(rp, tv) or (ab and not inst):
                V(cid, "OK",
                  f"installed={int(inst)} abstain={int(ab)} reply={rp.strip()[:90]}")
            elif ab and inst:
                V(cid, "OK",
                  f"installed but abstained (safe): reply={rp.strip()[:90]}")
            else:
                V(cid, "BUG", f"unexpected: reply={rp.strip()[:90]}")
        out["runs"]["coinc"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "taught_good": good, "taught_total": len(info["truth"]),
            "dupes": dupes, "overwrite": D104.sleep_overwrites(nb)}

    # ---- C: name collisions
    if want("collide"):
        pre, info = b_collide()
        r = drive_run(root, "collide", 13, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        # Sam teaches are t017 (M01) and t018 (M02, must not write)
        sam2 = replies["t018"]
        si = sleep_info(d)
        inst = si["installed"]
        p1 = ask(d, replies, "p01", "Who is Sam's mother?")
        p2 = ask(d, replies, "p02", "Who is K01's maternal grandmother?")
        p3 = ask(d, replies, "p03", "Who is K02's maternal grandmother?")
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = si["log"]

        def turn_event(fname: str) -> dict:
            for e in log:
                if e.get("event") == "turn" and e.get("file") == fname:
                    return e
            return {}
        sam_active = active_values(nb, "Sam", "mother")
        sam2wrote = bool(turn_event("t018.txt").get("new_fact_ids"))
        V("C1", "OK" if (sam2.strip() and sam_active == ["M01"]
                         and not sam2wrote) else "BUG",
          f"reply={sam2.strip()[:90]} active={sam_active} wrote={int(sam2wrote)}")
        rec1 = get_record(log, "p01")
        ab1 = is_abstain(p1, rec1)
        ans1 = rec1.get("fields", {}).get("answer", "")
        V("C2", "OK" if (ab1 or ans1 == "M01" or has(p1, "M01")) else "BUG",
          f"reply={p1.strip()[:90]} answer={ans1}")
        for cid, rp, nm, gv in [("C3a", p2, "p02", "G01"),
                                ("C3b", p3, "p03", "G02")]:
            rec = get_record(log, nm)
            ab = is_abstain(rp, rec)
            if (inst and has(rp, gv)) or (not inst and ab):
                out["cases"][cid] = {"verdict": "OK",
                                     "detail": f"reply={rp.strip()[:80]}"}
            elif ab and inst:
                out["cases"][cid] = {"verdict": "OK",
                                     "detail": f"abstain-while-installed (safe): {rp.strip()[:80]}"}
            else:
                out["cases"][cid] = {"verdict": "BUG",
                                     "detail": f"reply={rp.strip()[:80]}"}
        c3 = ("OK" if all(out["cases"][k]["verdict"] == "OK"
                          for k in ("C3a", "C3b")) else "BUG")
        V("C3", c3, "; ".join(f"{k}={out['cases'][k]['detail']}"
                              for k in ("C3a", "C3b")))
        # reboot + re-ask
        proc2 = D104.spawn(d, 13)
        q1 = ask(d, {}, "q01", "Who is Sam's mother?")
        q2 = ask(d, {}, "q02", "Who is K01's maternal grandmother?")
        q3 = ask(d, {}, "q03", "Who is K02's maternal grandmother?")
        finish(d, proc2)
        nb2 = C.Notebook(d / "notebook")
        good2, dupes2 = D104.taught_ok(nb2, info["truth"])
        same = (("M01" in q1 or is_abstain(q1, {})) and
                ("G01" in q2 or is_abstain(q2, {})) and
                ("G02" in q3 or is_abstain(q3, {})))
        V("C4", "OK" if (same and good2 == len(info["truth"])) else "BUG",
          f"q={[q1.strip()[:40], q2.strip()[:40], q3.strip()[:40]]} taught={good2}")
        out["runs"]["collide"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "dupes": dupes2, "overwrite": D104.sleep_overwrites(nb2)}

    # ---- D: two mothers
    if want("twomom"):
        pre, info = b_twomom()
        r = drive_run(root, "twomom", 14, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        dbl = replies["t017"]
        cor = replies["t019"]
        si = sleep_info(d)
        inst = si["installed"]
        p1 = ask(d, replies, "p01", "Who is K01's maternal grandmother?")
        p2 = ask(d, replies, "p02", "Who is K02's maternal grandmother?")
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = si["log"]
        # D1/D2 from post-stop notebook + captured replies + log write flags
        m_now = active_values(nb, "K01", "mother")
        t017wrote = any(e.get("event") == "turn" and e.get("file") == "t017.txt"
                        and e.get("new_fact_ids") for e in log)
        V("D1", "OK" if (m_now == ["M01b"] and not t017wrote) else "BUG",
          f"double-teach reply={dbl.strip()[:80]} wrote={int(bool(t017wrote))} "
          f"final-active={m_now} "
          f"(conflict must clarify; Actually-correction sets M01b)")
        V("D2", "OK" if (taught_pair_ok(nb, "K01", "mother", "M01b")
                         and cor.strip()) else "BUG",
          f"correction reply={cor.strip()[:80]} active={m_now}")
        rec1 = get_record(log, "p01")
        ab1 = is_abstain(p1, rec1)
        if has(p1, "G01b") or (ab1 and not inst):
            V("D3", "OK", f"installed={int(inst)} reply={p1.strip()[:90]}")
        elif ab1 and inst:
            V("D3", "OK", f"abstain-while-installed (safe): {p1.strip()[:90]}")
        elif has(p1, "G01") and "G01b" not in p1:
            V("D3", "BUG", f"STALE via superseded M01: {p1.strip()[:90]}")
        else:
            V("D3", "BUG", f"unexpected: {p1.strip()[:90]}")
        rec2 = get_record(log, "p02")
        ab2 = is_abstain(p2, rec2)
        good, dupes = D104.taught_ok(nb, info["truth"])
        ow = D104.sleep_overwrites(nb)
        d4ok = (good == len(info["truth"]) and dupes == 0 and ow == 0
                and (has(p2, "G02") or ab2) and "wrong" not in p2.lower())
        V("D4", "OK" if d4ok else "BUG",
          f"taught={good}/{len(info['truth'])} dupes={dupes} ow={ow} ctrl={p2.strip()[:60]}")
        out["runs"]["twomom"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "taught_good": good, "dupes": dupes, "overwrite": ow}

    # ---- E: taught contradicts derived
    if want("taughtwin"):
        pre, info = b_taughtwin()
        r = drive_run(root, "taughtwin", 15, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        si = sleep_info(d)
        inst = si["installed"]
        got = {}
        for j, q in enumerate(
                ["Who is T01's maternal grandmother?",
                 "Who is T02's maternal grandmother?",
                 "Who is T03's maternal grandmother?"], 1):
            got[q] = ask(d, replies, f"p{j:02d}", q)
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = si["log"]
        stored = {i: taught_pair_ok(nb, f"T{i:02d}", "maternal_grandmother",
                                    f"Z{i:02d}") for i in (1, 2, 3)}
        e1reply = replies["t025"]
        e1wrote = any(e.get("event") == "turn" and e.get("file") == "t025.txt"
                      and e.get("new_fact_ids") for e in log)
        V("E1", "OK" if e1reply.strip() else "BUG",
          f"reply={e1reply.strip()[:90]} wrote={int(bool(e1wrote))} stored={stored}")
        for cid, i, q in [("E2", 1, "Who is T01's maternal grandmother?"),
                          ("E3", 2, "Who is T02's maternal grandmother?")]:
            rp = got[q]
            rec = get_record(log, f"p{i:02d}")
            ab = is_abstain(rp, rec)
            zv, gv = f"Z{i:02d}", f"G{i:02d}"
            src = rec.get("fields", {}).get("source", "")
            if stored[i]:
                if has(rp, zv) or ab:
                    V(cid, "OK",
                      f"stored; installed={int(inst)} abstain={int(ab)} "
                      f"src={src} reply={rp.strip()[:80]}")
                elif has(rp, gv):
                    V(cid, "BUG",
                      f"TAUGHT OVERRIDDEN by derived: src={src} reply={rp.strip()[:80]}")
                else:
                    V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
            else:
                if has(rp, gv) or ab:
                    V(cid, "OK",
                      f"not-storable branch; reply={rp.strip()[:80]}")
                else:
                    V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
        rp4 = got["Who is T03's maternal grandmother?"]
        rec4 = get_record(log, "p03")
        src4 = rec4.get("fields", {}).get("source", "")
        rows_active = all(stored.values())
        ow = D104.sleep_overwrites(nb)
        if stored[3] and has(rp4, "Z03") and src4 == "sleep-derived":
            V("E4", "BUG",
              f"taught win mislabeled sleep-derived: {rp4.strip()[:80]}")
        elif ow == 0 and rows_active and (
                has(rp4, "Z03") or is_abstain(rp4, rec4)):
            V("E4", "OK",
              f"taught intact src={src4} reply={rp4.strip()[:80]}")
        elif not stored[3] and ow == 0:
            V("E4", "OK", f"not-storable branch, ow=0 reply={rp4.strip()[:80]}")
        else:
            V("E4", "BUG",
              f"ow={ow} stored={stored} src={src4} reply={rp4.strip()[:80]}")
        out["runs"]["taughtwin"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "stored": stored, "overwrite": ow}

    # ---- F: wrong teaches before any question
    if want("wrongpre"):
        pre, info = b_wrongpre()
        r = drive_run(root, "wrongpre", 16, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        si = sleep_info(d)
        inst = si["installed"]
        p1 = ask(d, replies, "p01", "Who is K01's maternal grandmother?")
        p2 = ask(d, replies, "p02", "Who is K09's maternal grandmother?")
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = si["log"]
        rec1 = get_record(log, "p01")
        src1 = rec1.get("fields", {}).get("source", "")
        trail1 = rec1.get("fields", {}).get("trail", [])
        ab1 = is_abstain(p1, rec1)
        if inst and has(p1, "X01") and src1 == "sleep-derived":
            V("F1", "OK",
              f"wrong-vs-truth X01, provenance sleep-derived (measured)")
        elif not inst and ab1:
            V("F1", "OK", "refused + abstained (safe)")
        else:
            V("F1", "BUG",
              f"src={src1} reply={p1.strip()[:90]} installed={int(inst)}")
        reps = [f["fact_id"] for f in report_rows(nb)
                if f.get("relation") == "sleep_report"]
        if (not inst and ab1) or (trail1 and trail1[0] in reps):
            V("F2", "OK", f"trail-head={trail1[:1]} reports={reps}")
        else:
            V("F2", "BUG",
              f"trail does not head report: {trail1[:2]} reports={reps}")
        good, dupes = D104.taught_ok(nb, info["truth"])
        ow = D104.sleep_overwrites(nb)
        V("F3", "OK" if (good == len(info["truth"]) and dupes == 0
                         and ow == 0) else "BUG",
          f"taught={good}/{len(info['truth'])} dupes={dupes} ow={ow}")
        rec2 = get_record(log, "p02")
        ab2 = is_abstain(p2, rec2)
        if has(p2, "G09") or (ab2 and not inst):
            V("F4", "OK", f"reply={p2.strip()[:80]}")
        else:
            V("F4", "BUG", f"contaminated: {p2.strip()[:80]}")
        out["runs"]["wrongpre"] = {
            "installed": inst, "attempted": si["attempted"],
            "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
            "taught_good": good, "dupes": dupes, "overwrite": ow,
            "wrong_vs_truth": int(inst and has(p1, "X01"))}

    # ---- G1-G4: 200-file flood during sleep
    if want("flood"):
        pre, _ = b_few(12)
        d = root / "flood"
        if d.exists():
            shutil.rmtree(d)
        truth12 = {}
        for i in range(1, 13):
            truth12[(f"K{i:02d}", "mother")] = f"M{i:02d}"
        proc = D104.spawn(d, 17, threshold=len(pre))
        replies = {}
        for i, text in enumerate(pre, 1):
            name = f"t{i:03d}"
            D104.submit(d, name, text)
            if i == len(pre):
                flood = flood_fillers()
                for fname, ftext in flood:
                    D104.submit(d, fname, ftext)
                replies[name] = D104.wait_outbox(d, name, timeout=900.0)
            else:
                replies[name] = D104.wait_outbox(d, name, timeout=120.0)
        flood_got = {}
        for fname, _ in flood:
            flood_got[fname] = D104.wait_outbox(d, fname, timeout=300.0)
        si = sleep_info(d)
        try:
            D104.stop_daemon(proc, d, timeout=60.0)
            stopclean = True
        except RuntimeError:
            proc.kill()
            stopclean = False
        missing = [f for f in flood_got if not flood_got[f].strip()]
        V("G1", "OK" if not missing else "BUG",
          f"replies={len(flood_got) - len(missing)}/200 missing={missing[:5]}")
        V("G2", "OK" if stopclean else "BUG",
          f"clean-stop={int(stopclean)}")
        extra = [e for e in si["sleeps"][1:]
                 if e.get("recipe", {}).get("attempted")]
        V("G3", "OK" if (si["sleeps"] and not extra) else "BUG",
          f"sleeps={len(si['sleeps'])} attempted-first={si['recipe'].get('attempted')} "
          f"extra-attempted={len(extra)} installed={int(si['installed'])}")
        aims = {f"z{i:03d}": m for i, m in
                zip([40, 80, 120, 160, 200],
                    ["M01", "M02", "M03", "M04", "M05"])}
        ok4 = all(has(flood_got[f], m) for f, m in aims.items())
        V("G4", "OK" if ok4 else "BUG",
          "; ".join(f"{f}={flood_got[f].strip()[:50]}" for f in aims))
        out["runs"]["flood"] = {
            "installed": si["installed"], "attempted": si["attempted"],
            "episodes": si["episodes"], "sleeps": len(si["sleeps"])}

    # ---- G5-G8: STOP mid-sleep
    if want("stop"):
        pre, _ = b_few(8)
        d = root / "stop"
        if d.exists():
            shutil.rmtree(d)
        proc = D104.spawn(d, 18, threshold=len(pre))
        replies = {}
        for i, text in enumerate(pre[:-1], 1):
            name = f"t{i:03d}"
            D104.submit(d, name, text)
            replies[name] = D104.wait_outbox(d, name, timeout=120.0)
        D104.submit(d, f"t{len(pre):03d}", pre[-1])
        marker = d / "sleep104-SLEEPING"
        deadline = time.time() + 300.0
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if marker.exists():
                break
            time.sleep(0.05)
        saw = marker.exists()
        (d / "STOP").write_text("stop\n", encoding="utf-8")
        try:
            got = D104.wait_outbox(d, f"t{len(pre):03d}", timeout=600.0)
        except RuntimeError:
            got = ""
        t1 = time.time()
        while time.time() - t1 < 180.0:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        code = proc.poll()
        if code is None:
            proc.kill()
            code = proc.poll()
        try:
            proc._log.close()  # type: ignore[attr-defined]
        except (OSError, ValueError):
            pass
        log = D104.read_log(d)
        stopped = any(e.get("event") == "stopped" for e in log)
        V("G5", "OK" if (code == 0 and stopped and saw) else "BUG",
          f"saw-marker={int(saw)} exit={code} stopped={int(stopped)}")
        V("G6", "OK" if got.strip() else "BUG",
          f"trigger reply present={int(bool(got.strip()))}")
        proc2 = D104.spawn(d, 18)
        status = json.loads((d / "daemon_status.json").read_text(
            encoding="utf-8"))
        q: dict = {}
        for j, qq in enumerate(["Who is K01's maternal grandmother?",
                                "Who is K02's maternal grandmother?"], 1):
            q[qq] = ask(d, q, f"q{j:02d}", qq)
        finish(d, proc2)
        nb = C.Notebook(d / "notebook")
        truth8 = {}
        for i in range(1, 9):
            truth8[(f"K{i:02d}", "mother")] = f"M{i:02d}"
            truth8[(f"M{i:02d}", "mother")] = f"G{i:02d}"
        good, dupes = D104.taught_ok(nb, truth8)
        ow = D104.sleep_overwrites(nb)
        wp = d / "sleep104-word.json"
        if wp.exists():
            wvalid: bool | None = D104.check_routing(d)
            wstate = "valid" if wvalid else "INVALID"
        else:
            wstate = "absent"
        V("G7", "OK" if (status.get("boot_ok") and good == 16 and dupes == 0
                         and ow == 0 and wstate in ("valid", "absent"))
          else "BUG",
          f"boot_ok={status.get('boot_ok')} taught={good}/16 dupes={dupes} "
          f"ow={ow} word={wstate}")
        wrong = sum(1 for v in q.values()
                    if not (is_abstain(v, {}) or "G0" in v))
        abst = sum(1 for v in q.values() if is_abstain(v, {}))
        if wrong == 0 and ((wstate == "valid" and abst == 0) or
                           (wstate == "absent")):
            V("G8", "OK",
              f"word={wstate} replies={[v.strip()[:50] for v in q.values()]}")
        elif wrong == 0 and wstate == "valid" and abst > 0:
            V("G8", "OK", f"valid word but abstained (safe): "
                          f"{[v.strip()[:50] for v in q.values()]}")
        else:
            V("G8", "BUG",
              f"word={wstate} replies={[v.strip()[:50] for v in q.values()]}")
        out["runs"]["stop"] = {"exit": code, "stopped": stopped,
                               "word": wstate, "taught_good": good}

    # ---- H: too few episodes
    for tag, seed, wantn in [("few5", 19, "H1"), ("few10", 20, "H2"),
                             ("few15", 21, "H3")]:
        if not want(tag):
            continue
        n = {"few5": 5, "few10": 10, "few15": 15}[tag]
        pre, info = b_few(n)
        r = drive_run(root, tag, seed, pre)
        d, proc, replies = r["dir"], r["proc"], r["replies"]
        p1 = ask(d, replies, "p01", "Who is K01's maternal grandmother?")
        p2 = ask(d, replies, "p02", "Who is K02's maternal grandmother?")
        finish(d, proc)
        nb = C.Notebook(d / "notebook")
        log = D104.read_log(d)
        si = sleep_info(d)
        inst, att = si["installed"], si["attempted"]
        ab = [is_abstain(p1, get_record(log, "p01")),
              is_abstain(p2, get_record(log, "p02"))]
        wrong = [not (a or has(p, "G01" if i == 0 else "G02"))
                 for i, (p, a) in enumerate(zip([p1, p2], ab))]
        if tag == "few5":
            V("H1", "OK" if (not att and not inst and all(ab)
                             and not any(wrong)) else "BUG",
              f"attempted={int(att)} installed={int(inst)} abstain={ab} "
              f"replies={[p1.strip()[:50], p2.strip()[:50]]}")
            rr = len(report_rows(nb))
            good, _ = D104.taught_ok(nb, info["truth"])
            V("H4", "OK" if (rr == 0 and not (d / "sleep104-word.json").exists()
                             and good == 2 * n) else "BUG",
              f"report-rows={rr} word={((d / 'sleep104-word.json').exists())} "
              f"taught={good}/{2 * n}")
        else:
            cid = wantn
            V(cid, "OK" if not any(wrong) else "BUG",
              f"attempted={int(att)} installed={int(inst)} abstain={ab} "
              f"replies={[p1.strip()[:50], p2.strip()[:50]]}")
        out["runs"][tag] = {"installed": inst, "attempted": att,
                            "episodes": si["episodes"], "oof": si["oof"],
                            "agree": si["agree"]}

    out["wave_seconds"] = round(time.time() - t0, 1)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True),
                                 encoding="utf-8")
    for cid in sorted(out["cases"]):
        c = out["cases"][cid]
        print(f"{cid}: {c['verdict']} -- {c['detail'][:100]}", flush=True)
    print(f"wave {out['wave_seconds']}s -> {args.report}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
