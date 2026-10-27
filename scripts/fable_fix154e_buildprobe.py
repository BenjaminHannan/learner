#!/usr/bin/env python3
"""Experiment 154e -- OPEN pre-seal helper (NOT sealed, NOT registered).

Builds the L1 case file turns (quota layout below) and fills "expect"
replies from a live Loop154e pilot run, ASSERTING each reply equals the
hand-predicted sealed form first. Any assertion failure stops the build
for human review. Run:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix154e_buildprobe.py
Output: artifacts/fable-lang154e-20260922/case154e.jsonl
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

import fable_loop154e_agent as L154e  # noqa: E402 (pilot only, pre-seal)

ART = ROOT / "artifacts" / "fable-lang154e-20260922"

# (turn, predicted reply or None, state-check or None)
SEG1: list = []  # 8 x two-language: teach, teach, ask
for person, v1, v2 in [
        ("Rana", "Hindi", "Urdu"), ("Mira", "Spanish", "French"),
        ("Kiran", "Tamil", "Telugu"), ("Dev", "Marathi", "Gujarati"),
        ("Asha", "Bengali", "Punjabi"), ("Ravi", "Kannada", "Malayalam"),
        ("Sana", "Assamese", "Odia"), ("Tara", "Sanskrit", "Maithili")]:
    SEG1 += [
        (f"{person}'s language is {v1}.",
         f"Saved: {person}'s language is {v1}.", None),
        (f"{person}'s language is {v2}.",
         f"Saved: {person}'s language is {v2}. (I also have {v1}.)", None),
        (f"What is {person}'s language?",
         f"{person}'s language is {v1} and {v2}.",
         {f"{person}|language": [v1, v2]}),
    ]

SEG2: list = []  # 4 x three-language: teach x3, ask
for person, v1, v2, v3 in [
        ("Noor", "Hindi", "Urdu", "Bengali"),
        ("Kabir", "Tamil", "Kannada", "Malayalam"),
        ("Lata", "Spanish", "French", "German"),
        ("Omar", "Arabic", "Persian", "Turkish")]:
    SEG2 += [
        (f"{person}'s language is {v1}.",
         f"Saved: {person}'s language is {v1}.", None),
        (f"{person}'s language is {v2}.",
         f"Saved: {person}'s language is {v2}. (I also have {v1}.)", None),
        (f"{person}'s language is {v3}.",
         f"Saved: {person}'s language is {v3}. "
         f"(I also have {v1} and {v2}.)", None),
        (f"What is {person}'s language?",
         f"{person}'s language is {v1}, {v2} and {v3}.",
         {f"{person}|language": [v1, v2, v3]}),
    ]

SEG3: list = [  # 4 removals: correct-not x2 + forget-one x2, each + ask
    ("Rana's language is Hindi.", "Saved: Rana's language is Hindi.", None),
    ("Rana's language is Urdu.",
     "Saved: Rana's language is Urdu. (I also have Hindi.)", None),
    ("Rana's language is Bengali.",
     "Saved: Rana's language is Bengali. (I also have Hindi and Urdu.)",
     None),
    ("No, Rana's language is Tamil, not Hindi.",
     "Saved: Rana's language is Tamil. (I also have Urdu and Bengali.)",
     None),
    ("What is Rana's language?",
     "Rana's language is Urdu, Bengali and Tamil.",
     {"Rana|language": ["Urdu", "Bengali", "Tamil"]}),
    ("Forget Rana's language Urdu.", "Forgotten: Rana's language Urdu.",
     None),
    ("What is Rana's language?", "Rana's language is Bengali and Tamil.",
     {"Rana|language": ["Bengali", "Tamil"]}),
    ("Mira's language is Spanish.", "Saved: Mira's language is Spanish.",
     None),
    ("Mira's language is French.",
     "Saved: Mira's language is French. (I also have Spanish.)", None),
    ("No, Mira's language is German, not Spanish.",
     "Saved: Mira's language is German. (I also have French.)", None),
    ("What is Mira's language?", "Mira's language is French and German.",
     {"Mira|language": ["French", "German"]}),
    ("Forget Mira's language French.", "Forgotten: Mira's language French.",
     None),
    ("What is Mira's language?", "Mira's language is German.",
     {"Mira|language": ["German"]}),
]

SEG4: list = [  # 3 repeats: no duplicate write
    ("Dev's language is Hindi.", "Saved: Dev's language is Hindi.", None),
    ("Dev's language is Urdu.",
     "Saved: Dev's language is Urdu. (I also have Hindi.)", None),
    ("Dev's language is Urdu.", "I already have that.", None),
    ("What is Dev's language?", "Dev's language is Hindi and Urdu.",
     {"Dev|language": ["Hindi", "Urdu"]}),
    ("Asha's language is Tamil.", "Saved: Asha's language is Tamil.", None),
    ("Asha's language is Tamil.", "I already have that.", None),
    ("What is Asha's language?", "Asha's language is Tamil.",
     {"Asha|language": ["Tamil"]}),
    ("Ravi's language is Spanish.", "Saved: Ravi's language is Spanish.",
     None),
    ("Ravi's language is French.",
     "Saved: Ravi's language is French. (I also have Spanish.)", None),
    ("Ravi's language is Spanish.", "I already have that.", None),
    ("What is Ravi's language?", "Ravi's language is Spanish and French.",
     {"Ravi|language": ["Spanish", "French"]}),
]

SEG5: list = [  # 12 traps: citizenship / city / boss stay single; unknown asks
    ("Rana's citizenship is India.", "Saved: Rana's citizenship is India.",
     None),
    ("Rana's citizenship is Nepal.",
     "I have Rana's citizenship as India. Do you want me to change it "
     "to Nepal?", None),
    ("no.", "Okay, I left it as it was.", None),
    ("Who is Rana's citizenship?", "Rana's citizenship is India.",
     {"Rana|citizenship": ["India"]}),
    ("Ana's city is Rome.", "Saved: Ana's city is Rome.", None),
    ("Ana's city is Madrid.",
     "I have Ana's city as Rome. Do you want me to change it to Madrid?",
     None),
    ("no.", "Okay, I left it as it was.", None),
    ("Ana's boss is Zed.", "Saved: Ana's boss is Zed.", None),
    ("Ana's boss is Yan.",
     "I have Ana's boss as Zed. Do you want me to change it to Yan?",
     None),
    ("no.", "Okay, I left it as it was.",
     {"Ana|boss": ["Zed"], "Ana|city": ["Rome"]}),
    ("What is Zed's language?", "I don't know Zed's language.", None),
    ("Who is Zed's citizenship?", "I don't know Zed's citizenship.", None),
]


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    base = tempfile.mkdtemp(prefix="build154e_")
    out_lines: list[str] = []
    n = 0
    seg_no = 0
    for seg in (SEG1, SEG2, SEG3, SEG4, SEG5):
        seg_no += 1
        loop = L154e.build_agent154e(
            {"state_dir": str(Path(base) / f"seg{seg_no}")})
        loop_c = None
        out_lines.append(json.dumps({"reset": True}, sort_keys=True))
        for turn, predicted, state in seg:
            n += 1
            said = " ".join(loop.turn(turn))
            if predicted is not None and said != predicted:
                print(f"BUILD STOP n={n} turn={turn!r}\n  pilot {said!r}\n"
                      f"  predicted {predicted!r}", flush=True)
                return 1
            row: dict = {"n": n, "turn": turn, "expect": said}
            if state is not None:
                row["state"] = state
            out_lines.append(json.dumps(row, ensure_ascii=False,
                                        sort_keys=True))
        # full_state at segment end
        import fable_fix154b_multival as M154
        pairs: dict[str, list[str]] = {}
        seen: set[tuple[str, str]] = set()
        for fact in loop.nb.facts.values():
            if fact.get("source") != "taught":
                continue
            seen.add((fact["subject"], fact["relation"]))
        for subject, relation in sorted(seen):
            rows = M154.taught_current154b(loop.nb, subject, relation)
            if rows:
                pairs[f"{loop.nb.entities[subject]}|{relation}"] = [
                    M154.display154b(loop.nb, r["value"]) for r in rows]
        last = json.loads(out_lines[-1])
        last["full_state"] = pairs
        out_lines[-1] = json.dumps(last, ensure_ascii=False, sort_keys=True)
    (ART / "case154e.jsonl").write_text("\n".join(out_lines) + "\n",
                                        encoding="utf-8")
    print(f"wrote case154e.jsonl: {n} turns in 5 segments; "
          f"all {n} pilot replies matched hand predictions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
