# Scoring plan for the uncle's questions

Status: SUGGESTED. Marks below are written BEFORE any run, per rules.md, and are not changed after a score is seen. Item 8 of the roadmap ("ready for uncle") depends on item 1 (joined model) existing first, so nothing here can run yet.

## What is scored
The joined model (reader -> learned reasoner -> talker, with notebook) and the same-size rivals from the goals page: MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B, on the same sealed questions, same session, same settings, answers shuffled and unlabelled (which model wrote which answer hidden from the judges).

## Who judges
1. **The uncle (the real judge).** He sees the question, then the answers side by side in random order, model names hidden, and for each question picks the answer that helps most, or "none". This is the number that matters for "ready for my uncle". ~10 minutes for 30 questions; he can skip any he can't judge.
2. **Blind non-Claude second judge** (GPT via Codex or GLM, model name hidden from it), on the same shuffled pairs, using the same three grades below. Used to check the uncle's picks are not noise. Claude does not judge and does not write any of the data. Claude only runs the counting script.
3. Disagreements between judges are reported as a count, never averaged away.

## Grades per answer (uncle and second judge)
- **Helpful**: he would use it as is or with small edits.
- **Wrong or made up**: contains a claim that is false, or invents a fact/number/source.
- **Says it doesn't know**: honestly says it can't answer or needs a record it doesn't have.
- **Unhelpful**: on topic but useless.

## How "I don't know" counts
- On a question that needs information the model was never given (his records, a customer's history, today's price), "I don't know / I'd need X" **counts as correct** and scores the same as a good answer. A confident guess counts as wrong.
- On a question the model could answer, "I don't know" counts as a miss (same as unhelpful), not as a wrong answer.
- Which questions need unseen records is decided by the uncle (one tick per question: "needs my records"), before he sees any answers.
- Report separately: helpful count, wrong-or-made-up count, honest-don't-know count, "x of 30" each. Never fold them into one score. Making things up is reported on its own line.

## Comparison
- Per question, uncle's pick counts: joined model wins / a rival wins / none, as "x of N". Also each model's helpful count and wrong-or-made-up count.
- Both size counts reported (biggest single part, and total ~2B), as on the goals page.
- With only about 30 questions, differences of a few are noise. Report the raw counts, no percentages, and say "suggested" unless a gap is at least 6 of 30 in the same direction for the uncle and the second judge.

## Pass marks (fixed now)
- PASS for "ready for uncle": on the questions he judges, the joined model has helpful >= the best rival's helpful, and wrong-or-made-up count is no higher than the best rival's, and the uncle's own answer to "would you use this?" is yes for at least 10 of 30.
- Proof it wrong: the joined model has fewer helpful answers than any rival, or more made-up answers than any rival. Then it is NOT ready, and the report says so.
- One run only per build. Re-running after a change needs a new sealed set.

## Not part of this
Small card experiments and the village model are kept out of any claim. Scores from this set are never used for training or tuning (see 02).
