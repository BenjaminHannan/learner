# Length evaluation of the baseline-v2 I1-H1 checkpoints — exact commands

Scores each registered `fable-baseline-transformer-v2` I1-H1 checkpoint, unchanged, on
all 25 frozen v3 **development** panel cells (`artifacts/fable-dispatcher-v3-20260920/panels`,
64 units per cell), greedy decoding, mark 58/64.  Scoring only; nothing was trained,
nothing existing was edited, no `test.pt` was loaded.

## Files

| file | sha256 |
| --- | --- |
| `scripts/fable_baseline_length_eval.py` | `24bf7d3a9f713fd74e33f72a8fb312e62c2ce7bb420fc54ae546c3ccb8aecb01` |
| `tests/test_fable_baseline_length_eval.py` | `68795b4f86130ae3d2a05bef5845ac28c220d9bf61ab6148b3046c5f374bf4bf` |

## Environment

```
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
```

## Checks (57 checks, all passed)

```
$PY -B tests/test_fable_baseline_length_eval.py
```

## Scoring (run sequentially, ~13 s per seed)

```
for s in 1200 1201 1202; do
  $PY -B scripts/fable_baseline_length_eval.py score \
    --run artifacts/fable-baseline-transformer-v2-20260920/I1-H1/seed-$s \
    --panels artifacts/fable-dispatcher-v3-20260920/panels \
    --out artifacts/fable-baseline-length-eval-20260920/I1-H1-seed-$s \
    --block 32
done
```

Each seed directory holds only `length.json` and `transcripts.json`, both written by
that command.  `PREDICTIONS.md` in this directory was not touched.

## Decode cap

Per cell, `max_out = hops + 1 + margin` with `margin = 3` (the default): 5 at one hop and
exactly `fable_baseline_transformer.MAX_OUT` = 12 at eight hops.  The cap is recorded in
every cell row as `decode_max_out`.  Every cell was scorable — no position table was
clamped at these caps — and `cells_unscorable` is empty for all three seeds.
