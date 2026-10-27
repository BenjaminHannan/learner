# Experiment 43E — pass marks (fixed before any full run; smoke run of 250 updates only)

Question 1: which automatic rule should sleep use to pick its checkpoint?
Question 2: on clean data, does a rank-4 (compact) update beat plain replay?

Setting = Experiment 42: registered bases (seeds 4102/4103/4104), 100 clean raw episodes,
3,000 updates, half new / half old-skill replay.  One change: 20 of the 100 episodes are held
out of sleep and used only to pick the checkpoint (so sleep trains on 80).
Checks every 250 updates.  "fresh" = exact match on the 200 never-seen test inputs.

Rules compared on the SAME run (no extra training):
- loss rule  = lowest held-out loss (43B's rule)
- match rule = highest held-out exact match; ties -> later check; never before update 1,000

V0 validity: base old-skills score >= 0.95.  Invalid seeds are reported, not counted.

E1 selector better:  plain arm, fresh(match pick) >= fresh(loss pick) + 0.05 in >= 2/3 seeds,
                     and never lower by more than 0.02 in any seed.
E2 selector good:    plain arm, fresh(match pick) >= best-possible fresh - 0.05 in 3/3 seeds.
E3 rank-4 helps:     fresh(rank4, match pick) >= fresh(plain, match pick) + 0.10 in >= 2/3 seeds,
                     and never lower by more than 0.02 in any seed.
E4 safety:           old-skills at the match pick >= base - 0.02 in all 6 runs.

Decision rule (fixed now):
- E1 and E2 and E4 pass -> the match rule replaces the loss rule in Sleep-vNext.
- E3 pass -> rank-4 earns ONE confirmation run on fresh seeds; no claim before that.
- E3 fail -> rank-4 is dropped; Sleep-vNext stays plain replay.
- Nothing here can show length generalisation or fewer-episode learning; "long" is recorded only.
Every seed reported separately.  Toy only.
