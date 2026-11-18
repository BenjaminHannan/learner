# D6 literature scout A: span selection, pointers, and kind diversity for a small talker

Written 2026-10-08, about 21:05 ET (task started 20:54 ET). Scout: Haiku worker, arXiv search only. No repo files edited, no GPU, no training, no commits.

## Scope and labels

- **Track:** these papers are external literature and belong to neither the card experiments nor the village model. Any recipe below is a suggestion for the 5-25M talker. Which track runs these tests is the team's call (untested mapping).
- **shown** = read in the arXiv abstract fetched on 2026-10-08 (arxiv.org/abs/<id>). **suggested** = my inference or what the paper's body/search snippet implies. **untested** = nobody has tested it for our setup.
- **Verification budget:** 13 abstract fetches used of 14. Each arXiv id below was fetched and its title matched.
- **Scale gap (suggested):** almost all of these results come from BERT-base/large or T5-scale models (110M+) trained on large corpora. Carrying them to a 5-25M talker trained from scratch is an inference, not a result.

## Papers (12 verified)

1. **arXiv 2101.00438. Few-Shot Question Answering by Pretraining Span Selection** (Ram, Kirstain, Berant, Globerson, Levy). 2021 (submitted 2 Jan 2021; ACL 2021).
   - Result that matters (shown): "72.7 F1 on SQuAD with only 128 training examples."
   - Objective (shown): in each passage, hide all but one occurrence of each repeated span and learn to locate the kept one.
   - From a search snippet, NOT the fetched abstract (not verified): the QASS layer builds start/end detectors from the [QUESTION] token's representation; pretraining corpus Wikipedia + Toronto BookCorpus; encoder-only, BERT-like.
   - Recipe for talker (suggested): run recurring-span cloze on FineWeb-Edu text (no labels), with the pointer's query taken from the thinker's output at the placeholder slot (not from the question alone), no per-kind heads, and the thinker kept in the loop during pretraining. This is the only item here that trains a pointer on unlabeled text.

2. **arXiv 1909.04120. Span Selection Pre-training for Question Answering** (Glass et al.). 2019.
   - Result (shown): on Natural Questions, "outperforming BERT-LARGE by 3 F1 points on short answer prediction."
   - Objective (shown): cloze instances whose masked answer is a span chosen from a relevant passage, not from the model's parameters.
   - Recipe (suggested): build cloze questions from FineWeb-Edu sentences, where the answer is a span of the same passage. Same idea as Splinter, with a different question source.

3. **arXiv 1907.10529. SpanBERT: Improving Pre-training by Representing and Predicting Spans** (Joshi et al.). 2019.
   - Result (shown): with BERT-large data and size, "94.6% and 88.7% F1" on SQuAD 1.1 and 2.0.
   - Objective (shown): predict a masked span's full content from its boundary representations.
   - Recipe (suggested): add a span-boundary objective to talker pretraining on FineWeb text. This teaches reading out a span from its two endpoints. It does not force the talker to use the thinker state, so it needs the thinker-ablation check below.

4. **arXiv 1910.10683. Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer** (Raffel et al., T5). 2019 (first submitted 23 Oct 2019).
   - Abstract (shown): "Our systematic study compares pre-training objectives, architectures, unlabeled data sets." Span corruption is NOT in the abstract; it is in the paper body. Span corruption itself is **untested here** (not checked in the body).
   - Recipe (suggested): span-corruption pretraining on FineWeb as a general copy-and-fill skill for the talker. Teaches copying, but not thinker dependence. Ranked lower.

5. **arXiv 1704.04368. Get To The Point: Summarization with Pointer-Generator Networks** (See, Liu, Manning). 2017.
   - Result (shown): on CNN/Daily Mail, "outperforms the current abstractive state-of-the-art by at least 2 ROUGE points."
   - Mechanism (shown): at each step, a learned gate blends copying words from the source (pointing) with generating from a vocabulary.
   - Recipe (suggested): a pointer-generator talker with a copy gate. Log the gate value per kind, because the gate can switch the copy path off (see item 7).

6. **arXiv 1506.03134. Pointer Networks** (Vinyals, Fortunato, Jaitly). 2015.
   - Result (shown): learned approximate solutions to planar convex hull, Delaunay triangulation, and planar TSP from examples alone.
   - Mechanism (shown): attention acts as a pointer that selects one input element as the output, with no fixed output vocabulary.
   - Recipe (suggested): for span answers, let the output softmax range over input positions only, with the query built from the thinker state. Any answer then has to point at input, so the talker cannot answer from memory. Length generalization is **untested** here; the abstract does not claim it.

7. **arXiv 2403.10963. Pointer-Generator Networks for Low-Resource Machine Translation: Don't Copy That!** (Bafna, Koehn, Yarowsky). 2024.
   - Result (shown): models "do not exhibit the expected usage of the mechanism for shared subwords"; improvements over baselines are weak.
   - Relevance (suggested): a cautionary negative result. A pointer path can exist and still go unused, which parallels the PR #37 failure where the talker barely used the thinker on unseen kinds. Measure copy-path usage directly rather than assume it.

8. **arXiv 2305.07759. TinyStories: How Small Can Language Models Be and Still Speak Coherent English?** (Eldan, Li). 2023.
   - Result (shown): on a synthetic dataset of simple-vocabulary stories, models "below 10 million total parameters" (or with one transformer block) still produced fluent, consistent multi-paragraph stories with almost perfect grammar.
   - Relevance (suggested): supports that a 5-25M model trained from scratch can be fluent when the data is narrow and clean. It says nothing about QA or unseen-kind transfer. This is the closest evidence for the from-scratch scale.

9. **arXiv 1910.09753. MRQA 2019 Shared Task: Evaluating Generalization in Reading Comprehension** (Fisch et al.). 2019.
   - Result (shown): 18 QA datasets unified into one format; 6 train, 6 dev, 6 hidden. Ten teams. The best system averaged F1 72.5 on the 12 held-out datasets, 10.7 points above a BERT-based baseline.
   - Relevance (suggested): a template for a held-out-kind split. It also shows that cross-dataset transfer is hard even at scale.

10. **arXiv 1905.13453. MultiQA: An Empirical Investigation of Generalization and Transfer in Reading Comprehension** (Talmor, Berant). 2019.
    - Result (shown): "training on multiple source RC datasets leads to robust generalization and transfer," and it can cut the cost of collecting examples for a new RC dataset.
    - Relevance (suggested): supports training on several sources (kinds) over one. The abstract compares multiple sources with a single source; it does not claim that more sources always helps.

11. **arXiv 2005.00700. UnifiedQA: Crossing Format Boundaries With a Single QA System** (Khashabi et al.). 2020.
    - Result (shown): "performs surprisingly well across 17 QA datasets spanning 4 diverse formats." On 12 datasets not in its training mix (in formats seen in training, per a search snippet; not in the fetched text) it still performs well, which the authors attribute to "strong generalization from its out-of-format training data."
    - Limit: unseen datasets within seen formats, not unseen kinds. This weakens it as support for Recipe 3.
   - Relevance (suggested): include several answer formats (span, yes/no, number) in the talker's training mix, so span picking is not the only learned route. Model size is not in the abstract, so I did not state it.

12. **arXiv 2309.08798. D3: Data Diversity Design for Systematic Generalization in Visual Question Answering** (Rahimi et al.). 2023.
    - Result (shown): "the diversity of simple tasks" plays a key role in systematic generalization.
    - **Correction to the planned rationale:** the abstract does NOT say the models are small or trained from scratch. I did not verify that claim. The paper is about visual QA, so transfer to a text talker is suggested only.
    - Relevance (suggested): supports adding many simple kinds rather than more rows per kind.

## Gaps (said plainly)

- **No paper found for held-out question-kind transfer in span or pointer talkers.** Four searches found none. The closest are MRQA, MultiQA and UnifiedQA (dataset-level, not kind-level).
- **Pointer-generator generalization to unseen tasks:** no paper found in search. The only pointer-generator result here is the negative MT study (item 7).
- **Answer-type heads:** not searched directly, and no hit surfaced in the four searches. Treat as a gap.
- **Skipped:** arXiv 2204.11117 (task transferability), Natural-Instructions 2104.08773, Muppet 2101.11038. Unverified; not cited as evidence.
- **Cited numbers (92.6 / 66.1 / 13.6 vs 78.2, PR #37):** taken from the task prompt. **Cited in task, not checked by me.** I did not read PR #37.

## Ranked recipes (priority order; Recipe 3 is cheap and can run in parallel)

Pass marks and falsifiers are my proposals, not pre-registered, and need Astra or Ben to confirm before any run. All thinker-dependence checks use the same held-out-kind split as the main test.

**Recipe 1. Splinter-style recurring-span pretraining of a thinker-conditioned pointer, on FineWeb-Edu, no per-kind heads.** (Items 1, 2; 4 as an alternative.)
- Why first: it is the only self-supervised objective here that trains a span pointer on unlabeled text, which the task allows. Splinter reports 72.7 F1 on SQuAD with 128 examples (shown in abstract; model size not verified).
- First probe (size and data to be set by the team): pretrain the pointer on a small FineWeb-Edu slice with the thinker in the loop, then fine-tune on the templated kinds with some held out.
- Proposed pass mark: held-out-kind accuracy at least 2x the same talker without pretraining, AND thinker-ablation drop of at least 15 points on held-out kinds.
- Would prove it wrong: held-out-kind accuracy rises but the thinker-ablation drop stays near 0. That means the pointer reads the question or input directly and skips the thinker.

**Recipe 2. Pointer-only answer path for span kinds, with copy-path usage logged per kind.** (Items 5, 6, 7.)
- Why second: it changes the architecture so a span answer must come from input positions chosen by the thinker-state query. The Bafna result (item 7) says a pointer can exist and go unused, so the test must log pointer mass and the copy gate, not just accuracy.
- Proposed pass mark: on held-out kinds, the correct span gets at least 50% of pointer mass with the real thinker state, and this drops by at least 30 points when the thinker state is shuffled across examples.
- Would prove it wrong: pointer mass on the correct span is unchanged when the thinker state is shuffled. Then the pointer is picking the answer from the question or input alone.

**Recipe 3. Leave-kinds-out diversity sweep at fixed rows (cheap diagnostic).** (Items 9, 10, 11, 12.)
- Why third: cheapest and needs no new model code. It tests whether the cited 13.6% vs 78.2% gap (cited in task, not checked) is a kind-count problem or a coupling problem. Its result decides whether Recipes 1 and 2 are needed. Support in the literature is at BERT/T5 scale (MultiQA, UnifiedQA, MRQA) and in VQA (D3), so it is suggested for text.
- Setup (fix before running): hold out one fixed set of about 5 kinds for every arm; draw nested training sets of 10, 15, 20 and 25 kinds from the remaining 25, at fixed ~170k rows.
- Proposed pass mark: unseen-kind accuracy on the fixed held-out set rises by at least 10 points from 10 to 25 training kinds.
- Would prove it wrong: a flat curve. Then kind diversity is not the bottleneck, and effort should go to Recipes 1 and 2.

## Handoff (scout finished; next steps for the team)

- Ranking is priority order. Recipe 1 runs first: it is the only option here that trains a span pointer on unlabeled text, with the thinker in the loop. Recipe 3 is cheap and needs no new model code, so it can run in parallel. Recipe 2 follows once Recipe 1's thinker-ablation check is in.
- Fix the held-out kinds before any run (see Recipe 3 setup).
- Do not cite these numbers as evidence for either track without the scale caveat above.
- Optional if budget allows: one fetch to check span-corruption details in the T5 body, and one search for pointer-network length generalization.
