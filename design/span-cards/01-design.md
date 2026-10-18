# Span cards: card layout decided by the model, not by line breaks

Status: DRAFT (Ultracode SOLVE session, 2026-10-17). $0 work only. Nothing here has been trained. All code is a
draft until the coordinator code-reviews it.

## 0. Plain-language summary (for Ben)

Today every line of the input becomes exactly one memory card. The proposal: let the reader learn where a card
should end. The reader looks at each token and gives it a "start a new card here" score. A card closes wherever
that score crosses one half. Each card is still made the same way today's cards are made (a learned weighted
average of its tokens). The model just chooses the edges.

The difficulty is that "where to cut" is a yes/no choice, and you cannot take a gradient of a yes/no. The fix:
during training, a second, smooth version of the card lets content leak across an edge in proportion to how
unsure the cut is. The real (hard) card is used for the answer. The smooth card only supplies the gradient that
says "merging across this edge would have helped" or "cutting here would have helped". A small budget term keeps
the average number of cards equal to today's, so the model cannot win by simply storing more. It has to place
the same number of cards better.

Per-line cards are a special case of this mechanism (cut exactly at every line start). So the new writer can
start as an exact copy of a trained per-line model and only differs where training moves the cuts. That makes
the comparison clean: any difference comes from the learned layout.

Honest expectation: in today's village data almost every line is one fact (measured below). On that data the
best layout is close to "one card per line", so a large win on today's ruler is not expected. The win, if
any, should show when line breaks and facts disagree. The run card therefore has a second cell that tests
exactly that.

## 1. Grounding: what the code does today

All claims below were read in the code in this session (shown), unless marked otherwise.

- **Writer** (`premonition/model.py:171-197`, `CardWriter`): a softmax pool over each line's reader states
  (`pool = Linear(d, 1)`, a masked per-line softmax over `line_of` slots), then `key = normalize(W_k p)`
  (64-d) and `value = W_v p` (128-d). One pooled vector feeds both key and value.
- **Store** (`premonition/store.py:52-70`, `CardStore.write`): indexed `[visit, line]`. A line has a card iff
  it is a non-question line whose last token (`card_end`, the newline) is in the batch. Each card also carries
  `tags` (first token), `ents` (`line_ents`, up to `MAX_LINE_ENTS = 4`) and a diary pointer
  (`line_start`, `line_len`). The NULL card is index `lines` (last), with a learned key and value.
- **ASK** (`store.py:106-117`): `s_i = kappa * q.k_i + b_age(bucket(q_line - line_i))`. Only cards on lines
  before the question line are eligible (`store.py:82-98`), NULL always is, and already-fetched cards are not.
  `top(scores, top_k = 4)` fetches cards into the 16 FIFO card rows of the think state
  (`model.py:446-481`). Each fetched card's value becomes a row with an age embedding, and its `ents` drive
  the slot binder.
- **Supervision is line-level.** Gold evidence is a set of line indices from the oracle
  (`premonition/data.py:340-352`, from `step1` `evidence_text_lines`). `CardStore.gold` maps gold lines to
  card columns (`store.py:138-157`). `L_ask` is a set cross-entropy over gold minus fetched, plus a BCE on
  the ASK logit (`model.py:596-603`). The teacher fetches gold cards plus 1-2 distractors
  (`model.py:631-654`).
- **Loop counts derive from line counts.** Teacher mode runs `ceil(|G| / top_k) + 3` loops, where `|G|` is
  the number of gold lines (`model.py:536-545`, mirrored by `train.planned_loops`, `train.py:106-118`).
  Gold mode runs 2 and own mode runs `max_loops` (8). The FLOP charge of a step uses the planned loop count
  (`train.py:290-294`).
- **What a line is in the data.** The village generator writes one record per line
  (`learnlab/village/render.py:450-472`; scout report, checked by sampling). Measured on 20 freshly
  generated train visits (1,830 lines; v2 tokenizer): a non-question line averages 11.9 tokens (range 6-26),
  with about 91 lines per visit. Multi-fact lines exist but are rare. About 0.6% of lines are visibly
  multi-update ("Pata headed to the stable, and Vinu followed."; "Soon Taba and Venu traded their current
  holdings."). Teacher lines carry filler inside the line ("[teacher] Just watch and wait. Lizo hurried to
  the shed."). Facts span lines by derivation: one answer's evidence is 1-15 lines. No pure filler lines
  exist (time markers are evidence). There is no token-level evidence: gold is line-level only.

Consequence: on today's data, line breaks and fact boundaries almost coincide. Ben's objection is correct in
general ("one line can hold two facts, a fact can span two lines, filler gets the same storage"), but in this
data only the third point (in-line filler) and a small share of the first are present.

## 2. The design space

The crux for every option is the training route. Layout is a discrete decision, and the only supervision we
have is (a) the answer loss and (b) line-level evidence labels.

### (a) Learned write decisions, variable card count
The reader emits a gate at each token. A card is written where it fires and pools the tokens since the
previous write.
- *Training:* the write decision is discrete. Possible routes: REINFORCE (high variance at 2M parameters and
  ~90 lines per visit; nothing in this repo trains a policy stably); Gumbel or straight-through on the gate
  alone (the gradient only says "scale this card", not "merge or split"); or a **soft surrogate whose content
  is a differentiable function of the gate** (a decay or forget-gated pool, as in dynamic token pooling and
  H-Net's dynamic chunking). The last gives a dense merge-or-split signal.
- *Breaks first:* the gate collapses to "always" or "never" unless a rate term holds the card count. Gold
  labels must be remapped from lines to cards.
- *Cost:* moderate. A new writer, a token-indexed store, a gold remap and a report.

### (b) Adaptive allocation: a fixed budget of K slots filled by importance
- *Training:* slots attend over spans (slot attention or Perceiver style), trained by the answer loss.
- *Breaks first:* **causality.** A question may only see cards written before its line. A global slot set
  over the visit leaks later lines into earlier questions' cards. Slots would have to be rebuilt per question
  (cost x questions per visit, about 8.6) or chunked, which brings fixed segment boundaries back.
- *Cost:* high, and it fights the store's per-question eligibility rule.
- *What survives:* the "fixed budget" idea. It is adopted below as a rate target inside (a), so placement
  is adaptive while the average count is held.

### (c) Token- or span-level cards with learned merging
- *Training:* every token is a candidate card, and merges come from a learned similarity (token merging).
  Gold becomes "tokens of gold lines". The set cross-entropy is satisfied by any one gold token, and top-4
  fetches return fragments.
- *Breaks first:* the 16 card rows and top-4 ASK cannot carry a fact made of 10 tokens. Fragments starve
  the decoder. This repo's own token-memory successor (`reviews/premonition-token-memory-20260920.md`) had to
  drop discrete ASK and cards entirely and read all tokens softly, which changes the inference contract.
- *Cost:* high. In practice it becomes "no cards".

### (d) Delta-rule memory writes (erase-then-write; Gated DeltaNet, Kimi Linear KDA)
- *Training:* fully differentiable: `S <- S (I - b_t k_t k_t^T) + b_t v_t k_t^T`, where `b_t` is a learned
  write strength. This is "adaptive writing" with no discrete layout at all.
- *Breaks first:* it **removes cards**. There is no discrete ASK, no gold-card set cross-entropy, no per-card
  `ents` for the binder, no age per card, and no inspectable notebook entry. Per-question causality needs a
  snapshot of `S` at every question line. One 64x128 matrix holds roughly 64 orthogonal facts; a visit has
  about 90 lines, so interference is expected (untested).
- *Cost:* a new model, not a writer change. It cannot be A/B'd against per-line cards "with everything else
  fixed".

### (e) A small reader-pair (a transformer reads encoder states and decodes digest slots)
- *Training:* answer loss through the digest slots.
- *Breaks first:* the same causality problem as (b), plus a second network to train. Its digests have no
  span, so gold labels cannot be mapped to them without a learned alignment.
- *Cost:* highest.

## 3. Recommendation: boundary-gated span cards (option (a) with the budget of (b))

One mechanism. It changes only the writer and the store's indexing. The reader, think loop, ASK, binder,
decoder, losses and curriculum are unchanged.

### 3.1 Forward (the same at training and test time)
For each token `t` the writer computes a boundary probability
`p_t = sigmoid(c_0 + c_nl * [token_{t-1} is a newline] + w . [h_{t-1}; h_t])`.
Here `h` are the reader states, **detached** (review fix: otherwise the surrogate and the rate loss also train the reader, which would confound the A/B). `c_0`, `c_nl` and `w` are learned. The newline indicator is an input feature
the gate may use or unlearn. It is not a rule. A hard boundary starts before token `t` iff `p_t > 0.5`, or
`t` follows a **wall**. Walls are a question line, padding, or the visit start; cards never pool question
tokens, so a question line is a hard wall in both directions. A card is also forced closed after `max_span`
tokens (default 64, about 5 lines).

A **card** is a maximal run of tokens between hard boundaries. It is written at its last token `e`. Its
content is today's softmax pool over exactly its tokens:
`pooled_e = sum_{t in card} softmax(pool(h))_t h_t`, `key = normalize(W_k pooled)`, `value = W_v pooled`.
These are the same `pool`, `key` and `value` modules as `CardWriter`, so a trained per-line writer loads
unchanged.

### 3.2 Training route (the crux)
1. **Content-merge gradient (main signal, dense).** A soft surrogate pool lets content cross a boundary in
   proportion to `1 - p`:
   `soft_e = sum_{t <= e, same wall region, e - t < max_span} a_{e,t} h_t`, with
   `a_{e,t} proportional to exp(s_t + sum_{t < u <= e} log(1 - p_u))`.
   Starts the gate did not choose (walls, the `max_span` cap) enter as hard boundaries (log 0, floored). With `p` exactly 0 or 1 this is exactly the hard pool. The writer outputs
   `pooled = hard + (soft - stopgrad(soft))`, with `soft` computed from `stopgrad(h)` and `stopgrad(s)`.
   The forward value is exactly the hard pool. Reader and pool gradients are exactly today's. Only the gate
   receives the surrogate gradient. `dL/dp_u` then answers: "would the card after `u` be better if it also
   held the content before `u`?" That is the merge-or-split decision, and it is also the write decision. When
   `p_u` falls below 1/2 the earlier card disappears and its content flows into the next card.
2. **Rate (budget) loss.** H-Net's ratio loss
   `L_rate = N/(N-1) * ((N-1) * F * G + (1-F) * (1-G))`,
   where `F` is the share of tokens that start a hard card, `G` is the mean `p`, and `N` is the target tokens
   per card. Correction (found in code review of the draft): the loss is bilinear in (F, G), so
   `F = G = 1/N` (value 1) is a saddle, not a minimum. It works because `F` is a hard count with no gradient.
   Only `G` is trained, and `dL/dG ∝ N·F - 1` pushes the gate down when there are too many cards and up when
   there are too few, and is zero at `F = 1/N`. This is H-Net's own usage. **`N` is set to the training cache's mean tokens per
   non-question line**, so the span arm stores the same number of cards as the per-line arm on average.
   Any gain must come from placement, not from storing more. Weight `w_rate = 0.03` (H-Net's value; an
   assumption, not tuned).
3. **Retrieval labels.** The oracle's evidence lines label *which tokens hold evidence*, not the layout. The
   rule is **one gold card per evidence line**: the eligible card holding most of that line's tokens (a tie
   goes to the later card). A merged card holding two gold lines is gold once. Of a gold line split over two
   cards, only the larger piece is gold. So `|G_cards| <= |G_lines|` always. The parent's teacher loop count
   (`ceil(|G_lines| / top_k) + 3`) and gold-mode preload width (`<= MAX_GOLD + 1`) therefore always cover
   every gold card. The planned loops, and hence the FLOP charge, stay identical to the per-line arm and are
   known before the step. (Revision after the second code review: the earlier "every overlapping card is
   gold" rule let a split layout outnumber the line-counted schedule, e.g. 13 gold lines split in two gave 26
   gold cards against 24 teacher fetches, an ASK target the line arm never faces.) The cost: a split
   evidence line's smaller piece is never a teacher target, which mildly discourages the gate from splitting
   facts. `L_ask` and the teacher then run unchanged over cards.
4. **No layout supervision.** Nothing ever says "cut at the newline". The newline feature only sets the
   starting point (3.3).

### 3.3 Initialisation: start as the parent
`c_nl = 8`, `c_0 = -4` and `w` near 0 give `p` about 0.982 after a newline and about 0.018 elsewhere. The
initial hard layout is **exactly** one card per non-question line, and the content is today's pool. So a span
writer loaded from a trained per-line parent answers exactly as the parent at the branch point (unit-tested
below). From there the gate moves only if the gradient says so. The sigmoid slope at these values,
`p(1 - p)`, is about 0.018, small but nonzero. A from-scratch option (`newline_prior = 0`) exists but is not
the recommended arm.

### 3.4 What changes in the store
The span store is indexed by **token position** (card id = the position of its last token). `valid[b, t]`
marks written cards. Width is `T + 1` with NULL last, so every consumer of
"`[Q, width + 1]` scores, NULL last" keeps working unchanged:
- eligibility: `card_line < q_line` (the card's last line). After a wipe, the card's **first** line must be
  `>= floor`. This is conservative: a card that started before the window is gone.
- age bucket: `q_line - card_line`.
- `ents`: the distinct entities in the card's tokens, first 4. Overflow is counted in the report.
- `tags` and diary pointer: the card's first token, start and length.
- `gold`: one card per evidence line (the rule above), with the same `(G, told, missing)` signature.

`answer()` maps `first_top` and `fetched` back to line indices (a card's last line), so `train.validate`'s
accuracy, slices and asked-rate stay valid. Its line-based recall@4 and `cards` block are only approximate
for span cards and are superseded by `card_economy` (below), which is layout-aware and runs on both arms.

### 3.5 Cost
- Parameters: `+2d + 2` for the gate (a `2d + 1` linear plus the newline weight; 258 at d = 128, +0.01%).
  Nothing else is added.
- Training FLOPs: the surrogate is a banded `[K, K + W]` product per 64-token chunk, about `2 * (K + W) * d`
  multiply-adds per token (about 33k), against D's about 18 MFLOP per token by hand (+0.2%). It is charged by
  the same `FlopCounterMode` fit as every contender.
- Inference: the hard pool only (an index_add, the same as today).

## 4. Exact code changes

No existing file is edited (the standing "never edit `premonition/`" rule, HANDOFF.md; card_pools.py is the
precedent for adding a new file).
- `premonition/span_cards.py` (new):
  - `SpanConfig(enabled=False, max_span=64, chunk=64, tokens_per_card=..., w_rate=0.03, newline_prior=8.0,
    base_logit=-4.0, newline_id=...)`. **`enabled=False` is the default.**
  - `build_model(config, span)` returns a plain `PremonitionMini` when off (the same class, construction and
    random stream), and a `SpanCardMini` when on.
  - `SpanCardWriter`, `SpanCardStore(CardStore)`, `SpanCardMini(PremonitionMini)`,
    `SpanTrainer(MiniTrainer)` (layout-aware card stats plus a card-economy log), `card_economy(model,
    batches)` (works on both arms) and `tokens_per_line(cache)`.
- `premonition/reflow.py` (new): `reflow_cache(cache, merge=, split=, seed=, ...)`, a `VisitCache` to
  `VisitCache` transform that merges consecutive non-question lines (newline removed, the second line's tag
  dropped) or splits a line at a word start. Gold lines, `q_line`, `q_span`, `answer_end` and `line_ents` are
  remapped. `merge = split = 0` returns a bit-identical cache. It is used for the stress cell of the run card.
- `tests/test_premonition_span_cards.py`, `tests/test_premonition_reflow.py` (new).

## 5. Failure modes watched (each with its readout)

| # | Failure | What we would see | Readout |
|---|---|---|---|
| F1 | Gate never leaves the newline layout (relearns lines) | line-aligned card share stays above 0.98 | `card_economy.line_aligned`, boundary/newline precision and recall |
| F2 | Rate collapse (all tokens or giant cards) | tokens per card far from `N` | `F`, `G`, `L_rate`, tokens-per-card histogram |
| F3 | Gold inflation: big cards make "gold" trivial, recall looks fine, answers drop | gold cards per question falls, gold card size rises, own-retrieval accuracy drops while recall@4 rises | `card_economy.gold_*`, `accuracy` vs `gold_recall_at_4_span` |
| F4 | ASK or fetch collapse (the model stops asking, or always takes NULL) | asked rate and fetches per question fall, NULL share rises | `card_economy.asked_rate`, `fetch_per_q`, `null_share` (guard in the run card) |
| F5 | Entity overflow: merged cards hold more than 4 entities, so the binder loses some | overflow share above 2% | `card_economy.ents_overflow` |
| F6 | Wipe leak: a card straddling the window start | handled by the first-line rule; checked by a unit test | test |
| F7 | Surrogate and forward disagree (STE bias) | gate oscillates near 1/2 | share of `p` in (0.4, 0.6) |
| F8 | Branch-point shock (a loss jump right after branching) | none expected: the function is identical at the branch | step-0 loss of both arms equal, tested |

## 5b. $0 checks run on the draft (2026-10-17, CPU, this session)
- Unit tests: 22 span-card and 11 reflow tests, plus the existing model, card-pool, train, data and
  pool-control suites. Result: 88 passed, 1 skipped (a pre-existing skip).
- Real data at full size (d = 128, v2; 256 generated train visits): the branch-point `answer()` tokens, loops
  and `first_top` of SPAN-at-init equal the per-line parent's on 12 visits. `card_economy` is identical for
  both (1,076 cards, line_aligned 1.0, gold_missing 0).
- Overhead (one CPU sample, not used for costing): writer forward+backward 0.16 s vs 0.06 s; a full own-mode
  step 27.7 s vs 24.2 s (about +15%), mostly the wider token-indexed store. Stage 0 measures it on GPU.
- Tiny-preset smoke, 300 steps per arm on real data: stable, with similar losses (6.46 vs 6.42), `L_rate`
  about 1.000, and 11.0-11.3 tokens per card against N = 11.17. The gate barely moved (newline weight 8 to
  7.99, bias -4 to -3.97) and the DEV layout stayed 100% line-aligned. Open observation for the reviewer: at
  that identical layout, the arms' DEV `null_share` differed (SPAN 0.16, LINE 0.016) and so did
  `fetches_per_q` (10.6 vs 14.9). The likely cause is trajectory noise: the wider store makes the same
  generator seed draw different teacher cards, so the arms are paired by parent, data and seed, not bitwise
  after the branch. That was not confirmed (the seed-noise check was stopped). If G1's absolute margins are
  inside seed noise, G1 is flaky. The bars are not changed here; a change would go to Ben.

## 6. What this does not claim
- Nothing is trained. No accuracy claim of any kind is made here.
- The gate cannot learn a layout the data never rewards. Trained on today's line-aligned data, staying near
  per-line is the *correct* outcome, not a failure of the mechanism. The run card's cell B (reflow) is where
  the mechanism should show its value.
- The gold rule over-labels: a card holding a gold line and a filler line is "gold". It does
  not tell the model which half mattered. No sub-line evidence exists in the data to do better.
- "Far held-out join score", "house-form bars", "DEV slip" and "the house family rule" are not defined
  anywhere in this repo (searched; newest repo content is 2026-09-30). The run card maps them to the closest
  documented conventions and asks the coordinator to confirm.
