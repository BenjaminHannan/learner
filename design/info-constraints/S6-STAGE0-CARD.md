# RUN CARD: S6 Stage 0, `ask_ent_match` (S5's entity-match feature in the ASK score), base D + S2 + S5

**Status: SEALED BEFORE ANY S6 CODE OR NUMBER EXISTS.** Committed 2026-10-20 under the coordinator's 10-20 GO,
after the Opus design review of the S5 PASS. The design, marks and VOID rules below are the coordinator's,
recorded in substance. Where the ruling left a detail open, I fixed it here, before any code, and marked it
"(fixed here)". The code is built to §2 after this commit. It runs only after ONE focused built-in review on
main...head is clean (blocking items fixed, the rest logged). Implementation deviations go into an amendment
before the first run. §3-§7 do not move after the first run starts.

**Model size: the tiny preset (d = 32, about 80k parameters), as in every Stage 0 so far.** $0, CPU.

## 0. What S6 tests
- **S5 showed** that the decoder chooses among supplied cards by person once it gets the entity-match bit
  (d2 38-40.5% → 89.6-91.2%).
- **S4 showed** that ASK never learned an entity term on its own. κ_e stayed near 0, because π was uniform and
  W_e got no gradient.
- **S6** hands ASK the same fixed, label-free bit that S5 gave the decoder, with one learned scale. It asks:
  - does fetch then rank the right person's card first (rank1)?
  - does that carry through to own-retrieval answers, i.e. is fetch the binding link?
- **Data-only ceiling (context, not a mark; S4 card §0):** on the test split a question's entity is named by
  2.29 eligible cards on average (minimum 1). "Filter by entity, then pick uniformly" ranks gold first with
  expectation 0.485. Relation choice beyond that has to come from the existing q·k term.

## 1. Arms (paired, seeds 0, 1, 2)
- **Control:** D + S2 + S5, i.e. `MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
  decoder_raw_cards=True, dec_ent_match=True)`.
- **Treated:** the same plus `ask_ent_match=True`. ONE change.
- **Paired start:** the only new parameter is the scalar κ_a = 0, built after `reset_parameters` with no RNG
  draw. So every shared weight, κ_d and the RNG streams are identical at the same seed.

## 2. The change (S6 `ask_ent_match`, behind a default-off flag)
- **Score term.** In every ASK, card l's score gets `+ κ_a · m_l`. This covers `_step` (teacher, own and
  `answer()` fetches), the first-ASK recall metric `_recall`, and so the first-ASK readout.
  - `m_l = 1` if card l's pointerizer entity ids (`store.ents`) include an entity in the question span, else 0.
    This is S5's feature: the same `_mentions(batch, start)` set (`episode.q_ents`).
  - NULL gets 0, and so do entity-free cards.
  - The term is added before the eligibility mask, as S4's `extra` was. Label-free: it uses only the model's own
    input.
- **κ_a** is one scalar parameter, initialised to 0. Because `m_l` is fixed, ∂s_l/∂κ_a = m_l ≠ 0, so the
  gradient is live from the first ASK-loss step. S4's dead-gradient trap does not apply.
- **Unchanged:** keys, query, κ, the age bias, eligibility, top-k, NULL handling, the decoder, and S5's bias.
  With the flag off, the base text runs.
- **Refusals:** it needs `dec_ent_match` (which already needs `decoder_raw_cards` and refuses `card_address`).
  It is refused together with `ent_key` (fixed here: two learned ASK extras would be two changes). It is defined
  on `PremonitionMini` only.
- **Stage-1 identity (fixed here, as S5 amendment 1):** while κ_a is frozen at exactly 0, the term is skipped
  (it is exactly zero, so this is the same function).
- **Pre-run tests (required):**
  - flag-off identity to the reviewed S5 code at 7c0456589 with S2 + S5 on;
  - paired start, and bit-identical forward and gradients while κ_a is frozen at 0;
  - the term equals κ_a·m_l against a hand computation on a toy batch, NULL 0;
  - ∂L_ask/∂κ_a ≠ 0 at κ_a = 0 on a teacher batch;
  - finite training in every mode, including `answer()` with wipes;
  - refusals, the config round trip, digests with the flag off unchanged, and the reset.

## 3. Protocol (both arms)
- **Common:** far-fact toy v16, 16 visits per step, `label_free`, train stream `toy_stream(spec, 16, 101)`;
  AdamW betas (0.9, 0.99), eps 1e-8, weight decay 0.1 on dim ≥ 2 shared tensors, lr 1e-3 with warmup 100;
  1 thread; CPU; $0.
- **Stage 1:** 800 gold-only steps (the S2 protocol: answer loss only, 2 loops). κ_d and κ_a are **both frozen
  at 0** (no gradient, not in the optimiser). The shared-weight digest (every parameter except κ_d, κ_a) must be
  equal across arms at the end.
- **Stage 2:** 1,600 TEACHER-mode steps on the same stream, same optimiser.
  - `forward(mode="teacher", generator=G)` with the config's default loss weights (lm 1, ask 0.5, ans 1,
    halt 0.1), as S4's stage 2.
  - `G = torch.Generator().manual_seed(2000 + seed)`, identical across arms.
  - κ_d (both arms) and κ_a (treated) are unfrozen and go in their own optimiser group: lr 1e-2, weight decay
    0, no warmup.
  - **Clipping:** the shared weights are clipped at norm 1.0. Each scalar's gradient is clipped on its own at
    1.0 (fixed here: |g| ≤ 1 per scalar), so neither scalar enters the shared norm.
- **Progress readouts (reported, no marks):** rank1 and acc_gold every 400 stage-2 steps.

## 4. Readouts (end of stage 2, test split `toy_set(spec, 16, 16, 303)`, 1,024 questions)
- **`rank1` (PRIMARY):** among told questions whose gold card is eligible, the share where the gold card has the
  strictly highest first-ASK score among eligible real cards. First ASK means loop 0 of a fresh episode, with
  scores from `_step`. This is the S4 runner's `first_ask`, unchanged.
- `recall4`: gold in the first-ASK top-4 (same runner).
- **Own-retrieval answers:** `model.answer(batch)` (own ASK, own HALT, no wipe), judged by `ptrain.judge`.
  - Reported overall (`own_acc`), and split by n_q, the number of eligible real cards that name a question
    entity: 1, 2, ≥ 3 (fixed here).
- `acc_gold` (gold card alone), `acc_d2` (gold + 2 fact cards, generator 7002, the S2 §10b reading),
  `acc_nocard`, and `distinct_256` on `acc_d2` and on `acc_gold`.
- `κ_a`, `κ_d`.
- **Fetches per question in own retrieval:** the mean number of distinct real (non-NULL) cards fetched, and the
  share of questions with at least one real fetch (fixed here).
- **Also recorded:**
  - stage-1 acc_gold and the stage-1 digest;
  - ∂L/∂κ_a at the first stage-2 step, before clipping;
  - on the test split, the share of told questions whose gold card has m = 0.

## 5. VOID rules (per seed pair)
A seed's pair is VOID if any of these holds:
- (i) **the control can't read:**
  - control acc_gold < 95% after stage 1, or < 90% after stage 2;
  - or control `distinct_256` on acc_d2 = 1.
- (ii) **the S5 base isn't working:** control κ_d < 1.0, or control acc_d2 < 75%.
- (iii) the stage-1 shared-weight digests differ.
- (iv) |∂L/∂κ_a| < 1e-3 at the first stage-2 step (treated).
- (v) m = 0 on the gold card for more than 1% of told test questions (treated; a property of the data and
  pointerizer, so equal in both arms).
- (vi) **the control never fetches in own retrieval:** no test question fetches a real card.

VOID cells count for nothing. At least 2 valid seeds are needed; otherwise INCONCLUSIVE.

## 6. Pass marks
d_s = treated rank1 − control rank1; a_s = treated own_acc − control own_acc. "Every" means every valid seed.
- **PASS** needs all of:
  1. d_s ≥ +15 points on every seed, and mean(d) − 2·SD(d)/√n > 0;
  2. treated recall4 ≥ 0.85 on every seed;
  3. a_s ≥ +10 points on every seed;
  4. treated acc_gold ≥ 95%, acc_nocard ≤ 9.25%, `distinct_256` > 1 (on acc_d2), acc_d2 ≥ control acc_d2 − 3
     points, and finite gradients and complete runs in every run.
- **FAIL:**
  - mean d ≤ +3 points, **or** mean a ≤ 0;
  - **or** treated κ_a < 1.0 at the end on any valid seed. The gradient was live at the start, since rule (iv)
    passed. Reported with the note **"not engaged"**; this is a FAIL, NOT a VOID. ("Any valid seed" is fixed
    here; the ruling did not say how many seeds.)
- A firing FAIL or proves-wrong rule blocks PASS.
- **INCONCLUSIVE:** anything else, reported as is, with no re-run under changed marks.

## 7. Proves wrong
- |d_s| ≤ 3 points on 2 or more valid seeds whose treated κ_a ≥ 1: entity match in the ASK score does not change
  which card ranks first.
- **Or:** mark 1 is met, but a_s ≤ +3 points on 2 or more valid seeds: **fetch is not the binding link.**

## 8. What a PASS does and does not buy
- **Buys:** a supplied entity-match bit lets ASK rank the right person's card first, and that raises
  own-retrieval answers. This holds on the tiny far-fact toy.
- **Does not buy:**
  - a learned entity cue (the bit is hand-built, only its scale is learned);
  - relation choice (same-person cards are still told apart only by q·k);
  - d = 128;
  - the village. Whether entity cues carry over there is the S4-P0 village count, filed separately.

## 9. Raw outputs
`artifacts/claude-infoconstraints-20261018/s6-stage0/{control,treated}-seed{0,1,2}.json` and `.log`, plus
`summary.json` applying §5-§7. Runner: `scripts/info_s6_stage0.py`.

---

## 9a. Result (appended after the run; §1-§8 unchanged since 88fe1ac97)

Run 2026-10-20, CPU, 1 thread per run (6 runs sharing 4 cores, 1,135-1,188 s each), **tiny preset (d = 32)**;
800 stage-1 + 1,600 teacher steps; code = 23cf36d64 (one focused review, clean). Raw:
`artifacts/claude-infoconstraints-20261018/s6-stage0/`; `summary.json` is the verbatim §5-§7. Test split,
1,024 questions, all told.

| seed | control rank1 / recall4 / own | treated rank1 / recall4 / own | d (rank1, points) | a (own, points) | κ_a | κ_d (control / treated) | d2 (control / treated) |
|---|---|---|---|---|---|---|---|
| 0 | 9.08% / 0.328 / 29.39% | 48.73% / 1.000 / 49.22% | +39.65 | +19.82 | 8.57 | 3.34 / 2.97 | 89.94 / 89.16% |
| 1 | 8.40% / 0.326 / 28.71% | 51.56% / 1.000 / 50.98% | +43.16 | +22.27 | 8.57 | 2.45 / 2.30 | 87.60 / 88.09% |
| 2 | 8.11% / 0.339 / 31.25% | 49.12% / 1.000 / 49.80% | +41.02 | +18.55 | 8.56 | 3.10 / 3.86 | 88.57 / 89.45% |

Own-retrieval answers by n_q (eligible cards naming the question's person; 104 / 517 / 403 questions):

| seed | control n_q = 1 / 2 / ≥ 3 | treated n_q = 1 / 2 / ≥ 3 |
|---|---|---|
| 0 | 32.7 / 30.4 / 27.3% | 97.1 / 53.0 / 32.0% |
| 1 | 30.8 / 28.6 / 28.3% | 94.2 / 54.0 / 36.0% |
| 2 | 31.7 / 34.4 / 27.0% | 100 / 52.6 / 33.3% |

- **Validity:** no seed is VOID.
  - Stage-1 acc_gold is 100% in every run, and control acc_gold is 100% after stage 2.
  - The stage-1 digests are equal across arms (aa2fe67d / afcd13ff / 3075a389).
  - The S5 base works: control κ_d 2.45-3.34, control d2 87.6-89.9%.
  - First stage-2 ∂L/∂κ_a: −0.422 / −0.415 / −0.454.
  - Gold card with m = 0: 0% of questions. Both arms fetch on every question (4.0 real cards on average).
  - All runs complete and finite.
- **Marks (§6):**
  1. d ≥ +15 every seed: yes. Mean − 2SE > 0: yes (mean d +41.28 points; mean − 2SE +39.23).
  2. Treated recall4 ≥ 0.85: yes (1.000).
  3. a ≥ +10 every seed: yes (mean a +20.21 points).
  4. Gold 100%, no card 6.1-7.0%, 16 distinct, d2 within 3 points of the control (−0.8 / +0.5 / +0.9), finite:
     yes.
- **FAIL:** not fired (κ_a 8.56-8.57 ≥ 1.0 on every seed). **Proves-wrong:** neither rule fired.
- **Verdict: PASS (toy evidence only; the coordinator's 10-20 ruling).**
- **Progress (no marks):** treated rank1 is 48-48.4% at stage-2 step 400 and flat after that. The control stays
  at 7.5-9.4% throughout.
- **Readings:**
  1. **Shown.** Treated rank1 (48.7-51.6%) sits on the data-only ceiling of "filter by person, then uniform"
     (0.485, §0). recall4 is 1.000. So ASK now fetches every card that names the person. Among those cards, the
     q·k term ranks gold first no better than chance: it adds no relation choice.
  2. **Shown.** Own-retrieval answers fall with n_q: about 97% when one card names the person, about 53% with
     two, and about 34% with three or more. That is close to 1/n_q. It is the same relation-choice limit S5 left
     in the decoder: same-person cards pick at about a coin flip.
  3. **Suggested.** Fetch was a binding link: own answers went from about 29.8% to about 50.0% once retrieval
     found the person. **Relation choice**, in ASK and in the decoder, is now the binding link on this toy.
  4. **Scope.** This is a hand-built, label-free person bit with one learned scale, on the tiny far-fact toy.
     By the S4-P0 village count (REPORT), this cue covers few village questions: 70.6% name no person, and
     12.1% of gold cards name a question entity. By the coordinator's 10-20 ruling, it gets no Stage-1 or
     village money as built.
