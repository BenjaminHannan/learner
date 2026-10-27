# Step 4 — The architecture, version 2

**Name:** the model is **Premonition**. The first fully functioning model will be released as **premonition v1-small** (Ben, 2026-09-18).

2026-09-18. Version 2 revises [version 1](04-architecture-v1.md) after Ben's external review (three independent reviewer passes plus his own audit). The changes are listed at the end. Inputs: [01](01-learning-spec.md), [02](02-options.md), [03](03-issues-and-decisions.md).

The core structure is kept: **a small reasoning core + an immediate episodic memory + a slow learned memory + offline consolidation + an independent synthetic world.** Version 2 makes four commitments that version 1 lacked:
1. Persistent retrieval survives drift in the model's representations.
2. Replay of history is version- and time-aware.
3. External ground truth stays separate from anything the model learns about itself.
4. Every component has to earn its place through causal ablation, not through a bundled stage win.

## Project rule: causal ablation

A component does **not** pass because adding it improves the complete model. It passes only if **removing or lesioning it again removes the improvement**, and only against baselines that get equal compute, equal retrieval budget, and equal information. This extends the old project's W=0 test to every component.

## One picture

```
 BensPC CPU (12 threads, 47 GB)             Mac (M1 Pro)
 ┌───────────────────────────────┐        ┌──────────────────────────┐
 │ VILLAGE WORLD (many at once)  │◄───────│ Bonsai 27B: writes pattern│
 │ grid · narrator · teacher ·   │verified│ banks & stories; verified │
 │ ORACLE (ground truth)         │patterns│ before use                │
 └───────────────┬───────────────┘        └──────────────────────────┘
                 │ microbatched text stream
                 ▼
 RTX 5070 Ti ────────────────────────────────────────────────────────────
 WORKING MEMORY: recent stream + recalled cards + own [think] notes
 CORE: small transformer — predicts, thinks, decides stop vs continue
   ├─ KNOWLEDGE SLOTS: product-key memory layers, learned slowly, sparse
   ├─ EPISODE CARDS: separate retriever (slow encoder), cards re-keyed
   │   in sleep; key = entity + relation; versions + history
   └─ CHECKER: measured only; never authorises training data (for now)
 SLEEP: version-aware replay · repair · consolidate · oracle-approved
        practice · utility-based unit replacement · lesion tests
```

## Source reliability (fixed order)
**World oracle > mechanically verified transformations (patterns that pass the placeholder/no-new-fact checks) > teacher free text (Bonsai) > the model's own output.** Only the first two may create training targets about facts. The model's own output never becomes a target without oracle approval.

## The parts

### 1. World (village on a grid)
- Same as v1: grid of places, people and objects; universal and per-village rules; fresh bursty names; a teacher that states, asks, corrects, demonstrates made-up rules, and changes facts over time.
- **Held out for testing, entirely:** name pools, *narrator templates*, *teacher styles*, and *rule-generator families*. Passing on new names alone only proves the model handles new names.
- **Counterfactual pairs:** nearly identical wording with opposite correct answers, so surface patterns cannot score.
- The world is **deterministic given a seed**. Any past stream can be regenerated exactly from (seed, step range, pattern-bank version), which is what keeps the diary small.
- **Speed requirement:** world generation must never slow GPU training by more than 5%, measured against the learner's actual consumption rate. The old fixed 1.2M tokens/s target is dropped.

### 2. Tokenizer
Unchanged: about 8,000 subword pieces trained on village text plus Bonsai-written simple English; names split into syllable pieces.

### 3. Core
**Scale plan (measured on the 5070 Ti; see 03):**
- Build and debug every component at **4M** (minutes per experiment).
- Confirm each passing component at **28M**.
- Run the life model at about **90M** (≈99k tokens/s, 3-7 GB, room for the library).
- **300M** is this GPU's ceiling (≈32k tokens/s, 12 GB at batch 16, tight with the library). Use it only if the scale check shows clear gains from 28M to 90M.
- 700M does not fit.

**Scale check:** every component that passes small is re-tested at the next size, because some abilities (following instructions, in-context learning) appear only with size and some tricks stop helping. Runs abort if peak GPU memory exceeds 14 GB, because Windows otherwise silently spills to system RAM at about 1/30 speed.

A decoder-only transformer. **Learning is microbatched:** every token contributes to the loss, and weights update once per microbatch (e.g. every ~64k tokens), never once per token.

### 4. Knowledge slots (slow, learned)
- **Product-key memory layers** ([Lample et al. 2019](https://arxiv.org/abs/1907.05242)). Two sub-key tables of 512 combine into 262,144 slots, so each token compares against about 2 × 512 sub-keys instead of scanning every slot, then reads its top ~32 slots. Retrieval cost is **benchmarked before anything is built on it.**
- Updates touch only the slots used, favouring slots used by new material far more than by old.
- **Sparse writes do not imply sparse interference.** Related facts deliberately route to similar slots, and a changing core reinterprets rows it never touched. So we measure old-fact damage against slot overlap, slot-usage entropy, and routing drift over time, with a **fixed hash-routing** control.

### 5. Episode cards (immediate)
- Each card stores the **episode text** (so it can always be re-encoded), a **key** (entity + relation, e.g. "Nera + where"), time, source, importance, version links and history.
- **Drift fix.** Keys come from a **separate retriever encoder**, not the continually changing core. It is a slowly updated copy (an exponential moving average) trained contrastively. Each card records which retriever version keyed it. Whenever the retriever changes, sleep **re-keys every card from its stored text**. Required test: write 1,000 cards, train on unrelated villages, and measure Recall@k without touching the cards, comparing moving, frozen, and slow-plus-re-keyed retrievers.
- **Versions:** same key with a different value is a correction. The newest version is current and the old one is kept as history ("Nera used to live in the mill").
- **Shared vs separate retrieval is an experiment, not a commitment.** Ben's hypothesis is that one similarity space can serve both memories. The default build uses separate retrievers for cards (exact identity + version) and knowledge slots (abstraction), and a shared-retriever arm tests his idea directly.

### 6. Working memory and thinking
- Working memory = recent stream + recalled cards + `[think]` notes; temporary and never saved.
- **Stop vs continue.** The model's own thinking decides via a `done` token. The stop decision is trained to estimate **value(stop now) versus expected value(continue)**. During training, thinking runs are *forced to full length* and the answer is scored at every step, so a path like wrong → wrong → breakthrough → right teaches that continuing past a plateau can pay.
- **No compute cost (Ben's decision).** Long thinking is fine whenever it helps. When extra thinking makes answers worse (drift, loops, losing the question), the per-step scores show the decline and the model learns to stop before it. When extra thinking is harmless but useless, ties go to the earliest step that reaches the best value. Only if a reward-trained stopper is seen idling to the cap with no gain is a tie-breaker added, too small ever to outweigh a better answer. The hard cap stays only as a safety net, and it is set high.

### 7. Checker
Trained on oracle right/wrong feedback about the model's own attempts, and measured for calibration. **It does not authorise training data** while the oracle exists. It is used only to route "unsure" questions to the teacher. Giving it any training authority comes much later, and only with its own ablations.

### 8. Gating
Card write priority = importance × reliability, using the fixed reliability order above. Importance: teacher flags, surprise, reward relevance, corrections. Unflagged items are stored at low priority. The store has a fixed budget; low-priority and consolidated cards are evicted first.

### 9. Learning while awake
- Stream loss on every token, applied per microbatch.
- Teacher/oracle facts → instant card writes.
- **The model's own wrong answers are masked out of the imitation loss.** They receive only the feedback update: push the wrong answer down, train the correct answer. This prevents one gradient training the error up just before feedback trains it down.
- Rule demonstrations → step-by-step imitation, with a copy mechanism.

### 10. Sleep
1. **Repair corrections:** train the current answer up and the superseded one down.
2. **Consolidate:** cards teach knowledge slots (answer with the card visible → train to answer with the card hidden).
3. **Version-aware replay:** diary episodes are replayed **with their time context**. A superseded fact is replayed only as history ("used to"), never as current truth, so replay cannot undo repairs.
4. **Oracle-approved practice:** world-generated problems graded by the oracle. Self-made problems count only when the oracle can grade them.
5. **Maintain:** continual backprop as published ([Dohare et al.](https://arxiv.org/abs/2108.06325)), replacing units by **utility** (contribution to the output, with a maturity threshold), not merely because they look inactive. Rare features can be useful.
6. **Lesion tests:** card hidden *and* slot lesion (see Step 5a).

### 11. Diary and storage
- The diary stores **(seed, step range, pattern-bank version)** plus the model's own interactions (answers, feedback), and regenerates text on demand. Storing raw tokens would grow about **8.6 GB/hour** at 1.2M tokens/s with 16-bit IDs.
- Compaction: interactions older than a horizon are summarised to the facts and corrections they produced. History markers are capped per key.
- The storage audit reports the diary and card growth rate; the life-run budget must stay inside the 100 GB cap (80 GB target).

### 12. Health gauges
Utility distribution, dead-unit fraction, weight size, effective rank, and fresh-task speed, logged continuously. A stress test (tasks changing every few thousand steps) compares fixes in minutes.

## Baselines (serious ones)
| Component | Must beat |
|---|---|
| Episode cards | same-encoder retrieval with equal retrieval budget and equal retrieved tokens; a kNN external memory in the style of [Memorizing Transformers](https://arxiv.org/abs/2203.08913) |
| Knowledge slots | core with equal parameters and compute; core + replay; external-memory-only; hash routing |
| Gating | FIFO, LRU, reservoir sampling, surprise-only, teacher-flag-only, at the same budget |
| Thinking + stop | fixed-K thinking at the **same average compute**, not only no-thinking |
| Continual learner | core + replay; external-memory-only |
| Transfer | an **age-matched** model given equal tokens, updates and compute on irrelevant or permuted village experience, not only a fresh network |

## Build order (one component per step, each lesioned)
| Step | Adds | Passes when (vs baselines above; lesion removes the gain) |
|---|---|---|
| 0 | Test bench | Metrics, read-only mode, ablation/lesion harness, holdout splits, leak detectors and baseline slots run on a toy stream |
| 1 | World v0, tokenizer, plain core (childhood) | ≥ 90% on visible-text questions with **held-out templates, teacher styles and rule families**; counterfactual pairs above chance; forgetting baseline recorded; world ≤ 5% bottleneck |
| 2a | Continual-training recipe (utility replacement etc.) on the plain core | Stress test keeps fresh-task speed ≥ 90% of a new network; removing the recipe loses it |
| 2b | Knowledge slots (product keys) | Less forgetting than an equal-compute core and core + replay; zeroing the slots removes the gain; damage-vs-overlap measured; beats hash routing |
| 3a | Retriever + drift test | Recall@k after unrelated training: slow + re-keyed ≥ frozen and ≫ moving |
| 3b | Episode cards | Beat same-encoder retrieval and kNN memory on reworded / pronoun questions; removing cards removes the gain |
| 4 | Gating | Beats FIFO/LRU/reservoir/surprise-only/flag-only at the same budget |
| 5a | Consolidation alone | With the card hidden, the fact is answered; **zeroing the slots written during consolidation removes it**; a core-only control shows the slots are doing the work |
| 5b | Version-aware replay | A→B→C→A fact flips under full replay: no old-answer rebound; plain replay shows the rebound it prevents |
| 5c | Repair | Corrections hold after further learning; removing repair brings relapse back |
| 5d | Oracle-approved practice | Skill gain that disappears when practice is removed |
| 6a | Thinking (fixed K) | Beats no thinking on multi-step questions |
| 6b | Stop decision | Beats fixed-K at the same average compute; thinks longer on harder questions |
| 6c | Checker | Calibrated; used only for routing |
| 7 | Instruction imitation, reward, acting | Follows unseen rule families; improves from feedback |
| 8 | A life (overnight) | Transfer beats the age-matched control; health gauges stay healthy; storage within budget |

## What stays from the old project
The test discipline (fresh names, read-only evaluation, answers never in model inputs, bit-exact checkpoint restart, W=0-style causal checks), the BensPC tooling, and `memorylab/` as baselines. The old rule "reading memory never writes" becomes: a recall may *flag* a card for repair; all changes happen through gating or sleep, never during tests.

## Changes from version 1 (after Ben's review)
1. **Stale keys (blocker):** a separate slow retriever, card text stored, re-keying in sleep, and a drift test.
2. **Replay vs corrections (blocker):** version- and time-aware replay; superseded facts replayed only as history; A→B→C→A rebound test.
3. **Reliability order was backwards:** now oracle > verified transformations > teacher > model.
4. **Sparse writes ≠ sparse interference:** overlap/entropy/drift measurements and a hash-routing control.
5. **Memory lookup cost:** product keys, benchmarked first.
6. **Circular checker:** the oracle approves practice; the checker has no training authority.
7. **One cosine space for everything:** separate retrievers by default; shared is a tested hypothesis (agreed by Ben).
8. **Stopping regressed:** value(stop) vs expected value(continue) from forced full trajectories; no compute cost (Ben), with collapse handled by per-step scoring.
9. **Bundled stages allowed false victories:** one component per step and the causal-ablation rule.
10. **Baselines too easy:** replaced by the table above, including the age-matched transfer control.
11. **Template leakage:** whole templates, styles and rule families held out; counterfactual pairs.
12. **Smaller:** microbatched updates; the model's own wrong answers masked from imitation; the diary regenerated from seeds and compacted; the 1.2M tokens/s target replaced by "≤ 5% bottleneck"; utility-based continual backprop.
