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
