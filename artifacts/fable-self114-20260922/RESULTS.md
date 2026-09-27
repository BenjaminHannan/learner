# Exp 114 RESULTS — scope-guard follow-up, fresh blind panel (Muse, 2026-09-22)

Registered FAIL. One run, 1.0 s, Mac CPU, offline. The frozen scope-guarded
router (`scripts/fable_self114.py`, sha
c7762e22ae594b48bea4986e9cae32024835a6472a9714184dd612425dbbbef6,
hashed into PASSMARKS.md and sealed BEFORE the run, ledger P114.1–P114.5
appended before the run) rebuilt the exact exp-99 session (gate exact: 19
taught, 6 people, 1 quarantine, 2 corrections, 1 forgotten, 0 sleeps, 26
turns) and answered the 100 sealed fresh blind questions via
`answer_self()` with no new turns. Panel seal verified OK before scoring;
router hash re-verified in-run. Answer bodies inherited untouched from exp
99 via exp 105; only the guard is new.

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| K1 | WRONG == 0 over all 100 | 4 wrong | FAIL |
| K2 | CORRECT >= 45/70 on existing-intent rephrasings | 17/70 | FAIL |
| K3 | TRICK 10/10 decline | 10/10 | PASS |
| K4 | exp 99's 40 still 40/40 and exp 100's 80 WRONG == 0 | 40/40 and 0 | PASS |

Split of the 100: 17 CORRECT, 79 HONEST_DECLINE, 4 WRONG (existing
17/50/3, new 0/19/1, trick 0/10/0). Zero hallucinated names/numbers: all 4
WRONGs state live-state-true neighboring-intent content. The 4 WRONGs
(verbatim in `WRONGS.md`): Q017 C9-asked/C3-answered (hypothetical
"Assuming..." outside the frozen guard set — the one in-scope miss); Q023
"forgotten tally?" (synonym outside the inherited count-guard); Q053 web
"origin" (inherited keyword overlap C6/C27); Q074 new-intent time question
answered with C4 content. Unregistered dev context, same invocation:
exp-105 panel re-score exactly 1 WRONG (Q003 "individuals" synonym gap, as
ledgered in P114.5).

## Guard evidence (from the frozen dev freeze + this run)

At freeze the guard declined all 5 in-scope exp-105 WRONGs and fired on
zero of 220 dev questions answered CORRECT. On the fresh panel it caused
exactly 4 of the 50 existing declines (Q046, Q059, Q066, Q069), every one
already declining under the 105 router — the guard cost zero K2 points.
The K2 collapse is inherited coverage: 46 of the 50 existing declines fell
below the unchanged threshold/margin on harder phrasings, and 3 existing
WRONGs are synonym/overlap gaps in the unchanged 105 machinery. K3 went
8/10 → 10/10: every fresh trick declined, six of them by guard reason
(future, Tom, pronoun, hypothetical).

## What it means

The one change did exactly what it was built for — every third-party,
future, and policy/capability trap that beat exp 105 now ends in an honest
decline, with zero cost to existing coverage — but the fresh panel shows
the router's real ceiling is vocabulary, not scope: oblique rephrasings
("tally", "cite its origin") still slip past or under the keyword scorer.

## What it does not mean

Not a knowledge failure (every value stated was live-state true; 79 of 100
answers were honest declines) and not a guard failure (the guard fired on
none of the 4 WRONGs except by design gap in one). No claim about
real-English ears: this tests the scaffolding keyword router only.

## Deviations and notes

D0: pre-run runner fixes only (my own file, router untouched): the panel
seal verifies with cwd set to the panel dir (its SEAL lists bare
filenames), and the runner accepts the panel's bare-list shape (105's was
`{"questions": [...]}`). D1: scoring reuses the exp-100 scorer read-only.
D2: the inherited honest-decline sentence counts as DECLINE wherever the
exact fallback does. No questions for Ben.

## Reproduce

```bash
shasum -c artifacts/fable-self114-20260922/SEAL.sha256.txt  # seals PASSMARKS.md (pre-run)
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self114_runner.py --run --out artifacts/fable-self114-20260922
```

New files only (`fable_self114_` prefix + artifact folder + doc 114):
`scripts/fable_self114.py` (frozen guard), `scripts/fable_self114_runner.py`,
`artifacts/fable-self114-20260922/` (PASSMARKS, SEAL, RESULTS, WRONGS,
results JSON, notebook state), design doc 114.
