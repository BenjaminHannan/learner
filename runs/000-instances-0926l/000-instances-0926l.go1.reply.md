Cleaning up the stray instance — verifying rules and system health first.
Report written. Pushing as instructed.
Commit is now clean. Restoring the pre-existing staged state:
Index restored to its prior state; my commit contains only the new report. Push was attempted but the environment denies all `git push*` calls, so the commit waits locally. Final report:

---

**REPORT — vast instance check (2026-09-26 20:05 UTC task)**

1. **Instances** (`vastai show instances --raw`, checked Sat Sep 26 20:01:37 UTC 2026) — 2 instances, integer count 2:
   - id **52755827**, label `claude-director-depot`, actual_status **exited (stopped)**, dph_total **0.11361111111111112**, start_date **1790430329.5646422**
   - id **52799251**, label `claude-fixsleep-dl7b`, actual_status **running**, dph_total **0.41666666666666663**, start_date **1790448172.1066332**
2. **Instance 52807320 (`claude-sleep-358t3`): NOT present** — already gone. No destroy command was needed or run. Nothing else touched: 52799251 and 52755827 undisturbed, zero destroys executed.
3. **User credit** (`vastai show user --raw`): **33.29925189036976**.

Artifact: `artifacts/claude-instances-20260926l/REPORT.md` (new file, numbers only).

**Deviations (2, both reported):**
- (a) My first commit accidentally swept in 19 already-staged lines belonging to another agent (`artifacts/claude-rsn358i2-20260926/*`, 18 files + 1 ledger append). Caught on `git show --stat`, undone via `git reset HEAD~1`, recommitted with only REPORT.md (commit `ab09c935c`, 1 file, 17 insertions), and re-staged the other agent's files so the index matches its prior state exactly. No other-agent file content was modified at any point.
- (b) PUSH ordered but **not completed**: this environment denies every `git push*` invocation. Commit `ab09c935c` ("Add vast instance check report 20260926l") sits on branch `claude/card-experiment-handoff-7c5b27` (ahead 39); someone with push rights must push it.

Disk: 52 GB free at start. Key used only via env var, never printed.
