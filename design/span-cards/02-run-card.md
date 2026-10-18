# Run card SC-1: span cards vs per-line cards (pre-registered)

Status: **SEALED 2026-10-18** (`05-seal.md` holds the hashes). Terms confirmed by the coordinator (Q21,
2026-10-17); the Q20 code review passed (review log, round 4: no blocking finding on bd28adcd7). The
data-dependent items of section 9 (N, the cache files, the Stage 1 run script) are sealed in an addendum
before any arm runs. **No registered run has started.** Training needs the coordinator's gate
(see `03-funding-bid.md`); only Stage 0 (a measurement, not a registered run) is booked. Bars, predictions and guards below are fixed now, before any run. After the
coordinator approves this card, it is sealed (`shasum -a 256` of this file plus every code file in section 9)
before the first registered run. Nothing in it may change after sealing; a FAIL gets exactly one
diagnosis-driven follow-up (house rule).

## 1. The single change
The card writer. LINE = today's `CardWriter` (one card per non-question line). SPAN = `SpanCardWriter`
(`premonition/span_cards.py`; design: `01-design.md`). Everything else is shared and identical: reader, think
loop, ASK, binder, decoder, losses, curriculum, optimiser, data order, FLOP budget and evaluation code.

## 2. Terms in the brief that this repo does not define (CONFIRMED by the coordinator, Q21)
The repo was searched; its newest dated content is 2026-09-30. The coordinator confirmed every mapping below
as written, with the primary ruler fixed as `far`.

| Brief's term | Not found as such. Mapped to | Source |
|---|---|---|
| far held-out join score (primary ruler) | own-retrieval exact match on the **`far`** slice (knowable, evidence outside A's 736-token cut) of the **held-out split**, label-free regime, v2 tokenizer, scored once through the sealed procedure. There is no "join" slice. **Primary = `far`** (Q21). `far_deep` (far and depth >= 2) is reported as a **secondary slice only**. | `premonition/slices.py:94-100, 147-153`; `exp1.py:8` |
| house-form bars | the code policy: one-sided alpha = 0.01, paired by question, at least 100 paired items, minimum effect 3 points | `learnlab/policy.py:8-14`; `premonition/exp1.paired` |
| house family rule | a claim holds for a family of seeds iff it holds in >= 2 of 3 seeds, judged per seed, never averaged | `tests/test_fable_dispatcher_probes26.py:541`; `artifacts/claude-fewex-20260927/PASSMARKS.md:9` |
| DEV slip | a drop on the development split (`validation`). Defined in G2 below. | `exp1.py:8` |
| same parent | the per-seed checkpoint P_s defined in section 3 | this card |

## 3. Parent, arms, pairing
- **Data:** the standard village splits, label-free v2 cache (`premonition.data.load_or_build(...,
  regime="label-free")`), tokenizer `premonition-tok-v2-fallback`. Built once and hashed into the seal.
- **Model:** D, preset "full" (d = 128), `MiniConfig.preset("D", "full", vocab_size=VOCAB_V2)`.
- **Recipe:** `train.train_d` defaults: design/06 curriculum (gold to 5%, teacher to 30%, own ramp to 60%,
  p_own 0.75), AdamW lr 1e-3, warmup 100, clip 1.0, max_tokens 55,000, max_visits 48, FLOP budget F as
  `train_d` sets it, stop at F +/- 5%.
- **Parent P_s (s = 0, 1, 2):** LINE trained from scratch with seed s to **5% of F** (the end of the gold
  phase). The branch point is the start of the teacher phase, so SPAN's gate experiences both the teacher and
  own phases. P_s is built fresh inside Stage 1 (Q21: the coordinator holds no substitutable checkpoint).
- **Pairing scope:** the arms share the parent, data order and seeds. They are **not** bit-paired after the
  branch: SPAN's store is wider (token columns), so the same generator seed draws different teacher cards.
  Per-question pairing of the test is unaffected.
- **Arms from P_s, for the remaining 95% of F:**
  - LINE: P_s continued unchanged.
  - SPAN: `SpanCardMini` loaded from P_s (the gate is new; every other weight is P_s's).
    `SpanConfig(enabled=True, max_span=64, newline_prior=8.0, base_logit=-4.0, w_rate=0.03,
    newline_id=23, tokens_per_card=N)`, where
    **N = `span_cards.tokens_per_line(train cache)`**. N is computed once and written into this card's sealed
    addendum before any arm runs. Pilot measurement (2026-10-17, this session): **11.17** on a label-free v2
    cache of 256 freshly generated train visits (seed 0, one shard, 23,075 non-question lines, visits about
    1,149 tokens and about 99 lines). This keeps SPAN's average card count equal to LINE's.
  `newline_id = 23` is `"\n"` in `premonition-tok-v2-fallback` (`tokenizer.encode("\n") == [23]`, checked
  2026-10-18; Stage 0 checks it again on the box and stops if it differs).
- **Pairing:** the same P_s, the same batch order (data seed s), the same trainer generator seed s, and the
  same budget F. Each arm is charged by its own `calibrate()` FLOP fit (the house convention: every contender
  is charged in FLOPs).
- **Branch-point check (pre-flight, logged):** on 64 DEV visits, SPAN-at-branch and P_s give identical
  `answer()` tokens (also unit-tested). If not identical, stop: the pairing is broken.

## 4. Cells
- **Cell A (today's data):** both arms train on the unchanged train cache.
- **Cell B (line breaks no longer match facts):** both arms train on `reflow_cache(train, merge=0.15,
  split=0.15, seed=1000 + s, max_merge=3, drop_prefixes=[tok.encode("[world]")], word_start=<v2 ids whose
  decoded text starts with a space>)`. Drop only the tag token (`[4]` in v2), not `"[world] "`: dropping the
  space too glues sentences together ("inn.<Pamo>"), as checked on real data. A split right after the tag
  leaves a content-free `[world]` line. That is a filler line, which is kept deliberately. The augmentation is
  static (one reflowed copy per seed) and identical for both arms. Cell B branches from the same P_s.
  Pilot on the real 256-visit cache at the E3 rates (0.30/0.30): 25,345 lines became 22,648 (4,836 merged
  lines, 3,559 splits, 0 entity overflows); all 2,270 question spans were intact and `collate` builds.

Cell B is conditional: it runs only if Cell A passes guards G1-G4 for SPAN (section 7). Otherwise the result
is "the mechanism breaks retrieval on today's data", and B is not funded.

## 5. Evaluation sets (all label-free, own retrieval, `PremonitionMini.answer`, greedy)
- **E1 (primary, sealed):** the held-out split's `far` slice, scored once per arm per seed by the
  coordinator's sealed procedure. `far_deep` is reported as a secondary slice, with no verdict. This session
  never loads it.
- **E2 DEV:** the `validation` split: overall, `near`, `far`, `multi_hop`.
- **E3 (secondary, sealed):** E1's split passed through `reflow_cache(merge=0.30, split=0.30, seed=777)`,
  with the same slice. The reflow seed differs from training's, and so do the rates.
- **Card economy:** `span_cards.card_economy(model, batches)` on 200 DEV visits, for both arms, at the branch
  point and at the end.

## 6. Bars and predictions (fixed now)
Test: `exp1.paired(a, b, ids, margin=m, alpha=0.01)` per seed on the slice's question ids. `n >= 100` is
required, or the cell is "insufficient". Family rule: >= 2 of 3 seeds, never averaged, never pooled.

- **BETTER(A over B):** in >= 2/3 seeds, `paired(A, B, margin=0)` is significant AND the difference is
  >= +3.0 points.
- **NON-INFERIOR(A vs B):** in >= 2/3 seeds, `paired(A, B, margin=-0.03)` is significant (A beats B minus 3
  points).
- **WORSE:** BETTER(B over A).
- Otherwise: INCONCLUSIVE (reported as such, never rounded to a win).

| # | Prediction (registered) | Cell / set | Falsified if |
|---|---|---|---|
| P1 | SPAN is NON-INFERIOR to LINE | A / E1 | SPAN is WORSE, or not NON-INFERIOR |
| P2 | SPAN is **not** BETTER than LINE (expected difference within +/-2 points: lines are about facts in this data) | A / E1 | SPAN is BETTER (a pleasant surprise, but the prediction fails) |
| P3 | Adaptation stays small on today's data: SPAN's `line_aligned` share at the end is >= 0.85 | A / economy | `line_aligned` < 0.85 |
| P4 | **The mechanism's claim:** SPAN is BETTER than LINE on reflowed held-out text | B / E3 | not BETTER |
| P5 | SPAN is NON-INFERIOR to LINE on unreflowed held-out text when both train with reflow | B / E1 | not NON-INFERIOR |
| P6 | LINE trained on Cell B loses on E3 vs E1 by more than SPAN does (SPAN is more format-robust) | B / E1 and E3 | LINE's E1 - E3 drop <= SPAN's, in >= 2/3 seeds |

The verdict on Ben's question is P4 (with P5 and the guards). P1-P3 say whether the mechanism is safe on
today's ruler and whether it adapts there at all.

## 7. Guards (per seed, family rule; a failed guard voids the arm's primary claim, which is then reported as FAIL)
- **G1 ASK/fetch must not collapse** (from `card_economy` on DEV at the end, SPAN vs LINE of the same seed):
  `asked_rate` >= LINE - 0.05; `fetches_per_q` >= 0.8 x LINE; `null_share` <= LINE + 0.05;
  `first_ask_recall` (layout-aware) >= LINE - 0.05.
- **G2 DEV slip:** SPAN's DEV overall accuracy and DEV `far` accuracy may not be WORSE than LINE's (the
  BETTER rule with the arms swapped, on DEV). Also reported: each arm's DEV minus its parent's DEV.
- **G3 budget held:** SPAN's DEV `tokens_per_card` mean is within +/-25% of N; otherwise SPAN stored a
  different amount, and the comparison is no longer "placement at equal storage". It is then reported as
  such, not as a placement result.
- **G4 compute matched:** both arms land at F +/- 5% (`budget_ok`); `loop_mismatches` is reported.
- **G5 entity overflow:** SPAN's `ents_overflow` < 0.02 (otherwise the binder is starved; flagged, not voided).

## 8. Card-economy report (what "the adaptation actually happening" looks like)
For each arm and seed, at the branch point and at the end: cards per visit (mean, p10/p50/p90); the
tokens-per-card histogram; `line_aligned`, `merged` and `split_lines` shares; newline precision and recall
of card starts; `ents_overflow`; gold cards per told question and gold card size; `asked_rate`,
`fetches_per_q`, `null_share`, `first_ask_recall`, `full_gold_fetched`. In training, `SpanTrainer.span_log`
logs `start_rate` (F), `gate_mean` (G), `gate_mid`, newline precision and recall, and `L_rate`. These are
reported for every run. LINE's economy is the reference: `line_aligned` = 1 by construction.

## 9. Seal list (hashed before the first registered run)
`premonition/span_cards.py`, `premonition/reflow.py`, `premonition/model.py`, `premonition/store.py`,
`premonition/train.py`, `premonition/data.py`, `premonition/slices.py`, `premonition/exp1.py`, this card,
the run script, the train/validation cache files, and the value of N.

## 10. What a result can and cannot show
- It can show whether a learned layout beats line-per-card at equal average storage, on this village data and
  on a reflowed version of it, at 2M parameters, under three seeds.
- It cannot show general text robustness. The reflow is synthetic: it merges and splits lines but never
  rewrites sentences.
- It does not test REINFORCE, delta-rule or slot alternatives (`01-design.md` section 2 says why they were
  not chosen).
