#!/usr/bin/env python3
"""Exp 273 M1/M2 order tests (20 seeded cases each, 273 vs 292t).

M1 order test: fresh loop with sleep_due() forced True (sleep_threshold
small + pre-filled experience) AND one user message in the inbox; the
first step() must be a listening tick. Bar: 273 20/20 listening first
(292t comparison arm expected 0/20: sleep first).

M2 no starvation: sleep due + a stream of 1 user message per tick for 10
ticks, then an empty inbox; sleep must run within 3 ticks of the inbox
emptying. Bar: 273 20/20. 292t numbers are reported for comparison only.

All names/values are invented. No sealed panel is read. Usage:
  python -B scripts/claude_loop273_test.py <out.json>
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop273_agent as A273  # noqa: E402 (under test)
import claude_loop292t_agent as A292T  # noqa: E402 (comparison arm)

N_CASES = 20
M1_THRESHOLD = 5
M1_PREFILL = 5
M2_THRESHOLD = 5
M2_PREFILL = 5
M2_STREAM = 10
M2_SLEEP_WITHIN = 3
M2_DRAIN_CAP = 30

_NAMES = ["Zara", "Milo", "Kessa", "Ruan", "Ilsa", "Tobin", "Wren",
          "Calix", "Odessa", "Perrin", "Sable", "Tilda", "Vesper",
          "Bran", "Cleo", "Dario", "Elif", "Fintan", "Greta", "Hadil"]
_RELS = ["city", "color", "boss", "teacher", "friend"]
_VALS = ["Quiln", "Bluefen", "Marlow", "Tess", "Amberline"]


def msg_for(seed: int, tick: int = 0) -> str:
    name = _NAMES[(seed + tick) % len(_NAMES)]
    rel = _RELS[(seed * 3 + tick) % len(_RELS)]
    val = _VALS[(seed * 7 + tick * 2) % len(_VALS)]
    if (seed + tick) % 4 == 3:
        return f"What is {name}'s {rel}?"
    return f"{name}'s {rel} is {val}."


def _cfg(root: Path, threshold: int) -> dict:
    cfg = copy.deepcopy(A292T.DEFAULT_CONFIG292T)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = threshold
    return cfg


def _build_pair(seed: int, threshold: int):
    d273 = Path(tempfile.mkdtemp(prefix=f"m273_s{seed}_"))
    d292t = Path(tempfile.mkdtemp(prefix="m292t_s%d_" % seed))
    l273 = A273.build_agent273(_cfg(d273, threshold))
    l292t = A292T.build_agent292t(_cfg(d292t, threshold))
    return (l273, l292t), (d273, d292t)


def _force_sleep_due(loop, n: int) -> None:
    for _ in range(n):
        loop.experience.append({"tick": 0, "kind": "turn",
                                "text": "setup", "statuses": []})


def _cleanup(dirs) -> None:
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)


def run_m1() -> dict:
    rows = []
    for seed in range(N_CASES):
        (l273, l292t), dirs = _build_pair(seed, M1_THRESHOLD)
        try:
            _force_sleep_due(l273, M1_PREFILL)
            _force_sleep_due(l292t, M1_PREFILL)
            pre273, pre292t = l273.sleep_due(), l292t.sleep_due()
            m = msg_for(seed)
            l273.submit(m)
            l292t.submit(m)
            try:
                e273 = l273.step()
                mode273 = e273.get("mode", "?")
            except Exception as exc:  # noqa: BLE001
                mode273 = f"ERROR:{type(exc).__name__}"
            try:
                e292t = l292t.step()
                mode292t = e292t.get("mode", "?")
            except Exception as exc:  # noqa: BLE001
                mode292t = f"ERROR:{type(exc).__name__}"
            rows.append({"seed": seed, "sleep_due_273": bool(pre273),
                         "sleep_due_292t": bool(pre292t),
                         "first_273": mode273, "first_292t": mode292t,
                         "pass273": mode273 == "LISTENING"})
        finally:
            _cleanup(dirs)
    n273 = sum(1 for r in rows if r["pass273"])
    n292t = sum(1 for r in rows if r["first_292t"] == "LISTENING")
    return {"n": N_CASES, "listen_first_273": n273,
            "listen_first_292t": n292t, "rows": rows,
            "verdict": "PASS" if n273 == N_CASES else "FAIL"}


def run_m2() -> dict:
    rows = []
    for seed in range(N_CASES):
        (l273, l292t), dirs = _build_pair(seed, M2_THRESHOLD)
        try:
            out = {"seed": seed}
            for tag, loop in (("273", l273), ("292t", l292t)):
                _force_sleep_due(loop, M2_PREFILL)
                stream_modes = []
                ok = True
                for t in range(M2_STREAM):
                    loop.submit(msg_for(seed, t))
                    try:
                        ev = loop.step()
                        stream_modes.append(ev.get("mode", "?"))
                    except Exception as exc:  # noqa: BLE001
                        stream_modes.append(f"ERROR:{type(exc).__name__}")
                        ok = False
                        break
                ticks_to_sleep = None
                if ok:
                    for k in range(1, M2_DRAIN_CAP + 1):
                        try:
                            ev = loop.step()
                        except Exception:  # noqa: BLE001
                            ticks_to_sleep = None
                            ok = False
                            break
                        if ev.get("mode") == "SLEEP":
                            ticks_to_sleep = k
                            break
                passed = (ok and ticks_to_sleep is not None
                          and ticks_to_sleep <= M2_SLEEP_WITHIN)
                out[tag] = {"stream_listening": sum(
                    1 for m in stream_modes if m == "LISTENING"),
                    "stream_ticks": len(stream_modes),
                    "ticks_to_sleep": ticks_to_sleep,
                    "pass": bool(passed)}
            out["pass273"] = bool(out["273"]["pass"])
            rows.append(out)
        finally:
            _cleanup(dirs)
    n273 = sum(1 for r in rows if r["pass273"])
    n292t = sum(1 for r in rows if r["292t"]["pass"])
    return {"n": N_CASES, "pass_273": n273, "pass_292t": n292t,
            "within_ticks": M2_SLEEP_WITHIN, "rows": rows,
            "verdict": "PASS" if n273 == N_CASES else "FAIL"}


def main(argv) -> int:
    out_path = argv[1] if len(argv) > 1 else None
    m1 = run_m1()
    m2 = run_m2()
    res = {"m1": m1, "m2": m2,
           "verdict": ("PASS" if m1["verdict"] == "PASS"
                       and m2["verdict"] == "PASS" else "FAIL")}
    print(f"M1 273 listen-first {m1['listen_first_273']}/{m1['n']} "
          f"(292t {m1['listen_first_292t']}/{m1['n']}) -> {m1['verdict']}")
    print(f"M2 273 sleep-within-{M2_SLEEP_WITHIN} {m2['pass_273']}/{m2['n']} "
          f"(292t {m2['pass_292t']}/{m2['n']}) -> {m2['verdict']}")
    print("VERDICT:", res["verdict"])
    if out_path:
        Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"wrote {out_path}")
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
