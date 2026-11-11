# Prompt for GPT (web): is the English failure the exit or the data?

Paste everything below the line. GPT cannot see the repo; this stands alone.

---

I am building a small reasoning model and need a second opinion on a diagnosis. Please label every claim **shown** (measured, in my numbers or a paper you can cite), **suggested** (your reasoning) or **untested**.

**The model.** A frozen 1.2B language model (LFM2.5, mostly short-convolution layers plus a few attention layers) is used twice. (1) As a reader: the passage (at most 64 tokens) goes through the LM once and we take the final-layer hidden state per token (width 2048). A small trained reader maps each token 2048 → 32 → 256. (2) As a talker: a ~9M-parameter trained "core" (2 shared transformer blocks, width 256, 8 heads, 4 loop rounds) processes those 256-wide token states. Its final per-token states go 259 → 32 → 2048 and are then **average-pooled into exactly 8 vectors**. The frozen LM sees only BOS + those 8 vectors + its own output so far, and must generate the answer. It never sees the passage text. Trained: reader, core, prefix map. Frozen: the LM.

**Result 1 (calculator task, shown).** Two-number add/subtract word problems with a calculator tool. 60 two-digit answers used in training, 30 held out. With the 8-vector pooled exit, held-out answers scored 0-4% (2 seeds); 375 of 377 wrong held-out answers were training answers, while the right calculator call was made ~90% of the time. Adding one extra prefix vector equal to the frozen LM's own embedding of the calculator's result token raised held-out answers to 84-90%, and after varying the training wording, 99.3% over 6 seeds.

**Result 2 (English reading, shown).** Same architecture, no calculator. 48 training question-answer pairs about short passages, answers ~4 tokens, usually words from the passage. After 9,216 updates, 4 runs fit 40-43 of 48 training questions but answer only 2-7 of 48 fresh understanding questions and 1-3 of 48 transfer questions.

**Two explanations.** (A) The pooled 8-vector exit only learns to say a closed set of answers, as in result 1, so fresh answers (new words) can't come out. (B) 48 training questions is far too few for any architecture to learn reading comprehension; it simply memorised.

**Questions.**
1. Which explanation is more likely, or is it both? What else could explain result 2?
2. Propose **one** cheap check that tells A from B, using only the already-generated wrong answers (no training). Fix the decision thresholds before seeing the data, and say which result would prove your preferred explanation wrong.
3. My proposed fix for A is a pointer exit: 8 pointer slots, each a softmax over input positions computed from the core's final state, whose value is the frozen LM's input embedding of the pointed-to token. Is this sound? What would make it fail? How would you stop the frozen LM from doing the reasoning itself?
4. Propose one experiment, one change at a time, with pass marks fixed in advance (I use 6 paired seeds because seed-to-seed SD is ~12 points on the noisy metric) and the result that would prove it wrong.
5. Finish with a plain-language summary for a high-school senior.
