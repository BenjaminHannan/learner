# Premonition: research-level review and strategy

I'm Ben, a student building my own AI model, **Premonition**, with Claude as my engineering partner. Code review is already done: an adversarial pass found 28 issues and we've fixed or scheduled all of them. What I want from you is the **research-level** view:
- Is the core idea sound?
- Where is it naive?
- What would make it genuinely strong?
- What should we do next?

Please be direct and specific. I'd rather hear "this part is a dead end, do X instead" than polite encouragement.

If you can read files, the repository is at `/Users/ben-hannan/Desktop/projects/beautiful-model`. Key files:
- `design/06-premonition-mini-spec.md` (Experiment 1 spec, with §9 overriding it after the review)
- `design/research/2026-09-18-decisions-log.md` (every design decision)
- `design/research/2026-09-18-motivation.md`, `design/research/2026-09-18-novel-mechanisms.md`, `design/research/2026-09-18-fresh-names.md` (research memos)
- `reviews/codex-review-prompt.md` (what the code review covered)
- the code: `premonition/`, `learnlab/`

If you can't read files, everything essential is summarised below.

---

## 1. Goal

A model that **genuinely keeps learning over its life**, not a frozen network with memory bolted on. Human learning is inspiration, not a constraint. Priorities:
1. Reasoning first, language second.
2. **Make intelligence more efficient**: accuracy per weight, per unit of compute and per training token.

Constraints: one person plus AI assistants. Compute is rented GPUs (vast.ai; RTX 4090/5090 at about $0.4–0.5/hour each). Budgets are tens of dollars per experiment, not thousands. We plan to scale up later.

## 2. The world it learns in

A procedurally generated text **village**:
- **The world:** a grid of places, people with made-up syllable names (fresh names in every village; held-out villages use names never seen in training), objects and containers, and per-village made-up rules (e.g. "glass breaks", "Tavi follows Nera").
- **The narrator** describes events.
- **The teacher** states facts, asks questions, gives feedback and corrects mistakes.
- **The checker (oracle)** knows every true answer and the exact evidence lines each answer depends on.
- **Question types:** where things are, who holds what, counts, directions, "what if", "why", multi-step plans and rules, with derivation depths 1–6. Held-out splits use unseen question templates, unseen teacher styles and deeper questions.
- **Test discipline:** read-only evaluation, answers never in the input, leak detectors (dumb guessers that must not beat chance) per answer class, and counterfactual twin visits that change one fact.

## 3. The architecture we agreed (long-term)

- **Split:** a small **skills-only reasoner** plus a separate **knowledge store**.
  - The store has a permanent raw **diary**, instant **cards** (like the hippocampus: key, value, time, source, confidence, version, pointer into the diary) and slow **knowledge slots** (like the cortex: a sparse memory-layer table).
  - Boundary: instance-specific, mutable, source-attributed facts go in the store; reusable schemas, language and procedures go into weights.
  - **Wipe-store test:** fact questions must fail without the store while reasoning over visible facts survives.
  - Two recall routes: automatic "familiarity" (the slots) and deliberate ASK (cards). The model's own inferences are stored as "inferred", at lower trust, and never overwrite observations. Slots may fade to the gist.
- **Thought space:** an encoder produces a **scene** of 16–32 entity slots, plus **thought steps** of 2–4 discrete codes from a learned codebook (a private language; pointer codes to slots; ASK and DONE codes). A decoder maps back to English. Names are pointers; spellings live in the store.
  - The codebook **keeps growing**, stabilised ART-style: new codes are born only in sleep when thoughts repeatedly fit no existing code; young codes are plastic and old ones harden; codes split rather than being overwritten; IDs are permanent; example sentences are checked for drift.
  - The teacher can also name concepts (provisionally), and the model can ask "what's this called?".
- **Training plan:**
  1. Build the thought space (round trip, paraphrase agreement, grounding to the simulator's world state).
  2. JEPA-style prediction of the next scene, with whole entities knocked out.
  3. Imitation, with words gradually replaced by codes.
  4. RL, rewarded only by the simulator's checker. The model's own checker head never gives reward, and decoded thoughts are for reading, never for reward.
- **Sleep:**
  - **Weights change only in sleep; cards change any time.**
  - Triggered by "consolidation pressure" (store fill, unconsolidated facts, health gauges), a learned body clock, and naps.
  - Runs on a background copy as a **transaction**: it commits only if checks pass, otherwise rolls back.
  - Deep-sleep phase: corrections first, consolidation interleaved with old diary material, reverse replay of successful thought traces, shrink-and-perturb plus resetting dead units, fading details to the gist.
  - Dream phase: recombining facts into new scenarios (rewarded only if the simulator can build and check them), inventing and splitting codes, and anchor drift checks.
  - Consolidation uses self-tutoring: a copy that can see the card teaches the copy that can't. A told-ledger records exactly what the model was told.
- **Drives:**
  - Mastery (learning progress chooses self-chosen practice; never abandons tasks a user assigns).
  - Gap curiosity (what to ask or look up; paid only when ground truth confirms).
  - Replay priority.
  - Effort (how long to think).
  - Fixed limits: consolidation pressure and a hunger-like compute budget.
  - No novelty bonus, approval reward, resource-seeking or self-preservation drives.
- **Inputs:** time, a speaker/source tag, its own internal state (readable, not writable), and later a partial map view and body sense.

## 4. Evidence so far

- **Transformer baseline** (4M and 28M weights, 10–60 minutes on a 4090/5090, about 0.7–1.5B tokens):
  - 52–72% on held-in questions but only **10–16% on held-out** ones, regardless of size or training time.
  - It fails counterfactual twins (below chance) and multi-step plans (about 0–5%).
  - It saw the 100k visits 10–15 times, so it memorised.
- **0% on answers that are fresh names.** A tokenizer bug: the old tokenizer made 262 train names single tokens and split every held-out name into rare pieces. Now fixed; nothing has been retrained yet.
- **Leak work:** most generator shortcuts are fixed. Two real priors remain (in "who has X?" and "what's in the box?", a blind guess reaches about 2× chance). They're guarded by the twin test and excluded from decision cells.

## 5. Experiment 1 (being built now)

**Question:** does a ~2.1M-weight reasoner with a per-visit card store beat plain transformers on village reasoning, at equal compute and with fewer weights?

- **D (Premonition-mini)**, d = 128:
  - a minGRU recurrent reader plus 64-token block-local attention, reading the whole visit label-free (earlier answers and feedback stripped, for every contender);
  - every non-question line becomes a card (key 64, value 128);
  - names are replaced by 16 entity IDs using a rule, with exact spellings in a per-visit name table;
  - a think block (2 layers, shared) looped up to 8 times over question rows, 16 entity slots, up to 16 fetched card rows and 4 registers, with ASK (top-4) and HALT heads;
  - a decoder that copies entity spellings.
  - Losses: next token (answers masked), ASK as set cross-entropy imitating the oracle's reachable evidence cards, deep-supervised answers, and HALT from own-retrieval rollouts.
  - Curriculum: gold cards → teacher-forced cards → own retrieval.
- **Contenders:**
  - A: the "4M" transformer preset (5.0M weights), 736-token prompt
  - B: 13.4M and 28.9M transformers
  - C: A + BM25 lookup
  - C2: A + a learned dense retriever with the same oracle labels
  - E: A on anonymised text (names → entity IDs)
  - controls: D-noask (no cards), D-noptr, D-no-oracle
- **Claims:**
  - *Store claim* = D vs D-noask.
  - *Efficiency claim* = D vs A, B, C, C2, E. These are compared at matched FLOPs (a measured counter plus the recurrent scan and retrieval) and also at matched tokens, with at most about 3 passes over the data.
- **Tests:** near/far relative to A's window, multi-hop 2–5, changed facts, fresh names, long visits (~2–3k tokens, against the usual ~1.1k), and separate wipes (cards / name table / reader state).
- **Statistics:** visit-clustered bootstrap with one-sided 99% bounds, for non-inferiority (> −3 points), superiority (> +10 points), and a kill rule (the upper bound on D − C on far ∩ depth ≥ 2 is below +5 points).
- Built and tested so far: the name pointerizer (precision = recall = 1.0), the data pipeline, the model (2,102,228 weights), the store and FLOP counting, and the evaluation slices and decision rules. The trainer, the contenders and the §9 fixes are in progress.

## 6. What I want from you

1. **The core thesis.** Is "small reasoner + external store" a real route to more efficient intelligence, or will a well-tuned transformer with retrieval always match it? What does the recent literature (2025–2026 especially) say? What is our honest novelty relative to RETRO, memory layers, Titans / nested learning, recurrent-depth reasoners (HRM/TRM), JEPA, and "Language Models Need Sleep"?
2. **Experiment 1.** Is it the right *first* experiment? Would a win be convincing to a skeptical ML researcher, and what one change would make it much more convincing (or much cheaper)? Is the village too easy or too artificial to transfer? What result would make you say "stop, change direction"?
3. **Architecture weak points.** Name the 3–5 decisions most likely to fail in practice (e.g. the growing codebook, sleep-only weight updates, rule-based name pointers, the skills/facts boundary, RL in a discrete private language, drives) and a better alternative for each.
4. **Continual learning.** This is the headline goal. What is the smallest experiment that would show *lifelong* learning (new villages learned faster over time, no forgetting of old ones) better than standard baselines (fine-tuning, replay, EWC, LoRA-per-task, retrieval-only)? What are the right metrics?
5. **What would make this genuinely impressive**, the kind of result people would pay attention to, within a budget of about $50–200 of GPU time? Be concrete about the task, baseline and number.
6. **A roadmap:** the next 5 experiments in order, each with its question, cost, success criterion, and what we do if it fails.
7. **Anything we're blind to**: failure modes, wasted effort, or a much simpler design that would get 80% of the benefit.

**Format:** lead with a one-paragraph verdict, then sections 1–7. Cite papers with year and authors, and mark anything you're unsure of as uncertain. Prefer concrete numbers and designs over general advice.
