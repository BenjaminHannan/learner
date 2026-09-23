# 264: question-answering checker (director, 2026-09-23)
Ben's pick (research thread, 02:36): replace the YES/NO entailment checker with targeted questions, each hiding the part being checked. His safeguards are adopted: allow NOT STATED and AMBIGUOUS, allow several answers, and test wrong relations. Two matching answers are NOT proof of correctness. Round-trip agreement is never permission to write.

The one change (on 261b's registered arm A: canonicaliser + brake + span guard, with the checker swapped out):
For each TEACH frame (S, R, V) the brake keeps, ask Qwen3.8-27B three separate questions at temperature 0 with thinking off. Each question sees only the message and the parts named:
- Q-value (V hidden): "Message from the speaker: «turn». According to this message, stated as a real, current fact (not asked, pretended, planned, wished, denied, or replaced), what is <S>'s <relation words>? Answer with the exact words from the message. If several, list them separated by ' | '. If the message does not state it, answer NOT STATED. If it is unclear, answer AMBIGUOUS."
- Q-owner (S hidden): the same frame of words, "whose <relation words> is <V>?". The speaker is answered as "the speaker".
- Q-relation (R hidden): "How is <V> related to <S> in this message? Answer with one to three words, or NOT STATED or AMBIGUOUS."
Save iff V (case- and space-normalised) is one of Q-value's answers, AND S is one of Q-owner's answers ("the speaker" matches "me"), AND Q-relation's answer maps to R through relation table v2 names, aliases or narrower. Otherwise hold back as UNSURE. No threshold, so nothing is tuned; dev is used only to debug prompt wording, and every wording change is logged. The span guard stays after it.
Report wrong saves per saved fact AND per turn, plus recall, with every arm on the same scorer (Ruling 1 included).
"our/we" owners are excluded from panel 264 (Ben ruled they must ask whose; that is a separate experiment, 265).
Certification is separate: panels like 264 are discovery panels, and certifying uses the 600-turn fixed set (to be written).
