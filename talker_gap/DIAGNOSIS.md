> **Update 2026-10-08 (read RESULTS.md first):** the wave-1 and sealed runs changed the headline. A new-style pointer head over Gemma states is good on held-out TEACH kinds (82-85%) but 11-20% on the outside sets, and TEACH's training questions contain no where/why/when/how-many. So the leading explanation is question-type coverage in the training data, not the talker design. This file's older claims stand as written; claim 2 (question-blindness) is absent in the new head on 28 DEV pairs.

# Why our own talker trails the borrowed one - diagnosis (2026-10-08, ET)

Evidence is in `diag/D1`..`D8` (read-only Haiku reports plus orchestrator checks). **shown** = read or measured, source cited in the D-report; **suggested** = reasoning/literature; **untested** = no run yet. Everything here is the English-QA line; nothing is claimed for the card toys or the village model.

## What the numbers really compare

1. **"350M from scratch = 66.1 vs borrowed = 92.6" is not a from-scratch result (shown).** 66.1 is a *pretrained* LFM2.5-350M with the allptr recipe (`baselines.md:87`, `results-digest.md:29`); 92.6 is the pretrained 1.2B. The gap there is LM size (budget differences unknown, untested). The primary file `RESULTS-SMALL-LM.md` and `/mnt/project-files/whole-model-roadmap/` are **not on this machine**; I could not check them.
2. **"13.6 vs 78.2 on unseen kinds" is not like-for-like (shown).** The 13.6 is a ~8k-parameter pointer head on a 9.0M core, trained on 48 bank questions + 8,000 generated rows from **6 families with no how/when/why questions** (D1). The 78.2 is a frozen pretrained 1.2B LM that is handed **every prompt-word embedding** plus 8 core vectors (D8, `run_english.py:219-225`). Our planned talker would train on TEACH: **52 kinds, 171,940 rows** (D4).
3. **The borrowed LM does most of the work itself (shown, with one-seed caveats).** Bare 8-shot LM pooled 72.7 on the unseen sets; allptr's six-seed mean is 78.2 (CI 74.1-82.2), so the core path adds about 5 points at most. The shuffled-core check covers one seed only, and that seed is the low rerun (73.18): shuffling leaves it at 73.18 (334/384 identical; 14 go right->wrong, 14 wrong->right). A core-skipped allptr control does not exist (untested). The gap therefore mostly measures *pretrained comprehension vs a tiny head*, not "talker quality".

## Why the small copy talker fails on unseen kinds

4. **Errors are where to point, not how to speak (shown).** Unseen kinds, 6 seeds: wrong location 47.0%, wrong span edges 31.2% (84.8% of those too long), yes/no 6.1%, decode/gate 2.0%. The borrowed LM: location 2.9%, edges 12.5% (D1, D8).
5. **It is question-blind on unseen kinds (shown, medium confidence).** For two different questions on the same passage, 59% (335/564) get the *identical* span; practised kinds 0/80.
6. **Likely mechanism (suggested).** The span scorer is a unary Linear(256,2) per position with no question vector; the reader is a frozen *causal* LM, so passage states cannot see the question; all question binding must come from a 9M core trained on 6 families, which reached loss 0.006 (memorised the practice mix). 'where' training answers are all first-sentence locations, unseen 'where' asks for the location after a move (a shortcut is plausible, untested).

## Why this does not carry over to our plan

7. **EmbeddingGemma 2 attention is bidirectional (shown, `modeling_embedding_gemma2.py:313,331`).** With "passage + question" as one input, its per-token states can see the question, unlike PR #37's causal reader.
8. **TEACH is span-shaped (shown):** 97.0% of short answers occur verbatim in `source_text`; 0.45% contain a word absent from the prompt. A copy/pointer talker is the right form.
9. **Today's own talker cannot say most eval answers (shown):** B2's GEN registers hold 8 characters; 18.4% of TEACH short answers and **60.6% of eval-set answers are longer than 8 characters**, so they only pass through the NUM/span path. B2 reads the final state plus the raw prompt characters, **not** intermediate notes (D3).
10. **Yes/no is 51% of TEACH but 10.7% of the eval sets (shown)** - score short answers separately or a yes/no head hides the gap.
11. Literature (suggested, BERT/T5-scale, not verified at 5-25M): Splinter recurring-span pretraining gives 72.7 F1 with 128 SQuAD examples; question-kind diversity helps transfer (MRQA/UnifiedQA); decoders bypass the state when the input is visible, so remove or log the bypass and run a state-swap test (D6, D7).

## What is still unknown (the small check must answer it)

- How a talker trained on **TEACH + Gemma states** behaves on held-out kinds at all. PR #37's 13.6 may largely vanish with 52 kinds and a bidirectional reader (untested).
- Whether the answer is already linearly readable from Gemma's states on unseen kinds (probe P0, untested).
- Whether LM pretraining of a ~30M decoder (reference R) really beats a from-scratch pointer talker at equal data, and whether R uses the thinker (untested).

## Plain-language version (for Ben)

The scary numbers compare apples and oranges. The "borrowed" talker is a whole pretrained language model that reads the question again by itself, so it barely needs our thinker; the "own" talker was a tiny pointing head that had only ever seen six kinds of question, and it mostly pointed at the wrong spot. Our real plan gives the talker 52 kinds and a reader that can see the question, so that failure may be much smaller. We now test that directly, with the pass marks written down first.
