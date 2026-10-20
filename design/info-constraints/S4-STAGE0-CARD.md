# RUN CARD: S4 Stage 0, `ent_key` (entity identity in the ASK score) on the base D + S2, far-fact toy

**Status: SEALED BEFORE ANY S4 CODE OR NUMBER EXISTS.** Committed 2026-10-20 under the coordinator's 10-20 GO.
The S4 code is built to §2 after this commit. It runs only after the built-in review on main...head is clean
(blocking items fixed, the rest logged). Any implementation deviation goes into an amendment before the first run;
§3-§7 do not move after the first run starts.

## 0. What S4 tests, and why this protocol
- **Target.** REPORT N9 / R4: fact-card keys collapse to one direction. ASK finds "a fact" but not "this person's
  fact"; gold ranks first 24.2% at recall@4 0.90 (steals diagnostic, tiny D).
- **The change.** S4 puts the line's entity identity, which `store.ents` already holds from the pointerizer, into
  the ASK score. It changes **retrieval**. So its primary readout is the first-ASK ranking, not answer accuracy.
- **Why two stages.** Retrieval only learns under the ASK loss (teacher/own modes). But under the full curriculum
  the answer path collapses (S1-P0, sweep: one distinct answer), and S3's cell B showed a choosing cell is
  meaningless if the control cannot read. So:
  - Stage 1 is the S2 protocol, where D + S2 is known to read (1024/1024);
  - Stage 2 then trains retrieval with the teacher loss;
  - the "control can read" check (§5) makes a non-reading cell VOID.
- **Data-only ceiling (context, not a mark; computed before sealing, no model).** On the §3 test split, a
  question's entity is named by 2.29 eligible cards on average (minimum 1). So "filter by entity, then pick
  uniformly" ranks gold first with expectation 0.485.

## 1. Arms (paired, seeds 0, 1, 2)
- **Control:** D + S2, i.e. `MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
  decoder_raw_cards=True)`.
- **Treated:** the same plus `ent_key=True`. One change.
- **Paired start:** shared weights and global RNG streams are identical at the same seed. The S4 modules are built
  after `reset_parameters` inside `fork_rng` with their own generator (the S3 pattern), and a test must prove it.
- In stage 1 the two arms compute identically, because κ_e = 0 and there is no ASK loss. The runner records a digest
  of the shared weights after stage 1, and they must match across arms (§5).

## 2. The change (S4 `ent_key`, behind a default-off flag)
- **Entity sub-score.** In every ASK (`_step`, and the first-ASK recall metric):
  `s_l = κ·q·k_l + b_age + κ_e · (π · e_l)`.
  - `e_l ∈ [0, 1]^16` is the multi-hot of card l's `ents`, divided by their count (zero for a card without
    entities, and for NULL).
  - `π = softmax(W_e r0)` over the 16 entity ids, restricted to the entities mentioned up to the question
    (`_mentions`). `r0` is the same LayerNormed register 0 that gives the query. `W_e: Linear(d, n_ent)`.
  - `κ_e` is a scalar parameter **initialised to 0**, so at init the flag-on scores equal D + S2's exactly.
  - Cost: `W_e` 528 parameters at d = 32 and 2,064 at d = 128, plus 1 for κ_e. Reported apart from the band.
- **Unchanged:** the eligibility mask, top-k, NULL handling, and every other module. With the flag off, the base
  text runs.
- **Refusals:** it needs the store, and it is defined on `PremonitionMini` only (the S3 rule).
- **Pre-run tests (required):**
  - flag-off identity to D + S2 as committed at e548d89d2 (the S3 head reviewed in round 12), only S2 on;
  - flag-off identity to 73b8e0224 (S2 harness);
  - paired start, and κ_e = 0 giving identical ASK scores;
  - the entity term equals `κ_e·(π·e_l)` against a hand computation;
  - finite training in every mode;
  - refusals;
  - config dicts and digests with the flag off equal to the base commit's.

## 3. Setup (fixed here)
- **Common:** far-fact toy v16 (`ToySpec()`), 16 visits per step, `label_free`, train stream
  `toy_stream(spec, 16, 101)`; AdamW lr 1e-3, warmup 100, betas (0.9, 0.99), eps 1e-8, weight decay 0.1 on
  dim ≥ 2 tensors; clip 1.0; 1 thread; CPU; $0.
- **Stage 1:** exactly S2-STAGE0-CARD §2 (gold mode, answer loss only, 2 loops, 800 steps).
- **Stage 2:** 400 more steps on the same stream, same optimiser (no reset, lr 1e-3):
  `forward(mode="teacher", generator=G)` with the config's default loss weights (lm 1, ask 0.5, ans 1, halt 0.1).
  - Teacher fetches are the gold card plus 1-2 random distractors, so the ASK set-CE trains the ranking.
  - `G = torch.Generator().manual_seed(2000 + seed)`, identical across arms.
- **Test split:** `toy_set(spec, 16, 16, 303)`, 1,024 questions, scored once at the end.

## 4. Readouts (every arm and seed)
- **`rank1` (PRIMARY).** The share of told questions whose gold card has the strictly highest first-ASK score among
  eligible real cards. That is loop 0 of a fresh episode, scores from `_step`, the steals-diagnostic definition.
- `recall4`: gold in the first-ASK top-4.
- `acc_gold`: gold card alone, 2 passes, greedy (S2 card §2 reading).
- `acc_nocard`: no card.
- `distinct_256` on `acc_gold`.
- Secondary, reported only:
  - `acc_d2` (gold + 2 fact cards, S2 §10b reading);
  - own-retrieval answer accuracy (`model.answer`);
  - treated `κ_e`, and π's mean mass on the question's own entity.

## 5. VOID rules
A seed's pair is **VOID** if any of these holds:
- (i) the control gives one distinct answer over the first 256 questions on `acc_gold` (coordinator 10-19);
- (ii) **the control cannot read**: control `acc_gold` < 50% (coordinator 10-20);
- (iii) the stage-1 shared-weight digests differ between the arms.

VOID cells count for nothing. At least 2 valid seeds are needed for a verdict; otherwise INCONCLUSIVE.

## 6. Pass marks (written before any S4 code or run)
d_s = treated `rank1` − control `rank1`. "Every" means every valid seed.
- **PASS** needs all of:
  1. d_s ≥ +15 points on every seed, and mean(d) − 2·SD(d)/√n > 0;
  2. treated `recall4` ≥ control `recall4` − 0.02 on every seed;
  3. reading kept: treated `acc_gold` ≥ control `acc_gold` − 3 points on every seed;
  4. **no-card guard:** treated `acc_nocard` ≤ 9.25% (chance + 3 points) on every seed;
  5. treated `distinct_256` > 1; every run, VOID or not, completed both stages with finite gradients.
- **FAIL:** mean d ≤ +3 points.
- A firing FAIL or proves-wrong rule blocks PASS.
- **INCONCLUSIVE:** anything else, reported as is, with no re-run under changed marks.

## 7. The result that would prove S4 wrong
- |d_s| ≤ 3 points on at least 2 valid seeds: entity identity in the score does not change which card ranks first.
- Reported notes, not verdicts:
  - if proved wrong with treated κ_e < 0.5, "the mechanism was not engaged";
  - if proved wrong with π's question-entity mass > 0.8, "identity is in the score and still does not decide the
    rank".

## 8. What a PASS does and does not buy
- **Buys:** an entity-identity term lets ASK rank the right person's card first more often on the far-fact toy.
- **Does not buy:** better answers (S2 still picks among cards at random; S3 failed); two-hop; village.
- Next, only after a PASS: a Stage-1 bid priced by measured seconds per update (E5), held until ruled.

## 9. Raw outputs
`artifacts/claude-infoconstraints-20261018/s4-stage0/{control,treated}-seed{0,1,2}.json` and `.log`, plus
`summary.json` applying §5-§7. Runner: `scripts/info_s4_stage0.py`.
