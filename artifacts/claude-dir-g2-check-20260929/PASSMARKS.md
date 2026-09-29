# dir-g2 pass marks: retrain only the check head (G builder thread, written 2026-09-29 09:31 UTC (`date -u`), before any code or run)

Fixed now. Nobody changes them after a score is seen. A separate blind recount reads only the raw files and this page.
Labels: SHOWN = counted from a file. SUGGESTED = fits the counts. UNTESTED = nobody has run it. Design and reasons: DESIGN.md. No score of this test exists.

## The single change
On each of the two frozen G nets (g-s13, g-s14; final.pt sha256 6832f4d655242b7183c77edaa1c39c1bce1304083c7ef79937e75580b8739a5f and c1049a23815ad158105816d64b8b245a418a85792c56ac9b06260d78c99a8c68, RUN-NOTE.md), replace the halt head used for picking by a fresh Linear(512,1) trained on the net's own tries labelled by the exact checker (DESIGN.md section 3). Net weights, start vectors, stop rule, the four answers per hand and every test are unchanged. Kind-blind at test (no checker, no label). Training data only from code (generators, the checker, the net's own outputs): no text Claude wrote.

## Measures (held-out numbers4, the sealed 300; per net; new head trained with 3 head seeds 1, 2, 3; the score of a net is the MEAN of the 3 seeds, all 3 also reported)
- S_pick_new: right after picking, among the 4 streams at their own stop, the stream with the highest new-head probability (ties lowest index).
- Comparators (SHOWN, G RESULT.md, unchanged because the nets and stops are unchanged): S_pick_old 30 (s13), 24 (s14); S_rand mean of 4 streams 16.25, 13.0; S_any 42, 33; one stream with an any-of-48-rounds oracle 37, 35.
- Reported only, never judged: S_pick_full (new head also drives the stop rule), P192 (new head argmax over 4 streams x 48 rounds; ceiling 90, 94), sums4, grids5, sums6, grids6, numbers5, the new head's AUC on the numbers4 dev set and on sums4/grids5 dev items.

## Validity (V). Any miss = INCONCLUSIVE
- V1 frozen: sha256 of both final.pt equals the values above before and after.
- V2 repro: recomputing the OLD pick from the new run's own rounds gives S_pick_old within 2 of the recorded 30 and 24 on numbers4, and S_any identical (42, 33) within 2. (Shows the runner sees the same tries as G; float differences between machines may move a stop by a hair.)
- V3 sha256 of PASSMARKS.md, DESIGN.md, the runner and G's sealed files match their lines before the run.
- V4 learned something: the new head's AUC (right vs wrong, all rounds pooled) on the 3,000-pair numbers4 dev set is >= 0.70 on each head seed of each net. If not, INCONCLUSIVE-UNDERFIT (the head did not learn; a verdict on checking would be unfounded).
- V5 control (plain-net row, item 4 below): the shuffled-label head on each net has S_pick_shuf <= S_rand mean + 6 (22 for s13, 19 for s14). If a shuffled-label head beats that, the pick rule itself is biased (for example by stream index); any pass is then NOT credited (INCONCLUSIVE-BIASED).
- V6 gates: unchanged by construction (frozen nets); numbers reported.

## PASS-G2 ("a trained checker picks the right try", needs V1-V6)
On BOTH nets, mean S_pick_new >= bar, with bar = max(30, ceil(2 x S_rand mean), S_pick_old + ceil((S_any - S_pick_old)/2)) = **36 for s13** (max(30, 33, 36)) and **30 for s14** (max(30, 26, 29)), AND no single head seed of a net more than 3 below its bar. Wording of a pass, fixed: "a trained checker picked the right try on unseen number hands." Never worded "it checks arithmetic": whether the head checks arithmetic or uses another cue is UNTESTED.
Replication (more head seeds, then a second G net pair) only after the primary is recounted; it can confirm or contradict, not rescue a non-pass or overturn WRONG.

## The result that would prove it wrong
**WRONG (training the checker did not help)** = V1-V6 met and, on both nets, mean S_pick_new <= S_pick_old + 3 (<= 33 for s13, <= 27 for s14). Reading: the frozen state does not let a linear head tell right tries from wrong ones beyond what the sealed head did; the fix, if any, is a bigger or verifier-mode check (own tests, not proposed here).
Anything else (one net passes, or a mean between the WRONG and PASS bars, or head seeds disagree by more than 3 on a net): PARTIAL, no claim, no second change until the marks are read.

## Prediction (SUGGESTED, not a result)
PASS about 25%. Likeliest: PARTIAL or WRONG, since judging arithmetic from a mean-pooled state through one linear layer is hard. The pick already beats a random stream by 13 and 11 (SHOWN), so some room is used; the remaining gap to S_any is 12 and 9.

## MARKS SELF-CHECK (Ben 21:37 UTC 09-28), one line each
1. Noise. The measured spread of the number score across seeds is 0 to 3 of 300 for a net at 4 (RECOUNT.md, RESULTS.md:12) and G's two nets differ by 6 in S_pick (30 vs 24). Head-seed noise is UNTESTED; hence 3 head seeds per net, a margin (+3 either side) and the gap-half rule; WRONG's +3 is at the size of that spread, PASS's bar is 6 above old on s13 and 6 on s14.
2. "Every seed" reading. PASS needs both nets and all head seeds within 3 of the bar; WRONG needs both nets; one net passing or seeds disagreeing is PARTIAL (no claim).
3. Fair comparator. The comparator is the same nets' own old pick, random stream, four-stream oracle and the one-stream any-round oracle (all in the table above), all from the same tries; the pick can never exceed S_any (42, 33), so the bars are set as a share of that gap, not as a fixed number above it. F4 (19.2) is beaten by the old pick already and is not the bar.
4. Plain-net row. A plain same-size net cannot pass: it has no tries and no head (numbers4 6 and 4 of 300, H2 RECOUNT.md, SHOWN). The shuffled-label head (V5) is the control that the pass comes from the labels: same features, same head, permuted labels. "Not memorising": the head trains on practice items only; held-out hands are absent from the pool (H2 pool line, SHOWN) and V4's dev set is separate practice items.
5. F_few (k = 1..64). Not applicable: no examples in the input, no sleep or memory step.
6. Sleep gates. Not applicable.

## Procedure
1. Builder writes the runner and queue job, runs the CPU selftest; Director seals sha256 of this page, DESIGN.md and scripts.
2. Run (cost and box in queue job). Head training and eval each once per head file; the eval reads the numbers4 test panel (the same sealed 300 as G) counts only.
3. Blind recount reads only raw files and this page and writes VERIFY-recount.md.
