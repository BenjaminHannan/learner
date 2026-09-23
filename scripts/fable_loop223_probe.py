#!/usr/bin/env python3
"""Experiment 223 probe driver (M1/M2/M5-probe; harness only, no agent change).

Builds one FRESH loop138i loop and one FRESH loop223 loop in isolated
scratch state dirs (never the repo-root notebook/), teaches the same 4
fictional facts on both (replies must match), then asks every case in
artifacts/fable-cantdo223-20260922/questions223.jsonl on both in lockstep
and compares reply + stored-facts fingerprint per case.

Per-case router intent comes from the base's own call
(fable_loop138_agent._route127). Expected replies for A-cases marked
capability (intent C24/C25) are the base's own grounded self answers
(fable_fix168_ground.grounded_self_answer on the BASE loop) for the
canonical capability question -- i.e. what the base serves when routed as
C24/C25. A-cases with any other intent are "not capability": expect
byte-identical to the base (the router is never widened).

Modes:
  --pilot : dry run before the seal (writes pilot rows only).
  --run   : registered run after the seal (writes registered rows +
            verdict lines for M1/M2/M5-probe). Same code path.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop223_probe.py --pilot|--run \\
    --out artifacts/fable-cantdo223-20260922
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ART = Path(__file__).resolve().parent.parent / "artifacts" \
    / "fable-cantdo223-20260922"

TEACHES = [
    "Kim's city is Oslo.",
    "Kim's boss is Lee.",
    "Kim's job is baker.",
    "Lee's city is Bergen.",
]


def show_val(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def facts_fp(loop) -> str:
    """Semantic stored-facts fingerprint (chain hashes excluded: event_id
    carries a per-build random suffix, so raw events can never match
    across two fresh builds; what matters is the stored triples)."""
    nb = loop.nb
    triples = sorted(
        (nb.entities.get(f["subject"], f["subject"]), f["relation"],
         show_val(nb, f["value"]), f.get("source"),
         bool(nb.active(fid)))
        for fid, f in nb.facts.items())
    sup = sorted(
        (nb.entities.get(nb.facts[o]["subject"], "?"),
         nb.facts[o]["relation"], show_val(nb, nb.facts[o]["value"]),
         show_val(nb, nb.facts[n]["value"]))
        for o, n in nb.superseded.items()
        if o in nb.facts and n in nb.facts)
    blob = json.dumps({"triples": triples, "superseded": sup},
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def build_pair(root: Path, cfg138i: dict):
    import fable_loop138i_agent as L138I  # noqa: E402
    import fable_loop223_agent as L223  # noqa: E402
    d_base = root / "state138i"
    d_new = root / "state223"
    for d in (d_base, d_new):
        if d.exists():
            shutil.rmtree(d)
    c1 = copy.deepcopy(cfg138i)
    c1["state_dir"] = str(d_base)
    c2 = copy.deepcopy(cfg138i)
    c2["state_dir"] = str(d_new)
    base = L138I.build_agent138i(c1)
    new = L223.build_agent223(c2)
    return base, new


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 223 probe (M1/M2/M5-probe)")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    if bool(args.pilot) == bool(args.run):
        ap.error("pass exactly one of --pilot / --run")
    mode = "pilot" if args.pilot else "registered"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    import fable_loop138_agent as L138  # noqa: E402 (base router, read-only)
    import fable_fix168_ground as G168  # noqa: E402 (base answerer, read-only)

    cfg138i = json.loads((out / "loop223-config.json").read_text(
        encoding="utf-8"))
    questions = [json.loads(line) for line in
                 (out / "questions223.jsonl").read_text(
                     encoding="utf-8").splitlines() if line.strip()]

    work = out / ("pilot-work" if args.pilot else "run-work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    # Expected capability sheets from the BASE's own answerer on a base
    # loop (canonical C24/C25; fixed text, read from the base loop state).
    base0, _ = build_pair(work / "exp", cfg138i)
    for line in TEACHES:
        base0.turn(line)
    exp_c25 = G168.grounded_self_answer(
        base0, "What can you not do?", "C25")
    exp_c24 = G168.grounded_self_answer(base0, "What can you do?", "C24")
    shutil.rmtree(work / "exp", ignore_errors=True)

    rows = []
    teach_ok = True
    m1_need = m1_got = m1_writes = 0
    m2_need = m2_got = 0
    m5_bad = 0
    for i, q in enumerate(questions):
        text = q["text"]
        # Fresh pair per case (teach 4 shared facts + ask 1): histories
        # stay in lockstep, so count-dependent replies stay comparable and
        # an A-case bypass can never pollute another case's counters.
        base, new = build_pair(work / f"c{i:03d}", cfg138i)
        for line in TEACHES:
            r_base = " ".join(base.turn(line))
            r_new = " ".join(new.turn(line))
            if r_base != r_new:
                teach_ok = False
                rows.append({"phase": "teach", "case": q["id"],
                             "text": line, "base": r_base, "new": r_new,
                             "identical": False})
        intent, _info = L138._route127(text)
        fp_b0, fp_n0 = facts_fp(base), facts_fp(new)
        teach_fp_same = fp_b0 == fp_n0
        teach_ok = teach_ok and teach_fp_same
        r_base = " ".join(base.turn(text))
        r_new = " ".join(new.turn(text))
        fp_b1, fp_n1 = facts_fp(base), facts_fp(new)
        wrote_b = fp_b1 != fp_b0
        wrote_n = fp_n1 != fp_n0
        grp = q["group"]
        if grp == "A" and intent in ("C24", "C25"):
            expected = exp_c25 if intent == "C25" else exp_c24
            mark = "capability"
            passed = (r_new == expected) and not wrote_n and not wrote_b
            m1_need += 1
            m1_got += passed
            m1_writes += wrote_n or wrote_b
        else:
            mark = "not-capability" if grp == "A" else "identical"
            passed = (r_new == r_base) and (fp_n1 == fp_b1)
            if grp in ("B", "C"):
                m2_need += 1
                m2_got += passed
            else:
                m1_need += 1
                m1_got += passed
        if wrote_n != wrote_b or (wrote_n and r_new != r_base):
            m5_bad += 1
        rows.append({"phase": "case", "id": q["id"], "group": grp,
                     "text": text, "intent": intent, "mark": mark,
                     "base": r_base, "new": r_new,
                     "expected": expected if mark == "capability" else r_base,
                     "pass": passed, "wrote_base": wrote_b,
                     "wrote_new": wrote_n, "fp_base": fp_b1,
                     "fp_new": fp_n1})
    wall = round(time.monotonic() - t0, 1)
    m1 = {"need": m1_need, "got": m1_got, "writes": m1_writes,
          "pass": m1_got == m1_need and m1_writes == 0 and teach_ok}
    m2 = {"need": m2_need, "got": m2_got, "pass": m2_got == m2_need
          and teach_ok}
    m5p = {"bad": m5_bad, "pass": m5_bad == 0}
    rep = {"mode": mode, "seconds": wall, "teach_ok": teach_ok,
           "exp_c25": exp_c25, "exp_c24": exp_c24, "M1": m1, "M2": m2,
           "M5probe": m5p, "rows": rows}
    name = ("probe223-pilot.json" if args.pilot
            else "probe223-registered.json")
    (out / name).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(f"{mode}: M1 {m1_got}/{m1_need} writes={m1_writes} "
          f"M2 {m2_got}/{m2_need} M5probe-bad={m5_bad} {wall}s -> "
          f"{'PASS' if m1['pass'] and m2['pass'] and m5p['pass'] else 'FAIL'}",
          flush=True)
    for r in rows:
        if r.get("phase") == "case" and not r["pass"]:
            print(f"  MISS {r['id']} [{r['mark']}/{r['intent']}] "
                  f"Q={r['text'][:60]}", flush=True)
            print(f"    base={r['base'][:160]}", flush=True)
            print(f"    new ={r['new'][:160]}", flush=True)
    return 0 if (m1["pass"] and m2["pass"] and m5p["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
