# Funding ledger (coordinator)

Started 2026-10-19 by the coordinator who took over from Muse. Before this file there was no written ledger in the
repo. Rows marked "handoff" come from Muse's handoff text and are not yet matched to a bill.

Caps: Vast.ai $50/week, Modal $30/month. Long or final runs: Ben adds money case by case. A 10M run on a Vast
5090 is reported to Ben and never approved here.

## Spent this week (handoff figures)

| Item | $ | Source |
|---|---|---|
| GPU-RUN-3 | 3.03 | handoff |
| Replicas | ~1.09 | handoff (the LT2 marks file also quotes $1.09 for the replica box) |
| Scratch | 1.46 | handoff |
| Span Stage 0 | 0.15 | handoff |
| Span Stage 1 | 7.98 | handoff; the span session also reports $7.98 of an $18 hard stop |
| **Total** | **~13.71** | handoff |

Not yet in the total: disk rent on the six stopped span boxes (below) since they stopped on Oct 19.

## Vast account check, 2026-10-19 23:20 UTC (read-only API)

- Credit $22.36. Last top-up $50 on Oct 13. The invoice API lists payments only, not per-run charges.
- The speed session saw $32.75 of credit on Oct 17 at about 16:00 UTC. The drop since then is $10.39: span Stage
  0+1 ($8.13) plus about $2.3 of disk rent. That roughly matches the handoff.
- The speed session's own week estimate ($16.3, from credit drops) does not match the $13.71 above. The cause is not
  reconciled; the week boundary each figure uses is unknown.
- Six instances exist, all "exited / stopped", 3090s, 50 GB disk each. Storage total is $0.156/h, about $3.74/day:

| Instance | Label | $/h disk |
|---|---|---|
| 56601518 | claude-spancards-s1-seed0 | 0.0139 |
| 56601519 | claude-spancards-s1-seed1 | 0.0602 |
| 56601524 | claude-spancards-s1-seed2 | 0.0306 |
| 56611888 | claude-spancards-s1b-seed1 | 0.0185 |
| 56611889 | claude-spancards-s1b-seed2 | 0.0185 |
| 56611901 | claude-spancards-s1b-seed0 | 0.0139 |

These hold the only copies of the span Stage 1 arm checkpoints. Retrieval route and destruction are Ben's call.

## Approved, not spent

| Item | Hard stop $ | State verified 2026-10-19 |
|---|---|---|
| D1 dose test (unknown/refusal) | 4.10 | NEVER BOOKED. Approved Oct 16 21:51 UTC. The session first had to commit probe data; Ben rejected that tool call at 21:53, and nothing ran after. Marks file says "DESIGNED, NOT BOOKED". |
| GPU-RUN-4 (speed) | 2.07 | NOT BOOKED. The session's Vast create call was blocked by the permission check. It waits on a Yes/No prompt only Ben can answer in that session. |
| Week-1 Item A calibration | 2.10 | NOT BOOKED. The session was interrupted on Oct 17 15:40 before any work. No rate card exists. |
| Week-1 Item B / R1 | 16.01 | HELD (after Item A and the Q14 fix). |
| Decoder reader-KV Stages 1+2 | 2.80 | GATED (review pass plus sealed card). Stage 0 is $0. |
| Swarm C0+S0 | 4.20 | GATED. Round-2 re-review not clean; the session says "C0 does not book". |
| Week-1 Item C / logic R5 | 0.84 | Not booked (handoff). |

## Rulings log

| When (UTC) | Session | Ruling | $ |
|---|---|---|---|
| 2026-10-19 23:3x | Info constraints (session_016AV7Th…) | GO: plain-D CPU sweep (425/1,000/2,000 steps), then S2 Stage 0 under E3. Void guard: a control with one distinct answer voids the cell. Marks committed before the run. | 0 |
| 2026-10-19 ~23:50 | Swarm (session_015V6Z9z…) | GO on the two blocking review-round-2 items (torch._assert_async; spec T matches the kit's 120), then the built-in review. C0+S0 ($4.20) still gated. | 0 |
| 2026-10-19 ~23:55 | Brain (session_01R6PEw…) | G3-over-G1 NOT signed off (a bar change; Ben's call). GO to commit round-G work to a new branch and run the built-in review. Stop the loop. | 0 |
| 2026-10-20 ~00:00 | Steals (session_01DPxyxb…) | Resume the fix round on findings 1, 2, 4, 10 after Ben confirmed the restart. R1/R2 Stage 0 held until review is clean. | 0 |
| 2026-10-20 ~00:00 | Decoder (session_0183EgSA…) | premonition/ override confirmed for flag-gated edits only. Stage 0 GO after Ben confirmed the restart; marks committed before the run. Stages 1+2 ($2.80) gated. | 0 |
| 2026-10-20 ~00:10 | Restart gate (session_01GR2gp7…) | B2 = option (a), via the Opus xhigh gate. Pass marks and the proves-wrong result fixed in the ruling. B3 as a separate commit. B1 still with Ben. | 0 |
| 2026-10-19 | GPU-RUN-4 | Ben said yes ($2.07 hard stop). Booking needs Ben's click in the speed session: the auto-mode check blocks standing rental permission. | 0 so far |
| 2026-10-20 00:16 | ShinkaEvolve trial (session_01YVHzs7…) | Ben approved. Goal: genuinely new mechanisms for PremonitionMini, with a novelty filter and judge. CPU only. NEW COST TYPE: Claude API spend, $5.00 hard stop, outside the Vast/Modal caps. Stage 0 ends with a sealed card before any evolve run. | API ≤5.00 |
| 2026-10-20 00:13 | Brain (session_01R6PEw…) | Ben: "Opus review first" on G1 vs G3. Opus xhigh review running. | 0 |
| 2026-10-20 00:12 | Swarm | GO on round-3 blocking items a–c, then the full-diff review, the dry run, the seal and the bid. | 0 |
| 2026-10-20 00:11 | Brain | GO on a fix round for the 9 code-review findings (E0 identity check first). | 0 |
| 2026-10-20 ~00:30 | Brain | BEN: keep G1 (pre-set rule), after the Opus xhigh review. G3 not adopted; its "proved wrong" condition was triggered. Verdict file to be corrected. G1 still needs the Main brain gate (DM1/DM3) and E0 before shipping. | 0 |
| 2026-10-20 ~00:35 | Restart gate | Ben delegated. B1 = ADD the "framing falsified: escalate" outcome as its own amendment before any run (an exit only, no bar moved). B1/B2/B3 as separate commits. | 0 |
| 2026-10-20 ~00:35 | Size (session_01BWoBq8…) | Ben delegated. Bid C chosen (B2 creative body; critical path; about 1/3 of Bid A's cost). Option 2(b) not taken, so the pre-set depth-first redirect stands. Booking waits on review and a sealed card. | 0 now; Bid C $14.0–24.4 committed, or $0 on BensPC |
| 2026-10-20 ~00:35 | Game world | Ben delegated. Track 10: write OPTIONS.md defining label-side vs collection-side ($0) before the coordinator rules. | 0 |
| 2026-10-20 ~00:35 | Steal 9 | Ben delegated. NOT NOW: the 8 steals still lack a clean review, and no Steal 9 spec exists in the repo. | 0 |
| 2026-10-20 ~00:35 | Span boxes | HOLD; not destroyed (that can't be undone, and these are the only copies). Disk rent about $3.74/day. If Ben hasn't connected storage by Thu Oct 22, the coordinator asks him once more, then recommends destroying. | ~3.74/day |
| 2026-10-20 ~00:35 | ShinkaEvolve | Stays on the API key, $5 hard stop, unless Ben says "subscription only". | — |
| 2026-10-20 00:15 | GPU-RUN-4 (speed) | BOOKED after Ben's click. Vast 56810922 gr4full (4090, $0.47/h, hard stop 03:15Z) and 56810924 gr4rep (4090, $0.513/h, destroyed by 01:32Z). Expected about $1.55; hard stop $2.07. Credit $22.02 at 00:25Z. | ≤2.07 |
| 2026-10-20 00:25 | Decoder | Ben chose Muse's Oct 17 rulings over the new coordinator's. The coordinator runs the PR #79 code review; Stage 0 waits until it passes. | 0 |
| 2026-10-20 00:31 | Swarm | GO on round-3b items 1, 2, 4, 5. Item 3 (delegated by Ben): pooled M1 test averages items over seeds, then pairs over items; the ≥2-of-3-seeds rule is kept. Allowed pre-seal (no data yet) and stricter. | 0 |
| 2026-10-20 00:28 | Steals | GO on round-5 blocking items #1 (row_halt HALT read) and #8 (R1 arm-order rotation). | 0 |
| open | Ledger check | The decoder session claims "$29.86 of $50 committed" this week on Vast. Not yet reconciled with this ledger. | — |
| 2026-10-20 00:50 | Steals | Round-6 review accepted as clean for the R1 path (9ce46e2..2004775 is docs only). R1 Stage 0 GO at 2004775: $0, CPU, marks as filed. Design questions (a)–(d) settled or held as listed. | 0 |
| 2026-10-20 00:41 | Info constraints | S2 Stage 0 PASSED its pre-set marks (control about 11%, treated 1024/1024 on 3 seeds). Coordinator review of the final head running. Distractor reading GO ($0). | 0 |
| 2026-10-20 01:10 | Info constraints | Coordinator review of PR #87 @90077ef2b: CLEAN (0 blocking, 7 non-blocking), so S2 code is no longer DRAFT. The `distract` runner addition is not yet reviewed. S3 build GO ($0); the run waits on the S3 review. | 0 |
| 2026-10-20 ~01:00 | Restart gate | Deferral-line wording ruled. B1 add stands (delegated); the session may stage it as PENDING BEN. | 0 |
| 2026-10-20 ~00:57 | Brain | Fix round 2 GO; G1-config bit-identity on the --guard replay path checked first. | 0 |
| 2026-10-20 ~00:55 | Swarm | GO on the dry-run blocker, no tracked diagnostics under seconds_budget, items 5/6/10. | 0 |
| 2026-10-20 01:20 | Decoder | Coordinator re-review of PR #79 @84bda16a8: CLEAN (0 blocking, 8 non-blocking). Stage 0 GO ($0) under Muse's rulings; fix step matching first if Stage 0 uses train_d. | 0 |
| 2026-10-20 01:17 | Restart gate | Fix round GO (F1-F7, N2, N3); B1 staged PENDING BEN. | 0 |
| 2026-10-20 01:12 | Swarm | Fourth-pass fixes 1-3 plus the _recall desk-0 slice GO. | 0 |
| 2026-10-20 ~01:55 | Decoder | Step-matching fix (Addendum A, runner only) reviewed CLEAN at 7de83cf5f. Stage 0 runs from there count; the two superseded runs (both at chance) are disclosed and uncounted. G1 passes trivially and counts as no evidence. | 0 |
| 2026-10-20 ~01:35 | Swarm | Fifth-pass items 1-7 GO; next review is one highest-effort full sweep of kit and readout. | 0 |
| 2026-10-20 02:05 | GPU-RUN-4 | DONE. Session reports $1.16 of the $2.07 grant spent. Vast check at 02:07Z: no GPU-RUN-4 instances remain, credit $20.69. Verdict: mark 2 FAILED (E4 loss diff 0.048 vs 0.02), so defer does NOT ship. Speed was 1.36x / 1.51x. | 1.16 |
| 2026-10-20 02:07 | GPU-RUN-5 bid ($1 cap) | Sent to the Opus xhigh gate as a possible bar-move after seeing a score. The session waits on an AskUserQuestion that Ben has to answer. | pending |
| 2026-10-20 02:20 | GPU-RUN-5 (speed) | Opus gate: APPROVE WITH CHANGES. GPU-RUN-4 stays FAIL. New B/D×3 noise-floor test with bars sealed before rental: about $0.55, hard cap $1.00. Booking needs Ben's click in the session, then the seal hash sent to the coordinator. | ≤1.00 approved |
| 2026-10-20 02:43 | Decoder reader-KV | Stage 0 FAIL (G2): control 0/3 and treated 1/3 above chance+0.05 (0.074, 0.160, 0.066). Line CLOSED as specced. The $2.80 Stages 1+2 approval is RELEASED. | 0 |
| 2026-10-20 02:52 | GPU-RUN-5 | Seal accepted (PREREG 0ab5dbfd…, commit 6eef85bfe), with "incomplete = FAIL" added. No AA-floor guard. Waiting on Ben's click; hard cap $1.00. | 0 so far |
| 2026-10-20 03:08 | Info constraints | S3 built and reviewed (11 rounds). Distractor-pool mismatch disclosed and corrected (10b: fact-only 29-36%). Ruled: pool = facts; mark 2 STAYS 55% (no lowering after seeing scores). S3 Stage 0 GO ($0), provided round 11 covered the final head. | 0 |
| 2026-10-20 03:03 | Brain | Identity confirmed (G1 config unchanged old vs new). One E0-scoped fix round; stop rule: "E0-ready" once e0_score + the G1 path review clean. H1 flag marked not for use. | 0 |
| 2026-10-20 03:26 | Info constraints | S3 Stage 0 FAIL, and proves-wrong fired (cell B mean d −0.33 pts; treated d2 23.6/9.9/19.7%). Final. Cell-B controls never learned to read (suggested), which goes to the Opus queue for any S3 redesign. S4 Stage 0 card GO ($0) with a "control can read" validity check. | 0 |
| 2026-10-20 03:37 | ShinkaEvolve | Stage 0 sealed (6996899, PR #90). The mechanism is the card WRITE rule. All-Opus 5.5, per Ben's direct ask in that session. Stage 1 GO: Shinka ≈$2.02 + judge $1.60, trial stop $4.50. Spent so far $0.155 (API). | API ≤4.50 |
| 2026-10-20 03:55 | Info constraints | S4 Stage 0 FAIL, proves-wrong fired, "mechanism not engaged". Line on STAND BY pending an Opus xhigh design review of the choosing protocol (the shared S3/S4 pattern). S1 parked (no village checkpoint). | 0 |
| 2026-10-20 ~04:05 | Info constraints | Opus design review: the S3/S4 failures were protocol-limited (tiny preset d=32; no positive control). S5 dec_ent_match Stage 0 GO ($0, CPU) with VOID/engaged checks and marks sealed before code. | 0 |
| 2026-10-20 04:22 | ShinkaEvolve | Trial FAILED by the sealed card: all 5 judged finalists KNOWN (best 6a-1: OT/PMA pooling, 0.715/0.740 vs multi-head 0.743/0.740). API spent $3.389 of $5.00 (Claude API, outside the Vast/Modal caps). Lesson: code-level novelty is not idea-level novelty. NEXT.md requested ($0). | API 3.39 |
| 2026-10-20 ~04:20 | Steals R1 Stage 0 | A1 (Muon, lr 3e-3) PASS; A2 (Muon, lr 2e-2) NOT SHOWN. $0 CPU. Formal report pending. | 0 |
| 2026-10-20 04:23 | Steals | R1 stage 0 final: A1 Muon lr 3e-3 PASS (d +0.628, 2SE band +0.317 to +0.939, 3/3 seeds; toy answers above chance in all 3 seeds); A2 NOT SHOWN. R2 stage 0 GO ($0). R1 stage 1 bid to be drafted, with a recall@4 guard. | 0 |
| 2026-10-20 04:35 | Steals | R2 card fix + re-seal GO ($0). R1 stage 1 bid accepted in principle: both arms at lr 1e-3, G-RET pass-blocking; P1-P3 GO ($0). Booking (≤$2.80: 1a ≤$0.30, 1b ≤$2.50) after review, seal and re-quote, plus Ben's click. | 0 now; ≤2.80 approved |
