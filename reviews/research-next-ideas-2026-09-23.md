# Research note: what to try next (2026-09-23, corrected 02:40 UTC)

Written by the research thread for Ben. Every claim says where it comes from and how strong it is:
**shown** (a paper or our own run measured it), **suggested** (a paper points that way but not in our setting), **untested** (my reasoning only).
This note is about the chat assistant pipeline (ear → checker → notebook). It says nothing about the small card experiments or the village model.
No blind-panel items are quoted; only category counts.

**Correction (02:40 UTC).** The first version said 4 of 261's 9 wrong saves gave a pet to the wrong owner and 2 kept an old value. That was wrong: I took the builder's descriptions on trust. My own recount from the raw files agrees with the director's diagnosis (`design/v3/30-modes/261b-decision.md`). In 6 of the 9 the ear had the right owner and the right name but wrote "dog" or "cat" where the answer key said "pet", and the scorer only accepted "pet". Only 3 were real meaning errors. So the old top idea (a question-answering checker aimed at owner mistakes) had no target in 261, and it has moved down.

## The short version

1. **Count the facts before listing them.** This is now the biggest gap: when one sentence named several relatives, the ear wrote only 4 of 16 facts. If the ear and the checker each count the facts first, a missing one turns into a question back to you instead of a silent miss.
2. **Ask whether the turn is telling or checking, as its own question.** One of the 3 real wrong saves was a check-question with no "?" ("so …"). A separate "is the speaker telling me something or checking something?" step targets it directly.
3. **Fix the checker's confidence and certify smartly.** The checker approved all 3 real errors (confidence 0.37–0.85). "Fake annotators" can calibrate that confidence, and "active inference" may certify the <1% wrong-save rate with fewer hand-labelled turns.
4. **For your own architecture: train your own ear and mouth as a round trip** (sentence → facts → sentence). The round trip gives your own model a built-in checker, so the borrowed Qwen checker can eventually go.
5. **A question-answering checker** (it answers "whose pet is it?" itself rather than approving) is kept as a guard for owner mistakes, which showed up in 257 but not in 261.

The 2 typo errors are already covered by 261b's mixed-case guard, so they are not an idea here.

## What 261 actually showed (my recount from the raw files, shown)

Files: `panel261_score.json`, `panel261_earpreds.json` and the sealed panel on branch `claude/card-experiment-handoff-7c5b27`. I compared each wrong frame's owner, relation and value with the answer key, category by category.

- 9 wrong saves as scored (bar ≤ 1).
- 6 of them had the right owner and right value, with relation "dog" or "cat" against a key of "pet": 1 plain turn, 2 plural-owner ("we"/"our") turns, 1 appositive turn, 2 correction turns. The canonicaliser turned "My/We/Our" into "me", which matches the key. These are scorer label mismatches. 261's FAIL still stands; the director's rule counts them as hits from 261b on.
- 3 were real errors: 2 chat typos that ended up inside a stored fact, and 1 fact saved from a check-question that should save nothing. The checker passed them at 0.85, 0.68 and 0.37.
- If the 6 had been counted as hits, recall would be about 101/122 = 82.8% (my recount, not the sealed scorer). That is still under the 85% bar.
- The biggest remaining loss is the plural-relatives family: 4 of 16 facts found.

So the checker didn't approve a stream of near-misses. It approved 3 plain errors, and most of the fail came from the answer key and from missed facts in plural sentences.

## Idea 1 (rank 1, recall): count first, then list

**What.** Train the ear to write how many facts a turn holds before writing them ("3 facts: …"), and ask the checker for the same count separately. If the counts disagree, ask the user instead of saving part of the list.
**Evidence.** Set-prediction relation extraction (Sui et al., "Joint Entity and Relation Extraction with Set Prediction Networks", arXiv 2011.01675) treats a sentence's facts as an unordered set predicted in parallel, because making a sequence model write them in one fixed order adds a burden that hurts extraction when a sentence holds several facts. **Suggested.** The count-first trick itself is **untested**.
**As one sealed experiment.** Retrain the ear on the same data with count-prefixed targets; that is the only change, and counterfactual pair training stays a separate experiment. Pass: plural-relatives recall goes from 25% (4 of 16) to at least 80% of key facts on a fresh panel's plural family, with every other family within 2 facts of 261 (scored with the 261b narrower-relation rule). **Proved wrong if** the count is right but the list still comes out short (then the problem is the decoder, not knowing the number).

## Idea 2 (rank 2, wrong saves): a separate "telling or checking?" question

**What.** Before any fact is saved, ask the checker one extra question in its own prompt, without showing it the fact: "Is the speaker stating something new, or checking, asking or supposing?" Save only on "stating". Right now the YES/NO question mixes "does the turn say this?" with "is the turn a statement?", and a check-question does *say* the fact.
**Evidence.** Sorting a turn by what the speaker is doing (statement, question, check) is a long-standing task of its own, known as dialogue-act tagging (Stolcke et al., 2000, arXiv cs/0006023). **Shown** that it can be learned as its own task (71% accuracy on transcripts against 84% for people, on phone conversations). That splitting it out fixes our case is **untested**. 257 also had check-questions without "?", plus plans and pretend turns saved as facts (board entry for 257; I have not re-checked those against the raw files).
**As one sealed experiment.** 261b's pipeline plus the act question; that is the only change. Pass: 0 saves from no_save check, plan and pretend turns on a fresh panel, and at most 2 true facts lost. **Proved wrong if** check-questions still pass as "stating" (then the model can't tell the act either, and the ear needs act training data instead).

## Idea 3 (rank 3, certification): calibrate the checker, then label smartly

Two pieces, two experiments:
- **Fake annotators.** Trust or Escalate (Jung et al., ICLR 2025, arXiv 2407.18370) asks the judge the same question as several few-shot "annotators" and uses their agreement as its confidence. They report this "significantly improves judge calibration" and gives a provable agreement guarantee with a threshold picked by a statistics test. **Shown** for pairwise chat judging; **suggested** for us. We already pick cutoffs with Learn-then-Test (213); the new part is the confidence score.
- **Active inference.** Zrnic and Candès (ICML 2024, arXiv 2403.03208) give valid confidence intervals while hand-labelling mostly the items the model is unsure about. **Shown** in general; **untested** for rare errors. Caution (**untested**, my reasoning): the plain count rule stays the fallback. With 0 wrong in 299 turns the 95% upper bound is just under 1%; with 0 in 150 it is 1.98%. Any smarter method must beat that honestly, and its intervals may lean on large-sample maths that is shaky near 0%. GPT-6 Pro prompt 2 asks about exactly this.
- **Lesson from the correction (shown, our own run):** 6 of 9 "wrong saves" were a gap in the answer key. Any certification plan has to check the key too, not only the model. Prompt 2 asks about that.

## Idea 4 (rank 4, guard): the checker answers, it doesn't approve

**What.** For each fact, ask Qwen in separate fresh prompts, never showing the ear's fact: "According to this message, whose [relation] is [value]?" and "what is [owner]'s [relation] now?". Save only if both answers match.
**Evidence.** QAFactEval (Fabbri et al., NAACL 2022, arXiv 2112.08542): a well-built question-answering checker beat the best YES/NO entailment checker on summaries, and the two combine for a further gain. Chain-of-Verification (Dhuliawala et al., 2023, arXiv 2309.11495): verification questions answered one at a time work better. **Suggested.**
**Why it dropped from rank 1:** after the correction, none of 261's 3 real errors was an owner or stale-value mistake, so this has no measured target yet. It stays as a guard for the owner errors 257 reported ("A's R is B and he …", "our" as subject).
**As one sealed experiment** (only if a panel shows owner errors again): 261b's pipeline, with the two-question check added as the only change. Pass: owner-error wrong saves ≤ 1 and at most 3 true facts lost.

## Idea 5 (rank 1 for your own architecture): a round-trip ear and mouth

**What.** When the own ear (sentence → facts) and own mouth (facts → sentence) from design doc 24 are trained, add one extra loss: the facts the ear reads must turn back into a sentence the ear reads the same way (facts → sentence → facts is a fixed point). At run time, a fact whose round trip doesn't come back identical is not saved. That gives your model its own checker, so Qwen stops being needed for safety.
**Evidence.**
- CycleGT (Guo et al., 2020, arXiv 2006.04702) trained text→graph and graph→text together with cycle losses and little paired data. **Suggested** (their graphs were WebNLG facts, close to our notebook rows).
- UniversalNER (Zhou et al., ICLR 2024, arXiv 2308.03279): a much smaller model trained on a big model's labels beat that big model on its own task by 7–9 F1. **Shown** for naming things in text; **suggested** for us: Qwen labels lots of made-up chat, and a small own ear learns from it. Using Qwen as a teacher is allowed, and doc 24 says how to state it honestly.
- TinyStories (Eldan and Li, 2023, arXiv 2305.07759): models under 10 million parameters wrote fluent, grammatical short stories after training on simple-vocabulary text. **Shown** for stories; supports the 99%-grammar goal for a small own mouth. **Suggested.**
**As one sealed experiment.** Doc 24's stage S1 ear+mouth, trained twice from the same seed: once plain, once with the cycle loss. Only change: the cycle loss. Pass: on a fresh ear panel, the round-trip-filtered own ear has ≤ 2 wrong saves at recall within 10 points of the plain one. **Proved wrong if** wrong frames round-trip cleanly as often as right ones (then the ear and mouth share the same mistake and the check is blind).

## Ideas I looked at and dropped

- Semantic entropy (Farquhar et al., Nature 2024): measures whether a model gives different *meanings* when sampled several times. Good for open questions, but our real wrong saves came from misreading the turn (typos, a check-question), which sampling would probably repeat. **Untested.**
- An LLM judge on its own: a new study that corrupted correct answers step by step (Gharsallah et al., arXiv 2609.15561, Sept 2026) found step-by-step pipeline checkers beat single LLM judges at spotting the damage. It backs splitting the checker into small separate questions (Ideas 2 and 4). **Suggested.**
- Things already adopted (logit margin, counterfactual pairs, Qwen as full reader, a trained 360M verifier) are not re-proposed.

## Sources

- QAFactEval: https://arxiv.org/abs/2112.08542
- Chain-of-Verification: https://arxiv.org/abs/2309.11495
- Dialogue act tagging (Stolcke et al.): https://arxiv.org/abs/cs/0006023
- Calibrate Before Use: https://arxiv.org/abs/2102.09690
- Set Prediction Networks: https://arxiv.org/abs/2011.01675
- Trust or Escalate: https://arxiv.org/abs/2407.18370
- Active Statistical Inference: https://arxiv.org/abs/2403.03208
- Conformal factuality (background for prompt 2): https://arxiv.org/abs/2402.10978
- CycleGT: https://arxiv.org/abs/2006.04702
- UniversalNER: https://arxiv.org/abs/2308.03279
- TinyStories: https://arxiv.org/abs/2305.07759
- Semantic entropy: https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750
- Judge perturbation study: https://arxiv.org/abs/2609.15561
