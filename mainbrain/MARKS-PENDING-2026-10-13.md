
### Result 31, arm NK-soft (graded mask + 10x KL) seed 201, full run: PASS (2:20 AM ET 10-13)
runs/sheet-s201-kf99n-kl10-soft (constants-kf99n-kl10-soft-lr3e4.json, code c823e4b9a; 9 nights, none undone, stop = quiz rise < 1 over 2 nights). Scored from local copies while the shared-folder mount
was down in this box (same domain.analyze, same panel file: sha256 prefix dda9dc62, checked against the cached score files; parent checkpoint hash edbd1ee4 unchanged); outputs in the scratchpad
until the mount returns, then copied to runs/.
- **DM1 near +65.71** (0.95 -> 66.67): pass. **DM3 pass: pooled in_dist drop 0.96 (90.88 -> 89.93), nothing fired at the end.** Marks (1:10 PM ET 10-12): pass = DM1 >= +30 and DM3 passes; proved wrong =
  pooled drop >= 1.84, or 2+ families fired, or DM1 < +10. None of those. DM2 far +2.14 (fails as always). DM5 reads PROVED WRONG (the run stopped at night 9 while still rising, +5.24); DM5 is not in this arm's marks.
- Per-night pooled drop: 0.15, 0.44, 0.66, 0.74, 0.74, 0.59, 1.10, 0.74, 0.96. **fewshot_number_rule fired on nights 3, 6 and 7** (a family at 47.5% on 40 questions flips in and out of the 5-point rule) but not on the final night.
  Honest reading: the end-of-run verdict is clean, the middle is not; Fable's Q3 point (weak-power rule at 40 rows) fits, and the same family is the first to move in every arm.
- Seed 201 table (near / pooled drop / fired at the end): N99 +60.7 / 1.84 / none (FAIL); NK +68.1 / 0.74 / fewshot_number_rule (FAIL); **NK30 +65.0 / 0.44 / none (PASS)**; **NK-soft +65.7 / 0.96 / none (PASS)**.
- So two guards pass s201: NK30 (hard lock, smaller drop) and NK-soft (graded lock, passed the join test with HO 26.4). Not confirmed until seed 200 (both running: NK-soft night 8, NK30 night 1 at 2:20 AM ET).

### Result 32, arm NK-soft seed 200, full run: DM1 PASS, DM3 FAIL on one family (seq_next); not proved wrong (4:57 AM ET 10-13). Arm NK-soft30 marks written now (before it runs)
runs/sheet-s200-kf99n-kl10-soft (12 nights, none undone; scored from local copies, mount down; panel sha dda9dc62).
- **DM1 near +62.62** (2.14 -> 64.76): pass. **DM3: pooled drop 0.81 (90.22 -> 89.41), but seq_next fired (85.0 -> 72.5, 5 of 40 questions)**: FAIL. DM2 far -0.71 (fails as always). DM5 +3.33 (not in this
  arm's marks). Marks: not proved wrong on seed 200 (one family, drop < 1.84, DM1 >= +10). Per-night pooled drop: 0.51, 0.59, 0.66, 0.66, 0.37, 0.74, 0.59, 0.74, 0.44, 0.81, 1.10, 0.81.
- **seq_next fired on every night from night 2 through night 12** (night 1 clean), so this is a steady loss, not a flip near the threshold. fewshot_number_rule (50 -> 42.5) fired only on night 11.
- Seed 200 table (near / pooled drop / fired at the end): N99 +55.0 / 0.74 / none (PASS); **NK-soft +62.6 / 0.81 / seq_next (FAIL)**. Seed 201 (Result 31): NK-soft +65.7 / 0.96 / none (PASS).
  So NK-soft passes one seed and fails one; it is not a passing guard yet.
- Shown: with the graded mask at soft=1 and KL 10x, seq_next drops from night 2 on s200. Suggested, untested: seq_next's directions sit near the edge of the protected set (arm A and arm E, both
  lock-only, also fired seq_next on this seed; N99 did not), so a mask that lets boundary directions move at full speed opens exactly them, and KL 10x does not repair it. NK30 on s201 shows that
  KL 30x repaired fewshot_number_rule where KL 10x did not, which is the evidence for trying 30x here.
- **Next, arm NK-soft30 = NK-soft with replay_kl_weight 30 (one change vs NK-soft: the weight).** Because the fire starts at night 2, a 3-night screen on seed 200 is enough to see it:
  constants-kf99n-kl30-soft-lr3e4-n3.json, folder runs/screen-s200-NKsoft30-n3, scored by domain.analyze and harm_nights.
  **Pass:** seq_next does not fire on nights 2 or 3 (harm_nights), nothing fired at night 3, pooled drop at night 3 <= 0.9, no night undone (agreement >= 97), near at night 3 >= +25
  (NK-soft s200 night 3 was +38.1). **Proved wrong** (30x KL does not repair the soft mask): seq_next fires on night 2 or night 3 (NK-soft's signature), or near at night 3 < +10.
  On pass: the full run on seed 200 (constants-kf99n-kl30-soft-lr3e4.json), then seed 201, then the join test with KL 30x (Far transfer's L11 recipe with the weight changed, through the coordinator).
  Full-run marks: pass = DM1 >= +30 and DM3 passes on both seeds; proved wrong = pooled drop >= 1.84, or 2+ families fired at the end, or DM1 < +10.
- NK30 seed 200 (hard lock + KL 30x) is still training (night 5 of 12 at 4:57 AM ET); its marks are those of Result 30. If it passes s200, NK30 is the old-skills guard that passes both seeds; whether the
  hard lock blocks transfer for it is unmeasured (the hard lock without KL got HO 9.3).
