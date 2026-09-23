# Exp 100 RESULTS — blind phrasing test of the self-question answerer (Muse, 2026-09-22)

Registered FAIL. One run, 0.9 s, Mac CPU, offline. `scripts/fable_self99.py`
imported read-only and unmodified; its exact scripted session rebuilt (gate
exact: 19 taught, 6 people, 1 quarantine, 2 corrections, 1 forgotten,
0 sleeps, 26 turns); all 80 frozen blind questions asked via `answer_self()`
with no new turns; scored by `scripts/fable_self100_runner.py`.

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| B1 | WRONG == 0 over all 80 | 5 wrong | FAIL |
| B2 | CORRECT >= 40/60 on rephrasings Q01-Q60 | 27/60 | FAIL |
| B3 | new intents Q61-Q80 CORRECT/DECLINE/WRONG | 0/19/1 | gated by B1: FAIL |

Split of the 80: 27 CORRECT, 48 DECLINE (38 exact fallbacks + 10 proper
declines), 5 WRONG. Zero hallucinated names/numbers anywhere: every WRONG
used live-state-true content aimed at a neighboring intent. The 5 WRONGs:
Q14 (belief question answered with holdings starting "Yes"), Q23/Q24
("hw many"/"count" forgotten asked, forgotten fact told), Q28 ("how many
times" corrected asked, correction list told), Q69 (correct-process asked,
correction list told). All 19 misses are verbatim in `WRONGS.md`: the router
matches exact substrings, so "taught" misses "teach" (Q05), "told"/"tell"
miss "teach" (Q06/Q09), "hw many" misses "how many" (Q01/Q23/Q36),
contractions miss (Q43 "don't"), and C24 needs exact equality (Q44).

## What it means

The answerer is safe but brittle: unparsed phrasing declines honestly
(never invents), yet only 27/60 natural rephrasings get through, and 5
misfire into a confident neighboring answer — one of them (Q14) with a
misleading leading "Yes" on a belief question.

## What it does not mean

Not a knowledge failure: every value the answerer did state was live-state
true. No claim about real-English ears: this tests the scaffolding template
router only.

## Deviations

D1: the exact fallback ("I do not understand…") counts as CLARIFY — the
brief's WRONG clauses (invented name/number, confident wrong-intent content)
do not cover a content-free non-answer; its verb "Ask" is exempt from the
name scan. D2: intent-value check runs before the decline-marker scan (else
the correct C22/C23/C25 answers, which honestly quote "never taught" /
"nobody taught" / "do not know" from live state, mis-score as declines),
and for C-mapped questions an other-intent value match scores WRONG before
markers are consulted. D3: before sealing I also read exp-99 `RESULTS.md`
state counts (templates themselves first seen after sealing, in the
read-only import above). D4: B2's denominator 60 includes the 10
decline-expected rephrasings, so its ceiling is 50/60. Obvious-fix sketch
(not implemented, per brief): stem/typo/contraction-tolerant matching,
substring (not exact) triggers, a count-vs-list guard for "how many"-forms,
and testing "believe" before "internet" in branch order. No questions
for Ben.

## Reproduce

```bash
shasum -c artifacts/fable-self100-20260921/SEAL.sha256.txt  # sealed pre-run: OK
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self100_runner.py --run --out artifacts/fable-self100-20260921
```

New files only (`fable_self100_` prefix): `scripts/fable_self100_runner.py`,
`artifacts/fable-self100-20260921/` (PASSMARKS, QUESTIONS, SEAL, RESULTS,
WRONGS, results JSON, notebook state), design doc 100.
