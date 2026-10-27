#!/usr/bin/env python3
"""Exp 138i M2 driver -- 138h's own M1/M2 pieces unchanged on loop138i.

Part A reuses scripts/fable_fix138h_m1pieces.run_simple (read-only) with
the fresh-loop builder pointed at loop138i, mirroring 138h's M1 (162b,
165, 166c, 173-t1/t1b, 167b). Part B reuses scripts/fable_fix138h_m2
m2_* functions (read-only) with fresh138h/build138h re-pointed at
loop138i (m2_139e is copied here with the builder swapped since it
closes over its own build_h). Diffs must be exactly the predicted 173b
/ 154e / 171b moves + 138h-lineage classes in PASSMARKS.md (pilot
first); anything else FAILs the mark.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138i_m2.py --out <path> [--only A|B]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"


def fresh138i(extra: dict | None = None):
    d = tempfile.mkdtemp(prefix="m2-138i-")
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    if extra:
        cfg.update(extra)
    return L138I.build_agent138i(cfg)


def build138i_extra(extra: dict):
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg.update(extra)
    return L138I.build_agent138i(cfg)


def triples(loop) -> list[list]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


# --------------------------------------------------- Part A: 138h M1 jobs
def part_a() -> dict:
    import fable_fix138h_m1pieces as M1H  # noqa: E402 (driver, read-only)
    M1H.build138h = build138i_extra  # type: ignore[method-assign]
    out: dict = {}
    import fable_fix162b_probe as P162B  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-plural162b-20260922"
                         / "probe162b-loop162b.json").read_text(
                             encoding="utf-8"))["cases"]
    out["162b"] = M1H.run_simple(
        "162b", ROOT / "artifacts" / "fable-plural162b-20260922"
        / "cases162b.json", {r["id"]: r for r in frozen},
        P162B.run_case, M1H.mkbase("fable_loop162b_agent"), P162B.drive)
    import fable_fix165_probe as P165  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-typo165-20260922"
                         / "probe165-loop165.json").read_text(
                             encoding="utf-8"))["cases"]
    out["165"] = M1H.run_simple(
        "165", ROOT / "artifacts" / "fable-typo165-20260922"
        / "cases165.json", {r["id"]: r for r in frozen},
        P165.run_case, M1H.mkbase("fable_loop165_agent"), P165.drive)
    import fable_fix166c_probe as P166C  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-me166c-20260922"
                         / "probe166c-loop166c.json").read_text(
                             encoding="utf-8"))["cases"]
    fmap = {r["id"]: {"verdict": r["verdict"], "replies": r["replies"],
                      "stored": r["stored"], "asks": r["asks"]}
            for r in frozen}
    out["166c"] = M1H.run_simple(
        "166c", ROOT / "artifacts" / "fable-me166-20260922"
        / "cases166.json", fmap,
        P166C.run_case, M1H.mkbase("fable_loop166c_agent"), P166C.drive)
    import fable_fix166c_probeB as P166B  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-me166c-20260922"
                         / "probe166c-B.json").read_text(encoding="utf-8"))
    frozen = frozen["cases"] if isinstance(frozen, dict) else frozen
    out["166c-B"] = M1H.run_simple(
        "166c-B", ROOT / "artifacts" / "fable-me166b-20260922"
        / "cases166b.json", {r["id"]: r for r in frozen},
        P166B.run_case, M1H.mkbase("fable_loop166_agent"), P166B.drive)
    import fable_fix166c_probeC as P166CC  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-me166c-20260922"
                         / "probe166c-C.json").read_text(encoding="utf-8"))
    frozen = frozen["cases"] if isinstance(frozen, dict) else frozen
    out["166c-C"] = M1H.run_simple(
        "166c-C", ROOT / "artifacts" / "fable-me166c-20260922"
        / "cases166c.json", {r["id"]: r for r in frozen},
        P166CC.run_case, M1H.mkbase("fable_loop166_agent"), P166CC.drive)
    import fable_fix173_probe as P173  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-username173-20260922"
                         / "probe173-t1.json").read_text(
                             encoding="utf-8"))["cases"]
    out["173-t1"] = M1H.run_simple(
        "173-t1", ROOT / "artifacts" / "fable-me166-20260922"
        / "cases166.json", {r["id"]: {"verdict": r["verdict"]}
                            for r in frozen},
        P173.check_166_row, M1H.mkbase("fable_loop173_agent"),
        P173.drive_steps, steps_key="teaches")
    frozen = json.loads((ROOT / "artifacts" / "fable-username173-20260922"
                         / "probe173-t1b.json").read_text(
                             encoding="utf-8"))["cases"]
    out["173-t1b"] = M1H.run_simple(
        "173-t1b", ROOT / "artifacts" / "fable-username173-20260922"
        / "cases173.json", {r["id"]: {"verdict": r["verdict"]}
                            for r in frozen},
        P173.check_173_row, M1H.mkbase("fable_loop173_agent"),
        P173.drive_steps, steps_key="steps")
    import fable_fix167b_probe as P167B  # noqa: E402
    frozen = json.loads((ROOT / "artifacts" / "fable-verb167b-20260922"
                         / "probe167b-loop167b.json").read_text(
                             encoding="utf-8"))["cases"]
    out["167b"] = M1H.run_simple(
        "167b", ROOT / "artifacts" / "fable-verb167b-20260922"
        / "cases167b.json", {r["id"]: r for r in frozen},
        P167B.run_case, M1H.mkbase("fable_loop167b_agent"), P167B.drive)
    return out


# --------------------------------- Part B: 138h M2 gpieces/fpieces on 138i
def m2_139e_138i() -> dict:
    import fable_fix139e_probe as P139E  # noqa: E402 (judge, read-only)
    import fable_loop139c_agent as L139C  # noqa: E402 (frozen base)
    cfg_c = copy.deepcopy(L139C.DEFAULT_CONFIG139C)
    build_i = lambda c: L138I.build_agent138i(  # noqa: E731
        dict(copy.deepcopy(L138I.DEFAULT_CONFIG138I), **c))
    build_c = lambda c: L139C.build_agent139c(  # noqa: E731
        dict(cfg_c, **c))
    cases = json.loads((ROOT / "artifacts" / "fable-tail139e-20260922"
                        / "cases139e.json").read_text(encoding="utf-8"))
    rows = [P139E.run_case(r, build_i, build_c) for r in cases]
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


def part_b() -> dict:
    import fable_fix138h_m2 as M2H  # noqa: E402 (driver, read-only)
    M2H.fresh138h = fresh138i  # type: ignore[method-assign]
    M2H.build138h = build138i_extra  # type: ignore[method-assign]
    out: dict = {"139e": m2_139e_138i(), "137e": M2H.m2_137e(),
                 "158c": M2H.m2_158c(), "168": M2H.m2_168()}
    out.update(M2H.m2_138f())
    # Auto-compare the four known-fail pieces + 142 + 156b vs 138h's
    # sealed M2 outputs (fail-set + got-reply equality, not sealed-pass).
    sealed = json.loads((ROOT / "artifacts" / "fable-agent138h-20260922"
                         / "m2-138h.json").read_text(encoding="utf-8"))
    for piece in ("137e", "158c", "168", "142", "156b"):
        mine = out[piece]
        base = sealed["pieces"][piece]
        mf = mine.get("fails") or mine.get("diffs") or []
        bf = base.get("fails") or base.get("diffs") or []
        mid = sorted([str(x.get("id", x.get("n", x)))
                      for x in mf] if mf and isinstance(mf[0], dict)
                     else [str(x) for x in mf])
        bid = sorted([str(x.get("id", x.get("n", x)))
                      for x in bf] if bf and isinstance(bf[0], dict)
                     else [str(x) for x in bf])
        same_got = True
        if piece in ("137e", "158c", "168") and mid == bid:
            m_by = {str(x.get("id")): x for x in mf}
            b_by = {str(x.get("id")): x for x in bf}
            for i in mid:
                if str(m_by[i].get("got")) != str(b_by[i].get("got")):
                    same_got = False
        mine["vs138h"] = {"fail_ids": mid, "base_fail_ids": bid,
                          "ids_equal": mid == bid, "got_equal": same_got}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138i M2")
    ap.add_argument("--only", default="all")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    out: dict = {"agent": "loop138i", "seconds": 0.0, "pieces": {}}
    rc = 0
    if args.only in ("all", "A"):
        for piece, rep in part_a().items():
            out["pieces"][f"A-{piece}"] = rep
            status = "IDENTICAL" if not rep["diffs"] else "HAS-DIFFS"
            print(f"M2-A {piece}: {status} "
                  f"identical={rep['identical']}/{rep['n']}", flush=True)
            for d in rep["diffs"][:16]:
                print(f"  DIFF {d}", flush=True)
            if rep["diffs"]:
                rc = 1
    if args.only in ("all", "B"):
        for piece, rep in part_b().items():
            out["pieces"][f"B-{piece}"] = rep
            status = "PASS" if rep.get("pass") else "FAIL"
            print(f"M2-B {piece}: {status} "
                  f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:300]}",
                  flush=True)
            for f in rep.get("fails", [])[:12]:
                print(f"  FAILCASE {f}", flush=True)
            if not rep.get("pass"):
                rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    dest = Path(args.out) if args.out else ART138I / "m2-138i.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
