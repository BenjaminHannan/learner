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

Reviewed before posting by the project coordinator and an independent Opus critic, then updated with the build
thread's findings and GPT-6 Pro's reply (10-06); what changed is in section 10.

## 0. For Ben

Your definition: when the thinker is stuck, a creative part tries lots of different things, a checker keeps the ones
that work, and the model learns from them in sleep so next time it doesn't need luck.

- **It has worked once, in one place.** On number puzzles with a borrowed 1B, sleeping on its checked lucky hits about
  doubled its right tries on fresh puzzles, and it replicated (63 to 131, then 59 to 138.5, out of about 2,000 tries).
  First-try solving barely moved.
- **Four walls make it the hardest problem.**
  1. Cold start: on a brand-new kind of task there are no lucky hits, and no hit means nothing to learn from. Tonight,
     32 tries by our own thinker B2 found an answer for 1 question out of 240 on three never-seen kinds.
  2. Sameness: B2's 32 tries hold only 2 to 4.5 programs that really differ (averages), and sleeping on the same
     answers over and over once shrank the old model's reach from 27-29 puzzles to 3-4.
  3. No checker yet for open worlds: there the checker has to be a simulator or the game itself.
  4. B2's program language can't even write some answers (dates, word edits).
- **The plan climbs four floors**, one tested step at a time:
  - Search: try, check, sleep inside our own thinker.
  - Invent: first hits on never-seen kinds, through stepping stones, a library of reusable pieces, and beating the
    teacher.
  - Choose: it picks its own practice, calls creative mode when stuck, and asks you when something is truly impossible.
  - Worlds: a tiny crafting world early, then a small Minecraft-like game, then Minecraft.
- **The first real test (C2) is your few-examples idea.** The model gets a few examples of a new rule, tries many
  programs, keeps the ones that reproduce every example (no answer key needed), and sleeps on them. The cheap
  machinery check before it (C1, make-the-target puzzles) was closed on 10-06: practice on right answers made B2's
  first answers better on both trial copies, but its right tries rose enough on only one of the two (1.66x and 1.29x
  against a 1.6x bar fixed in advance), so C1's sealed test was never opened. C2 then needed easier
  versions of its new rules before any try fitted (10-06/07), and its trial run (10-07) passed only on the two rules
  that need one fixed program (x times x, last digit); the rules that need a number read off the examples did not move
  and a second night did not climb. Next is one fix: keep the old add and multiply skills alive during every sleep,
  since the stepping stones wiped them and every harder rule is built from them. Its sealed test
  waits for B2's 6-run confirm. Every sleep test now scores better
  first answers separately from better search (GPT-6 Pro's main point), and C2 passes only on first answers.
- **Settled (Ben, 9:24 PM ET 10-05):** ideas like gifts or plans don't need a creative model. Creativity is only for
  when the model runs into trouble on a problem it is trying to solve. Gift and plan ideas are out of scope.

## 1. What "creative" means here, and the scoreboard

**Definition (operational).** Within a fixed budget of tries, the model finds checked solutions to problems it could not
solve on its first try and that nobody gave it the answer to (discovery), then learns from them so it needs fewer tries,
and fewer examples, next time (learning). Discovery and learning are scored separately: a searcher can discover without
learning, and a student can learn answers it never discovered.

Every creative test reports the same scoreboard, on fresh problems the model never practised, always with its
denominators and next to the value-blind floor (what a try that follows the rules but ignores the target scores):

| Score | What it counts | Why |
|---|---|---|
| Luck (hit rate) | share of kept tries (at most 32) that pass the checker | the old runs' main measure (blurt-3) |
| Reach | problems with a passing try within 4 tries, and within 32 | catches variety collapse that luck hides; pass@4 because pass@32 saturates (on C1's puzzles a value-blind rule follower already reaches 48.8% at 32 tries, 9.2% at 4, 2.4% per try; shown, `creative/` build, PR #44) |
| First try | greedy solves | what the user sees; it moved least before (blurt-2) |
| Examples to learn | labelled examples a same-size plain net needs to match the creative model on a new kind; also a fresh net | **Ben's main measure** (ben-goals, 09-26: "how few examples a new kind takes to learn") |
| Variety | distinct programs per problem that change the result (counted on the steps that do something) | variety is the fuel |
| Frontier | problems no teacher, solver or training answer covered, solved | the one job only creativity can do (blurt-5s) |
| Transfer | task kinds never practised | Ben's carry-over goal |
| Harm | practised skills lost after sleep, against the parent | sleep once cost 61 and 98 of 200 general answers (dl-5) |
| Lesions | the same scores with loops:0 and with a donor's thinker state | a "creative" gain must come from the thinker, not a pointer leak (B2 missed loops:0 by 1.76 points in one seed) |

Scope (Ben, 9:24 PM ET 10-05): the creative part is only for when the model runs into trouble on a task. Open-ended
ideas (gifts, plans) are not its job, so no taste judge or novelty score is needed.

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

1. The tested recipe of sleeping on checked hits raised luck and reach within one family; the tested recipe of sleeping
   only on repeated known answers concentrated success on fewer puzzles (shown, 1B, one family). This does not show that
   replay of old skills is harmful in general.
2. Where a solver or teacher can answer, its answers teach as well as creative hits (shown once, blurt-5s; answer length
   is a confound). So the loop is needed most where no solver or teacher can answer, and is also useful where search is
   cheaper than the teacher or aims at the student's own gaps: expensive search becomes cheap first tries (Expert
   Iteration's split of searcher and learner; suggested).
3. First-try gains are small and unstable; luck and reach move more (shown). Sleep has so far improved the searcher more
   than the first answer, so every sleep test reports first try as its own mark.
4. Learned judges are weak at small size (weak evidence for ideas; suggested generally by "Mind the Gap", 2412.02674).
   Ideas are now out of scope, so this matters only for C4's ranking head, which is always checked against real checkers.
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
3. **No checker yet in open worlds.** Puzzles and rules carry their own check; in a game the check has to be the
   simulator or the game itself (C5, C10), and small learned judges are weak.
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
- **D2. The deciding filter is always a real check.** Checkers are part of the task (the target, the examples, the
  simulator or game), never a learned judge's say-so. C4's filter only ranks tries before the real check runs.
- **D3. Teacher where it can answer, creativity where it can't.** The 1.2B writes problems, stepping stones and fading
  hints during training only (lesson 2). It never ships and never judges inside the shipped model. Ben's 09-26 rule
  holds: nothing written or judged by Claude goes into training. Test prompts use one fixed instruction line, the same
  in every arm and masked from the loss (Ben's 09-26 16:50 card allows this in tests); wording meant for a build comes
  from the 1.2B. Order of making a practice item: a valid short program first, then its input/output examples, then the
  1.2B's wording of that task; a held-out sample of worded items is checked against its program before a build uses
  them. Answer-informed hints are counted as hints, and the student is always scored with every hint removed.
- **D4. Variety is designed in, twice.** At try time, a shared sampler drops duplicate programs before running them
  and branches over the top first steps. At sleep time, a variety rule (diverse picks, rare correct answers upweighted,
  some wrong tries pushed down) is tested as its own change (C3).
- **D5. Climb a ladder of checkers:** the target (C1) -> the examples (C2) -> a simulator (C5, C10) -> the model's own
  trained filter that ranks tries for those checks (C4).
- **D6. Honesty rules for every step:** one change, marks sealed before running, a placebo arm, a harm mark, lesions,
  fresh sealed test sets, 6 independent parents before any claim (the project's noise rule), and the result that
  proves it wrong.
- **D7. Gates and machines.** Sealed test sets (T1, T1b) of C1 and C2 are opened only after B2's 6-seed confirm passes;
  its seeds 200-205 become the 6 parents. If Plan B's B1 passes first, the 10.8M students are the parents. Before that, a
  DEV-only pilot may run on the two existing B2 parents (s100, s101): warm-up, floors, the aim check, the gates, and the
  learning-rate choice with the PC arm. It makes no claims and leaves T1 sealed. CPU builds are done (PR #44). Runs go
  on Ben's own machines first (the 5070 Ti or the M1 Pro, whichever is free, sharing with B1 under the GPU-BUSY rule).
  Research gathering for later steps goes to Sonnet agents.

## 5. The roadmap

Four floors. Each step's single change, pass mark and kill result are below. Marks for C3 onward are provisional and get
sealed in their own spec before running.

### Floor A: Search (try many, keep what checks, learn)

| Step | One change | Pass (provisional after C2) | Proves it wrong |
|---|---|---|---|
| **C0** (done 10-06) | Scoreboard on B2, no training | Read: cold start on new kinds, narrow variety (shown) | n/a |
| **C1** machinery check | B2 sleeps on its own checked tries for make-the-target puzzles (+ - x /); claim capped at "the loop works on B2", since a solver exists. Hindsight arm included. **Retired 10-06 at its DEV gate** | Section 6 | Section 6 |
| **C2** few-examples rules (the main first test) | C2a: programs over input roles, checked by re-running them on the prompt's own examples (no answer key). C2b: key-free sleep on held-out rule kinds | Section 7 | Section 7 |
| **C3** keep the variety | Variety sleep rule (diverse picks + rare-correct upweight + some wrong tries pushed down), 5 nights, on C2's family, against C2's plain sleep; a fixed share of old-skill replay and at most a few near-duplicate programs per problem in both arms. Ask Ben first: rule-picked replay (his 09-21 "sleep is automatic") or model-picked (his 09-28 note) | Reach@4 after night 5 >= plain + 5 points (interval above 0); distinct rule-following programs do not fall night to night; first try and luck within 2 of plain; old skills within 2 of the parent | Reach@4 no better than plain |
| **C3b** (only if a sameness gate fires) | One variety source at a time, each against the plain sampler at the same tries and checker calls: (a) half the tries are single type-valid edits of earlier winning programs; (b) winners kept by kind of behaviour instead of by score; (c) a small "style code" the sampler is conditioned on | Distinct rule-following programs per problem at least double at equal luck, and reach@4 >= plain + 5 on every parent | Variety up, reach flat |
| **C4** its own filter | A head trained on the checker's verdicts ranks tries before they run (Ben's "one model is dreamer, filter and worker") | AUC >= 0.80 against the checker on fresh tries; ranking raises pass@4 by >= 10 points over random order at the same tries | AUC < 0.65 |
| **C5** first world | A tiny text crafting world (8-12 items and recipes); the thinker writes plans, the simulator is the checker; sleep on plans that reached new items. Needs plan ops from B2's owner | Reaches items it never saw a plan for >= 10 points more often than no-sleep, every parent, interval above 0 | Within 2 points of random plans |

### Floor B: Invent (first hits on kinds it has never seen)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C6** stepping stones | Easier variants of fresh, sealed new kinds, made program first (short verified programs, then their examples, then the 1.2B's wording), never from their tests; the loop climbs one step at a time (Lee 2025, Ben's "reframing"). Placebo: matched unrelated practice; positive control: full-difficulty solver programs. Only kinds B2's language can express (checked first); not P0's four kinds | New kinds: reach@32 >= 25% and >= the value-blind floor + 15, first try >= 10% and >= placebo + 10, examples-to-learn at least halved against the plain net | Reach@32 < 10%, or no better than the placebo |
| **C7** pieces library | Repeated sub-programs (from training solutions only) become new named operations the thinker can call (Stitch, DreamCoder); a piece counts only if reused in 2 or more kinds. Placebo: type-correct random pieces of matched size and count; also a no-library reference; equal checker calls | New-kind reach >= both the placebo and no library + 5, every parent, also at equal wall-clock; >= 30% of new solutions use a counted piece. Shorter programs alone count as a speed win, not more reach | Reuse < 5%, or reach no better than random pieces |
| **C8** beyond the teacher | Checkable problems the 1.2B gets wrong with the same 32 tries, the same checker and tools, on a sealed set; budgets named in the spec | Solves >= 20% of the teacher's failures | < 5% |

### Floor C: Choose (own practice, and knowing when to stop)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C9** | The model picks practice by learning progress (problems it solves sometimes, not always). The worker calls creative mode when stuck and returns to work with what it found (Ben, 09-21). "Can't" is said only with a certificate (a complete search of the finite program space); otherwise it says "not found within this budget". The finished model asks its user when a task is truly stuck (Ben, 09-21 and 09-25), while our research loop just logs it and moves on | >= 1.3x fewer updates than random practice to reach a fixed reach level; "can't" on a balanced solvable/impossible set: precision and recall both >= 0.9; stuck-then-return raises task success over never calling creative | No faster than random practice |

### Floor D: Worlds (from puzzles to Minecraft)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C10** | Craftax-Classic (fast symbolic Crafter), then Crafter pixels; a small world model lets the thinker "dream" tries that the real game then checks (Ben, 09-18: dreams count only if a simulator checks them) | Beats a same-size plain agent at equal steps by >= 5 reward points, interval above 0; stretch: human level (65%), all 22 achievements | At or below the same-size plain agent |
| **C11** | Minecraft (screen in, keyboard and mouse out) | First rung: wooden-pickaxe rate above a same-size plain agent at equal steps. Today's best pixel result: Dreamer 4, diamonds in 0.7% of episodes at 2B weights. "Beats Minecraft" gets a written definition (for example, the Ender Dragon from a fresh survival start, no privileged state for the agent) before this floor starts | First rung not above the plain agent; the rest is a research gamble |

**Out of scope: ideas with no checker** (gifts, plans, messages). Ben, 9:24 PM ET 10-05: these don't need a creative
model; creativity is only for when the model runs into trouble.

## 6. C1 spec: machinery check (seal before any GPU stage)

**Status: retired 10-06 at its DEV gate; T1 and T1b were never read** (see the PC gate under Marks and "What C1 leaves
behind" at the end of this section). The spec below is kept as written.

Built on creative prototype v2 (five Opus review passes, 10-03), moved to B2 and fixed by this roadmap's review.

- **Claim cap.** A solver exists for these puzzles, so a PASS means "B2 learns more from its checked tries than from
  look-alike tries, and the sleep machinery works". It does not show creativity (lesson 2).
- **Parents:** the 6 B2 confirm seeds (200-205), one sleep per arm each. If they are not available, B2_s100 and
  B2_s101 with 3 sleep seeds each, paired within parent, with the claim limited to those two parents. Until then, the
  DEV-only pilot on s100 and s101 (D7) runs the warm-up, the aim check, the gates and the PC learning-rate choice.
- **Puzzles:** "use A, B and C once each with + - x / to make T", exact division only, numbers 3..40 excluding 10 (so no
  number equals a constant slot 1, 2, 10 or 100), T >= 1 (B2's number reader drops minus signs), solvable, no 2-number
  shortcut, T not a given number. Every step is exact integer arithmetic, as in B2's executor (an inexact division is
  invalid; shown, `custom_io/models/progparse.py` `ex`, `creative/puzzles.py`), so "solvable" means solvable in B2's
  language. Twin targets on every test puzzle (same numbers, two targets with different solutions). Splits by number
  set: practice 1,024; DEV 128; T1 256 (once); T1b 256 (replication); X 128 four-number puzzles (report only). One fixed
  instruction line, identical in every arm and masked from the loss; C1 joins no build.
- **Measured floors and solution counts** (shown, PR #44, CPU, no model): a value-blind rule follower scores 2.4% per
  try, 9.2% at pass@4 and 48.8% at pass@32 on DEV (T1: 2.4 / 8.9 / 48.1); the uniform floor is near 0. Targets average
  1.9 solutions (DEV 2.0, T1 1.9, T1b 1.7, X 4.4). Reach@32 is therefore report-only in C1, and reach@4 is the reach
  mark. The generator stays as it is: preferring many-solution targets would raise every floor. Counts of distinct
  correct programs are report-only here and are read on X.
- **Shared warm-up:** every arm starts from the same warmed parent. N is this warmed parent. Warm-up harm against the
  original B2 is reported. Changed after the DEV pilot (10-06): the warm-up mixes 1,500 two-number puzzles with
  three-number puzzles, all with solver programs, on number sets in no sealed or practice split, with the same skills
  replay as the sleeps. The three-number count is the smallest of 1,500, 3,000 and 6,000 that passes the gates on
  DEV (the least warm-up that teaches the format leaves the most room for sleep to help); the warmed parent's DEV luck
  and first try are reported as headroom. Chosen 10-06: **1,500, with the 4-visit cap**, on both pilot parents. In this puzzle family any labelled three-number program is a correct
  solution for some target, so the format cannot be taught without some aiming; the claim cap above already covers
  that. If 6,000 still fails the signal gate: first check whether the warmed parent fits its own warm-up puzzles; if
  not, allow up to 16 visits per warm-up record (the 4-visit cap is for sleep records); if it fits but fails DEV, add
  "dreams" (random rule-following programs labelled with the value they make, as in DreamCoder and DeepCoder), which
  are code-made like the solver puzzles; if that fails too, stop and redesign (a step-by-step subgoal head as in
  ExeDec would be an architecture change, outside C1). Hindsight on the model's own tries is not a warm-up: raw B2's
  tries break the rules 99.6% of the time, and a rule-breaking program cannot be relabelled into a valid three-number
  puzzle. Hindsight stays an arm (H).
- **Second DEV pilot, B2 s100 and s101 (shown, Mac, with skills replay, `creative/results/` on
  `claude/project-thread-2zeaoc`, commit 8c82c5cad1):** the mixed warm-up works. At the 1,500 rung the warmed parent
  solves 543 and 535 of 1,024 practice puzzles, and on DEV scores luck 4.7% and 4.6% against the value-blind floor of
  2.4%, reach@4 16.0% and 16.1% against the floor's 9.1%, with 4.4 and 4.3 distinct rule-following programs per puzzle.
  The 6,000 rung with 16 visits reaches luck 8.2%, reach@4 27.9% and reach@32 81% against the floor's 50.8%. Every rung
  failed the old signal gate only because the share of tries that follow the rules sat at 25-29% against a 50%
  threshold, at every rung and at every temperature from 0.21 to 3.0. That threshold was the wrong measure: the
  value-blind follower's own share is 58%, so 50% asked for near-perfect legality, while among its legal tries the
  warmed parent hits the target 16% of the time against the follower's 4.1%, which is the aim the gate was meant to
  look for (5.4x at the 6,000 rung, 7.9x after 16 visits). The gate was rewritten above; the sealed T1 marks were not
  loosened to match, they were re-scaled for a separate reason (see Marks). Still open for the ultracode thread, not
  blockers: why legality sits at a quarter of tries, and why variety is 4.4 distinct programs against the follower's
  18.7. Leading guess (untested): B2's 200k skills rows let programs point at the constants 1, 2, 10 and 100, which
  C1's checker forbids, so its prior writes illegal operands; the rejection-reason breakdown settles it cheaply.
- **DEV pilot, B2 s100 (shown, CPU, no skills replay, `/mnt/project-files/creative-pilot/`):** raw B2 writes
  rule-following programs on 0.2% of tries and solves 1 of 256 practice puzzles; after the two-number-only warm-up
  (200 updates) 0.4% and 3 of 256, with 0.1 distinct rule-following programs per puzzle (gate 4). Both gates failed.
  B2 has to chain a result into a second step, which two-number puzzles never show. The PC arm (1,377 solver records,
  86 updates, lr 1e-3 at the grid edge) moved DEV luck from 0.05% to 2.0%, first try from 0 to 7.8% and reach@32 from
  1.6% to 45%, at a temperature of 2.0 that was picked while every score was near zero.
- **Gates on DEV after warm-up** (rewritten 10-06 after the second pilot; see the pilot bullet below for why):
  signal: the warmed parent has an accepted try on at least 100 distinct practice puzzles. Aim: among its
  rule-following tries, the share that hit the target is at least twice the value-blind rule follower's (4.1%), which
  is a feasibility check, not a claim; G0 is the claim. Sameness: >= 4 distinct rule-following programs per puzzle on
  average, by canonical program key (forcing the top 8 first steps keeps about 7 result-changing programs even near
  temperature 0, so that count is reported, not gated). The share of tries that follow the rules is reported, never
  gated: a model that writes fewer legal programs but aims them better is what C1 wants, and the value-blind follower's
  own share is only 58%, so any threshold near 50% asks for near-perfect legality instead of signal. A failed gate
  stops C1 with T1 sealed (C3b first for sameness; fix the warm-up for signal).
- **Aim check on DEV (no training; added from GPT-6 Pro's reply):** at the same 32 tries and checker, compare the warmed
  parent's tries for the real target, its tries for the twin target scored against the real target, and the value-blind
  rule follower; luck and reach@4. Reported, not a gate: in blurt-3 luck started near chance and sleep created the aim.
  If the rule follower matches the parent, search is still random before sleep, and G0 decides whether sleep taught
  aim. The same check is repeated on W after sleep.
- **Tries:** 32 per practice puzzle from the shared sampler: sample op and operand pointers at a DEV-chosen temperature
  (P0's sampler; chosen on the warmed parent by reach@4 among temperatures that pass the sameness gate, with the grid
  widened whenever the choice lands on its edge), drop duplicates (commutative order merged) before running and top up, branch over the top 8 first
  steps. Variety is reported with and without branching, so the sampler's own variety stays visible.
- **Luck is counted over samples, not distinct programs (fixed 10-06 after pilot 3):** luck is the share of sampled
  tries the checker accepts, with repeats counted, from B2's plain sampler at the frozen temperature (the model alone,
  as in F1); reach@4 is whether any of the first 4 sampled tries hits, in sampling order. This is how blurt-3 counted
  ("right blurts among 30 samples"), and the marks below were scaled from blurt-3. The deduplicated, masked tries above
  still collect every sleep pool and measure variety (sameness), and their luck is reported, never gated. Why (shown,
  `creative/scoreboard.py` "all shares are over kept (distinct) tries"): counting each distinct program once caps luck
  at the number of solutions over the number of distinct tries. DEV targets have 1.97 solutions; the warmed s101
  parent already finds 1.42 of them among 10.6 distinct masked tries (luck 13.4%), so at that variety luck could reach
  at most about 18.5%, 1.39 times N, and a 1.6x mark was out of reach unless variety fell. Pilot 2's plain dedup luck
  had the same cap (27.3 distinct tries, at most 7.2%, 1.54x). The error was made here when the marks were re-scaled
  from blurt-3's sample count onto C1's distinct-try share.
- **Used-number mask (adopted 10-06, disclosed test scaffolding):** every arm's tries, the temperature choice and the
  floors use the level-4 mask from the ultracode thread (`creative/legal.py`, PR #45): B2's own op and pointer heads
  pick every step, restricted to unused numbers and results, + - x /, exact division, and a stop after the last real
  step. The mask never reads the target (tested), so it cannot aim. Why: on DEV half of all plain tries broke the rules
  the same way, by reading in step 2 a number step 1 had already used, because nothing in B2 marks a slot as used; that
  is bookkeeping, not the creative question. Shown on DEV (1,500 rung, T 0.21): luck 4.7% to 13.1% (s100) and 4.6% to
  13.4% (s101), 10.5 legal programs per puzzle instead of 4.4, and own-target luck still 2.9x and 3.2x the twin target's,
  which sits at the value-blind follower's rate, so the mask makes no hits itself. Under Ben's 09-26 Redirect rule this
  is an allowed stand-in: disclosed test scaffolding that isolates the learned part being tested, never product work.
  The product route is a learned "used" mark inside B2 (B2 thread, untested). Disclosure: chosen after DEV numbers; the
  same sampler for every arm, so it favours none; T1 and T1b stayed sealed. Floors are recomputed under the same rules
  (the follower is uniform over exact legal programs: 4.1% per try), and the plain sampler's legal share is reported
  for every arm, so whether sleep teaches B2 the bookkeeping on its own stays visible.
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
- **Sleep recipe (identical across arms):** fresh AdamW; every puzzle record is seen the same number of times
  (visits), so updates = visits x records / 32; every batch half puzzle rows, half replay of the 200k skills rows;
  learning rate and visits chosen on DEV using the PC arm only (lr 3e-4 or 1e-3; visits 4, 8 or 16, and one try at 32
  if 16 wins), among settings that cost skills at most 2 points, then frozen. Visits were fixed at 4 until 10-06 (see
  the PC gate under Marks).
- **Marks** (6 parents; luck = share of 32 plain sampled tries accepted on T1, repeats counted (see the luck bullet);
  95% t-intervals over parents on paired differences).
  Re-scaled 10-06, before any sleep arm ran on the new warm-up, because the old point marks were mis-scaled: the one
  replicated creative result we have (blurt-3 and blurt-3r on the 1B) moved luck from 3.2% to 6.4-6.9% and from 2.9% to
  6.4-7.4%, which is +3.2 to +4.4 points, a doubling. A +10-point mark would have called those runs a failure, and B2's
  warmed luck is on the same scale (4.7% at the chosen rung). The marks are now ratios with an absolute guard, set
  below the old effect so the test can detect the effect it is looking for:
  - L1: W / N >= 1.6 and W - N >= +3 points, W above N for every parent. (Old runs: 2.0 to 2.5x.)
  - L2: W / R >= 1.4 and W - R >= +2.5 points, interval above 0. (Old W against its control: 1.5 to 2.6x.)
  - G0 aim (own-target hits minus twin-target hits): W / R >= 1.5 and W - R >= +3 points, interval above 0, and W above
    N with interval above 0. Provisional: the old runs had no twin targets, so this one is scaled by analogy.
  - G1 reach@4: fails only if the upper end of W - N is below -2.
  - G2 stopping: STOP-rule luck W - R >= +4.
  - G3 harm: skills pooled-5 drops by at most 2 points against the warmed parent, every parent.
  - F1 first try (added from GPT-6 Pro's reply): greedy solves on T1, W - N >= +5 and W - R >= +5, intervals above 0.
    Scored on B2's plain greedy try, without the mask (what the thinker does alone); the masked first try is reported
    beside it.
    It decides whether a PASS also turned search into first answers.
  - Lesion: tries sampled from a donor puzzle's prompt (its twin) and judged on the recipient's target must not score
    above the rules-only floor; otherwise the run is void. (loops:0 writes no steps, so its luck is 0 by construction;
    reported, not a test.)
  - H question (secondary): reach@32 H - W >= +5 with interval above 0, and H - H' above 0.
  - PC gate: PC / N >= 1.6 and PC - N >= +3 points, moved with L1 because it is L1's positive control: it must stay at
    L1's level or L1 becomes unreachable by design. Measured after the warm-up, at the chosen temperature, with skills
    replay on; PC's first-try gain is reported beside it. Disclosure: PC on the first, failed warm-up gave +2 points on
    DEV (0.05% to 2.0%), so this re-scaling is not blind to every sleep number, though its size comes from the old 1B
    runs and not from that one. If PC still misses on both pilot parents, the roadmap thread decides before sealing.
    Pilot 2 with the plain sampler (shown, DEV, commit 531adb7ea): PC / N 1.15 and 1.20, PC - N +0.7 and +0.9 points,
    first try -1.6 and +1.6 (one DEV puzzle is 0.8 points), at lr 1e-3 with 4 visits (172 updates); lr 3e-3 and 1e-2
    cost skills 9 to 68 points. Decided 10-06: the gate is judged on the masked sampler, which every arm uses, and pilot
    2 stays a labelled comparison. The mark does not move. The PC arm gets a dose grid on DEV (see the sleep recipe)
    because pilot 2 suggests 4 visits is too small a dose: the same kind of solver programs, at 6,000 three-number
    puzzles and 16 visits, raised the warmed parent's plain luck from 4.7% to 8.2% (1.75x), while 4 visits of PC moved
    it 1.2x (suggested, not shown: those two doses differ in puzzle count as well as visits). If the masked PC misses on
    either parent at every setting that keeps skills within 2 points, C1 stops with T1 sealed and comes back here.
    Disclosure: the dose grid was added after seeing PC miss on DEV; it applies to every arm the same way, and T1 and
    T1b stayed sealed.
    Pilot 3, masked (shown, DEV, s101, commit 9e63311d9): on distinct-try luck PC missed at every setting (best lr
    3e-4 with 16 visits: 1.16x, +2.1 points; 32 visits worse), which the stop rule above sent back here. The cause is
    the cap in the luck bullet, not the sleep: at that frozen setting PC cut its loss on the puzzle records from 4.86 to
    1.96, raised the plain first try from 8.6% to 14.8% and the masked first try from 20.3% to 31.3%, and raised
    plain luck counted over samples (8 per puzzle, repeats counted) from 8.6% to 14.3%, 1.66x and +5.7 points, with
    skills harm 0.4 points. Decided 10-06, before the roadmap thread saw any s100 number other than its distinct-try
    best (1.11x, +1.5): the PC gate is judged on plain luck counted over samples, at the setting each parent's pilot 3
    already froze by the rule above, from the numbers pilot 3 already logged (`dev_plain_luck`, 8 samples per puzzle);
    the mark stays 1.6x and +3 points on both parents. s101 passes narrowly (1.66x; with 128 puzzles a few points of
    noise either way). If s100 passes: freeze, and the power simulation uses this measure (re-measured with 32 samples
    per puzzle and reported) before sealing. If s100 misses: C1 is retired at its DEV gate with T1 and T1b never read,
    and the build thread moves to C2. Disclosure: this is the third change made after seeing DEV numbers (gates,
    dose, now the luck count); the bar did not move, the measure now matches the runs the bar was scaled from and
    matches F1, and T1 and T1b were never read.
    **Result (shown, commit dcdcaf011):** both parents froze lr 3e-4 with 16 visits. s100: 9.9% to 12.7%, 1.29x and
    +2.8 points, a miss; s101: 8.6% to 14.3%, 1.66x and +5.7, a pass. By the rule above, **C1 is retired at its DEV
    gate.** Not taken: s100 at lr 1e-3 with 16 visits reached 16.2% (1.64x), but choosing that setting after seeing it
    would have been a fourth change after the fact.
- **Ordered verdicts:** void (checkers disagree on a T1 try, unresolved above 1%, or a lesion fails) -> gate stop ->
  placebo too close (over half of R's records are accepted tries) -> PASS (L1, L2, G0, G1, G2, G3), named "PASS with
  first answers" when F1 also holds and "PASS, search only" when it does not -> rules only (L1 holds, G0 fails) -> gain with harm (G3 fails) -> **proved wrong** (the PC gate passes, yet W - R has an upper end
  below +1.5 points on luck and below +1 on aim) -> not shown.
- **Before sealing:** measure the spread between parents on DEV and run a power simulation; if L2 or G0 has under 80%
  power at a true +15 luck or +8 aim, add parents.
- **Build (done, CPU-tested, PR #44):** puzzle generator, twin builder, both checkers (23 planted bad programs rejected,
  10,000 fuzzed tries without a split), the shared sampler, the gates, the arms and the sleep plumbing B2 lacks (resume
  from a checkpoint, forced slot-id targets, skills replay, visit cap), in `creative/`, which imports `custom_io`
  without editing it. Not built yet: the warm-up, the power simulation and the run loop.
- **Cost (untested estimate):** B2 trains at about 8 updates a second on a 5090 (shown: 24,000 updates in 49 minutes).
  36 short sleeps plus sampling should take a few hours on one of Ben's machines, $0.
- **What C1 leaves behind (10-06):**
  - Shown on both parents, DEV, PC at the frozen setting: sleeping on checked right programs raised B2's first answer
    with used numbers greyed out (18.8% to 28.1%, 20.3% to 31.3%) and its hit rate among its legal plain tries
    (25.9% to 34.9%, 23.3% to 35.4%), with skills harm 0.1 and 0.4 points. Its plain first try moved +1.6 and +6.3
    points, so the unaided gain is not consistent across parents.
  - Shown: the same sleep did not teach the bookkeeping (plain legal share 38% to 36%, 37% to 40%). B2 needs a learned
    "used" mark on its slots; that is B2 work, not creative work.
  - Shown: luck must be counted over samples with repeats; counted over distinct programs it is capped by the
    solution count (see the luck bullet). C2 counts this way from the start.
  - Built and reused by C2: the sampler, both checkers, sleep with forced slot targets and skills replay, the arms.
  - Not answered on B2: whether sleeping on its own hits beats a placebo. That question stays answered only on the
    1B (blurt-3 and 3r passed; blurt-5s showed solver answers teach as well as own hits).
- **Owner:** the Sonnet thread "Build the first creative test" builds and runs it; this thread keeps the design and
  scores the result.

## 7. C2 spec: rules from a few examples (provisional; sealed after C1's plumbing works)

- **C2a, the checker.** A try is a program over the query's input slot, the constants and its own results. To re-run it
  on example i, the query slot is re-bound to that example's input; pointers at other prompt numbers are rejected and
  the program must read the input (built this way in PR #44, with no change to B2). A try passes only if it reproduces
  every example pair in the prompt; then it answers the query. Families: the induction families
  `verify.py:321-405` already enumerates (fewshot_number_rule, rule_apply and the others listed there), where B2 trails
  the step-writing transformer (fewshot_number_rule -9.4, rule_apply -6.3 points, 2-seed means from
  `SCREEN-ANALYSIS.json`). Warm-up: solver programs from that enumerator on a subset of rule kinds; held-out rule kinds
  sealed by hash.
  - Pass (mechanism): the example check agrees with the answer key on >= 99% of accepted tries; practised kinds do not
    drop by more than 2 points.
  - Representability first: a held-out kind is sealed only if its reference program runs in B2's executor within 7
    steps; kinds that can't are listed as wall 4, not tested.
  - Gates on DEV: cold start: an accepted try within 32 on >= 10% of questions and at least 3 times the value-blind
    floor (a random program over the input and constants that fits every example by chance, computed first); sameness
    as in C1. If cold start fails: stepping stones first, in C6's form on these kinds (short verified rule programs,
    against matched unrelated practice and full-difficulty solver programs).
  - **DEV gate result (10-06, Mac job 4, s100 and s101): stop, cold start.** Real rule rows: practised kinds add and
    mult (warm-up: 2,048 solver programs, 4 visits, skills replay); held-out kinds affine, square, sq_plus,
    last_digit, double_add (256 DEV questions; pool, test and labelled sealed). Best temperature 1.4 (the grid's top):
    reach@32 3.9% and 6.3% against a value-blind floor of 4.8% (gate: 10% and 3x the floor). Without the warm-up both
    parents write no rule-following program at all. So the warm-up teaches the format but B2's tries on new kinds are
    at chance. Why (shown from the data): the warm-up only ever writes "x, then one op with a built constant". Two
    held-out kinds are recombinations of those pieces (affine: multiply then add; double_add: add then double); three
    need a piece it never saw (reading x twice for square and sq_plus, the MOD op for last_digit). Per kind, reach@32
    at T 1.4 (s100 / s101, commit ebdc26e2c): double_add 13.7% / 9.8%, square 3.9% / 19.6%, affine 1.9% / 1.9%,
    sq_plus 0 / 0, last_digit 0 / 0. So the short recombination (double_add) is partly reachable, s101 sometimes reads
    x twice on its own, and the kinds needing a new op or a longer chain get nothing. Variety passes (12.6 and 15.8
    distinct rule-following programs).
  - **Stepping-stone stage (decided 10-06, the rule above):** C2 is not retired; it retires only if this stage also
    fails. One job per parent, DEV only, every sealed split stays closed:
    0. Practised-kind check (C1's lesson): the warmed parent on 256 fresh add/mult questions (new salt; practised kinds
       are not sealed), reach@32 and first try. If reach@32 is below 50%, re-warm with 16 visits, re-run the plain DEV
       gate on that parent, and use it for every arm below; if it passes alone, cold start was under-warming and C2b
       starts from it with no stepping stones.
    1. Stepping stones (SS): 2,048 rows made program-first by code, easier variants of the held-out kinds whose
       reference program has at most 3 written steps and whose parameters are in no sealed split's list: affine with
       a = 2 (b 3-15) or b in {1, 2} (a 3-6); sq_plus and double_add with b in {1, 2}; x mod k for k in {2, 3, 4, 5}
       (last_digit's family). square has no easier variant of its own; sq_plus's easy variants contain its program as
       their first step, which is the point of a stepping stone and is reported per kind.
    2. Arms from the same warmed parent, same sleep: SS; placebo P, 2,048 more add/mult rows on fresh questions
       (matched unrelated practice); PC, 2,048 full-difficulty solver programs for held-out kinds from the pool split
       (report only, never used for C2b).
    3. Each arm gets the same DEV gate (32 plain samples, repeats counted, temperatures 0.5-1.4, widened to 2.0 and 3.0
       when the best is the top edge, C1's standing rule), with reach@32, reach@4, greedy first try and variety per
       kind, and the number of DEV questions a stepping-stone rule also fits with a different answer.
    Decision: if SS passes the cold-start and sameness gates on both parents, the SS parent becomes C2b's N and C2b
    runs as written, its claim now "climbs from stepping stones". SS beating P by 5 or more points of reach@32 labels
    the help as the stepping stones rather than more practice (reported). If SS misses on either parent, C2 retires at
    cold start with its test never read, and wall 1 stands confirmed on B2; any other pattern comes back here.
  - **Stepping-stone result (10-07, Mac job 5, commit 05f1efb36; shown, DEV):** the warm-up took (fresh add/mult:
    reach@32 61% and 57%, first try 27% and 20%). Best-temperature reach@32, s100 / s101: N 5.1% / 9.8%, placebo P
    4.3% / 5.1%, SS 25.4% / 19.5%, PC (full-difficulty pool programs, report only) 63% / 68%; floor 4.8%, gate 14.5%.
    **SS passes on both parents and C2 goes on.** Read with four limits:
    - It passes only at the hottest temperatures (s100 at 2.0 and 3.0, s101 at 3.0 only), still rising at the top of
      the grid; at 1.4 and below it misses on both parents. SS minus P at matched temperature: +8.6 / +7.8 at 1.4,
      +21.1 / +16.0 at 3.0, so the stepping stones help at every temperature.
    - The gain is mostly square (reach@32 82% / 71% at 3.0, from 18% / 39% for N), whose whole program is the first
      step of the sq_plus stepping stones; then last_digit (31% / 8%, mod with a new constant); double_add moves at
      low temperature (N 4-14% to SS 22-29% at 0.7-1.4); affine and sq_plus stay near 0.
    - Greedy first try fits 1.6% / 0.8% of DEV questions: hits come from sampling wide, not from choosing well.
    - Even PC, trained on full-difficulty programs of the held-out kinds themselves, writes first answers for square
      (94%) and last_digit (100%) but sq_plus 18%, double_add 6% and affine 0% (s100): B2 learns one-step rules
      readily and the 3-5-step ones barely.
  - **Next: C2b DEV pilot on s100 and s101 (decided 10-07).** C2b runs as written from the SS parent (its N), on DEV
    only, with C1's lessons built in:
    1. Pool temperature: chosen on DEV by reach@32 among temperatures passing sameness; 3.0 is the grid edge, so the
       grid widens once to 4.0 and 6.0 (standing rule).
    2. Arms on the 1,024 pool questions, 32 plain samples each: W (tries that fit every example, at most 2 distinct
       per question), R (tries that fail the example check, matched questions and counts), H (tries relabelled with
       what they compute on the shown examples, same count), PC (solver programs for W's questions, same count).
    3. Sleep: learning rate and visits chosen on DEV with the PC arm (lr 3e-4 or 1e-3; visits 4, 8, 16), skills harm
       at most 2 points, then frozen; every arm sees each record the same number of times.
    4. Measured on DEV: greedy first try (fits and right) per kind and pooled, reach@4 and reach@32 with repeats,
       the practised-kind check and skills harm.
    5. PC feasibility gate before anything is sealed (C1's lesson): PC - N greedy first try on DEV >= +15 points
       pooled on both parents, the size of W's mark; if PC misses, the mark is out of reach by design and C2 comes
       back here.
    6. Night 2 (report only): sample the pool again with W's parent, sleep again on the new hits, and report per-kind
       reach@32 and first try. This asks whether the loop climbs (sq_plus after square, affine after double_add)
       rather than only copying what the stepping stones showed.
    7. Labels for the real C2b, fixed now (the marks do not move): gains are reported per kind; if the pooled pass is
       carried by square and last_digit alone (affine, sq_plus and double_add each within 2 points of N), the verdict
       reads "PASS, near-copy kinds only".
    The real C2b waits for B2's six confirm parents (warm-up, stepping stones, then the arms on each); its test stays
    sealed until then.
  - **C2b DEV pilot result (10-07, Mac job 6, commit 95df4f6d9; shown, DEV, s100 / s101).** Pool temperature 3.0 /
    4.0; dose frozen at 16 visits (lr 1e-3 / 3e-4; the grid is nearly flat, first try 0.39-0.42 everywhere); the
    corrupt-every-key test passes. PC - N first try +40.2 / +41.8 (gate +15). Greedy first try right: W 35.9% / 27.3%,
    N 1.2% / 0.4%, R 1.2% / 0.4%, H 0 / 0, so W - N = W - R = +34.8 [28.9, 40.6] / +27.0 [21.5, 32.8]; reach@4 W - N
    +21.1 / +5.1; skills harm 1.7 / -0.1. Tries that fail the example check (R), and the same tries relabelled to fit
    (H), teach nothing: the check is what makes the sleep work.
    - **Ruling: "PASS, near-copy kinds only."** Per kind W - N: square +96 / +94, last_digit +78 / +39, affine +4 / -2,
      sq_plus +2 / 0, double_add -6 / +4 points. The gain is 89 / 68 DEV questions, all of them square and last_digit;
      the three multi-step kinds net 0 / +1 of their 154 questions. The label as written (each multi-step kind within
      2 points of N) prints "beyond the near-copy kinds", because a 2-point band is narrower than one question (1.9-2.0
      points at 51-52 questions per kind), so wobbles of 1-3 questions, one of them a drop, tripped it. That band was
      my design error, and the less favourable reading stands. Replacement, fixed now before any C2b test number
      (fifth post-hoc change, toward the stricter label): a pass reads "beyond the near-copy kinds" only if W - N on
      the three multi-step kinds pooled has a paired 95% interval above 0; otherwise "near-copy kinds only".
    - Square and last_digit have one fixed program for every question (no parameter), so W's gain there is learning
      one program per kind that the stepping stones put within reach, not reading a new rule's parameter off its
      examples.
    - **No climbing (night 2, report only):** first try after night 2 on affine 4% / 0%, sq_plus 2% / 2%, double_add
      2% / 8%; only last_digit grows (78% to 82%, 39% to 65%). W's sleep records were 257 / 149 square and 87 / 39
      last_digit; the multi-step kinds gave 21 / 22 of 365 / 210.
    - **Practised-kind guard missed:** fresh add/mult reach@32 W - N -3.9 / -3.5 against "within 2" (noise about +-3).
      The larger loss came earlier, at a point my stage design never measured: the stepping-stone sleep took the same
      check from 61% / 57% (warmed parent) to 11% / 11% (N). Night 2 leaves 1.6% / 10%. Pooled-5 skills harm stays
      small, so the loss is in this question format.
  - **Next: Mac job 7, "keep the parts" (decided 10-07; DEV only, s100 and s101).** Every multi-step kind is a part
    the warm-up taught plus a part the stones taught: sq_plus = square then add B, double_add = add B then times 2,
    affine = times A then add B. The add B and times A parts are what the stepping-stone sleep wiped. Two explanations
    fit the missing climb (both suggested): (a) the parts were forgotten, so the loop had nothing to combine; (b) B2
    cannot learn programs of 3-5 steps that build a parameter out of its four constants, even when shown them (job 5's
    PC on 2,048 full-difficulty programs reached first try affine 0% / 4%, double_add 6% / 12%, sq_plus 18% / 14%).
    Job 7 makes one change and tells them apart:
    1. The change: every sleep (stepping stones, PC', each night) replays the 2,048 warm add/mult solver rows. The
       replay half of each batch is split evenly between the skills replay and these rows. Everything else as in jobs
       5 and 6: same seeds, rows, pool, temperature rule and dose rule, with visits widened once to 32 because 16 was
       the top of the grid (standing rule).
    2. Parts kept (if this fails, the job reports and stops): fresh add/mult reach@32 >= 50% for the stepping-stone
       parent with replay (N') and after each night; N' still passes the cold-start gate (reach@32 >= 14.5% with
       sameness at its best temperature); skills harm <= 2.
    3. Feasibility gate (C1's lesson): PC' = reference programs for every multi-step pool question (affine, sq_plus,
       double_add), at the dose chosen on DEV with PC' (now picked on the multi-step first try, then reach@4).
       PC' - N' greedy first try on the 154 multi-step DEV questions >= +10 points on both parents. A miss means B2
       cannot learn these kinds even from right answers, so the climb mark is out of reach by design: explanation (b),
       and the climb claim retires on B2.
    4. Climb, the main mark: W' night 1 and night 2 from N' at the frozen dose, each night sleeping on its own
       example-checked tries. Pass: multi-step first try W'(night 2) - N' >= +10 points with the paired 95% interval
       above 0, on both parents. Reported per kind, with night 1, reach@32 and records per kind.
       Build readings, confirmed 10-07: night 2 continues from the night-1 model and resamples the pool with it; N'
       skills harm is measured against the warmed parent and later models against N'; each parent stops on its own
       parts or feasibility miss (Mac job 7, commit a3f09b033).
       Partial, relayed 12:45 AM ET 10-07, before night 2 (shown, not yet pushed): parts kept (N' fresh add/mult
       61.7% / 61.3%; cold start 23.4% / 28.1%; harm +0.2 / -0.1); dose lr 1e-3 x 32 visits; feasibility PASS (PC' - N'
       multi-step first try +26.6 [19.5, 33.8] / +34.4 [27.3, 42.2]); W' night 1 multi-step first try only 0.6% / 1.9%.
       Reading fixed now, before the night-2 numbers: feasibility passing rules out explanation (b), since B2 does learn
       these kinds from right answers once the parts are kept (so job 5's weak PC was suggested to be partly the lost
       parts). If the climb misses or meets the proved-wrong line, the climb claim retires for this loop as specified
       (32 tries, one pool pass per night), and the cause is labelled (c): too few multi-step finds to learn from, a
       search limit rather than a learning or forgetting limit. Item 5's "explanation (b)" is corrected to (c) for
       that case. The next step then changes only the search, chosen from the per-kind records and reach@32.
  - **Job 7 result (10-07, commit f08bb3d22; shown, DEV, s100 / s101): between the marks; the climb as specified
    retires, cause (c).** Parts kept through night 2 (fresh add/mult 95.3% / 96.5%; skills harm +0.6 / +1.3).
    Multi-step first try W'(night 2) - N' +0.6 [-1.3, +3.2] / +3.2 [0.0, +6.5], night 1 0.0 / +1.3; per kind
    W'(night 2) - N': affine -1.9 / -1.9, sq_plus +3.9 / +2.0, double_add 0.0 / +9.8 (square +94 / +94, last_digit
    +69 / +94). Pass missed; the proved-wrong line not met. By the reading fixed before night 2, the climb claim retires
    for this loop as specified, and the cause is search:
    - N' finds few multi-step answers (DEV reach@32 on the multi-step kinds 1.9% / 5.2%), so W' slept on 25 / 30
      multi-step records in night 1 and 33 / 60 in night 2, against PC''s 614 (both copies).
    - Gains track finds: the one kind that moved (double_add on s101, +9.8) had the most records (17, then 46).
    - PC' shows the kinds are learnable except affine: first try sq_plus 53% / 61%, double_add 27% / 41%, affine 2% /
      4%, at the top corner of the dose grid (lr 1e-3, 32 visits), still rising, so feasibility may be understated.
  - **Next: Mac job 8, "more tries where it's stuck" (decided 10-07; DEV only, s100 and s101).** One change to the
    search, blind to rule kind (it uses only the example check, the signal a stuck model really has, and Ben's scope:
    creativity is for when it is stuck): each night samples every pool question 32 times as before, then gives every
    question with no example-fitting try 480 more tries (512 in all); questions already solved get nothing more.
    Everything else is frozen from job 7: start from job 7's N' checkpoint, pool temperature 3.0, dose lr 1e-3 x 32
    visits, add/mult and skills replay, at most 2 distinct fitting tries per question, night 2 from the night-1 model.
    1. Parts kept, as in job 7 (fresh add/mult reach@32 >= 50% after each night, skills harm <= 2 against N').
    2. Search check (the change must do its job): multi-step records in night 1 at least 3x job 7's (>= 75 on s100,
       >= 90 on s101). If it fails on either parent, more tries do not reach these answers from N', and the next step
       is bridging stones (back here).
    3. Climb, the same mark as job 7: multi-step first try W(night 2) - N' >= +10 with the paired 95% interval above
       0, on both parents. Affine stays in the pool of 154 (PC' says it is barely learnable; reported per kind).
    4. Proved wrong: the search check passes and the multi-step upper end is below +3 on both parents. Finds then do
       not turn into first answers, and the climb claim retires on B2 for this sleep.
    5. Anything else comes back here. Reported: per kind first try, reach@4, reach@32, records and questions with a
       find, per night; samples drawn per night; practised check and skills harm per night.
    If the climb passes, the real C2b uses replay plus this search. If it retires, the real C2b carries only the
    near-copy claim.
  - **Memory sleep, ruled 10-07 (fast-sleep thread, PR #48; RESULTS in the project folder under fast-sleep/).** Shown on
    a 2-parent DEV screen, with s101 untuned: a notebook of the night's W records plus 512 warm add/mult programs, read
    by top-16 cosine votes on the op and slot heads with no weight change, matches the fine-tune's W first-try gain
    (0.95x / 1.04x) at 25-32x fewer FLOPs. Skills harm is 0, and R/H notebooks gain nothing. Per kind it is the same
    near-copy gain (square, last_digit); the multi-step kinds stay near 0 for every method. Decided:
    1. Mac job 7 runs unchanged. It asks whether parts kept in the weights let the loop combine them, and a
       nearest-neighbour notebook cannot compose by design, so it is not mixed in.
    2. The real C2b keeps W (weight sleep) as the arm its marks are written for, and adds memory as a reported second arm
       M: the setting frozen by the fast-sleep 6-seed confirm, the same old notes, an R-notebook placebo, the same marks
       and the stricter label. M can carry the near-copy claim. Only a sleep that lifts multi-step first try can carry
       the climb claim.
    3. M's practised score is recall, not kept parts: its old notes are warm-split add/mult programs over the same 35
       parameter values the practised check asks. It is reported under that name.
    4. For the creative loop's nightly design: if the confirm passes and job 7's climb passes with weights, memory does
       nightly recall and weight sleep does the climbing, and how often weight sleep runs is set by the climb results,
       not by FLOPs. If job 7's climb retires, memory alone is the loop's nightly sleep for near-copy kinds.
    5. Proved wrong: parts kept and W'(night 2) - N' on the multi-step kinds with its upper end below +3 on both
       parents. The parts were there and the loop still did not combine them: explanation (b), and the climb claim
       retires on B2.
    6. Anything else (a split between parents, or a result between the marks) comes back here.
    If the climb passes, the real C2b runs on B2's six confirm parents with the replay and the stricter label. If the
    climb retires, the real C2b runs on the six parents only for the near-copy claim (sleeping on checked tries turns
    lucky finds into first answers on new kinds that need one fixed program), and combining parts moves to Floor B's
    next step (C7, the pieces library). Its test stays sealed either way until then.
- **C2b, the creative test.** On held-out rule kinds, with no answer keys: 32 tries per question, keep tries that fit
  every example, sleep. Arms N, W, R (fits no example check, matched count), H (each try relabelled with the rule it
  actually computes on the examples). Comparison nets: a same-size plain transformer and a fresh net, each given k
  labelled examples of the new kinds, k in {0, 8, 32, 128}.
  - Pass: first try on fresh questions of the held-out kinds W - N >= +15 and W - R >= +10 (intervals above 0), with
    reach@4 and practised skills each within 2 points of N; report "examples to learn": the k at which the plain net
    matches W. The claim is about sleep only; a claim that our thinker's design beats a transformer would need one
    with the same executor and copy talker.
  - Proved wrong: W - R upper end below +3.
  - No key leak: W, R and H records are answered by the try's own output, never the key (the build tests this by
    corrupting every key); the key-agreement check of C2a is a measurement only and never filters records; sleep-pool
    questions and test questions share no (rule, examples, query) triple. H relabels the shown examples with what the
    try computes, so it carries no key either.
- **Counting (from C1's pilot 3):** luck and reach@4 count sampled tries in sampling order with repeats included;
  counts over distinct programs measure variety only.
- **Owner:** the same Sonnet build thread (C2a and the arms are built and smoke-tested on synthetic kinds; the real
  rule rows and the held-out sealing are its next step, started 10-06 alongside C1's last DEV check because C1's
  plumbing works: PC sleep taught first answers on B2).

## 8. How it fits the other work

- **Plan B test B1** (teacher-made variety for a 10.8M B2) runs first. C1 does not need its data. If B1 passes, C2 onward
  use the bigger student, and the 1.2B also writes C6's stepping stones.
- **The B2 6-seed confirm** gates C1 and C2 (D7); its leak check (loops:0) is now a creative lesion too.
- The swarm result (members all miss the same questions) says more copies of one model are not a variety source; D4 and
  C3b make variety inside one model.
- The ultracode plan route is the same idea as D1 inside the sandwich; the two lines stay separate.

## 9. Risks, and what would change the plan

- **C1 signal or C2 cold start** (the DEV gate fails): fix the warm-up (C1), or stepping stones in C6's form (C2)
  before retrying.
- **Representability.** A held-out failure can mean the language can't write the answer, the model hasn't learned the
  pieces, or it can't combine them. Every test classifies its failures into those three before calling it a creativity
  failure.
- **Sameness** (the DEV gate fails): C3b before retrying.
- **Small model, short programs:** B2's 7 write steps may be too few for later floors; growing them is its own change.
- **Language growth vs "no new hand-written rules"** (Ben, 09-26): C2, C5 and C6 need input roles, plan ops, string and
  date ops. Default: a small general base set (like a calculator for text), with the pieces library growing the rest.
  Ben can overrule before C2 is sealed.
- **Transfer may not come.** The evidence leans against automatic transfer between families; C6 and C10 are where it
  shows.
- **Minecraft is far.** Small-model Minecraft is a research gamble; the crafting world and Craftax are the honest near
  targets.
- **Outside opinion:** GPT-6 Pro's reply (prompt in `reviews/gpt6pro-creative-roadmap-2026-10-06.md`) was checked
  against the code and folded in; see section 10.

## 10. Review log

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
- **Build thread findings (PR #44, 10-06, CPU, no model):** a value-blind rule follower reaches 48.8% at 32 tries, so
  the C1 cold-start gate became a signal gate and reach@32 became report-only; branching keeps about 7 result-changing
  programs even near temperature 0, so the sameness gate now counts distinct rule-following programs; targets average
  1.9 solutions, kept as is (preferring many-solution targets would raise the floors), with correct-solution variety
  report-only and read on X; loops:0 is trivially zero for this checker, so the donor lesion carries C1; C2a needs no
  change to B2 (the query slot is re-bound per example).
- **GPT-6 Pro (10-06, checked against the code):** taken: discovery and learning scored separately and a budget in the
  definition; luck called hit rate with denominators; a first-try mark F1 in C1 (sleep has improved search more than
  first answers); the aim check (real target vs twin target vs a value-blind rule follower) before sleep; a DEV-only
  pilot on the existing two B2 parents; representability checked before sealing; program-first practice items with the
  1.2B only wording them; C3 at 5 nights with old-skill replay; C3b one variety source at a time; C7 against random
  pieces of matched size and a no-library reference at equal checker calls; "can't" only with a certificate; a written
  definition of "beats Minecraft" before C11; lessons 1 and 2 narrowed. Already true in the code: its worry about
  fractional intermediates (B2's DIV is valid only when exact, and the puzzle solver uses the same rule). Not taken: a
  known-answer replay arm in C1 (R already holds the rules constant, and blurt-3 ran that control); its pass mark of
  +10 reach@30 for the aim check, because blurt-3 started near chance and sleep created the aim, so the check is
  reported rather than gated; its milestone table past C2, which stays provisional until C2 reads out.
- **Ben (9:24 PM ET 10-05), answering the ideas card:** gift and plan ideas don't need a creative model; creativity is
  only for when the model runs into trouble. The ideas side track is removed, wall 3 is now about open worlds, and C4
  only ranks tries before a real check.
- **DEV pilot on B2 s100 (10-06, build thread):** both DEV gates failed because a two-number warm-up does not teach
  three-number programs (rule-following tries 0.2% raw, 0.4% warmed). Decided here: a mixed two- and three-number
  warm-up on unsealed number sets, sized as the smallest that passes the signal gate; temperature chosen among values
  that pass the sameness gate, widening the grid at an edge; learning-rate grid 3e-4 to 1e-2; PC gate kept at +10.
- **Warm-up papers (Sonnet papers thread, `/mnt/project-files/papers/warmup-blocker-papers.md`, abstracts only):** they
  support the mixed two- and three-number warm-up (Lee 2025; length transfer needs the longer task in the mix,
  2506.09251) and give the fallback order above (more visits, then DreamCoder/DeepCoder-style dreams). CodeIt/SOAR
  hindsight is already arm H and cannot serve as the warm-up for C1 (see the warm-up bullet).
- **Second DEV pilot (10-06, both parents):** the mixed warm-up passed on signal, aim and sameness; the old 50%
  rules-share criterion failed it and was the wrong measure, so the DEV gates were rewritten (signal, aim, sameness)
  and the share is now reported only. This gate change was made after seeing DEV numbers and is a feasibility check,
  not a claim; T1 and T1b stayed sealed throughout. Separately, L1, L2, G0 and the PC gate moved from fixed points to
  ratios with an absolute guard, because +10 points would have failed blurt-3 and blurt-3r, the only replicated
  creative result we have. Warm-up rung chosen: 1,500 with the 4-visit cap.
- **Used-number mask (10-06, ultracode thread, PR #45):** adopted for C1's tries as disclosed test scaffolding (Ben's
  09-26 rule on stand-ins), with the floors recomputed under the same rules and F1 scored without it. Its own marks,
  written before the s101 numbers, pass on both parents (masked luck 2.8x and 2.9x plain; own target 2.9x and 3.2x the
  twin's; 10.5 and 10.6 legal programs). Pilot 2, already running on the Mac with the plain sampler, finishes as a
  labelled comparison and is never pooled with masked arms.
- **PC gate on pilot 2 (10-06):** PC missed on both parents with the plain sampler (1.15x and 1.20x against 1.6x).
  Decided: judge the gate on the masked run (the C1 sampler) and keep the mark; give the PC arm a DEV dose grid
  (lr 3e-4 or 1e-3; visits 4, 8, 16) with a 2-point skills limit; report for every setting the plain sampler's legal
  share and hit rate among legal tries, and the sleep loss split into puzzle rows and replay rows (pilot 2's single
  loss mixes them, so it cannot say whether PC's records were learned); stop before sealing if masked PC still misses.
- **Pilot 3, masked (10-06):** PC missed again on distinct-try luck, at every dose. Found here: luck counted each
  distinct program once, which caps it at solutions over distinct tries (about 1.4x N at the parent's variety), so the
  1.6x mark could not be met; the marks had been scaled from blurt-3, which counted right samples with repeats. The
  sleep itself worked (s101: puzzle-record loss 4.86 to 1.96, plain first try +6.3 points, masked first try +10.9,
  plain luck over samples 1.66x). Decided: count luck over samples on the plain sampler for every mark, keep the mask
  for sleep pools and variety, judge the PC gate on pilot 3's logged plain sample luck at the frozen settings, retire
  C1 if s100 misses. C1's plumbing works, so C2's CPU build and sealing start now and use the same counting.
- **C1 retired (10-06):** s100 missed the PC gate on the corrected count (1.29x, +2.8 at its frozen setting) while
  s101 passed (1.66x), so C1 stops at its DEV gate with T1 and T1b never read. A better s100 setting existed in the
  grid and was not taken (fourth post-hoc change). C2 continues as the main test.
- **C2 cold start (10-06):** the DEV gate stopped C2 at cold start (reach@32 3.9% and 6.3% against a 4.8% floor).
  Per the pre-set rule, stepping stones come next (section 7): easier variants of the held-out kinds made by code,
  against matched add/mult practice, with full-difficulty solver programs as a report-only ceiling. C2 retires only if
  the stepping-stone parent also misses the gate.
- **C2 stepping stones (10-07):** SS passed the cold-start gate on both parents (25.4% and 19.5% against 14.5%;
  placebo 4.3% and 5.1%), but only at the hottest temperatures and mostly on square, whose program is the first step
  of a stepping stone; first answers stayed near 0. Decided: run C2b's DEV pilot from the SS parent with a PC
  feasibility gate, a report-only second night to see whether the loop climbs to the multi-step kinds, and a
  pre-set "near-copy kinds only" label for a pass carried by square and last_digit.
- **C2b DEV pilot (10-07):** pooled marks met on both parents (W - N +34.8 / +27.0, W - R the same, R and H at 0), but
  the gain is square and last_digit only, night 2 did not climb, and the practised-kind check had already fallen from
  61% / 57% to 11% after the stepping-stone sleep. Ruled "PASS, near-copy kinds only" (the 2-point band was narrower
  than one question; replaced by a pooled multi-step interval, the fifth post-hoc change). Decided: Mac job 7 replays
  the add/mult rows in every sleep, with a PC' feasibility gate and a night-2 climb mark on the multi-step kinds.
