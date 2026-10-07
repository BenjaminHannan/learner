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
- **Extra guard on B1-a** (added 2026-10-06 about 21:25 UTC, 5:25 PM ET, before any student trained; thinker-first B1 addendum, commit
  32cd2128d on `claude/project-thread-9ye9md`): B1-a is also scored on the short-answer questions of new kinds pooled alone (340 of the 384
  rows). If B1-a passes overall but that short-answer-only gap (b2t - b2g, mean over the screen seeds) is below +10, the verdict is NOT SHOWN
  (driven by yes/no), not PASS. It only tightens B1-a. Per-kind and per-type scores of every arm are reported (read only). The data above is
  unchanged: TEACH = teach_clean, GEN = gen_matched_94831 (the thinker-first thread withdrew its 5:15 PM ET switch to the 171,940-row pair at
  5:20 PM ET; `teach.jsonl` is 51% yes/no).

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

## Addendum 9: EGW, thinker slots built for EmbeddingGemma (written 2026-10-06 about 20:20 UTC, 4:20 PM ET, before any EGW run and before any EGM or EGO result)
Ben (3:48 PM ET): instead of an adapter, new thinker slots made for Gemma. **EGW**
(`{"copy":true,"d":768,"n_heads":12,"eg_embed":true,"reader_layers":0,"letters_in":false,"eg_adapter":"none"}`) builds B2's thinker and talker at
EmbeddingGemma's width, 768 (12 heads of 64, the same head size as B2), so EmbeddingGemma's states go in through a LayerNorm with no adapter:
each char's input is LayerNorm(its word piece's state) + position + place code, then the reader's final LayerNorm. The thinker's own first layers
do the adapting. Trainable 22,164,357; whole 293,166,981 with EmbeddingGemma counted. Same recipe as every arm (24,000 updates, batch 256, lr 1e-3).
**This is two changes from EGO, not one:** no adapter AND a thinker 3x wider (7.8x the trainable params). A win cannot be split between the
direct slots and the extra width; a 768-wide B2 with its own letter reader would split it and is added only if EGW wins.
**Runs:** EGW_s200, EGW_s201, paired with B2_s200 / B2_s201 of queue 33. Queue 36 is now EGW, EGM, EGO; EGR and R0 move to queue 38.
**Marks:** exactly addendum 6's marks 1-5, proved-wrong rule and "better than B2" label, against plain B2 on the same seed.
**Which EmbeddingGemma reader goes on (replaces addendum 8's rule; no EGM, EGO or EGW result exists yet):** among EGW, EGM and EGO, those that pass;
the highest 2-seed pooled-5 mean wins, but any passing arm within 0.5 of it that is smaller wins instead (smallest first). The winner goes to the
6-seed confirm at the same marks. Read only: EGW minus EGM per seed.

## Addendum 10: EGW moves to two rented 5090s (written 2026-10-06 about 20:45 UTC, 4:45 PM ET, before any EGW, EGM or EGO result)
EGW is too slow for Ben's PC: 0.75 updates/s, about 8.9 h a run, and it fills the 16 GB card, so the second seed cannot share it and EGM, EGO and
queues 35, 37 and 38 would wait about 18 h. The recipe stays exactly as addendum 9 (24,000 updates, batch 256, lr 1e-3, bf16); cutting updates or
batch would make EGW unfair against B2. Instead each EGW seed runs on its own rented RTX 5090 (custom_io/queue/egwA, egwB; box.sh with
transformers 5.19 and EmbeddingGemma at the pinned revision), and **each box also trains plain B2 on the same seed (B2V_s200, B2V_s201)**, same
flags as queue 33's B2. The PC's EGW_s200 is stopped at under 2,000 updates; nothing from it is scored.
**Base:** every arm is judged against plain B2 of the same seed **on the same machine** (config.device and config.data equal), as before: EGW
against B2V on its box; EGM, EGO, EGR, EGE, EGT and R0 against queue 33's B2 on the PC. Marks, proved-wrong rule, label and the addendum 9 choice
are unchanged; the choice already compares each arm's pooled-5 change against its own base, so the machine drops out.
**Device check (read only):** B2V minus queue 33's B2 per seed on pooled-5, reported next to the EGW result. If it is more than 3 points on either
seed, the EGW result is reported as "machine-sensitive", and EGW is not picked over a passing PC arm until it is re-run on the PC.
**Cost cap:** each box stops itself after 7.5 h (about $3.75 at $0.49-0.50 an hour with its disk), under the $4 a job standing cap, and both
together leave the Vast credit (8.77 dollars before renting) above the 1 dollar floor.

## Addendum 11: EGM and EGO join EGW on the rented boxes (written 2026-10-06 about 21:10 UTC, 5:10 PM ET, before any EGW, EGM or EGO result)
On the 5090s EGW trains at about 3 updates/s (4x the PC), so each box finishes EGW and B2V in about 2.5 h. On the PC, EGM_s200 alone holds
13.6 GB, so queue 36 ran one run at a time (2.4 h each, done about 2:20 AM ET) and held queues 35, 37 and 38 behind it. So EGM and EGO move to
the boxes too, by seed: **box A trains EGW_s200, B2V_s200, EGM_s200 and EGO_s200; box B the same for seed 201** (custom_io/queue/egwA,
egwB), same recipe and flags. The PC's EGM_s200 is stopped at under 40% of its updates; nothing from it is scored. Queue 36 is retired and the
PC goes straight on to queues 35, 37 and 38.
**Base:** unchanged rule (plain B2 of the same seed on the same machine): every EmbeddingGemma reader arm for seed 200 is judged against B2V_s200
on box A, and seed 201 against B2V_s201 on box B. EGR, R0, EGE and EGT (queue 38, PC) stay against queue 33's B2.
**Choice (addendum 9) and the device check (addendum 10):** EGW, EGM and EGO now share machines seed by seed, so the choice between them is a
same-machine comparison. The addendum 10 exclusion applies only when the passing arms were judged on different machines.
**Cost:** the boxes stay up about 1.5 h longer (about $1.50 more in all); the 7.5 h self-stop is unchanged.

## Addendum 12: EGR moves to the rented boxes too (written 2026-10-07 about 00:00 UTC, 8:00 PM ET 10-06, before any EGR run)
EGW failed (pooled-5 -3.39 / -5.30 against B2V on its box). Its losses sit in the tasks that need each letter: cipher_map fell from 100 to 1.2,
and its training loss stayed 5-7x B2V's, almost all of it in the GEN talker that writes answers letter by letter (custom_io/diag_eg.py tests
how much spelling EmbeddingGemma's states keep). EGR (addendum 6: EmbeddingGemma plus each char's own letter, no window,
`{"copy":true,"eg_embed":true,"reader_layers":0}`) is the arm that gives the thinker both. It was waiting in queue 38 on the PC, hours away, so
it runs now on the two boxes, which are free once EGO ends: **box A trains EGR_s200, box B EGR_s201** (custom_io/queue/egwA/44, egwB/45), same
recipe and flags as queue 38. **Base:** B2V of the same seed on the same box (the same-machine rule). Marks: exactly addendum 6's. Queue 38 on
the PC drops its two EGR lines. Cost about $2 more; credit before these runs $5.30, and each box's 1-hour idle exit keeps it above $1.
**Diagnosis check (read only, not a mark; added about 00:15 UTC 10-07, 8:15 PM ET, while EGR_s200 and EGR_s201 were at their first updates and
before any EGR score existed):** EGO, EGM and EGW all lost cipher_map (seed 200: 100 to 10, 2.5, 2.5). If missing letters are the cause, EGR's
cipher_map in_dist is >= 50 on both seeds. Below 50 on either seed means the letter explanation is wrong.

## Addendum 13: R0 and EGE move to the rented boxes (written 2026-10-07 about 01:10 UTC, 9:10 PM ET 10-06, before any R0 or EGE run)
**EGR_s200 result (box A, against B2V_s200):** pooled-5 -0.26, chain-5 98.8, loops:0 in_dist 11.54 (B2V 1.40). Its cipher_map in_dist is
**5.0** (B2V 100), so addendum 12's diagnosis check already fails on seed 200: giving the thinker each letter's own code back does not bring
cipher_map back, and the explanation "EmbeddingGemma hides the letters, so the thinker cannot do letter tasks" is **wrong as stated**. The
probe facts (diag_eg.py: a linear read gets 23% of letters from EmbeddingGemma's states vs 99.9% from B2's reader) still stand; what fails is
the step from them to the cipher losses. EGR's full verdict waits for EGR_s201 (box B).
**What every losing arm shares:** EGO, EGM, EGW and EGR all have `reader_layers: 0`, so none has B2's +-4-character window, and all have
EmbeddingGemma. Two arms already written in addenda 4 and 6 separate these: **R0** (window removed, nothing added) and **EGE** (window kept,
EmbeddingGemma added). They were waiting in queue 38 behind queue 35 on the PC, hours away, so they run now on rented 5090s:
- **Box B** (54540404, which trained B2V_s201): job 47, R0_s201 and EGE_s201 side by side, after EGR_s201. Base: B2V_s201 (same box).
- **Box C** (new, `--qsub /egwC`, same image and env as boxes A and B): job 46, R0_s200 and EGE_s200 side by side. Base: B2V_s200 from box A
  (54539753, destroyed after its jobs). Box C is a different RTX 5090 with the same image, software pins and data; base_for() pairs runs by
  config.device and config.data, which match. This is disclosed as a weaker pairing than same-box; no plain B2 re-run is bought for it.
Same recipe and flags as queue 38's lines. Queue 38 on the PC drops its R0 and EGE lines and keeps EGT. Cost about $1.50 more; credit $9.29
before these runs, and the 1-hour idle exit and MAXH 7.5 keep it above $1.
**Marks:** unchanged. EGE: addendum 4 (the "better than B2" test is EGE's mark 1, pooled-5 gain >= +1.0 on both seeds). R0: addendum 6's
diagnostic verdict.
**Window check (read only, not a mark):** "the window is what cipher_map needs" predicts R0 cipher_map in_dist < 50 on both seeds and EGE
cipher_map in_dist >= 90 on both seeds. R0 >= 50 on either seed means removing the window is not the cause, and the cause is adding
EmbeddingGemma (then EGE should lose cipher_map too). Any other pattern is "unclear".
**Timing note (about 02:25 UTC 10-07, 10:25 PM ET 10-06, before EGE_s201 or R0_s201 started; R0_s200 had just finished and was seen):** box B
runs slower than planned (EGR_s201 ends about 02:45 UTC), and R0_s201 plus EGE_s201 side by side would end at about box B's 7.5-hour cap
(04:20 UTC). So box B's job 47 is now EGE_s201 alone (PAR 1, base B2V_s201 on the same box), and R0_s201 runs on box C as job 48 after job 46,
with B2V_s201 from box B as its base (the same weaker pairing as box C's seed-200 runs). No mark, recipe or flag changes.
**Second timing note (about 03:05 UTC 10-07, 11:05 PM ET 10-06, before any EGE score existed):** box B trains EGE_s201 at only 2.8 updates/s
alone (step 5,500 after 36 min), so it would end about 04:50 UTC, past box B's 7.5-hour cap (about 04:20 UTC), which kills every job. Box B is
destroyed now (all its finished jobs, 41, 43 and 45, are collected) and EGE_s201 restarts from scratch on box C as job 49, after jobs 46 and 48,
with B2V_s201 from box B as its base. Both EGE seeds are therefore paired across boxes (same GPU model, image and data), as are both R0 seeds.
No mark, recipe or flag changes; any EGE pass still needs the 6-seed confirm, which will pair each seed on one machine.

## Addendum 14: EGK, EmbeddingGemma feeds only the thinker (written 2026-10-07 about 03:20 UTC, 11:20 PM ET 10-06, before any EGK run; EGE_s201 and R0_s201 not yet scored)
**What we know (seed 200, read only):** R0 (window removed) lost 6.65 on pooled-5 and cipher_map fell to 12.5, so the window, not
EmbeddingGemma, is what cipher_map needs. EGE (window kept, EmbeddingGemma added before the window) gained +1.63 on pooled-5 against B2V_s200
(frame +4.26, vocab +2.75, variant +1.44) and kept cipher_map at 97.5, but read 18.09 at loops:0 in_dist (mark 5 limit 5; B2V 1.40), so EGE
already misses mark 5 on seed 200. At loops:0 the controller does nothing, so those answers come from the talker reading the reader output
directly: the WORD content keys, the number-slot pools and the GEN copy keys all take the reader output, which in EGE carries EmbeddingGemma
(EGE loops:0 hits: copy_word 85, prop_eval 70, kin_chain 55, object_track 52.5, story_chain3 42.5).
**EGK** (`{"copy":true,"eg_embed":true,"eg_thinker":true}`, `models/ledger.py`): one change from EGE. The reader runs twice with the same
weights; the run with the EmbeddingGemma term feeds only the controller's cross-attention to the reader output, and the number slots, the WORD
content keys and the GEN copy keys take B2's own reader output, without EmbeddingGemma. No new parameters: trainable 3,500,881, whole
274,503,505 (EmbeddingGemma counted). At step 0 it computes exactly what B2 and EGE compute (eg_proj is zero; tested in test_thinker_only).
**Runs:** seeds 200 and 201, the B2 recipe and flags of queue 38 (24,000 updates, batch 256, lr 1e-3, bf16), on rented RTX 5090s (the PC is
busy with queue 35): EGK_s200 on box C (job 50), EGK_s201 on a new box D (job 51, same image and env). Bases: B2V_s200 (box A) and B2V_s201
(box B), the cross-box pairing disclosed in addendum 13.
**Pass:** exactly addendum 4's five marks, unchanged (1 pooled-5 gain >= +1.0 on both seeds; 2 variant gain >= +3.0, 2-seed mean; 3 no dev
split drops more than 2.0, 2-seed mean; 4 chain-5 >= 99.0 on both seeds; 5 loops:0 in_dist <= 5 and donor in_dist <= 5 on both seeds,
absolute). A pass is "better than B2" by mark 1 and goes to the 6-seed confirm at the same marks, each seed's arm and plain B2 on one machine.
**Proved wrong:** EGK's 2-seed mean pooled-5 gain < +0.5 means EGE's gain needed the talker's direct view of EmbeddingGemma, not the thinker's
(the thinker does not turn EmbeddingGemma's meaning into better programs at this recipe).
**Read only:** EGK minus EGE per split, per family and at loops:0; the prediction that EGK's loops:0 in_dist is within 1.0 of B2V's.
**Size rule** as in addendum 4: a 274.5M model, so a pass is a B2-internal result.
**Retry note (about 05:05 UTC 10-07, 1:05 AM ET, before any EGK score existed):** EGK_s201 (box D, job 51) hit a non-finite loss at update
3,000 (logged loss 0.418 at 2,500, NaN at 3,000; status `nonfinite_loss`), the first non-finite run in this project; EGE_s201 on the same seed
passed update 3,000 normally and EGK_s200 is training normally. A run that is not status `ok` is not judged, so EGK_s201 runs once more,
identical (job 52, box D). If the retry is also non-finite, EGK fails (unstable at this recipe) and stops; it is not retried again.
**EGK result (about 05:45 UTC):** the retry also went non-finite (update 4,500), so EGK **fails as unstable**. Read only, seed 200 (status ok):
pooled-5 +0.98 against B2V_s200 (EGE +1.59), loops:0 in_dist **13.68**. EmbeddingGemma cannot reach EGK's talker at loops:0
(test_thinker_only), yet the zero-round score stays high, so the explanation written above (EGE's talker reads EmbeddingGemma directly)
is **wrong** as the cause of EGE's loops:0 score. Shown instead: the loops:0 score varies widely across runs that share the talker design
(plain B2: 1.40, 4.34, and 6.76 on screen seed 101; EGE 18.09 and 4.49; EGK 13.68).

## Addendum 15: EGE 6-seed confirm against plain B2 (written 2026-10-07 about 05:40 UTC, 1:40 AM ET, before any run of seeds 202-207 with EmbeddingGemma)
**Screen result (addendum 4 marks, 2 seeds, against B2V on the rented boxes):** EGE **FAILS**. Mark 1 holds (pooled-5 +1.59 / +2.12), mark 3
holds (every split up on the 2-seed mean: in_dist +1.18, answer +0.25, frame +3.60, vocab +2.69, variant +1.70), mark 4 holds (chain-5 99.9 /
100.0); mark 2 misses (variant +1.70, needs +3.0) and mark 5 misses on seed 200 (loops:0 in_dist 18.09, limit 5; seed 201 4.49, plain B2
4.34). By addendum 4 the arm stops. EGK (addendum 14), the fix for the leak, failed as unstable.
**Why a confirm anyway, and who decides:** the variant +3.0 mark was the meaning-teacher test's own target (it came with EGT's source marks),
and the absolute loops:0 <= 5 mark is one plain B2 itself misses (6.76 on screen seed 101). Ben's goal is a Gemma version that beats plain B2.
Running this confirm despite the failed screen is **Ben's call**; it is staged on the PC behind queue 38 so it costs nothing until he
answers, and it is removed if he says stop. It is a new test on fresh seeds with its marks fixed here, not a re-judging of seeds 200-201.
**Runs:** fresh seeds 202-207, EGE exactly as in addendum 4 and plain B2 with queue 33's flags, each seed's pair on one machine:
on the PC (queue 39) plain B2_s202..s205 are queue 33's runs and B2_s206, B2_s207 are new. If Ben picks rented 5090s instead, each box trains
EGE and plain B2 (B2V) of its seed.
**Pass (all must hold):**
1. pooled-5 gain >= +1.0 on the 6-seed mean, and EGE ahead of plain B2 on at least 5 of the 6 seeds.
2. No dev split (in_dist, answer, frame, vocab, variant) drops more than 2.0 on the 6-seed mean.
3. chain-5 >= 99.0 on every seed.
4. Leak: the 6-seed mean of loops:0 in_dist is no more than plain B2's 6-seed mean + 1.0, and donor in_dist <= 5 on every seed.
**Proved wrong:** pooled-5 gain < +0.5 on the 6-seed mean, or EGE behind plain B2 on 3 or more seeds.
**Size rule** as in addendum 4: EGE is a 274.5M model with EmbeddingGemma counted, so a pass is a B2-internal result ("the Gemma version of B2
beats B2"), not a claim against other models of its size. **Read only:** the variant gain, per-family changes, loops:0 per seed, and every
seed's sign.

## Addendum 16: D0, the digit check before T1 (written 2026-10-07 about 15:55 UTC, 11:55 AM ET, before any D0 run)
Marks are the architecture thread's, sealed in `/mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md` (D0 section and Amendment 1).
This addendum only fixes how this thread reads them; where it chooses, it chooses the stricter reading. No training; CPU; the six q33 B2
checkpoints (branch `claude/b2-confirm-checkpoints` f41d0f7d5, sha256-checked), code `custom_io/diag_d0.py`.
- **Prompts:** the five pooled dev splits (in_dist, answer, frame, vocab, variant), deduplicated. Dev numbers are mostly 1-3 digits, so
  every place up to the 9th gets data from copies of each prompt in which every number is replaced by a random number with 1-9 digits
  (length uniform 1-9, no leading zero; 8 copies per prompt, fixed seed; copies over 208 chars dropped). The prompt-level split is
  75% train / 25% held out, fixed and the same for every seed; all copies of a prompt sit on the same side.
- **Official reading probe:** for each number (every `\d+` run of 1-9 digits), the reader output X at the 9 characters ending at the
  number's last digit (zeros before the prompt start), concatenated -> one linear classifier per place p = 1..9 (the digit, or "no digit
  here") and one for the digit count. Trained on the train prompts, scored on held-out prompts. Per-place accuracy is scored only on
  numbers that have that place (the "no digit" rows are reported apart, since they would pad the score).
- **Mark (stricter reading):** reading passes only if every place 1-9 and the digit count are >= 99.0% on held-out prompts on EVERY seed
  200-205. The architecture file's own mark does not say "every seed"; this is a tightening.
- **Read only, no mark:** (a) the same probe scored on the real dev numbers (held-out prompts, unsubstituted); (b) the digit from the X of
  that digit's own character alone; (c) the digit from the mean of X over the number's span (what B2's number slots add to the exact value
  code), to show what the pooled path keeps.
- **Writing:** B2's talker has no learned digit writer (NUM prints `str(value)` and the 8-letter GEN path never trained on digits,
  Amendment 1), so a copy test on these checkpoints would need training. Per the D0 text ("if that needs the T1 build, run it on the T1
  screen instead and say so"), writing exact-copy >= 99% is scored on the T1 screen checkpoints, not here.
- **Digits-only reader control** (Amendment 1): run only if B2's reader misses the reading mark. If B2's own reader passes, the control
  cannot change the reading verdict and is not run (disclosed).
- **Free check from the coordinator, read only:** controls 2-7 of the thinker state are never read by a head. Lesion `ctl27` sets
  Z[:, 2:8] to zero after every controller iteration at test time; report pooled-5, chain-5 and per-split changes against intact B2 on
  seeds 200-205 (dev splits only).
- **Seed SD recheck (from q33 RESULT.json, shown):** B2's own pooled-5 SD across seeds 200-205 is 0.63 (73.00, 74.27, 74.74, 74.02,
  73.63, 74.47). The 0.94 in the T1 marks is the SD of the paired difference B2 minus plain_tf (CONFIRM-ANALYSIS.json), not B2's own
  spread. Reported to the architecture thread; no T1 mark is changed here.

## Addendum 17: T1, the calculator outside the model (written 2026-10-07 about 16:15 UTC, 12:15 PM ET, before any T1 run)
Marks are the architecture thread's, sealed in `/mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md` (Ben 10:49 and 11:35 AM ET 10-07:
the calculator is a tool the talker calls; if it only works inside, a link is broken, and the fix is that link, never moving it back in).
Build: `custom_io/models/tool.py` (model name `tool`, cfg `{}`), 3,277,393 params (B2 3,302,481, -0.76%; inside +-3% of 3.24M). Every weight it
shares with B2 starts identical at the same seed (tested). Same recipe as q33's B2: 24k updates, batch 256, lr 1e-3, bf16, 8 fixed loops.
- **What the talker writes:** at rounds 1-7, an op word (B2's op head; NOOP = no call) and two operand strings written cell by cell, units
  first, by B2's own pointer-generator (the vocabulary or a copy of any context char). `calc()` is plain Python over that text and returns the
  result string or `?`. The entry `op a b = r` (the call is echoed, Ben's "any other necessary information") is read by the reader as its own
  string (positions from 0, at most 40 chars) plus a learned entry-order vector, and the thinker sees it from the next round on.
- **Disclosed choices:** (1) the 16 workspace slots for the PROMPT numbers stay, each the reader's mean over the number's digits + ordinal + type,
  with NO value code (the regex only says where a number is); the 4 constant slots and 7 result slots are gone (constants are written from the
  vocabulary). (2) B2's NUM mode (Python `str()` of a slot value) is gone: those rows are GEN rows and the 9 registers write the answer, copying
  from the prompt and the entries. WORD is B2's. (3) Teacher forcing: the gold calls and their results are the entries (the same text `calc()`
  returns for them: 0 mismatches on 2,053 training calls, tested); the call writer is trained by -log p of the gold operand strings, either order
  for ADD MUL MIN MAX. (4) Lesions keep B2's names: `noexec` = the calculator returns `?` for every call (tool off), `opswap` = the calculator
  swaps add and sub, `nocopy` = no copy in calls or answers.
- **Pairing:** inside = q33's plain B2 (BensPC, seeds 200-205), not retrained. T1 runs on BensPC after q39; if a run lands elsewhere, the
  cross-machine pairing is disclosed with its result.
- **Screen (s200, s201), as sealed:** pooled-5 T1 minus B2 >= -2.0 on both seeds, and chain-5 >= 95 on both. **Tightening:** the D0 writing
  check is scored here (addendum 16): `write_copy` operand copy and answer copy (every calculator result replaced by a random 1-9 digit string;
  the answer part only 1-8 digits, the GEN limit) must be >= 99.0 on both seeds too. Any miss: no 6-seed run; the report names the link
  (input digits, step choice, call writing, result reading) from call accuracy, write_copy, tool-off and the lesions, and the fix is one change
  to that link, re-screened.
- **6-seed confirm, as sealed:** (1) the 95% CI of T1 minus B2 on pooled-5 inside +-1.0; (2) chain-5 mean within 1.0 of B2 and >= 99.0 on 5 of 6
  seeds; (3) tool off: the noexec program set (NUM rows whose gold answer slots are all result slots, B2's `noexec.program_families`) < 5%;
  (4) loops:0 in_dist <= 5 and donor in_dist <= 5 on every seed (B2's values shown beside them); (5) opswap: >= 99% of the affected chain-5 rows
  give the swapped value (affected = right when intact, the answer is a call result, and the replay of the model's own calls with add and sub
  swapped changes it; sources are matched by text, the latest earlier result first); (6) no dev split mean drop > 2.0. Proved wrong: mean
  < -2.0 or chain-5 mean < 95. Between: not shown.
- **SD note (shown, reported, no mark changed):** the 0.94 is the SD of the paired difference B2 minus plain_tf; B2's own seed SD is 0.63. With
  a paired SD near 0.94 the CI half-width is 2.571 x 0.94 / sqrt(6) = 0.99, so mark (1) passes only if the mean difference is within about
  +-0.01 of zero; with SD 0.63, within about +-0.34. Sent to the architecture thread to decide before the 6-seed run; never loosened here.

## Addendum 17, amendment (written 2026-10-07 about 17:25 UTC, 1:25 PM ET, before any T1 run)
- **Parity mark 1 re-sealed by the architecture thread (MARKS-D0-T1 Amendment 2), mirrored here word for word:** 1a the 6-seed mean of T1 minus
  B2 on pooled-5 is >= -1.0; 1b the lower bound of its 95% CI is >= -2.0; 1c T1 >= B2 - 1.0 on at least 5 of the 6 seeds. It replaces "the 95% CI
  inside +-1.0", which no model could pass at the observed seed spread (SD note above). Marks 2-6, the screen and the proved-wrong line are unchanged.
  `analyze_t1.confirm` computes 1a-1c and prints the paired SD of T1 minus B2 beside the verdict.
- **T1's own leak definitions (fixed before the first run):** zero-round = lesion `loops:0`: the thinker runs no round, so no call is written and
  the talker answers from the initial state and the question; donor = the donor row's whole thinker output (its registers, its transcript of calls
  and results, and its mode and word logits) with the current row's question; the talker copies from the current question and the donor's transcript.
- **Saved outputs (no-hardcoding plan, section 2):** every T1 run writes the intact per-row dev predictions of all 6 splits to PREDS.json
  (`train.py --save-preds`) and its checkpoint.pt, and prints its trainable count against the sealed band (3,147,208 to 3,341,880; T1 3,277,393,
  64,487 below the top).
- **Replace, not alongside (Amendment 2):** T1 already removes the executor, the value codes and the result slots; the regex-found spans of the
  question's numbers stay in T1 (disclosed) and the N1 rung removes them.

## Addendum 18: U0, letters vs word pieces in the all-learned text baseline (written 2026-10-07 about 17:30 UTC, 1:30 PM ET, before any U0 run)
- **Source, mirrored as sealed:** `/mnt/project-files/no-hardcoding/INPUT-UNITS-2026-10-07.md`, U0. Report-first, 2 runs, BensPC, seeds 200 and 201
  against q33's plain_tf_steps on the same seeds (not retrained).
- **The one change:** `plain_tf_steps` with `bpe: 308`. The prompt is read as byte-level BPE ids (`custom_io/bpe.py`): the 95 printable ASCII
  characters are the base symbols with their char-vocab ids, merges are learned GPT-2 style on the 200,000 train prompts only (train.jsonl
  sha256 010af671...; GPT-2's pre-tokenizer pattern in ASCII form; ties broken by the pair's text), until 308 new tokens exist: 13 + 95 + 308
  = 416 ids. The merges are fixed in `custom_io/models/bpe_prompt.json` before any run. The 308 merged tokens get their own input table, created
  last, so every other weight starts identical to plain_tf_steps at the same seed; steps and answer stay letters and the tied readout stays the
  letter table. Size 3,339,776 (+2.94% over plain_tf, inside the band, 2,104 below the top).
- **Disclosed, from the merges (not a result):** at 308 merges a prompt token averages 2.31 letters (not the ~4 of large tokenizers), and digits
  stay almost one per token (only a leading space joins some single digits, " 1", " 2" ...). Prompts are about 2.3x shorter, so less compute per row.
- **Marks, as sealed:** "Ben right": pooled-5 (U0 - letters) >= +2.0 on both seeds. "Letters fine": <= +1.0 on both. Anything else: tie.
  Letters fine or tie: letters stay ("no evidence word pieces help at this size"). Ben right: the next gain test is a from-scratch word-piece side
  channel next to the letters in B2. Pre-registered prediction: letters fine; cipher_map falls by 10 or more; arithmetic families fall; frame and
  vocab move less than 2. Prediction proved wrong: cipher_map pooled over in_dist, answer and frame (120 rows, 2-seed mean, in rows) is at or
  above letters - 5 for word pieces (q33's plain_tf_steps ranges 45-112 of 120 across its 6 seeds, so this check is noisy).
- **Judge:** `python -m custom_io.analyze_gain --results custom_io/results/33-pc-confirm-b2 custom_io/results/41-pc-gain-u0`. pooled-5 is the
  intact score (as q33 reports plain_tf_steps); the calculator-on (C1') numbers are printed beside it, report only.

## Addendum 19: W1, global attention in the reader (written 2026-10-07 about 17:30 UTC, 1:30 PM ET, before any W1 run)
- **Source, mirrored as sealed:** `/mnt/project-files/architecture/redesign-ideas-2026-10-07.md` section 8 (revised 12:55 PM ET). One change on
  B2: `ledger` with `copy: true, gattn: 32`, one low-rank global self-attention block (one head, inner width 32; pre-LayerNorm residual, padding
  masked) after the +-4 conv window, before the reader's final LayerNorm, created last so every B2 weight starts identical at the same seed.
  Size 3,336,113 (+33,632; 5,767 below the band top). 2-seed screen (200, 201) against q33's B2 on BensPC, then a 6-seed confirm if it passes.
- **Marks, as sealed (2-seed means where stated):** pooled-5 W1 - B2 >= +1.0 on both seeds; cipher_map in_dist >= 95 (2-seed mean) and no other
  family down more than 2.0 (2-seed mean); no dev split (in_dist, answer, frame, vocab, variant) down more than 2.0 (2-seed mean); chain-5 >= 99.0
  on both seeds; loops:0 in_dist <= B2's on the same seed + 1.0 and donor in_dist <= 5. Proved wrong: pooled-5 mean below 0, or cipher_map in_dist
  (2-seed mean) down more than 2.0.
- **Reading fixed here (the source does not say):** a "family" is its rows pooled over the five pooled dev splits (about 120-200 rows), the
  least noisy reading.
- **Null check (shown, from q33, no mark changed):** with no change at all (one plain B2 seed standing in for W1 against another, 2-seed means over
  every ordered choice of 4 of the 6 q33 seeds, 360 cases), "no other family down more than 2.0" fails in 100% of cases (median worst family
  -6.6; -10.0 if read on in_dist alone), "no dev split down more than 2.0" fails in 22%, and the cipher_map proved-wrong line fires in 6.7%.
  So the family mark cannot pass as written. Sent to the architecture thread to re-seal before any W1 run; W1 is staged in its own queue and
  does not run until then. `analyze_gain` prints this null check with every W1 verdict.

## Addendum 19, amendment 1 (written 2026-10-07 about 17:50 UTC, 1:50 PM ET, before any W1 run)
- **Family mark re-sealed by the architecture thread (redesign-ideas-2026-10-07.md section 8a, 1:45 PM ET), mirrored here:** the line "no other
  family down more than 2.0" and this addendum's "family" reading for it are deleted.
  - **F1.** cipher_map, fewshot_number_rule, group_induct and seq_cycle pooled as one number on in_dist (rows summed); 2-seed mean of W1 minus plain
    B2 not down more than 2.0. cipher_map alone must still be >= 95 (2-seed mean).
  - **F2.** `analyze_gain` prints F1's no-change failure rate on the same 360 draws with every W1 verdict. Above 25%, F1 is reported, not judged,
    and only the cipher_map >= 95 line and the split mark apply.
  - **F3.** Every other family's change (rows pooled over the five pooled splits) is reported beside its no-change 5th-95th percentile, never judged.
  - Everything else in addendum 19 is unchanged: pooled-5 >= +1.0 on both seeds, the split mark, chain-5 >= 99.0, the leak lines, proved wrong.
- **F2 computed now on q33 (shown):** F1 fails in 22.2% of the 360 no-change draws (q33 B2 in_dist on the four families: 81.25, 83.75, 80.62,
  81.25, 77.5, 78.75), at the 25% limit's safe side, so F1 is judged. W1 may queue (42-pc-gain-w1.txt) after U0.

## Addendum 20: C0, a fair LLM-recipe baseline (written 2026-10-07 about 18:00 UTC, 2:00 PM ET, before any C0 run)
- **Source, mirrored as sealed:** `/mnt/project-files/no-hardcoding/PLAN-AND-MARKS-2026-10-07.md` section 3.1 (added after D0b). One change on
  plain_tf_steps: the steps-plus-answer cap goes from 64 chars to the longest step-family target on train, **107 chars** (measured on the 200,000
  train rows: 54,095 step rows, median 20, 99th percentile 71; at 64, 840 var_chain rows were trained answer-only, at 107 none are). Generation
  gets 119 new chars and the position table 288 -> 329 rows (the plan's "e.g. 400" was an upper estimate). `cap` is a cfg flag of
  plain_tf_steps, so any depth can use it (for example a 13-layer PT: `{"cap":107,"n_layers":13}`). Every other weight starts identical to
  plain_tf_steps at the same seed. Size 3,271,424 (+10,496; inside the band). Seeds 200 and 201 on BensPC against q33's plain_tf_steps.
- **Reported:** pooled-5 and chain-5 with and without the C1' calculator, and B2 - C0 per seed (q33's B2).
- **Prediction, as sealed:** C0 with the calculator reaches chain-5 >= 98.5 on both seeds. Proved wrong: below 97.5 on both. Between: not shown.
- **Consequence, as sealed:** if C0's pooled-5 2-seed mean is at or above plain_tf_steps', C0 replaces plain_tf_steps everywhere it is the
  yardstick (B3 mark 2, U0's base model, the LLM-recipe arm of the growth ladder). If B2 - C0 (2-seed mean) is more than 3.0 below today's +6.9,
  the "+6.9 over the LLM recipe" claim is withdrawn until a 6-seed C0 confirm restates it.
- **Judge:** `python -m custom_io.analyze_gain --results custom_io/results/33-pc-confirm-b2 custom_io/results/43-pc-c0`. Queue `43-pc-c0.txt`.
- **Note on U0:** U0 (addendum 18) is already staged on plain_tf_steps at the 64-char cap; it is a prompt-side change, so the cap is the same on
  both of its arms. If C0 replaces plain_tf_steps, U0's verdict stands as measured and any later word-piece test uses C0.

## Addendum 21: H1, the model picks how many thinking rounds a turn gets (written 2026-10-07 about 19:20 UTC, 3:20 PM ET, before any H1 run)
- **Source, mirrored as sealed:** `/mnt/project-files/architecture/redesign-ideas-2026-10-07.md` section 8b (sealed 2:55 PM ET). Required for
  B3 by Ben's rule 0 (the deployed model decides how long to think). A rung on T1: queue 49 runs only after the T1 screen (queue 40) and only if
  analyze_t1 does not say PROVED WRONG. Seeds 200 and 201 on BensPC, each against T1 on the same seed. Model `tool_h1`, cfg `{}`, 3,277,650
  params (T1 + 257, inside the band).
- **Build, as disclosed in `custom_io/models/tool_h1.py`:**
  - A turn = answering one question; rounds = T1's controller iterations. Rounds 1..7 write T1's calls exactly as in T1; rounds 8..32 only
    think (T1's tape holds 7 entries; K1 lifts that later). The round embedding stays at T1's last one after round 8, as T1's loops:K does.
  - Per-round readout: after every round the answer heads (mode, word pointer, GEN with the copy path over the prompt and the entries written
    so far) read the state with T1's normal losses; each row's mean over its rounds t >= L (L = gold calls, so its calls are on the tape) is the
    answer loss, weight 1.0. The call heads keep T1's rounds and losses.
  - Stop head: Linear(256, 1) on ln_z(control 1), input detached (the stop loss cannot move the loop; tested). Label = the model's own greedy
    readout after that round equals the target answer (teacher-forced tape, the model's own heads). BCE over every trained round.
  - Run rule: stop after the first round with sigmoid >= 0.5, at least 1 round, cap 32. Rows in a batch are independent; the batch runs until
    every row has stopped and each row keeps its own stop round's state, tape and calls (tested against forced runs of the same length).
  - Training rounds: K drawn per batch from {4, 8, 16, 32}; the batch runs n = max(K, longest gold program + 1) rounds, so every row's program
    and answer are trained in every batch as in T1 (K = 4 then mostly runs 8). Measured on CPU: about 1.9x T1's step time on average; saved
    activations about 1.0x T1's (rounds 9..32 and the per-round heads are gradient-checkpointed; same values).
  - loops:K = exactly K rounds with the stop ignored; K = 8 reproduces T1 exactly (tested on lesions and outputs). final_eval's loop sweep for
    H1 is loops:{0, 1, 2, 8, 16, 32} (loops:32 gives H-a).
- **Marks (screen, both seeds against T1 on the same seed), as sealed:**
  - H-a stability: pooled-5 at loops:32 minus pooled-5 at the model's own stop >= -0.3 on both seeds.
  - H-b parity: pooled-5 H1 - T1 >= -1.0 on both seeds; chain-5 >= 99.0 on both; no dev split's 2-seed mean of H1 - T1 below -2.0 (the six
    dev splits; this split line fails 22% of the time with no change in the q33 null check).
  - H-c adaptive: mean rounds on chain-5 turns minus the mean on one-step turns (arith_bare, div_exact, story_addsub), both on the big build's
    in_dist, >= 2.0 on both seeds. Proved wrong on this line: the 2-seed mean gap within 0.5 of zero.
  - H-d cap: pooled-5 turns that reach 32 rounds <= 1%, and their median rounds < 16, on both seeds.
  - H-e leaks: loops:0 and donor in_dist <= 5 on both seeds, T1's and B2's values printed beside.
  - H-f audit: the result records p_stop 0.5 and cap 32; `generate()` has no other threshold (code: P_STOP and CAP are the only ones).
  - Pass = H-a to H-f. Proved wrong: pooled-5 H1 - T1 2-seed mean < -2.0, or H-c's line, or H-a < -1.0 on either seed. Between: not shown.
- **Reported, not judged:** rounds per split and family, by gold program length, for right vs wrong turns; pooled-5 at loops:8 and loops:16;
  per-row rounds for the pooled-5 and big in_dist rows (`extra.h1.rows`); the training stop-label rate.
- **Risk, flagged before the run (suggested, not shown):** the sealed label "already right" never fires on a turn the model cannot get right,
  so a calibrated stop head keeps thinking to the cap on those turns. In q33's plain B2, 25% of pooled-5 rows sit in split-family cells below
  50% (mostly the variant split), so H-d's 1% cap line may fail for that reason alone. An alternative label is built and tested but NOT sealed:
  cfg `{"label": "settled"}` (right now, or no later round of the turn is right), which gives up early on turns more rounds will not fix. The
  architecture thread chooses before the run; the queue uses the sealed label.
- **Judge:** `python -m custom_io.analyze_h1 --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-pc-t1-screen custom_io/results/49-pc-h1-screen`.
  Queue `49-pc-h1-screen.txt` (45-48 are the 8a queues).

## Addendum 21, amendment 1 (written 2026-10-07 about 19:35 UTC, 3:35 PM ET, before any H1 run)
- **Source, mirrored as sealed:** spec section 8c ("H1 amendment 1", 3:30 PM ET), the architecture thread's ruling on the label question above.
- **Change:** the H1 screen uses the stop label `settled` (right now, or no later round of this turn is right); queue 49's cfg is now
  `{"label":"settled"}` and the judge accepts only that cfg (H-f also checks the recorded label). Marks H-a to H-f are unchanged, H-d stays 1%.
- **Reported, not judged (new):** (i) pooled-5 rounds on turns right vs wrong at the end; (ii) the stops that fired with the turn already
  right vs settled as wrong vs reaching the cap; (iii) rounds, cap share and accuracy on the pooled-5 split x family cells where q33's B2 of the
  same seed is below 50%, vs the other cells (`extra.h1.split_family`, combined by `analyze_h1.py`).
- **Named risk, as sealed:** early in training every round is wrong, so "settled" labels "stop at round 1" everywhere and may bias the head to stop
  early; H-c and H-a catch a collapse (proved wrong on those lines). The named next change then is a disclosed warm-up before the stop loss.

## Addendum 22: T1S, T1 + span copy, the one link fix (written 2026-10-07 about 21:45 UTC, 5:45 PM ET, before any T1S run)
- **Source, mirrored as sealed:** /mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md Amendment 3 (the architecture thread, about
  5:25 PM ET), after the T1 screen was NOT SHOWN (S3 write_copy 29-42%: exact copy 85-98% at 1-3 digits, 14% / 59% at 4, about 0 at 5+).
- **The change (one, nothing else):** model 'tool' with cfg `{"span_copy": true}` (custom_io/models/tool.py; 3,311,060 params, +2.2% vs
  3.24M, inside the +-3% band). Each writer (both call operands, and the answer) can copy a whole number already in the context: a pointer
  picks one char, the copy advances by itself one char at a time, and a learned stop head ends it. No code gives it a length. T1's cells and
  GEN registers stay, with their losses unchanged, for numbers the writer composes itself. Plain T1 (no cfg) is bit-identical to before
  (tested on the T1_s200 checkpoint: same answers, calls and losses under four lesions).
- **Disclosed details (build thread's choices inside the sealed fix):**
  - Direction: T1's writers write units first, so the pointer picks the number's units digit and the copy runs toward its front (the writers'
    own order). "Start" and "forward" in Amendment 3 are read in that order.
  - Stop head: one logit per source (prompt text vs calculator entry) on the char about to be copied, read from the char table (detached,
    parameter-free layer norm). It ends the copy before that char; the copy also ends at the edge of its string (nothing is there). Ceiling
    40 chars (an entry's length), never reached by a number.
  - Gate: per operand, span (sigmoid >= 0.5) or T1's cells. The answer: mode 0 (B2's NUM slot, which T1 did not use) = copy the span the
    answer pointer picks, over the current prompt and the state's tape. A span answer has no 8-char register limit, so write_copy's answer
    copy now counts 9-digit strings too (T1's excluded them as too long).
  - Training labels (targets only, never inputs): number tokens are the prompt-number regex (digit runs, as Amendment 2 already discloses)
    on the prompt and signed digit runs on the entries; the gate is span iff the gold string is a number token of the visible context;
    the pointer loss marginalises over every visible occurrence; NUM rows whose answer is such a token get mode 0 (and keep T1's GEN targets).
- **Marks:** R1-R4 and the proved-wrong line exactly as Amendment 3 (judge below). Pass: the 6-seed confirm with marks 1-6 as amended
  (Amendment 2), then H1 on these checkpoints.
- **Run:** seeds 200 and 201, the queue 40 recipe (24k steps, batch 256, lr 1e-3, bf16, q33's data file 010af671), on the two rented RTX 5090s
  that ran T1. Queue `50-pc-t1s-screen.txt`, box jobs custom_io/queue/t1a|t1b/50-t1s-*.sh.
- **Judge:** `python -m custom_io.analyze_t1s --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-vast-t1 custom_io/results/50-vast-t1s`.

## Addendum 22, amendment 1 (written 2026-10-07 about 22:30 UTC, 6:30 PM ET, before any T1S result is read)
- **Source, mirrored as sealed:** MARKS-D0-T1-2026-10-07.md Amendment 4 (6:10 PM ET; the idea swarm's finding via the coordinator), copied into
  the repo as custom_io/design/MARKS-D0-T1-2026-10-07.md.
- **Step 1, the disclosure check (data only, done):** custom_io/results/WC-LABELS.md (`python -m custom_io.diag_wc_labels`). On the big
  build's in_dist (2,793 program rows), of the gold operands write_copy's text rule called copies, a prompt number or constant also holds the
  value for 213 of 388 at 1 digit (55%), 671 of 2,145 at 2 (31%), 233 of 473 at 3 (49%), 0 of 31 at 4 and 0 of 11 at 5. The new rule's
  unambiguous set agrees with the gold slots in every case.
- **Scorer (Tool.write_copy_u, custom_io/rescore_wc.py):** the same rows, oracle and copy events as write_copy; an operand counts only if its
  intact-run text equals exactly one earlier result and no prompt number or constant (an answer: exactly one call result, no prompt number
  or constant); the rest are reported apart. Pass 0 is write_copy's own random draw; while any unambiguous length 1-9 cell (operand or
  answer) has n < 200, another pass re-draws every random string on the same rows (seed + "|pass"), at most 8 passes. The rule reads only
  texts and n, never whether the model was right.
- **Where it runs:** on the two boxes, same dev file, eval batch 128 and bf16 as the final eval: T1's queue 40 checkpoints first (jobs 51,
  started before any T1S result exists), then T1S's checkpoints once each run has finished (jobs 52). Judge:
  `python -m custom_io.analyze_t1s --results ...33 ...40-vast-t1 ...50-vast-t1s --wc ...51-vast-wc-t1 ...52-vast-wc-t1s`; R1, R3 and the
  proved-wrong line read the unambiguous cells; a cell with n < 200 is reported and cannot pass or fail by itself; the old numbers are printed
  beside. Marks unchanged.

## Addendum 22, amendment 2 (written 2026-10-07 about 22:55 UTC, 6:55 PM ET, before any T1S result is read)
- **Source, mirrored as sealed:** MARKS-D0-T1-2026-10-07.md Amendment 5 (6:50 PM ET), after this thread named the CPU proxy's answer-selection
  risk. Pass unchanged (R1: operand AND answer >= 99 at every length 1-9, unambiguous set, both seeds).
- **Proved wrong is read by path:** an operand cell at 4-9 digits below 90 on either seed = span copy proved wrong (both paths below 90 too).
  Operands all >= 90 but an answer cell at 4-9 below 90 = "NOT SHOWN: answer selection", never reported as span copy failing. Cells 90-99 = not
  shown, one more change named from the per-length table.
- **The single next change, named now, if answer selection is the case:** a learned entry-index signal on the span pointer's keys (which
  string, prompt or entry k, a char belongs to; from the text layout, as entry spans are; no rule picks the last result). Same recipe,
  re-screen seeds 200/201, R1-R4 unchanged. `analyze_t1s.py` prints these verdicts.
