---
name: month-end-02c
description: 0.2c plan for Ben's 01:45 UTC 09-26 goal (joined proof run before 11:00 UTC): files, switches, cutoff rule, what is in/out
metadata:
  type: project
  modified: 2026-09-26T01:59:04.090Z
---
Ben /goal 01:45 UTC 09-26: "by 7am tomorrow [11:00 UTC], solve each problem ... $5 vast ai". Month-end owns problem #2 (refuses too much = 383) and the final joined proof 0.2c. See [[month-end-results]].

- Marks: artifacts/claude-e2e02c-20260926/PASSMARKS-02c.md (+ addenda). Rule: a fix joins only if its OWN registered test is a verified PASS by 07:30 UTC. Rows: sleep L1-L5, no-harm H1-H4 (bank D + chat vs G), conversation C1-C2, refuses-less Q1-Q2, creative K1-K2, memory Y1, milestone ME1 (edit asks), safety S1.
- Builder scripts/claude_e2e02c.py: switches MEM02C=20, ROUTE02C, SLEEP02C, READER02C="r319" ("r319c" only if lis-319c passes), FIX02C. Set at cutoff, then seal.
- Sleep in agent: scripts/claude_sleep02c.py (Fix sleep's copy-practice night on the agent's shared 1B; adapter02c.pt; SLEEP02C_ADAPTER loads it; never reloads over trained weights). Joins as a component only if dl-2 PASS; brd-5 = evidence for the same copy_examples, no code swap.
- Review fixes scripts/claude_fix02c.py (test 12/12): delivered history, route final-answer tail, heard date across restarts, one-row support counter (report only).
- Panels sealed: artifacts/claude-panel02c-20260926 (chat 7a6312d8…, creative 66188c9e…); bank D copied unread artifacts/claude-e2e331-bankD-20260925.
- Rental task handoff/held/rent-02c.md ($2.00, 2.75 h, stop by 10:50 UTC; DEV gate; needs lis-301 AND lis-319 readers). Director must OK then queue.
- Open (not in 0.2c): explicit routing states, per-claim evidence, durable store, chunking, reader evaluator relation bug (Reading), sleep rollback process.
- 03:20 UTC evaluator reply (sec 3/6/10): freeze adds MANIFEST-02c.md (write at cutoff), three labels (fixed in code / own PASS / joined PASS), params via scripts/claude_params02c.py (rent-02c step 7a; INCLUDE in SEAL-code). Queued sel-02d, log-02d, date-02d, sleep packaging split (Fix sleep owns packaging, Month-end the interruption test): design/v3/30-modes/02d-month-end-followups-2026-09-26.md.
- 02:18 UTC Ben asleep until ~11:00 UTC: no questions to him; take defaults and note them. Month-end defaults: a fix joins 0.2c only on its own verified PASS (dl-2 PASS -> SLEEP02C on); reader per Reading's whole-claim re-score, else lis-301; if vast credit < $3 at the cutoff, ask the Director to run rent-02c's steps on BensPC once rsn-358a frees it (same marks, same order), else report "not run" honestly.
- 03:35 UTC Fix sleep split agreed: sleep02c writes adapter02c.json sidecar (base fingerprint, code hash, adapter sha256, 10 check answers), refuses mismatched/torn loads; --check-activation = rent-02c step 4a (report only); selftest now 9/9 (e675f3631). Fix sleep owns scripts/claude_night.py packaging + interruption test later. dl-3 never swapped into 0.2c.
- 02:31 UTC brd-5 = INCONCLUSIVE (registered; artifacts/claude-brd5-20260926/VERIFY-brd5.md). Nothing joins 0.2c from Creative. For the cutoff addendum (description only): at equal size, 20 won puzzles repeated dropped fresh coverage below base (83-97 vs 123 of 240); one hit per won puzzle raised it (136-145). sleep02c already uses one example per puzzle (D1.copy_examples, unchanged).
- 02:50 UTC bm-397 = registered FAIL (LoCoMo F1 +0.28, mark +5): TRIM02C stays False. Problem #4 (answers too long) listed open in the 0.2c report.
- 04:00 UTC Director: vast credit ~$2.60 projected. rent-02c gate lowered to $2.30; BensPC backup handoff/held/006k-02c-benspc.md (Director releases only on LOW-CREDIT; BensPC free ~06:00). Seal SEAL-code before either runs.
- 04:37 UTC Reading: lis-319c-full = registered FAIL (F2: 0.98 wrong saves 7/239 vs 5 at 0.995). READER02C stays "r319" (whole-claim diag: 65 right, 1 wrong of 240; H3 holds). Report: on the fresh 319c panel 0.995 makes whole-claim wrong saves on 5/239 (~2%, mostly wrong relation). Note checker (006i) verdict pending. Problem #1 (saves too little) and #3 (notes) likely stay open.
- 05:25 UTC FROZEN + SEALED (b89c105c3, 347 lines; MANIFEST-02c.md). Rentals can't take readers (Mac->vast 0.37 MB/s; rent-382b INCOMPLETE, only T ran; rent-02c-dev never reached its gate). X = G + sleep + lis-319 @0.995 + F1; MEM/ROUTE off (no 382b/383 verdict). Run = 006k on BensPC from ~06:00 (Director queues). Expected: Q1, Y1 unlikely -> 0.2c likely FAIL overall; the sleep and no-harm rows are the information. #2 (383) still needs its own run (reader staged from BensPC, or after 0.2c).
- 05:45 UTC: SEALED files include PASSMARKS-02c.md, MANIFEST-02c.md and the 382 PASSMARKS: NEVER append to them before the runs finish (use a separate ADDENDUM file). rent-02c moved to held/superseded; 006k queued by Director (f4cfe6d64); 007b-382b-benspc held (rest of 382b/383 after 0.2c, T reused). Seals re-checked OK on builder-outbox+main at 05:45.
- 05:19 UTC rd-371b note checker = registered FAIL (kept 1 of 132 good notes at 0.98; C2). Out of 0.2c (already frozen without it). Reading: #1 and #3 end as FAILs tonight.
