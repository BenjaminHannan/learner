# mu-405b arm U: run counts (written 2026-09-26 23:25:00 UTC by date -u, before any judging)

- Exit: "U exit 0 23:24:32" (run/exits.txt); started 22:39:09 UTC (run/started.txt); 0 tracebacks in run/logU.txt.
- talk_U.jsonl: 300 rows, all session 2, 60 chats, 60 asks; 0 empty replies; 0 <think> leftovers; median 7162.7 ms per
  reply. sha256 dbbe502e5bd84036a5521de81b53dd2f724722a208d3d638f870a888882a93c3.
- Stored-fact asks right (code, the sealed ask_right): U 12 of 60. Controls from mu-405 run2: N 0, W 4 (H 1, report
  only). Blind recount follows before any verdict is reported.
- Deviation: run/logU.txt ends at "(55/60)" and has no final JSON line. The thread committed logU.txt at 23:20 UTC while
  the run was still writing it (RUN-NOTE, 2a56c7428); the next git pull --rebase replaced the file on disk, so the
  last 5 progress lines and the JSON line went to the replaced copy. talk_U.jsonl was written fresh at the end and is
  complete; the counts above come from it. Lesson: never commit a log that is still being written.
