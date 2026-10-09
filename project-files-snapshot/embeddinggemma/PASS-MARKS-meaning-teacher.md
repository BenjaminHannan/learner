# EmbeddingGemma 2 as a meaning teacher for B2: pass marks (written 2026-10-06, before any run)

Thread: "EmbeddingGemma 2" (Ben's link, 12:57 PM ET 10-06). Not approved to run yet. Nothing here touches GOLD-PRIVATE,
reserved or blind panels. Labels: shown = measured, suggested = reasoned, untested = not run.

## The one change

B2 (custom_io, `copy=True`, S config, 3,302,481 params), trained exactly as in the screen (same 200k skills rows, same
order, 24k updates, batch 256, lr 1e-3, bf16), plus ONE extra loss:

- Teacher: `google/embeddinggemma-2` (Apache 2.0, not gated), text part only (270M = 130M transformer + 140M word
  table). Run once, offline, over the TRAIN prompts only, with the `SentenceSimilarity` prefix, MRL-truncated to 256 dims,
  re-normalized. Dev prompts are never embedded.
- Student head: mean of the controller's 8 control tokens after iteration 1 -> LayerNorm -> Linear(256 -> 256).
- Loss: total = B2 loss + 0.1 * (1 - cosine(head, teacher vector)). Weight 0.1 fixed, no sweep.
- The head is thrown away after training. Test-time model = B2, 3,302,481 params, nothing pretrained inside it.

Why this place: the reader is a +-4-char conv with no attention, so it cannot hold a sentence's meaning; the controller
attends over the whole prompt, and iteration 1 is where it decides what is being asked (suggested).

## Comparison

Paired by seed against plain B2 on the SAME machine and seeds. Default: seeds 200 and 201, paired with the B2 confirm
runs of those seeds if they ran on the same machine; otherwise also rerun plain B2 on that machine.

## Pass (all must hold, 2-seed screen)

1. pooled-5 gain >= +1.0 on BOTH seeds.
2. variant-split gain >= +3.0, 2-seed mean (B2's weakest split: 32.3 / 34.6 in the screen, shown).
3. No dev split (in_dist, answer, frame, vocab, variant) drops more than 2.0, 2-seed mean.
4. chain-5 >= 99.0 on both seeds.
5. Leak check unchanged: loops:0 in_dist <= 5% on both seeds; donor in_dist <= 5%.

## What proves it wrong

- Any pass mark missed -> stop; the meaning teacher does not help B2 on the skills curriculum.
- If it passes: one control run per seed with the teacher vectors SHUFFLED across train rows (same everything else).
  If the control keeps >= 2/3 of the real arm's pooled-5 gain, the gain is regularization, not meaning -> reject.
- Adopt only after a 6-seed confirm at the same marks (noise rule).

## Cost

- One embedding pass over ~200k short prompts (270M model), then 2 B2-sized runs (+2 control runs only if it passes).
- Own machines first: queue behind the B2 confirm / Plan B students on whichever of the PC or Mac frees first.

## Expectation (suggested)

Small at best. The variant split holds out whole sub-tasks of a family (one structural variant per family with 3 or more, e.g. a compare_numbers question type it never
practised), and a meaning teacher can help the model recognise the question, not compute a new
sub-task. Held-out families (0-4% for every model) are not expected to move.
