# Addendum 1 (H12)

Written 2026-09-28 21:46 UTC (`date -u`) by the Director before any run, dev score or holdout score of this test, from artifacts/claude-dir-review2-20260928/REVIEW.md section 8 (claims checked: A marks.py:81, ruler stop rule claude_fewex_bench.py:76-78, R2g PASSMARKS:37/39). These change the words a verdict may use and add read-only checks. They never change a number a seed was already judged by, and none can turn a REJECTED into a PASS. Where a rule names a script line to change, the verdict is read by hand from the script's numbers under this rule until a new *_add1 script exists; the sealed script is not edited.

- **H12-1.** Before the word STOP LEARNED, on each seed's kept k = 1,024 checkpoint (dev, no training, no holdout): (a) the agreement-only read (halt ignored) and (b) the AUC of the halt probability at round 16 against exact-now over the 300 dev mazes. STOP LEARNED needs AUC >= 0.8 in both seeds and the agreement-only read worse than the learned read by at least 6 of 300 on one judged rung or more mean rounds; otherwise the word is STOP FIRES (informative: not shown).
- **H12-2.** Recommending the loss for the maze recipe needs both accuracy words not HURTS and the body delta (fixed-16 F_eq) above -3.5 in both seeds.
- **H12-3.** The word WRONG is renamed WRONG-AT-THIS-RECIPE and its meaning is limited to "the maze stop loss with the baseline round schedule (rounds 4, 5, 9, 10, 14, 15, 19, 20) and weight 0.5".
- **H12-4.** V5 tolerance is 3 of 300 and 3 of 200, or equal `source.pt` sha256 (the Mac job already prints it).
