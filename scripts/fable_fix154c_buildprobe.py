#!/usr/bin/env python3
"""Experiment 154c -- T1b probe BUILDER (open, pre-seal only).

Runs a fixed ordered turn list through THREE fresh loops (138b, 154b,
154c), asserts the 154c contract (deny turns byte-identical to loop138b,
allow/two-hop turns byte-identical to loop154b), and writes the sealed
case file artifacts/fable-multival154c-20260922/probe154c_cases.jsonl
with expects + state maps + final full_state.

NOT a registered run: its output is reviewed, then sealed. The registered
T1b run replays the sealed file through a fresh 154c loop.
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

import fable_fix154b_multival as M154  # noqa: E402
import fable_loop138b_agent as L138b  # noqa: E402
import fable_loop154b_agent as L154b  # noqa: E402
import fable_loop154c_agent as L154c  # noqa: E402

ART = ROOT / "artifacts" / "fable-multival154c-20260922"

# (turn, arm) arm: deny -> expect loop138b reply; allow -> loop154b reply.
# {"reset": True} starts a fresh loop in every arm (segments isolate the
# yes/no pending state, which legitimately evolves per-arm once behaviours
# differ; each segment is pending-clean on its own).
TURNS: list[tuple | dict] = [
    {"reset": True},
    # -- deny re-teach/edits (multi-word + copula included) --
    ("Omar's citizenship is Spain.", "deny"),
    ("Omar's citizenship is Portugal.", "deny"),
    ("no.", "deny"),
    ("Who is Omar's citizenship?", "deny"),
    ("Lionel Messi is a citizen of Argentina.", "deny"),
    ("Lionel Messi is a citizen of Portugal.", "deny"),
    ("Who is Lionel Messi's citizenship?", "deny"),
    ("Mira's language is Spanish.", "deny"),
    ("Mira's language is French.", "deny"),
    ("no.", "deny"),
    ("Who is Mira's language?", "deny"),
    ("Tom's occupation is Mason.", "deny"),
    ("Tom's occupation is Baker.", "deny"),
    ("no.", "deny"),
    ("Who is Tom's occupation?", "deny"),
    ("Ann's employer is Initech.", "deny"),
    ("Ann's employer is Hooli.", "deny"),
    ("no.", "deny"),
    ("Dan's team is Reno.", "deny"),
    ("Dan's team is Vega.", "deny"),
    ("no.", "deny"),
    ("Who is Dan's team?", "deny"),
    ("Lea's country is Chile.", "deny"),
    ("Lea's country is Peru.", "deny"),
    ("no.", "deny"),
    ("No, Omar's citizenship is Portugal, not Spain.", "deny"),
    ("Forget Tom's occupation Baker.", "deny"),
    ("Who is Tom's occupation?", "deny"),
    {"reset": True},
    # -- allow add-second-value (12 relations x teach/teach/ask) --
    ("Kim's sister is Ana.", "allow"),
    ("Kim's sister is Bea.", "allow"),
    ("Who is Kim's sister?", "allow"),
    ("Hal's brother is Cid.", "allow"),
    ("Hal's brother is Dan.", "allow"),
    ("Who is Hal's brother?", "allow"),
    ("Ivy's sibling is Eve.", "allow"),
    ("Ivy's sibling is Fay.", "allow"),
    ("Who is Ivy's sibling?", "allow"),
    ("Al's friend is Cal.", "allow"),
    ("Al's friend is Gus.", "allow"),
    ("Who is Al's friend?", "allow"),
    ("Paz's child is Uma.", "allow"),
    ("Paz's child is Vik.", "allow"),
    ("Who is Paz's child?", "allow"),
    ("Rex's son is Max.", "allow"),
    ("Rex's son is Noa.", "allow"),
    ("Who is Rex's son?", "allow"),
    ("Zoe's daughter is Mia.", "allow"),
    ("Zoe's daughter is Nia.", "allow"),
    ("Who is Zoe's daughter?", "allow"),
    ("Sam's pet is Pip.", "allow"),
    ("Sam's pet is Sky.", "allow"),
    ("Who is Sam's pet?", "allow"),
    ("Ned's dog is Rex.", "allow"),
    ("Ned's dog is Fido.", "allow"),
    ("Who is Ned's dog?", "allow"),
    ("Eli's cat is Tom.", "allow"),
    ("Eli's cat is Kit.", "allow"),
    ("Who is Eli's cat?", "allow"),
    ("Ava's cousin is Leo.", "allow"),
    ("Ava's cousin is Mia.", "allow"),
    ("Who is Ava's cousin?", "allow"),
    ("Gibson's notable work is Neuromancer.", "allow"),
    ("Gibson's notable work is Pattern.", "allow"),
    ("Who is Gibson's notable work?", "allow"),
    {"reset": True},
    # -- two-hop clarifies through 2-valued allow hops --
    ("Kim's sister is Ana.", "allow"),
    ("Kim's sister is Bea.", "allow"),
    ("Hal's brother is Cid.", "allow"),
    ("Hal's brother is Dan.", "allow"),
    ("Al's friend is Cal.", "allow"),
    ("Al's friend is Gus.", "allow"),
    ("Ana's city is Rome.", "allow"),
    ("Bea's city is Madrid.", "allow"),
    ("Who is Kim's sister's city?", "allow"),
    ("Cid's city is Oslo.", "allow"),
    ("Dan's city is Quito.", "allow"),
    ("Who is Hal's brother's city?", "allow"),
    ("Cal's city is Lima.", "allow"),
    ("Gus's city is Nice.", "allow"),
    ("Who is Al's friend's city?", "allow"),
    ("Ana's boss is Zed.", "allow"),
    ("Who is Kim's sister's boss?", "allow"),
    ("Cid's boss is Yan.", "allow"),
    ("Who is Hal's brother's boss?", "allow"),
]


def fresh(kind: str):
    tmp = tempfile.mkdtemp(prefix=f"build154c_{kind}_")
    if kind == "138b":
        return L138b.build_agent138b({"state_dir": tmp})
    if kind == "154b":
        return L154b.build_agent154b({"state_dir": tmp})
    return L154c.build_agent154c({"state_dir": tmp})


def notebook_state(loop) -> dict[str, list[str]]:
    nb = loop.nb
    pairs: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for fact in nb.facts.values():
        if fact.get("source") != "taught":
            continue
        seen.add((fact["subject"], fact["relation"]))
    for subject, relation in sorted(seen):
        rows = M154.taught_current154b(nb, subject, relation)
        if rows:
            key = f"{nb.entities[subject]}|{relation}"
            pairs[key] = [M154.display154b(nb, r["value"]) for r in rows]
    return pairs


def main() -> int:
    loops = {k: fresh(k) for k in ("138b", "154b", "154c")}
    n_deny = n_allow = bad = n = 0
    cases: list[dict] = []
    states: dict[int, dict] = {}
    for entry in TURNS:
        if isinstance(entry, dict):
            for k in loops:
                loops[k] = fresh(k)
            cases.append({"reset": True})
            print("-- reset --")
            continue
        turn, arm = entry
        n += 1
        reps = {k: " ".join(loops[k].turn(turn)) for k in loops}
        ref = reps["138b"] if arm == "deny" else reps["154b"]
        got = reps["154c"]
        n_deny += arm == "deny"
        n_allow += arm == "allow"
        if got != ref:
            bad += 1
            print(f"MISMATCH n={n} arm={arm} turn={turn!r}\n"
                  f"  154c {got!r}\n  ref  {ref!r}", flush=True)
        print(f"[{arm:5s}] {turn!r} -> {got!r}")
        cases.append({"n": n, "turn": turn, "expect": got})
        states[n] = notebook_state(loops["154c"])
    print(f"deny={n_deny} allow={n_allow} mismatches={bad}", flush=True)
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
    (ART / "probe154c_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False, sort_keys=True)
                  for c in cases) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} lines", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
