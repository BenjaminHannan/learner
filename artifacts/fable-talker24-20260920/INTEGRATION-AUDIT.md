# INTEGRATION AUDIT — talker 24, the three builds meeting for the first time

Run on 2026-09-20/21 on the Mac (CPU only, `OMP_NUM_THREADS=1`) by an auditor who wrote
none of the three pieces. Everything below is measured, not read off a docstring.

**VERDICT: READY-FOR-S0 = YES**, after four fixes in the build-3 files. Before the fixes
S0's `slots` and `thinker` stages would have trained on **synthetic stand-in turns**, and
the loader's output was **not reproducible between processes**.

---

## 0. What was run

| | |
|---|---|
| python | `cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B`, torch 2.14.0, numpy 2.5.3 |
| data | the real `shards/s0`, `shards/valid`, the real `dialogues/L1-test.jsonl` and `L2-test.jsonl`, and 4,000 freshly generated dialogues straight out of `fable_talker24_dialogues.py` |
| code under test | `fable_talker24_loader.py`, `fable_talker24_train.py`, `run_s0.sh`, `README-S0.md` (build 3) |
| not edited | `fable_talker24_data.py`, `fable_talker24_dialogues*.py`, `fable_talker24_parser.py`, `INTERFACE-data.md`, `INTERFACE-dialogues.md` — mismatches in those are **reported**, section 5 |

---

## 1. Part A — the real generator output through the real loader

6,000 dialogue records, **77,873 turns**, through `parse_v1_record` and `dialogue_batch`.
The expected labels were recomputed **independently** from the record JSON (not with the
loader's own helpers) and compared field by field.

| stream | records | parsed | failed | turns | longest user / reply, pieces |
|---|---|---|---|---|---|
| `L1-test.jsonl` (sealed) | 1000 | 1000 | 0 | 13,005 | 29 / 21 |
| `L2-test.jsonl` (sealed) | 1000 | 1000 | 0 | 12,996 | 21 / 21 |
| generated L1 `[50000:51000]`, m0 | 1000 | 1000 | 0 | 12,903 | 28 / 21 |
| generated L2 `[50000:51000]`, m0 | 1000 | 1000 | 0 | 13,105 | 22 / 21 |
| generated L1 `[50000:51000]`, pool/train | 1000 | 1000 | 0 | 12,932 | 31 / 21 |
| generated L1 `[50000:51000]`, pool/reserved | 1000 | 1000 | 0 | 12,932 | 31 / 21 |
| **total** | **6000** | **6000** | **0** | **77,873** | |

### Label disagreements: zero

| checked, both the user thought and the reply thought | disagreements |
|---|---|
| `act` → `HEARD_ACTS` / `REPLY_ACTS` index | **0** |
| subject code (m0 `symbol−52`; pool `code_pool.indices[slot]`) | **0** |
| object code **and** `kind` (`person` vs `value` → 4096 + symbol−12) | **0** |
| relation path → `friend`/`gift`/`prize`/`charm` = 1/2/3/4, `none` = 0 | **0** |
| the 8 flag numbers (`path_len` bits, speaker, three unknown reasons, `has_old_value`, not-teachable) | **0** |

No relation word outside M0's four ever appeared, in L1 **or** L2, so `RelationIds`' "next
free id" path was never taken and no run can drift its relation numbering.

### The other counts

| | L1 | L2 | gen L1 m0 | gen L2 m0 | gen pool/train | gen pool/reserved | total |
|---|---|---|---|---|---|---|---|
| `<unk>` tokens, user side | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| `<unk>` tokens, reply side | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| turns over the 48-piece cap | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| reply target holding a literal **name** | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| reply target holding a literal **value word** | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| reply turns carrying a copy action | 9,393 | 9,397 | 9,363 | 9,480 | 9,427 | 9,427 | 56,487 |
| user turns whose `old` the loader drops | 302 | 81 | 270 | 87 | 289 | 289 | **1,318** |
| reply turns whose `old` the loader drops | 843 | 821 | 794 | 854 | 833 | 833 | **4,978** |
| reply turns with a non-null `unknown_step` | 645 | 573 | 638 | 625 | 611 | 611 | **3,703** |
| capitalised words not in `world.people` | 77 | 51 | 70 | 48 | 60 | 60 | **366** |
| **reserved-half codes reaching a TRAIN batch** — *before* fix F1 | 154 | 102 | 140 | 96 | 120 | 120 | **732** |
| **reserved-half codes reaching a TRAIN batch** — *after* | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

The last row of the reserved count for `pool/reserved` is **45,918 after the fix, and that
is correct**: that stream is held-out *evaluation* data, whose whole point is that its codes
were never trained on. Before fix F2 it produced **zero** reserved codes — see F2.

### The bridge nobody owned, checked against builder 1's own tokenizer

The loader's pure-Python `BytePairEncoder` is the only thing that turns dialogue *text* into
*ids*; neither interface owns it, so it had never been checked against the real tokenizer.
Test: take real sentences out of `shards/s0`, decode them with builder 1's shipped
`shards/decode_numpy.py`, re-encode them with the loader's BPE, compare ids.

> **2,631 sentences round-tripped, 2,631 byte-identical, 0 differing.**

The bridge is sound. `tokenizer_meta.json`'s `specials` block also matches
`fable_talker24_model`'s `PAD…DOC = range(10)` exactly, id for id.

---

## 2. Part B — the trainer on real dialogues

### The bug that would have silenced S0

`TrainConfig.dialogue_split` defaults to `'train'`; `find_dialogue_file` looks for
`dialogues/train.jsonl`, `dialogues/train-test.jsonl`, `dialogues/dialogues-train.jsonl`.
**None of those exist and none ever will** — `INTERFACE-dialogues.md` §1 says training data
is not shipped as a file. `run_s0.sh` passed `--dialogues` but never `--dialogue-split`, so
`build_dialogues` fell straight through to `L.synthetic_dialogues`. Steps 3 and 4 of S0
would have run to completion, written a `result.json`, and reported
`dialogues: synthetic (…)` — honest, but useless.

### After the fix

| stage | steps | source string | loss |
|---|---|---|---|
| `slots` | 50, preset S, CPU | `1 shard(s) under …/shards + dialogues: generated L1[100000:100128] symbol_mode=m0 pool=train via fable_talker24_dialogues (REAL generator output)` | act 1.06→0.18, path 1.21→0.48, flags 0.37→0.06, subject ptr 0.64→0.04, object ptr 0.77→0.04, say 7.56→3.72 |
| `thinker` | 50, preset S, CPU | same | through-mouth 8.99→8.58, act 0.13 (small, as expected: the mouth is frozen and untrained) |

Every loss finite, every loss falling, and `"synthetic": false` in both `result.json` files.

### Checkpoint / resume

| test | result |
|---|---|
| stock `kill-test` (preset tiny, autoencode, real `SIGKILL` at step 18 of 40) | **BIT-IDENTICAL** |
| `slots` on **real generated dialogues**, preset S, killed at 17 of 40, resumed from `step-00000015.pt` | **BIT-IDENTICAL** (`26e1253228e0406d…`) |
| the same, with `PYTHONHASHSEED` deliberately different (0 / 1 / 2 across the three processes) | **BIT-IDENTICAL** — this is the test fix F1 exists for |

### The whole dry S0, end to end

`S0_DRY=1 bash run_s0.sh` — **7/7 steps, 0 failures, 2 min 26 s**, kill test
`BIT-IDENTICAL`, throughput S 2,234 tok/s and M 719 tok/s (Mac CPU, meaningless as a GPU
number). Every `source` string real:

* stages 1–4: `1 shard(s) under …/shards`
* stages 3–4 dialogues: `generated L1[100000:100512] … (REAL generator output)`, 6,749 turns
* step 6 held-out: `valid shards …`; thought exactness set:
  `…/dialogues/L1-test.jsonl`

The word `synthetic` appears in the log only inside the honesty warnings, never in a source
string. The S0 model marks are `NOT ALL MET`, which is right — this was 20 seconds of
training per stage.

---

## 3. What was fixed (build-3 files only)

### F1 — `fable_talker24_loader.py`: the unknown-name code was random and held out

```python
# before
code = ENT_RESERVED_MIN + (abs(hash(word)) % (ENT_POOL - ENT_RESERVED_MIN))
```

The generator emits, on purpose, UNCLEAR turns that name people the notebook never records
(*"both Hal's prize and Ada's prize are a whistle"*, *"write down Bram's gift as a ribbon and
Ada's prize as a coin"*). Those names are correctly absent from `world.people`. 366 of them
across the 6,000 records. The loader gave each one a code with two defects:

1. **It drew from the reserved half.** `ENT_RESERVED_MIN + …` is 3072–4095 — exactly the
   codes `SymbolTable`'s docstring says "the talker must never have seen". 732 reserved
   codes were reaching training batches, which would have quietly voided any later
   new-names evaluation.
2. **`hash()` is salted per process in Python 3.** Measured: the same file, read three
   times with different `PYTHONHASHSEED`, produced three different code arrays
   (`ac895ce3…`, `fb0c8dd2…`, `6067f2ab…`). That breaks §2.6's "the data order is a pure
   function of (seed, position)" and would have made any `slots`/`thinker` resume
   non-identical.

Fixed with `_unnamed_person_code`: `blake2b(word)` — stable across processes — folded into
0…3071, then advanced to the first code the dialogue's own people are not already using.
After the fix all three hash seeds give `07c74ed9…` and the reserved count is 0.

### F2 — `fable_talker24_loader.py`: `pool='reserved'` landed in the trained half

`INTERFACE-dialogues.md` §7 says `code_pool.indices[slot]` is a row of
`fable_newnames21.pool_subset(pool, which)` — an index **into the subset**, not an absolute
0…4095 code. The reserved subset has 1,024 rows, so its indices run 0…1023 and
`_person_code` returned them unchanged. Measured on generated `pool/reserved` data:
**0 of 928 people codes landed in the reserved half; all 928 landed in the trained half.**
Held-out evaluation data would have been indistinguishable from training data.

`_person_code` now maps a reserved subset row to `3072 + row % 1024` and a train subset row
to `row % 3072`. After the fix: **928 of 928 in the reserved half.** This is latent for S0
(m0 mode only) and blocking for M1.

### F3 — `fable_talker24_loader.py` + `fable_talker24_train.py`: stream the training data

New `L.generate_dialogues(root, split, n, start, symbol_mode, pool)` calls
`fable_talker24_dialogues.Generator.dialogue(i)` directly, parses each record and throws it
away — **no file on disk**. Measured: 2,048 dialogues → 26,546 parsed turns in **1.4 s**;
512 → 6,749 turns in 0.4 s. That is cheaper than reading the equivalent 37 MB of JSON back,
and it answers design gap D4 (18 GB) outright.

`build_dialogues` now resolves, in order: a real file named by `--dialogue-split` → the
generator → synthetic. New flags: `--generate-split`, `--dialogue-start`, `--symbol-mode`,
`--code-pool`, `--synthetic-dialogues`, `--allow-sealed`.

**The leak this closes.** `INTERFACE-dialogues.md` §9 guarantees dialogue *i* is a pure
function of `(namespace, split, i)`, and `SEALED-SPLITS.md` seals L1/L2 indices **0…999**.
The contract's own example is `generate --split L1 --n 200000 --out train.jsonl`, with no
`--start`: **that reproduces the entire sealed test set as the first 1,000 training
dialogues.** `generate_dialogues` refuses any `start < 1000` with a `ValueError` and defaults
to 100,000; `build_dialogues` additionally refuses to train on `L1`/`L2` without
`--allow-sealed`.

### F4 — `fable_talker24_train.py`: every `result.json` now says what the turns were

`Trainer.data_note()` adds `dialogues: {source, turns, parse_counters, synthetic}`. The
loader's own counters (`name_not_in_world`, `symbol_out_of_range`, `copy_without_span`, …)
now land in the result file instead of scrolling past, so a silent parse regression on the
GPU box shows up in the artifact.

`run_s0.sh` passes `--dialogue-split train --generate-split L1 --symbol-mode m0` and a
dialogue count (512 dry / 4,096 real) explicitly, so the behaviour is chosen, not defaulted.
`README-S0.md` gains a file-and-size checklist (§4a) and a Windows-differences section.

### Hashes after the fixes

| file | sha256 |
|---|---|
| `scripts/fable_talker24_loader.py` | `abc2e25584042c5d5c2a28583ffee4de63d7279013a036c9f960d60996143527` |
| `scripts/fable_talker24_train.py` | `8b24b45b8927093817bbb6fbb93dbe9a8d18db598155310caabcad2cd27a50b7` |
| `artifacts/fable-talker24-20260920/run_s0.sh` | `92f30bc92ccfc8c04b1cea616ab96fc3a841a82becd7cc96e26239ec1ca1b036` |
| `artifacts/fable-talker24-20260920/README-S0.md` | `2275f48d3c3d3b64fc1cfc95029f56c9f21724d8403065881eb151ea3c957e3b` |

### Test suites re-run after the fixes

| suite | result |
|---|---|
| `tests/test_fable_talker24_train.py` | **ALL 140 CHECKS PASSED** (16.8 s) |
| `tests/test_fable_talker24_model.py` | **ALL 85 CHECKS PASSED** (12.5 s) |
| `tests/test_fable_talker24_data.py` | 30 passed, **5 failed** — all five are `ModuleNotFoundError: tokenizers`. Pre-existing, builder 1's suite, untouched by this audit; builder 1 built the shards inside its own `artifacts/…/venv`. |
| `tests/test_fable_talker24_dialogues.py` | **could not run** — `import pytest`, and pytest is not in this environment. Pre-existing, builder 2's suite, untouched. |

---

## 4. Part C — what must exist on BensPC

Nothing may be installed there, and nothing below needs to be.

**Packages imported by the S0 path:** `torch` (CUDA build) and `numpy`. Everything else is
standard library — `argparse dataclasses hashlib importlib.util inspect json math os
pathlib random re signal subprocess sys time`. Verified by import trace: **no
`tokenizers`, no `datasets`, no `pyarrow`, no `pytest`.** The dialogue generator that F3
pulls into the training path is pure standard library too (checked by module trace: it adds
only `fable_talker24_dialogues`, `_dialogues_frames`, `_parser`).

**Files to copy — 7 scripts + ~166 MB of data:**

| what | path | bytes |
|---|---|---|
| model | `scripts/fable_talker24_model.py` | 47,160 |
| loader | `scripts/fable_talker24_loader.py` | 49,080 |
| trainer | `scripts/fable_talker24_train.py` | 44,460 |
| interventions | `scripts/fable_talker24_interventions.py` | 18,324 |
| generator | `scripts/fable_talker24_dialogues.py` | 90,856 |
| generator frames | `scripts/fable_talker24_dialogues_frames.py` | 35,220 |
| generator parser | `scripts/fable_talker24_parser.py` | 27,109 |
| training shard | `shards/s0/s0-00000.{tokens.u16, ents.u16, sents.u32, docs.u32, json}` | 132,006,952 |
| held-out shard | `shards/valid/valid-00000.*` (step 6 needs it) | 22,222,760 |
| tokenizer export | `shards/tokenizer_vocab.json` + `tokenizer_merges.txt` + `tokenizer_meta.json` | 244,116 |
| the name rule | `dialogues/LEXICON.json` | 4,280 |
| thought-exactness set | `dialogues/L1-test.jsonl` | 18,018,730 |

**Not** needed: `shards/train/` (170 MB), `shards/parts/` (192 MB), `shards/tokenizer.json`
(the HuggingFace form, only the Mac's shard builder reads it), `dialogues/L2-test.jsonl`,
`runtime.local.json` (a Mac-only shim; `fable_talker24_model.py` tries the ordinary
`import torch` first).

**Unix-only things in `run_s0.sh` — it cannot run on BensPC at all**, which README §3
already says; these are the specific reasons, so nobody tries:

| line | why it fails under Windows/PowerShell |
|---|---|
| `#!/usr/bin/env bash`, `set -u -o pipefail` | no bash unless Git Bash or WSL is installed, which it may not be |
| `HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` | `BASH_SOURCE` is bash-only |
| `UVPY="$HOME/.local/share/uv/python/cpython-3.12.14-**macos-aarch64**-none/…"` | the default interpreter path is hard-coded to **macOS**; under Git Bash it would silently fall back to `python3`, which is probably not the CUDA env |
| `date +%s`, `date -u '+%Y-%m-%d %H:%M:%SZ'` | PowerShell's `date` is `Get-Date`; the flags do not exist |
| `… \| tee -a "$LOG"` with `${PIPESTATUS[0]}` | `PIPESTATUS` has no PowerShell equivalent; `$LASTEXITCODE` through a pipe means something else |
| `ls -1 "$S0_OUT"/autoencode/step-*.pt \| tail -1` | no `tail` |
| `$((ELAPSED/60))`, `exit $(( FAILURES > 0 ? 1 : 0 ))` | bash arithmetic |
| `printf '\n=== %s ===\n'` | `printf` collides with PowerShell aliasing |

**Signals / `kill`.** `run_s0.sh` never calls `kill`. The kill test does it from inside
Python: `os.kill(os.getpid(), signal.SIGKILL)` guarded by `hasattr(signal, 'SIGKILL')`.
Windows has no `SIGKILL`, so it falls to `os._exit(137)`. That still skips every checkpoint,
`atexit` hook and buffer flush, so the *resume* is tested just as hard, and
`kill-test.json` simply reports `killed_signal: 137` instead of `-9`. It is **not** an
OS-level hard kill, so it does not exercise a crash *during* a checkpoint write —
`atomic_save`'s temp-file-then-`os.replace` is designed for exactly that case and remains
**unverified on Windows**. `os.replace` is atomic on NTFS within a volume, so the design is
sound; it just has not been proven there.

---

## 5. Mismatches in builders 1 and 2 — reported, not edited

1. **`reply.thought.*.span` does not index `reply.surface`.** `INTERFACE-dialogues.md` §6
   says "In a reply thought, `span` is into `reply.surface`". Measured on `L1-test.jsonl`:
   **6,172 of 6,361 reply object spans and 1,356 of 9,485 reply subject spans are wrong** —
   they are the *user* turn's spans, copied over. Example: reply surface
   `"i have written it down: Nils's prize is a feather."` carries `object.span = [17, 24]`,
   which is `" down:N"`; the correct span is in `copy[1].surface_span = [42, 49]`.
   **Impact today: none** — nothing in the loader reads a reply thought's span, and
   `copy[].surface_span` is correct. **Impact later:** any evaluation that scores the reply
   pointer from `reply.thought.*.span` will be wrong. User-side spans are perfect:
   16,148 of 16,148 correct.
2. **The contract's own training-data recipe reproduces the sealed test set.**
   §1 shows `generate --split L1 --n 200000 --out train.jsonl`; §9 guarantees dialogue *i*
   is a pure function of `(namespace, split, i)`; `SEALED-SPLITS.md` seals indices 0…999.
   Nothing in either document reserves an index range for training. Worked around in the
   loader (F3), but the interface should say so.
3. **`--from` vs `--start`.** §9 promises `generate --split L1 --n 1000` and
   `--from 500 --n 500` agree. The CLI flag is `--start`; `--from` does not exist.
4. **`symbol_mode` / split names.** §3's record shape suggests a `train` split; the
   generator accepts only `L1` and `L2`. The loader now treats `train` as "generate L1".
5. `tokenizer_meta.json` says `"lowercase": true` while `tokenizer.json` has
   `"normalizer": null` — i.e. builder 1 lower-cases the text *before* the tokenizer, and
   the loader must do the same. It does, driven by the meta flag. Worth a line in
   `INTERFACE-data.md` so the next consumer does not read `normalizer: null` and skip it.
6. Minor, build 3, left alone deliberately: `parse_v1_record` passes its `counters` dict as
   `_get`'s `filled` argument, so a missing `user`/`reply` key would be counted under the
   bare key `'user'`. Never fired on 77,873 turns.

---

## 6. Part D — the four design gaps builder 3 flagged

### D1 — `<OLD>` has no slot in the 416-number thought

**Real problem, for S1, not for S0.** The thought is `act(8) + subject(48) + path(48) +
object(48) + flags(8) + gist(256) = 416` and there is no third code field, so
`_slot_code(thought['old'])` is computed and then **thrown away** — `Turn` has no `old_code`
and `dialogue_batch` emits no `old` label. Measured: **1,318 user turns and 4,978 reply
turns carry a non-null `old`**, and **534 of 13,005 L1 reply texts (4.1 %) contain the
literal `<OLD>` marker** that the mouth is trained to emit. The printer has `field: "old"`
in `copy[]` and nothing to read, so every one of those replies would print the raw string
`<OLD>` — the loader's decoder deliberately makes that visible rather than dropping it.

S0's marks (reconstruction, whole-thought exactness, slot swap) do not touch `old`, so S0 is
unaffected. **Smallest fix, before S1:** `flags.has_old_value` is already a bit in the
thought and is already learned; add a **third pointer** (`old_pointer`, an exact copy of
`object_pointer`) and widen the thought by 48 to 464, or — cheaper and no wider — make the
printer resolve `<OLD>` from the *notebook's* `replaced.object_symbol`, which is where the
old value actually lives (`notebook.replaced` is populated on every correction). The second
option costs nothing in the model and is the honest one: the old value **is** a notebook
fact, not something the ears should have to hold.

### D2 — `unknown_step` is not carried

**Not a real problem at S0 or S1.** Measured: `unknown_step` is non-null on 3,703 reply
turns, but `chain_broke` — the only reason §6 says it qualifies — occurs **only with
`unknown_step == 2`** in the whole L1 set (120 turns, 19 distinct wordings, 6 frame ids),
because M0's paths are at most 2 hops. No reply wording names the step: they say *"one of
the steps is missing"*, *"a step in the middle is missing"*, *"a step for `<SUBJ>` is
missing"*. So given `flags.unknown_chain_broke`, `unknown_step` carries **zero extra
information** today. **Smallest fix, only if 3-hop questions are ever generated:** reuse the
two `path_len` bits' spare capacity or the single remaining spare flag to encode the step;
nothing needs to move now.

### D3 — preset L is width 576, the design says 640

**Not a problem.** The design's own two numbers ("≈85M" and "width 640") are arithmetically
inconsistent; `fable_talker24_model.py` ships **both** (`L` = 576 → 87.6M, `L640` = 640 →
107.2M) and says why in a comment. S0 only *benchmarks* L; nothing trains on it. The choice
stays Ben's. **Smallest fix: none — just pick one when S1 is planned.**

### D4 — 18 KB per record, so 1M dialogues = 18 GB

**Was a real problem; fixed.** See F3. Records are now generated in memory and never
written: 2,048 dialogues → 26,546 turns in 1.4 s, so a stage can re-draw a fresh block
whenever it wants. Because a record is a pure function of `(namespace, split, index)`, a
resumed run re-draws byte-identical records, which the kill test above confirms.

**One thing this does not yet do:** the block is drawn **once** at `Trainer.__init__` and
`_sample_turns` cycles through it, so a long run sees the same `--synthetic-dialogues`
dialogues over and over rather than a million distinct ones. At 4,096 dialogues that is
~53,000 turns, far more than the 20 minutes of S0 can consume, so it does not matter for S0.
**Smallest fix, before S1:** make `_sample_turns` advance a block index and call
`generate_dialogues` again when it runs off the end — about eight lines, and the block index
belongs in the checkpoint beside `stream.position`.

---

## 7. What is still unverified

* **Nothing GPU.** No CUDA run, no bf16 autocast path, no Windows path, no `torch.compile`
  absence check on the box. Every number here is Mac CPU.
* **Throughput.** S 2,234 tok/s and M 719 tok/s on this CPU say nothing about the
  60,000 tok/s gate in §2.4. The XL preset was never even instantiated (the dry run
  benchmarks S and M only), so its 16 GB fit at batch 32 × length 48 is unknown.
* **`atomic_save` under a real Windows crash** — see §4.
* **L3.** `dialogues/L3/` is empty by design; nothing about out-of-grammar wording was
  tested and nothing can be until Ben types his 100 sentences.
* **`pool` mode end to end.** F2 is verified at the code level (928/928 land in the reserved
  half) but no model has been trained in pool mode, and the pool-mode path pulls in
  `fable_newnames21` (which needs torch) at generation time — fine on the GPU box, untested.
* **Builder 1's own test suite** (5 checks) and **builder 2's** (all of it) could not run
  here for want of `tokenizers` and `pytest`. Neither gap is caused by, or affects, the
  training path.
* **The S0 model marks themselves.** They came out `NOT ALL MET` after 20 seconds of
  training per stage, which is the expected answer to a question nobody asked yet.
