# Whole-model roadmap: from today to Minecraft (2026-10-06)

Ask (Ben, 9:27 PM ET 10-05): "roadmap for the whole model. What progress was made today?"

> **Out of date (note added 1:15 PM ET 10-09 after the architecture audit, B03-6 to B03-11).** This 10-05 version is kept
> as history. The current plan is `whole-model-roadmap-2026-10-06.md`; the source of truth is
> `/mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md`. Read these lines as replaced:
> - Section 3, "rules every stage keeps": GLM, Luna and new 1.2B text are not allowed. Training text is only the existing
>   171,940 TEACH rows, code generators and FineWeb-Edu (rule of 10-08). (B03-10)
> - Section 2, thinker row: the calculator is an outside tool the model calls (T1SDR, shown at 3M on 6 seeds) and never
>   moves back inside (Ben, 10-07). The "70% of the model" figure was never counted. (B03-11)
> - Stage 4, more operations: a new operation lives either in the outside calculator, which may hold hand code, or in what
>   the model learns. No new hand-written rules inside the model (Ben, 2:45 PM ET 10-07). Not in run-1. (B03-6)
> - Stage 4b: the talker does not write calculator calls. A call writer reads the thinker, and the talker writes only the
>   final answer. (B03-9)
> - Stage 5, sleep: sleep the model schedules itself comes after shipping, not in run-1 or the growth runs. (B03-8)
> - Stages 8 and 10: no rented GPUs and no ladder of small one-change tests (Ben, 3:27 PM ET 10-08 and 10:43 AM ET 10-09).
>   The size ladder is gate G1, then B3's own ladder on the PC. (B03-7)

This revises two earlier pages rather than starting blank: "Premonition Roadmap Oct 3" (a one-day plan,
https://claude.ai/artifact/BkhCvfRLpBmrbWrJAWpUdc, republished at the same link) and "Ben's Model Ideas" (09-30,
https://claude.ai/artifact/FfiNaagpFy8RfQwywAkyu3, the list of parts and abilities Ben asked for). It folds in the
existing pieces instead of redoing them: the learning-blocker bench (PR #38), the custom reader/talker and B2 (PR #39),
Plan B and test B1 (PR #41), the waste audit (`/mnt/project-files/model-audit/`), the creative roadmap (PR #43, build
PR #44), the paused vision and audio designs (PRs #25, #26, #28), notebook (PR #20) and sleep replay (PR #19).

Labels: **shown** = measured in this repo, **suggested** = reasoned from results or papers, **untested** = a plan or a
guess. Every pass mark below that is not copied from a sealed spec is marked **proposed** and gets sealed in its own
spec, by the thread that runs it, before any run. Times are US Eastern (ET). Revised 9:50 PM ET 10-05 after the
coordinator's review (bench freeze made a question for Ben, early talker probe, named race tests, eyes as teacher only,
earlier Craftax probe, next-48-hours box).

## Next 48 hours (ET)

Tonight, Mon Oct 5 (already queued, nothing new needed):
- About 10:30 PM (our guess from its pace: 45,056 of 120,000 items at 9:22 PM): TEACH finishes writing on the PC, then
  its answering pass starts (no ETA yet).
- About 10:45 PM: CRDW (wide doors on the plan route) on Vast boxes E/G. Stacks if held >= 292.0 of 320, ahead 5 of 6.
- About 12:30 AM: T2 quiet notes (box F) and T1 learning-rate decay (E/G, behind CRDW).
- Mac queue 31 keeps running.

Tuesday Oct 6, in this order (no ETAs yet):
1. B2's 6-seed confirm on the PC (queue 33, 18 runs) once TEACH frees the memory; read against PASS-1/PASS-2.
2. Test B1 2-seed screen once TEACH lands.
3. C1 DEV pilot on B2 s100/s101 on whichever own machine is free (allowed now).
4. On CPU: the stage 4 program-language spec and the stage 4b talker-probe spec, so both are sealed before GPU time.
5. The bench recipe written up as the reference (Ben chose to park the bench).

Wednesday Oct 7 (if B2 passes): C1 on the 6 confirm parents; the Craftax-Classic probe can start (stage 12a).

## 0. For Ben

- **Where we are.** Two roads. The *test bench* (the frozen 1.2B with our ~9M thinker inside) found today's best recipe:
  the thinker writes a plan and an exact calculator does the sums (89.7% on new questions, 6 seeds). *Our own model*
  B2 (3.3M numbers, nothing borrowed) uses that same recipe and beat a same-size transformer 73.7% to 67.7% (2 seeds).
  Both roads arrived at the same recipe.
- **The goal shape (Plan B, your pick).** The thinker is most of the model. The reader and talker are small and only
  translate. The 1.2B is a teacher during training and never ships.
- **The ladder has four phases:**
  1. Prove our own brain: B2's 6-seed confirm, then test B1 (does a teacher give it breadth?).
  2. Make it learn like a person: few examples, notebook and sleep, creative mode when stuck, and an early test of
     plain-English talking.
  3. Grow and race: about 11M, then 30M, then 100M, each beating a same-size plain model; then a sealed race against
     same-size models, and later against 1-2B models.
  4. Senses and worlds: its own eyes, ears and hands; a tiny crafting world, then Craftax, then Crafter, then Minecraft.
- **The biggest unknown right now is breadth.** Every from-scratch model we have scores 0-4% on kinds of question it never
  practised (shown). B1 is the first test of the fix (teacher-made variety). If B1 fails, a bigger student is next.
- **The biggest risk to "beat 1-2B models" is talking.** A from-scratch talker that writes open English has never
  worked here: P0 showed B2's language cannot write dates or word edits, a 350M LM as reader and talker lost (66.1% vs
  92.6%) and a ~2M copy-and-gate talker on the bench lost on unseen kinds (13.6% vs 78.2%). So a cheap talker probe (stage 4b) runs early, in Phase 2, not
  only after growing to 100M.
- **Decided (Ben, 11:20 PM ET 10-05): park the 1.2B test bench** after tonight's three bench tests. No new bench tests
  unless they answer a question about our own model; its GPU time moves to the own-model road. Most bench lessons are
  already in B2 (plan + calculator, wide paths, decaying learning rate).

## 1. Progress today (Mon Oct 5, ET)

Wins (shown):
- 12:26 AM. A 3.2M character-level transformer trained from scratch matched the 1.2B sandwich on practised skills
  (75.7% over 4 seeds vs 74.6%). This set the bar for building our own reader and talker.
- 8:15 AM. Plan route confirmed on 6 seeds (CRDC): the thinker plans, an exact calculator computes. Fit 92.9%, held-out
  89.7%, against 85.5% / 81.3% for worked steps (SR2). Swapping in another question's plan drops chain answers to
  2-3 of 160, so the thinker decides them. Caveat: at matched practice the plan route is level with the LM writing its
  own steps (82.8 vs 85.8; 97.6 vs 98.8), not better.
- 10:42 AM. B2 (from scratch, 3,302,481 numbers: thinker writes programs, exact executor, copy talker) led the
  2-seed screen: 73.7% pooled vs 67.7% for the step-writing transformer and 54.4% for the plain one. A donor's notes
  drop it to 3.8%. Missed one pre-set leak check: with the thinker switched off it still scored 6.76% on seed 101
  (limit 5%).
- 8:15 PM. Ben's talker-calls-the-calculator design (CRT) works: 471/480 held chain over 3 seeds, level with the
  direct route (470). Missed one mark: a swapped note was copied only 79-84% of the time on 2 of 3 seeds (bar 90%).
- 9:10 PM. Wide doors (2048 instead of 32) confirmed on 6 seeds: held 274.8 vs 260.0 of 320 (fit 287.0 vs 273.5),
  ahead on 5 of 6. The gain is +15, about half the first 3 seeds' +26.

Ruled out (shown): merged Hearer+Reader (held 278.8 vs 287.0, ahead 2 of 6); per-round routers from Ben's
Chain-of-Experts paper (131.2 vs 132.5); two-hop pointer (76/160) and 2048 thinker reader (77/160) against 77; wide
attention heads (T3, 78 vs 77); design A (loses by 3 to the step-writer); the swarm (parked 7:09 PM: training together
was void, the picker was -0.6 on twisted questions). Speed-up T4: 22.7% faster, between its marks (pass 25%, wrong
under 10%).

Found (shown, waste audit 6:40 PM): the thinker's 8 notes are about 1,300x louder than words; only about 1.6M of the
thinker's 9M numbers ever train (the "8 experts" are one expert run twice); the main model's learning rate never
decays; the Reader squeezes 2,048 numbers to 32.

Decided (Ben): Plan B at 7:44 PM (our thinker stays and grows; the 1.2B only teaches; the layer map is cancelled).
Creativity only when the model gets stuck, 9:24 PM.

Built: GEN control data (200,000 questions); TEACH generation started on the PC at 8:43 PM (1.2B teacher); B1 marks
fixed (8:45 PM, `custom_io/PASS-MARKS.md` addendum 3); creative roadmap (PR #43) and C1/C2 code with CPU tests (PR #44);
T4 speed code (PR #42); the Mac session may now start PC and Mac jobs without asking Ben (8:05 PM).

Running at 9:30 PM ET: CRDW (wide doors on the plan route, about 10:45 PM) and T2 quiet notes (about 12:30 AM) on
Vast; T1 learning-rate decay after CRDW (about 12:30 AM); TEACH on the PC (45,056 of 120,000 items at 9:22 PM, then an answering pass);
B2's 6-seed confirm (18 runs) and baselines queued on the PC behind TEACH; Mac queue 31 running. Vast credit $7.10.

## 2. Where the model stands

| | Test bench (CRDC) | Our own model (B2) |
|---|---|---|
| Reader | frozen LFM2.5-1.2B (1,170,340,608 numbers) + a 2048->32 door | character reader, trained from scratch |
| Thinker | ~9M looped core (about 1.6M live) + a planner + exact calculator | looped controller writing up to 7 program steps + exact int64 executor (about 70% of the model; suggested, not counted per module yet) |
| Talker | the same frozen 1.2B, re-reading the question | copy talker (numbers, word pointers, letters) |
| Whole size | about 1.18B | 3.3M (S); 10.9M (M, built for B1) |
| Best score | 89.7% held-out skills (6 seeds) | 73.7% pooled-5 skills (2 seeds) |
| Ships under Plan B? | no (the 1.2B never ships) | yes, grown |

What both roads showed (shown): exact step values beat latent ones; a thinker that writes a plan for an exact tool
decides the answer (plan-swap and donor lesions); wide paths beat narrow ones; a decaying learning rate helps.

What our own model still lacks:
1. **Breadth.** 0-4% on held-out families for every from-scratch model (shown). B1 tests the fix.
2. **A program language for more than arithmetic.** B2 trails the step-writer where the rule must live in latent space
   (fewshot_number_rule -9, rule_apply -6), and its language cannot write dates or word edits (creative probe P0).
3. **Open English.** It reads and writes short curriculum prompts only; it does not chat.
4. **Few-example learning, memory and sleep** have not run on it. The notebook (PR #20), sleep (PR #19), reasoner
   (PR #23) and fair-scaling (PR #18) designs were all written around the frozen 1.2B as reader and talker, so each
   must be re-posed on our own model before it runs (shown, read from the designs). None of their ladders has a scored
   number yet.
5. **Senses and hands.** No eyes, ears or actions yet.

## 3. Rules every stage keeps

- One change at a time; pass mark, proved-wrong result and prediction written before the run.
- 6 or more paired seeds before any claim (noise rule, PR #29); 2-seed screens only decide whether to confirm.
- Lesions show the thinker decides: donor state, loops:0 (the leak check), and an exact-tool lesion where there is one.
- A harm mark on old skills for anything that trains further (sleep, creative, growth).
- Size counts the whole model. Every claim is against a same-size plain model trained the same way.
- Nothing pretrained ships. A pretrained model may be a teacher during training only. No Claude-written or
  Claude-judged training text (Ben, 09-26); the 1.2B, GLM, Luna and code may write it.
- Never score on GOLD-PRIVATE; never touch reserved or blind panels.
- Own machines first (5070 Ti and M1 Pro, several jobs each); Vast only when both are full.

## 4. The ladder

Each stage: the one question, its test and pass mark, what proves it wrong, what it waits on, and what runs next.
Stages in the same phase can overlap where the "waits on" column allows.

### Phase 1: Prove our own brain

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 1 | Do tonight's bench changes stack? (finish the bench) | **CRDW** (wide doors on the plan route, seeds 4-9 vs CRDC 287.0): stacks if held >= 292.0 and ahead on >= 5 of 6. **T2** quiet notes: helps if held >= 292.0 and ahead >= 5 of 6. **T1** learning-rate decay to 0: helps if other-4 held >= 136.7 and ahead >= 5 of 6 (sealed, `DIAG-v4.md`) | T2: held within 5 of CRDC and the family-mean lesion under 16 rows on every seed. T1: gain under +2 or ahead on <= 3 of 6 | Vast boxes E/G (CRDW about 10:45 PM), F (T2 about 12:30 AM); T1 behind CRDW | Write up the bench recipe as a reference; port any winner that applies to B2; then park the bench (Ben decided 11:20 PM ET 10-05) and give its GPU time to stages 2-3 |
| 2 | Does our own small model beat same-size models? | **B2 confirm**, seeds 200-205. PASS-1: pooled-5 vs plain_tf >= +2.0, CI above 0, >= 5 of 6 seeds; chain-5 >= +8 (McNemar p < 0.01); in_dist >= -1.0. PASS-2 (Ben's criterion): PASS-1 + pooled-5 vs plain_tf_steps >= +1.0 (CI above 0) + >= 2 points above fine-tuned pythia-31m + above 8-shot SmolLM2-135M and pythia-31m. loops:0 reported on all 6 (sealed, `custom_io/PASS-MARKS.md`) | pooled-5 d < +1.0, or in_dist d < -2.0 | PC memory: queue 33 (18 runs) and 30 wait behind the TEACH job; Mac queue 31 running | Its 6 parents feed the creative tests C1/C2; the Craftax-Classic probe (12a) can start |
| 3 | Does a teacher give it breadth? (Plan B, B1) | 10.9M B2 on TEACH vs B2 on GEN vs same-size plain_tf on TEACH; 2 seeds, then 6. **B1-a** TEACH - GEN on new kinds pooled >= +15, ahead on both seeds. **B1-b** donor state <= 10% on new kinds. **B1-c** B2 - plain_tf on TEACH >= +3, both seeds (sealed, PR #41 and addendum 3) | B1-a < +5 | TEACH data (PC, writing then answering); student code (custom reader/talker thread) | Pass: B2-M becomes the parent for phases 2-3. Wrong: one change, a ~100M student; then a stronger teacher arm, run as an open-weight model on our own machines or Vast (OpenCode Go: the teacher-data thread recommended against it because its terms ban programmatic extraction for training; Ben is deciding) |

### Phase 2: Make it learn like a person

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 4 | Can its program language say more? (build step) | Add rule, lookup, string and date operations as a small general base set, with a pieces library to grow the rest (creative roadmap section 9 default). Mark (proposed): practised skills within 1 point of the old language; the rule families where B2 trails (fewshot_number_rule, rule_apply) reach the step-writer's level, 6 seeds | rule families still trail by > 5 | custom reader/talker thread (owns B2's language); Ben can overrule "no new hand-written rules" before C2 is sealed | Unblocks C2 kinds, the crafting world (C5) and stepping stones (C6) |
| 4b | Can a small from-scratch talker turn the thinker's answer into plain English? (early probe of stage 9, the main risk) | On B2-M, add a small from-scratch sentence talker and train it on teacher-written answer sentences for the TEACH kinds (the 1.2B writes them; no Claude text). The value inside the sentence must come from the thinker's exact answer, as in CRT (talker writes calc(note)). Pass (proposed): sentence answers keep B2's held-out score within 3 points; donor thinker state <= 10%; report exact-value rate on dates and word edits and held-out story-text loss against a same-size plain LM (reported, not gated) | sentence answers more than 10 points below the copy talker: stage 9 then needs a bigger talker share or a talker that only fills slots | Stage 3's TEACH data (sentences); stage 2's parents; spec on CPU now (custom reader/talker thread) | Decides stage 9's design before any growth money is spent |
| 5 | Does it learn from its own checked tries? (creative C1) | B2 sleeps on its own checked tries at make-the-target puzzles. L1 W - N >= +10 every parent; L2 W - R >= +8; G0 aim; G3 harm <= 2 points; F1 first try W - N and W - R >= +5 decides "PASS with first answers" vs "search only" (sealed draft, creative roadmap section 6) | PC gate passes yet W - R upper end below its bar | Stage 2's 6 parents (a DEV-only pilot on B2 s100/s101 may run now) | C2 |
| 6 | Can it learn a new rule from a few examples? (Ben's main measure; creative C2) | Tries must reproduce every example in the prompt; sleep on the ones that do. Pass: first try on held-out rule kinds W - N >= +15 and W - R >= +10, reach@4 and practised skills within 2 of N. Report examples-to-learn: the k (0/8/32/128) at which a same-size plain net matches (provisional, creative roadmap section 7). In-context ruler (PR #23 C5 marks): with 8 examples in the prompt, >= 25 points above 0 examples, and shuffled-answer examples within 5 points of 0. Whole-model ruler (proposed): the plain net needs at least 4x our labelled examples to match | W - R upper end below +3 | Stage 4's rule operations; stage 5 plumbing | Creative floors C3-C9 (variety, own filter, stepping stones, pieces library, beyond the teacher, ask when stuck) as their own one-change tests |
| 7 | Does it keep facts exactly and get better overnight? (notebook PR #20, sleep PR #19) | **Notebook** (PR #20's pair test, re-posed on our own thinker because PR #20 was written around the frozen 1.2B): a pair is one question with two notebooks that differ in one fact, and both answers must be right. N1 read, N2 read then calculate, N3 edits, N4 the model writes its own notes, N5 notes survive a restart. Pass per rung: at least 16 of 32 pairs on every seed; N4 also exact writes >= 80% and junk writes <= 10% (PR #20 marks; seeds raised from 2 to 6 by the noise rule). **Sleep** (PR #19, also re-posed): day attempts, a code checker, a short night on checked work plus older checked work and some original practice; arms S (sleep), F0 (no sleep), PF (plain fine-tune), SU (unchecked). P1 learns: S beats F0 and PF by more than the margin on nights 1-5; P2 keeps old skills; P3 transfers to a never-trained kind; P4 does not lose plasticity night to night; P5 the checker matters (S beats SU); P6 no harm. Margins are fixed from a noise run before the first night (PR #19 rule) | Notebook: under 8 of 32 pairs even with 1 entry (exact facts cannot get through). Sleep: S no better than F0, or old skills drop past the tolerance | A parent from stage 3 (or 2); the notebook needs the code change PR #20 names | Sleep becomes part of every later stage's training loop |

### Phase 3: Grow and race

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 8 | Does it stay ahead as it grows? | Same recipe at about 11M, 30M and 100M, each against a same-size plain transformer. Pass (proposed, Ben's 09-26 scaling rule): ahead on new kinds pooled by >= +3 with CI above 0 and >= 5 of 6 seeds at every size, and the gap at 100M is not smaller than at 11M. One-change tests inside it: real sparse experts at equal active numbers (Ben approved 09-29; never live yet, the audit showed the router locked), and a learned stop (Ben's "thinking stop") | the gap at 100M is <= 0 | Stage 3 passing (the recipe); compute: our guess is hours per 100M run on the 5070 Ti, so 12 runs take days unless rented | Stage 10 at 100M |
| 9 | Can it talk in plain English, built from scratch? | An open-text talker that only translates the thinker's state into words (Ben, 09-29), trained on teacher-written simple text (TinyStories-style). Pass (proposed): on a sealed simple-English set, >= same-size plain transformer + 3 over 6 seeds, and a talker-alone control (donor thinker state) <= 10% | talker-alone within 5 of intact (the talker is doing the thinking) | Stage 4b's probe result; stage 3 (teacher data path); stage 8 size | Stage 10 |
| 10 | Does it beat same-size models in a sealed race? | Sealed panel, never trained on, scored the same way for every model. Our own sets: B2's held-out families, the B1 new kinds and the C2 few-example kinds. Outside sets: bAbI (20 reasoning tasks) and ARC-Easy at ~100M; GSM8K and MMLU-Redux added at 1-2B. A 13-gram overlap check against all training data runs before scoring. Whole size counts every weight that runs when it answers, borrowed ones included (Ben's rule); a teacher used only during training is not part of the model. Pass (proposed): ahead of every same-size rival by >= +3, CI above 0 over 6 of our seeds, on our own sets AND on at least one outside set (bAbI at ~100M, GSM8K at 1-2B); ARC-Easy and MMLU-Redux are reported, not gated, because they mostly test stored knowledge. At ~100M: SmolLM2-135M and pythia-160m (fine-tuned on our practice rows where possible, as PASS-2 does). At 1-2B: LFM2.5-1.2B, Qwen3.5-2B, MiniCPM5-1B (Ben's 09-26 list) | behind any same-size rival on our own sets, or behind on every outside set | Stages 6-9. The 1-2B race needs about a month of the 5070 Ti per from-scratch run (PR #41 estimate) or rented GPUs; spend over 50 cents needs Ben | Phase 4 uses the 100M model; the 1B run can go in parallel |

### Phase 4: Senses, hands and worlds

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 11 | Can it see and hear with its own eyes and ears? | **Ears** (PR #25, already from scratch: a 0.52M causal stereo ear, 50 ms slots): S1a left/right >= 90% and sound-onset F1 >= 0.8; S1b keep ours if its detection F1 is within 0.03 of the pretrained frame_mn06 at a third of its size; G2 with sound on, >= 20 points fewer creeper explosions than muted. **Eyes** (PR #26 uses a frozen 93M SigLIP2 encoder): SigLIP2 follows the Plan B teacher pattern, used only during training and never shipped, exactly like the 1.2B, so it does not break "nothing pretrained". Our own small eye is distilled from it and trained on game frames. Pass (proposed): within 5 points of SigLIP2 on the CPU probes already run (count, left-of, more-than, 9-digit hotbar 99.8%) at a third of its size or less, then PR #26's E1 (8-way same-scene pick >= 50%, >= 25 points above shuffled images) | Ears: mono within 10 points on left/right (a loudness shortcut). Eyes: our eye more than 10 points behind SigLIP2 on the hotbar digits | Ben restarting vision and audio (paused 10-03); recommended after stage 8, so the senses plug into the model that will play | Stage 12 pixels |
| 12 | Can it plan and act in a world? | **C5** tiny text crafting world (8-12 items): reaches items it never saw a plan for >= 10 points more often than no-sleep, every parent. **C10** Craftax-Classic (symbolic, fast), then Crafter pixels: beats a same-size plain agent at equal steps by >= 5 reward points, CI above 0; stretch: human level (65%), all 22 achievements (provisional, creative roadmap floor D). Hands: a small action head, like the talker but for keys | C5 within 2 points of random plans; C10 at or below the plain agent | C5: stage 4 plan operations. Craftax-Classic scored test: stage 3's parent. Crafter pixels: stage 11 eyes | Stage 13 |
| 12a | What breaks first when our thinker acts in a game? (Craftax-Classic probe, no pass mark) | B2's thinker with a small action head on Craftax-Classic's symbolic view (no eyes needed), a fixed step budget, next to a same-size plain agent. Reports achievements unlocked and where it fails. A probe only: it informs C10's sealed spec, it cannot pass or fail | n/a | Stage 2 (B2 confirmed). Craftax runs on JAX; on the Windows PC that likely means WSL (untested) | C10's spec |
| 13 | Can it beat Minecraft like a person? | First rung: wooden-pickaxe rate above a same-size plain agent at equal steps (creative roadmap C11). Then stone, iron and diamond tools, the Nether, the Ender Dragon. Today's best pixel result: Dreamer 4, diamonds in 0.7% of episodes at 2B weights (as cited in the creative roadmap) | first rung not above the plain agent | Stages 11-12; a written definition of "beat Minecraft like a person" before this stage starts | The north star |

Proposed definition for stage 13 (Ben decides before Phase 4): from a fresh survival world, with only the screen and
game sound in and keyboard and mouse out, no hidden game data, kill the Ender Dragon. Report how many hours of play it
needed next to a new human player's, because Ben's measure is how quickly it learns, not only whether it wins.

### Alongside, not on the Minecraft path

From "Ben's Model Ideas" (09-30): always-on thinking between messages, asking when stuck (creative C9), knowing it is
Premonition, tools and agentic jobs, quarantined web curiosity, a reading ladder, and the home assistant for Ben's uncle.
These join once phases 2-3 give a model worth running every day.

## 5. What runs next

Tonight (already queued, nothing new needed): CRDW (about 10:45 PM), T2 (about 12:30 AM), T1 after CRDW, on Vast; TEACH
then B2 confirm on the PC; Mac queue 31.

Then, in order of what unblocks most:
1. B1 students: 2-seed screen on the PC once TEACH lands (custom reader/talker thread).
2. B2 confirm read against PASS-1/PASS-2 (custom reader/talker thread).
3. C1 DEV pilot on B2 s100/s101 on whichever own machine is free (creative build thread; allowed now).
4. Program-language growth spec (stage 4) on CPU, so C2 can be sealed when B1 lands.
5. After tonight's bench results, the bench is written up and parked as the reference (decided by Ben).
6. Once B2 confirms: the Craftax-Classic probe (12a) on a free own machine.

## 6. Decisions only Ben can make

Decided at 11:20 PM ET 10-05: park the 1.2B test bench after tonight's three tests and move its GPU time to the
own-model road (Ben chose "Park it"). Nothing else is needed tonight. Later:

- Restart vision and audio: default after stage 8.
- The written definition of "beat Minecraft like a person": default above, before Phase 4.
- Money for the 1-2B race and for renting during stage 8: asked when the stage starts.
- A stronger teacher: OpenCode Go was recommended against by the teacher-data thread (its terms ban programmatic
  extraction for training); Ben is deciding. Any stronger-teacher arm would be an open-weight model on our own machines
  or Vast.

## 7. Risks and what would change the plan

- **B1 fails** (variety does not bring breadth): a ~100M student next; then a stronger teacher; then episodic
  few-example training (practice built as many small new tasks) as its own one-change test (suggested by the custom
  reader/talker report).
- **Breadth comes only from the teacher's answers**, not from the thinker: B1-b (donor <= 10%) and the plain_tf arm
  catch this.
- **Open English from scratch is the main risk to beating 1-2B models.** Every smaller talker so far lost (a 350M LM
  as reader and talker 66.1% vs 92.6%; a ~2M copy-and-gate talker 13.6% vs 78.2% on unseen kinds) and P0 showed B2's language cannot write dates or word edits
  (shown). TinyStories showed models under 10M write simple fluent English from teacher-written text (suggested); chat
  is harder. Stage 4b probes this early so stage 9's design is settled before growth.
- **The program language grows into hand-written rules**, against Ben's 09-26 rule: keep a small general base set and
  let the pieces library grow the rest.
- **Small-model Minecraft is a research gamble.** The crafting world and Craftax are the honest near targets.
- **Compute.** 100M runs fit the 5070 Ti (guess); a 1B from-scratch model is about a month of it (PR #41 estimate).

## 8. Sources

- Board and wins: `/mnt/project-files/progress-board/data.json` (updated 9:22 PM ET), live page
  https://claude.ai/artifact/GNHPEqGLygB1HNNiBkD95g.
- Bench: PR #38, `artifacts/ultracode-v4/{SCREEN,DIAG}-v4.md` on `claude/ultracode-learning-blocker-gh011t` (e9453368a).
- Own model: PR #39, `/mnt/project-files/custom-io/REPORT-custom-reader-talker.md`, `custom_io/PASS-MARKS.md` and
  `custom_io/design/B1-students.md` on `claude/custom-reader-talker-4x309r` (28ed57fe5).
- Plan B: PR #41, `design/thinker-first-split-2026-10-05.md` on `claude/project-thread-9ye9md`.
- Waste audit: `/mnt/project-files/model-audit/AUDIT-ranked-2026-10-05.md`.
- Creative: PR #43, `/mnt/project-files/creative-roadmap/creative-roadmap-2026-10-06.md`; build PR #44.
- Paused designs: vision PR #26 (+ #28), audio PR #25, notebook PR #20, sleep PR #19, CPU demo PR #27.
- Goals: `design/v3/30-modes/ben-goals-2026-09-26.md`; Ben's ideas page https://claude.ai/artifact/FfiNaagpFy8RfQwywAkyu3.
- PC state: Ben's Mac session log, 9:22 PM ET.
