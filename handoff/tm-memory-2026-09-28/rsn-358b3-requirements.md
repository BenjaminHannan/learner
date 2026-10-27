---
name: rsn-358b3-requirements
description: Everything agreed for the 358b3 chat-puzzle gate (loop reasoner answering grid puzzles asked in chat) before it is sealed, as of 15:22 UTC 09-26
metadata:
  type: project
  modified: 2026-09-26T15:22:24.138Z
---
358b3 is the 0.2d headline gate H-A. Seal it after a loop design has its own verified PASS (358i or 358t).

- **Net:** a loop net with a verified PASS. Talker = plain MiniCPM5-1B, adapter OFF (Month-end).
- **Grid reading by code (358b2 lesson):** in 358b2 the 1B copied only 25/39/28 of 100 exactly (it drops "_"). The Thread manager (15:22) requires:
  (1) the marks disclose that code parses the grid and the 1B does not copy it;
  (2) the blind writer owns the panel wordings, never fitted to the parser;
  (3) a parser miss or misparse counts as a failed item for the build arm;
  (4) the grid format is agreed with Plain-English puzzles (cse_0168iLXHqs7XrkFePoRbNPSR), whose shared reader rt-02g fires on 15/55 lookalikes; the reader's false-fire count is a reported row.
- **Manager's 15:25 correction:** (a) the marks call the parser "a hand-written stand-in for the learned reader, used so the test isolates the reasoner"; (b) the marks say which steps are the 1B (rt-02g pattern: the 1B decides "is this a puzzle") and which are code (reading the grid and checking it against the message); (c) one line saying a learned grid reader is still owed after 358b3, and who takes it (asked Plain-English puzzles to own it).
- **15:40 Plain-English puzzles owns the shared reader + the learned grid reader after 358b3.** New scripts/claude_puzzle_reader.py read(text) returns {kind:"latin",size,grid,clash}; code detects and reads grids, and the 1B only writes the reply (their 1B decider got 15/55 on sum lookalikes at f7c75aeec, withdrawn; report it as that). Broken square: clash:true, reply "no finished square", net not called. PIN scripts/claude_puzzle_reader.py @3de583312, read_latin().
- **Panel:** scripts/claude_rsn358b3_panel.py make(seed) writes panel {id,message} and answers, with "broken" lookalikes. Seed chosen at sealing; not 35900-36000 and not 47311 (Month-end's row A panel).
- **Rival arms** use Benchmarks' harness scripts/claude_bmriv_rivals.py (38c370465): GENERAL_SYSTEM, the message verbatim, greedy, thinking off, 512 tokens, output {id,reply}. Arms: plain MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B, plus Qwen thinking-on (report only). These run on MY 358b3 rental, billed to Sleep research.
- **Smoke:** Benchmarks' smoke run on seed 36000 (rent-bmrivsmoke). Check the parser on the real rival replies before sealing.

Related: [[reasoner-exit-rule]], [[ben-talks-only-to-thread-manager]].
- (not 358b3) 358x carry-over test v2 SEALED 965d9b2c2 (steps-to-bar primary) for Ben's 15:41 goal: 358i nets vs fresh on mazes, 4k steps; job HELD handoff/held/claude-sleep-358x.md ($0.60) for Ben's yes + 358i ckpts on Mac.
- 16:35 smoke 1: rivals need 4,096 tokens (16,384 for Qwen think, report only); scorer now takes the FINAL grid (last run; markdown tables), cut-off/missing never right (a2dc051fe). Cost ≈ 2.7 GPU-h per 60 items with the think arm. Smoke 2 (whole replies) pending → parser check.
- 17:12 09-26: smoke 2 found 4 scorer bugs, fixed 92fed38a8 (qwen 1/7 -> 5/7 true; plain 0/8, lfm 0/8). Seal 8,192 tokens for thinking-off arms, hit_max reported, capped = never right.
- Thinking budgets (the Thread manager asked for this to go in the PASSMARKS): the loop gets <= 48 rounds, about 4e10 FLOPs per 7x7 answer; Qwen at 8,192 tokens gets about 3e13, roughly 1000x more. Report the loop's rounds used and each rival's tokens used, so that a loop win can't be put down to budget.
