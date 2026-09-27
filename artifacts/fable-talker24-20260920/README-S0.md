# S0 — how to run the smoke test (Windows/BensPC and Mac)

Design source: `design/v3/24-talker-from-scratch-fable-design.md` §5 (S0), §2.3–2.6, §3.4.
Written by the model/trainer builder. **No GPU run has been done by this builder** — every
number below that is labelled "measured" was measured on the Mac CPU; the GPU column is
empty on purpose until the coordinator runs it.

---

## 1. What S0 does

Seven steps, time-boxed to **≤ 25 minutes of training** in total:

| # | Step | Budget | What it proves |
|---|---|---|---|
| 1 | autoencoder, size S, transformer mouth | 11 min | a sentence → 416 numbers → the sentence back |
| 2 | **GRU-mouth side arm** (decision D2's control) | 3 min | whether the transformer mouth is worth its parameters |
| 3 | slot fine-tuning (act, relation path, flags, both pointers) | 3 min | the typed part of the thought is learnable |
| 4 | thinker through the **frozen** mouth | 3 min | SONAR-LLM's recipe runs and the mouth really is frozen |
| 5 | kill test — a real `SIGKILL`, then a real resume | ~1 min | a crashed night costs minutes, not the night |
| 6 | the S0 model marks + the four §3.4 interventions | ~1 min | reconstruction, whole-thought exactness, slot swap |
| 7 | throughput benchmark of **M, L and XL** | ~3 min | real hours, instead of the 15-TFLOPS planning guess |

Every step writes its own `result.json`, and nothing has to be watched. Step 7 exists
because §2.4 says so: **if size-M throughput comes out under 60,000 tokens/s, the hours in
§2.4 are re-quoted to Ben before anything long starts.**

---

## 2. Mac (this is what has actually been run)

```sh
cd <worktree>/artifacts/fable-talker24-20260920
S0_DRY=1 bash run_s0.sh          # ~2 minutes, CPU, single-threaded
```

`S0_DRY=1` keeps the real preset S and the real data and shrinks only the clock, so it
exercises every code path the GPU run uses. **Measured on the Mac, 2026-09-20:** 7/7 steps
ran, 0 failures, 2 min 3 s wall-clock, kill test `BIT-IDENTICAL`.

The full (non-dry) form is the same command without `S0_DRY`, but it asks for ~20 minutes
of training and will use the CPU if there is no CUDA, which is not worth doing on a Mac.

---

## 3. BensPC — Windows, over ssh, PowerShell

`run_s0.sh` is bash and **BensPC does not run it**. The same seven steps as PowerShell:

```powershell
$repo = "C:\path\to\beautiful-model"
$py   = "$repo\.venv\Scripts\python.exe"
$art  = "$repo\artifacts\fable-talker24-20260920"
$out  = "$art\s0"
$common = @("--device","cuda","--preset","S","--micro-batch","64",
            "--shards","$art\shards","--dialogues","$art",
            "--checkpoint-minutes","2","--checkpoint-steps","500","--log-every","25")

& $py -B "$repo\scripts\fable_talker24_model.py" sizes
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage autoencode `
      --steps 1000000 --max-minutes 11 --out "$out\autoencode" @common
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage autoencode --gru-mouth `
      --steps 1000000 --max-minutes 3  --out "$out\autoencode-gru" @common
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage slots `
      --steps 1000000 --max-minutes 3  --out "$out\slots" @common
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage thinker `
      --steps 1000000 --max-minutes 3  --out "$out\thinker" @common
& $py -B "$repo\scripts\fable_talker24_train.py" kill-test --out "$out\kill" `
      --preset tiny --steps 40 --die-at 18 --micro-batch 8
& $py -B "$repo\scripts\fable_talker24_train.py" eval `
      --checkpoint "$out\autoencode\final.pt" --n 512 --device cuda `
      --shards "$art\shards" --dialogues "$art" --json "$out\s0-marks.json"
& $py -B "$repo\scripts\fable_talker24_interventions.py" report `
      --checkpoint "$out\autoencode\final.pt" --stage S0 --json "$out\interventions.json"
& $py -B "$repo\scripts\fable_talker24_train.py" bench --presets M L XL `
      --steps 20 --batch 32 --length 48 --device cuda --json "$out\throughput.json"
```

**One line over ssh** (the outer quotes are the shell's, the inner ones PowerShell's):

```sh
ssh benspc "powershell -NoProfile -Command \"& 'C:\path\to\beautiful-model\.venv\Scripts\python.exe' -B 'C:\path\to\beautiful-model\scripts\fable_talker24_train.py' train --stage autoencode --steps 1000000 --max-minutes 11 --device cuda --preset S --micro-batch 64 --shards 'C:\path\to\beautiful-model\artifacts\fable-talker24-20260920\shards' --out 'C:\path\to\beautiful-model\artifacts\fable-talker24-20260920\s0\autoencode'\""
```

### The restart loop (§2.6)

The design asks for a `.bat` loop that restarts from the newest checkpoint if the process
dies. It is built into the trainer instead, so it behaves the same on both machines:

```powershell
& $py -B "$repo\scripts\fable_talker24_train.py" restart-loop --stage autoencode `
      --steps 1000000 --max-minutes 11 --out "$out\autoencode" @common
```

It re-launches `train` from the newest checkpoint on any non-zero exit, up to 20 times. A
run that stops because it hit its own `--max-minutes` exits 0 and is **not** restarted.

### What is different on Windows

* **The kill test is not a `SIGKILL` there.** Windows has no `SIGKILL`, so
  `fable_talker24_train.py` falls back to `os._exit(137)`. That still skips every
  checkpoint, `atexit` hook and buffer flush, so the resume is tested exactly as hard —
  but the run is not killed by the operating system, so it does not exercise a crash
  *during* a checkpoint write. `kill-test.json` then reports `killed_signal: 137` instead
  of `-9`; both mean "the process did not get to save".
* **`run_s0.sh` is bash and cannot run there at all** — not only the `#!/usr/bin/env bash`
  line: it uses `${BASH_SOURCE[0]}`, `set -o pipefail`, `${PIPESTATUS[0]}`, `$(( ))`
  arithmetic, `date +%s`, `tee -a`, `ls -1 | tail -1` and a hard-coded **macOS** default
  interpreter path. Use the PowerShell block above, which is the same seven steps.

---

## 4. What the GPU box needs installed

`torch` (CUDA build) and `numpy`. That is all: the **training path imports neither
`tokenizers` nor `datasets`**, and there is a unit test asserting it (§2.1 says those are
needed for *building* the shards, which happens on the Mac). No `torch.compile` anywhere —
it still needs Triton, which Windows does not have, so everything is eager, as §2.3 assumes.
bf16 autocast turns on by itself on CUDA and stays off on CPU.

### 4a. Files that must be on the box

Training data is **generated on the box**, not copied: `INTERFACE-dialogues.md` §1 ships no
training file (a record is ~18 kB, so a million would be ~18 GB) and the generator makes one
in well under a millisecond from `(namespace, split, index)` alone. That means the three
generator modules travel with the trainer — they are pure standard library, so this adds no
package requirement.

| what | path | bytes |
|---|---|---|
| model | `scripts/fable_talker24_model.py` | 47,160 |
| loader | `scripts/fable_talker24_loader.py` | ~49,000 |
| trainer | `scripts/fable_talker24_train.py` | ~44,500 |
| interventions | `scripts/fable_talker24_interventions.py` | 18,324 |
| generator | `scripts/fable_talker24_dialogues.py` | 90,856 |
| generator frames | `scripts/fable_talker24_dialogues_frames.py` | 35,220 |
| generator parser | `scripts/fable_talker24_parser.py` | 27,109 |
| training shard | `artifacts/.../shards/s0/s0-00000.{tokens.u16,ents.u16,sents.u32,docs.u32,json}` | 132,006,952 (126 MB) |
| held-out shard | `artifacts/.../shards/valid/valid-00000.*` | 22,222,760 (21 MB) |
| tokenizer export | `shards/tokenizer_vocab.json`, `tokenizer_merges.txt`, `tokenizer_meta.json` | 244,116 |
| name rule | `dialogues/LEXICON.json` | 4,280 |
| evaluation set | `dialogues/L1-test.jsonl` | 18,018,730 |

≈ **166 MB** in total. `shards/train/`, `shards/parts/`, `dialogues/L2-test.jsonl` and
`shards/tokenizer.json` are **not** needed for S0 — `build_streams` prefers the `s0` split,
and `tokenizer.json` is the HuggingFace form that only the Mac's shard builder reads.

`runtime.local.json` is a Mac-only shim: `fable_talker24_model.py` tries the ordinary
`import torch` first and only falls back to it, so the file does not need to exist on the box.

---

## 5. Reading the result

* `s0/s0-marks.json` — the four model marks against the §5 thresholds, plus
  `all_marks_met`. Each threshold is printed beside its measurement.
* `s0/interventions.json` — the four thought-intervention tests and the two **pre-named**
  failure signatures ("the mouth ignores the thought", "the gist is blurry"), each with
  its fixes in the order the design fixed them in, before any run.
* `s0/kill/kill-test.json` — `ok: true` means the resumed run's parameter hash equals the
  uninterrupted run's, bit for bit.
* `s0/throughput.json` — tokens/s, peak GPU memory and implied TFLOP/s for M, L and XL.
  TFLOP/s is `6 × forward-parameters × tokens/s` (§2.4), and the row says so.

**Honesty rule built into the tooling.** Every `result.json` carries a `source` string. If
it contains the word `synthetic`, that run trained on stand-in data this builder generated,
not on the real corpus or the real dialogues, and **nothing from it may be quoted as an S0
result**. The S0 evaluation repeats the same warning in its own output.

---

## 6. Sizes (printed by `fable_talker24_model.py sizes`)

| preset | width | blocks (ears+mouth+thinker) | total trainable | yardstick chat-LM |
|---|---|---|---|---|
| S | 192 | 4+4+2 | 7,013,312 | 5,245,696 |
| M | 384 | 6+6+4 | 33,569,664 | 29,369,856 |
| L | 576 | 8+8+4 | 87,627,968 | 29,369,856 |
| L640 | 640 | 8+8+4 | 107,235,456 | 29,369,856 |
| XL | 768 | 12+12+4 | 209,009,664 | 29,369,856 |

The frozen reasoner is 79,316 parameters in every preset and is never trained.
`L` uses width 576 because the design's stated "≈ 85M" and its stated "width 640" disagree
arithmetically; `L640` is the literal reading and is there so the choice is Ben's, not this
builder's.
