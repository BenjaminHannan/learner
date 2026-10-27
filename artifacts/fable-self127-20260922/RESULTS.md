# Exp 127 RESULTS — novelty guard, fresh blind panel (Muse, 2026-09-22)

Registered FAIL (K1). One run, 10.7 s, Mac CPU, offline. The frozen
novelty-guard router (`scripts/fable_self127.py`, sha
6b835c77b5aaefbbdae82755a276781af603dd05e30d9da4d118da5d56ecbe9b;
bank sha 293d9b04…; deltas sha 8803034b…; all hashed into PASSMARKS.md and
sealed BEFORE the run, ledger P127.1–P127.5 appended before the run)
rebuilt the exact exp-99 session (gate exact: 19 taught, 6 people,
1 quarantine, 2 corrections, 1 forgotten, 0 sleeps, 26 turns) and answered
the 100 sealed fresh blind questions via `answer_self()` with no new turns.
Panel seal verified OK before scoring; router, bank, and deltas hashes
re-verified in-run. Encoder, head (seed 12202, tau=0.6, mu=1.5), scope
guard, and all answer bodies byte-identical to 122; the only new code is
the novelty guard (NN cosine distance vs per-intent δ, one fixed rule).

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| K1 | WRONG == 0 over all 100 | 1 wrong | FAIL |
| K2 | CORRECT >= 45/70 on existing-intent rephrasings | 45/70 | PASS (at bar) |
| K3 | TRICK 10/10 decline | 10/10 | PASS |
| K4 | exp 99's 40 still 40/40 and exp 100's 80 WRONG == 0 | 40/40 and 0 | PASS |

Split of the 100 (127 path): 45 CORRECT, 54 HONEST_DECLINE, 1 WRONG.
Existing-C: 45 correct / 15 decline / 0 wrong. Existing-D: 10/10 decline.
New: 19/20 decline, 1 wrong. Trick: 10/10 decline. Zero hallucinated
names/numbers anywhere.

## The 122 → 127 table (same fresh panel, same invocation)

| path | CORRECT | DECLINE | WRONG | existing | tricks |
|---|---|---|---|---|---|
| 122 (frozen) | 50 | 47 | 3 | 50/70 | 9/10 |
| 127 (novelty guard) | 45 | 54 | 1 | 45/70 | 10/10 |

The 122 path's 3 fresh wrongs: Q074 opinion-about-Paris → C15, Q078
word-count → C18, Q099 teach-others-policy (trick) → C26. The guard
converts Q074 and Q099 into honest declines — including a trick the scope
guard missed — at a cost of 5 keeps (Q030/C15, Q042/C21, Q045/C23,
Q048/C24, Q052/C26). The surviving wrong, Q078 "How many words have I
spoken across all turns combined?" → C18 ("We have had 26 turns."), sits
inside δ_C18: a blend nearer than the nearest known-good phrasing, which
no distance guard can see. Verbatim in `WRONGS.md`.

## Unregistered dev context (same invocation, 127 path)

panel105: 55/45/0 (guard costs nothing). panel114: 46/54/0 (costs nothing).
panel122: 41/59/0 — the 3 dev wrongs → decline at the designed cost of 3
keeps (44→41). 122-path re-run on the 122 panel reproduces the sealed
44/53/3 exactly.

## Reading the FAIL honestly

The guard does what it claims: on blind data it converts far- and
mid-range near-blends into declines (2 of 3 fresh wrongs, all 3 dev
wrongs, plus a scope-missed trick) while costing 0 keeps on two of three
dev panels and 3–5 keeps where blends crowd an intent. What it cannot do
is also stated in the design: blends nearer than the nearest known-good
phrasing (fresh Q078) are invisible to any distance threshold. K2 passed
at exactly the bar (45/70) because this fresh panel routed easier for the
head (50/70) than the 122 panel did (44/70) — the 5 guard losses were
affordable here and would not be on a harder panel.

## What it means

A novelty guard on frozen embeddings is a strict safety improvement over
the head alone on every blind set tried: dev wrongs 3→0, fresh wrongs
3→1, tricks 9–10/10→10/10, with zero invented names/numbers and all
regressions green.

## What it does not mean

Not a fix for near-intent novelty: questions asked in an intent's own
closest words still clear the bar, and the C15 knife-edge (δ 0.1290 vs
nearest keep 0.1298) shows the threshold has no margin where it matters
most. No new answering power; nothing here touches real English
understanding beyond scaffolding routing.

## Deviations and notes

D1: three dev-only helper scripts (all `fable_self127_` prefix, none
touched after the seal): calibrate (distance survey), deltas
(full-precision δ writer that caught a 4-decimal rounding bug which had
hidden 2 dev wrongs and flipped 2 keeps), runner (devrescore + registered
modes). D2: δ rule carries two fixed constants (keep-margin 1e-4 for
measured float noise ≤ 1.2e-7, wrong-epsilon 1e-6), applied uniformly —
one rule, no per-intent hand-tuning; bank = all 2060 train122 rows, zero
added phrasings. No questions for Ben.

## Reproduce

```bash
shasum -c artifacts/fable-self127-20260922/SEAL.sha256.txt  # seals PASSMARKS.md (pre-run)
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self127_runner.py --run --out artifacts/fable-self127-20260922
```

New files only (`fable_self127_` prefix + artifact folder + doc 127):
`scripts/fable_self127.py` (router), `scripts/fable_self127_runner.py`,
`scripts/fable_self127_calibrate.py` + `scripts/fable_self127_deltas.py`
(dev-only), `artifacts/fable-self127-20260922/` (PASSMARKS, SEAL, bank,
deltas, RESULTS, WRONGS, results JSON, notebook states), design doc 127.
