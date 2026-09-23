#!/usr/bin/env python3
"""Exp 138h M2 driver -- 138g's own M1/M2 pieces unchanged on loop138h.

Reuses scripts/fable_loop138d_m1 (probes+judges) and
scripts/fable_fix138f_m1 (156b judge) read-only with the fresh-loop
builder pointed at loop138h, mirroring scripts/fable_fix138g_m1.py m2_138f
plus 138g's four added pieces (139e/137e/158c/168 vs their sealed rows).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138h_m2.py [--only gpieces|f|all]
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

import fable_loop138h_agent as L138H  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138h-20260922"


def fresh138h(extra: dict | None = None) -> object:
    tmp = tempfile.mkdtemp(prefix="m2-138h-")
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    if extra:
        cfg.update(extra)
    return L138H.build_agent138h(cfg)


def build138h(extra: dict) -> object:
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg.update(extra)
    return L138H.build_agent138h(cfg)


def triples(loop) -> list[list]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


# --------------------------------------------------- 138g's M1 on 138h
def m2_139e() -> dict:
    import fable_fix139e_probe as P139E  # noqa: E402 (judge, read-only)
    import fable_loop139c_agent as L139C  # noqa: E402 (frozen base)
    cfg_c = copy.deepcopy(L139C.DEFAULT_CONFIG139C)
    build_h = lambda c: L138H.build_agent138h(  # noqa: E731
        dict(copy.deepcopy(L138H.DEFAULT_CONFIG138H), **c))
    build_c = lambda c: L139C.build_agent139c(  # noqa: E731
        dict(cfg_c, **c))
    cases = json.loads((ROOT / "artifacts" / "fable-tail139e-20260922"
                        / "cases139e.json").read_text(encoding="utf-8"))
    rows = [P139E.run_case(r, build_h, build_c) for r in cases]
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


def m2_137e() -> dict:
    import fable_fix137d_frame as F137D  # noqa: E402 (read-only)
    import fable_fix137d_probe as P137D  # noqa: E402 (T1 lists, read-only)
    import fable_fix137e_probe as P137E  # noqa: E402 (T1b lists, read-only)
    sealed = {r["id"]: r for r in json.loads(
        (ROOT / "artifacts" / "fable-frame137e-20260922" / "probe137e.json")
        .read_text(encoding="utf-8"))["cases"]}
    fails: list = []

    def seq(turns):
        loop = fresh138h()
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
        loop = fresh138h()
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
        loop = fresh138h()
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


def m2_158c() -> dict:
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
        loop = fresh138h()
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


def m2_168() -> dict:
    import fable_fix168_probe as P168  # noqa: E402 (harness, read-only)
    spec = json.loads(P168.CASES.read_text(encoding="utf-8"))
    names = spec["name_check"]["extra_names"]
    sealed = json.loads((ROOT / "artifacts" / "fable-selfground168-20260922"
                         / "probe168" / "probe168-results.json")
                        .read_text(encoding="utf-8"))
    workroot = Path(tempfile.mkdtemp(prefix="m2-168h-"))
    fails: list = []

    def fresh(tag: str):
        d = workroot / tag
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        return L138H.build_agent138h(cfg)

    la = fresh("hA")
    for i, c in enumerate(spec["partA"]):
        ra, ca, wa = P168.turn_logged(la, c["q"])
        bad = [] if ca else P168.violations(ra, P168.nb_names(la), names)
        s = sealed["rowsA"][i]
        if ra != s["m168"] or ca is not None or bad or wa:
            fails.append({"id": f"A{i + 1}", "q": c["q"],
                          "got": ra[:120], "want": s["m168"][:120],
                          "named": bad, "wrote": wa})
    la = fresh("hB")
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
    la = fresh("hC0")
    for c, s in zip(spec["partC_empty"],
                    sealed["parts"]["C"]["empty"]):
        ra, ca, wa = P168.turn_logged(la, c["q"])
        if ra != s["m168"] or wa:
            fails.append({"id": f"C0 {c['q']}", "got": ra[:120],
                          "want": s["m168"][:120]})
    ma = fresh("hC1")
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
    la = fresh("hD")
    for t, s in zip(spec["partD"], sealed["parts"]["D"]["rows"]):
        ra, ca, wa = P168.turn_logged(la, t)
        if ra != s["m168"]:
            fails.append({"id": f"D {t}", "got": ra[:120],
                          "want": s["m168"][:120]})
    return {"piece": "168", "n": 61, "fails": fails,
            "pass": not fails}


# ------------------------------------------------------------- 138f pieces
def m2_138f() -> dict:
    import fable_fix138f_m1 as F138M  # noqa: E402 (156b judge, read-only)
    import fable_loop138d_m1 as M1  # noqa: E402 (probes+judges, read-only)
    M1.fresh138d = fresh138h  # type: ignore[method-assign]
    M1.ART = ART  # type: ignore[method-assign]
    F138M.fresh138f = fresh138h  # type: ignore[method-assign]
    out: dict = {}
    for fn in (M1.run142, M1.run146d, M1.run153,
               F138M.run156b_138f, M1.run157, M1.run158, M1.run159,
               M1.run150b):
        rep = fn()
        out[rep["piece"]] = rep
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138h M2")
    ap.add_argument("--only", default="all",
                    help="'gpieces', 'f', or 'all'")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {"seconds": 0.0, "pieces": {}}
    if args.only in ("all", "gpieces"):
        for fn in (m2_139e, m2_137e, m2_158c, m2_168):
            rep = fn()
            out["pieces"][rep["piece"]] = rep
            status = "PASS" if rep["pass"] else "FAIL"
            print(f"M2-g {rep['piece']}: {status} "
                  f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:400]}",
                  flush=True)
            for f in rep.get("fails", [])[:12]:
                print(f"  FAILCASE {f}", flush=True)
            if not rep["pass"]:
                rc = 1
    if args.only in ("all", "f"):
        t1 = time.time()
        fpieces = m2_138f()
        out["pieces"].update(fpieces)
        for piece, rep in fpieces.items():
            status = "PASS" if rep.get("pass") else "FAIL"
            print(f"M2-f {piece}: {status} "
                  f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:300]}",
                  flush=True)
            if not rep.get("pass"):
                rc = 1
        out["fseconds"] = round(time.time() - t1, 1)
    out["seconds"] = round(time.time() - t0, 1)
    dest = Path(args.out) if args.out else ART / "m2-138h.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
