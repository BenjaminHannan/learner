# Fair scaling comparison: design (Premonition stage 2 of 4)

Status: DESIGN ONLY. No training, GPU use, spending, queue change or data authoring is authorised or performed by this file.
Written 2026-10-03 for the Premonition execution owner. Roadmap order from Ben's brief: current-size capability (English pilot, in progress) -> **fair scaling (this file)** -> notebook use -> sleep replay.

## 0. What I could and could not read

The execution owner's `docs/premonition-status/CURRENT.json`, `docs/premonition-recovery/CURRENT.json` and integrated design document v5 are **not on** branch `claude/premonition-launch-recovery-96c708` (head a163a3163). I asked the channel session to get them. Everything below is built from Ben's brief plus these pushed receipts, and each number is tagged:

- **[receipt]** read in `artifacts/cap256-launch/mixture10240-v1/PROTOCOL-v4.json` and `RESOURCE-FORECAST.json`: reasoner = "ordered D256 loop: two shared blocks, 8 experts/top2, 4 loops, thin32 translators, eight-token prefix, frozen full-FP32 LM"; 10,240 updates per arm; optimizer point forecast 1,170 s and 1,104 s for the two arms (about 0.11 s/update, a forecast, not a measurement); CUDA peak-reserved cap 15,032,385,536 B; checkpoint cap 134,217,728 B per arm; project cap 100 GiB.
- **[brief]** disposable benchmark control: 0.413 s mean update, 272.53 s whole job.
- **[CURRENT.json, reconciled 2026-10-03; commit 42552d9ee]** frozen LM = 1,170,340,608 params, 4,681,362,432 B in FP32 (shown); benchmark control mean complete step 0.4134 s, of which the four-loop core trains in 0.0282 s (about 7%), the reader 0.0005 s, native decode 0.045 s, teacher forcing 0.015 s; the original 49/32 English caps fail and 64/48 English-only caps were prepared but native qualification is unrun; the recent benchmark used a 10 GiB CUDA cap and a 16 GiB host guard, and a 12 GiB host guard had failed at load. CURRENT.json still records the shared-GPU hold; Ben's later release (relayed) supersedes it. Design v5, the ROOT handoff and the English TRAIN bank are not yet on the branch.
- **[unverified]** the exact parameter breakdown of the ~9M reasoner, the reader size, and any v5 conventions for pass marks. Section 6 lists what to confirm.

Do not treat this file as superseding v5. Where v5 disagrees, v5 wins and this file needs a patch.

## 1. The claim to test, and the claim not to make

**Claim under test:** with the frozen LFM2.5-1.2B language model, the reader interface and the data held fixed, a larger learned reasoner gets more fresh comprehension and meaning-transfer right, under matched conditions, than a smaller one, and the gain is credited to reasoner capacity rather than to extra data, extra updates, extra tuning or a lucky seed.

**Not claimed by this design:** that the end-to-end system scales (the frozen LM and the 8-token prefix are fixed), that scaling holds at 1B+ reasoner size, or that any size-trend extends beyond the sizes measured. A trend over 3-4 points is a description of those points.

## 2. Gates before any scaling run (all must hold)

- **G0 floor.** The base size (the English pilot's size) already shows fresh comprehension above chance and above the talker-alone / no-reasoner control in *both* seeds on the pilot's own fresh bank. Scaling from a floor of zero measures nothing. If G0 fails, this stage does not start; the English pilot's failure branch is followed instead.
- **G1 interface check (CPU).** Parameter and FLOP counts for every ladder point recorded; checkpoint fits the 134 MiB cap or the cap is explicitly raised by the owner (the cap breaks from D=384 up; see section 7).
- **G2 resources.** Resolved: Ben (2026-10-03 12:09 UTC, via the channel session) freed the PC GPU for Premonition full time. Still verify at launch that the Qwen service is not holding VRAM, and keep one execution owner and one queue.
- **G3 evaluation.** The fresh bank in section 5 is authored, independently checked, hashed and sealed before the first scaling run.

## 3. What scales, one axis at a time

The frozen LM is identical (same pinned revision, FP32, no fine-tuning, no causal-mask change) in every arm. The prefix stays 8 x 2048. Calculator-return encoding unchanged. Only one axis moves per ladder.

| Axis | Ladder | Needs Ben's approval? | Priority |
|---|---|---|---|
| A. Reasoner width D (blocks, experts, loops fixed) | D = 256 (base), 384, 512, 768 | No. Ben ruled scaling needs no approval (2026-10-03) | 1 |
| B. Experts: total vs active | 8/top-2 base; 16/top-2 and 32/top-2 (total grows, active fixed); and an equal-total dense width as the comparator | No (same ruling) | 2 |
| C. Loop count (4 -> 8) | train-time loops only | No. Ben removed the extra-reasoning-depth rule (2026-10-03) | 3 |
| D. Reader/translator width. Checked in code: the reader reads the frozen LM's *input-embedding table* (not cached LM states) through 2048->32->256 (about 78K params), and the prefix adapter is 259->32->GELU->2048 pooled to 8 tokens. So D here means the thin-translator hidden size, 32 -> 128 -> 512 [shown in `train_mixture.py:150-151`, `sol_translator_english_v6.py:41-45`] | 1x, 4x, 16x on the 32-wide hidden | No (same ruling) | 4 |

Loops are now an allowed axis: train-time loops 4 -> 6 -> 8 with width fixed at base, reported with FLOPs per update since loops multiply reasoner cost. Test-time-only extra loops (a 4-loop-trained model run for 6) is a cheap add-on; label it "untrained depth".

Reported parameter counts per point: total, active per token, and reasoner FLOPs per update. For axis A the points are roughly 1x, 2.2x, 4x, 9x of D=256 if the reasoner scales as D^2 [suggested, unmeasured]. "Roughly 9M, 20M, 36M, 80M" is therefore an estimate until counted in code.

**Code facts that shape the ladder** (checked by an Opus review against `scripts/`; torch absent, counts by hand):
- Core at D=256 is 9,007,790 params, about 136 D^2 (per block about 4 D^2 attention plus 8 experts of 8 D^2): 9.0M, 20.2M, 36M, 81M at D=256/384/512/768 [shown]. Active params at D=256 are about 2.7M [shown].
- "Same architecture, bigger" needs code work: D=256 is hard-coded in several files, and the v10 prefix checkpoint loader refuses any (state_width, hidden, prefix) other than (256, 32, 8) as a "changed thin-adapter architecture" (`sol_translator_english_ordered_v10.py:13`). Changing D means changing both translators and the loader [shown].
- **The interface may be the narrowest point.** All 8 prefix vectors sit in one 32-dimensional affine subspace, and the input side is 32 wide. Whether it limits results is untested. So axis A needs a built-in test: **widen the translator hidden 32 -> 128 at D=256.** If that gains as much as raising D, the interface, not the reasoner, is the bottleneck, and axis A results are not read as "the reasoner scales" [suggested; this is the test that would prove the axis-A reading wrong].

## 4. Matched conditions

Matched across every size within a seed pair:
- **same initialisation recipe.** The existing D=256 core is warm-started from a pretrained parent (experts copied from one MLP, zero-init router) and continues from update 10240 with Adam state carried over (`train_mixture.py:101-120`, `attention_core.py:20-26`). Wider points have no such parent. Choose one: (a) every size, base included, is trained from the same kind of fresh start (base re-run), or (b) every size gets its own parent pretraining of equal length. Updates are counted from initialisation, never from a continuation. Do not compare a warm-started base to from-scratch wide models;
- same TRAIN set and the same exposure schedule, precomputed and hashed (the v4 protocol already uses precomputed schedules with local RNG; reuse that mechanism);
- same optimizer family, same update count, same batch, same token caps (the core's query cap is 49 including EOS, `ordered_v2.py:13`; the brief's 64 in / 48 out is a separate English-pilot limit, confirm which applies), same warmup/decay shape;
- same stopping rule: fixed update count, no early stopping on fresh results;
- same number of sweeps over a hyperparameter budget for every size.

**Learning rate is the main unfairness risk.** A fixed LR tuned at D=256 will under-train larger models and produce a false "no scaling" result; a per-size tuned LR with unequal tuning effort produces a false "scaling". Rule: each size gets the same small LR grid (3 values, factor 2 apart, scaled by 1/D as the starting guess [suggested]), selected on a TRAIN-derived development split that never touches the fresh bank, using one seed; the other seeds then use the chosen LR unchanged. The grid, split and selection rule are frozen before the first run. The selection metric is dev cross-entropy, not exact-answer accuracy.

**Gradient clipping and router balance.** One global clip at norm 1 covers core, reader and prefix together (`sol_cloud_capability256_v1.py:227`); as D grows the core's gradient dominates and shrinks translator updates, confounding the LR rule. Clip per parameter group, or report how often clipping fires at each size [suggested]. The router load-balancing loss has weight 0 (`train_mixture.py:186`), so 16 or 32 experts risk routing collapse [weight shown, collapse suggested]; use one fixed nonzero aux weight for every MoE arm in axis B, and report expert-usage entropy.

**Axis B comparators at fixed D=256:** equal-total dense (MLP hidden 1024 x E) and equal-active dense (hidden 2048), plus the 8/16/32-expert top-2 points.

**Controls per size (matched-cost, so credit is not just size):**
1. *No-reasoner / talker-alone* control: must fail on fresh items, at every size.
2. *Plain reasoner controls, exactly defined.* Equal-FLOPs = the existing `sparse_unrolled4` (4 unshared rounds, about 35.8M params, `sol_spatial_poc_plain.py`). Equal-parameters = a 1-round control, which needs a code change (`fixed4_training` forbids it, `train_api_v2.py:13-18`; ordered plain hard-codes 4 rounds). Section 6's pass mark uses the equal-FLOPs control; the equal-parameter control is reported alongside. Neither is tuned less than the treatment.
3. *Data-matched memoriser check*: TRAIN exact-fit versus fresh accuracy per size. A rising TRAIN fit with flat fresh accuracy is the expected failure on a 24-passage bank and must be reported as such.

**Seeds.** The pilot uses two matched seeds per arm. For a trend over four sizes, two seeds cannot separate size from seed noise. Minimum for any scaling statement: **3 seeds per size**; with 2 seeds only, statements are limited to "the sign agrees in both seeds" for the largest-vs-smallest pair. Seed 0 and 1 reuse the pilot's seeds so base-size runs can be reused if (and only if) the pilot's recipe is byte-identical to this stage's; otherwise re-run.

**Data.** The pilot's TRAIN bank is small (24 passages, 48 questions). Capacity added to a tiny set mostly buys memorisation, so the main ladder uses a *larger* TRAIN set than the pilot but identical across sizes, with fresh families held out. If a bigger TRAIN set does not yet exist, authoring and independent checking of it is CPU work that can proceed now, before the GPU question is resolved. A 2 x 2 (size x data) view comes after the main ladder, never replaces it.

## 5. Fresh evaluation

- A new bank, authored and independently checked after the pilot finishes, **never** containing: the consumed 128-output questions, the pilot's fresh bank, any TRAIN or dev item, or anything from the reserved user/blind panels (not inspected by this design or by whoever authors the bank).
- Size: at least 200 questions in at least 40 story groups, six families kept balanced, so that story-group clustering is not mistaken for independent samples. At p = 0.5 and 200 questions the per-model standard error is about 0.035; because every size answers the same questions, paired differences have less variance, but the clustering means the real error is larger [suggested; compute from the actual bank].
- Sealed by hash before the first scaling run. Opened once per final checkpoint set. If any score on it informs a design change, it is consumed and a new bank is authored for the next claim.
- A separate *scale-dev* split (TRAIN-derived, disclosed) is used for LR selection and debugging; it is allowed to be reused.
- Primary outcomes (as in the pilot): fresh comprehension (strict exact final answer plus emitted EOS) and meaning transfer on the same bank. Paraphrase quality and calculator-call accuracy are secondary. Count "correct tool call, wrong final answer" separately, since that was 71 of 128 earlier outputs.
- Independently checked: answer keys and aliases by a checker who did not write them; numbers and any Luna word problems checked per the standing rule.

## 6. Pass and fail marks (to freeze before runs; numbers are proposals)

Let `acc(s)` be fresh primary accuracy at size s averaged over seeds, `Δ` = acc(largest) - acc(base).

| Result | Condition (all must hold) | What it supports |
|---|---|---|
| **Scaling shown (limited)** | G0-G3 held; Δ >= +0.08 absolute; 95% CI (bootstrap over story groups, then seeds) excludes 0; at least 3 of 4 sizes non-decreasing within 0.02 tolerance; sign of Δ positive in every seed; talker-alone control at floor at every size; looped beats equal-parameter plain at the largest size | The reasoner gets better with size on this bank with this recipe |
| **Not shown** | CI includes 0, or sign differs across seeds | No scaling claim; not evidence of no scaling |
| **Memorisation, not scaling** | TRAIN fit rises with size while fresh accuracy is flat or falls | Capacity is going to fitting; do more data first (follow-up: size x data) |
| **Wrong-way** | Δ <= -0.08 with CI excluding 0 | Larger is worse under this recipe; check LR selection first, then optimization instability |
| **Void** | Any matched-condition violation, bank re-use, seed-count shortfall, or LR-tuning asymmetry | Re-run; results not reported as scaling evidence |

The +0.08 mark and the 3-of-4 monotonicity rule are placeholders to be replaced by numbers derived from the bank's actual power once the bank exists. Whatever final numbers are chosen must be frozen before any fresh score is seen. **What would prove this design wrong:** if a deliberately shuffled-label control (same data, scrambled answer keys) shows an apparent size trend of similar size, the metric or recipe is measuring something other than comprehension.

## 7. Compute on the RTX 5070 Ti (16 GB)

Dominant cost is the frozen 1.2B FP32 LM forward and backward (gradients flow through it into the prefix), not the reasoner. So reasoner size changes cost less than proportionally [suggested; to be measured by the first CPU/GPU smoke].

- Time: forecast ~0.11 s/update (v4 receipts) to measured 0.413 s/update (benchmark control). Only about 7% of the measured step is the core, so ladder points change step time little [shown for D=256; larger D untested]. At 10,240 updates that is 20 min to 70 min per run, plus ~10 min evaluation. Ladder of 4 sizes x 3 seeds = 12 runs, plus 1 LR grid per size (3 short runs x 4 sizes), plus plain controls at the largest two sizes: roughly **10-30 GPU hours** [unverified range; first smoke narrows it].
- Memory: LM FP32 about 4.7 GB plus activations, so under the 15.0 GB v4 cap roughly 10 GB remain (under the 10 GiB CUDA cap used in the recent benchmark only about 5 GB do, so the cap must be raised for the larger points; the card has 16 GB) for for reasoner, Adam state (about 3x parameter bytes in FP32) and activations. A 100M-parameter reasoner needs about 1.6 GB for weights plus Adam; the 768-wide point is likely to fit, and a >300M reasoner is the realistic ceiling [suggested]. Larger needs a bigger card and is outside this stage.
- Checkpoints include optimizer state (about 12 B per parameter, `train_mixture.py:200`), so D=384 (about 240 MB) already breaks the 134 MiB cap; even a reasoner-only D=768 checkpoint is about 324 MB. Raise the cap (owner decision) or drop Adam state for D >= 384; either way respect the 100 GiB project cap and 1 GiB free-space safeguard.
- Spend: none requested. Everything here is PC-GPU-only. Any vast rental would need Ben's approval of the $-amount under the standing rule.

**CPU work that can start now without GPU:** author and independently check the larger TRAIN set and the fresh bank; write ladder configs and the parameter/FLOP counter; precompute exposure schedules and hash them; write the analysis script (bootstrap, pass-mark table) and test it on synthetic results; run fixture tests that every ladder point loads, preserves token IDs/masks/EOS/numeral spans/positions, and keeps the frozen LM pin.

## 8. Rulings from Ben (2026-10-03 12:09 UTC, relayed by the channel session)

1. Scaling width, experts or reader size needs no approval. The scaling rule is removed.
2. Loop count may be scaled. The extra-reasoning-depth rule is removed.
3. A larger checked TRAIN set than the 24-passage bank may be authored.
4. The PC GPU is free for Premonition full time.

Still binding from the brief: no LM fine-tuning, no causal-mask change, no forced answer copying, no digit auxiliary heads or latent-matching objectives; never inspect reserved panels; spending needs a fresh authorisation.

## 9. Order of work

1. Now (CPU): confirm numbers against v5; author bigger TRAIN set and fresh bank; fixtures; analysis script.
2. When the English pilot reports: check G0. If failed, stop and follow the pilot's failure branch.
3. When GPU is released: LR grid per size (seed 0), then ladder A, then B, then D; then C.
4. Report per section 6. Any change to the design after a fresh score is seen consumes the bank.

## 10. Plain-language summary

We want to know if a bigger "thinking part" actually understands more English, or just memorises more. We make the thinking part a few sizes bigger while keeping the language model, the data, the tuning effort and the training length identical, then test all of them on brand-new questions nobody has trained on or looked at. We only say it scales if the biggest beats the smallest by a clear margin in every seed and the "cheating" controls (no thinking part, same-size non-looping net) stay low. If bigger just fits the training questions better, that is reported as memorising, not scaling.

## 11. Review trail

An Opus subagent reviewed sections 3, 4 and 7 against the code (per Ben's rule that architecture goes to Opus). I spot-checked its claims on the reader input, warm start, aux weight 0, the (256, 32, 8) loader refusal, query cap 49 and optimizer-in-checkpoint, and they match the code. Edits above come from that review; the hand-counted parameter figures remain unverified until run in an environment with torch.
