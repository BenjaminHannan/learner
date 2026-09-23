# Exp 129 PASSMARKS — teach-punctuation single-change patch (sealed BEFORE any registered run)

Registered single-change patch for the wrong-write bug found by red team 124
(bug 4: bench73-style teaches store the sentence-final period in the value).
THE ONE CHANGE: strip trailing sentence punctuation from subject/value spans
on every teach path before the write (scripts/fable_fix129_punct.py rule:
strip-then-restore, abbreviation periods kept), applied as subclass-only
mixins to both lineage heads (loop129a = loop117 + mixin, loop129b =
loop121 + mixin). No existing file is edited.

Sealed inputs:
- F1 probe set: artifacts/fable-fix129-20260922/fable_fix129_f1_cases.json
  (45 cases, 41 teach turns across bench73/correction/fake/extra/abbrev/
  subject/quote paths x '.', '!', '?', trailing spaces; 9 abbreviation
  names incl. Washington, D.C. and U.S.S.R.),
  sha256 d31fec06556dfff120699da4c411614e0bfcbe5fee558b6dcb132395c768aa9a
- 124 suite+checker: artifacts/fable-redteam124-20260922/ (sealed there).
- 110 suite+checker, 98 suite+judge, loop96 L-runners, 30 innocents, 3 bench
  splits + scorer v2: sealed in their own exps, read-only here.

## Marks (integer counts, every seed/case reported, never averaged)

- F1 sealed probe set through BOTH new loops (fresh daemon dir per case,
  scripts/fable_fix129_f1.py): 0 failures. A failure = stored
  subject/value with trailing sentence punctuation, a dropped abbreviation
  period, a missing expected fact, or any write on a clarify case.
- F2 red team 124's 62 cases re-run through both new loops with the sealed
  124 checker (scripts/fable_fix129_redteam124.py): 0 wrong writes caused
  by punctuation (a wrong write whose strip maps to an allowed fact);
  all remaining BUGs reported by family; families with no punctuation
  involvement byte-identical to 124's rows (129a vs 124-loop102 rows modulo
  the inherited loop117 underscore->space mouth rendering, verified field
  by field).
- F3 regressions: loop129a exp-117 Q1-Q5 + exp-102 P2/P3/P4 identical to
  loop117's reported outcomes (Q1 both OK; Q2 58 OK + 4 BUG, still-BUG
  exactly R4/N6/S3/S6, BUG->OK exactly F5+M5, 0 OK->BUG, 0 HARNESS-ERROR;
  P2 0 OK->BUG + 0 still-BUG; P3 all 7 pass; P4 pass 0 false refusals;
  Q4 0 leaks); loop129b identical to loop121's exp-121 regression outcomes
  (T4 pass; P2 ok_to_bug ⊆ {B7, D8} and still_bug ⊆ {B7, C2, C5, D8},
  nothing else moves; P3 all 7 pass; P4 pass 0 false refusals).
- F4 loop129b bench, scorer v2 (scripts/fable_loop129b_bench.py --run
  --agent loop129b): Fable-Edit-200 200/200; old fresh 4-hop ≥ 157 correct
  and 0 wrong; new bench121 split ≥ 136 correct and ≤ 1 wrong.
- F5 whole registered wave < 25 min wall-clock on the Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...).

## Pre-seal evidence (dev only, NOT registered runs; new loops never run)

- Step-0 probe (scripts/fable_fix129_probe.py, old code read-only): LEAK on
  bench73 citizen/capital/official-language + '.', '!', '?', trailing
  spaces; exp-92 employer/occupation/child + '.'; FakeEars possessive + '!'
  and '?'. Clean: FakeEars possessive + '.'; explicit-dot bench73 patterns.
- Old-loop calibration: '?' teaches clarify with 0 writes ("Was that a
  question?"); '!' teaches write junk ("Italy!"); correction-prefix
  "Actually, Gus Webb. ..." writes subject "Gus Webb." + value "Chile.".
- loop121 bench calibration (scripts/fable_loop129b_bench.py --run --agent
  loop121; rows kept in calibration/): edit200 150 correct / 50 abstain /
  0 wrong; old fresh 157 / 43 / 0; new 136 / 63 abstain / 1 wrong (the known
  bench121-4hop-069 teach-gap item). Edit200 abstains are 25
  abstain-absent + 25 abstain-broken (expected-abstain, structural).
- Mixin unit check: 20/20 strip/keep cases (Italy./!/ ?/;/:/D.C./U.S.S.R./
  St./J./U.K./quotes/spaces) pass.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.
