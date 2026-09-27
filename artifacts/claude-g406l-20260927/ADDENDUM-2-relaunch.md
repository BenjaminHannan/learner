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

## Limit (added 08:23 UTC, date -u, after the Thread manager's review; still before any resume result)
- The Thread manager agreed with the reading above, on one condition, so a relaunch cannot become retry-until-it-works:
  - at most 2 more launches of the resume after the failed first one: madeup-g406l-resume2-mac, and at most one
    more after it;
  - no launch after 16:00 UTC on 2026-09-27.
  - If neither of those launches finishes every packet's attempts, the verdict is INCONCLUSIVE.
- Every launch that made no Luna call is listed with its rc in the run note and in VERIFY.md. The job's own
  RESULTS.md cannot see earlier launches. The first such launch was madeup-g406l-resume-mac, rc=1 (c858cb577).
- This section replaces the last bullet under "Rule" above: one more launch after resume2 is allowed, within the limit.
- Correction: this heading first read "08:26 UTC", which I typed ahead of the clock. date -u read 08:23:30 UTC. The
  Thread manager's note says 08:27 in its text, but it arrived at 08:23:02 UTC (commit ad1933437 had the wrong stamp).

## Route change (08:44 UTC, date -u; still before any resume result)
- The watcher held madeup-g406l-resume2-mac on its builder cap from 07:4x UTC onward (6 builders running at 08:42 UTC).
  It never launched, so I moved it to handoff/held/. A job that never launched is not a launch.
- The same steps now run as handoff/queue/madeup-g406l-resume3-mac.md on the Director's BASH-ONLY route (2bf4f9ea7).
  That route runs the job's bash block with no builder and skips the builder cap, as the Thread manager suggested at
  08:38 UTC. It keeps the same sealed command and the same checks: start hash, seal, 4 selftests, one Luna call at a
  time, a 30-minute runner cap and a stop by exact PID at 60 minutes.
  - If resume2 somehow launched first, resume3 stops before step 1. The job checks for resume2's .running, .exit and
    .pushed files, and for any g406l run already going.
- Count under the limit: resume3 is launch 2 of the resume. At most one more launch is allowed, and none after
  16:00 UTC.
- I dry-ran the block here in a temporary worktree of main, with local stand-ins for uv and codex. It ran end to end
  with rc 0. Its numbers came from a fake labeller and were deleted unread beyond the rc.
