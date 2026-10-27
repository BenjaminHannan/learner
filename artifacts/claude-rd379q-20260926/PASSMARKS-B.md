# rd-379q addendum B (registered 2026-09-26 ~14:30 UTC, before rd-379q ran and before rd-378L's result): report-only rescore on store v3

Why (thread manager, 14:22 UTC, checked in the code): rd-378L's scorer ranks with store v1 (claude_rd378L_recall.py:36
imports claude_ep382_store), while 0.2c ships store v3 (v2's '<speaker> said, "<text>"' ranking; heard-only recall by
default). A notes gain on v1 might not hold on v3's ranking.

Added (report only; the marks Q1-Q3 stay on v1 exactly as PASSMARKS.md says, and no verdict uses these numbers):
scripts/claude_rd379q_rescore_v3.py runs rd-378L's same score() with v3 swapped in and notes asked for explicitly
(sources = heard + note), on the same questions, writing to a separate folder:
- v3 store A (heard only) and store Q (heard + question notes);
- v3 store B (heard + rd-378L's fact notes), if rd-378L's notes.jsonl is on the Mac at ~/rd378L-private/notes.jsonl.
Reported: fused any@10 and anyT@10, overall and per category, for each store, next to the v1 numbers.

How it will be read (fixed now): if Q passes on v1 but on v3 Q's anyT@10 is below v3 A's + 2 points, the result reads
"question notes help the old ranking, not the shipped one", and they are not proposed for the build until a registered
v3 test passes.

SEAL-B.sha256.txt covers this file, the rescore script and store v2/v3, with everything SEAL.sha256.txt covers.
