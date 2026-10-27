---
name: month-end-results-log3
description: Month-end log 20:20 UTC 09-24 to 03:40 UTC 09-25: 336 and 336b registered FAILs, banks C/D, gram-360 PASS, sleep checkpoint lesson
metadata:
  type: project
---
Continues [[month-end-results-log2]]; current state in [[month-end-results]].
- **336 = registered FAIL** (~20:20 UTC 2026-09-24, main 219853633, artifacts/claude-e2e336-20260924/VERIFY-336.md).
  - PASS: variety 3.5%, clarify 5.1%, P vs old base 39/40, speed 770/1200 ms, 0 creative writes, abstention +45 vs twin b.
  - FAIL: wrong-save turns 33 (all right after the harness's lenient confirm "yes", scripts/claude_e2e336_run.py:121), wrong answers 3 (twin b 187 mechanical), saved 57%, answerable right 22%, never-told 83%, grammar 87%/56%, kept 96.8%, creative useful 12/40 with 11 unsupported person-facts, confirm rows 28%.
  - Blocker: the reader stack.
- **All 6 rows FAIL for 0.1.** No chat page.
- Bank A spent; 336b used bank B.
- 01:00 UTC 09-25 (main f2e35907b): 336 likely ran without sleep's base checkpoint (artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt, Mac only), so sleep learning probably never ran (slp-360 finding; VERIFY-336 addendum). Every later rental: rebuild it on the box (`fable_reasoner44.py --stage base --seed 4102`, ~30 s) and check the sleep report says learning was attempted. The grammar fix is owned by a separate grammar thread (gram-360, scripts/claude_gram360.py, bank G); don't duplicate it.
- 01:30 UTC 09-25 (main 43575a6ed): Ben "just run the thing". 336b registered + queued (handoff/queue/rent-336b.md, PASSMARKS-336b.md): bank B, G = 330c + gram-360 (registered), P = 330c control, T, B; checkpoint rebuilt on box, scripts/claude_sleepcheck_wrap.py stops on missing file. Marks M1-M11 on G + B1 (G grammar ≥ P +5 both graders) + B2 (sleep attempted). Judge like 336 (grammar packet = union of G and P replies). Background watcher polls builder-outbox.
- 02:18-04:00 UTC 09-25 (Ben: "as much done tonight as possible", road map; no rentals tonight, GPU via the director on BensPC):
  - 336b moved to BensPC: handoff/held/benspc-336b.md (Windows smoke first; copies Mac's pinned MiniLM to BensPC). Asked the director via the coordinator to slot it. rent-336b held, never ran.
  - Road map: design/v3/30-modes/380-joined-agent-roadmap.md. Confirm guard belongs to the reading thread (rd-373).
  - 381 stricter confirm harness = FAIL on H2 (38/43 true kept; 0 wrong yes vs old harness 10/73). 381b registered (PASSMARKS-381b.md), tested on a blind-written 120-item set.
  - Banks C and D being written blind into /mnt/project-files/escrow-331/C, D (spec: 331-bank-CD-addendum.md); need blind audit + SEAL.
- ~02:35 UTC 09-25: gram-360 = registered PASS on its own bank G (fill-in lines ~60% -> 91% clean; 0 changed saves/answers/confirms; VERIFY-360.md). So 336b's G arm counts for the conversation row and gram-360 is a 0.2 candidate. 381 and 381b (stricter confirm harness) = registered FAILs; C/D use the old harness, 381b answers reported alongside; a judge-model user is the post-Sept-30 option. rent-336b is running on a rental (launched 01:42 UTC); benspc-336b stays held unless it fails.
- Banks C (653 turns) and D (658 turns) written blind, sealed in /mnt/project-files/escrow-331/C and D; blind-audited (C 58 fixes, D 36 fixes, 0 wrong golds), v2 registered, seals on main (artifacts/claude-e2e331-bank{C,D}-seal-20260925). NEVER open scratchpad/bankc or bankD (the writers' source with bank text).
- ~03:40 UTC 09-25 (main 1750036f3, VERIFY-336b.md): **336b = registered FAIL** on M1-M11 (same 3 pass: variety, clarify, 38/40 vs old base). Saved 47%, answerable right 21%, wrong-save turns 35, grammar 89%/77%. **B1 grammar gain PASS** (+10.3/+7.9; grader A invalid 24/40, replaced by A2, disclosed). **B2 FAIL: sleep tried to learn 0/360 times** even with the checkpoint: its only recipe needs 8 new-family-word questions, which chat never gives. Bank B spent. Asked Ben (ASK WHEN SURPRISED) whether 0.2 keeps old sleep (recommended) — learning row joins via Fix-sleep's new sleep after its own PASS.
