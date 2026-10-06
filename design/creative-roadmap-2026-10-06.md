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
  programs, keeps the ones that reproduce every example (no answer key needed), and sleeps on them. Before it, a cheap
  machinery check (C1) on make-the-target puzzles. The code for both is built (PR #44). A small trial on the two
  existing B2 copies can run now; the sealed tests wait for B2's 6-run confirm. Every sleep test now scores better
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
| **C1** machinery check | B2 sleeps on its own checked tries for make-the-target puzzles (+ - x /); claim capped at "the loop works on B2", since a solver exists. Hindsight arm included | Section 6 | Section 6 |
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
- **Shared warm-up:** every arm starts from the same warmed parent: B2 learns the format on 2-number puzzles with solver
  programs. N is this warmed parent. Warm-up harm against the original B2 is reported.
- **Gates on DEV after warm-up:** signal: at least half of the tries follow the rules, and the warmed parent has an
  accepted try on at least 100 distinct practice puzzles (rules alone reach about half the puzzles at 32 tries, so a
  pass@32 cold-start gate would test nothing here); sameness: >= 4 distinct rule-following programs per puzzle on
  average, by canonical program key (forcing the top 8 first steps keeps about 7 result-changing programs even near
  temperature 0, so that count is reported, not gated). A failed gate stops C1 with T1 sealed (C3b first for sameness;
  fix the warm-up for signal).
- **Aim check on DEV (no training; added from GPT-6 Pro's reply):** at the same 32 tries and checker, compare the warmed
  parent's tries for the real target, its tries for the twin target scored against the real target, and the value-blind
  rule follower; luck and reach@4. Reported, not a gate: in blurt-3 luck started near chance and sleep created the aim.
  If the rule follower matches the parent, search is still random before sleep, and G0 decides whether sleep taught
  aim. The same check is repeated on W after sleep.
- **Tries:** 32 per practice puzzle from the shared sampler: sample op and operand pointers at a DEV-chosen temperature
  (P0's sampler), drop duplicates (commutative order merged) before running and top up, branch over the top 8 first
  steps. Variety is reported with and without branching, so the sampler's own variety stays visible.
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
  - F1 first try (added from GPT-6 Pro's reply): greedy solves on T1, W - N >= +5 and W - R >= +5, intervals above 0.
    It decides whether a PASS also turned search into first answers.
  - Lesion: tries sampled from a donor puzzle's prompt (its twin) and judged on the recipient's target must not score
    above the rules-only floor; otherwise the run is void. (loops:0 writes no steps, so its luck is 0 by construction;
    reported, not a test.)
  - H question (secondary): reach@32 H - W >= +5 with interval above 0, and H - H' above 0.
  - PC gate: PC - N >= +10.
- **Ordered verdicts:** void (checkers disagree on a T1 try, unresolved above 1%, or a lesion fails) -> gate stop ->
  placebo too close (over half of R's records are accepted tries) -> PASS (L1, L2, G0, G1, G2, G3), named "PASS with
  first answers" when F1 also holds and "PASS, search only" when it does not -> rules only (L1 holds, G0 fails) -> gain with harm (G3 fails) -> **proved wrong** (the PC gate passes, yet W - R has an upper end
  below +5 on luck and below +3 on aim) -> not shown.
- **Before sealing:** measure the spread between parents on DEV and run a power simulation; if L2 or G0 has under 80%
  power at a true +15 luck or +8 aim, add parents.
- **Build (done, CPU-tested, PR #44):** puzzle generator, twin builder, both checkers (23 planted bad programs rejected,
  10,000 fuzzed tries without a split), the shared sampler, the gates, the arms and the sleep plumbing B2 lacks (resume
  from a checkpoint, forced slot-id targets, skills replay, visit cap), in `creative/`, which imports `custom_io`
  without editing it. Not built yet: the warm-up, the power simulation and the run loop.
- **Cost (untested estimate):** B2 trains at about 8 updates a second on a 5090 (shown: 24,000 updates in 49 minutes).
  36 short sleeps plus sampling should take a few hours on one of Ben's machines, $0.
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
- **C2b, the creative test.** On held-out rule kinds, with no answer keys: 32 tries per question, keep tries that fit
  every example, sleep. Arms N, W, R (fits no example check, matched count), H (each try relabelled with the rule it
  actually computes on the examples). Comparison nets: a same-size plain transformer and a fresh net, each given k
  labelled examples of the new kinds, k in {0, 8, 32, 128}.
  - Pass: first try on fresh questions of the held-out kinds W - N >= +15 and W - R >= +10 (intervals above 0), with
    reach@4 and practised skills each within 2 points of N; report "examples to learn": the k at which the plain net
    matches W. The claim is about sleep only; a claim that our thinker's design beats a transformer would need one
    with the same executor and copy talker.
  - Proved wrong: W - R upper end below +3.
- **Owner:** the same Sonnet build thread after C1 (C2a and the arms are built and smoke-tested on synthetic kinds;
  the real rule rows and the held-out sealing are its next step).

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
