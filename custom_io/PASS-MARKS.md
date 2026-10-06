# Pass marks: custom reader/reasoner/talker screen and confirm (fixed before any design trains)

Written 2026-10-05 about 05:58 UTC (1:58 AM ET), committed and pushed before any A, A0, B, plain_tf_steps, L2x2 or
open-LM run starts. Only the calibration runs in CALIBRATION.md (plain_tf, no verdict) have trained so far.
Designs and judging: `design/SYNTHESIS.md`, `design/JUDGES.md`, `design/design-*.md`. Fast lane: dev splits of the
seed-1 skills build only; nothing touches GOLD-PRIVATE, reserved or blind panels.

## Arms (all from scratch, character input, 24,000 updates, batch 256, shuffled order, bf16, AdamW as in train.py)
- **A (register loop):** shared shallow reader (char + position + place codes, 2 masked conv blocks, receptive field
  about +-4 chars); 16 slots (9 answer registers + 7 scratch) updated for 6 weight-shared rounds of
  self-attention + cross-attention to the reader output + MLP; linear per-register talker that sees only the final
  slots. Loss: per-round register cross-entropy; on rows whose `steps` give 2+ values, round r targets the r-th value.
- **A0:** A with the answer as the target on every round (one change: no step targets).
- **B (Ledger-lite):** same reader; a looped controller emits (op, operand, operand) steps executed by an exact
  integer executor; talker = print a pointed value, copy a pointed prompt word (content-free keys), or a linear
  register readout. Programs teacher-forced from `steps` where they parse.
- **plain_tf (S):** d256 x 4 layers, 3.24M params. Matched params and compute.
- **plain_tf L2x2:** 2 layers looped twice, 1.67M params, matched compute.
- **plain_tf_steps (S):** plain_tf trained to write `steps` then ` # ` then the answer on the 11 arithmetic families
  (targets capped at 64 chars), scored on the text after the last `#`. Also scored as **C1'**: a calculator fills each
  `a op b =` while decoding, no retraining.
- Size rule: A and B within +-3% of 3.24M params (S). A 10.8M (M) pair runs only if money remains.
- lr 1e-3 (S); one retry at 5e-4 is allowed only if every arm gets it. A run counts only with status ok.

## Metrics
- **pooled-5 (primary):** micro exact match over dev in_dist + answer + frame + vocab + variant (6,040 rows).
- **chain-5:** the five chain families (chain_ops, chain_story2, story_chain3, state_update, var_chain) on the
  200-per-cell in_dist build (1,000 rows; built on the box with `--dev-per-cell 200`, train.jsonl hash asserted).
- Also reported: multi-step in_dist (12 families), variant, each split, held-out families (expected 0-5% for all).
- Statistic: per-seed paired difference d = design - baseline at the same seed (same init seed and data order).
  Report mean d, 95% CI = mean +- t*sd/sqrt(n), seeds positive; paired McNemar on chain-5 rows for confirm.
- Noise (from CALIBRATION.md, 4 seeds of plain_tf S): one-seed paired-difference sd sigma_P = 1.4 (pooled-5),
  sigma_V = 1.5 (variant). sigma_C (chain-5) is not measured yet: 3.0 is used.

## Screen (seeds 100 and 101 shared by every arm; 2-seed means)
GO for a design needs ALL of:
- **G1:** pooled-5 d vs plain_tf >= +1.0.
- **G2:** chain-5 d vs plain_tf >= +8, both seeds positive.
- **G3:** in_dist d vs plain_tf >= -2.0.
- **G4:** pooled-5 d vs plain_tf_steps >= -1.0 (for B also vs C1').
- **G5:** the wiring lesions below hold in both seeds.

## Confirm (fresh seeds 200-205; the screen winner vs plain_tf S and plain_tf_steps S)
- **PASS-1 (beats a same-size transformer):** pooled-5 d vs plain_tf >= +2.0 with CI above 0 and >= 5 of 6 seeds
  positive; chain-5 d >= +8 with CI above 0 and McNemar p < 0.01; in_dist d >= -1.0.
- **PASS-2 (Ben's criterion, beats similarly sized models):** PASS-1, plus pooled-5 d vs plain_tf_steps >= +1.0 with
  CI above 0, plus pooled-5 at least 2 points above fine-tuned EleutherAI/pythia-31m (30.5M params, same rows, order,
  batch and updates; paired on seeds 200-202; its lr picked from {1e-4, 3e-4, 1e-3} by 6k-update runs, which can only
  flatter it), plus above 8-shot HuggingFaceTB/SmolLM2-135M and pythia-31m without fine-tuning.
- **Secondary:** variant d vs plain_tf >= +2.0 with CI above 0.
- **FAIL:** pooled-5 d < +1.0, or in_dist d < -2.0. Between FAIL and PASS: inconclusive, no claim, no more spend.
- L2x2 joins confirm only if it came within 2 pooled-5 points of the winner in the screen.

## Lesion marks (every seed)
Wiring checks (hold by construction; they show the plumbing, not reasoning):
- shuffle_state in_dist <= 10; zero_state <= 5; loops:0 <= 5; loops:2n within 3 of intact;
- same-family donor swap drops in_dist by >= 20, with donor_match >= 50% on number and string families.
Real evidence, A:
- round-1 register interchange with a same-family donor: counterfactual match (the row's own steps 2..k applied to the
  donor's first value) >= 40% and own-answer match <= 30%;
- prompt-blind after round 1 (cross-attention off from round 2) puts chain-5 <= 10;
- in A0 only: loops:1 puts chain-5 <= 15 while one-step families stay within 5 points;
- A - A0 >= +8 on chain-5.
Real evidence, B:
- loops:1 puts chain-5 <= 5; loops:2 cuts chain-5 by >= 40 while one-op families stay within 5 points;
- noexec (every executor result invalid) puts program families <= 10;
- opswap (ADD and SUB swapped at inference): >= 90% of outputs equal the swapped program's value.

## Results that prove a design wrong
- **A:** chain-5 d < +3; or A - A0 < +3 (and if A0 - plain_tf < +3 too, answer-only recursion is ruled out); or
  counterfactual match < 15% (the loop recomputes from the prompt, the sandwich's failure); or in_dist d < -4.
- **B:** chain-5 d < +10; or pooled-5 d <= 0; or C1' within 3 points of B on both chain-5 and pooled-5 (then the
  credit belongs to the calculator plus the steps, not to B's structure).

## Budget
Screen about $1.1, confirm one design about $1.5, open LMs about $0.5 (box $0.45-0.55/h). If over $3, drop
pythia-14m first, then shrink the lr grid to {1e-4, 3e-4}. A second confirmed design or the 10.8M pair only if money
remains above the $1 floor.

## Addendum 1: ingredient test, place codes alone (written 2026-10-05 about 11:20 UTC, 7:20 AM ET, before these runs)
Why: after the first screen results, design A beats plain_tf by about +10 pooled-5 points, most of it on lookup and
rule families (cipher_map, fewshot_number_rule, seq_cycle, list_index) as well as chains. A's reader adds place codes
(each char's index from the right end of its word). This test asks whether place codes alone, given to plain_tf, buy
that gain (SYNTHESIS section 5, step 2). One change: `place: true` (one 16 x 256 table added at prompt chars, +4,096
params). Arms tfp (plain_tf + place) and tfstepsp (plain_tf_steps + place), seeds 100 and 101, paired with the screen's
tf and tfsteps runs (same seed; the extra table is created last, so every other weight starts identical).
- **Place codes explain most of A's gain:** tfp - tf pooled-5 d >= +5.0 (2-seed mean). Then A's slots and loop add
  only A - tfp, and A - tfp < +3 means A's custom structure adds nothing that counts.
- **Place codes do nothing:** tfp - tf pooled-5 d < +1.0.
- **Place codes help step writing too:** tfstepsp - tfsteps pooled-5 d >= +2.0; then tfstepsp becomes the bar every
  custom design must beat (G4 is re-scored against it as well and reported both ways).
- Reported per family as well (the lookup families above). 2 seeds only: this is a screen, not a claim.

## Addendum 2: B2 screen (written 2026-10-05 about 12:30 UTC, 8:30 AM ET, before any B2 code or run)
Screen verdicts so far (`custom_io/results/SCREEN-ANALYSIS.json`): A, A0 and L2x2 NO-GO. B NO-GO by the letter: G1-G4
pass (pooled-5 +14.2 vs plain_tf, +0.8 vs plain_tf_steps, -0.3 vs C1'; chain-5 +65.4), but G5 fails on one wiring
check, donor_match on the string families (both seeds). That check cannot pass for a pointer talker: a donor's state
points into the recipient's prompt, so the recipient's own word comes out. B2 (`design/design-B2.md`) is B plus one
change: a content-addressed copy talker. Seeds 100 and 101, paired with the existing tf, tfsteps and B runs at those seeds
(same code path and flags; B2 is expected to run on BensPC's 5070 Ti in bf16, the earlier runs ran on Vast 5090s in bf16).
**Copy-target families** (fixed now): letter_ops, copy_word, cipher_map, group_induct, digits_parity, exact match pooled over
the five dev splits (1,000 rows per seed; correction 12:50 UTC, before any B2 run: the dev data has 800 rows of these
families per seed, not 1,000; the marks are unchanged).
GO to confirm needs ALL of:
- G1-G3 as in the screen.
- **G4':** pooled-5 d vs plain_tf_steps >= +1.0 and vs C1' >= 0 (raised from -1: B already ties them).
- **G5':** the screen's wiring checks, with the string-family donor_match check replaced by: string-family donor drop
  >= 20 points on in_dist (the state, not the talker, decides what is copied).
- **B2.copy:** B2 - B pooled-5 >= +1.5 (2-seed mean).
- **Copy evidence:** lesion `nocopy` lowers the copy-target families by >= 20 points (each seed).
Proves the idea wrong: B2 - B pooled-5 < 0; or copy-target families rise < +3 vs B; or `nocopy` moves them by < 5
(the copy path is not used). Reported either way: B2 - B per split and per family, `nowordc`, all screen lesions.
If B2 is GO, the confirm (seeds 200-205) uses the PASS-1 / PASS-2 marks above unchanged, with B2 as the design.

## Addendum 3: Test B1 students (written 2026-10-06 about 00:40 UTC, 8:40 PM ET 10-05, before any student trained; the code was being built)
Plan B's Test B1 (`design/thinker-first-split-2026-10-05.md` section 6, branch `claude/project-thread-9ye9md`, PR #41;
Ben chose Plan B at 7:44 PM ET). This thread runs the student side. Full build spec, reviewed before any code:
`design/B1-students.md`. Its "operational choices" 1-13 are part of this addendum.
**Students:** B2-M on TEACH (`b2t`), B2-M on GEN (`b2g`), plain_tf-M on TEACH (`tft`). B2-M = ledger M cfg with copy and
the span talker (10,914,681); plain_tf-M = d_model 384, 6 layers, 6 heads, 32-char answers (10,782,336). Same recipe:
16,000 updates, batch 256, lr 7e-4, warmup 500, bf16, `--max-ans 32`. Screen seeds 300 and 301 (confirm 300-305), every
run of a seed on one device. Equal training-row counts in both arms (choice 3).
**Scores:** round-6 scorer (choice 2). New kinds pooled = NEW-KINDS-R5 + NEW-KINDS2-R6, 384 rows; FRESH-EN-R3, 192 rows.
**Marks (copied from the source, means over the screen seeds, unrounded):**
- **B1-a:** b2t - b2g on new kinds pooled >= +15 and b2t ahead on both seeds. Proved wrong: mean < +5.
- **B1-b:** b2t with a donor's state <= 10% on new kinds pooled. Donor = same kind, same question type, different
  answer, no shared answer position (choice 9; the plain same-kind pairing is read only, because a donor's pointer
  lands on the right word by position alone in 13-16% of those pairs).
- **B1-c:** b2t - tft on new kinds pooled >= +3 and b2t ahead on both seeds.
A mark is not judged if a run it needs is missing or invalid (`design/B1-students.md` section 5). Read only: loops:0,
the other lesions, GEN-HELDOUT-R4 (the GEN arm's own distribution), the held-out in-dist slices, atype splits, the
distance to the bare 1.2B 8-shot (75.0 FRESH; 67.7 R5, 77.6 R6) and to the sandwich (92.2 FRESH; 78.2 new pooled).
If B1-a is proved wrong, way B at this size is dead (source section 6): next single change a ~100M student.
**Data** (sha256 of the adapter's outputs, filled in before any student trains):
- Sources (recorded 2026-10-06 about 12:05 UTC, 8:05 AM ET, before any student trained), the default pair from the teacher-data thread (PR #46):
  TEACH = `plan-b/data/teach_clean.jsonl` (94,831 questions: every short answer plus 5,349 yes and 5,349 no, after a yes/no support filter;
  sha256 ea271eb4b143ca32a731278c7a0364128c58ec389fa3ba0353cce6573c1ecb05), GEN = `plan-b/data/gen_matched_94831.jsonl` (the same question
  count and type mix from round 6's generator; sha256 2098d01a7b1e2df0f5ace716811d2c354fcbbde7f56297cd312e10692abcb667). If the teacher-data
  thread's 1.2B-verified yes/no set lands before queue 35 starts, these lines and the two below are replaced by its build, still before any
  student trains.
- Built arms: 187,667 training rows each (16,000 updates x 256 = about 22 passes), held-out in-dist slices of 1,958 (TEACH) and 1,896 (GEN)
  rows. The overlap guard refused nothing; no eval passage or near-copy (max word Jaccard 0.73, none >= 0.8). Its "eval name" counts are
  common capitalised words (According, weekday names), not names. Packed for the PC as `custom_io/data_b1/plan_b.tgz`.
- Equal row counts take priority in choice 3: whole examples are dropped (seeded) from the longer arm, and only if an odd remainder is left, at most 3 rows
  are trimmed from the end of one seeded example (the manifest records `rows_trimmed_from_one_example`; 0 on the real-data trials).
- Adapter outputs are written with LF line ends on every machine, so the manifest sha256 is the same on Linux and Windows. Record one line per arm,
  in exactly this form (analyze_b1 reads it; `<hex>` = sha256 of `plan_b/<arm>/MANIFEST.json`, from the machine that builds the data the queue trains on):
  - teach MANIFEST.json sha256 40316ed14090e7e438030ce6ed403b9054d19f136e92c1d90c789955a1c3fe9d
  - gen MANIFEST.json sha256 9121d7ac26ffa5b04481a99f5817d6db0ce494a8357f0c79b1160f7d69ebc875

## Addendum 4: EmbeddingGemma 2 arms for B2 (written 2026-10-06 about 17:40 UTC, 1:40 PM ET, before any EG run; design/EG2-embedding.md)
Source: the marks at `/mnt/project-files/embeddinggemma/PASS-MARKS-meaning-teacher.md` (written 10-06 before any run), applied unchanged to both arms.
Ben (1:10 PM ET): no need to keep this one free of pretrained parts; use EmbeddingGemma 2 as the model's embedding.
**Arms** (each paired by seed with plain B2 `B2_s200`, `B2_s201` of queue 33, same PC, same recipe: 200k skills rows, 24,000 updates, batch 256,
lr 1e-3, bf16, `--cfg '{"copy":true}'` plus the one switch):
- **EGE** (`"eg_embed":true`): frozen EmbeddingGemma 2 text part (google/embeddinggemma-2 at revision 914f7f89, 271,002,624 params) gives the
  768-d per-token state of every prompt token (prompt = `task: sentence similarity | query: ` + prompt); each character gets its token's
  state through LayerNorm and a zero-initialised Linear(768 -> 256), added to B2's own character embedding before its conv reader. Trainable
  3,500,881; whole model with EmbeddingGemma counted 274,503,505.
- **EGT** (`"eg_teach":0.1`): training-only meaning teacher exactly as in the source: mean of the 8 control tokens after iteration t = 1 ->
  LayerNorm -> Linear(256 -> 256), loss += 0.1 * (1 - cos) to EmbeddingGemma's pooled vector of the training prompt, cut to 256 dims and
  re-normalised. The head (66,304) is dropped after training: shipped model = B2, 3,302,481, nothing pretrained inside. Deviation from the source:
  the teacher vectors are computed on the fly from each training batch (same frozen model, same prompts) instead of once into a file; dev
  prompts are still never embedded for this arm (tested).
**Pass (each arm on its own, all must hold, 2-seed screen):**
1. pooled-5 gain >= +1.0 on BOTH seeds.
2. variant-split gain >= +3.0, 2-seed mean.
3. No dev split (in_dist, answer, frame, vocab, variant) drops more than 2.0, 2-seed mean.
4. chain-5 >= 99.0 on both seeds.
5. Leak check: loops:0 in_dist <= 5% on both seeds; donor in_dist <= 5% on both seeds (absolute, as written; plain B2's own values on the
   same seeds are reported next to them, read only, because B2 itself read 6.76 at loops:0 on screen seed 101).
**What proves it wrong:** any pass mark missed for an arm -> that arm stops. EGT passing -> the source's shuffled-teacher control (teacher
vectors permuted across training rows, 1 run per seed; defined now: a FIXED map, `numpy.random.RandomState(0).permutation` over the
train.jsonl line order with any fixed point swapped with the next line, and each row's target is EmbeddingGemma's vector of its mapped
row's prompt, the same map every epoch, not a per-batch shuffle): if it keeps >= 2/3 of EGT's pooled-5 gain the gain is regularisation, not meaning ->
reject. EGE passing -> no shuffle control (the embedding ships inside the model, so its gain counts whatever its source); next is the 6-seed
confirm at the same marks. Nothing is adopted on 2 seeds (noise rule).
**Size rule:** EGE is a 274.5M model (borrowed parts count), so a pass is a B2-internal result; whether it beats similar-size models is a separate
comparison against ~135M-360M models, not judged here. EGT ships at 3,302,481.
**Read only:** the family split, per-family changes, the other lesions, steps per second and peak memory.

## Addendum 5: Test LR, a readout loss at every round for B2 (written 2026-10-06 about 18:40 UTC, 2:40 PM ET, before any LR code or run)
Opened by gate G1 of design/LOOPS-probe.md (probe result there). **The one change** (`--cfg '{"copy":true,"round_readout":1.0}'`, default 0 =
B2 exactly): during training, after every iteration t with L + 1 <= t <= 6 (L = the row's gold program steps, so its program is already written;
t = 7 is the normal final readout), B2's own talker heads read the state (mode, answer pointer, word pointer, GEN registers with the copy
path) and get the same losses as the final readout. Each row's loss is averaged over its rounds and added with weight 1.0 (fixed, no sweep).
No new parameters: 3,302,481, nothing pretrained. Eval is unchanged (answers after the trained 8 loops).
**Runs:** LR_s200, LR_s201, paired with B2_s200 / B2_s201 of queue 33 on the same PC and recipe (queue 37, after queue 36).
**Pass (all, 2-seed screen):**
1. pooled-5 gain >= +1.0 on BOTH seeds.
2. Stability, the mechanism: in_dist at loops:16 minus in_dist at the trained 8 loops >= -0.3 on both seeds (plain B2 read -1.1 and -0.8 on the
   screen checkpoints; its q33 values on seeds 200 / 201 are reported next to it).
3. No dev split (in_dist, answer, frame, vocab, variant) drops more than 2.0, 2-seed mean.
4. chain-5 >= 99.0 on both seeds; loops:1 chain-5 <= 5 on both seeds (the program still needs its rounds).
5. Leak: loops:0 in_dist no more than 1.0 above plain B2 on the same seed, and donor in_dist <= 5, on both seeds.
**Proved wrong:** pooled-5 gain < 0 (2-seed mean), or mark 2 missed on both seeds (the extra loss does not make the answer stable) -> stop;
no halting gate or extra-loop test follows from this probe. A pass goes to the 6-seed confirm at the same marks (noise rule).

## Addendum 6: B2's reader without its letter window (written 2026-10-06 about 19:55 UTC, 3:55 PM ET, before any EGR or R0 run)
Ben objects to the reader's +-4-character window (its 2 conv blocks, `models/reader.py`). The window was set by construction in
`design/SYNTHESIS.md` before any training, so that all cross-word work falls to the thinker; no other window size was ever tried. Two new arms,
each one change from a run that already exists (no code change: `reader_layers` is an existing switch):
- **EGR** (`{"copy":true,"eg_embed":true,"reader_layers":0}`): EmbeddingGemma 2 replaces the window. A char's input is its letter, position and
  place code plus the zero-initialised projection of its EmbeddingGemma token state (as in EGE), then a LayerNorm, with no conv: a char sees
  its neighbours only through EmbeddingGemma, which reads the whole prompt. One change from EGE (window removed). Trainable 2,843,985; whole
  model 273,846,609 with EmbeddingGemma's 271,002,624 counted.
- **R0** (`{"copy":true,"reader_layers":0}`): plain B2 with the window removed and nothing added, so each char sees only itself before the
  thinker. One change from B2. 2,645,585 params (656,896 fewer, all in the removed conv blocks, which can only hurt it). Diagnostic, never adopted.
**Runs:** seeds 200 and 201, the B2 recipe on the same PC, paired with B2_s200 / B2_s201 of queue 33. Queue 36 now runs EGR, then R0, then EGE
(addendum 4, unchanged), ahead of queue 35; EGT moves to queue 38.
**EGR pass (all must hold, 2-seed screen, each seed against plain B2 on the same seed): "EmbeddingGemma can replace the window"**
1. pooled-5 change >= -1.0 on both seeds.
2. New words and new wording (the vocab and frame splits, exact match pooled over both) change >= 0.0, 2-seed mean.
3. No dev split (in_dist, answer, frame, vocab, variant) drops more than 2.0, 2-seed mean.
4. chain-5 >= 99.0 on both seeds.
5. Leak: loops:0 in_dist no more than 1.0 above plain B2 on the same seed, and donor in_dist <= 5, on both seeds.
A pass with pooled-5 change >= +1.0 on both seeds is also labelled "better than B2" (a label, not an extra mark).
**Proved wrong:** pooled-5 change < -3.0 (2-seed mean), or chain-5 < 95.0 on either seed: EmbeddingGemma cannot stand in for the window at this
recipe. A pass goes to the 6-seed confirm at the same marks before anything is adopted (noise rule).
**R0 verdict (diagnostic):** B2 minus R0 pooled-5 >= +1.0 on both seeds -> "the window matters"; within 1.0 either way on both seeds -> "the
window does nothing on these tests" (it can go at no cost); anything else -> "unclear".
**Size rule** as in addendum 4: EGR is a 273.8M model, so a pass is a B2-internal result. **Read only:** EGR minus EGE (what the window adds on
top of EmbeddingGemma), per-split changes, the family split, steps per second.

## Addendum 7: EGO, EmbeddingGemma 2 as B2's whole reader (written 2026-10-06 about 20:10 UTC, 4:10 PM ET, before any EGO run)
Ben (3:44 PM ET): EmbeddingGemma takes the question in, hands it to the thinker, the thinker thinks, the talker answers. **EGO**
(`{"copy":true,"eg_embed":true,"reader_layers":0,"letters_in":false}`) is EGR with one change: the letters are no longer added to the reader's
input. Each character position carries only its position, its place code and the projection of the EmbeddingGemma state of the word piece it sits
in, so nothing B2 learned about letters reaches the thinker; EmbeddingGemma alone reads the question. The talker is unchanged: it still copies
words and letters by position and spells with its letter table (the GEN readout is tied to that table, so it stays, as the talker's alphabet).
Same parameters as EGR: trainable 2,843,985, whole 273,846,609 with EmbeddingGemma counted. Kept per character because the copy and spell
paths point at characters; a word-piece-level thinker input would change the talker too (two changes), so it is not this arm.
**Runs:** EGO_s200, EGO_s201, the B2 recipe on the same PC, paired with B2_s200 / B2_s201 of queue 33. Queue 36 now runs EGO, then EGR, then R0;
EGE (addendum 4) moves to queue 38 with EGT.
**Marks:** exactly addendum 6's EGR marks 1-5, its proved-wrong rule and its "better than B2" label, each seed against plain B2 on the same seed.
**Read only:** EGO minus EGR (what B2's own letters add once EmbeddingGemma reads the question), per family, with the letter families
(letter_ops, copy_word, cipher_map, digits_parity, group_induct) listed on their own: those are where losing the letters should show first (suggested).

## Addendum 8: EGM, a trained 2-layer adapter between EmbeddingGemma and the thinker (written 2026-10-06 about 20:25 UTC, 4:25 PM ET, before any EGM run)
Ben (3:47 PM ET) asked for an intermediate between EmbeddingGemma and the thinker. EGO already has one: a LayerNorm and one trained linear map
(768 -> 256), then the reader's own final LayerNorm. **EGM** (`{"copy":true,"eg_embed":true,"reader_layers":0,"letters_in":false,"eg_adapter":"mlp"}`)
is EGO with one change: the adapter is LayerNorm -> Linear(768, 256) -> GELU -> Linear(256, 256) (LLaVA-1.5's projector shape; the last layer
zero-initialised like EGO's), and the reader's final LayerNorm still normalises its output. Trainable 2,909,777 (+65,792); whole 273,912,401 with
EmbeddingGemma counted. EmbeddingGemma stays frozen.
**Runs:** EGM_s200, EGM_s201, paired with B2_s200 / B2_s201 of queue 33. Queue 36 is now EGM, EGO (the linear check), EGR; R0 moves to queue 38.
**Marks:** exactly addendum 6's marks 1-5, proved-wrong rule and "better than B2" label, each seed against plain B2 on the same seed.
**Which adapter goes on:** if EGM and EGO both pass, the one with the higher 2-seed pooled-5 mean goes to the 6-seed confirm; if they are within
0.5 of each other, the linear one (smaller and simpler). Read only: EGM minus EGO per seed.
