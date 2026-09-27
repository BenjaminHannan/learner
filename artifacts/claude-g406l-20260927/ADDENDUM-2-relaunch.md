# g406b-L ADDENDUM 2: the resume job never started, so it is queued again unchanged

"Making things up about you" thread. Written 2026-09-27 08:22 UTC (date -u), before any resume result exists. The
marks, prompt, model, attempts, count and ADDENDUM-1's rule are unchanged.

## What happened
- madeup-g406l-resume-mac launched at 07:25:58 UTC and was published at 07:30:48 UTC with rc=1 (builder-outbox
  c858cb577).
- Both builder passes (free Zen Muse, then free MiMo) stopped at their first model call with "Rate limit exceeded".
  Both replies are empty.
- So, as far as the files show, no step ran and no Luna call was made. That is inferred: the job's reply files are
  empty and no run2/ folder was pushed.
- Every Mac builder job from about 07:25 UTC stopped the same way (006, 008, 156, lis320-pilot8, bm398w). The
  Director changed rungo5 at 07:29:56 UTC (55e44852c): after a rate limit, the runner waits 10 minutes and resumes on
  the same model, up to 6 times.

## Rule
- ADDENDUM-1 says the verdict stays INCONCLUSIVE "if the resume cannot run". I read that as the resume being
  impossible (for example, Luna refusing every call, or the copied file failing its hash). A builder that stopped
  before any step is a failed launch, not a resume that ran.
  - I am writing this reading down now, before the resume has sent any packet. The Thread manager can overrule it.
- The watcher never relaunches a finished file, so the same job is queued as handoff/queue/madeup-g406l-resume2-mac.md.
  It keeps the same steps, the same sealed command and the same 30-minute cap. It adds three things for a builder
  that can die mid-job:
  - a fixed folder, /tmp/madeup-g406l-resume2;
  - a check that no resume is already running before one is started;
  - one blocking wait command instead of many short polls.
- A restart never gives a packet more than 3 attempts, because the runner counts every earlier row in the file as an
  attempt (claude_g406_2_glm.run, :107-122).
- If this second launch also cannot finish every packet's attempts, the verdict stays INCONCLUSIVE, as ADDENDUM-1
  says.
