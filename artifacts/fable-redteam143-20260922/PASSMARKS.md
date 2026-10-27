# Exp 143 PASSMARKS (sealed BEFORE the first registered run)

QUESTION-side red team vs loop132
(`scripts/fable_loop132_agent.py` + `scripts/fable_qrewrite132.py` on top of
loop121). No existing file is edited by this experiment; all new files carry
the `fable_redteam143_` prefix.

124 cases (122 FRESH + 2 confirm of doc-124 findings 1/2, flagged
`"confirm": true` and excluded from the novelty count). Each case = one fresh
Loop132Daemon dir, 2-6 teach sentences through the mailbox first, then one
question through the mailbox; the outbox reply is the verdict input.
Every seed/case reported, never averaged (single deterministic run per case).

## Abstain markers (sealed; case-insensitive substring of the reply)

"don't know", "not someone", "which one do you mean", "didn't understand",
"could you say", "was that a question?", "split that", "only follow",
"do you know that yourself", "didn't catch", "please say it like",
"couldn't read", "only handle one-word", "could not use that",
"didn't get the value", "not allowed", "do you want me to change",
"i didn't catch anything", "i can take one fact at a time",
"i only save facts", "i wasn't waiting for an answer"

## Verdict rules (sealed; mechanical, from the case file only)

- HARNESS-ERROR: exception on any turn, or any teach reply that is not
  `Saved:` / `I already have that.` ("Saved:" acks are never answers).
- Expected "abstain": abstain marker -> OK, else WRONG-ANSWER.
- Expected answer: normalized extracted value (text after final " is "/" are ",
  lowercased, punctuation/articles stripped) equals sealed answer -> OK;
  abstain marker -> MISSED; else WRONG-ANSWER.
- Before any WRONG-ANSWER is claimed, the sealed expectation is re-read by
  hand (doc 124 had 48 expectation errors).

## Marks (integer counts over all 124 cases, every case reported)

- M1 harness errors == 0 (every case yields a verdict). Bar 0.
- M2 WRONG-ANSWER cases: reported per case, grouped into root-cause classes
  with responsible code (file:line) + one-line single-change fix each. No bar
  (finding bugs is the job); classes ranked by normal-user likelihood.
- M3 MISSED cases: reported per case (coverage). No bar.
- M4 confirm cases A1/B1 reproduce doc-124 findings 1/2 (both WRONG-ANSWER).
  Falsified by any other verdict on A1/B1.

## Families (fresh case counts; confirms extra)

one-hop 6, two-hop 12, three-hop 8, four-hop 6, four-hop-island-prefix 1,
of-phrasing 6, relative-clause 8, passive 5, robust 12, never-taught 10,
unknown-relation 6, yes-no 6, negated 5, unknown-entity 5, look-alike 5,
post-correction 7, ambiguity 5, qualifier 5, chain-end 5.
Fresh total 122. Confirm total 2 (confirm-broken-prefix 1, confirm-qualifier 1).
