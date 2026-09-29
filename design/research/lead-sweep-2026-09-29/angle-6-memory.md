# Angle 6: memory for assistants (LongMemEval, retrieval vs parametric, small readers)

Written 2026-09-29 01:5x UTC (`date -u` at start: Tue Sep 29 01:53:59 UTC 2026). Research only: nothing run, no repo file touched except this one.
Labels: **shown** (source's measured result, or a repo file) / **suggested** (my reasoning) / **untested**. **Author-only** = not independently reproduced. Reading depth is stated per source: **A** = abstract page or search snippet only, **F** = fetched page text (a summariser model read it, so numbers are second-hand until Ben or Astra opens the paper).
Small card experiments and the village model are kept out of this file. Everything below is about the notebook/talker/sleep side, not the maze reasoner.

## What already exists in the repo (so I do not repeat it)
- `handoff/director-roadmap.md`: item 1 (joined reader-reasoner-talker, notebook recall with sources, "I don't know") NOT STARTED, nothing has run end to end. Item 6 (LongMemEval final, never trained on it) waits behind item 1.
- `design/v3/30-modes/382-memory-store-interface.md`: one append-only store, `remember()` / `recall(k, sources)` with cited turn ids, MiniLM retriever, verifier rd-371 ("does this source support this statement?") before stating anything, else "I don't know". Practice ruler already named: LoCoMo practice (`390-public-bench-plan.md` keeps LongMemEval as the final exam).
- `standing/05`: y1t trained doubt was NO-GO (22 right / 20 wrong candidates); plain 1B failed at copying a grid (25/39/28 of 100). Talker retelling untested.
- `final-sweep-2026-09-19/02-memory.md`: token-level addressing, query-drift compensation; those are about the village card model, not this file.
- `memorylab/` holds code only (bench, model, storage, tasks, checkpoint, controls, positive_controls, transformer_model, experiment). No README. That is the small card-experiment side; I do not draw claims from it.

## Sources (strongest first)

**1. LongMemEval, Wu et al., ICLR 2025, https://arxiv.org/abs/2410.10813 (F, html v1).**
- shown: 500 questions in 7 types (single-session user / assistant / preference, multi-session, knowledge-update, temporal, abstention). S version about 115k tokens of history per question; M about 500 sessions, ~1.5M tokens. Judge GPT-4o agrees 97-98% with humans.
- shown: long-context reading collapses vs the "oracle" (only evidence sessions given): GPT-4o -30.3 points, Llama-3.1-8B -55.1, Phi-3-Medium -45.9. Chain-of-note did not close it for the 8B (-66.3). Search snippet: Llama-3.1-8B about 42-45% vs 71% oracle on S. Closed-book about 3-4% (so the questions really need the history).
- shown: indexing tricks each give a few points: store rounds (turn pairs) not whole sessions (helps GPT-4o; ~nothing for the 8B), keys expanded with extracted user facts (+~4 points recall@5/10, +~5 points answer accuracy), time-aware query expansion (+11.4 recall for rounds on temporal questions), JSON-structured notes plus chain-of-note reading (up to +10 absolute). Extracting facts and storing only them HURT overall but helped multi-session counting.
- Independent (the benchmark itself); the design tips are the authors' own but widely re-used.
- Caveat: reader models tested were GPT-4o, 70B, 8B. **No 1-2B reader in the paper.** So "what does a 1-2B reader score" has no primary number that I found (see A below).

**2. MemDelta, https://arxiv.org/abs/2606.29914 (F; abstract level).** An independent controlled-baselines audit on LongMemEval-S with one fixed reader (Qwen3.5-9B on their own machines).
- shown (their measurements): no memory 2%, plain verbatim RAG 47%; verbatim RAG vs full-context GPT-4o-mini 47.2 vs 49.8 (p = 0.34, a tie). Swap ONLY the embedding model: +6.2 points (n = 500, p = 0.004), which is the size of gains vendors credit to new architecture. Mem0 vs plain RAG on a subset: 72.7 vs 73.9 (p = 1.0) once the same embedder is used; the earlier "Mem0 wins" appeared with a weak MiniLM baseline (61.4 vs 72.7). Model family flips the ranking: Gemini gains +14 from full context, Sonnet gains +31 from RAG because it refused 63% of full-context queries. Mem0 costs about 50x plain RAG.
- Independent of the vendors, but a single 2026 preprint; not yet reproduced by others as far as I saw. Strongest evidence I found for question (a).
- Relevant to Ben: the MiniLM retriever named in note 382 is exactly the weak-embedder trap; the fix is cheap.

**3. Hindsight, https://arxiv.org/abs/2512.12818 (A + search snippets).** Four memory networks (world facts, experiences, entity summaries, evolving beliefs) plus a reflect step.
- Author-only claim: LongMemEval 83.6% with a 20B open model (vs 39% for the same model with full context), 91.4% with a larger backbone (Gemini-3 Pro per a secondary page); LoCoMo 89.6%. I could not open the results section (the PDF fetch did not surface it), so per-category and abstention numbers are unread.
- suggested: the 39 -> 83.6 jump at a fixed 20B reader says structure and retrieval, not reader size, moves the score for mid-size readers. This is author-only.

**4. Fine-tuning or retrieval? Ovadia et al. 2023, https://arxiv.org/abs/2312.05934 (A).** shown: RAG beats unsupervised fine-tuning for both old and new facts; models learn new facts poorly from plain fine-tuning; many paraphrases of each fact help. Independent, 2023, mid-size models, so not a claim about a 1-2B model or about parametric memory written by a designed sleep.
- Companions (A only): Memory Layers at Scale, Berges et al., https://arxiv.org/abs/2412.09764 (sparse key-value layer adds parameters without FLOPs, up to 128B memory params, beats dense models with >2x compute on factual tasks; Meta authors). Continual Learning via Sparse Memory Finetuning, Lin et al., https://arxiv.org/abs/2510.15103 (update only memory slots highly used by the new data relative to pretraining usage, ranked by TF-IDF; NaturalQuestions F1 drop 89% with full fine-tune, 71% with LoRA, 11% with sparse memory finetuning at similar new-fact learning; author-only, one model family, QA tasks).

**5. Reader scaling and compression, https://arxiv.org/abs/2606.21807 (A).** 20 readers: notes/compression help weak readers most and can hide gains of stronger ones; a generic summariser reversed 31% of model rankings on LongMemEval-S. shown by authors (new preprint, unreproduced). Meaning for us: small readers do benefit from clean, short notes; do not tune the note format on a big judge reader and assume it transfers to the 1.2B talker.

Also seen, lower weight: leaderboard pages (Mem0 blog https://mem0.ai/blog/ai-memory-benchmarks-in-2026 says its own list is self-reported and "none of these numbers used the same model stack, judge or retrieval"). Vendor numbers I saw: Agent Zero 95.6, Mastra 94.9, Mem0 93-94 (own paper/page), Hindsight 91.4, EmergenceMem 86.0, Supermemory 85, Zep 63.8 (temporal) / 71.2 (GPT-4o; the only one repeated by an independent comparison per the Mem0 page, which is itself a competitor). Treat every one as author-only, different readers, different judges. I did not open Zep/Graphiti, Letta, A-Mem, LightMem, MIRIX, Memory-R1, Titans, MemoryLLM/M+ primary pages this pass: **unread, cited from background only**.
Small-reader hint: BudgetBench https://arxiv.org/abs/2609.13149 (A) runs Qwen2.5-1.5B locally with strategies under 2k-32k token budgets; reports that budgeted vs full context differ little locally and quality is non-monotonic in budget. No LongMemEval score for a 1-2B reader was given in what I read. Evidence Interfaces https://arxiv.org/abs/2607.17108 (A) says its 1B/3B/8B readers all do better from a support-first rendering than raw context, but on 2Wiki/MuSiQue, not LongMemEval.

## Answers to the key questions

**(a) What drives LongMemEval scores?** 
- shown (MemDelta, Wu et al.): the retriever/index dominates: none -> plain RAG is +45 points at a fixed reader; the embedder alone is +6; each of the paper's indexing tricks is +3 to +7. Fancy memory architectures mostly tie plain RAG once the embedder is matched (independent, one preprint).
- shown: reader size matters at the "reading" step too: 8B drops 55 points from oracle in long context; GPT-4o drops 30. With good retrieval the gap to oracle shrinks for everyone (suggested: retrieval turns a long-context problem into a short-context one, which small readers handle far better).
- Two levers, not one: recall of the evidence sessions (retriever), and whether the reader uses it (reader size, note format, abstention behaviour). Refusal behaviour alone swung one model by 31 points.
- 1-2B readers: **untested / no primary number found.** Best bracket: 8B about 42-45% raw, Qwen2.5-1.5B and LFM2.5-1.2B unknown; suggested guess low (single digits to ~30%) on raw long context, and much closer to oracle only when handed 1-3 clean notes. This guess is mine and must be measured, not quoted.
- Abstention is the smallest slice (30 of 500). Fixing "I don't know" alone cannot lift the total much, but a wrong-confident answer on a false-premise question is the safety count Ben cares about (roadmap item 1).

**(b) Retrieval vs parametric.**
- shown (Ovadia, Berges, Lin, all outside our size range): retrieval is the reliable way to add facts; plain fine-tuning learns them poorly and forgets old skills; sparsity (memory layers, sparse slot updates) is what reduces interference. Memory layers scale with parameters (Meta, author-only at 128B); a notebook scales with storage and retriever quality but not with reader smarts.
- suggested: retrieval improves with use for free (more entries, no weight change) and improves with scale via a better reader and embedder. Parametric memory improves with scale (more room) but only with a designed write path. So the notebook is the record; sleep should add what the notebook cannot: skills, habits, style, and fast access to facts used often (turning frequent lookups into knowledge). It should NOT be the only home of a fact that needs a source or a correction.
- What sleep adds over a notebook (suggested, untested): (1) no lookup cost or miss for facts used every day; (2) generalisation across entries (multi-session questions: counting, preferences) that plain retrieval of separate notes handles worst (Mem0's own page shows multi-session at 88% vs 98% single-session); (3) the ability to compose. What it loses: sources, exact dates, undo, correction. Repo evidence (shown, brief): sleep with 128 stored examples per kind recovers old kinds, 16 collapses, so sleep needs a store of raw examples anyway: the notebook doubles as the sleep replay buffer. That is a real synergy: notebook entries are the sleep rehearsal set.
- Sparse memory finetuning maps onto Ben's approved sparse MoE thread (suggested only): the same "update only the slots this new data lights up" rule could be a cheaper sleep write than LoRA-day. Do not treat as a new proposal; hand to the MoE owner.

**(c) Cheapest fit for Premonition.** The test must use the talker (LFM2.5-1.2B) as reader, the store from note 382, and a dev slice. See tests.

## The ruler for this angle (cannot use the maze ruler)
- The maze F_eq/F_few ruler measures few-example adaptation of the reasoner. It says nothing about notebook recall, so no test below claims a maze number, and none should be reported against the +8.0 F_eq bar.
- Ruler instead: **LongMemEval-S dev slice**, fixed once now: 100 questions drawn with a fixed seed, stratified by type, INCLUDING all 30 abstention questions' share (about 6) and at least 10 per other type; written to a file and hash recorded before any run; never used for final scoring, never used to train, never looked at per-question after the design freeze. Held-out remainder (the other 400) is the untouched final and stays sealed (roadmap item 6 rule "never trained on"). Note: the final scoring set should ideally be the full 500 with the dev 100 REMOVED from headline numbers, so tune on 100, report on 400. Suggested; Ben decides.
- Noise: n = 100 gives a binomial sd of about 5 points at 50% accuracy. So bars must be at least +10 points, or use paired per-question comparison (McNemar) with 2 seeds of any random step. Recall@k (retrieval only) is far less noisy: score it on all questions with known evidence sessions.
- Rows every time: (i) plain twin = same talker, raw long context truncated to its window; (ii) closed-book (must be near 3%, a contamination check); (iii) oracle (evidence sessions only) as a ceiling for the reader. Without (iii) you cannot tell reader failure from retriever failure, which is the whole question.
- Compute: all runs are inference. RTX 5070 Ti or Mac CPU can run a 1.2B reader on 100 questions x a few thousand tokens in minutes to an hour; embedding 100 x ~50 sessions x ~10 rounds is a few thousand short texts, trivial. No judge cost worry only if a local judge is used; the official GPT-4o judge needs an API call (author-recommended); a local judge changes scores, so use the same judge in every row and never compare with vendor numbers.

## Proposed tests (one change each; pass marks fixed before running)

**M1. Retriever first: swap the embedder only (suggested by MemDelta).**
- Change: recall() ranks with a stronger open embedding model (for instance bge-small/e5-small class, same k=10, same round-level chunks, same reader) instead of MiniLM. Nothing else.
- Measure: Recall@10 of the evidence session on the whole dev slice (paired), then oracle-vs-retrieved gap for the 1.2B reader.
- Pass: Recall@10 up by at least 4 points AND end-to-end accuracy up by at least 5 points paired (McNemar p < 0.1) on the dev slice.
- Proved wrong if: recall moves under 2 points (then the embedder is not the bottleneck at this stage: look at the reader), or recall rises but answers do not (the reader is the bottleneck).
- Cost: minutes, CPU fine. Zero training. Cheapest and it fixes the retrieval factor before any expensive step.

**M2. Reader diagnosis with the talker: oracle vs top-k notes (the "size of reader" question).**
- Change: only what the reader sees: (A) evidence sessions only (oracle), (B) top-10 rounds from M1's retriever, (C) top-10 rounds rewritten as short JSON facts with dates (Wu et al.'s chain-of-note + JSON), same LFM2.5-1.2B, same prompt otherwise.
- Pass marks (fixed now): A must reach at least 50% or the 1.2B cannot read even perfect evidence: then reader is the bottleneck and item 6 needs a bigger reader or a trained reader, not a better store. C beats B by at least 10 points paired, else the format trick does not transfer to small readers (this contradicts the 8B/GPT-4o result and would be worth knowing).
- Proved wrong if: A is below 30% while B is close to A (retriever is fine, model is the limit), or B > A (noise or the reader likes distractors; recheck).
- Cost: 3 x 100 questions x 1.2B forward passes: under an hour on the 5070 Ti; 1-3 hours on Mac CPU.

**M3. "I don't know" from retrieval, not from a trained judge.**
- Change: only add an abstention gate: answer "I don't know" if the top retrieval score (or the rd-371 verifier's verdict on the top note) falls under a threshold set on a separate calibration set: LoCoMo practice questions plus false-premise and evidence-deleted variants made from the dev-slice sessions with a different seed (suggested). Never from the sealed final 400.
- Metric: coverage vs wrong-confident rate on the dev slice: answered-wrong count on the 30-share of abstention questions plus a set of unanswerable variants (evidence sessions deleted from the store, code-made).
- Pass: on unanswerable variants at least 80% say "I don't know" while answered-correct on answerable questions drops no more than 5 points paired. Compare to y1t's known failure (22 right / 20 wrong): AUROC of the retrieval-score gate must exceed 0.75 in both seeds of the split.
- Proved wrong if: AUROC under 0.65, or the gate rejects more than 15 points of answerable-correct items. Then a retrieval score is not a usable doubt signal and doubt must be trained (a different, later test).
- Cost: inference only; one calibration pass plus one scoring pass; under 2 hours on either machine. Depends on the retrieval score existing in recall() (it does: `score` is returned per note 382).

Order suggestion (suggested): M1, then M2, then M3. M1 and M2 together tell Ben whether item 6 is a retriever job, a reader job, or both, which is the decision that costs the most if guessed wrong. A sleep test that puts notebook facts into weights (a later parametric-consolidation test, e.g. write the 20 most-used facts by sleep and check recall without the notebook, plus that sources still come from the notebook) is deliberately NOT proposed now: it needs M2's reader numbers first and it belongs to the sleep owners (T1-T3 are already queued).

## Mapping to open problems
| Premonition item | Bearing of these findings | Label |
|---|---|---|
| 1 notebook recall with sources | Store cited ids; retriever/embedder matter most; chunk by round; add facts to keys; give the reader dated short notes. All of these are cheap and inference-only. | shown (Wu, MemDelta) for big readers; untested for the 1.2B talker |
| 1 "I don't know" | Refusal is reader-dependent (Sonnet refuses 63% in full context). Retrieval-score gating is untested here; y1t shows text-only trained doubt failed. | suggested |
| 6 LongMemEval final | Keep dev slice separate; vendor numbers are not comparable to ours; report oracle, RAG, closed-book, full-context rows. Do not tune on the 400. | suggested |
| Sleep = parametric memory | Notebook is the source of truth and the replay buffer; sleep consolidates frequently used facts and skills; sparse-slot updates reduce forgetting (author-only). Ovadia: raw fine-tuning is a poor fact learner, so do not make sleep the only path. | suggested / shown for Ovadia (mid-size, older) |
| Improves with use and scale | Notebook grows by writing (use) and gains from a better embedder and reader (scale); sleep gains from bigger models with sparse memory layers (Meta, author-only). | suggested |

## Cautions for Ben
- Every "state of the art" in this area is vendor-run with a different reader and judge. The one independent audit I found (MemDelta) says an ordinary RAG baseline with a good embedder ties the fancy systems on LongMemEval-S; single preprint, treat with care.
- Several of the newest papers (2026) I saw only as abstracts or search snippets; Astra should open Wu et al. sections 4-5 and MemDelta's tables before any pass mark is finalised.
- Per CLAUDE.md, check any factual claim above against the sources before acting. Numbers marked F came through a summariser and could be off by a digit.

## Plain-language summary for Ben
Think of the notebook as a filing cabinet and the model as a person who reads the pages the search hands them. On the big memory test, most of the score comes from how well the search finds the right pages, and very little comes from clever filing schemes: one careful study found a plain search matched the fancy systems once both used the same search engine. Small readers do worse at reading long piles, but do better when given a few short clean notes. Sleep is like learning things by heart: good for things you use daily, bad as the only copy, because you lose the page number and the ability to correct it. So the first cheap steps are: switch the search engine, then check whether the 1.2B talker can read perfect pages at all, then try saying "I don't know" when the search finds nothing good. All three cost only inference and use a 100-question practice slice, never the final exam.
