# Why Copperfern, Sunwillow and Starmeadow were never learned (read-only diagnosis)

Scope: no model loaded, no training, no GPU, no code edits. Evidence = the six raw `HF-report.json` files (Wave 2 `raw-{on,off}-s{1,2}`, r5 `raw-{on,off}` = seed 0), `run_hf.py`, and the source in `/Users/ben-hannan/learner-ops/premonition-research-20261029.noindex/sequential-control/src/sleepmlx` (`gate.py`, `grading.py`, `grading-contract.json`, `torch_backend.py`). Tokenizer only (`/Users/ben-hannan/learner-ops/lfm3/hf/tokenizer.json`). Labels: **shown** = read directly from files; **suggested** = fits the data, not isolated; **untested** = no data.

## 0. How the test is built (the key mechanism)

- A "card" is only a question and an answer (no statement). Training uses the first string of each plan row, `"What is the fictional Aster station door word?"`, with system text "Answer with just the name." (`run_hf.py` batch loop: `for q,ans,_ in ...`). **Shown.**
- Scoring uses the third string, a different wording: `"Name the door word assigned to the Aster station."` (`evaluate()`: `for i,(train,ans,q) in enumerate(allfacts)`). So every "held" check is a paraphrase probe. The training wording itself is never probed. **Shown.**
- Training target = `encode(answer) + [stop]`, no prefix (`training_answer_prefix` is empty for lfm3_mps), `add_special_tokens=False` (`torch_backend.py:148`). My token counts therefore match training. **Shown.**
- Loss `ce` is summed over all answer tokens in the 3-card batch divided by total answer tokens (`torch_backend.py:261-267`). Only this pooled number is logged; **per-fact losses were not recorded**.
- Grader strict-4: the answer must appear as a whole phrase in the first 12 words of the first line, with no hedge/negation words (`gate.py` `correct`, `has_phrase`, `unambiguous`; `head_words: 12`).

## 1. Per-fact table

Tokens are from the LFM3 tokenizer (answer only, as trained; the stop token adds 1 more).

| Fact | Card (training) question | Held (scored) question | Answer | Tokens |
| --- | --- | --- | --- | --- |
| Copperfern (block 1) | What is the fictional Aster station door word? | Name the door word assigned to the Aster station. | Copperfern | 3: Cop / per / fern |
| Sunwillow (block 1) | What is the fictional Cobalt library vault label? | Name the vault label assigned to the Cobalt library. | Sunwillow | 3: Sun / will / ow |
| Starmeadow (block 2) | What is the fictional Fennel garden room name? | Name the room assigned to the Fennel garden. | Starmeadow | 3: Star / me / adow |
| Moonhaven (learned) | ...Brindle airship home bay? | Name the home bay assigned to the Brindle airship. | Moonhaven | 3: M / oon / haven |
| Mistbrook (learned) | ...Dapple clocktower access word? | Name the access word assigned to the Dapple clocktower. | Mistbrook | 3: M / ist / brook |
| Pinecrest (learned) | ...Ember courier call sign? | Name the call sign assigned to the Ember courier. | Pinecrest | 4: P / ine / c / rest |

Token count does not separate the groups: learned facts have 3, 3, 4 tokens; the three misses have 3, 3, 3. **Shown.** The hard-fact first tokens are whole common-word pieces (Cop, Sun, Star); the learned ones start with a bare letter (M, M, P). **Shown (tokens); causal role untested.**

### Model answers (greedy, 32 tokens) at each checkpoint

Baseline (phase 0) for all three: a rambling guess ("Aster Station's door word is "Astra" or something else?...", "Cobalt-01...", "Fennel Garden Room ... Wait, that doesn't sound right"). All runs identical here.

| Fact | Phase 1 (after own/first block), all 6 runs | Phase 2 ON (s0,s1,s2) | Phase 3 ON | Phase 2 OFF | Phase 3 OFF |
| --- | --- | --- | --- | --- | --- |
| Copperfern | "Copper" (s0, s2), "Moon" (s1) | "Copper", "Copperwillow" (s1), "Copper" | "Copper" x3 | "Mistbrook" x3 | "Rocket" (s0), "Oak" x2 |
| Sunwillow | "Sunrise" x6 | **"Sunwillow" x3 (hit)** | **"Sunwillow" x3 (hit)** | "Moonhaven", "Mercury" x2 | "Cobalt_04", "Rosecliff" x2 |
| Starmeadow | "Sunroom" x6 | "Sunroom" x3 | "Moonlight" x3 | "Morning" x3 | "Fenice" (s0), "Rose" x2 |

(s0 = r5, s1/s2 = Wave 2. Source: all `HF-report.json`; `checkpoints[*].held[*].out`.) **Shown.**

Note on the task's framing: Sunwillow is not "never learned" in the ON arm. It is wrong at its own block (phase 1) in every run, then right at phases 2 and 3 in all three ON seeds (it was counted as not-learned because the L column is the own-block checkpoint). Copperfern and Starmeadow are never right in any of the 12 post-training checkpoints per fact.

### Training loss (pooled over the 3 cards in each step; per-fact not logged)

| Phase | step 1 | step 12 | step 24 (last) |
| --- | --- | --- | --- |
| 1 (block 1, cards 0-2, both arms) | 8.12 | 1.64-1.72 | **0.48 (s2), 0.54 (s0), 0.57 (s1)** |
| 2 OFF (block 2 only) | 2.9 | 0.01-0.02 | **0.003** |
| 3 OFF (block 3 only) | 5.4-5.7 | 0.01 | 0.002 |
| 2 ON (rehearsal mix) | 0.9-2.4 | 0.07-0.48 | 0.007-0.013 |
| 3 ON | 2.2-3.5 | 0.4-0.5 | 0.017-0.053 |

**Shown.** Block 1 ends far from fitted (0.5 nats per answer token) while block 2 in the OFF arm ends at 0.003.

## 2. Which cause is it?

### GRADER: ruled out for these facts (shown)
- I scanned all 12 post-training outputs for each of the three facts in all six runs for a case where the answer string appears but `hit` is False: zero such cases. No reformatted-but-right answer exists.
- The "close" answers are genuinely different strings: "Copper", "Moon", "Sunrise", "Sunroom", "Copperwillow". Strict-4 correctly rejects them. A lenient prefix match would be wrong and would also hide that the model never emitted "fern", "will", "meadow".

### TRAINING EXPOSURE: ruled out as the main cause for Copperfern and Starmeadow; partly real for Sunwillow
Draws per card (index 0..8; Copperfern=0, Sunwillow=2, Starmeadow=5), from `phases[*].selected`:
- ON s1 total [48, 40, 43, 24, 19, 14, 8, 9, 11]; ON s2 [41, 44, 52, 19, 18, 22, 7, 6, 7]; ON s0 [46, 45, 44, 21, 22, 21, 6, 5, 6]. OFF: 24 each, every card, every run.
- Block 1 cards (Copperfern, Moonhaven, Sunwillow) got exactly the same 24 draws in phase 1 in all runs, yet only Moonhaven was learned. So equal exposure, different outcome. **Shown.**
- Block 2 in OFF: Mistbrook, Pinecrest and Starmeadow each got 24 draws and ended at pooled loss 0.003, yet Starmeadow answered "Morning" x3 while the other two were right. **Shown.** In ON s2, Starmeadow got 17 phase-2 draws (the most in its block; Mistbrook 11, Pinecrest 13) and was still wrong, while Pinecrest was right. **Shown.**
- Sunwillow: wrong after 24 draws (phase 1), right after ~11 more (phase 2, ON, all 3 seeds: 16, 11, 8 phase-2 draws). So for Sunwillow more exposure helped. **Shown (association over 3 seeds); causal role suggested.** Copperfern had 4-15 phase-2 draws and 41-48 total and still never worked.

### HARD FACT (answer clashes with common word / first-token prior): leading explanation, partly shown
- Outputs are common words that share the first token: Copperfern -> "Copper" (Cop+per), Sunwillow -> "Sunrise" (Sun+...), Starmeadow -> "Sunroom". The model emits a plausible English word and stops, never the invented tail. **Shown (outputs); mechanism suggested.**
- Token count and length are NOT the reason (see table above). **Shown.**
- Note "Sunroom" for Starmeadow is already the phase 1 answer in all six runs, before block 2 has been trained: it is a prior (and a block-1 leak), not a trained confusion. **Shown.**

### PARAPHRASE TRANSFER (not in the user's list, but the strongest single finding): shown for Starmeadow, untested for the other two
- Starmeadow's own training question reached pooled loss 0.003 in the OFF arm (all three block-2 cards memorised to that level), yet the scored paraphrase gives "Morning". The training question is never probed, so we cannot say whether the model answers "What is the fictional Fennel garden room name?" correctly. If it does, the fact is stored but does not generalise to "Name the room assigned to the Fennel garden." **Shown (loss, wrong paraphrase); the memorised-but-not-transferred reading is suggested; untested directly.**
- Caveat for reading the whole experiment: the harness uses ONE training wording per fact. The real nightly recipe trains paraphrases and several Q&A cards per fact (`recipe.py` lines 3, 578, 1023-1024), so this test probably overstates paraphrase failures relative to the real app. **Shown (code).**

### UNDERFIT in block 1 (shown for the block, per-card attribution untested)
- Phase 1 ends at pooled 0.48-0.57 per token (about 8 nats over 3 answers) versus 0.003 for block 2. Moonhaven is the only phase-1 hit in all six runs, which is consistent with Copperfern and Sunwillow carrying the unlearned loss. **Block-level numbers shown; per-card attribution suggested (per-fact loss not logged).**
- Why block 1 is slower: it starts from a zero adapter and ce 8.1, so early steps learn the answer format and stop token; block 2/3 start with that done (first-step loss 2.9 vs 8.1). **Suggested.** The optimizer and cosine schedule are reset every block (`train_begin(24, 2e-4)`), so each block has only 24 steps of decaying lr.

### INTERFERENCE (blending between facts): present, but secondary
- Within block 1 (phase 1): Copperfern answered "Moon" in s1 (Moonhaven is its block neighbour). Mistbrook answered "Copper" and "Moon" before block 2 was trained, so block-1 name pieces leak onto unrelated untrained questions. ON phase 2: Copperfern -> "Copperwillow" (s1), a fusion of its two block-1 siblings Copperfern + Sunwillow. **Shown.**
- Same-slot clashes (door word: Aster vs Iris; call sign: Ember vs Glimmer; bay: Brindle vs Harbor) only matter for retention (OFF phase 3: Moonhaven -> "Rosecliff", Pinecrest -> "Ashwater"); they cannot explain misses at the own-block checkpoint because the clashing block-3 cards do not exist yet. **Shown.**
- Interference cannot explain Starmeadow (wrong at phase 2 in OFF, where block 2 is trained alone at 0.003). **Shown.**

## 3. Ranking of likely causes

1. **Weak transfer from the single training wording to the scored paraphrase, for rare invented names that begin with a common-word token** (Cop/Sun/Star). Evidence: Starmeadow memorised in OFF (0.003) yet wrong; wrong answers are common-word stems; exposure and length do not separate. Starmeadow part: **shown**. Copperfern/Sunwillow part: **suggested**. Whether the first-token prior is causal: **untested**.
2. **Block-1 underfit (24 cold-start steps, loss 0.5)**, mainly hurting Copperfern and Sunwillow. Block-level loss: **shown**. Sunwillow flipping to correct after ~11 rehearsal draws: **shown (3/3 ON seeds)**. Copperfern not flipping with 41-48 total draws: **shown**, so underfit alone is incomplete.
3. **Block-mate interference** (Moon/Copper/Copperwillow leakage): **shown** as a symptom, **suggested** as a minor cause.
4. **Exposure differences between cards:** **shown** not to be the main factor (equal draws, different outcomes), except Sunwillow.
5. **Grader:** **shown** not a factor.

## 4. The ONE smallest change to test first

Because the weights from those runs are deterministic (OFF s1 and ON s1 phase-1 losses match to the digit, 0.565), the cheapest decisive step is a **measurement-only change, no training change**: in `evaluate()` also generate the answer to each fact's training wording (`allfacts[i][0]`, 9 extra short generations per checkpoint) and log it next to the scored paraphrase. Nothing else changes (same seeds, same steps, same recipe, same grader).

Why this first: it separates "never stored" (cause 2) from "stored but not transferred" (cause 1) for the two block-1 facts and for Starmeadow. Without it, any training change (more steps, paraphrased cards) cannot be attributed.

- Runs: ON arm, seeds 0, 1, 2 (harness takes `--seed`; seed 0 = r5). About 2.5-3 min each, about 9 min total, well inside the 30-min cap, run one at a time.
- Pass marks (fixed in advance):
  1. Reproduction: the scored-paraphrase hits and general-question counts in all 3 ON runs equal the existing reports exactly (held hits 0/1/4/4 at phases 0-3 for s0, 0/1/3/4 for s1, 0/1/3/4 for s2; general 6/7/5/6, 6/7/6/6, 6/7/4/4). HARM unchanged by construction.
  2. Transfer reading confirmed if: at the own-block checkpoint (phase 1 for Copperfern, Sunwillow; phase 2 for Starmeadow) the training wording is answered correctly for at least 2 of the 3 hard facts in at least 2 of 3 seeds while the paraphrase stays wrong.
  3. Underfit reading confirmed if: at least 2 of 3 hard facts are wrong under the training wording too at phase 1/2 in at least 2 of 3 seeds.
- Result that would prove the transfer reading wrong: the training wording is also wrong for Starmeadow at phase 2 in OFF/ON (it would mean even the memorised-loss 0.003 does not reach generation, pointing at a generation or stop-token issue instead). A split (2 of 3 facts each way) means both causes are real and the next change must be per-fact.
- Next change decided by the result (not run yet): if transfer, add a second wording per fact to training (as the real recipe does) and re-score on a third, unseen wording, pass = at least 2 of the 3 hard facts learned across 3 seeds in the ON arm with HARM unchanged (general hits no more than 2 below baseline); if underfit, raise block-1 steps (e.g. 24 -> 36) with the same pass mark.

## For Ben

- Three of the six made-up facts never stuck. I checked the "grader was too strict" idea first. It is not the problem: when the model got it wrong, it said a different word, like "Copper" instead of "Copperfern".
- It is also not that those facts got less practice. In the no-review runs every card got the same 24 turns, and two of the three untouched ones still failed while their block-mates passed.
- The best clue: for "Starmeadow", the model had practised its question until it was almost perfect (the practice score was near zero error), but when we asked the same thing in different words it said "Morning". So it may have learned the one sentence and not the idea. We have not checked that directly yet. That is why the next step is only to ask the practised question out loud as well, and change nothing else.
- The first lesson block was also practised less well than the others (the practice error was about 0.5 instead of about 0.003). That probably hurt Copperfern and Sunwillow. Extra review fixed Sunwillow in all three review runs, but never Copperfern.
- Why the wrong words look the way they do: the model's brain already has strong words like "Copper", "Sun" and "Star", and it grabs them and stops before the strange end of the new name.
- The real app teaches each fact in several wordings, but this test used only one. So this test may be harder than real life.
- What I know for sure: the grader is fine, and practice counts do not explain it. What I only suspect: the wording-switch problem and the weak first lesson. What I have not tested: whether the strong starting words are really the cause.
