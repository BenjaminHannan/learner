#!/usr/bin/env python3
"""Exp 154b -- build the sealed T-probe cases file (PRE-SEAL characterization).

Runs the draft dialogue through fresh 154b + 138b loops, bakes expects from
observed 154b replies (each reviewed against the sealed reply forms), attaches
full taught-state snapshots on write turns + full_state on the last turn, and
asserts single-valued-block replies are string-identical across arms.

Output: artifacts/fable-multival154b-20260922/probe154b_cases.jsonl (sealed).
NOT a registered run: no PASSMARKS verdict is produced or claimed here.
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

ART = ROOT / "artifacts" / "fable-multival154b-20260922"

TURNS = [
    "Omar's sister is Priya.", "Omar's sister is Lena.", "Who is Omar's sister?",
    "Omar's friend is Ana.", "Omar's friend is Tom.", "Who is Omar's friend?",
    "Mira's brother is Sam.", "Mira's brother is Eli.", "Who is Mira's brother?",
    "Mira's child is Zoe.", "Mira's child is Max.", "Who is Mira's child?",
    "Omar's pet is Rex.", "Omar's pet is Coco.", "Who is Omar's pet?",
    "Omar's sister is Ana.", "Who is Omar's sister?",
    "Omar's brother is Gil.", "Omar's brother is Ira.", "Who is Omar's brother?",
    "Mira's pet is Pip.", "Mira's pet is Sky.", "Who is Mira's pet?",
    "Omar's boss is Ann.", "Omar's boss is Beth.", "yes", "Who is Omar's boss?",
    "Mira's mother is Eve.", "Mira's mother is Fay.", "no", "Who is Mira's mother?",
    "Omar's city is Paris.", "Omar's city is Rome.", "yes",
    "Omar's spouse is Ivy.", "Omar's spouse is May.", "no",
    "Tom's teacher is Ash.", "Tom's teacher is Bo.", "no",
    "No, Omar's sister is Ana, not Priya.", "Who is Omar's sister?",
    "No, Omar's friend is Tom, not Ana.", "Forget Omar's friend Tom.",
    "Who is Omar's friend?", "Forget Mira's brother Sam.",
    "Who is Mira's brother?", "No, Mira's child is Max, not Zoe.",
    "Forget Omar's pet Coco.", "Who is Omar's pet?",
    "Leo's sister is Amy.", "Leo's sister is Kay.",
    "Amy's boss is Ned.", "Kay's boss is Paz.", "Who is Leo's sister's boss?",
    "No, Leo's sister is Kay, not Amy.", "Who is Leo's sister?",
    "Ned's friend is Al.", "Ned's friend is Cal.", "Who is Ned's friend's boss?",
    "Paz's child is Uma.", "Paz's child is Vik.",
    "Uma's boss is Zed.", "Vik's boss is Yan.", "Who is Paz's child's boss?",
    "Ivy's brother is Cid.", "Ivy's brother is Dan.",
    "Who is Ivy's brother's teacher?",
    "Zoe's friend is Fay.", "Zoe's friend is Gus.",
    "Who is Zoe's friend's mother?",
    "Max's sister is Hal.", "Max's sister is Ida.", "Who is Max's sister's city?",
    "Tom's brother is Jay.", "Tom's brother is Ken.", "Who is Tom's brother's boss?",
    "Forget Tom's brother Jay.", "Who is Tom's brother?",
    "Eli's city is Oslo.", "Who is Mira's brother's city?",
]

# 1-indexed turns reviewed line-by-line against the sealed forms.
SINGLE_BLOCK = set(range(24, 41))  # checked standalone (fresh loops)
CLARIFY_TURNS = {55, 60, 65, 68, 71, 74, 77}  # must end with the clarify tail
TAIL = "Which one do you mean?"


def snapshot(loop) -> dict[str, list[str]]:
    nb = loop.nb
    pairs: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for fact in nb.facts.values():
        if fact.get("source") == "taught":
            seen.add((fact["subject"], fact["relation"]))
    for subject, relation in sorted(seen):
        rows = M154.taught_current154b(nb, subject, relation)
        if rows:
            pairs[f"{nb.entities[subject]}|{relation}"] = [
                M154.display154b(nb, r["value"]) for r in rows]
    return pairs


def run_all(build) -> tuple[list[str], list[dict]]:
    loop = build({"state_dir": tempfile.mkdtemp()})
    replies, snaps = [], []
    for turn in TURNS:
        replies.append(" ".join(loop.turn(turn)))
        snaps.append(snapshot(loop))
    return replies, snaps


def run_seq(build, seq) -> list[str]:
    loop = build({"state_dir": tempfile.mkdtemp()})
    return [" ".join(loop.turn(t)) for t in seq]


def main() -> int:
    got154, snaps = run_all(L154b.build_agent154b)
    got138, _ = run_all(L138b.build_agent138b)

    problems = []
    # Single-valued block: compared standalone on fresh loops, so no pending
    # change-prompt from the multi dialogue pollutes the 138b side.
    seq = TURNS[min(SINGLE_BLOCK) - 1:max(SINGLE_BLOCK)]
    solo154, solo138 = run_seq(L154b.build_agent154b, seq), run_seq(
        L138b.build_agent138b, seq)
    for k, (a, b) in enumerate(zip(solo154, solo138), min(SINGLE_BLOCK)):
        if a != b:
            problems.append(f"single n={k}: 154b={a!r} 138b={b!r}")
    for i in CLARIFY_TURNS:
        if not got154[i - 1].endswith(TAIL):
            problems.append(f"clarify n={i}: {got154[i-1]!r}")
    # No silent guesses anywhere: every ask reply is baked, reviewed below.
    if problems:
        print("CHARACTERIZATION MISMATCH (fix code, do not seal):")
        print("\n".join(problems))
        return 1

    print("All predicts hold: single-block identical (17/17), clarifies 7/7.")
    for i, (t, r) in enumerate(zip(TURNS, got154), 1):
        print(f"{i:02d} {t!r} => {r!r}")

    out = []
    for i, (t, r, s) in enumerate(zip(TURNS, got154, snaps), 1):
        case = {"n": i, "turn": t, "expect": r}
        if s != (snaps[i - 2] if i > 1 else {}):
            case["state"] = s  # state changed on this turn: pin the full map
        if i == len(TURNS):
            case["full_state"] = s
        out.append(case)
    (ART / "probe154b_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False, sort_keys=True)
                  for c in out) + "\n", encoding="utf-8")
    print(f"wrote {ART / 'probe154b_cases.jsonl'} ({len(out)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
