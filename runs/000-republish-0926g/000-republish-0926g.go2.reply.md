Republishing skipped results — verifying the watcher and queue state.
2 markers removed at 16:18:18Z. Waiting for watcher rounds, polling builder-outbox.
All verified. Writing the follow-up report as a new file (existing REPORT.md left untouched per additive-only rule).
VERDICT: PASS — every job skipped by the old publish is now on builder-outbox, byte-for-byte verified for rent-02dr (25/25 sha256).

Marks table (integer counts):

| mark | asked / expected | got |
|---|---|---|
| watcher has `git add -f -- "$p"` in publish() | 1 | 1 (line 36, confirmed) |
| watcher handles `PUSH to builder-outbox:` / `PUSH (builder-outbox):` forms | 1 | 1 (self-updated 12:14 local, `^PUSH[^:]*:`) |
| .pushed files audited (modified 2026-09-26) | all | 41 |
| .pushed markers removed by this agent | only qualifying | 2 (rent-02dr, rent-bmrivsmoke) |
| rent-02dr files on builder-outbox after wait | 24 data | 25 (24 data + 1 RESULTS) |
| rent-02dr sha256 worktree-vs-outbox match | 25 / 25 | 25 / 25 |
| rent-bmrivsmoke files on builder-outbox after wait | 7 | 7 |
| rent-ch403 files on builder-outbox (h-agent's removal, verified) | 9 | 9 |
| rent-sf401 files on builder-outbox (h-agent's removal, verified) | 16 | 16 |
| copy-back manifest file found by name | — | 0 (reply claims 24/24 at copy time; current 25/25) |
| rentals | 0 | 0 |
| result file contents opened | 0 | 0 |
| TEST-ONLY panels read/tuned/quoted | 0 | 0 |
| disk free (GB, start/end) | ≥3 | 53 / 53 |

Every move: (1) confirmed watcher fix + self-update; (2) re-audited 41 jobs — 35 already equal on outbox, ch403 already landed by h-agent's 12:16:57 republish, sf401 marker already removed by h-agent, 6 left alone with nothing publishable from this Mac (q404, rd378L, mu404-run, 006k-run02c, 006m empty, 358i no PUSH lines; 006h/006i prose fragments, real path 8=8); (3) removed exactly rent-02dr.pushed + rent-bmrivsmoke.pushed at 16:18:18Z; (4) waited ~3 min — watcher republished 02dr 12:19:22, bmrivsmoke 12:19:25, sf401 12:19:29; (5) verified counts on origin/builder-outbox; (6) sha256-compared all 25 rent-02dr files worktree-vs-outbox as hashes only; (7) wrote 1 NEW file artifacts/claude-republish-20260926g/FOLLOWUP.md (84 lines).

Every miss: 0. Nothing skipped remains unpublished.

Deviations (2): REPORT.md already existed from the cut-off agent, so per additive-only I did not touch it and wrote FOLLOWUP.md instead (file placement only); OPUS-RULES.txt not found at the tasked scratchpad path, followed the quoted key points (inherited from go1).

What it means in plain English: the old publisher was skipping results because it didn't recognize some jobs' "PUSH…" lines. It has since updated itself and now understands them. I re-queued the last two stuck jobs, and all four (02dr, bmrivsmoke, ch403, sf401 — 57 files total) are now published, with 02dr's copies verified identical. What it doesn't mean: I didn't look at any result contents, didn't score anything, and didn't check whether the results themselves are right — only that every file arrived intact.
