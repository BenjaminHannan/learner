# dl-6 verify (Fix-sleep thread, 2026-09-26)
The rental hit its $0.57 kill line with 27 of 28 nights done (L seed 11 night 7 never ran; RESULTS-gpu.md). A blind
recount (a separate agent read only PASSMARKS.md, the scorer and the raw per-night rows in gpu/dl6_results.json and
gpu/log.txt) finds the registered verdict already decided: **FAIL, whatever the missing night would have shown.**
- F3 FALSE: L seed 10's night-7 lucky guesses are 140, below 2 x L0 = 150 (L0 = 75).
- F4 FALSE: 3 L nights fell more than 15% below the night before (seed 10: 99 -> 80 and 98 -> 80; seed 11: 151 -> 120);
  the limit is 1.
- F1, F2, F5 UNDETERMINED (depend on the missing night): F1 needs L s11 night-7 lost <= 13; F2 needs it <= 10; F5
  needs reached >= 35.
- Not INCONCLUSIVE (L0 75 >= 10; S night-7 lost 25 + 27 = 52 >= 20). Not proved wrong (L s10 lost 13 < S s10 25).
- Recount slip, no effect: the agent listed L s11 night-5 lucky as 115; the log says 125.
- Code label note (also in dl-4's VERIFY): the count named "nights_lost_over_15" tests lost > 10, as PASSMARKS says.

## What it shows (report-only, plain words)
One epoch per night roughly halved forgetting and roughly halved learning. Night 7: L lost 13 (seed 10) vs S 25 and
27; L seed 11 had lost 7 by night 6 vs S seed 11's 20. Lucky guesses: L s10 gained 65 over the base vs S's 123 and 162;
L s11 night 6 was 115 vs S s11's 190. Drift from the base on chat replies (KL) was NOT lower for L (0.22 vs 0.19-0.21
at night 7). Reading (suggested): lost tracks how much is trained, not the KL measure on chat, and cutting the dose
trades learning away about one for one.

## Dose split (report-only, computed after the verdict at the Thread manager's request)
Cumulative example-epochs (right examples x epochs, summed over nights) -> lost, lucky:
- S s10: 210->4,123; 468->7,140; 747->11,153; 1065->14,164; 1392->21,170; 1719->25,176; 2046->25,198
- S s11: 219->3,96; 489->12,118; 756->12,168; 1074->15,175; 1407->26,234; 1734->20,190; 2070->27,237
- L s10: 70->3,99; 149->4,80; 230->3,98; 331->4,80; 426->10,130; 522->8,127; 616->13,140
- L s11: 73->3,100; 147->4,135; 222->6,151; 317->4,120; 426->7,125; 531->7,115 (night 7 not run)
At matched totals S and L lose about the same and learn about the same (near 220: lost 4, 3 vs 3, 6; near 430-490:
7, 12 vs 10, 7). Suggested: forgetting and learning both track the total amount trained, not the number of nights.
