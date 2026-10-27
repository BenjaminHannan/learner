#!/usr/bin/env python3
"""Exp 138h M1 driver -- each ported piece's OWN sealed probe on loop138h.

For each of the 5 pieces, runs its sealed case file through a FRESH
in-process loop138h using the piece's OWN probe judge (imported
read-only), with the piece's own base as the live base arm, and compares
per-case (verdict + reply + stored + asks) against the piece's sealed
frozen rows. Diffs must be exactly the interaction cases listed in
PASSMARKS.md (with expected replies); anything else FAILs the mark.

Also prints the 155-absence check (MRO has no 155 class; no
fable_loop155* module imported).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138h_m1pieces.py --out <path>
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138h_agent as L138H  # noqa: E402 (agent under test)

import fable_loop138g_agent as L138G  # noqa: E402 (138g base, read-only)

ROOT = SCRIPTS.parent
ART138H = ROOT / "artifacts" / "fable-agent138h-20260922"


def build138h(extra: dict) -> object:
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg.update(extra)
    return L138H.build_agent138h(cfg)


def build138g(extra: dict) -> object:
    cfg = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
    cfg.update(extra)
    return L138G.build_agent138g(cfg)


def mkbase(modname: str):
    mod = __import__(modname)
    cfg = None
    builder = None
    for attr in dir(mod):
        if attr.startswith("DEFAULT_CONFIG"):
            cfg = copy.deepcopy(getattr(mod, attr))
        if attr.startswith("build_agent"):
            builder = getattr(mod, attr)
    assert cfg is not None and builder is not None, modname

    def build(c):
        return builder(dict(cfg, **c))

    return build


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compare_frozen(got: dict, frozen: dict) -> list[str]:
    """Field diffs vs the piece's own frozen row (reply/stored/asks)."""
    diffs = []
    for key in ("reply", "replies", "stored", "asks"):
        if key in frozen:
            g, f = got.get(key), frozen.get(key)
            if key == "asks" and isinstance(g, list) and isinstance(f, list):
                g = [a.get("reply") if isinstance(a, dict) else a
                     for a in g]
                f = [a.get("reply") if isinstance(a, dict) else a
                     for a in f]
            if g != f:
                diffs.append(key)
    return diffs


def asks_replies(asks) -> list:
    out = []
    for a in asks or []:
        out.append(a.get("reply") if isinstance(a, dict) else a)
    return out


def run_simple(piece: str, cases_path: Path, frozen: dict,
               run_case, build_own, drive_fn, steps_key: str | None = None) -> dict:
    cases = load_json(cases_path)
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    f_by_id = frozen if isinstance(frozen, dict) else {
        r["id"]: r for r in frozen}
    rows, diffs = [], []
    for row in cases:
        t0 = time.time()
        try:
            got = run_case(row, build138h, build_own)
        except Exception as exc:  # noqa: BLE001
            got = {"id": row["id"], "verdict": "HARNESS-ERROR",
                   "reply": repr(exc)[:160]}
        f = f_by_id.get(row["id"], {})
        verdict_same = got.get("verdict") == f.get("verdict")
        field_diffs = compare_frozen(got, f) if f else ["no-frozen-row"]
        # 138g-identity check for diffs: same drive on loop138g.
        g138_same = None
        if not verdict_same or field_diffs:
            try:
                if steps_key:
                    g_rep, g_stored, _ = drive_fn(
                        row.get(steps_key, []), build138g)
                    h_rep, h_stored = got.get("replies"), got.get("stored")
                    g138_same = (g_rep == h_rep and g_stored == h_stored)
                else:
                    drv = drive_fn(row, build138g)
                    if len(drv) == 4:
                        g_rep, g_stored, _, g_asks = drv
                        h_rep = got.get("replies")
                    else:
                        g_rep, g_stored, g_asks = drv[0], drv[1], drv[2]
                        h_rep = got.get("reply")
                        if h_rep is None:
                            h_rep = got.get("replies")
                    g138_same = (g_rep == h_rep and g_stored == got.get("stored")
                                 and asks_replies(g_asks) == asks_replies(got.get("asks")))
            except Exception as exc:  # noqa: BLE001
                g138_same = f"HARNESS {exc!r}"[:120]
        rows.append({"id": row["id"], "verdict": got.get("verdict"),
                     "frozen_verdict": f.get("verdict"),
                     "field_diffs": field_diffs, "g138_same": g138_same,
                     "reply": str(got.get("reply", got.get("replies", "")))[:160]})
        if not verdict_same or field_diffs:
            diffs.append({"id": row["id"],
                          "verdict": got.get("verdict"),
                          "frozen": f.get("verdict"),
                          "fields": field_diffs, "g138_same": g138_same,
                          "reply": str(got.get("reply", got.get("replies", "")))[:160],
                          "frozen_reply": str(f.get("reply", f.get("replies", "")))[:160]})
    ok = sum(1 for r in rows if r["verdict"] == r["frozen_verdict"]
             and not r["field_diffs"])
    return {"piece": piece, "n": len(rows), "identical": ok,
            "diffs": diffs, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138h M1 pieces")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    out: dict = {"agent": "loop138h", "seconds": 0.0, "pieces": {}}

    import fable_fix162b_probe as P162B  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-plural162b-20260922"
                       / "probe162b-loop162b.json")["cases"]
    out["pieces"]["162b"] = run_simple(
        "162b", ROOT / "artifacts" / "fable-plural162b-20260922"
        / "cases162b.json", {r["id"]: r for r in frozen},
        P162B.run_case, mkbase("fable_loop162b_agent"), P162B.drive)

    import fable_fix165_probe as P165  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-typo165-20260922"
                       / "probe165-loop165.json")["cases"]
    out["pieces"]["165"] = run_simple(
        "165", ROOT / "artifacts" / "fable-typo165-20260922"
        / "cases165.json", {r["id"]: r for r in frozen},
        P165.run_case, mkbase("fable_loop165_agent"), P165.drive)

    import fable_fix166c_probe as P166C  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-me166c-20260922"
                       / "probe166c-loop166c.json")["cases"]
    fmap = {r["id"]: {"verdict": r["verdict"], "replies": r["replies"],
                      "stored": r["stored"],
                      "asks": r["asks"]} for r in frozen}
    out["pieces"]["166c"] = run_simple(
        "166c", ROOT / "artifacts" / "fable-me166-20260922"
        / "cases166.json", fmap,
        P166C.run_case, mkbase("fable_loop166c_agent"), P166C.drive)

    import fable_fix166c_probeB as P166B  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-me166c-20260922"
                       / "probe166c-B.json")
    frozen = frozen["cases"] if isinstance(frozen, dict) else frozen
    out["pieces"]["166c-B"] = run_simple(
        "166c-B", ROOT / "artifacts" / "fable-me166b-20260922"
        / "cases166b.json", {r["id"]: r for r in frozen},
        P166B.run_case, mkbase("fable_loop166_agent"), P166B.drive)

    import fable_fix166c_probeC as P166CC  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-me166c-20260922"
                       / "probe166c-C.json")
    frozen = frozen["cases"] if isinstance(frozen, dict) else frozen
    out["pieces"]["166c-C"] = run_simple(
        "166c-C", ROOT / "artifacts" / "fable-me166c-20260922"
        / "cases166c.json", {r["id"]: r for r in frozen},
        P166CC.run_case, mkbase("fable_loop166_agent"), P166CC.drive)

    import fable_fix173_probe as P173  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-username173-20260922"
                       / "probe173-t1.json")["cases"]
    out["pieces"]["173-t1"] = run_simple(
        "173-t1", ROOT / "artifacts" / "fable-me166-20260922"
        / "cases166.json", {r["id"]: {"verdict": r["verdict"]}
                            for r in frozen},
        P173.check_166_row, mkbase("fable_loop173_agent"), P173.drive_steps,
        steps_key="teaches")
    frozen = load_json(ROOT / "artifacts" / "fable-username173-20260922"
                       / "probe173-t1b.json")["cases"]
    out["pieces"]["173-t1b"] = run_simple(
        "173-t1b", ROOT / "artifacts" / "fable-username173-20260922"
        / "cases173.json", {r["id"]: {"verdict": r["verdict"]}
                            for r in frozen},
        P173.check_173_row, mkbase("fable_loop173_agent"), P173.drive_steps,
        steps_key="steps")

    import fable_fix167b_probe as P167B  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-verb167b-20260922"
                       / "probe167b-loop167b.json")["cases"]
    out["pieces"]["167b"] = run_simple(
        "167b", ROOT / "artifacts" / "fable-verb167b-20260922"
        / "cases167b.json", {r["id"]: r for r in frozen},
        P167B.run_case, mkbase("fable_loop167b_agent"), P167B.drive)

    out["seconds"] = round(time.time() - t0, 1)
    out["mro155"] = {
        "ears_mro": [c.__name__ for c in L138H.Loop138hEars.__mro__],
        "has155class": any("155" in c.__name__
                           for c in L138H.Loop138hEars.__mro__),
        "fable_loop155_modules": [m for m in sys.modules
                                  if "fable_loop155" in m],
    }
    rc = 0
    for piece, rep in out["pieces"].items():
        status = "IDENTICAL" if not rep["diffs"] else "HAS-DIFFS"
        print(f"M1 {piece}: {status} identical={rep['identical']}/{rep['n']}",
              flush=True)
        for d in rep["diffs"][:20]:
            print(f"  DIFF {d}", flush=True)
        if rep["diffs"]:
            rc = 1
    print(f"155-check: {out['mro155']}", flush=True)
    dest = Path(args.out) if args.out else ART138H / "m1-138h-pieces.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
