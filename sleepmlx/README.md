# sleepmlx: a sleep trainer for Ben's assistant

Plain version: while the assistant is "asleep", this program reads one new day of Ben's real chats, turns the facts in them into
practice cards, studies the cards by training a small add-on to the model (a LoRA adapter), and then checks that the model did not
get dumber and that it can answer questions about cards it was never shown. If the check fails, it throws the night away.

It is a port of the `ab_ob_b4_nb` recipe from `backbone/sleep/brain/sleepb.py` (branch `origin/claude/project-thread-cqc4bi`),
run as a Sleep Mode worker (`sleepmode/workers.py` `CommandWorker`, branch `origin/claude/project-thread-sl2x88`).

**Status, read this first.** Everything that touches MLX (`model.py`) or PyTorch (`torch_backend.py`) has never run: there is no
Mac or Windows machine here. What *is* shown (unit tests, Linux, fake model): the diary converter, the night pipeline logic,
budget stop and resume, the gate and its undo, the worker's output format (also checked against the real `CommandWorker` class),
recall, status, the SHY maths in numpy. Everything else is "untested until the Mac run".

## What a night does

One night = one new diary day (days already slept are tracked in `state.json`; a slept day that gains 5+ new turns counts as new again).

1. **Convert** the raw logs to sleepb's week JSON (`diary.py`): only Ben's own turns plus final answers, secrets redacted, `ignore.txt` applied.
2. **Tag** the day's facts: for each turn the model lists subject-relation-object triples (`tag_prompt`, "Sam" is now "Ben"). K2 thinks first (up to 512 tokens).
3. **Names pass**: pairs of capitalised names in a turn that no fact links yet are asked about ("how are A and B related?"). Verifier prompts and parsers are sleepb's.
4. **NREM cards**: per fact, the base model (adapter off) writes paraphrases and question/answer pairs in both directions; each Q&A is verified by asking the base model from the chat text alone; leaks of the gate questions, duplicates and cards that miss the names are dropped.
4b. **Corrections, lessons, habits, notes** (`lessons.py`, new, not from sleepb; on by default, switch off with `use_lessons` / `use_habits` / `use_userdata`):
   * *Corrections, newest wins*: when Ben corrects Glim ("no, it's X", "that's wrong", "X, not Y"), the facts in his correction get the corrected flag
     (priority x2 or more), and an older fact about the same name that it replaces is retired (dead, in `dropped`, never re-made); its value is kept in
     `items.json` `wrong`, and any paraphrase or question card that mentions a wrong value for that name is dropped (`dropped_wrong_claim`).
   * *Lessons*: the day's failures (Ben corrected Glim, a tool step failed or was retried, Glim gave up, its self-check said "not done", Ben pressed Stop)
     each get a short post-mortem by the base model (`lesson_prompt`: what Glim did, what went wrong, what to do instead, plus one question and a
     1-4 word answer). Checked like other cards: the answer must be in the chat text (in Ben's own words for a correction), must not be a wrong value,
     and the base model must give it back from the chat text alone. Kept lessons become one text card and one Q&A card (priority like an important,
     corrected fact), at most `max_lessons` (8) x s per night. The wrong value Glim said is replaced by "the wrong answer" in the card text.
     The night's lessons are in the chunk output (`lessons`), in `nights.jsonl`, and in the Windows sleep summary under **Lessons**.
   * *Habits*: the same kind of tool job (open the same website or app, run the same command, search the web) on 3+ turns becomes a habit card;
     the most used job of each kind also gets a question card. Built from the logged tool steps, word for word (no model writes them).
   * *Saved notes and the Keeping track of list*: `memory.json` and `tracking.md` in the Desk's userData folder (`SLEEPMLX_USERDATA`; default the
     app's folder) become cards (tracked items with source and until questions). Every such card carries `source` (and `until`) in `cards.jsonl`.
     A tracked item past its until date, finished or removed, and a forgotten note, leave the training pool. Secret-looking or ignored text is left out.
   The diary converter now also reads, per turn, the tool steps (`tools`: name, short args, ok, short result), the app's self-check notes (`checks`)
   and `stopped`, which the Desk gateway adds to its records (it adds fields, the old ones are unchanged). The app's own "[Self-check]" and screenshot
   messages are no longer taken as Ben's turns.
5. **Hold-out**: about 10% of the night's new cards (Q&A only) are held out and never trained on. Each fact keeps at least 2 other cards, so the held-out question tests a *new wording* of a taught fact, and (alternating) the *reverse* direction.
6. **Train** a LoRA in 4 cycles. Each step is 16 cards (text paraphrases, closed-book Q&A, and 50% open-book Q&A where the prompt carries BM25 notes from the diary) plus 8 generic replay sequences with a KL penalty against the base (LoRA scale 0 = base). Cards of earlier nights stay in the pool, so they are replayed. After each cycle's NREM steps comes **REM**: the current adapter writes two-step "chain" questions that combine two facts through a shared name (K2: `q_think` variant), and "gist" habit questions for facts seen on 3+ days; the base model verifies them from the chat text; kept dreams join the practice pool. Cosine learning rate, fresh AdamW per night, gradient clip 1.0.
7. **Downscale (SHY)**: every LoRA's weight change is SVD'd, its singular values x 0.85, those under 5% of the largest zeroed (sleepb defaults).
8. **Gate** (replaces sleepb's ARC slice):
   a. 40 fixed general questions (facts, arithmetic; `gate.py`). The base model's correctness is recorded the first time (`gate_base.json`); the adapter may not lose more than 3 percentage points (with 40 questions: at most 1 more wrong).
   b. Recall quiz on the held-out cards, closed book, adapter on. `quiz` = recall %.
   If (a) fails the night is undone: the committed adapter stays, the model in memory goes back to it.
9. **Commit** on pass: publish the immutable adapter under `adapters/<night-id>/` and atomically update `adapters.json` with the current and previous paths. The prior adapter and the night's checkpoint stay available throughout promotion.

Flags that equal `ab_ob_b4_nb` (sleepb defaults): work scale s (see below), bsz 16, replay 8, KL weight 1, lr 2e-4, LoRA rank 16 / alpha 32,
SHY 0.85 / 0.05, 160 items, 30 REM chains, 30 gist dreams (all x s), NREM share 0.80/0.65/0.50/0.35 per cycle, 50% open-book,
`bridge_prompt` for REM chains, the names pass on, K = 4 cards per fact at s = 1, dream length 400 tokens x s.

**Work scale.** At the start of a night the backend times a training-shaped step and one generation batch; then
`s = clip(B / R, 0.25, 4)` with `R = 150 x t_step + ref_gen_batches x t_gen` (sleepb's `plan_scale`), B = `SLEEPMLX_NIGHT_BUDGET_S` or, if unset, the budget of that
chunk. Steps, cards per fact, item cap, REM chains and gist dreams all scale with s. On the M1 at ~33 s per step R is ~7,500 s, so a 1 h chunk gives s of about 0.5 (about 70 steps for a small night).

## Stopping and resuming

Sleep Mode calls the worker once per "hour". The worker stops cleanly, checkpoints, writes `SLEEPMODE_OUT` and exits 0 when:
the chunk budget (minus a reserve of max(20 s, 5%)) would be exceeded by the next generation batch or training step; SIGTERM/SIGINT; `ASSISTANT_RUNNING` appears; `PAUSE_OTHERS`
exists; memory pressure is above 1 (Mac `sysctl`; elsewhere psutil available RAM below `min_free_ram_gb`, skipped if psutil is missing).
State: `night/night.json` is the publication manifest for an immutable `night/checkpoints/<generation>/` containing matching phase, step count, items/REM bookkeeping, and adapter weights. New weights checkpoint every 10 steps, before REM generation, on stop, and at the SHY boundary. Metadata-only generations share immutable weight files where the filesystem supports hard links. Prior generations remain until the night completes; incomplete generations are ignored. An unexpected failure resumes the last published generation, replaying any unsaved updates. A required missing checkpoint fails explicitly instead of restarting from the base.
The next chunk resumes mid-night. Optimizer state is not saved: AdamW restarts on resume (the learning-rate schedule continues from the saved step).
The gate decision and final state are journaled before promotion. Restarting finalization preserves the candidate, promotes once, and writes one state increment and one history row. Legacy `night/adapter/` checkpoints and committed `adapter/` folders are readable. GGUF export and the later served-model check remain separate: an interrupted Python export is reported as incomplete and needs an explicit `export-gguf` retry; these tests do not establish recovery through a power loss or a model-server restart.
`quiz` is `null` in every chunk except the one where the night finishes. When no unslept day is waiting the worker answers in a moment without loading the model.

## Files

Sleep root: Mac `~/learner-ops/sleepmlx/` (env `SLEEPMLX_HOME`); Windows `%APPDATA%/Premonition/sleep`.
`adapters.json` (current and previous immutable adapter paths), `adapters/<night-id>/` (`adapters.safetensors` + `adapter_config.json`, mlx_lm format; PEFT format on the torch backend), legacy `adapter/` and `adapter.prev/`, `cards.jsonl` (every card with status
`trained` / `pending` / `held_out`), `nights.jsonl` (one row per night: scale, quiz, harm, steps, stats), `items.json`, `state.json`, `gate_base.json`, `ignore.txt`, `sleepmlx.log`.
Diary input: Mac `~/learner-ops/diary/raw/YYYY-MM-DD.jsonl` (+ `blobs/<sha1>`; `{"$blob": sha}` content refs are resolved; `k2-helper` records skipped);
Windows app `%APPDATA%/Premonition/diary/*.jsonl` of `{ts, model, messages:[{role, content}], response:{content}}` (any file name; days are taken from `ts`). Override with `SLEEPMLX_DIARY_DIR`.

**ignore.txt** (sleep root, created on first use): one phrase or regex per line, case-insensitive; a user turn matching any line is dropped with its answer. Seeded with
`AP Chem 4th period`, `Mr. Phipps`, `I like short answers`, `open example.com`, `Remember that I take`. Records with `test: true` (or a `test` / `X-Test` header) are skipped.
Items whose turns disappeared this way are dropped at the next night. If a false fact was already slept, delete `items.json`, `cards.jsonl` and `adapter*` and re-sleep.

The converter's block stripping (date prefix, "Saved notes about Ben", "[Background, not a request ...]", `<memory>` tags) is a guess at the Desk's format.
Preview it first: `python -m sleepmlx diary`.

## Commands

```
python -m sleepmlx.worker                 # the Sleep Mode CommandWorker entry (reads SLEEPMODE_BUDGET_S, SLEEPMODE_OUT, SLEEPMODE_PRACTICE [accepted, unused], SLEEPMODE_WORKDIR)
python -m sleepmlx.worker --dry-run       # tag and write cards, no training; day stays unslept
python -m sleepmlx recall "question" [--server URL]   # base + adapter, one short line, no-think, max 64 tokens (for the Desk's recall tool)
python -m sleepmlx status                 # JSON: slept days, next day, night in progress, adapter, card count, last night
python -m sleepmlx night --budget-s 1200  # same as the worker, flags instead of env
python -m sleepmlx diary [--date D]       # preview the converted diary
python -m sleepmlx export-gguf --llama-cpp DIR --base HF_BASE_DIR   # torch backend: PEFT adapter -> llama.cpp GGUF LoRA
```
`SLEEPMODE_OUT` JSON: `{"quiz": float|null, "steps": int, "interrupted": bool, "harm", "general", "reverted", "status", "phase", "scale", "message", ...}`.
`interrupted` is true only for external stops (wake, pressure, signal), not for a plain budget end. `general` (the 40-question score) is there for the scheduler's forgetting guard.

### A 20-minute test night on the Mac

**Default model is now LFM3-1.7B on the torch backend (MPS)**, profile `lfm3_mps`. Download the HF weights once (the worker prints this exact command if the folder is missing):
```
huggingface-cli download LiquidAI/LFM3-1.7B --local-dir ~/learner-ops/models/lfm3-1.7b-hf
```
The venv needs `torch transformers peft safetensors psutil`. K2 on MLX stays available: add `--profile k2` (or `SLEEPMLX_PROFILE=k2`) to any command below.
The assistant's model servers must be stopped (no `ASSISTANT_RUNNING`, nothing else big in memory). Use the venv python.
```
cd ~/learner   # the repo, on this branch
PY=~/learner-ops/swap1/venv/bin/python
export PYTHONPATH=$PWD

$PY -m unittest discover -s sleepmlx/tests -t .          # sanity (also runs on the Mac)
$PY -m sleepmlx diary                                    # read it: is anything private or wrong still there? edit ~/learner-ops/sleepmlx/ignore.txt
SLEEPMODE_BUDGET_S=1200 SLEEPMODE_OUT=/tmp/dry.json $PY -m sleepmlx.worker --dry-run
cat /tmp/dry.json; head -20 ~/learner-ops/sleepmlx/cards.jsonl
SLEEPMODE_BUDGET_S=1200 SLEEPMODE_OUT=/tmp/night.json $PY -m sleepmlx.worker     # a 20 min chunk
cat /tmp/night.json; $PY -m sleepmlx status
# if status shows night_in_progress, repeat the last worker line: it resumes. When done:
$PY -m sleepmlx recall "Where does Marta work?"
```
The dry run's generations are cached and reused by the real night, so the dry run costs nothing extra. Watch peak memory in `~/learner-ops/sleepmlx/sleepmlx.log` and Activity Monitor.
With one day of diary the first night is likely a dry run by design: fewer than 12 trainable cards (`SLEEPMLX_MIN_CARDS`) writes the cards, prints a message and leaves the day unslept so the next day's chat adds to it.

## Expectations (honest)

* **Mac, K2 4-bit** (measured by the bench, not by this code): 33 s per night step (8 text + 8 Q&A + 8 replay at budget 256, GC off, train peak 8.12 GB); generation 38.9 tok/s at batch 8, peak 5.12 GB; load 4.14 GB.
  This code defaults to gradient checkpointing ON, memory limit 5 GB and cache limit 0.5 GB (as in the bench); with GC on the peak should drop below the 8.1 GB measured with it off, and the aim is under 8 GB. Untested.
  Thinking tag/names calls cost up to 512 tokens each: a 40-turn day is roughly 10-15 minutes of tagging alone. Expect a real night to take 1-3 chunks of an hour.
* **Windows CPU, LFM3-1.7B (profile `lfm3_cpu`)**: bf16 frozen base (~3.4 GB), LoRA rank 8 on attention + `conv.out_proj`, 4 cards per step, micro-batch token budget 256, gradient checkpointing, `torch.set_num_threads(cores-1)`,
  KL replay every 4th step, 20 gate questions with 16 new tokens, abort if free RAM < 1 GB. **No CPU timing has been measured.** A rough guess: 1.7B parameters x ~6 FLOPs x ~600 tokens plus recompute
  is ~15-20 TFLOP per step, so roughly 1-3 minutes per step on a laptop CPU, and generation of a few tokens per second. The night measures its own step time and shrinks to the budget (s down to 0.25), so a 1-3 h night is a small night (tens of steps, dozens of cards). Treat all of this as a guess until it runs.
* **LFM3 on the Mac (profile `lfm3_mps`, torch on MPS)**: released `mlx_lm` cannot load LFM3 yet (shown), so the Mac uses PyTorch on the GPU (MPS). Frozen base in fp16 (bf16 is shaky on M1), LoRA weights and the loss in fp32,
  so no loss scaling is needed (the safe option: only the frozen weights are half precision); `PYTORCH_ENABLE_MPS_FALLBACK=1` is set; memory is capped with `torch.mps.set_per_process_memory_fraction` at about 10 GB (`runtime.mps_mem_gb`);
  LoRA rank 16 on attention q/k/v/o + `conv.out_proj`; token budget 512; gradient checkpointing on. **No timing or memory number exists for this path yet**: the 33 s/step figure above belongs to K2 on MLX. LFM3 is 1.7B (K2 3.7B), so it should be faster, but that is a guess. The night measures its own step time and scales to the budget.

## Models and backends (profiles)

A profile (`sleepmlx/profiles/*.json`, or any path) holds the model dir / HF id, loader, chat-template mode and strings, think and no-think markers, stop token, LoRA targets, per-model parsing quirks, recipe overrides and runtime settings.
**Default `lfm3`** is an alias: `lfm3_mps` on macOS, `lfm3_cuda` on Windows/Linux with a CUDA card, otherwise `lfm3_cpu`.
`lfm3_mps` (torch on MPS, HF dir `~/learner-ops/models/lfm3-1.7b-hf`), `lfm3_cuda` (LoRA on attention + conv + feed-forward by regex), `lfm3_cpu` (the small-laptop settings above), `k2` (MLX, still available). Select with `SLEEPMLX_PROFILE` or `--profile`.
The torch backend picks its device in the order cuda, mps, cpu. If a profile's `model_dir` is set but missing, the worker prints `huggingface-cli download <hf_id> --local-dir <dir>` and stops with that error; a profile with no `model_dir` loads `hf_id` from the Hugging Face cache.
Overrides: `SLEEPMLX_MODEL_DIR`, `SLEEPMLX_HF_ID`, `SLEEPMLX_LOADER=module:function` (+ `SLEEPMLX_LOADER_PATH`; the function takes the model dir and returns `(model, tokenizer)`), `SLEEPMLX_BACKEND_KIND=mlx|torch`.
K2 (MLX) loads with plain `mlx_lm.load(path, trust_remote_code=True)`; the loader hook is kept anyway. Another runtime can be plugged in with `SLEEPMLX_BACKEND=module:function` returning `(backend, tokenizer)`; the `Backend` interface is in `backend.py`.
The K2 quirks live in the profile: full thinking (512 tokens) for tagger and names pass, the "not / none / nothing / nope / unrelated = no" reply rule, REM chain mode `q_think`. LFM3 profiles ask without thinking (`<think></think>`).

**Recall on the Mac.** `recall` with the torch backend loads the model each call (slow). `--server http://127.0.0.1:8080` instead asks a running llama-server (started with `--lora ~/learner-ops/sleepmlx/adapter.gguf`, built with LFM3 support) through `/completion`
with the same no-think prompt; if the server does not answer it prints a note on stderr and falls back to the slow load.

**Automatic GGUF at night end.** When a night commits (not when it is undone), `adapter.gguf` is exported into the sleep root if `SLEEPMLX_LLAMA_CPP_DIR` (or the profile's `runtime.llama_cpp_dir`) is set and the HF base dir exists
(the profile's `model_dir`). Any failure is logged and returned in the chunk output as `gguf: {ok, message}`; it never fails the night. Only the torch backend writes the PEFT adapter the converter needs.

**Windows / GGUF.** The torch backend saves the adapter in PEFT format. To use it in the app: `python -m sleepmlx export-gguf --llama-cpp <llama.cpp dir> --base <HF dir of LiquidAI/LFM3-1.7B> --out adapter.gguf`
(this runs `convert_lora_to_gguf.py <adapter dir> --base <HF dir> --outfile adapter.gguf`; it needs the HF base directory, not the GGUF), then start `llama-server -m <base>.gguf --lora adapter.gguf`. Untested; the LFM3 llama.cpp support was merged only on 2026-10-27.
Model environment for torch: `pip install torch transformers peft psutil safetensors` (the HF repo needs `trust_remote_code`).

## Simplifications (each one is a place where this differs from sleepb.py)

1. **Gate**: 40 own questions + held-out recall instead of 100 ARC-Easy questions; no "consolidated items recall" rule (there are no morning probes).
2. **No morning probes, consolidation or update detection** (`detect`, `now_prompt`, "reconsolidation" of changed facts such as a new address). Priority is days seen x (1 + important + corrected) x 2; an item is eligible after 1 day (`min_item_days`, sleepb needs 2). Facts that change are handled only when Ben corrects Glim (step 4b); a plain change without a correction can still leave both values as cards. Lesson, habit and note cards are not held out, so the recall quiz does not measure them.
3. **Held-out cards replace sleepb's probe** (sleepb's probe is also an untrained card, but one per fact and used for priority).
4. **KL replay set**: 34 generic prompts rendered as sequences (KL on all their tokens), not base-model answers to 200 generic prompts.
5. **No optimizer state across chunks**; the batch stream is re-seeded per step (deterministic), so a resumed night is equivalent but not bit-identical to an uninterrupted one.
6. **No twist / vary / x4 / efficiency flags** (they are off in `ab_ob_b4_nb`); `--rem-dirs alt`, `--rem-tries 1`, REM writer = the adapter, as defaults.
7. **MLX specifics**: LoRA through `linear_to_lora_layers` (all layers, 7 projection keys), logits only at target positions, right padding without a mask (causal), generation by `batch_generate` with the stop tag applied after the fact (a thinking stage runs to its cap if the close tag is not a stop token), memory caps by `mx.set_memory_limit`. SHY runs in numpy on the CPU (QR of the thin factors, as sleepb).
8. **The recall/gate check never uses the open-book notes** (closed book only).
9. **CPU profile**: KL replay every 4th step; 4 cards per step instead of 16; rank 8, attention only.
10. **Practice data** (`SLEEPMODE_PRACTICE`) is accepted and ignored for now. The practice checkers on `origin/claude/project-thread-nilgf9` (`practice/grade.py`) are simple, but practice there is expert iteration with its own trainer (SFT + DPO on solved tries, multi-turn transcripts) and its pilots did not show a significant gain, so it was not wired into this night.
11. Redaction and block stripping are heuristics (passwords, PINs and codes after their keyword, Luhn-valid card numbers, SSNs, API-key shapes, long random tokens).

## Tests

`python3 -m unittest discover -s sleepmlx/tests -t .` (Linux, no mlx / torch needed; a fake model learns name pairs from its training examples and advances a fake clock).
Covers: device order with a mocked torch, profile choice per platform, the `lfm3_mps` profile, the missing-model download command, `recall --server` against a local HTTP stub, GGUF export on commit (and its failure), diary converter (dedupe, tool loops, blob refs, helper records, block stripping, redaction, ignore list, test-mode records, the app's simple format), week-JSON validity against sleepb's `check_week` rules,
the full night and a second night (adapter.prev, replay of earlier cards), dry run and the too-little-data path, held-out cards never trained, budget stop and resume (no step repeated, no finished generation batch repeated),
external stops (assistant running, PAUSE_OTHERS, memory pressure, SIGTERM-style), wake mid-training checkpoint, gate judge and undo (including the first night), the CommandWorker output format
(including a subprocess run of `python -m sleepmlx.worker`), recall with a fake model, status, profiles and templates, Windows paths, the SHY maths;
`test_lessons.py`: tool steps / self-checks / stops in the diary (both log formats, secrets hidden), failure kinds and correction words, lesson checks, a correction night
(old fact retired, no positive card for the wrong value, lesson trained, `lessons` in the output), the lesson cap, habits, notes and tracking cards with source and expiry.
