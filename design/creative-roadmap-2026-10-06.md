# Creative model roadmap (2026-10-06)

Ask (Ben, 7:56 PM ET 10-05): a thread dedicated to figuring out a creative model, "the hardest problem", with a really
good roadmap. It must fit Plan B (Ben's pick, 7:44 PM ET 10-05): our own thinker grows to most of the model, the
reader and talker are tiny, and the 1.2B is only a teacher during training and never ships.

Labels: **shown** = measured in this repo or in a cited paper; **suggested** = reasoned; **untested** = a plan or guess.
The old creative runs used a frozen MiniCPM5-1B with a LoRA "sleep" and are cited as that model only. The sandwich
(frozen 1.2B + 9M core) and the from-scratch B2 are kept apart. No creative experiment has run on the village model or
the small card experiments, and none is planned here. Times are ET.

Inputs:
- creative history digest: `design/creative-roadmap-notes/history-digest.md`
- 40 checked papers: `design/creative-roadmap-notes/papers.md` (also in the project folder under papers/)
- probe P0 on B2, 10-06: `design/creative-roadmap-notes/p0/`
- creative prototype v2: `origin/claude/project-thread-1w6411:design/next-parts/creative-prototype.md`
- Plan B: `origin/claude/project-thread-9ye9md:design/thinker-first-split-2026-10-05.md`
- B2: `origin/claude/custom-reader-talker-4x309r:custom_io/`
- Ben's goals: `design/v3/30-modes/ben-goals-2026-09-26.md`

Reviewed before posting by the project coordinator and an independent Opus critic; what changed is in section 10.

## 0. For Ben

Your definition: when the thinker is stuck, a creative part tries lots of different things, a checker keeps the ones
that work, and the model learns from them in sleep so next time it doesn't need luck.

- **It has worked once, in one place.** On number puzzles with a borrowed 1B, sleeping on its checked lucky hits about
  doubled its right tries on fresh puzzles, and it replicated (63 to 131, then 59 to 138.5, out of about 2,000 tries).
  First-try solving barely moved.
- **Four walls make it the hardest problem.**
  1. Cold start: on a brand-new kind of task there are no lucky hits, and no hit means nothing to learn from. Tonight,
     32 tries by our own thinker B2 found an answer for 1 question out of 240 on three never-seen kinds.
  2. Sameness: B2's 32 tries hold only 2 to 4 programs that really differ, and sleeping on the same answers over and
     over once shrank the old model's reach from 27-29 puzzles to 3-4.
  3. No checker for fuzzy things like ideas.
  4. B2's program language can't even write some answers (dates, word edits).
- **The plan climbs four floors**, one tested step at a time:
  - Search: try, check, sleep inside our own thinker.
  - Invent: first hits on never-seen kinds, through stepping stones, a library of reusable pieces, and beating the
    teacher.
  - Choose: it picks its own practice, calls creative mode when stuck, and asks you when something is truly impossible.
  - Worlds: a tiny crafting world early, then a small Minecraft-like game, then Minecraft.
- **The first real test (C2) is your few-examples idea.** The model gets a few examples of a new rule, tries many
  programs, keeps the ones that reproduce every example (no answer key needed), and sleeps on them. Before it, a cheap
  machinery check (C1) on make-the-target puzzles. Both wait for B2's 6-run confirm; the code can be built now.
- **One question for you:** park ideas with no right answer (gifts, plans) until the model has its own judge (C4)?
  I recommend parking.

## 1. What "creative" means here, and the scoreboard

**Definition (operational).** The model finds checked solutions to problems it could not solve on its first try and
that nobody gave it the answer to, then learns from them so it needs fewer tries, and fewer examples, next time.

Every creative test reports the same scoreboard, on fresh problems the model never practised:

| Score | What it counts | Why |
|---|---|---|
| Luck | share of 32 tries that pass the checker | the old runs' main measure (blurt-3) |
| Reach | problems with a passing try within 4 tries, and within 32 | catches variety collapse that luck hides; pass@4 because pass@32 saturates on easy families |
| First try | greedy solves | what the user sees; it moved least before (blurt-2) |
| Examples to learn | labelled examples a same-size plain net needs to match the creative model on a new kind; also a fresh net | **Ben's main measure** (ben-goals, 09-26: "how few examples a new kind takes to learn") |
| Variety | distinct programs per problem that change the result (counted on the steps that do something) | variety is the fuel |
| Frontier | problems no teacher, solver or training answer covered, solved | the one job only creativity can do (blurt-5s) |
| Transfer | task kinds never practised | Ben's carry-over goal |
| Harm | practised skills lost after sleep, against the parent | sleep once cost 61 and 98 of 200 general answers (dl-5) |
| Lesions | the same scores with loops:0 and with a donor's thinker state | a "creative" gain must come from the thinker, not a pointer leak (B2 missed loops:0 by 1.76 points in one seed) |

Later, for fuzzy work, add quality times novelty (CreativeBench, 2603.11863): junk that is new and copies that are
good both score zero.

## 2. What we already know

### Our runs (shown; frozen MiniCPM5-1B + LoRA sleep, number puzzles, exact code checker, marks fixed first)

| Run | Result | Verdict |
|---|---|---|
| blurt-3 / blurt-3r | Lucky tries 63 to 126/136 (C 85/87); then 59 to 129/148 (C 59/58). Puzzles reached 27 to 38/38 (C 3/4); 29 to 40/43 (C 4/3). C = sleep on its own known answers, same count | PASS, replicated |
| blurt-2 / 2p | First-try solves on fresh puzzles rose a little: 6/127 to 15-19 (CPU) and 11-13 (GPU) vs 5-6 for C; wrong-guess placebo 9.5 vs 13.5 | FAIL on the size of the gain |
| blurt-2b | Sleeping on all hits: W 6/8 vs C 7/9 | Proved wrong |
| blurt-4 | Hindsight relabels ("made 22" becomes a "make 22" puzzle) lowered luck (140 vs 221); wrong relabels did the same (140). Both relabel arms reached more puzzles (41-46 vs 32-35), not a registered mark | Proved wrong on luck; the reach effect is suggested |
| blurt-5s | Puzzles solved in 30 tries: own hits 112/108/110, exact-solver answers on the same puzzles 123/113/117, known answers repeated 14/12/11, before 77 (of 184) | Proved wrong: own hits are not special |
| brd-9 | Three nights of own hits: 96 to 139/135/131 of 240; near carry-over to new targets 13 to 45/32/32 of 80; nights did not compound (brd-8) | PASS; harm not measured |
| ask-24ab | The 1B cannot tell solvable from impossible puzzles (50% balanced accuracy) | Proved wrong: "can't" must come from code or be learned |
| ideas (DEV) | 44 of 300 tries good; a trained judge picked a good one first 3/10 (AUC 0.80), self-judge 2/10; the trained judge used a fitter that later diverged and was never refitted | Judge is the bottleneck (weak evidence) |

### Probe P0 on our own thinker B2, 10-06 (shown; CPU, no training, scored with the answer key)

- Held-out kinds (clock_date, op_define, string_transform, unit_convert; 40 questions each): greedy 0.6% / 1.2% (seeds
  100 / 101); best pass@32 1.9% / 5.6%. On clock_date, op_define and string_transform, 32 tries found an answer for 1
  question out of 240 (one op_define question, seed 100). The rest of the hits are unit_convert. **Cold start** for
  seed 100 and **weak signal** for seed 101, by lines fixed before the probe.
- **Narrow variety (post-hoc count):** raw sampled programs differ a lot (15.6 to 30.2 distinct per question), but
  most differences are in steps that do nothing; counting only steps that change the result, 32 tries hold 2.1 to 4.5
  distinct programs.
- On rows it gets wrong in new wordings, 32 tries rescue 5-25%, but guessing a random prompt word 32 times scores
  15-25% on the same rows (post-hoc): pointer re-guesses, not new programs.
- Two of the four new kinds have answers B2's program language cannot write (dates, string edits).
- B2 has no key-free checker, no example slot, no memory, and no way to resume training from a checkpoint yet.

### Lessons (labelled)

1. Sleeping on checked hits raises luck and reach within a family, and keeps variety; sleeping on repeated known answers
   collapses it (shown, 1B, one family).
2. Where a solver or teacher can answer, its answers teach as well as creative hits (shown once, blurt-5s; answer length
   is a confound). So creativity earns its keep only where no solver or teacher can answer.
3. First-try gains are small and unstable; luck and reach move more (shown).
4. Learned judges are weak at small size (weak evidence for ideas; suggested generally by "Mind the Gap", 2412.02674).
5. Sleep can cost general skill, so every step needs a harm mark (shown, dl-5).

### Papers (the ones that shape this plan; full list in the papers file)

- **The loop is real.** SOAR (2507.14172): sample programs, relabel, fine-tune took a 7B from 14.25% to 36.25% on ARC,
  with a "greedy-diverse" rule for choosing what to sleep on (shown). CodeIt (2402.04858) relabels every try's actual
  output as its goal (hindsight). DreamCoder (2006.08381) grows a library in sleep.
- **Small transformers can climb.** Lee et al. 2025 (2502.01612): keep only correct self-made answers to slightly
  harder problems each round; 10-digit to 100-digit addition (shown).
- **Training only on winners kills variety.** Negative reinforcement (2506.01347) keeps pass@k up and positive-only
  lowers it (shown, 7-8B). Fixes: learn from losers, upweight rare correct answers (2506.02355), invent sibling tasks
  (2508.14029), add new data to old instead of replacing it (2404.01413).
- **Sleep cannot create a try with zero chance** (sharpening theory, 2412.01951; Yue 2025). Stepping stones or
  hindsight are needed first.
- **Learning from a task's own few examples at test time works** (test-time training, 2411.07279: up to 6x on ARC at
  8B; shown). Untested at our size.
- **Libraries can be fake.** Reuse of learned functions was "extremely infrequent" in two systems (2410.20274): log
  reuse.
- **Games.** Crafter is solved by modest world models (EMERALD, 2507.04075: all 22 achievements within 10M steps);
  Craftax-Classic is above human level at 1M steps (2502.01591); full Craftax is unsolved (best 18.3% of max reward,
  repo leaderboard); Dreamer 4 (arXiv 2509.24527, https://arxiv.org/abs/2509.24527) gets Minecraft diamonds from pixels
  in 0.7% of episodes with 2B weights (paper's full text, checked by the papers worker; not reproduced here).
- **Tiny reasoners need care.** TRM (7M) scores on ARC come with 1,000 augmentations, a vote and a task ID; with the ID
  blanked it drops to 0 (2512.11847, shown).

## 3. Why it is the hardest problem: four walls

1. **Cold start.** No hit, no signal (P0).
2. **Sameness.** Few distinct tries (P0: 2-4 that matter in 32), and training on winners narrows them further.
3. **No checker.** Ideas, open-world plans and advice have no exact check, and small judges are weak.
4. **The language can't say it.** A try cannot be right if the program language cannot express the answer (P0: dates
   and string edits). This one is a gap in B2's program language, owned by the custom reader/talker thread; the
   roadmap lists what each step needs from it.

## 4. Design decisions

- **D1. Creativity lives in our thinker, as program search.** The thinker writes many candidate programs (plans); the
  exact executor or a simulator runs them; a checker keeps the ones that work. This fits Plan B (the thinker is most of
  the model) and Ben's "tools like a calculator". It departs, at first, from Ben's 09-22 wish that one model plays
  dreamer, filter and worker: the filter starts as code. C4 adds the model's own filter, trained on the checker's
  verdicts, so the one model takes the filter role too. The free hook is sampling B2's heads (`ledger.py:227`, `269`;
  shown in P0).
- **D2. The deciding filter is code until the ladder reaches fuzzy problems.** Checkers are part of the task (the
  target, the examples, the simulator), never a learned judge's say-so, until C4's filter is shown to agree with them.
- **D3. Teacher where it can answer, creativity where it can't.** The 1.2B writes problems, stepping stones and fading
  hints during training only (lesson 2). It never ships and never judges inside the shipped model. Ben's 09-26 rule
  holds: nothing written or judged by Claude goes into training. Test prompts use one fixed instruction line, the same
  in every arm and masked from the loss (Ben's 09-26 16:50 card allows this in tests); wording meant for a build comes
  from the 1.2B.
- **D4. Variety is designed in, twice.** At try time, a shared sampler drops duplicate programs before running them
  and branches over the top first steps. At sleep time, a variety rule (diverse picks, rare correct answers upweighted,
  some wrong tries pushed down) is tested as its own change (C3).
- **D5. Climb a ladder of checkers:** the target (C1) -> the examples (C2) -> a simulator (C5, C10) -> the model's own
  trained filter (C4) -> people.
- **D6. Honesty rules for every step:** one change, marks sealed before running, a placebo arm, a harm mark, lesions,
  fresh sealed test sets, 6 independent parents before any claim (the project's noise rule), and the result that
  proves it wrong.
- **D7. Gates and machines.** GPU stages of C1 and C2 start only after B2's 6-seed confirm passes; its seeds 200-205
  become the 6 parents. If Plan B's B1 passes first, the 10.8M students are the parents. CPU builds start now. Runs go
  on Ben's own machines first (the 5070 Ti or the M1 Pro, whichever is free, sharing with B1 under the GPU-BUSY rule).
  Research gathering for later steps goes to Sonnet agents.

## 5. The roadmap

Four floors. Each step's single change, pass mark and kill result are below. Marks for C3 onward are provisional and get
sealed in their own spec before running.

### Floor A: Search (try many, keep what checks, learn)

| Step | One change | Pass (provisional after C2) | Proves it wrong |
|---|---|---|---|
| **C0** (done 10-06) | Scoreboard on B2, no training | Read: cold start on new kinds, narrow variety (shown) | n/a |
| **C1** machinery check | B2 sleeps on its own checked tries for make-the-target puzzles (+ - x /); claim capped at "the loop works on B2", since a solver exists. Hindsight arm included | Section 6 | Section 6 |
| **C2** few-examples rules (the main first test) | C2a: programs over input roles, checked by re-running them on the prompt's own examples (no answer key). C2b: key-free sleep on held-out rule kinds | Section 7 | Section 7 |
| **C3** keep the variety | Variety sleep rule (diverse picks + rare-correct upweight + some wrong tries pushed down), 3 nights, on C2's family, against C2's plain sleep. Ask Ben first: rule-picked replay (his 09-21 "sleep is automatic") or model-picked (his 09-28 note) | Reach@4 after night 3 >= plain + 5 points (interval above 0); distinct result-changing programs do not fall night to night; luck within 2 of plain | Reach@4 no better than plain |
| **C3b** (only if a sameness gate fires) | A trained variety source: a small "style code" the sampler is conditioned on, or mutating earlier winning programs | Distinct result-changing programs per problem at least double at equal luck | Variety up, reach flat |
| **C4** its own filter | A head trained on the checker's verdicts ranks tries before they run (Ben's "one model is dreamer, filter and worker") | AUC >= 0.80 against the checker on fresh tries; ranking raises pass@4 by >= 10 points over random order at the same tries | AUC < 0.65 |
| **C5** first world | A tiny text crafting world (8-12 items and recipes); the thinker writes plans, the simulator is the checker; sleep on plans that reached new items. Needs plan ops from B2's owner | Reaches items it never saw a plan for >= 10 points more often than no-sleep, every parent, interval above 0 | Within 2 points of random plans |

### Floor B: Invent (first hits on kinds it has never seen)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C6** stepping stones | The 1.2B writes easier variants of fresh, sealed new kinds without seeing their tests; the loop climbs one step at a time (Lee 2025, Ben's "reframing"). Not P0's four kinds | New kinds: reach@32 >= 25%, first try >= 10%, examples-to-learn at least halved against the plain net | Reach@32 < 10% |
| **C7** pieces library | Repeated sub-programs become new named operations the thinker can call (Stitch, DreamCoder); a piece counts only if reused in 2 or more kinds | New-kind reach >= C6 + 5; >= 30% of new solutions use a counted piece | Reuse < 5% |
| **C8** beyond the teacher | Checkable problems the 1.2B gets wrong with the same 32 tries and the same checker | Solves >= 20% of the teacher's failures | < 5% |

### Floor C: Choose (own practice, and knowing when to stop)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C9** | The model picks practice by learning progress (problems it solves sometimes, not always). The worker calls creative mode when stuck and returns to work with what it found (Ben, 09-21). "Can't" comes from exhaustive search or a learned estimate; the finished model asks its user when a task is truly stuck (Ben, 09-21 and 09-25), while our research loop just logs it and moves on | >= 1.3x fewer updates than random practice to reach a fixed reach level; "can't" on a balanced solvable/impossible set: precision and recall both >= 0.9; stuck-then-return raises task success over never calling creative | No faster than random practice |

### Floor D: Worlds (from puzzles to Minecraft)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C10** | Craftax-Classic (fast symbolic Crafter), then Crafter pixels; a small world model lets the thinker "dream" tries that the real game then checks (Ben, 09-18: dreams count only if a simulator checks them) | Beats a same-size plain agent at equal steps by >= 5 reward points, interval above 0; stretch: human level (65%), all 22 achievements | At or below the same-size plain agent |
| **C11** | Minecraft (screen in, keyboard and mouse out) | First rung: wooden-pickaxe rate above a same-size plain agent at equal steps. Today's best pixel result: Dreamer 4, diamonds in 0.7% of episodes at 2B weights | First rung not above the plain agent; the rest is a research gamble |

**Side track: ideas with no checker** (gifts, plans, messages). Recommended: park until C4 gives the model its own judge.
Then the judge learns from real outcomes (Ben's thumbs up or down), the 1.2B helps only in training, and every idea is
shown labelled as a guess. Ben decides on the decision card.

## 6. C1 spec: machinery check (seal before any GPU stage)

Built on creative prototype v2 (five Opus review passes, 10-03), moved to B2 and fixed by this roadmap's review.

- **Claim cap.** A solver exists for these puzzles, so a PASS means "B2 learns more from its checked tries than from
  look-alike tries, and the sleep machinery works". It does not show creativity (lesson 2).
- **Parents:** the 6 B2 confirm seeds (200-205), one sleep per arm each. If they are not available, B2_s100 and
  B2_s101 with 3 sleep seeds each, paired within parent, with the claim limited to those two parents.
- **Puzzles:** "use A, B and C once each with + - x / to make T", exact division only, numbers 3..40 excluding 10 (so no
  number equals a constant slot 1, 2, 10 or 100), T >= 1 (B2's number reader drops minus signs), solvable, no 2-number
  shortcut, T not a given number. Floors (uniform and rules-only, per try and at pass@4) recomputed for B2's slots in S0.
  Twin targets on every test puzzle (same numbers, two targets with different solutions). Splits by number set:
  practice 1,024; DEV 128; T1 256 (once); T1b 256 (replication); X 128 four-number puzzles (report only). One fixed
  instruction line, identical in every arm and masked from the loss; C1 joins no build.
- **Shared warm-up:** every arm starts from the same warmed parent: B2 learns the format on 2-number puzzles with solver
  programs. N is this warmed parent. Warm-up harm against the original B2 is reported.
- **Gates on DEV after warm-up:** cold start: an accepted try within 32 on >= 10% of puzzles; sameness: >= 4 distinct
  result-changing programs per puzzle on average. A failed gate stops C1 with T1 sealed (C3b first for sameness;
  stepping stones first for cold start).
- **Tries:** 32 per practice puzzle from the shared sampler: sample op and operand pointers at a DEV-chosen temperature
  (P0's sampler), drop duplicates before running, branch over the top 8 first steps.
- **Checker (no answer key):** two independently written checkers. Allowed ops ADD, SUB, MUL, DIV only. Take the tree
  of steps that feeds the final answer slot: it uses each given number exactly once by slot id, never T's slot or a
  constant, and ends on T. Unresolved (checkers disagree, a replay doesn't reproduce, a crash) counts as no hit. Planted
  bad programs of every kind must be rejected before any GPU stage.
- **Training form:** the accepted tree in the first steps, then NOOP. Targets come from the logged slot ids (forced
  replay), never from re-parsing values. On puzzle rows the answer pointer targets the final result slot. Stopping is
  scored separately (STOP-rule luck).
- **Arms (each differs from W in one thing: what it sleeps on):**
  - N: no sleep (the warmed parent).
  - W: its own accepted tries, at most 2 distinct programs per puzzle.
  - R placebo: its own rule-following tries chosen without looking at the value, from a separate pool, matched to W's
    puzzles and per-puzzle counts.
  - H hindsight: rule-following tries relabelled as "make v" for the value v they actually made, same count.
  - H' wrong relabel: the same tries relabelled to a value they did not make, same count (blurt-4's control).
  - PC positive control: solver programs for W's puzzles, same count.
- **Sleep recipe (identical across arms):** fresh AdamW; a fixed number of updates with each puzzle record seen at most
  4 times; every batch half puzzle rows, half replay of the 200k skills rows; learning rate and update count chosen on
  DEV using the PC arm only, then frozen.
- **Marks** (6 parents; luck = share of 32 tries accepted on T1; 95% t-intervals over parents on paired differences):
  - L1: W - N >= +10 points, W above N for every parent.
  - L2: W - R >= +8, interval above 0.
  - G0 aim (own-target hits minus twin-target hits): W - R >= +5 with interval above 0, and W above N with interval
    above 0.
  - G1 reach@4: fails only if the upper end of W - N is below -2.
  - G2 stopping: STOP-rule luck W - R >= +4.
  - G3 harm: skills pooled-5 drops by at most 2 points against the warmed parent, every parent.
  - Lesions: W's luck with loops:0 must be under half its full luck, and a donor puzzle's thinker state must not raise
    hits on the recipient's target above the rules-only floor; otherwise the run is void.
  - H question (secondary): reach@32 H - W >= +5 with interval above 0, and H - H' above 0.
  - PC gate: PC - N >= +10.
- **Ordered verdicts:** void (checkers disagree on a T1 try, unresolved above 1%, or a lesion fails) -> gate stop ->
  placebo too close (over half of R's records are accepted tries) -> PASS (L1, L2, G0, G1, G2, G3) -> rules only (L1
  holds, G0 fails) -> gain with harm (G3 fails) -> **proved wrong** (the PC gate passes, yet W - R has an upper end
  below +5 on luck and below +3 on aim) -> not shown.
- **Before sealing:** measure the spread between parents on DEV and run a power simulation; if L2 or G0 has under 80%
  power at a true +15 luck or +8 aim, add parents.
- **Build (CPU, now):** puzzle generator, twin builder, both checkers, the shared sampler, and the sleep plumbing B2
  lacks (resume from a checkpoint, targets from kept tries, skills replay), in a new `creative/` folder that imports
  `custom_io` without editing it (the custom reader/talker thread is building Plan B students there).
- **Cost (untested estimate):** B2 trains at about 8 updates a second on a 5090 (shown: 24,000 updates in 49 minutes).
  36 short sleeps plus sampling should take a few hours on one of Ben's machines, $0.
- **Owner:** a Sonnet implementation thread builds and runs it; this thread keeps the design and scores the result.

## 7. C2 spec: rules from a few examples (provisional; sealed after C1's plumbing works)

- **C2a, the checker.** B2's pointers today point at fixed prompt slots, so a program cannot be re-run on each example.
  C2a lets a program point at input roles (the example's input, and the query's input) plus constants. A try passes
  only if it reproduces every example pair in the prompt; then it answers the query. Families: the induction families
  `verify.py:321-405` already enumerates (fewshot_number_rule, rule_apply and the others listed there), where B2 trails
  the step-writing transformer (fewshot_number_rule -9.4, rule_apply -6.3 points, 2-seed means from
  `SCREEN-ANALYSIS.json`). Warm-up: solver programs from that enumerator on a subset of rule kinds; held-out rule kinds
  sealed by hash.
  - Pass (mechanism): the example check agrees with the answer key on >= 99% of accepted tries; practised kinds do not
    drop by more than 2 points.
  - Needs from B2's owner: input-role pointers; this thread specifies, they decide how.
- **C2b, the creative test.** On held-out rule kinds, with no answer keys: 32 tries per question, keep tries that fit
  every example, sleep. Arms N, W, R (fits no example check, matched count), H (each try relabelled with the rule it
  actually computes on the examples). Comparison nets: a same-size plain transformer and a fresh net, each given k
  labelled examples of the new kinds, k in {0, 8, 32, 128}.
  - Pass: first try on fresh questions of the held-out kinds W - N >= +15 and W - R >= +10 (intervals above 0);
    report "examples to learn": the k at which the plain net matches W.
  - Proved wrong: W - R upper end below +3.
- **Owner:** the same Sonnet implementation thread after C1, with the input-role change agreed with the custom
  reader/talker thread.

## 8. How it fits the other work

- **Plan B test B1** (teacher-made variety for a 10.8M B2) runs first. C1 does not need its data. If B1 passes, C2 onward
  use the bigger student, and the 1.2B also writes C6's stepping stones.
- **The B2 6-seed confirm** gates C1 and C2 (D7); its leak check (loops:0) is now a creative lesion too.
- The swarm result (members all miss the same questions) says more copies of one model are not a variety source; D4 and
  C3b make variety inside one model.
- The ultracode plan route is the same idea as D1 inside the sandwich; the two lines stay separate.

## 9. Risks, and what would change the plan

- **C1 or C2 cold start** (the DEV gate fails): stepping stones (C6's method) or hindsight before retrying.
- **Sameness** (the DEV gate fails): C3b before retrying.
- **Small model, short programs:** B2's 7 write steps may be too few for later floors; growing them is its own change.
- **Language growth vs "no new hand-written rules"** (Ben, 09-26): C2, C5 and C6 need input roles, plan ops, string and
  date ops. Default: a small general base set (like a calculator for text), with the pieces library growing the rest.
  Ben can overrule before C2 is sealed.
- **Transfer may not come.** The evidence leans against automatic transfer between families; C6 and C10 are where it
  shows.
- **Minecraft is far.** Small-model Minecraft is a research gamble; the crafting world and Craftax are the honest near
  targets.
- **Outside opinion:** a GPT-6 Pro prompt is in `reviews/gpt6pro-creative-roadmap-2026-10-06.md`; its reply gets checked
  against the code before anything changes here.

## 10. Review log (before posting)

- **Coordinator:** lead with rules-from-examples (now C2, the main first test); design variety in before the first
  sleep (shared sampler and a sameness gate); gate on B2's confirm and add its loops:0 and donor lesions; pull a tiny
  crafting world forward (C5); name the owner of the program-language gap; ask Ben about parking ideas; link the
  Dreamer 4 claim. Not taken: making "can't, ask Ben" autonomous, because the asking is the finished model's behaviour
  that Ben asked for; the research loop itself only logs it.
- **Opus critic:** C1's add/subtract puzzles had one solution almost always and a trivial solver, so the claim is now
  capped and the puzzles use + - x /; reach at pass@4; hindsight arm H plus a wrong-relabel control; independent
  parents and v2's interval rules restored (G1, G0 against N, G2, the placebo-too-close verdict, a power check); checker
  and targets fitted to B2's code (ops, constant clashes, minus signs, seven write steps, answer pointer); a fixed sleep
  recipe; fact fixes (P0's one op_define hit, post-hoc variety counts, blurt-2b proved wrong, blurt-4's reach effect
  only suggested, the idea judge's diverged fitter); Ben's main measure (examples to learn) and test-time training
  added; Ben's rules on Claude-written frames, the filter role (C4), replay choice (asked before C3) and stuck-then-
  return (C9).
