# Width pilot: Bid C, the creative model (B2) widened cleanly, priced at $0 (2026-10-17)

This responds to the coordinator's order to price Bid C, the same way as Bids A and B. **Pricing only; nothing books.** The A / B / C ruling is Ben's, on the coordinator's recommendation.

Labels: **shown** = read from result files or code; **estimate** = to be replaced by a calibration measurement. Facts come from a record search (live git, 10-17) and were re-checked by the coordinator session where marked.

## 1. What Bid C tests

**The question:** does the creative model, trained 2.2× wider with nothing else changed, score better on the creative line's own sealed measures?

**Model (shown).** B2 is the `custom_io` `ledger` model with `copy=True`, S config (d256, 4 heads, 2 blocks, 8 loops, reader 2, mlp 4.8), **3,302,481 params**.
- Parent line: `custom_io/queue_local/33-pc-confirm-b2.txt`, branch `claude/b2-confirm-checkpoints`: `--model ledger --cfg '{"copy":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed N`.
- Parents s200–s205 are at commit f41d0f7d5.
- The creative code (`creative/` on `claude/project-thread-2zeaoc`) imports `custom_io` B2 and edits nothing there.

**The bug to fix (shown).** custom_io's B2 has 9 register / answer slots: `MAX_PROMPT, MAX_ANS = 208, 8`, so 8 characters plus EOS, and GEN reads the 9 register tokens. The creative parents carry this configuration.
- The record's fix is from the 8a-G line: the caps path sets 36 registers and max_ans 35, landed for G1 at 612f5c5b01 plus the caps overlay.
- **A code ruling is needed** on which fixed B2 Bid C uses: the custom_io B2 with the caps fix ported, or the 8a-G `src-b3` B2 without the Gemma front. Either way the fix applies **identically to both arms**: it is a baseline change, not an arm.

**Arms, one change: width.**
- **Base:** fixed B2, d256 / 4 heads.
- **Wide:** fixed B2, **d384 / 6 heads**: 7,223,071 params, **2.21× non-embedding** (shown, CPU count; the nearest to 2× at d_head 64, as in Bid A).
- Fresh parents from scratch at each width under the frozen B2 recipe, 24k updates. The fleet B2 parents s200–s205 cannot be reused, because they carry the unfixed configuration.

**Per parent, the creative pipeline as sealed for C2b (shown, `creative/c2b.py`):**
1. raw parent;
2. warm-up (2,048 add/mult rows, 4 visits, lr 3e-4, skills replay, seed 0);
3. N′ (stepping-stone sleep);
4. two nights per arm from N′.

Bid C keeps arms **N, W and R**, the three the marks need (W−N, W−R). H and M are dropped from this bid.

**Readout (shown, `creative/c2b.py`, `creative/marks.py`)** on the **sealed C2b test** (`creative/data/c2/test.jsonl`, 512 rows; held-out kinds affine, square, sq_plus, last_digit, double_add):
- first_try, plus W−N and W−R in points;
- reach@4;
- practised (256 add/mult, reach@32);
- skills harm (pooled-5 vs N′);
- the by-kind table and the model-free **blind baseline**, printed beside every result.

**Contrast:** per seed-index, d = (W−N)_wide − (W−N)_base, with W first_try alone as a co-headline. Paired by seed-index; the statistic runs over seed-indices (house rule; `custom_io/pilot_bars.py` on this branch).

**Measured spread at one size (shown, re-checked).** C2b W first_try counts across the 6 parents: 202, 208, 192, 173, 214, 218 of 512.
- W−N per parent: 39.26, 40.23, 36.72, 33.40, 41.02, 41.80. **Mean +38.74, sd 3.15** (n = 6); W first_try sd 3.24 points.
- This is between-parent spread at one size. The **paired width contrast's own sigma_d is unmeasured**, so these numbers size no bar (house rule).
- Expect sigma_d to be at least about √2 × 3.15 ≈ 4.5 if parents don't correlate across widths (suggested). That is near the v2-style UNRESOLVED tripwire (sigma above about 4), so a sigma gate after the first indices is mandatory.

**Headroom caveat (shown).** W already scores +38.7 over N. The model-free blind search finds a fitting right answer within 1,000 candidates on 55.5% of rows pooled, and on 100% / 99% of square / last_digit. So a width effect must be read **by kind**: affine, double_add and sq_plus have room (W−N +1.1 / +15.5 / +14.4); square and last_digit are near ceiling for a search.

## 2. Price (4090 at $0.43/h; estimates until calibration measures them)

**Basis (shown):**
- **B2 parents** (24k updates, BensPC 5070 Ti, sharing the device three ways): 59–253 min per parent.
- **Register-loop parents** (3.2M, Vast 5090): 17–20 min, about $0.23 per run including the box.
- **C2b creative stage:** "about 3 to 3.5 h per parent" for all five arms on BensPC (`creative/MAC-JOB-9.md`, itself an untested estimate). Actual per-run times are not committed.

**Per unit:**

| Item | Base | Wide d384 (≈1.4–1.6× per update) |
|---|---|---|
| Parent, 24k updates | 0.4–1.0 h, $0.17–0.43 | 0.6–1.6 h, $0.26–0.69 |
| Creative stage, N′ plus N/W/R nights (about 3/5 of the 5-arm C2b) | 1.5–2.1 h, $0.65–0.90 | 2.1–3.4 h, $0.91–1.44 |
| **Per paired seed-index (both widths, both stages)** | | **$1.99–3.46** |

| Line | Cost |
|---|---|
| **Calibration** (one parent plus creative stage per width, at a calibration seed never used in the verdict) | $2.1–3.6 (hard stop $5) |
| **Pilot: 6 paired seed-indices** (6, as in C2b; Ben's 5+ rule) | $11.9–20.8 |
| **Committed before the sigma gate** | **$14.0–24.4** |
| Contingent seed purchases (tranches of 2, cap 10 indices, so 4 more) | $3.98–6.92 per tranche; $7.96–13.84 for all 4 |
| Contingent horizon extension (2 pre-named indices; parents retrained at 48k at both widths, then the creative stage re-run) | $4.8–9.2 |
| **Expected pathway total** (Bid A's branch probabilities: 35% clean, 40% plus 2 indices, 25% plus 4; extension at 60%) | **about $20–36** |
| **Worst case (capped)** | **about $27–47** |

**Weeks and cap fit:**

| Week | Contents | Cost |
|---|---|---|
| Week 0 | Calibration | $2.1–3.6 |
| Week 1 | Pilot, 6 indices (can split 3 + 3 across two weeks; the sigma gate reads after the first 3) | $11.9–20.8 |
| Week 2 (contingent) | Seed tranches | $4–14 |
| Week 3 (contingent) | Extension alone | $4.8–9.2 |

- **About 3–4 weeks.** The largest single week is **≤ about $21**, under the $50 cap alongside other tracks.
- **Free route:** everything on BensPC, at **$0**, taking about 40–60 PC-hours (estimate). The C2b arms themselves ran there.

**What it displaces:**
- At most about 42% of one week's Vast cap at the peak week; or 40–60 BensPC hours.
- Those PC hours compete with Bid A's parents (if they go on the PC) and with the queued B3G2 jobs (NEEDS ATTENTION).
- No other Vast track loses its slot at the weekly level.

## 3. Prerequisites before Bid C could book (if chosen)

1. **Fix ruling:** which fixed B2 (above).
2. **The creative pipeline's own confounds at width.** Warm-up and sleep lrs (3e-4 and the night settings) were set for 3M. Hold them fixed (one change), and log the C8 analogue for the creative stage, or rule an lr probe.
3. **A frozen recipe citation** (parent line plus creative commit) and a **paired two-stage seed scheme**, as for Bid A (`reviews/width-pilot-v2-amendment-2026-10-17.md` §A–B).
4. **Bars written before runs**, in the v2 house form, sized from Bid C's own measured sigma_d at its gate. They need a by-kind headroom rule and the blind baseline printed beside them. Bar changes go to Ben.
5. **The sleep 6-seed confirm FAILED on harm** (s205 harm 3.9 against a limit of 2, `creative/results/fastsleep/RESULTS-2026-10-06.md`). The harm readout is therefore a live guard in Bid C, not a formality.

## 4. The three bids side by side (all pricing only)

| Bid | What it tests | Before the gate | Expected | Worst | Weeks |
|---|---|---|---|---|---|
| **A**: v2, far-join HO under L13, fresh T1SDR parents per width (amended per the Item 0 ruling) | Does width move the stalled far-join cell? | about $53.9–58.1 | about $111–118 | about $156–165 | 6–7 |
| **B**: T1SDR re-host on logic R2a (withdrawn 10-17 as a replacement for A; numbers kept for comparison) | Does width move logic R2a? | ≤ $12 (PC parents), ≤ $24 (Vast) | about $25–30 | about $59 | about 3 |
| **C**: B2 creative model widened cleanly (this file) | Does width move the creative measures (C2b)? | about $14.0–24.4 ($0 on BensPC) | about $20–36 | about $27–47 | 3–4 |

**Every figure above is an estimate.** Each bid's calibration replaces its unit prices before any booking.
