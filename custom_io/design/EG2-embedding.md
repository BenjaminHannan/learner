# EmbeddingGemma 2 inside B2 (written 2026-10-06, 1:40 PM ET, before any run)

Ben, 1:10 PM ET: "No I don't care. I think it would be best for our model as an embedding." So the test that was planned as a
training-only meaning teacher (marks: `/mnt/project-files/embeddinggemma/PASS-MARKS-meaning-teacher.md`) now has EmbeddingGemma 2
inside the model as its embedding. The teacher arm is kept as a third arm because it costs only 2 more runs. Marks: PASS-MARKS.md
addendum 4 (the source's marks, unchanged). Code: `models/eg.py`, `models/ledger.py` (`eg_embed`, `eg_teach`), `models/reader.py`
(`extra`). Tests: `tests/test_ledger_eg.py`.

## The interface: per-token states, spread over each token's characters (chosen)
B2 reads characters. Its thinker points at numbers and words by where they are, and its talker copies answers letter by letter from
the prompt. A single pooled vector says what a sentence means but not where anything is, so it could not feed those pointers. The
per-token states keep both: each token's 768-d state (EmbeddingGemma's own `last_hidden_state`, after its 512 -> 768 projection)
is given to every character inside that token. Gemma tokens carry their leading space, so every character lies inside exactly one
token (checked on 2,000 training prompts), and digits are single-digit tokens.

Where it goes in: added to B2's character embedding (letter + position + place), before B2's small conv reader:
`x = E_char + E_pos + E_place + eg_proj(LayerNorm(H_token))`, then the 2 conv blocks, controller and talker exactly as in B2.
B2's own letter path stays because the skills prompts are full of made-up words (`sune`, `perayu`) and letter tasks that
EmbeddingGemma only sees as sub-word pieces. `eg_proj` (Linear 768 -> 256) starts at zero, so at step 0 the model computes exactly
what plain B2 computes (tested), and every B2 weight starts identical at the same seed. Only `ln_eg` and `eg_proj` (198,400 params)
are new; EmbeddingGemma itself is frozen, never saved in the checkpoint and run again on the current rows wherever B2 runs its
reader (thinker and talker, the donor swap included).

Prefix: `task: sentence similarity | query: ` (the card's SentenceSimilarity prompt, the same one the teacher arm uses). Only the
prompt's own tokens feed B2; the prefix only conditions them.

## Sizes (vocab 108, S config)
| model | trainable | borrowed, frozen | whole model (borrowed counted) |
|---|---|---|---|
| plain B2 | 3,302,481 | 0 | 3,302,481 |
| EGE (embedding) | 3,500,881 | 271,002,624 (EmbeddingGemma 2 text part) | 274,503,505 |
| EGT (teacher; head dropped after training) | 3,368,785 in training | 0 | 3,302,481 |

The text part's 271,002,624 = 134,217,728 word table + 136,784,896 transformer and projection (the card's "270M text"); the
vision (170M) and audio (300M) encoders are never loaded.

## Cost
EmbeddingGemma runs once per training batch (frozen, no gradients). On the build box CPU a batch of 32 takes about 3 s, nearly all
of it EmbeddingGemma; on the 5070 Ti it should add something like half again to a B2 run (untested until the first run reports
steps per second). The teacher vectors are computed the same way, on the fly, from the training batch only, instead of being
precomputed into a file: same frozen model, same prompts, no file to stage and hash.

## What could go wrong (suggested)
- The reader gets much stronger, so the leak checks matter: with loops:0 the talker's copy pointer reads the reader output directly,
  and EmbeddingGemma gives every character a view of the whole prompt. Mark 5 catches it.
- Gains, if any, should show first on the frame and vocab splits (new wording, new words); the variant split (unpractised sub-task)
  needs new computation, which an embedding cannot supply.
- A real pass changes the size class: EGE is a 274.5M model under the size rule.

## Setup on the PC (PC-JOB.md section 6)
transformers >= 5.19 in its own folder first on PYTHONPATH (the shared venv keeps 5.17 for the running queues), the weights once,
then `python -m custom_io.models.eg check cuda` must print `"ok": true` (3 probe vectors within cos 0.999 of the build box's).
