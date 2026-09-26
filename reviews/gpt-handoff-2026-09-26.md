# Premonition: handoff for an outside reviewer (2026-09-26, about 02:00 UTC)

The project's coordinating Claude wrote this for Ben to give to you. You cannot see the code repository, so everything you need is in this file. File and test names are included only so the project's agents can find what you refer to. Times are UTC; Ben is UTC-4.

Labels: **shown** = measured in a registered or verified run; **reported** = a builder's count not yet independently rechecked; **inferred** = our interpretation.

## 1. What the project is

- Owner: Ben, a high-school senior. He is building "Premonition", a small personal assistant on his own architecture (CAIRN v3). It should run on consumer hardware, learn over time, speak fluent English, be creative and reason deeply. The month-end target is a working build by September 30.
- Ben's brain analogy:
  - reasoner = cortex;
  - notebook of facts the user taught = hippocampus;
  - sleep = replay and self-improvement in downtime;
  - creative generator = wild ideas, filtered afterwards by exact checkers.
- Principles: learned parts over hand-written rules; exact recall with a source for every fact; never guess about the user (say "I don't know"); when surprised, ask one short question. The top priority is reasoning.
- Base language model: MiniCPM5-1B, always run with thinking turned off.
- Facts about people's relations (family and so on) are about 1% of the intended work (Ben, 09-25). They are a foundation, not the focus.

## 2. Current version: 0.1 (sealed 09-24)

- Chat model: plain MiniCPM5-1B.
- Reader (lis-301): a fine-tuned MiniCPM5-1B that turns each chat turn into typed facts. It saves a fact only when its confidence is at least 0.995. Confidence here is the minimum generated-token probability over the fact.
- Notebook: a durable, append-only log of taught facts (fsync, read-back, torn-tail detection).
- Reasoner: hand-written rules over the notebook.
- Sleep: a "word-route" sleeper that only learns from episodes that teach new family words.
- Turn log. A grammar fill-in finisher is added in 0.2.

**Result (shown):** 0.1 fails all six month-end checks (tests 336 and 336b) and the public benchmark test (bm-390).

Planned next versions:
- **0.2** = 0.1 + grammar finisher (gram-360) + episodic memory 382b (raw chat turns kept; the 20 most relevant are looked up when the notebook has no answer) + 383 (plain questions go to the chat model; see problem 2).
- **0.2b** adds the history-aware reader lis-319 and the lower save bar.
- **0.2c** is tonight's build; see section 5.

## 3. Scoreboard (shown unless marked)

LoCoMo memory benchmark, categories 1-4, 1,540 questions, token F1. LoCoMo has been used for development since bm-390, so it is now practice. LongMemEval is kept untouched as the final exam.

| System | LoCoMo F1 |
|---|---|
| Qwen3.5-2B, whole chat in context (2x our size; the bar) | 47.87 |
| Plain MiniCPM5-1B + our memory store, top 20 turns (dev, report-only) | 29.85 |
| Plain MiniCPM5-1B, whole chat in context | 27.50 |
| Plain MiniCPM5-1B + our memory store, top 10 turns (bm-395) | 26.84 |
| Plain MiniCPM5-1B + BM25 search, top 10 turns | 25.06 |
| LFM2.5-1.2B, whole chat in context | 19.01 |
| Premonition 0.1 (full agent) | 2.98 |

Uncertainty was measured by resampling questions. LoCoMo has only 10 conversations, so these numbers are weak evidence of generalising across conversations.

Why the plain 1B trails Qwen, on the whole chat (shown): it finds almost as much of the answer (token recall 43.6 vs 48.6) but writes about 8 words where the answer is 3 (median), so its precision is 23.7 vs 54.5. Cutting its answers to exactly the right words would score about 48. That is an upper bound, not an achievable result.

No-harm checks, 300 items each:

| System | MMLU-Redux | GSM8K |
|---|---|---|
| Qwen3.5-2B | 201 | 209 |
| LFM2.5-1.2B | 159 | 217 (165 when placeholder final answers get no credit) |
| Plain MiniCPM5-1B | 50 (234 replies gave no letter: a format problem) | 191 |
| Premonition 0.1 | 85 | 29 |

## 4. Standing problems

### Problem 1: it barely remembers what the user says
- **Shown:**
  - On LoCoMo, 0.1 saved 18 facts from 5,882 chat lines and said "I don't know" to 923 of 1,540 questions.
  - On our own chat panels (336b) it saved 47% of taught facts and answered 21% of answerable questions right, with 35 turns that saved something wrong.
- lis-319 (the reader sees the 6 earlier turns) = PASS:
  - back-references resolved 93/98 vs 1/98;
  - turns with a wrong save 1 vs 11 of 240.
  - But the save gate still held back 132 of 197 facts the reader found.
- Lowering the save bar from 0.995 to 0.98, on practice data: 771 vs 611 of 1,053 facts saved, with the same 3 wrong. Ben approved testing it.
  - The sealed test lis-319c (239 turns, 424 facts) is running now.
- A learned "does the source say this?" checker (rd-371) FAILED: it saved 15 vs 106. Its threshold fallback picked the maximum, and it was trained only on short turns.
- **Confirmed from the outside review:** the panel scorer checks only the person and the value, so "Mira works at Oxford" counts as right for "Mira studies at Oxford". It also lets a first name match a full name and silently drops messages the reader didn't answer.
  - The development check that picked 0.98 does check the relation, so that choice stands.
  - Before the 0.98 result came in, a stricter re-score was registered: person, relation and value must all match, and where the wording differs two blind judges must agree. Problem 1 counts as solved only if both scorings pass.
  - 0.98 is a confidence cut-off, not "98% correct". Even zero wrong saves in 239 messages leaves up to about 1.25% possible.
- Separately, 0.2 keeps raw chat turns (episodic memory), so conversation is preserved even when no fact is saved.

### Problem 2: it refuses too much
- **Shown:** inside 0.1, the chat model's GSM8K falls from 191 to 29 of 300, and MMLU gives no answer letter on 134 of 300. The wrapper answers "I'm not sure" instead of letting the chat model answer.
- Fix 383:
  - It triggers when the final reply abstains, the turn is a question, the question isn't about the user or people they know, and nothing was written to the notebook.
  - Then the plain 1B answers.
  - Names heard earlier in the chat count as people, so those questions keep the honest "I don't know".
  - It is being tested now in the rental run rent-382b.
- **Known issues:**
  - The outside review says a refusal trigger can't catch confident wrong answers, and the personal-question detector misses cases like "Where do I work?". It recommends explicit routing by what information a question needs.
  - Benchmarks measured that the reply trim used by 382b and 383 (cut back to the last full sentence) loses 4 of 191 correct GSM8K answers. 0.2c fixes this for routed answers: the final number, letter or name is kept.

### Problem 3: its own memory notes aren't trustworthy
- **Shown** (rd-378): blind judges found that 113 of 360 notes written by the 1B say things the chat didn't (31%; the bar was 5%). On overheard chats it was 38%.
- Policy now: notes are search pointers back to the raw chat, never answers.
- Tonight: blind judges grade the 1B's own practice notes, a sentence checker trains on them, and it gets one test on 30 fresh sealed chats.

### Problem 4: answers are too long
- See section 3.
- Tonight's test bm-397 trims answers using only the model's own draft (first line, copy-only; never the gold answer). Its no-drop marks on GSM8K and MMLU were registered and sealed before any output. It is running on CPU.

### Problem 5: the learned reasoner hasn't beaten a plain one yet
- **Shown:** earlier learned reasoners rsn-350, 351, 353, 353b, 355 and 356 all failed. For example, rsn-355 got 0 of 30 unseen three-step questions right.
- Rebuilt as 358:
  - a loop network (2 layers repeated for several rounds, with a learned stop head) vs a plain 8-layer network, about 6.4M weights each;
  - trained on sums, Latin grids and number puzzles; practised on small sizes and tested on bigger ones (6-digit sums, 6x6 grids, 5-number puzzles);
  - it reads grid or number tokens, not English.
- 358a has been running on Ben's PC since about 00:25 (up to 8 hours). It reports scores at fixed round counts as well as with its own stop.
- The outside review found four real limits:
  - the stop label is trained against one stored answer while any valid answer is accepted;
  - the stability check compares the whole grid, not just the answer cells;
  - stop rounds are not real compute savings, because all 48 rounds are computed;
  - the loop uses more compute than the plain network.
  - The thread's view (inferred): none of these can turn a fail into a pass.
- The "3x goal": a bigger learned reasoner must beat a smaller one through genuine reasoning, with equal tuning, on fresh blind tests.

### Problem 6: sleep doesn't learn in the real model yet
- **Shown:** 0.1's sleeper trained 0 of 360 times. It needs at least 8 new-family-word episodes, and ordinary chat never gives them.
- dl-1 (1B, 6 nights of puzzles):
  - the reinforcement-learning arm lost;
  - plain copy practice on each day's newly checked answers raised sampled correct answers from 69 to 160 of 169 (greedy solves only 8 to 9 of 12).
- dl-2 (7 nights, copy practice vs a wrong-answer placebo) = PASS, and a blind recount agrees:
  - right guesses on 100 fresh puzzles went from 64 to 237 and 249;
  - first-try solves went from 3 to 17 and 18;
  - the placebo ended at 42 and 51;
  - the worst drop between two nights was 11%.
  - **The catch (shown): slow forgetting.** On 300 general questions, it lost 26 of the 200 it used to get right by night 7 (5-7 after night 1). The overall score hid this because both arms picked up short-answer habits. So "almost never worse" holds for about 3 nights, not a week. The next fix is mixing old general answers into every night.
  - Also from the review, and confirmed: each arm collects from its own changing model, so dl-2 compares two training policies.
  - Nights now log whether weights actually changed and whether the saved version is live.
- Small-reasoner nights (slp-358n2) = PASS: sleeping on the day's checked puzzles beat nights of old practice only (5x5 grids +79 and +83 of 400), with no harm vs skipping the night.
- The packaged night joins 0.2c; its sleep row reports losses separately from gains.

### Problem 7: creative can't turn lucky hits into lasting skill
- blurt-3 = PASS, replicated. Sleeping on new checked hits kept the model's variety of guesses, while sleeping on repeated known answers collapsed the puzzles it reached from 27 to 3-4 of 66.
- Six follow-up tests on 09-25 all failed.
- It can't tell solvable puzzles from impossible ones: it picked the solvable twin in 66 and 52 of 120 pairs, which is chance.
- tgt5 = PASS: after sleep, it matched answers to their right targets in 97, 97 and 100 of 120 pairs vs 81 before (bar 84).
  - But sleeping on repeated known answers matched about as well, so matching isn't why good sleep solves more.
  - Training on an exact solver's answers still beats training on the model's own lucky hits.
- Best guess (inferred): **breadth**, meaning many different newly solved puzzles.
- Test brd-5 is registered: about 180 different puzzles vs 20 repeated, at equal size. It passes if the broad version solves at least 24 more of 240 fresh puzzles in each of 3 seeds.

### Other
- **Grammar:** the gram-360 finisher = PASS; rule-made fill-in lines went from 60% to 91% clean. The 1B's own chat is about 90% clean by strict graders, and Ben chose to stop there. Ben's rule: no chat-time checker models, only a better single model. The 1B cannot judge its own grammar (51-59% on same-length pairs).
- **Backtracking (Ben's idea):** the model reverts to an earlier thought with the abandoned path as input. rv-385 FAILED on 5x5 grids: restart 0, revert + ban 46/54, revert + note 13/14 of 80; the 1B copies the noted failures. Next: revert inside the 358 loop.
- **Infrastructure:**
  - Ben's Mac launches every job, and it stops launching below 5 GB free disk. It filled up again within about an hour on 09-26; the cause is being found.
  - Five modules the joined build imports lived only on a builder branch; they are now on main too.

## 5. Tonight's goal (set by Ben at 01:44 UTC)

"By 7am (11:00 UTC 09-26), solve each problem, with $5 of vast.ai compute."
- Solved means a pass mark registered before the run passes on fresh data. Honest fails stay fails.
- Fixes that pass reach the Month-end thread by 07:30 UTC. It builds 0.2c from them and runs one joined test on fresh sealed panels that finishes before 11:00, including rows for "sleep trained overnight and improved the day's work" and "no harm".

## 6. Outside code review (received 01:54 UTC), status

A 13-point review (routing, durable memory, one authoritative history, evidence-backed answers, reader scoring, answer extraction, reasoner stopping, sleep isolation and forgetting, creative metrics, statistics, reproducibility, disk). Each thread is checking its sections against the code. Confirmed so far:
- Section 1 (reader scoring): true; see problem 1.
- Sections 2-5 (Month-end's parts): the claims held.
  - Four fixes are in 0.2c: the next turn now sees the reply the user actually saw; routed math answers keep their final answer; remembered messages keep their dates after a restart; the word-overlap memory guard is now being counted, without changing behavior yet.
  - They pass a 12/12 code test.
  - Too big for tonight and listed as open: routing by the information a question needs, one evidence line per personal claim, and crash-safe memory writes.
- Section 6 (notes and store): true. The store would let notes straight into answers; no notes are written today, and answers must use only the original chat, with notes pointing back to it.
- Sections 7 and 13 (save bar and statistics): agreed.
- Section 8 (trimming): real in 0.2's chat layer (4 of 191 GSM8K answers lost), fixed in 0.2c; not present in bm-397's trim.
- Section 9 (reasoner stop limits): all four real; they limit claims but can't flip 358a's verdict.
- Sections 10-11 (sleep): confirmed; see problem 6.
- Section 12 (creative metrics): brd-5 will report first try, within budget, distinct puzzles and 3- vs 4-number puzzles separately.
- Section 13 (missing modules): all five were on the builder branch; now on main.

## 7. Who works on what (each is a Claude agent in its own thread)

| Thread | Owns | Now |
|---|---|---|
| Director | job queue, Mac watcher, Ben's PC and rentals, spending ledger, verdict board | Mac disk fix; holds tonight's $5 |
| Month-end ("Working build by September 30") | 0.1, 0.2, 0.2c builds and joined tests | rent-382b (382b + 383); builds 0.2c at 07:30 |
| Reading facts | reader, save gate, notes, sentence checker | lis-319c test; note checker |
| Benchmarks | public benchmarks, memory store, answer trimming | bm-397 trim test |
| Sleep research | small loop reasoner (3x goal), nights for the small reasoner | 358a; bigger-unseen-puzzle night test |
| Fix sleep | nights for the 1B | dl-2 recount; packaged night for 0.2c |
| Creative | creative generator, lucky hits, exact checkers | brd-5 breadth test |
| Memory for its own thoughts | backtracking | waits for 358a |
| Grammar | fill-in finisher | done |

## 8. Compute, budget and rules

- **Compute:**
  - Ben's PC: Windows, RTX 5070 Ti 16 GB, Python 3.10, usually one job at a time.
  - vast.ai RTX 5090 rentals, at most $4 per job. The total cap is $30; about $22 was spent before tonight's $5.
  - The cloud agents can't reach Hugging Face, so models live on Ben's PC and Mac. New model downloads need Ben's yes.
- **Research rules:**
  - One change per experiment.
  - The pass mark, and the result that would prove it wrong, are registered before the run; the code is sealed by hashes before it runs; a separate blind agent recounts; fails stay fails.
  - Blind test panels are never trained on, tuned on, read or quoted.
  - No benchmark data in training.
  - Fictional names only.
  - Text written by Claude isn't training data for our models; prefer code-made labels, graded drafts of our own model, or a teacher model (GLM 5.3 Flash).
  - Files are additive only.

## 9. How to send instructions back

Ben will paste your answer into the project chat. The coordinating Claude splits it by owner thread, and each thread checks every factual claim against the code before acting.

Please:
- label each claim shown / suggested / untested;
- name the thread each item is for;
- propose one change at a time, and give for each test its pass mark and the result that would prove it wrong, fixed in advance;
- keep small-network experiments separate from the full joined model;
- respect the budget and the rules above;
- end with a plain-language summary for Ben.

Please don't propose: training or tuning on test panels or benchmarks, new model downloads without Ben's yes, chat-time checker models for grammar, or making relation facts the focus.

## 10. Glossary

- **F1:** token-overlap score between the answer and the gold answer.
- **Registered:** pass marks fixed before the run.
- **Sealed:** code or data hashed so it can't change unnoticed.
- **Panel:** a fixed test set.
- **Arm:** one variant in a test.
- **Placebo:** a control arm with the useful information destroyed.
- **Rental:** a vast.ai GPU run.
- **LoCoMo / LongMemEval:** long-chat memory benchmarks.
- **GSM8K:** grade-school math.
- **MMLU-Redux:** multiple-choice knowledge.

End of handoff.
