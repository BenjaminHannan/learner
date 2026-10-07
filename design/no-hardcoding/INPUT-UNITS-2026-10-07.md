# Letters, bytes, word pieces, byte patches or Gemma: what B2 should read (2026-10-07)

Asked by Ben 12:01 PM ET 10-07: "feeding individual letters ... not a lot of information into the model". Thread "No hard-coding + richer input" (Opus, ultracode).
Labels: **shown** = in our result files or a paper's abstract page that was opened, **suggested** = reasoned, **untested** = not run. Our numbers: 2-seed means (200, 201) from `custom_io/results/*/RESULT.json` on branch `claude/custom-reader-talker-4x309r`, pulled by a helper and spot-checked against `RESULTS-EG2.md`. Papers: `/mnt/project-files/papers/no-hardcoding-papers.md`.

## Short answer

- Letters lose no information: every word and digit of the question is there. What can be thin is how much each position **knows** before the thinker starts, because B2's reader is shallow (2 conv layers, a 9-letter view, no attention) and has learned word meanings from only about 12M words of practice.
- Our own tests say this costs about 2 points, not more: adding Google's pretrained word meanings on top of the letters (EGE) gained +1.6 / +2.1, mostly on new wording (frame +3.6, vocab +2.7) and on word-relation families (order_chain +22, list_index +15, table_calc +15, kin_chain +13).
- Taking the letters away is much worse: every version that read only Gemma's word pieces lost the cipher tasks (100 to 2.5-10), and removing the 9-letter window alone cost 6.3-6.8 points.
- B2's big losses are elsewhere: the variant split (B2 misses 66% of it: new layouts and new kinds of computation) and the families with no worked steps in the data (fewshot_number_rule 24%, table_lookup 27%). Better reading does not fix those.
- So: keep letters (as raw bytes) for exactness, and make each position richer on top: (1) attention across the whole question inside the reader, (2) learned groups of letters that act like words, with no hand-written word splitter, (3) pretrained meaning as a side channel (EGE) if the 6-seed check confirms it.

## What we have measured (shown)

| Arm (2-seed mean) | What the reader gets | pooled-5 | frame | vocab | cipher_map (pooled) | chain-5 |
|---|---|---|---|---|---|---|
| B2 (5090 pair) | letters + 9-letter window | 73.9 | 87.4 | 88.0 | 96.7 | 99.5 |
| EGE | letters + window + Gemma word pieces | 75.8 | 91.0 | 90.7 | 96.2 | 100.0 |
| R0 | letters, no window | 67.4 | 74.1 | 82.1 | 4.2 | 99.2 |
| EGR / EGO / EGM / EGW | Gemma word pieces (+/- letters), no window | 72.5 (EGR); the rest lower | | | 2.5-10 (in_dist) | |
| EGT | letters + window; Gemma only as a training-time teacher | 74.0 | 87.2 | 87.8 | | 99.5 |
| plain_tf_steps | letters, causal transformer writing steps | 67.0 | 80.7 | 77.3 | | 94.2 |

Other facts that bear on it (shown):
- Gemma's own vectors keep only 23% of letters under a linear read (`WHY-GEMMA-LOST-2026-10-06.md`). The letters are lost at its input, where words are cut into pieces.
- EGE lost on two letter-heavy families: seq_cycle in_dist 90 -> 73.8, letter_ops 98.8 -> 90.0 (40-80 rows, could be noise).
- Hand place codes do nothing for plain transformers (+0.8 / -0.8, `RESULTS-SCREEN.md`), so dropping them (rung P1) is probably cheap.
- More thinking rounds do not help the program families: in_dist saturates at 8 rounds and 16 costs about 1 point (`40-loops-probe`).
- Bigger plain transformer (10.8M vs 3.2M, one seed): about +2 on most splits, nothing on new answers (`02-calib-long`).
- Word pieces cut numbers at irregular places: GPT-2 splits 4-digit numbers 2+2 52%, 1+3 38%, 3+1 6%; "4821 + 937" becomes `48|21| +| 9|37`. cl100k always cuts left-to-right in threes, so the units digit of 4821 sits alone (helper measurement with tiktoken, shown).
- Our prompts are short: train p50 78 chars, p95 142, max 204 (`research/data.md`). With about 4 chars per word piece that would be about 20-35 positions instead of 78-142. At this length the thinker can already attend to every letter every round, so sequence length is not the bottleneck (suggested).

## The options

| Option | Per position | Exact letters and digits? | Hand rules? | Our evidence (shown) | Papers (abstracts opened) | Verdict (suggested) |
|---|---|---|---|---|---|---|
| **Letters / bytes** (today) | 1 letter, plus a 9-letter view from the window | yes, by construction | only the hand vocab (bytes remove it) and the place code | B2 73.9; window worth 6.3-6.8; cipher 97 | Byte-level attention is what drives character skills; hierarchies that shrink bytes lose them (Edman 2026, 2609.00463). Subword models must spend depth to get letters back (Hiraoka 2025, 2506.10641) and still fail to manipulate them (CUTE 2409.15452) | **Keep as the base stream**, as raw bytes |
| **Word pieces** (BPE) | about 4 letters | no: spelling hidden, numbers cut at odd places | the tokenizer is a frozen algorithm, not end-to-end | GPT-2 splits 4821 as 48\|21; Gemma-only readers lost the ciphers (2.5-10) | Subwords win mainly by more text per unit of compute and by giving word boundaries, not by richer positions (Gigant 2026, 2604.27263). Left-to-right digit grouping hurts arithmetic (Singh 2024, 2402.14903) | **Don't swap.** U0 tests it once, as the direct answer |
| **Learned byte patches / chunks** (BLT, H-Net, MrT5, AU-Net) | a learned group of letters | only if the letters are kept beside the groups | none: boundaries are learned | none yet | H-Net's learned chunks beat a BPE transformer at matched compute and are strongest where tokenizers are weak, nearly 4x data efficiency on DNA (2507.07955). AU-Net keeps byte skips so character tasks survive (2506.14761). MrT5 shortens after full-resolution layers (2410.20771). BLT matches token models up to 8B (2412.09871) | **Add as a side channel (U2)**, never instead of letters. Built for long text; our questions are 78-142 letters, so the win can only be meaning, not speed |
| **Pretrained embeddings** (EmbeddingGemma) | one meaning vector per word piece | no (23% of letters linearly readable) | none at run time; 271M borrowed weights | on top of letters: +1.6 / +2.1, frame +3.6, vocab +2.7; instead of letters: all four versions lost | Byte-ifying pretrained subword models keeps their knowledge and fixes character tasks (Bolmo 2025, 2512.15586) | **Side channel only (EGE)**; 6-seed check q39 decides |
| **Deeper reader on letters** (W1: attention across the whole question) | a letter that knows its whole sentence | yes | none | the window's +6.3-6.8 says local context matters; no global test yet | Local convolution alone is weak at recall; adding attention closes most of the gap (Zoology 2312.04927, in `thinker-absorb-papers.md`). Copying needs attention, proven for 2-layer transformers (Jelassi 2024, 2402.01032) | **First test (W1)** |

## Tests (marks fixed now, before any run)

All against today's plain B2 on the same seeds unless stated; recipe as B2 (24k updates, batch 256, lr 1e-3, bf16, same rows and order); size within +-3% of 3,302,481 trainable (borrowed parts counted, as Ben ruled).

**W1, global attention after the window** (architecture thread's spec, `redesign-ideas-2026-10-07.md` sec. 5; its marks stand and are repeated here so they are sealed in one place): pooled-5 >= B2 + 1 on both seeds, cipher_map in_dist >= 95, no dev split down more than 2, loops:0 leak no more than 1 above B2. Proved wrong: a cipher or lookup family drops by more than 2, or pooled-5 mean below 0.

**U0, letters vs word pieces, the direct test of Ben's question** (report-first, 2 runs). Model: plain_tf_steps (the all-learned text baseline; 6 seeds of its letter version exist from q33). Change: input and output as BPE word pieces learned on the training rows (no hand digit-splitting; vocab size chosen so the whole model stays within +-3% of 3,260,928 by shrinking width, disclosed). Seeds 200, 201 against q33's plain_tf_steps on the same seeds.
- "Ben right": pooled-5 (BPE - letters) >= +2.0 on both seeds.
- "Letters fine": <= +1.0 on both seeds.
- Anything else: tie, reported as such.
- Pre-registered prediction (from the papers and our Gemma runs, suggested): letters fine; cipher_map and letter_ops fall by 10 or more for word pieces; arithmetic families fall; frame and vocab move less than 2.
- Proved wrong for the prediction: word pieces at or above letters on cipher_map.
- If "Ben right": add a from-scratch word-piece side channel next to the letters in B2 (like EGE, no pretraining) as the next gain test.

**U2, learned letter groups** (after W1; one change on top of W1 if W1 passed, else on B2): a boundary scorer on the reader output decides where groups end (H-Net-style dynamic chunking with its ratio loss, target about 4 letters per group); each group's letters are pooled into one vector; the thinker attends to the groups and the letters. No hand-written word splitter. Pass: pooled-5 >= +1.0 on both seeds, frame and vocab both up, cipher_map in_dist >= 95, no split down more than 2, loops:0 no more than 1 above the base. Proved wrong: pooled-5 mean below 0 or cipher_map below 90. Also reported: how often the learned boundaries match word ends (a check that it found words, not a mark).

**EGE** (running as q39, marks sealed in `PASS-MARKS.md` addendum 15): unchanged.

**V1, bytes**: see the plan, section 3b. For our ASCII data it is the same input.

## What I would not test

- Gemma or word pieces instead of letters: done four times, all lost the ciphers (shown).
- Byte-patch models with a separate global model (MegaByte, BLT) at full size: they are built to shorten very long sequences; ours are 78-142 letters (suggested). U2 takes the useful part, learned groups, without the rest.
