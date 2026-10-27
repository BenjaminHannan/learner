# mu-406 run note ("Making things up about you")

Times are from date -u. Plan and marks: ../PASSMARKS.md, sealed in ../SEAL.sha256.txt (fb92c1dee).

- 2026-09-27 09:59:41 UTC: sealed at fb92c1dee (30 files). Step 2 queued as handoff/queue/madeup-mu406-panel-mac.md
  (e18863022): the 60-chat test panel plus 3 smoke chats, Luna at 2 calls at a time. Launch 1 of at most 3 for this
  step. No mu-406 chat, reply or adapter exists yet.
- Launch 1 of madeup-mu406-panel-mac ran 10:01:23-10:22:50 UTC (its RESULTS.md), rc=0, pushed to builder-outbox.
  Seal check OK for all 30 files, 3 selftests ok. Luna wrote 78 of 78 chats on the first pass in 20.7 minutes (0
  errors). select: 60 panel + 3 smoke. Scan: 0 hits; 25 user messages appear in 3 or more chats (max 12). Counts
  only; I did not read the panel's rows.
- 2026-09-27 10:46:49 UTC: panel copied to main and sealed in ../SEAL-panel.sha256.txt (items, facts,
  facts_all, raw). Step 3 (practice chats) moved from handoff/held/ to handoff/queue/.
- 2026-09-27 10:47:41 UTC: step 3 queued as handoff/queue/madeup-mu406-practice-mac.md. The panel job ran
  at about 16 s per chat with 2 calls at a time, so the practice job writes the first 240 of the 260 sealed
  candidates in id order and stops itself at 50 minutes. The selection is unchanged: select keeps the first 220
  that pass, in id order, so a later candidate could never be chosen while 220 of the first 240 pass. A second
  launch (new file name) seeds raw.jsonl from builder-outbox and writes only what is missing. If fewer than 220 of
  the first 240 pass, a later launch writes candidates 241-260.
- 2026-09-27 10:49:28 UTC: ADDENDUM-1-launches accepted by the Thread manager. Each launch line below gives rc,
  chats added and time per chat.
- Time per chat so far: panel launch 1, 78 chats in 20.7 minutes at 2 calls at a time = 15.9 s per chat.
- Step 3, launch 1 (madeup-mu406-practice-mac): 10:50:22-11:43:55 UTC, rc=0. The writer stopped itself on time at
  53.4 minutes: 168 chats written, 167 passed the checks (1 failed "value_in_chat2" after 3 attempts). 19.1 s per
  chat (slower than the panel's 15.9). select stopped as expected: 167 passing, 220 needed. Scan: 0 hits.
- 2026-09-27 11:51:10 UTC: launch 2 queued as handoff/queue/madeup-mu406-practice2-mac.md (same block; it seeds
  raw.jsonl from builder-outbox, writes the remaining 72 of the first 240, and keeps its own RESULTS-2.md and
  write-2.log). Progress launches so far for step 3: 1 of at most 6 (ADDENDUM-1).
- Step 3, launch 2 (madeup-mu406-practice2-mac): 11:52:12-12:11:30 UTC, rc=0. Seal check OK for all 30 files, 3
  selftests ok (the "timeout after 300s" line in RESULTS-2.md is the Luna selftest's own failure-path case; it is
  in launch 1's RESULTS.md too). It seeded 168 chats from builder-outbox and wrote the other 72 of the first 240 in
  18.7 minutes: 71 passed, 1 failed "value_in_chat2" after 3 attempts. 15.6 s per chat. In all, 238 of 240 pass.
  select: 200 training chats + 20 held-out (seed 4062); 0 held-out ids in the training set. Scan: 0 hits; 68 user
  messages appear in 3 or more chats (max 33). Step 3 done in 2 launches (2 of at most 6, ADDENDUM-1).
- 2026-09-27 12:41:42 UTC: practice/ copied from builder-outbox to main (counts only; I did not read chat text). Overlap
  (report only, scripts/claude_mu406_prep.py overlap; user messages matched after strip and lower-case):
  - 200 training chats vs the 63 panel chats: 80 shared user messages; 196 of 200 training chats share at least one.
    By place (turn count): session 1 81, small talk 174, ask 140, feelings 2, advice 1, follow-up 1.
  - 20 held-out chats vs the panel: 22 shared messages; 20 of 20 share one. Session 1 8, small talk 18, ask 10.
  - Panel vs the 200 training chats (the direction PASSMARKS' seen-ask-line split uses): 63 of 63 panel chats
    (3 are smoke) share a message; 56 of the 63 ask turns match a training user message. The judge's split
    (claude_mu406_judge.py:158, same strip and lower-case match) scores the 60 non-smoke chats, so it will have 53-56
    seen and 4-7 unseen: too few unseen to test the "seen wording" worry. It stays report only, as sealed; any M2
    pass is read with this in mind.
- 2026-09-27 12:41:42 UTC: step 4 (teaching replies) moved from handoff/held/ to handoff/queue/ as madeup-mu406-teach-mac.md
  (launch 1, L=1): 220 chats, 1,100 turns, held-out first, 2 calls at a time, the writer stops itself at 50 min.
- Step 4, launch 1 (madeup-mu406-teach-mac): ended about 12:49 UTC, rc=5, 0 chats written, 0 Luna calls. The code
  seal passed (30 of 30 OK), then the panel seal check failed: SEAL-panel.sha256.txt lists paths relative to
  artifacts/claude-mu406-20260926 and the job ran shasum from the temp root, so it could not find panel/*.jsonl.
  My path bug in the job block; the panel files and their hashes are unchanged. This counts as a no-progress
  launch (1 of 2 in a row allowed, 1 of 6 in all, ADDENDUM-1).
- 2026-09-27 13:54:56 UTC: launch 2 queued as handoff/queue/madeup-mu406-teach2-mac.md. Same block with the panel check run inside
  the folder, L=2, a new temp folder, and launch 1's leftover temp folder removed. Dry run here up to the write step:
  both seals OK (34 lines), teach selftest 9/9, 220 chats and 220 facts rows in order. The Luna helper selftest
  needs the Mac's codex binary and was skipped in the dry run only.
- Step 4, launch 2 (madeup-mu406-teach2-mac): 13:58:09-14:50:33 UTC, rc=0. Seals and both selftests ok. The writer
  stopped itself on time at 51.8 minutes: 92 of 220 chats written, all 92 whole, 460 turns, all 460 passed on the first
  try, 0 fails, 0 stops. Median 59.5 s per chat (2 calls at a time), 33.8 s of wall time per chat. Progress launch;
  launches so far for step 4: 2 of at most 6 (ADDENDUM-1).
- 2026-09-27 15:36:52 UTC: launch 3 queued as handoff/queue/madeup-mu406-teach3-mac.md (same block; L=3, new temp folder; it seeds
  teach.jsonl from builder-outbox and writes the remaining 128 chats; at this rate about 72 minutes, so a launch 4
  will likely be needed).
- Step 4, launch 3 (madeup-mu406-teach3-mac): writer 15:38:29-16:31:01 UTC, rc=0, stopped itself on time at 52.1
  minutes. Total 160 of 220 chats (68 added), all 160 whole, 800 turns; 799 passed on the first try and 1 on a retry
  (1 "too_long" attempt); 0 stops. Median 57.9 s per chat (2 calls at a time), 46 s of wall time per added chat.
  Launches so far for step 4: 3 of at most 6.
- 2026-09-27 16:46:50 UTC: launch 4 queued as handoff/queue/madeup-mu406-teach4-mac.md (same block, L=4) for the last 60 chats.
- 2026-09-27 16:50:16 UTC: teacher gate started while launch 4 writes the last 60 training chats. The gate reads only the 20
  held-out chats, which launch 2 wrote whole and later launches never touch (teach_runs uses only the items given), so
  its result cannot change. Read from teach.jsonl at builder-outbox 120ebdb05 (160 rows, sha256 091038f535170634...; all 20 held-out
  chats whole, 100 turns). gate-prep wrote gate/packets/b1-b2 (20 packets each) and gate/keys/key.json; judge files
  match SEAL lines 3-4; 4 fresh blind judges in private folders (claims b1, claims b2, fit b1, fit b2).
- 2026-09-27 16:51:39 UTC: teacher gate PASS (gate/gate.json; complete, 2c2f on all 20 chats, 0 bad rows). G1 claim flags summed
  over both claims judges 2 of 200 (bar 6); flagged by both 0, by either 2 of 100. G2 on-turn by both fit judges 80
  of 80 (bar 72). G3 real answers by both 20 of 20 (bar 16). A separate count straight from gate/out agrees.
- Step 4, launch 4 (madeup-mu406-teach4-mac): writer 16:47:34-17:27:36 UTC, rc=0, stopped itself when done (40.0
  minutes). Total 220 of 220 chats (60 added), all whole, 1,100 turns; all 300 new turns passed on the first try
  (1,099 of 1,100 overall, the 1 "too_long" retry was launch 3's); 0 stops. Median 56.9 s per chat (2 calls at a time),
  40 s of wall time per added chat. Step 4 done in 4 of at most 6 launches (1 without progress).
- The 160 chats the teacher gate read are unchanged in the final teach.jsonl (160 of 160 rows byte-identical,
  including all 20 held-out chats), so the gate result (5d592c0f4) stands for the final file.
- 2026-09-27 17:56:16 UTC: step 6's rows built here (claude_mu406_train.py rows, code only): 200 training chats, 1,000 rows (200 per
  turn kind), 20 held-out chats excluded. PASSMARKS needs at least 800 kept turns before the dev split: 1,000. A $0
  length check: the longest row is 2,581 characters of JSON (median 1,560), so the 1,536-token cut should drop none
  (inferred from characters; the rental's training log counts the real drops).
- SEAL-data.sha256.txt: teach/teach.jsonl, train/rows.jsonl and ADDENDUM-2-vast.md (repo-root paths).
- 2026-09-27 19:29:52 UTC: mu-406 WITHDRAWN before step 6, with no GPU run and no money spent, so it has no verdict. Ben chose the LFM2.5-1.2B
  talker at 19:27 UTC (Thread manager), so a MiniCPM5-1B adapter would not load in 0.2d. The reason for no LFM
  follow-up is c1-dl (artifacts/claude-c1dl-20260927/RESULTS.md:34-35, a side count from pair judges):
  - flags for made-up user details: LFM with the W block 3 vs plain LFM 3, 4 vs MiniCPM's 17, 5 vs Qwen's 30 per 60
    DEV chats;
  - ask_known right: 6 of 8 with the W block, 4 of 8 without it.
  So on LFM, usable memory did not raise the made-up count, which was mu-405b's failure on MiniCPM. The held jobs
  rent406-* go to handoff/held/superseded via the Director. The gate, rows and kit stay as records.
