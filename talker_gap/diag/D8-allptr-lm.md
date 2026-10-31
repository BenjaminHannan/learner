# D8: how the allptr LM talker works, and whether the thinker adds anything on unseen kinds

Scope: English real-pipeline QA runs (`reasoner_ptr/real/english`, PR #37 = branch `claude/project-thread-utxkpw`, title "Copy-talker test: a tiny talker fails on new question kinds; the LM talker ignores the core there", OPEN, per `gh pr view 37`). Second source: branch `claude/custom-reader-talker-4x309r` (`custom_io/research/results-digest.md`, `baselines.md`). These numbers do not belong to the card toys or the village model.

Labels: **shown** = I read it or measured it (file:line or command given); **suggested** = reasoning or literature; **untested** = not checked.

## Short answer

- **allptr** feeds the frozen 1.2B LM an embedding prefix (8 pooled core vectors, 8 pointer-weighted sums of prompt-word embeddings, and every prompt-word embedding), then the answer. It generates text greedily. It does not point into the prompt. (shown)
- **Shuffled-core lesion, seed 0, unseen kinds:** accuracy stays at 73.18% (281/384). 334 of 384 answers are identical. But 50 answers change, and 14 go right→wrong while 14 go wrong→right. That is a net-zero change, not "no effect". (shown, one seed)
- **The decisive control is missing.** No allptr run with the core skipped exists. The closest comparison is a bare 8-shot LM at 72.7% pooled on the same unseen sets, which is level with the seed-0 rerun (73.2%). (shown for the numbers; "no core-skipped allptr" is shown by the arm list at run_english.py:28)
- **Conclusion:** the thinker's question-specific content changes about 13% of LM answers and nets zero on this seed. So "the LM mostly ignored the thinker" is roughly right for the net accuracy, but it is not established that the core is irrelevant. (suggested)

## 1. What allptr feeds the LM, and how it outputs

Source: `reasoner_ptr/real/english/run_english.py` on `origin/claude/project-thread-utxkpw`. I saved it to the scratchpad; line numbers below are the branch's.

- **Frozen LM:** default `--lm LiquidAI/LFM2.5-1.2B-Instruct` (line 33), loaded with `from_pretrained(...).requires_grad_(False)` (line 55). (shown)
- **Core input (`core_states`, lines 188-210):** the frozen LM runs once over `[BOS] + prompt` and its last hidden state is the reader input (`e0`, line ~193). The reader (`HumanInputProjection`) projects it to 256-d (line 197). A 9.0M ordered-attention core (8 experts, 2 active; `build_core` lines ~143-150, with an assert of 9,007,790 params) runs `begin_latent` (line 205) and 4 `advance_latent` steps (line 207). The 8-slot notebook holds fixed role/status vectors, not question content (lines 200-203). (shown)
- **Prefix (`make_prefix`, lines 212-226), used by allptr:**
  - line 215: `query, h, ... = core_states(model, ids)`;
  - lines 216-217, shuffle lesion only: `h = h.roll(1, dims=0)`, i.e. the donor is the previous row in the same-length batch. This happens **before** both the pool adapter and the pointer, so the donor controls both;
  - line 219: `prefix = model.adapter.project_training(h, ...)`, giving 8 pooled prefix vectors (StatePrefix is in an imported module and was not read);
  - lines 220-221, zero-pool lesion only: `prefix = prefix * 0`. The pointer and the word embeddings are not zeroed;
  - line 224: `pw = model.ptr(h).softmax(1)`, a Linear(256→8) over prompt positions;
  - line 225: `torch.einsum("bnk,bnl->bkl", pw, tok_e)` gives 8 soft-pointer vectors (value = LM input embedding at each prompt position), and `tok_e` itself appends all n prompt-word input embeddings. `tok_e = emb(ids)` is computed inside `core_states` (lines 188-210) and is never rolled.
  - So the LM receives **all prompt words as input embeddings** plus the core-derived vectors. It re-reads the question itself. (shown)
- **Training loss (`loss_on`, lines 283-296):** `[prefix, BOS, answer-token embeddings]` goes into the LM. Cross-entropy is taken on the answer tokens and EOS, with the LM frozen. (shown)
- **Output (`generate`, lines 300-313):** greedy argmax, up to `max_new` tokens, stop on EOS, then `tok.decode`. Exact match after normalisation against the accepted answers. It is generative, not a pointer into the prompt. The pointer is soft attention feeding embeddings. (shown)
- **Batching (`group_by_len` line 229, `evaluate` lines 329-345):** rows are grouped by prompt length, then batched 32 at a time. The shuffle donor is therefore a different question of the same length, within the same batch. (shown)

Copytalk (`copytalk` / `copytalk_nocore`, `CopyTalk` at line 165): no LM answer pass. It is a start/end span head over core states plus a gate over 27 classes (`<span>` + 26 answers; `V=26` in the JSON). `copytalk_nocore` skips the core (`h = query`). (shown)

## 2. The numbers and their sources

All below are English real-pipeline QA, not card toys or village.

| Quantity | Value | Source |
|---|---|---|
| allptr, 6 seeds (round 6 control), unseen pooled | 78.17 (CI 74.12–82.21); per seed 82.29, 75.52, 79.42, 82.55, 76.04, 73.17 | `ANALYSIS-CT.json` `allptr_r6.unseen` |
| allptr, seed-0 CT rerun, unseen pooled | 73.18 = 281/384 | `results_ct/box54195608/out/allptr-gen-ct-seed0.json` (`extra` 76.04 / `extra2` 70.31 from rows); `ANALYSIS-CT.json` lines 381-386 |
| allptr seed-0 rerun, **shuffle-core lesion**, unseen | 73.18 = 281/384 | `allptr-gen-ct-seed0-lesion-shuffle_core-unseen-rows.json`; `ANALYSIS-CT.json` line 384 |
| shuffle lesion: identical answers | 334/384 (includes 3 singleton batches left unshuffled, `shuffle_core_b1_unchanged = 3`) | my row comparison of the two files |
| shuffle lesion: changed answers | 50; right→wrong 14, wrong→right 14, ok→ok 6, wrong→wrong 16 | same comparison |
| shuffle lesion: "contains" | 334 → 332 | same |
| copytalk, 6 seeds, unseen | 13.63 (CI 11.56–15.70) | `ANALYSIS-CT.json` `copytalk.unseen` |
| copytalk_nocore, 6 seeds, unseen | 12.89 (CI 11.66–14.12) | `ANALYSIS-CT.json` `copytalk_nocore.unseen` |
| core effect, copytalk − nocore, unseen | +0.74 (CI −1.96 to +3.43) | `ANALYSIS-CT.json` key `B_copytalk_minus_nocore` |
| **bare 8-shot 1.2B LM (no core), unseen extra** | 67.71 = 130/192 | `results6/box54161987/out/lm_fewshot-seed0-extra-rows.json` (my count) |
| **bare 8-shot 1.2B LM, unseen extra2** | 77.60 = 149/192 | `lm_fewshot-seed0-extra2-rows.json` |
| bare 8-shot, pooled unseen (one run, no seeds) | 72.66 = 279/384 | derived from the two row files |
| bare zero-shot 1.2B LM, unseen | **not run** (round-3 `lm_alone` covers FRESH only: 29.69% exact, 76.04% contains, n=192) | `results/box54092912/out/lm_alone-seed0.json` |
| allptr zero-pool lesion (seed 0, CT) | 0.0 on FRESH (practised kinds, n=192) | `allptr-gen-ct-seed0.json` `lesion_zero_pool` |
| practised kinds, human wording (FRESH-EN-R3) | allptr 92.2 (six) / copytalk 58.7 / nocore 24.5 | `RESULTS-CT.md` table; digest row 7 |
| practised kinds, generated heldout | allptr 99.7 / copytalk 97.4 / nocore 41.6 | `ANALYSIS-CT.json` |
| allptr + generated, round 4, FRESH | 92.6 (fresh exact); bare 8-shot 75.0 | `RESULTS-R4.md` line 12; `ANALYSIS-R6.json` `lm_fewshot.fresh` 75.0 |
| taxonomy stdout reproduction | allptr unseen 73.2 (n=1), copytalk 13.6, nocore 12.9, heldout 97.4, nocore heldout 41.6 | `talker-gap-wt/.../diag/out/ct_taxonomy_stdout.txt` (head read; matches) |

Mismatch checked: `RESULTS-CT.md` lines 45-47 report the seed-0 rerun as 73.2 against round 6's 82.3 for the same seed (a 9-point drop, same code, different GPU, nondeterminism suspected). This makes the 73.2 vs 72.7 comparison fragile.

Two uses of "78.2" appear. In `ANALYSIS-CT.json` it is the allptr six-seed pooled unseen mean. In `results-digest.md` line 21 it is the 12-kinds arm on the second unseen set (75.3 for six kinds). They are different numbers; keep them apart.

## 3. What this implies

- **Shown:** the copy head adds 0.7 points on unseen kinds (CI includes 0). The core makes no measurable difference for the copy talker there. (ANALYSIS-CT.json B)
- **Shown, one seed:** shuffling the core across questions of the same length leaves 13% of allptr answers different, with zero net accuracy change. The LM does use the core's question-specific content for some answers.
- **Shown:** the shuffle donor is in the same family as the replaced question about 70% of the time (consecutive-row same-family share 0.697 in the shuffle file, against 0.083 for two random rows). So the lesion mainly removes question-specific content and keeps kind-level content. That makes it a weaker test than a cross-kind swap. (my computation on the shuffle rows; the file's order is the batch order)
- **Shown, changes by family:** the 28 correctness flips are spread across 11 families (speech_quote 0 right→wrong and 3 wrong→right; cause_reason 3 right→wrong; counting_quantity 2 right→wrong and 1 wrong→right; direction_turn 2 right→wrong). No single family explains the net zero. Note the "on the shelf → in the drawer" example in my sample is not a location_tracking case in the table.
- **Suggested:** on unseen kinds the LM's own reading of the words, steered by practice, carries most of the score. This matches the bare 8-shot LM at 72.7 sitting at the seed-0 allptr level. The round-6 advantage over bare LM (82.3 on seed 0, 78.2 six-seed mean) is not reproduced by the seed-0 rerun.
- **Untested:** (a) a core-skipped allptr arm on the same unseen sets (the decisive control; it does not exist); (b) cross-kind donor swaps; (c) six-seed shuffle; (d) rerun-to-rerun variance of the same weights (how many of the 50 changed answers are GPU noise); (e) whether zero-pool's 0% is a pure out-of-distribution effect (zeroed prefix vectors) rather than evidence the core matters. The zero-pool lesion was run on FRESH, not the unseen sets.
- **Comparison caveat:** the 8-shot LM uses a chat template with shots and is one run. allptr is a different input format and is seeded. The two are not matched.

For the planned pipeline (frozen EmbeddingGemma reader → thinker → talker): note that the copytalk arm still runs the frozen 1.2B LM once as a reader (`core_states`, line 193), and allptr runs it twice (reader pass and talk pass). Any cost estimate for an LM talker should count both. (shown by code; suggested for the mapping)

## 4. Pretrained vs from scratch

- **Pretrained, frozen:** LFM2.5-1.2B-Instruct (run_english.py:33, 55). Also the 8-shot bare LM (`eval_lm_alone`, lines 352-362; `lm_fewshot` shots are one training-bank example per family plus 2 yes/no, lines 410-411). (shown)
- **From scratch (trained):** the reader `HumanInputProjection`, the 9.0M core (`build_core`, lines ~143-150, `manual_seed` only, no checkpoint load), `StatePrefix`, the tool role/status vectors, the pointer `ptr` (line 161), and the `CopyTalk` head (line 165). Shown by code.
- **Parameter counts (shown, arithmetic from the JSON):** allptr `params` = 9,297,240 and copytalk `params` = 9,303,405 (`allptr-gen-ct-seed0.json`, `copytalk-gen-ct-seed0.json`). The difference 6,165 = 8,221 (copy head) − 2,056 (pointer layer, Linear 256→8). The copy head = span 514 + q 256 + LN 512 + gate 256·27+27 = 6,939, total 8,221. So the copytalk head is about **8k parameters, not ~2M** as the digest's row 7 says. The whole copytalk model is about 9.30M, of which the core is 9,007,790. The "~2M" label is not supported by this code. (shown by arithmetic; the digest row 7 cites an RTC/RESULTS-CT.md that is not in any git ref I searched)
- **92.6% (allptr, round 4):** FRESH set, pretrained frozen LM plus from-scratch core/reader/adapter. (shown, `RESULTS-R4.md` line 12)
- **8-shot 75.0% (1.2B, FRESH):** pretrained, no training. (shown, `ANALYSIS-R6.json` `lm_fewshot.fresh` 75.0)
- **66.1% (350M system, FRESH):** not verified from raw data. Two secondary docs state it: `custom_io/research/baselines.md:87` ("bare LFM2.5-350M scores 33.9% zero-shot and 50.0% 8-shot against 75.0% for bare 1.2B, and the 350M system reached 66.1%") and `results-digest.md:29` ("350M LM as reader and talker | allptr recipe | fresh 66.1% (60.9-72.0)"). The arithmetic is consistent: 66.1 − 50.0 = 16.1 (the digest's "+16.1"), and 92.6 − 75.0 = 17.6 (the "+17.6" for 1.2B). LFM2.5-350M is a pretrained Hugging Face checkpoint (`baselines.md:26`). I could not find the cited source file `RESULTS-SMALL-LM.md` (`hearer-talker/`) in any git ref (`git log --all` and `ls-tree --all` found nothing) or on disk (find, maxdepth 6, under the projects and Desktop folders). No 350M run code is in `reasoner_ptr/real/english`. So the 66.1 is "reported, not verified". Instruct vs Base is unknown. (suggested: pretrained and frozen, like the 1.2B recipe)
- **Digest row 7 ("~2M")** and **row 10 (66.1)** are the two numbers that I could not match to primary files. Treat them as reported, not checked.

## Open questions and handoff

1. Run the decisive control: allptr with the core skipped (prefix and pointer from zeros or from the reader query only) on the same unseen sets, with six seeds. Marks proposed here (not yet fixed by anyone, not run): pass = core-on minus core-skipped gap of at least +5 points on the six-seed pooled unseen mean, with the CI excluding 0; fail = gap within ±3 points.
2. Run a cross-kind donor shuffle (donor from a different family, same length), not just a same-length swap. Untested.
3. Rerun the seed-0 lesion twice on the same weights to measure GPU/batch noise on the 50 changed answers. Untested.
4. Locate `RESULTS-SMALL-LM.md` or the 350M run files. Until then the 66.1 stays "reported".
5. Confirm where "~2M" in the digest comes from (RTC branch? a different head?). The code in `reasoner_ptr/real/english` gives an 8,221-parameter head.
6. The taxonomy breakdown for allptr (wrong location 2.9, boundary 12.5, gate/decode 8.6, yes/no flip 2.3) was given in the task. I read only the head of `ct_taxonomy_stdout.txt` and did not re-derive these.

Scratch copies (not in this folder): `/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model/37c50658-739a-4a96-928b-102f2d7b8dad/scratchpad/` (`run_english_D8.py`, the row JSONs, `ACT.json`, `AR6.json`).

Times: the CT round is dated 2026-10-04 in `RESULTS-CT.md`. Source notes give UTC; for example 21:07 UTC is 17:07 ET (EDT, UTC−4).
