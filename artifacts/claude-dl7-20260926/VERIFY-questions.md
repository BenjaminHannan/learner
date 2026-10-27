# dl-7b: answers to the Thread manager's review questions (20:15 UTC), 2026-09-26T20:15:11Z. Registered verdict unchanged: FAIL.

(a) F1 per seed: seed 12 F lost 3 vs S 11; seed 13 F lost 4 vs S 15. Which items: F's lost items are {42, 62, 197}
(s12) and {42, 56, 98, 197} (s13); 2 of 3 and 2 of 4 were also lost by S on the same seed, so F mostly spares the
same shaky items S loses, but not only those (197 and 98 are lost by F and not by S). Items 42 and 197 are lost by F
on both seeds (S loses 7 items on both seeds). All 7 of F's lost items are in the base's least-confident third.

(b) The shortfall is not flat, and it comes from one seed. F's gain as a share of S's gain, nights 1-7:
seed 12: 0.62, 0.58, 0.99, 0.88, 0.83, 0.51, 0.55; seed 13: 0.55, 0.50, 1.47, 1.07, 1.25, 1.03, 1.09.
F s12 lucky per night 101, 110, 145, 184, 207, 200, 179 (falls on nights 6-7) while S s12 jumps to 329 on night 6
(then 273). F s13 matches or beats S from night 3 and is flat after night 4 (211, 205, 217, 216). So on seed 13
replay did not slow learning at all; on seed 12 F stopped gaining after night 5 while S kept gaining. With two
seeds and S itself swinging (S s12 -56 on night 7, S s13 -24 on night 5), neither "replay slows learning" nor
"replay stops learning" is shown; both are suggested at most.

(c) The premise row (22 of 26 = 84.6% of S's lost items in the base's shakiest third, bar 60%) is the SECOND try:
fd-1 (9d583ef5f) missed the same bar (17 of 29, 59%). Two tries, one pass: suggested, not shown.

(d) sha256 recomputed here on the files copied to main (d0246e874):
- gpu/dl7_results.json  da4d739e1684a847d11954a93f8d54f2fdce4ea7de0ed4b303c2cd0e930212a1  (98893 bytes)
- gpu/fragile_pool.json 5f670998a22806bdba65df080f9ce4e45e0681f8b34076a22d14bf0992db4273  (59682 bytes)
- gpu/log.txt           8329a78f23b11372a0d8611e520fab04641d130b7f5dc5ba7db424210502074a  (12941 bytes)
- gpu/suffix.json       c1df47be21f2415d39b559aed61f566e4a56b644b09146c449797dc29176ecad  (121 bytes)
Sizes match the builder's Python check. There is no earlier hash to compare with (the builder's tools failed), so
these pin the files from now on; the recount used exactly these bytes.
