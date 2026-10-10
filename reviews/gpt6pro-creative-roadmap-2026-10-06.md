# Prompt for GPT-6 Pro (web): a roadmap for a creative small model (2026-10-06)

Paste everything below the line into GPT-6 Pro. It cannot see the repo, so the prompt carries the numbers.
Check every factual claim in the reply against the code and the cited files before acting on it.

---

I'm building my own small AI model and I want an outside opinion on the hardest part: making it **creative**. I want
a roadmap I can actually run on my own hardware, one experiment at a time. Please be blunt about what won't work.

Rules for your answer:
- Label every claim **shown** (a published or measured result you can name), **suggested** (reasoned) or
  **untested** (a guess).
- Keep these lines of work separate and say which one each idea is for: (1) the old 24-puzzle experiments on a frozen
  1B model, (2) today's "sandwich" model, (3) the small from-scratch models. Don't mix in our toy card experiments or
  our "village" text world unless you say so explicitly.
- Every experiment you propose must change one thing at a time, with pass marks fixed in advance and the result that
  would prove it wrong.
- End with a plain-language summary for me (I'm a high-school senior), at most 200 words.

## 1. What I mean by creative

My working definition: when the thinker can't solve something, a creative part produces many varied tries (wrong
guesses allowed), a checker or judge keeps the lucky ones, and the lucky ones are trained into the model during a
"sleep" phase, so next time the thinker can do it alone. Earlier I also liked these extra ideas: restate a hard
problem as easier variants and carry the pieces back; keep a library of reusable solved pieces fetched by shape;
let the model choose what to practise (problems it solves sometimes but not always); retry open problems after each
sleep; give it tools like a calculator; and teach it to say "can't" on impossible problems.

The long-run goal (north star) is an agent that beats Minecraft like a person does: screen in, keyboard and mouse out.
Other goals: skills and critical thinking first, learning from few examples, and beating 1-2B models at the same
total size.

## 2. The model today

**The sandwich (the main line until yesterday).** A frozen LiquidAI LFM2.5-1.2B-Instruct reads the question. A small
door (2048 -> 32 -> 256) feeds a ~9M-weight looped "core" (256 wide, 4 fixed rounds; its mixture-of-experts router
never trained, so about 1.6M weights are live). The same frozen 1.2B then talks, reading 8 core vectors plus every
question word again. The thinker is under 1% of the weights. Measured (shown, 6 paired seeds unless noted):
- 92.2% exact on practised question kinds written by people; 78.2% on 384 questions of never-practised kinds; the
  bare 1.2B with 8 examples gets 75.0% practised and 67.7% / 77.6% on the two new-kind sets.
- On new kinds the 1.2B does the thinking: giving the talker another question's core vectors still scores 73.2%,
  the same as the right vectors (1 seed).
- A "plan route" works: the core picks numbers and operations, an exact calculator computes, the talker reads the
  result. 89.7% held-out on the 8 hardest families (chain questions 156 of 160). Swapping plans between questions drops
  chain answers to 2-3 of 160, so there the thinker really decides.
- A 32-member "swarm" of small models voting or routing did not help on twisted versions of questions: the members
  all miss the same questions.

**The direction I picked yesterday ("Plan B").** My own thinker grows to most of the model; the reader and talker
become tiny custom parts; the 1.2B is used only as a teacher during training (it writes and answers practice
questions) and never ships.

**The from-scratch design B2 (3.3M weights, nothing pretrained).** A character-level reader; a looped thinker that
writes a tiny program (operations plus pointers to numbers or words in the question); an exact integer executor that
runs the program; and a pointer-generator copy talker that copies letters or words from the question. Trained on
200,000 synthetic "skills" rows (arithmetic chains, letter and word tasks, lookups, rules), 24,000 updates.
Shown, 2 seeds:
- 73.7% over five held-out splits (new answers, new sentence frames, new words, new wordings, in-distribution),
  against 67.7% for a same-size transformer that writes out worked steps and 54.4% for a plain same-size transformer.
- 99.7-99.8% on 5-step chain problems.
- The thinker decides: another question's thinker state gives 3.8%; with no executor, program families drop to 0.6%;
  swapping the executor's ADD and SUB makes 99.9% of answers follow the swapped program.
- It loses where the data has no program and the rule must be found in latent space: few-shot number rules -9 points,
  rule application -6 points against the step-writing transformer.
- **Every model here, ours and the baselines, scores 0-4% on held-out task families.** Programs exist only for the 11
  arithmetic families that have worked steps in the data.
- Next test (not run yet): B2 at 10.8M trained on 200,000 teacher-written rows over 60 question kinds, against the
  same student on hand-generated rows, scored on 12 held-out kinds. Pass mark: +15 points on both seeds.

## 3. What our creativity experiments showed

All of these used a frozen MiniCPM 1B with LoRA "sleep" on number puzzles like "use 3 to 4 numbers once each to make
the target" (targets 5-40, or 24). The "checker" is exact code. "Luck" = right tries out of 30 per fresh test puzzle.
All shown, with pass marks fixed before each run.

| Run | Question | Result | Verdict |
|---|---|---|---|
| blurt-1 | How often are free guesses right? | 2 and 4 of 1,800 right; 69-78% used numbers not given. Guesses forced to keep the rules: 42 of 1,740 (2.4%) | Rule-keeping helps 10x |
| blurt-2 | Does sleeping on lucky hits raise first-try solving? | Fresh puzzles solved first try: 6 of 127 before; 17 (CPU run) and 12 (GPU run) after, vs 6 and 5.5 for sleeping on the same amount of known answers. Bar was +8 on both runs | FAIL (GPU run +6) |
| blurt-2p | Do the hits need to be right? | Sleep on right guesses 13.5, on wrong guesses 9.5, before 8 (of 120) | FAIL (+4 vs bar +5); wrong guesses gave +1.5 |
| blurt-3 | Does sleeping on lucky hits raise luck itself? | Lucky tries 63 before; 126 and 136 after (2 seeds) vs 85 and 87 for sleeping on its own known answers. Puzzles with at least one hit: 27 before, 38 and 38 after, vs 3 and 4 | PASS |
| blurt-3r | Replication on new seeds and another machine | 59 -> 129 and 148 vs 59 and 58. Puzzles hit 29 -> 40 and 43 vs 4 and 3 | PASS, replicated |
| blurt-4 | Hindsight relabelling ("a try that made 22 solves make-22") | Lucky tries: plain recipe 221, correct relabels 140, WRONG relabels 140. But puzzles reached: relabel arms 41-46 vs plain 32-35 | Proved wrong on the registered measure; relabel correctness didn't matter; more varied targets widened reach |
| blurt-5s | Are the model's own hits special? | Puzzles solved within 30 tries (3 seeds): own hits 112/108/110; exact-solver answers to the same puzzles 123/113/117; repeated known answers 14/12/11; before 77 | Proved wrong: own hits are not special |
| ask-24ab | Can the frozen 1B tell solvable from impossible puzzles? | 50% balanced accuracy in every answer format | Proved wrong |
| ideas | Gift and plan ideas, 30 tries per request | 44 of 300 tries good (15%); 9 of 10 requests had at least one good try. Best trained judge picked a good idea first on 3 of 10 (AUC 0.80); the 1B judging itself 2 of 10 (AUC 0.69) | The judge is the bottleneck |

Lessons we drew (please check them):
1. Sleeping on checked hits about doubles luck on fresh puzzles of the same family and keeps variety; sleeping only
   on already-known answers collapses variety (puzzles reached fell from 27-29 to 3-4). (shown, one family)
2. The gain comes from correct answers to NEW problems, not from the answers being the model's own. Where a solver or
   teacher exists, its answers teach as well. So the creative loop's real job is finding checked answers where no
   solver or teacher exists. (shown for puzzles; the solver answers were also shorter, which isn't ruled out)
3. First-try solving moves much less than luck. (shown)
4. For fuzzy problems (ideas), the judge, not the generator, limits us. (shown, small sample)

A design from 3 days ago (never run) moved this to the sandwich's 9M core: "make-the-target" puzzles checked without
an answer key, candidates made by sampling the core's calculator-call heads (the language model's temperature can't
vary the calls, because they are chosen before it speaks), a rule-valid but value-blind placebo, a solver-trained
positive control, and a "twin target" test (same numbers, different target) to prove the model aims at the target
rather than just following the rules.

## 4. Hardware and budget
One RTX 5070 Ti (16 GB) and an M1 Pro laptop, often busy with other runs. Short rentals of an RTX 5090 are possible at
about $0.40-0.50 an hour, but I prefer my own machines. The teacher 1.2B runs on the 5070 Ti with plain transformers
generation.

## 5. What I want from you

1. **A usable definition.** Turn "creative" into things I can measure for a small program-writing thinker. For
   example: luck (pass@k on fresh problems), reach (problems with at least one hit), first-try gain after sleep,
   number of distinct correct solutions, solving problems no solver or teacher in training could, transfer to new
   families. Which should be the main score at each stage, and why?
2. **Where variety should come from** in a thinker that writes programs: sampling the program heads, latent noise, a
   separate proposer network, the teacher writing hints or variants, mutating earlier solutions (evolutionary),
   quality-diversity archives. What keeps variety from collapsing over many sleep rounds?
3. **Cold start.** Held-out families score 0-4%, and "no hit means no signal". How should a small model get its first
   hits on a family it has never seen: easier variants, a library of pieces, analogy to known families, teacher hints
   that fade, self-set practice tasks? Which is most likely to work at 3-100M weights?
4. **The checker ladder.** Order the environments from exact checkers to fuzzy ones on the way to Minecraft. For
   example: number puzzles -> program puzzles with hidden tests -> a text crafting world with a tech tree (a simulator
   is the checker) -> a 2D pixel game like Crafter or Craftax -> Minecraft. Which steps are necessary, which can be
   skipped, and what pass mark proves each step before climbing?
5. **The role of the 1.2B teacher** in a creative loop it must not ship inside: problem writer, hint giver, judge for
   fuzzy ideas, curriculum setter? Where does it help, and where does it cap the student at the teacher's level?
6. **Library of pieces.** Should solved sub-programs become new named operations the thinker can call (DreamCoder or
   Stitch style)? How do I test that the library makes the model more creative and not just faster?
7. **What will NOT work at small size**, with evidence.
8. **The first three experiments**, in order, each with one change, the model and data, arms and controls (including a
   placebo), pass marks fixed in advance, the result that would prove it wrong, and a rough GPU-hour cost on a 5070 Ti.
9. **A milestone roadmap** from here to "creative enough to play Minecraft", with what each milestone must show. Say
   honestly where the path is a research gamble.

Please end with the plain-language summary for me.
