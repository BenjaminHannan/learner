#!/usr/bin/env python3
"""Exp 138j M2 driver -- 138i's own M1/M2/G3 cases unchanged on loop138j.

M2-M1: reuses scripts/fable_fix138i_m1pieces runners (read-only) with
  the 138i module reference re-pointed at a loop138j facade (rebinding
  the import name inside that driver module only; no file edited), then
  joins every 138j diff against the sealed m1-138i-pieces.json rows:
  a diff ALSO diffing on sealed 138i (same got) is inherited; anything
  else must be in the C-layer predicted set in PASSMARKS.md. Ids that
  diffed on sealed 138i but no longer diff on 138j are reported as
  RESOLVED (also predicted).
M2-A: mirrors scripts/fable_fix138i_m2.part_a (138h M1 jobs via
  fable_fix138h_m1pieces.run_simple with the builder pointed at
  loop138j), compared vs sealed m2-138i.json.
M2-B: mirrors part_b (m2_139e/137e/158c/168/138f bundle) with the
  builder pointed at loop138j, compared vs sealed m2-138i.json
  (fail-ids + got).
M2-G3: replays sealed cases138i-g3.json pairs on loop138j vs the sealed
  138i replies + stored.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138j_m2.py --out <path> [--only <csv>]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138j_agent as L138J  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART138J = ROOT / "artifacts" / "fable-agent138j-20260922"
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"


def fresh138j(extra: dict | None = None):
    d = tempfile.mkdtemp(prefix="m2-138j-")
    cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    if extra:
        cfg.update(extra)
    return L138J.build_agent138j(cfg)


def build138j_extra(extra: dict):
    cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    cfg.update(extra)
    return L138J.build_agent138j(cfg)


def triples(loop) -> list[list]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def facade138j():
    return types.SimpleNamespace(
        DEFAULT_CONFIG138I=copy.deepcopy(L138J.DEFAULT_CONFIG138J),
        build_agent138i=build138j_extra,
        Loop138iDaemon=L138J.Loop138jDaemon,
        Loop138iEars=L138J.Loop138jEars,
        Loop138iAgentLoop=L138J.Loop138jAgentLoop)


# ------------------------------------------- M2-M1: 138i M1 jobs on 138j
def m2_m1() -> dict:
    import fable_fix138i_m1pieces as I1  # noqa: E402 (driver, read-only)
    I1.L138I = facade138j()  # type: ignore[method-assign]
    # Run the full 138i M1 main (all its runners) with --out redirected
    # by re-pointing that driver's artifact dir at scratch.
    import io
    from contextlib import redirect_stdout
    I1.ART138I = Path(tempfile.mkdtemp(prefix="m2m1-138j-"))  # type: ignore
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = I1.main(["--out", str(I1.ART138I / "m1-on138j.json")])
    rep = json.loads((I1.ART138I / "m1-on138j.json").read_text(
        encoding="utf-8"))
    sealed = json.loads((ART138I / "m1-138i-pieces.json").read_text(
        encoding="utf-8"))
    # Join diffs: inherited (same id diffed on sealed 138i) vs new.
    joined: dict = {}
    for piece, block in rep.get("pieces", {}).items():
        mine = {(d.get("id", d.get("n"))) for d in block.get("diffs", [])}
        mine_got = {d.get("id", d.get("n")): d.get("got", d.get("reply"))
                    for d in block.get("diffs", [])}
        sblock = sealed.get("pieces", {}).get(piece, {})
        sdiffs = sblock.get("diffs", [])
        base = {(d.get("id", d.get("n"))) for d in sdiffs}
        base_got = {d.get("id", d.get("n")): d.get("got", d.get("reply"))
                    for d in sdiffs}
        inherited = sorted(mine & base)
        inherited_same = all(
            str(mine_got[i]) == str(base_got.get(i)) for i in inherited)
        new = sorted(mine - base)
        resolved = sorted(base - mine)
        joined[piece] = {
            "n": block.get("n"), "identical": block.get("identical"),
            "inherited": inherited, "inherited_same_got": inherited_same,
            "new_vs_138i": new, "resolved_vs_138i": resolved,
            "m1_rc": rc}
    return {"pieces": joined,
            "mro155": rep.get("mro155"),
            "seconds": rep.get("seconds")}


# ------------------------------------------------- M2-A: 138h M1 on 138j
def part_a() -> dict:
    import fable_fix138h_m1pieces as M1H  # noqa: E402 (driver, read-only)
    M1H.build138h = build138j_extra  # type: ignore[method-assign]
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


# --------------------------------------- M2-B: 138h M2 pieces on 138j
def m2_139e_138j() -> dict:
    import fable_fix139e_probe as P139E  # noqa: E402 (judge, read-only)
    import fable_loop139c_agent as L139C  # noqa: E402 (frozen base)
    cfg_c = copy.deepcopy(L139C.DEFAULT_CONFIG139C)
    build_j = lambda c: L138J.build_agent138j(  # noqa: E731
        dict(copy.deepcopy(L138J.DEFAULT_CONFIG138J), **c))
    build_c = lambda c: L139C.build_agent139c(  # noqa: E731
        dict(cfg_c, **c))
    cases = json.loads((ROOT / "artifacts" / "fable-tail139e-20260922"
                        / "cases139e.json").read_text(encoding="utf-8"))
    rows = [P139E.run_case(r, build_j, build_c) for r in cases]
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
    M2H.fresh138h = fresh138j  # type: ignore[method-assign]
    M2H.build138h = build138j_extra  # type: ignore[method-assign]
    out: dict = {"139e": m2_139e_138j(), "137e": M2H.m2_137e(),
                 "158c": M2H.m2_158c(), "168": M2H.m2_168()}
    out.update(M2H.m2_138f())
    sealed = json.loads((ART138I / "m2-138i.json").read_text(
        encoding="utf-8"))
    for piece in ("137e", "158c", "168", "142", "156b"):
        mine = out[piece]
        base = sealed["pieces"][f"B-{piece}"]
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
        mine["vs138i"] = {"fail_ids": mid, "base_fail_ids": bid,
                          "ids_equal": mid == bid, "got_equal": same_got}
    return out


# --------------------------------------- M2-G3: 138i director pairs
def m2_g3() -> dict:
    spec = json.loads((ART138I / "cases138i-g3.json").read_text(
        encoding="utf-8"))
    rows = []
    for case in spec["cases"]:
        loop = fresh138j()
        replies = [" ".join(loop.turn(t)) for t in case["turns"]]
        stored = sorted(triples(loop))
        want_r = [str(x) for x in case.get("replies", [])]
        want_s = sorted([list(x) for x in case.get("stored", [])])
        ok = (replies == want_r and stored == want_s)
        rows.append({"id": case["id"], "turns": case["turns"],
                     "replies138j": replies, "replies138i": want_r,
                     "stored138j": stored, "stored138i": want_s,
                     "identical": ok})
        print(f"M2-G3 {case['id']}: {'IDENTICAL' if ok else 'MOVED'}",
              flush=True)
        if not ok:
            print(f"  got  {replies} stored={stored}", flush=True)
            print(f"  want {want_r} stored={want_s}", flush=True)
    return {"suite": "g3-138i-pairs", "n": len(rows), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138j M2")
    ap.add_argument("--only", default="all")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    want = ["m1", "A", "B", "g3"] if args.only == "all" \
        else args.only.split(",")
    out: dict = {"agent": "loop138j", "seconds": 0.0, "pieces": {}}
    rc = 0
    if "m1" in want:
        t1 = time.time()
        rep = m2_m1()
        out["pieces"]["M1-on-138j"] = {**rep,
                                       "seconds": round(time.time() - t1, 1)}
        for piece, j in rep["pieces"].items():
            print(f"M2-M1 {piece}: identical={j['identical']}/{j['n']} "
                  f"inherited={j['inherited']} new={j['new_vs_138i']} "
                  f"resolved={j['resolved_vs_138i']} "
                  f"same_got={j['inherited_same_got']}", flush=True)
    if "A" in want:
        for piece, rep in part_a().items():
            out["pieces"][f"A-{piece}"] = rep
            status = "IDENTICAL" if not rep["diffs"] else "HAS-DIFFS"
            print(f"M2-A {piece}: {status} "
                  f"identical={rep['identical']}/{rep['n']}", flush=True)
            for d in rep["diffs"][:16]:
                print(f"  DIFF {d}", flush=True)
    if "B" in want:
        for piece, rep in part_b().items():
            out["pieces"][f"B-{piece}"] = rep
            status = "PASS" if rep.get("pass") else "FAIL"
            extra = {k: v for k, v in rep.items() if k != "pass"}
            print(f"M2-B {piece}: {status} "
                  f"{json.dumps(extra)[:300]}", flush=True)
            for f in rep.get("fails", [])[:12]:
                print(f"  FAILCASE {f}", flush=True)
    if "g3" in want:
        out["pieces"]["G3-138i"] = m2_g3()
    out["seconds"] = round(time.time() - t0, 1)
    dest = Path(args.out) if args.out else ART138J / "m2-138j.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
