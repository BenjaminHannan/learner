# Exp 122 WRONGs — verbatim (registered run 2026-09-22, 3.7 s)

Session gate exact: 19 taught, 6 people, 1 quarantine, 2 corrections,
1 forgotten, 0 sleeps, 26 turns. Router frozen
(ce11b15b516d75097fc357760d3c9928a1aa5b14136a24e7109a4e6f4d162112),
head frozen (5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25).
Full records: `self122-results.json`. Zero hallucinated names/numbers in
all 100 answers: every WRONG below states live-state-true content aimed at
a neighboring intent (other-intent check pass), never an invented
name/number. The scope guard fired on none of the three (no scope trigger
present by design); all three cleared the frozen confidence bar
(tau=0.6, mu=1.5). Existing intents: 0 WRONG of 70.

## WRONG (3) — all on new intents; routed intent shown

- W1 Q078 (new intent, routed C15): Q "How confident are you, as a
  percentage, that Mira lives in Paris?" A "Yes. You taught me Mira's city
  is Paris. It replaced Oslo. Nothing you taught contradicts it." (A
  percentage-confidence question about Paris; the C15 certainty training
  neighbours over-attracted it.)
- W2 Q086 (new intent, routed C5): Q "Translate everything you know about
  Mira into French for my cousin." A "You did, in turn 21, when you
  corrected Oslo to Paris. Your correction replaced the old row; I kept
  both." (A translation task borrowing Mira vocabulary; answered with C5
  provenance content.)
- W3 Q089 (new intent, routed C29): Q "How many distinct relation types
  appear across your stored facts?" A "0 of my facts came from rules."
  (A metadata-counting question; answered with rule-count content that
  matches the C28 value check.)

## Not WRONG (97)

44 CORRECT (all on existing-C intents). 53 HONEST_DECLINE: 16 on
existing-C (low-confidence oblique phrasings), 10 on existing-D, 17 on new
intents, 10 on trick. The decline sentence used is "I do not know that
from what you taught me. I have no record of it, so I will not guess."
Every decline states no name/number outside live state.
