# Why do some training runs never take off? Diagnose and propose the smallest fix (no file access needed)

You are an expert in optimisation of small neural networks, retrieval/memory models and learning dynamics (plateaus, symmetry breaking, late "take-off"). You cannot see my code or files; everything you need is below. Do not ask me to run anything before answering. Label every claim **shown** (follows from the data below), **suggested** or **untested**. Do not invent citations. I am a high-school senior, so end with a plain-language summary.

## 1. Setting (a toy with synthetic vocabulary; nothing here is about a large model)

**Task.** A "visit" is a token sequence: a shuffled block of fact lines, then >= 128 filler tokens, then questions. Attribute line: `[world] ENT_e REL_r VAL_v f? \n` for each of 6 people x 3 relations (values uniform over 16 ids). Link line: `[world] ENT_a LINK ENT_b f? \n`, one per person (b = a's friend). People are pointer tokens ENT0-15 that are **re-assigned at random in every visit**. One-hop question: `[question] ENT_e REL_r [answer] VAL`. Two-hop: `[question] ENT_a LINK REL_r [answer] VAL` (value of friend(a)'s relation r). So a visit has 24 fact cards plus a NULL card.

**Model (d_model 32, key_dim 16, about 2M-parameter design run at its tiny size).**
- Reader over the whole visit: minGRU, block-local attention (window 64), minGRU, LayerNorm; causal.
- Card writer: each fact line -> one card. `p` = softmax-pooled reader states of the line's tokens (one learned scalar score per token, `Linear(d,1)`); `key = normalize(W_k p)`; `value = W_v p`. One pooled vector feeds both.
- Per question a workspace of rows: last 40 question-token reader states, 16 entity slots (initialised from ENT embeddings), 16 card rows (empty at start), 4 registers. A shared 2-layer transformer block ("Think") runs over the rows once per loop (4 loops here), adding a learned loop-step embedding each loop.
- Search request: `query = W_q norm(register0)`; `score_i = kappa * cos(query, key_i) + age_bias[bucket_i]`; kappa is learned (log-space), **initialised at 10**; age bias zero-initialised; fetched cards become ineligible; top-1 card fetched when an ASK logit > 0; the discrete choice is detached from the answer loss. Fetched card re-enters as `value + age_embedding + row_type` and also updates the entity slots of people named on that line through a gated binder.
- Optional arm "shortcut": `query += sigmoid(gate(register0)) * W_r E[REL]`, where `E[REL]` is the static embedding of the question's relation token; `W_r` and the gate start at zero.
- Init: all Linear weights N(0, 0.02), biases 0; token embedding std d^-0.5; residual output projections scaled down; minGRU time constants spread log-uniformly over 2-512 tokens.

**Training.** Losses: LM loss on the visit; answer cross-entropy decoded at every loop (weight 0.2 until all gold cards are fetched); ASK loss = binary cross-entropy on the ASK logit (target: some gold card still missing) + a **marginal set cross-entropy** `-log(sum of softmax probabilities of the gold cards not yet fetched)`; HALT loss. Gold cards are simulator labels. AdamW, lr 1e-3 constant after 100 warm-up steps, betas 0.9/0.99, weight decay 0.1 on matrices, grad clip 1.0, fp32, one consumer GPU. Curriculum in the 12,000-step recipe: steps 0-1,225 "gold" (gold cards preloaded; **no ASK or HALT loss**), 1,225-2,246 "teacher" (after each loop the teacher inserts one random still-needed gold card), 2,246-3,267 ramp from teacher picks to the model's own picks, then own picks only to step ~12,250.

## 2. The problem

Identical recipe, different random seed: most runs "take off" and become essentially perfect; some stay flat forever. `recall@k` below = share of gold cards hit by the *first* own request, measured on training batches. Its ceiling is 0.75 (one-hop questions can score 1.0, two-hop first requests at most 0.5).

`run | final one-hop answers | recall@k at steps 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 6000, 8000, 12000 | ASK loss at steps 1000 / 3000 / 6000 / 12000 | answer accuracy at 1000 / 3000 / 12000`

| baseline s0 | 115/512 | 0.00 0.00 0.00 0.08 0.13 0.12 0.12 0.13 0.12 0.13 0.13 0.13 | 0.63 / 1.98 / 2.08 / 2.06 | 1.00 / 0.95 / 0.47 |
| baseline s1 | 512/512 | 0.00 0.00 0.04 0.11 0.35 0.57 0.61 0.66 0.74 0.75 0.75 0.75 | 0.78 / 0.73 / 0.01 / 0.00 | 0.06 / 0.98 / 1.00 |
| baseline s2 | 512/512 | 0.03 0.00 0.00 0.07 0.28 0.54 0.69 0.73 0.75 0.75 0.75 0.75 | 0.69 / 0.94 / 0.02 / 0.00 | 1.00 / 0.98 / 1.00 |
| baseline s3 | 512/512 | 0.04 0.04 0.04 0.09 0.24 0.40 0.54 0.59 0.66 0.72 0.74 0.75 | 0.62 / 1.17 / 0.44 / 0.10 | 1.00 / 0.98 / 1.00 |
| baseline s4 | 489/512 | 0.00 0.05 0.04 0.10 0.39 0.58 0.64 0.63 0.74 0.75 0.75 0.75 | 0.76 / 0.83 / 0.10 / 0.12 | 0.85 / 0.98 / 0.99 |
| shortcut s0 | 506/512 | 0.00 0.00 0.00 0.12 0.13 0.13 0.12 0.12 0.66 0.70 0.74 0.74 | 0.64 / 1.93 / 0.55 / 0.05 | 1.00 / 0.93 / 0.99 |
| shortcut s1 | 99/512 | 0.00 0.00 0.03 0.10 0.12 0.13 0.12 0.12 0.13 0.12 0.12 0.13 | 0.77 / 1.92 / 2.07 / 2.07 | 0.06 / 0.96 / 0.48 |
| shortcut s2 | 92/512 | 0.03 0.02 0.00 0.09 0.13 0.12 0.12 0.13 0.13 0.12 0.13 0.12 | 0.69 / 1.95 / 2.07 / 2.06 | 1.00 / 0.95 / 0.43 |
| shortcut s3 | 512/512 | 0.04 0.04 0.05 0.12 0.12 0.26 0.39 0.45 0.75 0.75 0.75 0.75 | 0.63 / 1.62 / 0.04 / 0.05 | 1.00 / 0.95 / 1.00 |
| shortcut s4 | 473/512 | 0.00 0.04 0.00 0.11 0.13 0.51 0.56 0.58 0.69 0.75 0.75 0.74 | 0.75 / 0.88 / 0.05 / 0.16 | 0.89 / 0.98 / 0.98 |

Stuck: baseline s0, shortcut s1, shortcut s2 (3 of 10). Ten more seeds per arm are training now; I do not have them yet.

**Observations**
- Every run first reaches a plateau at recall@k about 0.12-0.13 around step 2,000-2,500. Runs that learn leave it between step ~2,500 and ~5,000 (shortcut s0 only after step 4,000). Stuck runs sit on it for the remaining ~10,000 steps with ASK loss about 2.07.
- My arithmetic (**suggested**): if the request names the right relation (or LINK) but a *random person*, the first request hits the gold card 1/6 of the time on one-hop and the friend card 1/6 of the time on two-hop (1 of 2 gold cards), giving recall (1/6 + 1/12)/2 = 0.125, and a cross-entropy near ln 6 to ln 8 = 1.8-2.1. So the plateau looks like "knows which kind of card, not whose".
- Final kappa: stuck runs 11.0, 14.8, 10.7 (barely moved from 10); runs that learned 79-147.
- Card-pooling weight by token position `[world], person, relation-or-LINK, value-or-friend, f?, newline`, averaged over validation lines (attribute lines | link lines):
  - baseline s0 (stuck): .03 .02 .42 .49 .04 .01 | .02 .02 .02 .91 .03 .01
  - shortcut s1 (stuck): .00 .01 .01 .98 .01 .00 | .00 .00 .00 .99 .01 .00
  - shortcut s2 (stuck): .02 .01 .46 .47 .02 .01 | .09 .05 .11 .58 .08 .05
  - baseline s1: .02 .30 .19 .44 .03 .01 | .03 .39 .02 .51 .03 .01
  - baseline s2: .02 .30 .29 .34 .03 .01 | .03 .42 .02 .47 .04 .02
  - baseline s3: .03 .03 .59 .31 .02 .01 | .05 .05 .38 .46 .03 .02  (learned, yet little weight on the person token)
  - baseline s4: .03 .22 .33 .36 .03 .02 | .06 .39 .07 .39 .06 .03
  - shortcut s0: .01 .01 .39 .56 .02 .01 | .03 .02 .04 .87 .03 .01  (learned, held-out 171/171, yet ~1% on the person token)
  - shortcut s3: .02 .30 .38 .26 .03 .01 | .03 .41 .04 .47 .03 .02
  - shortcut s4: .01 .33 .38 .24 .02 .01 | .02 .51 .03 .40 .03 .01
  The reader is causal and recurrent, so later tokens' states can carry the person forward; low weight on the person token does not prove the person is absent from the key.
- In stuck runs answer accuracy *falls* from ~0.95 (teacher phase) to ~0.45 once the model must use its own picks.
- Earlier 4,000-step screens (same model, shorter curriculum) showed the same thing at lower resolution: late, seed-dependent take-off, and runs that had not taken off by the end.
- People are arbitrary pointer ids re-drawn per visit, so matching "whose card" means the query path (reader -> Think -> register 0 -> W_q) and the key path (reader -> pooled line -> W_k) must agree on a code for 16 interchangeable ids; relations are 3 fixed tokens.
- For context: when a run does learn, the shortcut arm generalises to a held-out two-hop combination (171/171, 170/171, 132/171) and the baseline mostly does not (88, 18, 13, 12 of 171). The stuck-run rate is now what blocks a dependable result.

## 3. What I want from you

1. **Ranked explanations** for why some seeds never leave the "right kind of card, random person" plateau while others do, in *this* architecture and training recipe. Consider at least: symmetric alignment of two separate pathways on arbitrary pointer ids; the single pooled vector serving key and value, with the answer loss (active alone for the first 1,225 steps) pulling pooling toward the value token before any retrieval loss exists; cosine scores with kappa starting at 10 over ~25 candidates (gradient size at the plateau); the marginal set loss; the detached top-1; weight decay 0.1 and constant lr 1e-3; the curriculum switching to own picks at a fixed step whether or not retrieval has taken off; init scale N(0, 0.02) into a 16-d normalised key; a saddle or symmetric fixed point that needs noise to escape. For each: mechanism, which numbers above support it, which argue against it, what is untested.
2. **Check my plateau arithmetic** and say what else could produce 0.125 and ASK loss 2.07.
3. **What measurements on existing checkpoints would discriminate your top explanations** (I can run evaluation-only probes in seconds): be specific about what to compute and what each outcome would mean.
4. **The smallest single change most likely to cut the stuck rate**, stated so an engineer can implement it, with its closest precedent in the literature (real references only), why it should work here, and what it might break. Then a second and third candidate. I change one thing at a time, so rank them and keep them separate. Candidates I have thought of, for you to criticise rather than accept: a separate pooling for keys; tying the person code on both sides (the same projection of the static ENT embedding added to both query and key); a higher or scheduled kappa; starting the ASK loss from step 0; making the curriculum wait for retrieval to take off; lr warm restarts; an auxiliary contrastive loss between a question and its gold card.
5. **An experiment design with numbers.** Each 12,000-step run takes ~40 minutes; I can run 5-10 at once on one GPU. If the true stuck rate is around 30%, how many seeds per arm do I need to show a drop to about 5% with reasonable confidence? Give the pass mark to fix in advance and the result that would prove your top fix wrong.
6. **Mistakes in my reasoning.** Be direct.
7. **Plain-language summary for me:** 8-12 sentences, with an everyday analogy for "stuck on a plateau", each technical term explained in one line.
