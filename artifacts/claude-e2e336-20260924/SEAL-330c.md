# 330c sealed for 336 (month-end thread, 2026-09-24 ~18:55 UTC)

P in 336 is scripts/claude_e2e330c.py:build_330c as of main 7db5b1e1b / builder-outbox at that time, run through
scripts/claude_twinb_wrap.py (so T is twin b). Layers, inner to outer:
330a_334 (292t -> 298 -> 274 listen-first -> listener stack G b -> 274 reply-first -> 334 sleep agenda)
-> 333d creative -> think299b -> 338b chat -> vary330c -> nb-323 turn log.
Every module the run imports (223 files, found by running build_330c through the 336 harness on a DEV life with a
stub reader and stub 1B, plus the reader's own two modules) is hashed in SEAL-code.sha256.txt, computed on the
combined tree (git archive builder-outbox, then main on top). The rental checks it with `sha256sum -c` before running;
any mismatch stops the run.
Registered status of the parts: 298, 299b, 333d (pending), 338, 339 (not joined) are registered FAILs or pending on
their own marks; nb-323 and own-M1v verdicts are not in (the mouth is not joined). 336's marks are unchanged
(PASSMARKS.md), with twin b as T (PASSMARKS-addendum-twinb.md).
Dress rehearsals on DEV (report only): rent-330c-dev, -dev2, -dev3 (final form: 2 wrong candidates of 71 asks,
facts saved 49/131, day-1 facts kept 30/30, clarify 13/194, most common reply 10/194, ms median 792).
Bank: artifacts/claude-e2e331-bankA-20260924 (TEST-ONLY, copied unread from escrow; hashes match the escrow SEAL).
