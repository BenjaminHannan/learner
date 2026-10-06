# Creative model roadmap (2026-10-06)

Ask (Ben, 7:56 PM ET 10-05): a thread dedicated to figuring out a creative model, "the hardest problem", with a really
good roadmap. It must fit Plan B (Ben's pick, 7:44 PM ET 10-05): our own thinker grows to most of the model, the
reader and talker are tiny, and the 1.2B is only a teacher during training and never ships.

Labels: **shown** = measured in this repo or in a cited paper; **suggested** = reasoned; **untested** = a plan or guess.
The old creative runs used a frozen MiniCPM5-1B with a LoRA "sleep" and are cited as that model only. No creative
experiment has run on the village model or the small card experiments, and none is planned here. Times are ET.

Inputs: creative history digest (`design/creative-roadmap-notes/history-digest.md`), 40 checked papers
(`design/creative-roadmap-notes/papers.md`, also in the project folder under papers/), probe P0 on B2 tonight (`design/creative-roadmap-notes/p0/`),
creative prototype v2 (`origin/claude/project-thread-1w6411:design/next-parts/creative-prototype.md`), Plan B
(`origin/claude/project-thread-9ye9md:design/thinker-first-split-2026-10-05.md`), B2 (`origin/claude/custom-reader-talker-4x309r:custom_io/`).

## 0. For Ben

Your definition: when the thinker is stuck, a creative part tries lots of different things, a checker keeps the ones
that work, and the model learns from them in sleep so next time it doesn't need luck.

- **It has worked once, in one place.** On number puzzles with a borrowed 1B, sleeping on its checked lucky hits about
  doubled its luck on fresh puzzles, and it replicated (63 to 131, then 59 to 138.5 right tries out of about 2,000).
- **Three walls make it the hardest problem.** (1) On a brand-new kind of task there are no lucky hits, and no hit
  means nothing to learn from. Tonight our own thinker B2 found 0 answers in 32 tries on 3 of its 4 never-seen task
  kinds. (2) Tries that are all the same: B2's 32 tries contain only 2 to 4 different programs, and sleeping on the
  same answers over and over shrank the old model's reach from 27-29 puzzles to 3-4. (3) No checker for fuzzy things
  like ideas: the best judge we trained picked a good idea first 3 times in 10.
- **The plan climbs four floors**, one tested step at a time: Search (try, check, sleep inside our own thinker), Invent
  (first hits on never-seen kinds: stepping stones, a library of reusable pieces, beating the teacher), Choose (pick
  its own practice, say "can't" and ask you), Worlds (a crafting world, then a small Minecraft-like game, then
  Minecraft).
- **First step (C1):** teach B2 to sleep on its own checked tries on make-the-target puzzles, where the checker needs no
  answer key. It must beat a look-alike placebo by a fixed margin.

## 1. What "creative" means here, and the scoreboard

**Definition (operational).** The model finds checked solutions to problems it could not solve on its first try and
that nobody gave it the answer to, then learns from them so it needs fewer tries next time.

Every creative test reports the same scoreboard, on fresh problems the model never practised:

| Score | What it counts | Why |
|---|---|---|
| Luck | share of 32 tries that pass the checker | the old runs' main measure (blurt-3) |
| Reach | problems with at least one passing try in 32 (pass@32) | catches variety collapse that luck hides |
| First try | greedy solves | what the user sees; it moves least (blurt-2) |
| Variety | distinct working programs per problem, and distinct behaviours among the 32 tries | variety is the fuel |
| Frontier | problems no teacher, solver or training answer covered, solved | the one job only creativity can do (blurt-5s) |
| Transfer | task kinds never practised | the point of being creative |
| Harm | practised skills lost after sleep | sleep cost 61 and 98 of 200 general answers once (dl-5) |

Later, for fuzzy work, add quality times novelty (CreativeBench, 2603.11863): junk that is new and copies that are
good both score zero.

## 2. What we already know

### Our runs (shown; frozen MiniCPM5-1B + LoRA sleep, number puzzles, exact code checker, marks fixed first)

| Run | Result | Verdict |
|---|---|---|
| blurt-3 / blurt-3r | Lucky tries 63 to 126/136 (C 85/87); then 59 to 129/148 (C 59/58). Puzzles reached 27 to 38/38 (C 3/4); 29 to 40/43 (C 4/3). C = sleep on its own known answers, same count | PASS, replicated |
| blurt-2 / 2p / 2b | First-try solves on fresh puzzles rose a little: 6/127 to 15-19 (CPU) and 11-13 (GPU) vs 5-6 for C; wrong-guess placebo 9.5 vs 13.5 | FAIL on the size of the gain |
| blurt-4 | Hindsight relabels ("made 22" becomes a "make 22" puzzle) lowered luck (140 vs 221); wrong relabels did the same (140); but both relabel arms reached more puzzles (41-46 vs 32-35) | Proved wrong on luck; varied targets widen reach |
| blurt-5s | Puzzles solved in 30 tries: own hits 112/108/110, exact-solver answers on the same puzzles 123/113/117, known answers repeated 14/12/11, before 77 (of 184) | Proved wrong: own hits are not special |
| brd-9 | Three nights of own hits: 96 to 139/135/131 of 240; near carry-over to new targets 13 to 45/32/32 of 80; but nights did not compound (brd-8) | PASS; harm not measured |
| ask-24ab | The 1B cannot tell solvable from impossible puzzles (50% balanced accuracy) | Proved wrong: "can't" must come from code |
| ideas (DEV) | 44 of 300 tries good; best trained judge picks a good one first 3/10 (AUC 0.80); self-judge 2/10 | Judge is the bottleneck |

### Probe P0 on our own thinker B2, tonight (shown; CPU, no training, scored with the answer key)

- Held-out task kinds (clock_date, op_define, string_transform, unit_convert): greedy 0.6% / 1.2%; best pass@32 1.9% and
  5.6% (seeds 100 and 101). Every hit but one is unit_convert. **Cold start** by the line fixed before the probe.
- **Narrow variety:** 2.1 to 4.5 distinct real programs in 32 tries.
- On rows it gets wrong in new wordings, 32 tries rescue 5-25%, but guessing a random prompt word 32 times scores
  15-25% on the same rows (post-hoc): pointer re-guesses, not new programs.
- Two of the four new kinds have answers B2's program language cannot write at all (dates, string edits).
- B2 has no key-free checker, no example slot, no memory, and no way to resume training from a checkpoint yet.

### Lessons (labelled)

1. Sleeping on checked hits raises luck and reach within a family, and keeps variety; sleeping on repeated known answers
   collapses it (shown, 1B, one family).
2. Where a solver or teacher can answer, its answers teach as well as creative hits (shown once, blurt-5s; answer
   length is a confound). So creativity earns its keep only where no solver or teacher can answer.
3. First-try gains are small and unstable; luck and reach move more (shown).
4. Learned judges are weak at small size (shown for ideas; suggested generally by "Mind the Gap", 2412.02674).
5. Sleep can cost general skill, so every step needs a harm mark (shown, dl-5).

### Papers (the 10 that shape this plan; full list in the papers file)

- **The loop is real.** SOAR (2507.14172): sample programs, relabel, fine-tune took a 7B from 14.25% to 36.25% on ARC,
  with a "greedy-diverse" rule for choosing what to sleep on (shown). CodeIt (2402.04858), DreamCoder (2006.08381).
- **Small transformers can climb.** Lee et al. 2025 (2502.01612): keep only correct self-made answers to slightly harder
  problems each round; 10-digit to 100-digit addition (shown).
- **Training only on winners kills variety.** Negative reinforcement (2506.01347) keeps pass@k up; positive-only
  lowers it (shown, 7-8B). Fixes: learn from losers, upweight rare correct answers (2506.02355), invent sibling tasks
  (2508.14029), add new data to old instead of replacing it (2404.01413).
- **Sleep cannot create a try with zero chance** (sharpening theory, 2412.01951; Yue 2025). New tasks or stepping
  stones are needed first.
- **Libraries can be fake.** Reuse of learned functions was "extremely infrequent" in two systems (2410.20274): log
  reuse.
- **Games.** Crafter is solved by modest world models (EMERALD, 2507.04075: all 22 achievements within 10M steps);
  Craftax-Classic is above human level at 1M steps (2502.01591); full Craftax is unsolved (best 18.3% of max reward,
  repo leaderboard); Dreamer 4 (2509.24527) gets Minecraft diamonds from pixels in 0.7% of episodes with 2B weights.
- **Tiny reasoners need care.** TRM (7M) scores on ARC come with 1,000 augmentations, a vote and a task ID; with the ID
  blanked it drops to 0 (2512.11847, shown).

## 3. Why it is the hardest problem: four walls

1. **Cold start.** No hit, no signal (P0: 0 of 32 on 3 of 4 new kinds).
2. **Sameness.** Few distinct tries (P0: 2-4 programs in 32), and training on winners narrows them further.
3. **No checker.** Ideas, open-world plans and advice have no exact check, and small judges are weak.
4. **The language can't say it.** A try cannot be right if the program language cannot express the answer (P0: dates
   and string edits).

## 4. Design decisions

- **D1. Creativity lives in our thinker, as program search.** The thinker writes many candidate programs (plans); the
  exact executor or a simulator runs them; the checker keeps the ones that work. This fits Plan B (the thinker is most
  of the model), Ben's "tools like a calculator", and his 09-22 wish that one model plays dreamer and worker (the
  filter here is code, like the calculator). The free hook is sampling B2's heads (`ledger.py:227`, `269`; shown in
  P0).
- **D2. The filter is code until the ladder reaches fuzzy problems.** Checkers are part of the task (the puzzle's rule,
  the examples, the simulator), never a learned judge inside the small model (lesson 4).
- **D3. Teacher where it can answer, creativity where it can't.** The 1.2B writes problems, stepping stones and fading
  hints during training only (lesson 2). It never ships and never judges inside the shipped model. Ben's 09-26 rule
  holds: nothing written or judged by Claude goes into training.
- **D4. Sleep keeps variety by rule.** Keep old data (replay), pick a diverse set of hits, upweight rare correct ones,
  push down some wrong ones. Each of these is tested as its own change (C2).
- **D5. Climb a ladder of checkers:** goal check (make the target) -> example check (the rule fits the given examples)
  -> simulator (crafting world, game) -> partial checks -> people.
- **D6. Honesty rules for every step:** one change, marks sealed before running, a placebo arm, a harm mark, fresh test
  sets, 6 paired seeds before any claim (the project's noise rule), and the result that proves it wrong.

## 5. The roadmap

Four floors. A floor's later steps wait for its earlier ones; each step's single change, pass mark and kill result
are fixed below (marks for C3 onward are provisional and get sealed in their own spec before running).

### Floor A: Search (try many, keep what checks, learn)

| Step | One change | Pass (provisional after C1) | Proves it wrong |
|---|---|---|---|
| **C0** (done 10-06) | Scoreboard on B2, no training | Read: cold start on new kinds, narrow variety (shown) | n/a |
| **C1** | B2 sleeps on its own checked tries (make-the-target puzzles, goal checker) | Luck: W - N >= +10, W - R placebo >= +8; aims at its own target; no harm (section 6) | Solver control learns, but W - R stays under +5 |
| **C2** | Sleep that keeps variety: diverse picks + rare-correct upweight + some wrong tries pushed down, over 3 nights, against C1's plain sleep | Reach after night 3 >= plain + 5 points; distinct working programs per puzzle do not fall night to night; luck within 2 of plain | Reach no better than plain sleep |
| **C2b** (only if C1 or C2 hits the sameness wall) | A variety source: a small "style code" the sampler is conditioned on, or mutating earlier winning programs | Distinct programs in 32 tries at least double, at equal luck | Variety up but reach flat |

### Floor B: Invent (first hits on kinds it has never seen)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C3** | Rules that can be re-run: programs become functions of the inputs, so a try is checked on the prompt's own examples with no answer key. Target: induction families where B2 trails the step-writing transformer (fewshot_number_rule -9, rule_apply -6) | Beats B2 and the step-writing transformer by >= 5 on those families; key-free check agrees with the key on >= 99% of accepted tries | Sleeping on example-fitting rules gains < 2 |
| **C4** | Stepping stones: the generator or the 1.2B writes easier variants of a new kind; the loop climbs one step at a time (Lee 2025, Ben's "reframing") | Held-out kinds: reach@32 from P0's 2-6% to >= 25%, first try >= 10% | Reach stays < 10% |
| **C5** | Pieces library: repeated sub-programs become new named operations the thinker can call (Stitch, DreamCoder) | New-kind reach >= C4 + 5; >= 30% of new solutions use a learned piece | Reuse < 5% (a single-use library) |
| **C6** | Beyond the teacher: problems with a checker that the 1.2B gets wrong (more numbers, longer rules) | Solves >= 20% of the teacher's failures within 32 tries | < 5% |

### Floor C: Choose (own practice, and knowing when to ask)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C7** | The model picks its practice by learning progress (problems it solves sometimes, not always); "can't" comes from exhaustive search, then it asks Ben | Reach grows >= 1.3x faster than random practice at equal compute; "can't" right >= 95% of the time | No faster than random practice |

### Floor D: Worlds (from puzzles to Minecraft)

| Step | One change | Pass (provisional) | Proves it wrong |
|---|---|---|---|
| **C8** | A text crafting world with a tech tree (wood, planks, table, pickaxe, stone, ...); the thinker writes plans, the simulator is the checker; sleep on plans that reached new items | Reaches items it never saw a plan for more often than the no-sleep thinker and random plans, every seed | No gain over random plans |
| **C9** | Craftax-Classic (fast symbolic Crafter), then Crafter pixels; a small world model lets the thinker "dream" tries that the real game then checks (Ben's 09-18: dreams count only if a simulator checks them) | Beats a same-size plain agent at equal steps; stretch: human-level reward (65%), all 22 achievements | Below the same-size plain agent |
| **C10** | Minecraft (screen in, keyboard and mouse out) | Honest bar today: Dreamer 4, diamonds in 0.7% of episodes at 2B weights | Research gamble; no fixed kill yet |

**Side track, parked: ideas with no checker** (gifts, plans, messages). It waits until C7. The judge would learn from
real outcomes (Ben's own thumbs up or down), the 1.2B helps only in training, and every idea is shown labelled as a
guess.

## 6. C1 spec (the next step; seal before any GPU stage)

Built on creative prototype v2 (five Opus review passes, 10-03), moved from the old 9M core to B2.

- **Parents:** B2_s100 and B2_s101 (`/mnt/project-files/custom-io/checkpoints/29-b2-screen/`). If the B2 6-seed confirm
  lands first, use two of its seeds instead and say so.
- **Puzzles:** "use A, B and C once each, adding or subtracting, to make T" in B2's prompt style (fits its 208-character
  input), numbers 2..40, solvable, no 2-number shortcut, target not a given number. Twin targets on every test puzzle
  (same numbers, two targets with different sign patterns), so aiming can be told apart from rule-following. Splits by
  number set: practice 1,024; DEV 128; test T1 256 (once); replication T1b 256. Sealed by hash before any GPU stage.
- **Shared warm-up (identical for every arm):** B2 learns the puzzle format on 2-number puzzles with solver programs.
  No arm sees a solved 3-number puzzle before the loop. Cold-start gate on DEV after warm-up: an accepted try within 32
  on >= 10% of puzzles; if it fails, stop with T1 sealed and go to C2b.
- **Tries:** 32 per practice puzzle, by sampling the op and operand-pointer heads at a DEV-chosen temperature (P0's
  sampler, `design/creative-roadmap-notes/p0/p0_probe.py`).
- **Checker (no answer key):** two independently written checkers; accept only if the program uses each given number
  exactly once, never the target or a constant, chains each result into a later step, and ends on the target. Planted
  bad programs of every kind must be rejected before any GPU stage.
- **Arms (the one change: what the model sleeps on):**
  - N: no sleep.
  - W: its own accepted tries (at most 2 distinct programs per puzzle).
  - R placebo: its own rule-following tries chosen without looking at the value, same count.
  - PC positive control: solver programs for the same puzzles, same count.
  - Every sleep: resume from the parent, the same updates, and replay of the 200k skills rows in every batch.
- **Seeds:** 2 parents x 3 sleep seeds = 6 per arm (noise rule).
- **Marks (means over 6 seeds; luck = share of 32 tries accepted on T1):**
  - L1: W - N >= +10 points, every W seed above its parent.
  - L2: W - R >= +8, 95% interval above 0.
  - G0 aim: W - R on "hits its own target minus hits its twin's target" >= +5, interval above 0.
  - G1 reach: W not more than 2 points below N.
  - G3 harm: skills pooled-5 drops by at most 2 points in every seed.
  - PC gate: PC - N >= +10 (the model can learn these puzzles at all).
  - **Proved wrong:** the PC gate passes, yet W - R has an interval upper end below +5 on luck and below +3 on aim.
  - Reported, not judged: distinct programs per puzzle, first-try twin pairs, uniform and rules-only floors.
- **Build (CPU first):** puzzle generator, twin builder, both checkers, sleep plumbing B2 lacks today (resume from a
  checkpoint, targets from kept tries, skills replay). Put it in a new `creative/` folder that imports `custom_io`
  without editing it, because the custom reader/talker thread is building the Plan B students there.
- **Cost (untested estimate):** B2 trains at about 8 updates a second on a 5090 (shown, 24,000 updates in 49 min).
  Eighteen sleeps of a few thousand updates each, plus sampling, should take a few hours on the 5070 Ti at $0.
- **Owner:** a Sonnet implementation thread (project rule); this thread keeps the design and scores the result.

## 7. How it fits the other work

- **Plan B test B1** (teacher-made variety for a 10.8M B2) runs first on the 5070 Ti. C1 does not need its data and can
  run on the 3.3M checkpoints in parallel on whatever machine is free (own machines first).
- If B1 passes, C3 onward use the bigger student, and the 1.2B also writes the stepping stones for C4.
- The ultracode thread's plan route (thinker plans, exact calculator computes) is the same idea as D1 inside the
  sandwich; its example-derived plans can seed C4.
- The swarm result (members all miss the same questions) says more copies of one model are not a variety source; C2b
  makes variety inside one model.

## 8. Risks, and what would change the plan

- **C1 cold start** (the gate fails): go to C2b before C1 is retried.
- **Small model, short programs:** B2's 7 write steps may be too few for later floors; growing them is its own change.
- **Language growth vs "no new hand-written rules"** (Ben, 09-26): C3 and C4 need ops for strings, dates and rules.
  Default: a small general base set (like a calculator for text), with the pieces library growing the rest. Ben can
  overrule before C3 is sealed.
- **Transfer may not come.** The evidence leans against automatic transfer from one family to another; C4 and C8 are
  where that shows.
- **Minecraft is far.** The best pixel result is 0.7% diamonds with 2B weights; small-model Minecraft is a research
  gamble, and the crafting world and Craftax are the honest near targets.
- **Outside opinion:** a GPT-6 Pro prompt is in `reviews/gpt6pro-creative-roadmap-2026-10-06.md`; its reply gets
  checked against the code before anything changes here.
