#!/usr/bin/env python3
"""Experiment 154f -- OPEN pre-seal helper (NOT sealed, NOT registered).

Builds the N1 case file. "new" rows assert a live Loop154f pilot reply
equals the hand-predicted sealed form; "trap" rows capture the live
Loop154e reply as the expect (byte-identical bar) and assert Loop154f
says the same. Any assertion failure stops the build for human review.

Run:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix154f_buildprobe.py
Output: artifacts/fable-negate154f-20260922/case154f.jsonl
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

import fable_fix154b_multival as M154  # noqa: E402 (state readers)
import fable_loop154e_agent as L154e  # noqa: E402 (base pilot, pre-seal)
import fable_loop154f_agent as L154f  # noqa: E402 (pilot only, pre-seal)

ART = ROOT / "artifacts" / "fable-negate154f-20260922"

# (turn, mode, predicted-or-None, writes, state)
# mode "new": predicted is the hand-sealed reply. mode "trap": predicted
# is None and the expect is captured from live loop154e.
# writes "w": >=1 new notebook event; "0": exactly 0 new events.
SEG_A = [  # Rana: 3 languages, 2 plain-negation removals + asks
    ("Rana's language is Hindi.", "new",
     "Saved: Rana's language is Hindi.", "w", None),
    ("Rana's language is Urdu.", "new",
     "Saved: Rana's language is Urdu. (I also have Hindi.)", "w", None),
    ("Rana's language is Bengali.", "new",
     "Saved: Rana's language is Bengali. (I also have Hindi and Urdu.)",
     "w", None),
    ("Rana's language is not Hindi.", "new",
     "OK, Rana's language is not Hindi. I still have Urdu and Bengali.",
     "w", None),
    ("What is Rana's language?", "new",
     "Rana's language is Urdu and Bengali.", "0",
     {"Rana|language": ["Urdu", "Bengali"]}),
    ("Rana's language isn't Urdu.", "new",
     "OK, Rana's language is not Urdu. I still have Bengali.", "w", None),
    ("What is Rana's language?", "new",
     "Rana's language is Bengali.", "0",
     {"Rana|language": ["Bengali"]}),
]

SEG_B = [  # Mira pair, 1 removal
    ("Mira's language is Spanish.", "new",
     "Saved: Mira's language is Spanish.", "w", None),
    ("Mira's language is French.", "new",
     "Saved: Mira's language is French. (I also have Spanish.)", "w", None),
    ("Mira's language is not Spanish.", "new",
     "OK, Mira's language is not Spanish. I still have French.", "w", None),
    ("What is Mira's language?", "new",
     "Mira's language is French.", "0",
     {"Mira|language": ["French"]}),
]

SEG_C = [  # Noor pair, 1 removal (isn't form)
    ("Noor's language is Hindi.", "new",
     "Saved: Noor's language is Hindi.", "w", None),
    ("Noor's language is Urdu.", "new",
     "Saved: Noor's language is Urdu. (I also have Hindi.)", "w", None),
    ("Noor's language isn't Urdu.", "new",
     "OK, Noor's language is not Urdu. I still have Hindi.", "w", None),
    ("What is Noor's language?", "new",
     "Noor's language is Hindi.", "0",
     {"Noor|language": ["Hindi"]}),
]

SEG_D = [  # Kabir pair, 1 removal
    ("Kabir's language is Tamil.", "new",
     "Saved: Kabir's language is Tamil.", "w", None),
    ("Kabir's language is Kannada.", "new",
     "Saved: Kabir's language is Kannada. (I also have Tamil.)", "w",
     None),
    ("Kabir's language is not Tamil.", "new",
     "OK, Kabir's language is not Tamil. I still have Kannada.", "w", None),
    ("What is Kabir's language?", "new",
     "Kabir's language is Kannada.", "0",
     {"Kabir|language": ["Kannada"]}),
]

SEG_E = [  # Lata pair, 1 removal
    ("Lata's language is Spanish.", "new",
     "Saved: Lata's language is Spanish.", "w", None),
    ("Lata's language is French.", "new",
     "Saved: Lata's language is French. (I also have Spanish.)", "w", None),
    ("Lata's language is not French.", "new",
     "OK, Lata's language is not French. I still have Spanish.", "w", None),
    ("What is Lata's language?", "new",
     "Lata's language is Spanish.", "0",
     {"Lata|language": ["Spanish"]}),
]

SEG_F = [  # Omar pair, 1 removal
    ("Omar's language is Arabic.", "new",
     "Saved: Omar's language is Arabic.", "w", None),
    ("Omar's language is Persian.", "new",
     "Saved: Omar's language is Persian. (I also have Arabic.)", "w", None),
    ("Omar's language is not Arabic.", "new",
     "OK, Omar's language is not Arabic. I still have Persian.", "w", None),
    ("What is Omar's language?", "new",
     "Omar's language is Persian.", "0",
     {"Omar|language": ["Persian"]}),
]

SEG_G = [  # Asha pair, 1 removal (8th multi-valued removal)
    ("Asha's language is Bengali.", "new",
     "Saved: Asha's language is Bengali.", "w", None),
    ("Asha's language is Punjabi.", "new",
     "Saved: Asha's language is Punjabi. (I also have Bengali.)", "w",
     None),
    ("Asha's language is not Bengali.", "new",
     "OK, Asha's language is not Bengali. I still have Punjabi.", "w",
     None),
    ("What is Asha's language?", "new",
     "Asha's language is Punjabi.", "0",
     {"Asha|language": ["Punjabi"]}),
]

SEG_H = []  # 6 single-valued removals: teach, negate, ask-don't-know
for person, rel, val in [
        ("Kim", "boss", "Lee"), ("Ana", "city", "Rome"),
        ("Raj", "citizenship", "India"), ("Eli", "teacher", "Moss"),
        ("Max", "mother", "Lisa"), ("Zoe", "father", "Mark")]:
    SEG_H += [
        (f"{person}'s {rel} is {val}.", "new",
         f"Saved: {person}'s {rel} is {val}.", "w", None),
        (f"{person}'s {rel} is not {val}.", "new",
         f"OK, {person}'s {rel} is not {val}. "
         f"I don't have another {rel} for {person}.", "w", None),
        (f"What is {person}'s {rel}?", "new",
         f"I don't know {person}'s {rel}.", "0",
         {f"{person}|{rel}": []}),
    ]

SEG_I = [  # 6 not-a-current-value: 0 writes, fixed miss reply
    ("Rana's language is Hindi.", "new",
     "Saved: Rana's language is Hindi.", "w", None),
    ("Rana's language is Urdu.", "new",
     "Saved: Rana's language is Urdu. (I also have Hindi.)", "w", None),
    ("Rana's language is not Tamil.", "new",
     "I don't have Tamil as Rana's language.", "0", None),
    ("What is Rana's language?", "new",
     "Rana's language is Hindi and Urdu.", "0",
     {"Rana|language": ["Hindi", "Urdu"]}),
    ("Kim's boss is Lee.", "new",
     "Saved: Kim's boss is Lee.", "w", None),
    ("Kim's boss is not Yan.", "new",
     "I don't have Yan as Kim's boss.", "0", None),
    ("What is Kim's boss?", "new", "Kim's boss is Lee.", "0",
     {"Kim|boss": ["Lee"]}),
    ("Ana's city is Paris.", "new",
     "Saved: Ana's city is Paris.", "w", None),
    ("Ana's city is not Rome.", "new",
     "I don't have Rome as Ana's city.", "0", None),
    ("Raj's citizenship is India.", "new",
     "Saved: Raj's citizenship is India.", "w", None),
    ("Raj's citizenship is not Nepal.", "new",
     "I don't have Nepal as Raj's citizenship.", "0", None),
    ("Eli's teacher is Ann.", "new",
     "Saved: Eli's teacher is Ann.", "w", None),
    ("Eli's teacher is not Moss.", "new",
     "I don't have Moss as Eli's teacher.", "0", None),
    ("Max's mother is June.", "new",
     "Saved: Max's mother is June.", "w", None),
    ("Max's mother is not Lisa.", "new",
     "I don't have Lisa as Max's mother.", "0", None),
    ("Zoe's father is Paul.", "new",
     "Saved: Zoe's father is Paul.", "w", None),
    ("Zoe's father is not Mark.", "new",
     "I don't have Mark as Zoe's father.", "0", None),
]

SEG_J = [  # 4 unknown names: base reply, 0 writes
    ("Zed's language is not Hindi.", "trap", None, "0", None),
    ("Zed's boss is not Lee.", "trap", None, "0", None),
    ("Vex's city is not Rome.", "trap", None, "0", None),
    ("Quin's citizenship is not India.", "trap", None, "0", None),
]

SEG_K = [  # 14 traps: loop154e replies + events byte-identical
    ("Rana's language is Hindi.", "trap", None, "w", None),
    ("Rana's language is Urdu.", "trap", None, "w", None),
    ("No, Rana's language is Tamil, not Hindi.", "trap", None, "w", None),
    ("What is Rana's language?", "trap", None, "0",
     {"Rana|language": ["Urdu", "Tamil"]}),
    ("Forget Rana's language Urdu.", "trap", None, "w", None),
    ("What is Rana's language?", "trap", None, "0",
     {"Rana|language": ["Tamil"]}),
    ("Say Rana's language is not Tamil.", "trap", None, "0", None),
    ("Is Rana's language not Tamil?", "trap", None, "0", None),
    ("Kim's boss is Lee.", "trap", None, "w", None),
    ("The city of Kim's boss is not Oslo.", "trap", None, "0", None),
    ("Kim's boss's city is not Oslo.", "trap", None, "0", None),
    ("Rana's sister is not Kim's boss.", "trap", None, "0", None),
    ("Nott's boss is Lee.", "trap", None, "w", None),
    ("Rana's city is Knot.", "trap", None, "w", None),
]

SEG_L = [  # single-valued change-prompt untouched + pretend traps
    ("Rana's citizenship is India.", "trap", None, "w", None),
    ("Rana's citizenship is Nepal.", "trap", None, "0", None),
    ("no.", "trap", None, "0",
     {"Rana|citizenship": ["India"]}),
    ("Pretend Rana's boss is not Lee.", "trap", None, "0", None),
    ("Please say Kim's city is not Rome.", "trap", None, "0", None),
    ("Rana's language is not Hindi.", "new",
     "I don't have Hindi as Rana's language.", "0", None),
]


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
        key = f"{nb.entities[subject]}|{relation}"
        vals = [M154.display154b(nb, r["value"]) for r in rows]
        if vals:
            pairs[key] = vals
        elif key.split("|")[0] in ("Kim", "Ana", "Raj", "Eli", "Max", "Zoe"):
            pairs[key] = []
    return pairs


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    base = tempfile.mkdtemp(prefix="build154f_")
    out_lines: list[str] = []
    n = 0
    seg_no = 0
    for seg in (SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G, SEG_H,
                SEG_I, SEG_J, SEG_K, SEG_L):
        seg_no += 1
        kw = {"state_dir": str(Path(base) / f"seg{seg_no}")}
        loop_f = L154f.build_agent154f(dict(kw))
        loop_e = L154e.build_agent154e(dict(kw,
                                            state_dir=str(Path(base) /
                                                          f"seg{seg_no}e")))
        loop_e_c = None
        out_lines.append(json.dumps({"reset": True}, sort_keys=True))
        for turn, mode, predicted, writes, state in seg:
            n += 1
            eb, fb = len(loop_f.nb.events), set(loop_f.nb.facts)
            said_f = " ".join(loop_f.turn(turn))
            nev_f = len(loop_f.nb.events) - eb
            if mode == "new":
                if said_f != predicted:
                    print(f"BUILD STOP n={n} turn={turn!r}\n"
                          f"  pilot {said_f!r}\n  predicted {predicted!r}",
                          flush=True)
                    return 1
                expect = predicted
            else:
                ee = len(loop_e.nb.events)
                said_e = " ".join(loop_e.turn(turn))
                if said_f != said_e:
                    print(f"TRAP DIVERGENCE n={n} turn={turn!r}\n"
                          f"  154f {said_f!r}\n  154e {said_e!r}",
                          flush=True)
                    return 1
                nev_e = len(loop_e.nb.events) - ee
                if (nev_f > 0) != (nev_e > 0):
                    print(f"WRITE DIVERGENCE n={n} turn={turn!r}\n"
                          f"  154f +{nev_f} events, 154e +{nev_e}",
                          flush=True)
                    return 1
                expect = said_e
            if writes == "0" and nev_f != 0:
                print(f"WRITE STOP n={n} turn={turn!r}: +{nev_f} events, "
                      f"wanted 0", flush=True)
                return 1
            if writes == "w" and nev_f < 1:
                print(f"WRITE STOP n={n} turn={turn!r}: +{nev_f} events, "
                      f"wanted >=1", flush=True)
                return 1
            row: dict = {"n": n, "turn": turn, "expect": expect,
                         "writes": writes}
            if state is not None:
                got = notebook_state(loop_f)
                for pair, want in state.items():
                    if got.get(pair, []) != list(want):
                        print(f"STATE STOP n={n} turn={turn!r}\n"
                              f"  got {got}\n  want {pair}={want}",
                              flush=True)
                        return 1
                row["state"] = state
            out_lines.append(json.dumps(row, ensure_ascii=False,
                                        sort_keys=True))
        last = json.loads(out_lines[-1])
        last["full_state"] = notebook_state(loop_f)
        out_lines[-1] = json.dumps(last, ensure_ascii=False, sort_keys=True)
    (ART / "case154f.jsonl").write_text("\n".join(out_lines) + "\n",
                                        encoding="utf-8")
    print(f"wrote case154f.jsonl: {n} turns in 12 segments; all new "
          f"replies matched hand predictions, all traps equal live 154e")
    return 0


if __name__ == "__main__":
    sys.exit(main())
