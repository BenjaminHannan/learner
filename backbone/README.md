# backbone: stage 1 (borrowed pretrained model)

Fixed by `PREREG-stage1.md` (arms, data, pass marks). Village model only; the `test` split is never generated.

Files: `build_data.py` (data), `train.py` (all arms + eval), `test_wiring.py` (CPU checks), `run_box.sh` (GPU box), `requirements.txt`.

## Data (pure Python, CPU, ~12 min on 4 cores)
    python3 backbone/build_data.py data            # raw shards, train/dev/validation.jsonl, DATA_REPORT.json
Builds train shards 0-39, dev-pool shards 380-399 and the 4 validation shards with the v1 generator settings and checks
every file against v1's SHA256SUMS (read from git commit 71a6919e0). Rows: `context` (all visit lines before the
question, stream tags kept), `question` (`[question] ...`), `answer`, plus qtype/template/style/rule_family metadata.
Prompt = left-truncated context + question + ` [answer]`; target = ` answer` + EOS.

## Wiring test (CPU, no download)
    python3 backbone/test_wiring.py
    python3 backbone/train.py --arm b --smoke --data data --out /tmp/smoke --steps 4 --bsz 4 --micro-bsz 2 --max-len 256

## Arms (one at a time)
    python3 backbone/train.py --arm a0 --data data --out out/a0
    python3 backbone/train.py --arm a  --data data --out out/a --steps 3000 --bsz 16 --micro-bsz 4
    python3 backbone/train.py --arm b  --data data --out out/b --steps 3000 --bsz 16 --micro-bsz 4   # loops=3, block [8,12)
    python3 backbone/train.py --arm b  --data data --out out/b --eval-loops 1 --load-adapter out/b/adapter   # 1-pass lesion
    python3 backbone/train.py --arm a  --model Qwen/Qwen3.5-2B --data data --out out/a2                 # A2
Results: `out/<arm>/result_*.json` (dev/validation accuracy, per qtype/style/rule_family/template_seen, loss curve,
peak GPU memory, wall time); adapter in `out/<arm>/adapter`.

## Box
    bash backbone/run_box.sh        # env: STEPS BSZ MICRO MAXLEN RUN_A2=1 WITH_CONV1D=1
Writes `out/` and `out.tar.gz` (adapters and results, not the data). Re-running skips finished steps.

## Notes
- Loop block default is the multiple-of-4 start at or below `n_layers//2 - 2` (24 layers: [8,12), i.e. whole
  3-linear + 1-full groups; plain `n//2-2` = 10 would split a group). Override with `--loop-start`.
- Needs `flash-linear-attention` on the GPU box for the Gated DeltaNet layers (pure-PyTorch fallback works but is slow).
  `causal-conv1d` is optional (`WITH_CONV1D=1`, needs nvcc).
- Evaluation decodes with a KV/state cache using one cache slot per visit of a layer (verified equal to cache-free decoding by
  `test_wiring.py`); `--no-cache` forces cache-free decoding if a kernel misbehaves.
