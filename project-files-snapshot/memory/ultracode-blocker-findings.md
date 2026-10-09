---
name: ultracode-blocker-findings
description: Shown facts from the ultracode 1.2B bench (Oct 5-6, PARKED): eval bug, SR2 steps, plan route confirmed, doors confirmed, T1/T2/MH/PX-family wrong; recipe in BENCH-RECIPE.md
metadata:
  type: project
  modified: 2026-10-06T06:15:00.000Z
---

Ultracode thread (branch claude/ultracode-learning-blocker-gh011t, PR #38; results artifacts/ultracode-v4/{SCREEN,DIAG}-v4.md + results/). Shown by 12:20 UTC 2026-10-05 (worst-8 fit screen, 2k rows x3, 6k updates, fit/held of 320):
- GEN BUG: copy-path generation fed the prompt twice; fix = --gen-fix. Older copy-path numbers are wrong.
- SR2 (--steps --steps-rich --seq-steps-v2, LM-written worked steps) 6 seeds CF4-9: fit 85.5%, held 81.3% = reached the 85% mark. Lesions: the LM does the thinking, core = family switch. 32-wide reader drops number identity (probe). No small learner learns one arithmetic step from 2k rows.
- PLAN ROUTE (uc_diag_v4.py --mode plan: thinker plans start/ops/pointers, exact calculator computes): +--op-attend +17k rows +--lr-cosine (PLCD) 97.6% held, 6 seeds. Matched practice (PLS) 82.8 vs LM steps 85.8 (level). LMDC (LM steps on the same 17k rows + cosine) 158/160 on all 3 seeds (98.75%) -> route is LEVEL with LM steps at equal data, not better. Correction posted to Ben 11:24 UTC.
- REAL MODEL ROUTE CRDC (SR2 + --plan-route 17000 --plan-cosine) CONFIRMED 6 seeds 12:15 UTC: fit 92.9%, held 89.7% (paired SR2 85.5/81.3); chain held 156/160 vs 138 (+18, data-confounded); plan_swap lesion -> chain held 2-3 on every seed = the thinker decides every chain answer. Other 4 kinds held +8.9.
- PX (other 4 kinds as pointer plans) 77/160; PXW (reader 256) 75, PXW2048 77, PXH (two-hop content pointer) 76 = all WRONG/flat 22:35 UTC: same per-family scores even on practised rows -> limit is not door width or pointer form (untested next: probe thinker states for pairings; cipher sub-word splits).
- CRT (--plan-talk, talker writes calc(thinker note)) 3 seeds: held 285.7, chain 471/480 vs direct 470 = level; plan_swap -> chain 2-14 (note decides); copies swapped note 79-96% (90% mark missed 2/3).
- Macs: old session session_01Y9yKSuBCF1PPHaBtnheV6X offline; NEW Mac session session_018qt3j4biYuC1uFu7tzHb4A (Remote Control, ssh benspc, context nearly full: keep messages compact). Ben 18:27-18:30 UTC: wait / rent / dont.
- PLR (per-round routers in planner) WRONG 22:05 UTC: 6 seeds 131.2 vs PLS 132.5, ahead 2/6; rounds did use different experts (not void). Dropped.
- MH (merge Hearer+Reader, --direct-reader, Ben's ask) WORSE 00:28 UTC 10-06: 6 seeds held 278.8 vs CRDC 287.0, ahead 2/6; loss all on other-4 (122.8 vs 130.7), chain level; lesion still tiny.
- WD (both doors 2048, Ben's ask): WDC 6-seed CONFIRMED vs SR2: held 274.8 vs 260.0, ahead 5/6. CRDW (doors on CRDC) does NOT stack by marks: held 291.5 vs 287.0, ahead 3/6; CONFOUNDED: train_planner deep-copies the widened reader, so the planner got 2048 too (chain -3.5); other-4 +8.0.
- AUDIT TESTS: T1 (--lr-final-mult 0, main model) HURTS: held 276.2 vs 287.0, behind 6/6. T2 (--quiet-notes) HURTS: 226.5 vs 287.0, 6/6. T3 global heads WRONG. T5 skipped.
- BENCH PARKED (Ben 03:20 UTC 10-06 'Park it'): no new bench tests unless they answer a B2 question. Reference recipe /mnt/project-files/bench/BENCH-RECIPE.md (= artifacts/ultracode-v4/BENCH-RECIPE.md): nothing new to port to B2; warning: pointer programs for lookup kinds flat-lined (5 designs). Vast boxes E/F/G destroyed 06:12 UTC 10-06; credit $8.84.
**Why:** any claim that the core reasons needs a lesion; equal-data controls decide "better than LM".
**How to apply:** use --gen-fix; judge with --final-lesions; compare routes at equal practice. Related: [[blocker-ideas-opus]].
