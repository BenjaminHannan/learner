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
