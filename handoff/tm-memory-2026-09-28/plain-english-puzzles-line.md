---
name: plain-english-puzzles-line
description: Plain-English puzzles thread (chat-typed puzzles never reach the slept skill): grid readers gr-1..gr-7 FAIL, gr-7d/gr-8 practice findings; gr-9 dev DEV-FAIL: held-out separators 94 vs 44 (all from the separator rows) but familiar squares 197/200; thread stopped by Ben 20:00 UTC 09-27
metadata:
  type: project
  modified: 2026-09-27T11:59:31.923Z
---
Thread "Plain-English puzzles" (cmsg_01FuvegZXjMmeUzStiEFVnEWAsTeKcqPMUJJnhbfaaQYSE). Problem: 0.2c lifted puzzle-format solves 74 -> 192 but chat-typed puzzles stayed 0/40. Reports go to the Thread manager (session_01T8RjGifsQdqHsTQnCvPjPr), never a thread reply; status line 1 says so.
- Sums line: rt-02h FAIL e62b1069e; rt-02h-T CONFOUNDED. GLM relabel deferred (TM 20:04).
- Grid line (for Sleep research's 358b3; read_latin in scripts/claude_puzzle_reader.py is a disclosed code stand-in). All $0 on container CPU; blind recounts under <exp>/recount/.
  - gr-1 FAIL 85/100. gr-2 FAIL (3 false; had U1 50/60). gr-3 FAIL. gr-4 practice 7/30.
  - gr-5 (LoRA reader 1B, VERIFY bb3bc66e2) FAIL R2 2 false; U1 40/60. gr-6 DEV-FAIL (1b519a88c).
  - gr-7 (gr-6 + 3 epochs; VERIFY 737d4c3f4) FAIL R2 2 false, R3 3 wrong, U2 5; U1 54/60 passed. gr-6 panel SPENT. Adapters gr5/6/7 in /mnt/project-files/plain-english-puzzles/ (gr-7 sha c8f95557...).
  - TM 07:38: never read a spent panel even as counts; use fresh code-made practice sets.
  - gr-7d (practice, RESULT 07ccf04be): distractor idea SUNK, lost-place PROVED WRONG; 11 of 16 wrong grids wrong SIZE.
  - gr-8 dev (size pick by total log-prob incl. EOS; RESULT c0dd55c54): DEV-FAIL; sizes 21 -> 7, wrong grids 37 -> 33. Seen seps 99/100, new seps 63/100.
  - gr-9 (owner chose separator variety; TM agreed the order 11:5x; TM said don't record it as the decider): SEALED 98b53d445 after TM review (added L7c control = gr-7 + 3 epochs on gr-6 rows only, report only; cousin list). Chain launched once 12:03Z on CPU; stopped 14:32Z by Ben's stop-all (ad05244ab), stop lifted 14:33; re-launched once as chain-r1.sh 14:37Z (3ecca9cc4, outputs run-r1/). RESULT 30def6482 DEV-FAIL (recount matches): held-out 94 vs L7 44 (+50; misses all 'none'); M2 squares 197/200 FAIL, M3 seen 97/100 FAIL (L7 had 96/99 on other items), M4 5 vs 8 pass. 4 wrong grids = row skips then padding (3 seen misses all format S00 with '- - -' dividers). L7c control (e9c9f5cc6): 44/100 = L7, so the +50 is the separator rows. Post hoc squares reads (0396f85ae) never ran. THREAD STOPPED 20:00Z 09-27 by Ben (he now runs cloud chats from prompts); trigger disabled; final report sent to TM. Ben's usage rule 14:34: research, launching tests, reading results only; no polling; TM messages only verdict/launch/blocker in <= 8 lines. Draft e7f28868f. scripts/claude_gr9.py: 59 marks split into families sharing no character (LOOKS lookalike map): dev 17 (dot/star/equals/colon-dash families), test 11 (seed 5091, reserved for a blind test), train 28. 300 sq + 80 near added to gr-6's 1072 rows; 3 epochs from gr-7. Greedy marks M1 held-out >= 90/100, M2 >= 199/200, M3 seen >= 98/100, M4 false <= L7+1; PROVED WRONG gain < 10; TOO-EASY if L7 >= 85. Design caveat: dot/star row errors 12/121 with adjacent blanks vs 0/87. ~7 h CPU in all.
- If a grid reader passes, it is offered to Sleep research as their own single change.
- door-1 (Ben's Mac agent) not on main as of 09-27 10:40.
LESSONS: review changes go in dated addenda; commit blind recount script+output; commit only finished run files; never print panel rows; check "first ever" claims against earlier VERIFYs; file times from date -u; never call a pattern from a few examples "mostly"; split held-out sets by shared characters, not strings.
**How to apply:** verify every run with a blind code recount before sending one line to the TM. See [[month-end-results]], [[sleep-research-line]].
