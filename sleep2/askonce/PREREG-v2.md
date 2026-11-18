# Ask once, then remember: pre-registration v2 (askonce-v2)

Written 2026-10-25, before job 2 of v2 runs. Everything not listed under "What changed" is the v1 prereg, unchanged.

## Why v2 exists
v1 was refuted as registered (results/VERDICT.md), but for a design reason, not because of the idea (shown, simulated world, K2-3.7B, 2 seeds):
- Every trained arm (A+, B, B-sft) gave 0 ASK replies on 420 eval items. The untrained model P asked on 57 of 420, and on 14 of 80 H_new items (16.2% right on H_new; every trained arm 0%).
- The shared night SFT (identical in all arms) held fact sentences and corrected ACTIONS only. It taught "always act" and erased asking, and B's 28 DPO pairs over 5 nights could not win it back. So B vs A+ was 0.0 vs 0.0 and the test could not see the mechanism.

## What changed (v2)
1. Shared night SFT now keeps asking alive, in all arms equally (build_night_data.py: `ask_act_pools`, `pick_ask_act`):
   - **Shared ASK examples**, taken from the day logs: turns whose first move was ASK on an underspecified request, where the slot was NOT answered in the [Memory] the model saw and Ben's next reply supplied the slot value. Target = the model's own ASK line.
   - **Not reused:** any turn the tagger tagged regret or annoyance. Those are B's slice material, so the arms still differ only in the 15% slice.
   - **Equal number of correct ACT-on-known examples** (first move ACT, matches gold, slot answer visible in [Memory]; when a night has too few, correct ACT on fully specified requests fills the count), so asking does not spread to known slots.
   - The corrected-action SFT and fact SFT are as in v1.
   - **Target share:** ask / (ask + corrected-ACT + ACT-on-known) is about 0.20 (`config.ASK_SHARE`), near P's ask rate on underspecified items (17.5% on H_new, 20% on knowable). The realised share per night is logged in plan.json and printed by the build.
2. The ledger equality assertion (arms within 5% token-passes) is kept. The shared set is now slightly larger, so auto repeat went from 9 to 7 passes per night (all arms equal).
3. report.py gets the gate below. Nothing else in the analysis changed.

## Unchanged pass marks (B vs A+, fixed in advance, all five must hold)
1. H new ambiguity: B >= A+ + 8 points, p < 0.05, positive in both seeds.
2. R overall: B >= A+ + 3 points and ask rate on fully specified <= A+ + 3.
3. Knowable: B >= A+ - 2.
4. ARC within 1, recall within 2, general ask rate <= A+ + 3.
5. B >= B-sft + 3 on new ambiguity (and B-sft replaces B if it meets marks 1-4).
Result that proves the idea wrong (any one): B <= A+ + 3 on H new; B's Split R change < 0; B more than 5 below A+ on knowable.

## New gate (fixed before running)
The run is **INCONCLUSIVE, not refuted**, if A+'s ASK rate on H_new (pooled over both seeds) is below half of P's ask rate on H_new (P: 14/80 = 17.5%, so the line is 8.75%). Reason: below that, the shared training still suppresses asking and B has nothing to improve on. If P's results are missing the gate cannot be checked and the run is also INCONCLUSIVE. When the gate is met, the five marks decide exactly as before.

## Compute
Job 1 is reused: day logs at /mnt/project-files/mechanism/askonce-job1-out/v2/ (job1/diary) and its P_1 eval (job1/results/P_1.json). The tagger tags are v1's (askonce-nightdata/tags.jsonl). eval_inputs.jsonl is byte-identical to job 1's, so P and the trained arms see the same prompts. Only job 2 reruns: 2 lanes (seeds) x about 126 min = about 4.2 T4 GPU-h, new kernel benhannanjfkldsfds/askonce-v2-job2 (v1 outputs are not overwritten). Same hard caps as v1 (2.5 h per lane). Grading is the same small Batches job (v1: about $0.02).

## Schedule
Runs after the Kaggle GPU quota resets (about Oct 31). Nothing is pushed before then.
