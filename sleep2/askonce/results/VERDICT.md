# Ask-once (Invent-1) verdict, 2026-10-25

Ran on Kaggle (account benhannanjfkldsfds, T4 x2): job 1 12 min, job 2 about 2 x 126 min. Claude Batches spend: $1.08 (data) + $0.02 (grading). Grader kappa 0.94.

**Result: REFUTED as pre-registered (shown, simulated world, K2-3.7B, 2 seeds).** B = A+ on new-ambiguity items (0.0 vs 0.0, both seeds), and B-sft is the same. Adopt none.

**Why (shown):** every trained arm stopped asking entirely. They gave 0 ASK replies out of 420 eval items, while the untrained model P asked on 57 of 420. On new-ambiguity items, P was right 16.2% of the time and every trained arm 0%. The shared night training (fact SFT plus corrected-action SFT, identical in all arms) is all ACT examples, and it drowned out B's 28 DPO pairs over 5 nights. So the test could not see the mechanism at all. This is a design flaw in the shared part, not evidence about ask-vs-act DPO itself.

**Side findings (shown, this sim only):**
- Night training raised knowable-slot accuracy from 61 to 93-94%, and right moves on fully specified items from 92.5 to 100%.
- Fact recall went from 3 to 22-24%.
- ARC-Easy fell from 88.4 to 84-85 in all trained arms.

**Lesson for skill sleep (suggested):** SFT that only shows corrected actions teaches "always act" and erases asking. Any nightly action SFT needs ask examples mixed in (for instance, the questions from regret turns), or asking dies.

**Possible next test (untested):** the same harness with the regret turns' good questions added to the SHARED SFT for all arms, so asking survives in A+. Then B's DPO slice is the only difference, as intended.
