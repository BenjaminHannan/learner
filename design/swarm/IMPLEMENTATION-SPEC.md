# Swarm prototype: implementation spec (Opus layer -> Sonnet coder), 2026-10-17

Status: DRAFT until the coordinator code-reviews it. $0 work. No training, no GPU.

Read first: `premonition/model.py`, `premonition/config.py`, `premonition/store.py`,
`tests/test_premonition_model.py` (helpers `synthetic_batch`, `tiny_model`, `eager`).
The design reasons are in `design/swarm/SWARM-DESIGN.md`; this file is only the build contract.

## 0. Hard rules

* Flag OFF (`thinkers == 1`, the default) must be **bit-identical** to `73b8e0224`. The frozen copy
  `tests/_premonition_model_pre_swarm.py` is the reference; never edit it.
  - Do not reorder or change any existing parameter creation. New parameters are created ONLY when
    `thinkers > 1` (so no RNG is consumed with the flag off).
  - Do not edit `_start`, `_step`, `_insert`, `_teacher_cards`, `_greedy`, `_decode_logits`, `_recall`.
    `forward` and `answer` each get exactly one early dispatch line at the very top:
    `if self.config.thinkers > 1: return swarm_forward(self, ...)` (same arguments).
  - `Answers` gets ONE new optional trailing field `swarm: Optional[dict[str, Any]] = None`.
* The swarm code lives in a new file `premonition/swarm.py` (functions taking the model as first arg),
  built on top of `model._start / _step / _insert / _teacher_cards / _greedy` so subclasses
  (`address_reader.py`, `direct_reader.py`) compose. Import it lazily inside `forward`/`answer`
  to avoid an import cycle.
* Match the house style: dense, terse docstrings, shapes in comments, no new dependencies.

## 1. Config (`premonition/config.py`)

New `MiniConfig` fields (append after `distractors`, before `check_band`):

```
thinkers: int = 1          # desks per question; 1 = today's single thinker (swarm OFF)
swarm_board: bool = False  # the one communication channel; False = S0 (independent desks + combiner)
swarm_rounds: int = 4      # fixed rounds per question in teacher/own/eval (gold: 2); <= max_loops
board_cards: int = 16      # posted-card rows on the board (FIFO); only used with swarm_board
```

Validation in `__post_init__`: `thinkers >= 1`; `1 <= swarm_rounds <= max_loops`; `board_cards >= 1`;
`swarm_board` requires `thinkers > 1` and `registers >= 2` (register 1 is the post register).

`parameter_breakdown`: when `thinkers > 1`, `think += thinkers * d` (desk embeddings); when also
`swarm_board`, `think += 2 * d` (board row types: note, card). Nothing else changes. The d=128 band
check must still pass for thinkers 2..8 with the board on (it adds < 1.3k parameters).

## 2. New parameters (`Think.__init__`, after `self.binder`, only when `config.thinkers > 1`)

```
self.desk = nn.Embedding(config.thinkers, d)                 # assigned role/identity per desk
self.board_type = nn.Embedding(2, d) if config.swarm_board else None   # 0 = note row, 1 = card row
```
When `thinkers == 1` set neither attribute... **except** define `self.desk = None; self.board_type = None`
(attribute assignment of None creates no parameters and consumes no RNG). `reset_parameters` already
inits every `nn.Embedding` with std 0.02 — fine.

## 3. Layout and ordering

* Desk index `qm = q * M + m` (question-major, desk-minor). `owner = arange(Q).repeat_interleave(M)`,
  `desk_of = arange(M).repeat(Q)`.
* Desk episode: call `model._start(desk_batch, hidden, desk_store, mentions.repeat_interleave(M, 0))`
  where `desk_batch = dataclasses.replace(batch, q_visit=…rep, q_line=…rep, q_span=…rep)` (rep =
  `repeat_interleave(M, 0)`), and `desk_store = dataclasses.replace(store, floor=store.floor.repeat_interleave(M))`
  if `store.floor is not None` else `store`. Use `desk_store` for every `_step/_insert/_teacher_cards` call.
  Compute `gold` with the ORIGINAL store/batch (`store.gold(batch.gold_lines, batch.q_visit, batch.q_line)`) → [Q, L+1].
* After `_start`: add `desk.weight[desk_of]` to every register row of each desk
  (`x[:, reg_base:reg_base + registers] += desk.weight[desk_of].unsqueeze(1)`), where
  `reg_base = model._register_base`. `R_desk = episode.x.shape[1]` measured right after `_start`
  (subclasses may append rows; keep them inside the desk).
* Board (only `swarm_board`): per question state, `B = M + board_cards` rows:
  notes `[Q, M, d]` + `notes_ok [Q, M]` (False at start), cards `[Q, C, d]` + `cards_ok [Q, C]`,
  `board_count [Q]`, `posted [Q, L+1]` bool. Before every round, the board is (re)written into a
  board region appended at the END of every desk's rows: `episode.x = cat([x[:, :R_desk], board[owner]], 1)`,
  `episode.valid` likewise (first round: append; later rounds: overwrite that region). Board rows are
  read-only inside a round: their think outputs are discarded when the region is overwritten.

## 4. One round (training and eval share this order)

1. Write board into desks (if board).
2. `rows, halt, ask, scores = model._step(episode, all_desks, step, desk_store)` (`all_desks = arange(Q*M)`).
   All desks of all questions run as ONE batch: this is the concurrency.
3. Notes (if board): `notes[q, m] = rows[qm, reg_base + 1].float() + board_type.weight[0] + desk.weight[m]`;
   `notes_ok = True`. (Gradient flows desk -> board -> other desks next round. Intended.)
4. Combiner memory -> decode (see §5). Deep supervision (training) / final greedy (eval, last round).
5. ASK losses (training) and fetch choice; `model._insert(episode, desk_store, all_desks, cards)` into
   the fetching desk only; then post (if board) the same cards to the question's board (§6).
   No fetch after the last round.

## 5. Combiner (the merge point, also the "speaker")

`memory = episode.x[:, :R_desk].view(Q, M * R_desk, d)` concatenated with the board rows `[Q, B, d]`
(if board). `valid` the same way from `episode.valid`, with the **bound-slot merge mask** on the slot
region `[question_rows, question_rows + slots)` of each desk, only when `model.think.binder is not None`:
* `bound[qm, e]` = desk qm has fetched (per `episode.fetched[:, :L]`) a real card whose `store.ents` contains e
  (one-hot over `n_ent`, ignore -1).
* slot (q, m, e) visible iff its original valid (mention) AND (`bound[q,m,e]` OR (`not any_m bound[q,:,e]` AND m == 0)).
  So a name's fact found by any desk reaches the decoder from the desk that bound it; unbound duplicate
  copies are hidden so they do not dilute attention; an entity nobody bound shows desk 0's copy.
Decode with `model._decode_logits(memory, valid, inputs)` in training; at eval, call
`model._greedy(batch, _Episode(memory, valid, …dummy…), mentions, stop)` (`_greedy` reads only `.x`, `.valid`).

## 6. Posting cards to the board

For the round's chosen `cards [Q*M, K]` (−1 = none), view as `[Q, M*K]` and walk the M*K columns in
desk order, **exactly as a one-by-one FIFO would** (review round 2, 2026-10-18). Column c is new iff
`c >= 0`, `c != store.null`, and c is **not on the board at that moment**: `slot_card`, the card each row
holds, is the only state. So a card evicted earlier in the same round is
posted again, even if it was on the board when the round began, and a card still on the board is never
posted twice. A new card's row = `values + model.think.age(bucket) + board_type.weight[1] +
desk.weight[m_author]` (values/lines via `store.gather`, `bucket` as in `_insert`). It is written at
`board_count % C`, evicting that row's card, with `cards_ok = True` and `board_count += 1`. Every step is a
whole-tensor op: no boolean-mask indexing, no host `.any()`, no `F.one_hot`. So `post` forces no host
sync (tested by `NoSyncTest`, which matters because C0 is a timing measurement). Skip all of this when the
board is off or the store is off.

## 7. Training (`swarm_forward(model, batch, mode, p_own, loops, weights, generator)`)

Mirror `PremonitionMini.forward` (same return dict, same weights defaults, same `count == 0` early return):
* Rounds: `loops` if given, else 2 for "gold", else `config.swarm_rounds`; every question runs all rounds
  (fixed rounds, no per-question schedule).
* "gold" preload (review fix 2, 2026-10-18): keep the question's `width = min(L + 1, MAX_GOLD + 1,
  M * card_rows)` **latest** gold cards (as the single thinker's preload keeps its latest `card_rows`), then
  deal them round-robin across its desks in line order (kept card i -> desk i % M, so no desk exceeds
  `card_rows`; NULL for never-told goes to desk 0). They are inserted before round 1 (and posted, if board).
  This teaches the combiner to join across desks from step 0.
* L_ans per round from the combiner; `scale = 1` if the UNION of the question's desks' `fetched` covers
  gold else `config.early_ans`; `l_ans = sum(scale * per_question over rounds) / (Q * rounds)`.
* HALT: `swarm_halt = halt.view(Q, M).mean(1)`; BCE vs combiner-correct, as in forward.
* ASK — balanced assignment (multiple-choice-learning style; training-only, uses gold labels, NOT an
  inference channel, identical in S0 and S1):
  - `need_union [Q, L+1] = gold & ~fetched_union`.
  - `prefs = scores.detach().view(Q, M, L+1)` with `-inf -> -1e9`.
  - Greedy balanced matching with a floor and a ceiling (review round 3, 2026-10-20): `floor = n // M`,
    `cap = ceil(n / M)` per question, n = |need_union[q]|. Each pick: while any desk is below floor, only those
    desks are eligible; otherwise desks below cap. Take the per-question argmax pref over (eligible desk,
    unassigned needed card) and assign it. So every desk gets floor or ceil, disjoint, covering need. Output
    `T [Q, M, L+1]` bool. Vectorised over Q, with a static number of picks (`gold_lines.shape[1] + 1`) and
    unmasked writes, so it forces no host sync.
  - Desk target: `asks_m = T[q, m].any()`. `bce` over all Q*M desks; `set_cross_entropy(scores[qm], T[qm])`
    over desks with a non-empty target.
* Fetch for the next round (not after the last; not in "gold"): teacher = `model._teacher_cards(desk_store,
  episode, all_desks, need=T.view(Q*M, -1), gold=gold.repeat_interleave(M, 0), generator)`;
  "own" with `p_own > 0`: per desk, with prob p_own, use its own `store.top(scores, top_k)` masked where
  `ask <= 0` (pad to the teacher width as in forward).
* metrics: `gold_missing`, `answer_acc_first`, `answer_acc` (final round), `question_loops =
  Q * rounds * M` (desk-rounds: keeps `fit_flops` linear), and `recall_at_k` (first round, **desk 0's**
  top-k over told questions, comparable with D1; only when `model.train_diagnostics`, which MiniTrainer turns off
  for matched wall-clock runs). There are **no per-step swarm diagnostics** in training (review round 3); the
  diversity report (§9) comes from `swarm_answer`. In "gold" mode the split and the ASK terms are computed as in
  every mode (weight 0 by default), so the ASK head is in the graph exactly as D1's is (zero gradient, decayed by
  AdamW in both arms). The skip added in round 3, fifth pass, was reverted (sixth pass, item 15, ADOPTED Oct 20).
  The answer path's round-invariant masks (kept-token indices, owners, targets, counts) are computed once before
  the round loop (sixth pass, item 18), so the loop adds no host syncs.

## 8. Eval (`swarm_answer(model, batch, *, wipe, window_line, stop, max_loops, lesion=None)`)

Mirror `PremonitionMini.answer` (same wipe handling, mentions, empty-batch return). Rounds =
`min(max_loops or config.swarm_rounds, config.swarm_rounds)` (a cap on the trained rounds, as D1's `max_loops` is), fixed (no HALT exit; record the mean desk HALT
probability of the last round as `halt_prob`). Each desk fetches its own `top_k` when its `ask > 0`
(not after the last round). Add keyword `lesion` to `PremonitionMini.answer`'s dispatch only through
`**kwargs` passthrough — simplest: give `PremonitionMini.answer` a trailing keyword `lesion: Optional[str] = None`
that raises `ValueError` if set while `thinkers == 1`, and is otherwise passed to `swarm_answer`.
Lesions (eval-only): `None`; `"board"` (board never written: notes and cards stay invalid — an S1 model
run as S0); `"notes"` (cards posted, notes never written); `"cards"` (notes, no cards).
Return `Answers(tokens, lengths, loops=[Q] rounds, first_top=desk 0's first top-k (NULL -> -1),
fetched=union over desks [Q, L+1], halt_prob, swarm={...})` with
`swarm = {"desk_fetched": [Q, M, L+1] bool, "desk_asks": [Q, M] long (rounds with ask > 0, counting only rounds
that can fetch, i.e. all but the last), "registers": [Q, M, registers, d] float (final rows), "notes": [Q, M, d] or
None, "rounds": rounds that can fetch (max(1, rounds - 1))}`.

## 9. Diversity report (`swarm.diversity(swarm_dict) -> dict[str, float]`)

* `fetch_overlap`: mean over questions and desk pairs (i < j) of Jaccard(desk_fetched_i, desk_fetched_j),
  NULL excluded, pairs with empty union skipped (NaN if none).
* `register_cos`: mean over questions and pairs of cosine(flattened registers_i, registers_j).
* `ask_rate`: list [M] mean `desk_asks / rounds` over the rounds that can fetch (a final-round ask never fetches,
  so it is not usage); `fetch_count`: list [M] mean cards per question.
* `collapsed`: `register_cos > 0.95 and fetch_overlap > 0.8` (the pre-registered collapse line).
* `silent_desks`: number of desks with `ask_rate < 0.05`.

## 10. train.py plumbing (minimal, flag-off untouched)

* `planned_loops`: when `config.thinkers > 1`, return `(2 if mode == "gold" else config.swarm_rounds) * thinkers`
  per question (desk-rounds), matching `metrics["question_loops"]`.
* `MiniTrainer._train_step`: `recorder = InsertLog(model) if track and config.store and config.thinkers == 1 else None`
  (card_stats assumes question indices).

## 11. Tests (`tests/test_premonition_swarm.py`, unittest, CPU, < 60 s total)

1. **Flag-off bit-identity vs the frozen copy.** For variants D, D-noask, D-noptr (tiny, `tiny_config`):
   `torch.manual_seed(s)` then build the live model and the frozen `tests._premonition_model_pre_swarm.PremonitionMini`
   with the SAME config; assert identical `state_dict` keys and `torch.equal` on every tensor; then for modes
   gold/teacher/own (fixed generators) assert `torch.equal` on loss/lm/ask/ans/halt and on every gradient after
   `backward`; and `answer()` (with and without `eager`) `torch.equal` on every Answers tensor, `swarm is None`.
   Also check `MiniConfig.preset("D")` full-size parameter count is still 2,013,140.
2. Parameter accounting: `parameter_breakdown()` of model == config for thinkers 2/4, board on/off, all variants.
3. Forward/backward finite in every mode for S0 (board off) and S1 (board on), M = 3; `question_loops == Q*rounds*M`;
   `gold_missing == 0`; grads finite; desk and board_type get non-zero grads in S1 teacher mode.
4. **Concurrency**: in one round `model.think` is called exactly once per round with batch dim `Q*M`
   (forward hook counting calls/shapes).
5. **Comm ablation is real**: S0 (board off): perturbing desk 1's register rows after `_start` must not change
   desk 0's rows after round 2 (independence, check via a hook or a small direct harness). S1: it must change them.
6. **Board lesion**: on an S1 model, `answer(lesion="board")` equals the answers of a model with identical weights
   but `swarm_board=False`... (weights differ in board_type only, which is unused when lesioned) — assert tokens equal.
7. **Merge-point binding**: synthetic case where only desk 2 fetched a card mentioning entity e: combiner valid
   mask shows slot e for desk 2 and hides it for the other desks; an entity bound nowhere shows only desk 0's copy.
8. **Assignment**: balanced split — with |need| = 5 and M = 2 every desk gets 2 or 3 cards, disjoint, union = need;
   with identical prefs it still splits; NULL-only need goes to exactly one desk.
9. **Board posting**: same card fetched by two desks in one round is posted once; FIFO wraps at board_cards;
   `post` equals a one-by-one FIFO on random rounds, including every row's embedding and the re-post of a card
   evicted earlier in the same round; `post` runs no host-syncing op (`NoSyncTest`).
10. Causality holds for the swarm: reuse the "answers ignore everything after the question" construction from
    `tests/test_premonition_model.py` with thinkers = 3, board on.
11. `diversity()`: identical desks -> collapsed True; disjoint fetches -> overlap 0.
12. A 25-step tiny training run of S1 reduces the loss (like `test_training_steps_reduce_the_loss`).

Then run: `python -m unittest tests.test_premonition_swarm tests.test_premonition_model tests.test_premonition_train`
and any other `tests/test_premonition_*.py` that imports model/config; all must pass.

## 12. Added in review (Opus, 2026-10-17)

* `MiniTrainer(seconds_budget=None)`: when set, `plan()` uses training seconds / budget (eval pauses
  excluded) and `train()` stops at the budget; `train_d(seconds_budget=…)` passes it. Needed for the matched
  wall-clock arms: with `flop_budget` out of reach, the FLOP share would leave the curriculum in "gold" forever.
  `train_seconds` enters `state_dict` only when the budget is set (flag-off checkpoints unchanged).
* Flag-off reports unchanged: `train_d` adds `swarm` / `seconds_budget` and `evaluate_d_checkpoint` adds
  `lesion` only when given.
* Eval `halt_prob` = sigmoid(mean desk HALT logit), the quantity HALT is trained on.
