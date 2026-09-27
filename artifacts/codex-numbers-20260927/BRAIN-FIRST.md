# Starting hypothesis — 2026-09-27

SUGGESTED, not a neuroscience claim: a person solving the 24 game chooses a pair, computes an intermediate result, checks it against useful target decompositions (3 × 8, 4 × 6, 12 + 12), and backs up to try a different pair or operator when it fails. The useful lesson to test is learning reusable intermediate relationships rather than remembering a whole hand and one answer.

SHOWN in the existing code: the loop has a recurrent hidden state and can change its predicted answer across rounds. It has no explicit stack of candidate operations or failed branches and gets final-answer supervision, not intermediate reasoning supervision. UNTESTED: whether its hidden state nevertheless implements a useful revision strategy. Absence of an explicit search stack is not proof that it cannot learn one.

This note was written before selecting the candidate. The next step is diagnosis and a small fixed-env baseline on this M3 Pro, followed by a committed diagnosis and preregistration.
