#!/usr/bin/env python3
"""Exp 138j M1 driver -- each ported piece's OWN sealed case file on loop138j.

For each of the 10 pieces (+189b/190b separately = 12 runners), replays
its sealed case file through a FRESH in-process loop138j in lockstep
with the piece's OWN agent (same session structure the piece's own
probe uses). Per-case verdict + reply + stored facts must be identical
to the piece's own agent, except the cross-piece interaction classes
listed in PASSMARKS.md (pilot first); anything else FAILs the mark.

Also prints the 155-absence check (MRO has no 155 class; no
fable_loop155* module imported).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138j_m1pieces.py --out <path> [--only <csv>]
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

import fable_loop138j_agent as L138J  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART138J = ROOT / "artifacts" / "fable-agent138j-20260922"


def fresh138j():
    d = tempfile.mkdtemp(prefix="m1-138j-")
    cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L138J.build_agent138j(cfg)


def mkbase(modname: str):
    mod = __import__(modname)
    cfg = next(copy.deepcopy(getattr(mod, a)) for a in dir(mod)
               if a.startswith("DEFAULT_CONFIG"))
    builder = next(getattr(mod, a) for a in dir(mod)
                   if a.startswith("build_agent"))

    def build():
        d = tempfile.mkdtemp(prefix="m1-base-")
        c = dict(cfg)
        c["state_dir"] = d
        c["sleep_threshold"] = 100000
        return builder(c)

    return build


def triples(loop) -> list:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def turn(loop, text: str) -> str:
    return " ".join(loop.turn(text))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------- 180b / 193: cap/ask/teach/trap single session
def run_capask(piece: str, cases_path: Path, build_own,
               dupes_fn=None) -> dict:
    steps = load_json(cases_path)
    new, own = fresh138j(), build_own()
    rows, diffs = [], []
    for s in steps:
        kind = s["kind"]
        rec = {"id": s.get("id"), "kind": kind, "turn": s["turn"]}
        if kind == "cap":
            rn, ro = turn(new, s["turn"]), turn(own, s["turn"])
            ok = (rn == ro and triples(new) == triples(own))
            rec.update(reply138j=rn, reply_own=ro)
        elif kind == "ask":
            b_new, b_own = triples(new), triples(own)
            rn, ro = turn(new, s["turn"]), turn(own, s["twin"])
            ok = (rn == ro and triples(new) == b_new
                  and triples(own) == b_own)
            rec.update(reply138j=rn, reply_own=ro)
        elif kind == "teach":
            rn = turn(new, s["turn"])
            ro = turn(own, s["twin"])
            ok = (rn == ro and triples(new) == triples(own))
            rec.update(reply138j=rn, reply_own=ro)
            if dupes_fn is not None:
                dupes = dupes_fn(new)
                ok = ok and not dupes
                rec["dupes"] = dupes
        elif kind == "trap":
            rn, ro = turn(new, s["turn"]), turn(own, s["turn"])
            if "expect" in s:
                ok = (rn == s["expect"]
                      and triples(new) == triples(own))
            else:
                ok = (rn == ro and triples(new) == triples(own))
            rec.update(reply138j=rn, reply_own=ro)
            if dupes_fn is not None:
                dupes = dupes_fn(new)
                ok = ok and not dupes
                rec["dupes"] = dupes
        else:
            rec["verdict"] = "BAD-KIND"
            rows.append(rec)
            diffs.append(rec)
            continue
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:160] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": piece, "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 164b: A/B/C must-rows + D near-rows
def run_164b() -> dict:
    import fable_fix164b_probe as P  # noqa: E402 (dialogue runner)
    cases = load_json(
        ROOT / "artifacts" / "fable-about164b-20260922" / "cases164b.json")
    build_own = mkbase("fable_loop164b_agent")
    rows, diffs = [], []
    for grp in ("A", "B", "C"):
        for row in cases[grp]:
            got = P.run_dialogue(fresh138j(), row["turns"])
            checks = [(row["ask_idx"], row["expect_reply"])]
            if "expect_reply2" in row:
                checks.append((2, row["expect_reply2"]))
            ok_r = all(got["replies"][i] == e for i, e in checks)
            ok_w = all(got["fact_deltas"][i] == 0 for i, _ in checks)
            ok_t = got["triples"] == sorted(row["expect_triples"])
            ok = ok_r and ok_w and ok_t
            rec = {"id": row["id"], "group": grp, "replies": got["replies"],
                   "expect": row["expect_reply"], "verdict":
                   "OK" if ok else "FAIL"}
            rows.append(rec)
            if not ok:
                diffs.append({**rec, "triples": got["triples"],
                              "expect_triples": row["expect_triples"]})
    for row in cases["D"]:
        got = P.run_dialogue(fresh138j(), row["turns"])
        base = P.run_dialogue(build_own(), row["turns"])
        ok = (got["replies"] == base["replies"]
              and got["fact_writes"] == base["fact_writes"])
        rec = {"id": row["id"], "group": "D", "replies138j": got["replies"],
               "replies_own": base["replies"],
               "verdict": "OK" if ok else "FAIL"}
        rows.append(rec)
        if not ok:
            diffs.append(rec)
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "164b", "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 189 / 189b: R1 lockstep
def run_189(piece: str, cases_path: Path, modname: str) -> dict:
    mod = __import__(modname)
    build_own = mkbase(modname)
    cases = load_json(cases_path)
    new, own = fresh138j(), build_own()
    tb_new, tb_own = triples(new), triples(own)
    rows, diffs = [], []
    prev_nonrepeat = None
    for row in cases:
        t, kind = row["turn"], row["kind"]
        rn = turn(new, t).strip()
        ro = turn(own, t).strip()
        ta_new, ta_own = triples(new), triples(own)
        rec = {"id": row["id"], "kind": kind, "turn": t,
               "reply138j": rn, "reply_own": ro}
        if kind == "noprev":
            ok = (rn == mod.NO_PREV189B if piece == "189b"
                  else mod.NO_PREV189) and ta_new == tb_new
            ok = ok and rn == ro
        elif kind == "repeat":
            want = prev_nonrepeat if prev_nonrepeat is not None else (
                mod.NO_PREV189B if piece == "189b" else mod.NO_PREV189)
            ok = (rn == want and ta_new == tb_new) and rn == ro
        else:
            ok = (rn == ro and ta_new == ta_own)
        tb_new, tb_own = ta_new, ta_own
        if kind not in ("noprev", "repeat"):
            prev_nonrepeat = ro
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:160] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": piece, "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 190: v1 lockstep
ASK190 = ("single", "multi", "corrected", "nomatch", "unknown")


def run_190() -> dict:
    case = load_json(
        ROOT / "artifacts" / "fable-reverse190-20260922" / "case190.json")
    build_own = mkbase("fable_loop190_agent")
    new, own = fresh138j(), build_own()
    rows, diffs = [], []
    for step in case["turns"]:
        before = triples(new)
        rn = turn(new, step["turn"]).strip()
        ro = turn(own, step["turn"]).strip()
        after, after_own = triples(new), triples(own)
        kind = step["kind"]
        rec = {"id": step["id"], "kind": kind, "turn": step["turn"],
               "reply138j": rn, "reply_own": ro}
        if kind in ASK190:
            ok = (rn == ro) and (after == before)
            rec["expect"] = step["expect"]
            rec["match_expect"] = (rn == step["expect"])
        else:
            ok = (rn == ro) and (after == after_own)
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:160] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "190", "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 190b: v1b lockstep
def run_190b() -> dict:
    case = load_json(
        ROOT / "artifacts" / "fable-reverse190b-20260922" / "case190b.json")
    build_own = mkbase("fable_loop190b_agent")
    new, own = fresh138j(), build_own()
    rows, diffs = [], []
    for step in case["turns"]:
        kind = step["kind"]
        before = triples(new)
        rn = turn(new, step["turn"]).strip()
        ro = turn(own, step["turn"]).strip()
        after, after_own = triples(new), triples(own)
        rec = {"id": step["id"], "kind": kind, "turn": step["turn"],
               "reply138j": rn, "reply_own": ro}
        if kind in ("r1", "r1-corrected"):
            ok = (rn == ro) and (after == before) and (after == after_own)
            rec["expect"] = step["expect"]
            rec["match_expect"] = (rn == step["expect"])
        elif kind == "teach-check":
            ok = (rn == ro and after == before and after == after_own)
            rec["expect"] = step["expect"]
            rec["match_expect"] = (rn == step["expect"])
        else:
            ok = (rn == ro) and (after == after_own)
            if kind not in ("teach", "correct"):
                ok = ok and (after == before)
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:160] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "190b", "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 187b: S1 lockstep
def run_187b() -> dict:
    import fable_loop187_agent as L187  # noqa: E402 (want replies)
    import fable_loop138g_agent as L138G  # noqa: E402 (cando lineage)
    steps = load_json(
        ROOT / "artifacts" / "fable-selfq187b-20260922" / "case187b.json")
    build_own = mkbase("fable_loop187_agent")
    new, own = fresh138j(), build_own()
    canon_cando = turn(L138G.build_agent138g(
        {"state_dir": tempfile.mkdtemp(prefix="m1-cando-"),
         "sleep_threshold": 100000}), "What can you do?")
    want = {"maker": L187.MAKER187, "identity": L187.IDENTITY187,
            "name": L187.NAME187, "cando": canon_cando}
    rows, diffs = [], []
    for s in steps:
        kind = s["kind"]
        rec = {"id": s.get("id"), "kind": kind, "turn": s["turn"]}
        if kind == "setup":
            rn, ro = turn(new, s["turn"]), turn(own, s["turn"])
            ok = rn == ro
            rec.update(reply138j=rn, reply_own=ro)
        elif kind == "self":
            rn = turn(new, s["turn"])
            ro = turn(own, s["turn"])
            exp = want[s["self187"]]
            ok = (rn == exp and ro == exp)
            rec.update(reply138j=rn, reply_own=ro, expect=exp)
        elif kind in ("trap", "stmt"):
            b_new, b_own = triples(new), triples(own)
            rn, ro = turn(new, s["turn"]), turn(own, s["turn"])
            ok = (rn == ro and triples(new) == b_new
                  and triples(own) == b_own
                  and triples(new) == triples(own))
            rec.update(reply138j=rn, reply_own=ro)
        else:
            rec["verdict"] = "BAD-KIND"
            rows.append(rec)
            diffs.append(rec)
            continue
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:200] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "187b", "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 192: drive + template check
def run_192() -> dict:
    import fable_fix192_probe as P192  # noqa: E402 (drive, read-only)
    spec = load_json(
        ROOT / "artifacts" / "fable-correctreply192-20260922"
        / "cases192.json")
    turns = [t["t"] for t in spec["turns"]]
    cfg0 = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    build_new = lambda c: L138J.build_agent138j(dict(cfg0, **c))  # noqa: E731
    mod192 = __import__("fable_loop192_agent")
    cfg192 = next(copy.deepcopy(getattr(mod192, a)) for a in dir(mod192)
                  if a.startswith("DEFAULT_CONFIG"))
    builder192 = next(getattr(mod192, a) for a in dir(mod192)
                      if a.startswith("build_agent"))
    build_own = lambda c: builder192(dict(cfg192, **c))  # noqa: E731
    replies, stored, events = P192.drive(turns, build_new)
    replies_o, stored_o, events_o = P192.drive(turns, build_own)
    rows, diffs = [], []
    for i, t in enumerate(spec["turns"]):
        r, ro = replies[i], replies_o[i]
        rec = {"n": i, "turn": t["t"], "kind": t["kind"],
               "reply138j": r, "reply_own": ro}
        if t["want"] == "updated":
            exp = (f"Updated: {t['subj']}'s {t['rel']} is {t['new']} "
                   f"(it was {t['old']}).")
            ok = (r == exp) and (r == ro)
            rec["expect"] = exp
        else:
            ok = (r == ro)
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:200] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    rec_store = {"stored_equal": stored == stored_o,
                 "events_equal": events == events_o}
    if not (stored == stored_o and events == events_o):
        diffs.append({"store_or_event_diff": rec_store,
                      "stored138j": stored, "stored_own": stored_o})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "192", "n": n, "identical": ok, "diffs": diffs,
            "store": rec_store, "rows": rows}


# ---------------- 154f / 154g: jsonl sequential-session
def run_jsonl(piece: str, cases_path: Path, modname: str) -> dict:
    import fable_fix154b_multival as M154  # noqa: E402 (state reader)
    cases = [json.loads(line) for line in
             cases_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]

    def notebook_state(loop) -> dict:
        nb = loop.nb
        pairs: dict = {}
        seen: set = set()
        for fact in nb.facts.values():
            if fact.get("source") != "taught":
                continue
            seen.add((fact["subject"], fact["relation"]))
        for subject, relation in sorted(seen):
            rows = M154.taught_current154b(nb, subject, relation)
            key = f"{nb.entities[subject]}|{relation}"
            vals = [M154.display154b(nb, r["value"]) for r in rows]
            if vals:
                pairs[key] = vals
            elif key.split("|")[0] in ("Kim", "Ana", "Raj", "Eli", "Max",
                                       "Zoe"):
                pairs[key] = []
        return pairs

    def build_new():
        return fresh138j()

    build_own = mkbase(modname)

    def _pass(build):
        got: dict = {}
        loop = build()
        for case in cases:
            if case.get("reset"):
                loop = build()
                continue
            eb = len(loop.nb.events)
            said = turn(loop, case["turn"])
            nev = len(loop.nb.events) - eb
            entry: dict = {"reply": said, "nev": nev}
            if "state" in case or "full_state" in case:
                entry["state"] = notebook_state(loop)
            got[case["n"]] = entry
        return got

    got, own = _pass(build_new), _pass(build_own)
    rows, diffs = [], []
    for case in cases:
        if case.get("reset"):
            rows.append({"reset": True})
            continue
        n = case["n"]
        said, said_own = got[n]["reply"], own[n]["reply"]
        rec = {"n": n, "turn": case.get("turn"), "reply138j": said,
               "reply_own": said_own}
        ok_reply = (said == case.get("expect", said))
        ok_live = (said == said_own)
        writes_ok = True
        if case.get("writes") == "0" and got[n]["nev"] != 0:
            writes_ok = False
        if case.get("writes") == "w" and got[n]["nev"] < 1:
            writes_ok = False
        state_ok = True
        if "state" in case:
            for pair, want in case["state"].items():
                if got[n].get("state", {}).get(pair, []) != list(want):
                    state_ok = False
        full_ok = None
        if "full_state" in case:
            full_ok = (got[n].get("state") == case["full_state"])
        ok = bool(ok_reply and writes_ok and state_ok
                  and (full_ok is not False))
        rec.update(expect=case.get("expect"), live_equal=ok_live,
                   writes_ok=writes_ok, state_ok=state_ok,
                   full_ok=full_ok, verdict="OK" if ok else "FAIL")
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:200] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = sum(1 for r in rows if "turn" in r)
    ok = sum(1 for r in rows if r.get("verdict") == "OK")
    return {"piece": piece, "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


# ---------------- 188: F1 fresh-loop-per-turn
def run_188() -> dict:
    import fable_loop188_agent as L188  # noqa: E402 (sealed texts)
    cases = load_json(
        ROOT / "artifacts" / "fable-statefall188-20260922"
        / "cases188.json")
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    build_own = mkbase("fable_loop188_agent")
    rows, diffs = [], []
    for case in cases:
        new, own = fresh138j(), build_own()
        rn = turn(new, case["turn"]).strip()
        ro = turn(own, case["turn"]).strip()
        sn, so = triples(new), triples(own)
        rec = {"id": case["id"], "kind": case["kind"],
               "turn": case["turn"], "reply138j": rn, "reply_own": ro}
        if case["kind"] == "statement":
            ok = (rn == L188.STATEMENT_FALLBACK188 and sn == []
                  and ro == L188.STATEMENT_FALLBACK188 and so == [])
            rec["expect"] = L188.STATEMENT_FALLBACK188
        else:
            ok = (rn == ro and sn == so)
        rec["verdict"] = "OK" if ok else "FAIL"
        rows.append(rec)
        if not ok:
            diffs.append({k: (str(v)[:200] if isinstance(v, str) else v)
                          for k, v in rec.items()})
    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    return {"piece": "188", "n": n, "identical": ok, "diffs": diffs,
            "rows": rows}


PIECES = {
    "180b": lambda: run_capask(
        "180b", ROOT / "artifacts" / "fable-case180b-20260922"
        / "case180b.json", mkbase("fable_loop180b_agent")),
    "193": lambda: run_capask(
        "193", ROOT / "artifacts" / "fable-apos193-20260922"
        / "case193.json", mkbase("fable_loop193_agent")),
    "164b": run_164b,
    "189": lambda: run_189(
        "189", ROOT / "artifacts" / "fable-sayagain189-20260922"
        / "cases189.json", "fable_loop189_agent"),
    "189b": lambda: run_189(
        "189b", ROOT / "artifacts" / "fable-sayagain189b-20260922"
        / "cases189b.json", "fable_loop189b_agent"),
    "190": run_190,
    "190b": run_190b,
    "187b": run_187b,
    "192": run_192,
    "154f": lambda: run_jsonl(
        "154f", ROOT / "artifacts" / "fable-negate154f-20260922"
        / "case154f.jsonl", "fable_loop154f_agent"),
    "154g": lambda: run_jsonl(
        "154g", ROOT / "artifacts" / "fable-nocorrect154g-20260922"
        / "case154g.jsonl", "fable_loop154g_agent"),
    "188": run_188,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138j M1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    t0 = time.time()
    want = list(PIECES) if args.only == "all" else args.only.split(",")
    out: dict = {"agent": "loop138j", "seconds": 0.0, "pieces": {},
                 "mro155": {
                     "ears_mro": [c.__name__ for c in
                                  L138J.Loop138jEars.__mro__],
                     "has155class": any("155" in c.__name__ for c in
                                        L138J.Loop138jEars.__mro__),
                     "fable_loop155_modules": sorted(
                         m for m in sys.modules if "fable_loop155" in m)}}
    rc = 0
    for piece in want:
        t1 = time.time()
        rep = PIECES[piece]()
        rep["seconds"] = round(time.time() - t1, 1)
        out["pieces"][piece] = rep
        print(f"M1 {piece}: identical={rep['identical']}/{rep['n']} "
              f"diffs={len(rep['diffs'])} in {rep['seconds']}s", flush=True)
        for d in rep["diffs"][:20]:
            print(f"  DIFF {json.dumps(d)[:400]}", flush=True)
        if rep["diffs"]:
            rc = 1
    print(f"155-check: has155class={out['mro155']['has155class']} "
          f"mods={out['mro155']['fable_loop155_modules']}", flush=True)
    if out["mro155"]["has155class"] or out["mro155"]["fable_loop155_modules"]:
        rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    dest = Path(args.out) if args.out else ART138J / "m1-138j-pieces.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, sort_keys=True,
                               ensure_ascii=False),
                    encoding="utf-8")
    print(f"wrote {dest} seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
