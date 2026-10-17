# Width pilot v2: amendment package after the coordinator's Item 0 ruling (2026-10-17)

This files back what the ruling asks for: the frozen parent recipe (by repo citation), the two-stage seed scheme, the amended text for spec §2, §5, §6 and §7, and the extended Item 1 bid. It is drafted by the size-versus-stall session for coordinator review, and nothing books from it.

Labels: **shown** = read in code or result files; **estimate** = to be replaced by the Item 1 measurement.

Ruling adopted as written: **reading (a′)**. For each (width, seed-index), a fresh parent is trained under the frozen T1SDR recipe, then the exact L13 join phase runs on that run's own parent. No run continues from an existing checkpoint. Depth counts distinct blocks (base depth 2; n_loops 8; 16 effective passes as a note), so **axis-gate condition 2(a) fails**, and the gate can pass only through an explicit 2(b) decision with the post-amendment totals below printed. The redirect stays live.

## A. Frozen parent recipe, by repo citation (shown)

- **Recipe source:** `custom_io/queue/t1c2/80-t1sdr-s204.sh` on branch `claude/project-thread-94a956` (file at commit 4d294b665). It is the T1SDR 6-seed confirm line, "seeds 202-205 of T1SDR as built, recipe unchanged".
- **Code pin:** `custom_io` at **f6d724cffc86e028b4286cc17a2d022e78541f77** (branch `claude/custom-reader-talker-4x309r`), checked out sparse to `custom_io/`, with the HEAD asserted equal to the pin.
- **Command:**
  ```
  run T1SDR_s<P> --model tool --cfg '{"span_copy": true, "span_idx": true, "span_end": true, "ans_drill": 0.25}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed <P> --log-every 500 --final-eval --save-preds
  ```
- **Defaults in force** (shown in RESULT.json of T1SDR_s200): warmup 300, grad_clip 1.0, order shuffled, max_ans 8, AdamW (0.9, 0.95), weight decay 0.1 on matrices, cosine to 10%.
- **Data:** the box's seed-1 200k build, `skills_curriculum.build --train 200000 --dev-per-cell 40 --seed 1` from branch `claude/project-thread-y0sxwe`, hash-checked against `FULL-BUILD-MANIFEST-200k-seed1.json` (`custom_io/box/box.sh`).
- **Width change, the only change per arm:** cfg gains `"d": D, "n_heads": H`.
  - **Base** (1×): d256 / 4 heads, 3,314,132 params.
  - **Wide:** **d384 / 6 heads** gives 7,288,226 params, 2.22× non-embedding. Exact 2× is not reachable at the fixed d_head 64 (Item 0 interim §5). **Still open: the coordinator has not yet ruled d384 vs exact 2×.** It is priced here at d384.
  - **0.5× arm** (gated follow-on): **d192 / 3 heads** gives 1,907,694 params, 0.57× non-embedding, the nearest at d_head 64.
  - The pinned `tool` / `Ledger` constructors take `d` and `n_heads` (shown at f6d724). Between the pin and the 94a956 head, `tool.py` differs only by a loss refactor, so the counts hold.
- **Parent-stage logging:** the pin has no C8 flag. The parent stage runs **at the pin, unchanged**. C8 is read in the join stage, where the ruling requires it (`learn_probe.py`; draft on this branch, commit 5ce1889). Adding the custom_io C8 draft (bit-identical by test) to the parents would move the pin, so the coordinator must say so explicitly if wanted.
- **Handoff:** the parent's `checkpoint.pt` goes to the join stage via `learn_probe train --parent <that checkpoint>`. **Parent DEV at handoff** is printed per run: custom_io final eval, in_dist and pooled-5.

## B. Two-stage seed scheme (filed)

- **Seed-indices i = 1…10** (1–5 the pilot, 6–10 the SE-rule purchases, in order).
- **Run seed:** **P_i = 700 + i** (701…710).
  - It is used in **both** stages: custom_io `--seed P_i` (init, shuffled order) and `learn_probe train --seed P_i` (torch seeds, data order `RandomState(P_i)`, KL replay stream `RandomState(P_i + 11)`).
  - It is the same P_i at every width.
  - 700s are unused by any line in the record. The fleet uses 200–205, the B1 students 300s, 8a/G1 400s, and the far forgetting runs 31001 / 93301.
- **Calibration seed (Item 1 only):** **P_0 = 700**. It is never a pilot or purchase index, and its parents and runs never enter a verdict.
- **Extension pre-named:** seed-indices **1 and 2** (P = 701, 702).
- **What pairing covers** (spec §3, extended into the parent stage):
  - identical parent data order, identical join data order and mixture draws, identical KL-replay index stream, identical eval sets (HO 3aba6de1…, HO2 eed9703a…, DEV);
  - identical seed values, recorded on each run card.
- **What pairing cannot cover:**
  - Init (each shape draws from its own scale).
  - The **diary content.** The replay pool is built from each run's own parent (`build_parent_diary`), so with the index stream identical, the rows' targets are parent-mediated.
  - This is the accepted "pipeline contrast" scope.
- **0.5× arm:** the same P_1…P_5.

## C. Amended spec text

These are drop-in replacements for the coordinator to adopt. Bars are **unchanged** numerically; bar changes go to Ben.

**§2 Dose (amended).** Each run has two stages at one width:
- (i) **parent stage:** 24,000 updates under the frozen T1SDR recipe (§A), from random init;
- (ii) **join stage:** 4,000 updates of the exact L13 recipe (every weight, lr 1e-4, batch 64, L5 join rows, K-FAC graded mask softness 10 refreshed every 500, 32 diary rows per update, 10 × KL to **this run's own frozen parent**).

5 paired seed-indices × 2 widths = 10 runs, so 10 parents and 10 join stages.
- The **horizon lock extends the join stage only.** Seed-indices 1 and 2 continue from their 4,000-update join checkpoints to 12,000 on the same parents, with ladder checkpoints added at 5,500, 8,000 and 12,000. Parents are never re-trained or extended.
- Everything else in §2 stands.

**§5 Readouts (amended additions).**
- Per run: parent n_params, the parent's final train loss, **parent DEV at handoff** (custom_io in_dist and pooled-5), parent host and seconds per update.
- The parent's own C8 is not read (pin unchanged).
- Per size: the mean and spread of parent DEV, printed beside the join results so a weak wide parent is visible before any join wording.
- **Licensed sentences:** "2× width" reads "**2.22× non-embedding width (d384), applied to both the parent and the join stage**". Each sentence gains: "this is a pipeline contrast: each run's parent was trained at its own width under the frozen T1SDR recipe."

**§6 Bars (amended labels only).** G0's label is replaced by: "**Fresh-parent vs fleet-parent provenance:** L13's 14.05% came from the fleet parent T1SDR s200; every pilot run uses a freshly trained parent of its own width, so no distance from 14.05% is a replication pass or fail." The comparable sanity reads and every bar are unchanged.

**§7 Costs (re-issued with a parent line).** All 4090 at $0.43/h.
- Parent prices are **estimates** until extended Item 1 measures them. They are not bookable figures, and the old $50.04 is void.
- **Parent basis (shown):** a 3M T1SDR, 24k updates, took 2,116 s at 11.34 updates/s (q70 rented 5090 box), 4,441 s on BensPC's 5070 Ti, and 7,809 s on the t1c2 5090 box (two concurrent).
- Estimates per parent on a 4090:

  | Parent | GPU-h | Cost |
  |---|---|---|
  | Base | 0.6–1.2 | $0.26–0.52 |
  | Wide d384 (≈1.35–1.6× slower per update, from tf3m→tf10m's 1.58× at 3.3× params) | 0.9–1.9 | $0.39–0.82 |
  | 0.5× d192 | 0.5–1.0 | $0.22–0.43 |

- **Join-stage basis (shown):** `learn_probe.py train` is **CPU-only**: `torch.set_num_threads(threads)`, and batches go through `to_device(…, 'cpu')`. L13 ran at 4.6 s/update on 4 CPU threads. A rented 4090 box's join stage is therefore box-CPU-bound unless the code moves to the GPU.
  - The spec's 7.2 s / 12.24 s per update (8.0 / 13.6 GPU-h) stand as **estimates** for Item 1 to measure.
  - The box is billed per hour whatever is used.

| Line | Cost (estimate until Item 1) |
|---|---|
| Item 0 | $0 |
| **Extended Item 1** (§D) | **about $1.4–2.1** |
| Base pilot joins (unchanged) | $48.38 |
| **Pilot parents (5 base + 5 wide)** | **$3.25–6.70** |
| Diagnostics | ≤ $0.92 |
| **Committed before the sigma gate** | **about $53.9–58.1** |
| Contingent extension (joins only, parents reused) | $37.41 |
| Contingent seed purchase, per paired index (joins $9.68 + 2 parents $0.65–1.34) | $10.33–11.02 |
| Contingent 0.5× arm (joins $12.15 + 5 parents $1.10–2.15) | $13.25–14.30 |
| **Expected pathway total** (Stage 2 branch probabilities kept: 35 / 40 / 25) | **about $111–118** |
| **Maximum capped pathway total** | **about $156–165** |

How the totals are built:
- **Expected:** $105.32, plus the pilot parents, the Item 1 parents and the extra Item 1 line, plus 0.40 × 3 + 0.25 × 5 purchase-index parents, plus the 0.5×-arm parents at the 0.75 probability the Stage 2 branches imply.
- **Maximum:** $148.00, plus the pilot parents, Item 1 parents, 5 purchase-index parents and the 0.5×-arm parents.

**Weekly split** (each week < $50 of new spend):

| Week | Contents | Estimate |
|---|---|---|
| Week 0 | Item 0 $0 + extended Item 1 | $1.4–2.1 |
| Week 1 | Tranche A: seed-indices 1–3 × both widths, parents + joins ($29.03 + $1.95–4.02) | $31.0–33.1 |
| Week 2 | Tranche B: seed-indices 4–5, parents + joins ($19.35 + $1.30–2.68) + diagnostics ≤ $0.92 | $21.6–23.0 |
| Weeks 3–6 | As spec, with parents added to purchase and 0.5× weeks: purchases $20.7–22.0 per tranche of 2; 0.5× $13.3–14.3; extension $37.41 alone | — |

**Axis gate, 2(b) totals to print (post-amendment):**
- Width-then-depth: about $113–118 without a base rebuy. That is pilot about $53.9–58.1, plus Item 7's two points ($59.56; their parent stage is unpriced in the spec and to be added if depth runs on fresh parents too). Add about $19.5–21 if the base arm must be rebought (the spec's $18.17 plus its parents).
- Depth-first: about $59.56 plus the shared base arm.
- Base depth 2 is inside the redirect condition, so the 2(b) decision must be written explicitly before booking.

## D. Extended Item 1 bid (for ruling; nothing books)

| Field | Value |
|---|---|
| **What** | (1) **One parent build per width** at the calibration seed P_0 = 700: base d256 and wide d384, the full 24k-update frozen recipe, timed per update, with parent DEV recorded. (2) **The original Item 1 join calibration on those two parents**: a short L13 join run per width (about 300–500 updates), timing seconds per update, measuring the eval-pass cost on HO, and verifying that the C2 loss-share fields and the C8 update-RMS fields exist in `learn_probe.py`'s output, with probe logging not altering the training step (spec §4). |
| **Venue (named)** | One rented **RTX 4090 on Vast**, the spec's booking line. The billed rate recorded in the project is $0.416–0.456/h. The join stage runs on that box's CPU (above); its core count is recorded on the run card. |
| **Cost** | Parents about $0.65–1.34 (estimate), plus the original Item 1 1.72 GPU-h, $0.74. **Total about $1.4–2.1**, with a hard stop at $3.00. |
| **Buys** | Measured parent seconds per update at both widths (replacing every parent estimate above); measured join seconds per update and eval-pass cost (replacing the spec's ESTIMATE factors, including the ladder-thinning trigger at 0.15 GPU-h); C2/C8 delivery verified. A re-issued §7 with measured numbers follows before any Tranche A booking. |
| **Displaces** | About 3–4% of one week's $50 Vast cap. No other track loses a slot. |
| **Prerequisites before it books** | Code review of the two C8 drafts. Two code changes to `learn_probe.py`: a parent list and sha map in place of the hard-coded s200/s201/s204 assumptions, and the diary built from the run's own parent. Also the d384 vs exact-2× shape ruling. |

## E. Status of the ruling's five conditions

| # | Condition | Status |
|---|---|---|
| 1 | Parent stage priced by measurement | Extended Item 1 is bid in §D; §7 is re-issued with an estimated parent line, to be replaced by the measurement |
| 2 | Parent recipe frozen by repo citation | §A |
| 3 | Two-stage seed scheme filed | §B |
| 4 | Spec §2/5/6/7 amended | §C |
| 5 | C8 confirmed in `learn_probe.py` | Draft on this branch (5ce1889); off and on bit-identical, including the kfsoft guard path, on a stand-in parent. **Awaits code review.** |

Also done under Q50: **HO2 is frozen** (seed 93703, 420 rows, sha256 eed9703a…), and HO1's hash was re-confirmed (3aba6de1…). See `reviews/width-pilot-item0/HO2-PRENAME.md`.
