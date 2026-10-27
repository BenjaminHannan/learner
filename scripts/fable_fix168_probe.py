#!/usr/bin/env python3
"""Exp 168 T1/T2 probe driver -- grounded self replies vs loop138b (live A/B).

Reads the sealed case file (same folder, fable_fix168_probe_cases.json).
Both arms run fresh in-process (build_agent with sleep_threshold=100000).

  Part A (>=25 self-style Qs, fresh notebook): loop168 -> 0 replies naming
      any check-name not in the notebook, 0 crashes. loop138b runs too, but
      only to prove probe sensitivity (violations/crashes reported, not
      scored).
  Part B (panel facts taught, >=10 same-style Qs): byte-identical replies.
  Part C (>=5 empty-state web/sleep/proposal Qs -> plain honest, 0 crashes;
      >=3 with state present -> byte-identical).
  Part D (>=15 ordinary teach/ask turns): byte-identical replies.
T2: 0 FACT/RETRACT events added by any self-question turn on loop168.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix168_probe.py --out
    artifacts/fable-selfground168-20260922/probe168
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138b_agent as B138  # noqa: E402 (frozen base, read-only)
import fable_loop168_agent as L168  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfground168-20260922"
CASES = ART / "fable_fix168_probe_cases.json"

WEB_URL = "https://example.org/zara-said"
WEB_SPAN = "zara's hobby is chess"


def fresh(tag: str, mod, workroot: Path):
    d = workroot / tag
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    cfg = copy.deepcopy(mod.DEFAULT_CONFIG168
                        if tag.startswith("m") else mod.DEFAULT_CONFIG138B)
    cfg["state_dir"] = str(d)
    cfg["sleep_threshold"] = 100000
    build = mod.build_agent168 if hasattr(mod, "build_agent168") \
        else mod.build_agent138b
    return build(cfg)


def turn_logged(loop, text: str):
    """One turn; returns (reply, crashed, wrote_fact). Never raises."""
    ev0 = [e for e in loop.nb.events
           if e.get("kind") in ("FACT", "RETRACT")]
    try:
        out = loop.turn(text)
        reply = " ".join(out) if out else "(nothing to say)"
        crashed = None
    except Exception as exc:  # noqa: BLE001 -- a crash is a scored finding
        reply, crashed = "", f"{type(exc).__name__}: {exc}"
    ev1 = [e for e in loop.nb.events
           if e.get("kind") in ("FACT", "RETRACT")]
    wrote = len(ev1) > len(ev0)
    return reply, crashed, wrote


def nb_names(loop) -> set[str]:
    names = {str(v).lower() for v in loop.nb.entities.values()}
    for fid, f in loop.nb.facts.items():
        if loop.nb.active(fid):
            v = f.get("value", {})
            if "literal" in v:
                names.add(str(v["literal"]).lower())
            elif "entity" in v:
                names.add(str(loop.nb.entities.get(
                    v["entity"], "")).lower())
    return names


def violations(reply: str, known: set[str], names: list[str]) -> list[str]:
    low = " " + reply.lower() + " "
    bad = []
    for n in names:
        if re.search(r"\b" + re.escape(n) + r"\b", low):
            if n not in known:
                bad.append(n)
    return bad


def file_web_harness(loop):
    """Mirror Self99 file_web_row on a loop168/138b notebook (harness only)."""
    res = loop.nb.resolve("Zara")
    assert res.status == "OK", "Zara must exist"
    eid = res.detail["entity_id"]
    out = loop.nb.assert_fact(
        "fix168-web-1", "thinking", "web-quarantine", eid, "hobby",
        {"literal": "chess"},
        provenance={"url": WEB_URL, "quoted_span": WEB_SPAN})
    assert out.status == "SAVED", out.status
    loop.self_web_filings.append(
        {"fact_id": out.detail["fact_id"], "url": WEB_URL, "span": WEB_SPAN})


def file_proposed_harness(loop):
    res = loop.nb.resolve("Zara")
    eid = res.detail["entity_id"]
    out = loop.nb.assert_fact(
        "fix168-prop-1", "thinking", "proposed", eid, "job",
        {"literal": "pilot"}, provenance={})
    assert out.status == "SAVED", out.status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 168 T1/T2 probe")
    ap.add_argument("--out", default=str(ART / "probe168"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    t0 = time.time()
    spec = json.loads(CASES.read_text(encoding="utf-8"))
    names = spec["name_check"]["extra_names"]
    rep: dict = {"parts": {}, "t2_writes": 0, "t2_turns": 0}
    rc = 0

    # ---- Part A: fresh notebook, 25 self-style questions ----
    la, lb = fresh("mA", L168, out), fresh("bA", B138, out)
    rows = []
    for i, c in enumerate(spec["partA"]):
        ra, ca, wa = turn_logged(la, c["q"])
        rb, cb, _ = turn_logged(lb, c["q"])
        bad = [] if ca else violations(ra, nb_names(la), names)
        badb = [] if cb else violations(rb, nb_names(lb), names)
        rows.append({"n": i + 1, "q": c["q"], "m168": ra, "crash168": ca,
                     "named168": bad, "loop138b": rb, "crash138b": cb,
                     "named138b": badb, "wrote168": wa})
        if ca or bad or wa:
            rc = 1
    rep["parts"]["A"] = {
        "n": len(rows), "need": 25,
        "crashes168": sum(1 for r in rows if r["crash168"]),
        "named168": sum(1 for r in rows if r["named168"]),
        "self_writes168": sum(1 for r in rows if r["wrote168"]),
        "base_crashes": sum(1 for r in rows if r["crash138b"]),
        "base_named": sum(1 for r in rows if r["named138b"]),
        "pass": len(rows) >= 25 and all(
            not r["crash168"] and not r["named168"] and not r["wrote168"]
            for r in rows)}
    rep["rowsA"] = rows
    if not rep["parts"]["A"]["pass"]:
        rc = 1

    # ---- Part B: panel facts taught, 10 same-style asks identical ----
    la, lb = fresh("mB", L168, out), fresh("bB", B138, out)
    rows = []
    for t in spec["partB_teaches"]:
        ra, _, _ = turn_logged(la, t)
        rb, _, _ = turn_logged(lb, t)
        rows.append({"teach": t, "m168": ra, "loop138b": rb,
                     "same": ra == rb})
    asks = []
    for i, c in enumerate(spec["partB_asks"]):
        ra, ca, wa = turn_logged(la, c["q"])
        rb, cb, _ = turn_logged(lb, c["q"])
        asks.append({"n": i + 1, "q": c["q"], "m168": ra, "loop138b": rb,
                     "same": ra == rb and ca is None and cb is None,
                     "wrote168": wa})
        if wa:
            rc = 1
    rep["parts"]["B"] = {"teaches": rows, "asks": asks,
                         "pass": len(asks) >= 10 and all(
                             a["same"] and not a["wrote168"] for a in asks)}
    if not rep["parts"]["B"]["pass"]:
        rc = 1

    # ---- Part C: empty-state plain + with-state identical ----
    la, lb = fresh("mC0", L168, out), fresh("bC0", B138, out)
    rows = []
    for i, c in enumerate(spec["partC_empty"]):
        ra, ca, wa = turn_logged(la, c["q"])
        rb, cb, _ = turn_logged(lb, c["q"])
        ok = ca is None and not wa
        if c["expect"] == "plain-web":
            ok = ok and ra == "I haven't filed anything from the web."
        elif c["expect"] == "plain-forget":
            ok = ok and ra == ("I haven't forgotten anything "
                               "you taught me.")
        else:
            ok = ok and ra == rb and cb is None
        rows.append({"n": i + 1, "q": c["q"], "m168": ra, "loop138b": rb,
                     "crash168": ca, "ok": ok})
        if not ok:
            rc = 1
    # with-state arm: same harness setups on both loops
    ma, mb = fresh("mC1", L168, out), fresh("bC1", B138, out)
    for loop in (ma, mb):
        turn_logged(loop, spec["partC_setup_teach"][0])
        file_web_harness(loop)
        file_proposed_harness(loop)
        loop.counters["sleeps"] = 1
        loop.self_sleep_history.append({"tick": loop.tick})
    full = []
    for i, c in enumerate(spec["partC_full"]):
        ra, ca, wa = turn_logged(ma, c["q"])
        rb, cb, _ = turn_logged(mb, c["q"])
        ok = ra == rb and ca is None and cb is None
        full.append({"n": i + 1, "q": c["q"], "m168": ra, "loop138b": rb,
                     "ok": ok})
        if not ok:
            rc = 1
    rep["parts"]["C"] = {"empty": rows, "full": full,
                         "pass": len(rows) >= 5 and len(full) >= 3 and all(
                             r["ok"] for r in rows) and all(
                             r["ok"] for r in full)}
    if not rep["parts"]["C"]["pass"]:
        rc = 1

    # ---- Part D: 15 ordinary teach/ask turns identical ----
    la, lb = fresh("mD", L168, out), fresh("bD", B138, out)
    rows = []
    for i, t in enumerate(spec["partD"]):
        ra, ca, wa = turn_logged(la, t)
        rb, cb, wb = turn_logged(lb, t)
        ok = ra == rb and ca is None and cb is None and wa == wb
        rows.append({"n": i + 1, "turn": t, "m168": ra, "loop138b": rb,
                     "ok": ok})
        if not ok:
            rc = 1
    rep["parts"]["D"] = {"rows": rows,
                         "pass": len(rows) >= 15 and all(
                             r["ok"] for r in rows)}
    if not rep["parts"]["D"]["pass"]:
        rc = 1

    # ---- T2: no writes from any self-question turn ----
    rep["t2_turns"] = (len(rep["rowsA"]) + len(rep["parts"]["B"]["asks"])
                       + len(rep["parts"]["C"]["empty"])
                       + len(rep["parts"]["C"]["full"]))
    rep["t2_writes"] = (sum(1 for r in rep["rowsA"] if r["wrote168"])
                        + sum(1 for r in rep["parts"]["B"]["asks"]
                              if r["wrote168"]))
    rep["t2_pass"] = rep["t2_writes"] == 0
    if not rep["t2_pass"]:
        rc = 1

    rep["seconds"] = round(time.time() - t0, 1)
    rep["pass"] = rc == 0
    (out / "probe168-results.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    for p, v in rep["parts"].items():
        print(f"part{p}: {'PASS' if v['pass'] else 'FAIL'}", flush=True)
    print(f"T2 writes={rep['t2_writes']}/{rep['t2_turns']} "
          f"{rep['seconds']}s -> {'PASS' if rep['pass'] else 'FAIL'}",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
