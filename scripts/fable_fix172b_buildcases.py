#!/usr/bin/env python3
"""Experiment 172b -- case-file BUILDER (open, pre-seal only).

NOT a registered run; output is reviewed, then sealed. Two jobs:

1. T1b: replay 154c's sealed T1b turns (probe154c_cases.jsonl) through
   fresh Loop172AgentLoop segments, capturing replies + state maps at the
   same pinned lines. Expectation: ONLY the copula silent-overwrite line
   (n=6) and its direct consequences change.

2. T1c: replay the authored TURNS172B_T1C below through fresh loops on
   BOTH agents (172 for expects, 154c as the identical-reference for the
   allow/other quotas), asserting the quota contract, then write the
   sealed case file with expects + state maps.

Writes into artifacts/fable-copula172b-20260922/ (un-sealed until the
PASSMARKS seal).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix154c_probe as P154C  # noqa: E402 (read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (reference, read-only)
import fable_loop172_agent as L172  # noqa: E402 (agent under test, read-only)

ART154C = ROOT / "artifacts" / "fable-multival154c-20260922"
ART = ROOT / "artifacts" / "fable-copula172b-20260922"

# (turn, quota) quotas: copula-yes / copula-no / actually / allow / other.
# {"reset": True} starts a fresh loop in both arms.
TURNS172B_T1C: list[tuple | dict] = [
    {"reset": True},
    # -- copula-yes x6 (prompt, yes replaces, ask shows new) --
    ("Zilo is a citizen of Velmar.", "copula-yes"),
    ("Zilo is a citizen of Ostrin.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Zilo's citizenship?", "copula-yes"),
    ("The capital of Velmar is Norvik.", "copula-yes"),
    ("The capital of Velmar is Selby.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Velmar's capital?", "copula-yes"),
    ("Quenna is married to Brax.", "copula-yes"),
    ("Quenna is married to Drell.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Quenna's spouse?", "copula-yes"),
    {"reset": True},
    ("Ysolde is employed by Haldor.", "copula-yes"),
    ("Ysolde is employed by Corvin.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Ysolde's employer?", "copula-yes"),
    ("Fenwick works in the field of cartography.", "copula-yes"),
    ("Fenwick works in the field of astronomy.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Fenwick's occupation?", "copula-yes"),
    ("Mirabel speaks the language of Velmaric.", "copula-yes"),
    ("Mirabel speaks the language of Ostric.", "copula-yes"),
    ("yes.", "copula-yes"),
    ("Who is Mirabel's language?", "copula-yes"),
    {"reset": True},
    # -- copula-no x6 (prompt, no keeps, ask shows old) --
    ("Pell is a citizen of Lumen.", "copula-no"),
    ("Pell is a citizen of Umbra.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Pell's citizenship?", "copula-no"),
    ("The capital of Lumen is Alba.", "copula-no"),
    ("The capital of Lumen is Dusk.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Lumen's capital?", "copula-no"),
    ("Sarella is married to Odric.", "copula-no"),
    ("Sarella is married to Petter.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Sarella's spouse?", "copula-no"),
    {"reset": True},
    ("Tormund is employed by Vestria.", "copula-no"),
    ("Tormund is employed by Kappor.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Tormund's employer?", "copula-no"),
    ("Wrenna works in the field of botany.", "copula-no"),
    ("Wrenna works in the field of geology.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Wrenna's occupation?", "copula-no"),
    ("Hadrin died in the city of Norvik.", "copula-no"),
    ("Hadrin died in the city of Selby.", "copula-no"),
    ("no.", "copula-no"),
    ("Who is Hadrin's place of death?", "copula-no"),
    {"reset": True},
    # -- Actually-corrects x6 (setup teach, silent correct as now, ask) --
    ("Remy is a citizen of Velmar.", "actually"),
    ("Actually, Remy is a citizen of Ostrin.", "actually"),
    ("Who is Remy's citizenship?", "actually"),
    ("The capital of Borin is Alba.", "actually"),
    ("Actually, the capital of Borin is Dusk.", "actually"),
    ("Who is Borin's capital?", "actually"),
    ("Celia is married to Odric.", "actually"),
    ("Actually, Celia is married to Petter.", "actually"),
    ("Who is Celia's spouse?", "actually"),
    ("Doran is employed by Vestria.", "actually"),
    ("Actually, Doran is employed by Kappor.", "actually"),
    ("Who is Doran's employer?", "actually"),
    ("Elif works in the field of botany.", "actually"),
    ("Actually, Elif works in the field of geology.", "actually"),
    ("Who is Elif's occupation?", "actually"),
    ("Garran speaks the language of Velmaric.", "actually"),
    ("Actually, Garran speaks the language of Ostric.", "actually"),
    ("Who is Garran's language?", "actually"),
    {"reset": True},
    # -- allow-listed copula re-teach x6 (identical to loop154c: add) --
    ("Vex is famous for Zoop.", "allow"),
    ("Vex is famous for Quux.", "allow"),
    ("Who is Vex's notable work?", "allow"),
    ("Jorah is famous for Flint.", "allow"),
    ("Jorah is famous for Tinder.", "allow"),
    ("Who is Jorah's notable work?", "allow"),
    ("Sable is famous for Ink.", "allow"),
    ("Sable is famous for Vellum.", "allow"),
    ("Who is Sable's notable work?", "allow"),
    ("Corvin is famous for Brass.", "allow"),
    ("Corvin is famous for Copper.", "allow"),
    ("Who is Corvin's notable work?", "allow"),
    ("Drell is famous for Maple.", "allow"),
    ("Drell is famous for Birch.", "allow"),
    ("Who is Drell's notable work?", "allow"),
    ("Petter is famous for Slate.", "allow"),
    ("Petter is famous for Shale.", "allow"),
    ("Who is Petter's notable work?", "allow"),
    {"reset": True},
    # -- other identical x8 (first-teach Saved, dup-ack, missing ask) --
    ("Zeben's hobby is whittling.", "other"),
    ("Zeben's hobby is whittling.", "other"),
    ("Who is Zeben's hobby?", "other"),
    ("Quilla's mentor is Odo.", "other"),
    ("Who is Quilla's mentor?", "other"),
    ("Who is Nobodyhere's hobby?", "other"),
    ("The official language of Umbra is Umbric.", "other"),
    ("Who is Umbra's official language?", "other"),
]


def fresh(kind: str):
    tmp = tempfile.mkdtemp(prefix=f"build172b_{kind}_")
    if kind == "154c":
        return L154c.build_agent154c({"state_dir": tmp})
    return L172.build_agent172({"state_dir": tmp})


def build_t1b() -> int:
    src = [json.loads(l) for l in
           (ART154C / "probe154c_cases.jsonl").read_text(
               encoding="utf-8").splitlines() if l.strip()]
    pinned_state = {i for i, c in enumerate(src) if "state" in c}
    pinned_full = {i for i, c in enumerate(src) if "full_state" in c}
    loops = {"172": fresh("172")}
    seg = 0
    out: list[dict] = []
    states: dict[int, dict] = {}
    n = 0
    for c in src:
        if c.get("reset"):
            seg += 1
            loops["172"] = fresh("172")
            out.append({"reset": True})
            continue
        n += 1
        assert c["n"] == n, (c["n"], n)
        said = " ".join(loops["172"].turn(c["turn"]))
        out.append({"n": n, "turn": c["turn"], "expect": said})
        states[n] = P154C.notebook_state(loops["172"])
    for idx, c in enumerate(out):
        if c.get("reset"):
            continue
        if idx in pinned_state:
            c["state"] = states[c["n"]]
    for idx in pinned_full:
        c = out[idx]
        c["full_state"] = states[c["n"]]
        c["state"] = states[c["n"]]
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "probe172b_t1b_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False, sort_keys=True)
                   for c in out) + "\n", encoding="utf-8")
    # Diff report vs 154c for the PASSMARKS changed-lines list.
    old = [json.loads(l) for l in
           (ART154C / "probe154c_cases.jsonl").read_text(
               encoding="utf-8").splitlines() if l.strip()]
    n_change = 0
    for a, b in zip(old, out):
        if a != b:
            n_change += 1
            print(f"CHANGED n={a.get('n')}:")
            for k in ("expect", "state", "full_state"):
                if a.get(k) != b.get(k):
                    print(f"  {k}: {json.dumps(a.get(k))[:160]!r}\n"
                          f"   ->  {json.dumps(b.get(k))[:160]!r}")
    print(f"t1b lines={len(out)} changed={n_change}")
    return 0


def build_t1c() -> int:
    loops = {k: fresh(k) for k in ("154c", "172")}
    n_allow = n_other = bad = n = 0
    n_quota: dict[str, int] = {}
    cases: list[dict] = []
    states: dict[int, dict] = {}
    for entry in TURNS172B_T1C:
        if isinstance(entry, dict):
            for k in loops:
                loops[k] = fresh(k)
            cases.append({"reset": True})
            print("-- reset --")
            continue
        turn, quota = entry
        n += 1
        n_quota[quota] = n_quota.get(quota, 0) + 1
        reps = {k: " ".join(loops[k].turn(turn)) for k in loops}
        got, ref = reps["172"], reps["154c"]
        if quota in ("allow", "other"):
            if got != ref:
                bad += 1
                print(f"IDENT-MISMATCH n={n} quota={quota} turn={turn!r}\n"
                      f"  172  {got!r}\n  154c {ref!r}", flush=True)
            n_allow += quota == "allow"
            n_other += quota == "other"
        else:
            print(f"[{quota:9s}] {turn!r} -> {got!r}")
        cases.append({"n": n, "turn": turn, "expect": got})
        states[n] = P154C.notebook_state(loops["172"])
    print(f"quotas={n_quota} allow={n_allow} other={n_other} mismatches={bad}",
          flush=True)
    if bad:
        return 1
    ART.mkdir(parents=True, exist_ok=True)
    for c in cases:
        if "turn" not in c:
            continue
        if c["n"] % 4 == 0:
            c["state"] = states[c["n"]]
    last_n = [c["n"] for c in cases if "turn" in c][-1]
    for c in reversed(cases):
        if c.get("n") == last_n:
            c["full_state"] = states[last_n]
            c["state"] = states[last_n]
            break
    (ART / "probe172b_t1c_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False, sort_keys=True)
                   for c in cases) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} lines, last_n={last_n}", flush=True)
    return 0


def main() -> int:
    rc = build_t1b()
    if rc:
        return rc
    return build_t1c()


if __name__ == "__main__":
    sys.exit(main())
