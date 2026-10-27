# Exp 147 RESULTS — mention-walk alignment (7–464 s per run, Mac CPU)

Registered runs on sealed code (SEAL.sha256.txt): A1 124 redteam143 cases
on loop147-132 (7.2 s); A2 48 new dialogues x 3 variants (2–3 s); A3 bench
pairs 15 x 200 items (256–378 s); A4 marks123 x 3 variants (169–464 s).

## Marks

| mark | bar | result |
|---|---|---|
| A1 143 on loop147-132 | 12 prefix/type cases abstain, 5 suffix answer sealed value, 0 worse | PASS: WRONG->OK A1/U1-U5/K8/S4/T4/L4/K6/K10 (12), MISSED->OK P1/P2/Q1/Q2/D2 (5); other 107 verdicts identical (incl. all 92 OK) |
| A2 new probe 48 | suffix answer, short-chain abstain, 0 wrong, x3 variants | PASS: 48/48 on 134, 113e, 132; 23 answers + 25 abstains each |
| A3 bench121-new/old, edit200, s2fresh, bench132-new per variant vs base | 0 new wrong; lost only predicted | PASS: 15/15 pairs 0 new wrong, 0 correct lost (3000 items) |
| A4 marks123 per variant vs base | identical except predicted | PASS (see moves): P2 134/132 0 OK->BUG + 0 still-BUG (4 sealed bugs fixed each); q4-132 base leaks + capital_in_2019; rt110-134 D7 race re-run clean; all else per-case identical |
| A5 timing | every run < 1500 s | PASS (max 463.5 s) |

P147.1–P147.6 all TRUE (Brier 0.0225/0.01/0.04/0.0225/0.04/0.01).

## A1 detail (every case reported)

Fixed: class-3 prefix answers now abstain (A1/U1-U5/K8/S4/T4/L4), class-4
cue-stem mismatches now abstain (K6/K10), suffix-blindness now answers
(P1 Litora, P2 Cardova, Q1 Petra Voss, Q2 Tormeil, D2 Aldport).
Unchanged non-OK (predicted still-open, same verdict+reply class as base):
negation N1-N5, qualifiers T1/T5/B1, substring entity O3 (still
WRONG-ANSWER); cue gaps H3/J5/J8/J9/J10 (still MISSED); H5 stays
WRONG-ANSWER (documented expectation error: the rewriter's Meridian is
human-correct). No HARNESS-ERROR (124/124 verdicts).

## A4 moves (only differences vs each sealed base)

- P2: 134 and 132 variants 0/0 (bases 2 ok_to_bug + 4 still_bug: B7/D8/C2/
  C5 all fixed); 113e 0/0 identical to its clean base.
- q4-132: base leak set + `capital_in_2019` (D8 qualifier abstain "I don't
  know Poland's capital_in_2019"). q4-134 clean both; q4-113e identical
  leak sets both.
- rt110-134: first run 1 OK->BUG (D7 empty-serve race: turn 0 got "I
  didn't catch anything" under shared-machine load, 0 wrong writes);
  open re-run once: 0 OK->BUG, still exactly R4/N6/S3/S6. Both reported.
  rt110-113e/132: 0 OK->BUG, still identical to bases (6 each).
- p3/p4/q1/bench/rt81/sleep/soak/q4-shape: per-case identical to bases
  (p3 134/132 all PASS; 113e l5z1/l5z2 FAIL both incl. 58/60 + identical
  rows; rt81 61/0/13 all three; soak PASS all three registered; sleep
  SKIP all three).

## Deviations / limits

One open re-run (rt110-134 D7 race, precedent exp 135 D1); no code edits
after the seal (docstring-only touches before seal are in the frozen
hashes). Single deterministic run per case/item; English only; no sleep
involved. Other agents shared the machine during every wave (load
flakes: dev saw P5/L3/soak race signatures; registered needed one
re-run). Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_align147_a1.py` (A1); `... scripts/fable_align147_a2.py
--variant all` (A2); `... scripts/fable_align147_bench.py --variant all`
(A3); `... scripts/fable_marks123_all.py --agent scripts/
fable_loop147_agent.py --config artifacts/fable-align147-20260922/
loop147-config.json --out <dir> --workers 4` (A4, per variant/config).

## Diagnosis note (one)

The gate fixes every 143 wrong/missed rooted in walk direction except the
families doc 143 assigned to follow-ups (negation, qualifiers, substring
entities, cue/format gaps) — those are byte-identical to base by design.

## What it means

Asked-chain vs taught-chain mismatches now resolve the safe way in both
directions on all three lineages, with zero regressions across 124
red-team cases, 48 new probes, 3,000 bench items and 30 regression
suites.

## What it does not mean

It does not mean the assistant handles negation, dates, typos or unknown
words any better — those replies are unchanged — and it does not mean
teaching changed (every teach reply identical to base).
