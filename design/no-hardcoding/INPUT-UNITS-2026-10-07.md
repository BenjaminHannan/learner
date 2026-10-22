# Letters, bytes, word pieces, byte patches or Gemma: what B2 should read (2026-10-07)

Asked by Ben 12:01 PM ET 10-07: "feeding individual letters ... not a lot of information into the model". Thread "No hard-coding + richer input" (Opus, ultracode).
Labels: **shown** = in our result files, our code, or a paper's abstract page that was opened; **suggested** = reasoned; **untested** = not run. Our numbers: 2-seed means (200, 201) from `custom_io/results/*/RESULT.json` on branch `claude/custom-reader-talker-4x309r`, recomputed by an independent fact-checker from the raw files. Papers: `/mnt/project-files/papers/no-hardcoding-papers.md`.

## Update 10-09 (audit fixes; read this first)

This note is the 10-07 reasoning. Four things have changed since (audit B05-3, B05-14, B05-19); the finished model is described in `architecture/FINISHED-MODEL-2026-10-09.md`.
- **Gemma is the main reader, not a side channel.** Ben, 10:16 AM ET 10-08: "the model should have the gemma embedder as it's main inputting/ecoder ... it should just be in our plans for the finished model." The finished model reads the question with EmbeddingGemma 2 (frozen, 271M, counted), and the learned 9-letter window runs on the letters on top of it (Ben, "Keep", 9:29 AM ET 10-09). EGE's 6-seed check (q39) is done: +2.67 over B2 on 6 of 6 seeds (shown), though it missed its zero-round leak mark (6.6 against a limit of 4.6, plain B2's 3.6 + 1.0); under Ben's 10-08 rule that leak is reported, not gated, and the thinker-off check gates instead.
- **The gain tests ran on 10-07** (`custom_io/results/RESULTS-GAIN.md`, shown): U0 (word pieces instead of letters) lost 3.1 and 5.4 points, so letters stay; W1 (attention across the whole question in the reader) was not shown (+0.88 and +0.07 against a +1.0 mark). U2 never ran. The next input question, tokens for the thinker with the letters kept, is the architecture thread's token test TK (`architecture/TOKENS-EXPERIMENT-2026-10-09.md`).
- **Inputs can now be 2,000 letters** (Ben, 9:29 AM ET 10-09). The "sequence length is not the bottleneck" point below holds only for today's 78-204-letter questions. At 2,000 letters the thinker reads up to about 10 times more positions per round than today's longest question (2,000-letter inputs cost about 2.1x per step at tiny width, big-run PLAN, suggested), so the speed case for tokens or learned letter groups is open again; TK measures it.
- **More rounds cost points on one probe** (16 rounds 1.2-1.9 below fewer, below). FINISHED sec. 5 item 13 now carries it as an open risk for the 100M run; the learned stop is meant to avoid paying it, and the B3 readout reports rounds used.

## Short answer

- Letters lose no information: every word and digit of the question is there. What can be thin is how much each position **knows** before the thinker starts, because B2's reader is shallow (2 conv layers, a 9-letter view, no attention) and has learned word meanings from only about 5.4M word pieces of practice (the 200k skills rows, each seen about 30 times).
- Our own tests say this costs about 2 points, not more: adding Google's pretrained word meanings on top of the letters (EGE) gained +1.6 / +2.1, mostly on new wording (frame +3.6, vocab +2.7) and on word-relation families (order_chain +22, list_index +15, table_calc +15, kin_chain +13). It also lost on some letter-pattern families, and it failed its 2-seed screen (below).
- The 9-letter window matters more than the unit: every reader without it lost the cipher tasks, with or without letters (R0, letters only: cipher 4; the four Gemma readers without the window: 0-10), and removing the window alone cost 6.3-6.8 points. None of our runs tried word pieces with the window, so letters vs word pieces is still untested here; U0 below tests it directly.
- B2's big losses are elsewhere: the variant split (B2 misses 66% of it: new layouts and new kinds of computation) and the families with no worked steps in the data (accuracy: fewshot_number_rule 24%, table_lookup 27%). Better reading moved them only a little (EGE: table_lookup +7.0, fewshot_number_rule -3.1).
- So: keep letters (as raw bytes) as the base, because word pieces hide spelling (papers below; Gemma's own vectors keep only 23% of letters readable), and keep the window. Make each position richer on top: (1) attention across the whole question inside the reader (W1), (2) learned groups of letters that act like words, with no hand-written word splitter (U2), (3) pretrained meaning as a side channel (EGE), if the 6-seed check running tonight overturns its failed screen. **10-09:** superseded; Gemma is now the main reader with the window on top, W1 was not shown and U2 did not run (update above).

## What we have measured (shown)

| Arm (2-seed mean) | What the reader gets | pooled-5 | frame | vocab | cipher_map (pooled) | chain-5 |
|---|---|---|---|---|---|---|
| B2 (5090 pair) | letters + 9-letter window | 73.9 | 87.4 | 88.0 | 96.7 | 99.6 |
| EGE | letters + window + Gemma word pieces | 75.8 | 91.0 | 90.7 | 96.3 | 100.0 |
| R0 | letters, no window | 67.4 | 74.1 | 82.1 | 4.2 | 99.3 |
| EGR / EGO / EGM / EGW | Gemma word pieces (EGR also letters), no window | EGR 72.5, EGO 72.7, EGM 72.7, EGW 69.6 | | | 0-10 (in_dist) | |
| EGT | letters + window; Gemma only as a training-time teacher | 74.0 | 87.2 | 87.8 | | 99.5 |
| plain_tf_steps | letters, causal transformer over the whole question, writing steps | 67.0 | 80.7 | 77.3 | 64 (6-seed range 38-93) | 94.2 |

Other facts that bear on it (shown):
- Gemma's own vectors keep only 23% of letters under a linear read (`WHY-GEMMA-LOST-2026-10-06.md`). The letters are lost at its input, where words are cut into pieces.
- EGE's losses, pooled over the five splits: seq_cycle -12.2, seq_next -6.2, list_stats -5.3, passage_qa -4.8, chain_story2 -4.5; on the answer split rule_apply -26.2, seq_cycle -22.5, fewshot_number_rule -15.0. In-family cells are 40 rows per seed, so single cells are noisy.
- EGE failed its 2-seed screen (`PASS-MARKS.md` addendum 4 marks, judged in addendum 15): variant +1.70 against a +3.0 mark, and a loops:0 in_dist leak of 18.1 on seed 200 against a limit of 5. EGK, the leak fix, was unstable (NaN twice on s201). A 6-seed confirm on fresh seeds 202-207 (addendum 15, EGE and plain B2 per seed on one machine) is running on the PC as q39.
- The thinker already attends to every letter in every round (`ledger.py:117-121, 295, 304`). Its heads read only control vector 0 (each step's op and operands) and control vector 1 (mode and answer pointers) (`ledger.py:312, 333-336`); controls 2-7 are read by no head and already act as 6 scratch vectors through attention. So more thinking room (W2) is a separate question from the input unit.
- Hand place codes do nothing for plain transformers (+0.8 / -0.8, `RESULTS-SCREEN.md:57`), so dropping them is probably cheap for full-attention models; untested for B2's +-4 reader (hence P1's W1 fix in the plan).
- More thinking rounds do not help: in_dist saturates at 8 rounds, and 16 rounds cost 1.2-1.9 points (`40-loops-probe`, one seed; RESULTS-EG2 LR section, q33 seeds). **10-09:** an open risk for the 100M run, carried in FINISHED sec. 5 item 13.
- Bigger direct-answer transformer (plain_tf 10.8M vs 3.2M, one seed, `02-calib-long`): in_dist +2.4, frame +3.0, vocab +5.5, variant +2.2, answer -1.2.
- Word pieces cut numbers at irregular places: for 1000-9999 with a leading space, GPT-2 splits them 2+2 52%, 1+3 38%, 3+1 6% (the rest stay whole or split 1+2+1); "4821 + 937" becomes `48|21| +| 9|37`. cl100k groups digits left-to-right in threes by its pre-split rule, so the units digit of 4821 sits alone (helper measurement with the tokenizers; cl100k from its regex, not re-run).
- Our prompts are short: train p50 78 chars, p95 142, max 204 (`research/data.md:46`). With about 4 chars per word piece that would be about 20-35 positions instead of 78-142, so sequence length is not the bottleneck (suggested). **10-09:** true only for these short questions; inputs can now be 2,000 letters (Ben 10-09), where length does cost (update at the top).

## The options

| Option | Per position | Exact letters and digits? | Hand rules? | Our evidence (shown) | Papers (abstracts opened) | Verdict (suggested) |
|---|---|---|---|---|---|---|
| **Letters / bytes** (today) | 1 letter, plus a 9-letter view from the window | yes, by construction | only the hand vocab (bytes remove it) and the place code | B2 73.9; window worth 6.3-6.8; cipher 97 | Byte-level attention is what drives character skills; hierarchies that shrink bytes lose them (Edman 2026, 2609.00463). Subword models must spend depth to get letters back (Hiraoka 2025, 2506.10641) and still fail to manipulate them (CUTE 2409.15452) | **Keep as the base stream**, as raw bytes |
| **Word pieces** (BPE) | about 4 letters | no: spelling hidden, numbers cut at odd places | the tokenizer is a frozen hand-written algorithm, not end-to-end | GPT-2 splits 4821 as 48\|21; never tried with the window | Subwords win mainly by more text per unit of compute and by giving word boundaries, not by richer positions (Gigant 2026, 2604.27263). Left-to-right digit grouping hurts arithmetic (Singh 2024, 2402.14903) | **Don't swap.** U0 tests it once, as the direct answer. **10-09:** U0 lost 3.1 and 5.4 points |
| **Learned byte patches / chunks** (BLT, H-Net, MrT5, AU-Net) | a learned group of letters | only if the letters are kept beside the groups | none: boundaries are learned | none yet | H-Net's learned chunks beat a BPE transformer at matched compute and are strongest where tokenizers are weak, nearly 4x data efficiency on DNA (2507.07955). AU-Net says it can handle character-level tasks (2506.14761). MrT5 shortens after full-resolution layers (2410.20771). BLT matches token models up to 8B (2412.09871) | **Add as a side channel (U2)**, never instead of letters. Built for long text; our questions are 78-142 letters, so the win can only be meaning, not speed. **10-09:** at 2,000 letters speed matters too; U2 never ran, and TK now asks the tokens question |
| **Pretrained embeddings** (EmbeddingGemma) | one meaning vector per word piece | no (23% of letters linearly readable) | none at run time; 271M borrowed weights | on top of letters: +1.6 / +2.1, but failed its screen (variant, leak); instead of the window: all four versions lost the ciphers | Byte-ifying pretrained subword models keeps their knowledge and fixes character tasks (Bolmo 2025, 2512.15586) | ~~Side channel only (EGE); the 6-seed check q39 decides~~ **10-09: the main reader** (Ben 10-08), with the letter window on top. q39 is done: +2.67 over B2 on 6 of 6 seeds (zero-round leak 6.6 against a 4.6 limit, now reported, not gated) |
| **Deeper reader on letters** (W1: attention across the whole question) | a letter that knows its whole sentence | yes | none | the window's +6.3-6.8 says local context matters; plain_tf_steps (attention, no window) reads ciphers at 64; no global test inside B2 yet | Local convolution alone is weak at recall; adding attention closes most of the gap (Zoology 2312.04927, in `thinker-absorb-papers.md`). Copying needs attention, proven for 2-layer transformers (Jelassi 2024, 2402.01032) | **First test (W1)**. **10-09:** ran, not shown (+0.88, +0.07 against +1.0); not in B3 |

## Tests (marks fixed now, before any run)

All against today's plain B2 on the same seeds and machine unless stated; recipe as B2 (24k updates, batch 256, lr 1e-3, bf16, same rows and order). **Size:** within +-3% of 3,244,544 trainable (the sealed band, 3,147,208 to 3,341,880; B2 is 3,302,481, about 39k below the top). Each test prints its count and says what it shrinks to fit, disclosed. Counting borrowed weights applies to the Gemma arms only (Ben's ruling).

**W1, global attention after the window** (architecture thread's spec, `redesign-ideas-2026-10-07.md` sec. 5; its marks stand and are repeated here so they sit in one place): pooled-5 >= B2 + 1 on both seeds, cipher_map in_dist >= 95, no dev split down more than 2, loops:0 leak no more than 1 above B2. Proved wrong: a cipher or lookup family drops by more than 2, or pooled-5 mean below 0. **Open, for the architecture thread to settle before W1 runs:** its spec of 2-3 global attention blocks is about 0.8M params per block at width 256, far past the size band, so as written it is two changes (add attention, shrink something). A low-rank global attention with inner width 32 (about 33k params) fits; otherwise it needs Ben's size exemption. Its "family drops by more than 2" is less than one row on a 40-row cell, and "no dev split down more than 2" does not say per seed or 2-seed mean; both need stating before the run.

**U0, letters vs word pieces in the all-learned text baseline** (report-first, 2 runs). This tests Ben's question on plain_tf_steps, which attends over the whole question; B2's own reader cannot take word pieces (its number and place parts work on letters), so B2's reading question is W1 and U2.
- One change: the **prompt** becomes byte-level BPE (the 95 ASCII characters as base symbols, merges learned on train prompts only), 416 ids in all, so the tied table stays inside the size band at the same width 256, 4 layers, 4 heads. Steps and answer stay letters. Shorter prompts mean less compute per row: disclosed.
- Seeds 200, 201 on the PC, against q33's plain_tf_steps on the same seeds.
- "Ben right": pooled-5 (BPE - letters) >= +2.0 on both seeds. "Letters fine": <= +1.0 on both seeds. Anything else: tie.
- Letters fine or tie: letters stay, reported as "no evidence word pieces help at this size". Ben right: add a from-scratch word-piece side channel next to the letters in B2 (like EGE, no pretraining) as the next gain test.
- Pre-registered prediction (from the papers, suggested): letters fine; cipher_map falls by 10 or more for word pieces; arithmetic families fall; frame and vocab move less than 2.
- Proved wrong for the prediction: cipher_map pooled over its 3 splits (2-seed mean, read against plain_tf_steps' 6-seed range on q33: 45-112 of 120) is at or above letters - 5 for word pieces.

**U2, learned letter groups** (after W1; one change on top of W1 if W1 passed, else on B2): a boundary scorer on the reader output decides where groups end (H-Net-style dynamic chunking with its ratio loss, target about 4 letters per group); each group's letters are pooled into one vector; the thinker attends to the groups and the letters. No hand-written word splitter. States what it shrinks to stay in the size band. Pass: pooled-5 >= +1.0 on both seeds, frame and vocab both up, cipher_map in_dist >= 95, no split down more than 2 on the 2-seed mean, loops:0 no more than 1 above the base. Proved wrong: pooled-5 mean below 0 or cipher_map below 90. Also reported: how often the learned boundaries match word ends (a check that it found words, not a mark).

**EGE** (running as q39, marks sealed in `PASS-MARKS.md` addendum 15): unchanged.

**V1, bytes**: see the plan, section 3b. For our ASCII data it is the same symbols.

## What I would not test

- Gemma in place of the window: done four times, and all lost the ciphers (shown).
- Byte-patch models with a separate global model (MegaByte, BLT) at full size: they are built to shorten very long sequences; ours are 78-142 letters (suggested). U2 takes the useful part, learned groups, without the rest.
