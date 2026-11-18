# D2: fact-check of the problem statement, and what the roadmap says about the talker

Written 2026-10-08, 20:56 EDT by a read-only Haiku worker. Nothing in `/Users/ben-hannan/Desktop/projects/beautiful-model` was edited. No commits, no GPU, no training. Every number below was read from a branch file, not taken from memory.

Labels: **shown** = I read it in a file (path:line given). **suggested** = my reasoning or a literature pointer. **untested** = nothing in the repo tests it.

Which line each result belongs to:
- **English-QA line** (frozen LM as reader and talker; "allptr"; "copy talker" in the CT experiment). Sources: branch `origin/claude/project-thread-utxkpw`, `reasoner_ptr/real/english/`, and `origin/claude/custom-reader-talker-4x309r`, `custom_io/research/`.
- **B2 skills / 8a ladder line** (the looped thinker, letter or EmbeddingGemma reader, NUM/WORD/GEN answer head). Source: branch `origin/claude/project-thread-yha868`.
- The sources never use the words "card" or "village". The line split above is my classification (suggested). I did not check whether either line is the village model.

---

## 0. Where the sources live (access check)

- `/mnt/project-files/` does not exist on this machine (`ls` failed, shown).
- The digest's own header says its key sources sit under `/mnt/project-files/` (`RTC`, `N`, `notes`). The most important one for the 350M number, `N/hearer-talker/RESULTS-SMALL-LM.md`, is in none of the three branches I searched (`git ls-tree -r` found no match for `SMALL-LM` or `hearer-talker`). So that number is only shown as a summary in other files.
- The roadmap folder `/mnt/project-files/whole-model-roadmap/` is also absent. The branch files point to it (`reviews/astra-diagnose-...md:30,66`).

---

## A. Problem-statement claims, checked against primary files

| # | Claim as written in the task | Verdict | Primary source (file:line) | Notes |
|---|---|---|---|---|
| A1a | "pretrained 1.2B LM as reader+talker ('allptr') 92.6% on fresh English QA" | **Shown.** The 1.2B is `LiquidAI/LFM2.5-1.2B-Instruct`, an off-the-shelf instruct model, frozen. | `RESULTS-R4.md:12` (row "allptr + generated (round 4)", fresh exact 92.6%). Model id: `run_english.py:33` (default `--lm`) and `gen_english.py:337`. Digest: "Sandwich = frozen 1,170M LM + ~9.3M trained parameters" (`results-digest.md`, text before section A). | Trained parts: 8 pointer vectors plus all prompt-word embeddings (allptr). Test: 192 fresh questions over the six practised kinds (`RESULTS-R4.md:3`). Trained with 8000 generated examples per seed. Six paired seeds. Seeds span 89 to 96 (`RESULTS-R4.md`, "Seeds are now tight"). The same six-kind arm scores **92.2** on this same fresh set in the R6 rerun (`RESULTS-CT.md` table, FRESH-EN-R3 row; `RESULTS-R6.md`, "Old kinds (fresh set): twelve 92.0 vs six 92.2"). |
| A1b | "pretrained 350M version 66.1%" | **Shown as a summary only. Pretrained, not from scratch.** The 350M model is `LFM2.5-350M`, bare pretrained, with the allptr recipe on top. | `baselines.md:87` ("bare LFM2.5-350M scores 33.9%... and the 350M system reached 66.1%"). `results-digest.md:29` (row 10: "350M LM as reader and talker | allptr recipe | fresh 66.1% (60.9-72.0)"). | The primary file `N/hearer-talker/RESULTS-SMALL-LM.md` is not on this machine or in these branches. **Open:** the 350M run may not have had the same 8000 generated examples or budget as the 1.2B run. No source states this, so it is **untested**. |
| A1c | 66.1 vs 92.6 as a size comparison | **Shown as quoted, but confounded.** | `results-digest.md:57` (section B, row 5: "LM size sets the ceiling: 350M system 66.1 vs 92.6"). | Different LM and possibly different training budget. A size-only comparison is **suggested**, not shown. |
| A2 | "copy-style talker 13.6% vs 78.2% on unseen kinds (PR #37)" | **13.6 and 78.2 are shown. The 78.2 is a pooled six-kind number, not the twelve-kind one.** I could not check PR #37 in these branches (**untested**). | `RESULTS-CT.md:8` and table row at `:15`: "Unseen kinds, pooled (384 Qs) \| 78.2 \| 13.6 \| 12.9". Digest row 7 at `results-digest.md:24`. | The 78.2 is the six-kind allptr mean over two unseen sets: (NEW-KINDS-R5 81.1 + NEW-KINDS2-R6 75.3) / 2 = 78.2 (shown, arithmetic from `RESULTS-CT.md` table rows). **Collision:** `RESULTS-R6.md:20` ("all \| 78.2 \| 75.3 \| 77.6") gives 78.2 for the **twelve**-kind model on the second unseen set alone. Two different things share the value 78.2. The copy-talker comparison uses the pooled six-kind figure. The digest uses both (`results-digest.md:21` and `:24`) without saying which is which. The copy talker is ~2M parameters with no second LM pass (`results-digest.md:24`). |
| A3 | "shuffled-core lesion 73.2 -> 73.2 with 334/384 identical" | **Shown, but one seed, read only, and the baseline is a rerun.** | `RESULTS-CT.md:28-31`: "control rerun scored 73.2%", "shuffled core... still scores 73.2%", "334 of its 384 answers were exactly the same". Labelled "Shown (one seed, read only)" in the source. Also `results-digest.md:26` and `:53`. | The 73.2 baseline is the rerun's own control, not the six-seed 78.2 mean. The R6 seed-0 value was 82.3, and the rerun gave 73.2 on a different GPU, outside the expected 3-point band (`RESULTS-CT.md:45-47`). So "73.2 -> 73.2" compares two numbers from the same rerun. The lesion is on the **1.2B allptr LM**, not on the copy talker. |
| A4a | "bare 8-shot 75.0" | **Shown.** | `RESULTS-R4.md:14`: "bare 1.2B LM, 8-shot (the bar) \| 75.0%" (fresh exact). | Naming hazard: the same row shows **77.6% as the "contains" score** on the fresh set (`RESULTS-R4.md:14`). That 77.6 is a different metric from the unseen-set 77.6 below. |
| A4b | "350M 33.9 / 50.0" (zero-shot / 8-shot) | **Shown as summary only.** | `baselines.md:87`; `results-digest.md:29` and section D ("bare LFM2.5-350M 8-shot 50.0 (zero-shot 33.9)"). | Primary file not on this machine (see section 0). |
| A4c | "unseen-set bare 77.6" | **Shown.** | `RESULTS-R6.md:20`: "bare 1.2B, 8-shot" column, "all \| ... \| 77.6". `baselines.md:88`: "77.6% (round-6 second unseen set)". | Round-5 unseen bare: 67.7 (`RESULTS-R6.md`, "vs bare 8-shot 67.7%"; `baselines.md:88`). |
| A4d | Arithmetic check on the trained-parts gain | **Shown.** | 92.6 - 75.0 = +17.6 (`RESULTS-R4.md:17`: "+17.6, CI +14.7 to +20.6"). 66.1 - 50.0 = +16.1 (`results-digest.md:29`). | Both match the sources. |

**Summary of section A:** every quoted number is in the repo. Two are only summaries (the 350M figures), because their primary note is on the project-files share. One label is misleading. "92.6% on fresh English QA" is the **practised-kinds** test, with human-written wording. The "13.6 vs 78.2" test is on **unseen kinds**. The problem statement puts them side by side, but they are different tests. The copy talker scores 58.7 (human wording) against 92.2 for allptr on the practised fresh set (`RESULTS-CT.md` table, FRESH-EN-R3 row). It scores 97.4 on generated wording with the core, but 41.6 with the core skipped. So the copy talker is competitive only when wording matches training.

---

## B. Roadmap on `origin/claude/project-thread-yha868`

### B1. Planned component sizes

| Component | Stated size | Source | Label |
|---|---|---|---|
| Reader: EmbeddingGemma 2 (frozen) | 271M parameters, about 768 numbers per word piece | `reviews/gpt-diagnose-b2-no-growth-2026-10-08.md:21` | shown (text) |
| Reader size in EGE line | "about 300M" for EmbeddingGemma's frozen part | `design/8a-bigger-is-better-2026-10-07.md:186` | shown (text); 300M vs 271M is a minor discrepancy |
| Thinker (the trained looped core) | "~100M build (8c)"; "the ~400M build (thinker about 100M)" | `design/8a-bigger-is-better-2026-10-07.md:100` and `:134` | shown (text) |
| Talker | **Not sized in these docs.** | grep for "25M", "talker" + size across `design/` and `reviews/` on this branch found no sizing. The only "25M" hits are unrelated (e.g. `design/v3/30-modes/35-...:45`, "Simple English Wikipedia \| 25M"). | **The "~25M learned talker" in the task is not on this branch.** It may be in the unavailable `/mnt/project-files/whole-model-roadmap/`. **Suggested:** 271 + ~100 + ~25 ≈ 396M, which fits "~400M", but no document says the 400M includes a 25M talker. **untested.** |
| B2 trained size, EGE arm | "about 30M trained" | `design/8a-bigger-is-better-2026-10-07.md:186` | shown (text) |
| Deep 10M B2 with copy talker | 10,254,105 parameters | `design/8a-bigger-is-better-2026-10-07.md:282` | shown (text) |
| Plain match | 13 layers, 10,368,768 | same, `:282` | shown (text) |
| Ben's bar (2026-10-08) | "the model must gain **more** from each size step than the plain model does" | `reviews/astra-diagnose-b2-no-growth-2026-10-08.md:64` and `design/8a-g-gemma-growth-2026-10-08.md:9-12` | shown (text) |

### B2. What "the current talker" is in the B2 line

The B2 answer head is **not** the English-QA copy talker. It is a mode head after the last loop, which chooses one of three answer modes:
- **NUM**: print the value of the slot an answer pointer picks.
- **WORD**: copy word *k* of the prompt.
- **GEN**: generate characters. Each register token emits one character through a linear readout tied to the character table, mixed with a pointer-copy distribution over prompt characters. It is **not autoregressive**. The design had 36 register tokens, but the runs used 9.

Sources: `reviews/gpt-diagnose-b2-no-growth-2026-10-08.md:72-76` (talker description); `reviews/astra-diagnose-b2-no-growth-2026-10-08.md:16` (`ledger.py`: "NUM / WORD / GEN talker"). Both say this. The 8a docs call it the "copy talker" (`design/8a-bigger-is-better-2026-10-07.md:21`, `:82`, `:282`).

**Naming collision (shown):** "copy talker" means two different things. In the B2 line it is the NUM/WORD/GEN mode head. In the English-QA line (`RESULTS-CT.md`) it is a ~2M pointer + word head + gate on core states, with no second LM pass. Any cross-line claim needs the full name.

### B3. Stated diagnosis of the answer writer

**Shown:** the two files `reviews/astra-diagnose-b2-no-growth-2026-10-08.md` and `reviews/gpt-diagnose-b2-no-growth-2026-10-08.md` are **prompts asking reviewers to diagnose**. They contain no conclusion. Each lists candidate explanations for "B2 does not improve with size".

Candidates that name the answer writer (quoted from the prompts):
- "the non-autoregressive GEN head can't use more capacity on web text" (GPT review, candidate list just before the question block, around line 160).
- "B2 is already saturated on the families its calculator covers, and its remaining errors are in pattern / rule families that its fixed program ops and parallel GEN head can't express" (same list).
- "Check whether W's small gain could come from the talker answering without the loop (its leak rose)" (`astra-...md:61`).
- "anything else has to be produced by WORD copy or the parallel GEN head" (`gpt-...md:135`).

**Leak data (shown)**, from the GPT review's shape-probe table (`gpt-...md`, table at lines 143-147). Leak = score with the loop switched off (0 rounds). The answer writer can answer without the loop, so leak is a diagnostic for the writer:

| Arm | Seed 400 / 401 | Leak (400 / 401) |
|---|---|---|
| 3M B2 | 71.59 / 73.21 pooled-5 | 5.3 / 9.8 |
| Deep 10M B2 | 71.62 / 73.49 | 0.6 / 0.1 |
| R (reader grows) | 72.32 / 71.75 | 0.0 / 0.0 |
| W (wider, shallower) | 73.16 / 73.68 | **10.9 / 12.4** |

W's small gain comes with a leak rise (shown, `gpt-...md:153`).

**Known setting bug that touches the answer writer (stated in both reviews, shown as text; I did not read the code):**
- Every 8a B2 run used **N_REG = 9** register tokens, not the designed 36 (`astra-...md:22-24`; GPT review, the GEN description).
- GEN targets were **cut to the first 8 characters**. About 191,000 of 1,655,902 pool rows have answers over 8 characters (`astra-...md:28`; `gpt-...md:50-55`).
- The fix is "addendum D" in the unavailable `/mnt/project-files/whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md` (`astra-...md:30`). I could not check it.

### B4. Current status in that branch (shown)

- 8a result: B2 with the letter reader gained +0.49 from 3M to 10M. The plain step model gained +3.77 on the same pool (`design/8a-g-gemma-growth-2026-10-08.md`, section 0).
- EGE (B2 with frozen EmbeddingGemma 2 in front): +2.67 pooled-5 over B2 on the q33 data, ahead on 6 of 6 seeds, failing only the zero-round leak mark (`8a-g:17-18`).
- Next gate: G1 (8a-G, EGE vs plain with the same Gemma front, 3M to 10M), to be re-run with the bug fix. Nothing in the repo says it has run.

---

## C. Talker ideas: proposed, never tested, and already shown not to work

### C1. Proposed, never tested (`custom_io/research/results-digest.md`, section C, lines 64-88, all labelled [U])

- **Talker options (digest lines 70-74):** 2-layer cross-attending decoder (5-7M); program head (op + operand pointers + calculator); Perceiver-IO query decoder; fixed answer slots + stop; Flan-T5 hear-and-talk; shared reader/talker embedding table; talker-to-reader round-trip self-check.
- **Copy talker note (digest line 74):** "Copytalk was tested only as one regularisation-free linear head." `RESULTS-CT.md:48-49` says the head's training loss went to about 0, and suggests "a different head might do better on boundaries. It is unlikely to close a 64-point gap" (**suggested**, by the author).
- **Structured interface (line 75):** reader emits slots/ops, deterministic executor, template talker, with SVAMP-style perturbation tests.
- **Core-forcing (lines 76-80):** vectors after the question; two-path loss with a prompt-free pass; shrink LoRA to a one-layer residual edit; random round count; batch-16 accumulation.
- **Deep exit (line 81):** exit into LM attention layers; learned Perceiver pooling; middle-layer features.
- **Latent-supervision papers (line 82):** CODI 2502.21074, implicit-CoT distillation 2311.01460, stepwise internalisation 2405.14838, LRT 2609.01117, progressive mask 2605.07106.
- **Pipeline arms S vs M (line 83):** queued, no results.

### C2. Critic notes relevant to the talker (`custom_io/research/critic.md`, 57 lines)

- **Character-level output (lines 36-37), suggested:** answers are at most 8 characters in train and 12 in dev, and 61% are numbers up to 4800, so "the output should be character-level with copying, possibly fixed slots read out in one pass".
- **Lesion design without an LM (lines 42-44), suggested:** add a core-skipped arm with the same reader and talker trained; fix the talker's access to the input in advance; use the donor-swap check.
- **Shortcut precedent (line 52):** SVAMP 2103.07191, and seq2tree / GTS / Graph2Tree, show solvers answering without reading the question. **Suggested** as a risk for any talker that cannot re-read the question.
- **Steps vs answer-only (line 14):** cites `looped-reasoners` (2603.21676), which says answer-only supervision extrapolated better. The repo measured the opposite on the step-based arm (+11.8 fit, +21.7 held-out).

### C3. Already shown NOT to work (`results-digest.md` sections A and B, and `RESULTS-CT.md`)

| Idea | Result | Line |
|---|---|---|
| Pool-only exit (8 averaged vectors) | 0.0% on unseen answer words | digest row 1 (`results-digest.md:18`) |
| Pointers only (talker sees 16 core vectors, no question words) | 18.9% pooled, vs allptr 82.9 | digest row 6 (`results-digest.md:23`) |
| Question-first + reused cache | -7.6 pooled (CI -8.7 to -6.5); no speed gain | digest row 5 |
| Copy-and-gate talker, ~2M | unseen kinds 13.6% vs 78.2; human wording 58.7 vs 92.2 | `RESULTS-CT.md:8, :15, :26` |
| Same talker, core skipped | unseen 12.9; core adds +0.7 (CI -2.0 to +3.4) | `RESULTS-CT.md` table |
| Reader + core with direct answer-class head, no LM | fit 13-15%, held-out ~10% | digest row 17 |
| Rank-8 LoRA on all LM linears | fit -37.8: LM collapses | digest row 16 |
| Fit-screen knobs (reader 32->256, 8 rounds, lr x0.3, etc.) | fit gains +0.2 to -2.5 | digest row 15 |
| Core 4x bigger (2->8 blocks, 9.0->35.8M) | new-kinds +1.9 (CI -0.95 to +4.77) | digest row 11 |
| Smaller pretrained readers (LFM2-350M/700M, SmolLM2, Qwen3-0.6B) | speed only; 30-layer models slower at batch 1 | digest row 14 (`:33`) |
| From-scratch talker101 (28.85M) + record fine-tune | grammar test 67.4% vs 70% bar: FAIL | digest row 24 (`:47`) |
| From-scratch ears (0.24M) vs borrowed SciBERT | seen 1,867 / 1,847 vs 1,954 of 2,000 | digest row 23 |

Two results need care:
- The **zero-core lesion** gives 0-5% in every round (digest row 9). `RESULTS-CT.md:33` says this is "a shock to the LM, not evidence that the core matters" (**shown**, by the author's own reading).
- The **25M-talker idea, the 33M ears/thought/mouth design, and the 416-number typed thought** are "designed, not built" (digest row 25, `[U]`). No result.

---

## D. Summary for the orchestrator (plain language)

- The problem statement's numbers are all in the repo. Two come only from summaries, because the primary note is on the unavailable project-files share.
- Two things need correcting before anyone builds on them:
  1. The 78.2 in the copy-talker comparison is a pooled six-kind figure. The same value also appears as the twelve-kind score on one set. The digest blurs them.
  2. The 73.2 lesion is one seed, read only, from a rerun whose own baseline came in 9 points below the original run. It says the allptr LM barely reads the core on unseen kinds. It does not show a general result.
- The "copy talker" name means two different things in the two lines. The B2 answer head is NUM/WORD/GEN. The English-QA copy talker is a ~2M pointer head.
- The "~25M learned talker" is not stated on the yha868 branch. Thinker ~100M and reader 271M are stated.
- No roadmap document states a diagnosis of the answer writer. The two B2 review files are prompts. They name candidate causes: the non-autoregressive GEN head, the 9-register setting bug, and the 8-character GEN cut. The leak numbers (W leak 10.9 / 12.4) suggest the writer may answer without the loop.

---

## E. Open questions and what a next agent should do

1. Get `N/hearer-talker/RESULTS-SMALL-LM.md` (the 350M source) and `/mnt/project-files/whole-model-roadmap/` (the "~25M talker" and addendum D). Neither is on this machine.
2. Confirm whether the 350M run used the same 8000 generated examples and budget as the 1.2B run. Until then, the 66.1 vs 92.6 comparison is confounded (**untested**).
3. Check PR #37 for the copy-talker claim. I did not look for it in these branches (**untested**).
4. In the B2 line, check whether addendum D fixes the GEN cut to 8 characters and the N_REG = 9 setting. This needs the code, not the reviews.
5. Keep "copy talker (B2 mode head)" and "copy talker (CT, ~2M)" separate in every write-up.
