# 92 — Fable-Edit-SCALE (experiment 92, 2026-09-22)

How far the Fable-Edit benchmark stretches before it breaks — and the
two exact mechanisms that break it. Written for Ben in plain language.

## The idea in five lines

Experiments 65 and 73 passed 200/200 on short two-hop edit questions.
Experiment 92 asks: what breaks first when the questions get longer
(3 and 4 hops), pile up (several edits on one chain), share one
notebook (1,000 cases taught together), contradict each other, or run
backwards over three hops? Answer: the notebook itself never breaks in
isolation (1,000/1,000 over the five isolated splits); sharing one
notebook breaks it 25 times, and the English template parser breaks it
41 times. Both failure mechanisms are identified exactly.

## The six splits (all from the same CC-BY-4.0 source, seed 9200)

Builder `scripts/fable_bench92_build.py` reads the same MQuAKE-Remastered
CF-3k parquet as exp 65 and writes `data/open/bench92/` (manifest with
hashes). Nothing is invented except S6's fictitious chains (like exp
65's reversal half); S5's "second edit" re-uses each case's own original
value (a revert, so the latest edit must win back the original answer).

- **S1** — 200 three-hop single-edit cases (356 eligible in source).
- **S2** — 200 four-hop single-edit cases (224 eligible).
- **S3** — 200 multi-edit cases: 2–4 edits on the same chain
  (60×2-hop, 80×3-hop, 60×4-hop).
- **S4** — all 1,000 chain-linked two-hop cases taught into ONE
  notebook (originals first, then edits), then all 1,000 questions.
  The interference test.
- **S5** — 200 conflicting edits: source edit, then an override back to
  the original; gold is the original answer.
- **S6** — 200 reversal-at-3-hops items (100 fictitious chains ×
  forward/backward, five relation pairs as in exp 65).

## The two arms

The **notebook arm** (`scripts/fable_bench92_notebook_arm.py`) feeds
triples through the unchanged notebook + QualifierAwareReasoner, one
fresh notebook per item except S4's shared one. The **English arm**
(`scripts/fable_bench92_english_arm.py`, S1–S3 only) feeds only English
sentences through new template ears: four new statement patterns
(employer, occupation, language-of-work, child), an N-hop chain walk
(exp 73's walker stops at hop 2, which would answer wrong here), and
widened question-word cues. Unparseable input becomes a structural
abstention, never a guess.

## Results (registered FAIL on the zero-wrong bar)

Notebook: S1 200/200, S2 200/200, S3 200/200, S5 200/200, S6 200/200 —
all with 0 wrong and full reasoner↔contract agreement. S4: 973/1000
with **25 confident wrongs + 2 misses**. English: S1 195/1/4, S2
142/32/26, S3 181/8/11. Whole wave took 10 seconds on Mac CPU; S4
queries run at p50 2.4 ms / p99 5.8 ms in a 1.5 MB notebook.

## Failure mechanism 1: shared bridge slots (S4)

Cases share mid-chain entities (Nigeria, USA, UK…). Case subjects are
unique (0 teach conflicts), but every edit is taught with
`correction=True`, so the last case in line to edit a shared slot
(e.g. Nigeria's head of government) overwrites earlier cases' edits.
Earlier questions then get the later case's value, confidently. The
reasoner is innocent — the contract agrees on every failure. The
missing piece is case isolation (namespacing), which was not tested.

## Failure mechanism 2: pattern shadowing (English arm)

Exp 73's catch-all pattern `The <X> is <Y>` fires before the three new
specific patterns, so `The director of The Beatles is Gilad Erdan`
parses as subject `director of The Beatles` instead of subject
`The Beatles`. The chain walk then stops early (1 hop instead of 4)
and answers confidently wrong. All 41 English wrongs involve a
shadowed relation; zero sentences failed to parse. Fix: try specific
patterns before the generic one (future work; registered numbers
stand).

## Limits

Template English only — paraphrase gaps become honest misses by design
(19 start-entities need aliasing, 12 questions drop a hop entirely).
No baseline model was run. The <95%-correct tripwire never fired on the
notebook arm (S4 = 97.3%); the break showed up in the zero-wrong bar
instead — a stricter, better tripwire.

## What it means

Depth, multi-edits, overrides and reversal are free with the current
design; sharing and parsing order are where scale bites, and both bites
have a named, minimal fix.

## What it does not mean

It does not mean the notebook or the hop loop has a depth limit (none
was found up to 4 hops), that batch teaching is hopeless, or that the
English failures need machine learning — pattern order, not model
size, caused every one of the 41.
