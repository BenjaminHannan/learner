I'm building a small personal assistant that learns facts from plain-English chat and saves them in an explicit notebook (rows like owner | relation | value). A wrong save is worse than a refusal. I need a write gate whose mistakes are not the same mistakes as the reader it is checking, and a reader that doesn't drop facts from list sentences.

THE PIPELINE
1. An "ear" (a fine-tuned small seq2seq model) reads one chat turn and writes candidate facts, e.g. (Speaker, pet, Biscuit).
2. A speaker canonicaliser maps I / we / our to "me".
3. A rule "brake" drops facts with obvious leftover words.
4. A checker: a 27B instruction model (quantised Qwen, run locally, single GPU) gets the turn plus the fact rendered as a sentence, and is asked whether the turn explicitly asserts that exact claim (ambiguity = NO). Its score is P(YES). A fact is saved if P(YES) >= theta (sealed at 0.25).
5. Coming next: a mechanical guard that holds back any stored name mixing a Capitalised word with a lowercase non-particle word (aimed at typos).

THE RESULT (fresh blind test set, 150 turns: 122 key facts in statement turns, 25 turns that must save nothing, 40 questions)
- As scored: 9 wrong saves (target <= 1) and recall 95/122 = 77.9% (target >= 85%). Questions 39/40.
- On re-inspection, 6 of the 9 "wrong saves" had the right owner and right value but the relation "dog" or "cat" where the answer key said "pet"; the scorer accepted only "pet". These are now ruled correct from the next experiment on (a narrower relation counts as a hit), but the registered verdict stays FAIL. With them counted, recall would be about 101/122 = 82.8%.
- The 3 real errors: 2 chat typos that ended up inside a stored fact (checker P(YES) 0.85 and 0.68), and 1 fact saved from a check-question with no question mark, a "so ..." turn that should save nothing (P(YES) 0.37).
- The checker's 10 hold-backs were all correct (pronoun-after-relative claims, plans/goals, lowercase check-questions).
- Sweeping theta: recall is flat from theta 0 to 0.8; the as-scored wrong count falls 19 -> 7; at 0.95 recall is 60.7%. No theta meets both targets.
- The biggest recall loss is before the checker: when one sentence names several relatives ("X and Y are my sisters"-type turns), the ear writes only 4 of 16 facts.
- An earlier, easier panel (same kind of pipeline) showed other real meaning errors: pretend turns and plans saved as facts, check-questions without "?", a pronoun after "A's R is B and he ..." given to the wrong person, and "our" as a subject.

ALREADY TRIED OR PLANNED (don't re-propose these as your main answer): a logit-margin score (logit YES - logit NO); relation-specific claim renderers; counterfactual paired training of the ear; the 27B model as the full reader; a trained 360M verifier; question-answering round-trip checking (asked blind, answer must match); the mixed-case typo guard; count-then-list decoding; a separate "stating or checking?" dialogue-act question.

THE QUESTION
The checker approved every real error it saw, and most of what it held back was easy. I suspect it shares the ear's blind spots: it reads the fact rendered from the ear's output and judges "does the turn say this?", not "is the speaker asserting this as a new fact?". It also never sees the facts the ear missed. Design the write path (ear output format + gate) that gets to <= 1 wrong save in 150 fresh turns and >= 85% exact recall, on one 16 GB consumer GPU, at <= 800 ms median per turn, with no human in the loop. In particular:
(a) How do we measure and then reduce common-mode failure between reader and gate, i.e. make their errors close to independent? Can we estimate the gate's miss rate on errors the ear actually makes, rather than on synthetic corruptions?
(b) How should the gate handle facts the ear dropped (recall), not only facts it wrote?
(c) If the honest answer is that a separate gate cannot fix this and the reader itself must change, say so and say what the change is.

WHAT I NEED BACK
1. Your diagnosis, with at least two rival explanations and a cheap test that tells them apart using only development data (never the fresh blind set).
2. ONE concrete change to try first (one change per experiment), with the exact prompt(s) or model changes, the score, and how to pick any threshold without touching the blind set.
3. Pass marks fixed in advance, and the specific result that would prove your idea wrong.
4. Label every claim as shown (published or measured), suggested (published evidence in a different setting), or untested (your reasoning). Cite papers with arXiv IDs where you can.
5. A plain-language summary of 6-10 sentences for a high-school senior.

Keep this separate from any "small card experiments" or "village model" work: this question is only about the chat ear -> checker -> notebook pipeline.
