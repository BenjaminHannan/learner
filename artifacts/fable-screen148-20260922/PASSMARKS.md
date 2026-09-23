# Exp 148 PASSMARKS (sealed BEFORE the registered run — do not edit after)

One change: question screen for meaning-changing words, as a mixin
(`QuestionScreenMixin148` in `scripts/fable_loop148_agent.py`, word logic in
`scripts/fable_screen148_mixin.py`) over loop134 (shipped arm) and over
loop132 (Q1 arm). Before any question composer/lookup runs, a trailing-"?"
turn is scanned after removing taught entity/value mentions from the live
notebook triples; on a sealed trigger the ears return a short honest
clarify and never answer. Statements (teach turns) are untouched.

## Sealed word list (exact; one-line reason each)

Negation (case-insensitive, word-boundary tokens):
- `not` — canonical predicate negation the composer silently drops.
- `never` — temporal negation with no notebook semantics.
- `n't` (straight/curly apostrophe) — contracted negation, same as `not`.
- `no one` (phrase) — negated-person quantifier the lookup cannot represent.
- `nobody` — same meaning as `no one`.
- `none` — negated quantifier with no set semantics in the notebook.

Time:
- 4-digit year (`\b[12]\d{3}\b`) — the notebook stores current facts, no dates.
- `as of` — explicit temporal scoping phrase.
- `before` — temporal ordering the hop walk cannot represent.
- `after` — same as `before`.
- `formerly` — asserts a non-current scope.
- `originally` — same as `formerly`.
- `used to` — past-habit scope the notebook cannot represent.
- `currently` — explicit currency claim the notebook cannot verify.

Borderline (decided now, sealed):
- `now` NOT a trigger — it coincides with current-fact semantics (answerable).
- `still` NOT a trigger — it asks a current fact; continuity is presupposed, not looked up.
- bare `no` NOT a trigger — `No,` is a teach-turn correction prefix and `No` opens titles (`No More Heroes`); only the phrase `no one` fires.
- `neither`/`nor`/`nothing` NOT triggers — not in the brief's list; no evidence.
- `No`/`Never` inside names (`Noam`, `Nevermore`, `No Doubt`, `Knot`, `Notre-Dame`, `Norway`, `Annotated`) never fire — matching is on word-boundary tokens, substrings never match.
- year-tokens inside taught mentions (`1984`, `Windows 2000`, `Can't Buy Me Love`) are exempted — there they name a thing, not a time (exemption uses the live notebook triples at question time).

Clarify texts (both contain bench-scorer `i didn't understand that` and
143-marker `could you say`):
- neg: "I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part?"
- time: "I didn't understand that. I only know current facts, not years or 'as of' -- could you say it without that part?"

## Sealed case files (sha256)

- fable_screen148_cases.json (40 NEW probe questions, written before any run):
  0c998442f5cf9b5a28438c5c64bbf41b7b74ca073f61699b273d7dae2bdaee5c
- fable_redteam143_cases.json (sealed 143 set, read-only, never overwritten):
  3e39464ad7c0ffa50a603b4f02e36d0c4facedc500af318dc869d384b6deaadb
- loop148-config.json (DEFAULT_CONFIG148 + thinker module string):
  7d5fc6d242679eb5827c0e69f77cd83377b2265ede0e1dae61a5a7816c6f1e1f
- loop148-on132-config.json (DEFAULT_CONFIG132 + 2 renamed plug strings):
  4f185130ac6c3ba960330a36c434727647012836adcb41ea913f4e6cd34c2007

## Marks

- Q1: 143's negation+qualifier cases (N1-N5, T1, T5, B1) re-run on the
  loop132+148 variant (sealed runner by import, daemon class + ART path only
  swapped) -> no confident answer on all 8; 0 of the other 116 cases worse
  than the sealed loop132 run (OK < MISSED < WRONG-ANSWER ordering).
- Q2: NEW probe (fable_screen148_cases.json): 20/20 trigger questions
  clarify with 0 answers (and the loop134 base answers each confidently, so
  the screen did the work); 20/20 innocent questions byte-identical replies
  to the loop134 base (incl. I17/I18 abstain-controls abstaining identically).
- Q3: bench121 new/old, Fable-Edit-200, bench132-new per-item verdicts
  identical base-vs-148 EXCEPT the 37 `never-taught` edit200 items below,
  predicted to keep the abstain verdict with a different clarify text
  (screen message vs base message):
  bench65-abs-absent-01 03 05 07 09 11 13 15 17 19 21 23,
  bench65-abs-broken-00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24.
  All other trigger-looking bench questions are predicted NO-change:
  year-titles are taught subjects (bench103-s2fresh-4hop-111 142 176,
  bench65-mquake-028 076, bench132-4hop-132 144), `Can't Buy Me Love`
  (bench132-4hop-057 072) is a taught subject, `No More Heroes`
  (bench132-4hop-177) is bare-`no`. No bench question otherwise contains a
  sealed trigger (full 800-question scan with the sealed logic pre-run).
- Q4: marks123 suites identical to loop134 EXCEPT P2-D8 (`Who is Poland's
  capital in 2019?`), predicted BUG->OK (the screen clarifies without
  `Warsaw`, which the sealed expectation demands); marks123-bench counts
  identical with reply-text-only diffs on the same 37 never-taught items.
- Q5: each registered run < 25 min wall-clock, Mac CPU,
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1. All drivers use in-process daemons
  (mailbox files, same code as subprocess daemons); daemon classes accept
  idle_seconds for real wrapper use (default 30.0).

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148_q1.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148_q2.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop148_agent.py --config artifacts/fable-screen148-20260922/loop148-config.json --out artifacts/fable-screen148-20260922/marks123-148 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop134_agent.py --config artifacts/fable-loop134-20260922/loop134-config.json --out artifacts/fable-screen148-20260922/marks123-134 --workers 4
