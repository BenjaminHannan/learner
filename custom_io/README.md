# custom_io: test harness for from-scratch models on the skills benchmark
Run from the repo root (or with PYTHONPATH=repo root): `python3 -m custom_io.train ...`, `python3 -m custom_io.test_harness`.

**Data** `--data DIR` (train.jsonl + dev/*.jsonl; default `data.DEFAULT_DATA`, env `CUSTOM_IO_DATA`; the only place a path is written).
`--vocab PATH` (default: build from DIR/train.jsonl, cache as DIR/charvocab.json). 90 ids: PAD0 BOS1 EOS2 SEP3 UNK4, Q0..Q7 = 5..12, 77 chars.
Batch (`data.collate`): `prompt_ids [B,T]`, `prompt_mask [B,T] bool`, `ans_ids [B,9]` (chars + EOS, PAD after), `ans_mask`, `rows` (raw dicts).
Prompts do NOT contain BOS/SEP; a model adds what it needs. `--order shuffled|curriculum`. `data.word_spans / word_ids` = word view.

**Model contract** (`models/base.py`; constructor is `Cls(vocab, **cfg)`; register in `models/__init__.py:MODELS`)
- `loss(batch)` -> scalar, or `(scalar, {aux_name: value})` (aux is logged)
- `generate(batch, lesion=None)` -> `list[str]`, greedy, in `batch['rows']` order
- `n_params()`; `LESIONS` = subset of `shuffle_state`, `zero_state`, `loops`; call `self.check_lesion(lesion)` -> `(name, K)`
- a model with an `n_loops` attribute is also swept over `loops:K`, K in {0,1,2,2*n_loops}, by `--final-eval`

**Eval** `evalx.evaluate(model, rows, batch_size, device, lesion)` -> `{exact(%), correct, n, by_family, by_level, multistep}`;
`eval_all(model, data_dir, max_per_split, lesion)` -> same, per dev split (in_dist answer frame vocab variant family).
Hit = `norm(pred)` in `{norm(a) for a in accepted}`. `python3 -m custom_io.evalx --run RUN_DIR --data DIR` re-evals a checkpoint.

**Train** `python3 -m custom_io.train --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4,"n_loops":1}' --steps 3000 --batch 64 --lr 1e-3 --out runs/x --final-eval`
AdamW (0.9, 0.95, wd 0.1 on matrices), `--warmup 300` then cosine to 10%, `--grad-clip 1`. `--minutes M` caps wall time (the cosine
follows whichever of steps or minutes runs out first), then still evals. `--bf16` is autocast on cuda only. `--eval-every N` = quick eval on 200
in_dist rows. `--eval-max N` caps rows per dev split in the final eval. Progress = JSON lines on stdout.
`--out` gets `checkpoint.pt` and `RESULT.json` (config, n_params, steps, train_s, steps_per_s, wall_s, final_train_loss, final_eval, lesions{name: eval_all}).

**Packing** `custom_io/pack.sh jobs.txt [logdir]`: one command per line, all run concurrently, one log each, waits, exit 1 if any failed.

**Numbers** prompt chars: mean 81, p99 163, max 204; a batch of 64 pads to ~161 (max 196) so the longest sequence is ~220 <= 224.
`plain_tf` d256 L4 H4 (3.24M params), batch 64, CPU 4 threads: ~960 ms/step train (n_loops=2: ~1830 ms); greedy decode of 128 rows ~4 s (no KV cache).
A d64 L2 model does ~12 steps/s at batch 16. Test: `python3 -m custom_io.test_harness` (~30 s).

**Gotchas** dev `family` has 5/160 answers longer than 8 chars (9 and 12; unreachable by 9-step decoding) and `#$&@`; dev `vocab` has `O`: all map to UNK.
