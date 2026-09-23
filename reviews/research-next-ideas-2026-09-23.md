# Research note: what to try next (2026-09-23)

Written by the research thread for Ben. Every claim says where it comes from and how strong it is:
**shown** (a paper or our own run measured it), **suggested** (a paper points that way but not in our setting), **untested** (my reasoning only).
This note is about the chat assistant pipeline (ear → checker → notebook). It says nothing about the small card experiments or the village model.
No blind-panel items are quoted; only category counts from 261's RESULTS.md.

## The short version

1. **Stop asking the checker "is this claim true?" and make it answer the question itself.** 261's checker said YES to 8 of its 9 wrong saves with at least 68% confidence. A checker that has to *produce* the owner and the value, without seeing the ear's answer, can't just agree. This is the most likely way to cut wrong saves.
2. **A spelling rule for saved values** kills 2 of the 9 wrong saves cheaply (typos that leaked into a stored fact).
3. **Count the facts before listing them.** The ear saved only 4 of 16 facts when one sentence named several relatives. If the ear and the checker each count the facts first, a missing one turns into a question back to you instead of a silent miss.
4. **Grade the checker with "fake annotators" before trusting its confidence**, and use "active inference" to certify the <1% wrong-save rate with fewer hand-labelled turns.
5. **For your own architecture: train your own ear and mouth as a round trip** (sentence → facts → sentence). The round trip gives your own model a built-in checker, so the borrowed Qwen checker can eventually go.

## What 261 actually showed (our own run, shown)

From `artifacts/claude-earcheck261-20260922/RESULTS.md` on branch `claude/card-experiment-handoff-7c5b27`:

- 9 wrong saves (bar ≤ 1). By kind: 4 gave a pet to the wrong owner (2 plural "our" turns, 1 appositive, 1 plain speaker-pet), 2 corrections kept the old value, 2 had a chat typo inside the saved value, 1 saved something from a turn that should save nothing (at low confidence, p = 0.37).
- 8 of the 9 wrong saves passed with checker confidence ≥ 0.68; most ≥ 0.94.
- Raising the checker cutoff barely helps: recall stays at 77.9% from cutoff 0 to 0.8 while wrong saves only fall 19 → 7.
- Recall is capped before the checker runs: on the plural-relatives family the ear found 4 of 16 facts.
- Everything the checker held back (10) was correctly held back.

So the checker is good at spotting claims that are *obviously* unsupported, and bad at spotting claims that are *almost* right (right pet, wrong owner; right person, old value).

## Idea 1 (rank 1 for wrong saves): the checker answers, it doesn't approve

**What.** For each fact the ear wants to save, say (owner, relation, value), ask Qwen two questions about the user's turn, each in its own fresh prompt and never showing the ear's fact:
"According to this message, whose [relation] is [value]?" and "According to this message, what is [owner]'s [relation] now?"
Save only if both answers match the ear's fact exactly (after the same name clean-up the notebook uses). Any mismatch or "not stated" means don't save; ask the user instead.

**Why it should work.**
- QAFactEval (Fabbri et al., NAACL 2022, arXiv 2112.08542) found a carefully built question-answering checker beat the best entailment (YES/NO) checker on the SummaC benchmark, and that the two signals combine for a further gain. **Suggested** for us: that was summaries, not chat facts.
- Chain-of-Verification (Dhuliawala et al., 2023, arXiv 2309.11495) found that verification questions work better when each is answered on its own, "so the answers are not biased by other responses". **Suggested.**
- Calibrate Before Use (Zhao et al., ICML 2021, arXiv 2102.09690) showed language models lean toward certain answers regardless of input. A YES/NO prompt that shows the claim invites that lean toward YES. **Suggested** as the cause of 261's confident YES; **untested** here.
- Why it targets our 9: a wrong owner can't survive "whose pet is it?", and a stale value can't survive "what is it *now*?". That covers 6 of the 9 (4 owner + 2 stale). It does not help the 2 typos (see Idea 2). **Untested.**

**As one sealed experiment.** Frozen ear v4.1 + canonicaliser + brake, exactly as 261. The only change: replace the YES/NO checker with the two-question checker. Develop only on the known dev/257 panels; run once on a fresh blind panel written from 261's family spec.
Pass marks to fix in advance: wrong saves ≤ 1; the checker drops at most 3 true facts that 261's checker kept (counted from the same frozen ear frames); median added time ≤ 600 ms per turn. **Proved wrong if** 3 or more owner-or-stale wrong saves still get through.

## Idea 2 (rank 2, cheap): a spelling rule for saved values

**What.** A value may be saved only if every word in it is either a name (capitalised, or already in the notebook) or a word in a fixed English word list. Otherwise ask "Did you mean …?".
**Evidence.** Our own run only: 2 of 9 wrong saves were typo'd words stored as facts (**shown**). Nothing to research; it's a guard.
**As one sealed experiment.** Add the rule on top of 261's pipeline, nothing else. Pass: the 2 typo classes stop, and at most 1 true fact on the dev panel gets a question instead of a save. **Proved wrong if** any true value from the dev panel is refused because a real name was lowercase (then the name rule is too narrow).

## Idea 3 (rank 3, recall): count first, then list

**What.** Train the ear to write how many facts a turn holds before writing them ("3 facts: …"), and ask the checker the same count separately. If the counts disagree, ask the user instead of saving part of the list.
**Evidence.** Set-prediction relation extraction (Sui et al., "Joint Entity and Relation Extraction with Set Prediction Networks", arXiv 2011.01675) treats a sentence's facts as an unordered set predicted in parallel, because making a sequence model write them in one fixed order adds a burden that hurts extraction when a sentence holds several facts. **Suggested.** The count-first trick itself is **untested**.
**As one sealed experiment.** Retrain the ear on the same data with count-prefixed targets (the only change); counterfactual pair training stays a separate experiment. Pass: plural-relatives recall goes from 25% (4 of 16) to at least 80% of gold facts on a fresh panel's plural family, with other families within 2 facts of 261. **Proved wrong if** the count is right but the list still comes out short (then the problem is the decoder, not knowing the number).

## Idea 4 (rank 4, certification): calibrate the checker, then label smartly

Two pieces, two experiments:
- **Fake annotators.** Trust or Escalate (Jung et al., ICLR 2025, arXiv 2407.18370) asks the judge the same question as several few-shot "annotators" and uses their agreement as its confidence. They report this "significantly improves judge calibration" and gives a provable agreement guarantee with a threshold picked by a statistics test. **Shown** for pairwise chat judging; **suggested** for us. 261's raw pYES of 0.96 on wrong saves is exactly the overconfidence it addresses. We already pick cutoffs with Learn-then-Test (213); the new part is the confidence score.
- **Active inference.** Zrnic and Candès (ICML 2024, arXiv 2403.03208) give valid confidence intervals while hand-labelling mostly the items the model is unsure about. **Shown** in general; **untested** for rare errors. Caution (**untested**, my reasoning): the plain count rule stays the fallback. With 0 wrong in 299 turns the 95% upper bound is just under 1%; with 0 in 150 it is 1.98%. Any smarter method must beat that honestly, and its intervals may lean on large-sample maths that is shaky near 0%. GPT-6 Pro prompt 2 asks about exactly this.

## Idea 5 (rank 1 for your own architecture): a round-trip ear and mouth

**What.** When the own ear (sentence → facts) and own mouth (facts → sentence) from design doc 24 are trained, add one extra loss: the facts the ear reads must turn back into a sentence the ear reads the same way (facts → sentence → facts is a fixed point). At run time, a fact whose round trip doesn't come back identical is not saved. That gives your model its own checker, so Qwen stops being needed for safety.
**Evidence.**
- CycleGT (Guo et al., 2020, arXiv 2006.04702) trained text→graph and graph→text together with cycle losses and little paired data. **Suggested** (their graphs were WebNLG facts, close to our notebook rows).
- UniversalNER (Zhou et al., ICLR 2024, arXiv 2308.03279): a much smaller model trained on a big model's labels beat that big model on its own task by 7–9 F1. **Shown** for naming things in text; **suggested** for us: Qwen labels lots of made-up chat, and a small own ear learns from it. Using Qwen as a teacher is allowed, and doc 24 says how to state it honestly.
- TinyStories (Eldan and Li, 2023, arXiv 2305.07759): models under 10 million parameters wrote fluent, grammatical short stories after training on simple-vocabulary text. **Shown** for stories; supports the 99%-grammar goal for a small own mouth. **Suggested.**
**As one sealed experiment.** Doc 24's stage S1 ear+mouth, trained twice from the same seed: once plain, once with the cycle loss. Only change: the cycle loss. Pass: on a fresh ear panel, the round-trip-filtered own ear has ≤ 2 wrong saves at recall within 10 points of the plain one. **Proved wrong if** wrong frames round-trip cleanly as often as right ones (then the ear and mouth share the same mistake and the check is blind).

## Ideas I looked at and dropped

- Semantic entropy (Farquhar et al., Nature 2024): measures whether a model gives different *meanings* when sampled several times. Good for open questions, but our wrong saves were confident and stable (pYES ≥ 0.94), so sampling would probably agree with itself. **Untested.**
- An LLM judge on its own: a new study that corrupted correct answers step by step (Gharsallah et al., arXiv 2609.15561, Sept 2026) found step-by-step pipeline checkers beat single LLM judges at spotting the damage. That matches 261 and backs Idea 1. **Suggested.**
- Things already adopted (logit margin, counterfactual pairs, Qwen as full reader, a trained 360M verifier) are not re-proposed.

## Sources

- QAFactEval: https://arxiv.org/abs/2112.08542
- Chain-of-Verification: https://arxiv.org/abs/2309.11495
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
