# Sleep-B addendum 8: notice more facts, more two-step dreams, and a second seed (written 2026-10-25 ~06:20Z, before any addendum-8 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), Week-2 world (sha256 70db7146...), tests, scoring and code
version as addendum 7 (PR #114 trainer), open-book rehearsal. Not the village model, not the card experiments.

## Why
Addendum 7 (Week-2, seed 1, recall from weights only on 200 C2+C4 forward questions, paired McNemar):
- 4x night work (ab_ob_b4): recall 76.0, +9.0 over 2x work (67.0), p = 0.0014. That is shown.
- 4x work is close to the note-taking ceiling. The day tagger finds 53% of fact mentions, so only 72 C2 and 87 C4 facts become
  eligible, and the most recall can reach is 79.5.
- The names-only tagging prompt (ab_ob_tag2) halved the tagger's recall (0.25) and cost 16.5 points. In its raw outputs, the
  small model kept listing "Sam ..." triples even for two-name facts.
- Guided two-step dreams (ab_ob_bridge, at 2x) gave two-hop 19 vs 11.5. That is unpaired, below the +10 mark, and the JSON was
  lost, so the chain-dream count is unknown. At 4x work, two-hop fell to 5.1 (6 of 78 dreamed).
- Every Week-2 result so far uses training seed 1.

## Reference
ab_ob_b4, seed 1, from addendum 7 (`results_a7/result_ab_ob_b4.json`). The new arms only add code paths. Every existing arm
stays bit-identical, which is checked by the selftest and a CPU smoke, so that run is a valid paired reference. Its
noise floor is known from addendum 7: two runs with identical settings differ by -0.5, with p = 1.0.

## Arms (Week-2, work scale 4)
- **ab_ob_b4_names, "re-read the day for names" (seed 1):** after the normal day tagging, a second pass over the same day's
  turns.
  - Candidate names are words that appear with a capital letter somewhere other than the start of a sentence in the diary so far.
    Sam, "I", weekdays, months and a short list of common capitalised words are left out.
  - For each turn, take up to 6 pairs of candidates that both occur in the turn (case-insensitive) and that no existing item
    already links.
  - Ask the model one short question per pair: does this message say how A and B are related? If yes, give the relation in
    1-4 words; otherwise answer "no".
  - Each "yes" becomes a candidate triple (A, relation, B). It goes through exactly the same validity and in-turn checks as day
    tagging, and is added to the same turn's tag record, so the tagger diagnostics include it.
  - Nothing else changes.
- **ab_ob_b4_bridge, "guided two-step dreams at 4x" (seed 1):** b4 with addendum 7's bridge prompt (start, answer and middle
  name given). All checks after generation are unchanged.
- **ab_ob_b2 and ab_ob_b4, seed 2:** the 2x vs 4x comparison repeated with training seed 2 (same world).

## Scoring
Paired, exact two-sided McNemar on per-question rows (`paired.py`). A gain is **shown** if it reaches its mark with p < 0.05,
and **suggested** if it reaches the mark with p >= 0.05. If a JSON cannot be pulled, that arm is unpaired and at most
suggested; the box is kept stopped and the pull retried first.

## Pass marks (fixed now)
- **No harm (every arm):** ARC-Easy >= 87.6, and diary pooled >= reference - 5.
- **S1 (4x work beats 2x on a second seed):** seed-2 b4 - seed-2 b2 >= +4 on C2+C4 recall. **Wrong if** it is <= 0.
- **N1 (mechanism):** the names arm's tagger mention recall >= 0.65 (b4: 0.533), precision lower bound >= 0.5, and
  eligible C2 + C4 >= 175 (b4: 159).
- **N2 (more facts noticed become memories):** ab_ob_b4_names - b4 >= +4 on C2+C4 recall.
  **Wrong if** N1 passes but N2's gain is below +1.
- **G1 (mechanism):** ab_ob_b4_bridge covers >= 20 of the 78 two-hop questions with a kept chain dream (b4: 6).
- **G2 (guided two-step dreams teach two-hop):** ab_ob_b4_bridge - b4 >= +10 on two-hop (78 questions, paired).
  **Wrong if** G1 passes but G2's gain is below +5.
- **G3:** ab_ob_b4_bridge recall >= b4 - 3.
- **Reported, not marked:** reverse, changed-new, routine, eligibility by class, the names pass's counts (pairs asked, yes
  answers, items added, of which match a true fact), chain yield, reverts, wall time and dollars.

## Compute
- RTX 5090 boxes, preferring hosts that already ran these jobs cleanly. Otherwise the best TFLOPS per dollar with >= 24 GB
  (`tools/vast_pick.py`), never China or California, plus Ben's PC if it is free.
- A box that is not running within 10 minutes is dropped. Each JSON is pulled after the self-stop, and only then is the box
  destroyed.
- Expected: about 1.1 h per 4x arm and 0.55 h per 2x arm on a 5090, so about $2 for the round.
