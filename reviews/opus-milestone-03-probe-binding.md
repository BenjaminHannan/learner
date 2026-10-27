# Opus milestone 3, continuation 2: binding probe (read-only)

**Exploratory synthetic-vocabulary evidence.** 2026-09-19, 08:45–09:05 EDT.
- No training. Model defaults unchanged, H1 OFF.
- Label-free inputs; read-only evaluation.
- `full_verdict: false`.
- Local Mac only. **Rental, paid services and BensPC: $0.**

Stopped here for review.

## In plain language

The four existing answer-only models were given a question plus four memory cards. For example, *"what is P2's
R2?"* with these cards:
- the right card (P2, R2);
- the same person with a different relation (P2, another relation);
- a different person with the same relation (P14, R2);
- a card that matches neither (P14, another relation).

We then changed facts and switched parts of the memory off to see what the answer actually depends on.

- **Needed: the cards the decoder reads.** Hide the card rows from the decoder and 230–239 of 256 answers change.
  Accuracy drops to the level of having no cards at all.
- **Not used: the "entity slot" memory.** Undo what the cards wrote into the per-person slots and only 10–22 of 256
  answers change. Accuracy does not move.
- **What the model responds to: the value word, not whose value it is.**
  - The model almost always answers with a value written on one of the cards, but it picks the card about evenly
    among the four.
  - It ignores whether the card's person and relation match the question.
  - When the right card's value is swapped with another card's value, the answer stays with the **value word** in
    97–105 cases and follows the **card** in 0–2.
  - Attention does the same: the most-attended card follows the value word in 115–131 cases and the card in 0–3.
- **What that looks like in practice** (predeclared examples, from `examples.md`):
  - *Pooled model, triplet 0.0.* Asked for P2's R2 value, it answered V15, which is correct. When V15 was moved onto
    P2's *other* relation's card, it still answered V15, which is now wrong. It was right for the wrong reason: it
    likes V15, not "P2's R2".
  - *Direct-reader model, triplet 0.1.* It answered V7, taken from the card of a different person. After the swap
    put V7 on the right card, it answered V7 again and so became "correct" by accident. Its attention moved from the
    wrong card to the right card, following V7.
  - *Pooled model, triplet 0.1.* Its attention followed V7 when V7 moved (0.26 on the old card, then 0.26 on the new
    one), but it answered V1 from the "matches neither" card in all three versions. Attention alone does not tell
    the whole story, which is why the behavioural tests come first.
- **Repair supported by these results:** make the decoder choose a card by its **address** (person + relation), and
  only then read the card's value.

## What was run

All steps were charged to the shared ledger, which went from 1539.14 s to 1552.72 s of 1800 s. The probe used
13.58 s, and 247.28 s is unused.

| Step | Seconds | Result |
|---|---|---|
| Probe mechanics tests (`tests/test_premonition_binding_probe.py`) | 1.49 | 3 OK |
| Dry run: one batch timed, outputs discarded | 0.26 | estimate 64.2 s including a 30 s reserve, so the full subset fit |
| Run, attempt 1 | 2.25 | **failed** in the example formatter, after checkpoint 1. Only the formatter changed; re-frozen and rerun from the start |
| Run | 8.53 | 4 checkpoints × 32 batches × 4 conditions, plus the no-card reference |
| Analysis of saved records (no model) | 0.75 | value- vs card-following |
| Final identity verification | 0.30 | all hashes OK. The sealed ledger prefix is intact; the milestone-3 `ledger.jsonl` sum differs only because rows were appended |

**Predeclared subset:** all 256 validation triplets in `data/triplets-validation.pt` (sha `979f43c6…`). Each
triplet has an original question x, an irrelevant change u and a relevant change v. Card order was the same as in
milestone 3's readout.

**Conditions, all built from one starting state per batch** (the same reader pass, store and insertion):

| Condition | What changes |
|---|---|
| full | nothing |
| no_evidence | the inserted card rows (or the direct arm's token rows) are masked from the decoder; the slots stay bound |
| no_slots | the slot rows are restored to their pre-insertion values; the evidence stays visible |
| neither | both of the above |

**Faithfulness checks.** These were predeclared as required before any causal statement, and all passed on all four
checkpoints:
- insertion changed only slot and card rows, and never slot validity;
- the full condition reproduced the saved triplet correctness bits;
- "neither" reproduced the no-card decode exactly;
- the attention and decoder reconstruction errors were at most 2.4e-6.

## Results

Counts are out of 256 triplets.

| | orig-s0 | orig-s1 | direct-s0 | direct-s1 |
|---|---|---|---|---|
| **full**: x correct / v correct | 78 / 75 | 91 / 66 | 90 / 71 | 76 / 84 |
| full: relevant pair both correct / answer changed on relevant swap | 0 / 7 | 0 / 7 | 0 / 7 | 0 / 2 |
| **no_evidence**: x correct (x answers changed vs full) | 11 (239) | 21 (239) | 25 (235) | 13 (230) |
| **no_slots**: x correct (x answers changed vs full) | 77 (22) | 89 (13) | 92 (10) | 76 (15) |
| **neither**: x correct (identical to no cards) | 18 | 21 | 18 | 13 |
| Change in x correct vs full, no_evidence (99% bounds) | −.26 [−.33, −.20] | −.27 [−.36, −.20] | −.25 [−.34, −.17] | −.25 [−.32, −.18] |
| Change in x correct vs full, no_slots | −.004 [−.035, +.027] | −.008 [−.039, +.023] | +.008 [−.012, +.031] | .000 [−.027, +.031] |
| x answer source: gold / same-person / same-relation / other | 51/51/44/47 | 60/43/42/38 | 57/43/38/47 | 46/47/58/43 |
| x answer source: ambiguous (value collision) / not on any card | 60 / 3 | 65 / 8 | 68 / 3 | 62 / 0 |
| Relevant swap, answer follows value / follows card (x answered from gold or partner) | 99 / 1 | 97 / 2 | 98 / 0 | 105 / 1 |
| Relevant swap, top-attended card follows value / card | 125 / 0 | 131 / 2 | 115 / 3 | 130 / 3 |
| Attention vector closer under the value mapping (/256) | 253 | 248 | 234 | 249 |

**Attention, reported alongside the interventions (full memory, first answer position, averaged over heads).**
- Mass is spread evenly over the four card types, about .16–.21 each, with no preference for the right card.
- Question-person slot: .02–.04.
- The direct arm, which does have separate person and relation rows, puts .67–.70 on value tokens and only .01–.025
  each on person and relation tokens. Making the address *available* did not make the decoder *use* it.

**Value-word preference** (in-sample, descriptive only).
- Each model has strong favourites. How often a value is chosen when it is present ranges from .03–.13 for the
  least-chosen value to .49–.65 for the most-chosen.
- "Pick the most-favoured value present" reproduces 104–140 of the 256 x answers.

## Limitations

- **Exploratory evidence.** Synthetic vocabulary; privileged supplied cards; 1-hop questions only; 256 validation
  triplets; 2 seeds per interface.
- **Ablations are off-distribution.** The models were never trained with masked rows. The ablations show what is
  necessary, not what would suffice. Masking also renormalises the attention over the remaining rows.
- **Question rows stay present.** They are the reader's states for the question tokens and remain in every condition.
  Even so, "neither" performs at the no-card level (13–21 correct; 16/256 would be chance).
- **What "no_slots" means.** It removes what binding wrote into the slots, but keeps each slot's base entity
  identity. It is not a model trained without slots.
- **Attention is a side observation.** It is one cross-attention layer at the first answer position, averaged over
  heads. Attention mass is not proof that the information is used; it is interpreted only alongside the behavioural
  results.
- **Collisions.** Value collisions make 60–68 answer sources per checkpoint ambiguous; they are left out of the
  source-based counts.
- **The value-preference predictor** is fitted and scored on the same questions.

## One recommendation

**Address-keyed evidence selection**, to be tested as its own matched diagnostic. It would not become a default.
- **The change:** compute the decoder's choice among evidence rows from each line's address (its person and
  relation positions) matched against the question, and read the value from the chosen line's value position.
- **Why these results support it:**
  - the evidence rows are necessary;
  - the slots are unused;
  - selection is keyed on the value word in all four checkpoints (97–105 vs 0–2);
  - exposing person and relation as separate rows was not enough, since they received about 2% of attention each;
  - reading a single card already works: 485–512 of 512 on reading, and at most 8 of 256 answers were not a card
    value.
- **How to test it:** the same data, the same seeds and the same unchanged gate, with H1 OFF.

These results locate the failure. They do not show that this particular repair will fix it.

## Files

- **Probe:** `scripts/premonition_binding_probe.py`
- **Tests:** `tests/test_premonition_binding_probe.py`
- **Artifacts:** `artifacts/opus-m03-20260919-071009/probe/`
  - JOURNAL.md, with the predeclaration
  - SUMMARY.txt, summary.json, dry.json
  - records/, holding every generated answer per question and condition
  - examples.md
  - value_following.py and value_following.json
  - checks/
  - SHA256SUMS (12 files)
- **Archive:** `archive/opus-m03-20260919-071009-probe/`
  - frozen probe
  - sources
  - external-state.sha256, covering the checkpoints, data, direct-reader sources and other workers' files
  - ARCHIVE.SHA256SUMS
- **Ledger:** `artifacts/opus-m03-20260919-071009/ledger.jsonl`, rows with kind `probe-*`.

Unchanged:
- all checkpoints and other workers' files;
- the milestone-3 and direct-reader reports and artifacts, apart from the rows appended to the shared ledger.
