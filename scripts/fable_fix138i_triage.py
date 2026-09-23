#!/usr/bin/env python3
"""Exp 138i pilot triage -- for each M1 diff case, run the same turns on
fresh loop138h and fresh loop138i; report whether 138i == 138h (lineage
interaction, listed) or 138i != 138h (new move, must be predicted).

Pilot-only helper (outputs to scratch, never artifacts/).
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138h_agent as L138H  # noqa: E402
import fable_loop138i_agent as L138I  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

ROOT = SCRIPTS.parent


def fresh(mod, cfg0):
    d = tempfile.mkdtemp(prefix="triage-")
    cfg = copy.deepcopy(cfg0)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return mod(cfg)


def run_seq(mod, cfg0, turns):
    loop = fresh(mod, cfg0)
    out = [" ".join(loop.turn(t)) for t in turns]
    return out, [list(t) for t in L90.notebook_triples(loop.nb)]


def main() -> int:
    H, I = L138H.build_agent138h, L138I.build_agent138i
    CH, CI = L138H.DEFAULT_CONFIG138H, L138I.DEFAULT_CONFIG138I
    jobs: list[tuple[str, list[str]]] = []
    cases166 = json.loads((ROOT / "artifacts" / "fable-me166-20260922"
                           / "cases166.json").read_text(encoding="utf-8"))
    want_ids = {"F12", "F14", "F20", "A01", "A02", "A03", "A04", "A05",
                "A06", "A07", "A08", "A09", "A10", "O08", "O09", "O10",
                "O12", "O14", "O15", "O16"}
    by_id = {r["id"]: r for r in cases166}
    for cid in sorted(want_ids):
        r = by_id[cid]
        turns = list(r.get("teaches", [])) + [a["q"]
                                              for a in r.get("asks", [])]
        jobs.append((f"166-{cid}", turns))
    cases173b = json.loads((ROOT / "artifacts" / "fable-username173b-20260922"
                            / "cases173b.json").read_text(encoding="utf-8"))
    for r in cases173b:
        if r["id"] in {"C01", "C02", "C03", "C04", "C05", "C06", "C07",
                       "C08", "C09", "C10", "C11", "C12", "C13", "C14",
                       "O01", "O05"}:
            jobs.append((f"173b-{r['id']}", list(r["steps"])))
    jobs += [
        ("171b-D12", ["Elsa's brother is Really nice.",
                      "Who is Elsa's brother?"]),
        ("171b-C02", ["Kim's dog is Bruno.", "No, Kim's dog is Chen.",
                      "Who is Kim's dog?"]),
        ("167e-n32", [json.loads((ROOT / "artifacts"
                                  / "fable-label167e-20260922"
                                  / "cases167e.json").read_text(
                                      encoding="utf-8"))["turns"][32]["t"]]),
        ("174-n35", ["The city of Lumen is Brack."]),
        ("172b-lang", ["Mira's language is Spanish.",
                       "Mira's language is French.", "no.",
                       "Who is Mira's language?"]),
        ("g3f", ["Kim's boss is Lee.",
                 "No, Kim's boss is Sam, not Lee."]),
        ("g3b", ["Bela's sister is Zuri.", "Is Zuri Bela's sister?"]),
    ]
    for jid, turns in jobs:
        rh, wh = run_seq(H, CH, turns)
        ri, wi = run_seq(I, CI, turns)
        same = (rh == ri and wh == wi)
        print(f"{jid}: {'SAME-AS-138H' if same else '138I-MOVES'}")
        if not same:
            for t, a, b in zip(turns, rh, ri):
                if a != b:
                    print(f"    turn={t!r}\n      138h={a!r}\n      138i={b!r}")
            if wh != wi:
                print(f"    stored138h={wh}")
                print(f"    stored138i={wi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
