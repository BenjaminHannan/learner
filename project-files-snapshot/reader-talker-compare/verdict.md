# Did the helpers help? Verdict on the two reader/talker reports

> **Superseded (2026-10-09).** This is the 10-04 verdict on the two helper designs. Its 'Merged recommendation' (a ~2M copy-and-gate
> talker on the borrowed LFM2.5 language-model path) is out of date and dropped. Plan B replaced that path: a frozen EmbeddingGemma 2
> reader (about 271M), our own thinker (about 100M) and our own talker (about 25M), about 397M in all (architecture/FINISHED-MODEL-2026-10-09.md,
> sections 1 and 2). Read the measurements here as a 10-04 record; do not act on the recommendation.

Judged 2026-10-04, finished about 3:25 PM ET. Judge: one Opus thread. Inputs: `blind/X.md`, `blind/Y.md`
(made by a Sonnet subagent from `armA-report.md` and `armB-report.md`, random order, process details stripped).
Supporting folders (`armB/`) were not read before scoring.

## Short verdict

- **Scores:** X (solo) **36/50**, Y (with helpers) **39/50**. The helpers' report is better, by a modest margin.
- **Where Y won:** a sharper deciding test, and a better fit with Ben's design (the talker should turn the core's
  state into words, not re-read the question). **Where X won:** correctness. I found no errors in X and 3 small ones in Y.
- **Worth it?** Partly. It took 5.4x the time (28 min vs 5 min 14 s), several times the tokens (7 helpers) and $0.15.
  For a decision that steers several days and a few dollars of GPU, yes. For routine shortlists, no.
  Two limits on this verdict: the test can't separate "helpers" from "5x more time", and Y's own notes say the
  ranking and test design (the parts that won) were done by the lead itself.
- **Best next test (merged):** Y's copy-and-gate talker test (tiny talker vs today's talker vs tiny talker with no core),
  run after round 7 lands, with three fixes listed at the end.

## Blinding was imperfect (read this first)

Before I opened either report, this thread's root message from the coordinator named each arm's top pick
(solo = the 350M model; helpers = a 2M talker plus a measured 2-2.8x truncation speedup). Y's caveats also still
mentioned "four literature surveys" and supporting notes. So I knew which report was which with high confidence
while scoring. I scored from checked evidence, but these are **not truly blind** scores.

## Spot checks

Repo facts were checked at commit `04c4c528e` (the runner before round 7), branch `claude/project-thread-ajo58u`.
Model facts were checked against Hugging Face API and config files, and papers against arXiv abstracts or full text.

### Report X (13 checks, 0 errors)

| # | Claim | Result |
|---|---|---|
| 1 | Reader takes the LM's last layer (`hidden_states[-1]`) | ✓ `run_english.py:128` |
| 2 | Eval `generate()` has no KV cache | ✓ `run_english.py:173-185` re-runs the full prefix each token |
| 3 | Round 4: mean 92.6%, seeds 89-96%, bare 8-shot 75.0%, zeroing the core gives 0% | ✓ `RESULTS-R4.md` |
| 4 | FRESH-EN-R3 has 192 questions | ✓ 48 passages x 2 versions x 2 questions |
| 5 | Pass marks committed before any run (PR #36, `51fcdcfb5`) | ✓ commit exists (18:43 UTC), adds `design/research/PASS-MARKS-SMALL-LM.md` |
| 6 | LFM2.5-350M revision `9e6c6cc…` exists, width 1024, 16 layers | ✓ HF API and config. It is instruction-tuned, like the 1.2B-Instruct in use, so the swap is clean |
| 7 | Same tokenizer as the 1.2B (same tokenizer.json sha) | ✓ both `df1d8d5e…` |
| 8 | Bare LM decodes ~70 tok/s at batch 1; our prompt read is 3-5x slower at batch 1 | ✓ 70.6 tok/s; measured 3.5-3.6x (the range is a bit loose) |
| 9 | Flan-T5-base 248M, -large 783M | ✓ 247.6M, 783.2M |
| 10 | T5's vocabulary cannot write `{ } <` or newline | ✓ none of the four are in flan-t5-base's vocab |
| 11 | ModernBERT-base 149M | ✓ 149.7M |
| 12 | Skean 2025, Gromov 2024 and ShortGPT support "middle layers read well, deep layers can be dropped" | ✓ abstracts |
| 13 | Predictions (labelled suggested): the 350M is no faster at batch 1, about 3x faster at batch 64, and a half-depth read is about 2x faster | ✓ later confirmed by Y's own measurements: 3.9 vs 4.1 ms, 3.1x, 2.0x |

Weak spots, not errors: mark M2 is implied by M1 (every 1.2B seed is at least 89, so any seed within 10 points is at
least 79, above 75). The test uses only the in-family fresh set, where the bigger LM's extra knowledge matters least
(X says so). Zeroing the core is a crude lesion.

### Report Y (14 checks, 3 small errors)

| # | Claim | Result |
|---|---|---|
| 1 | Reader is a 78k-param per-token MLP with no attention | ✓ `HumanInputProjection`: LN(2048) + 2048→32→256 = 78,112 params |
| 2 | Talker input = 8 pooled + 8 pointer + all prompt embeddings; greedy, 12 steps, no KV cache; LM loaded in fp32 | ✓ `run_english.py:39, 55, 123-148, 173` |
| 3 | LFM2.5-1.2B has attention at layers 2, 5, 8, 10, 12, 14; embedding table 65,536 x 2048 = 134M (about 11%) | ✓ config.json |
| 4 | Round 6 second unseen set ties the bare LM (78.2 vs 77.6); round 5 bare 8-shot 67.7%; zeroing gives 0% and is called crude | ✓ `RESULTS-R5/R6.md`. `RESULTS-R2.md` already suggests the shuffled-core lesion |
| 5 | A ~33M from-scratch reader and talker is sketched in design/v3/24 | ✓ `design/v3/24-talker-from-scratch-fable-design.md` ("≈ 33 million") |
| 6 | arXiv ids (I checked 19 of its 82) | ✓ all 19 match the named papers |
| 7 | Skean: middle layers beat the last on 32 embedding tasks | ✓ abstract |
| 8 | SVAMP: a model with the question removed still scores 60-77% | ✓ best 64.4% (ASDiv-A) and 77.7% (MAWPS) |
| 9 | Singh & Strouse: left-to-right digit grouping hurts arithmetic | ✓ abstract |
| 10 | LFM2-350M scores 30 on GSM8K vs 58 for the 1.2B | ✓ model card, but the 58 is LFM2-1.2B, not the LFM2.5-1.2B in use (minor) |
| 11 | Its correction: "Distilling step-by-step" 770M T5 beats 540B PaLM on ANLI **and SVAMP** | ✗ ANLI with 80% of the data is right. On SVAMP it only matches PaLM after adding ASDiv data |
| 12 | Smaller ready-made reader: **LFM2**-350M, "same tokenizer" | ✗ omission. The text vocab is the same, but it misses **LFM2.5**-350M, which is the same generation, instruction-tuned, has a byte-identical tokenizer and scores better (IFEval 77 vs 65) |
| 13 | Caveat: scores come "from the post-trained model cards, not from the Base reader" | ✗ minor. The runner uses LFM2.5-1.2B-**Instruct** (`run_english.py:33`), not a Base model |
| 14 | Speed table (10 readers on a 5090) | Not re-measured. It is consistent with the PR #35 bench, where bf16 = fp32 at batch 1, which supports "batch 1 is overhead". Its suggestion that fp32 is part of the 52 ms sits a little uneasily with that |

Y's report also says that two of its four literature surveys were written from memory, and that the supporting notes
still contain the errors it caught.

## Scores (1-10)

| Criterion | X | Y | Why |
|---|---|---|---|
| Correctness | **9** | 8 | X: 13 of 13 checks hold, and its speed predictions were later confirmed by Y's measurements. Y: strong (19/19 ids, code facts exact) but has 3 small errors and an omission in the reader fallback |
| Quality and novelty of ideas | 6 | **8** | Both lists contain the same core ideas (a pointer/copy talker, a truncated reader, a smaller LFM). Y adds the key argument: shrinking the reader saves no counted size while the talker is the full 1.2B, and the second pass may let the LM answer without the core. X's best insight is that batch-1 speed depends on depth, not width (correct). |
| Fit with Ben's goals | 7 | **8** | X attacks whole size directly (0.36B system vs bare 1.2B is literally mark M2) and mentions Minecraft, but keeps the LM re-reading the question. Y matches Ben's design (the talker turns the core's state into words) and tests whether the core thinks ("skills first"), but its first step leaves the size at 1.17B and its fallback picks the weaker LFM2-350M. No Minecraft mention. |
| Rigor and cheapness of the test | 7 | **8** | X: zero code, one flag, about $1, marks committed. But it uses only the in-family set and a crude lesion, and a pass can't say whether the core or the LM did the work. Y: 4 test sets, a control rerun, a no-core arm, a shuffled lesion, per-answer-type breakdown and a pre-planned follow-up. It needs a new head (about one class) and $1.5-2, and its marks are not committed yet. |
| Clarity for Ben | 7 | 7 | X is short and clean but has no plain summary and uses some jargon. Y is denser and longer, but leads with "the short answer" and ends with a plain summary for Ben |
| **Total** | **36** | **39** | |

## Unblinded: cost and time

| | Solo (X) | Helpers (Y) |
|---|---|---|
| Wall time | 5 min 14 s | about 28 min (2:42 to 3:10 PM ET) |
| Workers | 1 Opus | 1 Opus lead + 7 Sonnet helpers (6 in parallel) |
| Cash | $0 | about $0.15 Vast (speed probe) |
| Errors found by me | 0 | 3 small |

**What the helpers actually added:** the measured speed table, which turned X-style guesses into facts, plus a code map
and a wider literature base. Two helpers wrote from memory, which created citation errors that a seventh helper then had
to catch. One error in its fix list is still wrong (check 11). By Y's own account, the winning parts (the talker-first
ordering and the copy-talker test) were written by the lead.

**Verdict:** the helpers made the report better by about 3 points out of 50 (about 8%). The gain is concentrated where it
matters most, the deciding test: Y's test answers "is the core doing the thinking?", and X's test cannot. That is worth
5.4x the time for a research fork like this one. It is not worth it for a quick shortlist, where solo was faster and more
accurate. This single pair can't tell whether a solo lead given 28 minutes would match Y.

## Merged recommendation: the single best next test

**Copy-and-gate talker vs today's talker, with a no-core control** (Y's test), with three fixes taken from comparing the reports:

1. **Wait for round 7.** It is running now on 6 RTX 3090s (boxes created 2:57-2:58 PM ET). Its `ptr` arm (the talker sees
   only the core's vectors, no question words) is the first half of Y's question. Use round 7's exact recipe
   (`--gen 8000 --kinds 6 --block-r6`) so its `allptr` rows can serve as the control if the seeds reproduce. That cuts
   the test to 12 runs, about $1. If `ptr` falls more than 10 points below `allptr`, the core is not carrying the answer:
   run the no-core diagnostic first.
2. **Arms, 6 paired seeds:** `copytalk` is a ~2M head on the core's final states. It has a start/end pointer over the
   prompt, a small word head (yes/no plus training answer words, tied to the frozen embeddings) and a 2-way gate (drop
   Y's "calculator" branch, since the English runner has none). There is no second LM pass. `copytalk-nocore` is the
   same head placed on the reader output. Lesion: shuffled core, not zeroing.
3. **Marks, fixed and committed before training:** Y's marks, stated as paired 95% intervals like round 7:
   - PASS: copytalk minus allptr has a lower bound above −5 on the pooled unseen kinds (NEW-KINDS-R5 + NEW-KINDS2-R6).
   - CORE IS REAL: copytalk beats copytalk-nocore by at least 10 points there.
   - FAILS: a mean below −10, or below the bare 8-shot score on NEW-KINDS-R5 (67.7%).
   - Also report the FRESH set and accuracy by answer type.

**If it passes, the next single change is the reader.** Use copytalk in both arms and compare **LFM2.5-350M** (X's pick:
byte-identical tokenizer, instruction-tuned like today) with the first 8 layers of the 1.2B. Both against the full 1.2B
reader, same marks. That is the path to a ~0.36B whole system that has to beat the bare 1.2B at 8-shot, which is Ben's
size goal.

**Optional side run (zero code, about $1):** X's 350M swap can run in parallel now. Read it as "is 1.2B needed for the
in-family set", not as evidence about the core, because the talker still re-reads the question.
