# Shape ideas: memory, retrieval and hybrid sequence layers (2024-2026)

2026-10-03, design only. **Shown** = measured in the cited paper, in that setting. **Suggested** = reasoning. **Untested** = not tried on our core. "Via summary" = page opened but read by a summariser: check the paper before a mark rests on it. Repeats of older notes are flagged.

**For Ben:** (1) let each word look at its neighbours: cheap, and well shown to deepen reasoning. (2) Teach the reasoner to read worked examples as input → output pairs. (3) When facts arrive, keep them in a table you can unplug. (4) While training, give memorised items a corner that gets thrown away. (5) Later, maybe, think with a few "slots". I dropped Titans, TTT, ATLAS, Mamba-2 and xLSTM: they are the banned fast weights in new clothes.

## 1. Canon layers: each token mixes in its neighbours
- **What:** `h ← h + conv(h)`, a per-channel weighted sum of the nearest 3 tokens with no activation. It goes before attention and before the MLP in both blocks.
- **Source:** Allen-Zhu, *Physics of LMs 4.1: Canon Layers*, NeurIPS 2025, arXiv 2512.17351. I read the abstract plus alphaXiv's full-text summary; the PDF was too big to fetch. Supporting: *LFM2 Technical Report*, arXiv 2511.23404 (via summary): our frozen 1.2B LM is 10 short-conv layers (kernel 3) plus 6 attention layers, and its search found that adding linear-attention or state-space layers "does not improve aggregate quality".
- **Evidence:** shown on synthetic pretraining (8-12 layers, width 512-768):
  - 2-4× reasoning depth: k-hop lookup ≥50% at 8 hops where the plain model is near 0 (via summary);
  - breadth up about 30%;
  - no-position-code + Canon matches RoPE + Canon;
  - Mamba2's edge comes mostly from its built-in conv;
  - under 0.5% extra weights.
  - But at 1.3B on real data, every model still failed basic 2-hop. Untested on looped or non-causal cores.
- **Maps:** our sense of order is weak: the bias is clipped at ±4 and the notebook is an unordered bag (plan §2, shown). Use a symmetric kernel of 3, zero-initialised, applied only inside each 1-D segment and never to registers. Cost: 2 blocks × 2 points × 256 × 3 = **3,072 weights** (0.03% stored). The paper reports 12-20% slower steps.
- **Test:** generated pointer-chasing in the notebook ("x7 → q2." lines, nonce names, fresh draws). Train on 1-4 hops, test on 1-8. Run it against the row that already has §6 order coordinates, so Canon is not credited just for adding order. **Pass:** +15 points at 4 hops and +10 at 8 (untrained) hops, both seeds. **Wrong:** under +3 at 4 hops on both seeds.
- **Risk:** a 2-D version on mazes is close to the forbidden "neighbour message passing (NCA)". In NCA, local passing *is* the update; here it is 3 weights per channel beside full attention. Still, keep it off the puzzle path unless the Director rules otherwise.

## 2. Pair-binding head for few-shot examples
- **What:** one head per block does kernel regression over the notebook examples. Key = an example's input, value = its paired output, query = the question.
- **Source:** Zhang & Bottou, *Memory Mosaics at scale*, NeurIPS 2025, arXiv 2507.03285 (via summary). Background: Kirsch et al., *General-Purpose In-Context Learning by Meta-Learning Transformers*, arXiv 2212.04458 (2022, abstract only).
- **Evidence:** shown at 8B with 1T tokens, and at 1.5B with 200B tokens. Associative memories whose values include the *next* token, with no position code, beat a same-size transformer by more than 10% on in-context classification of new tasks. They also kept improving with more shots, where the transformer got worse. Nothing is written into weights (attention over stored pairs), so this is not fast weights. Kirsch: in-context learning is limited by state size, not weight count. Mapping "next token" to "paired output" is my step (untested).
- **Maps:** uses the §6 example roles. Pool each example's input states into a key and its output states into a value; the question queries across the k examples. Repurpose 1 of the 8 heads (**0 weights**), or add a separate head (about 65k).
- **Test:** one change on top of C5 (same episodes and held-out rule families). **Pass:** k=0 → k=8 gain at least C5's + 10 points, k=2 < k=4 < k=8, and shuffled pairings within 5 of k=0, all on both seeds. **Wrong:** at most +3 over C5, or shuffled pairs within 5 of true pairs.
- **Risk:** the pairing uses role ids we supply. There is no task label, so it stays kind-blind. It needs C5 to pass first.

## 3. A swappable fact table in the text reader
- **What:** an Engram-style hashed lookup on n-grams of LM token ids, added to the reader output through a gate. Facts sit in a table you can zero, swap or edit, never in the core.
- **Source:** Cheng et al., *Conditional Memory via Scalable Lookup*, arXiv 2601.07372 (abstract + alphaXiv overview). Also *Memory Layers at Scale*, arXiv 2412.09764 (abstract only), and Apple's *Pretraining with hierarchical memories*, arXiv 2510.02375 (via summary).
- **Evidence:**
  - Engram at 27B, equal weights: MMLU +3.4, BBH +5.0. The best split put about a quarter of the sparse weights in memory.
  - With the table removed (overview numbers, not checked in the PDF): factual tasks keep 29-44%, reading comprehension keeps 81-93%. That is the skill/fact split we want.
  - Apple: 160M + 18M fetched from a 4.6B bank ≈ a 2× larger model. The rarest-fact bucket rose from 17% to 83%, and memories can be deleted or added to frozen models.
- **Maps:** text adapter only, so the core stays modality-agnostic (§6). One table of 2^16 × 32 feeds the existing 32→256 map: **~2.1M stored (+23%)**, almost no extra compute.
- **Repeat:** the 09-18 note (novel-mechanisms §4) proposed an Engram sweep for the *village model*, which is not evidence here. Product-key slots inside the core are in 04-architecture. New here: the table sits in the reader, and the test zeroes it to check the split.
- **Test (stage two):** generated nonce-entity facts held fixed through training, plus skill questions that use them. **Pass:**
  - zeroing the table costs ≤5 points when the facts are in the notebook;
  - it costs ≥40 on fact questions without them;
  - the table beats the no-table core by ≥10;
  - all on both seeds.
  
  **Wrong:** zeroing costs >15 on notebook-given questions (skills leaked into the table), or the table gains <3.
- **Risk:** these are facts in trained weights, just outside the core. Ben decides whether a removable table counts as "lookup". §7 must count its weights separately.

## 4. Memorisation sinks
- **What:** each training item's ID hashes to a subset of reserved MLP neurons, which are cut at test. The shared weights keep only what generalises.
- **Source:** Ghosal et al., *Memorization Sinks*, ICML 2025, arXiv 2507.09937 (via summary).
- **Evidence:** shown at 344M-1.7B. With 30% of neurons as sinks, the train/held-out gap on repeated text closes by at least half, and validation loss is about the same as normal training, at least as good as deduplication. Untested for skills, tiny models or MoE.
- **Maps:** carve 30% of each expert's hidden units, with no new experts. **0 weights**, but 30% less MLP width at test.
- **Test:** repeat 256 fixed generated problems for 3,000 updates, with and without sinks, then score fresh draws. **Pass:** ≥+10, both seeds. **Wrong:** ≤+3, or a loss of ≥5 on the never-repeating C3 stream.
- **Risk:** C3 removes repetition by design, so this matters only for real repeated data (notes, guides, gameplay). Not for maze adaptation: added neurons there look like the forbidden "growing neurons".

## 5. Slot workspace (lowest priority)
- **What:** inputs are encoded once, and only K=16 slots plus the registers loop. Each round the slots read the input by slot attention (a softmax over slots, so slots compete for tokens).
- **Source:** *Slot State Space Models*, arXiv 2406.12272, and *SOLD*, arXiv 2410.08822 (abstracts only). **Evidence:** shown only in vision and robotics: SOLD beats DreamerV3 and TD-MPC2 on relational manipulation. Suggested for us.
- **Maps:** about 200k weights (+2%). A round costs K·N instead of N², which matters for Minecraft frames plus guides. K is a nearly free state-size knob.
- **Repeat:** close to "Register-only Think" (Perceiver latents, 09-19 overnight). New here: slot competition and a length mark.
- **Test:** English path at C3. **Pass:** within 3 points at the training length, and a drop of ≤5 at 4× longer notebooks where today drops ≥15. **Wrong:** >5 lost at the training length.
- **Risk:** the puzzle path needs per-cell answers, which means adding a write-back step. Biggest change on the list.

## Dropped
- **TTT layers (2407.04620), Titans (2501.00663), ATLAS (2505.23735)**, abstracts only. They write a small net's weights mid-episode; TTT-Linear is exactly the delta-rule fast weight. Papers 2102.11174 and 2501.12352 place them in the fast-weight family. The updates are error-driven rather than Hebbian, but the ban still covers them. Their wins also come at 16k-10M tokens, against our 256.
- **Mamba-2 (2405.21060), xLSTM (2510.02228), hybrids.** Both write outer products into a state, so they are also fast-weight family. In a hybrid study at 1.3B (2507.06457, via summary), recall rises with the share of full attention: RULER 0.256 pure linear, 0.397 at 3:1, 0.423 transformer. Take the conv (idea 1), skip the SSM.
- **kNN-LM, RETRO, Memory Decoder** mix at the output, on the talker side. **RARE** (2503.23513) is a data recipe that C3/C5 already cover.

## Top 2
1. **Canon layers:** 3k weights, the strongest evidence here, aimed at a known weak spot (word order), and a test that takes minutes.
2. **Pair-binding head:** goes straight at "learn from a few examples", costs zero weights, and slots in right after C5.

The fact table (3) is first in line once facts arrive.
