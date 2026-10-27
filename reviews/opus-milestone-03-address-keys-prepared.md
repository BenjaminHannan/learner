# Opus milestone 3, continuation 3: address-keyed evidence selection (prepared, NOT trained)

> **Update 2026-09-19 09:35.** After the budget amendment (shared cap 2,100 s) the comparison was run. See
> `reviews/opus-milestone-03-address-keys-results.md`. This report is kept as it was at the stop, with the
> address-swap correction applied.

2026-09-19, 09:08–09:25 EDT. Local Mac only. **Rental, paid services and BensPC: $0.** `full_verdict: false`.
H1 OFF. Model defaults unchanged.

**Status: implemented, tested, dry-forward validated. Not trained, because the complete two-seed comparison does not
fit the remaining allowance.** It needs **463.5 s**, and 231.0 s remained after calibration. The additional compute
needed is **232.5 s**; after the final 0.17 s verification it is 232.7 s. Nothing was shortened or run on a single
seed. Stopped for review.

## In plain language

The binding probe showed the models choose a memory card by the value word written on it. This variant changes how
the answer part chooses. Each card's "address" is its person and relation words. The answer part learns to match
the question against that address, then reads the chosen card's usual content. The value words cannot influence
which card is chosen. I built and tested it, but training both seeds would take about 400 s and only about 230 s
were left, so I stopped before training.

## What was built (additive; default off)

**`premonition/address_reader.py`, `AddressKeyedQReadMini`.** It is an explicit arm, `nothink+qread+addresskeys`.
- **Selection key of each inserted card row:** `W_addr · LN([embed(line token 1); embed(line token 2)])`. These are
  the line's subject person and its relation (or LINK).
- **Answer value:** the decoder's ordinary value projection of the ordinary pooled card row, unchanged.
- **Unchanged:** the question rows, entity slots, registers, the query side and all other computation.
- **Learned matching:** the question is matched against each address by the decoder's own learned query, which has
  read the question prefix.
- **New parameters:** 2,080. They are initialised from a dedicated generator (seed 7000 + model seed), so the shared
  weights and the global random stream are identical to the pooled build.
- **Behaviour boundaries:** decode-only (Think passes are refused). Address rows live on the episode, never on the
  module. With no cards the decode is identical to the pooled model's.

**Explicit structural help.** The controls do not get this:
1. A parse of the synthetic line layout: token 1 is the subject person and token 2 is the relation or LINK. It is
   applied identically to every supplied line, and the code raises an error if the layout assumption fails.
2. Non-contextual input embeddings for the address, so candidate value words (token 3 onward) cannot enter the
   selection keys.
3. A hard constraint: card selection keys come only from the address.

**Never used for selection:** gold-card identities, answer labels, triplet roles or intervention metadata. The
supplied evidence, training examples, answer loss, schedule and evaluation gates are the same as the controls'.

**`scripts/premonition_address_keys.py`.** The complete comparison is ready to run:
- `train --seed {0,1}` uses the same `answer_loop` as the pooled controls;
- `eval` is read-only and records actual outputs with and without cards;
- `compare` runs the predeclared paired rules on choosing and on relevant-pair both-correct, and reports the
  unchanged gate.

`train` refuses unless the dry run says the whole package fits.

**`tests/test_premonition_address_keys.py`, 6 tests.** They cover:
- shared weights, the random stream and the seeded address;
- that the re-implemented decoder is bit-exact to `Decoder.forward`;
- that address rows are exactly the token-1 and token-2 embeddings, and that values are unchanged;
- that changing every supplied value word, the answer labels and the gold lines leaves the selection keys
  identical, while changing a person token does change them;
- that swapping two cards' addresses changes the decoder's internal outputs at the first answer position, and that
  the no-card decode equals the baseline. **Correction (2026-09-19 09:16):** this test shows that the decoder's
  internal outputs change, *not necessarily the generated answers*. It was earlier summarised as "swapping two
  cards' addresses changes the answer". The test was renamed to say so; its assertions are unchanged;
- that gradients reach the address projection; train and greedy memory consistency; read-only decode; and the
  refusal of Think passes.

## What was run (charged to the shared ledger)

| Step | Seconds | Result |
|---|---|---|
| Tests: new + direct_reader, label_free, ovn and pool_controls regressions | 11.39 | 54 OK |
| Dry-forward validation and matched step timing, on throwaway copies | 4.93 | see below |
| Final identity verification | 0.17 | all hashes OK, sealed ledger prefix intact |

**Dry-forward validation:**
- the no-card decode is identical to the pooled model's at initialisation;
- the initial loss is 6.0545 and finite;
- the address gradient is finite and non-zero;
- read-only decoding works.

**Timing:**
- seconds per step (gold-only phase / all-cards phase): pooled .082 / .083, address .087 / .086;
- modelled training time: pooled 165.9 s, address 173.7 s, a ratio of 1.047.

**Complete-comparison estimate:**

| Item | Seconds |
|---|---|
| Training, per seed | 200.9 |
| Training, both seeds | 401.8 |
| Validation evaluation | 18.0 |
| Test evaluation | 8.6 |
| Comparison | 5.0 |
| Saving reserve | 30.0 |
| **Total** | **463.5** |

Each seed's training estimate is 10% above the larger of two figures: the modelled time, or the slowest measured
answer run scaled by 1.047.

**Ledger:** 1552.72 s → 1569.21 s of 1800 s. This step used 16.49 s, and 230.79 s is left.

## What is needed to finish

Any one of these would allow the full predeclared comparison (both seeds, validation and test, analysis, reserve):
- raise the shared cap by at least about 233 s;
- grant a fresh allowance of at least 463.5 s for this comparison alone.

The commands are then (the dry run must be re-run under the new allowance):

```text
PY -B scripts/premonition_address_keys.py dry
PY -B scripts/premonition_address_keys.py train --seed 0
PY -B scripts/premonition_address_keys.py train --seed 1
PY -B scripts/premonition_address_keys.py eval --ckpt answer-address-s0
PY -B scripts/premonition_address_keys.py eval --ckpt answer-address-s1
PY -B scripts/premonition_address_keys.py eval --ckpt answer-address-s0 --split test
PY -B scripts/premonition_address_keys.py eval --ckpt answer-address-s1 --split test
PY -B scripts/premonition_address_keys.py compare
```

`PY` is `/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12`, with
`PYTHONPATH` set from the `import_roots` in `runtime.local.json`.

## Limits

- **Toy and privileged.** Synthetic vocabulary; privileged supplied cards; the layout parse is explicit format
  knowledge that the controls lack.
- **Untrained.** No result about whether the repair works exists yet.
- **Estimate uncertainty.** Step timings come from 8 steps per phase and are noisy. The estimate includes a 10%
  margin and a 30 s reserve.

## Files

- **Source:** `premonition/address_reader.py`, `scripts/premonition_address_keys.py`
- **Tests:** `tests/test_premonition_address_keys.py`
- **Artifacts:** `artifacts/opus-m03-20260919-071009/address/`
  - JOURNAL.md, with the predeclaration and the stop
  - dry.json
  - checks/
  - SHA256SUMS
- **Archive:** `archive/opus-m03-20260919-071009-address/`
  - frozen/ (59 files)
  - sources/
  - external-state.sha256
  - ARCHIVE.SHA256SUMS
- **Ledger:** `artifacts/opus-m03-20260919-071009/ledger.jsonl`, rows with kind `address-*`.

Unchanged: all checkpoints, the earlier continuation artifacts, and other workers' files (verified).
