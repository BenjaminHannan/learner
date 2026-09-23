# Opus milestone 3, continuation: direct contextual-state reader (after Astra's review)

2026-09-19, 08:10–08:30 EDT. This continuation ran under milestone 3's existing cap and shared ledger. Local Mac only.
**Rental, paid services and BensPC: $0.** `full_verdict: false`.

This is a declared diagnostic:
- a synthetic-vocabulary toy ladder;
- the legacy toy label-free rule;
- supplied gold-evidence cards, which are privileged;
- H1 OFF.

It is not a full-v2 experiment and not a primary verdict. The milestone-3 report and artifacts are unchanged; this
report and the `direct/` artifacts are additions. Stopped here for review.

## In plain language

- **What was tested.** Until now the model squashed each memory line into one summary vector before answering.
  This time the answer part read the line's own word-by-word states, straight from the same reading pass. Nothing
  else changed: the same cards, the same training and the same starting weights.
- **Reading improved slightly.** With one correct card, the new reader was perfect on both seeds: 512/512. The old
  one managed 512 and 485.
- **Choosing did not improve.** With look-alike cards present, it picked the right fact about as often as before:
  170 vs 164 on seed 0, and 162 vs 161 on seed 1, out of 512. That is still far below the 0.537 bar.
- **What the model is doing instead.** In both versions the answer depends on *which values are on the cards*, not
  on *which person and relation each value belongs to*.
  - When the right fact's value was swapped with another card's, the prediction changed in only 2–9 of 256 cases.
  - So pairs where the model gets both the original and the changed fact right are 0 of 256.
  - The models are **not** ignoring the cards. Remove them and the answer changes for 85–97% of questions.
- **Conclusion.** The squashing step was not the main cause of the choosing failure. The model does not yet link
  a value to its person and relation.

## Status

| | Implemented | Tested | Trained | Validated |
|---|---|---|---|---|
| Direct contextual-state reader, an explicit variant (`nothink+qread+directread`); not the default | yes | yes: 48 OK including regressions; dry-forward validated | seeds 0 and 1, full 2000 steps each | 2-seed screen; the choosing rule is inconclusive |
| H1 | unchanged | — | not trained; OFF by design here | — |

## What was built (all additive; no existing file edited)

**`premonition/direct_reader.py`: `DirectReaderQReadMini`, a subclass of the pooled arm's `QReadMini`.**
- Each selected line enters the decoder memory as one row per position that the writer pools:
  `value(h_t) + age(line) + type_card`. The pooled line is a single row, `value(Σ w_t h_t) + age + type`.
- The h_t come from the same causal reader pass. This is not raw-token access and not re-encoding of the line.
- It adds no new parameters and no position embedding.
- The pooled card rows are masked out of the decoder memory.

These stay identical to the pooled arm:
- the selected line and card indices, and their order;
- the age and type metadata;
- the question rows, entity slots and registers.

Both arms still bind the entity slots with the pooled value, as D does. That pathway is therefore matched, not
removed.

Behaviour boundaries:
- The class is decode-only: Think passes are refused, and so is a second insertion.
- Token rows live on the episode, never on the module, so evaluation stays read-only.
- With no cards, the episode and the decode are identical to the pooled arm's.

**`scripts/premonition_direct_reader.py`: the continuation harness.**
- Source: its own frozen snapshot, the milestone-3 snapshot byte-for-byte plus the two new files.
- Ledger: the shared milestone-3 ledger, append-only; the sealed 27-row prefix is verified on every command.
- Training: the direct arm uses exactly milestone 3's `answer_loop`, so the stream, optimizer, schedule, CE and
  card-order generator are the same.
- Evaluation: read-only, and the test split is scored once.
- Saved outputs: the actual greedy token sequences with all cards, with gold cards only, and with no cards.

**`tests/test_premonition_direct_reader.py`.** It checks:
- identical initial weights and random stream;
- that token positions are exactly the pooled positions;
- **that the pooled row equals the pool-weighted mean of the direct rows**;
- that only the card region differs, and that the pooled rows are masked;
- that with no cards the episode and decode are identical;
- no leakage from later text, and label-free question lines (`[answer]` then newline, with no feedback or answer
  tokens);
- that gradients reach the reader through the token rows;
- that training and greedy decoding see the same memory, and that the token rows are actually attended;
- read-only decoding;
- the refusals.

## What was actually run

All rows are charged to the shared ledger. It stood at 1149.30 s at the start and 1539.14 s at the end, so this
continuation used 389.84 s and left 260.86 s unused.

| Step | Seconds | Outcome |
|---|---|---|
| Focused tests plus relevant regressions: `direct_reader`, `label_free`, `ovn`, `pool_controls` | 11.12 | 48 OK |
| Dry-forward validation and matched step timing, on throwaway copies | 5.42 | estimate below |
| Train `answer-direct-s0` | 174.49 | full 2000 steps |
| Train `answer-direct-s1` | 170.74 | full 2000 steps |
| Validation evaluation, direct s0 / s1 (including outputs) | 7.39 / 7.47 | |
| Validation outputs, pooled s0 / s1 | 1.31 / 1.30 | |
| Test, direct s0 / s1 | 3.61 / 3.55 | |
| Test outputs, pooled s0 / s1 | 1.27 / 1.26 | |
| Paired analysis | 0.71 | |
| Final identity verification | 0.20 | |

Dry-forward findings:
- Each question's memory had 76 rows in the pooled arm (on average 5 of them valid card rows).
- The direct arm had 136 rows, of which about 30 were valid token rows.
- Step times were equal within noise.
- The full-package estimate was 483.8 s against 634.2 s available, including a 30 s reserve. It fit, so training
  went ahead.

The pooled controls were reused, not retrained. They follow the same code path, build, stream and schedule:
- `answer-original-s0` is the overnight checkpoint. Its replay was verified exact in milestone 3.
- `answer-original-s1` comes from milestone 3.

## Results

Validation; direct vs pooled, with paired, visit-clustered one-sided 99% bounds (triplet-clustered for the triplet
metrics).

| | Seed 0 | Seed 1 |
|---|---|---|
| Read 1-hop /512 | 512 vs 512 | 512 vs 485, +.053 [+.029, +.080] |
| Choose 1-hop /512 | 170 vs 164, +.012 [−.045, +.066] | 162 vs 161, +.002 [−.051, +.055] |
| Combine 2-hop, practised /341 | 121 vs 118 | 132 vs 119 |
| Combine 2-hop, held-out /171 | 49 vs 52 | 48 vs 60 |
| Triplets: relevant pair both correct /256 | 0 vs 0 | 0 vs 0 |
| Triplets: invariant pair both correct /256 | 70 vs 57 | 56 vs 59 |
| Triplets: prediction changed on relevant swap /256 | 7 vs 7 | 2 vs 7 |
| Causal 2-hop pairs, both correct (relevant / tempting / link) | 36/34/20 vs 36/46/18 | 33/51/20 vs 41/49/11 |
| Answer sequence changed when cards removed, 1-hop /512 | 496 vs 477 | 464 vs 481 |

- **Predeclared choosing rule: INCONCLUSIVE.** Neither seed's bound excludes 0.
- **Test split** (once, previously consulted, so not untouched) points the same way:
  - choose: +.022 and +.025, with both bounds spanning 0;
  - reading on seed 1: +.059;
  - relevant pair both correct: 0 vs 1 on both seeds.
- **Unchanged gate, reported only.**
  - Reading now passes: 512 and 512.
  - The identity path still fails: the choose lower bounds are .285 and .268, below .537.
  - It would not pass. H1 stayed OFF.
- **Constant answers.** They do not explain the scores: every arm gives 16 distinct first tokens with cards. With no
  cards, the arms give only 1–3 distinct first tokens.

**Descriptive observation (not predeclared).** In every arm the relevant swaps change the prediction in only 2–9 of
256 triplets. A swap keeps the same set of card values but moves them between cards, so the model is answering from
the set of values rather than from which card holds each value. That is why "relevant pair both correct" is exactly
0 everywhere.

## Correction to the milestone-3 report

The milestone-3 report called the three retrieval arms "card-blind". That claim is **withdrawn**.
- It rested on unchanged correctness totals and on correctness bits.
- Those totals do not prove identical answers. `retrieval-original-s0` had 2 per-question K3 correctness outcomes
  that changed on removal, both in practised 2-hop.
- Milestone 3 saved no predicted sequences, so the claim cannot be restated from the saved data.

This continuation saves actual token sequences, and it shows the answer-only arms clearly use their cards.

## Limits

- **Seeds.** Two seeds, so this is a screen; finalists need three.
- **Setting.** A toy ladder with synthetic vocabulary. The supplied cards are privileged.
- **Decoder.** The decoder has one layer.
- **What is actually isolated.** In both arms the entity slots still carry the pooled value. The comparison isolates
  the card rows' interface, not "no pooling anywhere".
- **Memory size.** The direct arm has more memory rows: about 30 valid token rows vs 5 card rows. The measured
  training time was the same.
- **Test split.** The ladder test split, and the triplet test set for the pooled arms, were consulted before. No
  tuning was done on either.
- **Probes.** No fitted probes were run. Failed choosing does not prove the information is absent from the states.

## One recommendation

**Localise the binding failure read-only before any new training arm.**
- For the four existing checkpoints, measure where the decoder's first answer-position cross-attention mass goes on
  choosing questions. Split it by card type: gold, same-person decoy, same-relation decoy, other decoy. In the
  direct arm, also split it by the token within the line.
- Use the inventory-preserving swaps to check whether the attention follows the edited card.
- If the attention does not land on the gold card, the repair is the question-to-card conjunctive match, not the
  card interface.
- Keep the gate and H1 unchanged.

## Files

- **Source:**
  - `premonition/direct_reader.py`
  - `scripts/premonition_direct_reader.py`
- **Tests:** `tests/test_premonition_direct_reader.py`
- **Artifacts:** `artifacts/opus-m03-20260919-071009/direct/`
  - JOURNAL.md, with the predeclaration written before calibration
  - SUMMARY.txt, dry.json, compare.json
  - runs/, ckpt/ (`answer-direct-s0` `41fab440…`, `answer-direct-s1` `8136a501…`)
  - eval/, tests/
  - outputs/, holding the actual token sequences
  - checks/
  - SHA256SUMS (25 files)
- **Ledger:** `artifacts/opus-m03-20260919-071009/ledger.jsonl`, 14 appended `direct-*` rows.
  - The milestone-3 `SHA256SUMS` line for this file no longer matches, because rows were appended.
  - The sealed 27-row prefix still hashes to `6a53be97…`.
- **Archive:** `archive/opus-m03-20260919-071009-direct/`
  - frozen/ (57 files), sources/
  - external-state.sha256
  - ARCHIVE.SHA256SUMS (61 files)
- **Unchanged:**
  - Other workers' files, `premonition/model.py` and the overnight modules and artifacts, all verified against the
    overnight hashes.
  - The milestone-3 artifacts other than the appended ledger.
