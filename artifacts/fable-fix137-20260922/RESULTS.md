# RESULTS — Experiment 137 (multi-word possessive subjects, Muse)

One change on loop129b: the possessive teach frame accepts 2–4 capitalised
name tokens (hyphens/apostrophes inside tokens, exp-129 abbreviation rule).
Delivered as stackable `Fix137PossessiveMixin` (scripts/fable_fix137_names.py)
+ thin `loop137 = loop129b + mixin` wrapper (scripts/fable_loop137_agent.py,
--daemon entry). No existing file edited or committed.

## Marks (registered bars from sealed PASSMARKS.md, seal 64f55430…)

| mark | bar | number | verdict |
|---|---|---|---|
| N1 store | >= 38/42 stored exactly | 42/42 stored exactly (subject, relation, value) | PASS |
| N1 answer | >= 38/42 answered | 42/42 answered with taught value | PASS |
| N1 wrong writes | 0 | 0 | PASS |
| N1 overall | all three | 42/42 + 42/42 + 0 | PASS |
| N2 traps | 0 wrong writes / 18 | 4 writes / 18 (T09, T11, T14, T17) | FAIL |
| N3a marks123 | every suite verdict identical 137 vs 129b | 10/10 suite rows identical (bar+number+status); p2/rt110/rt81/bench per-case verdicts identical; sleep SKIP both (reason differs only by agent filename) | PASS |
| N3b bench | per-item identical, 3 splits | 600/600 rows identical (edit200 150/50/0, old 157/43/0, new 136/63/1 — same as sealed exp-129 calibration) | PASS |
| N4 time | whole wave < 25 min Mac CPU | probe 1.4 s + bench 45.1 s + marks137 169.4 s + marks129b 135.9 s ≈ 5.9 min | PASS |

SCORE: N1 PASS, N2 registered FAIL, N3a PASS, N3b PASS, N4 PASS.

## N2 diagnosis (why FAIL, and what each write is)

- T09 "The city of Dara Fenn is Lyon." → Saved via bench73 officeholder
  catch-all. Base loop129b writes it byte-identically (verified). Inherited.
- T14 "123's city is Lyon." → Saved via the untouched ONE-WORD path
  (FakeEars has no case/digit check). Base writes it identically. Inherited.
- T11 "Dara Fenn's city is Dara Fenn's town." → Saved by the mixin. The
  frame's value rule refuses only possessive+copula ("X's w is") in the
  value; the single-word twin "Mira's city is Mira's town." Saves on both
  loops (verified). Consistent extension, but my sealed trap expected
  clarify — trap-expectation error.
- T17 "Ana Beatriz Cruz Vale's city is Rome." → Saved by the mixin, and
  correctly so: "'s"-split gives 4 Title-case tokens ("Vale"), inside the
  1–4 cap. My trap label said "five-token" — counting error.
- Zero cases of wrong subject split, value junk, or relation swap in any arm.

## Question side

Needed no change. FakeEars' question branch never had the one-word guard;
the mixin returns the base result untouched on every "?" turn. Evidence:
42/42 N1 questions answered after the teach.

## Deviations

1. Diagnostic base-vs-137 rerun of the 4 N2 writers (+ single-word twin)
   after the registered probe, to attribute inheritance. Report-only; sealed
   files untouched; N2 stays FAIL.
2. PASSMARKS N4 assumed the whole wave; reported per-phase timings instead
   of a single clock (sum ≈ 5.9 min, each phase timed).

## Questions for Ben

None. Default stands: ALL-CAPS tokens ("DARA") are refused (not Title-case);
"child" possessives keep using the loop121 extra-pattern path.

## Reproduce (Mac CPU, offline, after seal 64f55430…)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix137_probe.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix137_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop137_agent.py --config artifacts/fable-fix137-20260922/loop137-config.json --out artifacts/fable-fix137-20260922/marks123-137 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop129b_agent.py --config artifacts/fable-fix129-20260922/loop129b-config.json --out artifacts/fable-fix137-20260922/marks123-base --workers 4

## What it means

Full names now teach through the possessive frame with zero regressions.

## What it does not mean

The trap suite is not clean: two inherited oddities (officeholder
catch-all, digit names) and two accepted edge writes remain on the record.
