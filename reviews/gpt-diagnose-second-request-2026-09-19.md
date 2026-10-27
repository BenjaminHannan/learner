# Diagnose a two-step lookup failure in a small neural model (no code or file access needed)

You are an expert in neural architectures, retrieval-augmented models and compositional generalisation. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer rather than guessing. Mark every claim as **shown by the data below**, **suggested**, or **untested**. Five seeds is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

## 1. The task (a toy, synthetic vocabulary)

Each "visit" is a token sequence:

1. A shuffled **fact block**. For each of 6 people and each of 3 relations, an attribute line `[world] ENT_e REL_r VAL_v f? \n`; for each person one link line `[world] ENT_a LINK ENT_b f? \n` (b = a's friend, a random other person); plus 4 filler lines. Values are uniform over 16 ids. People are pointer tokens ENT0-15, re-assigned per visit.
2. A **filler block** of at least 128 tokens (longer than the reader's 64-token attention window).
3. **Questions**: one-hop `[question] ENT_e REL_r [answer] VAL` (the value of (e, r)) and two-hop `[question] ENT_a LINK REL_r [answer] VAL` (the value of (friend(a), r)). 2 of each per visit.

**Held-out split:** in training, no two-hop question uses relation 2. One-hop questions use all three relations. So the held-out test ("a LINK REL_2") combines two familiar operations in an unseen combination; the token pair `LINK REL_2` never occurs in training. Validation: 512 one-hop, 341 practised two-hop, 171 held-out two-hop.

Plain example: "Mira's friend is Oren", "Oren's shoes are blue". "What colour are Mira's friend's shoes?" needs card 1 (Mira's friend = Oren) and then card 2 (Oren's shoes = blue).

## 2. The model (run here at the "tiny" size: d_model = 32, key_dim = 16)

- **Reader:** 3 layers over the whole visit: minGRU, block-local attention (window 64), minGRU; then LayerNorm. Causal.
- **Card writer:** every fact line becomes one card. `p` = softmax-pooled reader states of the line's tokens (one learned scalar score per token); `key = normalize(W_k p)` (16-d); `value = W_v p` (32-d). One pooled vector feeds both key and value. There is a learned NULL card.
- **Think workspace**, per question: rows = [last 40 question-token reader states + row-type embedding] + [16 entity slots, initialised from the ENT token embeddings] + [16 card rows, empty at start] + [4 learned registers]. A shared 2-layer transformer block ("Think") runs over these rows once per loop, up to 4 loops here. Each loop first adds a learned **loop-step embedding** to every row: `x = x + step_emb[step]`.
- **Heads, all read register 0 only:** `query = W_q · norm(register0)` (Linear d -> key_dim), `ask_logit = W_a · norm(register0)`, `halt_logit`.
- **Retrieval:** `score_i = kappa * cos(query, key_i) + age_bias[age_bucket_i]`; cards already fetched are ineligible; the **top-1** card is fetched when `ask_logit > 0`. The top-k choice is discrete and **detached**: the answer loss cannot reach the query or the keys.
- **Inserting a fetched card:** its row is `value + age_embedding + card_row_type`, written into the next card row. It also "binds" into the entity slots of the people mentioned on that line: `slot <- slot + sigmoid(g) * (tanh(c) - slot)` with `[g, c] = W_b [slot; value]`.
- **Decoder:** one block (causal self-attention + cross-attention to the Think rows) generates the answer. In the variant used here ("card bypass") the decoder reads the card rows exactly as inserted (before any Think pass); Think still sees and updates its own copy.
- Evaluation uses a fixed 4 loops, so up to 3 fetches; halting is ignored.

## 3. Training

- Losses: language-model loss on the visit; answer cross-entropy (every loop decodes the answer; weight 0.2 before all gold cards are fetched); ASK loss; HALT loss. AdamW, lr 1e-3 constant after 100 warm-up steps, grad clip 1.0. Runs stop on a compute budget at step ~3,745.
- **ASK loss at every loop:** a *set* cross-entropy over `need` = gold cards not yet fetched (so at loop 0 of a two-hop question the target set is both the friend card and the answer card), plus a binary cross-entropy on `ask_logit` (target: any gold card still missing). Gold cards come from the simulator (privileged evidence labels).
- **Curriculum by share of compute:** 0-30% "gold" (gold cards preloaded, no ASK/HALT loss); 30-55% "teacher" (after each loop the teacher inserts **one random card from `need`**, so the answer card arrives before the friend card about half the time); 55-80% ramp from teacher picks to the model's own picks; then own picks only.

## 4. How I probed it

For every two-hop validation question I ran four conditions and classified every card the model itself requested as: the asker's friend card (`link`), someone else's link card, the answer card (right person + right relation), right person wrong relation, right relation wrong person (including the asker's own), or neither.

- **own:** the model fetches everything.
- **handed 1st card:** loop 0 runs, then the model's first fetch is replaced by the correct friend card (exactly what the training teacher does); the model fetches the rest itself.
- **preloaded:** the friend card is already in memory before loop 0 (never happens in training).
- **both given:** both gold cards in memory, no fetching.

## 5. Results (validation; P = practised two-hop, n = 341; H = held-out two-hop, n = 171; six-relation rows: P n = 434, H n = 78)

All runs: same recipe, one consumer GPU, fp32, 5 seeds per arm. GPU runs are not bit-reproducible, so "seed 0" in two arms is not a paired draw. Arms, each a **single change** against baseline:
- **no-step-emb:** loop-step embedding zeroed and frozen.
- **ordered:** ASK set target and the teacher restricted to the *next reachable* gold card (friend card first, then answer card).
- **cooldown:** learning rate ramped down over the last 30% (it only reached 0.29x because runs stop early).
- **base6 / ordered6:** data with 6 relations (5 practised at hop 2, 1 held out), otherwise identical; visits have 42 fact lines instead of 24, so absolute numbers are not comparable with the 3-relation rows.

| arm | seed | 1-hop own | both given P | both given H | own 2-hop P | own 2-hop H | 1st own request = friend card P | same H | handed 1st card: acc P | acc H | 2nd request P (full/rel/person of n) | 2nd request H |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0 | 359/512 | 341/341 | 171/171 | 149/341 | 12/171 | 199/341 | 102/171 | 190/341 | 9/171 | 134/279/134 of 341 | 0/0/5 of 171 |
| baseline | 1 | 199/512 | 340/341 | 170/171 | 67/341 | 26/171 | 250/341 | 32/171 | 70/341 | 30/171 | 49/316/49 of 341 | 11/94/20 of 171 |
| baseline | 2 | 473/512 | 341/341 | 171/171 | 303/341 | 28/171 | 327/341 | 166/171 | 309/341 | 29/171 | 283/341/283 of 341 | 22/23/103 of 171 |
| baseline | 3 | 371/512 | 340/341 | 171/171 | 170/341 | 19/171 | 246/341 | 58/171 | 202/341 | 11/171 | 153/284/153 of 341 | 0/25/8 of 171 |
| baseline | 4 | 426/512 | 341/341 | 171/171 | 233/341 | 13/171 | 294/341 | 131/171 | 258/341 | 16/171 | 222/340/222 of 341 | 0/5/24 of 171 |
| no-step-emb | 0 | 115/512 | 341/341 | 171/171 | 61/341 | 25/171 | 0/341 | 0/171 | 92/341 | 46/171 | 57/341/57 of 341 | 34/171/34 of 171 |
| no-step-emb | 1 | 422/512 | 341/341 | 171/171 | 226/341 | 64/171 | 288/341 | 110/171 | 252/341 | 81/171 | 214/331/214 of 341 | 55/138/55 of 171 |
| no-step-emb | 2 | 460/512 | 341/341 | 171/171 | 209/341 | 12/171 | 286/341 | 136/171 | 233/341 | 13/171 | 192/341/192 of 341 | 0/0/85 of 171 |
| no-step-emb | 3 | 455/512 | 341/341 | 171/171 | 181/341 | 15/171 | 287/341 | 38/171 | 197/341 | 16/171 | 151/315/151 of 341 | 0/0/27 of 171 |
| no-step-emb | 4 | 457/512 | 322/341 | 168/171 | 271/341 | 19/171 | 305/341 | 98/171 | 295/341 | 17/171 | 267/341/267 of 341 | 7/7/109 of 171 |
| ordered | 0 | 112/512 | 317/341 | 171/171 | 59/341 | 34/171 | 44/341 | 0/171 | 57/341 | 24/171 | 8/40/8 of 341 | 26/171/26 of 171 |
| ordered | 1 | 385/512 | 317/341 | 154/171 | 60/341 | 9/171 | 63/341 | 31/171 | 99/341 | 4/171 | 20/37/20 of 341 | 0/0/30 of 171 |
| ordered | 2 | 496/512 | 319/341 | 162/171 | 280/341 | 12/171 | 325/341 | 130/171 | 290/341 | 13/171 | 265/341/265 of 341 | 0/0/144 of 171 |
| ordered | 3 | 456/512 | 337/341 | 169/171 | 228/341 | 10/171 | 285/341 | 130/171 | 258/341 | 16/171 | 221/308/222 of 341 | 2/4/66 of 171 |
| ordered | 4 | 494/512 | 314/341 | 159/171 | 256/341 | 17/171 | 314/341 | 119/171 | 274/341 | 20/171 | 240/338/240 of 341 | 6/8/67 of 171 |
| cooldown | 0 | 112/512 | 340/341 | 171/171 | 63/341 | 18/171 | 0/341 | 0/171 | 106/341 | 35/171 | 64/341/64 of 341 | 24/171/24 of 171 |
| cooldown | 1 | 491/512 | 325/341 | 158/171 | 321/341 | 17/171 | 329/341 | 0/171 | 328/341 | 109/171 | 316/341/316 of 341 | 99/171/99 of 171 |
| cooldown | 2 | 296/512 | 341/341 | 171/171 | 75/341 | 12/171 | 92/341 | 33/171 | 80/341 | 12/171 | 57/341/57 of 341 | 0/0/33 of 171 |
| cooldown | 3 | 512/512 | 341/341 | 171/171 | 326/341 | 9/171 | 341/341 | 171/171 | 326/341 | 9/171 | 320/341/320 of 341 | 0/0/145 of 171 |
| cooldown | 4 | 448/512 | 310/341 | 150/171 | 246/341 | 51/171 | 277/341 | 96/171 | 282/341 | 65/171 | 246/336/246 of 341 | 52/120/53 of 171 |
| base6 (6 relations) | 0 | 108/512 | 423/434 | 78/78 | 92/434 | 14/78 | 76/434 | 8/78 | 97/434 | 18/78 | 69/434/69 of 434 | 16/78/16 of 78 |
| base6 (6 relations) | 1 | 115/512 | 434/434 | 78/78 | 100/434 | 18/78 | 38/434 | 0/78 | 113/434 | 22/78 | 78/434/78 of 434 | 13/78/13 of 78 |
| base6 (6 relations) | 2 | 391/512 | 433/434 | 77/78 | 179/434 | 6/78 | 215/434 | 43/78 | 255/434 | 7/78 | 204/433/204 of 434 | 0/0/23 of 78 |
| base6 (6 relations) | 3 | 198/512 | 434/434 | 78/78 | 92/434 | 5/78 | 73/434 | 14/78 | 109/434 | 5/78 | 84/434/84 of 434 | 0/0/17 of 78 |
| base6 (6 relations) | 4 | 452/512 | 433/434 | 78/78 | 274/434 | 6/78 | 410/434 | 74/78 | 286/434 | 6/78 | 257/430/257 of 434 | 3/6/37 of 78 |
| ordered6 (6 relations) | 0 | 105/512 | 402/434 | 75/78 | 55/434 | 3/78 | 78/434 | 20/78 | 57/434 | 3/78 | 0/3/0 of 434 | 0/0/0 of 78 |
| ordered6 (6 relations) | 1 | 118/512 | 393/434 | 69/78 | 75/434 | 2/78 | 80/434 | 13/78 | 77/434 | 2/78 | 1/2/1 of 434 | 0/0/0 of 78 |
| ordered6 (6 relations) | 2 | 410/512 | 370/434 | 55/78 | 217/434 | 7/78 | 317/434 | 47/78 | 271/434 | 8/78 | 193/375/195 of 434 | 0/0/10 of 78 |
| ordered6 (6 relations) | 3 | 116/512 | 406/434 | 72/78 | 98/434 | 20/78 | 75/434 | 19/78 | 110/434 | 23/78 | 77/434/77 of 434 | 16/76/18 of 78 |
| ordered6 (6 relations) | 4 | 112/512 | 434/434 | 78/78 | 65/434 | 6/78 | 64/434 | 19/78 | 69/434 | 7/78 | 3/14/3 of 434 | 0/0/13 of 78 |

"2nd request" = the first card the model requests once the friend card has been handed over: fully right / right relation / right person.

Pass marks I fixed in advance: both-given P >= 90%, own two-hop P >= 50%, own two-hop H >= 50%. **Held-out own two-hop: 0 of 30 runs pass.**

Other observations:
- Preloaded condition (3-relation baseline seeds 0-4): fully-right next requests 6, 23, 223, 6, 0 of 341, versus 134, 49, 283, 153, 222 when the same card is handed over after loop 0. Zeroing the step embedding did not close this gap. The preloaded condition is off-distribution, so I no longer read this as a "position habit".
- Ordered-evidence models read slightly worse with both cards given (314-337 of 341 vs 340-341). Unexplained.
- An earlier CPU-trained checkpoint (same recipe): on held-out questions its **first** own request was the friend card 80/171, someone else's link card 45, right-relation-wrong-person 31, the answer card 14. On practised: friend card 231/341, someone else's link card 110.
- A separate earlier experiment on answer-only models (cards supplied with look-alike distractors, no retrieval training): answers followed the *value word* rather than whose value it was (swap tests: 0-2 of 256 followed the card); entity slots were unused; a selector that was *told* where the person and relation tokens sit fixed choosing (about 1/3 -> 9/10) but not two-hop.

**Training curves** (`recall@k` = how often the first own request hits a gold card, measured on training batches):

| run | 1-hop own (final) | recall@k at step 1000 / 2000 / 2500 / 3000 / 3500 / 3700 |
|---|---|---|
| base-s0-4000lr | 359/512 | 0.00 / 0.12 / 0.13 / 0.25 / 0.34 / 0.44 |
| base-s1-4000lr | 199/512 | 0.00 / 0.12 / 0.12 / 0.12 / 0.13 / 0.25 |
| base-s2-4000lr | 473/512 | 0.00 / 0.18 / 0.54 / 0.59 / 0.68 / 0.71 |
| base-s3-4000lr | 371/512 | 0.04 / 0.12 / 0.26 / 0.40 / 0.49 / 0.52 |
| base-s4-4000lr | 426/512 | 0.05 / 0.13 / 0.37 / 0.49 / 0.57 / 0.60 |
| nostep-s0-4000lr | 115/512 | 0.03 / 0.12 / 0.12 / 0.13 / 0.12 / 0.13 |
| nostep-s1-4000lr | 422/512 | 0.00 / 0.13 / 0.25 / 0.53 / 0.55 / 0.61 |
| nostep-s2-4000lr | 460/512 | 0.04 / 0.13 / 0.13 / 0.43 / 0.60 / 0.62 |
| nostep-s3-4000lr | 455/512 | 0.05 / 0.13 / 0.47 / 0.58 / 0.61 / 0.60 |
| nostep-s4-4000lr | 457/512 | 0.05 / 0.30 / 0.53 / 0.59 / 0.64 / 0.66 |
| ordered-s0-4000lr | 112/512 | 0.00 / 0.13 / 0.12 / 0.12 / 0.12 / 0.12 |
| ordered-s1-4000lr | 385/512 | 0.00 / 0.12 / 0.13 / 0.29 / 0.35 / 0.37 |
| ordered-s2-4000lr | 496/512 | 0.04 / 0.15 / 0.54 / 0.56 / 0.69 / 0.71 |
| ordered-s3-4000lr | 456/512 | 0.04 / 0.18 / 0.47 / 0.57 / 0.64 / 0.66 |
| ordered-s4-4000lr | 494/512 | 0.05 / 0.13 / 0.47 / 0.60 / 0.69 / 0.71 |
| cool-s0-4000lr | 112/512 | 0.00 / 0.12 / 0.13 / 0.12 / 0.12 / 0.12 |
| cool-s1-4000lr | 491/512 | 0.00 / 0.20 / 0.53 / 0.57 / 0.71 / 0.72 |
| cool-s2-4000lr | 296/512 | 0.01 / 0.13 / 0.13 / 0.13 / 0.27 / 0.31 |
| cool-s3-4000lr | 512/512 | 0.04 / 0.14 / 0.53 / 0.63 / 0.69 / 0.72 |
| cool-s4-4000lr | 448/512 | 0.05 / 0.13 / 0.48 / 0.59 / 0.64 / 0.64 |
| base6-s0-4000lr | 108/512 | 0.00 / 0.12 / 0.13 / 0.12 / 0.12 / 0.12 |
| base6-s1-4000lr | 115/512 | 0.04 / 0.13 / 0.12 / 0.12 / 0.12 / 0.12 |
| base6-s2-4000lr | 391/512 | 0.00 / 0.13 / 0.13 / 0.23 / 0.44 / 0.53 |
| base6-s3-4000lr | 198/512 | 0.00 / 0.13 / 0.13 / 0.12 / 0.20 / 0.22 |
| base6-s4-4000lr | 452/512 | 0.00 / 0.13 / 0.29 / 0.54 / 0.61 / 0.64 |
| ordered6-s0-4000lr | 105/512 | 0.00 / 0.13 / 0.12 / 0.13 / 0.13 / 0.12 |
| ordered6-s1-4000lr | 118/512 | 0.04 / 0.12 / 0.13 / 0.12 / 0.13 / 0.12 |
| ordered6-s2-4000lr | 410/512 | 0.00 / 0.13 / 0.24 / 0.33 / 0.54 / 0.58 |
| ordered6-s3-4000lr | 116/512 | 0.00 / 0.12 / 0.12 / 0.13 / 0.12 / 0.12 |
| ordered6-s4-4000lr | 112/512 | 0.00 / 0.13 / 0.13 / 0.13 / 0.12 / 0.13 |

In every run recall stays near 0.12 until about step 2,000 (the teacher phase ends at 55% = step ~2,060), rises at a seed-dependent time, and is still rising when the run stops. A 12,000-step baseline run is in progress; I do not have its results yet.

## 6. What I want from you

1. **Ranked candidate causes**, treating these as possibly different failures: (a) practised questions: right relation, wrong person in the second request; (b) held-out: the second request almost never names relation 2, even in runs that name the right person 100+ times; (c) held-out: in many runs the *first* request is not the friend card; (d) seed spread / late take-off. For each cause: the mechanism in this architecture, which numbers above support it, which argue against it, and what is untested.
   Please consider at least: that the query is one linear read of one register, so both "who" and "which relation" must be routed through a small shared Think block with no explicit copy path; that a card's key and value come from the same pooled vector; whether the friend's identity on a fetched link card is available to the query path at all (pooled value row, slot binding); that `LINK REL_2` never occurs in training, so the reader's contextual state for the held-out question may itself be out of distribution; the set-style ASK loss, the BCE ASK target, the random teacher order, the detached top-1 and the 0.2 early answer weight; and plain undertraining.
2. **What the numbers above already settle**, and what they cannot settle.
3. **Is the held-out test fair for this architecture?** With 2 (or 5) practised relations, is a relation-specific lookup simply the easier solution than a general "copy the question's relation" rule? What minimum change to data or architecture would make the general rule the easier one? Cite relevant literature on compositional generalisation, pointer/copy mechanisms, multi-hop retrieval training or variable binding if it bears on this (real references only; say so if you are unsure a paper exists).
4. **The single cheapest next experiment** that separates your top two causes: one change against the baseline, 5 seeds, runs of about 11 minutes each on one consumer GPU (5 in parallel), with pass marks fixed in advance and the result that would prove you wrong. Then the next two experiments in order, each conditional on the previous result.
5. **Mistakes in my reasoning or my probe design.** Be direct.
6. **Plain-language summary for me:** 8-12 sentences, using the Mira/Oren shoes example, every technical term explained in one line.

Keep the three questions (who, which relation, first request) separate in your answer, and do not propose bundles of several changes at once: I want to change one thing at a time.
