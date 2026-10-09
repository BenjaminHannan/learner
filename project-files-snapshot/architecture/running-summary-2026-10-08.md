# A running summary instead of attention over every word (Thu Oct 8, ~8 PM ET)

Asked by Ben, 8:00 PM ET 10-08: "The way humans think is of a general summary in their brain of relevant information, rather than a
human doing attention across all words I believe. How can we add that to the model? Would it help"
Labels: **shown** = read in our code or results, **suggested** = reasoned or from papers, **untested** = never run here.
Nothing was run for this note. Small card experiments (B2 at 3M/10M) and the village model are not mixed here; this is about B2 only.

## 1. Short answer

- Our thinker already works this way (shown). Its whole memory is a small fixed set of vectors, much smaller than the question, and it
  keeps and updates that set over its rounds. It does not keep a vector per word the way a plain transformer does.
- What it lacks is the "running" part: it sees the whole question at once and forgets everything after each question (shown).
- For today's short questions that gap costs little (suggested). It matters for long input and for the Minecraft goal (suggested).
- Recommendation: no change to the big-run recipe. Add the running part at the long-input / text-world stage, as "carry the thinker's
  vectors from one piece of input to the next", keeping its ability to glance back at the current piece (suggested, untested).

## 2. How close B2 already is (shown, `custom_io/models/ledger.py` on `claude/custom-reader-talker-4x309r`)

- The thinker's state Z is 8 control vectors plus N_REG letter vectors: 17 in the build described in `model-deep-dive.html`, 44 in the
  caps-fixed build that G1 runs (N_REG 36; count inferred from `Z = cat(ctrl, place[:N_REG])` and the G1 caps).
- Every round, each Z vector cross-attends over the workspace slots and every reader output (`CBlock.forward`), then the Z vectors
  talk to each other (self-attention) and pass through an MLP. The reader outputs never attend to each other inside the thinker.
- This is the Perceiver pattern (Jaegle et al. 2021, arXiv 2103.03206): a small learned "latent" set reads a long input.
- The 6 scratch controls carry real information: zeroing them cost -1.6 pooled-5 and -7.8 chain-5 on seed 200 (shown, thread notes).
- Z starts from the same learned vectors on every question; nothing carries over between questions (shown).
- The talker still copies exact letters and words straight from the reader output (WORD and GEN copy paths), not from the summary (shown).

## 3. What humans do (suggested, from reviews)

- Working memory holds about 4 chunks (Cowan 2001, Behav. Brain Sci.).
- Readers do not read strictly once: about 10-15% of eye movements in reading go back to earlier words (figure attributed to
  Rayner 1998, Psych. Bull. 124:372; other estimates range 5-30%).
- So the human picture is "a small summary plus glances back at the page". That is close to what B2 already does within one question.

## 4. What the papers say (suggested; abstracts and summaries, not full papers)

| Idea | Paper | What it shows | Meaning for us |
|---|---|---|---|
| Small latent set reads the input | Perceiver, 2103.03206 | Works across many input types | Same as our thinker |
| Carry memory vectors chunk to chunk | RMT 2207.06881; BABILong 2402.10790 (NeurIPS 2024) | A GPT-2 with recurrent memory, fine-tuned, answered bAbI-style questions hidden in up to ~11M tokens; GPT-4 and retrieval held up only to about 10^4 | Strongest case for the "running" part; ties to our bAbI gate and long input |
| Fixed-size state only | Jelassi et al. 2402.01032 (ICML 2024); Zoology 2312.04927 | Fixed-state models are worse than attention at copying and exact lookup | A pure summary would hurt our copy talker and lookups; keep the glance back |
| Summary that learns while reading | Titans 2501.00663 (NeurIPS 2025) | Attention for the recent part plus a memory network trained as it reads; claims gains over transformers and linear recurrent models | Closest to "learn from a few examples as you read"; a large change |

Consensus pattern (suggested): the best long-input designs are hybrids, a small running memory plus attention over the recent part.

## 5. Would it help our goals? (all suggested, untested here)

- **Skills on today's questions:** little. Questions average 81 letters (max 204); the thinker already has a summary. Removing the
  look-back would likely hurt copying and lookups (section 4). An earlier note already ruled out a Perceiver bottleneck in the reader for
  this reason (`redesign-ideas-2026-10-07.md` sec. 2).
- **Few-example learning (new kinds about 1%):** possibly, in its strongest form: carry the vectors from one example to the next, or make
  the memory something that learns while reading (Titans-style). No evidence yet at our size.
- **Scaling better than a plain model (Ben's bar):** no paper found that a summary design gains more from size than attention does.
  The size of the summary (how many vectors, how wide) is one more knob to grow, which G1 partly tests (17 to 44 vectors).
- **Long input, text world, Craftax, Minecraft:** yes, eventually needed. A game runs for hours; attention over every past moment gets
  slower and costlier as it grows, while a running summary stays the same size.
- **Rules:** fits them. What to keep in the summary is learned from the training loss, not hand-coded, and the deployed model does it itself.

## 6. How it would fit in (suggested, untested)

1. Read long input in pieces (a paragraph or a block of Gemma tokens).
2. The thinker updates its vectors on each piece and carries them to the next piece (RMT-style), instead of starting fresh.
3. It can still glance at the current piece (and the talker can still copy from it), so exact words are not lost.
4. Train with back-propagation through a few pieces, as the big-run plan already does for rounds.
5. Later, if few-example learning stays stuck: test a memory that learns while reading (Titans-style), one change at a time.

Where: the long-input part of the deploy-rule table and roadmap stage 12 (text world, then Craftax). Not on the big run's path; G1 decides that.

## 7. One optional free check (proposed, not run)

"Look once" lesion on existing B2 checkpoints (`claude/b2-confirm-checkpoints`, seeds 200-205): let the thinker see the question only in
round 0, then hide the letters from its cross-attention in rounds 1-7 (workspace slots and talker copy stay). Test only, no training.
- Cost: $0, CPU only (cloud container), about 15-30 minutes; does not touch the PC GPU. Needs a small eval change (Sonnet medium).
- Marks, fixed in advance: if chain-5 stays >= 95 and pooled-5 drops <= 3 points, the thinker already thinks from its summary and the
  running version is a safe later change. If pooled-5 drops > 10, the thinker depends on re-reading and any streaming version must keep a
  look-back. Between those: mixed, report only.
- It informs the long-input design only; it does not change the big run.
