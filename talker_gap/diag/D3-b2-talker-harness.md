# D3: how the own-model talker (B2 copy/span talker) and the English eval harness work

Date of this report: 2026-10-08. Read-only task. Nothing in `/Users/ben-hannan/Desktop/projects/beautiful-model` was edited.
Source: files read with `git show origin/claude/custom-reader-talker-4x309r:<path>` (branch tip includes results commit `e10ea0232`, 2026-10-07 08:05:08 UTC, which is 04:05 ET). Line numbers below refer to those branch files. Copies were saved in the scratchpad only for line-numbered reading.

Labels: **shown** = I read it or measured it (file:line or command). **suggested** = my reading or reasoning. **untested** = not run.

Which experiment these belong to: everything in sections 1 to 4 is the **English track** (the B1 "students": B2 at M size, 10,914,681 params, trained on English passages). This is separate from the small card experiments and from the village model. Do not mix these numbers with either.

---

## 1. What the B2 answer writer reads and how it decodes

Config: `copy=True` plus `span=True` (the "span talker"). **shown** `custom_io/PASS-MARKS.md:119-120`: "B2-M = ledger M cfg with copy and the span talker (10,914,681)". The M cfg is `d=384, n_heads=6, reader_layers=2, blocks=3, n_loops=8, mlp=6.0` (`models/ledger.py:12`). The reader is a from-scratch char-level `CharReader` (`ledger.py`, `__init__`, `self.reader = CharReader(...)`), not EmbeddingGemma (EmbeddingGemma appears only in the `eg_*` arms).

**What it reads.** **shown**
- The reasoner's **final** state only. `state()` returns `(R, vals, valid, lmode, lans, lword)` plus `lwend` when `span=True` (`ledger.py:359-362`). `R` is the 9 GEN registers `[B,9,d]`; `vals` are the executed integer values; `lmode` is a 3-way head (0 NUM, 1 WORD/SPAN, 2 GEN); `lans` is a pointer over answer slots; `lword` and `lwend` are start and end pointers over prompt words.
- **Intermediate states ("notes") are NOT read.** `run()` builds per-round snapshots (`ledger.py:305` `snaps = []`, `:341` append, `:356` `out['rounds'] = snaps`). Those are used only by the training-time round loss (`round_loss`, `ledger.py:462-463`, "Test LR"). `state()` drops them, and `talk()` never sees them.
- The **current row's raw prompt** via `talk(state, batch)`. `batch` is the CURRENT rows (`ledger.py:380-386`). Two things come from it: (a) the char-level copy path, `X, xm = self.read(batch, talker=True)` (`ledger.py:386`) plus `batch['prompt_ids']` (char ids, `ledger.py:387`); (b) word spans, `word_spans(row['prompt'])[:W_MAX]` (`ledger.py:392`), with `W_MAX = 64` (`models/progparse.py:8`). So the talker sees the final state plus the current prompt's characters and word boundaries.

**How it decodes** (`talk()`, `ledger.py:380-406`; `generate()` at `ledger.py:409-415`). Decoding is greedy argmax, no beam. **shown**
- Line 384 unpacks the state. Line 385 `if self.copy`: the GEN distribution is `gen_copy(...)` (`ledger.py:239-250`), a mixture `p = g * softmax(readout(R)) + (1 - g) * copy`. The copy part is attention of `q_cp(ln_t(R))` over `k_cp(X)` on the CURRENT prompt, scatter-added onto the prompt's char ids. Without `copy`, it is `readout(R)` alone.
- GEN output: argmax over the 9 registers, then `vocab.decode(r)[::-1]` (registers are units-first; decode stops at the first EOS, `ledger.py:389-390`).
- Mode choice (`ledger.py:391`, `lmode.argmax`): **mode 0 NUM** prints `str(vals[k])` when the chosen answer slot is valid (`:398-399`). **Mode 1 with span** prints `prompt[ws[s]:we[e]]` of the CURRENT row for the best `(s, e)` from `span_pick` (`ledger.py:368-378`): `s <= e < s + span_max`, `e <` the row's word count, `span_max = 12` (constructor default, `ledger.py:130`). Mode 1 without span (`:402-403`) copies one word `w`. **Mode 2 or any invalid pointer** falls back to GEN (`:404-405`).
- Max answer length. GEN: **8 characters** in training targets, `answer[:GEN_MAX]` with `GEN_MAX = N_REG - 1 = 8` (`ledger.py:63`, `:447`, and the docstring at `:26-27`: "the register targets never change with data.MAX_ANS"). Decoding reads all 9 registers and stops at the first EOS, so the code could in principle emit 9 symbols if no EOS appears; in training the target is 8 + EOS. NUM: any integer in `vals`. Span: up to 12 words, any number of characters, inside the first 64 words. Word mode without span: one word.
- Answer-slot setting. `data.py:11` `MAX_ANS = 8` (answer chars before EOS). `data.set_max_ans()` (`data.py:15-19`) changes it at run time. The English B1 students were trained with `--max-ans 32` (`PASS-MARKS.md:121-122`, "`--max-ans 32`"). That changes the dataset target length (`data.py:116`, `answer[:MAX_ANS] + [EOS]`; training asserts `len(answer) <= MAX_ANS`, `data.py:109`). It does NOT change the GEN register cap (8), because `GEN_MAX` is fixed at `N_REG - 1`.

**Why this matters (shown counts, my own script, see section 4).** In each eval set, 122 of 192 GEN-HELDOUT rows have every accepted answer longer than 8 characters, and 86 of 192 FRESH rows do. Those rows can only be scored through the NUM or span path, not the GEN path.

---

## 2. state()/talk() split and the donor-swap lesion

**Split.** **shown**
- `state(batch, loops=None, lesion=None)` = `run(...)` then the tuple above (`ledger.py:359-362`). This is the reasoner.
- `talk(state, batch, lesion=None, return_modes=False)` = the writer above (`ledger.py:380-406`). Its only use of `batch` is the copy source and word lengths.
- `generate(batch, lesion)` for `Ledger`: `noexec`, `opswap`, `ctl27`, and `nowordc` go through `talk(state(...), batch)`; `nocopy` goes through `talk(state(batch), batch, lesion='nocopy')` (`ledger.py:409-414`); everything else goes to `super().generate`.
- `base.py:50-57`: for a model that `supports_donor()`, `generate` computes `st = self.state(batch, loops)` and applies the `zero_state` (zeros) or `shuffle_state` (`roll(1, 0)` over the batch) lesion to `st`. Lines 58 and later of `base.py` were not read; the call to `talk` is presumably there (untested).
- `Ledger.LESIONS = ['shuffle_state', 'zero_state', 'noexec', 'opswap']` (`ledger.py:128`). `loops:K` is handled by the base class. `nocopy` and `nowordc` are handled in `talk`/`generate`.

**Donor-swap lesion** (`evalx.py`). **shown**
- `donor_pairs(rows, seed)` (`evalx.py:75-90`): row i gets a donor row j of the SAME `family` whose normalised answer is not in i's accepted set and is not i's own answer (`:85`). Rows with no such donor are skipped and counted (`:89-90`).
- `donor_eval` (`evalx.py:93-127`): pairs are sorted by length; for each chunk it collates the current rows and the donor rows separately, pads both to one prompt length, then calls `out = model.talk(model.state(don), cur)` (chunk loop, roughly `evalx.py:104-122`). So the **reasoner reads the donor's prompt** and the **talker reads the current prompt** (which is also the copy source).
- Two scores (`evalx.py:123-125`): `exact` = current row's accepted-answer hit (`is_hit`, `:19-20`); `donor_match` = `norm(pred) == norm(donor['answer'])`. `donor_position_match` and `pos_coincide` appear in the English results (`RESULTS-B1.md:95`) but I did not read their definitions.
- English version (`english.py:276-289`, `judged_pairs` at `english.py:139-152`): donor must be the same `kind` AND `type`, the donor's canonical answer must not be in the current row's accepted set, and the donor's taught span must not itself produce an accepted answer. The "plain" control is the same-kind pairing from `donor_pairs`. `les['donor']` is stored under `lesions['donor']` for `new_pooled` and `fresh`.
- `donor_all` / `eval_all(..., donor=True)` (`evalx.py:153-166`) add the donor block to each split. The English path calls `eval_english` instead.

**Interpretation (suggested).** A high `exact` under the donor state means the talker is answering from the current prompt and ignores the reasoner's state. A high `donor_match` means it copies the donor's answer. The B1 numbers in section 4 show both are low for new kinds, which is where the "thinker decides" mark came in.

---

## 3. How english.py turns a TEACH jsonl row into train and eval rows, and scores the four sets

**Input.** `load_examples` (`english.py:87-94`) accepts `{'examples': [...]}`, a JSON list, or JSONL. `clean_example` (`:97-100`) applies `clean()` (curly quotes to ASCII, dashes, NBSP; `:20-21`, `:29-33`) to `source_text`, `paraphrase`, each question, each canonical answer, and each accepted answer.

**Rows.** `qa_rows` (`english.py:103-115`). For each example, each panel in `('source_text', 'paraphrase')` (`:14`), and each question:
- `prompt = e[panel] + ' ' + question`
- `canonical = canonical_answer`; `accepted = dedup([canonical] + accepted_answers)`
- `answer = taught_answer(prompt, canonical, accepted)` (`:70-77`): if the canonical answer is yes/no, keep it; otherwise the first string in `[canonical] + accepted` whose `en_norm` equals a run of the prompt's word tokens; otherwise the canonical answer.
- Each row also gets `family`, `type`, `panel`, `atype` (reporting only, `:79-85`), and `id = f"{ex}-{panel}-q{qi}"`. One example gives 2 panels times its questions.

**Dropping rows at build time** (`_bad_row`, `english.py:319-330`): non-printable-ASCII text; prompt over `MAX_PROMPT = 208`; empty answer; answer over `MAX_TAUGHT = 32` (`:13`). Answers over 8 characters are **not** dropped at build time.

**Build** (`build_pair`, `english.py:504-520`; CLI `main`, `:522-`, flags `--teach --gen --out --eval --seed`, `:526-530`). **shown**
- `prepare_arm` (`:332-355`) cleans and drops rows; `guard` (`:361`) raises an `OverlapError` before any writing if a training passage overlaps an eval passage.
- `split_heldout` (`:421-`): 1% of examples (at least 1, at most 2000 rows), closed under "shares a passage" (`en_norm` of panel text).
- `parity_cut` (`:453-`) trims both arms to the same number of training rows.
- `_write_arm` (`:477-503`) writes `out/<arm>/train.jsonl`, `out/<arm>/dev/in_dist.jsonl` (held-out rows), and `charvocab.json`, and asserts no held-out passage equals a training passage (`:487`).

**Training row.** Each written row is one JSON line from `_rows()`, with `prompt`, `answer`, and the metadata above. `data.Dataset` (`data.py:102-116`) encodes `prompt` and `answer[:MAX_ANS] + [EOS]`. Training uses `strict=True` (asserts answers fit `MAX_ANS`, `data.py:109`). Dev uses `strict=False` (truncates).

**Eval sets** (`english.py:15`, `EVAL_FILES`): `fresh` = FRESH-EN-R3.json (practised kinds, human wording); `new_r5` = NEW-KINDS-R5.json and `new_r6` = NEW-KINDS2-R6.json (kinds neither arm practises); `gen_heldout` = GEN-HELDOUT-R4.json (the GEN arm's own generator kinds). `eval_examples` (`:117-119`) loads these with `load_examples` and calls `qa_rows` directly, **without** `clean_example`. `eval_sets` (`:121-126`) returns the four sets plus `new_pooled = new_r5 + new_r6`. Each set is 192 rows (`english_eval/README.md` lists 48 examples per file; 48 x 2 panels x 2 questions = 192; the docstring at `:122` says 192; my counts agree, section 4).

**Scoring.** `en_norm` (`english.py:23-27`): NFC, lower-case, curly single quotes to `'`, strip, collapse whitespace, strip trailing `[.!?,;:]+`, strip. `score` (`:203-209`): a row is a hit when `en_norm(pred)` is in `{en_norm(a) for a in accepted}`; `exact = 100 * hits / n`. The same norm is passed into `evalx.evaluate(..., norm=en_norm)` (`evalx.py:37-66`), which takes one prediction per row through `model.generate`.

**eval_english** (`english.py:245-306`): intact `exact` for `fresh`, `new_r5`, `new_r6`, `new_pooled`, `gen_heldout`, and `in_dist_heldout` (the held-out split from build). Lesions for `new_pooled` and `fresh`: `donor` (section 2), `loops:0`, and every name in `model.LESIONS`.

Possible harness gap (untested): eval rows skip `clean_example` (`english.py:117-119`), so curly quotes or non-ASCII in the eval JSON reach the model unchanged. `en_norm` handles curly quotes at scoring time, but the model's char vocab maps unknown chars to UNK. Whether this costs any hits is untested.

---

## 4. Own-model English QA numbers on the four sets (latest found on this branch)

Source: `custom_io/results/RESULTS-B1.md` (commit `e10ea0232`, 2026-10-07 04:05 ET). Scorer: round-6 (`en_norm`). Seeds 300 and 301 (screen). Students: B2-M on TEACH (`b2t`), B2-M on GEN (`b2g`), and plain_tf-M on TEACH (`tft`), 16,000 updates, batch 256, lr 7e-4 (`PASS-MARKS.md:117-125`). Design spec: `custom_io/design/B1-students.md:1-21`.

Means over seeds 300 and 301 (`RESULTS-B1.md:29-34`), in percent:

| arm | fresh | new_r5 | new_r6 | new_pooled (384 rows) | gen_heldout | in_dist_heldout | donor (exact) | loops:0 |
|---|---|---|---|---|---|---|---|---|
| b2t (B2 span talker, TEACH) | 22.92 | 16.15 | 6.25 | 11.20 | 22.92 | 91.19 | 9.44 | 0.78 |
| b2g (B2 span talker, GEN) | 48.96 | 12.24 | 8.59 | 10.42 | 96.09 | 96.47 | 6.78 | 0.00 |
| tft (plain transformer, TEACH) | 17.71 | 18.49 | 9.38 | 13.93 | 16.41 | 92.19 | n/a | n/a |

Per seed (`RESULTS-B1.md:16-23`): b2t_s300 fresh 22.92, R5 16.15, R6 4.69, pooled 10.42; b2t_s301 fresh 22.92, R5 16.15, R6 7.81, pooled 11.98. Size 10,914,681 (B2) and 10,782,336 (tft).

Donor detail, b2t (`RESULTS-B1.md:95-100`): donor exact 9.04 and 9.84; `donor_match` 3.46 and 4.26; `donor_position_match` 7.06 and 7.35; skipped 8 rows; exact given intact-right 27.03 and 28.57; loops:0 exact 0.78, with all 384 rows in span mode. b2g: donor exact 7.71 and 5.85; `donor_match` 3.19 and 3.99; loops:0 exact 0.00, all GEN.

Reachability (`RESULTS-B1.md:104-113`): 100% of new-kinds-pooled rows are emit-able by every arm (the gold answer can be produced by the talker at all).

Marks as written in the file (`RESULTS-B1.md:3-8`; spec `design/B1-students.md:14-21`):
- B1-a (b2t minus b2g on new pooled, need >= +15): mean 0.78, **PROVED WRONG**.
- B1-c (b2t minus tft, need >= +3): mean -2.73, **FAIL**.
- B1-b (donor state <= 10% on new pooled): mean donor 9.44 would pass the rule, but the file labels it **UNINFORMATIVE** because intact new-kinds 11.20 is under the 20 floor ("the rule alone would say PASS").

Reference numbers (not our model): bare 1.2B 8-shot 75.0 FRESH, 67.7 R5, 77.6 R6; "sandwich" 92.2 FRESH and 78.2 new pooled (`PASS-MARKS.md:132`; `design/B1-students.md:21`). `results-digest.md:20` gives allptr (pretrained 1.2B reader plus talker) fresh 92.6% (`english/RESULTS-R4.md`, not checked). The 13.6% number is a core-only copy-and-gate talker on unseen English kinds (`design/design-latent-reread.md:187`; `design/design-workspace-typed.md:195`). I did not open PR #37 itself, so I cannot confirm the "13.6 vs 78.2" pairing from PR #37; the 78.2 on this branch is the sandwich's new-pooled score, a different system.

**Shown counts from my own script** (reading the four `custom_io/english_eval/*.json` files from the branch; raw strings, no `clean`; this is my counting, not the harness):
- FRESH-EN-R3: 48 examples, 96 questions, 192 rows; yes/no 22; canonical answer over 8 chars 108; all accepted answers over 8 chars 86.
- NEW-KINDS-R5: 48, 96, 192; yes/no 24; over 8 chars 66; all accepted over 8 chars 18.
- NEW-KINDS2-R6: 48, 96, 192; yes/no 20; over 8 chars 104; all accepted over 8 chars 60.
- GEN-HELDOUT-R4: 48, 96, 192; yes/no 16; over 8 chars 138; all accepted over 8 chars 122.

Caveat: the "over 8 chars" counts use raw canonical and accepted strings, not the taught span, so they are an upper bound on rows the GEN path cannot emit. Not checked whether any newer English results sit in other result directories on the branch (the `results/` listing was truncated).

---

## 5. Implications for a small Mac experiment (suggested, untested)

1. The existing pipeline is self-contained: `english build --teach --gen --out --eval` (`english.py:522-530`), then train B2 with `copy` and `span` at `--max-ans 32` (the B1 settings), then `eval_english` for the lesions. Train-script flags were not read (untested).
2. The copy talker reads only the final state and the current prompt. To test "talker reads intermediate notes", `state()` would have to return `out['rounds']` (`ledger.py:356`), which it does not today. `talk()` would also need to read them. This is a code change, not a flag.
3. The donor lesion measures the reasoner's influence on the talker, but a high `exact` under a donor can also mean the talker copies from the prompt. Read `donor_match` together with `exact`. In the B1 students, both were low on new kinds (section 4).
4. GEN answers are capped at 8 characters while the training targets for B1 were 32 characters. Rows whose taught answer is not a span and is over 8 characters are trained with truncated GEN targets (`ledger.py:447`). How many such rows exist is untested.
5. The four eval sets are not run through `clean_example` (section 3). Untested whether this matters.

---

## Open questions
- Whether the train script's CLI flags match the B1 recipe (not read; `train.py` not opened).
- Whether a newer own-model English result exists on other branches or in other `results/` directories (not checked).
- Whether `base.py:58+` calls `talk` exactly as assumed (not read).
- The number of non-span, over-8-character training rows (not counted; needs `taught_answer` on the TEACH files, which are not in the branch).
