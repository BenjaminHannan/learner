# g406 ADDENDUM-2: the registered run launched on helper v1 (written 2026-09-26 20:04:04 UTC by date -u, before any GLM output is read)

- The Director reports (20:03 UTC message) that the Mac watcher launched claude-madeup-g406-mac at 19:34:54 UTC, right
  after the release in 857ca7eb9. That run is the registered g406 run. It uses exactly the sealed setup: helper v1
  (sha256 3b597086...), 4 workers, the fixed prompt, the sealed packets.
- The thread moved the task file to handoff/held/ at 20:01 UTC (abf546464) after the Director found that helper v1 leaves
  one opencode session behind per call, and that commit says "no GLM call made". That was wrong: the run had already
  launched about 26 minutes earlier. The hold changes nothing about the run already going; the held file is not
  requeued.
- Deviation from the Director's 20:00 budget: g406's share of the opencode route is 3 workers; this run uses 4 (it was
  launched before that budget was set).
- Nothing about the marks, the prompt or the count changes. If the run is stopped early, the partial glm.jsonl is
  copied back and a later task resumes it (the script skips packets already marked); the resumed part and its helper
  version are recorded in a further addendum before its output is read.
