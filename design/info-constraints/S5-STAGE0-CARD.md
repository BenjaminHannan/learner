# RUN CARD: S5 Stage 0, `dec_ent_match` (an entity-match bias in the decoder's card attention), base D + S2

**Status: SEALED BEFORE ANY S5 CODE OR NUMBER EXISTS.** Committed 2026-10-20 under the coordinator's 10-20 GO,
after the Opus design review of the S3/S4 "mechanism never engaged" pattern. The design and marks below are the
coordinator's, recorded verbatim in substance. The code is built to §2 after this commit. It runs only after ONE
focused built-in review on main...head is clean (blocking items fixed, the rest logged). Implementation deviations
go into an amendment before the first run. §3-§7 do not move after the first run starts.

**Model size: the tiny preset (d = 32, about 80k parameters), as in every Stage 0 so far.** Not the d = 128 /
2.1M model.

## 1. Arms (paired, seeds 0, 1, 2)
- **Control:** D + S2, i.e. `MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
  decoder_raw_cards=True)`.
- **Treated:** the same plus `dec_ent_match=True`. ONE change.
- **Paired start:** the only new parameter is the scalar κ_d = 0, built after `reset_parameters` with no RNG draw.
  So every shared weight and the RNG stream are identical at the same seed.

## 2. The change (S5 `dec_ent_match`, behind a default-off flag)
- **Score bias.** In the decoder's cross-attention, every memory row of card l (its think card row and its S2 raw
  row, same ring slot) gets `+ κ_d · m_l` added to its attention score, in every head and at every answer position.
  - `m_l = 1` if the card's pointerizer entity ids (`store.ents`) include an entity id that occurs in the question
    span (`q_span` tokens), else 0. NULL and entity-free cards get 0.
  - **Label-free:** it uses only the model's own input (pointerized tokens), never gold or answer labels.
- **κ_d** is one scalar parameter, initialised to 0. Its gradient is non-zero from step 1, because the score
  derivative does not pass through κ_d = 0 the way S4's did.
- **Unchanged:** values, keys, every other row, and Think. With the flag off, the base text runs.
- **Refusals:** it needs `decoder_raw_cards` and the store; it is refused together with `card_address`; it is
  defined on `PremonitionMini` only.
- **Pre-run tests (required):**
  - flag-off identity to the reviewed code at 7a2f5a32a with only S2 on;
  - flag-off identity to 73b8e0224 (S2 harness);
  - paired start;
  - κ_d = 0 gives identical decoder outputs;
  - the bias lands exactly on the matching card's two rows (attention logits by hand);
  - ∂L/∂κ_d ≠ 0 on a batch with a matching card;
  - finite training in every mode;
  - refusals;
  - config dicts and digests with the flag off unchanged.

## 3. Protocol (both arms)
- **Common:** far-fact toy v16, 16 visits per step, `label_free`, train stream `toy_stream(spec, 16, 101)`;
  AdamW betas (0.9, 0.99), eps 1e-8, weight decay 0.1 on dim ≥ 2 shared tensors; clip 1.0; 1 thread; CPU; $0.
  2 think loops throughout.
- **Stage 1:** the S2 protocol (S2-STAGE0-CARD §2): 800 gold-only steps, lr 1e-3 with warmup 100, answer loss only.
  **κ_d is frozen** (no gradient, not in the optimiser). The shared-weight digests must be equal across arms at the
  end.
- **Stage 2:** 1,600 steps, continuing the stream.
  - Each visit preloads the gold card plus k fact distractors, k ∈ {0, 1, 2} drawn uniformly per visit. They are
    drawn from fact lines only (S2 §10b pool), shuffled, generator `1000 + seed`, identical across arms.
  - Answer loss after each of the 2 loops, averaged over loops.
  - Shared weights at lr 1e-3. κ_d (treated) in its own optimiser group at lr 1e-2, weight decay 0.
- **Progress readouts (reported, no marks):** `acc_gold` and `acc_d2` on the test split every 400 stage-2 steps.

## 4. Readouts (end of stage 2, test split `toy_set(spec, 16, 16, 303)`, 1,024 questions)
- **`acc_d2` (PRIMARY):** gold + 2 FACT cards, generator 7002 (S2 §10b reading).
  - Reported separately on questions where a distractor names the same person as the question, and where none
    does.
- `acc_gold` (gold alone), `acc_nocard`, `distinct_256` on `acc_d2`.
- **Engagement (reported):**
  - treated κ_d;
  - the share of decoder cross-attention, at answer position 0 averaged over heads, that the three supplied cards'
    rows give to the gold card's rows, on questions where no distractor names the person.
- **Eval-only check:** treated `acc_d2` with κ_d forced to 8.
- Also recorded: stage-1 `acc_gold`, the stage-1 shared-weight digest, and ∂L/∂κ_d at the first stage-2 step.

## 5. VOID rules (per seed pair)
A seed's pair is VOID if any of these holds:
- (i) the control gives one distinct answer over the first 256 questions on `acc_d2`;
- (ii) the control's `acc_gold` is below 95% after stage 1, or below 90% after stage 2;
- (iii) the stage-1 shared-weight digests differ;
- (iv) ∂L/∂κ_d = 0 at the first stage-2 step (treated).

At least 2 valid seeds are needed; otherwise INCONCLUSIVE.

## 6. Pass marks
d_s = treated `acc_d2` − control `acc_d2`. "Every" means every valid seed.
- **PASS** needs all of:
  1. d_s ≥ +15 points on every seed, and mean(d) − 2·SD(d)/√n > 0;
  2. treated `acc_d2` ≥ 60% on every seed;
  3. treated `acc_d2` on questions where no distractor names the person is ≥ 20 points above its `acc_d2` on
     questions where one does, on every seed;
  4. treated `acc_gold` ≥ 95%, `acc_nocard` ≤ 9.25%, `distinct_256` > 1, and finite gradients in every run.
- **FAIL:** mean d ≤ +3 points, **or** treated `acc_d2` < 45% on 2 or more valid seeds.
- A firing FAIL or proves-wrong rule blocks PASS.
- **INCONCLUSIVE:** anything else, reported as is, with no re-run under changed marks.

## 7. Proves wrong, and reported notes
- **PROVES WRONG:** |d_s| ≤ 3 points on 2 or more valid seeds.
- **ENGAGED (reported):** κ_d ≥ 1.0, and ≥ 0.6 of the supplied-card attention on the gold card's rows, on
  questions where no distractor names the person.
- **κ_d = 8 check:** if treated `acc_d2` stays ≤ 45% with κ_d forced to 8, report "the fault is after selection (the
  decoder's query or value path)".
- **If the control also reaches ≥ 60%** `acc_d2`: report "the protocol alone teaches choosing".

## 8. Raw outputs
`artifacts/claude-infoconstraints-20261018/s5-stage0/{control,treated}-seed{0,1,2}.json` and `.log`, plus
`summary.json`. Runner: `scripts/info_s5_stage0.py`.

## Amendment 1 (2026-10-20, before any S5 run; §3-§7 unchanged)

Implementation details within §2-§4, recorded under the card's rule:
1. **Stage-1 identity.** While κ_d is frozen at exactly 0 (stage 1), the bias is skipped. It is exactly zero, so
   this is the same function, and the base attention path runs. This is needed for bit-identical stage-1 arms:
   SDPA with a float mask that requires grad takes a different backward path, which differs from the boolean-mask
   path in the last bit of the shared gradients (found by the pre-run test). From the first stage-2 step, κ_d
   requires grad and the bias is always applied.
2. **k per visit.** `torch.randint(3)` per visit from generator `1000 + seed`. Then the S2 §10b fact-only pool
   noise and the shuffle, drawn from the same generator in that order. Identical across arms, because the draws do
   not depend on the model.
3. **Attention share (§4).** Position 0, the mean over heads of the softmax over all valid memory rows, including
   the S5 bias. The share is the gold card's two rows (think card row + raw row of its slot) over the supplied
   cards' rows.
4. **Per-question d2.** The runner tallies `acc_d2` per question for the same-person split and **asserts** that
   its total equals `S2.distract(..., facts_only=True)`'s.
5. **Pre-run tests:** `tests/test_premonition_dec_ent_match.py` 5/5, covering:
   - flag-off identity to 7a2f5a32a (only S2 on);
   - paired start, and bit-identical forward and gradients while frozen at 0;
   - the bias on exactly the matching card's two rows (attention logits by hand);
   - ∂L/∂κ_d ≠ 0 at κ_d = 0;
   - finite modes with wipes;
   - refusals, the config round trip, and the reset.
