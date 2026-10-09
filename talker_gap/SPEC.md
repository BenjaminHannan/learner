# Small talker check - spec and pass marks (written 2026-10-08 ET, before any arm is trained)

Track: English QA line only (Mac/CPU check). Not the card toys, not the village model. Nothing here queues GPU work; the PC GPU stays untouched. Claims are labelled shown / suggested / untested in the results file.

## Question

With reader, thinker and data held fixed, which talker recipe closes most of the gap between today's talker (B0) and a pretrained-LM reference talker (R) on question kinds the talker never trained on?

## Fixed pieces (identical in every arm)

- **Reader:** frozen EmbeddingGemma 2 (`~/eg2`, transformers 5.19 via `PYTHONPATH=/Users/ben-hannan/tf519`), input = `PREFIX + source_text + " " + question`, per-token last-hidden states 768-d cached to disk (fp16). Bidirectional, so states see the question.
- **Thinker:** learned, trained jointly with the talker from scratch: Linear(768->256) then 2 transformer layers looped 3 times (~1.6M params); the "notes" are the [T,256] states after each loop. No pretrained weights.
- **Data (TEACH, 171,940 rows):** `split_proposal_v2.json` (dev = 8 whole kinds, test = 6 whole kinds, passage-disjoint, practised slice = 2,001 rows from kept kinds, rest = train). Small check trains on a fixed random 24,000-row subsample of the train side (seeded, same ids in every arm). Dev/test kinds are never seen in training, in pretraining prompts or in selection of anything except the dev reading of marks.
- **Targets, all arms that can produce them:** say-back + answer, e.g. `who was playing the game? hugo`; never truncated. B0 cannot say back (it is a pointer/class head), so it is trained answer-only and **scored on the answer part only**. Scoring = exact match after `en_norm` against `accepted_answers`.
- **Sealed final check (run once, at the very end, only for the chosen winner, B0 and R):** TEST kinds from TEACH, plus FRESH-EN-R3, GEN-HELDOUT-R4, NEW-KINDS-R5, NEW-KINDS2-R6 (192 questions each; nothing is ever trained or tuned on them; they are not GOLD-PRIVATE/reserved).
- **Compute:** Mac only (MPS/CPU), each wave < 30 min wall-clock.

## Arms (one change at a time)

| arm | what changes | notes |
|---|---|---|
| **P0 probe** | none: linear start/end head on frozen Gemma states, no thinker | is the answer location readable at all on unseen kinds? Diagnostic only, not a candidate |
| **B0** | today's design: non-autoregressive; query from the thinker's final (loop-3) pooled state; start/end pointer over prompt words, 3-way mode (yes/no/span) plus a closed class list; no notes, no say-back | the number to beat |
| **B0-nothinker** | B0 with the thinker layers removed (talker reads Linear(768->256) of the reader states), trained with the same budget | the trained "thinker off" control |
| **R** | reference: pretrained `pythia-31m` (31M, cached) as decoder; thinker notes projected to its embedding size and used as a prefix; it never sees the raw prompt text; trained on say-back targets | measures what LM pretraining buys; also checked for bypass |
| **T1** | autoregressive char-level pointer-generator decoder (~6M), say-back targets, cross-attends over ALL thinker notes (pointer keys = notes; values = char embeddings of the prompt); no raw reader states | candidate 1 |
| **T1-nothinker** | T1 with the thinker layers removed, same budget | trained control for T1 (built only if T1 is built) |
| **T2** | T1 + pretraining before TEACH on FineWeb-Edu through the same reader->thinker->talker: Splinter-style recurring-span question answering plus say-back of the cloze sentence (no teacher labels, no TEACH text) | candidate 2; only run if T1 passes or ties B0 |
| later, only if T1 wins | T1 minus notes (final state only), T1 minus say-back, T1 at 25M | one change at a time, to see which part did it |

**How B0 differs from B2 (scope of "beats the current talker"):** B0's pointer keys come from the final thinker states; B2's come from the raw reader states of the current prompt. B0 has no 8-character GEN register and no NUM path (B2 has both). So passing here means "beats a B2-style head in this harness", and the PR claim is scoped that way.

Seeds: screen at seed 0 for all arms; any arm that clears a mark is repeated with seeds 1 and 2. All arms use the same optimiser, batch size, and update budget (set in the harness config, not per arm).

## Run order

Wave 1 (seed 0, cheap): **P0, B0, B0-nothinker.** It decides (a) whether the ceiling rule fires, (b) whether the thinker adds anything on TEACH at all, and (c) whether T1, R and T2 are worth building. T1, T1-nothinker, R and T2 are built only after wave 1 reports. The marks are fixed, so this is not tuning on DEV.

## Measurements

For every trained model, on DEV (unseen kinds), PRACTISED slice, and (at the end) the sealed sets: exact match overall, **short-answer exact match (headline)**, yes/no exact match, error buckets (wrong location / wrong edges / wrong word / yes-no flip), answer length buckets (<=8, >8 chars). Checks: **shuffled thinker state** (donor row from the same kind with a different answer, swapped notes; reported for all arms, but it is nearly automatic here because the talker's only view of the passage is the notes, so passing it is NOT evidence against bypass), the **trained no-thinker arms** (the real thinker check), and for T1 the pointer mass on the correct span. Decode speed: milliseconds per answer at batch 1 on CPU, and talker parameter count.

## Pass marks (fixed now)

Let S(x) = short-answer EM on DEV (unseen kinds). Hard slice H = DEV short answers longer than 8 characters or with 2+ words; S_H(x) is EM on H.

**Ceiling rule (decided before wave 1):** if S(B0) >= 80 the headline switches from S to S_H. If S_H(B0) >= 85 as well, there is no room for a +10 gain on TEACH-DEV: no candidate is built, the finding is "no measurable talker gap on TEACH-DEV with a Gemma reader", and the decision is deferred to the one-shot sealed R5+R6 check (B0, P0 and the best other arm are evaluated there; mark 6 below applies to that check).

A candidate T passes only if all of marks 1-5 hold on DEV (with S replaced by S_H if the ceiling rule fired):

1. **Beats B0:** S(T) - S(B0) >= 10 points, the paired bootstrap 95% interval of the difference on DEV excludes 0, and every seed run is above B0's seed-matched run.
2. **Uses the thinker:** S(T) - S(T-nothinker) >= 10 points, where T-nothinker is a separately trained arm with the same budget. (The eval-time shuffle cost is also reported; it is expected to be large and does not count as evidence.)
3. **No regression on practised kinds:** PRACTISED EM >= B0's PRACTISED EM - 3 points.
4. **Yes/no guard:** yes/no EM within 3 points of B0 or higher.
5. **Cheap and fast:** talker <= 25M parameters, and decoding an answer takes <= 50 ms at batch 1 on the Mac CPU.

Secondary numbers (reported, not pass/fail):
- **Gap closure against R:** (S(T) - S(B0)) / (S(R) - S(B0)), reported only if R is valid: S(R) >= S(B0) + 5. If R is not valid, say so; do not use it to say there is no gap.
- Gap vs P0: S(P0) - S(B0).

6. **Sealed check (end, one shot):** the winner beats B0 on the pooled NEW-KINDS-R5 + R6 short answers with the 95% interval excluding 0. Mark 6 decides whether the result goes in the PR as a recipe or as a negative result.

## What would prove each idea wrong

- **P0:** if linear probing already gives S >= S(B0) + 10, the answer location is readable without our thinker/talker and the talker head is the bottleneck, not information.
- **R:** has no copy path (it must spell names from word pieces using only the notes), so it may score low for reasons unrelated to pretraining. It is valid as a reference only if S(R) >= S(B0) + 5; otherwise report it and rely on the primary marks.
- **T1:** wrong if S(T1) - S(B0) < 5 points, or if S(T1) - S(T1-nothinker) < 10 (the thinker is not used).
- **T2:** wrong if S(T2) - S(T1) < 3 points (pretraining adds nothing).
- **Diagnosis (data and reader explain PR #37):** wrong if B0 on DEV is still < 25% short-answer EM while a TEACH-trained P0 or valid R is > 60%.

## Honesty rules

- Marks above are not edited after the first arm trains. Any change goes in a dated, labelled amendment.
- Results go in `RESULTS.md` with shown/suggested/untested labels; DEV-set tuning is limited to the single config in the harness; no per-arm hyperparameter search.
- No training target is truncated or answer-only except B0, whose head cannot say back (stated, scored on the answer part).
- Everything the model does is learned; hand-written code is only data preparation and evaluation.

## Amendment 1 (2026-10-08 ET, after wave 1, before any candidate was built)

Wave 1 (seed 0) left the ceiling rule at S_H(B0) = 84.52, just under 85, with the headline S_H and mark 1 needing S_H(T) >= 94.5. Ben chose to stop building and run the sealed check on B0, B0-nothinker and P0 only (R, T1, T2 not built). Marks 1-5 were never applied to a candidate. Mark 6 was evaluated only as a descriptive B0 vs B0-nothinker vs P0 comparison on pooled R5+R6 (RESULTS.md); there is no winner.

## Amendment 2 (2026-10-08 ET, after the sealed check on B0/B0-nothinker/P0 and before any T1 or T2 step)

Ben chose option C ("let it read lots of ordinary text first"). That is T2 = T1 + FineWeb-Edu pretraining, so T1 must be built first (as T2's base and as its control). Two one-change comparisons are reported separately: **T1 vs B0** (does the architecture help) and **T2 vs T1** (does the pretraining help). B0 is not used as T2's base because B0 trains answer-only.

**Fresh scoring set FRESH-R7 (evaluation only).** R3-R6 are spent, and DEV/TEST (held-out TEACH kinds) cannot show the outside-set drop (B0 85.3 DEV vs 85.9 practised). No unused outside set exists in the repo (searched 2026-10-08). So agents write a new one before any T1/T2 training: 160 questions (who 20, what 24, which 20, where 24, why 20, when 24, how 28), made-up names, 1-2 sentence passages of 8-30 reader tokens like R5/R6, short answers only, the answer a contiguous verbatim word span of the passage (checked by code), each scored on source text and paraphrase = 320 rows. Deduplicated against TEACH train passages, R3-R6 and the FineWeb sample (no 8-word-gram overlap). sha256 of every file goes into `fresh_r7/MANIFEST.json` before training starts. It is evaluation data only: never trained on, never used to select anything. It is not GOLD-PRIVATE, reserved or blind. **It is run once, at the very end, on B0, T1, T1-nothinker and T2 (seeds 0, 1, 2 each).** A bug found after seeing R7 numbers voids and documents that run; nothing is re-tuned on R7.

**Pretraining data and task (T2).** FineWeb-Edu pulled fresh through the HF dataset server (not the desmos-llm holdout files, which belong to another project). Chunks of 2-4 consecutive sentences; a word span of 1-3 words that occurs in two different sentences of the chunk is the recurring span; the passage is the chunk minus the sentence holding the second occurrence; the question is that sentence with the span blanked out; the target is `<that cloze sentence> ? <span>` (say-back plus answer, never cut: sentences over 120 characters are dropped, not truncated). Same reader -> thinker -> talker path as T1. No teacher model, no TEACH text. Then the same TEACH fine-tune as T1 (same 3000 updates, same 24,000-row subsample, same optimiser). N pretraining rows are chosen after a timing probe so the pretraining step fits a 30 minute wave and the state cache stays under 5 GB; check `df` shows >= 10 GB free before each launch.

**Arms:** T1, T1-nothinker, T2 (seeds 0, 1, 2 each; seeds are not gated on DEV marks because the R7 comparison is the decision). T2 also gets a **T1-long** control (T1 trained for the same total number of updates as T2 on TEACH only), run only if T2 clears mark C1, to separate "FineWeb text" from "more updates".

**Marks (fixed now):**
- **C1 (decides whether pretraining helped):** mean over 3 seeds, S_R7(T2) - S_R7(T1) >= 3 points, paired bootstrap over rows 95% interval excluding 0, and the difference positive in every seed.
- **C2 (decides whether the end result beats today's talker on the outside set):** S_R7(T2) - S_R7(B0) >= 5, same interval rule.
- **C3 (architecture):** S_R7(T1) - S_R7(B0) reported with its interval; no pass mark.
- **DEV marks from the original spec stay as written and are reported pass/fail:** T1 - B0 >= 5 on S, T1 - T1-nothinker >= 10, T2 - T1 >= 3. Expected: the +10 thinker mark may fail (B0's thinker adds only 2.2); that is reported, not tuned.
- **Guards, all arms:** S_DEV(T2) >= S_DEV(T1) - 2; shuffled-thinker-state drop >= 20 points; thinker-off gap as above; <= 25M talker parameters; decode <= 50 ms per answer at batch 1 on the Mac CPU.
- **Secondary, descriptive:** the T2 - T1 gain on R7 split into practised openers (who, what, which) and never-practised openers (where, why, when, how). This only bears on the two guesses (question types vs style shift) and any reading stays **suggested**.

**What would prove C wrong:** C1 fails (T2 - T1 < 3 or the interval includes 0). That says FineWeb-Edu recurring-span pretraining does not close the outside gap on this set; it does not say which of the two guesses is true.

**Compute and data rules unchanged:** Mac only, no GPU job, no Vast, no paid compute; TEACH + FineWeb-Edu only for training; no new teacher model; everything the model does is learned, hand-written code only prepares data and scores; no training target is truncated or answer-only for T1/T2.

## Amendment 2b (2026-10-08 ET, after the timing probe and before the first real T1 step)

Timing probe (T1, seed 0, Mac MPS, machine under load average ~10): 0.31 s per update, so ~15.5 min per 3000-update TEACH run. Fixed now, before any real training:
- **T2 pretraining = 3000 updates** (batch 64, same optimiser and warm-up/cosine as the TEACH stage, ~5.3 passes over the 36,363 filtered FineWeb-Edu rows), then the unchanged 3000-update TEACH stage. Seeds 0-2 each use their own seed for both stages.
- **T1-long = 6000 TEACH updates** (same optimiser, one warm-up/cosine over 6000), seeds 0-2, run only if C1 passes.
- Waves: T1 and T1-nothinker first; T2 after. Jobs run at most two at a time because the Mac is memory-tight. A run whose wall-clock exceeds 30 min because of machine load is reported as such; nothing is changed to make it faster.
- FRESH-R7 is scored exactly once, after every arm and seed has finished, by an eval script that refuses to run without `--final`. DEV is scored per run as in the harness.
- Nothing above changes any mark in Amendment 2.
