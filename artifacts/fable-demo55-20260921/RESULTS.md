# 55 — Added demo beats (Q10 two-hop, Q11 learn-after-training) — RESULTS

**Registered run 21 Sep 2026, one clean invocation, seeds 5401/5402/5403. PASSMARKS sealed before the run. SCORE: PASS (A1–A5).**

## Frozen sources (sha256)

```
e2b50501020b325663110e53a1a3005a3b93b949988d8aa20e7bc71965d32da4  artifacts/fable-demo55-20260921/PASSMARKS.md  (SEAL)
773c7f999c90953e5fcf4523ee29ea46da7a4c80fa14305e5a6e8793657292fe  scripts/fable_demo55_advantage.py
de80e7bca8fc7bc84e88308da4985427f19edb68fbf5a96654c397a019441333  scripts/fable_modes54_demo.py  (imported, not edited)
```

Exact reproduce command (Mac CPU, no install):

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
{ time uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo55_advantage.py --out artifacts/fable-demo55-20260921 ; } \
  > artifacts/fable-demo55-20260921/registered-stdout.txt 2>&1
```

**Baseline budget rule (stated, sealed):** modes54's TinyTransformer (2 layers, d_model 64, 4 heads, FFN 128, word vocab over all demo texts; positional table widened 512→768 so the 600-token story fits; 128,512 params), one full-batch next-token sequence over the **byte-identical 120 teaching lines the notebook heard**, Adam lr 1e-3, grad-clip 1.0, exactly **600 fixed updates**, seeds 5401/5402/5403 reported separately, greedy decode ≤8 tokens, exact match after `norm`. The 20 questions are never trained on; asked only at evaluation. Q11 frozen = zero updates; Q11 fine-tune = fresh Adam lr 1e-3 on the 5 new teaching lines until wall-clock ≥ the notebook's Q11 beat (min 1 update).

## Marks

| # | mark | threshold | result |
|---|---|---|---|
| A1 | notebook Q10 | ≥ 18/20 | **PASS — 20/20** |
| A2 | baseline integers per seed (20+5+5), decode cross-check | 3/3 seeds, no performance bar | **PASS — 3/3 seeds, cross-check ok** |
| A3 | notebook Q11 | 5/5 | **PASS — 5/5** |
| A4 | wrong notebook writes, whole demo | 0 | **PASS — 0** |
| A5 | whole registered invocation | < 600 s | **PASS — 37.4 s** (shell 37.9 s) |

## Outcome integers (never averaged)

### Q10 — 20 two-hop questions over 120 taught facts

| | notebook | base5401 | base5402 | base5403 |
|---|---|---|---|---|
| correct /20 | **20** | 0 | 0 | 0 |
| train | — | 600 updates, 10.73 s, loss 0.002457 | 9.98 s, 0.002489 | 10.04 s, 0.002454 |

Per-question (nb / 5401 / 5402 / 5403): Q10.1–Q10.20 = 1/0/0/0 on every question (gold values: Keir, Rosa, Yara, Fritz, Marek, Finn, Milo, Naya, Ugo, Bram, Ilse, Bo, Iris, Pia, Bern, Krakow, Osaka, Cairo, Lima, Porto). Baseline emits story-continuations (`mother ->`, `teach …`, `city …`) — it never saw a question in training. **No question ties and none is won by the baseline.**

### Q11 — 5 brand-new facts taught after training

| | notebook | base5401 frz/ftn | base5402 frz/ftn | base5403 frz/ftn |
|---|---|---|---|---|
| correct /5 | **5** | 0 / 0 | 0 / 0 | 0 / 0 |

Fine-tune: 1 update each (a step ≈2 ms exceeds the notebook's whole Q11 beat of 0.0011 s, so the net got *more* wall-clock than the notebook and still scored 0/5). Frozen nets emit `teach`/`mother` continuations; new-name tokens exist in the vocab (0 OOV) but were never trained.

## What it means

- On this frozen script, the notebook answers **20/20** two-hop questions over 120 facts stored through LISTENING, and learns 5 brand-new facts after training was finished (**5/5**), with **0 wrong writes** — every saved row was exactly what Ben's line said.
- The plain transformer, given the *identical* 120 sentences under the *identical* 600-update budget, answers **0/20** — weights-only storage of these sentences does not yield question-answering — and cannot use 5 new sentences after training (**0/5 frozen, 0/5 even with equal-or-greater wall-clock**).

## What it does not mean

- **Not** "a transformer can't recite this script." modes54's baseline, *drilled on the question–answer pairs*, ties the notebook 8/9. We also ran that QA-supervised variant during development (dev seeds 5591/5592/5593, before sealing — not the registered protocol): it memorized all 20 pairs, **20/20/20, tying the notebook**, and its integers are recorded here so nothing is hidden. The registered Q10 follows the beat's spec: trained on the teaching lines, asked the questions.
- Not broad English, not GPU training, not learned mode switching, not long-run stability; one script, these runs only.

## Deviations (all stated in PASSMARKS/design before the run)

1. Positional table 512→768 (story length); reserved `<UNK>` id added to the vocab (0 hits).
2. Fine-tune rule = ≥ notebook wall-clock with a **minimum of 1 update** (a single step overshoots the notebook's 1.1 ms beat).
3. Batched greedy decode replaces modes54's per-row loop for speed; proven token-identical per seed (cross-check folded into A2).
4. Development (pre-seal): the QA-supervised variant above was run on dev seeds only; registered protocol chosen per the beat's wording ("trained on the same 120 teaching lines") and disclosed per this section. No registered FAIL; nothing re-run.

## Predictions (ledger P228–P233, written before the run)

- P228 notebook ≥18/20 → **TRUE** (20/20). P229 baseline ≤5/20 every seed → **TRUE** (0/20/20/20). P230 notebook Q11 5/5 → **TRUE**. P231 frozen 0/5 ×3 → **TRUE**. P232 fine-tuned ≤1/5 and below notebook ×3 → **TRUE** (0/5 ×3). P233 A4=0 and A5<600 s → **TRUE** (0; 37.4 s).

## Files

`PASSMARKS.md`, `SEAL.sha256.txt`, `registered-stdout.txt`, `demo55-results.json`, `demo55-transcript.txt`, `DEMO-ADDENDUM.md`; design `design/v3/30-modes/55-demo-advantage-questions-mimo.md`.
