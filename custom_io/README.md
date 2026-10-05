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
- optional reasoner/talker split: `state(batch, loops=None)` -> the reasoner's final state (tensor or tuple of tensors, batch first), `talk(state, batch)` -> `list[str]` (`batch` = the CURRENT rows: only what the talker may read, e.g. a copy source, plus lengths);
  `supports_donor()` is True when both exist, and then `generate()` is free (`talk(state(batch, loops), batch)`, with the loops/zero_state/shuffle_state lesions applied to the state)
- a model with an `n_loops` attribute is also swept over `loops:K`, K in {0,1,2,2*n_loops}, by `--final-eval`

**Eval** `evalx.evaluate(model, rows, batch_size, device, lesion)` -> `{exact(%), correct, n, by_family, by_level, multistep}`;
`eval_all(model, data_dir, max_per_split, lesion)` -> same, per dev split (in_dist answer frame vocab variant family).
`evalx.donor_eval(model, rows, batch_size, device, seed=0)` = donor-swap lesion (needs `state`/`talk`): every row gets a donor of the same family whose answer differs from all the row's accepted answers
(`donor_pairs`; rows with none are skipped and counted); `talk(model.state(donor_batch), current_batch)` -> `{exact, donor_match (pred == donor's answer), n, skipped, by_family}`.
Donor and current batches are collated separately, then padded to one prompt length. `eval_all(..., donor=True)` adds `donor` to each split; `donor_all` gives `{split: donor_eval}`.
Hit = `norm(pred)` in `{norm(a) for a in accepted}`. `python3 -m custom_io.evalx --run RUN_DIR --data DIR` re-evals a checkpoint.

**Train** `python3 -m custom_io.train --model plain_tf --cfg '{"d_model":256,"n_layers":4,"n_heads":4,"n_loops":1}' --steps 3000 --batch 64 --lr 1e-3 --out runs/x --final-eval`
AdamW (0.9, 0.95, wd 0.1 on matrices), `--warmup 300` then cosine to 10%, `--grad-clip 1`. `--minutes M` caps wall time (the cosine
follows whichever of steps or minutes runs out first), then still evals. `--bf16` is autocast on cuda only. `--eval-every N` = quick eval on 200
in_dist rows. `--eval-max N` caps rows per dev split in the final eval. Progress = JSON lines on stdout.
`--out` gets `checkpoint.pt` and `RESULT.json` (config, n_params, steps, train_s, steps_per_s, wall_s, final_train_loss, final_eval, lesions{name: eval_all}); a state/talk model also gets `lesions['donor']` = `{split: donor_eval}` and a JSON `eval` line with `exact` and `donor_match` per split.

**Pretrained baselines** `python3 -m custom_io.hf_baseline --hf-id EleutherAI/pythia-70m --mode finetune|fewshot ...` (needs `transformers==5.17.0`; HF hub weights, no checkpoint is saved). Same CLI as train.py (`--steps --batch --warmup --seed --order --bf16 --minutes --eval-max --eval-batch --final-eval --out`, same row order via `data.train_batches`) plus `--revision`, `--shots`; `--lr` defaults to 1e-4.
Text = `{prompt}\nAnswer:` then ` {answer}\n`; finetune = AdamW (0.9, 0.95, wd 0), warmup + cosine to 10%, clip 1, loss only on ` {answer}\n` + eos (prompt and answer are tokenised separately, then joined). Decode = greedy, 16 new tokens, left-padded, cut at the first newline, scored by `evalx.eval_all`.
`--mode fewshot`: no training; `--shots` solved train rows per prompt (same family if it is in train, else random families; seeded per row id; oldest shots dropped if the context would overflow); always runs the final eval.
The adapter is `hf_baseline.HFLM` (a `models/base.py` Model: `loss`, `generate`; no lesions, no state/talk). RESULT.json = train.py's fields (`lesions` = {}) + `n_params` (all, tied weights once) + `n_params_non_embedding`; config has `transformers` version, `resolved_revision` (commit), `shots_policy`.
Gotchas: BPE is not char-level (pythia merges digits, `" 1234"` -> `" 12","34"`; SmolLM2 splits every digit); pythia ctx 2048, SmolLM2 8192 (8-shot dev prompts are ~280 tokens, max ~440); pad token = eos when missing; `eval_batch` default is 64 (few-shot prompts are long).
Numbers (4-core CPU, shared box): pythia-14m 14.07M params (1.19M non-embedding) ~5 steps/s at batch 8; SmolLM2-135M 134.5M (106.2M) ~0.6 steps/s at batch 8; dev eval rows are ~0.3 s per 32 on pythia-14m.

**Packing** `custom_io/pack.sh jobs.txt [logdir]`: one command per line, all run concurrently, one log each, waits, exit 1 if any failed.

**Numbers** prompt chars: mean 81, p99 163, max 204; a batch of 64 pads to ~161 (max 196) so the longest sequence is ~220 <= 224.
`plain_tf` d256 L4 H4 (3.24M params), batch 64, CPU 4 threads: ~960 ms/step train (n_loops=2: ~1830 ms); greedy decode of 128 rows ~4 s (no KV cache).
A d64 L2 model does ~12 steps/s at batch 16. Test: `python3 -m custom_io.test_harness` (~30 s).

**Gotchas** dev `family` has 5/160 answers longer than 8 chars (9 and 12; unreachable by 9-step decoding) and `#$&@`; dev `vocab` has `O`: all map to UNK.
