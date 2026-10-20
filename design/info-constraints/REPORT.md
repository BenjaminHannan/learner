# Information constraints in PremonitionMini: audit check, new constraints, priced fixes

**Status: DRAFT.** Written 2026-10-18 (UTC) on branch `claude/info-constraint-solutions`, based on `main` at
73b8e0224 (the base that `claude/steals-8`, `claude/decoder-reader-kv` and `span-cards-solve` also build on).
No GPU, no spend. Nothing here merges. Every bid below is addressed to the coordinator and is not booked.

**Revised 2026-10-18 after S1-P0** (ruled E3: CPU toy runs in this session's container count as $0 probes).
S1-P0 came back **negative on eviction**. The ring never overflows, and the tiny-D toy model gives one
constant answer to every question, with or without cards. R2, item 8, N1, S1, S2's Stage 0 setting and the
ranking (d) are corrected below. The original claims are kept, struck through or marked "retracted", so
the change is visible. Result: §S1-P0 result, raw files under
`artifacts/claude-infoconstraints-20261018/`.

Labels: **shown** = read in the code or in a recorded artifact in this session; **suggested** = my reading
of what was shown; **untested** = not measured by anyone.

Method: eight Haiku readers fanned out over `premonition/config.py`, `model.py`, `store.py`, `card_pools.py`,
`data.py`, `batch.py`, `preprocess.py`, `pointer.py`, `train.py`, the B2 code (`custom_io/` on
`claude/b2-confirm-checkpoints`), the prior diagnostic reviews, and the in-flight branches. I read
`config.py`, `model.py`, `store.py`, `batch.py` and the relevant parts of `train.py` myself, and re-checked
every line number cited in sections (a) and the "big" rows of (b). Haiku items I could not re-check are
marked "(reader)".

---

## 0. Plain-language summary (for Ben)

The model reads a long story, writes one index card per line, and later fetches 4 cards at a time into a
16-card tray to answer a question. The coordinator listed where information gets squeezed. I checked each
one against the code and looked for more.

1. **I guessed the tray was the problem, and the free test says no.** I thought the model fetched 4 cards
   every loop and pushed its best cards out of the 16-card tray. When I re-ran the toy, it asked for cards
   on only one or two loops, so the tray never filled up. The test showed something else instead: the
   little toy model says **the same answer to every question**, even with no cards at all. So the famous
   "answers are at chance even when we hand it the right card" number is the score of a model that hasn't
   learned to answer yet. It tells us nothing about cards, the tray or the thinking block.
2. **Earlier experiments already showed two more real problems.** The thinking block smears every row with
   the same big update, which wipes card contents (a bypass fixed copying from 11% to 100%). And the answer
   writer picks a card by what answer word it holds, not by whose fact it is (giving it a "who and what"
   address raised choosing from 32% to 98%, but only when the address was handed in).
3. **Two coordinator items are about a different model.** The forgetting guard (G1, the 6,800-row test) is in
   the custom_io "parent" model, not this one. B2 does no search.
4. **Fixes, in the order to run them now:** (S2) give the answer writer an unwashed copy of each fetched
   card; (S1, kept for later) let a card that was pushed out be fetched again, and stop empty "NULL" cards
   from taking tray slots;
   (S3) give each card a learned "who and what" address that the answer writer uses to choose; (S4) let the
   card's key carry which people the line names, so fetching can tell facts about different people apart.
   Each starts with a free check on a laptop-sized toy before any money is asked for.

---

## 0b. Read first: what changes the picture

| # | The audit assumes | What the repo shows | Consequence |
|---|---|---|---|
| R1 | Measured numbers describe the main model | **No PremonitionMini checkpoint exists** (steals REPORT F1, `claude/steals-8:design/steals-2026-10-17/REPORT.md:16`). 7.4% / 24.2% / recall 0.90 come from tiny D (d = 32) trained 425 steps (130 s CPU) on the far-fact toy (`artifacts/claude-steals-20261017/qk-diagnostic.json` on that branch). The pool-mass, direct-reader and address-key numbers are from the ladder toy, 2,000 steps. The bypass / think-gated numbers (m02) are from the far-fact toy, gold mode, answer loss only, 600-800 steps (corrected 10-19). | Every "measured" row below is early tiny-D toy behaviour (shown). None is village behaviour. |
| R2 | "7.4% even with gold cards" isolates the answer path | **Revised after S1-P0 (shown, 3 seeds).** The tiny D of that diagnostic outputs **one constant answer** for all 256 held-out questions, in every condition: own retrieval, gold preloaded, gold preloaded with ASK off for 1-8 loops, and **no cards at all**. Accuracy (7.42 / 8.20 / 7.81%) is just the share of questions whose answer is that one value. It asks on 1-2 loops only (4-8 inserts per question), so the ring never overflows (0/256 on every seed). My first reading here was eviction (`asked_rate 1.0` read as "asks every loop"). That was **wrong**: `asked_rate` (`train.py:659`) counts questions that fetched at least once. | "Chance even with gold cards" is not evidence about the squeeze, Think, the decoder or the ring. It is an untrained (collapsed) answer path at 425 steps. S2 goes first (ruling E3). |
| R3 | The squeeze causes chance answers with gold cards | With the **same** one-vector cards, D-card-bypass and D-think-gated copy from a supplied card 1024/1024 vs D's 112/1024 on two seeds (`reviews/opus-milestone-02-m02-20260918-232457.md:149-156`, shown). The direct reader (one decoder row per token instead of one pooled row) did not improve choosing (170 vs 164, 162 vs 161; `reviews/opus-milestone-03-continuation-direct-reader.md:26-30`, shown). | For the shown failures, Think's row-shared update (norm 8.7, row spread 0.3; m02 review `:120-121`) and decoder selection-by-value matter more than pooling. The squeeze is real but is not the shown cause. |
| R4 | Direction-only matching loses gold rank | The raw key norm does not separate gold from the wrong cards that outrank it (+0.006 median gap); those wrong cards tie gold in direction (cos 0.992 vs 0.992). κ ≈ 13 (steals REPORT §3, shown). | The binding problem is **key collapse** (every fact card points the same way), not lost magnitude. The fix has to put new information into the key (S4; also steals `key_split`). |
| R5 | The forgetting guard is a PremonitionMini training constraint | There is no guard of any kind in `premonition/train.py` or `learnlab/` (grep: ewc, fisher, distill, kl, anchor, freeze, guard; reader, re-checked by grep). G1 (KL weight 30), G3, the 6,800-row test (parent 90.62%) and DEV parent 90.22 belong to the custom_io/domain parent model (`claude/forgetting-guard-review-prompt:reviews/gpt-forgetting-guard-choice-2026-10-18.md`; `claude/lt2-r2a-replica:domain/far/MARKS-L11-NKsoft-2026-10-12.md:8`). | Moved out of the PremonitionMini table. Noted under (e). |
| R6 | In-flight work | `span-cards-solve` (card **layout**, Stage 1 at $18 is live today), `claude/decoder-reader-kv` (decoder reads all reader states up to "[answer]"), `claude/steals-8` (12 flags incl. `key_split`, `delta_bind`, `fetch_gate`, `fetch_sink`, `row_halt`). | None of my four fixes duplicates these. Interactions are listed per fix and in the matrix in §(c). |

---

## (a) Audit verification table

All line numbers are `main` @ 73b8e0224 and were re-read by me unless marked (reader).

| # | Audit item | Verdict | Code evidence | Note |
|---|---|---|---|---|
| 1 | CardWriter pools each line into ONE value (d = 128) + ONE key (64) | **CONFIRMED** | `model.py:177-179` (`pool = Linear(d,1)`, `key = Linear(d,key_dim)`, `value = Linear(d,d)`); `:188-196` masked per-line softmax, then `self.key(pooled), self.value(pooled)`; key normalised at `store.py:65` | The pool is a fixed, question-blind direction (`pool` has no query). One pooled vector feeds the ASK key, the decoder's cross-attention key and the decoder's value. |
| 1m | "Two facts on one line share one vector; answers at chance even with gold cards" | **CORRECTED** | Village lines are mostly one fact: 11.9 tokens/line, ~0.6% visibly multi-update (`span-cards-solve:design/span-cards/01-design.md` §1, measured on 1,830 lines). The chance reading is a constant-output artifact (R2, S1-P0) and the copy failure is shown to be Think's update (R3). | What the pool does lose is shown: trained pools put 70-98% of mass on 1-2 tokens. Answer-only training kept the value (0.979) and lost the person (probe 116/2048). Retrieval training kept the relation (0.71) and lost the value (125/2048). Reader states keep both (2304/2304) (`reviews/opus-overnight-2026-09-19-ovn-20260918-235851.md:292-306`). So the squeeze is **within one fact**: person vs value. Two-fact blending is rare in this data. |
| 2 | Decoder cross-attends ONLY to the 76 think rows; an unfetched card is unreachable | **CONFIRMED, with nuance** | Training `model.py:571` (`_decode_logits(rows, ...)`), eval `:746` (`episode.x`); `Decoder.forward` `:286-288` attends `memory` only | The 40 question rows are reader states (`:419`), so the GRU summary of the visit reaches the decoder through them. An unfetched card's *content* is reachable only through that compressed state. The decoder also gets no card key, tag or line pointer. |
| 3 | Keys and query L2-normalised; score = κ·cos + age bias; magnitude discarded | **CONFIRMED (mechanism), CORRECTED (diagnosis)** | `store.py:110` (query), `:65` (keys), `:113-116` (κ·q·k, then bias, which κ does not scale); κ = `exp(log_kappa)`, unbounded (`model.py:257`, `:494`) | Values keep their norm. The magnitude loss is real but not what fails (R4). |
| 3m | Gold first 24.2%; recall@4 ≈ 0.90 | **CONFIRMED as recorded** | `qk-diagnostic.json`: `gold_ranked_first 0.2421875`, `recall_at_k 0.90234375` (steals-8) | Tiny D, far-fact toy, 425 steps (R1). Each toy question has exactly one gold card, so 3 of 4 fetches are wrong by construction. |
| 4 | Reader causal: GRU, local attn (window 64 + previous block), GRU | **CONFIRMED** | `config.py:27` `("gru","attn","gru")`, `:29` window 64; `model.py:119-123` (own block causal, plus the full previous block) | A query at offset p sees 64 + p tokens back (64-127). Beyond that, only the two minGRU states carry anything. A card never sees later lines: `CardWriter` reads causal states (`:183-196`). |
| 5 | Thinker sees only the last 40 question tokens | **CONFIRMED, cap non-binding** | `config.py:35`; `model.py:415-419` (`position = end - 40 + arange`, `question_ok = position >= start`) | `q_span` starts at the question **line** (`data.py:17`, `:359`), so rows before the question line are masked, not filled with context. The recorded `question_max` is 32 (`reviews/astra-design-2026-09-19/evidence.json:377`), so at least 8 of the 40 rows are always padding. On the toy, at most 5 tokens (`ovn_qread.py:22`). The real limit is "the question line only", not "40". |
| 6 | 16 entity slots (N_ENT = 16); pointer AUC ≈ 0.51 | **CONFIRMED (16); AUC NOT FOUND** | `batch.py:19`; slots `model.py:423-426` (valid only if mentioned, `:395-407`) | More than 16 names raises `NameOverflow` (`pointer.py:159-161`), which `data.py:406-409` does not catch, so the cache build aborts (reader). Recorded `names_max` 12 (`evidence.json:376`). I could not find the AUC 0.51 / "replicas" measurement for PremonitionMini. The only hit, `artifacts/claude-mu403-20260926/AUC.md:13`, is unrelated. The ladder toy's binding failure is shown elsewhere (changed-fact pairs 0/256, R3). |
| 7 | top_k 4 per ASK, max_loops 8, ONE ASK query from register 0 | **CONFIRMED** | `config.py:38-39`; `model.py:488-495` (`register = _norm(rows[:, _register_base])` feeds `halt`, `ask` and `query`) | Registers 1-3 feed no head. HALT reads the same row. |
| 8 | 16-row ring, position = count % 16; eviction rate unmeasured | **CONFIRMED (code); eviction NOT observed (S1-P0)** | `model.py:461`; `count` includes NULL inserts (`:452`, `:466`); `fetched` is never cleared on overwrite (`:467-468`) and fetched cards are ineligible (`store.py:95-97`) | An evicted card is gone for the rest of that question. ~~At the recorded toy behaviour there are 29 inserts into 16 rows~~ (retracted): measured 4-8 inserts per question, 0/256 overflow on 3 seeds. Latent: it bites only if ASK fires on ≥ 4 loops (16 / top_k). The counters already exist (`train.py:167-216`, `fifo_overflow_questions`, `fifo_gold_evicted_questions`). They read 0 in m02 only because m02 ran max_loops 4, top_k 1 (`design/research/broad-sweep-2026-09-19/README.md:187-189`). |
| 9 | Card time = one of 16 log2 age buckets | **CONFIRMED** | `config.py:40`; `store.py:28-30`, `:103`; row embedding `model.py:456-458` | Age is **line-index** distance, so question lines count. Ages 0 and 1 share bucket 0, as do 4-7 and 8-15. Bucket 15 needs ≥ 32,768 lines (never reached). Age enters twice: as a score bias and as a row embedding. |
| 10 | Memory is one visit; only lines before the question | **CONFIRMED** | `store.py:90` (`valid[q_visit] & line < q_line`), `:111` | Question lines never become cards (`store.py:63`). Episodes are per question: slots, ring and fetched set restart for every question of a visit (`model.py:410-436`). |
| 11 | Working memory 76 rows; 2 shared layers; 4 heads of 32 | **CONFIRMED, wording fixed** | `config.py:89-91`; `model.py:228` (two distinct layers), reused every loop `:486` | "Shared" means shared across loops, not between the two layers. The think rows have no positional code (`:213-218`), so ring order and question-token order are invisible apart from row-type embeddings. The step embedding is added and stored back every loop (`:237`, `:487`), so it accumulates in the rows. |
| 12 | Binder blends on write: s ← s + g(c − s) | **CONFIRMED, plus two details** | `model.py:242-245`; content = tanh(W_b[s; v]), g = per-channel sigmoid | Same raw value is written into **every** entity of the card's line (`:478-481`): role-blind. `MAX_LINE_ENTS = 4` (`batch.py:22`, `data.py:316`), recorded overflow 0. Steals `delta_bind` targets the overwrite. |
| 13 | Deep supervision: answer scored every loop with early_ans | **CONFIRMED, plus a bug-like coupling** | `model.py:566-587`; `have_all` from `fetched`, not residency (`:583`) | Loop 0 is always ×0.2 in teacher and own modes (reader). An evicted gold card counts as "have", so the answer is trained at full weight without it. "96.9% given a correct prefix / 4.3% assemble it": **NOT FOUND** in PremonitionMini. The nearest is custom_io plan-assembly work (`claude/plan-assembly-solve`), whose own conclusion is "bracket blindness, not plan assembly". |
| 14 | Answer cap MAX_ANSWER = 32 | **CONFIRMED** | `batch.py:20`; `data.py:651` (`ids[:MAX_ANSWER]` drops `<eos>` on overflow); decode `model.py:742-745` | Recorded `answers_over_max` 3, `answer_max` 64 (`evidence.json:369-371`). Digits are one token each (`learnlab/tokenizer.py:37`, reader). |
| 15 | Forgetting guard taxes new learning (90.22 → 33.16; G1 ≈ 0.7 drop) | **CORRECTED: not this model** | R5 | No sequential stage exists in `train_d` (`train.py:1041-1105`). The only PremonitionMini terms that tax learning are `early_ans` and the hard top-k (S1, (b) T-items). |
| 16 | ≈ 2.1M params is a ceiling | **CONFIRMED** | `config.py:13-16`: 2,013,140 at v1, 2,102,228 at v2 (the tokenizer to use); band 1.9-2.15M `:13`, enforced `:70-74` | Embeddings are 39-41% of the total (817,664 at v1). Every fix below costs ≤ 0.9%. |
| 17 | B2: no card squeeze; caps are 8 loops, fixed registers, program and answer caps, and search | **MOSTLY CONFIRMED; "search" CORRECTED** | B2 = `custom_io/models/ledger.py` (`Ledger`, `copy=True`; `models/__init__.py:8-12`, `design/design-B2.md:1`). Reader K/V once, controller re-attends every loop: `ledger.py:289`, `:294-301`, `:117-118`. 8 loops `:127`; 8 control + 9 registers `:59`; 7 program steps `progparse.py:8`, `:199`; 8-char GEN answers `data.py:11` | **No search.** Decoding is greedy and programs are hand-parsed: `progparse.py:1` "Hand-written, no search". The queries are 17 controller tokens, not workspace slots. B2's own caps: prompt ≤ 208 chars (`data.py:11`); numbers read by regex, not learned (`ledger.py:194-197`); 16 numbers, 64 words. Its "no squeeze" is partly because inputs are short. |

---

## (b) New constraints

"Big" marks the ones I think bind the shown failures. Every measurement listed is $0 (data counts,
eval-only, or a CPU toy run).

### Fetch and ring (the biggest new group)

**N1 (latent; downgraded after S1-P0). Ring eviction once ASK fires on ≥ 4 loops; it hits the best cards first.**
- Where: `model.py:461` (FIFO position), `:707` (8 loops), `:725` (insert whenever ASK > 0), `config.py:36-39`.
- Loses: if ASK fired on every loop with no halt, the first ASK's top-4 would be overwritten at loop 5, and
  the answer would be decoded from ranks 13-28.
- Measured (S1-P0, tiny D, far-fact toy, 3 seeds): 4-8 inserts per question, 0/256 overflow. Not active in
  that model. ~~It can by itself explain answers at chance~~ (retracted).
- Why it still matters: a model that learns to keep asking (own-mode training rewards asking while gold is
  missing, `model.py:597-599`) would reach it. Measure it on DEV (S1-P1) before building S1.
- Measure ($0): existing `InsertLog` + `card_stats` (`train.py:130-216`) around `answer()` and
  `answer_with_gold()`. Count overflowed questions, gold evicted before decode, NULL inserts, and the loop at
  which the last gold card left the ring.

**N2 (BIG). An evicted card can never be re-fetched.**
- Where: `model.py:467-468` sets `fetched` and nothing clears it; `store.py:95-96` `ok &= ~fetched`.
- Loses: the card for the rest of the question.
- Measure: same probe. Count evicted cards whose score at the answering loop would rank in the top-4.

**N3. NULL is re-fetchable and takes a ring row each time.**
- Where: `store.py:97` `ok[:, self.null] = True` after the fetched mask; `model.py:452` counts it.
- Loses: one real card per NULL fetch. Train/eval mismatch: training never re-requests NULL (`model.py:597`).
- Measure: NULL inserts per question at eval (the recorded toy run had 0 NULL fetches, so this matters for
  village "not told" questions).

**N4. Supervision treats "fetched" as "present".**
- Where: `model.py:583` (`have_all`) and `:597` (`need`).
- Loses: the learning signal stays correct-looking while the gold card is gone. The answer is trained at
  full weight on a tray without it.
- Measure: per (question, loop), the share of full-weight answer terms whose gold set is not resident.

**N5. The halt never fires, so the ring always fills.**
- Where: HALT is BCE on teacher-forced per-loop correctness (`model.py:579-588`) and is never executed in
  training (all questions run `n_loops`, `:566-567`). Eval stops at p > 0.5 (`:720`).
- Loses: the ability to stop before eviction. Shown at halt_rate 0.0 (toy) and in m03 ("asked every loop,
  never halted", `reviews/opus-milestone-03-m03-20260919-071009.md:139`).
- Measure: halt-probability histogram per loop. Steals `row_halt` is the in-flight fix.

**N6. Retrieval is trained only by oracle evidence labels.**
- Where: hard top-k (`store.py:122`), no straight-through anywhere; own-mode picks use `scores.detach()`
  (`model.py:610`). L_ans and L_halt never reach the query or keys. Keys learn only "is this an evidence
  line" through the set CE (`:600-601`).
- Loses: any signal that a card helped answer.
- Measure: correlation, over eval questions, between "gold in top-4" and "answer correct". Near 0 means the
  two are learned apart.

**N7. One gold card in the top-4 satisfies the set CE.**
- Where: `store.py:33-35` (−log Σ_gold softmax). Chains need every card.
- Measure: `full_gold_fetched` vs `any_gold_fetched` (already in `summarize_cards`).

**N8. Teacher regime differs from eval regime.**
- Where: teacher inserts up to 4 gold + 1-2 random distractors per loop for ceil(|G|/4) + 3 loops
  (`model.py:541-542`, `:634-654`). Eval inserts the model's 4 per loop for 8 loops.
- Loses: the model never trains on a full ring. At the 30% phase switch, loop count and retrieval source
  change together (`train.py:96-103`).
- Measure: overflow counter in teacher mode (non-zero only for |G| ≥ 11, < 1% of questions,
  `batch.py:21`) vs own and eval modes.

### Card store and keys

**N9 (BIG). Keys collapse: every fact card points the same way.** Shown in R4. Where: one pooled vector →
64-d unit key (`model.py:196`, `store.py:65`). Loses which fact a card holds; ASK separates fact from filler
only. The key has no entity identity, although `store.ents` already holds the line's entity ids
(`store.py:44`, `:67-68`). Measure: cos between gold and the best wrong card (done: 0.992 / 0.992), and the
$0 ceiling count in S4-P0.

**N10. Card rows carry value + age + type only.** Where: `model.py:458-459`. Lost at insert: the key, the
exact line index, the fetch round, the tag (`store.tags`) and the diary pointer (`line_start`, `line_len`).
`tags` has no consumer; `line_len` is used only by `address_reader.py:116`. The thinker and decoder cannot
tell two cards from the same age bucket apart except by content.

**N11. Age is in line units, counts question lines, and is fixed at insert.** `store.py:103`,
`model.py:456`. Minor.

**N12. A line whose last token is outside the batch tensor gets no card, silently.** `store.py:57-63`
(`card_end`). Visits are kept whole by `length_batches` (`data.py:666-691`), so this is latent (reader).

**N13. Gold evidence is silently dropped from targets.** Gold lines at or after `q_line`, without a valid
card, or older than the newest 16 (`data.py:653`) are removed. Only `gold_missing` traces it
(`store.py:149-157`, `model.py:550`). Recorded `gold_max` 15, `gold_over_max` 0 (`evidence.json:372-373`).

### Think, binder, decoder

**N14 (BIG). Think writes a row-shared update over every row, washing card contents.**
- Where: `ThinkLayer` (`model.py:213-218`) applied to all 76 rows, stored back each loop (`:486-487`). The
  decoder reads the post-Think rows (`:571`, `:746`).
- Shown: row-shared update norm 8.7, row-to-row spread 0.3 in collapsed questions (m02 review `:120-121`).
  Bypassing Think for the decoder's card rows copies 1024/1024 vs 112/1024.
- Measure ($0, eval-only): cosine between each card row as inserted and the same row after loop t.

**N15 (BIG). The decoder chooses a card by its value, not by its address.**
- Where: `Decoder.forward` `model.py:287` builds K and V from the same normalised row, so a card row's
  attention key is a function of its value vector.
- Shown: replacing the card-row key with a (person, relation) address raised choosing 164 → 503/512 and
  161 → 467/512, and changed-fact pairs 0 → 239/256 (`reviews/opus-milestone-03-address-keys-results.md:70-74`).
  That address was a **layout parse handed in**, so it is a ceiling, not a fix.

**N16. The decoder's first query is question-blind.** Decoder input starts at the "[answer]" token
(`model.py:560-561`, `:741`). Its first cross-attention query is the same for every question, so selection
depends only on what Think already marked. `+qread` reads 512/512 but chooses 164-169 (overnight review
lines 194-206), so this is not sufficient alone (shown).

**N17. Binder is role-blind.** The whole line value goes to every entity on the line (`model.py:478-481`).
"Kelo gave Pata the kite" writes the same vector into Kelo's and Pata's slots. A slot's validity is fixed
at start (`:426`), so binding an unmentioned entity is invisible.

**N18. Register 0 carries every decision.** ASK, HALT and the query come from one LayerNormed row
(`model.py:488-495`). The query cannot be sharpened without moving HALT.

**N19. LayerNorm removes scale twice on the answer path.** Reader output norm (`model.py:163`, `:168`) and a
parameter-free LN on every decoder memory row (`:287`), which also normalises away the age and row-type
offsets added to card rows.

**N20. Greedy decode and no copy pointer.** ENT ids are emitted through the tied embedding (`model.py:747`).
The "copy constraint" is an inference-only mask (`:738-740`); training CE is unmasked (`:574`).

### Reader and input

**N21. The minGRU state is nonnegative.** `g(x) > 0` (`model.py:46-48`), h_0 = 0, so h ≥ 0; sign comes back
only through the output gate (`:91`). Long-range content beyond 127 tokens lives in this state.
Timescales start log-uniform over 2-512 tokens (`:361-364`). Minor, but it is the only channel for an
unfetched card.

**N22. Unbound target names cannot be answered by pointer.** A name that appears only in a target is
spelled out (`preprocess.py:218-225`) and scores as `<entK>` (reader). Label-free input also removes every
earlier answer and feedback (`preprocess.py:138-141`), by design. Measure: `cache.target_unbound.mean()`.

**N23. Name detection is exact-string and regex-split.** "Mara-Lee" becomes two entities. A capitalised
ordinary word never seen lowercase becomes a name (`pointer.py:33`, `:81`; reader). Headroom over the
13-name generator max is 3 slots (N_ENT 16), and overflow aborts the build (item 6).

**N24. Lowercasing of non-names; digits one per token** (`learnlab/tokenizer.py:37`, `:185-186`; reader).
Matters for answer length and scoring normalisation.

### Training time

**T1. `early_ans` ×0.2 lands where retrieval fails.** Questions whose own retrieval never collects all gold
keep ×0.2 at every loop (`model.py:582-586`). Answer learning is weakest exactly where retrieval is weak (a
selection bias).

**T2. HALT target is teacher-forced exact match.** `model.py:579-588`. HALT learns "would the gold-prefix
answer be argmax-correct", not "is the free-running answer right" (N5).

**T3. Loss scales are not comparable** across L_lm, L_ans, L_ask and L_halt (different normalisers,
`model.py:389-390`, `:617-623`), under one global clip at 1.0 (`train.py:313`) and a constant LR after
warmup (`learnlab/train.py:99-101`) (reader).

**T4. Train depth ≤ 3, eval depth ≤ 6** (`learnlab/village/scheduler.py:39`). Loops beyond the
teacher's ceil(|G|/4) + 3 are trained only in own mode.

**T5. D vs D-noask is confounded by the loss schedule.** D-noask drops `early_ans` and L_ask
(`model.py:582-586`, `:594-595`), so the store comparison is not "the store alone".

**T6. Validation is the first 256 visits in cache order and never selects a checkpoint**
(`train.py:1074`, `:1095-1104`).

**Out of scope, flagged:** contender E trains on the legacy cache with earlier answers and feedback in
context but is scored label-free (`premonition/contenders.py:221-224`, `:521-523`, `:256`; reader, not
re-checked). If true, it is a train/eval input mismatch for E, not D.

---

## (c) Solution designs

House pattern for every fix: one named mechanism behind its own default-off flag. Flag off is
bit-identical to 73b8e0224, proved the way `claude/steals-8` does it (`tests/test_premonition_steals_identity.py`:
`torch.equal` over init, RNG stream, the three training modes, gradients, `answer()` with wipes,
`answer_with_gold`, trainer steps; D, D-noask, D-noptr; seeds 0 and 1). Stage 0 is a $0 probe. Any spend is a
bid. Shared bars are the house ones: paired difference per seed, mean(d) − 2·SD(d)/√n > 0, d_s > 0 in at
least 2 of 3 seeds, DEV non-inferiority −3 points (steals REPORT §5; reader-kv RUN-CARD §4).

One clarification first: my S-numbers are ordered by the order I would run them, not by the audit's order.
The audit's big three map as follows: **squeeze → S3**, **writer's blind spot → S2**, **direction-only
fetch → S4**. **S1** is the biggest new constraint (N1-N4).

### S1. `ring_resident`: "fetched" means "in the tray"

**Targets:** N1-N4 (new). Prerequisite reading for every answer-path number, including the coordinator's
"7.4% with gold cards".

**Mechanism.** One semantic change: a card counts as fetched only while it occupies a ring row.
1. When `_insert` overwrites a ring row, clear the evicted card's `fetched` bit. That card is eligible again
   at the next ASK. A gold card that still scores in the top-4 comes back by itself.
2. NULL takes at most one ring row per question. Re-picking NULL while it is resident inserts nothing.
3. `have_all` and `need` (`model.py:583`, `:597`) read the resident set, so an evicted gold card is asked
   for again and the answer is not trained at full weight without it.

**Flag:** `MiniConfig.ring_resident: bool = False`. It needs a `[Q, card_rows]` long tensor `episode.held`
(card index per ring row, −1 empty) next to `episode.fetched`. Cost: 0 parameters, O(Q·16) bookkeeping.

**Bit-identical when off:** `_insert` keeps its current code path, and `held` is neither allocated nor read.
`card_stats` gains a residency-aware counter that is only reported, never used in a loss.

**Sketch** (inside `_insert`, after `position` is computed; flag on only):
```python
if config.ring_resident:
    slot = position[real] - self._card_base
    old = episode.held[who[real], slot]                         # card leaving each overwritten row
    gone = old >= 0
    episode.fetched[who[real][gone], old[gone]] = False         # 1. evicted -> eligible again
    episode.held[who[real], slot] = cards[real]
# 2. before computing `order`: drop NULL picks when NULL is already held for that question
# 3. in forward: resident = scatter of episode.held -> [Q, L+1] bool; have_all/need use it
```

**$0 probes.**
- **S1-P0 (decides whether S1 and the coordinator's headline are what they look like).** Re-run
  `claude/steals-8:scripts/premonition_steals_qk_diagnostic.py` unchanged (tiny D, far-fact toy, 425 steps,
  about 130 s CPU) for seeds 0-2. On the trained model, evaluate `answer_with_gold` and `answer` three ways:
  (i) as recorded; (ii) `max_loops = 4`, so 1 + 3 × 4 = 13 ≤ 16 and nothing is evicted; (iii) ASK
  suppressed after the preload. Log `card_stats` for each.
  - If (ii) or (iii) lifts gold-card accuracy above 25% while (i) stays near 7.4%, eviction is shown to
    mask the answer path.
  - If all three stay at chance, the Think wash (N14) is the binding cause, and S2 goes first.
- **S1-P1 (eviction rate on DEV, the named probe).** The same counters on the first funded village
  checkpoint (any line's), eval-only, CPU or the box already running. $0.

#### S1-P0 result (run 2026-10-18 in this session's container, CPU, $0; ruled E3)

Script: `scripts/info_s1_p0.py` (additive; `premonition/` untouched). It trains the same tiny D as the
steals QK diagnostic (`train_toy`, `ToySpec()`, 380 requested steps, 16 visits, 425 steps run), torch
2.14.1+cpu, seeds 0-2, 89-149 s of training each. The decision line was fixed in the script's docstring
before the run. Raw: `artifacts/claude-infoconstraints-20261018/s1-p0b-seed{0,1,2}.{json,log}` (the
first pass `s1-p0-seed*` gave identical accuracies and lacked the two columns added below). 256 held-out
questions per seed; chance 6.25%.

| condition | seed 0 acc | seed 1 acc | seed 2 acc | inserts / question (s0/s1/s2) | ring overflow (questions) | distinct answers |
|---|---|---|---|---|---|---|
| own (as shipped, ≤ 8 loops) | 7.42% | 8.20% | 7.81% | 4.00 / 8.00 / 3.75 | 0 / 0 / 0 | 1 / 1 / 1 |
| own, max_loops 4 | 7.42% | 8.20% | 7.81% | 4.00 / 8.00 / 3.75 | 0 / 0 / 0 | 1 / 1 / 1 |
| gold (as recorded) | 7.42% | 8.20% | 7.81% | 5.00 / 5.38 / 3.81 | 0 / 0 / 0 | 1 / 1 / 1 |
| **gold, max_loops 4** | **7.42%** | **8.20%** | **7.81%** | 5.00 / 5.38 / 3.81 | 0 / 0 / 0 | 1 / 1 / 1 |
| gold, ASK off, 1 loop | 7.42% | 8.20% | 7.81% | 1 | 0 | 1 / 1 / 1 |
| gold, ASK off, 2 loops | 7.42% | 8.20% | 7.81% | 1 | 0 | 1 / 1 / 1 |
| gold, ASK off, 4 loops | 7.42% | 8.20% | 7.81% | 1 | 0 | 1 / 1 / 1 |
| **gold, ASK off, 8 loops** | **7.42%** | **8.20%** | **7.81%** | 1 | 0 | 1 / 1 / 1 |
| no cards, 1 loop (removal control) | 7.42% | 8.20% | 7.81% | 0 | 0 | 1 / 1 / 1 |

Seed 0's `own` reproduces the recorded 0.07421875 exactly.

**Verdict against the pre-set line (shown):** gold-card accuracy with `max_loops = 4` and with ASK off after
the preload stays at chance on every seed, far below 25%. The ring never overflows. **Eviction is not the
cause.** Per ruling E3, **S2 goes first**.

**What it does show (shown, and new):** every condition produces the *same single answer* for all 256
questions. The answer does not change with the card present, absent, fresh (1 loop) or after 8 loops. At
this budget the answer path has collapsed to the most frequent value. That is upstream of every fix
here: no card mechanism can be read through a decoder that ignores its memory.

**Consequences:**
1. The "7.4% even with gold cards" headline should be re-labelled "answer path collapsed to a constant at
   425 toy steps". This touches the steals REPORT F2 ranking argument too.
2. Any Stage 0 on the far-fact toy needs a budget where the control is *not* constant. I added a guard to
   every Stage 0 below: **the control must give > 1 distinct answer, else the cell is void, not a fail.**
3. S2's Stage 0 moves to the m02 protocol (far-fact toy, gold mode, answer loss only; corrected 10-19, it is not the ladder toy), where D reached 112/1024 (not constant) and bypass
   reached 1024/1024. See S2.
4. S1 stays designed but is **not built** until S1-P1 shows eviction on a trained model.

#### Plain-D step sweep (run 2026-10-19, CPU, $0; coordinator GO 10-19, step 1)

Same script and protocol as S1-P0 (`train_toy`: the full curriculum gold → teacher → own, all four losses,
far-fact toy, 256 held-out questions per seed). Only the budget changes. Raw:
`artifacts/claude-infoconstraints-20261018/sweep/plainD-steps{1000,2000}-seed{0,1,2}.{json,log}`. The 380 rows
are S1-P0's `s1-p0b` files. Chance 6.25%.

| requested / run steps | seed | own acc | gold acc | gold, ASK off, 8 loops | no cards | distinct answers (own / gold / no cards) | gold: ring overflow (questions /256) |
|---|---|---|---|---|---|---|---|
| 380 / 425 | 0 | 7.42% | 7.42% | 7.42% | 7.42% | 1 / 1 / 1 | 0 |
| 380 / 424 | 1 | 8.20% | 8.20% | 8.20% | 8.20% | 1 / 1 / 1 | 0 |
| 380 / 424 | 2 | 7.81% | 7.81% | 7.81% | 7.81% | 1 / 1 / 1 | 0 |
| 1000 / 1115 | 0 | 3.91% | 3.91% | 3.91% | 3.91% | 1 / 1 / 1 | 0 |
| 1000 / 1115 | 1 | 6.64% | 6.64% | 6.64% | 6.64% | 1 / 1 / 1 | 0 |
| 1000 / 1115 | 2 | 7.42% | 7.42% | 7.42% | 7.42% | 1 / 1 / 1 | 0 |
| 2000 / 2230 | 0 | 5.47% | 5.47% | 5.47% | 5.47% | 1 / 1 / 1 | 65 |
| 2000 / 2229 | 1 | 7.42% | 7.42% | 7.42% | 7.42% | 1 / 1 / 1 | 0 |
| 2000 / 2228 | 2 | 5.08% | 5.08% | 5.08% | 5.08% | 1 / 1 / 1 | 0 |

**Reading (shown):**
- **At every budget and seed, every arm gives exactly one answer to all 256 questions.** That is 9 of 9
  cells, with no card, a fresh gold card, or 8 loops on it. Accuracy (3.9-8.2%) is just how often that one
  value is right.
- Under D's own curriculum, the far-fact toy's answer path does not come alive by about 2,230 steps.
- The ring does overflow once the model learns to ask more: 65/256 gold-card questions at 2,230 steps on
  seed 0, all of them losing the gold card. This is the first observed instance of N1. It changes nothing
  while the output is constant.
- **Consequence:** the far-fact toy under the full curriculum cannot read any answer-path fix at ≤ 2,230
  steps. Every such cell would be VOID under the 10-19 rule. S2 Stage 0 uses the m02 protocol instead (gold
  mode, answer loss only, where m02 recorded D at 112/1024 and bypass at 1024/1024), with the same VOID rule.

**Paired A/B (Stage 0, CPU, $0; only if S1-P1 shows eviction).** Far-fact toy, D vs D + `ring_resident`, paired init (S1 adds no
parameters, so both arms draw the same stream), 3 seeds, 425 steps.
- Primary: own-retrieval answer accuracy at eval, no `max_loops` override.
- Bar: d_s > 0 on 3/3 seeds and mean ≥ +5 points.
- Guards:
  - recall@4 of the first ASK is not lower than control −0.02 (S1 must not move retrieval);
  - L_lm within 1% of control;
  - fetched cards per question not above control +50% (churn check);
  - on untold questions, NULL-only answers ("nobody") not below control.
- Proves it wrong: P0 shows no eviction effect and the A/B gain is within noise.

**Funding bid (to the coordinator, not booked):** none until S1-P0 reports. If P0 and the toy A/B pass:
Stage 1 timing smoke **$0.30 cap**, Stage 2 three pairs at F ≈ 3.15e16 **$2.50 cap** on the RTX 5090
on-demand class, costed as in `artifacts/claude-rkv-20261017/BID.md` (expected $0.80-1.85). See question E5
on the cost model.

**Interactions:** `row_halt` (steals) attacks N5 from the other side. If halting works, eviction falls. The
two should be measured separately, then together. `ask_reuse` (steals) caches rankings, so with S1 an
evicted card can re-enter from the cache. Test that combination before merging both.

### S2. `decoder_raw_cards`: the writer sees an unwashed copy of every resident card (writer's blind spot)

**Targets:** audit item 2 (the decoder sees only post-Think rows) and N14 (Think wash). It does not try to
make unfetched cards reachable. That is `decoder_reader_kv`'s job, and I do not duplicate it.

**Mechanism.** Keep a decoder-only copy of each card row exactly as inserted (value + age + row type), in 16
rows aligned with the think ring (same position, overwritten together). Decoder memory becomes
76 think rows + 16 raw rows = 92, with the raw rows' valid mask equal to the card rows' mask. Think is
unchanged: it still sees and updates its own card rows.

This differs from D-card-bypass (`premonition/answer_path.py`), which *replaced* the post-Think card rows
and so removed Think's card work from the decoder. Here they are **added**.

**Flag:** `decoder_raw_cards: bool = False`. 0 parameters (raw rows reuse `row_type[ROW_CARD]`). Cost: +16
memory rows in one cross-attention, about +0.3% training FLOPs (estimate, untested).

**Bit-identical when off:** the episode gets an optional `raw` tensor that is `None` when off. `_decode_logits`
concatenates only when it is present.

**Evidence it can work (shown, far-fact toy, m02 protocol; corrected 10-19 from "ladder toy"):** bypass and gated copy 1024/1024 vs 112/1024 on 2 seeds (m02).

**$0 probes.**
- **S2-P0 (wash probe, eval-only).** On the S1-P0 models: cosine and value-probe decodability of each card
  row as inserted vs after loops 1..8 (N14 measure).
- **S2-P1 (per-head masking, the named probe).** On the Stage-0 treated checkpoints, mask each decoder head's
  access to the raw rows, then to the post-Think card rows, and report the accuracy drop. This shows which
  path the answer actually uses. Run it on DEV once a village pair exists.

**Paired A/B (Stage 0, CPU, $0). Revised after S1-P0: the far-fact toy at 425 steps collapses to a constant answer, so it cannot read S2.**
- Ladder toy, the m02 protocol (`reviews/opus-milestone-02-m02-20260918-232457.md`: 256 visits x 4
  questions, fresh bindings, writer-produced gold cards, untouched test run once per checkpoint), 3 seeds.
  Control = plain D (S1 did not pass). Per E4, this is also the plain-D pair.
- Validity guard first: the control must give > 1 distinct answer and must reproduce D's ≈ 11%
  (112/1024 in m02) within its Wilson interval. Otherwise the cell is void.
- Primary: supplied-gold-card accuracy on the test split.
- Bar: ≥ 50% on 3/3 seeds. This is a large effect: bypass reached 100% here.
- Second reading: the same pair on the far-fact toy at the budget where the control first gives > 1
  distinct answer (found by a $0 step sweep of the control alone: 425, 1,000, 2,000 steps).
- Guards (the reader-kv guard, so a gain counts only if cards are used):
  - removing the cards drops treated accuracy to within 3 points of chance;
  - fetched cards per question ≥ 80% of control;
  - recall@4 ≥ control −0.02;
  - L_lm within 1%.

**Funding bid:** after Stage 0 passes, Stage 1 **$0.30** + Stage 2 **$2.50** caps, same cost model.

**Interactions:**
- `decoder_reader_kv`: both widen decoder memory. Reader-kv is fetch-blind and S2 is fetch-gated. If both
  pass alone, run the combination once and apply reader-kv's own guard (a fetch-use drop of more than 20%
  means "writer bypassed the thinker").
- `fetch_gate` (steals R2) gates the card → decoder path. With both on, its gate should cover the raw rows
  too. Test separately first.
- S3 below uses the raw rows' aligned positions.

#### S2 Stage 0 result (run 2026-10-19, CPU, $0; card `S2-STAGE0-CARD.md`, sealed at 7f4f10a9a before the run)

Protocol: m02 far-fact toy, gold mode, answer loss only, 2 loops, 800 steps, 1,024 test questions. One change:
`decoder_raw_cards`.

| seed | control acc (/1024) | treated acc (/1024) | d | control distinct (256 / 1024) | treated distinct (256 / 1024) | no card: control / treated | train s (control / treated) |
|---|---|---|---|---|---|---|---|
| 0 | 10.94% (112) | **100.00% (1024)** | +0.891 | 2 / 2 | 16 / 16 | 5.66% / 7.03% | 178 / 180 |
| 1 | 12.60% (129) | **100.00% (1024)** | +0.874 | 2 / 2 | 16 / 16 | 6.93% / 6.64% | 184 / 181 |
| 2 | 10.94% (112) | **100.00% (1024)** | +0.891 | 2 / 2 | 16 / 16 | 5.27% / 0.00% | 182 / 180 |

**PASS on every sealed mark** (valid seeds 3/3; mean d +0.885, mean − 2·SE +0.874; card-use guard held). The
unwashed copy turns plain D's 11-13% into 100% on supplied cards, and the gain comes from reading the card
(no card: chance). It matches the D-card-bypass precedent while keeping Think's own card rows in the decoder's
memory. **Not yet bought:** choosing among cards, own retrieval, village. Next, per card §7: the distractor
reading (gold + 2 fact cards), then a Stage-1 bid priced by measured seconds per update (E5). With S2 passed,
the E4 cumulative base for S3 is D + S2.

#### S2 code review (E6; Claude Code built-in `/code-review`, high, on `main...branch`)

**Round 3 (final design).** The review's root finding was that raw rows held outside `episode.x` had to be
re-added at every decode call site. They now live **inside the episode**: 16 rows after the 76 think rows.
- `_step` runs Think on the first 76 rows only.
- `_insert` writes each card into the same ring slot of both blocks, with its own mask bit.
- So every decode path that reads `episode.x`/`episode.valid` (base, subclasses, scripts) sees them with no
  extra call. The `_memory` helper and the subclass guard are gone, and `forward`/`_greedy` are back to the
  base text.
- Also fixed:
  - the FLOP hand count includes the raw rows (tested against the measured count);
  - the identity tests skip, not error, without the base commit;
  - the runner records the steps actually run and gives no verdict unless all six runs are present;
  - output paths are repo-relative.
- **Equivalence (shown):** re-running Stage 0 treated seed 0 with the final code at 1 thread (as filed)
  reproduces the filed run exactly: all 9 logged losses, 1024/1024, no-card 72/1024, distinct 16/1.
  The same run at 4 threads drifts in the 4th decimal from step 200 (summation order) and gives the same
  scores. So the filed Stage 0 result stands for the final code.

**Round 4.**
- **Fixed:** the flag is refused on any subclass that overrides `_start`, `_insert`, `_step`, `_greedy` or
  `_decode_logits`. Those subclasses own the episode layout or the decode path: CardBypass, the qread family
  incl. direct/address readers, softread. Subclasses that only change Think or the writer (ThinkGated,
  ThinkCentered, TwoPool, MeanPool) stay allowed. This is tested both ways.
- **Fixed:** the summarizer checks mark 5 over every run, VOID or not. The dead bare-episode test is replaced.
- **Kept:** two extra out-of-place copies in `_insert`/`_step` with the flag on (16 of 92 rows; cost not
  material at this size), and the `variant` label (see round 2).
- The final summarizer re-applied to the filed Stage 0 files gives the same PASS (`summary.json` unchanged).

Earlier rounds (1-2), superseded where they conflict with rounds 3-4:
- **Fixed** in e35f43df3 and the next commit:
  - the flag is refused on any subclass that overrides `_greedy` or `_decode_logits`, and without a store;
  - `_memory` tolerates bare `x`/`valid` episodes (a flag-off regression for
    `scripts/premonition_binding_probe.py`, now tested);
  - the ring test uses distinct real cards;
  - `_greedy` builds memory once;
  - device-safe probe scripts;
  - `wilson(0, 0)` guard;
  - `score()` restores train/eval mode;
  - the stale "ladder toy" wording here.
- **Kept, with reasons:**
  - (i) the identity test pins 73b8e0224, the house pattern from steals-8 (Q41: a later branch rebases and
    re-runs its harness against the new base);
  - (ii) a flag in base D rather than a `CardBypassMini`-style subclass, as ruled in E6 (flags, default off);
  - (iii) external diagnostic scripts that call `_decode_logits(episode.x, ...)` directly would skip the raw
    rows. They run frozen snapshots or older variants. `_memory`'s docstring states the rule, and no S2
    readout uses them;
  - (iv) `MiniConfig.variant` stays "D" (the flag is recorded explicitly in every S2 artifact; changing the
    variant string would touch identity checks shared with other lines);
  - (v) the duplicated gold-preload block in probe scripts. These are additive scripts, and the runner card
    names the protocol it copies.

### S3. `card_address`: a learned "who and what" address for choosing (the squeeze)

**Targets:** audit item 1 as it is shown to bite: one pooled vector serves as ASK key, decoder selection key
and answer value, and the pool concentrates on person or value but not both (item 1m, N15). The fix
separates **selection** from **content** on the decoder side, learned from text, with no layout parse.

**Mechanism.**
- A second pool `addr_pool: Linear(d, 1)` and a projection `addr: Linear(d, d)` build an address
  `a_l = addr(Σ_t softmax(addr_pool(h))_t h_t)` per line. Same masked per-line pool as `card_pools.pool_lines`.
- `CardStore` carries `addresses [B, L, d]`.
- On insert, each card's `a_l + age + type` goes into a 16-row address buffer aligned with the ring.
- In the decoder's cross-attention, card rows take their **keys** from `cross_k(_norm(address row))` and
  their **values** from the card row as today. Question, slot and register rows are unchanged. The K half
  of `cross_kv` is reused, so the decoder gets no new parameters.
- Parameters: 129 + 16,512 = 16,641 (+0.8% at v2).

Why this is not the failed two-pool: two-pool's second pool reached only ASK, which the decoder never sees
(m03 review lines 189-190). Here the address is trained by L_ans through decoder selection, the path
address keys proved decisive. Why it is not `address_reader`: no token-1/token-2 parse and no
non-contextual embeddings. The address is learned from the same causal reader states. `address_reader`'s
503/512 is the ceiling to compare against.

**Flag:** `card_address: bool = False`. Flag on is not identical at init (keys change source), which is
intended. Flag off is bit-identical. The new modules are built inside `torch.random.fork_rng` and
`addr_pool` is initialised as a copy of `pool`, as `card_pools.py` does, so the global stream after
construction matches the control.

**$0 probes.**
- **S3-P0 (pool-mass probe, eval-only).** On the S1/S2 Stage-0 models, record pool mass on
  [person, relation, value, filler] and the person/value linear probes (the overnight protocol). This tells
  whether the single pool still drops one role once S1 and S2 are on. If it keeps both (person and value
  probes ≥ 1900/2048), S3 drops in priority.
- **S3-P1 (Stage 0 A/B, CPU, $0).** Ladder toy, the m03 / address-keys protocol: 2,000 steps, 3 seeds.
  - Control: D + whichever of S1/S2 passed. Treated: control + `card_address`.
  - Primary: choosing 1-hop /512 on validation.
  - Bar: d_s ≥ +0.15 on each seed (the oracle reached +0.60 to +0.66).
  - Guards:
    - single-fact reading ≥ control −0.03;
    - changed-fact pairs both-correct must rise (the binding readout; control 0/256);
    - recall@4 ≥ control −0.02;
    - address-pool mass on the value token < 0.5 (else the address learned the value and the result is
      selection-by-value again).
  - Proves it wrong: choosing gain < 0.05 on every seed with address mass on person + relation ≥ 0.5. That
    would mean a good address exists and the decoder still does not use it.

**Funding bid:** Stage 1 **$0.30** + Stage 2 **$2.50** caps after P1 passes, on the village ruler, with the
reader-kv primary readout once the coordinator defines it (reader-kv RUN-CARD F3).

**Interactions:** `span-cards` changes which tokens form a card. S3 changes how a card is chosen. They
compose, and the address pool would pool over a span instead of a line, but run them separately.
`key_split` and S4 change the ASK key, not the decoder key, so they are independent.

### S4. `ent_key`: entity identity in the ASK key (direction-only fetch / key collapse)

**Targets:** audit item 3 as corrected (R4, N9): fact keys collapse to one direction, so ASK finds "a fact"
and not "this person's fact". `store.ents` already holds each line's entity ids, label-free, from the
pointerizer, and the score ignores them.

**Mechanism.**
- Entity sub-score added to ASK: `s_l = κ·q·k_l + b_age + κ_e·(π · e_l)`.
  - `e_l ∈ {0,1}^16` is the multi-hot of the card's `ents` (normalised by its count).
  - `π` is a distribution over the 16 entity ids: `softmax(W_e r0)` restricted to mentioned entities
    (`mentions`, `model.py:395-407`), with `W_e: Linear(d, 16)` (2,064 parameters).
  - `κ_e` is a learned scalar **initialised to 0**, so at init the flag-on scores equal D's exactly. NULL
    gets 0.
- L_ask's set CE trains `W_e` and `κ_e`. For two-hop, register 0 can point at the bridge entity, whose
  slot was bound by the loop-1 card (`model.py:469-481`).
- Variant `ent_key_mode="question"` (0 parameters): π = uniform over the ENT ids in the question span. A
  fixed reading of the model's own input, offered as the cheaper control.

**Flag:** `ent_key: bool = False` (+ `ent_key_mode`). Flag off is bit-identical.

**Respects F5 (Engram HOLD):** ids are permuted per visit (`data.py:630-631`), so this adds no parametric
name memory. It matches the same id within one visit only.

**$0 probes.**
- **S4-P0 (data-only ceiling, no model).** For every eval question, count the eligible cards sharing at least
  one entity with the question. The rank-1 ceiling of "entity filter, then uniform" is E[1/n].
  - Far-fact toy, analytic from `ToySpec` (6 entities, 3 relations, 12 distinct (e, r) facts):
    1 + 11·2/17 ≈ 2.3 candidates, ceiling ≈ 0.5, vs 0.242 measured (suggested).
  - Village: a CPU count over a built label-free cache. No training, $0.
  - If the village candidate count is ≥ 8 (common names across many lines), S4's gain is small there and it
    waits.
- **S4-P1 (Stage 0 A/B, CPU, $0).** Far-fact toy, 3 seeds, 425 steps, control = D + passed fixes.
  - Primary: gold ranked first at the first ASK (control 24.2%).
  - Bar: +15 points on each seed.
  - Guards:
    - recall@4 ≥ control −0.02;
    - false fetches on never-told questions (non-NULL top-1) not up by > 5 points;
    - own-retrieval answer accuracy not below control;
    - L_lm within 1%.
  - Proves it wrong: κ_e stays < 0.5 after training, or rank-1 gain < 5 points while π puts > 0.8 on the
    question entity. That would mean entity identity is in the score and still does not decide the rank.

**Funding bid:** Stage 1 **$0.30** + Stage 2 **$2.50** caps after P1, village ruler.

**Interactions:** `key_split` adds line position to the key. It is orthogonal and could stack later, one at a
time. `qk_norm` / `qk_clip` are expected null (steals §3). `engram` is held. `delta_bind` changes slots,
which `π` reads in learned mode, so do not run S4 on top of `delta_bind` until each has been read alone.

### Remaining named $0 probes (no solution needed yet)

- **Per-pass entity fade (binder, N17 / audit item 12).** On any Stage-0 model, the cosine between an entity
  slot and the first bound card value after each later bind and each loop. This decides whether
  `delta_bind` (steals, ranked 4th there) has anything to fix. $0, eval-only.
- **Retrieval-answer coupling (N6).** Per question, the correlation between "gold in top-4" and "correct".
  $0, from existing eval rows.
- **Question-row occupancy (item 5).** A histogram of valid question rows per question on a village cache.
  If ≤ 32 always, `question_rows` could drop to 32 at no information cost (a FLOP saving, not a capacity
  change).

### Interaction matrix with in-flight work

| | `span-cards` | `decoder_reader_kv` | `key_split` | `row_halt` | `delta_bind` | `fetch_gate` |
|---|---|---|---|---|---|---|
| S1 ring_resident | independent | independent | independent | **same failure (N5), opposite side**: test apart, then together | independent | independent |
| S2 decoder_raw_cards | independent | **both widen decoder memory**: apply reader-kv's fetch-use guard to the combination | independent | independent | independent | gate should cover raw rows |
| S3 card_address | composes (pool over span) | reader-kv's rows have no address; independent | independent (ASK side) | independent | independent | gate on card values; independent |
| S4 ent_key | `ents` per span would need remapping | independent | **stackable**, one at a time | independent | **π reads slots**: read each alone first | independent |

---

## (d) Ranking (expected gain over cost and risk)

| Rank | Fix | Expected gain | Cost | Risk | Why here |
|---|---|---|---|---|---|
**Revised after S1-P0.**

| Rank | Fix | Expected gain | Cost | Risk | Why here |
|---|---|---|---|---|---|
| 1 | **S2 decoder_raw_cards** — **Stage 0 PASSED 10-19** (11-13% → 100%, 3/3 seeds) | Large on copying (bypass precedent: 11% → 100%) | 0 params, +16 decoder rows | Low-medium: the decoder could ignore Think (guarded by fetch-use and card-removal) | The only shown fix of the copy failure, made additive; S1-P0 rules eviction out |
| 2 | **S3 card_address** | Large on choosing if learned (oracle +0.66) | +16.6k params (0.8%) | Medium: the address may learn the value (guarded by pool mass) | Needs a decoder that reads cards (S2) first |
| 3 | **S4 ent_key** | Medium: rank-1 ceiling about 0.5 vs 0.24 on the toy; village unknown until P0 | +2k params | Medium: no help if names repeat across many lines | Retrieval is already at recall@4 0.90; answer path first (agrees with steals §5) |
| 4 | **S1 ring_resident** | Unknown; not active in the toy model (0 overflow) | 0 params, about 20 lines | Low | Latent; build only if S1-P1 shows eviction on a trained village model |

~~The single one I would run first: S1-P0~~ (done; negative). **Next: S2 Stage 0 on the m02 protocol
(far-fact toy, gold mode; corrected 10-19 from "ladder-toy")** (done 10-19: PASS), with the new validity guard (the control must not be a constant answer). Before it, there is
one $0 step that every answer-path line needs: a step sweep of plain D on the far-fact toy (425 / 1,000 /
2,000 steps, distinct-answer count and gold-card accuracy). It tells us the smallest budget at which this
toy's answer path is alive. Without it, no far-fact Stage 0, mine or the steals', can be read.

---

## (e) Questions and decisions for the coordinator

1. **E1. Unlocated audit numbers.** I could not find a PremonitionMini source for "96.9% given a correct
   prefix / 4.3% assemble it", "pointer AUC ≈ 0.51" or "replicas pick facts by property". They look like
   custom_io / domain tracks. Which model and file are they from? I left them out of the PremonitionMini
   table.
2. **E2. The forgetting guard row** (G1, 6,800-row test, 90.22 → 33.16) is the custom_io/domain parent model
   (R5). Confirm that it leaves this audit, or say which PremonitionMini run it refers to.
3. **E3. Do CPU toy trainings count as $0 probes?** S1-P0, S2/S3/S4 Stage 0 are short CPU trainings
   (130 s to about 2,000 steps), and this session was told "no training runs". I ran none. Who books them,
   and on which machine (BensPC CPU, or the cloud container)?
4. **E4. Base for each A/B.** I propose a cumulative base: each line's control is D plus every fix that has
   already passed, so each A/B stays one change. The alternative is every arm against plain D. Your call.
5. **E5. Cost model.** span-cards measured Stage 1 at about 17.5 GPU-h ($18 cap) for its arms. The reader-kv
   bid expects $0.80-1.85 for three pairs at the same F on a 5090. My caps use the reader-kv model. Which is
   right for a D pair at F ≈ 3.15e16?
6. **E6. `premonition/` edit permission.** `handoff/HANDOFF.md:33` forbids edits under `premonition/`. The
   steals line had an explicit override (Q39). Does this line get one for S1-S4 code, when you approve
   building it?
7. **E7. Merge order** (Q41: one at a time). S1 touches `_insert`, `forward` and `answer_with_gold`, the same
   region `steals-8` and `decoder-reader-kv` edit. Where in the queue?
8. **E8. This week's cap.** The steals REPORT records $5.58 spent and $29.86 committed of $50, and span-cards
   holds up to $18.50. Nothing here asks for money before its $0 stage passes. Do you want any Stage-1 bid
   held for next week by default?
9. **E9. Out of scope, but someone should look.** Contender E may train with earlier answers and feedback in
   context and be scored label-free (§(b), last item). Who owns E?

---

*Files:* this report only. No prototype code was needed to make the designs concrete; the S1 sketch above
is the whole change. All code citations are to `main` @ 73b8e0224 unless a branch is named.
