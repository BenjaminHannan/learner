# Fresh names: why the score was 0%, and what to do about it

*Memo, 18 Sep 2026. Covers the 10-minute 4M run (`artifacts/premonition-step1-4M-1789770088141917828-23843`). No project files were changed. The probe scripts are `probe.py` and `probe2.py` in this scratchpad. Every paper cited was checked by web search.*

## Headline

**The 0/222 on fresh names is a tokenizer bug. It isn't a finding about transformers.** The run loaded the saved file `data/tokenizer/premonition-tok-v1-fallback.json` (sha `16814d36…`). That file has **no syllable list**, so the name-splitting rule in `tokenizer.py` never ran. The tokenizer was fitted on train text only, so:

- **Train names became one token each.** All 262 train-split person names turned into a single token (" nuvi").
- **Fresh names became 3–4 odd pieces** (" ", "si", "ba").

In a 423k-token train sample, **45 of the 46 pieces that fresh names are made of never appear**. The lone " " token only ever comes before `[answer]` or `[feedback]`. The model never learned to write these tokens.

`build_tokenizer` (`step1.py`, around line 600) reuses any existing file without checking that it has syllables. The file seems older than the syllable feature: it was saved at 15:48, and `tokenizer.py` was changed at 16:39.

**Check the 1-hour reruns:** if their JSON shows the same sha, expect about 0% on fresh names at both 4M and 28M. That won't mean scale doesn't help.

## 1. Why small transformers fail to copy or bind new names

| Finding | What fixed it |
|---|---|
| **Induction heads** (Olsson 2022): the basic copy circuit ("predict what followed this token last time"). It needs 2+ layers and forms suddenly, early in training. | 2+ layers and enough training. Your 4 layers are enough. |
| **Data shape** (Chan 2022): the model learns from context when items are *bursty* (they clump inside a sequence), when many items are rare, and when meanings change between sequences. Otherwise it memorises into its weights. | Change the data. A Zipf-shaped mix gets both. |
| **The skill can fade** (Singh 2023, 2025): learning from context appears, then gets replaced by memorisation. The two strategies compete and share parts. | L2 regularisation kept it. Pick checkpoints on a context-dependent validation set. |
| **Race between circuits** (Bietti 2023; Reddy 2024; Nguyen & Reddy 2025; Singh 2024): simple statistics are learned first, and the copy circuit comes later, suddenly. Enough item diversity tips the model into generalising. | More distinct items. |
| **Binding** (Feng & Steinhardt 2024): larger LMs tag each entity and its attribute with a shared "binding ID", and this improves with size. Gur-Arieh 2026: position-based lookup gets noisy for middle entities as more are added. Tang 2026: a fragile "removed" tag causes tracking errors. | Mostly scale. Zeroing that tag partly fixes it. |
| **Variable binding from scratch** (Wu 2025): the model goes from random, to a shallow heuristic, to real chain-following. | Train past the heuristic stage. |
| **Symbolic heads** (Yang 2025, 70B model), **fresh-symbol theory** (Guan & Bradic 2026, preprint), **entity tracking** (Kim & Schuster 2023: a fine-tuned small T5 partly handled new entities) | Regularisation, data size, fine-tuning. |
| **Under-trained tokens** (Land & Bartolo 2024): tokens in the vocabulary but missing from training misbehave. **This is your bug.** | Match the tokenizer to the data, and scan for such tokens. |
| **Explicit copying** (Pointer Networks, CopyNet, Pointer Sentinel, Pointer-Generator): the output can be "copy input position *i*". | Handles rare and unseen words by design. |
| **ESBN** (Webb 2021): entities and the controller only meet through an external key–value memory. **Anonymisation** (Hermann 2015): names become markers, shuffled randomly for every example. | Almost perfect generalisation to new entities / the model has to read the text. |

## 2. Which cause is it here?

**For the 0%, it's tokenization.** I ran read-only probes on the checkpoint (CPU, about 3 minutes):

- **Lost at the first token.** After `[answer]`, the first token of a fresh-name answer (the lone space) gets a probability of about 0.0000 in every item I checked.
- **Swapping names flips the score.** 42 held-out "Who has … now?" items with fresh names scored **0/42**. With each fresh name swapped for a seen one, and the held-out templates and styles kept, they scored **8/42**. Going the other way, 60 train-split items dropped from **11/60 to 0/60**. Only the spelling changed.
- **The second, real problem is binding.** On 150 train-split name answers: 33 right, 101 a *wrong name from the same visit*, 16 "nobody", and 0 names from outside the visit. Picking randomly among the visit's median 7 people would score about 14% (my estimate); the model scores 22%. **It copies who is present, but barely binds who did what.** That fits the below-chance counterfactual pairs.
- **A generic copy test didn't help.** Repeating 60 random tokens didn't make the second copy easier (about 13.7 nats both times). This is weak evidence, because random tokens are far from village text.

Architecture is not the first suspect. Jelassi 2024 proved two layers can copy long strings.

**Cheap diagnostic experiments**

1. **Token audit (done, seconds).** *Result:* fresh-name pieces never appear in training.
2. **Full name-swap evaluation (about 5 min, existing checkpoint).** Swap every fresh name in the held-out set for an unused seen name, then run the normal grader. *Expected:* name answers go from 0% to about 20%, and overall held-out accuracy also rises, because fresh names in the context are unreadable too. Whatever gap remains comes from templates, styles or question depth.
3. **Refit the tokenizer and repeat the 10-minute run.** Move the old file aside so step1 refits it with `SYLLABLES`. The token cache is keyed by the tokenizer hash, so the data re-encodes automatically. *Expected:* fresh ≈ seen if the model really copies. If seen stays well above fresh, it memorised the 262 syllable pairs, which points to the data. One catch: in my simulation, about 60% of 7-person visits have two people who share a first syllable, so the model has to copy a 2-token span *and* bind it correctly.
4. **Name-diversity test (2 × 10 min, needs a small flag in `names.py`).** With the fixed tokenizer, compare (a) today's 262 train names with (b) random renaming for every visit from a much larger pool, such as 3-syllable person names. *Expected (Chan; Nguyen & Reddy):* (b) closes any fresh-vs-seen gap and may help binding.
5. **Undertraining check (free once the reruns finish).** Repeat the right / wrong-but-in-visit / "nobody" breakdown at 10 minutes and at 1 hour. *Expected:* if binding climbs well above about 14%, it was undertraining. If it stays flat, it's the data or the architecture.

## 3. Mechanisms for reliable fresh-name handling, ranked for Premonition

| Rank | Mechanism | Evidence | Fit with Premonition's design | Cost |
|---|---|---|---|---|
| 1 | **Names as pointers**: the reasoner sees only slot IDs (16–32 slots); spellings live in the store | ESBN; Hermann's anonymisation | Fresh names look exactly like seen ones by construction. This is your core design. | Low |
| 2 | **Shuffle slots for every visit** | Hermann's shuffled markers; Chan's changing meanings | Stops a slot picking up a fixed meaning in the weights. Needed alongside #1. | Trivial |
| 3 | **Exact-copy pointer in the reader** | Pointer nets, CopyNet, Pointer-Generator | Matches the short exact-copy window and works for unseen words | Low–med |
| 4 | **Consistent syllable tokens plus an under-trained-token check** | Land & Bartolo | Would have caught this bug | Trivial |
| 5 | **Bursty, diverse names plus weight decay** | Chan; Singh 2023; Nguyen & Reddy | Pushes the model to use context, and keeps it doing so | Trivial |
| 6 | **Learned entity memory** (EntNet) | Henaff 2017 | Overlaps with your explicit slots | Med–high |
| 7 | **Relational bottleneck** (Abstractor) | Altabaa 2024 | Optional extra for the reasoner | Med |

**Remaining risk:** pointers fix *spelling*, not *binding*. The 22%-vs-14% result shows that "who did what" is the hard part.

## 4. What a fair transformer baseline needs

- **The same fixed tokenizer**, and an audit showing every evaluation token appears in training.
- **An anonymised baseline**: the same text with names replaced by @e1…@e32, shuffled for every visit. This is probably the strongest cheap competitor. If Premonition can't beat it, the store isn't earning its keep.
- **A copy mechanism**: a pointer-generator-style head over the context.
- **The same data fixes** Premonition gets: diverse, bursty names and renaming for every visit.
- **Fair training**:
  - matched tokens and compute
  - one longer run that continues until binding stops improving
  - tuned learning rate and weight decay
  - at least 3 seeds
  - matched parameters at 4M and 28M, counting the store
- **Checkpoints chosen on a fresh-name validation set**, not on training loss.
- **The same report for both models**: seen vs fresh names, the name-swap test and counterfactual pairs.

## References

Olsson 2022 https://arxiv.org/abs/2209.11895 · Chan 2022 https://arxiv.org/abs/2205.05055 · Singh 2023 https://arxiv.org/abs/2311.08360 · Singh 2025 https://arxiv.org/abs/2503.05631 · Singh 2024 https://arxiv.org/abs/2404.07129 · Reddy 2024 https://arxiv.org/abs/2312.03002 · Nguyen & Reddy 2025 https://arxiv.org/abs/2412.00104 · Bietti 2023 https://arxiv.org/abs/2306.00802 · Feng & Steinhardt 2024 https://arxiv.org/abs/2310.17191 · Gur-Arieh 2026 https://arxiv.org/abs/2510.06182 · Tang 2026 https://arxiv.org/abs/2605.30233 · Wu 2025 https://arxiv.org/abs/2505.20896 · Yang 2025 https://arxiv.org/abs/2502.20332 · Guan & Bradic 2026 https://arxiv.org/abs/2605.07120 · Kim & Schuster 2023 https://arxiv.org/abs/2305.02363 · Land & Bartolo 2024 https://arxiv.org/abs/2405.05417 · Jelassi 2024 https://arxiv.org/abs/2402.01032 · Vinyals 2015 https://arxiv.org/abs/1506.03134 · Gu 2016 https://arxiv.org/abs/1603.06393 · Merity 2016 https://arxiv.org/abs/1609.07843 · See 2017 https://aclanthology.org/P17-1099/ · Webb 2021 https://arxiv.org/abs/2012.14601 · Hermann 2015 https://arxiv.org/abs/1506.03340 · Henaff 2017 https://arxiv.org/abs/1612.03969 · Altabaa 2024 https://arxiv.org/abs/2304.00195
