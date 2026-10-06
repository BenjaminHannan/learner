# Test B1, student side: build spec (2026-10-05, about 8:30 PM ET; revised after 3 reviews)

Source of the test: `design/thinker-first-split-2026-10-05.md` section 6 on branch `claude/project-thread-9ye9md`
(PR #41). Ben picked Plan B at 7:44 PM ET. A separate thread ("Teacher data for Plan B") writes the TEACH and GEN
data. This thread builds and trains the students on the B2 code in `custom_io/`. The spec was reviewed before any
code by three independent reviewers (fidelity and fairness, feasibility against the code, evaluation and
contamination); their findings are folded in below.

## The test, as fixed by the spec (copied, do not change)

- **Students (same recipe, same updates):** B2 at M size on TEACH, B2 on GEN, and `plain_tf` of the same size on TEACH
  (the shape control). 2 seeds each (screen), then 6 (confirm).
- **Scores:** FRESH-EN-R3 (practised kinds, human wording) and NEW-KINDS-R5 + NEW-KINDS2-R6 pooled (384 rows, kinds
  never practised by either arm). Lesions: donor state and thinker loops = 0.
- **Marks** (means over the 2 screen seeds):
  - **B1-a, variety helps new kinds:** B2-TEACH minus B2-GEN on new kinds pooled >= +15 points, ahead on both seeds.
    Proved wrong: < +5.
  - **B1-b, the thinker decides:** B2-TEACH with a donor's state <= 10% on new kinds pooled.
  - **B1-c, the shape matters:** B2-TEACH minus plain_tf-TEACH >= +3 on new kinds pooled, ahead on both seeds.
  - Read, not judged: distance to the bare 1.2B 8-shot (75.0 FRESH; 67.7 R5 and 77.6 R6) and to today's sandwich
    (92.2 FRESH; 78.2 new kinds pooled).

## Operational choices (this thread's; fixed before any student trains)

1. **Rows.** Every question of every example gives two rows, one per panel, in `rows_of` order (example, then panel
   `source_text` then `paraphrase`, then question): `prompt = panel + " " + question`, id
   `f"{example id}-{panel key}-q{qi}"`, `accepted` = `[canonical_answer] + accepted_answers` (raw, de-duplicated,
   order kept; used for scoring and for the span check below).
   **Taught string** (`answer`, the one target both students learn): if en_norm(canonical) is yes or no, the
   canonical answer; else the first of `[canonical] + accepted_answers` whose en_norm equals the text of a contiguous
   run of `data.word_spans` tokens of the prompt (`prompt[ws[s]:we[e]]`); else the canonical answer. B2 and plain_tf
   therefore learn the same string on every row.
2. **Scorer:** the round-6 scorer. `en_norm(s)` = NFC, lower-case, `’` and `‘` to `'`, strip, collapse whitespace,
   strip trailing `[.!?,;:]+`, strip. A row is right when `en_norm(pred)` is in `{en_norm(a) for a in accepted}`.
   New kinds pooled = all 384 rows of R5 + R6 (micro mean, unrounded).
   `atype` (reporting only, matches round 6 on all 768 eval rows): `yes_no` when en_norm(canonical) is yes/no; else try
   `[canonical] + accepted_answers` in order, take the first whose en_norm equals a word-token run of the prompt
   (earliest start): `span1` if the run is one token, else `spanN`; none: `nonspan`.
3. **Training data clean-up** (both arms the same): curly quotes to straight, en/em dashes to `-`, no-break space to
   space, then NFC; drop a row if any char of its prompt, taught answer or accepted answers is not printable ASCII, if
   its prompt is over 208 chars (`data.MAX_PROMPT`), or if its taught answer is empty or over 32 chars.
   **Parity:** after clean-up, the overlap guard and the held-out split, the arm with more training rows is cut to
   the other's count by dropping whole examples (seeded, seed 0). Both `train.jsonl` files have equal row counts;
   each manifest records the counts before and after the cut. The char vocab is the fixed 108 ids (13 specials + 95
   printable ASCII) for every arm; the adapter writes it.
4. **Held-out in-dist slice** (`in_dist_heldout`, read only): 1% of each arm's examples (at least 1, at most 2,000
   rows), grouped so that an example goes to the slice if either of its passages (en_norm) equals a slice passage.
   They are removed from `train.jsonl` and written to `dev/in_dist.jsonl`; the adapter asserts no slice passage
   equals a training passage.
5. **Overlap guard:** the adapter refuses to build (non-zero exit) if any eval `source_text` or `paraphrase` (en_norm)
   from FRESH-EN-R3, NEW-KINDS-R5, NEW-KINDS2-R6 or GEN-HELDOUT-R4 equals a training passage, and asserts no training
   prompt equals an eval prompt. Training questions equal to an eval question (stock questions such as "Which event
   happened first?") are counted per kind and per eval set in the manifest, not dropped: the passage check already
   keeps every eval row out. Report only: for each eval set, the highest word-set Jaccard (en_norm, small stop list
   removed) of its passages against any training passage, the number of training passages at or above 0.8, and the
   number containing a capitalised name from an eval passage.
6. **B2-M:** `ledger` with the M config (`d 384, n_heads 6, reader_layers 2, blocks 3, n_loops 8, mlp 6.0`), `copy`
   true, plus the new `span` talker mode. Expected size 10,914,681.
7. **plain_tf-M:** `d_model 384, n_layers 6, n_heads 6`, `max_ans 32` (33 answer slots, position table 243). Expected
   size 10,782,336 (B2-M is +1.23%). Tests assert both sizes exactly.
8. **Recipe, every arm:** batch 256, lr 7e-4, warmup 500, cosine to 10%, AdamW as in `train.py`, bf16, `--max-ans 32`,
   **16,000 updates**, no time cap. Seeds 300 and 301 (confirm: 300-305). All runs of a seed on one device.
9. **Donor lesion (B1-b, judged on new kinds pooled):** row i gets donor j of the same kind AND the same question type
   (`short_answer` / `yes_no`), whose canonical answer (en_norm) is not in i's accepted set, and whose taught-answer
   span positions (every (s, e) occurrence in j's prompt) never give, read on i's prompt, text whose en_norm is in i's
   accepted set. A row with no such donor is skipped and counted (expected 8 of 384 on new kinds pooled, 2 of 192 on
   FRESH). Seeded (seed 0), rows in `rows_of` order. Read only, next to it: the plain same-kind pairing, `pos_coincide`
   (share of plain pairs where the donor's positions give i's answer), `donor_match` (pred in the donor's accepted set),
   `donor_position_match` (pred equals i's text at the donor's first span position), and donor exact restricted to rows
   the intact model got right. If B2-TEACH's intact new-kinds score is under 20%, B1-b is printed as "uninformative".
10. **loops:0** (read only): reported with `by_atype` and the histogram of decoded talker modes (NUM / span / GEN),
    labelled "question-blind talker": with no loops every row gets the same mode and the same queries.
11. **Reachability** (read only): per eval set and model type, the share of rows the talker can emit at all (B2: a
    word-token span of the prompt, a number in the prompt, or an accepted answer of <= 8 chars; plain_tf: an accepted
    answer of <= 32 chars).
12. **GEN-HELDOUT-R4** is reported as "generator kinds, the GEN arm's own distribution" (most of its names and nouns
    are in the GEN arm's training pools). It is never subtracted across arms.
13. **Memory:** `--par 2` on the 16 GB card unless the first runs' measured peaks plus 1.5 GB show three fit.
    `# MEM 7500`. `train.py` records the CUDA peak memory so later queues can use measured numbers.

## What to build

### 1. `custom_io/english.py` (new)

- `en_norm(s)` and `clean(s)` (choices 2, 3); `load_examples(path)` (a `{"examples": [...]}` JSON file, a JSON list,
  or JSONL, one example per line); `qa_rows(examples)` (choice 1 rows, each with `id, prompt, answer, accepted, family,
  type, panel, level (0), atype`); `word_runs(prompt, text)` helpers shared with the ledger span targets.
- `build_pair(teach_src, gen_src, out_dir, eval_dir, ...)` and the CLI
  `python -m custom_io.english build --teach FILE --gen FILE --out DIR --eval DIR`: writes `DIR/teach/` and
  `DIR/gen/`, each with `train.jsonl`, `dev/in_dist.jsonl`, `charvocab.json` (108 ids, with `train_bytes`) and
  `MANIFEST.json` (source path + sha256, example / question / row counts before and after each step, drops by reason
  and by kind, atype counts and the yes:no ratio, max prompt and answer length, overlap and near-duplicate report, the
  count of training passages containing a GEN-HELDOUT name, sha256 of every file written). Unique ids asserted.
- `eval_sets(eval_dir)` -> `{'fresh', 'new_r5', 'new_r6', 'gen_heldout'}` rows; `new_pooled` = new_r5 + new_r6.
- `eval_english(model, eval_dir, heldout_rows, device, batch_size, amp)` -> a JSON-able dict:
  - intact exact on fresh, new_r5, new_r6, new_pooled, gen_heldout and in_dist_heldout, each with `by_family`,
    `by_type`, `by_atype`, `by_panel`, `reachable` and `n` (an empty set gives `{n: 0}` and is never evaluated);
  - `lesions` on new_pooled and fresh: `donor` (choice 9, with every read-only number listed there) when the model
    supports state/talk; `loops:0` when the model has `n_loops > 1` (choice 10); and every name in `model.LESIONS`
    that is not a loops lesion;
  - `preds` (id -> prediction) for intact new_pooled and fresh, and `donor_preds` (id -> [donor id, prediction]), so
    any number can be re-scored without a GPU.
- `evalx.evaluate`, `evalx.donor_pairs` and `evalx.donor_eval` gain optional arguments (`norm`, and for donor_pairs a
  `pairs` list or pairing function) whose defaults keep every skills number exactly as it is.

### 2. `custom_io/models/ledger.py`: `span` mode (cfg `span`, default false = B2 exactly)

- GEN targets use a module constant `GEN_MAX = N_REG - 1` (8) in place of `MAX_ANS`, so `data.set_max_ans` can never
  change B2's register targets whatever the import order.
- New module created LAST (after the copy modules): `q_wend = nn.Linear(d, dk)` (normal 0.02, zero bias); cfg
  `span_max`, default 12 words.
- `run()`: when span, `out['lwend'] = self.ptr(self.q_wend(zf), Kw, wvalid)` over the same word keys as `lword`.
- `state()` appends `lwend` when span (donor, zero and shuffle lesions then carry it like the rest).
- Targets (`gold`), when span: progparse NUM rows (mode 0) stay NUM. Otherwise, if en_norm(answer) is yes or no: GEN.
  Otherwise the span targets are every (s, e) with s <= e < s + span_max, e < min(#words, W_MAX), and
  `en_norm(prompt[ws[s]:we[e]]) == en_norm(answer)` (the taught string); any target makes the row mode 1, else GEN
  (answer[:GEN_MAX]). Cached per (row id, prompt).
- Loss, when span: mode-1 rows use `-log sum_{(s,e) in targets} p_start(s) * p_end(e)` (fp32 logsumexp over the
  masked [W, W] grid of log_softmax(lword)[s] + log_softmax(lwend)[e]), summed over mode-1 rows and divided by B,
  in place of the single-word loss. Everything else unchanged.
- Decode (`talk`), when span and mode 1: the (s, e) with s <= e < s + span_max and e < the CURRENT row's word count
  that maximises log p_start(s) + log p_end(e); output `prompt[ws[s]:we[e]]` of the CURRENT row; no valid pair: GEN.
  `talk` can also return the decoded mode per row (for the loops:0 histogram) without changing its default output.
- Docstring: one paragraph in the existing style, with the M + copy + span size 10,914,681.

### 3. `custom_io/models/plain_tf.py`: `max_ans` cfg (default 8 = exactly as now)

- `self.max_ans` replaces `MAX_ANS` everywhere in the class. Position table 224 when `max_ans <= 8` (old checkpoints
  still load), else `2 + MAX_PROMPT + max_ans + 1`. New kwarg goes after `place`; `PlainTFSteps` (positional args)
  behaves exactly as before.
- `_build` / `loss` pad or cut `ans_ids` / `ans_mask` to `max_ans + 1` columns.

### 4. `custom_io/data.py`, `custom_io/train.py`, `custom_io/local_runner.py`

- `data.set_max_ans(n)` sets the module's `MAX_ANS`, which `Dataset` and `collate` read at call time. Default 8.
- `train.py --max-ans N` (default 8) calls it before any data or model is built and records it in the config;
  refuse to start when the model has a `max_ans` attribute smaller than N.
- `train.py --english-eval DIR`: with `--final-eval`, run `english.eval_english` (held-out rows read with
  `load_rows(DATA/dev/in_dist.jsonl, keep=None)`), store it as `result['english']`, and skip `eval_all`, the chain-5
  panel and `extra_evals`. Assert `len(vocab) == 108`. One `event: eval` JSON line per set and lesion.
- `train.py` records `peak_mem_mib` and `peak_reserved_mib` (CUDA only) in RESULT.json and the `done` event.
- `local_runner.py`: in `parse_queue`, after `shlex.split`, replace `{WORK}` inside each token with the work dir (never
  in the raw line: Windows backslashes). `summary_line` also shows english fresh / new_pooled / donor when present.

### 5. `custom_io/analyze_b1.py` (new)

Reads the RESULT.json of runs named `b2t_sN` (B2 on TEACH), `b2g_sN` (B2 on GEN) and `tft_sN` (plain_tf on TEACH),
pairs them by seed, and writes `results/B1-ANALYSIS.json` and `results/RESULTS-B1.md`.
- diff_s = A_s - B_s per seed; "ahead on both seeds" = diff_s > 0 for every screen seed; unrounded percentages.
- B1-a: PASS if mean diff >= 15 and ahead on both; PROVED WRONG if mean < 5; else FAIL. B1-b: PASS if the mean of the
  seeds' judged donor exact <= 10. B1-c: PASS if mean diff >= 3 and ahead on both.
- A mark is NOT JUDGED if a run it needs is missing or invalid: status != 'ok', steps != 16000, a recipe or cfg that
  differs from choices 6-8, or a data manifest sha256 that differs from the one recorded in PASS-MARKS addendum 3.
- Also, read only: per-seed and mean FRESH, R5, R6, GEN-HELDOUT (choice 12) and in_dist_heldout; the B1-a and B1-c
  differences split by atype; always-"yes" and always-"no" scores on the yes/no rows; every donor and loops:0 number
  of choices 9-10; reachability; whole sizes; the read-only distances in the spec.

### 6. Eval files, queue and pass marks

- `custom_io/english_eval/`: the four eval JSONs, unchanged from `claude/project-thread-utxkpw` @ 338e22ba9, README
  with sha256 (done).
- `custom_io/queue_local/35-pc-b1-students.txt`: the 6 screen runs in seed order (b2t_s300, tft_s300, b2g_s300, then
  s301), `--data {WORK}/plan_b/teach` or `{WORK}/plan_b/gen`, `--english-eval custom_io/english_eval`, the recipe of
  choice 8, `# MEM 7500`, run with `--par 2`. The adapter command goes in PC-JOB.md.
- `custom_io/PASS-MARKS.md` addendum 3: the marks and choices above plus the data manifests' sha256, committed before
  any student trains.

### 7. Tests and CPU smoke

- Before editing ledger.py or plain_tf.py, record GOLD fingerprints at HEAD (as `tests/test_ledger_copy.py` does):
  Ledger (small cfg and M cfg, copy=True) and PlainTF (S and M): param count, state_dict key hash, weight sums, loss on
  a fixed batch at seed 0. New tests assert span=False / max_ans=8 still match them, that span=True only adds
  `q_wend` (last) and shares every other initial weight, and that both expected M sizes hold exactly.
- `tests/test_english.py`: en_norm cases; rows (ids, order, both panels, accepted, taught string); atype; clean-up
  drops; overlap guard (refuses an eval passage, counts an eval question); held-out grouping; parity cut; span targets
  (single word, multi-word, accepted-only form, yes/no never a span, absent answer); decode never crosses `span_max`
  or the current row's word count; judged donor pairs never cross type and never coincide by position; empty sets.
- `data.set_max_ans` tests restore 8 in a `finally`. With `set_max_ans(32)` called before the first ledger import,
  `gold()` on a 20-char non-span answer gives 8 chars + EOS.
- Smoke (CPU): take the first 1,500 and the next 1,500 examples of `/mnt/project-files/plan-b/data/gen.jsonl` as stand-in
  "teach" and "gen" files, run `english build` into the scratchpad, then each of the three students at a tiny size
  for about 60 updates with `--final-eval --english-eval custom_io/english_eval`, and the full M configs for a few
  updates to print `n_params`.
