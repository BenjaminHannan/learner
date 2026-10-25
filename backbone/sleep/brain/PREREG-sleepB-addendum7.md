# Sleep-B addendum 7: fix what limits memory now (written 2026-10-25 ~02:30Z, before any addendum-7 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), Week-2 world (sha256 70db7146...), tests and scoring code as
addendum 6, open-book rehearsal, training seed 1. Not the village model, not the card experiments.

## Why
Addendum 6 on Week-2 (seed 1, recall from weights only on 200 C2+C4 forward questions):

| arm | recall | two-hop | ARC-Easy | diary pooled |
|---|---|---|---|---|
| ab_ob control (Vast) | 52.5 | 6 | 92.2 | 84 |
| ab_ob_b2, 2x night work (PC) | 67.5 | 11.5 | 93.0 | 85.1 |
| ab_ob_win, b2 + guess + twisted scenes | 69.0 | 7.7 | 92.6 | 84.5 |
| ab_ob_winp, b2 + guess + plain paraphrases | 68.5 | 6.4 | 92.2 | 85.8 |

Guess + dopamine and twisted dreams add nothing on top of 2x work (W2, W3 fail; p = 0.74 and 1.0). The b2 run's diagnostics
point at two limits (suggested, one seed):
1. **Daytime notes miss facts.** The tagger finds 53% of fact mentions. Only 71 of 100 C2 facts and 83 of 100 C4 facts ever
   become eligible, so recall from weights cannot pass about 77%. Recall among eligible facts is already high (C4 81 of 83). The
   tagger often lists a fact about Sam alone ("Sam takes home 3200"), which the validity filter then drops, and skips the fact
   about two named people in the same message.
2. **Two-step dreams almost never survive.** About 95% of REM chain dreams fail the format check, because the prompt does not
   say which name goes in the question and which is the answer. 10 of 78 two-hop questions had their chain dreamed. Those were
   90% right; the other 68 were 0% right.

So this round tests one fix for each limit, and asks whether more work keeps helping.

## Code version
All four arms run on one code version, recorded in each result: this branch with PR #114's exact trainer speed patch
(lm_head only at target positions, length-sorted packing; its CPU selftest matches the old losses and gradients to 1e-6). The
2x-work arm is rerun on that version as this round's reference. Comparing it with addendum 6's b2 (same settings, older code,
different GPU) also measures the run-to-run noise of a paired test.

## Arms (Week-2, training seed 1, all at work scale s = 2 unless stated)
- **ab_ob_b2 (reference):** addendum 6's b2, rerun.
- **ab_ob_b4, "4x night work":** s = 4 (steps, dreams per item, item cap, REM chains and gist dreams all x 4). Nothing else changes.
- **ab_ob_tag2, "sharper daytime notes":** b2 with one new tagging prompt. It asks for facts that link two names written in
  the message (people, places, organisations, things), says that Sam, "I", "my friend" and common nouns are not names, and asks
  to skip small talk about Sam's own tasks. It keeps the same JSON format, the cap of 5, and the same validity checks after.
- **ab_ob_bridge, "guided two-step dreams":** b2 with one new REM chain prompt. For a pair of facts that share a name M, it names
  the start (one end), the answer (the other end) and the middle name M. It asks for one question that names the start, does not
  name M or the answer, and whose answer is the other end. The same format check, leak filter, diary check and caps apply after.
  Gist dreams are unchanged.

## Scoring
- All arms answer the same questions and are compared question by question against the ab_ob_b2 rerun.
- Paired test: exact two-sided McNemar on the questions where two arms disagree (`paired.py`).
- A gain is **shown** if it reaches its mark with p < 0.05. It is **suggested** if it reaches the mark with p >= 0.05.
- Result JSONs are pulled after each box stops itself; the PC returns them on a results branch.

## Pass marks (fixed now)
- **No harm (every arm):** ARC-Easy >= 87.6, and diary pooled >= reference - 5.
- **Noise floor (reported, not marked):** ab_ob_b2 rerun vs addendum 6's ab_ob_b2. Recall difference, disagreement and p.
- **D1 (more work keeps helping):** ab_ob_b4 - b2 >= +4 on C2+C4 recall. Prediction from the ceiling above: it fails, because
  C4 is near its eligibility ceiling. **Wrong if** b4 - b2 >= +8; then the ceiling reading is wrong. **Harm** if b4 < b2 - 4.
- **T1 (mechanism):** the tag2 tagger's mention recall >= 0.65 (b2: 0.53), with precision lower bound >= 0.5.
- **T2 (sharper notes become memories):** ab_ob_tag2 - b2 >= +5 on C2+C4 recall.
  **Wrong if** T1 passes but T2's gain is below +2.
- **B1 (mechanism):** ab_ob_bridge covers >= 30 of the 78 two-hop questions with a kept chain dream (b2: 10).
- **B2 (guided two-step dreams teach two-hop):** ab_ob_bridge - b2 >= +10 on two-hop accuracy (78 questions, paired).
- **B3 (no recall cost):** ab_ob_bridge recall >= b2 - 4.
  **Wrong if** B1 passes but B2's gain is below +5.
- **Reported, not marked:** reverse, changed-new, routine, integration, eligibility by class, chain yield per cycle, gate
  reverts, wall time and dollars per arm.

## Compute
- Ben's PC when free; otherwise the Vast offer with the most TFLOPS per dollar that has >= 20 GB VRAM (`tools/vast_pick.py`),
  never in China or California. One arm per box. Each box is destroyed after its JSON is pulled. A box whose job has not started
  within 20 minutes, or that has not finished a night within 50 minutes, is destroyed.
- Expected cost: about $0.35 to $0.80 per arm on an RTX 3090-class box, so about $2.50 for the round.
- A second seed is run only for an arm that passes, in the next round.
