#!/usr/bin/env python3
"""Experiment 160c -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN dialogues from artifacts/fable-twohop160c-20260922/cases160c.json
(20 two-/three-hop H dialogues) plus the sealed 160b cases
(artifacts/fable-correct160b-20260922/cases160b.json, read-only) for the
identity arms. Each dialogue runs through FRESH in-process loops
(build_agent160c; S/O groups also build_agent160b for the byte-identity
check), triples via fable_loop90_agent.notebook_triples. Every seed/case
reported, never averaged.

Judgements:
  H (chain answer then bare): bare reply is exactly the which-one-is-wrong
    clarify built from the sealed chain + V, with 0 FACT writes on the bare
    turn; the explicit follow-up replies "Saved: ..." and its triple set
    differs from the pre-explicit set ONLY in the named fact (exactly the
    named fact saved). Verdict OK/FAIL.
  S (160b cases A + B01-B08, single-fact): triples AND replies identical
    160c vs 160b. Verdict OK/FAIL.
  O (160b cases C + D, other turns): replies AND FACT counts identical
    160c vs 160b. Verdict OK/FAIL.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix160c_probe.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix160b_laststated as B160b  # noqa: E402 (parse, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop160b_agent as L160b  # noqa: E402 (base arm, read-only)
import fable_loop160c_agent as L160c  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART160C = ROOT / "artifacts" / "fable-twohop160c-20260922"
ART160B = ROOT / "artifacts" / "fable-correct160b-20260922"


def fresh(build_fn):
    tmp = tempfile.mkdtemp(prefix="p160c_")
    return build_fn({"state_dir": tmp, "sleep_threshold": 100000})


def step(loop, turn: str) -> tuple[str, int]:
    f0 = sum(1 for e in loop.nb.events if e.get("kind") == "FACT")
    reply = " ".join(loop.turn(turn))
    f1 = sum(1 for e in loop.nb.events if e.get("kind") == "FACT")
    return reply, f1 - f0


def expected_clarify(chain: list, value: str) -> str:
    opts = [f"{n}'s {r} is {v}" for n, r, v in chain]
    listed = f"{opts[0]}, or {opts[1]}" if len(opts) == 2 else (
        ", ".join(opts[:-1]) + f", or {opts[-1]}")
    ln, lr, _ = chain[-1]
    return (f"Which one is wrong: {listed}? Say e.g. "
            f'"Actually, {ln}\'s {lr} is {value}."')


def main() -> int:
    t0 = time.time()
    cases = json.loads((ART160C / "cases160c.json").read_text(encoding="utf-8"))
    base = json.loads((ART160B / "cases160b.json").read_text(encoding="utf-8"))
    rows: list[dict] = []

    for row in cases["H"]:
        loop = fresh(L160c.build_agent160c)
        replies, deltas = [], []
        for t in list(row["teaches"]) + [row["q"]]:
            r, d = step(loop, t)
            replies.append(r)
            deltas.append(d)
        val = B160b.parse_bare_correction(row["bare"])
        exp = expected_clarify(row["chain"], val or "")
        # 160b arm for the change-bites sanity check.
        loopb = fresh(L160b.build_agent160b)
        for t in list(row["teaches"]) + [row["q"], row["bare"]]:
            rb, _ = step(loopb, t)
        bare_reply, bare_delta = step(loop, row["bare"])
        pre = set(L90.notebook_triples(loop.nb))
        expl_reply, expl_delta = step(loop, row["explicit"])
        post = set(L90.notebook_triples(loop.nb))
        wn, wr, wv = row["followup_wrote"]
        named_before = [t for t in pre if t[0] == wn and t[1] == wr]
        named_after = [t for t in post if t[0] == wn and t[1] == wr]
        others_ok = all(tuple(t) in post for t in row["followup_untouched"])
        only_named_changed = (
            len(post - pre) == 1 and len(pre - post) == 1
            and tuple(row["followup_wrote"]) in post)
        ok = (val is not None
              and bare_reply == exp and bare_delta == 0
              and bare_reply != rb
              and str(row["chain"][-1][2]) in replies[-1]
              and expl_reply == f"Saved: {wn}'s {wr} is {wv}."
              and expl_delta == 1 and others_ok and only_named_changed
              and len(named_before) == 1 and named_after == [tuple(
                  row["followup_wrote"])])
        rows.append({"id": row["id"], "group": "H", "bare": row["bare"],
                     "bare_reply": bare_reply, "expected": exp,
                     "bare_delta": bare_delta, "expl_reply": expl_reply,
                     "triples": sorted(post),
                     "verdict": "OK" if ok else "FAIL"})

    for row in base["A"]:
        got_r, got_d, got_t = [], [], None
        loop = fresh(L160c.build_agent160c)
        for t in [row["teach"], row["bare"]]:
            r, d = step(loop, t)
            got_r.append(r)
            got_d.append(d)
        got_t = sorted(L90.notebook_triples(loop.nb))
        loopb = fresh(L160b.build_agent160b)
        exp_r = [" ".join(loopb.turn(t)) for t in
                 [row["teach"], row["bare"]]]
        exp_t = sorted(L90.notebook_triples(loopb.nb))
        ok = got_r == exp_r and got_t == exp_t and len(got_t) > 0
        rows.append({"id": row["id"], "group": "S",
                     "verdict": "OK" if ok else "FAIL",
                     "replies160c": got_r, "replies160b": exp_r})

    for row in base["B"][:8]:
        loop = fresh(L160c.build_agent160c)
        got_r = [" ".join(loop.turn(t)) for t in
                 list(row["setup"]) + [row["bare"]]]
        got_t = sorted(L90.notebook_triples(loop.nb))
        loopb = fresh(L160b.build_agent160b)
        exp_r = [" ".join(loopb.turn(t)) for t in
                 list(row["setup"]) + [row["bare"]]]
        exp_t = sorted(L90.notebook_triples(loopb.nb))
        ok = got_r == exp_r and got_t == exp_t and len(got_t) > 0
        rows.append({"id": row["id"], "group": "S",
                     "verdict": "OK" if ok else "FAIL",
                     "replies160c": got_r, "replies160b": exp_r})

    for row in base["C"] + base["D"]:
        loop = fresh(L160c.build_agent160c)
        got_r, got_w = [], 0
        for t in row["turns"]:
            r, d = step(loop, t)
            got_r.append(r)
            got_w += d
        loopb = fresh(L160b.build_agent160b)
        exp_r, exp_w = [], 0
        for t in row["turns"]:
            r, d = step(loopb, t)
            exp_r.append(r)
            exp_w += d
        ok = got_r == exp_r and got_w == exp_w
        rows.append({"id": row["id"], "group": "O",
                     "verdict": "OK" if ok else "FAIL",
                     "replies160c": got_r, "replies160b": exp_r})

    counts: dict = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    groups: dict = {}
    for r in rows:
        g = groups.setdefault(r["group"], {})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
    out = {"seconds": round(time.time() - t0, 1), "counts": counts,
           "by_group": groups, "rows": rows}
    (ART160C / "probe160c-loop160c.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"probe160c: {counts} by_group={groups} "
          f"seconds={out['seconds']}", flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']}: {json.dumps(r)[:400]}", flush=True)
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
