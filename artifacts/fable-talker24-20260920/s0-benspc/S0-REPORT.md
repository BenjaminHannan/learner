# S0 on BensPC — the GPU smoke test, run 2026-09-20

Coordinator's report. Every number here was measured on **BensPC** (RTX 5070 Ti 16 GB,
Windows 11, driver 591.86) unless it explicitly says otherwise. The raw files beside this
one are the tooling's own output, copied back unedited.

Remote working folder, left in place for later runs:
**`C:\Users\benja\talker24\`** — scripts in `scripts\`, data and results under
`artifacts\fable-talker24-20260920\` (results in `...\s0\`, run log at
`C:\Users\benja\talker24\s0-run.log`). 1.73 GB on disk; 97 GB free after.

---

## 1. The box, before anything ran

| check | measured |
|---|---|
| reachable | yes, `ssh benspc`, user `benspc\benja` |
| GPU idle | **yes** — 452 MiB / 16,303 MiB used, 0 % util, all of it desktop compositor and ordinary apps (dwm, explorer, Discord, PowerToys). No `llama-server.exe`, no other compute job. |
| `ScoutLlamaServer` | read only: state `Disabled`. **Not** enabled, started, modified or deleted, before or after. |
| free disk | 108 GB |
| interpreter used | `C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe` — Python **3.10.9** |
| torch | **2.11.0+cu128**, `cuda.is_available() True`, CUDA 12.8, arch list includes `sm_120` |
| numpy | 2.2.6 |
| bf16 | `torch.cuda.is_bf16_supported() == True` |
| device | `NVIDIA GeForce RTX 5070 Ti`, 17.09 GB total as torch reports it |
| installs | **none.** No pip, no conda, no winget, no downloads. |

There is a second Python on the box (3.13.1) whose torch is **2.6.0+cpu** — it must not be
used. The README's `$repo\.venv\Scripts\python.exe` does not exist on BensPC at all.

## 2. Files copied, and verified

The 22 files of INTEGRATION-AUDIT.md §4 (7 scripts + the `s0` shard + the `valid` shard +
the tokenizer export + `LEXICON.json` + `L1-test.jsonl`), 166 MB. **sha256 and byte length
of all 22 were compared local vs remote and all 22 matched** — the list is in
`copied-files-sha256.txt`. Nothing outside that checklist was copied; `shards/train/`,
`shards/parts/`, `shards/tokenizer.json`, `L2-test.jsonl` and `runtime.local.json` were
correctly not needed. No credential, `.ssh` or `.config` path was read, printed or copied.

---

## 3. The S0 marks (design §5) with their pre-fixed thresholds

| Mark | Threshold (set before the run) | Measured | Verdict |
|---|---|---|---|
| runs end to end in the environment, bf16, **no system installs** | yes | 7/7 steps ran; bf16 autocast on; nothing installed | **PASS** (after 3 source fixes — §6) |
| kill → resume → parameter hash equals the uninterrupted run | identical | CPU arm: `138c3be0…7127` both sides. **CUDA arm: `51a1d221…4c41d2` both sides.** | **PASS** |
| size-M throughput | measured and reported; re-quote the hours if < 60,000 tok/s | **33,685 tok/s** at the design's bench settings (batch 32 × 48); 67,610 at batch 64 × 48; **12,022 tok/s in the real training loop** at the trainer's own micro-batch 64 | **REPORTED — and the gate is tripped.** The hours are re-quoted in §5. |
| held-out sentences ≤ 16 pieces: token accuracy / exact sentence | ≥ 90 % / ≥ 50 % | **61.2 % / 41.4 %** (n = 512, real `valid` shard) | **FAIL** — see §4 |
| act + slots on seen frames, whole-thought exact | ≥ 95 % | **100.0 %** (n = 512 real L1 turns, on the `slots` checkpoint) | **PASS** |
| slot-swap test | ≥ 95 % (S0's relaxed mark; S1/S2 want 98 %) | **92.2 %** on the autoencode checkpoint; 40.1 % on the slots checkpoint | **FAIL** |

The other three §3.4 interventions, on the same real data (inside `s0-marks.json`):
gist-shuffle **1.000** (mark 0.99) PASS · gist-zero change **1.000** (mark 0.90) PASS ·
thought-replace **1.000** (mark 0.95) PASS.

**`s0/interventions.json` (step 6b) must not be quoted.** The `interventions.py report`
CLI has no `--shards` / `--dialogues` flag and builds its turns with
`L.synthetic_dialogues(...)`, so by the builder's own honesty rule those numbers measure
the plumbing only. The intervention numbers worth quoting are the ones embedded in
`s0-marks.json`, which ran over the real `valid` shard and real `L1-test.jsonl`.

### Why the two failures are not a verdict on the idea

The autoencoder had **11 minutes and 11.1M tokens**. S1 asks for **1.0–1.2B** — about
**100×** more. The reconstruction curve was still falling steeply when the clock stopped
(loss 8.59 → 0.55). The pre-named "mouth ignores the thought" signature *did* trigger, on
the clause `exact reconstruction 0.000 < 0.3` — but that clause was evaluated on the
synthetic step-6b run; on real held-out text exact reconstruction was **0.414**, well over
the 0.30 the signature looks for, and thought-replace was 1.000 (the mouth is plainly
following the thought). I would not spend a fix from the §3.4 list on this yet.

The slot-swap number is the one to keep an eye on. Broken down by field on the autoencode
checkpoint: relation **0.922**, subject **0.000**, object **0.000** — the mouth re-words the
relation when the relation slot changes, but a swapped subject or object pointer does not
reach the spoken sentence at all. On the `slots` checkpoint (which is where the pointer
heads were actually trained) subject rises to 0.213 and object to 0.129 while relation
falls, because that stage does not train the mouth. **This is a real signal, not noise, and
it is the thing to re-measure first in S1.**

## 4. What each step produced

| # | step | budget | wall-clock | outcome |
|---|---|---|---|---|
| 1 | autoencode, preset S, transformer mouth | 11 min | 660.2 s | 15,563 steps, 11,105,942 tokens, loss 8.59 → 0.55, `parameter_hash 7ae46aaf…` |
| 2 | **GRU-mouth side arm (D2)** | 3 min | 180.2 s | 5,929 steps, 4,231,533 tokens |
| 3 | slots | 3 min | 180.2 s | 4,055 steps, real generated L1[100000:100512], 6,749 turns, `synthetic: false` |
| 4 | thinker through the frozen mouth | 3 min | 180.1 s | 4,529 steps, same real dialogues |
| 5a | kill test, built-in | ~1 min | 9 s | `ok: true`, `killed_signal: 137`, resumed from `step-00000015.pt` |
| 5b | kill test, **CUDA** (added) | — | 10 s | hashes identical |
| 6 | S0 marks + interventions | ~1 min | ~40 s | see §3 |
| 7 | throughput M / L / XL | ~3 min | 4.5 s | see §5 |
| + | preset-M real-loop probe (added) | 1 min | 60.6 s | 1,021 steps, 728,784 tokens |
| + | extra benches at the corpus's real sentence length | — | ~25 s | §5 |

**Total GPU time ≈ 22.8 minutes, inside the 25-minute box.**

**D2, the GRU side arm — the transformer mouth earns its parameters.** At *equal tokens*
(4.23M, step 5925) the transformer mouth is at loss **1.121** and the GRU mouth at
**1.736**; mean over the last 20 log points, 1.112 vs 1.789. On the held-out `valid` shard
the 3-minute GRU checkpoint reconstructs 11.9 % of sentences exactly at 36.5 % token
accuracy, against the transformer's 41.4 % / 61.2 % at 11 minutes. One seed, minutes not
hours, so this is an indication and not a finding — but it points the same way the design
guessed.

**Kill/resume on Windows degrades to `os._exit`, as the audit said.** Windows has no
`SIGKILL`; `kill-test.json` reports `killed_signal: 137`, not `-9`. Every checkpoint,
`atexit` hook and buffer flush is still skipped, so the *resume* is tested exactly as hard,
and it passed on both CPU and CUDA. What is **still unverified** is `atomic_save`'s
temp-file-then-`os.replace` under a crash *during* a checkpoint write — no OS-level hard
kill was performed, so that path has not been exercised on NTFS.

---

## 5. Throughput, and the hours — measured, not assumed

`bench` trains a synthetic batch with no data loader. The real training loop was measured
too, and at matched batch and length the two agree closely: preset M, batch 64, 12 pieces —
real loop **12,022** tok/s against a bench of 13,089 and 15,804 on two separate runs of the
same bench point (small model, tiny batch, so the bench itself is ±20 % noisy at this
size). Taking the midpoint, **the real loop runs at ≈ 0.83 × bench** when the sequence
length matches. So the bench is trustworthy — **provided the sequence length matches the
real corpus**, which at `length 48` it badly does not.

### The headline benchmark — the design's own settings, batch 32 × length 48

| preset | forward params | tokens/s | peak GPU memory | implied TFLOP/s |
|---|---|---|---|---|
| **M** (33.57M) | 26,131,328 | **33,684.7** | **1,060 MB** | 5.28 |
| **L** (87.63M) | 71,162,368 | **22,994.3** | **2,177 MB** | 9.82 |
| **XL** (209.01M) | 179,977,856 | **13,927.4** | **4,651 MB** | 15.04 |

**Does XL fit in 16 GB at the design's batch/sequence settings? Yes, easily** — 4.65 GB of
the 15.85 GB free, a 3.4× margin. It also fits at batch 64 × 48 (6.73 GB) and at batch 512
× 12 (12.42 GB, which is the tightest configuration I would recommend).

Other measured points (all batch × length, tokens/s, peak MB):
S 32×48 **45,173** / 419 · S 64×48 **90,688** / 742 · M 64×48 **67,610** / 1,688 ·
L 64×48 **43,767** / 3,311 · XL 64×48 **23,843** / 6,730 · M 64×12 **13,089 and 15,804** /
776–778 · L 64×12 **9,729** / 1,714 · XL 64×12 **6,946** / 3,853 · M 128×12 **32,776** /
1,152 · M 256×12 **63,946** / 1,879 · M 512×12 **104,045** / 3,345 · M 1024×12 **107,364** /
6,285 · L 512×12 **50,100** / 6,369 · XL 512×12 **22,481** / 12,419.

### The thing that actually decides the hours

**The corpus sentences are short: mean 10.52 pieces in the `s0` shard, 10.54 in `valid`.**
The loader packs one sentence per row, so a batch of 64 rows is ~713 real tokens — not the
3,072 the `length 48` benchmark assumes. Measured in the real 11-minute run: 713.6
tokens/step, 23.6 steps/s. The loop is **step-rate-bound, not compute-bound**, and the
5070 Ti sits mostly idle. The §2.3 length curriculum does not rescue this: even its final
≤ 48 phase only lifts the mean row from ~11.2 to ~12.5 pieces, about 12 %.

### Projected GPU-hours, from the measured numbers

| job | at the design's bench settings (b32 × 48) | at the trainer's **current** micro-batch 64, real sentence length — *what you would actually get tonight* | at micro-batch **512**, real sentence length (recommended change) |
|---|---|---|---|
| **M on 1.2B tokens** (the planned S1) | 9.9 h | **≈ 28 h** | **≈ 3.9 h** |
| **L on ~2B tokens** | 24.2 h | **≈ 69 h** | **≈ 13.4 h** |
| **XL on ~4B tokens** | 79.8 h | **≈ 193 h** | **≈ 59 h** |

M on 1.2B at micro-batch 64 is measured end to end in the real training loop (12,022 tok/s
→ 27.7 h), no modelling involved. Every other cell in the middle and right columns is a
benchmark measured at that exact batch and at length 12 (the corpus's real sentence length,
mean 10.5 + 2 framing pieces), multiplied by the measured real-loop factor of 0.83. The
left column is the raw benchmark at the design's own `length 48`, which no real batch in
this corpus will ever look like.

### Does the design's "≈ 9–10 GPU-hours" still hold?

**As written, no.** Two separate corrections, pulling opposite ways:

1. **The 15-TFLOPS planning figure is optimistic for M at these settings.** Measured M is
   **5.28 TFLOP/s** at batch 32 × 48 and 10.6 at batch 64 × 48 — a third to two-thirds of
   the assumption. Only L and XL reach or pass 15 TFLOP/s (9.8 / 15.0 at batch 32, 18.7 /
   25.7 at batch 64); the card does reach ~25 TFLOP/s, but only on the big matrices, which
   is exactly what §2.4's "optimistic 25" said.
2. **The real bottleneck is not FLOPs at all, it is 10-token sentences at micro-batch 64.**
   Run as the README currently specifies, S1's M job is **≈ 28 GPU-hours, not 2.8** — a
   night becomes most of a week.

The design's total of ≈ 9.2 h for *everything* (S1 autoencoder + thinker + S2 + the
comparison model + S0) therefore does **not** hold at the current settings; the same
arithmetic on the measured real-loop rate lands near **35–40 h**.

**It is recoverable, and cheaply.** Raising `--micro-batch` from 64 to 512 was measured at
**7.1× the throughput** for M at the real sentence length (15,804 → 104,045 tok/s on the
bench; ≈ 12,000 → ≈ 86,000 tok/s once the real loop's 0.83 is applied), which puts the S1
autoencoder at **≈ 3.9 h** and the design's overall ≈ 9–10 h back within reach — with peak
memory 3.3 GB, comfortably inside 16 GB. Going further to 1024 buys almost nothing (107,364
tok/s) and doubles the memory. The learning rate and warmup would need re-tuning for the
larger batch, so this is a recommendation to Ben, not something I changed. **Nothing long
was started.**

---

## 6. What I changed

**On BensPC (the copies in `C:\Users\benja\talker24\scripts\`, not the repo):** three
one-place device fixes, without which *no* CUDA run is possible at all. Each is commented
in place with `BENSPC-S0 PATCH`. They are bugs on any CUDA machine, not Windows quirks.

| file | what was wrong | fix |
|---|---|---|
| `fable_talker24_model.py`, `perturb_gist` | the trainer's RNG is `torch.Generator(device='cpu')` and was handed to `torch.randn(device='cuda')` → `RuntimeError: Expected a 'cuda' device type for generator but found 'cpu'` **at step 1 of every CUDA run** | draw on the generator's own device, then `.to(gist.device)` — which keeps the random stream bit-identical to the Mac CPU run |
| `fable_talker24_train.py`, `evaluate` | `IV.thoughts_from_turns(model, turns)` left `device=None`, so CPU tensors met a CUDA model | pass `device=device` |
| `fable_talker24_interventions.py`, `set_act` | `torch.full(...)` defaulted to CPU, so the one-hot act could not be written into a CUDA thought | add `device=thought.device` |

Patched-file sha256 on the box: model `b436825edf75eb60c9de3730fed307535792e0eb9ec7da5f78a1b06deb5c79bd` ·
train `171657e10e56d9b352570e016a34bf8426e3f01e23af45c82eae0acf8e7634aa` ·
interventions `16c3f61c85a5fe73ecf6fe31acc9e0bf8f0fabf1196248261875db2f9d2e4110`.
**The repo copies were not edited.** They still need these three fixes before any GPU run.

**In the worktree:** one new file, `artifacts/fable-talker24-20260920/run_s0_benspc.ps1` —
the corrected form of README-S0.md §3's PowerShell block (README-S0.md itself was not
edited). Three things in that block are wrong for this box: the `.venv` interpreter does not
exist; `$out` is never created, so `--json "$out\throughput.json"` fails; and `kill-test` is
presented as the GPU kill/resume test although `kill_test()` hard-codes `--device cpu` in
its `common` list and therefore can never touch the GPU. The new script fixes all three and
adds an explicit CUDA kill/resume arm alongside the built-in CPU one.

## 7. Left unverified

* `atomic_save` under a crash *during* a checkpoint write — no OS-level hard kill exists on
  Windows, so only the `os._exit(137)` path was exercised (§4).
* **L and XL were never put through the real training loop** — only benchmarked. Their
  hours carry the real-loop factor measured on M (0.83), which is an assumption for them.
  That factor is itself only good to ±20 %: two runs of the same M 64×12 bench point
  returned 13,089 and 15,804 tok/s.
* The design's total of ≈ 9.2 h covers S1 + S2 + the comparison model + S0. I re-quoted the
  S1-M job directly and scaled the rest; I did not re-cost each row of §2.4's table.
* Whether micro-batch 512 **trains as well as** it runs fast. Only its speed and memory were
  measured; no model was trained at that batch size, and the LR/warmup would need re-tuning.
* Everything S1 and beyond: one seed, minutes of training, no conversation, no fluency.
* `pool` mode, L3, and builders 1 and 2's own test suites — unchanged from the audit's §7.
* The failed `slot_swap` mark is measured but not diagnosed; the subject/object pointers not
  reaching the mouth at all (0.000 both) is the single most interesting thing S0 turned up.

## 8. State the box was left in

No process of mine is running (`Get-Process python` empty, no `run_s0_benspc` PowerShell).
GPU back to 450 MiB / 0 % — the same idle desktop usage as before. `ScoutLlamaServer` still
`Disabled`, never touched. Nothing installed. `C:\Users\benja\talker24\` (1.73 GB) left in
place with the verified data, the patched scripts, every checkpoint and
`run_s0_benspc.ps1`, ready for the next run.
