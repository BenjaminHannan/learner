---
name: reasoner-exit-rule
description: Pre-registered exit rule for the loop-reasoner line plus next steps after 358i (maze 358m, chat bridge 358b2), fixed 2026-09-26 ~14:25 UTC
metadata:
  type: project
  modified: 2026-09-26T14:22:24.576Z
---
The exit rule is in artifacts/claude-rsn358i-20260926/EXIT-RULE.md (main 50745425c), written before any 358i result.

**STOP this loop design** (ADDENDUM-1 ac7eacbbd, Ben 14:54: NOT the learned-reasoner goal; run next ranked learned design e.g. 358f/learned halting; empty list -> Ben brainstorm; plain switch needs Ben; R10 right after 358b3 PASS) if G0 is met AND all of these hold:
- the 4-seed mean loop − plain is below +10 on sums6 and on grids6;
- it is below +20 on sums10 and on sums12;
- own-stop adds nothing over fixed 16 rounds.

**CONTINUE** if 358i passes, or if the lead is at least +20 on sums10/12 or grids7.

**In between:** run 358m only, then STOP if the pooled 8-seed mean stays below +20 on every bigger test.

**Next steps agreed with the thread manager** (session cse_01T8RjGifsQdqHsTQnCvPjPr, Ben's "push threads" thread):
- 358m: mazes after the 358i recipe, seeds 5-8, stage-1 checkpoints copied to the Mac for rv-390. Script scripts/claude_rsn358m_run.py; not sealed yet.
- 358b2 bridge (sealed 483b62ad5, rental claude-sleep-358b2, 358a loop-s1, narrowed to all-visible squares) = PLUMBING/report only. 0.2d HEADLINE GATE = 358b3: 358i nets, no narrowing, blind panel + lookalike negatives, ONE shared puzzle reader owned by Plain-English puzzles (cse_0168iLXHqs7XrkFePoRbNPSR, rt-02g pattern + grid format); Month-end to say plain 1B or adapter on. Original idea: chat-phrased Latin squares. The talker copies the grid, code tokenizes it, the loop solves it, the checker verifies, and the talker answers. It is scored against the 1B alone. This is the first end-to-end learned middle in Ben's reader -> reasoner -> talker picture.
- Caveat: seed 2 of the small trial cut the loop's grid lead to +20 with half-narrow heads.

**Why:** the thread manager asked for an exit condition, and Ben's rule is to own the problem and not idle during runs.
**How to apply:** apply this rule literally when the 358i RESULTS land, and don't move it afterwards. See [[reasoner-roadmap-state]], [[build-02c-message-flow]].
- Full loop test (mine, after rv-390 and only if downtime finds beat RESTART): nights on day hits + downtime finds vs day hits only vs day hits + RESTART finds (matched rows). Score = next-day first try on fresh 58600-59999 states.
- 14:45: H-A gate = 358b3 needs a loop net with its own verified PASS; plain 1B, adapter OFF (Month-end). Add rival arms: Qwen3.5-2B and LFM2.5-1.2B alone. Ben 14:43: "hard problems" = eventually real planning (uncle's business); for the demo, better than same-size models plus the design scales; size counts only the biggest model inside. Size-scaling test (1x vs 3x loop, plain 3x control) after 358i needs extra budget. Plot the rounds curve from 358i.
- 14:55: 358b3 panel maker scripts/claude_rsn358b3_panel.py (57e2f82ab): make(seed) -> panel {id,message} + answers; "broken" lookalikes. Benchmarks' prompt for all non-build arms (GENERAL_SYSTEM, no tail, 512). Smoke seed 36000; row A = fresh seed.
- 14:52: Ben 14:49 "scales" = loop beats same-size plain at EVERY size. 358s marks (442bf2d3b, PASSMARKS-draft.md): loop1x>plain1x AND loop3x>plain3x, 3x gap >= 1x gap. Only Ben approves architecture changes; sleep only while dormant, stoppable any moment.
- Ben 14:51: past $2, reasoning gets money before overnight learning (priority only; Director figure + Ben's OK still needed).
- 15:10 NOTE-vs-TRM (844933fbb): post-STOP order = TRM schedule (carried-state deep supervision, no bare round-1 loss, EMA) > two-state y/z > 358f > learned halting; also equal-but-longer training check.
- 358t v2 SEALED 657cc4f41: A loop-trm (schedule only), B loop8 (Ben's looped 8x256), vs 358i plain; EMA/loop8-trm report-only; lone pass -> seeds 5-8. Ben approved $1.60 15:19; QUEUED fcbca86ad.
