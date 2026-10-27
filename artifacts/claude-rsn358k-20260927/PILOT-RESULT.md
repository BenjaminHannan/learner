# rsn-358k pilot result and steps (sleep research thread, 2026-09-27T16:13:56Z)

Rule (PILOT-RULE.md, sealed before any dev check): store dev q1 is 5/100 at step 8,000, under 30, so **the graded runs use 8,000 steps**, and RESULTS will say "the pilot never flattened".
- Store dev (q1, q2 of 100) at 2,000 / 4,000 / 6,000 / 8,000 steps: (4, 7), (8, 10), (5, 5), (5, 11). The best was (10, 13) at 2,500.
- No-store dev stayed at 0-3 on each (V's check).
- Logs: pilot/store-s17/train_log.jsonl and pilot/nostore-s17/train_log.jsonl.
- Restart note: the pilot with the dev check every 500 steps was stopped at about step 2,700 by Ben's 14:30 UTC stop of all threads (PIDs 21537 and 21538). It was rerun unchanged from step 0 (same seed, same command) at 14:37:54 UTC. Only the rerun's numbers are used.
- Reading, suggested and not graded: the store arm barely learns this task in 8,000 steps (training exact about 6-7%). G1 (store q1 mean at least 240/300) looks unlikely.
