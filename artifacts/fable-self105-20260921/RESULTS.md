# Exp 105 RESULTS — scored-router fix, blind panel (Muse, 2026-09-22)

Registered FAIL. One run, 0.9 s, Mac CPU, offline. The frozen scored
router (`scripts/fable_self105.py`, sha
9950ada08742f969b54e9a09233c35e2b24ddf97a3b328dbadadb2ecdfaeb704,
hashed into PASSMARKS.md and sealed BEFORE the run) rebuilt the exact
exp-99 session (gate exact: 19 taught, 6 people, 1 quarantine,
2 corrections, 1 forgotten, 0 sleeps, 26 turns) and answered the 100
sealed blind questions via `answer_self()` with no new turns. Panel seal
verified OK before scoring; router hash re-verified after. Answer bodies
are inherited untouched from exp 99; only the routing changed.

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| K1 | WRONG == 0 over all 100 | 6 wrong | FAIL |
| K2 | CORRECT >= 45/70 on existing-intent rephrasings | 43/70 | FAIL |
| K3 | TRICK 10/10 decline | 8/10 | FAIL |
| K4 | exp 99's 40 still 40/40 and exp 100's 80 WRONG == 0 | 40/40 and 0 | PASS |

Split of the 100: 43 CORRECT, 51 HONEST_DECLINE, 6 WRONG. Zero
hallucinated names/numbers anywhere: all 6 WRONGs state live-state-true
content for a neighboring intent. The 6 WRONGs (verbatim in `WRONGS.md`):
Q003 (people-count asked as "individuals", answered with facts-count);
Q079/Q081 (forget-policy/capability asked, past-forgetting told);
Q080 (answer-standards asked, answered-count told — "answer"+"question"+
"actually" outscored all); Q092 (Tom's knowledge asked, my count told);
Q096 (future count asked, present count told — no tense guard).

Fixed vs exp 100 (all 5 old failure shapes gone on blind analogs): the
belief question (Q014-analog "u beileve..." declines; clean "believe"
rephrasings route C7 CORRECT), "how many/count" forgotten/corrections
(Q023/Q024/Q028-analogs CORRECT via the count-guard), and the
what-happens-when-correct trap (Q078-analog declines by margin).

## What it means

The one change (scored router + guards + margin-2 decline) removed every
exp-100 failure mode on unseen phrasings and held the line perfectly on
all 120 dev questions, but unseen phrasings still find six confident
misfires: formal synonyms ("individuals"), capability/process readings of
forget-words, and count questions about other minds or the future, which
the guards do not cover.

## What it does not mean

Not a knowledge failure: every value stated was live-state true, and 51
of 100 answers were honest declines. No claim about real-English ears:
this tests the scaffolding keyword router only, and the panel authors'
NEW/TRICK phrasings are harder than the dev distribution by design.

## Deviations and notes

D1: scoring reuses the exp-100 scorer read-only (its D1/D2
fallback-then-marker order inherited). D2: the honest-decline sentence
("I have no record...") counts as DECLINE wherever the exact fallback
does. D3: panel files opened only after the router freeze + PASSMARKS
seal + ledger P105.* (hashes re-verified in the run script; it aborts
otherwise). Sensitivity (not headline): Q079's C11 answer ("kept but
retired") directly answers NEW9, so under the panel's outcome key it
reads CORRECT; headline scoring follows the sealed exp-100-literal rule
(C-content for NEW = WRONG). Either way K1 FAILs (5 other WRONGs).
No questions for Ben.

## Reproduce

```bash
shasum -c artifacts/fable-self105-20260921/SEAL.sha256.txt  # seals PASSMARKS.md (pre-run)
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self105_runner.py --run --out artifacts/fable-self105-20260921
```

New files only (`fable_self105_` prefix): `scripts/fable_self105.py`
(frozen router), `scripts/fable_self105_runner.py`,
`artifacts/fable-self105-20260921/` (PASSMARKS, SEAL, RESULTS, WRONGS,
results JSON, notebook state), design doc 105.
