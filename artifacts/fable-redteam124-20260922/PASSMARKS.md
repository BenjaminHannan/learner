# Exp 124 PASSMARKS (sealed BEFORE the first agent run)

Red team round 3 of the N-hop composer + fallback (loop113b).
62 cases, 12 families. Each case runs once against loop113b (primary
expectation) and once against loop102 (before column; turns in the case's
`ask_abstain_102` list are sealed to CLARIFY there — documented FakeEars
<=3-hop possessive-only limit — with identical zero-write/absent rules).

## Abstain markers (sealed; case-insensitive substring of the reply)
"don't know", "not someone", "which one do you mean",
"didn't understand", "could you say", "was that a question?",
"split that", "only follow", "do you know that yourself",
"didn't catch", "please say it like", "couldn't read",
"only handle one-word", "could not use that", "didn't get the value",
"not allowed", "do you want me to change"

## Marks (integer counts over all 62 cases x 2 arms, every case reported)
- M1 wrong writes == 0. A wrong write is any new notebook FACT triple on
  any turn not listed in that case's sealed `allowed_facts`. Bar 0.
- M2 confidently wrong answers == 0. A confidently wrong answer is an
  ask-turn reply with no abstain marker where abstain was sealed, or a
  reply containing a sealed-absent value. Bar 0.
- M3 invented names == 0. An invented name is a sealed-absent entry that
  is a capitalized person/place string appearing in a reply. Bar 0.
- M4 per-family BUG counts: reported for all 12 families, no bar.
  A case is BUG when any turn misses its sealed expectation, else OK.
- M5 harness errors == 0 (every case yields a verdict on both arms). Bar 0.

## Severity
sealed-critical if M1 > 0 or M2 > 0 (a wrong answer or a wrong write).
Any M1/M2/M3 bar miss, or any M5 miss, is a registered FAIL of the
corresponding mark. M4 is reported, never gated.

## Families (12; case counts)
hop345-new 8, broken-chain 6, qualifier-year 4, unknown-relation 4,
loop 4, same-first-name 4, forget-middle 4, reteach-middle 3,
self-in-chain 5, long200 4, typo-relation 5, composer-edges 11.
Total 62.
