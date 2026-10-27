# Reasoning research, 2026-09-24 (reasoning research thread)

Two parts:
- **Part 1**: the main research report. Four search lanes ran: picking answers, learned reasoning, programs over the notebook, and brain-inspired methods. A skeptic agent checked each lane's sources and repo claims, and a final agent wrote this up, weighted toward scale-up.
- **Part 2**: a follow-up on Ben's 19:23 asks about our own loop reasoner: choosing its own number of steps, learning rules, real-world training, MiMo v2.6's RL recipe, and a teacher model.

Nothing here was trained or run. No repo code was changed.

The thread session checked these claims against the repo before this was saved:
- LoopThinker (scripts/claude_rsn294_core.py:484-503);
- random 2-12 passes and final-pass-only loss (scripts/claude_rsn294_run.py:75-83);
- loop-s2 dev 916/1200 at both 6 and 12 passes, with three-step at 0 (artifacts/claude-rsn294-20260923/runs/loop-s2/dev-final.json);
- 299b vote_key keys a date by its first number (scripts/claude_rsn299b_run.py:36-54);
- the r031, r047 and r054 stored samples (artifacts/claude-rsn299b-20260924/run/panel-V.jsonl).

Every other claim carries the label its author gave it.

# Premonition reasoning: research report and scale-up path (2026-09-24)

Labels: **shown** means checked in this repo (file path given). **suggested** means published, and the paper text was read. **abstract-only** means only an abstract or search snippet was read. **untested** means our own estimate. Where a skeptic corrected a claim, the corrected version is used.

Two tracks are kept apart throughout:
- **Card-style bench:** generated episodes, the ~30M from-scratch net and the 1B think path, each scored on sealed blind panels.
- **Village agent:** the full assistant, meaning the notebook plus the 1B plus routing.

Nothing below has been tested on the village agent. Evidence from the bench is not evidence about the agent.

---

## 1. For Ben

1. Doing arithmetic is not what holds Premonition's reasoning back. The weak spot is **picking the right answer**. In the last test, at least one of its 5 tries was right on 48 of 60 questions, but the vote got only 38 right.
2. The second weakness is **setting problems up wrong**, for example adding the wrong numbers together. A calculator can't catch that.
3. Our small home-grown net still **cannot compare two numbers**. Its looping version, which re-runs the same layers to "think longer", has **never trained properly**. So we don't yet know if thinking longer helps it.
4. **Move 1:** give the model a learned "feeling of being right". This is a *verifier*: a small add-on that scores each try. It is trained during sleep on practice problems where code already knows the answer, and it says "not sure" when no try scores well.
5. **Move 2:** let the model write tiny programs that look facts up in the notebook. Exact code runs them, and it says "I don't know" when a fact is missing, so it can't make one up.
6. **Move 3:** fix the loop net's training before making it bigger. First a free check on saved copies of it, then a run costing about $1.
7. What the research says about scaling up: in one study, making the checker bigger helped more than making the solver bigger. Loop models have matched models about 4 to 8 times their size, but only with careful training settings that ours is missing.
8. The affordable way to give a loop net language is to **add a loop inside the 1B**. Training a big loop model from scratch would take thousands of GPU-days.
9. **Don't:** pay for reinforcement learning (trial-and-error training) on the 1B yet, make the small net bigger before it can copy, or train anything on the old test panels.
10. Expect small steps: each move will probably gain a few questions out of 60 to 120, and most of the scale-up story is untested for Premonition.

---

## 2. What the repo results already tell us (all shown)

**Hand-written reasoner** (`scripts/fable_reasoner50.py`): exact lookups and multi-hop chains, with 0 reasoning errors. It cannot count, compare or reason about time.

**30M from-scratch reasoner** (294, 296, 296b; `design/v3/30-modes/294-learned-reasoner-plan.md`, `296-sleep-school-practice.md`, `296b-told-after-miss.md`):
- **Style overfit.** It scored 100/100 on practice-style items but only 6 to 30 of 30 on blind notebooks (`design/v3/30-modes/294-idea-check-5-14-16.md` line 30).
- **Comparing sits at chance, even when told the answer:** 93 and 88 of 200, and 13 and 16 of 30 on the fresh panel (`artifacts/claude-rsn296b-20260924/VERIFY-director.md`). 296 made "one fixed pick" (`artifacts/claude-rsn296-20260924/DIAG-director.md`).
  - Compare is not in COPY_KINDS (`scripts/claude_rsn294_run.py` line 42).
  - The compare label is an XOR of "A's number is bigger" and "the question says less". Each part on its own is uncorrelated with the answer (`scripts/claude_rsn294_core.py` gen_episode).
  - WHO answers are read from one summary token, `self.fixed(cls)` (Heads.forward).
- **Counting.** It learned once told after a miss: fresh 12 to 29 of 30, and counts 1-7 at 200/200. Counts 8-12, which were never practised, scored 0/200 (296b VERIFY).
- **Three-step questions:** 0 in every run.
- **Before/after:** 134/134 with 2 dated facts, but 131/266 and 157/266 with 3-4 dated facts (`artifacts/claude-rsn296-20260924/DIAG-director.md`). 296b made it worse.
- **The loop net failed the copy phase:**
  - 294 seed 1: copy loss about 1.0 from step 1,000 to 6,000. Seed 2 reached 0.12, and plain reached 0.002 (`artifacts/claude-rsn294-20260923/VERIFY-director.md` D2).
  - 296 loop: 1.85 and 1.97 on both seeds (`artifacts/claude-rsn296-20260924/VERIFY-director.md` D3).
- **Cost:** 296b spent about $0.60 for 2 plain seeds on one rental. Rental credit was about $5 on 2026-09-24 (296b VERIFY).

**298** (`298-branching-middle-hop.md`): 39/60 against a bar of 48, with 0 wrong.

**299** (`299-think-then-answer.md`, `artifacts/claude-rsn299-20260924/VERIFY-director.md`):
- The plain 1B scored 28/60 and the calculator arm 32/60, against a bar of +12. FAIL.
- There were 0 arithmetic errors. The 24 misses both arms shared were all setup errors.
- Neither arm said "not sure" on the 6 missing-fact items (0/6).

**299b** (`artifacts/claude-rsn299b-20260924/VERIFY-director.md`, `RESULTS.md`, `run/panel-V.jsonl`):
- The 3-of-5 vote scored 38/60 against plain's 28, a FAIL against the +12 bar. Wrong answers fell from 29 to 10, and it said "not sure" on 5 of 6 missing-fact items.
- Sample 0 alone got 33/60. At least one sample was right on 48/60.
- 11 of the 16 no-majority rows held a right sample.
- In 3 rows a right minority lost to a wrong majority: r031 1 vs 3, r047 2 vs 3, r054 1 vs 3. No counting rule can fix these.
- Samples average 111 characters.
- The vote took 6.27 s per item against plain's 0.965 s.
- **Vote-key defects:**
  - Dates are keyed by their first number, so 'March 3' and 'May 3' count as the same answer.
  - Text answers are not merged, so 'green' and 'green train' count as different answers (vote_key in `scripts/claude_rsn299b_run.py`).
- The 1B rarely says "not sure" itself. The sealed judge scores 6 of the 300 samples as unsure, and 21 mention the words anywhere (my count).

**Notebook contract** (`scripts/fable_notebook_contract.py` lines 224-255):
- It has no field for when something happened. `n` is the order rows were written.
- `current()` drops superseded rows.
- So "where did Ana live before Oslo" has nothing to read from.

**Takeaway (shown):** the 1B can already *generate* the right setup far more often than it *commits* to it. The 30M net's failures are learnability and training failures (comparing, looping), not a lack of practice.

---

## 3. Reasoning at scale-up

### 3.1 What the literature says emerges with size and RL

- **Test-time compute pays off where the base model already succeeds sometimes.** A compute-optimal strategy beat a 14x larger model on such problems (Snell 2408.03314, abstract-only). Our 1B is in that regime (pass@5 48/60, shown).
- **Verifiers scale well.** At 1.3B, growing the verifier from 125M to 1.3B gave +7.2 points, against +5.1 for growing the generator (TinyGSM 2312.09241, suggested). Self-evaluation improves with size, but it is poorly calibrated zero-shot (Kadavath 2207.05221, suggested). At 13B and below, a weak self-verifier limits gains (2404.17140, suggested).
- **RL mostly sharpens what the base already samples**, and coverage narrows at large k (Yue 2504.13837, suggested).
  - Prolonged RL (2,000+ steps, about 16,000 H100 hours, 136k diverse problems) starting from a distilled 1.5B reports strategies the base could not reach (ProRL 2505.24864, abstract-only).
  - RL composes new skills only after the atomic skills are mastered by supervised training. Supervised training on the composite task alone reached 90% on seen facts but 18% on novel ones (2512.01970, abstract-only).
  - At small and mid scale, distillation from a stronger model beats RL (DeepSeek-R1 2501.12948, abstract-only via search result). Models of 3B and below learn better from short chains (2502.12143, abstract-only).
  - Spurious-reward gains are mostly specific to Qwen (2506.10947, suggested). MiniCPM5-1B is Llama-style.
- **Looped (recurrent-depth) models:**
  - Huginn, 3.5B trained on 800B tokens, improves with more recurrences at test time (Geiping 2502.05171, suggested for its training details; its "up to 50B-equivalent compute" claim is abstract-only).
  - Ouro, at 1.4B and 2.6B on 7.7T tokens, matches models up to 12B. The authors attribute this to better knowledge manipulation rather than more knowledge capacity (2510.25741, abstract-only). Notebook reasoning is exactly manipulation of given facts.
  - A looped model can be built from a pretrained model by adding recurrence with a curriculum of loop counts (McLeish 2511.07384, abstract-only).
  - Qwen2.5-0.5B was retrofitted with a weight-tied recurrent block (2608.11233, abstract-only). With per-step supervision it computed one task step per loop, and a 6M-parameter adapter over frozen weights matched a 180M full block (83.8% vs 84.0%). It extrapolated to about 1.5x the supervised depth, while a same-size scratchpad model collapsed beyond its horizon. Learning the reverse rule afterwards caused catastrophic interference.
  - Loops help compositional tool calling (2608.18171, abstract-only).
- **Programs over structured data.** Big models gain a lot (Faithful CoT 2301.13379 and SatLM 2305.09656, both at code-davinci-002, suggested). A 1B needs supervised fine-tuning to write queries well: 30.8% on Spider untuned with 16-sample self-consistency, 63.8% after large supervised fine-tuning (SLM-SQL 2507.22478, suggested).

### 3.2 Which ideas get stronger or weaker with a bigger model

| Idea | With a bigger base model | Label |
|---|---|---|
| Learned verifier ("feeling of rightness") | Stronger. Verifier size pays off more than generator size (TinyGSM) | suggested |
| Majority vote | Less headroom as pass@1 approaches pass@k | untested |
| Programs + exact executor | The parser gets better; the executor's guarantee stays at any size and matters more as the notebook grows | suggested (parser), untested (notebook growth) |
| Sleep replay (RFT) | Smaller gain per round ("better models improve less"; 33B gained nothing), but it becomes the supervised stage that RL needs | suggested / abstract-only |
| RL practice | Useful only after atomic skills and a good starting model exist | abstract-only |
| Looped depth | Stronger if stable, but harder to train at scale (norm and learning-rate failures) | suggested |
| Prompted self-check | Improves with size; weak at 13B and below | suggested |
| Hand-picked confidence features | Weaker relative to learned verifiers | suggested (8B evidence) |
| 30M compare fixes | Unaffected by LM size; they matter for growing our own net | untested |

### 3.3 Recommended architecture (untested)

Neither a pure learned reasoner nor pure programs. Instead there are three parts, all trained by sleep practice with exact labels:

1. **A learned parser/planner.** The LM writes steps or a notebook program. Later this LM carries a retrofitted loop.
2. **An exact executor over the notebook.** It runs cited reads, counts, comparisons, arithmetic and dates, and returns the contract's statuses (OK, MISSING_FACT, AMBIGUOUS, UNKNOWN_ENTITY, BROKEN_CHAIN). This keeps facts exact at any scale.
3. **A learned verifier.** It scores each candidate and gates the answer with a calibrated "not sure".

**Where our own loop net fits:** it is a learned hop engine over notebook rows. It proposes a chain by pointing at rows on each pass, and the existing code fact-check accepts or rejects the chain (`claude_rsn294_core.supported`, shown).

**Why this split:**
- The notebook rule forbids facts in weights.
- RL does not create atomic skills (abstract-only).
- Our 30M evidence shows learned parts overfit their generator (shown).
- Programs alone leave parse errors uncaught, and they are not the brain-like part Ben wants. The verifier and the loop net are.

**What is novel:** a verifier trained during sleep on exact self-labels, a provenance gate that traces every literal to its source, and a loop reasoner whose every pass must point at cited rows.

### 3.4 Growing our own loop reasoner

**Why the looped version failed the copy phase.**

Shown in `claude_rsn294_core.py` LoopThinker and `claude_rsn294_run.py`:
- d=1024 with 2 layers, which is about 30M parameters.
- Pre-norm layers (`norm_first=True`).
- `inject = Linear(2d,d)` on an un-normalised state, plus a step embedding.
- No norm on the state between passes.
- Learning rate 3e-4.
- A random 2 to 12 passes per step, with full backprop through up to 24 layer applications and loss only on the final pass.

This is close to Geiping's "Bad Run 2" (pre-norm plus a learned adapter), which "learned early to ignore the incoming state" (suggested). Their fix, read in the paper text, was:
- a sandwich norm around attention and MLP;
- an RMSNorm on the core block's output;
- a concatenation adapter;
- truncated backprop through only the last k=8 iterations;
- iteration counts drawn from a log-normal Poisson distribution;
- the peak learning rate cut from 4e-4 to 4e-5.

They also say that at small scale all normalisations worked, so at 30M this may not be the cause (untested). Other candidates are state-norm blow-up across passes and the random pass count with only one supervised output (untested). The $0 gate in Proposal C tells these apart.

**Growth ladder.** Costs are untested and scaled from 296b's measured ~$0.60 for 2 plain 30M seeds. Cost grows roughly with parameters x steps x passes, and truncated backprop caps the backward cost. The rate is about $0.5/h on a 5090.

| Stage | Size | What changes | Gate to move on | Cost |
|---|---|---|---|---|
| 0 | 30M (existing) | Nothing is trained. On the kept 294/296 checkpoints, measure cross-row cosine, state norm per pass, and answer change between 2 and 12 passes | Diagnosis recorded | $0 (CPU; checkpoints must be fetched) |
| 1 | 30M | Make it trainable (Proposal C) | Copy loss ≤ 0.05 on both seeds | ~1.5-3 GPU-h, $0.8-1.5 |
| 2 | 30M | Hop ladder 1-3 in practice, passes tied to hop count (Fan 2409.15647, abstract-only), pass k supervised to point at the hop-k row (from 2608.11233, abstract-only; untested here); test on 4 hops, never practised | Trained hops ≥ 90%; 4-hop clearly above 0 and rising with passes | ~2-3 GPU-h, $1-1.5 |
| 3 | ~100M (e.g. 4 shared layers, d=1536) | Size only | A capacity signal from stage 2 (accuracy falls with notebook size or depth while training loss plateaus) | ~4-8 GPU-h per seed, $2-4 each; one seed per $4 job |
| 4 | ~300M | Size only | 30M to 100M gave a clear gain | ~$8-15 per seed-run; beyond this month |
| 5 | Retrofit inside MiniCPM5-1B | Prelude, a shared recurrent block with a small adapter, and a coda, using the stage 1-2 recipe | Stage 2 passed | ~2-8 GPU-h, $1-4 per run (untested) |

**Should it grow out of the 1B? Yes, eventually.**
- The from-scratch net reads encoded frames, not English. Teaching a looped model language from scratch took 800B tokens (Huginn) and 7.7T tokens (Ouro). That is thousands of GPU-days, far outside our budget (untested order-of-magnitude estimate).
- The 30M net stays useful as the cheap lab where the recipe is debugged (norms, truncated backprop, per-hop supervision, pointer readouts). It can also serve as a frame-level hop engine.
- The product path for English is stage 5.
- Watch for the interference limit: in 2608.11233, learning a second rule afterwards broke the first (abstract-only).

**Data and rewards:**
- Structurally varied generated episodes with fresh symbols (the 296 lesson, shown).
- About 30% missing facts, plus corrections that supersede earlier rows.
- Atomic skills first by supervision: lookup, count, compare, dated before/after. Composition comes later by practice (2512.01970, abstract-only).
- The 294 code fact-check reward (shown in `claude_rsn294_core.py` reward: a wrong try costs the same as "I don't know" when the fact exists, and inventing is punished hard).
- Told-after-miss (shown to teach counting).
- Loop-ladder self-training on the real notebook, only once the rung below is solved (294 idea-check verdict, shown).

**How it uses the notebook:**
- Rows are tokens it re-reads on every pass (shown).
- Answers are row pointers plus support bits, which serve as citations (shown).
- The fact-check rejects unsupported answers (shown).
- When the notebook outgrows the context, a retrieval step picks the top-k rows first (untested).
- Facts never go into weights.

**The small experiments that de-risk this path now:**
- Proposal C, stages 0-1: about $1, and the loop can't grow until it passes.
- Proposal A: its verifier carries over to any future generator.

---

## 4. Ranked proposals (ordered by value for scale-up)

Cheap now: A (≤ $2.5), B ($0), C ($0 gate, then about $1), E (about $0.1 diagnostic, then $0.5-0.8). D costs $1.5-2.5.

Also kept, but not ranked because its expected panel effect is about 0: **count by pointing**.
- **What:** a $0 CPU re-evaluation of the 296b checkpoints on `scripts/claude_rsn296_diag.py` count episodes 1-12, reading count = the number of support bits above 0.5.
- **Marks:** counts 8-12 ≥ 150/200 and counts 1-7 ≥ 190/200. It is proved wrong below 50/200.
- **Needed:** a rule for count 0 vs UNKNOWN. Report support precision and recall.
- **Honesty note:** the per-row choice is learned, but the sum is fixed code.

### A. A learned "feeling of rightness" that picks among the 1B's own samples (bench: 1B think path)

**What.** Train a Yes/No LoRA verifier on MiniCPM5-1B. It reads (question, one calculator-filled chain) and outputs P(Yes).
- Candidates are grouped by a fixed answer key, and each group's weight is the sum of its P(Yes) scores.
- The top group is answered if it clears tau. Otherwise Premonition says "not sure".
- Pre-registered fallback: say "not sure" if the top score is below tau AND the samples have no majority. This keeps the vote's free abstentions on missing-fact items.
- Training data: the 1B's own samples on program-generated practice, about 40 families across ARITH, TIME, COUNT, COMPARE, PLAN and UNSURE, labelled exactly by code. Samples are drawn at several temperatures. The bank must include missing-fact items.

**Evidence.**
- TinyGSM (suggested): 68.2% to 81.5% with a 1.3B verifier choosing among 48 samples. That verifier was trained with full fine-tuning on about 7.4k x 48 ≈ 355k GSM8K-train samples, which is about 30x our planned bank. Full fine-tuning "significantly outperforms" training only the head.
- V-STaR (suggested): its DPO verifier beats majority voting at k up to 64. But its classifier-style (pointwise) verifiers fail to search above 4 candidates, and we use 5.
- RL^V (suggested): the weighted vote beats majority only at 8 or more samples.
- GenRM (suggested): a direct Yes/No head is only "comparable or slightly better" than a discriminative verifier.
- Orgad (suggested): a hidden-state probe beats majority in-distribution at 7-8B with K=30 (e.g. 0.57 to 0.70), but probes transfer poorly across datasets.
- The gain at 1B with N=5 is untested.

**Targets.** The picking bottleneck: 48/60 reachable, 38/60 taken, 3 wrong-majority rows (shown).

**One change.** decide() is replaced by the verifier-weighted vote on the SAME stored samples. Conditions:
- The vote_key fix (dates and names) is applied to both arms, and V is re-scored first.
- tau and the wrong cap are set only on held-out generated families.
- The cap must be realistic. V's wrong rate among the answers it gave is 10/48. The repo's Learn-then-Test method returned ABSTAIN-ALL at a 2% cap (`design/v3/30-modes/69-abstention-ltt-on-rung1-muse.md`, shown).

**Dev gates (before any panel), fixed now.**
- AUROC ≥ 0.80 on held-out families.
- Writer-shift check: train on bank author A, test on an independent author B, AUROC ≥ 0.70.
- Report-only rows on the same held-out families: a hidden-state logistic probe (lane 4 idea 1) and a free-signal logistic (lane 1 idea 2). If the probe comes within 0.02 AUROC of the LoRA head, the probe is registered instead, because it is cheaper.
- Re-picking the burnt 299b samples is a sanity check only.

**Test.** A fresh blind 120-item panel with 299b's category mix, written and key-audited by fresh agents.

**Pass marks.**
- W right ≥ V right + 8.
- W wrong ≤ V wrong.
- Missing-fact "not sure" ≥ V's − 1.
- Also report a sign test on the rows that changed.

**Proved wrong if:** W right ≤ V right + 2, or panel AUROC < 0.65.

**Cost.** About 12k samples: roughly 5.3 h on BensPC ($0), or $1-2 rented. LoRA under 20 min. Total ≤ $2.5 (untested).

**Expected.** Untested: +2 to +7 of 120, with about a 30-40% chance of meeting +8.

**Novelty.** Low to moderate as a method. Ours: sleep-trained on exact self-labels, gating a three-way choice between answer, "not sure" and missing fact.

**Risks.**
- Generator-style overfit (the 294 D1 lesson).
- LoRA vs full fine-tuning.
- Too little data (Cobbe 2110.14168: verifiers don't help at small data sizes).

**Village.** Only after a pass, as a separate registered step. It adds 6.5x latency (shown).

### B. Notebook programs with a provenance gate (bench: 1B plus executor)

**What.** The 1B writes a short program over the pasted rows: read, count, compare, nested reads, date and number arithmetic, and 299's clock and weekday operations. An exact executor runs it over `Notebook.current()`. An answer is accepted only if all of these hold:
- it runs;
- every read returns active, cited rows;
- every literal traces to the question or a cited row;
- an empty read becomes MISSING_FACT, never 0.

Otherwise the reply is the contract's "I don't know" template. Before/after is limited to rows that store a date as a value (the contract has no event time, shown).

**Evidence.**
- Faithful CoT (suggested): CLUTRR 45.7 (CoT) vs 71.9 with self-consistency over executed programs.
- SatLM (suggested): wrong answers 21.0% to 7.7% when a solver can refuse.
- All of the above at about 175B.
- SLM-SQL: a 1B needs supervised fine-tuning to write queries well (see 3.1).

**Targets.**
- Comparing at chance (shown).
- 3-step at 0 (shown).
- 0/6 refusals (shown).
- No working path for "how many years older is Ana than Bo": the inner loop cannot count or compare (299 doc lines 21-25, shown).

**One change.** Output form plus executor, against 299's T arm on the same rows and the same 10 worked examples (rewritten as programs). It bundles three things (language, executor, gate); this is stated openly. Report-only baselines: the 299b vote, and `fable_reasoner50` on the chain items.

**Dev gate.** At least 90% of dev programs parse and run, else stop.

**Test.** A fresh blind 60-item "progpanel": 10 each of COUNT, COMPARE, dated BEFORE/AFTER, ARITH on stored numbers, 3-STEP, and MISSING.

**Pass marks.**
- B − A ≥ +12 overall, and ≥ +6 excluding MISSING.
- B wrong ≤ 4.
- MISSING "I don't know" ≥ 8/10.
- 3-STEP ≥ 7/10.

**Proved wrong if:** B − A < +6 overall, or ≤ 0 excluding MISSING, or B wrong > A wrong.

**Cost.** About $0 on BensPC, about $0.3 rented, plus about half a day of builder time.

**Expected.** Untested: +10 to +18 overall, but only +3 to +10 excluding MISSING.

**Novelty.** Moderate as a guarantee: "never invents a fact or a constant" becomes checkable by code.

**Risks.**
- Weak few-shot format skill at 1B. A special format already hurt the 1B at 299 dev2/dev3 (shown).
- A misparse onto a real row gives a confident, cited, wrong answer.

**Scale-up role.** The backbone. It becomes the object that A verifies.

### C. Make our own loop reasoner trainable (bench: 30M)

**What.**
- **Stage 0 gate ($0)** on the kept 294/296 loop checkpoints: cross-row cosine, state-norm growth per pass, and answer change between 2 and 12 passes.
- **If the gate shows collapse, blow-up or an ignored state:** the registered change is Geiping's stabilisation. This is a sandwich or normalised inject plus a lower learning rate. It is a bundle because the published fix was a bundle, and this is said openly.
- **Otherwise:** the registered change is an answer and support loss after every pass, averaged. This is iteration-level supervision inspired by TRM. It is not TRM's detached deep supervision, which is a separate later option.

**Evidence.**
- Geiping (suggested, read, see 3.4).
- TRM 2510.04871 (suggested): 87.4% on Sudoku-Extreme; the 1-step gradient ablation gives 56.5.
- Saunshi 2502.17416 (abstract-only): a k-layer model looped L times nearly matches a kL-layer model on p-hop tasks.

**Targets.** The loop copy failures: 294 seed 1 about 1.0, 296 at 1.85 and 1.97 (shown).

**Baseline.** 296's loop arm, copy phase.

**Pass mark.** Copy answer loss ≤ 0.05 by step 6,000 on both seeds. Report-only: 2-step dev accuracy at 12 passes vs 4 passes.

**Proved wrong if:** either seed is still > 0.5 at step 3,000.

**Cost.** $0 gate, then about 1.5-3 GPU-h, $0.8-1.5.

**Expected.** Untested: about a 50-60% chance of fixing copying, and about a 15% chance of then matching the plain twin within 5 points on the fresh panel.

**Caveat.** Fixing copying does not show that thinking longer works. That is stage 2 of 3.4. The lane 4 skeptic found no evidence that deeper, unpractised chains appear from extra passes alone.

**Scale-up role.** The prerequisite for every growth stage.

### D. Sleep replay: fine-tune the 1B on its own verified chains (bench: 1B think path; run after A)

**What.** Sample about 5-8 calculator chains per bank problem. Keep the distinct chains that code verifies as right, at most 2 per problem. Train a separate think-route LoRA on them.
- Missing-fact examples are template-written "not sure" chains. This is declared as a second data source, because the 1B rarely writes them (shown).
- STaR-style rationalization is left out, to keep one change.

**Evidence.**
- STaR (suggested): GPT-J GSM8K 5.8 to 10.7.
- RFT (suggested): LLaMA-7B 35.9 to 41.7 at k=100; the gain shrinks for better models.
- All at 6-7B; untested at 1B with k=5.

**Targets.** The gap between pass@1 and pass@5, and the setup errors (shown). Note that sample 0 was drawn at temperature 0.7, not greedy.

**One change.** The weights (base vs slept), with greedy decoding and the same prompt and calculator.

**Test.** A fresh blind 120-item panel.

**Pass marks.**
- Slept right ≥ base + 12.
- Wrong ≤ base.
- Missing-fact "not sure" ≥ base.
- pass@5 ≥ base − 4.
- The held-out-bank gain minus the panel gain is ≤ 15 points (the style alarm).

**Proved wrong if:** the panel gain is ≤ +3 while the held-out-bank gain is ≥ +15 points (style overfit), or pass@5 drops by more than 8.

**Cost.** $1.5-2.5; it shares A's bank.

**Expected.** Untested: +0 to +8 of 120, with about a 20-25% chance of meeting the bar.

**Scale-up role.** The supervised stage that RL needs later (2512.01970, abstract-only).

### E. Unblock comparing in the 30M net (bench: 30M)

This covers two kept ideas: the direction curriculum (lane 2) and the relational-bottleneck binding head (lane 4). They are run as separate single changes.

**Diagnostic first** (about $0.1, a few GPU-minutes). This replaces the tiny CPU model, which the repo showed to be misleading. Train the 30M net supervised on compare only for about 3,000 steps in a 2x2 design:
- direction: 'more'-only vs 50/50;
- readout: the current cls head vs a per-person binding query that retrieves only the rank features.

**Decision rule, fixed now.**
- Register whichever single change lifts mixed-direction compare to ≥ 90% alone.
- If both do, register the binding head, because pointer readouts are the scale-up design.
- If neither does, stop.

**Evidence.**
- Abstractor 2304.00195 and ESBN 2012.14601 (suggested): relational models learn order and binding where MLPs fail, but only on toy tasks.
- Abbe 2302.11055 (suggested): the rate is Θ̃(d^max(Leap,2)) for 2-layer nets. Applying it to our transformer is an analogy (untested).

**Registered run.** 296b plain, seeds 1 and 2, with one change.

**Pass marks.**
- Diagnosis compare ≥ 160/200 on both seeds.
- Fresh compare ≥ 24/30.
- 0 inventions.
- No other fresh category more than 3 below 296b's same seed.
- Counts 1-7 ≥ 190/200.

**Proved wrong if:** ≤ 110/200 on either seed. For the curriculum, also if 'more'-only is still below 140/200 at step 3,000.

**Cost.** $0.5-0.8.

**Scale-up role.** Comparing is an atomic skill that practice cannot create. It must be solved before the grown loop net can compose it. It has no effect on the 1B.

---

## 5. Dead ends and why

**Rejected by the skeptics:**
- **Free-signal selector** (lane 1 #2). Confidence adds about +0 to +0.5 at 8B (suggested), and the hand filters add at most +1 even with an oracle answer type (shown). Kept only as a diagnostic row inside A.
- **Backward check** (lane 1 #3). FOBAR gains only +0.3 to +2 at large scale (suggested). Our systematic misreadings would pass the inverse check: r054 coin values, r031 double counting (shown in stored samples).
- **Pairwise A/B judge** (lane 1 #4). Its cited evidence is a listwise 1.7B reasoning model trained with RL, not a pairwise judge. Position bias is a known failure. Fallback only.
- **Population number code** (lane 2 #3). The "extremes only" claim is not forced by a 6-layer net, and rank gaps are already 0.2-0.33. Run the free error-pattern check first.
- **Dream-and-check parser adaptation** (lane 3 #3). Premature: its bar is 3x GAZP's +3.8, and the dreams teach the notebook's names, not Ben's words. It is the most novel idea, so it is kept as a named follow-up.
- **SatLM declarative solver** (lane 3 #4). No greedy gain on plain word problems (suggested). A cheaper route: add literal provenance to the calculator path.
- **Execution-RL for the parser** (lane 3 #5). It depends on B, supervised fine-tuning gives most of the gain at 0.5-1.5B (suggested), and reasonpanel296 is no longer blind.
- **"3-step from more passes"** as the payoff of deep supervision (lane 4 #4). No evidence for depth that was never trained. The training fix itself lives in C.
- **Fast guess, slow check** (lane 4 #5). A latency optimisation only, and the P arm was not a greedy calculator run.

**Also dropped:**
- Zero-RL or GRPO on the 1B now (suggested: it stays bounded by the base, and 0.5B failed per TinyZero, abstract-only).
- Expecting spurious-reward gains on a non-Qwen model.
- More GRPO or more told answers for compare on the 30M net (shown at chance).
- A bigger majority vote.
- Prompted self-verification at 1B (suggested: below majority).
- Off-the-shelf process reward models (they need a download, and a mismatched policy does worse than majority, suggested).
- Coconut latent thoughts on the 1B (suggested: 34.1 vs 42.9 on GSM8K).
- HRM 1-step gradients (suggested: 56.5 vs 87.4).
- Predictive coding, the HRM hierarchy, and TEM as reasoners (weak or no reasoning evidence).
- Neural module networks for the executor (abstract-only: poor systematic generalisation).
- Plain plurality voting (shown: +1 right for +6 wrong).
- Training any verifier on the burnt 299/299b panels.
- **Growing the from-scratch net to 100-300M before it can copy and use extra passes** (shown: comparing points to a learnability problem, not capacity). This is a sequencing point, not a rejection of Ben's goal: growth is stages 3-5 of 3.4.

---

## 6. Sources

**Suggested (paper text read by a researcher or skeptic, or by me for Geiping):**
- TinyGSM 2312.09241 (2023)
- Cobbe 2110.14168 (2021)
- V-STaR 2402.06457 (2024)
- RL^V 2505.04842 (2025)
- GenRM 2408.15240 (2024)
- Kadavath 2207.05221 (2022)
- Zhang 2404.17140 (2024)
- rStar 2408.06195 (2024)
- Self-certainty 2502.18581 (2025)
- Weaver 2506.18203 (2025)
- DeepConf 2508.15260 (2025)
- Liu 2502.06703 (2025)
- Math-Shepherd 2312.08935 (2023)
- When To Solve, When To Verify 2504.01005 (2025)
- FOBAR 2308.07758 (2023)
- GenSelect 2602.02143 (2026)
- Yue 2504.13837 (2025)
- Spurious Rewards 2506.10947 (2025)
- STaR 2203.14465 (2022)
- RFT 2308.01825 (2023)
- TTRL 2504.16084 (2025)
- Orgad 2410.02707 (2024)
- Huang 2310.01798 (2023)
- TRM 2510.04871 (2025)
- Geiping 2502.05171 (2025)
- Coconut 2412.06769 (2024)
- Abbe 2302.11055 (2023)
- FoNE 2502.09741 (2025)
- Chang and Bisk 2405.20131 (2024)
- Webb 2309.06629 (2024)
- ESBN 2012.14601 (2021)
- Abstractor 2304.00195 (2023)
- Faithful CoT 2301.13379 (2023)
- SatLM 2305.09656 (2023)
- SLM-SQL 2507.22478 (2025)
- LEVER 2302.08468 (2023)
- GAZP 2009.07396 (2020)
- ToRL 2503.23383 (2025)
- SEP 2406.15927 (2024)
- Adaptive-Consistency 2305.11860 (2023)

**Abstract-only:**
- Ouro 2510.25741 (2025)
- McLeish retrofitted recurrence 2511.07384 (2025)
- Retrofitting recurrent depth at two budgets 2608.11233 (2026)
- Looped LMs for tool calling 2608.18171 (2026)
- Mixture-of-Recursions 2507.10524 (2025)
- Snell 2408.03314 (2024)
- ProRL 2505.24864 (2025)
- DeepSeek-R1 2501.12948 (2025; claim from a search result)
- Small Model Learnability Gap 2502.12143 (2025)
- Atomic Skills 2512.01970 (2025)
- Fan 2409.15647 (2024)
- Saunshi 2502.17416 (2025)
- Ni 2510.15990 (2025)
- RPC 2502.00511 (2025)
- ChatDB 2306.03901 (2023)
- PAL 2211.10435 (2022)
- PoT 2211.12588 (2022)
- Pangu 2212.09736 (2022)
- DreamCoder 2006.08381 (2020)
- LILO 2310.19791 (2023)
- MAPO 1807.02322 (2018)
- FINER-SQL 2605.03465 (2026)
- Bahdanau 1811.12889 (2019)
- CLOSURE 1912.05783 (2019)
- Predictive coding benchmark 2407.01163 (2024)
- TinyZero README (quoted in `design/v3/30-modes/294-learned-reasoner-plan.md`)

**Shown (repo):**
- `scripts/claude_rsn294_core.py`, `scripts/claude_rsn294_run.py`
- `scripts/claude_rsn299b_run.py`, `scripts/fable_notebook_contract.py`
- `artifacts/claude-rsn294-20260923/VERIFY-director.md`
- `artifacts/claude-rsn296-20260924/{VERIFY,DIAG}-director.md`
- `artifacts/claude-rsn296b-20260924/VERIFY-director.md`
- `artifacts/claude-rsn299-20260924/VERIFY-director.md`
- `artifacts/claude-rsn299b-20260924/{VERIFY-director.md,RESULTS.md,run/panel-V.jsonl}`
- `design/v3/30-modes/294-idea-check-5-14-16.md`
- `design/v3/30-modes/69-abstention-ltt-on-rung1-muse.md`

---

# Part 2

# Loop reasoner: research on five of Ben's asks (2026-09-24)

**How to read the labels**
- **shown**: I checked it in our repo; the file is named.
- **suggested**: I read the published text myself (the full text unless I say otherwise).
- **abstract-only**: I only saw the abstract, a search listing or a README.
- **untested**: my own estimate.

I made no repo edits, no training runs, no tests and no GPU use. The papers were read as full-text PDFs through curl and pypdf.

---

## 0. Where the loop stands today (shown)

- **Architecture.** `LoopThinker` (scripts/claude_rsn294_core.py:484-503) works like this:
  - the state starts as the input embedding x0;
  - each pass computes `x = inject(cat[x, x0]) + step.weight[t]`, then runs 2 pre-norm layers of width 1024;
  - the state is never normalized between passes;
  - the answer is read out only after the last pass.
- **Training.** The number of passes is random, 2–12 for each batch, and has nothing to do with how hard the question is (claude_rsn294_run.py:75-76). Backprop runs through every pass, and the learning rate is 3e-4 (run.py:255).
- **Copy phase.** Loop seed 1 sat at an action loss of about 0.99 from step 1,000 to 6,000. Loop seed 2 crawled down to 0.107. Plain seed 1 reached 0.0012 (artifacts/claude-rsn294-20260923/runs/*/train_log.jsonl). In 296 the loop sat at 1.85 and 1.97 (claude-rsn296-20260924/VERIFY-director.md, D3).
- **New finding from the 294 dev files: extra passes don't help today.**
  - Loop seed 2 on dev scored 916, 916 and 911 of 1,200 at 6, 12 and 20 passes.
  - Three-step scored 0 at every pass count.
  - Each category is flat across pass counts, e.g. value2 is 100/100/100 (runs/loop-s2/dev-final.json).
  - Also, step embeddings 12 and up are never trained, because training uses t = 0..11. So "thinking longer than 12 passes" uses untrained step signals.
- **Plain arm after 296b.**
  - Counting 1–7 is learned when it is told the answer after a miss.
  - Comparing is still at chance even when told (93 and 88 of 200). This is probably a readout or encoding problem.
  - Before/after got worse.
  - Three-step is 0 (claude-rsn296b-20260924/VERIFY-director.md).

**What this means for Ben's asks.** Halting, MiMo tricks and a teacher all sit on top of a loop that can't yet learn to copy and doesn't yet gain from extra passes. Comparing at chance and three-step at 0 are not fixed by any of the five asks.

---

## 1. Adaptive halting: "choose as long as it needs"

**What it is.** The net decides after each pass whether to stop. The published versions:
- **ACT** (Graves 2016): a halting unit, plus a cost for each extra pass.
- **PonderNet**: a halting probability at each step, pulled toward a set prior on how long to think.
- **Universal Transformer**: ACT applied to each position separately.
- **Recurrent depth** (Geiping 2025): no halting is trained. It stops when the answer stops changing between passes.
- **HRM / TRM**: a halt head trained on whether the current answer is right.
- **Fan et al.**: training ties the number of loops to the problem size, and at test time it stops at the most confident pass.

**Evidence**
- **ACT is sensitive to its compute-penalty setting** (suggested; 1603.08983). The paper's own text: "quite sensitive to the time penalty parameter". It also treats the pass count as a constant when taking gradients, so the gradients are biased.
- **PonderNet** (suggested; 2107.05407) gives unbiased gradients and a geometric prior on the number of steps. It is robust to that prior except when the prior's average is about 1 step. On parity it extrapolated to longer inputs where ACT stayed at chance.
- **Universal Transformer on bAbI** (suggested; 1807.03819) is our closest published analogue. Each fact is embedded as one vector and the net attends over the facts.
  - With dynamic halting it failed 0 of 20 tasks (10k training examples).
  - Average ponder time grew with the number of facts needed: 2.3 for one, 3.1 for two, 3.8 for three.
  - The authors say a standard transformer "always overfits" on bAbI.
- **Recurrent depth** (suggested; 2502.05171)
  - Its training recipe:
    - a random pass count from a heavy-tailed distribution;
    - backprop through only the last 8 passes;
    - the input fed back in by concatenation;
    - "sandwich" normalization.
  - Two failed large-scale runs, as they report them:
    - with pre-norm, the model "learned early to ignore the incoming state", and perplexity was the same at 1 or 32 passes;
    - the fix was sandwich norm plus a 10× lower learning rate.
  - They also say "at small scales all normalization strategies worked".
  - A core block told which pass it is on "interacts badly with path independence, leading to models that cannot extrapolate".
  - Their early exit needs no training: stop when the change between two passes' answers (KL) falls below 5e-4.
- **TRM** (suggested; 2510.04871)
  - The halt head is trained with binary cross-entropy on "is my current answer right?", in one forward pass.
  - The main driver is deep supervision: a loss at every outer step, with the carried state detached. An ARC analysis they quote found deep supervision doubled accuracy (19% to 39%), while the recursion alone helped only a little.
  - HRM and TRM use halting mainly to save training time. As TRM describes it, HRM runs all 16 steps at test time.
- **Fan et al.** (suggested; 2409.15647)
  - During training, each example gets T(n) loops tied to its size.
  - At test time they stop at the most confident pass or at the known step count.
  - Looped models then length-generalize on n-RASP-L tasks.
  - Their stated limit: they need the true step count in the training data. For us that is known: the hop count.

**How it maps onto our loop**
1. **Our random 2–12 passes are the opposite of Fan's recipe (shown, run.py:75).** The same weights must give the answer at 2 passes and at 12, so the net is pushed toward a shallow solution that doesn't use extra passes. The flat 6/12/20 dev result fits this (suggested mechanism, untested).
2. **We have both things Geiping warns about (shown, core.py:500).** A step embedding is added every pass, and there is pre-norm with no normalization of the state. His Bad Run 2 (the state gets ignored) is a plausible reading of our flat curves (untested).
3. **The loss is on the final pass only (run.py:82-83).** The early passes get no direct signal. That is TRM's main ingredient, and we don't use it.
4. **Our output is one choice from 114 actions.** So a KL-based exit is cheap and needs no new parameters.

**Order of changes.** First make the loop learn to copy. Then make its answer at each pass meaningful. Then halt. Halting on a loop whose extra passes don't help only saves compute; it cannot add right answers.

**Prerequisite experiment P0: per-pass supervision (dev screen, then registered)**
- **One change:** apply the copy loss (action CE + 0.5 × support BCE) to the readout after every pass from pass 2 onward, averaged, instead of only after the last pass. Everything else stays at 294's settings.
- **Screen:** copy-only, 6,000 steps, seeds 1 and 2, about 15 minutes each (shown: loop copy phase took 15.4 minutes in the loop-s1 log).
- **If P0 fails, screen these next, one at a time:**
  - fixed 4 passes;
  - learning rate 1e-4;
  - an RMSNorm on the state before it is fed back in;
  - no step embedding.
- **Baseline:** the 294 loop copy logs (0.99 and 0.107) and the plain arm (0.0012).
- **Pass marks, fixed now:**
  - action CE ≤ 0.05 at step 6,000 on both seeds;
  - dev value2 ≥ 95/100, checked, at 12 passes.
- **Proved wrong if:** CE stays ≥ 0.5 on either seed. Then per-pass signal isn't the blocker.
- **Cost:** about $0.15 per variant for both seeds (untested).

**Experiment H1: zero-training adaptive exit (only after P0 passes)**
- **One change, at evaluation only:** instead of a fixed 12 passes, stop when KL(pass t ‖ pass t−1) < 1e-3 on 2 passes in a row, with a cap of 24. Same checkpoint.
- **Pass marks:**
  - checked-right on dev and the fresh panel is within −3 of fixed-12;
  - 0 invented answers after the fact-check;
  - mean passes rise with hops, and 2-hop minus 1-hop is at least 1.0 pass.
- **Proved wrong if:** the pass-count gap between hop levels is under 0.5. Then the net isn't "thinking longer on harder" and halting is cosmetic.
- **Cost:** CPU evaluation, about $0.

**Next steps if H1 passes**
- **H2, the real test of Ben's idea:** Fan-style training with passes = 2 × hops, plus ±1 jitter. Pass mark: three-step ≥ 5/30 on dev with adaptive exit, against 0 today.
- **H3:** a TRM-style learned halt head, trained on "the current answer is right and passes the fact-check". It doubles as a confidence signal for "I don't know".

**Risks**
- Early exit on a confident wrong answer. The fact-check catches unsupported answers, not wrong-but-cited ones.
- ACT-style compute penalties teach the net to quit early. Avoid them; see item 4.
- The loop may never beat plain. 294 says that is still untested.

---

## 2. "Learns rules, not surface patterns"

**Evidence**
- **MLC** (suggested; Nature 623:115, full PDF read). Meta-training over many episodes with re-shuffled symbols solves SCAN's new-combination splits with ≤ 0.22% error. But it **fails 100%** on SCAN's length split and on COGS's structural splits. The authors: it "succeeds when generalization makes a new episode in-distribution". So variety fixes new combinations, not longer chains. That fits 296: two-step went to 30/30, three-step stayed at 0 (shown).
- **Grokked transformers** (suggested for its ID/OOD findings; 2405.15071). Two-hop composition generalizes out of distribution never, even after 2M steps. Comparison does. They suggest sharing weights across layers, which is what a loop does. Caveat: their facts are stored in the weights, while ours are in the notebook, so the transfer to us is untested.
- **Faith and Fate** (abstract-only; 2305.18654). Transformers solve compositional tasks by "linearized subgraph matching", which is what our D1 looks like.
- **RASP-L conjecture** (abstract-only; 2310.16028). A model length-generalizes when a short, length-independent program solves the task. Following one hop per pass is such a program.
- **Grokking** (abstract-only; 2201.02177). It is a small-dataset effect. Our generator is unlimited, so it is less relevant. The overfit in D1 was to the generator's *style*, not to its examples.
- **CLUTRR** (abstract-only; 1908.06177). Kinship chains, tested on held-out rule combinations and longer chains, with added noise facts. A graph network on symbolic input beat text models. This is the best template for our test design.
- **Contrast sets and counterfactual data** (abstract-only; 2004.02709, 1909.12434). Small edits that flip the gold answer expose shortcut rules. Training on both versions helps robustness.

**What test would show a learned rule.** Split by structure, not by example. Report one row per axis:
- **(a) Length ladder:** 1, 2, 3 and 4 hops. A rule gives a gentle slope; a pattern gives a cliff after 2.
- **(b) Minimal pairs:** change the row that decides the answer (the answer must change), and change an irrelevant row (it must not). Score how often both answers in a pair are right.
- **(c) New combinations of practised skills:**
  - a correction on the middle link of a chain;
  - a two-hop backwards "who";
  - before/after about a person reached by a chain.
- **(d) Out-of-range values:** counts 8–12. Today this is 0/200 (shown, 296b).
- **(e) Blind notebooks written by another author:** 296 already does this.

Gold always comes from an independent code solver. The code arm may not support (c), so check it first.

**Experiment R1: rule probe (measurement only, $0)**
- Run the probe (about 600 generated items, dev-only) on the existing 296b plain checkpoints and the code arm, on CPU.
- It sets the yardstick every later change is scored against.
- Prediction (untested): minimal-pair consistency is high on practised kinds and low on the new combinations.

**Experiment R2: paired contrast practice (the one training change)**
- **Change:** each practice episode appears in the same batch with its code-made contrast twin. A try earns +1 only if the same try index is also right on the twin.
- **Baseline:** the 296b plain recipe, same seeds and steps.
- **Pass marks:**
  - minimal-pair consistency ≥ baseline + 15 points;
  - new combinations ≥ baseline + 10 of 60;
  - fresh-panel total ≥ baseline − 3;
  - 0 invented answers.
- **Proved wrong if:** consistency rises but new combinations and three-step don't move. Then the net becomes sensitive to the right row but still doesn't compose.
- **Cost:** about $0.6–1 (same as 296b).
- **Risk:** harder practice may slow learning of the easy kinds.

---

## 3. "Real-world environments"

**What fits the 30M (shown by design).** The 30M net never sees words. `encode()` turns every name, value and relation into an anonymous symbol that is re-shuffled every episode (core.py:292-350). So it cannot act in text games, tool-use environments or chats directly. Its "real world" is **real-looking notebooks**: the rows our actual reader writes from real-looking chats. That is where the noise of real use comes from: duplicate names, half-parsed relations, corrections.

**What fits the 1B** (all abstract-only unless noted)
- **Reasoning Gym** (2505.24760, README read): over 100 generators with verifiers and adjustable difficulty. Tasks that fit the notebook work include `family_relationships`, `needle_haystack`, `time_intervals`, `calendar_arithmetic`, `syllogism` and `zebra_puzzles`.
- **Test-only sets:**
  - **LongMemEval** (2410.10813): 500 questions covering extraction, multi-session reasoning, time, knowledge updates and abstaining;
  - **LoCoMo** (2402.17753): 300-turn conversations.
  Both are too small, and too much at risk of leaking into training, to train on.
- **τ-bench** (2406.12045) needs an LLM playing the user. That is expensive and far from notebook QA.
- **TextWorld** (1806.11532): generated text games. Also far from notebook QA.
- **MiMo-V2.6** (suggested, report §4.2.5 and Table 7): training across several simplified agent "harnesses" improved every harness pair, including held-out ones. For us that means **varying the reader and pipeline versions** that make practice notebooks.

**Experiment E1: practice on reader-made notebooks (30M)**
- **Change:** practice notebooks come from running the real reader over chats. The chats are rendered from hidden scripts that code generates. Gold is recomputed by the code solver over the rows the reader produced, because the reasoner must reason over what it is actually given. Mix 50/50 with the 296 generator.
- **Baseline:** 296b plain.
- **Test:** a blind panel of chats written by a different author, run through the same reader. The code arm is scored on the same rows.
- **Pass marks:**
  - ≥ +10 over baseline on that panel, on both seeds;
  - no drop larger than 3 on reasonpanel296;
  - 0 invented answers.
- **Proved wrong if:** the gain is ≤ 3. Then 296's code variety already covers the reader's style.
- **Cost (untested):**
  - reader inference over about 15k chats: about 0.5 h on the 5090, about $0.25;
  - training: about $0.6;
  - chat text: $0 from templates, or $3–12 from a teacher (item 5).
- **Precondition:** the reader has to be good enough. 294 §1 named it as the blocker (shown), so check its current score first.

---

## 4. "MiMo v2.6's RL technique"

**It exists.** MiMo-V2.6 was released around 22 Sept 2026: Pro (1.02T total / 42B active) and Flash (309B / 15B), MIT license on Hugging Face. I read the full technical report (`MiMo_V2_6_technical_report.pdf` on the HF repo, 44 pages) and both model cards. I also read the predecessors: MiMo-7B (arXiv 2505.07608) and MiMo-V2-Flash (arXiv 2601.02780).

**The recipe (suggested, from the report)**
- **Scale:** one mixed RL run, "You Only RL Once", with GRPO:
  - 1,568 prompts × 16 rollouts per step, asynchronous;
  - learning rate 3e-6, with the Muon-family "Muown" optimizer and the MoE router frozen.
  - Cost: $2.6M (Pro) and $0.9M (Flash).
- **Environments:** coding 68%, tool use 12%, design 13%, context-following 3%, cybersecurity 4%, across several mini-harnesses.
- **Dynamic sampler:** it drops groups where every try passed or every try failed. A "Sample Mixer" keeps each data source's share of the batch fixed.
- **Groupwise Agentic Grading:**
  - **GRS:** reward = test pass × solution-rubric score × behaviour-rubric score;
  - **GAR:** among passing tries in a group, shift positive advantage toward the better-quality ones;
  - rewards for confirmed hacks are set to zero.
- **Group-relative length penalty:** it applies only to *successful* tries, only when the group pass rate is above a threshold, and only for length beyond a percentile of the passing lengths.
- **Reward-hack hardening:** clean the environments, have a "hack agent" probe them until it finds no exploit, and audit trajectories during training.
- **MOPD2:** after RL, a student learns from domain teachers through token-level reverse KL. This needs the teacher's per-token log-probs on the student's own tokens.
- **Earlier MiMo-7B tricks:**
  - a test-difficulty reward (partial credit by how hard each passed test is);
  - an "easy pool" resampled 10% of the time, because dropping solved problems destabilized training.

**What transfers to a 30M loop net at $4 per run**
1. **Dynamic sampling.** This is 294's D3 exactly: all 8 tries agree, so the group baseline gives zero signal (shown, run.py:110). The easy pool isn't needed, because our generator is unlimited.
2. **GAR and the group-relative length penalty, as a "thinking length" cost.** Among right tries only, and only in groups that are mostly right, prefer fewer passes and exact citations. This avoids ACT's known failure of teaching the net to quit early (item 1). Our +0.2 bonus for exact citations (run.py:106-107) is already a small quality multiplier in the GRS style.
3. **Hack hardening, as a ritual.** Red-team the reward and the fact-check before each registered run.
4. **Mixing across sources.** Keep each question kind's share of the batch fixed after filtering.

**What doesn't transfer:** the scale, asynchronous rollouts, router freezing and Muown. MOPD needs teacher log-probs; for the 30M, the exact code arm already is the teacher.

**Experiment M1: dynamic sampling (plain arm, can run now)**
- **Change:** drop any group whose 8 tries all get the same reward, and refill from fresh episodes until there are 128 mixed groups.
- **Baseline:** 296b.
- **Pass marks:**
  - fresh-panel total ≥ baseline + 5 on both seeds;
  - no kind drops more than 3;
  - 0 invented answers.
- **Proved wrong if:** every kind stays within ±3. Then the empty groups weren't slowing learning, since told-after-miss already covers the all-wrong groups.
- **Cost:** about $0.7.
- **Honest expectation (untested):** a small effect. It will **not** fix comparing, which is a readout problem.

GAR and the length penalty come later, as the RL stage of halting.

---

## 5. A teacher model through a cheap API

**What it could do, and what it can't**
- **Explaining a miss.** The 30M can't read an explanation, since it sees no words (shown). The exact version already exists and costs nothing: 296b "told the answer after a miss" (claude_rsn296b_run.py:62-67).
- **On-policy distillation** (suggested: MOPD formula in 2601.02780; abstract-only: GKD 2306.13649). It needs the teacher's per-token log-probs on the student's own text, with the same tokenizer. Most chat APIs don't score text you give them (untested). So real on-policy distillation means a **local open-weight teacher for the 1B**, not an API.
- **Grading.** The code checker is exact, so an LLM grader only adds noise for the 30M.
- **Real value:** varied *problems*, meaning notebook styles and chat wording, not answers.

**The project rule.** Teacher text is raw material only:
- gold always comes from code (the 296 generator already re-solves every episode with an independent solver, shown in 296 doc);
- the teacher's own answer is only a cross-check, with disagreements logged;
- a blind agent audits about 50 items per batch.

**Cost per 10k episodes (untested)**

Prices are search listings from 2026-09-23, not checked on the providers' pages, and they change often:
- MiMo-V2.6-Flash: $0.14 / $0.28 per million input / output tokens;
- DeepSeek V4.1 Flash: $0.30 / $1.20;
- GPT-5.4 nano: $0.20 / $1.25;
- Gemini 3.8 Flash: $0.75 / $3.75.

| use | tokens per 10k (untested) | MiMo Flash | DeepSeek | GPT nano | Gemini Flash |
|---|---|---|---|---|---|
| write notebooks (700 in / 600 out each) | 7M in / 6M out | $2.7 | $9.3 | $8.9 | $28 |
| write chats (500 / 900) | 5M / 9M | $3.2 | $12.3 | $12.3 | $38 |
| grade a miss (1,200 / 150) | 12M / 1.5M | $2.1 | $5.4 | $4.3 | $15 |

"Thinking" tokens can multiply the output cost by 2–10×. Turn thinking off.

**Terms of service: Ben must check the specific provider's current terms before any use**
- **Anthropic.** Commercial terms D.4, read today: the customer may not "access the Services to build a competing product or service, including to train competing AI models".
- **Google.** Gemini API additional terms, read today (updated 2026-04-28): "You may not use the Services to develop models that compete with the Services". They also say **you must be 18 or older**, and it is for professional or business use only.
- **OpenAI.** The same "develop models that compete" clause. Search listing only, because their page returned 403.
- **DeepSeek.** Its platform terms reportedly *allow* training other models and distillation. Search listing only, because the download failed.
- **MiMo-V2.6 weights** are MIT-licensed (the model card, read). I did not read the Xiaomi API platform's own terms.

**Rule of thumb**
- **Riskier:** training our weights on a closed provider's outputs.
- **Lower-risk:**
  - using those outputs for evaluation, or throwaway grading that never trains anything. Anthropic's "access to build a competing product" wording is broad, though, so even this needs checking;
  - using a permissively licensed open-weight model, self-hosted or through a host whose terms allow training.
- **Also check** the age rules for a high-school account. A parent's account may be needed.

**Experiment T1: teacher-written notebook styles**
- **Change:** practice is 50% teacher-written notebooks and 50% from the 296 generator. The teacher is permissively licensed, and the notebooks are 10k JSON-row sets about invented people with styles it invents. Code re-solves every one.
- **Baseline:** 296b plain.
- **Test:** a blind panel from a *different* model family, so the test measures transfer and not the teacher's own style.
- **Pass marks:**
  - fresh blind total ≥ baseline + 8 on both seeds;
  - 0 invented answers;
  - no category drops more than 3.
- **Proved wrong if:** the gain is ≤ 3. Then code variety is enough.
- **Cost:** $1–12 for the teacher plus about $0.6 GPU.
- **Risks:** overfitting to the teacher's style, and licence or terms problems.

---

## Recommended order for the loop work

1. **R1, the rule probe** ($0, CPU). It is the yardstick for everything else.
2. **P0, making the loop learn** (dev screen, about $0.15 per variant, then registered). Nothing about halting matters until the loop's copy loss falls.
3. **H1, the zero-training exit, then H2, passes tied to hops.** H2 is the real test of "thinks longer on harder" and of three-step.
4. **M1, dynamic sampling** on the plain arm. It is cheap and can run alongside the loop work at any time.
5. **R2, contrast practice.** Then GAR and the thinking-length cost as the RL stage of the halt head.
6. **E1 and T1** (environments and teacher), only after the terms check and the reader check. They target the style overfit from D1, which 296's code variety has already largely fixed (two-step 30/30).

Separately, a registered compare-readout change is still needed. None of the five asks fixes it.

---

## Plain-language summary for Ben

You're right that the model should get to think as long as it needs. Published models do that: they stop when their answer stops changing, or they learn a "stop now" signal. But our loop has two problems to fix first. It still can't learn the basic copying lessons, and even when it does learn, thinking longer doesn't change its answers yet: 6, 12 and 20 passes score the same. So step one is to fix how it learns, most likely by checking its answer after every pass instead of only at the end. Then we let it stop early and check that it really thinks longer on harder questions.

To test whether it learned rules, we give it longer chains than it practised, pairs of notebooks that differ in one fact, and new combinations of skills it knows. We don't test it only on more of the same.

MiMo-V2.6 is real and came out this week. Most of its recipe needs millions of dollars, but two tricks fit our $4 budget:
- skip practice rounds where every try got the same score;
- among right answers, reward the shorter thinking.

A teacher model can't explain things to our small net, because it doesn't know words. It can write more varied practice notebooks, as long as our code checks every answer. Before using any paid AI as a teacher, read its terms: Google, OpenAI and Anthropic forbid using their outputs to train competing models, and Google's API also requires you to be 18.

## Sources (read unless marked)
- MiMo-V2.6 report and card: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL ; MiMo-7B: https://arxiv.org/abs/2505.07608 ; MiMo-V2-Flash: https://arxiv.org/abs/2601.02780
- ACT https://arxiv.org/abs/1603.08983 ; PonderNet https://arxiv.org/abs/2107.05407 ; UT https://arxiv.org/abs/1807.03819 ; Geiping https://arxiv.org/abs/2502.05171 ; TRM https://arxiv.org/abs/2510.04871 ; Fan https://arxiv.org/abs/2409.15647 ; MLC https://www.nature.com/articles/s41586-023-06668-3 ; Grokked transformers https://arxiv.org/abs/2405.15071
- Abstract or README only: 2305.18654, 2310.16028, 2201.02177, 1908.06177, 2004.02709, 1909.12434, 2505.24760 (Reasoning Gym), 2410.10813, 2402.17753, 2406.12045, 1806.11532, 2306.13649, 2502.01612
- Terms: https://www.anthropic.com/legal/commercial-terms (read); https://ai.google.dev/gemini-api/terms (read); https://openai.com/policies/row-terms-of-use/ (search listing only, 403); https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html (search listing only, download failed)
- Prices (search listings, not verified): https://openrouter.ai/xiaomi/mimo-v2.6-flash ; https://costgoat.com/compare/llm-api
