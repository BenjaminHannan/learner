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
