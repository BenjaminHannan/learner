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
