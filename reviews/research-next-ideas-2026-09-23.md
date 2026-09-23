# Research note: what to try next (2026-09-23, version 3)

Written by the research thread for Ben. Every claim says where it comes from and how strong it is:
**shown** (a paper or our own run measured it), **suggested** (a paper points that way but not in our setting), **untested** (my reasoning only).
This note is about the chat assistant pipeline (ear → checker → notebook). It says nothing about the small card experiments or the village model. No blind-panel items are quoted; only category counts.

**Version history.**
- v2 (02:40 UTC): my own recount of 261 showed 6 of the 9 "wrong saves" were label mismatches (the ear wrote "dog"/"cat", the answer key said "pet"). Only 3 were real errors. This agrees with `design/v3/30-modes/261b-decision.md`.
- v3 (02:45 UTC): folds in an outside review Ben brought back (written about v1). Accepted: the round trip can't stand in for a source check; the QA checker's guarantee was overstated; spelling and counting are flags, not fixes; the calibration, denominator and active-inference points. Ben's call: the QA checker is the first experiment to run.

## The short version

1. **Run first: the checker answers questions instead of approving claims.** Keep the ear frozen and compare the old YES/NO checker with a question-answering (QA) checker on the same ear outputs. Honest size of the target in 261: 3 real errors (2 typos, 1 check-question). My reasoning, **untested**: the QA form can plausibly catch the 2 typos, because a garbled name won't come back as the answer, but probably not the check-question. 257's reported owner errors are the other target.
2. **Ask "telling or checking?" as its own question.** This targets the check-question kind of error.
3. **Count the facts to flag gaps, and score recall three ways.** The ear found only 4 of 16 facts when one sentence named several relatives. A count can reveal a missing fact; it doesn't recover it.
4. **Certification:** calibrate with real calibration data, and report two separate error rates plus recall.
5. **Your own architecture:** round-trip training is a way to *learn* the ear and mouth. It does not replace checking the fact against what you actually said.

## What 261 actually showed (my recount from the raw files, shown)

Files: `panel261_score.json`, `panel261_earpreds.json` and the sealed panel, on branch `claude/card-experiment-handoff-7c5b27`.

- As scored: 9 wrong saves (bar ≤ 1), recall 95/122 = 77.9%.
- 6 of the 9 had the right owner and right value, with relation "dog" or "cat" against a key of "pet" (1 plain turn, 2 "we"/"our" turns, 1 appositive turn, 2 corrections). They are label mismatches. 261 stays FAIL; from 261b on, the director's rule counts them as hits.
- 3 were real errors: 2 chat typos inside a stored fact (checker score 0.85 and 0.68), and 1 fact saved from a check-question that should save nothing (0.37).
- With the 6 counted as hits, recall would be about 101/122 = 82.8% (my recount, not the sealed scorer). That is still under 85%.
- Plural-relatives family: 4 of 16 facts found.
- The theta sweep's "19 → 7" and the headline "9" are the same arm at different cutoffs: 19 at cutoff 0 (nothing held back, so the same as the brake-only arm), 9 at the sealed 0.25, 7 at 0.7. As v1 wrongly put it, that was "barely helps". Going from 19 to 7 is a 63% cut with recall almost unchanged (77.9% → 77.1%). It still misses the bar of 1.

## Idea 1 (run first): the QA checker vs the YES/NO checker

**What.** For each fact, ask Qwen in separate fresh prompts: "According to this message, whose [relation] is [value]?" and "According to this message, what is [owner]'s [relation] now?". Each question hides the part it checks, but it does see the rest of the proposed fact. It is *not* an independent re-read of the whole turn.
Safeguards:
- the answer may be "not stated" or "ambiguous", and an unresolved "our" must not be turned into one person;
- several answers are allowed where the relation allows several;
- a relation question is added ("How is [owner] related to [value]?"), so a misread relation is tested too.

**What it can and can't promise.** A wrong owner is caught only when the checker answers the owner question correctly. Two matching answers do not prove the fact is right. The hypothesis is only that answering a targeted question exposes errors a YES/NO judgment overlooks. **Untested.**

**Evidence.** QAFactEval (arXiv 2112.08542): in a summary-checking comparison, a well-built QA metric beat the best YES/NO (entailment) metric, and the two combined did better still. Chain-of-Verification (arXiv 2309.11495): verification questions answered separately, without the original answer in view, worked better. **Suggested**: neither measures a chat-to-notebook task.

**As one sealed experiment.** Frozen ear v4.1 + canonicaliser + brake (+ 261b's guard if it has been accepted). Run the YES/NO checker and the QA checker on the same fresh turns and the same frozen ear outputs; the checker is the only change.
Report:
- wrong saves prevented and true facts lost, by error kind (owner, relation, value, stale, typo, act);
- how often it asks you instead of saving;
- latency: the median, plus the slowest 10% of turns and the 4-fact turns, since two or three questions per fact adds up.

Pass marks, fixed before the run: wrong saves ≤ 1; at most 3 true facts lost against the YES/NO arm; median added time ≤ 600 ms and slowest-10% ≤ 1500 ms. **Proved wrong if** the QA arm stops no more real errors than the YES/NO arm on the same frames.

## Idea 2: a separate "telling or checking?" question

**What.** Before a fact is saved, one extra prompt that doesn't show the fact: "Is the speaker stating something new, or checking, asking or supposing?". Save only on "stating".
**Evidence.** Dialogue-act tagging (Stolcke et al., 2000, arXiv cs/0006023) learns what a speaker is doing as its own task: 71% accuracy on transcripts, against 84% for people, on phone conversations. **Shown** that it is a separate, learnable task. That it fixes our case is **untested**. 257 also reported check-questions, plans and pretend turns saved as facts (board entry; I have not re-checked those against the raw files).
**As one sealed experiment.** Add the act question as the only change. Pass: 0 saves from no-save check, plan and pretend turns, and at most 2 true facts lost. **Proved wrong if** check-questions still come back as "stating".

## Idea 3: counting flags gaps; score recall three ways

**What.** The ear writes how many facts a turn holds, then lists them. If the ear's count and the checker's count disagree, it asks you instead of saving part of the list.
**Limits (from the review, accepted).** This *detects* omissions; it doesn't *recover* them. Both could agree on the same wrong count. The set-prediction paper (Sui et al., arXiv 2011.01675) supports treating facts as an unordered set, but its method predicts in parallel with a matching loss. It says nothing about putting a count in front of an ordinary list. **Untested.**
**Scoring.** Report three numbers separately, so better detection isn't mistaken for better reading:
1. facts the ear read correctly before checking;
2. facts actually saved correctly;
3. incomplete turns correctly sent back as a question.
**Proved wrong if** the count doesn't raise (3) without lowering (2). A right count with a short list does not by itself show the decoder is to blame, because binding each name to its relation is a separate skill.

## Idea 4: certification done properly

- **Calibration needs all predictions, not just the errors.** A score of 0.96 on a wrong save doesn't prove miscalibration: a calibrated 0.96 is still wrong about 4% of the time. Check the error rate inside each score band over every fact the checker saw.
- **Simulated annotators** (Trust or Escalate, arXiv 2407.18370) give a confidence *signal*. The paper's guarantee comes from picking the threshold with human-labelled calibration data, which we already do with Learn-then-Test (213).
- **Two rates, not one.** Report wrong saves ÷ all saved facts *and* turns with a wrong save ÷ all turns, plus recall. A system that rarely saves can look good on the second while many of its saves are wrong.
- **The 299 rule** (0 errors in 299 → 95% upper bound ≈ 0.997%; 0 in 150 → ≈ 1.98%; formula 1 − 0.05^(1/n)) holds only for independent samples of the unit being certified, with the system frozen. 299 turns do not certify the per-saved-fact rate. A panel you tuned against certifies nothing.
- **Active statistical inference** (Zrnic and Candès, arXiv 2403.03208). The reviewer points out that its Appendix C has finite-sample, time-uniform versions for bounded means, which a 0/1 wrong-save indicator is. That corrects my v1 worry about large-sample maths; the reviewer read it, I haven't re-checked it. It works by random sampling with known probabilities plus a correction, not by "check the unsure ones and trust the rest". Whether it saves labels at our rare error rate is **untested**.
- **The answer key can be wrong** (6 of 9 in 261, shown). A certification plan has to check the key too.
- **Two panels, two jobs.** Risk-family panels find out whether a known failure improved. Only a representative sample of everyday chat supports a claim about everyday error rates.

## Idea 5 (your own architecture): round-trip training, not round-trip permission

**Accepted from the review.** A round trip (fact → sentence → fact) can pass perfectly on a wrong fact. Invented example: the turn says the dog belongs to the speaker's sister; the ear writes (speaker, pet, Pip); the mouth says "My pet is Pip."; the ear reads back (speaker, pet, Pip). Nothing in the loop looks at the original turn again, so round-trip agreement cannot be the permission to write. v1 was wrong to suggest it could replace Qwen for safety.
**What stays.** Cycle training as a way to *learn* your own ear and mouth from less paired data. CycleGT (arXiv 2006.04702) shows cycles help learn text↔graph conversion from unpaired data. **Suggested** for us. It does not show that a round-trip-consistent graph is faithful to a given message.
**If the own model is ever to replace Qwen as the gate,** its check has to compare the proposed fact with the *original turn*, for example by the same QA questions answered by your own ear, and it needs its own measured miss rate.
UniversalNER (arXiv 2308.03279): a smaller model trained on a big model's labels beat that big model by 7–9 F1 at naming things in text. It supports training your own ear on Qwen-labelled made-up chat. TinyStories (arXiv 2305.07759): models under 10 million parameters wrote fluent, grammatical stories. It supports a small own mouth. Both **suggested** for us.
**As one sealed experiment.** Doc 24's stage S1 ear+mouth, trained twice from one seed, with and without the cycle loss. That is the only change. Pass: the cycle-trained ear reads fresh-panel facts at least 5 points better with the same or fewer wrong frames. **Proved wrong if** there is no gain in reading.

## Spelling: a flag, not a verdict

Not an experiment of its own; 261b's mixed-case guard already targets the 2 typos. Accepted from the review:
- an unfamiliar spelling is a reason to ask, not evidence that a value is false;
- keep the original text as evidence;
- never silently "correct" a name;
- a typo that happens to be another real word or name can still get through.

## Ideas I looked at and dropped

- Semantic entropy (Farquhar et al., Nature 2024): measures whether a model gives different *meanings* when sampled several times. Good for open questions, but our real wrong saves came from misreading the turn (typos, a check-question), which sampling would probably repeat. **Untested.**
- An LLM judge on its own: a new study that corrupted correct answers step by step (Gharsallah et al., arXiv 2609.15561, Sept 2026) found step-by-step pipeline checkers beat single LLM judges at spotting the damage. It backs splitting the checker into small separate questions (Ideas 1 and 2). **Suggested.**
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
