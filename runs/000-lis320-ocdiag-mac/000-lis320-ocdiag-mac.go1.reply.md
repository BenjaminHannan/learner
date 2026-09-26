Diagnosing the dialog failures — capturing opencode traces for the four failed prompts.
Prompts are ready — now probing opencode with the failing inputs.
All 12 calls finished — now building the diagnostic report.
Report draft is clean — now cleaning up the test sessions.
Sessions cleared — now packaging the redacted logs for handoff.
Files secured — verifying the cleanup is complete.
Verdict: diagnosis complete. 12/12 opencode calls ran one-at-a-time, files in `artifacts/claude-lis320-20260926/ocdiag/`. Did NOT reproduce pilot3's `exit 1` — got 10x `exit 0` + 2x 300s TIMEOUT. No tool use, no error events in streams.

Common-rules compliance: additive-only (only created `artifacts/.../ocdiag/`), fictional names only (from seeds), TEST-ONLY panels never read, report here. `git fetch -q origin main` + `git archive`/`git show` only; no checkout/push. GPU: no, Mac CPU, 12 GLM 5.3 Flash calls one-at-a-time. Label lis320-ocdiag. No reader/rental/BensPC/OpenRouter. No opencode config/auth read/copied/committed.

TREE:
- origin/main rev `b82795bf04cd43b11adb2386cc45d26ca7f1554d`
- opencode `--version` `1.18.32`
- D=`/var/.../tmp.eAT49UEYAb` via `git archive origin/main scripts` + `git show origin/builder-outbox:artifacts/claude-lis320-20260926/pilot3/seeds.jsonl`

PROMPTS (`scripts/claude_lis320_glm.py --seeds seeds.jsonl --dry-run --dialog ID`):
- s320-321-00004: 4448 chars, 6 lines starting `-`
- s320-321-00001: 4756 chars, 6
- s320-321-00000: 5108 chars, 7
- s320-321-00002: 5283 chars, 6
- dry-run stderr all 0 bytes.

CALLS (fresh empty T, stdin /dev/null, 300s limit, PID kill on timeout):

| call | exit | sec | stdout B | stderr |
|---|---|---|---|---|
| A-00004 | 0 | 133.6 | 1130 | `> build · glm-5.3-flash` + ANSI, 35B |
| B-00004 | 124 TIMEOUT PID56057 | 300.0 | 250 (1x step_start only) | `TIMEOUT after 300s (killed PID 56057)` 38B |
| C-00004 | 0 | 159.5 | 965 | `> plan · glm-5.3-flash` 34B |
| A-00001 | 0 | 111.7 | 1323 | `> build` 35B |
| B-00001 | 0 | 112.0 | 2616 | 0B empty |
| C-00001 | 0 | 138.7 | 1531 | `> plan` 34B |
| A-00000 | 0 | 120.6 | 1592 | `> build` 35B |
| B-00000 | 0 | 87.9 | 2479 | 0B empty |
| C-00000 | 0 | 142.1 | 1239 | `> plan` 34B |
| A-00002 | 0 | 263.4 | 1891 | `> build` 35B |
| B-00002 | 0 | 250.5 | 2886 | 0B empty |
| C-00002 | 124 TIMEOUT PID72489 | 300.0 | 0 | `TIMEOUT...` + `> plan` 72B |

Full first-300-chars + last-30-lines stderr in REPORT.md. A/C stdout are dialog JSON (quoted GLM output, not Claude text).

B event streams:
- B-00004: lines=1 types=`{"step_start":1}` tools={} errors=none, usage=none (no finish)
- B-00001: lines=3 types=`{step_start:1,text:1,step_finish:1}` tools={} errors=none usage in=15719 out=6767 total=22486 cost=0.00574135
- B-00000: lines=5 types=`{step_start:3,text:1,step_finish:1}` tools={} errors=none usage in=15764 out=303 total=16067 cost=0.0025161
- B-00002: lines=3 types=`{step_start:1,text:1,step_finish:1}` tools={} errors=none usage in=15853 out=7609 total=23462 cost=0.00618245
- Tool-name query (`..|.tool?`) count 0 everywhere. No error-message texts. No JSON parse fails.

What this means in plain English: the same `> build` stderr line pilot3 saw on `exit 1` failures appears here on successes too — so that line is just normal opencode chrome, not the error. Failures here look different: slow/hung calls (2/12 hit 300s), not fast `exit 1`. Same prompt can succeed once (A-00004 133s) and hang next time (B-00004 timeout), so it looks flaky/slow, not a bad prompt.

CLEANUP (by id, one per command):
- worktree root: listed 22 total, 12 titles `lis320diag-*`, deleted 12, 0 left.
- fresh plain temp dir: listed 5 total, 0 matching, deleted 0, 0 left.

REDACTION: dropped 3 lines before repo copy (1 each from B-00000/B-00001/B-00002 `.jsonl` finish records matching sensitive-pattern rule). Dest verified 0 matching lines. Count in `REDACTED_COUNT.txt`.

COPY: `artifacts/claude-lis320-20260926/ocdiag/` has p_*.txt, A/C *.out, A/B/C *.err, B_*.jsonl (redacted), *.meta, rev/version, REPORT.md, CLEANUP_SUMMARY.txt, REDACTED_COUNT.txt (43 copied files).

TEMP DELETE: `rm -rf` exact D path + all 12 T dirs + fresh dir; confirmed gone (`No such file or directory`, no `ocdiag-T-*` left).

Misses/deviations: none. Did not push (watcher pushes).

PUSH: `artifacts/claude-lis320-20260926/ocdiag`
