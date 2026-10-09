---
name: growth-test-8a
description: Stage 8a growth test 3M/10M (spec PR #50, addenda A-J); 10M FAILED mark 1 (B2 flat) but every B2 run had the 9-register bug; 30M dropped
metadata:
  type: project
---

Spec: /mnt/project-files/whole-model-roadmap/8A-SPEC-2026-10-07.md = design/8a-bigger-is-better-2026-10-07.md on branch claude/project-thread-yha868, PR #50.
- One change = size: today's B2 (calculator inside, 8 rounds; does NOT wait on 2c/2d), reader = q39 winner. Rungs 3.3M / 10M / 30M trained params, depth first. Arms per seed: B2, PT (gate), plain LLM (reported). Data 38% own / 62% web (cloze rows), pools 20/60/190M, seen 20x params, seeds 400-405.
- Marks: B2 +3 pooled-5 per step (CI>0); lead over PT not shrinking >1; >= +3 at 30M on 5/6. GOOD ENOUGH (Ben 1:23 PM ET "demonstrate scalability with a model that is good enough"): mark 4 = 3M B2 pooled-5 >= 72.0 (q33 B2 mean 74.0); mark 5 = at 30M B2 >= public model + 2.0 paired (pythia-31m; see F).
- ADDENDUM B 1:40 PM ET: every arm >= 24,000 updates x 256 rows; 3M+10M share the 60M pool/rows; speed check first.
- ADDENDUM E (17516b761), Ben 2:04 PM ET "don't cut off long answers": every cap = longest in the data, no answer-only fallback.
- ADDENDUM F 2:29 PM ET (5d8719a34), rulings on build PR #51 (claude/project-thread-f1to6a): letter reader at every rung whatever q39 says (EGE extra at 10M dropped: q39 failed the shortcut mark, 9:25 PM ET 10-07); public model pythia-31m only; caps set once from the largest pool for all rungs (n_loops = N_RES+1 may exceed 8, disclosed); PC fetches exactly the manifest shards.
- Ben "Start now" tap 1:23 PM ET: 8a may train before the protected-panel hash check; that check must pass before 8c.
- Default told to Ben: grow B2 now; B3 joins unstarted rungs once it passes, catches up on finished ones.
- ADDENDUM G 2:45 PM ET (6cf89d33db): global caps stand (prompt 280, ans 35, 91 nums, 208 words, 11 steps; B2 12 rounds/36 registers/106 slots, B2-3M 3,346,513); NO skip filter (E1b); per-batch slots optional if exact; q45 >24 h for 3M -> ask Ben re rent; recompute caps on new own72.
- FIRST LOOK + 3M ON VAST (Ben 3:00/3:02 PM ET "go ahead. With using VAST", "The vast refills"; addendum H 3:10 PM ET 7564b01609): box ids in . Speed (5090): per seed 3M 1.0 h, 10M 3.2 h, 30M 16 h; 30M six seeds ~96 h ~$45 (ask Ben first).
- FIRST LOOK 5:24 PM ET (7edf618302): UNCLEAR. B2 +1.42/-0.28; plain +2.73/+2.19 (skills-only data).
- 3M DONE 7 PM ET: mark 4 HELD, B2 mean 72.34; PT ~66.3, LLM ~46.
- 10M DONE 2:20 AM ET 10-08: 8a verdict FAIL (mark 1). B2 +0.49 (6 seeds), PT +3.77, LLM +15.77 (5 seeds; 404 PT/LLM cut by MAXH); lead 6.2 -> 2.9. B2 ~100% on calculator families, flat on rule/pattern families (fewshot 19%, seq_next 37%) where PT grows. Stop rule (10M-3M < 0) does NOT block 30M; mark 1 fails anyway. PROBE DONE 4 AM ET 10-08 (6a1e1e7491, results/8a-probe): R (reader 23 layers) FLAT +0.73/-1.46, broke cipher 98->73; W (d384 blocks 3) UNCLEAR +1.57/+0.46 (+1.54/+0.18 vs deep), leak up; disproof "both flat" did not happen. Write-up /mnt/project-files/whole-model-roadmap/8A-10M-RESULT-2026-10-08.md. 30M (~$42, ~14 h) asked of Ben, recommended hold + outside opinions (prompts reviews/{gpt,astra}-diagnose-b2-no-growth-2026-10-08.md, copies in whole-model-roadmap/reviews/).
- BUG (8b session, confirmed 3:40 PM ET 10-08): every 8a B2 run had ledger N_REG 9 / GEN_MAX 8, not 36/35 (caps.apply skips lazily imported ledger); plain arms fine. 8a FAIL = untested for B2 as designed; fixed re-run is gate G1, see [[scaling-bar-ben]].
- Never open protected panels (notepanel378/readpanel371, GOLD-PRIVATE).

**Why:** Ben wants bigger proven on a model that is already good, on his home GPU.
**How to apply:** any change to marks after the first run needs a dated addendum; keep [[whole-model-roadmap]] page in sync.
