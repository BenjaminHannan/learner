# Premonition discovery brief for GPT-6 Astra — Ultra

Prepared 19 September 2026; revision 2. Intended configuration: **GPT-6 Astra, Ultra reasoning**, with web research and preferably repo access. Select the model and reasoning effort in the session settings; this document does not change those settings. Paste this whole document into that session, or ask a session with this repo open to read and execute it. It contains a usable evidence snapshot for a session without file access. Refresh that snapshot when files are available.

## Objective and scope

Find one buildable architectural hypothesis that could produce a substantial, generalizable improvement in Premonition's reasoning or continued learning. Seek a computational principle with a credible route to a large gain, and the cheapest experiment that could distinguish it from the strongest ordinary explanation. An important result may make an existing capability much easier to learn rather than increase theoretical expressiveness.

Be ambitious about the hypothesis and exact about the evidence. Novelty, practical usefulness, and causal understanding are three separate judgments. Do not manufacture a discovery to satisfy the request. If the best outcome is an established improvement or a discriminating experiment, deliver it honestly and explain the larger question it opens.

Choose your own research decomposition, search order, and allocation of effort. The standards below define a trustworthy result, not a mandatory itinerary. Spend depth on the most consequential uncertainty rather than on fulfilling candidate or citation quotas. You may challenge any architectural assumption that is not a stated task constraint.

This session is research and experiment design. With repo access, inspect source and existing artifacts and save the research deliverable under `reviews/`; preserve existing work. Do not launch training, run model tests, use a GPU, contact outside models, or change model code. Small calculations using the standard library are allowed. Without file access, use the supplied snapshot, label its observations as reported, and provide the complete deliverable in your answer. Never invent execution, checkpoint access, or results.

Carry the authorized research through evidence checking, alternative mechanisms, literature comparison, constructive revision, and the final experiment specification. Do not stop at an outline or the first prior-art collision. Resolve routine choices yourself, record material assumptions, and finish the deliverable without asking whether to continue. Stop when the scientific bet is concrete and reviewable, or when you can justify the diagnostic that must precede it.

Use plain language for Ben, a high-school senior. Label important claims **shown**, **suggested**, or **untested**, and identify their source. “Shown” must state the experiment's scope. Provide public arguments, equations, examples, and evidence sufficient to assess the proposal; avoid a long narrative of your brainstorming.

## Project and constraints

Premonition is a small model trained from scratch on a synthetic village whose simulator provides facts, correct answers, and evidence labels. The ambition is reasoning first, language second: better capability per total parameter and actual compute than a comparable transformer, while acquiring new skills without losing old ones. Large pretrained models must not perform its inference or supply uncounted training expertise.

The design uses a recurrent reader with minGRU and local attention, 16 entity slots, a shared Think block repeated over a small workspace, and a decoder. External fact cards have learned keys and values. The model constructs requests, fetches cards, and answers. World-specific facts should live in the designated knowledge store. Wiping that store must remove access to those facts: inspect all accessible contextual states, caches, raw diaries, slots, and other stores when designing this control. Resetting only a named tensor is insufficient if another path carries the answer.

The larger vision includes sleep, replay, a growing thought codebook, prediction objectives, a told-ledger, and transactional learning with rollback. These are revisable proposals, not demonstrated capabilities or mandatory ingredients. Brain analogies are optional. Distinguish a new fact, relation, procedure, and composition of familiar procedures.

Hardware: a laptop and one RTX 5070 Ti with 16 GB VRAM. The reported lifetime cloud cap is $30; do not assume the whole amount remains. Experiments should be small enough to develop locally, with individual training runs generally minutes to about an hour. Budget the complete comparison, including calibration, unsuccessful runs, tuning, evaluation, and any later confirmation. Use measured runtime where available. Sum of process runtimes, elapsed time for concurrent runs, and exclusive GPU time are different quantities.

## Evidence snapshot: refresh before drawing conclusions

These observations concern separate experiments. Do not merge their scores.

**A. Retrieval ladder.** Synthetic token vocabulary; six people, three attribute relations, and friend links. People are reassigned arbitrary ENT0–15 tokens each visit. Training contains one-hop questions for all relations and two-hop questions for two relations; the third relation is withheld from two-hop training. The current diagnostic arm is `bypass-k1`: one card per request, four Think loops, and a decoder path using card rows from before Think. It is not simply the default full model.

The ladder uses `d_model=32`, `key_dim=16`. The repository's static parameter formula gives **79,748 parameters** for this configuration and **80,293 with the relation shortcut**. These are calculated counts, not a new checkpoint measurement. The approximately 2M size refers to a larger configuration, not this ladder run; verify actual counts before a comparison.

The writer pools each fact line once, feeding that pooled vector to both key and value projections. The request is projected from workspace register 0. A marginal set loss supervises retrieval using still-missing gold evidence; the top-card choice is discrete and detached. The early gold-card phase has answer and language losses, with ASK and HALT weights zero.

The relation shortcut adds `sigmoid(g(register0)) * W_r E[relation]` to the request. It adds 545 parameters. `W_r` starts at zero; the gate logit starts at zero, so its sigmoid is initially 0.5, not zero. The contribution is initially zero because `W_r` is zero. The relation is located by the synthetic question layout, a disclosed structural hint.

The 12,000-requested-step comparison is complete locally, replacing the older “pending” statement. Actual reported stops are 12,250–12,251 steps. Validation, all five seeds in order:

| Condition | Own one-hop /512 | Own practiced two-hop /341 | Own held-out two-hop /171 | Oracle-card practiced /341 |
|---|---|---|---|---|
| Baseline | 115, 512, 512, 512, 489 | 84, 341, 341, 340, 341 | 6, 13, 88, 18, 12 | 341, 341, 337, 341, 332 |
| Relation shortcut | 506, 99, 92, 512, 473 | 339, 69, 75, 338, 257 | 171, 32, 35, 170, 132 | 341, 341, 341, 323, 306 |

Own-retrieval numbers above use `fixed_K4`; oracle reading uses `gold_read_K2_no_fetch`. Do not silently substitute a different loop or halting policy. The prior advancement rule required oracle reading ≥307/341, practiced ≥171/341, and held-out ≥86/171 together in at least four of five runs. The shortcut met all three in **two of five**, so it did not pass that rule. Its three runs that learned retrieval had strong held-out results, but selecting only successful runs would hide reliability cost. Five runs do not establish whether the shortcut increases the stuck rate.

Later checkpoint probes found that stuck runs selected the correct card family but the correct person only about 15–18% of the time, near 1/6. Linear probes decoded person identity from the reader's person-token state but were near chance on card keys in those runs. In learned runs, keys supported nearly perfect decoding. Failed linear decoding does not prove information is absent, and successful decoding does not prove causal use.

Rescoring frozen similarities at different positive temperatures did not rescue stuck retrieval. This tests inference on those frozen representations; it does **not** rule out a role for temperature in training. Low attention weight on a person token also does not establish information loss, since later recurrent states can carry that identity.

Oracle-card success here has a limited interpretation: only one of the two correct cards contains an attribute value. Extracting that value can succeed without demonstrating general binding or composition. This control helps localize retrieval failure but does not certify reasoning mastery.

**B. Supplied-card choosing.** A separate answer-only task included look-alike distractors. Address-based selection, supplied with the person/relation token positions, improved validation choosing from 164 to 503 of 512 on one seed and 161 to 467 on another. Fresh examples supported that improvement. This is a two-seed result with structural assistance; it did not solve two-hop combining. It is not a matched demonstration that raw-text address discovery has been learned.

**C. Village-language model.** A separate approximately 4M transformer was reported at about 23% held-out and 44% familiar accuracy. Wording and answer-token training were identified as obstacles. Do not use these scores as the baseline for the retrieval ladder.

No continual-learning success or catastrophic-forgetting measurement is established by A–C. Design an explicit task before diagnosing that part of the project.

### Repo entry points, when available

Read targeted sources rather than every historical review. Record source paths, relevant configuration, artifact timestamps, and unresolved mismatches. Saved raw outputs and the code actually used outrank prose summaries.

- `CLAUDE.md`; `design/06-premonition-mini-spec.md` for intended behavior.
- `artifacts/claude-long-20260919/REPORT.md` and `runs/*.json` for the long baseline.
- `artifacts/claude-relcut-long-20260919/REPORT.md`, `STUCK_PROBE.md`, `runs/*.json`, `person_probe.json`, and `stuck_probe.json` for the shortcut and probes.
- `scripts/premonition_ovn_ladder.py` for frozen-source bootstrapping; `scripts/premonition_ovn_retrieval.py` for the evaluation definitions; `scripts/premonition_gpu_port.py` for training switches.
- `scripts/premonition_relation_shortcut.py`, `scripts/premonition_key_pool.py`, and `scripts/premonition_person_probe.py` for implemented changes and probe scope.
- `archive/opus-ovn-20260918-235851/frozen/premonition/` for the base source imported by these experiments. Inspect imports before assuming a live-file edit would affect the experiment.
- `reviews/opus-milestone-03-address-confirm.md` for the separate address-selection evidence.

Look for newer completed results and pending runs. A separate key-pooling scorer is already implemented locally; do not present it as a new invention or assume it succeeded because it exists. If an expected result is absent, record “not found locally,” not an inferred outcome.

## Research standards

### 1. Establish the scientific question

Write a short table: observation, at least two explanations, and an observation that would distinguish them. Include data, objective, optimization, curriculum, structural hints, and evaluation mistakes alongside architecture. Distinguish a path that cannot represent information from one that fails to preserve, learn, align, or use it. For each proposed intervention, say exactly what causal claim it can and cannot test.

Identify the most promising unnecessary computational burdens. Keep questions about both current reasoning and learning across tasks or episodes in consideration. Preserve a high-upside direction beyond the current retrieval plateau, even if it requires defining a capability the current benchmark does not test. The plateau is a useful instrument, but fixing it alone need not fulfill the discovery objective.

For each question, define a small **task family**, not just a single score: vary one relevant burden such as distractor count, composition depth, delay, number of independently varying roles, or number of skills learned sequentially. Identify an easy case where ordinary methods should work and a harder case where the hypothesized difference should appear. Ensure the data actually require the claimed operation; include the strongest cheap shortcut or trivial solver as a diagnostic ceiling.

### 2. Generate mechanisms before group critique

Use internal research subagents if available, starting each with the neutral project facts and a different computational question. Do not give initial inventors the lead's favored answer, the historical success stories, or the long prior-art inventory below. Retain their awareness of literature; withholding a supplied list does not make them independent scientists. If unavailable, use distinct passes and acknowledge that limitation. Do not contact outside people or models.

Choose assignments that investigate different computations rather than adopt different personas. Possibilities include simplifying a representation operation, removing a conflicting dependency, or changing what must be learned and retained. A separate critic should defend the strongest simple existing solution.

Generate materially different mechanisms before selecting one, including alternatives for learning over time. Deduplicate by computation, not names; choose the useful breadth yourself. Prioritize architecture, while keeping an objective or training-schedule explanation competitive if it solves the actual burden.

Each candidate needs a compact record: burden and assumption changed; state and update rule; learning signal and inference; one worked example; an observation on which it differs from its closest ordinary alternative; likely failure. Delay evocative names. Seek one coherent mechanism; if two pieces are necessary together, explain that dependence and propose a small factorial test rather than excluding the combination automatically.

### 3. Derive a prediction with consequences

For the strongest two candidates, give a minimal computational example or algebraic argument. Show what the baseline must do, what the proposal makes easier, and which cost or learning dependency changes. This can be an optimization or statistical argument; a formal lower bound is not required. Mark assumptions explicitly.

Predict a pattern across the task family, including a condition where the advantage should shrink, disappear, or reverse. “It should improve accuracy” is insufficient. A useful mechanism might change sensitivity to distractors, dependence on examples per combination, or retention as skills accumulate.

Give a modest first-test prediction separately from the ambitious payoff. A tenfold claim must define its numerator, denominator, target quality, and assumptions. Do not turn trainable-parameter savings into total-memory savings, or a tiny baseline into a large ratio. Explain a credible second experiment in a different surface task or regime that could show the principle travels beyond the village template.

### 4. Audit novelty precisely, then select

Search primary papers and current work through the actual current date, including older origins and equivalent formulations across fields. Search state, operations, learning rules, and dependencies rather than a proposed name. Open methods for close matches; an abstract or search snippet cannot settle identity. Record what could not be verified.

For each serious candidate classify the closest work as the same central mechanism, a shared ingredient, or a substantive unresolved difference. Check whether the difference survives renaming variables. Retain rediscovered useful methods as baselines. Give promising candidates a bounded constructive revision that changes computation or sharpens a prediction. Do not force a surviving invention.

Known territory to consult at this stage includes memory networks and key–value retrieval; MAC-style control/memory separation; Neural Production Systems and Local Module Composition; pointers, copying, and stage-dependent gates; recurrent or looped reasoners and adaptive halting; entity slots and tensor-product or holographic binding; VQ/FSQ and growing ART-style codebooks; JEPA and latent reasoning; fast weights, delta-rule memory, Titans, DeltaNet, and test-time training; program induction and library learning; complementary learning systems, replay, consolidation, model merging, shrink-and-perturb, and multi-timescale optimization; curiosity, curricula, hints, self-training, and verifiable-reward RL. The project's told-ledger, transactional sleep, consolidation pressure, paired interventions, ordered evidence supervision, and separate key pooling are also already considered. Components from this list are allowed; novelty must reside in a substantive difference.

Select by plausible impact, explanatory specificity, informative testability, total cost, and provisional novelty. Do not rank by persuasive prose or fabricated confidence percentages. If two explanations remain observationally indistinguishable, choose the test that separates them before committing to an architecture. Return the chosen hypothesis provisionally if no discriminating observation is yet available.

### 5. Produce an experiment an engineer can execute

Specify a development-only feasibility check and a frozen comparison. Do not run them in this research session.

- **Controls:** one mechanism change against the strongest relevant established baseline, with comparable tuning. On the present ladder, the long-trained relation shortcut is a necessary comparator for improvements to held-out retrieval, with its structural hint disclosed. A vanilla transformer is a useful broader comparison, but cannot replace the closest competent baseline. Include an ablation that isolates the claimed new part. If better curriculum or a known method could explain the gain, give that alternative a fair test.
- **Information:** match input access, parsing hints, supervision, pretraining, replay, and simulator calls. Count internally generated practice. “Told once” must report total subsequent examples and updates. Diagnostics with an oracle must not silently become the proposed inference algorithm.
- **Primary outcome:** name one primary metric and exact numeric advancement, retention, and failure thresholds before observing results. Justify them against baseline variability and useful effect size. Avoid selecting whichever of several metrics improves.
- **Replications:** use five matched training seeds as the minimum comparison screen. Report all seeds, failed runs, and stopping rules. Pair unchanged initialization/data where possible. Five is not automatically enough to establish a rare-failure rate; design an appropriately powered follow-up or narrow the claim. Report variation across training runs separately from variation across test worlds; multiple questions from one world are not independent replications.
- **Evaluation:** protect both structural training exclusions and fresh confirmation data. Freeze the confirmation generator, split, and analysis before use. An independent evaluator may hold the test seeds; otherwise document the freeze. Track which benchmarks have already influenced decisions. Fresh entities alone are not a new composition. Replay, counterfactual training, teacher labels, and sleep must preserve withheld structure.
- **Mechanism:** specify the discriminating intervention, negative control, expected outcomes under competing explanations, and which outcome defeats the causal account even if accuracy improves. A synthetic activation patch can be off-distribution; acknowledge that limit and prefer corroborating input interventions where feasible.
- **Continued learning, if claimed:** use A→B, measure acquisition of B and retention/continued access to A, and include a matched replay or established retention baseline. Keep a separate audit set outside any sleep acceptance/rollback checks. Count router and retrieval failures as forgetting when the skill is no longer usable. Add further tasks only after this initial test works.
- **Resources:** report total/trainable parameters, persistent state and external storage, peak VRAM, actual training and inference time, teacher/search/sleep costs, and the whole experiment budget. For unreliable training, include cost to obtain a usable model under a preregistered restart policy. State how cost matching is performed and disclose remaining differences. Do not compare unequal resources and call it efficiency.
- **Decision:** give an outcome-to-next-action table for efficacy plus mechanism support; efficacy without mechanism support; no efficacy despite a working implementation; and an invalid or inconclusive experiment. Distinguish rejecting this implementation, its causal explanation, and an entire architecture family. Permit one bounded diagnostic revision; prevent endless tuning on the confirmation set.

## Required deliverable

Lead with the candidate's precise contribution, novelty status, and most consequential uncertainty. Then provide:

1. The refreshed evidence table and any corrections to this snapshot.
2. A compact candidate table; detailed records only for the strongest two.
3. The selected idea in three plain sentences, followed by state, computation, learning signal, inference, a worked example, and its distinctive task-family prediction.
4. The closest three to five verified prior works and the exact remaining difference, with links to methods supporting the comparison.
5. A build map naming the repo modules/interfaces to change, what remains shared with the baseline, and what this makes unnecessary. Without file access, name interfaces rather than pretend to know line numbers.
6. The preregistered experiment, resource budget, outcome-to-next-action table, and second-stage transfer test.
7. A brief runner-up and an established fallback. Explain the best reason to prefer the fallback.

Keep the final brief compact enough to guide a build. Save detailed evidence or literature notes separately if needed. Completion means one inspectable scientific bet or a clearly justified diagnostic; it does not mean a breakthrough has occurred. Historical examples motivate the method but do not establish its success rate.

**Central instruction: Find a burden that the formulation unnecessarily imposes, derive a comprehensible way to remove it, and predict both where the change should help and where it should fail. Make the first experiment capable of changing our mind.**
