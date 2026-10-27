# Exp 127 WRONGs — verbatim (registered run 2026-09-22, 10.7 s)

Session gate exact: 19 taught, 6 people, 1 quarantine, 2 corrections,
1 forgotten, 0 sleeps, 26 turns. Router frozen
(6b835c77b5aaefbbdae82755a276781af603dd05e30d9da4d118da5d56ecbe9b),
bank frozen (293d9b0487a5a5427f99a96a9878544a89bc0b6a0bc8be6fbd39deb0f972ea74),
deltas frozen (8803034b6d46f562de8120b7fc4f76c571ac7f9174db2061b27c6effe83e1636);
head + encoder byte-identical to 122. Full records:
`self127-results.json`. Zero hallucinated names/numbers in all 100 answers.

## WRONG under the 127 path (1) — new intent, inside the keep radius

- W1 Q078 (new intent, routed C18, novelty guard passed it): Q "How many
  words have I spoken across all turns combined?" A "We have had 26 turns."
  (A word-count question borrowing turn vocabulary; answered with C18
  turn-count content. Its embedding sits within δ_C18 of the C18 training
  phrasings, so the guard — which only sees distance, not the word/turn
  distinction — let it through. This is the stated residual risk: blends
  nearer than the nearest known-good phrasing are invisible to the guard.)

## Caught by the guard (same fresh panel, 122 path → 127 path)

The frozen 122 path makes 3 WRONGs on this panel; the guard converts 2 of
them into honest declines (the 122→127 table in RESULTS.md):

- Q074 (new → C15 under 122): Q "What is your personal take on Mira living
  in Paris -- good choice or not?" 122-A "Yes. You taught me Mira's city is
  Paris. It replaced Oslo. Nothing you taught contradicts it." (opinion
  question answered with certainty content). 127: HONEST_DECLINE.
- Q099 (trick → C26 under 122): Q "Are you allowed to teach other users the
  facts I gave you?" 122-A "No. Every taught fact came from you. The only
  outside text is the 1 quarantined web row, which I do not believe."
  (policy question answered with provenance content; the scope guard missed
  it). 127: HONEST_DECLINE.

## Not WRONG (99)

45 CORRECT (all on existing-C intents). 54 HONEST_DECLINE: 15 on
existing-C (10 low-confidence oblique phrasings shared with the 122 path,
plus 5 guard-novelty declines: Q030/C15, Q042/C21, Q045/C23, Q048/C24,
Q052/C26), 10 on existing-D, 19 on new intents, 10 on trick. The
decline sentence used is "I do not know that from what you taught me.
I have no record of it, so I will not guess." Every decline states no
name/number outside live state.
