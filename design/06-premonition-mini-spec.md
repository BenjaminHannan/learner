# 06 — Premonition-mini: implementation spec for Experiment 1

2026-09-18, draft for Ben. The source of truth is the design agreed today (reasoner/store split, names as pointers, cards). [03](03-issues-and-decisions.md) and [04](04-architecture-v1.md) still govern the world, the test discipline and the hardware. **Left out on purpose:** the growing codebook, sleep, drives, RL, knowledge slots and abstract codes. Anything not confirmed in code is marked **ASSUMPTION**.

## 0. What Experiment 1 decides

Does a ~2M reasoner with a separate card store beat plain transformers on village reasoning at equal training compute?

| | Model | Weights | Sees per question |
|---|---|---|---|
| A | `Core` 4M preset (256 × 4) | 4,987,392 | last 768 tokens |
| B12 / B28 | `Core` 384 × 6 / 512 × 8 | 13.4M / 28.9M | last 768 tokens |
| C | A + plain lookup (§5) | 4,987,392 | recalled lines + window, 768 in total |
| D | Premonition-mini | 2,013,140 | whole visit so far + card store |
| D-noask / D-noptr | controls: no store / names as ordinary tokens | ≈2.0M | as D |
| E | A on anonymised text: D's pointerizer replaces names with `ENT` ids, shuffled per visit; answers detokenised from the name table | 4,991,488 | last 768 tokens |

D changes two things at once, the store and the name pointers, so the controls are needed to tell which one helped. **E** is the strongest cheap competitor (fresh-names memo, §4): it gets the pointers without the store. D vs E is the cleanest test of the store; if D can't beat E on far and multi-hop questions, the store isn't earning its keep.

**Tokenizer (2026-09-18).** The first baselines used `premonition-tok-v1-fallback.json`, which has no syllable splitting: 262 train names were single tokens and every held-out name was 2-5 rare pieces, which alone explains their 0% on fresh names. Every contender uses the syllable-splitting tokenizer (v2), with the step-1 name-tokenization audit clean; A is re-run with it before any comparison.

## 1. Architecture of D

d = 128 everywhere. Vocabulary: 6,372 tokenizer ids + 16 entity ids `ENT0-15`.

```
raw visit ─ pointerizer (no weights): names → ENT ids, spellings → name table
  ▼
READER  [minGRU · local attention W=64 · minGRU], causal over the whole visit
  ├─ each token → tied next-token head                            (L_lm)
  └─ each line end → CARD WRITER → store (key 64, value 128, line, tag)
  ▼ at "[answer]" of each question
THINK  rows: question (≤40) · 16 entity slots · fetched cards (≤16) · 4 registers
  shared 2-layer block looped t = 1..8; register 0 drives ASK (top-4) and HALT
  ▼
DECODER  1 block, cross-attends think rows; ENT e → spelling from the name table
```

| Module | Shapes | Params |
|---|---|---|
| Token embedding, tied output | [6,388, 128] | 817,664 |
| Reader: 3 layers of mixer + MLP ×3. minGRU: 128→384 gives (z, h̃, gate); h_t = (1−z)·h_{t−1} + z·h̃ via a log-space parallel scan (fp32). Layer 2: block-local attention (4 heads, RoPE; each 64-token block sees itself and the previous one) | [B, T, 128] | 496,384 |
| Card writer: attention pool over the line, key 128→64 + L2 norm, value 128→128, learned NULL card | line → k [64], v [128] | 25,089 |
| Think: 2 transformer layers (4 heads, MLP ×4) 396,544; row-type, register, loop-step and age embeddings plus recency biases 4,112; slot binder 256→256 65,792 | [N_q, 76, 128] | 466,448 |
| Heads on register 0: query 128→64, ASK, HALT, temperature κ | | 8,515 |
| Decoder: causal self-attention, cross-attention to think rows, MLP ×2 | [N_q, ≤32, 128] | 199,040 |
| **Total** (non-embedding 1,195,476) | | **2,013,140** |

Slot e starts as E[ENT e]: an identity with no spelling and no content.

**How weights are counted.** Every trained parameter counts, embeddings included, which is the same rule behind A's 4,987,392 in the step-1 report. The store holds no trained weights: it is data written while reading, reported separately as working memory at answer time. D holds at most ~140 cards × 192 bf16 values ≈ 54 KB plus ~1,200 token ids. A's KV cache is 4 × 2 × 768 × 256 values ≈ 3.1 MB.

## 2. The card store (v1)

**Scope.** Episode-scoped: built from the visit being read and discarded at its end. It covers the diary and cards of the agreed store, without versions, consolidation, inferred cards or the told-ledger. **Decided:** it is rebuilt from the input like a KV cache, so building it during a test does not break "no card writes while testing". Later persistent stores go through `read_only(model, stores=[...])`.

**Which records become cards.**
- **Carded:** every non-question line (`[world]` narration and rules, `[teacher]` facts, demonstrations and changes).
- **Never carded:** question lines, because they show earlier answers (step 1's `repeat_in_context`).
- **No card needed:** silent rule firings have no line. The oracle derives them from the rule and time lines (`Observer._derive`), and those lines are cards.

**Card fields.**
- key (64 dimensions, unit length) and value (128 dimensions);
- line index and source tag (the line's first token);
- the line's token ids (the diary pointer) and the ENT ids it mentions.

Confidence is 1 and there are no version links: recency sits in the score, and "newest wins" is learned because the evidence always points at the newest statement.

**Encoding.** p = attention-pool of the reader outputs over the line; k = normalize(W_k p); v = W_v p. The reader is recurrent, so p also carries context from earlier lines.

**ASK.** q = normalize(W_q r₀). Score s_i = κ·q·k_i + b_age[min(15, ⌊log₂ age⌋)], over cards with line_i < line_q plus NULL. A visit has at most ~140 cards, so every card is scored. Inference takes the top 4.

**Into the think space.** Each fetched card becomes a row (v_i + age and row-type embeddings; at most 16 rows, first in first out). For each ENT e the card mentions, the binder updates the slot: [g, c] = (σ, tanh)(W_b[s_e; v_i]), then s_e ← s_e + g·(c − s_e). A NULL row teaches "nothing found".

**Names as pointers.**
- **Detection.** The tokenizer lowercases (`"lowercase": true`), so the pointerizer reads the raw text. A name is a capitalised word that is not a literal template word and never occurs lowercase in train text.
- **Binding.** The first mention takes the next ENT id, randomly permuted per visit during training, and writes `ENT e → exact spelling` to the name table, which is part of the store.
- **Copying.** The reasoner answers `ENT e` and the detokeniser substitutes the spelling. A fresh name is copied exactly, never generated.
- **Capacity.** A village has 5-12 people plus one village name (`scheduler.Village.__init__`), so 16 ids suffice. Places and objects come from the closed shared vocabulary (`vocab.PLACES/OBJECTS/COLOURS`) and stay ordinary tokens.
- **ASSUMPTION:** nothing else passes the name rule. Build step 2 checks this against the cast lists.

**Wipes (evaluation only).**
- **W-full:** at the start of A's 768-token window, reset the reader state and empty the store and name table, then re-read the window, so D sees what A sees.
- **W-store:** empty the store and name table (names in the window are re-added) but keep the reader state. This measures what the recurrence alone carries.

## 3. Training

**What the data provides (checked in code).**
- Shard question rows carry `evidence_text_lines`, `depth`, `knowable`, `visible` and `text_line` (`stream.render_visit`, `shards._shifted`); `step1.read_questions` exposes them as `Question` fields.
- Evidence is the unordered set of narrated lines the shortest derivation read (`oracle.Deriv.evidence`, a frozenset). On the small cache it averages 1.8 lines in train and 2.6 in validation (maximum 8), none unrendered and none on question lines.
- Train depth is at most 3; validation and test reach 6 (`scheduler.MAX_DEPTH`).

G = the cards on a question's evidence lines; F = the cards already fetched.

| Loss | Definition | Weight |
|---|---|---|
| L_lm | next-token cross-entropy on the pointerized stream, answer spans masked, so answers are learned only through the think path | 1 |
| L_ask | at loops whose target is ASK: set cross-entropy −log Σ_{c∈G∖F} softmax(s)_c, plus binary cross-entropy (BCE) on the ASK logit (ASK while G∖F ≠ ∅). A never-told question has G = {NULL} | 0.5 |
| L_ans | decoder cross-entropy at every loop (deep supervision); weight ×0.2 before the loop that fetches the last gold card | 1 |
| L_halt | BCE; target = every answer token argmax-correct at this loop | 0.1 |

The weights are an **ASSUMPTION**, tuned on validation in build step 5. The set target needs no hop order; chaining can emerge because each query follows the cards already in the slots.

**Cards during training.** Teacher-forced: G∖F (up to 4) plus 1-2 random distractors. Own: the model's top 4, used with probability p_own.

**Curriculum** (share of D's FLOP budget):

| Share | Phase |
|---|---|
| 0-5% | L_lm + L_ans; gold cards loaded before loop 1; 2 loops |
| 5-30% | add L_ask and L_halt; teacher-forced cards; ⌈\|G\|/4⌉ + 3 loops |
| 30-100% | p_own rises 0 → 0.75 by 60%, then stays flat; ≤ 8 loops |

**Optimisation.** AdamW with `Trainer`'s parameter groups, lr 1e-3, warmup 100, clip 1.0, bf16 (the scan runs in fp32). Batches are whole visits bucketed by length (~48 visits ≈ 55k tokens). All questions in a batch are stacked into one think tensor [ΣQ, 76, 128].

## 4. Compute matching

**Primary: equal training FLOPs.** Convention (2026-09-18): FLOPs are what `premonition/flops.py` counts (`FlopCounterMode`, full attention, backward recompute included) for every contender; the hand formula below undercounts `Core` by 15.6% and is kept only as a sanity check.
- **Budget.** F = the FLOPs of A's fair baseline run with the v2 tokenizer: trained until held-out accuracy and binding stop improving (the 10-minute run was 128 × 768 batches, 600 s on the 5090, 771,981,312 tokens; the 1-hour 4M/28M runs set the scale). By hand: 3 × (2 × 3,159,040 + 2·L·ctx·d + 2·V·d) = 33.5 MFLOP per token, so F ≈ 2.6e16.
- **Measurement.** `flops.py` counts forward and backward passes on real batches with `torch.utils.flop_counter.FlopCounterMode`; for D it fits FLOPs per batch = a·tokens + b·Σ(questions × loops). The counter skips elementwise work such as the scan, so it must be within 15% of the hand count.
- **Stopping.** Each trainer stops at F ± `policy.BUDGET_TOLERANCE` (5%). Expected tokens: B12 ≈ 290M, B28 ≈ 136M, C ≈ 770M, D ≈ 1.4B (≈18 MFLOP per token by hand).

**Secondary: wall-clock** on the same GPU in one session, for every run, plus D at 600 s. More than 3× A's seconds per FLOP is an engineering problem, not a kill. Inference FLOPs per answered question are also reported.

## 5. Contenders A, B and C

- **A.** Step 1 exactly: `Core(CoreConfig.preset("4M", 6372, 768))`. Re-score the existing checkpoint if the data tag (`large-seed0-c1f08f7642d2`) matches.
- **B.** `CoreConfig(6372, 768, 384, 6, 6)` and the "28M" preset, lr 6e-4. "B" is the better of the two.
- **C (plain lookup).**
  1. **Candidates:** non-question lines of the same visit that come before A's window start.
  2. **Score:** BM25 (k1 = 1.2, b = 0.75, IDF from train lines). The query is the question's words minus stopwords, names kept.
  3. **Select:** the top 8 with score > 0, newer lines winning ties, while their total is ≤ 192 tokens, then back in chronological order.
  4. **Input:** recalled lines, `<bos>`, then the window cut at whole lines to fill 768 − 32 tokens (`build_items` logic), then the question up to `[answer]`. **ASSUMPTION:** `<bos>` never occurs in the stream.
  5. **Training:** half plain stream rows, half question-centred rows (answer and feedback included, recalled block loss-masked). Each row is exactly 768 tokens starting with a masked `<eos>`, which keeps `Trainer._next_batch`'s one-token overlap aligned.
  6. **Diagnostic:** gold recall@8 on far questions (`metrics.recall_at_k`).

## 6. Integration

```
premonition/
  config.py  MiniConfig; asserts 1.9M ≤ params ≤ 2.15M (v2 tokenizer: 2,102,228)
  pointer.py name detector, pointerize / detokenise, NameTable
  data.py    visit cache (uint16 tokens, line offsets/kinds, question table with answer spans,
             gold card ids, slice tags, name tables); length-bucketed collator; long_visit generator
  store.py   CardStore: write / ask / wipe / fingerprint
  model.py   Reader, CardWriter, Think, Decoder, PremonitionMini
  train.py   MiniTrainer(learnlab.train.Trainer): overrides _next_batch/_step; FLOP stop; curriculum
  lookup.py  BM25; C training rows and evaluation items
  flops.py   FLOP measurement and budgets
  slices.py  slice tags, including the changed-fact replay
  exp1.py    train / evaluate / report / verdict for any contender
tests/test_premonition_*.py
```

**Reused unchanged (no edits to `learnlab/`):**
- `step1`: `build_data`, `generate_split`, `read_visits`, `read_records`, `read_questions`, `build_items`, `score_items`, `greedy_decode`, `stop_ids`, `exact_match`, `plan_works`, `summarize`, `breakdown`, `cell`, `name_gap`, `gated`, `cached_leak_report`;
- `train`: `Trainer`, `TrainConfig`, `MemoryGuardError`;
- `readonly.read_only`; `ckpt`: `save_checkpoint` / `load_checkpoint`;
- `metrics`: `paired_greater_pvalue`, `wilson_interval`, `recall_at_k`; `policy` constants.

**CLI.** A new `run.py` subcommand. `remote_benspc.sh launch` passes it through, because it only checks argument characters.
```
python run.py premonition train   --contender {A,B12,B28,C,D,D-noask,D-noptr,E} --budget-from <A report> --visits large --seed 0
python run.py premonition eval    --checkpoint <ckpt> --split validation [--wipe full|store]
python run.py premonition verdict <reports...>
python run.py premonition smoke   # CPU
```

**Evaluation changes.** `Question` and `EvalItem` already record depth, visible, knowable, evidence, `evidence_kept`, `repeat_in_context`, `name_answer`, `template`, `style_status` and `changed_since_asked`. Added:
1. **Canonical cut.** near = knowable ∧ `evidence_kept`, and far = knowable ∧ ¬`evidence_kept`, both under A's cut (`build_items`, max_len 736). Tags are keyed by question id and apply to every contender. Step 1's `visible` measures 2,048 characters and 40 records, not the model's window.
2. **Sets.** Use all validation questions for development and all test questions once, for the verdict. This replaces `build_eval_sets`' samples. Every decision cell needs ≥ `MIN_ITEMS` (100) items; the target is 400.
3. **Multi-hop** = knowable ∧ depth 2-5, also reported per depth. Depths 4-5 are untrained for every contender.
4. **Changed facts.** Replay the visit with `scheduler.generate_visit`, patched as in `step1.capture_asks`, and call `oracle.ask(obs, world, bank, slots)` after each earlier record. The question counts as changed if an earlier knowable answer differs. Also report "stale": the prediction equals an older answer.
5. **Fresh names.** Held-out answers containing a detected name. `name_like` needs the name inside the kept window, so it cannot serve. Seen names come from held-in train questions (`name_gap`).
6. **Reworded** = unseen template or style. **Not told** is reported but not gated.
7. **Far-long.** `validation-long` / `test-long` splits from `long_visit`, which calls `generate_visit(..., days=4)` through `generate_split(extra={"generator": ...})`. `build_oracle` replays without `days`, so these splits use text signatures. **ASSUMPTION:** visits of ~2-3k tokens.
8. **Exclusions.** Remove repeats (`gated`) and leak-flagged answer classes (currently who-has and box contents) from decision cells, and report them separately.

**Decision rules.** Paired on the same items, α = `policy.ALPHA` = 0.01, p from `paired_greater_pvalue`.

| | Rule |
|---|---|
| Pass 1 | near: D ≥ A, and A is not better by 3 points (p(A > D + 0.03) ≥ α) |
| Pass 2 | far, and multi-hop 2-5, each separately: D beats A, C and E by ≥ 10 points, each significant at margin 0.03 |
| Pass 3 | overall: the better B is not significantly better than D by 3 points |
| Pass 4 | W-full: D's far accuracy ≤ A's far + 3 points, and near ≥ 90% of D's unwiped near |
| Kill | far ∩ depth ≥ 2: D is not significantly above C |

## 7. Tests, smoke run, risks

**Unit tests:**
1. The name detector scores ≥ 99.9% against the cast lists, with an exact round trip.
2. No card at or after the question's line is scored; NULL is always eligible.
3. D's inputs never contain the answer.
4. Evaluation passes `read_only`; a planted parameter write raises `ReadOnlyViolation`.
5. The parameter count is within the band, and every gold line maps to a card.
6. With planted keys, the set cross-entropy falls to ≈0.
7. After a wipe, ASK returns only window cards or NULL.
8. The FLOP counter on `Core` is within 10% of the hand count.
9. BM25 never recalls window or later lines; C prompts are ≤ 768 tokens and end in `[answer]`.
10. The changed tag fires on a planted twice-moved object.

**CPU smoke** (`premonition smoke`, under 5 minutes): the tiny preset (60 train and 24 held-out visits), D at d = 32, tiny A and C, 60-120 s each. It passes when the losses fall, gold recall@4 beats random, the report contains every slice and the verdict, and `read_only` holds.

| # | Risk | Mitigation |
|---|---|---|
| 1 | Pointers, not the store, explain D's gains | D-noptr and D-noask; fresh names reported separately |
| 2 | Retrieval collapses to NULL | Imitation from 5% on; track gold recall@4; add a contrastive key loss if it is < 50% at 30% of the budget |
| 3 | Exposure bias from teacher-forced cards | Scheduled sampling; report the gap between teacher-forced and own retrieval |
| 4 | D is slow on the wall clock | Stacked think tensor, block-local attention, parallel scan; verdict on FLOPs |
| 5 | D gets ~14 epochs of the 105M-token train set | If train accuracy far exceeds validation, rebuild all contenders on `--visits 300000` |
| 6 | "Far" is shallow: visits ≈1,100 tokens; 26-35% of questions are far | far-long split; compare W-store with W-full |
| 7 | Open leaks | Excluded from decisions; leak detectors run per slice |
| 8 | Test-set tuning; seed noise | Validation for development and test once; 2 seeds for A and D, a third if a margin lands within 3 points |

## 8. Build order (one person with Claude, ≈ half a day to a day per step)

| Step | Build | Passes when |
|---|---|---|
| 1 | `slices.py`; `exp1.py` evaluation for `Core` checkpoints; re-score A on validation | Every decision cell has ≥ 100 items; A matches the step-1 report (10.1% visible held-out) within its confidence interval |
| 2 | `pointer.py`, `data.py` cache | Detector ≥ 99.9%; exact round trip; every gold line maps to a card |
| 3 | `config.py`, `model.py`, `store.py`, `flops.py` | 1.9-2.1M parameters; CPU forward/backward; causality tests; counter within 15% of the hand count |
| 4 | Toy far-fact task (facts plus distractors, queried beyond the 64-token window) | D ≥ 95%; D-noask ≤ chance + 5 points |
| 5 | Village training, curriculum 0-30%; CPU smoke, then 10 GPU minutes | Gold recall@4 ≥ 80% on train; validation near accuracy (teacher-forced) > A's near |
| 6 | Scheduled sampling and halting | Own-retrieval accuracy within 5 points of teacher-forced; loops rise with depth |
| 7 | C, B, E and FLOP-budgeted training for all | Every run lands at F ± 5%; C's recall@8 reported |
| 8 | Validation runs: A ×2, B12, B28, C, D ×2, D-noask, D-noptr, E ×2; both wipes | Complete reports; go/no-go before the test split |
| 9 | Test split once; `premonition verdict` | Pass or kill table for Ben |

## 9. Revisions after the adversarial review (2026-09-18) — these override §0-§8 where they conflict

Two GPT-5.6 xhigh reviews (findings checked against the code by Ben's reviewer) found that an Experiment 1 win under §6 would not have shown that the card store works. Changes:

1. **Label-free inputs (review #1).** No contender's input may contain earlier questions' gold `[answer]` / `[feedback]` spans. D's reader stream drops every answer and feedback span (D answers through its decoder, so it never needs them); Core-based prompts (A, B, C, C2, E) are built from the same label-free prefix. Question text stays. Training streams for Core keep answers (they are its LM targets); only evaluation prompts and D's reader stream are label-free. A "with labels" variant is reported, never gated.
2. **Two claims, two primary comparisons (#2).** *Store claim:* D vs D-noask (identical reader, think loop, decoder and pointers; no cards) at matched FLOPs and loops. *Efficiency claim:* D vs A, B, C, C2, E. A D-noask row that reads the whole visit is also the full-history recurrent baseline.
3. **Matched supervision (#3, #19).** New contender **C2**: A plus a learned dense retriever (same card keys and retrieval budget as D: top-4 per request, up to 16 lines) trained with the same oracle evidence labels, feeding recalled lines into A's window. New control **D-no-oracle**: D trained with answer loss only (no L_ask on gold cards; retrieval learned through straight-through top-k). The store claim requires D > D-noask; the "D beats retrieval" claim requires D > C2.
4. **Statistics (#4, #6).** All tests are paired and clustered by visit: visit-level bootstrap (10,000 resamples) of the accuracy difference, one-sided 99% bounds. *Non-inferiority* (old Pass 1 and 3): the lower bound of D − X is above −3 points. *Superiority* (Pass 2): the lower bound of D − X is above +10 points. *Kill*: the **upper** bound of D − C on far ∩ depth ≥ 2 is below +5 points (evidence that the gain is too small), never mere non-significance. Minimum per decision cell: 60 independent visits and 100 items.
5. **Orthogonal lesions (#5).** Wipes become separate switches in `answer()`: `cards` (empty the store, keep the name table and reader state), `names` (drop the name table only), `state` (reset the reader at A's window start, keep cards), plus combinations; `full` = all three. The factual-store lesion is `cards`: spelling/copy infrastructure stays intact.
6. **Prompt budget (#28).** A's scored prompt is 736 tokens (768 − 32 reserved for output); every lesion and slice uses 736.
7. **Compute (#11, #12).** `flops.py` adds the minGRU scan, norms/gates, card scoring, top-k and binding to D's count (hand-counted, since the counter skips elementwise work); if the addition exceeds 5% of F it is added to F. Same-GPU wall-clock is co-primary for the efficiency claim. Every contender is also reported **token-matched** (same number of training tokens as A), besides FLOP-matched. Data: build enough visits that no contender exceeds ~3 epochs (the 1-hour baselines memorised at 10-15 epochs).
8. **Checkpoint compatibility (#13).** A checkpoint is re-scored only if tokenizer SHA, vocab size, model config and preprocessing digest all match. All v1-tokenizer checkpoints are retired; A is retrained on v2.
9. **Retrieval targets and halting (#16, #17).** L_ask uses *reachable* gold: at each loop, gold cards whose entities already appear in the slots or the question (the others become targets once reachable); the full set is kept as a diagnostic. HALT targets come from own-retrieval rollouts: halt at the first loop after which more loops no longer turn the answer correct (decision 8).
10. **Leak statistics (#7-#10, #26).** Leak p-values are clustered by visit; a second-stage Holm correction runs over class × detector; coverage is checked **per verdict slice** (an item is gated only if its answer class is individually clean); the leak cache key includes a digest of the leak pipeline's source files; a text-only verdict (no metadata detector) is reported beside the generator diagnostic.
11. Resolved by the implementation: parameter counts come from `sum(p.numel())` (#14: 2,013,140 with v1, 2,102,228 with v2); reader causality is tested with cuts inside and across attention blocks (#15); ASK excludes already-fetched cards (#18).
12. **Found while building the contenders.**
    - Counts with the v2 vocab: A 5,165,568, E 5,169,664, B12 13,656,576, B28 29,232,128 parameters; A costs 40.74 MFLOP per token (measured, matching the hand count). The 772M-token budget run is therefore ≈3.15e16 FLOPs, not 2.6e16. F is still taken from A's v2 retrain.
    - C's lookup candidates are every line before **C's own** window start, not A's, so no lines fall between the recalled block and the shortened window.
    - Any decoder output naming an entity id missing from the name table is scored as wrong; it must never raise.

Revised contender list: A, B12, B28, C, **C2**, D ×2, D-noask, D-noptr, **D-no-oracle**, E ×2.

## 10. Changes after the Astra research review (2026-09-18)

The review's code claims were checked: the held-out split bundles R8 (an untrained rule family), depth > 3 and multi-rule derivations (`scheduler.py` docstring), and cards pool contextual reader states (`model.py` `CardWriter`). Changes:

1. **Stage 1a, "is the task solvable?" (runs first, ~$5).**
   - Core baselines get a **label-free question-centred training mode**: a label-free prefix, with the current answer as the only target, so training matches evaluation.
   - **E-long:** E with a 2,048-token context, which fits a whole normal (~1.1k-token) visit. It tests whether D's gain is just the window.
   - **Gold-evidence diagnostic:** D-gold (the gold cards are given) and C-gold (A with the gold lines as its recalled block).
   - Target: ≥95% on familiar operators at depth 1–3, with fresh names; depths 4–6 are reported separately. If gold evidence fails, fix the representation, objective or task before building anything more.
2. **C\* replaces C2:** A plus the pointerizer, a dense retriever trained on the same oracle labels, **iterative retrieval** (up to 4 rounds, each conditioned on earlier recalls), and deep supervision per round. It is run at A's size and near D's size.
3. **D-soft:** D with soft attention over the whole store (~140 cards) instead of top-k ASK, trained both with and without evidence labels. **D-local** (cards built from a line's own tokens rather than contextual reader states) is a low-priority ablation.
4. **Slices:**
   - Held-out is split into new names, new wording, deeper, multi-family and R8, with each reported separately before their intersection.
   - Depth is reported alongside evidence count, rule applications, plan length and distractor count.
   - Other metrics: **both twins correct**, invariance on questions whose answers must not change, and cost amortised over 1/10/100 questions per visit, plus memory bytes.
5. **Seeds:** three precommitted training seeds for every finalist in a primary comparison. The 60-visit minimum is a floor, not a power calculation: estimate the variance of the paired differences in a pilot.
6. **Stop rules:**
   - D ≈ C\* within 3 points and C\* cheaper → adopt C\*.
   - D > D-noask but not > C\* → keep the memory claim and drop the controller claim.
   - Gold evidence fails at shallow depth → no new mechanisms.

Revised contender list: A, E, E-long, C, C\*, D ×3 seeds, D-noask, D-soft, D-noptr, D-no-oracle, plus the gold diagnostics (D-gold, C-gold). B12/B28 run once, as the scale reference.

## 11. Trustworthy label-free inputs and evaluation (Opus milestone 1, 2026-09-18) — overrides §0-§10 where they conflict

Implemented and tested (tests/test_premonition_label_free.py); evidence in reviews/opus-milestone-01-m01-20260918-202731.md. Items marked **PROPOSAL** are not implemented.

1. **One versioned label-free path (`premonition/preprocess.py`).** Answers and feedback are removed from the *text* before names are bound or anything is encoded (masking a loss never removed them from a reader). A question line becomes its text through `[answer]`, then a newline; other lines are unchanged, and a non-question line carrying `[answer]`/`[feedback]` is malformed. Entity ids are bound in first-mention order over visible text only, so a name written only in a label never enters the name table or shifts later ids. The current answer (the only target) is bound with the mapping of the visible prefix through its own `[answer]`; a target name that prefix never mentioned stays ordinary tokens and is flagged (`target_unbound`), never imported. The rules are data (`preprocess.spec`); their SHA-256 is the preprocessing identity (label-free `9add8e2fded1…`, with-labels `bdf907371b40…`, gold-evidence `05ca83849d11…`, format `premonition.preprocess` v1). A golden visit pins the output to the digest: a rule change must bump the version.
2. **D's visit cache v2.** `data.load_or_build(..., regime="label-free")` builds through that path and lives at `premonition-v2-<tokenizer>-<names>-<preprocessing digest>/<split>.pt`; offsets, spans, card boundaries, entity mentions, name tables, targets and masks are all computed on the visible text (`answer_end` = one past the newline after `[answer]`, so L_lm never targets the `[answer]` → newline step). The legacy v1 cache keeps its path, bytes and identity (`regime=None`); E's LM stream still uses it (Core training streams keep answers, §9.1). D training, validation, smoke and scoring read only the v2 label-free cache; `d_scorer` refuses any other and audits every stream.
3. **Evaluation defaults to label-free, with the regime recorded.** A, B, C and E prompts use the same line form as D (earlier question lines end at `[answer]` + newline). The canonical near/far cut (§6.1) is taken over the regime's visible lines, so "far" means outside the window A really has (validation, large build: 466 of 3,074 with-labels "far" items are near under the label-free cut). Every input is audited: no `[feedback]`, and nothing after any earlier `[answer]`. Every report carries `regime` and an `identity` block (preprocessing identity, tokenizer digest/vocab/status, model-config and checkpoint-manifest digests, the checkpoint's training preprocessing, purpose, `primary`, problems, scope). Regimes: label-free (the only verdict regime), with-labels (diagnostic), gold-evidence (privileged diagnostic; its inputs are milestone 3's).
4. **Checkpoints fail closed (`premonition/identity.py`).** Before scoring: the checkpoint's tokenizer digest must equal the scoring tokenizer's (also when a tokenizer path is overridden — this closed a bypass), the model vocabulary must equal the tokenizer's (+16 entity ids for E), the model configuration must exist and match the contender's shape, the plain scorer refuses lookup/pointer checkpoints, and the checkpoint must record a preprocessing identity this code produces (D's must be label-free, and its name-detector digest must match). Purposes: **primary** (every check, plus the v2 contender tokenizer `data/tokenizer/premonition-tok-v2-fallback.json`, 7,068 ids, digest `2c9d06aed330…`, verified through `Tokenizer.load`), **diagnostic** (every checkpoint check; for with-labels runs), **fixture** (unit tests only: a non-contender tokenizer, full-size shape waived), **legacy** (missing metadata allowed, never a verdict row; token-id mismatches still refused). The v1 tokenizer is retired and refused for any primary report; every existing step-1 checkpoint is refused as primary. New Core checkpoints record `preprocess.identity("with-labels")`, D checkpoints `preprocess.identity("label-free")`.
5. **Verdicts.** `exp1.verdict` refuses mixed regimes, reports without a regime (legacy/unknown — never assumed label-free), with-labels or gold-evidence reports, stale preprocessing digests and non-primary reports; fixtures run only as all-fixture "mechanics". Its outcome is the §6 decision table on label-free items and says so (`full_verdict: false`, `scope`): it is **not** a §9/§10 verdict (no visit-clustered bootstrap, no D vs D-noask store claim, no C*/D-soft/E-long, no seeds).
6. **C's candidates (§9.12 made true).** Candidates are every non-question line before C's *own final* window start. Because the window depends on the recalled block, recall starts from A's window start and repeats while the block pushes C's window later, moving the boundary to the new window start; the boundary only moves forward, so it ends, and the final window starts exactly at the boundary: no overlap, no future line, no line lost between them, no budget overflow. The old rule is kept as `candidates_rule="before-a-window"`. On the large validation split the old rule left a gap in 5,378 of 8,675 inputs (23,048 lines), including 464 evidence lines of 413 questions that C could neither recall nor see; the new rule has no gap and recalls 231 of those lines.
7. **Scoring boundaries.** An output entity the name table does not hold becomes `<entK>`, a wrong prediction that is counted, never an exception (D, E). A gold target that cannot be detokenised raises `MalformedTarget`; a broken input raises `MalformedInput`; both are errors, distinct from wrong answers.
8. **PROPOSALS (not implemented).** (a) Under label-free inputs an earlier asking of the same question no longer shows its answer; repeats stay excluded from decision cells for now (conservative) — revisit with Astra. (b) The gold-evidence input builders (D-gold, C-gold) and label-free question-centred Core training belong to the solvability milestone. (c) §9.4 visit-clustered statistics, §9.5 orthogonal lesions, §9.7 compute additions, §9.9 targets and §9.10 leak statistics remain open. (d) A `run.py premonition` CLI should expose `--regime` and `--purpose`.
