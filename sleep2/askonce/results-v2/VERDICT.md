# Ask-once v2 verdict, 2026-10-27

The run was on Kaggle, account benhannanjfkldsfds, T4 x2. Seed 1 took 115 min and seed 2 took 108 min. The day logs and the P eval were reused from v1. Grading cost about $0.03 in Batches, and grader kappa was 0.91.

**The gate passed (shown).** With asking examples in the shared lessons, A+ kept asking: it asked on 11.2% of H_new items, against 17.5% for P. So this time the test could see the mechanism.

**Result: REFUTED (shown, simulated world, K2-3.7B, 2 seeds).** On new-ambiguity items, B was 9.4 points WORSE than the equal-compute baseline A+: 0.6% vs 10.0%, p = 0.0001, with B below A+ in both seeds (-3.8 and -15.0). The slot-clustered 95% CI is -16.9 to -3.8. B-sft was also worse than A+, by 8.1 points (p = 0.001). The decision is to adopt none.

**Likely reason (suggested, untested):** B's slice had more "annoyance" pairs (prefer acting) than "regret" pairs (prefer asking). Over 5 nights that was about 20 against 14, and some regrets were dropped because memory already held the answer. So the practice taught "act" more than "ask", and it pushed new-ambiguity asking down.

**What did help (shown):** the shared night training with asking examples, which is arm A+. It raised knowable-slot accuracy from 61 to 93%, and right moves overall on split R from 71 to 80.5%. It also kept some asking alive, which v1 had lost completely. ARC still falls from 88.4 to about 84.

**Takeaways:**
1. Keep the slot memory and the mixed ask/act night lessons (A+).
2. Drop ask/act DPO practice in this form.
3. Any future version would need a balanced regret/annoyance slice, and that would be a new pre-registration.
