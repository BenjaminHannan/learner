# Exp 144 RESULTS — multi-"of" names are one fact (loop129b + of-name mixin)

The bug is fixed where it mattered (bench132-022 now answers Charleroi),
but the sealed F1 probe is a FAIL: it caught one pre-existing wrong write
that loop129b makes too (diagnosis below). No silent re-runs: F1 ran twice
(before/after a one-line daemon boot fix) with the identical signature.

## What was done

Step 1 (before sealing): the "split that" reply is
`scripts/fable_earsguard91.py:34` (SPLIT_MSG) via `screen_value()` at
`fable_earsguard91.py:53-60`. "The Protocols of the Elders of Zion" is 7
words > MAX_VALUE_WORDS = 6 (`fable_earsguard91.py:45`, check at `:58`).
No "of"-counter exists anywhere: 5-word probes pass only because they are
short. Loop121's Title-Case exemption (`fable_loop121_agent.py:78-99`,
applied at `:117-120`) needs "and", so pure-"of" names refuse there and
again at `fable_earsguard91.py:58`.

Step 2 (one change): `scripts/fable_fix144_ofname.py` — a message counts
as multi-fact only when the extra part is itself a complete teach frame
(relation cue + capitalised subject before + non-empty value after), not
when "of"/"of the" continues a capitalised name. `screen_value_144()` is
the loop121 screen with one wider door: the >6-word clause also passes a
single capitalised "of"-name span with no embedded frame. All other
screens (?, ;, possessive-is, and-possessive, second copula) are
untouched. `scripts/fable_loop144_agent.py` (loop140 style) upgrades a
SPLIT clarify to the structured teach/correct only for single teaches
passing that screen; everything else is byte-identical to loop129b.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| F1 must-write (26, 7 frames) | >= 25/26 exact, 0 wrong | 26/26 exact, 0 wrong on these |
| F1 two-fact (20) | 20/20 no-write | 19/20; 1 wrong write (t14) -> FAIL |
| F2 bench132-022 | teach saves, correct | Saved exact triple, correct (Charleroi) |
| F2 edit200 / old / new_121 | identical except predicted | 0 / 0 / only 069 (wrong->correct, Canberra) |
| F3 marks123 (p2/p3/p4/rt110/q1/bench/rt81/sleep/soak/q4) | per-case identical | identical (only timings/agent-path strings differ) |
| F4 time per run | < 25 min Mac CPU | F1 ~1 s, bench ~20 s, marks123 ~134 suite-s |

F3 detail: p2 identical (same 2 OK->BUG + 4 still-BUG as the reference);
p3 L1-L6 all PASS both; p4 30/30 both; rt110 identical (same 6 still-BUG);
q1 F5/M5 FAIL on both (base behaviour); bench rows per-item identical;
rt81 61/0/13 both; sleep SKIP both; soak 2000 turns 0 lost/0 wrong/0
doubled both; q4 leaks identical.

## Diagnosis note (F1 t14, the one FAIL)

"Ann is famous for Cats and Tom died in the city of Oslo" saved
(Ann is famous for Cats and Tom, place_of_death, Oslo) — on loop129b too
(verified live, ears_stage loop121-teach). Cause: the place_of_death
template `(.+?) died in the city of (.+?)` sits BEFORE famous-for in
STATEMENT_PATTERNS, so it matches first with a clause-containing subject
and a short clean value ("Oslo") the guards never inspect. Guards screen
the value only, never the subject. Out of scope for this one change;
needs a subject-side multi-fact rule (future experiment).

## Deviations

1. `Loop144Daemon.__init__` missed `self.idle_seconds` (copied __init__
   without it); the first F3 subprocess boot crashed (AttributeError).
   Fixed with one line in my own file; F1/F2 re-ran on final code with
   identical signatures (F1 same FAIL, F2 same PASS). Sealed inputs
   (cases/config) never changed.
2. The F3 attempt that crashed left partial outputs; `marks123/` was
   deleted and re-run fresh (my dir, unsealed outputs only).

## What it means

Long "of"-names now teach exactly; genuine two-fact messages still
refuse; bench + marks123 behaviour moved only on the two predicted items.

## What it does not mean

t14 shows the guard still cannot see a second fact hiding in the
SUBJECT; subject-side packing is unfixed and unmeasured beyond this probe.

## Reproduce (from worktree root, after seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix144_f1.py --out artifacts/fable-fix144-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix144_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop144_agent.py --config artifacts/fable-fix144-20260922/loop144-config.json --out artifacts/fable-fix144-20260922/marks123 --workers 4
