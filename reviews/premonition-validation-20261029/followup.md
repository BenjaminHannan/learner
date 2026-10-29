# Follow-up bug tests — 2026-10-29

## Real cached LFM3, training, export and serving

**Shown:** real locally cached LFM3-1.7B loads on this 32 GB Apple silicon Mac, generates, performs two finite synthetic CE + KL LoRA updates, changes adapter weights, restores saved adapter tensors exactly, exports the adapter to GGUF, and generates through llama-server with both the base and exported adapter. This is a plumbing smoke, not evidence of recall improvement, general learning quality, a successful full night, or safety under production batch sizes.

Checkout: `/Users/ben-hannan/Desktop/projects/premonition-reliability`, starting commit `33d9e6d02a6d13fc889ec2c6a1a294107a84e1e9`, plus the uncommitted follow-up fixes. No production adapters, diary, userdata, services or model settings were changed. All data used by the smoke were synthetic. The harness is `sleepmlx/tests/manual_lfm3_smoke.py`.

Exact second invocation, after the replay KL normalization fix:

```sh
cd /Users/ben-hannan/Desktop/projects/premonition-reliability
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -u -m sleepmlx.tests.manual_lfm3_smoke --model-dir /Users/ben-hannan/learner-ops/models/lfm3-1.7b-hf --llama-cpp-dir /Users/ben-hannan/learner-ops/lfm3/llama.cpp --base-gguf /Users/ben-hannan/learner-ops/lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf
```

The first invocation omitted `--llama-cpp-dir` and `--base-gguf` and also passed the Torch portion. The second invocation is the result recorded below.

### Sources and runtime

| Item | Observed value |
| --- | --- |
| HF model directory, resolved symlink | `/Users/ben-hannan/learner-ops/lfm3/hf` |
| HF weight file | `/Users/ben-hannan/learner-ops/lfm3/hf/model.safetensors` |
| HF weights SHA256 | `135922caef64e81e52af88ede8b7c3ddaa9d6da220a9737fb3065275dbfb4330` |
| HF config SHA256 | `8c6ae8b8f6d88c87cfb98cf4b5e34e943d0ee07e24215c4121b3159a46e1399d` |
| Loaded HF class | `Lfm3ForCausalLM` |
| torch / transformers / peft | `2.14.1` / `5.21.0` / `0.21.2` |
| Device and base dtype | `mps`, `torch.float16` |
| Profile | `lfm3_mps` |
| LoRA | rank 16, alpha 32, dropout 0, fp32 trainable weights |
| Trainable parameters | 3,194,880 |
| Target-module regex | `.*\.layers\.\d+\.(self_attn\.(q_proj\|k_proj\|v_proj\|o_proj)\|conv\.out_proj)` |
| Training options | gradient checkpointing enabled, nonreentrant; token budget 64; one synthetic sequence of length 13, two supervised CE tokens; replay sequence length 8, two selected KL positions; AdamW learning rate 0.0002; two updates |
| MPS memory cap | 8 GB; no high-watermark disabling |
| llama.cpp checkout | `/Users/ben-hannan/learner-ops/lfm3/llama.cpp`, clean commit `338fce6511c744893cc0d3d958b275f40552c7a4` |
| llama-server | `/Users/ben-hannan/learner-ops/lfm3/llama.cpp/build/bin/llama-server`; version `0.7.0-dev`, build 1, commit `338fce6`, AppleClang 21.0.0.21000334, Darwin arm64 |
| llama-server binary SHA256 | `77afb24d9e0ba6695f283c188dc71f8322e14b28ab609810efe550323c49bd13` |
| Converter SHA256 | `ddb143ac34022b0646e51d9c35e9cfa3ec3d0a36091975ebc88f553dd18ca350` |
| Base GGUF | `/Users/ben-hannan/learner-ops/lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf` |
| Base GGUF SHA256 | `43a7d09a0e9cba91b63eb7052488b9564569bddfd65754d2e426465e572a7452` |

The target modules are attention q/k/v/o projections and `conv.out_proj`; the regex cell escapes Markdown table pipes.

### Recorded results

Times are seconds since the harness timer started, including the HF weight hash. The timer starts after imports. An overall export-plus-serving duration was not recorded.

| Stage | Elapsed seconds | Result | MPS allocated GB | MPS driver GB |
| --- | ---: | --- | ---: | ---: |
| Loaded | 3.585 | real LFM3 class, 3,194,880 trainable parameters | 3.47457792 | 4.354080768 |
| Generated before updates | 3.828 | `Hello!`, 2 tokens requested | 3.47457792 | 4.356440064 |
| Update 0 | 4.776 | CE `0.6276475191116333`; KL `9.950557796400972e-06` | 3.51291648 | 4.391043072 |
| Update 1 | 5.579 | CE `0.24023447930812836`; KL `0.024223532527685165` | 3.51291648 | 4.39943168 |
| Save/reset/reload | 5.748 | exact adapter tensor equality after reset and reload | 3.51291648 | 4.39943168 |
| Generated after updates | 5.869 | `Hello!`, 2 tokens requested | 3.51291648 | 4.39943168 |
| Torch checks complete | 5.869 | finite metrics, gradients and updated weights; SIGTERM guard observed | 3.51291648 | 4.39943168 |
| Torch unloaded | not timed separately | MPS allocated 0 before converter/server startup | 0 | not recorded |
| Exported | not timed separately | GGUF LoRA, 12,788,192 bytes | 0 | not recorded |
| Served base | not timed separately | `Hello!`, `tokens_predicted: 2` | not measured | not measured |
| Served exported adapter | not timed separately | `Hello!`, `tokens_predicted: 2` | not measured | not measured |

All adapter parameters and non-None gradients were checked finite after each update, and at least one adapter tensor changed. Adapter files were `README.md`, `adapter_config.json`, and `adapter_model.safetensors`. Saved tensors were compared exactly after `load_adapter(None)` followed by reload.

The synthetic text was `Synthetic test only. A blue cup is on the table.`. The generation prompt came from the actual tokenizer chat template with user message `Say hello.` and the configured no-thinking suffix.

The harness overrides `SLEEPMLX_HOME`, `SLEEPMLX_DIARY_DIR`, `SLEEPMLX_USERDATA`, `LEARNER_OPS`, `SLEEPMODE_HOME`, `SLEEPMODE_OPS`, `SLEEPMODE_OUT`, `HF_HOME`, and `HF_MODULES_CACHE` into one fresh `TemporaryDirectory`; HF/transformers offline mode is enabled. Temporary directory names start `premonition-lfm3-smoke-` in the system temporary folder. Its exact randomized path was not printed by this run and cannot be recovered after deletion. The per-server logs were `<that temporary directory>/base.log` and `<that temporary directory>/adapted.log`; both were deleted with the sandbox after success. The tool console stage results are transcribed above; raw server logs were not retained. The exported adapter file's own hash was not recorded before deletion.

The converter invocation was the normal `sleepmlx.export.export_gguf` path using the Python interpreter above, the local `convert_lora_to_gguf.py`, `--base /Users/ben-hannan/learner-ops/lfm3/hf`, and fresh sandbox adapter/output paths. Both owned servers used fresh loopback ports and the following arguments, with `--lora <sandbox>/adapter.gguf` added for the adapter run:

```text
/Users/ben-hannan/learner-ops/lfm3/llama.cpp/build/bin/llama-server -m /Users/ben-hannan/learner-ops/lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf --host 127.0.0.1 --port <fresh ephemeral port> --ctx-size 256 --parallel 1 --batch-size 32 --ubatch-size 32 --n-gpu-layers 99 --threads 2
```

The harness waits on `/health`, then calls `/completion` with `n_predict: 2`, `temperature: 0`, `seed: 1`, `stream: false`, and `cache_prompt: false`. Every server process is terminated and waited for in `finally`; force-kill is limited to that owned process if graceful shutdown times out. These checks used separate base and adapted server processes. They did not exercise the per-request adapter scale switching in the larger served quality gate.

Cancellation scope: a real SIGTERM delivered to the harness was translated to `Guards.signal("sigterm")`, and `Clock.check()` raised the expected external `Stop`. This demonstrates the signal/guard boundary; it does not demonstrate cancellation in the middle of a GPU kernel, model load, converter process, or an entire worker night.

## Replay KL normalization regression

**Fixed:** both Torch and MLX selected replay logits according to `loss_start` but divided KL by all sequence continuation positions. A masked replay prefix incorrectly reduced the replay penalty. Both denominators now count selected targets, matching CE normalization. The normal recipe currently supplies replay with `loss_start = 0`, so this fix preserves that existing path.

`sleepmlx/tests/test_torch_loss.py` runs a CPU numerical test using actual torch without a model download. Identical one-position reference/current distributions must yield the same KL and gradient with and without a longer ignored prefix. The test passes with the fix. Running the same test against an in-memory copy of the original method fails: old masked KL `0.10844521969556808` versus expected `0.43378087878227234`. No source files were reverted to demonstrate the failure.

Focused command passed 19 tests in 1.524 seconds:

```sh
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -m unittest sleepmlx.tests.test_torch_loss sleepmlx.tests.test_oom sleepmlx.tests.test_platforms -v
```

The numerical regression is optional when torch is absent; it was actually executed with torch installed here. The shared MLX denominator was corrected consistently, but no pretrained MLX weights were loaded for this follow-up. `git diff --check` passed for the backend and smoke files.

## Apex-35B backend preparation after the user's model change

The requested checkpoint is [Apexintelligence-AI/Apex-35B-V1.0](https://huggingface.co/Apexintelligence-AI/Apex-35B-V1.0), pinned to `dde5ccd2c8da7ddbc99d804ac9dca656c6e927ef`. Its pinned config identifies `Qwen3_5MoeForConditionalGeneration` / `qwen3_5_moe`: 40 layers, hidden size 2048, 256 experts with eight selected per token, and untied output embeddings. The upstream safetensors index reports 71,903,645,408 bytes across 26 weight shards. Only small config/index/template metadata were fetched during this preparation; no Apex weights were downloaded or loaded.

The new `sleepmlx/profiles/apex35b_mlx.json` is an explicit native MLX profile, with the intended local base at `/Users/ben-hannan/learner-ops/models/apex35b-3bit`. It targets rank-eight LoRA on attention and linear-attention projections; expert matrices remain frozen. The proposed initial runtime uses batch one, token budget 256 and a 20 GB MLX memory cap. Full 35B peak memory, speed, generation and learning are **untested**; the profile's presence does not mean the requested checkpoint is installed or active.

The pinned [native Apex template](https://huggingface.co/Apexintelligence-AI/Apex-35B-V1.0/blob/dde5ccd2c8da7ddbc99d804ac9dca656c6e927ef/chat_template.jinja) is retained as the independent fixture `sleepmlx/tests/fixtures/apex35b_native_chat_template.jinja` (7,762 bytes; SHA256 `9ddeb864b619d97205205083cd090e648b4f03458ada48fa490c8ae26330e639`). The renderer leaves its generation prompt ending in `<think>` and supplies no thinking-mode override. Completed reasoning is removed before extraction/grading; an unfinished reasoning block exposes no answer. Supervised QA targets include `</think>\n\n` before the factual answer, so the answer is learned outside the hidden reasoning block. Held recall's token budget is now configurable (default 16 preserved, Apex profile 512), and upstream revision changes invalidate recall/general baselines.

**Additional bug fixed:** `MLXBackend._logits` previously missed the nested `language_model.lm_head` in Qwen3.5/3.6 wrappers and used the embedding matrix as the output head despite untied embeddings. The selected-position logits now use the model's actual output head. A numerical regression compares them with the real architecture's native forward output, and checks that the former tied-head result differs.

**Shown with tiny random weights, not the full Apex checkpoint:** the installed `mlx_lm.models.qwen3_5_moe.Model` supports the complete backend path. The test constructs two layers with both linear and full attention, four experts, hidden size 64 and vocabulary 128; quantizes eligible projections to three bits; adds rank-two LoRA; performs two finite CE + KL updates with changed weights; generates through actual `batch_generate`; saves/resets/reloads the adapter; and loads the same adapter through `mlx_lm.tuner.utils.load_adapters` (the native server's `--adapter-path` path). The resulting daytime logits match those from the trainer. The test does not establish full-size memory feasibility or model quality. Because norms and routing gates use other precision and this model is unusually small, its measured aggregate effective precision is 5.153 bits per parameter.

Both existing model runtimes have MLX 0.32.4 and mlx-lm 0.32.2. The chat runtime is `/Users/ben-hannan/learner-ops/swap1/venv/bin/python`; the installed sleep runtime is `/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python`. The latter also has torch/peft for the earlier real LFM3 checks. No package installation was needed. The system `python3` is Python 3.14 without NumPy/Jinja/MLX and cannot run the complete existing suite; selected dependency-free tests work there.

Native MLX adapter saves now include `sleepmlx_base` metadata (HF ID, pinned source revision, local quantization-config SHA256, informational resolved path). `sleepmlx.model.validate_adapter_base` is available to the daytime launcher and rejects mismatched base/revision/quantization metadata. Apex requires this identity; legacy K2 adapters retain their earlier compatibility behavior. A pinned base can move directories without invalidating the record if its source and quantization config still match. These metadata checks depend on correctly provisioned source weights; they do not cryptographically hash every weight file.

Reproducible architecture/profile/identity/target checks:

```sh
cd /Users/ben-hannan/Desktop/projects/premonition-reliability
/Users/ben-hannan/learner-ops/swap1/venv/bin/python -m unittest sleepmlx.tests.test_apex_profile sleepmlx.tests.test_adapter_identity sleepmlx.tests.test_mlx_qwen sleepmlx.tests.test_learning_correctness sleepmlx.tests.test_recipe -q
```

This focused command passed 56 tests in 1.932 seconds before adding the actual batch-generation assertion; the two architecture tests then passed with that assertion in 0.881 seconds. A full suite in the chat runtime passed 185 tests in 12.448 seconds, with one optional torch test skipped, before the final recall-budget/cache-identity change. The final installed-sleep-runtime suite passed 186 tests in 15.721 seconds with no skips, including the actual Torch numerical regression and tiny MLX architecture tests.

Provisioning constraints observed on this Mac: the existing Qwen3.6 3-bit MLX weights total 15,179,224,487 bytes, while the disk had only approximately 11 GiB free. A separate Apex MLX conversion therefore needs storage prepared first. Stock `mlx_lm.convert` lazy-loads parameters and writes output shards sequentially with model donation, which can reduce peak RAM, but its HF loader downloads the complete BF16 source before converting; it does not stream-download/delete one source shard at a time. The minimal standard conversion needs the 71.9 GB source on another mounted volume, plus room for the native MLX output. Stock MLX-LM does not accept GGUF as a trainable input. A custom shard-streaming converter would require additional validation of fused expert splitting, Qwen weight-name sanitization and per-module quantization metadata. No large downloads, storage deletion, service restart or active-job interruption were performed by this subtask.

The user subsequently changed the requested active model back to LFM3 for both chat and sleep. Apex provisioning was stopped. Before that instruction, an inert streamed converter and three tiny regression tests had been written; the tests passed in 1.560 seconds, including bitwise equality of every native quantized tensor against the stock Qwen conversion, strict native loading, matching logits, and a finite LoRA update. No full-size model conversion was run. The completed model correctness fixes remain useful independently of whether the inactive Apex profile is retained.

## LFM3 daytime adapter selection

`sleepmlx/day_adapter.py` provides the external LFM3 launcher with a conservative adapter selection. It checks `adapter.gguf` first, then `adapter.prev.gguf`, requiring the matching profile and HF ID, canonical HF base path and requested GGUF base path, a nonempty completed night identity, a successful served verdict with no pending descriptor, and artifact byte count plus SHA256 matching the actual file. Missing, malformed, legacy, failed, inconclusive, mismatched and changed artifacts are ignored. If neither candidate qualifies, the launcher receives empty stdout and exit status zero and can start the plain base model. `--json` exposes rejection reasons.

The normal export sidecar now retains top-level `artifact` metadata (version 1, byte count, SHA256) and `base_gguf` after its deferred served check completes. The pending descriptor reuses that artifact hash. An integration regression runs the real sidecar writer, observes rejection while pending, completes a synthetic successful served check, and then observes selection with the bound artifact metadata retained.

```sh
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -m sleepmlx.day_adapter --home /Users/ben-hannan/learner-ops/sleepmlx --profile lfm3_mps --base-dir /Users/ben-hannan/learner-ops/lfm3/hf --base-gguf /Users/ben-hannan/learner-ops/lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf
```

The focused daytime selection/export/recovery/checkpoint command passed 49 tests in 8.238 seconds:

```sh
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -m unittest sleepmlx.tests.test_day_adapter sleepmlx.tests.test_sleepcheck sleepmlx.tests.test_served_recovery sleepmlx.tests.test_checkpoint -q
```

This subtask has not started or reconfigured the production chat service; that integration is handled separately.

A later full-suite run exposed an export failure boundary: artifact hashing was outside the converter exception handler, so a converter claiming success without output could fail the trained night. Output existence/nonempty validation and artifact metadata publication now execute inside that boundary. Missing/empty output or metadata write errors are recorded as failed exports while preserving the committed training result. The positive fake converter now writes output bytes; new regressions verify missing output, empty output and metadata failure keep the trained adapter, finish night cleanup and cannot select an unverified daytime adapter. The CPU-only platform/day-adapter/recovery/checkpoint suite passed 50 tests in 7.479 seconds after this fix.

## Actual paired LFM3 replay experiment

After coordination reserved the Mac model slot and confirmed the day server was off, the isolated paired experiment ran once with the fixed plan: 12 updates per arm, learning rate 0.0002, replay sampling seed zero, maximum sequence length 256, teacher continuation limit 32, generation batch one, token budget 256, 8 GB MPS cap and 300-second boundary deadline. Each arm started from exactly the same saved adapter tensors and a fresh optimizer. Training used four fictional fact questions; the four learning probes used different wording. The independent 12-question retention monitor was excluded from both replay pools and all training. Every writable sleep/diary/userdata/ops/cache path was redirected into one disposable sandbox.

```sh
cd /Users/ben-hannan/Desktop/projects/premonition-reliability
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -u -m sleepmlx.replay_monitor --profile lfm3_mps --model-dir /Users/ben-hannan/learner-ops/lfm3/hf --output /Users/ben-hannan/Desktop/projects/premonition-reliability/reviews/premonition-validation-20261029/lfm3-replay-paired.json --steps 12 --seed 0 --max-seq-len 256 --replay-max-tokens 32 --gen-batch 1 --tok-budget 256 --mps-mem-gb 8 --budget-seconds 300
```

**The fixed learning criterion failed in both arms.** No target, seed selection, step count or pass mark was adjusted after observing results. Continuation replay remains opt-in and no adapter was promoted.

| Measurement | Before | Prompt replay | Continuation replay |
| --- | ---: | ---: | ---: |
| Independent strict monitor correct | 4/12 | 5/12 | 5/12 |
| Previously correct monitor answers lost | — | 0 | 0 |
| Fictional held paraphrases correct | 0/4 | 0/4 | 0/4 |
| Held learning gain | — | 0 | 0 |
| Last CE | — | 0.9881303906440735 | 0.987339437007904 |
| Last KL | — | 0.10624456405639648 | 0.13623209297657013 |
| Fixed exploratory pass (zero retention losses and at least one held gain) | — | false | false |

All 32 public teacher continuations were generated, contributing 941 selected target tokens. The small strict monitor is not a broad model-capability benchmark; preserving its four initially correct answers does not establish general retention. This short four-fact training run did not show generalization to the held wording and does not establish that larger or different LFM3 training would also fail. It provides no evidence of an advantage from continuation replay.

Elapsed time was 130.1596 seconds including imports/load/setup. At 0.1-second sampling intervals, maxima were MPS allocated 3.81844 GB, MPS driver 4.61352 GB and process RSS 7.28023 GB. These are sampled maxima, not allocator high-water marks. System memory-pressure probes remained level 1. The owned process (PID 5019) exited and released the model slot before the daytime service was allowed to start.

Reproducibility limitation: in this completed run, seed zero controlled replay sampling, while initial LoRA initialization was drawn once without an explicit Torch seed. Both arms did use the exact same saved initial tensors. Their safetensors SHA256 was `4ac9c7d905e280f3ecb3a899928b6fb3709e118d8de6ee9b50da1e9a106a8fe2`, read from `/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/premonition-replay-experiment-r793xkj0/initial-adapter/adapter_model.safetensors` before automatic sandbox deletion. That initial adapter was not retained. The harness now explicitly seeds Torch/MLX initialization for future CLI runs and automatically records initial adapter-file hashes; this fix does not change or retroactively reseed the completed result. The JSON result explicitly records the seed scope and initial hash.

Full measurements and sample answers are in `lfm3-replay-paired.json` alongside this report. The replay/day-adapter CPU regressions passed 24 tests in 0.527 seconds before the future-run seeding fix, and were rerun after that fix.


## Installed LFM3 and release validation

The final requested active model is LFM3 for both chat and sleep. Apex downloads and conversion work were stopped; the existing Qwen weights were preserved. Unused streamed-converter work was saved outside the checkout. The installed daytime service now runs the cached LFM3-1.7B QAD Q4 GGUF through the validated llama.cpp build on loopback port 18080, behind the existing gateway on 8090. Sleep remains `lfm3_mps` against the matching cached HF base. The service uses the accepted-adapter selector at each startup and wake; there is currently no accepted production adapter, so it serves the plain base.

The Mac service patch retains the pause, memory, competing-job and watchdog checks, updates process ownership checks for its llama-server, and preserves the existing MLX path. Originals, hashes and deployment manifests are saved in `/Users/ben-hannan/learner-ops/premonition-lfm3-backup-20261029-154045`. It also contains the previous app sources and settings. Source edits were made only in the isolated checkout; the original dirty checkout was preserved.

The installed app is version 1.2.2 with aliases `lfm3`, `lfm3-fast`, `lfm3-auto`, a smaller 4,500-token history budget, and the hidden creative proposer enabled for open ideation, stories and poetry. The proposer uses the same LFM3 weights through its fast alias, while the ordinary main chat keeps its reasoning mode. Planning, schedules, numeric budgets and explicit resource restrictions skip the extra proposal pass. Four final local probes returned valid proposals in 665–1032 ms (mean 889 ms); this is functional validation, not proof of better creativity. Main-alias probes exhausted the short output budget on reasoning, which is why the private pass uses the fast alias. Probes left the raw diary byte count, line count and modification time unchanged.

A real daytime API smoke produced `Hello`, emitted a native `test_add` call with arguments 4 and 5, and accepted its tool response before replying `9`. Those test-marked requests were excluded from the diary. Native app inspection confirmed the LFM3 aliases, version 1.2.2, available Sleep control and a successful connection test. The launcher was exercised through stop and restart; detached app-style startup keeps the service alive beyond the invoking command.

The memory editor now drains edits made during a save, rejects stale refreshes, preserves verified concurrent model appends, and retains both versions when overlapping changes need a comparison. Real Electron checks first exposed native keyboard/focus interference in the old test fixture and a separate real lost-update defect in the unconditional writer. The fixture now sends deliberate events explicitly; all persistence assertions remain.

Final complete suites: sleepmlx 221 passed; sleepmode 127 passed; desktop Node 437 passed and one skipped; real isolated Electron 209 passed, zero failures. Independent final integration review additionally passed 31 Python and 49 Node cases with no release-blocking findings. The upstream 1.2.1 updater fix that retains an offered update during background checks is preserved in 1.2.2; checks run every five minutes and installation still requires Update now.

Windows package: `desk/build/Premonition-win32-x64.zip`, 122,830,994 bytes, SHA256 `4c45a0d64f9c6311c8d2c53fbb7029d29349ee1fe7f5d67716ba3c1455d0c9af`. ZIP CRC, version, update interval/help, dream checker and fourteen important packaged-file hashes passed. Built with the existing Node 22 runtime after Node 26's packager aborted extraction without output. GitHub feed publication is recorded separately after verification; no remote installation on Jacob's machine has been observed.
