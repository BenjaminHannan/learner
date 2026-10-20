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

---

## Amendment 1 (2026-10-20, before any S3 run; §1-§7 marks unchanged)

Recorded under the card's own rule ("any deviation is recorded ... before the first run").
1. **Arithmetic correction in §2.** At the tiny d = 32 the S3 modules are 33 + 1,056 = **1,089** parameters, not
   2,209. At d = 128 it is 16,641, as stated. Checked against the modules: `config.parameter_breakdown()` equals
   `model.parameter_breakdown()`.
2. **Implementation choices inside §2 (not deviations):**
   - The address block is 16 episode rows after S2's 16 raw rows (rows 92-107 at the default sizes). Think skips
     it, as it skips the raw rows. It is never valid memory itself. `_decode_logits` drops it from memory and uses
     it only as the key source of the card and raw rows.
   - The S3 modules are built after `reset_parameters`, inside `torch.random.fork_rng`, seeded from
     `torch.initial_seed() + 0x53`. So the init is seed-dependent and consumes nothing from the global stream.
   - `addr_pool` is a copy of `writer.pool`; `addr` (`address.proj`) is N(0, 0.02) with zero bias.
   - NULL's address is zero, plus age and row type, like every card's.
3. **Pre-run tests (§2): pass.** `tests/test_premonition_card_address.py` covers:
   - flag-off identity to the reviewed D + S2 at 90077ef2b;
   - paired start at tiny and full size;
   - ring alignment through overwrite, with Think skipping the block;
   - K from the address and V from the row (hooked inputs);
   - finite training in every mode, with answers and wipes;
   - refusals;
   - the FLOP increment.
   Flag-off identity to 73b8e0224 is `tests/test_premonition_decoder_raw_cards.py`.

## Amendment 2 (2026-10-20, before any S3 run; §1-§7 marks unchanged)

This supersedes Amendment 1, item 2, bullet 2. The code changed under review (S3 review rounds 1-4), so the
record now matches the code that will run:
- **S3 module construction and init seed.** The S3 modules are built inside `torch.random.fork_rng()` (CPU and
  every CUDA stream restored), and the init seed is drawn there as `torch.randint(2**62)`.
  - The global streams after construction therefore equal D + S2's (tested: RNG state and `initial_seed`
    unchanged).
  - The `address.proj` init follows the seed **and** the stream position at construction. In the runner each
    arm is built right after `torch.manual_seed(seed)`, so it depends on the seed only.
  - `address.proj` is N(0, 0.02) from its own generator, bias zero. `address.pool` is a copy of `writer.pool`.
- **Keys.** `cross_kv` runs once over memory. The K half applied once to the 16 address rows replaces the keys of
  the 16 card rows and the 16 raw rows. This is the §2 rule unchanged, tested against an independent reference
  (K from address, V from rows).
- **Refusals.** It is refused on subclasses that override `build_store` or `_decode_addressed`, in addition to the
  S2 list.
- **Cell A VOID.** A seed is also VOID if the filed S2 distractor reading for that seed is absent.

## Amendment 3 (2026-10-20, before any S3 run; §1-§7 marks unchanged)

S3 review round 5 changed three implementation details. This supersedes the matching lines of Amendments 1-2.
- **Seed.** The draw inside `fork_rng` is mixed (64-bit LCG step) into `address.proj`'s generator seed, so it is
  never equal to the next value of the global stream.
- **Streams.** `fork_rng` covers CPU plus CUDA devices that are already initialised. It never starts a CUDA
  context.
- **Re-init.** `reset_parameters()` re-applies the S3 init rules (the pool copied from the writer; proj from the
  same seed). Tested.
- **Scope.** `card_address` is defined for `PremonitionMini` itself only. Every subclass is refused, including
  ones that swap the writer after init (card_pools). The runner uses the base class.

## Amendment 4 (2026-10-20, before any S3 run): the distractor pool needs a ruling. Marks unchanged.

The S3 code review (round 9) found that this card's §3/§4 wording is inconsistent with the S2 reading it points to.
- §3 says cell B trains with "2 random eligible non-gold, non-NULL **fact** cards (m02 `distractor_preload`)".
- §4 says `acc_d2` is "gold + 2 shuffled fact cards ... (S2 card §10 reading)".
- But m02's `distractor_preload`, and so the filed S2 §10 reading, draws from every eligible card, of which
  about 35% are fact lines (S2 card §10b).
- So "fact cards" and "the S2 §10 reading" are two different things.

The runner therefore takes a required `--pool {facts, mixed}` on both `run` and `summarize`, with no default.
That choice sets both the cell B training distractors and the primary `acc_d2`. Every run JSON records it,
`summarize` refuses runs from mixed pools, and every run also reports the other pool's reading.
- Cell A's reproduction check compares against the filed S2 reading of the same pool: `s2-distract` for mixed,
  `s2-distract-facts` for facts.
- **Mark 2 (55% = 39.84% + 15) is sealed as a number and is not changed here.** Whether it should instead be
  "best §10b S2 reading + 15" under the facts pool is the coordinator's call.

**Decision needed before any S3 run:**
- (a) which pool, facts (the card's words) or mixed (the card's S2 reference);
- (b) under facts, whether mark 2 stays 55% or follows the §10b S2 numbers.

**Ruling on amendment 4 (coordinator, 2026-10-20), recorded before any S3 run:**
- (a) **Pool: facts.** Run with `--pool facts`. The mixed-pool reading is reported as secondary (`d2_other_pool`).
- (b) **Mark 2 stays at the sealed 55%.** Lowering it to 51.04% after seeing the §10b numbers is not allowed, and
  55% is the stricter bar against the 36.04% fact-only reference.
- **Cell A's** reproduction check therefore compares against the filed §10b fact-only reading
  (`s2-distract-facts`: 299 / 369 / 315).
