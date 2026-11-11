# Premonition: creativity history digest (read-only sweep, 2026-10-06)

Repo: /home/user/learner (BenjaminHannan/learner). I edited nothing in the repo, and no runs, tests or GPU were used. I opened no GOLD, reserved, blind or consumed panel file.

## Labels and model key

**Labels:**
- **shown**: a registered or recorded measurement, with its file cited.
- **suggested**: argued, a DEV-only result, or indirect evidence.
- **untested**: designed or claimed, but never measured.

**Models:**
- **M1 = MiniCPM5-1B** (openbmb, commit 87179e5c, thinking off). Almost every creative run used it, either frozen or with a LoRA "sleep" adapter (r16, alpha 32, q/k/v/o, lr 2e-4, 3 epochs, batch 8).
- **LFM = LFM2.5-1.2B-Instruct** (@0f604ada). It was a plain rival in k1c, and has been the talker since Ben's swap on 09-27 at 19:27. It never ran as the creative writer: k1f never ran.
- **Qwen = Qwen3.5-2B** (@15852e8c). A plain rival in k1c only.
- **SANDWICH = frozen LFM2.5-1.2B + reader + ~9M core + prefix vectors.** This is the target of the 10-03 creative prototype v2, which is design only. Its definition is in origin/claude/custom-reader-talker-4x309r custom_io/REPORT.md.
- **TOY = a scripted, CPU-only creative-stopping toy** (Fable, 09-21/22). It has no neural network.
- **Village model (from-scratch Core) and small card experiments:**
  - The small card experiments are the synthetic-vocabulary toy ladder in design/research/broad-sweep-2026-09-19/README.md.
  - No creative experiment ran on either. Every creative number below belongs to M1, except the toy's.
  - Caution: reviews/creative-research-2026-09-25/E-asking.md calls the 24-game puzzles "card experiments" (see section 6).

---

## 1. Ben's definition of creativity and his creative decisions

Everything in this section comes from repo records: rulings, roadmap notes and team memory written by agents. There are no raw transcripts. Wording in quotation marks is as recorded.

| Date (UTC) | What Ben said or decided | Where recorded |
|---|---|---|
| 09-18 | REM dreams are "rewarded only if simulator can check". | design (human-learning-redesign.md) |
| 09-21 | Dreamer plus checker: a free dreamer, with a filter deciding what counts. | handoff/memory/dreamer-checker-idea.md |
| 09-21 | "I want it to do agentic work when I ask, and when I'm not asking it to do stuff it's either sleeping or thinking." Three modes. | handoff/memory/three-modes-goal.md |
| 09-21 | CREATIVE is a sub-routine of WORK: "...If it is working, then it can brainstorm for a bit using creative mode, then go back to work once creative mode gets an idea. If creative mode decides it can't think of anything, it can ask me..." | design/v3/30-modes/32-ben-simplification-ruling.md |
| 09-21 | Sleep must be automatic and mathematical, and the model never decides what to store. Whether this covers creative replay is unclear. | handoff/memory/sleep-automatic-mathematical.md |
| 09-21 | "My model. Everything is created and trained by me." Later relaxed (see 09-26). | handoff/memory (ben-vision / goals notes) |
| 09-22 | Vision: a strong dreamer plus a smarter filter; one model plays dreamer, filter and worker; thinking time is not a cost; he wants a provably good design to show family for funding. | handoff/memory/ben-vision-20260921.md |
| 09-23 19:07-19:13 | Emulate a brain, but better; it should be "unique/innovative". | handoff/tm-memory-2026-09-28/brain-emulation-goal.md |
| 09-24 19:13 | Routing: "It shouldn't be keyword. The worker model should be able to call the creative model as a tool ... can't you give it the conversation? And why monday, not today?" This led to 333e (tool-call head) and K1 (the writer sees the chat). | handoff/tm-memory-2026-09-28/creative-line-333e.md; creative-chat-k1-line.md |
| 09-25 00:31 | Goal: get creative to PASS. | design/v3/30-modes/creative-roadmap-2026-09-25.md |
| 09-25 00:39-00:51 | **His core definition:** creativity = "say random stuff then gets filtered out"; "maximize the number of times it gets lucky". The current safety filters are "stupid". He chose "Both" (ideas and puzzles). Guesses stay labelled as guesses. At 00:51: lucky guesses should be written into the model, so the reasoner can do it alone next time. | creative-roadmap-2026-09-25.md; handoff/tm-memory-2026-09-28/creative-line-history-0925.md |
| 09-25 16:11 | Rejected numeric "warmth" ("22 is close to 24"). Liked the egg/lobes belief that updates in sleep. | handoff/tm-memory-2026-09-28/creative-egg-search-design.md |
| 09-25 16:14 | Asked whether puzzles have any real link to the real world. This led to the scaling ladder. | design/v3/30-modes/creative-scaling-plan-2026-09-25.md |
| 09-25 16:37 | "the model should learn to ask the human when something really isn't solvable". This led to ask-24. | creative-roadmap-2026-09-25.md |
| 09-25 16:59-17:00 | Approved: ask-24; reframing; a pieces library; choosing what to practise (Absolute Zero style). | creative-roadmap-2026-09-25.md (17:00 update) |
| 09-25 17:47 | Liked surprises first, restate-and-carry-back, and a pieces library retrieved by shape. Asked to "give it tools like a calculator". | creative-roadmap-2026-09-25.md (17:47 update) |
| 09-25 19:13 | "you can use vast btw" (rentals allowed). | roadmap / handoff notes |
| 09-26 01:42 | "Ok do it then" (brd-5). | artifacts/claude-brd5-20260926/ notes |
| 09-26 12:59 | Work each unsolved problem with $2 per thread. | handoff notes |
| 09-26 | "Solve this problem. Get it to the first pass" (brd-8w, Mac agent). | origin/builder-outbox brd-8w files |
| 09-26 16:04 | Redirect: no new hand-written rules. | handoff/tm-memory-2026-09-28/redirect-and-brain-first.md |
| 09-26 16:05 | Brain first: ask "how does the brain do this?" | same |
| 09-26 16:39 | "Use GLM": nothing the model trains on (inputs or labels) may be written or judged by Claude. Borrowed models are fine for now. | design/v3/30-modes/ben-goals-2026-09-26.md; ben-goals-interview-0926.md |
| 09-26 18:41 | "Run it" (k1f). "Remove" the is_creative333c keyword route. | artifacts/claude-k1f-20260926/ notes |
| 09-27 13:25-13:28 | The talker gets no skill training: "can you make sure that happens all around". | handoff/tm-memory-2026-09-28/sleep-trains-reasoner-only.md; handoff/held/176-, 177- |
| 09-27 19:27 | Swap the talker to LFM. | handoff/tm-memory-2026-09-28/talker-swap-lfm.md |
| 09-27 19:44 | Novelty interest; the zero-data self-play paper. | handoff/tm-memory-2026-09-28/self-play-zero-data-paper.md |
| 09-27 19:57 | Stop all threads. | MEMORY.md (tm-memory) |
| 09-28 | Sleep idea: the "model picks what goes into replay (incl. failed and successful creative ideas)". | design/research/sleep-design-2026-09-28/MAP.md |
| 10-03 | Approved the "creative prototype" (v2) on the SANDWICH. Recorded constraints: "Sampling alone is not learned creativity; gold scoring is not unknown-live verification". Broad autonomy. | origin/claude/project-thread-1w6411 design/next-parts/creative-prototype-notes/FACTS.md |

**Net definition (suggested synthesis):** creativity is a generator that says random things, filtered by an exact checker. Lucky hits get written into the weights during sleep, so the reasoner can do them alone. Creativity is called by the worker as a tool when stuck. It asks Ben when nothing works. It must not use numeric warmth, keyword routing or new hand-written rules.

---

## 2. Experiments that ran

All of these are M1 unless marked otherwise. "Lucky" means right samples out of 30 per test puzzle. "cov@30" means test puzzles with at least one right answer in 30 samples. All verdicts come from registered PASSMARKS unless marked DEV/pilot.

### 2a. Puzzle sleep: does sleeping on lucky hits help? (M1 + LoRA, puzzle family "make-the-target"/24 game)

| Run | Arms | Key numbers | Registered verdict | Replicated? | Path |
|---|---|---|---|---|---|
| blurt-1 (DEV) | free blurts at T0.6 / T1.0 | puzzles: 2/1800 lucky (2/60 solved) at T0.6; 4/1800 (3/60) at T1.0 | DEV only | n/a | artifacts/claude-blurt1-dev-20260925/ (RESULTS-blurt1.md on origin/builder-outbox) |
| blurt-2 CPU (T1.0) | W, C | 173/379 wins; S0 6/127; greedy W 15, 19; C 6, 6 | Run headline PASS, but overall registered FAIL (see GPU) | No | artifacts/claude-blurt2-20260925/RESULTS-cpu.md, VERIFY-blurt2.md |
| blurt-2 GPU (BensPC, T1.5) | W, C | 184/379 wins; S0 6/127; W 13, 11; C 5, 6; L1 = +6 against a bar of +8 | FAIL (L1) | It is the replication, and it failed | RESULTS-gpu.md |
| blurt-2p (CPU) | W, P (wrong guesses) | S0 8/120; W 14, 13; P 10, 9; W − P = +4 (bar +5); W − S0 = +5.5 (bar +8) | FAIL | No | VERIFY-blurt2p.md |
| blurt-2b (CPU) | W (all hits), C | S0 5/119; W 6, 8; C 7, 9 | PROVED WRONG | No | VERIFY-blurt2b.md |
| **blurt-3** (CPU, T1.5, 66 × 30) | W, C | lucky L0 63; W 126, 136; C 85, 87. Puzzles hit 27 → W 38, 38; C 3, 4. Greedy 2 → W 4, 7; C 3, 3 | **PASS** | Yes, by blurt-3r | PASSMARKS-blurt3.md, VERIFY-blurt3.md, cpu-3/loop_summary.json |
| **blurt-3r** (BensPC GPU, new seeds, 67 × 30) | W, C | L0 59; W 129, 148; C 59, 58. Hit 29 → W 40, 43; C 4, 3. Greedy 1 → 6, 6 vs 2, 2 | **PASS** (replication) | It is the replication | RESULTS-gpu-3r.md, VERIFY-blurt3r.md |
| blurt-4 (vast 5090, T1.0, 64 puzzles, 560 examples per arm) | W padded, H (right relabels), P (v+1 wrong relabels) | L0 66 / hit 32; W 219, 223 / 32, 35; H 156, 124 / 41, 43; P 163, 117 / 46, 42 | PROVED WRONG (H = P; both average 140) | No | artifacts/claude-blurt4-20260925/ |
| **blurt-5s** (vast, about $0.24, 184 test puzzles, 3 seeds) | W, E (solver answers, same won puzzles), C | cov@30: base 77; W 112, 108, 110; E 123, 113, 117; C 14, 12, 11. W − E CI [−8.7, +0.5]. Solver targets 6.96 vs 8.13 characters | PROVED WRONG ("own-ness" is not special) | No | artifacts/claude-blurt5s-20260925/ |
| tgt-5 | W, C, base: scoring fixed strings | W pairs with D > 0: 97, 97, 100 of 120; mean D +1.40 nats. C raises matching about as much | PASS on its mark, but matching does not separate W from C | No | artifacts/claude-tgt5-20260926/ |
| brd-5 | W, N (few wins repeated), C | cov@30: base 123; W 144, 145, 136; N 91, 83, 97; C 22, 22, 18. W − N CI [+16.5, +26.2] | INCONCLUSIVE | No | artifacts/claude-brd5-20260926/ |
| brd-6 | W8 vs W4 | base 108; W4 162, 159, 160; W8 − W4 = −1, +1, −13 | PROVED WRONG | No | artifacts/claude-brd6-20260926/ |
| brd-7 | W, C, N | base 135; W 158, 158, 146; C 28, 33, 27; N 99, 89, 96 | NOT SHOWN | No | artifacts/claude-brd7-20260926/ |
| brd-8 | ITER vs CTRL | base 108; ITER 143, 161, 166; CTRL 152, 152, 167 | Compounding NOT SHOWN; G7 MET | No | artifacts/claude-brd8-20260926/ |
| brd-8w (Ben's Mac agent; 7 nights) | W, C, base | W − base +41, +35, +44; W − C +147, +152; the untrained base swung 118-139 by sampling seed | INCONCLUSIVE (seed 2 stopped) | No | origin/builder-outbox only |
| **brd-9** | N1, N3 (nights), base | base 96; N3 139, 135, 131 (bar 28.8, CI [+10.56, +21.81]); N1 111, 114, 122. Near carry-over to targets other than 24: 13 → 45, 32, 32 of 80. Harm not measured | **Registered PASS** (G7 met; NIGHTS not met) | No | artifacts/claude-brd9-20260926/ |

**What is shown for M1 puzzles:**
- Sleeping on checked hits roughly doubles luck and widens coverage at T1.5 (blurt-3/3r, replicated).
- Repeating known answers collapses coverage: 77 → 11-14 in blurt-5s, 123 → 18-22 in brd-5.
- Solver answers teach as well as own hits, or better (blurt-5s).
- More nights helped in brd-9 (N3 > N1). There is no compounding over iterations (brd-8), and W8 vs W4 showed no gain (brd-6).

**Greedy (first-try) improvement** is small and unstable: suggested only. The blurt-2 family failed.

### 2b. "Can't", reframing, feasibility (M1, 24-game)

| Run | Arms | Numbers | Verdict | Path |
|---|---|---|---|---|
| ask-24 (CPU) | W, N (+ 40 code-verified "none") | Base said "none" on 78/78 impossible and 71/71 solvable (and on all 400 practice items). W: 0 "none" anywhere. N: impossible 78, 78; solvable 70, 71; gap 0.7. Luck not taxed (N 158 vs W 166) | PROVED WRONG | artifacts/claude-ask24-20260925/ |
| ask-24ab (frozen, A/B letters) | two letter mappings | "yes" on 240/240 under both mappings; balanced accuracy 50%. Rescore AUC 0.539 / 0.455; yes-share 0.59-0.68 on every hand | PROVED WRONG (no solvability signal) | artifacts/claude-ask24ab-20260925/ (+ rescore/) |
| reframe-5 (CPU, no training) | plain vs reframe, 30 samples each | Of 79: plain 39, reframe 46. 3-number 32 → 41; 4-number 7 → 5. Oracle ceiling: 52/52 and 25/27 reachable | FAIL (not proved wrong) | artifacts/claude-reframe5-20260925/; CHECK file |
| feas-24 | logistic head on hidden states | The fit_lr fitter diverged (loss 8-47; results depend on thread count) | NOT SHOWN, test broken | artifacts/claude-feas24-20260925/ |
| feas-24b (Newton fit, layer 16, L2 = 100) | head vs shuffled placebo | Pairs 158, 155, 153 of 200 vs placebo 111, 95, 95. 3-value pairs 71, 68, 69 (bar 70). 2-value pairs 87, 87, 84 | NOT SHOWN (near miss) | artifacts/claude-feas24b-20260925/ |
| rv-388 (Memory thread; feas-24b judge inside DFS) | JUDGE, END, PLACEBO | JUDGE − END +8, +7; JUDGE − PLACEBO +5, +2 | NO CLEAR RESULT | artifacts/claude-rv388-20260926/ |

**Shown:** the frozen 1B carries no usable solvability signal. Sleep with verified "none" examples did not teach the difference: it was all-or-nothing.

### 2c. Ideas (no exact checker) (M1)

- **blurt-1 ideas** (40 DEV requests × 30 blurts; blind Opus labels):
  - 44/300 good (about 15%);
  - 9/10 requests have a good idea;
  - 17/300 invent a person fact.
  - DEV, so suggested.
  - The roadmap's "69-78% use numbers not given" was not re-derived (unclear).
- **Self-judge:** pick@1 2/10, AUC 0.691. Not used. (RESULTS-selfjudge.md, artifacts/claude-blurt2-20260925/)
- **Teacher agreement with blind Opus labels on 300:**
  - GLM 5.3 Flash 254/300 (84.7%, kappa 0.567). Fails the ≥85% rule.
  - GLM 5.3 256/300 (85.3%, kappa 0.568). Passes, just.
- **Idea head** (logistic on layer-20 state):
  - pick@1 3/10; top-3 has a good idea 7/10; AUC 0.799.
  - Not a pass.
  - It was fitted with the same fit_lr that later diverged in feas-24, and never re-fitted. (ideahead/result.json)
- **333g DEV rehearsal:** useful 3/10, invented 2/10. Not registered. (dev333g/DEV-333g.md)

### 2d. Creative chat line inside the assistant (M1 writer; panels of 40-160 items)

| Run | Change | Numbers | Verdict | Path |
|---|---|---|---|---|
| 333 | first panel | P333.2 17/30. Thinking was on, so all 25 routed items got the fallback line | FAIL | artifacts/claude-cre333-20260924/ |
| 333b | | useful 3/40 | PROVED WRONG | same |
| 333c | | useful 2/40 | (fail) | same |
| 333d | | useful 8/40 vs twin b 10/40 | PROVED WRONG | same |
| 333e | trained tool-call head (layer 12, threshold 0.7); e2: the writer sees the chat | Routing 40/40 creative, 0/30 controls (P333.2 30/30 PASS). Useful: e1 7/40, e2 6/40 vs twin 10/40. E.2 PROVED WRONG | Routing PASS; usefulness FAIL | artifacts/claude-cre333e-20260924/ (head333e.json, fitted with the fit_lr that diverged) |
| **k1a** | the writer sees the chat as messages (+ 0.2c sleep adapter) | Useful of 60: K 28, X 15, T 24. Lead items 20 vs 7 (sign p = 0.0001). With the adapter 28, without 21 | **PASS** | artifacts/claude-k1a-20260926/VERIFY-k1a.md |
| k1b | bare list endings | B 1 vs X 2 | FAIL | artifacts/claude-k1b-* |
| k1c | the 1B picks among 4 drafts by PMI | Useful of 160: C 47, K 46, T 46; Qwen 114; LFM 103. On DEV, any-of-4 useful 26/40 vs first 12 | FAIL, PROVED WRONG | artifacts/claude-k1c-20260926/VERIFY-k1c.md |
| k1d (pilot) | listener pick | 14/40 | Not registered | PILOT-k1d.md |
| k1e (DEV) | GLM as draft critic | 121/157 (77%, kappa 0.537); reasoning "high" 63/79 (80%) | Fails the rule; the critic was not trained | VERIFY-teacher-dev.md |
| k1g (DEV) | think vs no-think | 18/40 vs 15/40 | Reading unclear | DEV-k1g.md |
| 0.2c joined build | K1 inside the full assistant | creative 18/50 vs T 21 | FAIL | artifacts/claude-e2e02c-20260926/VERIFY-02c.md |
| 336 (Premonition 0.1 end to end) | | creative useful 12/40, with 11 unsupported person-facts | (as recorded) | 00-director-board.md:1168 |

The same 0.2c build also ran the L1-L6 puzzle sleep **inside** the joined assistant:
- lucky 74 → 192;
- greedy 5 → 12;
- puzzles reached 39 → 61;
- lost 10/201 general items;
- verdict PASS.

**Fix-sleep thread (M1):**
- dl-1 FAIL.
- dl-2 PASS: 7 copy-practice nights; lucky 64 → 237, 249; P 42, 51; reached 34 → 62, 60.
- dl-5: lost 98 and 61 of 200 general items. This is a harm signal.

### 2e. Creative stopping toy (TOY: scripted, no neural network)

- Verdict KEEP_FIXED_N, 3/3 seeds.
- 0 false FOUND when only the checker may say FOUND, against 143-154 when the filter may.
- Solving rose from about 25% to about 98% thanks to a same-model dreamer, a balanced filter and a backlog.
- Paths: artifacts/fable-creative-stop-toy-20260921/ (RESULTS.md, FREEZE-NOTE.md); handoff/memory/creative-stop-toy-result.md.

### 2f. SANDWICH (frozen LFM + 9M core)

- The v6 integrated design docx (commit c5cfd9176) cites a diagnostic: "40 calls, rescued 2 of 6, 0 updates".
- **No receipt was found.** Treat it as untested.

---

## 3. Designed or approved, never run (and why)

- **Creative prototype v2** (10-03, SANDWICH core).
  - File: origin/claude/project-thread-1w6411 design/next-parts/creative-prototype.md, plus notes (FACTS.md, v2-recheck.md, math/math-report.md, critic-report.md, fresh-design.md).
  - Content: ADD/SUB make-the-target in tiers W/P/T; twin targets; sampled call heads.
  - Arms: N, W, R placebo, PC (solver positive control).
  - Marks: L1 W − N ≥ 10; L2 W − R ≥ 8; G0 aiming ≥ 5; G1-G3; PC gate. Verdicts 1-11 in order.
  - Its own math: rules-only floor 14.4% per try; "add all three" solves 26.4%; 97-100% of puzzles have a single sign pattern.
  - Status: design only. No run on any branch.
- **brd-11.**
  - Sealed (PASSMARKS, SEAL, DEV-NOTE) and never run.
  - DEV found 0 luck on 4x4 squares and level-1 games. Only 120 unused 4-number target-24 puzzles were left.
  - Then 09-27 13:42: handoff/held/176-creative-brd11pc.md "DO NOT RUN", because it trains skills into the talker.
- **brd-12** (games + HER).
  - Sealed and held. DEV: 0 asked-goal hits in 600 samples, but 16 relabelled goals in 20 games.
  - handoff/held/177-creative-brd12pc.md says DO NOT RUN, for the same reason as brd-11.
- **brd-10 K3** (up to 3 answers per won puzzle). Plan only (brd-10-fallback-plan.md).
- **brd-13** (move own hits to the reasoner; arms O, H).
  - Settled as Sleep research's step (c). No run found.
  - Its grid hindsight rule was degenerate: only sums would be relabelled.
- **k1f** (LFM as the writer). Ben said "Run it". It still never ran:
  - rental HOST-FAIL around $0.10 on 09-26;
  - BensPC job never started;
  - vast HOST-FAIL $0.16 on 09-27.
  - Then the threads were stopped (19:57). Also, k1f is not a 0.2d input (02d-gates-ADDENDUM-49.md).
- **k1h.** Data gates PASS (895 rows; gate 2 60/60). Training never run; parked. It is also barred by the 09-27 "no talker skill training" ruling.
- **333f** ("train the writer"). Named as next after 333e and never run; it was superseded by K1.
- **Held blurt loops:** 006b-blurt4-loop.md and 008-blurt2b-loop.md. STATUS HELD, DO NOT RUN (Director 09-27 13:52).
- **GPT-6 Pro problems answer, tests B and C:**
  - B (padded-W checkpoints) is not possible as stated, because no adapters were saved.
  - C (scrambled-target placebo) was deferred.
- **gpt-xhigh-creative-mode.md v1:** 60 synthetic jobs. No record of a run.
- **39-creative-review-gpt-xhigh.md:** factorial experiment (shared vs separate generator/verifier × backlog, ≤1M parameters). Never run.
- **Concept invention** (reviews/concept-invention-proposal-2026-09-20.md + addendum): learn new latent variables from prediction failure. Kept separate from the card and village tracks. Never run.
- **Scaling ladder rungs 1-5** (creative-scaling-plan-2026-09-25.md) and the assistant practice ladder (assistant-practice-plan-2026-09-25.md: Reasoning Gym, Wordle, Lichess, xLAM, MBPP/APPS/TACO, Spider, SWE-Gym):
  - Not registered.
  - Only near carry-over within one family was measured (brd-9).
- **Approved 09-25 at 17:00/17:47 but never built:** pieces library, surprises first, choosing what to practise (Absolute Zero), calculator tool, egg/lobes search.
- **E-asking curriculum** (marks P1-P6) and F-discoveries parts A/B/C. Proposals only.
- **333 creative panel spec** (40 creative + 30 controls) and the blind judge prompt. These were used for the 333 series. The later G5 hedge-filter and router fixes from research-creative-2026-09-24.md (C1-C9) were only partly addressed (by 333e/K1).

**Why things stalled (shown from the records):**
- Rental host failures (k1f).
- Ben's 09-27 rulings that the talker gets no skill training (brd-11/12, k1h) and the talker swap to LFM.
- Stop-all-threads on 09-27 at 19:57.
- Running out of unused test puzzles (brd-11).
- Zero DEV luck in new families (brd-11, brd-12).
- Teacher labels failing the agreement rule (k1e).

---

## 4. Key lessons (with evidence)

1. **An exact checker is the load-bearing part.**
   - Shown on the TOY: 0 vs 143-154 false FOUND (artifacts/fable-creative-stop-toy-20260921/RESULTS.md).
   - Suggested by the literature: F-discoveries.md, exact check in 20 of 22 cases.
2. **Sleep on checked hits raises luck and coverage on fresh puzzles of the same family** (M1). Shown and replicated: blurt-3 and blurt-3r.
3. **Who made the hit does not matter.** Solver answers do as well or better (M1). Shown, one run: blurt-5s, W − E CI [−8.7, +0.5]. Answer length is a confound: 6.96 vs 8.13 characters.
4. **Repeating known answers collapses variety** (M1). Shown several times: blurt-3/3r C, blurt-5s C, brd-5/7 C.
5. **First-try (greedy) gains are small and unstable** (M1). Shown: the blurt-2 family failed. The 0.2c greedy 5 → 12 is one run.
6. **Hindsight relabels gave no benefit beyond a wrong-label placebo** (M1). Shown: blurt-4, H = P. But v+1 is a weak placebo (CHECK file).
7. **The 1B cannot tell solvable from impossible**, either frozen or after "none" sleep. Shown: ask-24, ask-24ab plus rescore AUC about 0.5.
   - "Can't" should come from code (adopted in the CHECK file).
   - Suggested: RFT erodes "I don't know" (E-asking.md).
8. **Reframing finds pieces only when the budget per piece is not spread thin.** Shown that it helps on 3-number puzzles and hurts on 4-number ones (reframe-5); the oracle shows the pieces existed.
9. **Learned judges are weak at this size.**
   - Shown: self-judge 2/10; feas-24b near miss; rv-388 no clear result.
   - Suggested: the literature on judges punishing novelty and judge-expert agreement of about 53% (C-creativity.md).
10. **Fitting bugs can fake results.** Shown: the fit_lr divergence in feas-24. The idea head and head333e used the same fitter and were never re-fitted.
11. **Seeing the conversation helps the creative writer** (M1). Shown once: k1a 28 vs 15/24. The same items scored 21/20 in k1c, so judge-set noise is real.
12. **Bigger plain models beat the 1B's creative tricks** (k1c). Qwen 114 and LFM 103 against about 46 for M1's variants. Shown, one run.
13. **Sleep can damage general skills.** Shown: dl-5 lost 98 and 61 of 200. 0.2c lost only 10/201.
14. **More nights help (brd-9), but iteration does not compound (brd-8), and there is near carry-over within the family.** One run each.
15. **New task families gave zero DEV luck** (brd-11, brd-12 DEV notes). Transfer beyond the 24 family is untested.

---

## 5. Open questions and known risks

**What is still unknown:**
- What sleep actually learns: sharpening, length/style, or "new puzzles have answers"?
  - tgt-5 showed that C also raises target matching, so matching is not the separator.
  - Length was not tested.
- Whether the creative part has any job beyond finding checked answers where no solver exists. This is untested.
- Temperature: W widened coverage at T1.5 (blurt-3r) but not at T1.0 with padding (blurt-4). The causes are confounded.
- Transfer to a second family or to real tasks (code with tests): untested. Ladder rungs 1-5 never ran.
- The harm and forgetting budget of creative sleep: brd-9 did not measure it, and dl-5 showed large losses.
- Whether the SANDWICH's ~9M core can blurt usefully at all. Prototype v2 is design only, and the 2/6 diagnostic has no receipt.
- Idea quality has no exact checker:
  - teacher labels fail or only just pass the agreement rule (256/300 vs k1e 77-80%);
  - Ben's "Use GLM" rule bars Claude labels;
  - person-fact invention persists (17/300; 11 in 336).

**Known risks:**
- Small test sets: 2-3 seeds and one run per result. The base varied 118-139 by sampling seed (brd-8w).
- Test sets shrank after registration: blurt-5s went 240 → 184.
- No saved adapters: B-type re-analysis is impossible.
- The RuleKeeper is hand-written scaffolding, in tension with the Redirect.
- The puzzle pool is nearly used up (brd-11).

**Governance risks:**
- Creative skill training is barred from the talker (09-27).
- The talker is now LFM, but every creative chat result was on M1, so none of it carries over directly.
- Sleep now trains the reasoner only.

---

## 6. Conflicts between documents

1. **blurt-2:** RESULTS-cpu.md says PASS, while the overall registered verdict is FAIL (VERIFY-blurt2.md, GPU L1 +6). The roadmap's "Where we are" table still says PASS.
2. **The "own hits" framing:**
   - creative-roadmap and creative-scaling-plan frame the method as learning from the model's own lucky hits.
   - blurt-5s showed own-ness is not special.
   - Ben's 00:51 "written into the model so it can do it alone" survives only as "train on checked answers".
3. **"Drafts are the limit":**
   - PASSMARKS-k1f says the drafts are the limit.
   - VERIFY-k1c corrects this: any-of-4 drafts was useful on 26/40 vs 12/40 for the first draft.
4. **PASSMARKS-brd12** says "brd-11 replicates it", but brd-11 never ran.
5. **The GPT brainstorm prompt** says blurt-2 used "150 puzzles". The records say 127, 120 and 119 test puzzles.
6. **"Card experiments":**
   - broad-sweep-2026-09-19/README.md uses it for the synthetic-vocabulary toy ladder.
   - E-asking.md uses it for the 24-card puzzles.
7. **Building from scratch:**
   - Ben 09-21: "Everything is created and trained by me."
   - Later work borrowed MiniCPM, LFM and Qwen; the 09-26 goals say borrowed models are fine for now.
8. **Who decides what to store:**
   - Ben 09-21: sleep is automatic and the model never decides what to store.
   - Ben 09-28 (MAP.md): the model picks what goes into replay, including creative ideas.
9. **Judge fitter:** the idea head (3/10) and head333e were fitted with the same fit_lr that diverged in feas-24, and neither was re-fitted. Their numbers are less trustworthy than they look.
10. **GLM labels:** GLM passed for idea labels (256/300, 85.3%), but failed for creative-draft labels (k1e 77-80%). Both are "GLM as teacher", with different outcomes.
11. **Same items, different scores:** k1a scored K 28 / T 24, while k1c's same items scored about 21/20. Judge-set noise.
12. **RuleKeeper:** it is hand-written scaffolding, which conflicts with the 09-26 Redirect ("no new hand-written rules"). It was built earlier, and no decision on keeping it was found.
13. **Talker creative results:** the talker-sleep creative results (k1a with the 0.2c adapter, the 0.2c joined build) conflict with Ben's 09-27 ruling that the talker gets no skill training. They are now historical only.
14. **0.2c:** the 0.2c "creative FAIL" (18/50) contrasts with k1a's PASS for the same writer idea.
15. **The v6 docx** cites a creative diagnostic ("rescued 2 of 6") with no artifact receipt.
16. **Roadmap vs ask-24 prompt:** the roadmap's "69-78% of ideas use numbers not given" was not re-derived. The GPT prompt's "576 of 600 blurts were none" refers to DEV practice, while the test said none on 149/149. These are consistent but easy to conflate.
