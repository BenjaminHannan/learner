# Think-1 run log

Times UTC. Code and PREREG are pinned by the commit named on each launch line; PREREG.md's sha256 is in PREREG.md.sha256.
- 2026-10-24 19:11Z, code 5dc3b08ab (PREREG sha256 aae4cb42...): Vast box 57553049 `claude-think1-compassionate-davinci-s0`
  (RTX 3090, Quebec, $0.122/h, 12 h self-stop): THINK_JOBS=a:0,b:0,aplus:0,bplus:0,t:0,t1:0 PARALLEL=1 MAXPAR=2.
- 2026-10-24 19:11Z, same code: Vast box 57553052 `claude-think1-compassionate-davinci-s1` (RTX 3090, Argentina, $0.135/h,
  12 h self-stop): THINK_JOBS=a:1,b:1,aplus:1,t:1,t1:1 PARALLEL=1 MAXPAR=2. Credit before launch $5.88.
- Seed 2 and tw:0: Ben's PC (commands in README.md).
- 19:45Z: box 57553049 (s0, Quebec) never left "created" in 33 min (no log); destroyed. Seed 0 relaunched on offer 55418674
  (RTX 3090, Argentina, the same host family as the working s1 box), new box 57556502, same pack (code 5dc3b08ab).
- 21:01Z: both boxes alive (their labels carry label_report's "|" suffix, so the job loop is running); no result files yet
  (stage 1 a and b side by side). Vast's log service gives S3 403 for both boxes (the host never uploads the log), and
  `cat` works only on stopped boxes, so progress is read from the labels. Credit $3.24; the account's other A100 boxes
  have ended, so the burn is these two boxes, $0.296/h plus storage.
- 21:17Z: s1 a_s1 done: validation 65.8, dev 81.3 (stage-1 A mean 66.72). 21:57Z: s1 b_s1 done: validation 66.5,
  1-pass lesion 60.1, dev 82.5 (stage-1 B mean 67.12); s1 moves to stage 2 (aplus, t, t1). Credit 21:41Z $2.99.
- 22:23Z: s0 a_s0 done: validation 67.0 (repeat eval 67.0, so eval noise is 0 at this level), dev 81.3.
- 22:37Z: credit $2.49. Two A100 boxes from another session (claude-sleepb11w/b11c-cqc4bi, $0.94/h) started at
  ~22:23Z; the account now burns ~$1.35/h, so credit ends ~00:30Z, before s1 (~02:00Z) and s0 (~03:30Z) finish.
  Asked Ben to top up or pause them; fallback: stop s0 shortly before credit ends so s1 runs longest, then pull results.
- 23:14Z, before any stage-2 result: summarize.py audited against PREREG (2 independent reviewers, 1 skeptic per finding).
  6 confirmed report/verdict-wording defects fixed (futility "laps real but small" and "go on" printed while a rule was
  not computable; FUTILE-STOP wording ignored the 2026-10-24 amendment and named no missing arms; G decided while
  bplus seeds 1-2 were owed; lap-table n read seed 0 only); no mark formula changed; tests S2 and FL added. New
  from_label.py rebuilds point-estimate results from the instance labels in case `cat` cannot copy files off the hosts.
- 23:35Z: one of the other session's A100s ended (burn ~$0.66/h). 23:48Z: stopped s0 (57556502) by hand, as planned:
  its stage 2 runs aplus and bplus first (MAXPAR=2), so t_s0 would start ~01:05Z and end ~05:00Z, which the credit
  ($1.23) cannot reach without a top-up; stopping it leaves the credit to s1 (t_s1 est. ~01:45Z, t1_s1 ~02:15Z).
  Vast shows cur_state stopped (billing stopped: burn fell to ~$0.54/h) but the host still reports running, and `cat`
  is refused until it does. a_s0 and b_s0 are kept on its disk and in its label.
- 00:17Z: s0's host finally reported it stopped (29 min after the stop). `cat` (Vast's command API) then failed the
  same way the log service does: the command's result URL stays S3 403 (the 21:00Z log request is still 403 at 00:25Z),
  so no file can be copied off these boxes. Results come back only through the instance labels (from_label.py):
  point estimates at 0.1-point rounding, no per-row hits, so no intervals, no M1/M2, no gates-off row check.
  s0 kept stopped (~$0.014/h storage) in case the upload path recovers.
- 00:26Z: the other session's last A100 ended; s1 is the only running box (~$0.2/h with storage). 00:35-00:38Z: the
  machine (54987, which also held s0) was offline for ~3 min; the job survived (its label kept updating).
- 00:41Z: s1 aplus_s1 done: validation 71.4, dev 86.5 (a_s1 65.8): 1,254 more LoRA steps alone add 5.6 points, so
  A_ref on seed 1 is ~71.4 and G needs S(8) >= ~74.4 there. aplus took ~2.7 h beside t (factor ~1.8 vs alone), so
  t_s1 is expected ~02:30Z and t1_s1 ~03:00Z.

## Deviations from PREREG (recorded before any t or t1 result exists)
- 2026-10-25 ~01:35Z: Ben is adding $50 of Vast credit. The PREREG budget line ($3.60 cap; seed 2 and tw on Ben's PC or a
  third 3090) is replaced by: seed 0 rerun in full and seed 2 on Vast, one A100 SXM4 40 GB box per seed (reliability >= 0.99,
  not machine 54987), all of a seed's arms on its box, so each seed is still on one GPU type in bf16. Reason: the first s0 box's
  files cannot be copied off its machine (only its labels: a_s0 67.0, b_s0 68.1), and A100s finish ~2-3x sooner than 3090s.
  Seed 1 stays on its 3090. The first s0 box's a_s0/b_s0 are reported as a same-seed rerun on another GPU type, not used.
- tw:0 runs on the s0 box instead of Ben's PC.
- bplus:2 runs on the s2 box speculatively, because its b_s2 adapter exists only there. It enters the analysis only if
  PREREG's bplus-extend rule fires on seed 0 (bplus_s0 - b_s0 >= 1.0); otherwise its result file is moved out of the
  result tree before summarize.py runs and is reported separately. bplus:1 would need b_s1's adapter, which is on the
  unreachable machine; if the rule fires it is rerun with b:1 on a 3090 and the rerun's b_s1 replaces the label one.
- 02:02Z: credit $50.49. Code 132623ff1 (think1.py, board.py, xent.py, run_box.sh identical to 5dc3b08ab):
  box 57595347 `claude-think1-compassionate-davinci-s0r` (A100 SXM4 40 GB, California, machine 149846, $0.416/h,
  10 h self-stop): THINK_JOBS=a:0,b:0,t:0,t1:0,aplus:0,bplus:0,tw:0 PARALLEL=1 MAXPAR=4;
  box 57595348 `claude-think1-compassionate-davinci-s2` (A100 SXM4 40 GB, Netherlands, machine 133104, $0.736/h,
  10 h self-stop): THINK_JOBS=a:2,b:2,t:2,t1:2,aplus:2,bplus:2 PARALLEL=1 MAXPAR=4.
- 02:04Z: the two A100 boxes were destroyed after ~3 min (still loading; cost a few cents) on Ben's instruction to buy the
  most compute per dollar. Vast DLPerf per $/h among reliable (>= 0.99) offers: RTX 5090 ~380-424, RTX 3090 ~300-360 (but
  ~4x slower), RTX 4090 ~280, A100 SXM4 229 ($0.416) and ~130 ($0.736). Replaced (same code, MAXPAR=3 for 32 GB) by
  box 57595542 `claude-think1-compassionate-davinci-s2` (RTX 5090, British Columbia, machine 38389, rel 0.9984,
  $0.537/h with storage) and box 57595544 `claude-think1-compassionate-davinci-s0r` (RTX 5090, Sweden, machine 54650,
  rel 0.9924, $0.532/h). Deviation amended accordingly: seeds 0 (rerun) and 2 each on one RTX 5090 (the 2 cheapest
  5090s skipped for 8-10 GB of host RAM). Still before any t or t1 result.
- 02:09Z: box 57595542 (s2, machine 38389) never started its container (host GPU error "unresolvable CDI devices");
  destroyed. Seed 2 relaunched on box 57596004 `claude-think1-compassionate-davinci-s2` (RTX 5090, South Korea,
  machine 145158, rel 0.9976, $0.497/h), same pack. vast.py now skips machines 54987 and 38389.
- 02:19Z: box 57595544 (s0r, Sweden, machine 54650) showed no state at all for 15 min; destroyed. Seed 0 relaunched on
  box 57597017 `claude-think1-compassionate-davinci-s0r` (RTX 5090, South Korea, machine 143234, rel 0.9982, $0.497/h),
  same pack. 02:18Z: s2 (57596004) is running its job loop (label has the "|" suffix).
- 02:27Z: the first s0 box (57556502, stopped, machine 54987) destroyed to stop its storage charge; its files could not be
  copied off that machine, and its label numbers (a_s0 67.0 / repeat 67.0 / dev 81.3; b_s0 68.1 / 1-pass 58.7 / dev 82.0)
  are recorded above. Logs work on the new 5090 hosts (served in ~24 s). Other sessions also started boxes on the account.
- 03:04Z s2 a_s2 66.7 (dev 80.9); 03:19Z b_s2 66.8 (1-pass 58.5, dev 82.1): stage 1 on a 5090 took 50 / 65 min side by
  side (~2.4x the 3090). 03:27Z s0r a_s0 67.2 (repeat 67.0, so eval noise 0.2 on this GPU; dev 81.5) vs 67.0 on the
  first s0 box (3090). Projected: s2 done ~05:45Z, s0r ~06:30Z. s1's t_s1 not in yet at 03:29Z (5.5 h after start).
- 03:57Z: s1 t1_s1 (3090) L0 65.9, L1 65.9, L8 66.0, dev L1 81.3. t_s1 still running (6 h); the box's run_box.sh is killed
  by its own timeout at ~06:45Z (12 h - 10 min after start), and t's eval (8 lap settings + lesions on 8,675 rows) may
  not end by then on a 3090.
- Deviation, 04:20Z: seed 1 is rerun in full on an RTX 5090 (box below), like seeds 0 and 2, and that run is the one
  analysed for seed 1 whatever its numbers. Reasons, neither of them the values seen so far: (1) the 3090 box's files
  cannot be copied off its machine, so seed 1 would have no per-row hits, and summarize.py then has no intervals and no
  M1/M2 for any seed; (2) t_s1 may be cut by that box's timeout. The 3090 seed-1 numbers (a 65.8, b 66.5, aplus 71.4,
  t1 65.9, and t if it finishes) are reported as a same-seed rerun on another GPU type. bplus:1 runs speculatively under
  the same rule as bplus:2. All three analysed seeds are then on RTX 5090s.
- 04:20Z: box 57609457 `claude-think1-compassionate-davinci-s1r` (RTX 5090, South Korea, machine 149008, rel 0.9946,
  $0.522/h, 10 h self-stop): THINK_JOBS=a:1,b:1,t:1,t1:1,aplus:1,bplus:1 PARALLEL=1 MAXPAR=3 (same code).
- 04:27Z: box 57609457 (s1r, machine 149008) had no DNS inside the container (pip install failed after 5 retries);
  destroyed after 6 min. Seed 1 relaunched on box 57610141 `claude-think1-compassionate-davinci-s1r` (RTX 5090, South
  Korea, machine 150804, rel 0.9963, $0.536/h), same pack. vast.py also skips 149008 and 54650. The 3090 s1 box's
  machine went offline again at 04:27Z.
- 05:23Z s2 aplus_s2 70.6 (dev 86.7); 05:34Z t1_s2 L0 66.6 / L1 66.7 / L8 66.5 (dev L1 81.0); 05:37Z s0r aplus_s0 70.7
  (dev 86.7); 05:38Z s1r a_s1 66.0 (dev 81.3) vs 65.8 on the 3090.
- 07:05Z: the 3090 s1 box (57553052) reached its run_box timeout with t_s1 unfinished (label "DONE" and no t_s1 entry);
  destroyed. Its seed-1 numbers stay as reported above (a 65.8, b 66.5, aplus 71.4, t1 65.9); seed 1 is analysed from
  the 5090 rerun (57610141). 06:04Z s1r b_s1 65.9 (1-pass 57.1, dev 82.3). 05:47Z s0r t1_s0 L0 67.2 / L1 67.3 / L8 67.3.
- 07:09Z s2 bplus_s2 70.7 (dev 87.3); 07:40Z s1r aplus_s1 71.0 (dev 86.2); 07:58Z s0r tw_s0 L1 67.1; 08:13Z s0r bplus_s0
  71.5 (dev 87.7): bplus_s0 - b_s0 = +3.9 >= 1.0, so PREREG's bplus-extend rule fires and bplus_s1 / bplus_s2 (run
  speculatively) enter the analysis.
- 08:44Z: s2 DONE. t_s2: L0 66.8, L1 66.8, L2 66.8, L4 66.8, L8 66.8, L12 66.6, L16 65.8 / L24 65.8 (first 2,000 rows),
  swap8 66.5, mean8 66.5, rep1_8 66.8, gatesoff8 66.7, ref0 66.7; dev L0 81.0, L1 81.0, L8 81.2. Flat in laps and
  equal to a_s2 (66.7) and t1_s2 (66.7). 08:45Z: s2 box stopped by hand to copy its files.
