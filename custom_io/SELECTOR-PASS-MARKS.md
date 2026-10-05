# Selector test: can a coach that sees the members' answers use the right answers the team already has?

Proposed by GPT (Ben relayed it 2026-10-05, 3:39 PM ET; prompt: `reviews/gpt-swarm-team-2026-10-05.md`). Written before any
selector was trained. Code: `custom_io/selector.py`.

## Why this test

Shown (re-scored solo screen, all 7 recipes, seeds 100/101): on `variant` the three-member team B2 + plain_tf_steps +
plain_tf has a union (right for at least one member) of 42.2 / 41.9 against B2 alone 32.3 / 34.6, but a plain majority vote
gets only 32.7 / 29.4. The right answers exist; nothing picks them.

## Setup

- Members, frozen: the solo screen checkpoints B2, plain_tf_steps, plain_tf at seed 100 (team s100) and at seed 101
  (team s101). GPT suggested the OFF checkpoints of the running team screen; the solo runs are the same recipe trained
  independently and exist now. No member weight, decoding rule or number of attempts changes.
- Practice data: 16,000 fresh questions + 4,000 validation questions from the practised families
  (`skills_curriculum.build.iter_train`, seed 2026100502). Held-out pieces are excluded by the curriculum's fixed split hash;
  any prompt already in the seed-1 train file or any dev split was dropped (1,421 dropped). These 20k labelled questions are
  extra supervision and count as such in any later whole-system claim.
- Each member's greedy answer is cached once for every row (fresh and dev).
- Selector: the team coach's encoder (0.44M). Input = three member-tagged answer fields of 8 characters each, then the
  question. Output = one right/wrong logit per member, trained with binary cross-entropy on the members' actual exact-match
  results (all-right and all-wrong rows kept). Team answer = the member with the highest logit; ties go B2, then
  plain_tf_steps, then plain_tf.
- **aware (test):** the answer fields hold the members' answers (padded to 8).
- **blind (control):** identical layout, every answer field is one fixed mask symbol. Same init, same batches, same steps.
  The only difference is whether the selector can see the proposed answers.
- Training: 2,000 updates, batch 256, AdamW (lr 1e-3, 100 warm-up, cosine to 10%, weight decay 0.01), clip 1.0. Validation
  every 200 updates; keep the checkpoint with the best validation team score (ties keep the earlier one). The dev splits are
  scored once, after that choice.

## Marks (two-seed screen: teams s100 and s101)

Primary: team exact on `variant`. References: the blind selector and the frozen B2 member of the same team.

- **PASS (go to 6 fresh paired member seeds):** aware beats blind AND beats B2 on `variant` by >= 3.0 points each (mean of
  the two teams), with a positive gain against both on both teams, and aware's mean `in_dist` is no more than 2.0 points
  below either reference.
- **STOP this recipe:** the mean `variant` gain against either reference is under 1.0 point, or aware loses to either
  reference on either team, or the `in_dist` guard fails.
- **Inconclusive:** anything between; it does not justify more members.
- No void rule: a selector that keeps choosing B2 is a valid negative result.

Also reported: rescues (B2 wrong, team right) and harmful overrides (B2 right, team wrong) as % of rows; the union (the
ceiling: a selector cannot fix a row every member gets wrong); picks per member.

Noise rule: no claim from two teams alone. A pass is only worth a 6-seed confirm, and the real bar afterwards is a single
~10M B2.
