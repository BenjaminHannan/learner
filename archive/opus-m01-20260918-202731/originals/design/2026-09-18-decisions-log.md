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
