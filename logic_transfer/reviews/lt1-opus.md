# lt1-opus (claude-opus-5-5, effort xhigh, batch)

stop_reason: end_turn; input 3,873 tokens, output 53,014 tokens; cost $0.54 at batch prices. Prompt: /mnt/project-files/logic-transfer/reviews/lt1-design-brief-2026-10-12.md

# Review of LT-1

Labels: **[SHOWN]** follows from your numbers. **[SUGGESTED]** likely, from the literature or reasoning. **[UNTESTED]** my guess.

## Verdict

- **The overall shape is right.** You continue training from the same parents, hold replay fixed, and compare a look-alike placebo with a replay-only arm. That is how the matched ablations you cite isolate logic [SUGGESTED].
- **It is not a one-night test.** A stage-1 run is 4,000 × 2.7 s = 3.0 h, and a stage-3 run is 1.5 h. The screen is 10 + 10 runs ≈ 45 CPU-h. Confirm adds 9 + 9 runs ≈ 40 h. The total is ≈ 87 CPU-h, about 4–6 of your nights [SHOWN, assuming stage-1 updates cost the same as learn-test updates: UNTESTED].
- **It checks its premise last.** M0 is scored only after all the compute is spent, and M0 as written can pass with no multi-step chaining (see Change 1).
- **The placebo has two leaks, and J cannot resolve its own pass marks.**
- **This is a marginal-dose test.** The parents already trained ~31 passes on 5 logic-flavoured families out of 34 [SHOWN]. LT-1 asks whether *more* logic at the end helps. That is a smaller expected effect than "logic vs. no logic" [SUGGESTED].

## Change queue (one at a time; each starts only after the previous one reports)

0. **Free checks** (30 min, no training).
1. **Feasibility gate**, tonight, ~12 CPU-h.
2. **Placebo fix.** Code it while Change 1 runs; it gets tested inside the screen.
3. **Frozen decision rules for V; J demoted.** Written before the screen starts.
4. **Tool fit count.** Zero training. Do nothing more on tools until LT-1 reports.

**Step 0.**
- (a) Pull the parents' existing per-split scores for syllogism, prop_eval, rule_apply, kin_chain and order_chain. They are a free prior on whether this model chains at all [SUGGESTED].
- (b) Benchmark 4 processes × 1 thread against 1 process × 4 threads for 100 updates. Then run the same 50 updates twice at 1 thread and compare the weights. Parallel single-thread runs often give tiny models more total throughput, and single-thread CPU runs are often bit-exact, which would remove the 2.6-point rerun noise [UNTESTED for your code].

---

## Q1. Is this the right test? What to change first

**Change 1: put a depth-resolved feasibility gate first.**

**What to run**
- Run arm L only, on s200, with the draft recipe (25% logic, lr 1e-4 constant), but go to 8,000 updates and checkpoint every 1,000.
- With a constant lr, the 4,000-update checkpoint *is* the draft's dose. The later checkpoints show whether more practice helps [SHOWN, from the recipe].
- Cost: 6.0 h plus logic-split evaluation [SHOWN].
- Use leftover budget to run C on s200 to 8,000 (6 h). C is needed in every later version, and this pair becomes screen pair 1.
- Do not look at V on this pair until the rules in Change 3 are frozen.

**What to measure**
- Use held-out wording and the rule-first generator, with ≥400 items per depth.
- The labels are balanced 3-way, so chance is 33.3%.
- Report per-label accuracy within each depth.

**Pass mark (logic learned).** Take the first checkpoint where all of these hold:
- depths 0–1 ≥ 80%;
- depth 2 ≥ 65%;
- depth 3 ≥ 55%;
- rule-first generator, depths 2–3 pooled, ≥ 50%;
- non-logic in_dist within 1.0 point of the parent.

That checkpoint's update count becomes the dose for every arm.

**Proved wrong** ("this model doesn't learn chaining from answer-only practice at this dose"):
- At 8,000 updates, held-out depth 3 < 45% **or** rule-first depths 2–3 < 45%.
- 45% is about 5 SE above chance at 400 items (SE ≈ 2.4 points) [SHOWN].
- If this happens, stop LT-1. Transfer from a skill that wasn't learned can't be read [SHOWN by logic]. The honest answer to the owner is "not by this route at this size."

**In between:** spend one more night on a single change, logic share 25% → 50%, with the same marks.

**Why the draft's M0 (L ≥ C + 20 overall) is too weak**
- If depths are roughly uniform over 0–3 [UNTESTED], a model perfect at depths 0–1 and at chance on depths 2–3 scores ≈ 67% [SHOWN arithmetic].
- C has never been trained to say "unknown" in this format, so C is probably ≤ 45% [UNTESTED].
- So "C + 20" can pass with zero two-step reasoning.
- Zhang et al. found ≈100% in distribution but 57% after a generator change. That makes the in-distribution logic dev split the wrong place to check M0 [SUGGESTED].
- The 11-feature classifier rules out 11 specific shortcuts, not the shortcuts a network can find [SUGGESTED].
- Check whether "unknown" is in the word list or must be generated (7 characters fits the 8-character generator) [SHOWN]. If it uses a different output mode, it has a different difficulty from true/false [SUGGESTED].

## Q2. Arms

**Is the placebo fair?** Its best feature is identical contexts. That absorbs new-wording and new-word effects, so keep it [SUGGESTED]. It has two leaks:

1. **Answer words.** P answers yes/no while L answers true/false/unknown. This shifts the talker's answer priors in any family that uses those words, which creates fake differences [SUGGESTED].
2. **Anti-inference labels.** P labels "derivable but unstated" atoms as "no." That actively trains the model *not* to draw conclusions, which makes P a mild anti-logic arm and inflates L − P [SUGGESTED].

**Is it too easy?**
- Probably yes. It is likely learned within a few hundred updates [UNTESTED]. After that its rows carry almost no gradient, so L vs P also compares "hard new rows" with "easy new rows."
- Wu et al.'s non-logic "Set" task recovered 65% of the pretraining benefit vs 67% for the logic-flavoured LIME task, so difficulty matters [SUGGESTED].
- Log each arm's training loss on its 25% slice.
- A difficulty-matched non-logic placebo is the next control, needed only if L beats P.

**Change 2: make the placebo format-matched and inference-neutral.**
- Use the same answer words and balance. Example: "Going only by the exact words above: Neil is not happy." → true (stated) / false (opposite stated) / unknown (not stated).
- Drop "derivable but unstated" queries. Keep the other-entity and opposite-polarity near misses.
- Keep the same contexts, lengths and NOOP calls.

**Pass mark:**
- P ≥ 95% on its own held-out wording (it actually did the task); and
- at the screen, mean(P − C) ≥ −1.0 on non-logic V and on in_dist.

**Proved wrong** (the placebo carries its own harm):
- mean(P − C) ≤ −1.0 on V, with all 3 parents negative.
- Then L − P is inflated and not logic-specific. Report L − C with that caveat, and don't confirm.
- Note that P − C ≥ +1 is a *finding* ("new text helps"), not a failure.

**Is C needed if P exists?** Yes.
- Only C tells you whether P harms on its own.
- L − C is the owner-facing comparison.
- The harm check H needs C.
- Save budget by dropping the standalone A/A run instead. The confirm's second course seed gives three within-parent C–C pairs for free [SHOWN, from the design].
- Make C's extra 25% come from a separate curriculum stream, so the shared 75% is identical batch-for-batch.

**Should logic rows replace syllogism/prop_eval rows?** No.
- It changes two things at once.
- It removes the near-transfer families you need to measure (Q5).

**A larger share?** Only through Change 1's "in between" branch.

## Q3. Dose, M0, training from scratch

**Is the dose enough?** Probably not for depths 2–3.
- 64,000 logic rows equal about 1,000 pure-logic updates at batch 64 [SHOWN].
- On the narrower F4 task, 2,000 pure updates gave only 15.7% [SHOWN].
- If families were evenly weighted [UNTESTED], the logic course is ~35% of one family's original exposure, at the end-of-schedule lr [SHOWN arithmetic].
- In ProofWriter, answer-only accuracy collapses with depth [SUGGESTED].
- Don't argue about it; Change 1 measures it.
- Keep lr at 1e-4. The learn test shows it can teach new tasks [SHOWN]. Change duration before changing lr.

**What M0 bar?** The depth-resolved marks in Change 1.

**Train from scratch?** No.
- 3 arms × 6 seeds × 1–3 CPU-days = 18–54 CPU-days [SHOWN].
- It also answers a different question (a logic-heavy curriculum from the start).
- Fund it only if LT-1 is positive.

## Q4. Pass marks and statistics

**Change 3: freeze these rules before the screen.**

**Design rules**
- A "pair" is (parent, course seed).
- Within a pair, all arms share the curriculum stream, and L and P share the order of contexts.

**V decision rules**
- **Screen (3 pairs).** Proceed to confirm only if all of these hold:
  - mean(L − P) ≥ +0.75;
  - mean(L − C) ≥ +1.0;
  - L − P > 0 on ≥ 2 of 3 parents;
  - M0 passed on all 3 parents.

  Otherwise stop and report "no sign of transfer; not tested to confirmed either way." Don't spend two nights proving a negative [SUGGESTED].
- **Confirm (6 pairs), PASS.** Keep your numbers: mean(L − C) ≥ +2.0 and mean(L − P) ≥ +1.0. Both need a paired-t 95% CI (df 5) above 0. Add two conditions:
  - parent-averaged L − P > 0 for all 3 parents;
  - H holds.
- **PROVED WRONG.** The upper 95% bound of L − P is below +1.0.
  - This replaces the draft's point-estimate falsifiers, which can't tell "no effect" from "too noisy to tell."
  - At a per-pair SD of 2, a true +1 effect would come out ≤ 0 about 11% of the time [SHOWN under a normal assumption; the SD is UNTESTED].
- **Anything else:** say "inconclusive."

**Statistics**
- The paired t over the 6 differences decides. But the 6 are 3 parents × 2 course seeds, so the effective n is between 3 and 6. The all-parents sign rule is the guard.
- Tell the coordinator this is a loose reading of "6 paired seeds" [SUGGESTED].
- Don't decide by item bootstrap, because it ignores training noise. The F4 rerun gap (2.6 points) is at least as large as the item SE (~2 points) [SHOWN numbers; the comparison is SUGGESTED]. Use the bootstrap only to report per-run SE.
- **Falsifier for the rules themselves.**
  - The 6-pair CI half-width is 1.05 × the per-pair SD [SHOWN: t(0.975, 5)/√6].
  - If the screen's SD of L − P is above 1.5, the confirm cannot reach either verdict at these marks.
  - In that case, write "underpowered" instead of running it.
- Noise context:
  - V has ~29 × 200 = 5,800 items, if every trained family has a variant cell [UNTESTED].
  - The item SE is ≈ 0.6 points at ~37% [SHOWN].
  - The per-pair training noise is the unknown.

**J: demote to exploratory for LT-1.**
- At 2,000 updates F4 ≈ 15.7%, with item SE ≈ 1.8 [SHOWN].
- If the single 2.6-point rerun gap is typical [UNTESTED], the per-pair difference SD is ≈ 3.3. The CI half-width is then ≈ 3.4 at 6 pairs and ≈ 8 at 3 pairs [SHOWN].
- So L − P ≥ +2 can never be resolved, and +4 is at the edge.
- The confirm phase costs ≈ 27 CPU-h for J alone [SHOWN].
- If you keep J:
  - generate a frozen 1,260-item F4 (evaluation cost only);
  - score the area under the curve at 500, 1,000, 1,500 and 2,000 updates;
  - add the answer's teacher-forced log-likelihood as a smoother companion measure.
- Exploratory marks: "a lead worth its own test" if L − P ≥ +4 on all 3 parents; "dead" if L − P ≤ 0 on 2 of 3.

**H:** keep it and apply it to both L and P: mean(X − C) ≥ −1.0 on non-logic in_dist.

## Q5. Measures

**Most likely to show real transfer**
- **Near families** (rule_apply, kin_chain, order_chain) on the variant and vocab splits. They share "chain over stated relations" [SUGGESTED; Thorndike & Woodworth].
  - Promote this to a pre-registered secondary, **N**.
  - PASS: mean(L − P) ≥ +3.0 with CI > 0.
  - Proved wrong: upper bound < +1.0.
  - If logic doesn't help its closest neighbours, "helps with stuff" is dead at this size [SUGGESTED].
- **Text families that bind facts to named entities** across several sentences, with distractors and negation (passages, word stories) [SUGGESTED].
  - Report V-text and V-calc separately.
  - Fix the family lists now, before seeing any results.

**Least likely to show real transfer, or most likely to show fake transfer**
- **Calculator variants.**
  - Your main weakness sits here: 268 of 270 errors were in the variant split, on the sibling model [SHOWN].
  - Those errors likely come from mapping unseen layouts to calculator programs, which logic doesn't practise [SUGGESTED].
  - L and P both teach NOOP 25% of the time. That can depress tool use in both arms, a *fake harm* relative to C [SUGGESTED].
  - Add: round-1 NOOP rate on calculator dev rows, per arm.
- **Any family answered with yes/no/true/false.** The answer-prior shift can fake a gain or loss [SUGGESTED]. Add: an answer-word histogram per family, per arm.
- **J.** A checkpoint that just trained on unfamiliar rows may fine-tune faster regardless of content. On top of that, J has about 3 points of noise [SUGGESTED / SHOWN].
- **Family split and F5.**
  - The family split is 1.3% ≈ 10 of 800 items, and F5 is 0–1.4% [SHOWN].
  - At the floor, a handful of flips reads as a doubling.
  - Drop both from every decision.
- **Frame split.** "Claim:" adds new closers. P absorbs this because its wording matches L's [SUGGESTED].

## Q6. Outside logic tool

**Not now.**

**The interface is too small for logic problems.**
- The call writer emits an op plus two numbers or spans, for at most 7 rounds [SHOWN].
- Your own example has 6 statements plus a claim. At one call per sentence that already uses all 7 rounds.
- "If Neil is pifmub, Neil is not happy" has three symbols plus a polarity, so it needs ≥ 2 two-argument calls. That makes ≥ 8 calls [SHOWN by counting].
- It fits only if the model skips the distractors. That means it already knows which sentences matter, which *is* the reasoning.

**Don't use a whole-prompt parser.**
- A tool that takes the whole prompt as one span and parses it in Python obeys the letter of the rules.
- But it puts the translation step, the weak link per Logic-LM and LINC [SUGGESTED], into hand-written code. The model would only learn to press a button.

**A cheaper honest design for later**
- A stateful fact-store tool with two-argument span-copy ops: FACT e p, NOTFACT e p, ALL p q, NO p q, ALLNOT p q.
- Conjunctions take two steps: AND p q returns a new id k, then ALL k r.
- QUERY e q returns true/false/unknown.
- The model chooses the spans and ops, so the translation is learned.
- It answers "can it use a logic tool?", not the owner's transfer question.

**Change 4: count whether problems fit (zero training).**
- Encode 5,000 generated rows under that op set.
- PASS (a tool test is mechanically possible): ≥ 60% of depth-≤3 rows fit in 7 rounds.
- Proved wrong (a model-side change is needed first, such as more rounds): < 30% fit.

## Q7. Predictions [all UNTESTED]

**Outcome probabilities**

| Outcome | Probability |
|---|---|
| M0 (Change 1 marks) passes at 4,000 updates | 25% |
| M0 passes by 8,000 updates | 40% |
| V passes at confirm | 5% |
| J passes | 5% |
| L beats C but not P (on V) | 10% |
| No arm separable on V (most likely outcome) | ~60% |
| L and P both slightly below C on calculator variants (NOOP/replay dilution) | ~20% |

**Reasons**
- At 8B–70B the effect is +0 to +4 points, and it shrinks under matched controls [SUGGESTED].
- 3.3M parameters is about 2,400× smaller than 8B [SHOWN].
- Chaining and calculator layouts share few elements [SUGGESTED].

## Q8. Summary for the owner

(In the summary below, the literature points are SUGGESTED and the odds are UNTESTED.)

Your hunch is reasonable, but the evidence says logic practice helps other skills only a little, and only in models thousands of times bigger than ours; nobody has checked one this small. So we'll treat it as a question, not a goal. Tonight: one check of whether our model can actually learn multi-step logic, not just tricks. If it can't, that's a real answer, found cheaply. If it can, we compare three versions: extra logic practice, a "fake" practice that looks the same but needs no reasoning, and normal practice. Logic only gets credit if it beats both on skills the model is bad at. My honest guess: roughly a 1-in-20 chance it does.
