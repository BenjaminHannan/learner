# Getting more information into the model

Written 2026-10-03 for Ben's ask (18:58 UTC): "figure out ways to have more information go to the model. Right now we use transformer's attention, but what else could we do." Design only. Nothing was trained, no GPU was used, no eval set was opened.

Labels: **shown** = measured (in a cited paper, or in our repo). **Suggested** = reasoning. **Untested** = never run on our model. Paper results are the authors' own unless noted. Small card experiments and the village model are not used here.

## 1. Summary for Ben

- Attention is not where we lose information. We lose it at two narrow pipes: the way in (each word is squeezed from 2048 numbers to 32) and the way out (the whole passage is averaged into 8 vectors before the language model sees it). **Shown in code**, see §2.
- The way-out pipe already failed once today and was fixed. The calculator answers only came out right for new numbers once the result skipped the averaging and went straight to the language model (0-4% to 84-99%, PR #29). **Shown.**
- The English pilot now has the same look: it learns its 48 training questions (40-43 of 48) and gets 2-7 of 48 fresh ones (LIVE.md, 20:10 UTC). Its answers are passage words, and passage words have to squeeze through the same 8 averaged vectors. **Suggested**, and there is a second explanation: 48 training questions is far too few. A free check on saved outputs can tell the two apart (§4, F-E1).
- **First pick: a pointer exit for words.** The reasoner points at the words in the passage it wants to say, and the language model receives those words' own embeddings. It is the calculator copy path, made general. The language model still never sees the raw passage, so the talker stays thin. Cheap test on vast (§4, T1).
- **Second: open the way in.** Widen the 32-number reader and read a middle layer of the language model instead of only the last one (§3, rank 2).
- **Third: a deep exit.** Feed the reasoner's state into the language model's attention layers, not only in front of it (§3, rank 3).
- **Not recommended now: replacing attention** with state-space or recurrent layers (Mamba, xLSTM, Titans). Our inputs are at most 64 tokens, where attention is cheap and copies best. The project's own rules ban the fast-weight family these belong to. Revisit when Minecraft brings long streams (§3, "looked at").

## 2. Where information flows today (shown in code)

The English pilot path (`scripts/cap256_launch/english_pilot_runtime_v1.py:1-10, 143-162`, `scripts/sol_translator_english.py:15-46` on branch `claude/premonition-launch-recovery-96c708`), and the PR #29 reimplementation (`reasoner_fresh/model.py:6, 70, 81, 147` on branch `claude/project-thread-cjyppo`):

| Pipe | What passes | Width | Status |
|---|---|---|---|
| 1. Way in | Frozen LM **final layer** state per token (`english_feature_cache64_v1.py:4`), at most 64 tokens | 2048 → **32** → 256 (reimplementation's reader; the PC reader's hidden width is not in the repo) | squeezed |
| 2. Inside | 2 shared blocks, 8 heads, attention over all positions + notebook slots, 4 rounds | 256 per position | fine for 64 tokens |
| 3. Tools | Calculator result re-enters as the LM's embedding of the result token, in a value slot | 256 | works (PR #29) |
| 4. Way out | Every position → 259 → **32** → 2048, then **averaged into 8 vectors**; the LM sees BOS + 8 vectors + its own output so far | 8 vectors, each from a 32-number code | squeezed |

Each of the 8 prefix vectors is a fixed linear map of an average of 32-number codes, so the whole answer reaches the LM through about 8 × 32 = 256 numbers, made by averaging roughly 8 positions each. Averaging blurs which word sat where (suggested). In PR #29 this exit learned a closed set of answers: every wrong unseen answer was a training answer, 375 of 377 (shown).

Capacity is not the hard limit. One trained input vector can make Llama-3.1-8B rebuild up to 1,568 tokens exactly (Kuratov et al., arXiv 2502.13063, shown for per-example optimised vectors). The authors call the gap between that and what trained encoders reach "two orders of magnitude". So the problem is that our learned squeeze is hard to learn in a way that generalises, not that 8 vectors are too small (suggested).

## 3. Ranked options

Judged by: does it attack a failure we have shown; is there a published result; weights added; one change with marks fixed first; does it get better with use and scale; and does it keep the talker thin (the LM must not do the reasoning).

| Rank | Idea | Pipe | Weights added | First test | Label |
|---|---|---|---|---|---|
| 1 | Pointer exit for words | out | ~2k-66k | T1 on vast, ~$0.6 | pattern shown (PR #29, pointer-generator); untested for words |
| 2 | Wider reader + middle-layer features | in | ~0.5M | T2 on vast | papers shown; untested |
| 3 | Deep exit (into the LM's attention layers) | out | ~0.1-0.5M | T3, after T1 | papers shown; untested |
| 4 | More exit vectors, no averaging (cross-attention pool) | out | ~0.1M | folded into T1 as a third arm | papers shown; untested |
| 5 | Notebook and tool results as workspace tokens | tools | 0 | already the §6 contract (PR #23) | design exists |
| 6 | Registers and state lanes across rounds | inside | ~12k | already ranked in PR #23 shortlist | see PR #23 |
| 7 | Retrieval memory for facts (stage two) | in | table | parked | papers shown |

### Rank 1. Pointer exit for words

- **What:** K = 8 pointer slots. Slot k scores every input position i as `w_k · h_i` from the core's final state, takes a softmax, and hands the LM the weighted mix of the **frozen LM's own input embeddings** of those tokens. These 8 vectors are added after the existing 8 prefix vectors. When a slot points sharply at one word, the LM receives exactly that word, in its native form.
- **Why:** it is the PR #29 copy path generalised from "the calculator's result token" to "any token the reasoner picks". There, final accuracy became equal to the right-call rate: every remaining error was a wrong choice, none a wrong readout (shown). Pointer-generator networks fixed rare and unseen words in summarisation the same way (See et al., arXiv 1704.04368, shown there; pointer networks, Vinyals et al., arXiv 1506.03134).
- **Thin talker:** the LM never sees the passage. It only sees the words the reasoner chose. Choosing is the reasoning; the LM still only translates.
- **Scale and use:** pointing works for any name or word never seen in training, which is what "learn a new thing from a few examples" needs. Later the same head can point at a screen patch or a guide sentence (Minecraft), still through §6 roles (suggested).
- **Cost:** 8 × 256 = 2,048 weights with fixed queries, or ~66k with a 256 × 256 query map. Needs the token ids next to the cached features (check they are stored).
- **Risk:** it only helps answers that are words already in the input. Answers the reasoner must compose (counts, yes/no, a word not in the passage) still go through the 8 averaged vectors. Ranks 3 and 4 cover those.

### Rank 2. Wider reader and middle-layer features

- **What:** two separate single changes. (a) Reader hidden width 32 → 256. (b) Read a middle LM layer (or a learned mix of 3 layers) instead of only the final layer.
- **Why:** the final layer of a causal LM is tuned to predict the next token. Middle layers beat the last layer by up to 16% on 32 embedding tasks (Skean et al., *Layer by Layer*, ICML 2025, arXiv 2502.02013, shown there). Mixing several encoder layers improved 19 vision-language benchmarks across LLMs from 2.7B to 70B (Dense Connector, arXiv 2405.13800, shown there).
- **Cost:** (a) about 2048 × 224 + 224 × 256 ≈ 0.5M extra weights; (b) zero weights for one layer, a few for a mix, and a re-cache of features.
- **Risk:** a wider reader adds weights that §7's scaling test counts. It matters only if the way in is a real limit; T2 checks that with a task where the facts are spread across the passage.

### Rank 3. Deep exit

- **What:** instead of only 8 vectors in front of the LM, the reasoner writes extra key/value entries into each of the LM's attention layers (prefix-tuning style). LFM2 is mostly short-convolution layers with a few attention layers (LFM2 report, arXiv 2511.23404), so this reaches only those layers.
- **Why:** deep prompts close most of the gap to full fine-tuning at small model sizes, where input-only prompts fall short (P-tuning v2, arXiv 2110.07602, 330M-10B, shown there). Feeding one model's key/value cache into another beat passing text between them by about 3-5% (Cache-to-Cache, arXiv 2510.03215, ICLR 2026, shown there).
- **Cost:** a small map from 256 to each attention layer's key/value width; about 0.1-0.5M weights.
- **Risk:** a stronger exit lets the LM do more of the work. Every exit test needs the lesion in §4.

### Rank 4. More exit vectors without averaging

- **What:** replace the 8 averages with 8 learned queries that attend over all positions (Perceiver-style pooling), or one prefix vector per position (up to 64).
- **Why:** in MM1 (arXiv 2403.09611), how many tokens reach the LM and their resolution mattered a lot, and the connector's design mattered little (shown there). A learned pool keeps "which word was where" that averaging loses (suggested).
- **Use:** run as a third arm in T1, so we learn whether pointing beats just "more and sharper vectors".

### Ranks 5-7 (already designed elsewhere or parked)

- **Notebook and tools as workspace tokens:** the §6 contract in PR #23 already puts notebook text, examples and tool results into the workspace with role and modality ids. Nothing new to add here.
- **Across rounds:** draft registers (PR #23 C2a), state lanes (Hyperloop, arXiv 2604.21254) and memory tokens (Recurrent Memory Transformer, arXiv 2207.06881) all carry information between rounds. They are ranked in `design/next-parts/critical-thinking-shape-shortlist.md` on PR #23.
- **Retrieval memory:** RETRO (arXiv 2112.04426) and Memorizing Transformers (arXiv 2203.08913) fetch stored text. Facts come in stage two, so this waits. The Engram-style fact table is already parked in PR #23.

### Looked at, not recommended now

- **State-space and recurrent layers instead of attention (Mamba-2, xLSTM, Titans, TTT).** Transformers copy from context far better than fixed-state models, proven for 2 layers and shown on pretrained LLMs (Jelassi et al., *Repeat After Me*, ICML 2024, arXiv 2402.01032). Our failure is a copy failure. LFM2's own architecture search found that adding linear-attention or state-space layers did not improve quality (LFM2 report, via summary in PR #23 notes). These layers save compute on long sequences, but ours are at most 64 tokens. The repo's forbidden list (`design/research/2026-09-28-reasoner-idea-harvest-r1-r5.md:9-13`) bans fast weights, and PR #23's memory notes place these in that family. Revisit when Minecraft frames and guides make inputs long; then only Ben can lift the ban.
- **Letting the LM read the raw passage.** It would raise the English score fastest and break Ben's rule that the talker is a thin translator (09-29). Not proposed.
- **Continuous thought (Coconut, arXiv 2412.06769)** feeds the LM's own hidden state back as input. Our reasoner already does the thinking in latent rounds, so it adds nothing here.

## 4. Tests, in order (marks fixed before any run)

All rows follow the project rules: one change, at least 6 paired seeds (same seeds both arms; paired mean with a 95% t-interval), fast-lane held-out split with the split seed and marks written down before training, no consumed or reserved panels.

### F-E1 (free, CPU, no training): which failure does the English pilot have?

On the already-scored eval v3 outputs from the 9216-update runs (4 endpoints): for every wrong fresh answer, is the output string equal to one of the 48 TRAIN answers?
- **Exit is the bottleneck** (go to T1 on the English recipe next): at least 60% of wrong fresh answers are TRAIN answers.
- **Not the exit** (data is the first fix; T1 still runs on the synthetic task): under 20%.
- In between: both; run T1 and more data together, as separate rows.
This only reads outputs that were already scored and is not a new score. The execution owner holds those files on BensPC.

### T1 (vast, ~$0.6): pointer exit on a held-out-names reading task

- **Harness:** the PR #29 `reasoner_fresh` code and box scripts, new generator. Short generated stories (2-4 sentences, 2-3 people, objects and places), questions like "Who has the cup?" or "Where did Mia go?". Answer = one name or place word from the story. Name and place lists are split once by a fixed seed: eval answers are **never** training answers (the unseen-answer design that exposed the closed set in PR #29). Varied wording from the start (the 18:35 lesson).
- **Arms:** A pooled exit (today). B = A + pointer exit (rank 1). C = A with 8 learned-query pools instead of averages (rank 4). 6 seeds each, 3000 × 16 updates as in PR #29.
- **Pass for B:** unseen-answer accuracy, paired over 6 seeds, B − A ≥ +25 points with the interval above 0, and B's seen-answer accuracy not more than 5 points below A's.
- **Lesion (must also hold):** at test, replace B's pointer weights with uniform weights (the average of all word embeddings). Unseen accuracy must lose at least half of B's gain. If not, the gain is not from pointing.
- **Falsified:** B − A < +8 points on unseen answers.
- **C is read, not judged:** if C reaches within 10 points of B, "more and sharper vectors" is enough and pointing is optional.
- **Cost:** 18 runs × ~5 min on one RTX 3090 at $0.163/h ≈ $0.25-0.6 (PR #29 rates).

### T2 (vast, after T1): is the way in a limit?

- **Task:** the T1 generator plus two-hop questions ("Ana gave the cup to Bo. Bo went to the garden. Where is the cup?"), on the T1 winner.
- **Single change (a):** reader width 32 → 256. **Single change (b), a separate row:** middle-layer features (layer 8 of 16, picked before the run).
- **Pass:** two-hop accuracy paired gain ≥ +10 points, interval above 0. **Falsified:** < +3.

### T3 (after T1): deep exit for answers that are not in the passage

- **Task:** questions whose answer is a count or yes/no (not copyable).
- **Change:** deep exit (rank 3) vs the T1 winner.
- **Pass:** paired gain ≥ +10 points on those questions. **Lesion:** with the core's rounds replaced by the reader output (0 rounds), the deep-exit arm must lose at least 70% of its accuracy above chance, so the LM is not reasoning on its own. **Falsified:** < +3.

## 5. Where this fits

- **Done:** copy path for calculator results (shown, PR #29); varied wording (shown, PR #29); English pilot NULL (LIVE.md).
- **This step:** F-E1 (free), then T1 (pointer exit).
- **Next if T1 passes:** pointer exit goes into the English recipe on the PC, with more training data, judged on fresh understanding questions. Then T2 and T3. **If T1 fails:** the exit is not the English problem; the fix is more and more varied English training data first.

## 6. Plain-language summary for Ben

The model has a small "thinking" part in the middle and a big borrowed language model at the end that does the talking. The thinking part is fine at passing information around inside itself. The problem is the two doors. Going in, every word gets squeezed from 2,048 numbers to 32. Coming out, the whole passage is blended into 8 averaged vectors, like mixing paint, so the talker can't tell which exact word to say. We already saw this with the calculator: answers only came out right after we let the result skip the blender. The best next step is the same trick for words. The thinking part points at the words it wants to say, and the talker gets those exact words. It's a cheap test, under a dollar on a rented GPU. Swapping attention for something else, like Mamba, would not help, because our texts are short and attention is the best tool for copying.

## Sources

Kuratov et al. 2502.13063 · See et al. 1704.04368 · Vinyals et al. 1506.03134 · Skean et al. 2502.02013 · Dense Connector 2405.13800 · P-tuning v2 2110.07602 · Cache-to-Cache 2510.03215 · MM1 2403.09611 · LFM2 2511.23404 · Jelassi et al. 2402.01032 · RMT 2207.06881 · Hyperloop 2604.21254 · RETRO 2112.04426 · Memorizing Transformers 2203.08913 · Coconut 2412.06769. Search-page summaries were read for most; abstracts or full text were not re-opened for every number, so re-check a number in its paper before a pass mark rests on it.
