# Thinker-first split: make the thinker the big part (2026-10-05)

Ask (Ben, 6:19 PM ET 10-05): today a huge model reads, a thinker about 100 times smaller thinks, and the same huge
model talks. How do we make the thinker most of the model, with the reader and talker as small parts that only read
and talk?

Labels: **shown** = measured in this repo or counted from a config, **suggested** = reasoned from results or papers,
**untested** = a guess. Times are US Eastern (ET).

## 1. Where the weight and the work sit today

| part | what it is | weights | share |
|---|---|---|---|
| hearer (reader) | frozen LFM2.5-1.2B-Instruct, all 16 layers, last hidden state | 1,170,340,608 | ~99% |
| door + thinker | reader 2048 -> 32 -> 256, ~9M looped core (4 rounds) | ~9M (about 1.6M live: the MoE router never learns) | <1% |
| talker | the same frozen LFM2.5-1.2B, run again over prefix + every question word + answer | (same weights) | |

- Shown (HF safetensors metadata): LFM2.5-1.2B-Instruct has 1,170,340,608 weights: a 134,217,728 tied word table
  and 16 layers (10 conv layers of 67,119,104, 6 attention layers of 60,821,632; counted from `config.json`, and the
  sum matches the total exactly).
- Suggested (estimate): per question word the big model runs 32 layer passes (16 to read, 16 to talk, because the talker
  re-reads every question word). The thinker does about 1-2% of the work.

### Why the big model is the real thinker today (shown)
- Copy-talker test (PR #37, `reasoner_ptr/real/english/RESULTS-CT.md`): feeding the LM talker another question's
  thinker states still scored 73.2% on unseen kinds, the same as the right states (73.2%); 334 of 384 answers did
  not change. On new kinds the 1.2B answers by re-reading the question.
- Without the question words the talker drops from 82.9% to 18.9% (R7, PR #30, `RESULTS-R7.md`). Speed: first answer
  token is 2.97x the bare LM, mostly from the second full LM pass.
- A 350M LFM as hearer and talker: 66.1% vs 92.6% (PR #36). The trained parts add about the same on top of either LM
  (+16 to +18 over its own 8-shot score), so the borrowed LM's skill sets the level.
- Growing the core: +1.9 only (fair scaling, PR #18).
- Ultracode lesions (PR #38): with LM-written steps the LM does the thinking and the core is a family switch; the
  plan route (thinker plans, exact calculator computes) is the one place the thinker decides every answer
  (plan_swap lesion -> chain 2-3 of 160).

So shrinking the reader and talker fails while they are also the thinker. The knowledge has to move into the thinker.

## 2. The shape we want already exists inside the big model (suggested, from papers)
- Lad, Gurnee, Tegmark (arXiv 2406.19384, NeurIPS 2025): across 8 model families, early layers turn tokens into
  ideas ("detokenization"), middle layers refine features, late layers turn ideas back into the next word. Deleting or
  swapping a middle layer keeps 72-95% of accuracy with no training; the first and last layers are fragile.
- Huginn-3.5B (Geiping et al. 2025, arXiv 2502.05171): 2 prelude layers, a 4-layer block looped up to 32 times,
  2 coda layers. That is Ben's picture: small reader, big looped thinker, small talker.
- Retrofitted recurrence (McLeish et al., arXiv 2511.07384): turned pretrained TinyLlama-1.1B, OLMo-2-1B and
  Llama-3.2-1B into prelude / looped block / coda, e.g. (4,6,4) for 16-layer Llama, and beat the plain post-trained
  model on GSM8K at equal training compute (TinyLlama 51.2 vs 46.2). They used about 52B tokens of training.
- Ouro (arXiv 2510.25741): looped 1.4B models, trained from scratch on 7.7T tokens, match 4B models.
- Caution: a probe of Huginn (arXiv 2507.02199) found little sign of step-by-step thinking inside the loop and only
  small gains from more loops on arithmetic. That matches our own finding that exact step values beat latent ones, so
  the looped thinker should keep the plan + exact calculator route.

## 3. Ways to get there

| | way | thinker share | keeps English | nothing pretrained | cost on our machines |
|---|---|---|---|---|---|
| A | **Cut the big model open** (recommended): reader = word table + first 2 layers, thinker = middle 12 layers looped, talker = last 2 layers. One pass; the talker only sees what came through the thinker. | 66% of weights, 86% of work at 2 loops | yes | no (for now) | 1.2B with 774M trained: suggested to fit the 5070 Ti with 8-bit Adam and checkpointing (untested) |
| B | **Teacher, then goodbye** (distill): train a thinker-heavy student with the big model as teacher, ship the student alone. | any we pick | if the distillation works | yes for the shipped model | large: many millions of teacher answers |
| C | **Build from scratch** (custom reader/talker thread owns it, PR #39): B2 at 3.3M beats a same-size transformer 73.7 vs 67.7 (2 seeds). | any we pick | must learn English from scratch | yes | fine at 3-100M; a 1B model from scratch is suggested at roughly a month of the PC non-stop (20B words), and still far short of the trillions LFM saw |
| D | Grow the tiny core inside today's sandwich | could reach a few % | yes | no | not recommended: +1.9 only, and the talker still re-reads the question |

Weights for A, counted from the config (shown): reader 268,455,936 (22.9%: word table 134.2M + 2 conv layers),
thinker 773,941,888 (66.1%: layers 2-13), talker 127,942,784 (10.9%: layers 14-15; it reuses the tied word table to
pick words). Work share at 2 loops: 24 of 28 layer passes per word (86%); at 3 loops 36 of 40 (90%). Today: 32
big-layer passes per question word.

### Recommendation
A first, then shrink, then C for the long run:
1. Map the big model (Test 1, no training) to find where reading ends and talking starts.
2. Cut it open and loop the middle (Test 2). Same total size as today, about half the reading work, and the thinker
   is 2/3 of the weights.
3. One change at a time after that: put the plan + calculator route inside the looped thinker; then cut open the
   350M LFM and try to match today's 1.2B model at a third of the size.
4. Long run (nothing pretrained): use the proven shape and the cut-open model as a teacher for the from-scratch line
   (way B into C). The custom reader/talker thread owns C.

## 4. Test 1: map the big model (no training; forward passes only)
Owner: a Sonnet implementation thread; machine per the compute rule (own machines first; this fits the M1 Pro).

- Model: `LiquidAI/LFM2.5-1.2B-Instruct`, revision `0f604ada3f766f9f257460c4c9f0b5d6f69d431b`, bf16, frozen.
- Questions: the round-6 bare 8-shot setup (`lm_fewshot` in `reasoner_ptr/real/english/run_english.py`, branch
  `claude/project-thread-utxkpw`) on FRESH-EN-R3 (192), NEW-KINDS-R5 (192) and NEW-KINDS2-R6 (192) = 576 questions.
  Bare 8-shot today: 75.0 / 67.7 / 77.6.
- Variants (33): the full model; **skip layer i** for i = 0..15 (a forward hook returns the layer's input unchanged);
  **repeat layer i** for i = 0..15 (run the layer twice in a row).
- Score: exact match, same scorer as round 6. If greedy generation is too slow, teacher-forced exact match on the gold
  answer for every variant (say which).

Marks, fixed now (F = full-model pooled exact; drop_i = F - skip_i):
- A layer is **critical** if drop_i >= 20 points.
- Reader = layers 0..k, k = the last critical layer among 0-5 (k = 0 if none). Talker = layers m..15, m = the first
  critical layer among 10-15 (m = 15 if none). Thinker = layers k+1 .. m-1.
- **GO** for Test 2: the thinker gets >= 10 layers.
- **KILL** for way A: the thinker gets < 8 layers. Switch the recommendation to way B.
- 8 or 9 layers: GO, with the smaller share stated.
- Loop readiness (read for Test 2's setup): mean drop when repeating a thinker layer <= 5 points -> start looping
  with a short heal; > 15 points -> heal first, as the retrofit paper did.
- Prediction written before running (untested): reader 1-2 layers, talker 1-2 layers, mean middle skip drop < 10.

## 5. Test 2: cut-open screen (2 seeds, then 6 to confirm)
Runs only after Test 1 says GO. Cut points come from Test 1 (default (2,12,2)).

- Data and budget: exactly round 6's `six` arm: allptr generator, 8000 generated examples, 2000 updates of 16 rows,
  `--kinds 6 --block-r6`, same seeds. Eval: FRESH-EN-R3, NEW-KINDS-R5, NEW-KINDS2-R6, GEN-HELDOUT-R4.
- **CO (cut-open):** reader and talker layers frozen; thinker layers trained (full weights, bf16, 8-bit AdamW,
  lr 1e-5 cosine, gradient checkpointing; LoRA only if memory forces it, and say so). Each round joins the reader's
  output to the thinker state with a learned adapter (input injection, as in the retrofit paper). Training samples
  loops from {1,2,3}; scored at 2 loops (main), also 1, 3 and 4. One pass: the talker sees only what came through the
  thinker. No prefix vectors, no second read of the question.
- **CO-0 lesion:** same checkpoints, thinker replaced by identity (0 loops).
- **FT control (same size, normal shape):** the same layers trained the same way, no loop and no adapter.
- Today (reference, not re-run): round 6 `six`: FRESH-EN-R3 92.2, NEW-KINDS-R5 81.1, NEW-KINDS2-R6 75.3
  (unseen pooled 78.2).

Marks, fixed now (screen means over 2 seeds; the confirm repeats them on 6):
- M1 practised kinds: CO FRESH-EN-R3 >= 89.0 (today - 3).
- M2 new kinds: CO unseen pooled (R5 + R6, 384) >= 75.0 (today - 3).
- M3 the thinker decides: CO-0 <= 10% on FRESH-EN-R3 and on unseen pooled.
- M4 cost: CO at 2 loops, time to first answer token at batch 1 <= 2.0x the bare LM on the same GPU (today 2.97x,
  R7). Suggested: 28 layer passes in one pass is about 1.75x bare.
- M5 loops help (confirm only): CO at 3 loops minus FT >= +2 points on unseen pooled, ahead on >= 5 of 6 seeds.
- **GO** = M1-M4 met on the screen -> 6-seed confirm. **Proved wrong** = CO below 86.0 on FRESH-EN-R3 or below 72.0
  unseen pooled on both seeds: a 2-layer talker cannot replace the re-reading LM. Next single change then: a 4-layer
  talker; if that also fails, way B.

## 6. Ben's objection (7:11 PM ET) and Plan B's first test

Ben: "is this getting rid of the thinker model we already have and replacing it with a looped 1.2B thinker?" Yes.
Way A retires the 9M core as its own network; only its ideas (the loop, plan + exact calculator) move into the LM's
middle layers. That makes the model more borrowed, against the nothing-pretrained goal. Test 1 is on hold; Ben is
choosing between A and B on a decision card (B recommended).

Way B keeps our own thinker: the 1.2B is only a teacher during training and never ships.
- The B2 design already has the wanted shape. Estimated from `custom_io/models/ledger.py` (S size, d=256): the 2 core
  blocks are about 2.3M of 3.3M weights (~70%), the character reader about 0.7M, the talker heads a few percent
  (suggested; count with `n_params` per module before quoting it as shown).
- What B2 lacks is breadth: every from-scratch model there scores 0-4% on held-out families, and the copy talker
  (fed by the 1.2B reader) got 13.6% on new English kinds. The custom report's own reading is that new kinds need
  task variety. The teacher's job is to supply that variety, which a hand-written generator cannot.
- Prior art (suggested): TinyStories (Eldan and Li 2023) trained models under 10M weights to write fluent simple
  English from LLM-written simple text. Our eval sets are one-sentence passages with short questions, close to that
  register.

### Test B1: teacher-made variety for a thinker-heavy model (untested; 2 seeds, then 6)
Owner suggestion: the custom reader/talker thread runs the student side (it owns B2); a Sonnet thread builds the
teacher data. Own machines first.

- **Teacher data (TEACH):** LFM2.5-1.2B-Instruct writes simple one-sentence passages, a paraphrase, and questions in
  60 question kinds (list fixed before generation; none of the 12 R5/R6 test kinds; every R5/R6 name and answer word
  blocked, as `--block-r6` does). It answers each question from the passage and again from the paraphrase; a row is
  kept only when both answers match exactly and the answer appears in the passage. 200,000 kept rows.
- **Control data (GEN):** 200,000 rows from round 6's generator (`gen_english.py`, the six practised kinds,
  `--block-r6`). The one change between arms is where the practice comes from.
- **Students (same recipe, same updates):** B2 at M size (10.8M) on TEACH, B2 on GEN, and `plain_tf` of the same size
  on TEACH (the shape control).
- **Scores:** FRESH-EN-R3 (practised kinds, human wording) and NEW-KINDS-R5 + NEW-KINDS2-R6 pooled (384, kinds never
  practised by either arm). Lesions: donor state and thinker loops = 0.

Marks, fixed now (means over the 2 screen seeds; the confirm repeats them on 6):
- **B1-a, variety helps new kinds:** B2-TEACH minus B2-GEN on new kinds pooled >= +15 points, ahead on both seeds.
  **Proved wrong:** < +5.
- **B1-b, the thinker decides:** B2-TEACH with a donor's state <= 10% on new kinds pooled.
- **B1-c, the shape matters:** B2-TEACH minus plain_tf-TEACH >= +3 on new kinds pooled, ahead on both seeds.
- Read, not judged: distance to the bare 1.2B 8-shot (75.0 practised; 67.7 and 77.6 on the new-kind sets) and to
  today's sandwich (92.2; 78.2 pooled).
- If B1-a is proved wrong, way B at this size is dead: the next single change is a larger student (about 100M), and
  if that also fails, way A.

### B1 data spec, fixed before generation (Ben chose Plan B on the card, 7:44 PM ET)
Test 1 (the layer map, way A) is cancelled.

TEACH covers 60 kinds: the 6 practised round-4 kinds (so both arms practised what FRESH-EN-R3 tests) plus these 54.
Each kind is a one-sentence passage, a paraphrase, one short-answer question and one yes/no question, in the
format of `FRESH-EN-R3.json`. Example questions are shown in brackets.

1 owner_possession (Whose kite is red?) · 2 agent_action (What did Tev do?) · 3 companion_with (Who did Tev go with?) ·
4 feeling_state (How did Tev feel?) · 5 naming (What is the dog's name?) · 6 family_relation (Who is Tev's sister?) ·
7 occupation (What is Tev's job?) · 8 part_whole (Which part of the bike broke?) · 9 goal_want (What did Tev want?) ·
10 object_eaten (What did Tev eat?) · 11 object_made (What did Tev bake?) · 12 object_read (What did Tev read?) ·
13 container_contents (What was in the box?) · 14 category_member (Is the robin a bird?) · 15 ability (Can Tev swim?) ·
16 rule_must (What must Tev do?) · 17 like_best (What does Tev like best?) · 18 dislike (What does Tev dislike?) ·
19 plan_next (What will Tev do next?) · 20 habit (What does Tev do every day?) · 21 if_then (What happens if the bell
rings?) · 22 team_member (Which team is Tev on?) · 23 helper (Who helped Tev?) · 24 patient_target (Who did the dog
chase?) · 25 winner (Who won the race?) · 26 loser (Who lost the game?) · 27 learned (What did Tev learn?) ·
28 topic_about (What was the book about?) · 29 creator (Who painted the picture?) · 30 language_spoken (What language
does Tev speak?) · 31 hobby (What is Tev's hobby?) · 32 title_role (Who is the captain?) · 33 best_friend (Who is Tev's
best friend?) · 34 lost_item (What did Tev lose?) · 35 found_item (What did Tev find?) · 36 choice_pick (Did Tev pick tea
or milk?) · 37 fact_yes_no (Did Tev lock the door?) · 38 forgot (What did Tev forget?) · 39 permission (Who let Tev
in?) · 40 game_played (What game did they play?) · 41 clothing (What did Tev wear?) · 42 replacement (What replaced the
old clock?) · 43 visitor (Who visited Tev?) · 44 joiner (Who joined the club?) · 45 search_for (What was Tev looking
for?) · 46 fear (What is Tev afraid of?) · 47 wish (What does Tev wish for?) · 48 pronoun_reference (In "Tev called Pim
because she was late", who was late?) · 49 teacher_of (Who taught Tev?) · 50 neighbor (Who is Tev's neighbor?) ·
51 named_after (Who was the dog named after?) · 52 caretaker (Who feeds the cat?) · 53 opponent (Who did Tev play
against?) · 54 role_in_play (Who played the king?)

Overlap guard against the 12 held-out kinds, checked by script on every kept row (any hit drops the row):
- Question words: how many, how much, where, why, when, what time, which way, how long, come from, use to, used for,
  what for, cost, price, pay, said, say, tell, told, asked.
- Weather words in passage or question: rain, snow, sun, sunny, wind, windy, cloud, cloudy, storm, fog, hot, cold.
- Attribute questions about colour, size, shape or material ("what colour", "how big", "made of").
- Every name and answer word in NEW-KINDS-R5 and NEW-KINDS2-R6 (the `--block-r6` list).
- Report the drop count per kind. A kind that loses more than half its rows is replaced from a spare list fixed
  in the same commit as the generator, before any student trains.

Teacher prompts: one fixed prompt per kind with 2 hand-written examples, temperature 0.9 to write and greedy to
answer. The prompts and generator are committed before the first student run. The question writer and the answerer
are both the 1.2B; nothing else writes training rows.

### B1 addendum, 2026-10-06 5:15 PM ET, after the data was built and before any student trains
Data actually built (PR #46, `/mnt/project-files/plan-b/data/MANIFEST.json`, read here):
- TEACH `teach.jsonl`: 171,940 questions (148,694 passages) over all 60 kinds, no spares used. That's short of
  200,000; Ben said at 3:11 PM ET to use this data with no new teacher run.
- Answer types differ in the full set. `teach.jsonl` is 51% yes/no (87,807 of 171,940), while round 6's generator is about
  11%. The eval sets are about 12% yes/no (FRESH 11 of 96, R5 12 of 96, R6 10 of 96). Extra yes/no practice alone could
  move new-kind scores by up to about 6 points.
- **The student arms use the type-matched pair** that the custom reader/talker thread fixed in `custom_io/PASS-MARKS.md`
  addendum 3, before any student trained: TEACH = `teach_clean.jsonl` (94,831: every short answer plus 5,349 yes and
  5,349 no, after a yes/no support filter) and GEN = `gen_matched_94831.jsonl` (94,831 from round 6's generator: 84,456
  short, 3,454 yes, 6,921 no). Both arms have the same size and nearly the same type mix (yes/no 11.3% vs 10.9%; counted
  here), and unsupported yes/no items are gone from TEACH. That fixes the confound
  better than a 171,940-row match would, so `teach.jsonl` and `gen_matched_171940.jsonl` are not used for B1. A request
  from this thread at 5:15 PM ET to switch to them was withdrawn at 5:20 PM ET.

Extra guard, fixed now (it only tightens B1-a): B1-a is also scored on short-answer questions alone. If B1-a passes
overall but the short-answer-only gap (TEACH minus GEN) is below +10, the verdict is NOT SHOWN, not PASS. Report
per-kind and per-type scores for both arms.

Nothing here touches GOLD-PRIVATE, reserved or blind panels.

## 7. Test B1 result (2026-10-07, 2 seeds) and the recommended next step

Source: `custom_io/results/RESULTS-B1.md` at e10ea0232 on `claude/custom-reader-talker-4x309r` (queue 35, BensPC 5070 Ti,
seeds 300-301, marks from `custom_io/PASS-MARKS.md` addendum 3). All numbers below are shown, read from that file.

| | b2t (B2-M, TEACH) | b2g (B2-M, GEN) | tft (plain_tf-M, TEACH) |
|---|---|---|---|
| New kinds pooled (384) | 11.20 | 10.42 | 13.93 |
| short-answer rows only (340) | 7.65 | 7.50 | 8.53 |
| FRESH-EN-R3 (practised kinds, human wording) | 22.92 | 48.96 | 17.71 |
| Held-out rows from its own training mix | 91.19 | 96.47 | 92.19 |

- **B1-a: PROVED WRONG.** b2t - b2g = +0.78 (seeds -0.52, +2.08); the line was +5. Short-answer-only +0.15.
- **B1-c: FAIL.** b2t - tft = -2.73.
- **B1-b: uninformative.** b2t's intact new-kinds score (11.2) is too low for a donor test to mean anything.
- Every student fits its own training mix (91-96% on held-out rows of it; b2t's final training loss 0.012) and gets about
  11% on new kinds, whichever data or shape. Even b2g, at 96% on its generator's own held-out rows, drops to 49% on the
  same 6 kinds in human wording.

Reading (suggested, not tested): the students learn the wording of their practice, not English. Each arm had 187,667
training rows seen about 22 times (16,000 updates x 256). The teacher's 60 kinds did not change that; 94,831 short
one-sentence questions are far too little English for any reader to learn from. The roadmap's own rule (no row seen
more than 4 times; about 20 word pieces per trained number) says all our question data together (about 12M word pieces)
supports only about 2M trained numbers, and this arm had much less than that.

**Next step: do not run the ~100M student on this data.** Section 6 pre-wrote "a larger student (about 100M), then way
A". Way A was rejected by Ben (7:44 PM ET 10-05), and a 100M student on the same 94,831 rows would have about 10 times
more weights for the same words, so it would most likely memorise faster, not read better (suggested). Rough cost
(estimate, not measured): about a day of the PC for 3 arms x 2 seeds after queue 39 finishes, with memory work to fit
16 GB; Vast credit is $5.22 (read 4:10 AM ET 10-07), too little above the $1 floor for it.

Recommended instead (it changes nothing that is staged): Plan B continues as the whole-model roadmap's stage 8a (the
bigger-is-better check: our thinker at about 3M, 10M and 30M, with plain human-written web text added, which Ben
approved at 8:57 PM ET 10-06). It already scores B1's 12 new kinds. Suggested for 8a's owner to seal: report b2t
(11.20 new kinds pooled, 10.9M) as the same-size, TEACH-only baseline for the 10M rung. The ~100M student is the
roadmap's 8c and waits for 8a to pass. The 1.2B teacher's data stays usable as one part of the 8b pool; it is not a
reason to run a new teacher (Ben, 3:11 PM ET 10-06).

**Decided (Ben tapped "Wait for web text", 9:32 AM ET 10-07):** no ~100M student on the B1 data. Plan B's next result
comes from stage 8a's 10M rung, read against b2t.

Nothing here touches GOLD-PRIVATE, reserved or blind panels.
