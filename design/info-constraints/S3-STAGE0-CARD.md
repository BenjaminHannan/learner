# RUN CARD: S3 Stage 0, `card_address` on the base D + S2 (far-fact toy)

**Status: SEALED BEFORE ANY S3 CODE OR NUMBER EXISTS.** Committed 2026-10-20 under the coordinator's 10-20 GO
("write and SEAL the S3 Stage 0 card now, on the base D + S2, one change"). **No run starts until the
coordinator sends a clean review of the S2 code.** The S3 code is written after that verdict, so the head under
review does not move. It must implement §2 exactly. Any deviation is recorded in §0 of an amendment **before**
the first run, or the run does not count. Nothing in §1-§7 moves after the first run starts.

## 0. Why two cells
- **The gap.** S2 Stage 0 trained on single gold cards. Neither arm ever had to choose, and the filed S2
  distractor reading (27.7 / 27.7-39.8%, about the 33.3% random-card rate) measures a model never trained
  to choose.
- **The precedent.** m02's bypass trained with gold + 2 distractors reached 623/1024 at n = 2 (validation,
  first token; `reviews/opus-milestone-02-m02-20260918-232457.md`, §2f). So training with distractors is
  needed for any choosing test.
- **Cell A** keeps the S2 protocol exactly. Its control is the filed S2 treated arm, reproduced, so S3 is read
  directly against the S2 numbers just filed.
- **Cell B** trains both arms with gold + 2 distractors. That is where choosing can be learned, and it is the
  primary cell.
- In both cells the arms differ by one flag.

## 1. Arms (paired, seeds 0, 1, 2)
- **Control:** D + S2, i.e. `MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
  decoder_raw_cards=True)`.
- **Treated:** the same plus `card_address=True`. One change.
- **Paired start:** every shared parameter is identical at the same seed, and the global RNG stream after
  construction is identical. The S3 modules are built and initialised inside `torch.random.fork_rng`, as
  `premonition/card_pools.py` does, and a test must prove it.

## 2. The change (S3 `card_address`, to be built behind a default-off flag)
- **Address.** A second per-line pool `addr_pool: Linear(d, 1)` and a projection `addr: Linear(d, d)` on the
  same causal reader states as the writer: `a_l = addr(Σ_t softmax(addr_pool(h))_t h_t)`, using the masked
  per-line softmax pool of `CardWriter` / `card_pools.pool_lines`.
  - `addr_pool` is initialised as a copy of `writer.pool`.
  - `addr` is initialised N(0, 0.02) with zero bias, inside `fork_rng`.
  - Cost: 129 + 16,512 = 16,641 parameters at d = 128 (2,209 at the tiny d = 32), reported apart from the band.
- **Store.** `CardStore` carries `addresses [B, L, d]`; NULL gets a zero address.
- **Episode.** On insert, each card's `a_l + age(bucket) + row_type[ROW_CARD]` goes into an address block aligned
  with the ring (same slot, overwritten together). Think never reads or writes it.
- **Decoder.** For the 16 think card rows and the 16 S2 raw rows, the cross-attention **keys** come from
  `cross_kv`'s K half applied to `_norm(address row of that slot)`. The **values** stay as today (from the row
  itself).
  - Question, slot and register rows are unchanged.
  - No new decoder parameters.
  - With the flag off, the decoder is the base text.
- **Refusals.** It needs the store and `decoder_raw_cards`. It is refused on subclasses that own the episode or
  decode path (the S2 guard list).
- **Tests (required before any run):**
  - flag-off bit-identity to 73b8e0224 (the S2 harness);
  - flag-off identity to D + S2 when only `decoder_raw_cards` is on;
  - paired start;
  - address rows aligned through ring overwrite;
  - card-row keys equal K(address) and values equal V(row);
  - finite training in every mode.

## 3. Setup (fixed here)
- **Common to both cells:** far-fact toy v16 (`ToySpec()`), 16 visits per step, `label_free`; train stream
  `toy_stream(spec, 16, 101)`.
  - Optimiser: AdamW lr 1e-3, warmup 100, betas (0.9, 0.99), eps 1e-8; weight decay 0.1 on dim ≥ 2 tensors;
    clip 1.0.
  - 2 think loops, 800 steps, 1 thread per run, CPU, $0.
  - Test split `toy_set(spec, 16, 16, 303)`, 1,024 questions, scored once at the end.
- **Cell A (S2 protocol):** `forward(mode="gold", loops=2, weights={"ans": 1.0})`, exactly S2-STAGE0-CARD §2.
  The control arm must reproduce the filed S2 treated result (1024/1024; distinct 16/16) and its filed
  distractor reading (387 / 284 / 408), else the cell is VOID for that seed.
- **Cell B (distractor training):** each step preloads the gold card plus 2 random eligible non-gold, non-NULL
  fact cards of the visit, in random order (m02 `distractor_preload`; generator seed 1000 + model seed).
  - Then 2 think loops, with the answer loss after each loop through the standard decode path, averaged over
    loops (m02 `arm_loss` "+distractors").
  - Data order and distractor draws are identical across arms at a seed.

## 4. Readouts (every cell, arm and seed)
- `acc_gold`: gold card alone, 2 passes, exact match (S2 card §2 reading).
- `acc_d2`: gold + 2 shuffled fact cards, generator seed 7002 (S2 card §10 reading). **Primary in cell B.**
- `acc_nocard`: no card, 2 passes.
- `distinct_256` / `distinct_1024` for each reading. Also `predicts_distractor_value` for `acc_d2`.
- Diagnostic, reported: treated address-pool mass on the toy line's token roles (position 1 ENT, 2 REL, 3 VAL,
  rest filler), and the writer pool's mass on the same.

## 5. VOID rule (coordinator 10-19 / 10-20)
- A seed's pair in a cell is **VOID** if the **control** gives one distinct answer over the first 256 test
  questions on that cell's primary reading. That is `acc_d2` in cell B and `acc_gold` in cell A.
- Cell A is also VOID for a seed if its control fails the §3 reproduction.
- VOID cells are evidence about nothing and are left out of every count.
- n valid seeds ≥ 2 per cell is needed for any verdict; otherwise INCONCLUSIVE.

## 6. Pass marks (written before any S3 code or run)
d_s = treated − control on the named reading. "Every" means every valid seed.
- **PASS** needs all of:
  1. **Choosing, paired (cell B):** `acc_d2` d_s ≥ +15 points on every seed, and mean(d) − 2·SD(d)/√n > 0.
  2. **Choosing, against the filed S2 numbers:** cell B treated `acc_d2` ≥ 55% on every seed. That is the best
     filed S2 distractor reading (39.84%, seed 2) plus 15 points, and well above the 33.3% random-card rate.
  3. **Reading kept:** treated `acc_gold` ≥ 95% on every seed in both cells.
  4. **No-card guard:** treated `acc_nocard` ≤ 9.25% (chance + 3 points) on every seed in both cells.
  5. **No harm under the S2 protocol (cell A):** treated `acc_d2` is not more than 3 points below its control
     (the reproduced S2 arm) on 2 or more seeds.
  6. Treated `distinct_256` > 1 on every primary reading. Every run, VOID or not, finished 800 steps with
     finite gradients.
- **FAIL:** cell B mean d ≤ +3 points, **or** cell B treated `acc_d2` < 40% on 2 or more valid seeds.
- A firing FAIL or proves-wrong rule (§7) blocks PASS. The card ranks neither.
- **INCONCLUSIVE:** anything else, reported as is, with no re-run under changed marks.

## 7. The result that would prove S3 wrong
- In cell B, |d_s| ≤ 3 points on at least 2 valid seeds: a learned address does not help choosing even when
  choosing is trained. Or the no-card guard fails for the treated arm: its answers do not come from the cards.
- If S3 is proved wrong **and** the treated address pool puts ≥ 0.5 of its mass on ENT + REL tokens, the reading
  is "a usable address exists and the decoder does not use it". That points at the decoder query (N16), not the
  address. Reported, not a verdict.

## 8. What a PASS does and does not buy
- **Buys:** a learned address, with no layout parse, lets the decoder choose the right supplied card among three
  on the far-fact toy.
- **Does not buy:** own retrieval; two-hop; the ladder toy; the village ruler. The ladder-toy address-keys
  oracle (503/512 choosing) remains the ceiling reference, not tested here.
- Next, only after a PASS: a Stage-1 bid priced by measured seconds per update (E5), held until the coordinator
  rules.

## 9. Raw outputs
`artifacts/claude-infoconstraints-20261018/s3-stage0/cell{A,B}-{control,treated}-seed{0,1,2}.json` and `.log`,
plus `summary.json` applying §5-§7 verbatim. Runner: `scripts/info_s3_stage0.py`, written with the S3 code
after the S2 review verdict.
