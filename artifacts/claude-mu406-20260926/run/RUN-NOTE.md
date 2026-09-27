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
