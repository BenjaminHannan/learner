# Premonition design decisions log (2026-09-18)

Copied from the assistant's project notes; the full reasoning is in the conversation. Newest entries are at the bottom.

On 2026-09-18 Ben rejected the "recurrent transformer + delta-rule side memory" design as "a transformer with a layer on it" and asked to restart the architecture. His first framing was to replicate human learning. He then clarified: "It doesn't even have to be a human, I just want to create my own version of a model that is able to learn."

**Why:** He wants a genuinely learning system of his own design, not a conventional frozen model with bolted-on memory.

**How to apply:** Co-design in small steps, starting from a precise definition of what "able to learn" means. Explain each concept and decision in plain language and confirm he understands before moving on. Use brain mechanisms (fast/slow learning, replay, gated plasticity, practice, forgetting) and ML continual learning as options, not requirements. Keep the old GRU/transformer code as baselines; never delete it. Research phases may use workflows (see [[workflows-research-only]]); engineering stays inline. Design docs live in `design/`.

**Name (Ben, 2026-09-18):** the model is called **Premonition**. The first fully functioning model is to be named **premonition v1-small**. Use these names in docs, artifacts and checkpoints.
**Core brainstorm (Ben, 2026-09-18, not yet in design/):** no plain transformer core. Split into a small skills-only REASONER (recurrent reader + short attention window + ~16-32 entity slots + TRM-style think loop + checker-based stopping; asks the store "out loud" via text queries, trained imitation→RL) and a KNOWLEDGE STORE (hippocampus-like cards + cortex-like slots, consolidated in sleep). Copy the brain at the systems level: route by learning signal (told once → store; practised with reward → reasoner weights). Wipe-store test must make fact questions fail. Goal: more efficient intelligence (accuracy per weight/compute/token vs the 4M transformer baseline). Later same day Ben added: encoder → abstract thought space (not English) → decoder; accepted fixes (reconstruction + paraphrase agreement + world-state grounding; words→thoughts curriculum for RL; decoder as a window into thoughts; store queries become abstract but decodable). Wants MOTIVATION treated as a research area (research memo commissioned). Expects to scale up later. Thought design agreed: scene = entity slots + thought steps = 2-4 codes from a learned codebook (VQ "private language", pointer codes, ASK/DONE codes); names are pointers, spellings live in the store. Training: build space → JEPA prediction (Ben likes JEPA) → imitation words→codes → RL. Codebook KEEPS GROWING (Ben's choice), stabilised ART-style: births only in sleep when thoughts repeatedly fit no code, young codes plastic/old codes harden, split not overwrite, permanent IDs, anchor drift checks, text kept as safety net. Proposed (not yet confirmed): reward final answers via decoder+checker, middle steps only via world ground truth, decoded thoughts for reading never for reward. Open question: teacher-named code births as well as blind clustering. Motivation research memo (2026-09-18, session scratchpad, offered to copy into design/) recommends v1 drives: mastery/learning-progress (practice choice), gap curiosity (ask/look up, paid only on ground-truth confirmation), replay-priority tag, effort (think length) + fixed regulators; reward only from simulator checker; do NOT build novelty bonuses, teacher-approval reward, resource/awake rewards, summed happiness score, or self-proposed tasks (v2). Ben's follow-ups (same day): option 3 locked; wants mid-thought readability (J-space/J-lens-style tooling over logged codes + decoder + slot probes); assigned tasks must never be abandoned — "frustrated" only applies to self-chosen practice, plateaus trigger strategy switches, user sets importance/limit; "sleep pressure" renamed consolidation pressure, can consolidate on a background copy; compute budget = hunger-like spending limit, never a reward for acquiring compute. Agreed: effort design; consolidation pressure ("tiredness") kept — Ben finds it very interesting; code births = both blind + teacher-named, with safeguards (teacher names provisional, synonyms attach to existing code, model can ask "what's this called?"). Novel-mechanisms research memo done 2026-09-18 (top: sleep-as-transaction, told-ledger, self-tutoring with card, slot knock-out JEPA, hint ladder; not yet walked through with Ben). Knowledge store agreed: diary (raw, permanent, never edited) + cards (hippocampal index: key/value/time/source/confidence/version/diary pointer, gated writes, same-key = new version) + knowledge slots (sparse memory-layer table, sleep-trained, sparse-memory-finetuning style, schema fast-track). Two recall routes (automatic familiarity into slots + deliberate ASK) — agreed. Store the model's own inferences, marked "inferred", lower trust, never overwrite observations — agreed. Knowledge slots may fade details to gist since the diary keeps everything — agreed. Consolidation gated (card-hidden test), cards rebuildable from diary (cf. arXiv 2605.12978). Sleep design AGREED 2026-09-18 (Ben: weights change only in sleep — yes; grow-during-sleep via upward distillation — wanted eventually, v2; naps whenever needed — yes): pressure + learned body clock + naps; background copy with snapshot; cycles NREM(sort, repair, interleaved consolidation, reverse replay of successful traces, shrink&perturb + dead-unit reset + gist fading) then REM(dreams recombining facts — rewarded only if simulator can check, code births/splits & insight, anchor checks); wake-up lesion test + wake-up check with bad-night rollback; ~1:2 sleep:awake compute; key baseline = same compute as plain training. Inputs AGREED: v1 = time (clock, time-since, card age), speaker/source tag, own-state interoception (read-only: pressure, compute left, confidence, drives, store hit/miss, think time); map view (partial, only what it can see) = first added sense; body sense with acting; teacher pointing (joint attention) with teacher-named concepts. Rules: no free answers (leak detectors cover all inputs), sense-not-set internal state, each input needs a with/without test.
**Priorities (Ben, 2026-09-18):** reasoning first, language second; being able to talk to it is a nice extra and can be traded away for something important.

**Experiment 1 / Stage 0 (2026-09-18):** Ben approved building it (code changes allowed now). Stage 0 = leak fixes + real transformer baseline. First 5090 baseline (4M, 10 min, ~670M tokens): held-in 51.5%, held-out 10.1%, FRESH NAMES 0% vs seen 24%, counterfactual pairs fail, plans 0% — the plain transformer memorises names instead of reading them (strong motivation for pointer/store design). Report: artifacts/premonition-step1-4M-1789770088141917828-23843.json. Leak status: place/count/what-if/not-told fixed (not-told was a within-visit detector artifact; leak test now per-answer-class with visit groups); who-has and box-contents target_line leaks are real and still open (answer names sit in holding/put-in lines). Ben chose "train now, fix leaks in parallel".**Adopted from the novel-mechanisms memo (Ben, 2026-09-18):** sleep as a transaction (commit only if checks pass, else roll back); told-ledger (exact record of what it was told; honest "don't know"; flags facts sleep lost); self-tutoring with the card in hand (sleep, Exp 3); slot knock-out prediction in JEPA (Exp 2); hint ladder for practice (Exp 4); pretend/belief/source frames as card fields from day one. Later: two memory strengths (retirement rule). Leaks: who-has and box-contents target_line accepted as known priors guarded by the counterfactual-twin test.
**Fresh-name 0% was a tokenizer bug (verified 2026-09-18):** `premonition-tok-v1-fallback.json` predates syllable splitting — 262 train names single tokens, no held-out name is. GPT xhigh agent fixing build_tokenizer (refit to a v2 file, audit in report). All contenders must use v2; baselines re-run. Spec for Experiment 1: design/06-premonition-mini-spec.md (D ≈2.0M: minGRU reader + local attn, 16 ENT slots, think loop ≤8, ASK top-4 into per-visit card store, rule-based name pointerizer). Added contender E = anonymised transformer (pointers without store); controls D-noask, D-noptr; per-visit store at test decided OK. Ben wants building done by GPT xhigh subagents via /gpt (serial; run claude-web with PATH="/opt/homebrew/bin:$PATH" because /usr/local/bin/node is x86 and fails).

**After the adversarial review (2026-09-18):**
- **Store vs weights, restated (review #20):** instance-specific, mutable, source-attributed propositions ("Nera is in the barn", "in this village glass breaks") go to the store; reusable schemas, language, procedures and statistical regularities of the world go into weights. Tested on unpredictable synthetic bindings, where only the store can help.
- **Open problems recorded for later experiments:** sleep transactions must version weights, optimizer, key encoder, card keys, codebook ids and sequence numbers, and re-key cards written during sleep before commit (#22); sleep-gating checks use their own data, separate from development data and an untouched shadow test (#23); lifetime budgets for diary bytes/event, active cards, code growth, retrieval cost and sleep FLOPs must be declared and simulated before building sleep (#24); the drive scheduler is tested alone on learnable, impossible, noisy and forgetting tasks, with a cap on the compute any self-chosen task can take (#25).

**Astra research review (2026-09-18):**
- Verdict: the core idea is sound, but novelty is modest at the mechanism level. Nearest prior art is Memory Networks (2015), Key-Value Memory Networks (2016), RETRO, Memory Layers/Engram, Titans/Nested Learning, HRM/TRM, and "Language Models Need Sleep" (2026).
- Experiment 1 changes adopted in spec §10: gold-evidence diagnostic first, C\*, D-soft, E-long, label-free Core training, decomposed held-out, 3 seeds.
- **Proposed roadmap, pending Ben:**
  1. solvable task
  2. memory advantage vs C\*
  3. depth generalisation (train shallow, test deep)
  4. a 20-lesson continual *procedural* learning stream vs tuned replay/EWC/LoRA/frozen+retrieval, with fresh-memory probes
  5. CLUTRR replication
- Postpone the growing codebook, private-language RL, learned sleep clock and drives until these earn a place. Try continuous thought states and plain replay first.
- Open problems added:
  - derived cards need dependency tracking so that a corrected premise invalidates them;
  - sleep transactions must report the acceptance rate (to avoid "stable by refusing to learn");
- learned memory parameters count as parameters.

**Lead handoff and execution arrangement (Ben, 2026-09-18):**
- Astra owns research direction, experiment design, interpretation, and review.
  Ben requests execution prompts for an Opus agent on Ultracode; Opus performs
  implementation and runs. Astra should think and review rather than execute
  engineering. Ben confirmed the earlier Claude trainer agent has stopped, so
  `premonition/train.py` and `premonition/toy.py` are released for Opus.
- Hard new GPU-rental ceiling: $30 total on Vast.ai only, excluding approximately
  $3.40 historical spend. Every rental still needs an explicit quote and yes.
  Mac work is free; BensPC remains off-limits. Ledger: artifacts/spend-ledger.md.
- Astra's baseline check: all 74 existing Premonition tests passed locally
  (17.785 seconds); this is not evidence of learning or full §§9–10 compliance.
- Proposed $30 allocation: solvability $5, memory comparison $12.99,
  four-lesson procedural pilot $5, reserve $7.01. Detailed plan:
  design/research/2026-09-18-lead-plan-30usd.md. Evidence-first roadmap remains
  pending Ben's answer; no long-term architecture change or rental is approved.
- Three gated Opus prompts live in reviews/opus-execution-01-correctness.md,
  reviews/opus-execution-02-learning.md, and reviews/opus-execution-03-solvability.md.
  Send prompt 1 first; later prompts require review of the preceding evidence.
  No engineering source files were changed during this lead handoff.

**Communication and roadmap clarification (Ben, 2026-09-18):**
- Ben has not approved the proposed roadmap yet and requests an explanation.
  Keep it pending. Existing Experiment 1 engineering authorization still applies;
  it does not authorize any rental or long-term architecture replacement.
- Ben is a high-school student and co-designer. Explain results and choices in
  simple language; define a new technical idea before using it. Sophisticated
  work is welcome, but Ben must understand what is being tested and why.

**First-stage testing approved (Ben, 2026-09-18):**
- Ben: "Yes, I think we should test it." This accepts the immediately proposed
  first stage: establish trustworthy tests, then test reasoning with the relevant
  facts supplied. Opus implements and runs; Astra designs and reviews.
- Begin with reviews/opus-execution-01-correctness.md. Review its evidence before
  the toy-learning and village-solvability milestones. Local work is authorized;
  rental requires a separate exact quote and explicit approval.
- Decide subsequent research stages from the first-stage results. This approval
  does not replace the long-term design or approve the full spending plan.

**Opus milestone 1 — trustworthy label-free inputs (implemented 2026-09-18, run m01-20260918-202731; report reviews/opus-milestone-01-m01-20260918-202731.md; contract in design/06 §11):**
- *Implemented.* Labels (answers and feedback) are removed from text before name binding and encoding, through one versioned module shared by D and the Core prompts (`premonition/preprocess.py`). Its identity is the SHA-256 of a rules-as-data spec, pinned by a golden-output test; a source-code hash was rejected because a comment edit would then retire every checkpoint.
- *Implemented.* One label-free line form for every contender: an earlier question line ends at `[answer]` + newline. D needs `[answer]` on every question line (each question is answered at its own tag); the older Core form (question text without the tag) was dropped so the path is truly shared. Two contender tests asserted "exactly one `[answer]`" and now assert the stricter structural audit instead.
- *Implemented.* Near/far is cut over the regime's visible lines (label-free by default). Using the with-labels cut would call 466 validation items "far" that A's label-free window actually shows.
- *Implemented.* D's label-free cache is a new v2 identity; the v1 cache is untouched and still feeds E's LM stream. On unperturbed real data the v2 cache reproduces "v1 + batch masking" bit for bit (no village visit writes a name only in a label), so the old D path was not leaking in practice; the fix closes the structural hole, proven with planted fresh names.
- *Implemented.* Checkpoint purposes (primary / diagnostic / fixture / legacy) with fail-closed admission; unit tests now declare `purpose="fixture"` and record a preprocessing identity (a legitimate contract change: the toy tokenizer must never pass as a contender). The tokenizer-path override no longer skips the digest check.
- *Implemented.* C's candidates follow §9.12 via a forward-only fixed point; the old rule stays selectable.
- *Kept, flagged.* Repeats remain excluded under label-free evaluation (conservative); Astra to decide.
- *Observed.* During this milestone another agent edited `learnlab/patterns.py`, `learnlab/village/render.py`, `scripts/gen_patterns.py` and `tests/test_learnlab_patterns.py`, and created `data/village/patterns/bank-v1.json` (edits seen 20:56–21:05, still ongoing). The pattern bank changes the rendered village used by every test fixture. While it was in flux, one pre-existing contender test (`test_a_planted_perfect_match_in_the_window_or_later_is_never_recalled`) errored, identically with the untouched pre-milestone code; on the 21:05 bank it passes again. Test outcomes in this checkout currently depend on another agent's in-progress files (`learnlab/` is outside this milestone). Hashes of the external files at the final run: archive/opus-m01-20260918-202731/external-state-at-final-run.sha256.
- No training, no rental. New rental total $0.00 / $30.00.

**Astra improvement research and Ben's TST suggestion (2026-09-18):**
- Completed a primary-source literature review and inspection of the current
  training/retrieval code. No engineering changes or training by Astra. Memo:
  design/research/2026-09-18-improvement-research.md.
- Highest-priority hypothesis: hard detached card selection prevents answer
  errors from directly training the query/key selector. Verify gradients; test
  the already specified D-soft separately. Also separate retrieval, answer
  generation and early stopping, and measure whether toy language loss helps.
- Answer-only retrieval must remove all gold-dependent behavior, including
  answer-loss weighting; setting the evidence-loss coefficient to zero is
  insufficient. This is an experimental-integrity requirement, not a measured
  explanation of the old toy score.
- Ben suggested Token Superposition Training. Recommend a free local three-arm
  pilot after correctness and an ordinary learning baseline: standard ordered
  pretraining, pairwise TST plus normal-token recovery, and ordered inputs with
  bag targets plus recovery. Compare subsequent reasoning at measured cost.
  Research consideration is not a finding of improvement or permanent adoption.
- New Opus handoffs: reviews/opus-research-learning-diagnostics.md (addendum
  within the existing learning milestone's time/tuning cap) and
  reviews/opus-research-tst-pilot.md (separate 30-minute local training cap).
  No rental allocation added. All paid runs still require Ben's exact approval.
- Opus's new completion entry reports concurrent generator/pattern-bank edits.
  Freeze their identities across arms; correctness acceptance remains separate
  from this research report. New rental spending remains $0.00 / $30.00.

## 2026-09-18 — deeper research, milestone-1 review and revised next experiment

- Ben requested deeper research and authorized Astra to manage the Premonition
  Opus conversation in Claude Desktop through computer use. Astra remains the
  research/design/review lead; Opus implements and runs.
- Scoped acceptance of `m01-20260918-202731`: shared label-free preprocessing,
  checkpoint/report identity safeguards and C's candidate-gap correction are
  accepted on submitted artifacts and source review. Astra did not independently
  rerun the final tests. Count is 108 tests total, one skipped. The skipped
  learning gate and unfinished full statistical verdict remain unresolved.
- Repeated questions remain excluded from primary scoring; a separately labeled
  diagnostic may include them later. No silent increase in independent samples.
- Trainer notes materially change priority: reported gold-card answer failure
  means using supplied evidence must be reproduced and localized before new
  retrieval methods. Prior scratchpad probes are reported evidence, not a new
  reproduced finding or proof of representation collapse.
- New report: `design/research/2026-09-18-deep-research.md`. New controlling
  handoff: `reviews/opus-execution-02-answer-path.md`. Older learning prompts
  have supersession notices. The 30-minute total local training limit replaces
  their budget; it is not additive. At most two focused diagnostic adjustments:
  whole-Think residual gating and separate pre-think card access.
- TST remains a separate conditional pilot after a working ordinary baseline.
  No paid run, long-term architecture replacement or additional rental budget
  is authorized. Generator/source/data must be frozen for compared runs.
- Computer use located the correct Claude conversation and confirmed Opus 5 /
  Ultracode. At this log entry, prompt dispatch is NOT verified: native window
  interaction failed, and Ben was asked to focus the composer. The handoff file
  exists and is ready; do not infer that milestone 2 has started from this entry.
- Ben explicitly authorized one Codex usage reset at <=10% remaining in the
  five-hour window. A live check reached 1%; one reset was redeemed successfully
  and a follow-up showed 98% remaining, with one credit left. This is separate
  from GPU rental spending, which remains $0.00 / $30.00.

**Opus milestone 2 — answer path (run m02-20260918-232457, 2026-09-18 23:25 to 2026-09-19 00:20 EDT; report reviews/opus-milestone-02-m02-20260918-232457.md):**
- *Result (toy diagnostic; gold evidence; synthetic vocabulary; `full_verdict: false`).*
  - Original D reproduces the gold-card failure: test scores are 112/1024 and 111/1024 on two seeds, against
    6.25% chance.
  - The bisection localises it to Think. With writer cards, no Think gives 477/512 and one Think pass gives
    55/512. With oracle cards, both arms reach 512/512.
  - Think's learned update writes a large row-shared vector. The median pairwise cosine after the decoder norm is
    0.994, and the loop-step embedding is not the source (norm 0.14–0.16). The writer card's value decodability
    also degrades, from 984 to 622 of 1024.
- *Result.* Both bounded adjustments pass the first gate (≥95% held-out with writer gold cards and fresh bindings).
  - D-think-gated and D-card-bypass each score 1024/1024 on the untouched test split, on seeds 0 and 1.
  - Their answers follow a consistently changed relevant fact (256/256 both correct) and ignore an unasked fact
    (256/256 unchanged).
  - They fall to chance when the card is removed. Trained D-noask stays at chance (42/512).
- *Result.* Neither makes Think useful.
  - The gate stays near zero (α = −0.025 and +0.001).
  - With gold plus 1–3 distractor cards: bypass 674, 545, 444 of 1024; gated 302, 192, 179.
  - Under D's full curriculum with own retrieval, the bypass reaches recall@4 1.00 but a constant answer. It
    scores 54/1024 on test; the gold-card and card-removed evaluations are also 60/1024 on validation.
  - The matched D-noask own-retrieval comparison was conditional on own retrieval working, so it was not run.
- *Recommendation (not adopted).* Keep both variants as diagnostics only. The next bottleneck is question-dependent
  Think computation without collapse: choose among supplied cards, then combine two. Each should come with a
  trained no-Think control and a final-loop-only-supervision control, before retrieval, TST or halting work.
- *Engineering changes (adopted, additive).*
  - `premonition/answer_path.py` (variants), the harness `scripts/premonition_m02_answer_path.py`, and
    `tests/test_premonition_answer_path.py`: 114 tests total, one skipped.
  - Original D source unchanged: `model.py` `f6d8c360…`.
- Training 1,196.2 s of the 30-minute cap. Rental $0.00 / $30.00.

**Opus overnight run ovn-20260918-235851 (2026-09-18 23:59 to 2026-09-19 08:00 EDT)**
Report: `reviews/opus-overnight-2026-09-19-ovn-20260918-235851.md`. Research note:
`design/research/2026-09-19-overnight-research-note.md`.

- *Results.* These are toy diagnostics on synthetic vocabulary, and the supplied-card results use gold evidence.
  `full_verdict: false`. Most runs used one seed.
  - Reading a supplied fact is fixed wherever the card keeps the value: ladder test 512/512, 323/323 and 189/189.
  - Choosing among mirror decoys was not learned from the answer loss by any variant. The variants tried:
    - the trained no-Think model;
    - bypass, gated, centred and final-loop-only;
    - the question-aware read.

    Test scores were ≤ 182/512, against a question-blind ceiling of 53.7%. An irrelevant change flipped 150 of
    256 answers.
  - Evidence-supervised retrieval with top-1 and a read-only reader:
    - default curriculum: retrieval is learned, reading is not (32/512);
    - long reading phase: seed 0 reads but retrieves poorly, and seed 1 retrieves but does not read (27/512);
    - seed 0 at 3745 steps: test 356/512 one-hop and 154/323 practised two-hop, but 14/189 held-out two-hop,
      where the second card was fetched once;
    - D-noask (the full-history memory control) scores 41/512.
  - **Mechanism, measured.** One softmax pool per card concentrates 70–98% of its mass on one or two tokens.
    - Answer-only training puts 0.979 on the value token, so the person is lost (116/2048).
    - Retrieval-dominated training puts 0.71 on the relation and 0.02 on the value, so the value is lost
      (125/2048).
    - Reader states keep both in every checkpoint (2304/2304).
  - Also measured:
    - Final-loop-only supervision made no difference (164 against 169 of 512).
    - The row-centred Think update blocked reading (64/512).
    - The gate stayed near zero (0.042).
    - Held-out two-hop fails at the second lookup: 139 of 171 first cards fetched, 0 of 171 second cards.
    - The second lookup asks for the wrong relation, taken from habit rather than from the question. On held-out
      questions it asks for the right relation 0 of 171 times (default) and 9 of 171 (4000 steps). On
      practised questions it does so 341 of 341 times.
- *Recommendations (not adopted; Astra and Ben decide).*
  - Next: the two-pool card writer, with separate key and value pools, against the single pool and a fixed mean
    pool, on 2 or more seeds. Handoff: `reviews/opus-next-2026-09-19-two-pool-cards.md`, at most 30 min, local,
    $0.
  - After it: compositional hop-2 queries built from name pointers, then a register-only Think.
  - Postponed: TST (not the bottleneck; algorithmically the same as patch-level training) and continued-learning
    pilots.
  - Astra's `opus-execution-03-solvability.md` is unchanged. Its D-gold arm uses the same single-pool writer.
- *Engineering changes (adopted, additive; no existing file edited).*
  - New source and scripts: `premonition/toy_ladder.py`, `premonition/ovn_variants.py`,
    `premonition/ovn_qread.py`, `scripts/premonition_ovn_ladder.py`, `scripts/premonition_ovn_retrieval.py`.
  - New tests: `tests/test_premonition_ovn.py`.
  - Prepared, untrained and not yet used: `premonition/card_pools.py`, which holds the two-pool and
    mean-pool writers, with `tests/test_premonition_card_pools.py` (6 tests). The suite now has 126 tests,
    1 skipped; see the final check.
  - The analysis scripts stay under `artifacts/opus-ovn-20260918-235851/`.
  - The original D is unchanged (`model.py` `f6d8c360…`).
- *Budgets.* Local Mac only; rental $0.00 of $30.00.
  - Milestone-2 increment tonight: 87.1 s. Its cumulative total is 1,196.2 s of the 1,800 s cap.
  - Exp 1: 1,675.7 s of 1,800 s.
  - Exp 2: 1,715.5 s of 1,800 s.
  - Tonight's ledgers total 3,478.2 s, of which optimizer training is 3,362.9 s.

**Opus milestone 3 — memory-card controls and optional H1 (run m03-20260919-071009, 2026-09-19 06:58 to 07:55 EDT; report reviews/opus-milestone-03-m03-20260919-071009.md):**
- *Results (screens; `full_verdict: false`).*
  - Answer-only choosing, seeds 0 and 1, reading/choosing out of 512:

    | Seed | Original | Mean pool |
    |---|---|---|
    | 0 | 512 / 164 | 363 / 138 |
    | 1 | 485 / 161 | 316 / 125 |

    Mean pooling hurts reading and gives no choosing gain.
  - Relevant-pair both-correct is 0 to 2 of 256 in every arm.
  - Evidence-supervised retrieval, seed 0 only, all arms matched to 1517 steps.
    - The answers are card-blind for the original, mean and two-pool writers.
    - The two-pool writer fetched all gold cards less often on practised two-hop questions (−.11 to −.17 paired, 99%
      upper bound < 0 on validation and test).
    - The value pool did not specialise.
  - H1 gate FAILED. Reading on seed 1 was 485 < 486, and choosing lower bounds of .27 are below the .537 shortcut.
    H1 is implemented and tested but not trained.
  - The retrieval seed-1 set did not fit the cap and was not run.
- *Recommendation (not adopted; Astra and Ben decide).* Repair choosing first with the direct contextual-state reader
  diagnostic from `03-learning.md`, in the answer-only choosing setup, with at least 2 seeds and the same gate.
  Keep H1 ready behind that gate.
- *Engineering changes (adopted, additive; no existing file edited).*
  - New source: `premonition/ladder_triplets.py` and `premonition/paired_objectives.py` (H1, off by default).
  - New harness: `scripts/premonition_pool_controls.py` (v2).
  - New tests: `tests/test_premonition_paired_objectives.py` and `tests/test_premonition_pool_controls.py`. The suite
    now runs 148 tests, OK, 1 skipped.
  - Read-only evaluation of bypass models allowlists only the transient `_reading` decode pointer. Failed
    evaluations are now charged.
- *Budget.* Local Mac only; rental $0.00 of $30.00. Charged 1,149.3 s of the 1,800 s cap, of which training was
  928.9 s.
