# 55b — Q11 forgetting arm (QA-drilled baseline, fixed 60 s fine-tune) — RESULTS

**Registered run 21 Sep 2026, one clean invocation, seeds 5401/5402/5403. PASSMARKS sealed before the run. SCORE: PASS (B1–B5).**

## Frozen sources (sha256)

```
a75fdda01a7b01a459afa65b15904e5183e64402e44306151815a9e3a47b8fac  artifacts/fable-demo55b-20260921/PASSMARKS.md  (SEAL)
dfed0818e5d2609526c91298a629b12a6cec18c0f1ce0709f2a84b1b6af220a5  scripts/fable_demo55b_forgetting.py
773c7f999c90953e5fcf4523ee29ea46da7a4c80fa14305e5a6e8793657292fe  scripts/fable_demo55_advantage.py  (imported, not edited)
de80e7bca8fc7bc84e88308da4985427f19edb68fbf5a96654c397a019441333  scripts/fable_modes54_demo.py  (imported, not edited)
```

Exact reproduce command (Mac CPU, no install):

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
{ time uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo55b_forgetting.py --out artifacts/fable-demo55b-20260921 ; } \
  > artifacts/fable-demo55b-20260921/registered-stdout.txt 2>&1
```

**Frozen protocol (sealed):** baseline = demo55's QA-drilled dev variant as the REGISTERED training rule — 250 fixed full-batch updates (Adam lr 1e-3, grad-clip 1.0) on the 20 Q10 story+question→gold rows (STORY10 prefix; TinyTransformer 2L/d64/4H/FFN128, 128,512 params, same vocab). Fine-tune arm = fresh Adam lr 1e-3, full-batch next-token LM on the 5 new teaching lines, FIXED 60 s wall-clock per seed (steps counted). Eval prompts identical before/after per set (old Q10 always STORY10, new Q11 always STORY11), greedy decode ≤8, exact match after `norm`.

## Marks

| # | mark | threshold | result |
|---|---|---|---|
| B1 | notebook old Q10 AFTER new teaching | 20/20 | **PASS — 20/20** |
| B2 | notebook new Q11 | 5/5 | **PASS — 5/5** |
| B3 | wrong notebook writes, whole run | 0 | **PASS — 0** |
| B4 | baseline integers per seed + decode cross-check | 3/3 complete, no bar | **PASS — 3/3, cross-check ok** |
| B5 | whole registered invocation | < 600 s | **PASS — 399.5 s** |

## Outcome integers (never averaged)

| | notebook | base5401 | base5402 | base5403 |
|---|---|---|---|---|
| Q10 before /20 | **20** | 19 | 20 | 20 |
| Q11 before /5 | — (taught after) | 0 | 0 | 0 |
| fine-tune (60 s fixed) | — | 43,585 steps, loss 0.000000 | 41,214 steps, 0.000000 | 41,669 steps, 0.000000 |
| Q11 after /5 | **5** | 0 | 0 | 0 |
| Q10 after /20 | **20** | 0 | 0 | 0 |

QA training took ~71 s/seed (loss 0.057/0.0065/0.0063). Seed 5401 missed one Q10 before fine-tuning (19/20); the other two tied the notebook at 20/20. After ~42k fine-tune steps drove LM loss to 0.0, the baseline answered **0/20 old and 0/5 new in every seed**: it plainly did NOT keep the old facts, and still could not answer the new ones as questions (it recites the teaching lines' LM loss to zero but never saw a question about them).

## Deviations

1. QA training = 250 updates, not modes54's 600 (dev pilot 5591: 18/20 at 200, 20/20 at 300; 250 chosen pre-seal to fit the <600 s budget; no bar on the baseline so nothing hangs on it).
2. Old-Q10 eval keeps the STORY10 prefix after fine-tuning (same prompt as training/before) so the gap isolates weight change; new-Q11 uses STORY11 as in demo55.
3. Q11-before reported as context (0/5 ×3); not a mark.

## Predictions (ledger P234–P239, written before the run)

- P234 B1 20/20 → **TRUE**. P235 B2 5/5 → **TRUE**. P236 B3=0 → **TRUE** (0).
- P237 old-Q10 drops ≥5 in ≥2/3 seeds → **TRUE** (19→0, 20→0, 20→0).
- P238 new-Q11 after ≤2/5 every seed → **TRUE** (0/5 ×3). P239 B5<600 s → **TRUE** (399.5 s). 6/6 TRUE.

## Files

`PASSMARKS.md`, `SEAL.sha256.txt`, `registered-stdout.txt`, `demo55b-results.json`, `demo55b-transcript.txt`; design `design/v3/30-modes/55b-q11-forgetting-arm-mimo.md`; script `scripts/fable_demo55b_forgetting.py`.

## What it means

- On this frozen script, the notebook learns 5 new facts after training and keeps every old answer (**20/20 old after, 5/5 new, 0 wrong writes**): separate storage does not disturb old storage.
- The QA-drilled tiny transformer, which could answer the old questions (19–20/20), after 60 s of fine-tuning that perfectly fits the 5 new lines (loss 0.0, ~42k steps) answers **0/20 old and 0/5 new**: the new fitting destroyed the old question-answering and still did not install the new answers. The forgetting is total on these runs.

## What it does not mean

- **Not** "fine-tuning always destroys everything": one tiny model, one script, three seeds, Mac CPU. Bigger nets, rehearsal, or other schedules are untested here.
- Not that the net "learned nothing": its LM loss on the 5 lines is 0.0 — it memorized the lines as text; it cannot ANSWER about them.
- Not broad English, not GPU training, not learned mode switching; these runs only.
