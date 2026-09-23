#!/usr/bin/env python3
"""Exp 138g M1+M2 driver -- added-piece probes + 138f-piece probes on loop138g.

M1: each ADDED piece's own sealed probe re-run on loop138g and compared
per-case (verdict + reply + stored) against the piece's sealed rows:
  139e (65, scripts/fable_fix139e_probe.run_case vs cases139e.json;
        tailu exact + diff-vs-139c arms),
  137e (107, sequences from scripts/fable_fix137d_probe by import +
        scripts/fable_fix137e_probe T1b lists; framed arms exact,
        N/O/E arms vs sealed probe137e.json),
  158c (46, teaches+question vs sealed probe158c-rows.json),
  168 (61, parts A/B/C/D vs sealed probe168-results.json).
Interaction cases (pre-listed in PASSMARKS.md with expected replies) are
exempt; anything else non-identical fails the mark.
M2: 138f's M1 (scripts/fable_fix138f_m1 pattern: the 8 remaining 138d
piece probes via scripts/fable_loop138d_m1 with fresh138g) unchanged.
Outputs into artifacts/fable-agent138g-20260922/ (m1-138g-pieces.json,
m1-138g-f.json).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138g_m1.py [--only pieces|f]
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138g_agent as L138G  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138g-20260922"


def fresh138g(extra: dict | None = None) -> object:
    tmp = tempfile.mkdtemp(prefix="m1-138g-")
    cfg = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    if extra:
        cfg.update(extra)
    return L138G.build_agent138g(cfg)


def triples(loop) -> list[list]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


# ------------------------------------------------------------- M1: 139e
def m1_139e() -> dict:
    import fable_fix139e_probe as P139E  # noqa: E402 (judge, read-only)
    import fable_loop139c_agent as L139C  # noqa: E402 (frozen base)
    cfg_c = copy.deepcopy(L139C.DEFAULT_CONFIG139C)
    build_g = lambda c: L138G.build_agent138g(
        dict(copy.deepcopy(L138G.DEFAULT_CONFIG138G), **c))  # noqa: E731
    build_c = lambda c: L139C.build_agent139c(  # noqa: E731
        dict(cfg_c, **c))
    cases = json.loads((ROOT / "artifacts" / "fable-tail139e-20260922"
                        / "cases139e.json").read_text(encoding="utf-8"))
    rows = [P139E.run_case(r, build_g, build_c) for r in cases]
    tails = [r for r in rows if r["mode"] == "tailu"]
    tail_ok = sum(1 for r in tails if r["verdict"] == "OK")
    wrong = sum(1 for r in rows if r["verdict"] == "WRONG-WRITE")
    diffs = [r for r in rows if r["mode"] == "diff"
             and r["verdict"] != "OK"]
    ok = (wrong == 0 and tail_ok == len(tails) and not diffs)
    return {"piece": "139e", "n": len(rows), "tail_exact": tail_ok,
            "tail_need": len(tails), "wrong_writes": wrong,
            "diffs": [{"id": r["id"], "note": r.get("note", "")[:160]}
                      for r in diffs],
            "pass": ok}


# ------------------------------------------------------------- M1: 137e
def m1_137e() -> dict:
    import fable_fix137d_frame as F137D  # noqa: E402 (read-only)
    import fable_fix137d_probe as P137D  # noqa: E402 (T1 lists, read-only)
    import fable_fix137e_probe as P137E  # noqa: E402 (T1b lists, read-only)
    sealed = {r["id"]: r for r in json.loads(
        (ROOT / "artifacts" / "fable-frame137e-20260922" / "probe137e.json")
        .read_text(encoding="utf-8"))["cases"]}
    fails: list = []

    def seq(turns):
        loop = fresh138g()
        replies = [" ".join(loop.turn(t)) for t in turns]
        return replies, triples(loop)

    for i, (marker, pre, rel, val) in enumerate(P137D.SAY_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        r, w = seq([frame, q])
        s = sealed[f"T1-S-say{i:02d}"]
        if not (r == s["reply137e"] and w == s["writes"]):
            fails.append({"id": s["id"], "got": r, "want": s["reply137e"]})
    for i, (marker, pre, rel, val) in enumerate(P137D.HEAR_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        loop = fresh138g()
        r1 = " ".join(loop.turn(frame))
        w1 = triples(loop)
        r2 = " ".join(loop.turn(q))
        w2 = triples(loop)
        if not (r1 == P137E.HEAR_EXACT and w1 == [] and w2 == []
                and val not in r2):
            fails.append({"id": f"T1-S-hear{i:02d}", "got": [r1, r2],
                          "want": [P137E.HEAR_EXACT, f"no {val}"]})
    for i, (marker, rel, real, rival) in enumerate(P137D.CONFLICTS):
        frame = f"{marker} Kim's {rel} is {rival}."
        turns = [f"Kim's {rel} is {real}.", frame,
                 f"What is Kim's {rel}?"]
        replies, w = seq(turns)
        exp1 = P137E.HEAR_EXACT if F137D.frame_kind(frame) == "hearsay" \
            else F137D.say_reply(frame)
        if not (replies[0] == f"Saved: Kim's {rel} is {real}."
                and replies[1] == exp1
                and replies[2] == f"Kim's {rel} is {real}."
                and w == [["Kim", rel, real]]):
            fails.append({"id": f"T1-C-{i:02d}", "got": replies,
                          "want": [f"Saved: Kim's {rel} is {real}.",
                                   exp1, f"Kim's {rel} is {real}."]})
    for i, teach in enumerate(P137D.NAMES_N):
        r, _ = seq([teach])
        s = sealed[f"T1-N-{i:02d}"]
        if r != s["reply137e"]:
            fails.append({"id": s["id"], "got": r,
                          "want": s["reply137e"]})
    for i, turn in enumerate(P137D.OTHERS_O):
        r, _ = seq([turn])
        s = sealed[f"T1-O-{i:02d}"]
        if r != s["reply137e"]:
            fails.append({"id": s["id"], "got": r,
                          "want": s["reply137e"]})
    for i, frame in enumerate(P137E.T1B_HEAR):
        rel = P137E._rel_of(frame)
        val = P137E._val_of(frame)
        q = P137E.T1B_Q[rel]
        loop = fresh138g()
        r1 = " ".join(loop.turn(frame))
        w1 = triples(loop)
        r2 = " ".join(loop.turn(q))
        w2 = triples(loop)
        if not (r1 == P137E.HEAR_EXACT and w1 == [] and w2 == []
                and val not in r2):
            fails.append({"id": f"T1b-H{i:02d}", "got": [r1, r2],
                          "want": [P137E.HEAR_EXACT, f"no {val}"]})
    for i, lead in enumerate(P137E.T1B_SAME):
        if F137D.frame_kind(lead) == "say":
            turns = [lead]
        elif lead.rstrip().endswith("?"):
            turns = [lead]
        else:
            rel = P137E._rel_of(lead)
            q = P137E.T1B_Q[rel]
            if "Kim's" in lead:
                q = "What is Kim's boss?"
            turns = [lead, q]
        r, _ = seq(turns)
        s = sealed[f"T1b-E{i:02d}"]
        if r != s["reply137e"]:
            fails.append({"id": s["id"], "got": r,
                          "want": s["reply137e"]})
    return {"piece": "137e", "n": 107, "fails": fails,
            "pass": not fails}


# ------------------------------------------------------------- M1: 158c
def m1_158c() -> dict:
    suite = json.loads((ROOT / "artifacts" / "fable-whcity158c-20260922"
                        / "cases158c.json").read_text(encoding="utf-8"))
    teaches = list(suite["teaches"])
    sealed = [json.loads(l) for l in
              (ROOT / "artifacts" / "fable-whcity158c-20260922"
               / "probe158c-rows.json").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
    s_by_id = {r["id"]: r for r in sealed}
    fails = []
    for row in suite["cases"]:
        loop = fresh138g()
        for t in teaches:
            loop.turn(t)
        before = len(loop.nb.events)
        reply = " ".join(loop.turn(row["question"])).strip()
        wrote = len(loop.nb.events) - before
        s = s_by_id[row["id"]]
        if not (reply == s["reply158c"] and wrote == s["wrote158c"]):
            fails.append({"id": row["id"], "got": reply[:140],
                          "want": s["reply158c"][:140],
                          "wrote": wrote, "want_wrote": s["wrote158c"]})
    return {"piece": "158c", "n": len(suite["cases"]), "fails": fails,
            "pass": not fails}


# ------------------------------------------------------------- M1: 168
def m1_168() -> dict:
    import fable_fix168_probe as P168  # noqa: E402 (harness, read-only)
    spec = json.loads(P168.CASES.read_text(encoding="utf-8"))
    names = spec["name_check"]["extra_names"]
    sealed = json.loads((ROOT / "artifacts" / "fable-selfground168-20260922"
                         / "probe168" / "probe168-results.json")
                        .read_text(encoding="utf-8"))
    workroot = Path(tempfile.mkdtemp(prefix="m1-168g-"))
    fails: list = []

    def fresh(tag: str):
        d = workroot / tag
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        cfg = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        return L138G.build_agent138g(cfg)

    la = fresh("gA")
    for i, c in enumerate(spec["partA"]):
        ra, ca, wa = P168.turn_logged(la, c["q"])
        bad = [] if ca else P168.violations(ra, P168.nb_names(la), names)
        s = sealed["rowsA"][i]
        if ra != s["m168"] or ca is not None or bad or wa:
            fails.append({"id": f"A{i + 1}", "q": c["q"],
                          "got": ra[:120], "want": s["m168"][:120],
                          "named": bad, "wrote": wa})
    la = fresh("gB")
    for t, s in zip(spec["partB_teaches"],
                    sealed["parts"]["B"]["teaches"]):
        ra, _, _ = P168.turn_logged(la, t)
        if ra != s["m168"]:
            fails.append({"id": f"B-teach {t}", "got": ra[:100],
                          "want": s["m168"][:100]})
    for c, s in zip(spec["partB_asks"], sealed["parts"]["B"]["asks"]):
        ra, ca, wa = P168.turn_logged(la, c["q"])
        if ra != s["m168"] or wa != s["wrote168"]:
            fails.append({"id": f"B-ask {c['q']}", "got": ra[:120],
                          "want": s["m168"][:120]})
    la = fresh("gC0")
    for c, s in zip(spec["partC_empty"],
                    sealed["parts"]["C"]["empty"]):
        ra, ca, wa = P168.turn_logged(la, c["q"])
        if ra != s["m168"] or wa:
            fails.append({"id": f"C0 {c['q']}", "got": ra[:120],
                          "want": s["m168"][:120]})
    ma = fresh("gC1")
    P168.turn_logged(ma, spec["partC_setup_teach"][0])
    P168.file_web_harness(ma)
    P168.file_proposed_harness(ma)
    ma.counters["sleeps"] = 1
    ma.self_sleep_history.append({"tick": ma.tick})
    for c, s in zip(spec["partC_full"],
                    sealed["parts"]["C"]["full"]):
        ra, ca, wa = P168.turn_logged(ma, c["q"])
        if ra != s["m168"]:
            fails.append({"id": f"C1 {c['q']}", "got": ra[:120],
                          "want": s["m168"][:120]})
    la = fresh("gD")
    for t, s in zip(spec["partD"], sealed["parts"]["D"]["rows"]):
        ra, ca, wa = P168.turn_logged(la, t)
        if ra != s["m168"]:
            fails.append({"id": f"D {t}", "got": ra[:120],
                          "want": s["m168"][:120]})
    return {"piece": "168", "n": 61, "fails": fails,
            "pass": not fails}


# ------------------------------------------------------------- M2: 138f pieces
def m2_138f() -> dict:
    import fable_fix138f_m1 as F138M  # noqa: E402 (156b judge, read-only)
    import fable_loop138d_m1 as M1  # noqa: E402 (probes+judges, read-only)
    M1.fresh138d = fresh138g  # type: ignore[method-assign]
    M1.ART = ART  # type: ignore[method-assign]
    F138M.fresh138f = fresh138g  # type: ignore[method-assign]
    out: dict = {}
    for fn in (M1.run142, M1.run146d, M1.run153,
               F138M.run156b_138f, M1.run157, M1.run158, M1.run159,
               M1.run150b):
        rep = fn()
        out[rep["piece"]] = rep
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138g M1+M2")
    ap.add_argument("--only", default="all",
                    help="'pieces', 'f', or 'all'")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    if args.only in ("all", "pieces"):
        out: dict = {"seconds": 0.0, "pieces": {}}
        for fn in (m1_139e, m1_137e, m1_158c, m1_168):
            rep = fn()
            out["pieces"][rep["piece"]] = rep
            status = "PASS" if rep["pass"] else "FAIL"
            print(f"M1 {rep['piece']}: {status} "
                  f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:400]}",
                  flush=True)
            for f in rep.get("fails", [])[:12]:
                print(f"  FAILCASE {f}", flush=True)
            if not rep["pass"]:
                rc = 1
        out["seconds"] = round(time.time() - t0, 1)
        (ART / "m1-138g-pieces.json").write_text(
            json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    if args.only in ("all", "f"):
        t1 = time.time()
        out2 = {"seconds": 0.0, "pieces": m2_138f()}
        for piece, rep in out2["pieces"].items():
            status = "PASS" if rep.get("pass") else "FAIL"
            print(f"M2 {piece}: {status} "
                  f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:300]}",
                  flush=True)
            if not rep.get("pass"):
                rc = 1
        out2["seconds"] = round(time.time() - t1, 1)
        (ART / "m1-138g-f.json").write_text(
            json.dumps(out2, indent=1, sort_keys=True), encoding="utf-8")
    print(f"M1+M2 done in {round(time.time() - t0, 1)}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
