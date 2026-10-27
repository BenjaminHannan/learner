# Experiment 92 — PASSMARKS (Fable-Edit-SCALE, notebook arm + English arm)

Sealed before the registered run. Data `data/open/bench92/` (builder
`scripts/fable_bench92_build.py`, seed 9200, manifest
`fable_bench92_build_manifest.json`), all from the SAME licensed source
as exp 65 (MQuAKE-Remastered CC-BY-4.0 CF-3k parquet; nothing invented
except S6's fictitious 3-hop reversal chains, like exp 65's reversal
half; S5's override re-uses each case's own ORIGINAL triple value):

| Split | Content | n |
|---|---|---|
| S1 | 3-hop single-edit | 200 |
| S2 | 4-hop single-edit | 200 |
| S3 | multi-edit, 2–4 edits, same chain (60×2hop/40×3hop-2ed/40×3hop-3ed/20×4hop-2ed/20×4hop-3ed/20×4hop-4ed) | 200 |
| S4 | batch: all 1,000 chain-linked 2-hop cases taught into ONE notebook (originals `correction=False` in case_id order, then edits `correction=True`), then all 1,000 questions | 1000 |
| S5 | conflicting edits: source edit, then override back to the ORIGINAL value (latest must win; gold = original answer) | 200 |
| S6 | reversal at 3 hops, ours-fictitious (100 chains × fwd/rev) | 200 |

Notebook arm (`scripts/fable_bench92_notebook_arm.py`): same notebook +
QualifierAwareReasoner + scoring as exp 65 (exact match after norm;
abstain n/a here — all items expect answers; WRONG = OK with a value
outside the gold set). S1/S2/S3/S5/S6 use a fresh notebook per item; S4
uses one shared notebook. English arm
(`scripts/fable_bench92_english_arm.py`, template92 ears, N-hop walk)
runs on S1–S3 only. Every seed/case reported, nothing averaged. Mac CPU,
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. A registered FAIL stays a FAIL.

| Mark | Bar |
|------|-----|
| B1 per-split counts | integer correct/wrong/miss reported separately for every split (notebook S1–S6, English S1–S3); nothing averaged |
| B2 zero wrong | WRONG = 0 on every split, both arms (the core safety property: never a confident wrong answer) |
| B3 first break | name the first split (in S1..S6 order, notebook arm) with correct < 95%, with 5 failing items verbatim incl. the notebook trace (taught triples → frame → status/answer) |
| B4 batch cost | S4 query latency p50/p99 and notebook size (events, bytes, entities, relations, teach conflicts) reported |

Ledger predictions P92.1–P92.8 (appended before the run).

## What it means

If B2 holds everywhere, the notebook scales to 3–4 hops, same-chain
multi-edits, batch teaching, overrides and 3-hop reversal without ever
answering confidently and wrong. B3/B4 say exactly where scale first
bites and what it costs.

## What it does not mean

It does not show English understanding at scale (template ears covers
only enumerated patterns; paraphrase gaps become MISS by design), nor
that batch teaching is safe (S4 interference is the point of the test),
nor anything about any other model or baseline.
