# lt1-fable (claude-fable-5-1, effort xhigh, batch)

stop_reason: end_turn; input 3,873 tokens, output 31,456 tokens; cost $0.81 at batch prices. Prompt: /mnt/project-files/logic-transfer/reviews/lt1-design-brief-2026-10-12.md

# Review of LT-1

**Verdict.** The shape is right — treatment vs. matched placebo vs. replay, continued training from shared parents, bars written first. That already beats most of the published transfer studies in your summary, which have no placebo arm. [SUGGESTED] As drafted, though, it is 2–3× over budget, its primary measure cannot register the effect sizes anyone has ever reported, and it tests "more logic," not "logic," because the curriculum already trains five logic families. [SHOWN — numbers below]

## Numbers that drive everything

1. **Cost.** Stage 1: 10 runs × 4,000 × 2.7 s = 30.0 CPU-h. Stage 3: 10 × 2,000 × 2.7 s = 15.0 h. Screen ≈ 45 h before scoring; confirm adds ≈ 27 h. Budget: 15–25 h. [SHOWN] Scoring ~40,800 dev rows per checkpoint × 10 checkpoints is un-timed; if the 7-round tool loop makes eval slow it could rival training. [UNTESTED — time one full eval first]
2. **Dilution.** V averages ≈ 29 non-logic families × 200 = 5,800 variant items. If logic gave +5 on five related families and 0 elsewhere, V moves +0.86 — under your +2.0 bar. [SHOWN, arithmetic]
3. **Dose.** 64,000 logic rows ≈ 1.0% of the 6.14M rows the parent saw; the whole course is 4.2% extra update-volume at one-tenth peak lr. [SHOWN] The +1 to +4 point effects in your summary came from logic in the pretraining mix at 8B–70B. [SUGGESTED, from your abstracts]
4. **Noise.** Item SE on V ≈ 0.63 points (p ≈ 0.37, n = 5,800). [SHOWN] Run-to-run noise on identical items is unknown; your one data point (2.6 pts) is from a 420-item probe, 14× smaller. [UNTESTED — this is what C vs C′ must tell you]
5. **J is handicapped against L.** L and P replace 25% of calculator-supervised rows with NOOP rows (weight 0.1); C does not. F4 needs SUM/MAX plus +/*. "PROVED WRONG: L − C ≤ 0" can trigger by construction. [SHOWN from the design; direction SUGGESTED]
6. **Logic is already in the model.** Syllogism, prop_eval, rule_apply, kin_chain, order_chain are trained. LT-1 asks whether a harder, more varied sixth logic family adds anything. [SHOWN]

## Changes, in order (do 1 first; 2–5 are edits to make while it runs)

**Change 1 — pilot the dose, shrink the grid.** Run arm L on s200 only, 4,000 updates, checkpoints at 1k/2k/3k/4k. Score logic dev (train wording), held-out wording, depths 4–5, rule-first generator, non-logic in_dist at each. Reuse it as the screen's s200-L. Time one full eval on the 1k checkpoint.
- *Pass (new M0, replaces "C + 20"):* ≥ 70% logic dev overall AND ≥ 55% at depth 3 AND held-out wording ≥ train wording − 5, at 4k or earlier. Earliest passing checkpoint D becomes course length. Rationale: C's ceiling is ~66.7% if it never emits "unknown," so "+20 over C" can pass with L at 55% on a 3-way task. [SUGGESTED, if no trained family answers "unknown"]
- *Proved wrong:* < 55% overall or < 40% at depth 3 at 4k → model didn't learn the logic; raise the share to 50% (not the update count), match in P, retry. Transfer runs on an M0-failed model are uninterpretable — don't run them.
- *Shortcut sub-check (report, not gate):* rule-first generator ≥ dev − 10. Failing is the Zhang 2022 pattern; transfer result still stands, mechanism claim weakens. [SUGGESTED]
- *Screen grid:* s200 {L, P, C, C′}, s201 {L, P}, s204 {L, P} = 8 runs ≈ 24 CPU-h at D = 4,000; no Stage 3 at screen. C's jobs (noise floor, P − C variety effect, absolute harm) need one parent, not three.

**Change 2 — make the placebo a placebo.**
(a) Labels: 3-way and balanced like L — "stated true / stated false / not stated." As drafted L learns a new 3-way label set and P a 2-way one; any gain on the "answer" split (new answer mix) could be a label-prior shift, not logic. [SUGGESTED]
(b) Drop "derivable-but-unstated → no." In arm P it teaches the model to deny the exact inferences that syllogism/rule_apply reward in the same batch — a negative control, not a neutral one, and a weakened P inflates L − P. [SUGGESTED] Use entity-swap, polarity-flip, never-mentioned atoms only.
- *Pass:* P's placebo dev ≥ 90% AND P's syllogism + rule_apply in_dist ≥ C − 2.0.
- *Proved wrong:* syllogism + rule_apply in_dist ≤ C − 3.0 → placebo is anti-logic; fix before confirm.
- P will be easier to learn than L; unavoidable — every non-chaining task on these contexts is a lookup. Log both learning curves so the gap is on record. [SUGGESTED]

**Change 3 — L − P is the hypothesis test; add a pre-registered "near" set.** L − C bundles logic with less replay, less calculator supervision and new-family variety; P removes all three. Keep L − C and L − parent as practical/harm numbers. Before seeing any arm result, list the non-logic families whose rows contain negation, a conditional, a universal word, or need ≥ 2 hops (V-near, ≥ 1,000 variant items). Thorndike–Woodworth and the LIME/Set result say that's where transfer lands if it exists. [SUGGESTED] V-all stays as the test of the owner's literal claim.
- *V-near pass:* mean L − P ≥ +2.0 over 6 pairs, ≥ 5/6 positive, paired-t 95% CI > 0. *Proved wrong:* mean ≤ +0.5.
- *V-all pass:* mean L − P ≥ +1.0, same rules. *Proved wrong:* ≤ 0.
- *H:* L − P on non-logic in_dist ≥ −1.0; L − parent ≥ −1.5.
- *Screen → confirm:* V-near L − P ≥ +1.0 with 3/3 positive, or V-all ≥ +0.5 with 3/3 positive.

**Change 4 — statistics.** Per pair: differences on identical items, item-bootstrap (10k) CI so each pair demonstrably clears item noise. Across pairs: mean and paired t, 5 df (half-width 2.57 × SD/√6). Your 6 pairs are 3 parents × 2 course seeds, not 6 independent pairs [SHOWN]; also report the three parent-level means and require all three to share sign for "confirmed." [SUGGESTED]
- *A/A gate:* |C − C′| ≤ 0.5 on V-all and ≤ 1.0 on V-near. *Proved wrong:* larger → bars sit in the noise floor; no claim either way; add seeds or items.

**Change 5 — demote J.** Run the learn test only at confirm, only L vs P, read F4 at 4,000 learn updates. At 2,000 the curve climbs ~6 points per 1,000 updates (15.7 → 28.1) [SHOWN], so you'd measure learning speed through a steep window with ±2.6 run noise. [SUGGESTED] *Pass:* L − P ≥ +5, t-CI > 0. *Proved wrong:* ≤ 0. Forward chaining and SUM/MAX grid formulas share no elements I can name; J is the measure most likely to come back null even if V-near is real. [SUGGESTED]

## Remaining questions

**Q2 — replace / share.** Don't replace syllogism/prop_eval; removing practice is a second treatment. 25% is fine if M0 passes; otherwise raise share, matched in P, accepting more forgetting risk. [SUGGESTED]

**Q3 — from scratch.** No: 1–3 CPU-days/run forbids 6 seeds, and continued training answers the owner's practical question. State up front that pre-pretraining effects in the literature exceed fine-tuning effects, so a null here doesn't exclude a from-scratch effect. [SUGGESTED] A 2-seed from-scratch ablation is the follow-up if V-near screens positive.

**Q5 — fakes.** "Answer" split via label priors (Change 2a); vocab via fresh-word exposure (P controls); J via calculator deficit (Change 5); any L − C gain via variety (P controls). Most likely real: V-near. Drop nothing; add the near list and the C′ floor.

**Q6 — tool.** Not now. It answers "can a 3M model drive a solver," not "does learning logic help other skills," and the owner's thesis is about the model being the logician. If you later want one that obeys the rules, keep the reasoning in the model and make the tool pure memory, using the span arguments the call writer already has: ASSERT(entity-span, predicate-span) stores an atom and echoes it; LOOKUP(entity-span, predicate-span) returns stated/denied/absent over prompt facts plus stored atoms; a polarity variant for negation. The model chains by choosing what to assert over its 7 rounds; the generator emits the derivation as program-checked steps. That is the ProofWriter step-by-step regime that held at depth 5 while single-shot collapsed. [SUGGESTED] Whether the thinker learns it: [UNTESTED]. A tool that parses English and chains for the model is allowed by the rules but tests nothing about the model.

## Predictions [all UNTESTED — priors]

- M0 passes at 25% / 4k: 60%.
- V as drafted passes through confirm: 7%. V-near (L − P ≥ 2.0, confirmed): 12%. V-all (≥ 1.0): 10%.
- J as drafted passes: 4%. J's L − C negative: 55%.
- L beats C by ≥ 1.0 on V-all but L − P ≤ 0.5 (variety, not logic): 30%.
- Everything within ±1.0 of everything (clean null): 45%.
- H fails, L vs C: 20%.

## For the owner

Your idea — teach the model logic so it gets better at everything — can be tested, and the plan is basically sound: continue training three copies on logic puzzles, three on look-alike puzzles that need no reasoning, then compare them on skills nobody practised. Two fixes first: the plan costs roughly twice the overnight budget, so we shrink it; and we check that the model actually learned the logic before asking whether it helped anything else. Honest forecast: at this tiny size, with five logic-style tasks already in training, the likeliest result is "no measurable help beyond what any new puzzle type gives." If so, logic isn't the headline goal. If it helps, we'll know where.
