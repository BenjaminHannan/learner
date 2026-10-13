
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

### Result 33, arm NK-soft30 3-night screen on seed 200: PROVED WRONG (6:58 AM ET 10-13); arm NK-soft3 marks written now (before it runs)
runs/screen-s200-NKsoft30-n3 (3 nights, none undone, scored from local copies).
- Near +37.38 at night 3 (2.14 -> 39.52), pooled drop 0.59, agreement 97.46, **seq_next fired at night 3 (85.0 -> 75.0)**; night 2 clean (pooled 0.44), night 1 clean (0.22). Marks (4:58 AM ET): proved wrong =
  seq_next fires on night 2 or night 3: **PROVED WRONG**. Other family moves (none fired): rule_apply 97.5 -> 92.5, passage_qa 97.5 -> 95, fewshot_number_rule 50 -> 45.
- Shown: 30x KL delayed the seq_next fire by one night (NK-soft 10x fired from night 2) but did not prevent it; with the soft mask at soft=1 the KL weight is not what protects seq_next. Same seed with the
  hard lock (N99) kept it.
- **Next, arm NK-soft3 = NK-soft with protect_soft 3 (one change vs NK-soft: the softness constant; KL stays 10x).** M = min(1, tau / (3 p)): the boundary pair moves at 1/3 speed and a pair 10x more
  important at 3.3%; soft = 1 is the NK-soft run, and soft -> infinity is the hard lock (N99 passed s200). Flag: soft is now a global constant of the same kind as `energy` (one value for every subject, not
  tuned per family); soft = 1 had no constant, soft = 3 is a dial between the two measured ends.
  3-night screen on seed 200 (constants-kf99n-kl10-soft3-lr3e4-n3.json, folder runs/screen-s200-NKsoft3-n3).
  **Pass:** seq_next does not fire on nights 2 or 3, nothing fired at night 3, pooled drop at night 3 <= 0.9, no night undone (agreement >= 97), near at night 3 >= +25 (NK-soft s200 night 3 was +38.1).
  **Proved wrong:** seq_next fires on night 2 or 3, or near at night 3 < +10. If it passes: the full run on s200 (constants-kf99n-kl10-soft3-lr3e4.json), then s201, then the join test with soft 3
  (Far transfer's L11 recipe, soft=3, through the coordinator): pass = HO >= 25 and DEV drop < 7.8, proved wrong = HO <= 10 or drop >= 7.8. If it fails the screen: soft 10 (Fable's backup 2) is next.
  Honest expectation (suggested, untested): the harder the mask, the lower the HO; soft = 3 may land between 9.3 (hard) and 26.4 (soft = 1), so the join test, not the screen, decides.

### Result 34, arm NK-soft3 3-night screen on seed 200: PROVED WRONG (8:50 AM ET 10-13)
runs/screen-s200-NKsoft3-n3 (3 nights, none undone). Near +34.29 at night 3 (2.14 -> 36.43), pooled drop 0.81, agreement 98.05, **seq_next fired at night 3 (85.0 -> 75.0)**; nights 1 and 2 clean.
Marks (7:00 AM ET): proved wrong = seq_next fires on night 2 or 3: **PROVED WRONG**. Softness 3 did not stop seq_next either (softness 1: fired night 2; 1 + KL 30x: night 3; 3: night 3).

### Result 35, arm NK30 (hard lock + 30x KL replay) seed 200, full run: PASS, so NK30 passes both seeds (8:50 AM ET 10-13)
runs/sheet-s200-kf99n-kl30 (11 nights, none undone, stop = quiz rise < 1 over 2 nights; trained locally 1:10-6:xx AM ET, scored from local copies, mount down).
- **DM1 near +63.10** (2.14 -> 65.24): pass. **DM3 pass: pooled drop 0.22 (90.22 -> 90.00), nothing fired** (largest: seq_next 85 -> 80, list_stats 92.5 -> 90, fewshot_number_rule 50 -> 47.5). DM5 pass (rise +0.71).
  DM2 far -0.36 (fails, as in every run). Marks (Result 30): pass = DM1 >= +30 and DM3 passes, seed 200 with the same file: **met.**
- NK30 table (near / pooled drop / fired): s201 +65.0 / 0.44 / none; s200 +63.1 / 0.22 / none. Against N99: s201 +60.7 / 1.84 (fail), s200 +55.0 / 0.74 (pass). The 30x KL on the hard lock learns more than N99
  and slips less on both seeds. Two seeds, not the six paired seeds a confirm needs; it passes the pass marks, it is not a six-seed confirm.
- **NK30 is the first whole-model guard to pass DM1 + DM3 on both seeds.** Its open question is transfer: the hard lock without KL got HO 9.3 on the join test, and a KL term only adds restoring force. Predicted
  (suggested, untested): NK30's join test lands near or below 10. Not worth 10 h of Far transfer's CPU unless NK-soft10 fails to find a middle.

### Marks for arm NK-soft10 (written 8:55 AM ET 10-13, before it runs): the dial's other end
Facts: hard lock (NK30) passes both seeds and probably blocks transfer; softness 1 passes the join test (HO 26.4) and seq_next breaks on s200; softness 3 and KL 30x did not stop seq_next. Softness 10 is Fable's backup 2
(every protected pair at most 10% speed). One change vs NK-soft: protect_soft 10 (KL stays 10x). It is a dial, not a new idea; soft is a global constant like `energy`, not tuned per family.
- **Full run on seed 200** (the failing seed; a 3-night screen could pass falsely, because the seq_next fire is moving later as softness rises): constants-kf99n-kl10-soft10-lr3e4.json, folder
  runs/sheet-s200-kf99n-kl10-soft10, up to 12 nights. **Pass:** DM1 >= +30 and DM3 passes at the end (seq_next quiet, nothing fired, pooled drop <= 1.5). **Proved wrong:** seq_next fires at the end, or 2+ families
  fired, or pooled drop >= 1.84, or DM1 < +10. Per-night harm_nights reported. On pass: seed 201 with the same file.
- **Join test with soft 10** (Far transfer, L11's recipe, soft=10; asked through the coordinator in parallel, because the join result is independent of seq_next and it fills in the HO-vs-softness curve:
  hard 9.3, soft 1 26.4): **Pass:** HO >= 25 and DEV drop < 7.8. **Proved wrong:** HO <= 10 or DEV drop >= 7.8. Between 10 and 25 is reported as a point on the curve, neither pass nor wrong.
- Ship rule if the dial has no sweet spot (soft 10 fails the join test, or fails seq_next): the shipped guard is NK30 (passes old skills on both seeds), transfer handled by the add-on path, and the
  shared-brain-transfer claim is dropped for now. Said out loud: that outcome would mean the guard that protects old skills at the level the marks demand also blocks learning that reuses old directions.

### Result 36, arm NK-soft10 (graded mask at softness 10 + 10x KL) seed 200 full run: PASS; its join test (Far transfer L13) lands between the marks (2:55 PM ET 10-13)
runs/sheet-s200-kf99n-kl10-soft10 (9 nights, none undone, stop = quiz rise < 1 over 2 nights; scored from local copies, mount down). Seed 201 is still training (night 9+).
- **DM1 near +57.86** (2.14 -> 60.00): pass. **DM3 pass: pooled drop 0.44 (90.22 -> 89.78), nothing fired on any of the 9 nights.** seq_next 85 -> 82.5 (softness 1: 72.5, fired from night 2); other largest
  moves rule_apply 97.5 -> 92.5, kin_chain 95 -> 92.5. DM2 far +1.07 (fails as always). DM5 reads PROVED WRONG (stopped at night 9 with a +5.48 rise; not in this arm's marks).
  Marks (8:55 AM ET): s200 pass = DM1 >= +30 and DM3 passes at the end: **met**. Per-night pooled drop: 0.37, 0.44, 0.44, 0.44, 0.51, 0.59, 0.59, 0.51, 0.44.
- **Join test, soft 10 (Far transfer L13, one run, 4,000 updates): HO 14.1, DEV drop 0.44, nothing fired at 4,000** (seq_next fired at the 2,000 check, then did not at 4,000). Marks: pass HO >= 25 and drop < 7.8;
  proved wrong HO <= 10 or drop >= 7.8; between = a point on the curve. **14.1 is between.**
- Curve at 4,000 updates (HO / DEV drop): unguarded 35.0 / 53.2; soft 1 + KL 26.4 / 0.59; **soft 10 + KL 14.1 / 0.44**; hard lock (no KL replay) 9.3 / 7.8. One run per point; the hard-lock point had no KL replay.
- Reading (shown, one seed per point): the softness dial trades transfer for old-skill protection smoothly: softness 1 transfers (26.4) and loses seq_next on s200; softness 10 keeps old skills on s200 and transfers about
  half as much (14.1); the hard lock transfers least. No point passes both marks on seed 200 so far. Softness 3 (between) lost seq_next in its 3-night screen, so a softness between 3 and 10 would land HO somewhere between
  14.1 and 26.4 at best, below the 25 line unless it also kept seq_next, which the data do not suggest. Said plainly: with these marks, the dial has no sweet spot yet.
- Open: NK-soft10 seed 201 (running). NK30's own join test (hard lock + 30x KL), offered by Far transfer, would say whether KL replay changes the hard lock's transfer: marks below.

### Marks for the NK30 join test (Far transfer L14; written 2:58 PM ET 10-13, before it runs)
Setup = L11's recipe with the hard mask (kf.factors soft=None, energy 0.99) and 30x KL on 32 diary rows per update (the NK30 training recipe), lr 1e-4, 4,000 updates, same rows and seed.
**Pass:** HO >= 25 and DEV drop < 7.8 (the hard lock with KL transfers: then NK30 passes both sides and is the ship candidate). **Proved wrong:** HO <= 10 (the hard lock still blocks transfer with KL).
Between 10 and 25: a point on the curve. Prediction (suggested, untested): HO <= 10, because the lock's mask does not depend on the replay term and the soft 10 point (every pair at most 10% speed) only reached 14.1.
Ship rule, fixed now: ship the guard that passes the old-skill marks on both seeds (DM1 >= +30, DM3) with the higher join-test HO. NK30 and NK-soft10 both pass s200; NK30 passes s201; NK-soft10's s201 is running.
If NK-soft10 passes s201 and NK30's join HO is below 14.1: ship NK-soft10 (it keeps more transfer at equal old-skill safety), reported with the one-seed caveat. If NK30's join HO >= 14.1: ship NK30 (no softness constant).

### Result 37, arm NK-soft10 seed 201, full run: PASS, so NK-soft10 passes both seeds on the old-skill marks (4:50 PM ET 10-13)
runs/sheet-s201-kf99n-kl10-soft10 (12 nights, none undone; scored from local copies, mount down).
- **DM1 near +65.48** (0.95 -> 66.43): pass. **DM3 pass: pooled drop 0.96 (90.88 -> 89.93), nothing fired at the end.** DM5 pass (+2.14). Per-night pooled drop: 0.37, 0.59, 0.88, 0.88, 0.96, 0.88, 0.74, 0.66, 0.66, 0.74, 0.81, 0.96.
- **Caveat, said plainly:** fewshot_number_rule fired on nights 3, 4 and 6, and at night 12 it reads 47.5 -> 35.0, a 12.5-point drop whose paired interval (-30 to +2.5) just reaches zero, so it does not fire by the rule. The end verdict
  is clean on the rule; the family itself dropped 5 of 40 questions. Same family, same pattern as NK-soft (nights 3, 6, 7). NK30 on s201: 47.5 -> 40.0 (interval -20 to +5).
- Both-seed table (near / pooled drop / fired at the end): NK-soft10 s200 +57.9 / 0.44 / none; s201 +65.5 / 0.96 / none. NK30 s200 +63.1 / 0.22 / none; s201 +65.0 / 0.44 / none. NK30 slips less and learns about as much;
  NK-soft10 keeps more transfer (join HO 14.1 vs the hard lock's 9.3 without KL).
- Open: the ship decision waits for Far transfer's NK30 join test (L14, marks and ship rule fixed in the 2:58 PM ET entry above). Rule: ship the guard that passes both seeds with the higher join-test HO.
