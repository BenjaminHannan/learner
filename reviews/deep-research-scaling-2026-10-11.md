# Research question: what makes a small looped reasoning model gain a lot from more parameters?

Please research the published literature and strong technical sources (papers, arXiv, official blog posts of labs; cite
every claim with a URL). Label each claim **shown** (a paper measured it), **suggested** or **untested**. Keep it under
about 2,000 words and end with a plain-language summary for the project owner, a high-school senior.

## Our situation (self-contained)

- We train a small reasoning model. A frozen pretrained text embedder (EmbeddingGemma, 271M parameters, frozen) reads the
  question; a trained "thinker" (a stack of transformer blocks over ~44 latent tokens, the **same blocks looped 12 times**
  with shared weights) reads it through cross-attention, calls an exact calculator (add, subtract, multiply, divide, mod,
  min, max, compare) on most rounds, and a small answer head writes the answer. Width 256. AdamW, lr 1e-3, cosine,
  24,000 updates of 256 rows.
- Data: 1.42M training rows (60M word pieces): 38% synthetic skill questions from 34 template families with worked steps,
  62% fill-in-the-blank rows from web text. About 4.3 passes over the data. Same rows at every size.
- Score: exact match on 6,040 held-out rows with one shift each (new answer values, new wordings, new names, new
  structural variants of a skill). About 42% of the rows are in families the smallest model already gets 100%; half of
  its misses are "new structural variant" rows.
- **Scaling result:** growing the thinker from 3.5M to 10M trained parameters (by depth: 2 -> 8 blocks, same width, same
  learning rate, same data) gained only **+1.6 points** (73.0 -> 74.7, one seed; seed noise sd about 1). An earlier version
  gained +0.5 (6 seeds). A plain decoder-only transformer of the same sizes on the same data gained +3.8 (it starts 6
  points lower), and a plain next-token language-model recipe gained +15.8 (it starts 26 points lower). Our model's
  training loss barely moves with size (1.139 -> 1.128); the plain model's does.
- Our model is weak exactly where the plain model of the same size is better: table lookup, if/otherwise rules, few-shot
  "find the rule" questions, sequence continuation, passage questions. These answers are not calculator results; our
  current answer head is a parallel (non-autoregressive) character writer plus pointers. A next version replaces it with
  a small autoregressive writer that also writes calculator calls as text.
- Goal: the finished thinker is ~100M parameters, and the owner wants each size step to **clearly** raise the score.
  Compute: one 16 GB consumer GPU for tests.

## What to find out

1. Known reasons small models, and especially **looped / weight-shared / recurrent-depth transformers** (Universal
   Transformers, looped transformers, recurrent-depth latent reasoning) or models with a **frozen pretrained encoder**,
   show flat scaling with parameters; which of these fit our numbers.
2. What the literature says makes parameter scaling strong at small scale: data per parameter and repeated data
   (data-constrained scaling), width vs depth, learning-rate and initialization rules across width and depth (muP,
   depth-muP), how loop count and parameter count trade off, answer decoders (autoregressive vs parallel), and benchmark
   ceilings / saturation (exact-match vs loss as a scaling measure).
3. Evidence on whether gains from size on **out-of-distribution template variants** (compositional / systematic
   generalization on synthetic tasks) come from size, from data diversity, or from architecture.
4. A ranked list of the **three** most promising single changes for us to test on one 16 GB GPU, each with what result
   would confirm it and what would rule it out, and a rough recipe for growing 10M -> 100M so the gain is large
   (shape, learning rate, data amount and diversity).
