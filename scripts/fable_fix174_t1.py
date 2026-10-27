#!/usr/bin/env python3
"""Exp 174 T1 driver -- sealed "of"-question case file through loop174.

Runs artifacts/fable-chainof174-20260922/cases174.json (40 turns: 6 teaches,
12 "of"-asks each followed by its hand-written possessive twin, 10 traps)
on a fresh in-process loop174 AND a fresh in-process loop138f base (same
script, separate notebooks, sleep_threshold=100000), recording per-turn
reply + notebook event count + rewrite label.

Bars (all in PASSMARKS.md):
  T1a twin-equality: every of-ask reply174 == its twin reply174 (same nb).
  T1b cross-agent twin: every of-ask reply174 == base reply138f(twin).
  T1c taught of-asks (8) answer exactly (expect strings in the case file).
  T1d untaught of-asks (4) == the base twin's honest no-record reply.
  T1e traps (10): reply174 byte-identical to reply138f on the same turn.
  T1f 0 writes from asks: events delta 0 on every ask/twin turn (174).
  T1g whole-script identity vs base except the 12 predicted of-ask moves.
  T1h every of-ask fires rewrite_chainof (unit label) and every trap does
      not (traps 35/36/40 are statements/bare: never eligible).

Outputs: artifacts/fable-chainof174-20260922/t1-174.json,
t1-138f.json, t1-compare.json.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix174_t1.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix174_chainof as C174  # noqa: E402 (rewrite labels, read-only)
import fable_loop138f_agent as L138f  # noqa: E402 (base agent, read-only)
import fable_loop174_agent as L174  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-chainof174-20260922"
CASES = json.loads((ART / "cases174.json").read_text(encoding="utf-8"))["cases"]


def fresh(kind: str):
    tmp = tempfile.mkdtemp(prefix=f"t1-174-{kind}_")
    if kind == "174":
        cfg = copy.deepcopy(L174.DEFAULT_CONFIG174)
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        return L174.build_agent174(cfg), tmp
    cfg = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L138f.build_agent138f(cfg), tmp


def nevents(loop) -> int:
    nb = getattr(loop, "nb", None)
    ev = getattr(nb, "events", None)
    return len(ev) if ev is not None else -1


def run_script(kind: str) -> list[dict]:
    loop, tmp = fresh(kind)
    rows = []
    for case in CASES:
        e0 = nevents(loop)
        t0 = time.time()
        try:
            reply = " ".join(loop.turn(case["text"])).strip()
        except Exception as exc:  # noqa: BLE001
            reply = f"HARNESS-ERROR {exc!r}"[:200]
        rows.append({"n": case["n"], "kind": case["kind"],
                     "text": case["text"],
                     "twin": case.get("twin"), "taught": case.get("taught"),
                     "hops": case.get("hops"),
                     "rewrite": C174.rewrite_chainof(case["text"]),
                     "reply": reply, "ev0": e0, "ev1": nevents(loop),
                     "seconds": round(time.time() - t0, 3)})
    return rows


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows174 = run_script("174")
    rows138 = run_script("138f")
    (ART / "t1-174.json").write_text(
        json.dumps(rows174, indent=1, ensure_ascii=False), encoding="utf-8")
    (ART / "t1-138f.json").write_text(
        json.dumps(rows138, indent=1, ensure_ascii=False), encoding="utf-8")
    r174 = {r["n"]: r for r in rows174}
    r138 = {r["n"]: r for r in rows138}
    twins = {c["n"]: c for c in CASES if c["kind"] == "twin"}
    ofasks = [c for c in CASES if c["kind"] == "of-ask"]
    traps = [c for c in CASES if c["kind"] == "trap"]

    fails = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'ok' if ok else 'FAIL'} {name} {detail}", flush=True)
        if not ok:
            fails.append(name)

    # T1h: rewrite labels.
    check("T1h of-asks all fire", all(
        r174[c["n"]]["rewrite"] is not None for c in ofasks),
        f"{sum(1 for c in ofasks if r174[c['n']]['rewrite'] is not None)}/12")
    check("T1h traps never fire", all(
        r174[c["n"]]["rewrite"] is None for c in traps),
        f"{sum(1 for c in traps if r174[c['n']]['rewrite'] is None)}/10")
    # T1a: twin equality on 174.
    for c in ofasks:
        twin_n = next(t["n"] for t in CASES
                      if t.get("of") == c["n"])
        check(f"T1a twin-eq n={c['n']}",
              r174[c["n"]]["reply"] == r174[twin_n]["reply"],
              f"of={r174[c['n']]['reply'][:70]!r} "
              f"twin={r174[twin_n]['reply'][:70]!r}")
    # T1b: cross-agent twin equality.
    for c in ofasks:
        twin_n = next(t["n"] for t in CASES
                      if t.get("of") == c["n"])
        check(f"T1b base-twin-eq n={c['n']}",
              r174[c["n"]]["reply"] == r138[twin_n]["reply"])
    # T1c: taught answers exact.
    for c in ofasks:
        if not c.get("taught"):
            continue
        check(f"T1c taught n={c['n']}",
              r174[c["n"]]["reply"] == c["expect"],
              f"got={r174[c['n']]['reply'][:70]!r} "
              f"want={c.get('expect', '')[:70]!r}")
    # T1d: untaught == base twin honest reply (covered by T1b + twin trap
    # honesty: base twin reply must be a no-record abstain, never a guess).
    for c in ofasks:
        if c.get("taught"):
            continue
        twin_n = next(t["n"] for t in CASES
                      if t.get("of") == c["n"])
        honest = ("don't know" in r138[twin_n]["reply"].lower()
                  or "no record" in r138[twin_n]["reply"].lower()
                  or "i don't" in r138[twin_n]["reply"].lower())
        check(f"T1d untaught-honest n={c['n']}", honest,
              f"twin={r138[twin_n]['reply'][:70]!r}")
    # T1e: traps byte-identical to base.
    for c in traps:
        check(f"T1e trap-identical n={c['n']}",
              r174[c["n"]]["reply"] == r138[c["n"]]["reply"],
              f"got={r174[c['n']]['reply'][:70]!r}")
    # T1f: 0 writes from asks.
    ask_ns = {c["n"] for c in CASES
              if c["kind"] in ("of-ask", "twin")}
    check("T1f 0 writes from asks", all(
        r174[n]["ev1"] == r174[n]["ev0"] for n in ask_ns))
    # Statement traps must not write either.
    for c in (c for c in traps if c["n"] in (35, 36)):
        check(f"T1f stmt-trap no-write n={c['n']}",
              r174[c["n"]]["ev1"] == r174[c["n"]]["ev0"])
    # T1g: whole-script identity except the 12 predicted moves.
    of_ns = {c["n"] for c in ofasks}
    unexpected = [n for n in r174
                  if n not in of_ns
                  and r174[n]["reply"] != r138[n]["reply"]]
    check("T1g identical except predicted", not unexpected,
          f"unexpected={unexpected}")
    moved = [n for n in of_ns
             if r174[n]["reply"] != r138[n]["reply"]]
    check("T1g all 12 of-asks move", sorted(moved) == sorted(of_ns),
          f"moved={sorted(moved)}")

    out = {"seconds": round(time.time() - t0, 1),
           "fails": fails,
           "pass": not fails}
    (ART / "t1-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"T1 {out['seconds']}s pass={out['pass']} fails={fails}",
          flush=True)
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
