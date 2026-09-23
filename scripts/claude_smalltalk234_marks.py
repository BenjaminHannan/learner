#!/usr/bin/env python3
"""Exp 234 marks driver (M1 panel, M2 dev, M5 latency).

  python -B scripts/claude_smalltalk234_marks.py --dev     # M2 + M5 on dev
  python -B scripts/claude_smalltalk234_marks.py --panel   # M1 + M5 on panel

Each case = one fresh temp notebook per agent: setup turns, then the test
turn, on loop234 and on loop138i (built in-process, same config file).
Scoring:
  wellbeing / expect small_talk: 234 test reply must be exactly
    [FIXED] or ["Hi! " + FIXED]; dev additionally requires the "Hi! " form
    iff the matcher saw a greeting (the panel counts either form as a hit).
  every other case: 234 test reply byte-identical to 138i and no line
    containing FIXED.
  every case: every setup reply byte-identical to 138i; notebook snapshot
    identical to 138i; wellbeing test turns write 0 facts on 234.
Latency: wall time of the test turn on each agent (build excluded), agent
order alternated per case; reported as paired median and mean deltas.
Rows -> artifacts/claude-smalltalk234-20260922/{dev,panel}-rows.json.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent
ART = REPO / "artifacts" / "claude-smalltalk234-20260922"
PANEL = REPO / "artifacts" / "claude-smalltalkpanel234-20260922" / "panel.jsonl"
CFG = ART / "loop234-config.json"
CFG138I = REPO / "artifacts" / "fable-agent138i-20260922" / "loop138i-config.json"

import claude_loop234_agent as A  # noqa: E402
import fable_loop138i_agent as L138I  # noqa: E402

FIXED = A.FIXED_234
HITS = ([FIXED], [A.GREET_PREFIX_234 + FIXED])


def build(tag: str):
    state = tempfile.mkdtemp(prefix=f"st234_{tag}_")
    if tag == "234":
        cfg = dict(A.DEFAULT_CONFIG234)
        cfg.update(json.loads(CFG.read_text(encoding="utf-8")))
        cfg["state_dir"] = state
        return A.build_agent234(cfg)
    cfg = dict(L138I.DEFAULT_CONFIG138I)
    cfg.update(json.loads(CFG138I.read_text(encoding="utf-8")))
    cfg["state_dir"] = state
    return L138I.build_agent138i(cfg)


def facts(loop) -> list:
    return sorted(
        (f.get("subject"), f.get("relation"),
         json.dumps(f.get("value"), sort_keys=True), f.get("source"),
         bool(loop.nb.active(fid)))
        for fid, f in loop.nb.facts.items())


def run(tag: str, setup: list[str], turn: str) -> dict:
    loop = build(tag)
    sreps = [list(loop.turn(t)) for t in setup]
    before = set(facts(loop))
    t0 = time.perf_counter()
    rep = list(loop.turn(turn))
    dt = time.perf_counter() - t0
    writes = len(set(facts(loop)) - before)
    snap = json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)
    return {"setup": sreps, "reply": rep, "writes": writes, "snap": snap,
            "ms": dt * 1000.0}


def score(cases: list[dict], positive, strict_form: bool) -> dict:
    rows, deltas = [], []
    for tag in ("234", "138i"):  # warm-up (lazy imports/caches), untimed
        run(tag, [], "How are you?")
    for k, c in enumerate(cases):
        order = ("234", "138i") if k % 2 == 0 else ("138i", "234")
        res = {tag: run(tag, list(c.get("setup") or []), c["turn"])
               for tag in order}
        new, old = res["234"], res["138i"]
        pos = positive(c)
        fixed_hit = new["reply"] in HITS
        fixed_any = any(FIXED in ln for ln in new["reply"])
        same = new["reply"] == old["reply"]
        setup_same = new["setup"] == old["setup"]
        nb_same = new["snap"] == old["snap"]
        if pos:
            ok = fixed_hit and new["writes"] == 0
            if strict_form:
                ok = ok and new["reply"] == [A.reply_234(c["turn"])]
        else:
            ok = same and not fixed_any
        ok = ok and setup_same and nb_same
        deltas.append(new["ms"] - old["ms"])
        rows.append({"id": c["id"], "family": c.get("family"),
                     "expect": c.get("expect"), "positive": pos,
                     "setup": c.get("setup") or [], "turn": c["turn"],
                     "r138i": old["reply"], "r234": new["reply"],
                     "moved": not same, "fixed": fixed_any,
                     "writes234": new["writes"], "writes138i": old["writes"],
                     "setup_same": setup_same, "nb_same": nb_same,
                     "ms234": round(new["ms"], 2),
                     "ms138i": round(old["ms"], 2), "ok": ok})
        flag = "ok " if ok else "MISS"
        print(f"{flag} {c['id']} [{c.get('family')}] {c['turn']!r}\n"
              f"     138i: {old['reply']}\n     234 : {new['reply']}",
              flush=True)
    lat = {"median_delta_ms": round(statistics.median(deltas), 3),
           "mean_delta_ms": round(statistics.mean(deltas), 3),
           "n": len(deltas)}
    return {"rows": rows, "latency": lat}


def summary(rows: list[dict]) -> dict:
    fam: dict = {}
    for r in rows:
        f = fam.setdefault(r["family"], {"n": 0, "ok": 0, "fixed": 0,
                                         "moved": 0})
        f["n"] += 1
        f["ok"] += r["ok"]
        f["fixed"] += r["fixed"]
        f["moved"] += r["moved"]
    return fam


def cmd_dev() -> int:
    data = json.loads((ART / "dev-cases.json").read_text(encoding="utf-8"))
    out = score(data["cases"], lambda c: c["expect"] == "small_talk", True)
    rows = out["rows"]
    n_ok = sum(r["ok"] for r in rows)
    fam = summary(rows)
    (ART / "dev-rows.json").write_text(json.dumps(
        {"rows": rows, "families": fam, "latency": out["latency"]},
        indent=1), encoding="utf-8")
    print(json.dumps(fam))
    print(f"M2 dev {n_ok}/{len(rows)} = {100.0 * n_ok / len(rows):.1f}%")
    print(f"M5 latency {out['latency']}")
    return 0 if n_ok / len(rows) >= 0.95 else 1


def cmd_panel() -> int:
    cases = [json.loads(ln) for ln in PANEL.read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    out = score(cases, lambda c: c["family"] == "wellbeing", False)
    rows = out["rows"]
    fam = summary(rows)
    wb = fam.get("wellbeing", {"n": 0, "fixed": 0})
    wb_hits = sum(1 for r in rows if r["family"] == "wellbeing"
                  and r["r234"] in HITS)
    other_fixed = sum(r["fixed"] for r in rows if r["family"] != "wellbeing")
    other_moved = sum(r["moved"] for r in rows if r["family"] != "wellbeing")
    wb_writes = sum(r["writes234"] for r in rows if r["family"] == "wellbeing")
    nb_diff = sum(not r["nb_same"] for r in rows)
    setup_diff = sum(not r["setup_same"] for r in rows)
    expect_agree = sum(
        1 for r in rows
        if (r["expect"] == "small_talk") == (r["r234"] in HITS))
    m1 = (wb["n"] > 0 and wb_hits / wb["n"] >= 0.90 and other_fixed == 0
          and other_moved == 0 and wb_writes == 0 and nb_diff == 0
          and setup_diff == 0)
    res = {"families": fam, "wellbeing_hits": wb_hits,
           "wellbeing_n": wb["n"], "other_fixed": other_fixed,
           "other_moved": other_moved, "wellbeing_writes": wb_writes,
           "notebook_diffs": nb_diff, "setup_diffs": setup_diff,
           "expect_field_agree": expect_agree, "n": len(rows),
           "latency": out["latency"], "M1": "PASS" if m1 else "FAIL"}
    (ART / "panel-rows.json").write_text(json.dumps(
        {"rows": rows, "summary": res}, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0 if m1 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--panel", action="store_true")
    a = ap.parse_args()
    if a.dev:
        return cmd_dev()
    if a.panel:
        return cmd_panel()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
