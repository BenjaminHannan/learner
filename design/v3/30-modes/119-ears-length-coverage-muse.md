# 119 — Ears length/distribution coverage PREP (Muse; GPU wave launched by Claude)

Status: PREP complete on Mac CPU. No BensPC GPU job started here; the 3-seed
wave, 47-panel scoring, and reading94 scoring are specified exactly for
Claude. PASSMARKS sealed (`840c0bad…38174`); predictions P119.1–P119.6 in the
ledger.

## 1. Goal (one sentence)

Give the GPU wave everything it needs to test whether rung-2 ears trained at
the real length distribution — same SciBERT + FrameEars as exp 47, wider
window plus length-matched synthetic rows — execute on WebRED and read the
400-sentence real Wikipedia panel better than the 0/46 and 9–11/312 of exp 47.

## 2. Premise (verified, not assumed)

Exp 47 already trained on all WebRED-train rows, so the change is NOT "add
WebRED". The sealed failure is length: web-positive sentences are ~4x longer
than CAL (median 134 vs 35 chars; MAX_LEN 96 truncates 5.9% of WebRED-train),
confidence collapses on long text (1,494/1,806 below 0.3), relations go wrong
(38.8% match), and raw SimpleWiki exact is 9/11/10 (docs 95, 107). The honest
ONE CHANGE is therefore length/distribution coverage only: window 96 → 192
(99.372% of WebRED-train, 99.9995% of the SimpleWiki86 corpus — measured, §4)
and the 60k synth rows lengthened to WebRED's token-length histogram. Encoder,
head, classes, recipe, and CAL-based calibration are untouched.

## 3. Data (builder: `scripts/fable_ears119_data.py`)

- Base synth = 47's exact 60k rows (same generator functions, same POOL_SEED
  stream → same facts). Each row is lengthened with appended distractor
  clauses (locative/temporal/appositive, generic nouns only) to a target
  sampled uniform-over-rows from the WebRED-train token-length histogram
  (RNG stream 11900; cap 190). Appending never moves gold spans; a clause is
  kept only if `flags_of()` is unchanged, so no hearsay/negation marker leaks.
- Result: lengthened synth med/p90/p99 = 43/83/179 vs WebRED-train 41/81/183
  (before: 14/20/26). Pool = 60k lengthened + all WebRED-train reachable at
  192, with identity gates (synth == 60,000; kept ≥ 140,903; dropped ≤ 614;
  synth median in [38,48]) — else prep FAILs and no seed trains.
- Overlap: WebRED-train ∩ reading94 panel = 0 (normalised exact); the panel
  is copied to BensPC for scoring ONLY (pre-registered deviation D5).

## 4. Training + scoring (all sealed in PASSMARKS)

- `fable_ears119_train.py`: 47's recipe verbatim (2 epochs, batch 32, lr 3e-5
  cosine, bf16, freeze 0, seeds 11901–11903, temps on sealed 47 CAL), except
  per-batch dynamic padding (masked-identical compute; deviation D2, keeps the
  wave in budget). Steps = 2·ceil(kept/32), forecast ~8,826.
- `fable_ears119_score.py --score47`: the carried 47 gate with the doc-95
  corrected SEEN bar (executable STATE rows only: 654, bar 589) + W1
  (wclosed executed ≥ 23/46, 0 silent wrong). `--score-panel`: W2 (≥30
  correct, ≤5% wrong, ≥2/3 seeds) and W3 (raw exact ≥ 3× positional 27/33/30,
  ≥2/3 seeds). Exp-118 brake was absent at seal — no 118 gate applies.

## 5. Mac smoke (the only training on the Mac; discarded)

50 updates, real SciBERT fp32, 83 mixed rows incl. 8 long rows >96 tokens:
step loss 23.17 → 4.65; full-subset 24.73 → 5.15 (falls ✓). Panel-eval path:
20/20 decoded, runs only (no scores). 1.38 s/step; 91.6 s total.

## 6. Timing + memory (T-CLOCK recorded only)

≈ 35–45 min for 3 seeds + scoring vs the 2,700 s bar (anchor: 47's
14.8/7.9/7.9 min/seed; dynamic padding ≈ 1.2–1.3× per-step). Confidence
MEDIUM-LOW — the window is tight, stated not hidden. Memory ≈ 5–6 GB at
batch 32 / width 192 bf16 — fits 16 GB.

## 7. Forecasts (ledger, before the run)

P119.1 W3 ≥2/3 (0.20 — namespace mismatch untouched). P119.2 W1 (0.35).
P119.3 W2 ≥2/3 (0.25 — 107 found 0 correct at ≤5% for 47 ears). P119.4
carried 47 marks (0.45). P119.5 clock <2,700 s (0.60). P119.6 pool gates
(0.85).

## 8. What this does and does not claim

Does: whether length/distribution coverage unlocks execution and real-text
reads while holding template behaviour and safety. Does not: that any panel
number transfers to papers, that the relation-namespace problem (doc 107) is
addressed — it is explicitly not — or that the ears "understand" anything. A
registered FAIL stops the line per PASSMARKS §2.
