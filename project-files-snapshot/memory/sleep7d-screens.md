---
name: sleep7d-screens
description: Roadmap 7d creative-sleep screens 10-07/08 on CPU (S1, S1b, VL pass; S3, J, R, S1w, S1f, L2 fail; 2x2 = overfit; lr 1e-4 night = no harm; SC proved wrong, SCL pass 10-09; AP/re-score held)
metadata:
  type: project
---

Fast sleep thread, for the creative roadmap thread (session_01Gm1Xzi5bZJjTsULogvCMP9, rules on marks). Code creative/sleep7d.py, drift7d.py, night7d.py, harm_look.py; results creative/results/fastsleep/sleep7d/README.md (branch claude/project-thread-2kevpk, PR #48), copy /mnt/project-files/fast-sleep/sleep7d/. Parents N' rebuilt on CPU from B2_s100/s101 (~/c7d/s10x/Nprime.pt). Times ET.
- S1/S1b PASS 10-07: creative REINFORCE adapter on N' (reach@32 +18/+16). S3/S3' FAIL: practising shaky passes = re-sleeping.
- HARM: each lr-1e-3 night costs rule-from-examples families (seq_next 81 -> 30 after 2 nights); pooled-5 guard near-blind. Measure = harm_look.harm_measure (in_dist drop >1.5 or family >5 with CI<0).
- J FAIL; R (replay-only repair) PROVED WRONG (worse harm, C2 erased); S1w PROVED WRONG; S1f FAIL -> loop 1 PARKED.
- 2x2 (5329b2c6c): cause = overfitting small reused row sets; fresh rows help skills; any 1e-3 replay-only pass erases C2 gain, 1e-4 keeps most.
- VL PASS (b942bb26a): night 1 at lr 1e-4 = NO skills harm, C2 first try ~kept. V (8 visits @1e-3) proved wrong.
- L2 FAIL mark 2, not proved wrong (10-08 ~1 PM): two 1e-4 nights, harm passes, but multi-step climb only +3.9/+3.2 vs +10 mark; reach@32 multi-step 9 vs W2 32/25.
- L64 FAIL, not proved wrong 3:53 PM ET 10-08 (3dc882fce): 64 visits at 1e-4; mark 2 misses by ONE question on both (-2.6 vs -2); s100 table_calc fires (-6.5) on night 2; reach@32 multi-step +9/+4 over L2. Night-1 visits change nothing. Roadmap ruled (009028cd42): fail on the table_calc fire; one-question miss = met (near-miss rule). Lever = lr (3e-4 next, held). 7d line PAUSED until the big-run thread asks.
- SC PROVED WRONG 12:13 PM ET 10-09 (864b0af6f; un-held by big-run scorecard row 5 + Ben's "Run it" card 11:16 AM ET): model-picked replay at lr 1e-3 keeps C2 gain (1.08x W1) and cuts in_dist drop to 1.5/0.1 (W1 3.8/3.6), but seq_next/rule_apply/list_stats/order_chain still fire -> scorecard rule 'harm on either parent' = proved wrong. Suggested next: SC at lower lr (roadmap's call).
- SCL PASS 1:15 PM ET 10-09 (29e768b53; Ben's Run card 12:27 PM ET): SC's picking on VL's lr 1e-4 night; harm clean (+0.9/+1.1 vs N'), gain 0.93x/0.98x L's. Picking = uniform at this rate (few rows' loss rises); reach@32 multi-step still ~half W1's. Covers replay choice only, not nights/temperature.
- D6 learned notebook gate BUILT 10-09 (creative/gate7b.py, a1afc86c2): question-level leave-one-out, settings fixed by roadmap; full run waits for job 9's scoring.
- Still HELD: AP, lr 3e-4, the 71.3% re-score (creative/rl/rescore_harm.py). Ben 10-09: cheap free-compute tests for his principles are OK, but the session's safety check needs his own word naming a run (decision card works).
**Why:** the roadmap's J (joint creative + worker sleep) needs loops that pass alone and a harm check that sees the damage.
**How to apply:** for any sleep/fine-tune night, use lr ~1e-4 not 1e-3, fresh replay rows, and judge harm per family (creative/harm_look.py), never pooled-5. Related: [[fast-sleep]], [[creative-roadmap]].
