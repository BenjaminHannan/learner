# 360 grammar roadmap: from 87% to 99%+ (grammar thread, 2026-09-25 ~02:25 UTC)

Goal (Ben's project goal): 99%+ of replies grammatical with no simple mistakes, judged by two blind graders that
catch planted errors. Today: 336 M7 87.0% / 55.9% (VERIFY-336.md); 338 chat 95.8% / 95.0% (VERIFY-338.md).

## Where the misses come from (evidence)
| Source | Share of replies | Clean today | Evidence |
|---|---|---|---|
| Rule agent's fill-in lines ("Saved: ...", "Just to check: ...?") | ~12% in 338, more in 336 | 48-83% | VERIFY-338 (34/41, 33/41); DEV strict grader 118/247 |
| Reader nonsense frames inside those lines ("is your granddaughter this?") | ~5% of fill-in lines on DEV | ~0% | DEV grader, 2026-09-25 |
| The 1B's own chat / creative replies | ~75% | ~97% | VERIFY-338 (289/296, 287/296) |

## Steps (one change each, sealed marks, fresh blind bank, blind Opus graders)
1. **gram-360: render the slots** (running, rent-360-gram; also arm G of 336b). Names capitalised, no underscores,
   possessive pronouns, lists, "?" on requests. Rules on purpose: it must never change a letter of a stored name.
   Pass: fill-in lines >= 90% and >= +20 points, 0 score changes.
2. **gram-361: a learned fluency check on fill-in lines.** The 1B (already loaded) scores each fill-in sentence
   (average token log-probability, a learned "does this sound like English" signal, like a listener noticing a
   garbled sentence). A confirm or save line whose frame scores below a threshold fixed on DEV is not voiced;
   the agent says its existing honest "I didn't catch that as a fact" line instead. Affects only lines built from
   nonsense frames. Marks: fill-in lines >= 98%; wrong saves not higher; answerable-right not lower.
   Built and tuned on DEV only; CPU prototype first (no GPU).
3. **gram-362: grammar-aware pick among the 1B's samples.** 338 already samples several replies and keeps the
   first that passes its safety guards. Add one more learned check: the 1B's own yes/no judgement "Is this reply
   grammatical English with no mistakes?" (logit margin), keeping the best-scoring safe candidate. Marks: 1B
   replies >= 99% by both graders; helpfulness judge not lower; 0 new invented facts.
4. **gram-363: the joined check.** 330c + 360 + 361 + 362 on a fresh blind bank: all replies >= 99% by both
   graders (the 336 M7 measure). If it passes, it goes to the month-end thread as a 0.1 candidate.
5. **Later (own-model line): the own mouth.** Premonition's own decoder must reach 99% itself; steps 2-3 give it
   a learned grader to train against (reward = the fluency check), not hand rules.

## Order and compute
- Tonight: verify gram-360; build and DEV-test 361 on CPU (the 1B scores short sentences fast enough on CPU);
  prepare 362 on DEV. GPU runs go to BensPC through the director's queue (no rentals tonight).
- Each step is registered before its run; a FAIL gets one diagnosis-driven follow-up; a registered FAIL stays FAIL.
- Coordination: the month-end thread owns 0.1 and 336b; any passed step is offered there through the coordinator.
