# Only keep the important word links? (Fri Oct 9, ~9:30 AM ET)

Asked by Ben, 9:26 AM ET 10-09: attention computes every word pair, even useless ones like "the" and "example", with the same effort;
could the model keep a summary of only the important relationships instead?
Follows `running-summary-2026-10-08.md` and `fast-slow-2026-10-08.md`. Labels: **shown** (our code or results), **suggested**, **untested**.
Nothing was run.

## 1. Short answer

- Ben is right about the work: full attention checks every pair. It is not right that every pair counts the same: attention learns to
  give useless pairs almost zero weight. It still pays to check them.
- Our model already does most of what he describes (shown): the letter reader only lets each letter see 4 neighbours each side
  (`custom_io/models/reader.py`: "no attention", kernel-5 convs), and inside the thinker the words never compare with each other. A few
  learned note vectors each look over the words and keep what matters (`ledger.py` `CBlock`).
- The only part that compares every word with every word is the borrowed, frozen Gemma embedder, and adding it helped: EGE +2.67 pooled-5
  over B2, ahead on 6 of 6 seeds (shown, big-run PLAN.md sec. 1).
- On today's short questions there is almost nothing to save (suggested). For long input it matters, and the modern recipe is learned
  picking. Big-run recipe unchanged.

## 2. Rough counts (suggested, arithmetic)

- An 81-letter question: every letter with every letter = 6,561 checks.
- Our thinker: 44 note vectors (caps-fixed build) x (81 letters + 27 slots) = 4,752 checks per round, x 8 rounds = about 38,000. So at
  this length the thinker does not save work; its gain is structure, not speed.
- A 10,000-word input: every pair = 100 million checks; 44 notes x 10,000 x 8 rounds = 3.5 million. Here the summary design wins big.

## 3. What the papers say (suggested; abstracts and summaries)

| Idea | Paper | Claim |
|---|---|---|
| Nearby words plus a few "global" positions | Longformer 2004.05150, BigBird 2007.14062 | Close to full attention on long documents at much lower cost. Our window + note vectors is this same shape. |
| Learned picking of which blocks to read closely | Native Sparse Attention, 2502.11089 (DeepSeek) | Compress each block of 32-64 tokens into one summary, use the summaries to pick blocks to read closely, plus a nearby-words window. Reported to match or beat full attention on general, long-context and reasoning tests, with large speedups at 64k length. |
| Learned skipping of whole words at some layers | Mixture-of-Depths, 2404.02258 | Same quality for less compute (from memory; not re-opened here). |

Pattern: the wins are in speed on long inputs; quality holds rather than jumps. No paper found showing it makes small models smarter on
short inputs.

## 4. Would it help our goals? (suggested, untested)

- Skills, few-example learning, scaling bar on today's questions: no expected gain; the one all-pairs part we added (Gemma) helped.
- Long input, text world, Minecraft: yes, together with the running summary: carry notes forward, and learn which old pieces to look back
  at (the NSA pattern).
- Rules: the picking must be learned (as in NSA), never a hand-written list of words to ignore. Fits the no-hard-coding and deploy rules.

## 5. What to do

Nothing now. Add learned picking at the long-input stage (roadmap stage 12), next to the running summary. No test proposed.
