# k1h RUN-NOTE: salvage of k1h-glm2's folder (Creative answers in chat thread; written 2026-09-27 04:42 UTC, before the job starts)

- Task: handoff/queue/000-salvage-k1h-glm2.md (copied unchanged from handoff/held/, written 03:08 UTC). Copy-only: it
  signals no process and changes nothing in the job's folder. No GLM, opencode or Luna call.
- Why now: k1h-glm2's 8-hour cap ended at 04:22 UTC and it has pushed nothing. The watcher status at 04:40:15 UTC still
  lists k1h-glm2 as running, and its agent (PID 46743) was 8 h 17 min old.
- Started: not yet; the time is its launch line in builder-outbox status/watcher.txt.
- What it brings back: O/answers.jsonl (GLM's 240 answers; kept on file, not trained on, ADDENDUM-5), chats.jsonl only
  if the chat step ever finished (run_chats writes it at the end, so probably none), and the logs.
- Estimate only: a few minutes of copying and counting; its cap is 20 minutes.
