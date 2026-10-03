# Curriculum and interfaces: skills first, facts later, few-shot after (design only)

Angle: the training curriculum and the two interfaces (reader in, prefix out). Nothing was trained or run. Labels: **shown** = I read it in this repo's code/artifacts or in the brief's measured numbers; **suggested** = reasoning or literature (papers named from memory, not re-opened today); **untested** = my guess. The calculator panel numbers (128 fresh, 32 practice) come from the brief; their code and outputs are on Ben's Mac and I could not read them. Nothing here uses numbers from the small card experiments or the village model.

## 0. What the code actually does at the two interfaces (checked)

- **Reader is not contextual.** `scripts/sol_translator_grounding_v6.py:183-186` feeds `lm.get_input_embeddings()(ids)`, i.e. the LM's *static per-token word vectors*, not LM hidden states. `HumanInputProjection` (lines 46-53) is LayerNorm -> Linear(lm_width, 32) -> GELU -> Linear(32, 256), applied to each token alone. Any word-order or context understanding must therefore be built by the 9M core (shown). The brief's phrase "contextual reader" is wrong for v6 (shown).
- **Word order is thin inside the core.** The question becomes a 1 x T grid (`unsqueeze(1)`, line 53). In `claude_fewex_net.py:23,35-45`, relative position biases are clipped at +-4, and half of the 8 heads are masked to +-1 column (`WINDOW = 1`). So beyond 4 tokens apart, the core cannot tell order from position bias (shown).
- **The notebook (context) is an unordered bag.** `sol_spatial_attention_core.py:84-90` gives every notebook position the "same position" bias index (`N.CLIP` = offset 0). The 256 context tokens arrive as a bag of static word vectors with no order and no sentence boundaries (shown).
- **Output: 8 averages.** `sol_translator_english_v6.py:21,38-45` projects each question position (256 + 2 geometry + 1 slot = 259) -> 32 -> LM width, then `adaptive_avg_pool1d` averages the answer-slot positions into 8 vectors. With a 48-token question each prefix vector is the mean of about 6 positions (shown). The LM sees only these 8 vectors plus BOS (shown, lines 64-74).
- **Training dose:** v6 plan = 500 updates x batch 2 = 1,000 row visits, 4 fixed rounds (`DEPLOYMENT-V6-PLAN.json`) (shown).
- **History to respect:** the 09-28 harvest lists "fast weights / Hebbian" as *forbidden to re-propose* for the maze few-example race (`2026-09-28-reasoner-idea-harvest-r1-r5.md:11`) (shown). ARCHITECTURE_DECISION.md's delta-rule memory passed an oracle two-hop control but its learned writer had not shown chaining (lines 58-69) (shown).

What this means for the 128-question panel (all **untested**, because I cannot see that pipeline): if the Mac pipeline uses the same reader and prefix, then "right calculator call, wrong final answer" (71/128) fits an *output* squeeze. Choosing an operation is a coarse, few-bit decision that survives averaging. A 3-5 digit result is fine-grained and has to survive 6-way averaging and a 32-wide hidden layer. "Wrong operation" (38/128) fits either memorising or a reader that cannot see word order past 4 tokens.

## 1. Staged curriculum (the long-term plan)

The stages follow Ben's order. Each stage has a gate that must pass before the next stage starts.

**Stage 0: interface round trip (English first).** Train reader + core + prefix so the frozen LM *reproduces the input text* (autoencoding), plus "repeat the number" items. The data is unlimited: code-generated numbers and templated sentences, plus human SQuAD TRAIN sentences already verified in `corpus/`. This teaches the pipe before any reasoning (suggested). Gate: change 1's probe marks.

**Stage 1: fact-free skill tasks, procedurally generated.** Every item comes from a generator that uses **nonce words** (invented names, objects and units such as "a blick weighs 7 drams"). Facts cannot help, so facts cannot be memorised (suggested). Six families:

| Skill | Generator sketch | What stops a shortcut |
|---|---|---|
| Decomposition | 2-5 step word problem over random quantities; target = the chain of sub-results, then the answer | depth split: train 1-3 steps, test 4-5 |
| Operation selection | one template, and one verb flips the operation ("gave away" vs "was given") | **minimal pairs** in the same batch, so surface cues cannot decide |
| Checking an answer | question + proposed answer (correct, off by one step, or wrong operation); output valid/invalid + the bad step | 50/50 balance; wrong answers are *plausible* (wrong-operation results) |
| Contradiction | 4-8 statements about nonce entities (orderings, set membership, counts); find the clashing pair or say "none" | about 1/3 "none"; clash distance varies |
| Abstain | same templates with one needed quantity removed; target "cannot tell" | about 1/4 unanswerable, matched in length to answerable ones |
| Compare hypotheses | evidence list + two candidate rules; pick the one consistent with more evidence | ties exist; evidence order shuffled |

"Effectively unlimited" (suggested): draw every training item fresh from a seed space far larger than total item visits (for example 10^6 visits from more than 10^12 combinations), with no item repeated. Keep held-out splits *by structure*, not just by item: unseen nonce vocabulary, unseen template wordings, deeper composition. With a fresh draw every step, memorising 32 problems is impossible by construction. The train-vs-held-out gap then measures generalisation directly (suggested). Related work (from memory, not re-opened): LIME (Wu et al. 2021: synthetic induction/deduction/abduction pretraining helped later theorem proving), and Raventós et al. 2023 (arXiv 2306.15063: in-context learning appears only above a task-diversity threshold). Both are **suggested** support for "skills from synthetic diversity."

**Stage 2: few-shot episodes** (change 4). **Stage 3: facts later**, through the notebook (retrieved text read at query time), not through weights. This matches "facts baked in later" and the 09-29 angle-6 finding that the retriever matters most (suggested). **Stage 4:** the real question format (calculator word problems), scored on a fresh panel.

## 2. Is the 32-wide reader / 8-prefix output a squeeze point?

- **Reader 32-wide:** probably *not* the main squeeze for token identity. A 32-dim linear map of word vectors can still keep thousands of tokens apart (suggested). The bigger reader limits are no context (static embeddings) and no order beyond +-4 (shown in code; their effect is untested).
- **Prefix 8 x pooled:** a likely squeeze for exact multi-token answers (untested). Prompt-compression work fits a few dozen tokens into a handful of soft vectors when those vectors are trained for it (gist tokens, Mu et al. 2023; xRAG; suggested). Here, though, the vectors are *averages of positions* through a 32-wide hidden layer, and they were trained for only 1,000 row visits (shown).
- **Cheap check:** change 1 below. One run of about 20-40 min on the 5070 Ti (estimate), plus a free embedding check:
  - **Free:** pass every number token and digit token through the saved reader's LN+Linear(->32). Count tokens whose nearest neighbour in the 32-dim space is a *different* token. If more than 2% collide, the reader loses token identity (falsifies "reader is fine").

## 3. Few-shot adaptation: which mechanism, and a fair measurement

Options, ranked by cost (all suggested):
1. **In-context examples in the notebook.** This needs almost no new machinery, but today the notebook is an unordered bag (shown). k examples would blur together. Minimal fix: add a learned *example-index* vector and a *role* vector (question / worked steps / answer) to each notebook token, and keep within-example order. Then meta-train on Stage-1 *episodes*: k worked examples of a fresh nonce rule, then a query. This is the route the task-diversity literature says produces in-context learning.
2. **Test-time training** (gradient steps on the k examples, with augmentation). This is already the fewex ruler's method (AdamW adaptation). It works but rewires weights for every task.
3. **Delta-rule fast weights** (ARCHITECTURE_DECISION.md). Closed-form and inspectable. But it is on the harvest's forbidden list for the maze race, and its learned writer is unproven (shown). Revisit only if option 1 fails its mark.

**Fair measurement of "learns from a few examples"** (untested design; author forms with a subagent, check them with an independent checker, seal by hash):
- Use **held-out rule families** never seen in training (for example a new operation defined by examples: "zib(a,b) = 2a - b").
- Plot accuracy at k = 0, 1, 2, 4, 8 and report the **slope** (gain per doubling of k), not one score.
- Two controls on every point:
  - **shuffled-answer examples:** the score should fall to the k=0 level. If it does not, the model ignores the examples.
  - **wrong-rule examples:** the score should fall *below* k=0. That proves the model reads and follows the examples.
- Compare against test-time training at the same k, and against the plain-net row.

## 4. Telling memorising, squeezing and genuine skill apart

**Free checks on saved outputs** (run on the Mac where the outputs live; read-only):
1. **Copy-from-train:** what share of wrong final answers equal *some training answer*? Memorising predicts a high share (above 25%; chance is about 32 / (number of plausible values)).
2. **Nearest-neighbour operation:** for the 38 wrong-operation cases, does the chosen operation match the operation of the most surface-similar training problem (word overlap)? Memorising predicts at least 70% match.
3. **Near-miss shape:** for the 71 right-call-wrong-answer cases, compare the output with the tool's true result: digit-level edit distance, same digit count, transposed digits, right first digit. Squeezing predicts mostly near-misses (distance of 1-2, right length). Memorising or confusion predicts unrelated numbers.
4. **Length dependence:** right-call-wrong-answer rate by answer length in tokens. Squeezing predicts a clear rise with length (for example 1-2 digits mostly right, 4+ mostly wrong). Skill failure does not predict a length effect.
5. **Output diversity:** the number of distinct final answers across the 128. Collapse to a few values means memorising or mode collapse.
6. **Sensitivity:** if any minimal-pair questions exist in the panel, does the answer change when the deciding word changes?

**Rule of thumb** (untested): checks 3 and 4 high and 1 and 2 low → squeeze. Checks 1, 2 and 5 high → memorising. Neither pattern, with errors scattered → skill gap. Then the **one cheap experiment** is change 1.

## 5. Ranked changes (one at a time; marks fixed now, before any run)

### 1. Interface round-trip probe (diagnostic; RECOMMENDED FIRST)
- **Claim:** untested that the pipe is the limit; suggested that it might be (section 2).
- **Change:** bypass the reasoning task. Take text "The answer is N." with N drawn fresh from 1-6 digit integers, plus 4-12-word templated sentences with nonce words. Run it through the current reader -> core (4 rounds) -> current StatePrefix (32 hidden, 8 pooled) -> frozen LM. Train reader + core + prefix to reproduce the text. Data is unlimited; no item repeats. Same lr and optimizer as v6, 3,000 updates, 2 seeds. Score exact match on 500 sealed fresh items per length bucket.
- **Pass (interface adequate):** at least 95% exact for 1-4 digit numbers and at least 90% exact on 8-word sentences, on both seeds.
- **Fail (interface is a squeeze):** under 80% on 4-digit numbers or under 60% on 8-word sentences, on both seeds. Then run the *same* probe with one change: prefix hidden 32 -> 256 and 8 pooled -> 32 learned query slots. If that clears the pass mark, the prefix was the squeeze.
- **Falsifier for "squeeze explains the 71":** the probe passes. Then the wrong final answers are a reasoning or copying skill problem, so go to change 3. Scores between the marks: no claim; add a third seed.
- **Why first:** it is about 1 GPU-hour, needs no new eval forms or approvals, and decides whether curriculum work can pay off at all.

### 2. Stage 0 pretraining as a standing gate (if change 1 fails, after widening)
- **Claim:** suggested.
- **Change:** prepend the change-1 round-trip objective (on the widened interface, if change 1 picked it) to the existing grounding run. Nothing else changes.
- **Pass:** the round-trip marks from change 1 hold *after* the following grounding/skill stage (loss of no more than 5 points). That shows the stage is retained, not overwritten.
- **Falsifier:** round-trip accuracy drops below 80% after the next stage. Then the interface must be frozen after Stage 0 (a separate change).

### 3. Replace the 32 practice problems with the Stage-1 generator
- **Claim:** suggested that it helps; untested here.
- **Change:** train the core on fresh generated items from the six families (no item repeats), at the same update budget as today's practice run. Interfaces stay as they are.
- **Pass** (on a *newly authored, sealed* 128-question panel in the real format):
  - right final answer at least 45/128 (3x today's 15);
  - wrong-operation cases no more than 19 (half of 38);
  - both seeds.
- **Falsifier:** generator held-out accuracy at least 90% but fresh panel at or below 20/128. That means the skills are generator-specific (a gap in template diversity), not general.
- **Report-only:** a per-family score on structural held-out splits (deeper chains, new nonce vocabulary).

### 4. Few-shot episodes through an ordered notebook
- **Claim:** untested.
- **Change:** add example-index and role vectors to notebook tokens, with within-example order (section 3), and meta-train on Stage-1 episodes with k drawn from 0-8.
- **Pass:** on held-out rule families, the k=8 score is at least 25 points above k=0 on both seeds; the shuffled-answer control is within 5 points of k=0; the wrong-rule control is below k=0.
- **Falsifier:** the k=8 gain is under 10 points, or shuffled answers score within 5 points of real examples (the model ignores the examples).

### 5. Self-check pass: the "checking" skill used at inference
- **Claim:** suggested (verify-then-retry is a known pattern); untested here.
- **Change:** after an answer, run the core once more on (question + proposed answer) with the checking head from Stage 1. If it says "invalid", re-run from a perturbed start, up to 2 retries. Nothing else changes.
- **Pass:** at least +8/128 right final answers on the fresh panel, and abstain precision of at least 70% on unanswerable items.
- **Falsifier:** the checker's valid/invalid accuracy on panel outputs is below 65% (it cannot judge real errors), or retries change fewer than 5 answers.

## 6. Risks and open calls
- Making the reader contextual (feeding LM hidden states instead of static word vectors) would likely fix word order cheaply. But it lets the frozen LM do part of the understanding, which bends "the reasoner does everything." That is Ben's call. I left it out of the top five on purpose (suggested).
- Nonce-word generators may teach skills that do not transfer to real English wording. Change 3's falsifier is designed to catch this (untested).
- Literature citations are from memory. Open each paper before any mark depends on it.

## Plain-language summary for Ben (a high-school senior)
- I checked the code. The "reader" doesn't really read sentences. It looks at each word alone, and the reasoner can only tell word order for words within 4 places of each other. The background text arrives as a jumbled bag of words.
- On the way out, the reasoner's answer gets averaged into 8 blobs before the language model writes it. Averaging is fine for "which operation?" but bad for an exact number like 4,827. That could explain why the model often picked the right calculator step but wrote the wrong final number.
- First test: can the pipe even carry a number through and back? Feed "The answer is 4827", train the pipe to repeat it, and see if it gets at least 95% right. If it can't, fix the pipe before teaching skills. If it can, the problem is the thinking, not the pipe.
- Then teach skills with made-up words ("a blick weighs 7 drams"). Facts can't help, and the computer can generate millions of fresh problems, so memorising 32 is impossible. Families: breaking problems into steps, choosing the operation, checking an answer, spotting contradictions, saying "can't tell", and comparing explanations.
- For learning from a few examples, put the examples in the notebook with labels saying which example each word belongs to. Prove the model uses them: scrambled examples should make it worse.
