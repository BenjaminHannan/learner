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

## Addition (2026-09-26 23:32:07 UTC by date -u; the Thread manager's 23:32 points; judges were already reading, counts not shown to them)
- Controls reused byte for byte (judge/runs, gathered 23:25 UTC): talk_N.jsonl sha256
  1ed656f1749beeb4eabee778b6e32c213c7d3dfda3de1376cae815573293df76, talk_W.jsonl
  3a6a73409645e29ab9a88e4af7edf2911af56cb372facdc19fb29c3223aa7ce5, talk_H.jsonl
  d3466d7242db1784962120bbc7390ce8d1d277c5320d7a7211dd785b422b0884 (all equal to mu-405 run2 and to SEAL.sha256.txt).
- Reading of the ask counts under the sealed marks (code counts; blind recount by a fresh agent with its own script
  matched: U 12, W 4, N 0 of 60; per chat U right and W wrong 10, W right and U wrong 2):
  - VB met: 12 >= 0 + 10. So Q3 is live and is decided by the judges.
  - R NOT met: 12 < 4 + 10 = 14. Its sign test would pass (10 vs 2, one-sided p 0.0193), but R needs both, so R is
    FAIL, not proved wrong (12 > 4). P405b.1 (VB and R PASS) cannot pass.
  - Plain words: moving the block into the user message took the 1B from 4 to 12 of 60 remembered facts; better, but
    short of the gain fixed in advance, and still 48 of 60 missed.
