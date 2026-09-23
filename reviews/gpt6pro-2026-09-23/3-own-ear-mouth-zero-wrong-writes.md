Please design an architecture and training plan for a small from-scratch language system that turns chat into notebook facts and facts back into English, where wrong notebook writes are prevented by the design, not only filtered afterwards.

THE PROJECT
A personal assistant that starts knowing nothing. It learns facts a user teaches in plain English, stores them in an explicit notebook (rows owner | relation | value; taught facts never overwritten by inferences; inverses computed at answer time), reasons over them with a small learned lookup reasoner (~79,000 parameters, multi-hop, abstains when a fact is missing), and replies in English. Today the "ear" (English -> facts) is a fine-tuned borrowed encoder and the "mouth" (facts -> English) is a borrowed 360M decoder. The owner wants the final system to be his own architecture and his own weights, trained from scratch on one RTX 5070 Ti (16 GB), with a total cloud budget of $30. Using a big model's generated text as training data is allowed if stated honestly; borrowing its weights is not.

TARGETS
- 0 wrong notebook writes, certified below 1% (about 300 fresh test turns with 0 errors).
- 99%+ grammatical replies, no simple mistakes.
- Beat an equal-size plain transformer chat model (same data, same parameter count) on: two-hop questions, reversal (asking the inverse of a taught fact: taught "Ada is Bo's mother", asked "Who is Ada's child?"), saying "I don't know" for untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style).

WHAT WE KNOW
- The borrowed ear plus a 27B entailment checker made 3 real wrong saves in 150 fresh turns: 2 chat typos stored inside a fact and 1 fact saved from a check-question with no "?". The checker approved all 3. (6 more were scored wrong only because the answer key wrote "pet" where the ear wrote "dog" or "cat".) An earlier panel showed other kinds too: pretend turns and plans saved as facts, a pronoun given to the wrong person, "our" as a subject.
- When one sentence names several relatives, the ear writes only 4 of 16 facts.
- An earlier internal design proposes: a ~33M-parameter system; a 6-layer width-384 encoder (ear) and a 6-layer width-384 decoder (mouth) that sees only a structured "thought" vector (sentence kind, who, relation, value slots, flags, a 256-number free gist); names can reach a reply only by being copied from a thought, never generated; training on ~1.2B tokens of simple-English data (TinyStories-style stories and dialogues) plus generated teach/ask dialogues with exact labels; a 29M plain transformer as the comparison model.
- The notebook plus reasoner already answers two-hop, reversal, abstention and single-edit multi-hop questions exactly when given clean structured input (200/200 on an internal benchmark). The weak point is reading English into clean facts.

THE HARD QUESTION
How should the own ear be built so that, by construction, it cannot write a fact whose owner, relation or value is not grounded in the turn? For example: pointer-only value and owner slots over the input tokens, set-structured output with an explicit fact count, a learned "no fact" option per slot, cycle consistency with the mouth (facts -> sentence -> facts must be a fixed point), an energy or reconstruction score as an internal checker, or something better. Which of these actually prevents the error kinds above, and which only moves them? What training data and curriculum make it robust to plural owners, appositives, corrections and typos without memorising templates? How should the comparison with the equal-size plain transformer be set up so it is fair and not won by the notebook alone?

WHAT I NEED BACK
1. A concrete design (layers, sizes, output format, losses, data mix with token counts, compute estimate on one 16 GB GPU), and why each part stops a named error kind.
2. A staged plan where each stage is ONE change against the previous stage, with pass marks fixed in advance and the result that would prove that stage wrong.
3. The strongest objection to your own design, and a rival design you considered.
4. Label every claim as shown (published or measured), suggested (published in a different setting), or untested (your reasoning). Cite papers with arXiv IDs where you can.
5. A plain-language summary of 6-10 sentences for a high-school senior.

This is only about the chat assistant (ear, notebook, reasoner, mouth). Keep it separate from any "small card experiments" or "village model" work.
