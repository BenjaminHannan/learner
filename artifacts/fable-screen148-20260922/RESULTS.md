# Exp 148 RESULTS — question screen for meaning-changing words (3.4 s + 1.4 s + 73.5 s + 134 s, Mac CPU)

One change: `QuestionScreenMixin148` (new files only) screens trailing-"?"
turns for a sealed trigger list (negation: not/never/n't/"no one"/nobody/
none; time: year, "as of", before/after/formerly/originally/"used to"/
currently; taught-mention exempted, word-boundary matched) before any
composer runs, clarifying honestly instead of answering. Statements untouched.

## Marks

| mark | bar | result |
|---|---|---|
| Q1 143 re-run on loop132+148 | 8/8 targets no confident answer; 0/116 worse | PASS: 8/8 clarify (N1-N5 neg, T1/T5/B1 time stages); worse [] (100 OK / 14 WRONG / 10 MISSED vs sealed 92/22/10: exactly the 8 targets fixed) |
| Q2 new 40-probe | 20/20 clarify 0 answers; 20/20 byte-identical | PASS 40/40: every base reply on triggers was a confident fact; all innocents (1984, Blade Runner 2049, No Doubt, Noam/Nevermore/Knot, Annotated, Norway, Notre-Dame, now/still, controls) identical incl. 2 abstain-controls |
| Q3 benches base-vs-148 | verdicts identical except 37 listed never-items | PASS: 0 verdict diffs on 800 items (edit200 150/50/0, old 157/43/0, new121 136/63/1, new132 139/59/2); reply diffs exactly the predicted 37 never-taught items |
| Q4 marks123 vs loop134 | identical except P2-D8 BUG->OK | FAIL: P2-D8 fixed as predicted, rt110/q1/p4/q4/bench/soak/rt81 identical — but p3 L5-Z1 58/60 (turns 42-43) and L5-Z2 37 MISS (never-items); see diagnosis |
| Q5 time | each run < 25 min | PASS: 3.4 / 1.4 / 73.5 / 134.3+153.5 s; in-process daemons, idle_seconds accepted (30.0) |

P148.1 TRUE | P148.2 TRUE | P148.3 TRUE | P148.4 FALSE | P148.5 TRUE.
SCORE: FAIL (Q4).

## Diagnosis note (the one failure)

Two faces of one plumbing fact: a screen clarify is an ears-level
`{"act": "clarify"}` with **no reasoner status**, while status-based judges
expect one. (1) L5-Z1 turns 42/43 (`What is Mira's city in 2019?`) seal
`OK` — the old qualifier-blind answer (the exact T1 bug class); the screen
honestly clarifies, so the status mismatches. The sealed expectation encodes
the bug. (2) L5-Z2's 37 never-items: the base asks an unknown relation and
the reasoner returns MISSING_FACT (abstain_ok); the screen clarifies first,
yielding status-less NO_RECORD (MISS). User-visible replies stay honest
abstentions in both arms (0 wrong writes everywhere, bench wrong 0); only
the record status differs. A status-preserving screen (e.g. routing the
refusal through a MISSING_FACT record) is a new change and out of scope —
this FAIL stands as registered.

## Deviations / limits

None from plan. Single deterministic run per case/item; in-process mailbox;
English only; no sleep involved. Q1 reuses the sealed 143 runner by import
(daemon class + ART path swapped only). Q3 bench132-new uses the same v2
scorer as the other splits (base-vs-148 comparison is scorer-identical).

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148_q1.py` (then `..._q2.py`, `..._bench.py --run`, and the two `fable_marks123_all.py` lines in PASSMARKS.md).

## What it means

Negation- and qualifier-blindness are gone with one pre-composer screen and
zero cost to intact questions: all 8 red-team targets clarify, 800 bench
verdicts and every innocent look-alike answer stand exactly as before.

## What it does not mean

It does not mean the assistant understands negation or time — it only knows
when to shut up — and it does not mean status-based suites accept the new
refusal (p3 L5 still wants the old answers/statuses there).
