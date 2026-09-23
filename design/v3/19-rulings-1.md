# Experiment 19 — Astra's rulings 1

Astra · 20 September 2026 · prospective amendment before freeze.

These rulings resolve the eight questions below; the remaining registration, budgets, primary marks and seeds stay as written. Include this file in the freeze manifest. The supplied rehearsal counts are disposable-fixture evidence, not registered outcomes. No experiment was run for these rulings; only this new file was written.

1. **Generation gate — count distinct (world, question) instances.** For each registered seed and each of the four structures, require at least 16 unique `(question-free world fact-set signature, full raw question tokens)` pairs, spanning at least 16 unique world signatures. Count only sampled, accepted G questions; exclude fallbacks and repeated pairs. The same question tokens on different worlds count separately. Each structure must have zero instances throughout the awake corpus. A memory index is an equivalent key only after memory-world uniqueness is verified. Entity-ID coverage is descriptive, not a gate.

   Reason: this measures generated practice across worlds; it does not require binding every possible entity name.

2. **Operator history — choose (a): reconstruct and exclude before freezing.** Fable should do the separate bounded, resumable provenance wave specified in §7, without model forwards. Reconstruct all training stages contributing to the canonical checkpoint from their exact archived sources, RNG state and schedules. Add question-free world signatures to the exclusions for development and later confirmation, including both sides of edit pairs. An incomplete reconstruction remains an unresolved freeze prerequisite.

   Exact audit claim, permitted only after verification: “No complete evaluation world matches a reconstructed canonical-operator training world or an experiment-19 training/replay world under the question-free, named-token fact-set signature. Composite relation-10 question types were excluded from every experiment-19 training channel for the dispatcher and transformer. The dispatcher still uses a historically pretrained primitive operator.” This establishes exact-world isolation, not isolation under arbitrary entity renaming. Development success remains development-only until confirmation passes.

   Reason: historical operator isolation is already required by §7, and no registered data have yet been generated.

3. **Fallback order — accept fixed-slot replacement as the resolved registration.** If `k < 4` sampled questions are accepted, keep them in slots `0..k−1`; for each remaining slot `j`, insert original awake question `j`. Apply identically to G and U. A fallback may duplicate an already accepted question: keep and log it, exclude it from the generation gate, and do not search for a replacement or extend the attempt budget.

   Reason: this makes the ambiguous “source order” instruction deterministic without introducing another selection rule; zero rehearsal fallbacks does not remove the need to specify it.

4. **World identity — yes.** Use the canonical question-free set of eligible fact tuples, retaining entity IDs and values while ignoring row order and filler. Admit the first 1,024 distinct signatures in encounter order, retain their original world bytes and four awake questions, and log/skip later duplicates for memory admission only. Training/evaluation collisions still follow §7's abort rule.

   Reason: different questions or presentations do not turn one fact world into several memory worlds.

5. **Distinct people — yes, including L.** Require all `c` visited people—the start and the people reached by the `c−1` LINK calls—to be distinct in every development and corresponding confirmation cell, and on both sides of pairs. The terminal attribute value is not another person. This explicitly extends §6's rule to L; do not impose it on awake/replay questions. Keep the fixed rejection limit and log attempts.

   Reason: the feasible restriction prevents cycles from making an apparently long question require fewer distinct steps.

6. **Answer stratification — accept the target rule, with one necessary ending-schedule correction.** With zero-based `i`, keep `target_answer(i) = 12 + (i mod 16)`, fixed before draws: four occurrences per value at 64 units and 32 at 512. In L's mixed 8/9 cells, replace the current `i mod 2` ending schedule with `r(i) = 8 + (floor(i/16) mod 2)`. This gives each answer value equally often with each ending: two per ending at 64, sixteen at 512. For E pairs, the target applies to the original side; relevant edits must still change its answer. Selection uses the interpreter only, never model performance.

   Reason: hiding `i` is insufficient when its two cycles otherwise make visible relation 8 predict an even answer and relation 9 an odd answer.

7. **Forgetting readout — amend and accept as secondary.** Score awake-final and offline-final on identical F/H units for every architecture × seed × arm. Record answer and strict counts separately, each out of 64; never add them. A trigger requires a fixed architecture, arm, cell and metric for which `awake_count − offline_count ≥ 7` in at least two of the three registered seeds. Different cells, metrics or arms cannot supply the two replications. Runs must satisfy §5's awake qualification; an H cell is eligible for a metric only when its awake count for that metric is at least 58/64. Report all counts and eligibility, including missing runs; do not shrink the three-seed denominator.

   Call this a “replicated forgetting screen,” not a significance result. Any D trigger advances experiment 20 to implementation and its own freeze; T-only triggers are a baseline note and leave 20 parked for D. Complete evidence with no trigger parks 20; missing required evidence means undetermined, not “no forgetting.” This readout cannot alter experiment 19's primary verdict, select its recipe/checkpoints, or establish recent activity as the cause. Fable's P62/P63 probabilities were written against the original trigger; preserve that provenance rather than silently relabeling them as forecasts of this amendment.

   Reason: repeated deterioration in the same skill and metric is a clearer problem for experiment 20 than unrelated drops gathered across seeds.

8. **G versus U — no change.** Keep the empirical transition sampler, 64 attempts, first-four acceptance, fixed buffers and update budgets. G represents what the learned transition counts propose under the supplied grammar and binding rules. U deliberately offers substantially more four/five-call practice. Report the actual accepted length mix in each seed; the approximate 6.5% versus 40% is not a quota or an exact finite-buffer prediction. If U matches or beats G, this recipe has shown no advantage from learned proposal statistics. A G failure remains a failure under this recipe, even if sparse long practice explains it.

   Reason: §4 explicitly registers this practical comparison, and increasing G's long-question share now would change the mechanism being tested.

**Astra's predictions are final and unchanged.** I expect the sampler to generate all four new structures without quotas. I expect G and U to improve practiced four/five-call execution more than R, but remain uncertain that final-answer-only RLOO will meet every primary mark across all seeds in 2,000 offline updates. I expect U to be competitive with G. Six-to-eight-call execution remains the hardest test, with a material risk that the stopping ceiling moves only to five. I predict no exclusive benefit unavailable to T. These qualitative forecasts were already in the draft; Fable's 0.08 is his forecast, not mine. Neither changes a pass mark.

Reviewed source identities: data builder SHA-256 `66eef57ca3c75696d2fc91d559a4374232e6180ee35a27c30479ca0280bd8bcb`; original forgetting readout SHA-256 `40ad701857247fc032bb2203ba792bb3c337264e7104afde0a2f9fca4ff33499`. Rulings 6 and 7 require corresponding implementation/registration updates by Fable before the final hash freeze; this file does not certify the pending independent audit or training implementation.

**For Ben — five lines**

Count a question separately when it is asked about a different world.  
Check the operator's old training worlds before freezing the experiment.  
Keep the fallback and no-cycle rules; fix the answer-and-ending pairing.  
Move to experiment 20 only if the dispatcher repeatedly loses the same measured skill.  
Keep G and U as designed; my predictions and the main pass marks stay unchanged.
