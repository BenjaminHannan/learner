#!/usr/bin/env python3
"""Exp 138i M1 driver -- each ported piece's OWN sealed case file on loop138i.

For each of the 9 pieces, replays its sealed case file through a FRESH
in-process loop138i and compares per-case (verdict + reply, plus stored
where the piece's format has it) against the piece's sealed frozen rows
AND a live run of the piece's own agent. Diffs must be exactly the
cross-piece interaction classes listed in PASSMARKS.md (pilot first);
anything else FAILs the mark.

Also prints the 155-absence check (MRO has no 155 class; no
fable_loop155* module imported).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138i_m1pieces.py --out <path>
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


def fresh138i():
    d = tempfile.mkdtemp(prefix="m1-138i-")
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L138I.build_agent138i(cfg)


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

    def build(extra: dict | None = None):
        d = tempfile.mkdtemp(prefix="m1-base-")
        c = dict(cfg)
        c["state_dir"] = d
        c["sleep_threshold"] = 100000
        if extra:
            c.update(extra)
        return builder(c)

    return build


def triples(loop) -> list:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------- generic jsonl sequential-session runner (154e / 172b)
def _jsonl_pass(cases: list, build) -> dict:
    """One full pass: fresh loop per reset segment; reply per n."""
    import fable_fix154c_probe as P154C  # noqa: E402 (state reader, read-only)
    got: dict = {}
    loop = build()
    for case in cases:
        if case.get("reset"):
            loop = build()
            continue
        said = " ".join(loop.turn(case["turn"]))
        entry: dict = {"reply": said}
        if "state" in case or "full_state" in case:
            entry["state"] = P154C.notebook_state(loop)
        got[case["n"]] = entry
    return got


def run_jsonl(piece: str, cases_path: Path, build_own) -> dict:
    import fable_fix154c_probe as P154C  # noqa: E402 (state reader, read-only)
    del P154C  # reader used inside _jsonl_pass
    cases = load_jsonl(cases_path)

    def build138i_seg():
        return fresh138i()

    got = _jsonl_pass(cases, build138i_seg)
    own = _jsonl_pass(cases, build_own)
    rows, diffs = [], []
    for case in cases:
        if case.get("reset"):
            rows.append({"reset": True})
            continue
        n = case["n"]
        said = got[n]["reply"]
        said_own = own[n]["reply"]
        ok_reply = (said == case.get("expect", said))
        ok_live = (said == said_own)
        state_ok = True
        if "state" in case:
            for pair, want in case["state"].items():
                if got[n].get("state", {}).get(pair, []) != list(want):
                    state_ok = False
        full_ok = None
        if "full_state" in case:
            full_ok = (got[n].get("state") == case["full_state"])
        ok = bool(ok_reply and ok_live and state_ok
                  and (full_ok is not False))
        rows.append({"n": n, "turn": case.get("turn"),
                     "reply": said, "expect": case.get("expect"),
                     "own_reply": said_own, "pass": ok})
        if not ok:
            diffs.append({"n": n, "turn": case.get("turn"),
                          "got": said[:160],
                          "want": str(case.get("expect"))[:160],
                          "own": said_own[:160], "state_ok": state_ok,
                          "full_ok": full_ok})
    n = sum(1 for r in rows if "turn" in r)
    ok = sum(1 for r in rows if r.get("pass"))
    return {"piece": piece, "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 167e: one sequential session, exact frozen replies
def run_167e() -> dict:
    frozen = load_json(ROOT / "artifacts" / "fable-label167e-20260922"
                       / "probe167e-loop167e.json")["cases"]
    suite = load_json(ROOT / "artifacts" / "fable-label167e-20260922"
                      / "cases167e.json")
    build_own = mkbase("fable_loop167e_agent")
    loop, own = fresh138i(), build_own()
    rows, diffs = [], []
    for frow, trow in zip(frozen, suite["turns"]):
        turn = trow["t"]
        said = " ".join(loop.turn(turn))
        said_own = " ".join(own.turn(turn))
        ok = (said == frow["reply"] and said == said_own)
        rows.append({"n": frow["n"], "turn": turn, "reply": said,
                     "frozen": frow["reply"], "own": said_own,
                     "pass": ok})
        if not ok:
            diffs.append({"n": frow["n"], "turn": turn,
                          "got": said[:160], "want": frow["reply"][:160],
                          "own": said_own[:160]})
    stored138i = triples(loop)
    stored_own = triples(own)
    return {"piece": "167e", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "stored_equal": stored138i == stored_own,
            "stored138i": stored138i, "stored_own": stored_own,
            "rows": rows}


# ---------------- 167d: piece's own judge
def run_167d() -> dict:
    import fable_fix167d_probe as P167D  # noqa: E402 (judge, read-only)
    frozen = load_json(ROOT / "artifacts" / "fable-verb167d-20260922"
                       / "probe167d-loop167d.json")["cases"]
    cases = load_json(ROOT / "artifacts" / "fable-verb167d-20260922"
                      / "cases167d.json")
    f_by_id = {r["id"]: r for r in frozen}
    build_own = mkbase("fable_loop167d_agent")

    def build138i_extra(extra: dict):
        cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
        cfg.update(extra)
        return L138I.build_agent138i(cfg)

    rows, diffs = [], []
    for row in cases:
        try:
            got = P167D.run_case(row, build138i_extra, build_own)
        except Exception as exc:  # noqa: BLE001
            got = {"id": row["id"], "verdict": "HARNESS-ERROR",
                   "reply": repr(exc)[:160]}
        f = f_by_id.get(row["id"], {})
        same = (got.get("verdict") == f.get("verdict")
                and got.get("reply") == f.get("reply")
                and got.get("stored") == f.get("stored"))
        rows.append({"id": row["id"], "verdict": got.get("verdict"),
                     "frozen": f.get("verdict"),
                     "reply": str(got.get("reply"))[:160],
                     "pass": bool(same)})
        if not same:
            diffs.append({"id": row["id"], "verdict": got.get("verdict"),
                          "frozen": f.get("verdict"),
                          "got": str(got.get("reply"))[:160],
                          "want": str(f.get("reply"))[:160]})
    return {"piece": "167d", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "rows": rows}


# ---------------- 173b: sealed judge (t1 cases166 + t1c cases173b)
def run_173b() -> dict:
    import fable_fix173b_probe as P173B  # noqa: E402 (judge, read-only)
    cases_t1 = load_json(ROOT / "artifacts" / "fable-me166-20260922"
                         / "cases166.json")
    cases_t1c = load_json(ROOT / "artifacts" / "fable-username173b-20260922"
                          / "cases173b.json")
    build_173 = mkbase("fable_loop173_agent")
    build_173b = mkbase("fable_loop173b_agent")

    def build138i_extra(extra: dict):
        cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
        cfg.update(extra)
        return L138I.build_agent138i(cfg)

    rows, diffs = [], []
    for row in cases_t1:
        try:
            got = P173B.check_166_row(row, build138i_extra, build_173)
        except Exception as exc:  # noqa: BLE001
            got = {"id": row["id"], "verdict": "HARNESS-ERROR",
                   "reply": repr(exc)[:160]}
        ok = got.get("verdict") == "OK"
        rows.append({"id": "t1-" + row["id"],
                     "verdict": got.get("verdict"), "pass": ok,
                     "reply": str(got.get("replies",
                                          got.get("reply", "")))[:160]})
        if not ok:
            diffs.append({"id": "t1-" + row["id"],
                          "verdict": got.get("verdict"),
                          "replies": str(got.get("replies"))[:200],
                          "base": str(got.get("base_replies"))[:200]})
    for row in cases_t1c:
        try:
            got = P173B.check_173b_row(row, build138i_extra, build_173b)
        except Exception as exc:  # noqa: BLE001
            got = {"id": row["id"], "verdict": "HARNESS-ERROR",
                   "reply": repr(exc)[:160]}
        ok = got.get("verdict") == "OK"
        rows.append({"id": "t1c-" + row["id"],
                     "verdict": got.get("verdict"), "pass": ok,
                     "replies": str(got.get("replies"))[:160]})
        if not ok:
            diffs.append({"id": "t1c-" + row["id"],
                          "verdict": got.get("verdict"),
                          "replies": str(got.get("replies"))[:200],
                          "base": str(got.get("base_replies"))[:200],
                          "stored": got.get("stored"),
                          "base_stored": got.get("base_stored")})
    return {"piece": "173b", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "rows": rows}


# ---------------- 171b (+171 T1): sealed semantics on loop138i + live + frozen
def run_171b() -> dict:
    import fable_fix171_nameval as N171  # noqa: E402 (rule, read-only)
    import fable_fix171b_nameval as N171B  # noqa: E402 (rule, read-only)
    frozen_b = {r["id"]: r for r in load_json(
        ROOT / "artifacts" / "fable-nameval171b-20260922"
        / "probe171b.json")["rows"]}
    cases_b = load_json(ROOT / "artifacts" / "fable-nameval171b-20260922"
                        / "cases171b.json")
    frozen_t1 = {r["id"]: r for r in load_json(
        ROOT / "artifacts" / "fable-nameval171b-20260922"
        / "probe171b_T1.json")["rows"]}
    cases_t1 = load_json(ROOT / "artifacts" / "fable-nameval171-20260922"
                         / "cases171.json")
    build_own = mkbase("fable_loop171b_agent")
    rows, diffs = [], []

    def facts(loop) -> list:
        return sorted(v for _, _, v in triples(loop))

    for case in cases_b:
        cid, kind = case["id"], case["kind"]
        f = frozen_b.get(cid, {})
        loop, own = fresh138i(), build_own()
        if kind == "save":
            r1 = loop.turn(case["teach"])
            ok_save = (facts(loop) == [case["value"]]
                       and loop.counters["writes"] == 1)
            ask = loop.turn(case["followup"])
            ok_ask = (case["value"] in " ".join(ask)
                      and facts(loop) == [case["value"]])
            o1 = own.turn(case["teach"])
            oask = own.turn(case["followup"])
            ok = (ok_save and ok_ask and r1 == o1 and ask == oask
                  and r1 == f.get("reply", r1)
                  and ask == f.get("ask", ask)
                  and facts(loop) == f.get("facts", facts(loop)))
            detail = {"reply": r1, "ask": ask, "facts": facts(loop)}
        elif kind == "save-after-clarify":
            ev0 = len(loop.nb.events)
            r1 = loop.turn(case["teach1"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_c = (r1 == [exp] and len(loop.nb.events) == ev0
                    and loop.counters["writes"] == 0)
            r2 = loop.turn(case["teach2"])
            ok_s = (facts(loop) == [case["value"]]
                    and loop.counters["writes"] == 1)
            ask = loop.turn(case["followup"])
            ok_a = (case["value"] in " ".join(ask)
                    and facts(loop) == [case["value"]])
            o1 = own.turn(case["teach1"])
            o2 = own.turn(case["teach2"])
            oask = own.turn(case["followup"])
            ok = (ok_c and ok_s and ok_a and r1 == o1 and r2 == o2
                  and ask == oask)
            detail = {"r1": r1, "r2": r2, "ask": ask,
                      "facts": facts(loop)}
        elif kind == "clarify":
            ev0 = len(loop.nb.events)
            r1 = loop.turn(case["teach"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_reply = (r1 == [exp])
            ok_write = (len(loop.nb.events) == ev0
                        and loop.counters["writes"] == 0)
            ask = loop.turn(case["followup"])
            ok_find = ("don't know" in " ".join(ask).lower()
                       and len(loop.nb.events) == ev0
                       and triples(loop) == [])
            o1 = own.turn(case["teach"])
            oask = own.turn(case["followup"])
            ok = (ok_reply and ok_write and ok_find and r1 == o1
                  and ask == oask and r1 == f.get("reply", r1)
                  and ask == f.get("ask_reply", ask))
            detail = {"reply": r1, "ask_reply": ask}
        elif kind == "identical":
            gotI, gotO, ok = [], [], True
            for t in case["turns"]:
                rI, rO = loop.turn(t), own.turn(t)
                gotI.append(rI)
                gotO.append(rO)
                if rI != rO:
                    ok = False
            if triples(loop) != triples(own):
                ok = False
            if sorted(case.get("values", [])) != facts(loop):
                ok = False
            detail = {"got138i": gotI, "gotOwn": gotO,
                      "triples": triples(loop)}
        else:
            ok, detail = False, {"note": "unknown kind"}
        rows.append({"id": cid, "pass": bool(ok), **{
            k: ([str(x)[:160] for x in v] if isinstance(v, list) else v)
            for k, v in detail.items()}})
        if not ok:
            diffs.append({"id": cid, "kind": kind, **{
                k: ([str(x)[:160] for x in v]
                    if isinstance(v, list) else v)
                for k, v in detail.items()}})
    for case in cases_t1:
        cid, kind = case["id"], case["kind"]
        f = frozen_t1.get(cid, {})
        loop, own = fresh138i(), build_own()
        if kind == "clarify":
            ev0 = len(loop.nb.events)
            r1 = loop.turn(case["teach"])
            exp = N171.clarify_for(case["name"], case["relation"])
            ok_reply = (r1 == [exp])
            ok_write = (len(loop.nb.events) == ev0
                        and loop.counters["writes"] == 0)
            ask = loop.turn(case["followup"])
            ok_find = ("don't know" in " ".join(ask).lower()
                       and len(loop.nb.events) == ev0
                       and triples(loop) == [])
            o1 = own.turn(case["teach"])
            oask = own.turn(case["followup"])
            ok_sealed = (f.get("reply") == r1
                         and f.get("ask_reply") == ask)
            ok = ok_reply and ok_write and ok_find and r1 == o1 and ok_sealed
            detail = {"reply": r1, "ask_reply": ask}
        elif kind == "identical":
            gotI, gotO, ok = [], [], True
            for t in case["turns"]:
                rI, rO = loop.turn(t), own.turn(t)
                gotI.append(rI)
                gotO.append(rO)
                if rI != rO:
                    ok = False
            if triples(loop) != triples(own):
                ok = False
            s = f
            ok_sealed = (s.get("gotB") == gotI
                         and s.get("triplesB") == triples(loop))
            ok = ok and ok_sealed
            detail = {"got138i": gotI, "gotOwn": gotO,
                      "triples": triples(loop)}
        else:
            ok, detail = False, {"note": "unknown kind"}
        rows.append({"id": "T1-" + cid, "pass": bool(ok), **{
            k: ([str(x)[:160] for x in v] if isinstance(v, list) else v)
            for k, v in detail.items()}})
        if not ok:
            diffs.append({"id": "T1-" + cid, "kind": kind, **{
                k: ([str(x)[:160] for x in v]
                    if isinstance(v, list) else v)
                for k, v in detail.items()}})
    return {"piece": "171b+171", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "rows": rows}


# ---------------- 154d: one sequential session, frozen exact replies
def run_154d() -> dict:
    frozen = load_json(ROOT / "artifacts" / "fable-yesno154d-20260922"
                       / "probe154d-loop154d.json")["rows"]
    cases = load_json(ROOT / "artifacts" / "fable-yesno154d-20260922"
                      / "cases154d.json")["cases"]
    build_own = mkbase("fable_loop154d_agent")
    loop, own = fresh138i(), build_own()
    rows, diffs = [], []
    for frow, crow in zip(frozen, cases):
        turn = crow["turn"]
        said = " ".join(loop.turn(turn))
        said_own = " ".join(own.turn(turn))
        ok = (said == frow["reply"] and said == said_own)
        rows.append({"n": crow["n"], "turn": turn, "reply": said,
                     "frozen": frow["reply"], "own": said_own,
                     "pass": ok})
        if not ok:
            diffs.append({"n": crow["n"], "turn": turn, "got": said[:160],
                          "want": frow["reply"][:160],
                          "own": said_own[:160]})
    return {"piece": "154d", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "rows": rows}


# ---------------- 174: one sequential session, frozen exact replies
def run_174() -> dict:
    frozen = load_json(ROOT / "artifacts" / "fable-chainof174-20260922"
                       / "t1-174.json")
    cases = load_json(ROOT / "artifacts" / "fable-chainof174-20260922"
                      / "cases174.json")["cases"]
    build_own = mkbase("fable_loop174_agent")
    loop, own = fresh138i(), build_own()
    f_by_n = {r["n"]: r for r in frozen}
    rows, diffs = [], []
    for crow in cases:
        turn = crow["text"]
        said = " ".join(loop.turn(turn))
        said_own = " ".join(own.turn(turn))
        f = f_by_n.get(crow["n"], {})
        ok = (said == f.get("reply", said) and said == said_own)
        rows.append({"n": crow["n"], "turn": turn, "reply": said,
                     "frozen": f.get("reply"), "own": said_own,
                     "pass": ok})
        if not ok:
            diffs.append({"n": crow["n"], "turn": turn, "got": said[:160],
                          "want": str(f.get("reply"))[:160],
                          "own": said_own[:160]})
    return {"piece": "174", "n": len(rows),
            "identical": sum(1 for r in rows if r["pass"]), "diffs": diffs,
            "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138i M1 pieces")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    t0 = time.time()
    out: dict = {"agent": "loop138i", "seconds": 0.0, "pieces": {}}
    want = args.only.split(",")
    jobs = {
        "154e": lambda: run_jsonl(
            "154e", ROOT / "artifacts" / "fable-lang154e-20260922"
            / "case154e.jsonl", mkbase("fable_loop154e_agent")),
        "172b-t1": lambda: run_jsonl(
            "172b-t1", ROOT / "artifacts" / "fable-copula172b-20260922"
            / "probe172b_t1_cases.jsonl", mkbase("fable_loop172_agent")),
        "172b-t1b": lambda: run_jsonl(
            "172b-t1b", ROOT / "artifacts" / "fable-copula172b-20260922"
            / "probe172b_t1b_cases.jsonl", mkbase("fable_loop172_agent")),
        "172b-t1c": lambda: run_jsonl(
            "172b-t1c", ROOT / "artifacts" / "fable-copula172b-20260922"
            / "probe172b_t1c_cases.jsonl", mkbase("fable_loop172_agent")),
        "171b": run_171b,
        "173b": run_173b,
        "167e": run_167e,
        "167d": run_167d,
        "154d": run_154d,
        "174": run_174,
    }
    rc = 0
    for name, fn in jobs.items():
        if want != ["all"] and name not in want:
            continue
        rep = fn()
        out["pieces"][name] = rep
        status = "IDENTICAL" if not rep["diffs"] else "HAS-DIFFS"
        print(f"M1 {name}: {status} "
              f"identical={rep['identical']}/{rep['n']}", flush=True)
        for d in rep["diffs"][:20]:
            print(f"  DIFF {d}", flush=True)
        for k in ("stored_equal",):
            if k in rep and not rep[k]:
                print(f"  DIFF stored: 138i={rep.get('stored138i')} "
                      f"own={rep.get('stored_own')}", flush=True)
                rc = 1
        if rep["diffs"]:
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    out["mro155"] = {
        "ears_mro": [c.__name__ for c in L138I.Loop138iEars.__mro__],
        "has155class": any("155" in c.__name__
                           for c in L138I.Loop138iEars.__mro__),
        "fable_loop155_modules": [m for m in sys.modules
                                  if "fable_loop155" in m],
    }
    print(f"155-check: has155={out['mro155']['has155class']} "
          f"mods={out['mro155']['fable_loop155_modules']}", flush=True)
    dest = Path(args.out) if args.out else ART138I / "m1-138i-pieces.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
