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
