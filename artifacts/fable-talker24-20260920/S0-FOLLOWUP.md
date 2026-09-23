# S0 follow-up — the three CUDA fixes landed, and what the 0.000 slot swap actually was

Written 2026-09-20, after `s0-benspc/S0-REPORT.md`. Task 1 changes the repo; task 2 changes
nothing (diagnosis only, as instructed).

---

## Task 1 — the three device fixes are now in the repo copies

All three were patched only on `C:\Users\benja\talker24\scripts\` during S0 (each marked
`BENSPC-S0 PATCH` there). They are now in the worktree, written to be device-agnostic —
they work on `cpu`, `mps` and `cuda` — and the CPU random stream is unchanged.

| file | site | what was wrong | fix |
|---|---|---|---|
| `scripts/fable_talker24_model.py` | `perturb_gist`, line 723 | the trainer's RNG is `torch.Generator(device='cpu')`; `torch.randn`/`torch.rand` refuse a generator whose device differs from the target, so every non-CPU run died at step 1 | draw on `generator.device`, then `.to(gist.device)`. When they already agree (the CPU path) `.to` is a no-op |
| `scripts/fable_talker24_train.py` | `evaluate`, line 692 | `IV.thoughts_from_turns(model, turns)` left `device=None`, i.e. CPU tensors meeting a non-CPU model | pass `device=device` (already a parameter of `evaluate`) |
| `scripts/fable_talker24_interventions.py` | `set_act`, line 99 | `torch.full(...)` defaults to CPU, so the one-hot act could not be written into a non-CPU thought | `device=thought.device` |

### sha256, old → new

| file | before | after |
|---|---|---|
| `scripts/fable_talker24_model.py` | `9ed26d5457ac818fa2775d409920675b1b14f9fe3fc25844751f710bf8e6092b` | `0614f95355a4cb39b8405824cf7bb41ff41bed19a62d2040fe1f33559951846e` |
| `scripts/fable_talker24_train.py` | `8b24b45b8927093817bbb6fbb93dbe9a8d18db598155310caabcad2cd27a50b7` | `ced66c17cceb72b6e1cfa05adcf6fb4f5d48e0b4469db14af53d93c4bc0d4f6d` |
| `scripts/fable_talker24_interventions.py` | `14dabaabbdd6aa48ee799d4677445619f2b8c9a901a7dec95bdacdadf415157b` | `5d72f9ebc76d332b6629d5f1d50e7e85add61ff0e8651cbd354530072c7fbf13` |

The repo text is not byte-identical to the BensPC copies (the comments are re-worded and
say "S0 on BensPC" instead of carrying the `BENSPC-S0 PATCH` marker), but the code is the
same in all three places.

### Checks run, on this Mac, CPU, `OMP_NUM_THREADS=1`

* `tests/test_fable_talker24_model.py` — **ALL 85 CHECKS PASSED** (12.5 s)
* `tests/test_fable_talker24_train.py` — **ALL 140 CHECKS PASSED** (16.9 s)
* `tests/test_fable_talker24_data.py` — **30 passed, 5 failed**. All five failures are
  tokenizer tests (`test_plain_vocab_export_matches_the_native_tokenizer`,
  `..._shipped_decoder_matches_the_real_tokenizer`,
  `..._produced_tokenizer_has_the_promised_special_ids`,
  `..._encoding_the_same_unit_twice_is_byte_identical`,
  `..._a_finished_part_is_reused_instead_of_recomputed`) and they fail because the
  `tokenizers` package is not importable in this environment. `fable_talker24_data.py`
  was not touched. **Pre-existing, unrelated.**
* `tests/test_fable_talker24_dialogues.py` — **could not run**: it `import pytest` at line
  26 and pytest is not installed here. Not run, not affected by any edit above
  (`fable_talker24_dialogues.py` was not touched).

Two extra probes:

* **CPU bit-identity of (a)**: `perturb_gist` under the new code vs. the old code path,
  same seeded CPU generator → `torch.equal(...) == True`.
* **Device-agnostic**: on `mps`, `perturb_gist` with a CPU generator, `set_act`, and
  `thoughts_from_turns(device='mps')` all return `mps:0` tensors. (No CUDA device here;
  the CUDA path is the one BensPC already ran.)

---

## Task 2 — the slot-swap diagnosis: **(i), the scorer is wrong**

**Verdict: (i).** `subject 0.000` and `object 0.000` on the autoencode checkpoint are not
measurements. They are the mean of an **empty list**. Not one subject or object sample was
ever run. The architecture is fine and the model was never asked the question.

### The arithmetic that gives it away

`s0-marks.json → interventions.slot_swap`:

```
{"score": 0.921875, "n": 64,
 "by_field": {"subject": 0.0, "object": 0.0, "relation": 0.921875},
 "diagnostics": {"copy_words_unchanged": 0.0, "copy_resolution_changed": 0.0,
                 "relation_words_changed": 0.921875}}
```

`slot_swap_test` appends **exactly one** relation result per thought and **up to two** copy
results per thought. `evaluate` feeds it 64 turns. `relation_words_changed = 0.921875 =
59/64`, so the relation arm has 64 results — and `n` is **also 64**. There is no room for a
single subject or object result. `copy_resolution_changed = 0.0` confirms it: that flag is
computed from the thought and the symbol table alone and is *always* true when it runs
(the `slots` checkpoint reports it as exactly `1.0`), so a `0.0` can only be an empty mean.

Compare `s0-marks-slots.json`, where the pointers *had* been trained: `n = 142` = 64
relation + 47 subject + 31 object, and `copy_resolution_changed = 1.0`.

### The three lines that do it

`scripts/fable_talker24_interventions.py:151-153`

```python
old = int(symbols.nearest(M.field_of(base[0], field)))
if old < 0:
    continue
```

`scripts/fable_talker24_interventions.py:249-251`

```python
def _mean(values):
    values = list(values)
    return float(sum(values)/len(values)) if values else 0.0
```

`SymbolTable.nearest` (`scripts/fable_talker24_model.py:344`) returns **-1** for any vector
that is not a bit-exact table row. When `Pointer` selects its NULL slot
(`fable_talker24_model.py:430, 435-439`) the routed code is the **zero vector**, which is
not a table row — so `nearest` returns -1, the sample is `continue`d, and `_mean([])`
silently reports `0.0` instead of "not measured". The autoencode stage
(`fable_talker24_train.py:371 loss_autoencode`) has no pointer supervision at all, so its
pointers sit on NULL for every turn; the `slots` stage (`loss_slots`, line 378) is the
first that trains them, which is exactly where the field counts become non-zero.

### Reproduced, small, on this Mac

Untrained `tiny` Talker, 16 real-shaped turns, ears run with the code ids blanked to
`ENT_NONE` so the pointer must take NULL — the same condition the autoencode checkpoint
converged into:

```
A subject ids: [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
A slot_swap: 0.375 n= 16 {'subject': 0.0, 'object': 0.0, 'relation': 0.375}
A diagnostics: {'copy_words_unchanged': 0.0, 'copy_resolution_changed': 0.0,
                'relation_words_changed': 0.375}
```

`n == 16 ==` the number of thoughts, subject and object `0.0`, both copy diagnostics `0.0`
— the same fingerprint as `s0-marks.json`, on an untrained model that was never asked.

### (ii) is false — the path exists

`Mouth.prefix = nn.Linear(THOUGHT_DIM, ...)` (`fable_talker24_model.py:542`) consumes the
**whole** 416-number thought, and `SLICES['subject'] = slice(8, 56)` is inside it. Swapping
the subject code and re-running the decoder moves the logits:

```
B mouth logits change under a subject swap: max|d| = 0.1697
B prefix reads full thought: 416 == THOUGHT_DIM 416
```

### (iii) is a live but separate question

On the `slots` checkpoint the copy arms *did* run (78 samples) and mostly failed:
`copy_words_unchanged = 0.179`. That is a genuine model failure — the mouth re-words the
sentence when a pointer changes, which is the thing the test exists to catch — but it is a
result about a 3-minute checkpoint whose mouth that stage does not train, and it is a
different number from the `0.000` in the headline.

### The second, deeper problem — even when it runs, the copy arm barely tests the model

Reply templates spell the slot as a literal placeholder
(`fable_talker24_dialogues.py:343`, `"ok. <SUBJ>'s {RPATH} is a <OBJ>."`), and
`Mouth.speak` bans `<ENT>` outright — a name has **no** route into the token stream. So the
token stream *cannot* change under a pointer swap, and the scorer rightly requires
`out == base_out`. But the other half of the pass condition,

`scripts/fable_talker24_interventions.py:159-160`

```python
resolution_changed = (env.resolve(action) == new
                      and base_env.resolve(action) == old)
```

is computed from the swapped thought and the symbol table with **no model in the loop at
all**. The only model-dependent half left is "nothing moved". A model that never emits a
`<SUBJ>` or `<OBJ>` token scores **1.0** on this arm. The test never checks that the copy
action was emitted, nor that the *rendered* sentence now carries the new name.

### Smallest fix

Two small, local edits in `slot_swap_test`, nothing else:

1. **Stop reporting "not measured" as 0.000.** Count the `continue`s, return `None` (not
   `0.0`) for a field with no samples, report `n_subject` / `n_object` beside `by_field`,
   and make the `slot_swap` mark **fail loudly as "not measured"** when either count is
   zero rather than silently scoring 0. (`_mean` should take an explicit `empty=None`.)
2. **Put the model back in the copy arm.** Before swapping, require that the base decoding
   contains the field's copy action (`M.SUBJ` / `M.OBJ`); a turn without it is *ineligible*
   and is counted as such, never as a pass. Then compare the **rendered** strings via
   `M.render(tokens, env, names)` (`fable_talker24_model.py:797`), not just the token ids.

### What a valid slot-swap test looks like

* Run it on a checkpoint whose pointers are trained — `slots` or `thinker`, **never**
  `autoencode`. The autoencode number should be reported as "not applicable", not as 0.000.
* Eligibility: the base decoding emits that field's copy action. Report eligible-n; if it
  is 0, the mark is *unmeasured* and the run is not gradeable on it.
* Pass = (a) the emitted token stream is bit-identical, **and** (b) the rendered sentence
  differs from the base rendering in exactly the one name at that copy action's position
  and nowhere else, **and** (c) that name is the newly-swapped code's name.
* Keep the relation arm as it is — `0.922` there is a real number about a real model, and
  it is the only part of the S0 slot-swap line worth quoting today.

### One line for the record

`S0-REPORT.md §3` says the subject/object `0.000` is "a real signal, not noise, and the
thing to re-measure first in S1". It is neither signal nor noise: **the measurement never
happened.** The re-measure is still the right next step, but on the `slots` or `thinker`
checkpoint and with the scorer above.

---

## Scorer fix — implemented 2026-09-20, after the diagnosis above

Changes are confined to `scripts/fable_talker24_interventions.py` and its test file. No
training script, model file or checkpoint was touched.

### 1. An unmeasured score is `None`, and the mark fails loudly

`_mean(values, empty=None)` now returns **`None`** on an empty list, never `0.0` — and
that is the only `_mean` in the file, so every intervention inherits it. `slot_swap_test`
returns `score=None`, `measured=False`, `not_measured=['object', 'subject']`, a plain-words
`note`, and per-field counts:

```
counts = {n_relation, n_subject, n_object, n_skipped_null_pointer, n_skipped_no_copy_token}
```

The new `_mark(score, mark, detail)` turns a `None` score into
`{'score': None, 'passed': False, 'measured': False, 'note': 'NOT MEASURED: …'}` — it can
never pass and can never be read as a zero. `ignores_thought_signature` strips `None`
metrics out before testing its clauses and reports them under `not_measured`, so an
unmeasured number can neither fire a clause nor clear one.

**The other three interventions were checked against `s0-benspc/s0-marks.json`, and all
three had `n > 0`:** gist-shuffle `n = 64`, gist-zero `n = 64`, thought-replace `n = 64`
(reconstruction `n = 64` too). **Their 1.000 scores are real measurements, not empty
means.** Only the slot-swap copy arms were empty. A regression check in the test file now
asserts that from the file itself.

### 2. The copy arm now tests the model

* A turn is **eligible** only if the base decoding actually emitted that field's copy
  action (`M.SUBJ` / `M.OBJ`). A mouth that never says `<SUBJ>` is no longer silently
  credited with a pass — the turn is counted under `n_skipped_no_copy_token`.
* A turn is **skipped** when the pointer sits on NULL (`nearest` → -1), counted under
  `n_skipped_null_pointer`.
* **PASS = the emitted token stream is bit-identical AND the rendered sentence
  (`M.render`) is the base sentence with that one name replaced by the swapped code's
  name** — `after == expected and after != before and names[new] in after and
  names[old] not in after`. `placeholder_names(symbols)` supplies a synthetic surface
  string per code when no lexicon is passed; a real `names=` map can be passed instead.
* The model-free `resolution_changed` shortcut is **out of the pass condition**. It
  survives only as the diagnostic `copy_resolution_changed_MODEL_FREE`, renamed so that
  nobody mistakes it for evidence about a model again.

### 3. An `autoencode` checkpoint is refused

`slot_swap_test(..., train_stage='autoencode')` raises `ValueError` naming the stage and
saying why (that stage never supervises the pointer heads). `'slots'` and `'thinker'` are
allowed; `None` (unknown) still runs. `run_interventions` takes and forwards
`train_stage`, and the `report` CLI reads it from `payload['train_config']['stage']`.

**Still to wire (outside the one-file scope of this change):** `fable_talker24_train.py`'s
`evaluate` calls `run_interventions` without `train_stage`, so the *explicit* refusal does
not fire on that path. It is a one-line addition
(`train_stage=train_cfg.get('stage')`). Even unwired, that path can no longer report a
false 0.000 — it now reports NOT MEASURED with the counts.

### sha256, old → new

| file | before | after |
|---|---|---|
| `scripts/fable_talker24_interventions.py` | `5d72f9ebc76d332b6629d5f1d50e7e85add61ff0e8651cbd354530072c7fbf13` | `f7ca79a490ed1660dfbfe4d3317199b6b8e974aaa363eda1c2380351e250012e` |
| `tests/test_fable_talker24_model.py` | `0211aee052008248bf168bb979e5bee2d4c68c9536ee768e1c39e32d58673b6b` | `badb083f73178850cfb49dd2d72e57a890b893be98c50abf0e91164d5d1a1fd4` |

(The "before" hash of the test file is reconstructed by reversing this change; that file is
untracked, so git holds no earlier copy. The reconstruction is 471 lines, matching the
file's length before the edit.)

### Tests — this Mac, CPU, `OMP_NUM_THREADS=1`

* `tests/test_fable_talker24_model.py` — **ALL 98 CHECKS PASSED** (13.0 s), up from 85:
  **13 new checks** in a new `slotswap` group, plus one existing check relaxed to accept
  `None` as NOT MEASURED.
* `tests/test_fable_talker24_train.py` — **ALL 140 CHECKS PASSED** (19.3 s), unchanged.
* `python scripts/fable_talker24_interventions.py toy --n 8` still runs end to end.
* `test_fable_talker24_data.py` (30 passed / 5 failed, missing `tokenizers`) and
  `test_fable_talker24_dialogues.py` (needs pytest) are as recorded above — untouched by
  this change.

The 13 new checks, by the three things they pin:

1. `_mean([]) is None`; a mouth that never emits the copy token gives
   `by_field['subject'] is None`, `score is None`, `measured False`,
   `n_skipped_no_copy_token == 4`, a note containing "NOT MEASURED"; and `_mark(None, …)`
   has `passed False`.
2. A scripted mouth that really copies passes both copy fields; a scripted mouth that
   re-words the sentence on a pointer swap **fails** it, while
   `copy_resolution_changed_MODEL_FREE` still reads `1.0` — proving the model-free flag is
   no longer doing any of the work.
3. `train_stage='autoencode'` raises and the message names the stage and NULL; `'slots'`
   and `'thinker'` are allowed. Plus the two regression checks against `s0-marks.json`.
