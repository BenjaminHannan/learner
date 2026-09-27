# Audit 83 — Ears rung-2 scoring audit (pre-results, read-only, 2026-09-21)

Seal: `SEAL.sha256.txt` verifies 12/12 files OK; all 9 §4 content hashes recomputed
identical (e.g. cal `d7609002…`, wnewrel `3b6bb0d6…`). Panels unmodified since sealing.
Nothing in this audit edits existing files; ledger predictions live here instead
(read-only mode forbids appending to the ledger — deviation D1).

## Verdict: PASS-READY with recorded ISSUES (no blocker)

Every sealed mark has a concrete computation in `fable_ears47_score.py`, panel sizes
match every denominator, temperatures/thresholds come from CAL only, and a CPU dry run
on random weights proves the pipeline executes end to end. The issues below qualify a
future PASS; they do not void the scoring machinery.

## (1) Marks vs scorer vs denominators — all check out

| mark | sealed bar | scorer lines | panel truth (recomputed) |
|---|---|---|---|
| R2-SAFE | 0 silent / 6,500; 0 trap written | `score_panel` 425–434; marks 585–588 | 2000+3000+1000+500 = 6,500 ✓; t_trap STATE = 0 ✓ |
| R2-NEG | ≤2% of 2,092 (≤41 STATE) | `_count_exec_fact` 667–679, STATE-only, RETRACT separate | wneg n = 2,092, all NO_FACT ✓ |
| R2-SEEN | ≥1,940/2,000; exec STATE ≥736 | `exec_stmt` 573–582 + 593–598 | t_seen 2,000, STATE 817 → ceil(0.9×817) = 736 ✓ |
| R2-NEW | ≥2,400/3,000; exec STATE ≥784 | same, 599–603 | t_new 3,000, STATE 1,205 → ceil(0.65×1205) = 784 ✓ |
| R2-NAMES | ≥300/500 | 604–605 | t_hard 500 (STATE 202) ✓ |
| R2-ASK | ≤25 over seen+new | 449–452, 606–608 | ASK golds: 369 + 544 ✓ |
| R2-WEB | exec ≥28/46; exact ≥85% of exec | `_count_exact` 682–691, 615–624 | wclosed 46/46 STATE → ceil(0.6×46) = 28 ✓ |
| R2-NEWREL | ≤1% of 1,500 (≤15) | `_count_wrong_seen` 694–711, 625–629 | wnewrel 1,500 ✓ |
| R2-ECHO | ≤65 recorded | 589–592 | — |

Registered unscorable counts re-verified exactly: t_seen/t_new/t_trap/t_hard/wneg/wclosed
0, wpos 13, wnewrel 11. Classes = 517 ✓.

## (2) Leakage — exact integer overlaps

- Synth↔synth sentences: t_seen×t_new 0, cal×t_seen 0, cal×t_new 0, t_seen×t_trap 0,
  **t_new×t_hard 8** (generator collisions; negligible, breaks strict independence).
- WebRED files: train∩dev 16 sentences; train∩heldout **7,476** sentences
  (same text, different relation annotation — expected in distant supervision, see below).
- Test panels vs train: wpos **813/1,806 triples** verbatim in train (memorization will
  inflate wpos — recorded only, not gated); wclosed **3/46 triples + 1 sentence**;
  wneg 38/2,092 sentences; **wnewrel 975/1,500 sentences seen in train, 0/1,500 triples**,
  0/40 relations in train (all 40 in heldout ✓), entities 1,190/1,727 seen.
- Synth train pool not on disk (trains remotely), but pool builder draws from the same
  generator with fixed independent seeds (47100/47107), so test-sentence collision with
  the pool is possible at the ~8/3,500 rate seen between panels — unmeasured, note only.

## (3) CAL-only discipline ✓

Temps: `train.py:213 fit_temperatures(model, cal_pack)` — CAL panel only. Thresholds:
`score.py:534–543 tau0_from_cal` on CAL parses before any test panel is scored; single-ear
taus likewise. No test data in either path.

## (4) Silent-wrong-write definition ✓

PASSMARKS §1 = scorer 425–434: verdict EXECUTE + act ∈ {STATE, RETRACT} + frame ≠ gold
(or unscorable). Matches doc 47 ("0 silent wrong writes"). `same_frame` demands exact
(act, rel, subj, obj, dir) equality, so a near-miss (right relation, wrong object) IS
counted wrong. Abstain-correct rule (REPHRASE + ≥2/3 raw-act majority) matches PASSMARKS.

## (5) Determinism ✓ with one caveat

Panels: fixed `PANEL_SEEDS` + hash-ranked newrel. Pool: `Random(47100)` families,
`Random(47107)` hearsay. Train: `Random(seed)` shuffle, `torch.manual_seed(seed)`,
sequential batches, fixed order. Eval: no shuffle. Caveat: CUDA/bf16 training sets no
deterministic flags — bitwise reproduction not guaranteed; per-seed reporting absorbs it.

## (6) CPU dry run (random init, seeds 4701–4703, unmodified scorer) ✓

Reproduce: `uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_audit83_dryrun.py` (~30 min CPU, one process).
Floors the real run must beat: tau0 = 0.0 → tau_exec = 0.5; SAFE 0 silent, 0 trap
written; NEG 0 STATE / 0 RETRACT of 2,092; t_seen 3/2,000 correct, 0 executed;
t_new 0/3,000; t_hard 0/500; WEB 0 executed; NEWREL 0/1,500. Brakes alone (esp. 3-seed
agreement) suppress every write at chance — the floor is ~0, so any EXECUTE in the real
run is learned behaviour, and any silent write is disqualifying, not noise.

## Predictions (ledger-append declined per read-only rule D1)

- P83.1 Real run tau_exec ∈ [0.5, 0.9]; tau0 > 0 (trained confidences will force it up).
- P83.2 Real SAFE: silent writes concentrate in wpos-style WebRED positives if any occur.
- P83.3 Real NEWREL rate < 1% partly via OPEN/REPHRASE, not via exact abstention — check
  the executed/wrong_seen split, not just the rate.
- P83.4 wpos recorded-correct will overstate web generalisation (813 memorised triples).

## What would make a PASS unconvincing

1. Passing NEWREL while 975/1,500 sentences are train-familiar — claim "novel-relation
   abstention", never "novel-sentence reading". 2. Citing wpos as web-reading evidence
   (45% triple memorisation). 3. A SAFE pass where EXECUTE counts are ~0 everywhere
   (all-brake abstention passes safety but fails coverage — that is what SEEN/NEW/WEB gate).
   None of these is present in the scoring code; they are reading rules for the results.
