# Small reasoners and cheap language I/O: literature compare (arm B)

Provenance: written from memory of the papers (no web fetch this session). Numbers are approximate and should be
checked before anyone cites them. Labels: SHOWN = reported by the paper itself; SUGGESTED = authors or third
parties argue it, evidence partial; UNTESTED = my guess, nobody has tested it for this setup.

## 1. Tiny recursive reasoners and how they do I/O

- TRM, Jolicoeur-Martineau 2025 (arXiv 2510.04871): 2-layer net, ~7M params, recursed many times with a latent
  plus an answer state and deep supervision. Reports ~87% Sudoku-Extreme, ~85% Maze-Hard, ~45% ARC-AGI-1, ~8%
  ARC-AGI-2. SHOWN. Trained on ~1k examples plus heavy augmentation (task-specific). SHOWN.
- HRM, Wang 2025 (2506.21734): 27M params, two coupled recurrent modules, ~1k examples per task. SHOWN.
  The ARC Prize team's ablation found the hierarchy mattered little; the outer refinement loop and
  per-task augmentation mattered most. SUGGESTED (third-party analysis, I recall it as a blog post).
- Universal Transformer (1807.03819): weight-shared layers applied repeatedly with adaptive halting; helped
  algorithmic tasks and some language tasks. SHOWN.
- Recurrent depth, Geiping 2025 (2502.05171): 3.5B model with a looped core; more loops at test time improves
  reasoning benchmarks without more tokens. SHOWN. Its prelude/coda split (input layers, looped core, output
  layers) is the same shape as Ben's design, but the prelude and coda there are real layers (hundreds of M params).
- Input/output of all of these: fixed grids or digit tokens, a vocabulary of ~10-12 symbols, an embedding table,
  and output as the same grid. No natural language. SHOWN (by their setups).
- Implication: the tiny cores are cheap because I/O is a trivial fixed encoding, and they are trained per task on
  the exact format. They give no evidence that a 7-27M core handles new wording. SUGGESTED (inference from setups).
  Looped depth at 9M can do search/iterative refinement in a structured space (SHOWN on grids); whether that
  transfers to a space of language-parsed problems is UNTESTED.
- Practical consequence for Ben: the reader must output a clean fixed-format structure (slots/ops), because that is
  the only interface these cores are known to work with. UNTESTED-GUESS that a soft embedding from a frozen LM
  also works at 9M; Ben's own card experiments are the only evidence there.

## 2. Small math-word-problem (MWP) models

- TinyGSM, Liu 2023 (2312.09241): ~12M synthetic GSM-style problems with Python solutions written by GPT-3.5.
  A 1.3B generator + 1.3B verifier reached ~81.5% GSM8K; the 125M-class models were far lower alone (I recall
  ~60s% with a verifier and lower without, check). SHOWN for 1.3B; exact small-model numbers uncertain.
  Key lesson: the win is synthetic data + code output + verifier selection, not architecture. SHOWN.
- Phi-1.5 (2309.05463, 1.3B) and Phi-2 (2.7B): small LMs trained on "textbook-quality" synthetic data match much
  bigger models on reasoning. SHOWN by authors; contamination and benchmark-narrowness concerns raised by others.
  SUGGESTED.
- Distilling step-by-step, Hsieh 2023 (2305.02301): T5 at 770M beat 540B few-shot PaLM on e-SNLI, ANLI, CQA,
  SVAMP using ~80% of the data when rationales are used as extra training targets. SHOWN. Tasks are narrow and
  in-distribution; SVAMP result is for that specific split.
- Fu 2023, Specializing smaller LMs toward multi-step reasoning (2301.12726): distilled chain-of-thought from a
  big LM into FlanT5 (250M to 11B). The 250M model gained but stayed weak on GSM8K; clear scaling with size.
  SHOWN. They also saw general ability drop (specialization trade-off). SHOWN.
- MathPrompter (2303.05398): LLM writes an algebraic template and Python, evaluates over random values for
  self-consistency. Needs a big LLM. SHOWN. Useful idea: separate parse from compute and cross-check by
  substitution. SUGGESTED as transferable.
- PAL (2211.10435) / Program-of-Thoughts (2211.12588): LM only translates text to code; the interpreter computes.
  Gains come mostly from offloading arithmetic. SHOWN (large LMs).
- Size needed for "parsing" word problems: no clean number exists. Evidence points to ~0.1-1B when fine-tuned on
  in-domain synthetic data (TinyGSM, Fu) and ~7B+ for general zero-shot wording. SUGGESTED. For a fixed small
  template family, even BERT-base class parsers work (see 3). A 1.2B frozen LM is probably more reader than
  needed for parsing but about right for open wording. UNTESTED-GUESS.

## 3. Semantic parsers and seq2tree solvers

- GTS, Xie & Sun 2019 (IJCAI; no arXiv id I trust): GRU encoder + goal-driven tree decoder emitting an expression
  tree. Order of ~10-30M params. ~74-76% on Math23K, ~80s% on MAWPS. SHOWN.
- Graph2Tree, Zhang 2020 (ACL): adds quantity-relation graph; small gains over GTS. SHOWN.
- MWP-BERT, Liang 2021 (2110.08464): continued pretraining of BERT-size (~110M) encoder on MWP; best-in-class
  Math23K ~84%+ at the time. SHOWN.
- SVAMP, Patel 2021 (2103.07191): a question-removed baseline scored ~60-77% on ASDiv-A/MAWPS, i.e. benchmarks are
  solvable from shallow cues. On the SVAMP perturbations (reorder, add irrelevant info, swap question), GTS and
  Graph2Tree fall to ~30-45% accuracy (roughly; verify), and even RoBERTa-based ones are ~40-50%. SHOWN.
- Risk for Ben: a small reader that gets high MAWPS/ASDiv-style scores may be keying on keywords ("each",
  "total", "more") rather than reading. Any claim of "generalizes to new wording" needs a SVAMP-like test: same
  quantities, changed question, added distractors, shuffled sentence order, paraphrase, number swaps. SHOWN
  that this breaks small solvers; the exact failure for Ben's reader is UNTESTED.
- Operations-as-output (tree/slots) is the interface TRM/HRM-style cores can consume, which makes this family the
  natural fit. SUGGESTED.

## 4. Byte/character-level and tokenizer-free

- ByT5 (2105.13626): byte-level T5, more robust to noise, spelling, and rare scripts, but ~sequence length x4-5
  and slower; at equal params, better on spelling-sensitive and noisy tasks, comparable elsewhere. SHOWN.
- CANINE (2103.06874): characters, with downsampling conv + deep transformer; ~on par with mBERT, 28% fewer
  params. SHOWN.
- Charformer (2106.12672): learned soft subword blocks. SHOWN.
- MEGABYTE (2305.07185): local patch model + global model; handles ~1M-byte sequences cheaply. SHOWN.
- Byte Latent Transformer (2412.09871): entropy-based dynamic patches; matches Llama-3-class BPE models at 8B
  with up to ~50% fewer inference FLOPs; better on noisy/character tasks. SHOWN (large scale, patch encoder
  itself is small, tens of M).
- For a ~10-50M reader: byte models spend capacity on spelling/composition that a subword vocabulary gives free
  (SUGGESTED). They help robustness to typos and layout, which matters for Minecraft chat/sign/UI text.
  The cheapest option that stays tokenizer-light is a small hashed or subword vocab (8-16k) with a character-CNN
  or byte fallback. UNTESTED-GUESS.
- Tiny-LM evidence: TinyStories (2305.07759) shows ~10-30M models produce fluent text in a narrow domain.
  SHOWN. This is the best sign that a small *talker* is feasible if the output domain is narrow
  (templated answers, short explanations), not open chat.

## 5. Multimodal-ready small encoders

- Perceiver / Perceiver IO (2103.03206, 2107.14795): a latent array of N vectors cross-attends to any
  byte/pixel/audio input array; the core is modality-agnostic; output via query arrays. Cost scales linearly in
  input size. Handles text as bytes (no tokenizer), ~equal to BERT-class on GLUE at similar FLOPs; the core's
  look is close to Ben's "latent core that loops". SHOWN.
- BLIP-2 Q-Former (2301.12597) and Flamingo-style resamplers: small learned query set bridges a frozen encoder to
  a frozen LM, trains only the bridge (~100-200M). SHOWN. Suggests Ben's bridge can be the only trainable
  part per modality. SUGGESTED.
- Gato (2205.06175) and Unified-IO: one transformer, tokenised text/images/actions; works but at 1B+ and
  weak per-task. SHOWN. data2vec (2202.03555) shares the training target across modalities. SHOWN.
- Minecraft: VPT (2206.11795) uses a small-ish vision-and-action policy (~0.5B) from video; MineDojo (2206.08853)
  and STEVE-1 (2306.00937) tie text instructions to behavior with a CLIP-style shared embedding. SHOWN.
  The language side in these is a frozen text encoder (CLIP/MineCLIP-class, ~60-120M), not an LLM. SHOWN.
- Implication: a latent-array core with per-modality read heads (text now, patches/audio later) is a proven
  pattern; the unproven part is doing it at 9M core size with few examples. UNTESTED.

## Ranked opinion for Ben (cheap reader+talker)

1. Small trained parser into a fixed structured form (slots/op-tree), with the core and a deterministic
   executor doing the work; reader = 20-110M text encoder (MiniLM / MWP-BERT / small T5 class) or a distilled
   student of the 1.2B reader, trained on synthetic paraphrase-heavy data (TinyGSM recipe) and checked with
   SVAMP-style perturbations. Talker = templates or tiny decoder reading the core's structured result.
   Main risk: shallow-heuristic parsing (SVAMP result), so it looks good on in-distribution wording and breaks
   on new wording, which is exactly Ben's goal. Mitigate with held-out paraphrase families as the pass mark.
2. Perceiver-style latent-array reader: a small cross-attention front end (bytes or small vocab) that writes
   into the core's latent slots, with the same pattern reusable for vision/audio later and a Q-Former-like bridge
   if a frozen LM is kept for rare cases. Fits the "borrowed LM counts toward size" rule best long-term.
   Main risk: learning to read language from scratch at this size needs lots of data; few-example learning may
   not survive. Possible hybrid: initialize from a distilled embedding table.
3. Keep the 1.2B frozen reader but shrink its cost: distill it to a ~100-300M student for the reader role only,
   and use a tiny narrow-domain talker (TinyStories-style, 10-30M). Main risk: the distilled student loses
   exactly the paraphrase robustness that motivated the big model; size accounting gets worse if the big LM is
   still needed for fallback.
Byte-level (section 4) is a component choice inside 2, not a direction of its own; main risk is wasted
capacity on spelling and 4-5x longer sequences.

Plain-language summary for Ben: the famous 7-27M puzzle solvers work because the puzzle is already a neat grid.
Nobody has shown a model that small reading messy English directly. The cheapest known recipe is a small
translator that turns the words into a neat structure, then the tiny core solves it, then a template says the
answer. The big danger is a translator that memorizes tricks instead of reading, so test it with reworded
problems from the start.
