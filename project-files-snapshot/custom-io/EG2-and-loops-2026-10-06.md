# EmbeddingGemma 2 in B2, and the looped-LM ideas (Oct 6, 2:55 PM ET)

Nothing is needed from you. Both tests are queued on your PC. They run after the Qwen teacher pilot, behind queues 33, 30 and 35.

## 1. EmbeddingGemma 2 as B2's embedding (queue 36, 4 runs)
- **How it plugs in (chosen):** per-token states, not one pooled vector.
  - B2 points at numbers and words by where they sit, and it copies answers letter by letter. A pooled vector cannot say where anything is.
  - So every character gets the 768-number state of the EmbeddingGemma token it sits in. That state is added to B2's own letter embedding.
  - B2's small letter reader stays. The skills prompts are full of made-up words (`sune`, `perayu`) that EmbeddingGemma only sees as word pieces.
- **The change starts at zero.** At step 0 the model computes exactly what plain B2 computes (tested).
- **Sizes**, with borrowed parts counted:

  | arm | trainable parts | whole model |
  |---|---|---|
  | plain B2 | 3,302,481 | 3,302,481 |
  | EGE (EmbeddingGemma as the embedding) | 3,500,881 | 274,503,505 (EmbeddingGemma's text part: 271,002,624, frozen) |
  | EGT (teacher arm, kept because it is cheap) | 3,368,785 while training | 3,302,481 (its extra head is thrown away) |

- **Marks**, written before any run: the coordinator's marks, unchanged.
  - Pooled-5 at least +1 on both seeds.
  - At least +3 on the unpractised-in-family split.
  - No split drops more than 2.
  - Chain-5 at least 99.
  - Leak check: loops:0 and donor both at most 5.
- **Risk to the leak mark (shown):** plain B2 itself read 10.8 at loops:0 on seed 201 of the confirm. An arm can therefore miss the mark for a reason that is B2's, not EmbeddingGemma's. B2's own values are reported next to each arm's.
- **On your PC:** EmbeddingGemma's self-check passed there (2:08 PM ET, cosine 0.99997 against this machine's vectors).

## 2. Amazon's looped model (ALoDLM): what fits B2
- **I measured before building anything.** The probe used B2's two saved models, on CPU, with no training. The gates were written first.

| question | answer (shown) |
|---|---|
| Does B2 need more loops on arithmetic? | No. Every program question is right by round 8, and more rounds change nothing. |
| Does it already give numbers more rounds? | Yes. Number tasks settle about 1.6 rounds later than word tasks, because their programs are longer. |
| Does the hidden state blow up across loops? | No. It grows 3-4x over 8 rounds; the gate was 10x. |
| Would stopping early help (halting gate)? | Barely. Only 1.7-1.9% of rows were right earlier and wrong at the end; the gate was 2%. |
| Where is the loss? | In the rule and lookup tasks that have no program. Their answers drift as rounds go on: 16 rounds cost about 1 point. |

- **One gate opened.** It leads to the one ALoDLM idea that fits B2: training the answer at every round, so the answer stays put once the program is done.
- **That is Test LR (queue 37, 2 runs).** No new parts, still 3.3M.
- **Its pass marks:**
  - Pooled-5 at least +1 on both seeds.
  - Answering at 16 rounds loses no more than 0.3.
  - Nothing else drops.
- **Expectation (suggested):** small. The rows it could fix are only about 1-2% of the in-dist questions.

## 3. B2 confirm so far (5 of 6 seeds, shown)
- **Against the plain transformer:** B2 is ahead by +20.1 on pooled-5, on all 5 seeds.
- **Against the transformer that writes its steps:** B2 is ahead by +6.8 on pooled-5, also on all 5 seeds.
- **Still to come:** seed 205 and the pretrained baselines, after the Qwen pilot.

## Backlog
- **A "used" mark for spent numbers.** This came from the creative roadmap: B2 reuses numbers it has already used.
