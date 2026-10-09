---
name: finished-model-source-of-truth
description: Finished-model architecture source of truth (10-09): Ben's Q1-Q3 answers, 100M size, audit, B3 group 1 built (PR #56), group 2 building, token test on PC
metadata:
  type: project
  modified: 2026-10-09T17:55:00.000Z
---

Ben 9:07 AM ET 10-09 (thread "Architecture ambiguities", cmsg_01GSLCHTCnZxn7DhV19qcDvMTBu4oLCm3tkUvBRzbBsHEQ): clear up ambiguities; 9:10 AM: make sure the architecture is as he intends "universally". Answer file: /mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md (wins over older notes until Ben says otherwise). Audit 12:20 PM ET: AUDIT-2026-10-09.md + audit-2026-10-09-findings.json beside it (220 checked findings, 14 high; none conflicts with Ben's intent; 17 fixes made in FINISHED; rest routed by owner via coordinator).

Settled from code:
- Calls are written INSIDE the thinker loop, at most one per round; the call writer reads thinker control 0; the talker writes only the answer. Reply read by the letter reader as a short new string; question not re-read. One H1 stop for the whole answer ('settled' label). Older notes with per-call "turns" are wrong vs code.
- 100M thinker = about 21 blocks at 512 (PLAN's "30 blocks at 512" = ~139M). B3 group 1 at 100M as built = 373.1M whole (no 25M talker yet).
- B3 must pass Ben's size bar itself (B3 ladder 3M/10M/30M on PC).
- Experts: Ben 09-29 "sparse moe ... for our model" + 10:18 AM ET 10-09 GX ask; join only if both GX stages pass before group 2 freezes, else dense.

Ben's card answers 10-09: Q1 calls at ANY round; Q2 inputs up to 2,000 letters; Q3 KEEP the letter window. 9:30/9:44 AM he asked to try tokens: TK/TKN test (/mnt/project-files/architecture/TOKENS-EXPERIMENT-2026-10-09.md) on BensPC first gap, kill-first, never delaying B3; card 8aTK-card.md pinned to 1ed55c8d5d96. Ben 10:49 AM ET "Hundred": finished thinker 100M.

B3 group 1 (any-round calls with gaps, Gemma + outside calculator, 2,000 letters via caps_b3, H1R stop; one config for 3M/10M/30M/100M) BUILT: PR #56 branch claude/project-thread-qtxfp4 e070556ce5; spec B3-GROUP1-BUILD-2026-10-09.md. Inventory vs B3: no-hardcoding/INVENTORY-B3-2026-10-09.md (counts 0/2/6/4/6).
B3 group 2 (hold lifted 12:15 PM ET 10-09, code only, its 3M run waits for G1 GO): spec /mnt/project-files/architecture/B3-GROUP2-BUILD-2026-10-09.md (Addendum A: steps the calculator can't write become `note <step>` tape entries; Addendum B: writer trains on its own copy feedback, refine=1). One learned byte writer writes whole calls (op name included, tool registry by first word) and answers; N1 no slots, P1 no place code, V1 bytes, L1 steps as written, ST1 self-teach (st1.py). 3M within 2% of g2c3 (4,022,440). Parts built ~1:45 PM ET: writer f29cde4457, inputs 5aab74a520, progtext/st1 f6695cbd4a; joined in scratchpad worktree g2int (branch g2-int, local) by a Sonnet helper building models/b3g2.py.
Fixes on PR #56: 425b036e8f (caps.apply had made H1's 32-round cap 109); 8fce7247a8 (H1 'settled' stop loss only in batches of all 32 rounds, stop_w; cap counter steps_unparsed). Ben 1:20 PM ET 'Allow' (blank rows with no steps OK); 1:32 PM ET 'Run, disclosed' (group 1 runs with steps_unparsed reported; group 2 must reach 0 via notes).

PAUSED 2:31 PM ET 10-09 (Ben: 5% weekly usage left, last until 7 AM ET 10-10): group 2 integration WIP bd1e98ae0c (untested) + writer/inputs/traces saved as /mnt/project-files/architecture/wip/g2-int-2026-10-09.bundle (base 8fce7247a8) with the brief. Ben chose 'All steps' 2:28 PM ET: build plain control PTS/g2c3s (steps for every row) on PR #56; not started (workflow stopped). Resume both after 7 AM ET.

**Why:** many notes described the model differently from the code; Ben wanted one clear picture.
**How to apply:** start any architecture question from that file; relay Ben's card answers to the big-run thread via the coordinator. Related: [[whole-model-roadmap]], [[scaling-bar-ben]], [[t1-calculator-outside]], [[h1-learned-rounds]], [[no-hardcoding]], [[one-proven-run-rule]].
