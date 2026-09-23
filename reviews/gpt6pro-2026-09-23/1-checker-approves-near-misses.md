I'm building a small personal assistant that learns facts from plain-English chat and saves them in an explicit notebook (rows like owner | relation | value). A wrong save is worse than a refusal. I need your help with one hard problem: a verifier that approves "almost right" facts.

THE PIPELINE
1. An "ear" (a fine-tuned small seq2seq model) reads one chat turn and writes candidate facts, e.g. (Speaker, pet, Biscuit).
2. A speaker canonicaliser maps I / we / our to "me".
3. A rule "brake" drops facts with obvious leftover words.
4. A checker: a 27B instruction model (quantised Qwen, run locally, single GPU) gets the turn plus the fact rendered as a sentence, and is asked whether the turn explicitly asserts that exact claim (ambiguity = NO). Its score is P(YES). A fact is saved if P(YES) >= theta (sealed at 0.25).

THE RESULT (fresh blind test set, 150 turns: 122 gold facts in statement turns, 25 turns that must save nothing, 40 questions)
- Wrong saves: 9 (target <= 1). Exact fact recall: 95/122 = 77.9% (target >= 85%). Questions: 39/40 correct. Checker held back 10 facts, all correctly.
- The 9 wrong saves, by kind: 4 gave a pet to the wrong owner (2 from "our"/plural-owner turns, 1 from an appositive (a name set off by commas after a relative), 1 plain speaker-pet); 2 corrections kept the old value; 2 had a chat typo inside the saved value; 1 was saved from a turn that should save nothing (P = 0.37).
- 8 of the 9 wrong saves had P(YES) >= 0.68; most >= 0.94.
- Sweeping theta: recall is flat at 77.9% from theta 0 to 0.8 while wrong saves fall only 19 -> 7; at theta 0.95 recall is 60.7% with 4 wrong; no theta meets both targets.
- On an older, easier development panel the same checker kept 100/112 facts with 6 wrong saves. With the literal prompt wording, <= 1% wrong needed theta 0.9 and recall fell to ~51%; a reworded prompt gave 91.9% recall at 0.95% wrong on development data (and then failed on the fresh set).
- Separately, when one sentence names several relatives, the ear writes only 4 of 16 facts. That is a recall problem before the checker; mention it only if your design fixes both.

ALREADY TRIED OR PLANNED (don't re-propose as your main answer): a logit-margin score (logit YES - logit NO); relation-specific claim renderers; counterfactual paired training of the ear; the 27B model as the full reader; a trained 360M verifier; question-answering round-trip checking ("whose pet is Biscuit?" asked blind, answer must match); a spelling rule for values; count-then-list decoding.

THE QUESTION
Why does a strong entailment checker confidently approve near-miss facts (right value, wrong owner; right owner, stale value), and what verifier design would get wrong saves to <= 1 in 150 fresh turns while losing no more than 3 true facts compared with the current checker? It must run on one 16 GB consumer GPU at <= 800 ms median per turn, with no human in the loop. Go beyond the planned list: e.g. what exactly fails in the model's computation, contrastive or minimal-pair scoring, structured slot-by-slot verification, disagreement between independent readers, or anything better. If the honest answer is that no single verifier can do this and the architecture must change, say so and say what the change is.

WHAT I NEED BACK
1. Your diagnosis of the failure, with at least two rival explanations and a cheap test that tells them apart using only the development data (never the fresh blind set).
2. ONE concrete change to try first (one change per experiment), with the exact prompt(s) or model changes, the score, and how to pick any threshold without touching the blind set.
3. Pass marks fixed in advance, and the specific result that would prove your idea wrong.
4. Label every claim as shown (published or measured), suggested (published evidence in a different setting), or untested (your reasoning). Cite papers with arXiv IDs where you can.
5. A plain-language summary of 6-10 sentences for a high-school senior.

Keep this separate from any "small card experiments" or "village model" work: this question is only about the chat ear -> checker -> notebook pipeline.
