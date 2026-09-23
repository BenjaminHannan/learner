# Exp 114 WRONGs — verbatim (registered run 2026-09-22, 1.0 s)

Session gate exact: 19 taught, 6 people, 1 quarantine, 2 corrections,
1 forgotten, 0 sleeps, 26 turns. Router frozen
(c7762e22ae594b48bea4986e9cae32024835a6472a9714184dd612425dbbbef6).
Full records: `self114-results.json`. Zero hallucinated names/numbers in
all 100 answers: every WRONG below states live-state-true content aimed at
a neighboring intent (other-intent check pass), never an invented
name/number. The scope guard fired on none of the four.

## WRONG (4) — routed intent shown; asked intent in brackets

- W1 Q017 (asked C9-sleep-learning, routed C3): Q "Assuming at least one
  sleep cycle has completed, please give a full account of any knowledge
  acquired during it" A "The last thing you taught me was: Tom's job is
  sailor, in turn 22." ("Assuming" is a hypothetical framing word outside
  the frozen guard set {suppose, imagine, pretend, hypothetical, what if};
  the one in-scope miss of this experiment.)
- W2 Q023 (asked C12-forgotten-count, routed C11): Q "forgotten tally?"
  A "I forgot: Mira's job is teacher. You asked me to forget it in turn
  23. The old row is kept but retired." ("tally" is not in the inherited
  exp-105 count-guard vocabulary {how many, how much, count, number of};
  a synonym gap in the 105 machinery, unchanged by this experiment.)
- W3 Q053 (asked C27-web-source, routed C6): Q "That quarantined internet
  row — cite its origin for me" A "Yes. I hold 1 quarantined web row. I
  filed it but I do not believe it." ("cite"/"origin" score no C27
  keyword; inherited keyword-overlap misfire, unchanged by this
  experiment.)
- W4 Q074 (asked NEW114-04, routed C4): Q "What time on the clock did I
  teach you the very first fact?" A "The first thing you taught me was:
  Mira's mother is Ana." (C4 content for a new intent asking for a time;
  no scope trigger present; unchanged 105 machinery.)

## Not WRONG (96)

17 CORRECT (all on existing intents). 79 HONEST_DECLINE: 50 on existing
intents (46 by the inherited margin/threshold, 4 by the new scope guard —
Q046 imagine-hypothetical, Q059 she-pronoun, Q066 Tom, Q069 she-pronoun —
all four already declining under the 105 router, so the guard cost zero
K2 points), 19 on new intents, 10 on trick. The decline sentence used is
"I do not know that from what you taught me. I have no record of it, so
I will not guess." Every decline states no name/number outside live state.
