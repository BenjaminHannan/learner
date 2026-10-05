# Team screen: can small models that learn in different ways be trained together?

Ben's idea (2026-10-05, 2:35 PM ET): a swarm of small models on a shared base, trained to work together and to learn
skills in different ways. His follow-up (3:01 PM ET): "see if they can be trained together". Written before any team run.

## What already exists (no training, re-scored 2026-10-05)

- 6 seeds of the confirmed planner model (PR #38, CRDC) voting: new questions of practised kinds 89.7% alone, 93.9% as a
  vote; the twisted versions (`variant` split) 49.2% alone, 53.7% as a vote; all six miss the same 95 of 280.
- The solo from-scratch screen (seeds 100, 101; 24k updates, batch 256): B2 variant 32.3 / 34.6, in_dist 89.0 / 90.1;
  plain_tf variant 21.2 (s100); a 10.8M plain_tf (02-calib-long) variant 21.7, in_dist 76.0.

## The test (`custom_io/team.py`)

Members: B2 (ledger + copy: writes a program, exact executor runs it), plain_tf_steps (writes worked steps), plain_tf
(answers directly). Each built right after `torch.manual_seed(seed)`, so it starts bit-identical to its solo run. A coach
(char encoder, 0.44M, head starts at zero = uniform) reads each question and scores the members. Each step draws a pool
of 512 training rows; every member trains on 256 of them with its own loss, optimizer and schedule (same as train.py).

- **ON (test):** the coach decides who practises what: member i's 256 rows are drawn from the pool with
  prob = 0.5 / 512 + 0.5 * coach_i(row) / sum(coach_i).
- **OFF (control):** each member's 256 rows are drawn uniformly from the pool (independent training).
- Both arms: every 8 steps all members answer 64 pool rows; the coach learns who was right. 24,000 steps.
- The one change between arms is `--route`.

Team answer (fixed now): coach-weighted vote (each member's answer gets that member's coach probability; the answer with
the most weight wins). Also logged, not used for marks: coach argmax, majority, any-member-right, each member alone.

## Marks (screen: seeds 100 and 101, ON vs OFF paired, same machine)

Primary readout: team-vote exact on the `variant` dev split (1,320 rows). Guard: team-vote exact on `in_dist`.

- **PASS (go to a 6-seed confirm):** ON beats OFF on variant by >= 3.0 points (mean of the 2 seeds), ahead on both seeds,
  and ON in_dist >= OFF in_dist - 2.0.
- **Proves it wrong:** ON - OFF on variant < +1.0 point (mean), or ON behind on either seed. Then routing by a coach does
  not make training together pay at this size; stop.
- In between: inconclusive; run seeds 102 and 103 before deciding.
- **Void if** routing never took: in ON's last train log line the coach's mean top probability per row (`coach_max`)
  is below 0.40 (uniform is 0.33), i.e. the coach routed almost nothing.
- **Amendment, 2026-10-05 3:58 PM ET, before any team result existed (both seed-100 runs were mid-training):** GPT
  pointed out that `coach_max` is not a test of routing. A coach that gives every row the same (0.8, 0.1, 0.1) passes
  it but routes nothing, because member i's sampling prob 0.5/512 + 0.5 c_i / (512 c_i) is uniform whenever its coach
  score is constant across rows. The void rule is replaced: from the saved final coach, on 50 fresh pools of 512 training
  rows, compute each member's sampling distribution and its total-variation distance from uniform; **void if the mean
  over members is under 0.05** (less than 5% of the sampling mass moved; the maximum possible with mix 0.5 is 0.5). The
  old `coach_max` number is still reported. This reads only the final coach, so it understates routing earlier in
  training. Note also that ON - OFF measures practice allocation only: both arms already have a coach choosing answers.

Secondary, reported but not a mark: (a) does the team help at all? OFF team-vote vs OFF's best single member on variant
(a team "helps" at >= +2.0); (b) shared mistakes between members, ON vs OFF (training together should make members
miss different rows); (c) OFF members vs the solo screen members (harness check: within seed noise, about 2 points).

Size: the team is about 10.2M (3 x 3.3M + 0.44M). Ben's bar is beating a same-size single model, so a team that passes
must next beat a ~10M single model trained the same number of steps (existing: plain_tf 10.8M, variant 21.7; a ~10M B2
does not exist yet and would be the real bar).

Noise rule: no claim from the 2-seed screen alone; a PASS goes to 6 paired seeds.
