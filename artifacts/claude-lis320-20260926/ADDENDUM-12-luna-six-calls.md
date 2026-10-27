# lis-320 ADDENDUM-12: 6 parallel Luna calls from full-run chunk 2, with retry logging (reading thread, 2026-09-27 10:00 UTC)

The Director (09:56 UTC 09-27) raised lis-320's Luna share from 3 to 6 parallel calls from the next chunk on, on one
condition: if a chunk logs Luna rate-limit or usage errors, or the helper's retries climb, the next chunk goes back to 3
and the Director is told; each chunk prints its failed and retried call counts.

Changes, from chunk 2 on (chunk 1 was already queued with 3 calls and claude_lis320_luna2.py):
- LW=6 in the chunk job.
- Wording runs through scripts/claude_lis320_luna3.py = claude_lis320_luna2.py plus one "[luna-try] failed: <reason>" log
  line per failed helper try (claude_luna_codex.call retries up to 3 times silently). Prompt, writer, rows and checks are
  unchanged; the wrapper only observes each try's result.
- The CHUNK-SUMMARY line adds tries_failed (count of [luna-try] lines) and ratelimit (log lines matching rate limit,
  usage limit, quota or too many requests).
- Back to 3 (decided by code before the next chunk is queued): ratelimit above 0, or tries_failed above 5% of calls.
No mark, prompt, seed, check or writer changes. ADDENDUM-11's stop rule is unchanged.
