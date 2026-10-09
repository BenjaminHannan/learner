# Test TK: the thinker reads tokens instead of letters (spec and marks; revised 10:15 AM ET Fri Oct 9 after 3 reviews, before any build or run)

Asked by Ben, 9:30 AM ET 10-09, thread "Architecture ambiguities": "it should be able to read a lot more. And experiment with doing tokens
instead of just letters." 9:44 AM ET: "I don't understand why doing a letter plus 4 letters on each side is so important to you? I feel like
you should use tokens and you get most of that meaning anyway right?"
Labels: **shown** = read in code, data or result files; **suggested** = reasoned; **untested** = never run.
Revision note: first draft 9:50 AM ET; three read-only reviewers (code fit, marks and noise, Ben's intent) found a memory check that could
not run, an untested "reads more" claim, a weak leak guard and loose wording; all fixed below. No run or build had started.

## 1. Why, in plain words (for Ben)

Today the thinker looks at every letter, one spot per letter, every round. Gemma already cuts text into tokens (word pieces). If the thinker
looks at one spot per token instead, its part of the reading gets about 3-4 times cheaper (**shown**, measured with Gemma's own tokenizer
on 10-09: 3.1 letters per token on our skill questions, 4.3 on web text; table in sec. 2). The rest of the model (Gemma, the small letter
window, the talker's copying) still runs on every letter, so the whole model gets cheaper by less than that.
The risk is spelling: the thinker would no longer see single letters. So each token's spot is built from its letters (after the letter
window), and the talker still copies exact letters and digits.
**What this test can and cannot show:** it shows whether tokens cost any accuracy on today's questions (up to 280 letters) and how much
cheaper the thinker's reading gets at 2,000 letters. It does NOT show the model reading long texts well: that needs long training rows,
which is the big-run thread's part of your 2,000-letter answer (sec. 7).

## 2. What we already know (shown)

- U0 (10-07, `custom_io/results/RESULTS-GAIN.md`, branch claude/custom-reader-talker-4x309r): word pieces INSTEAD of letters in the small
  text model lost 3.1 and 5.4 points pooled-5 (frame -10.8, vocab -6.6). Letters were removed there; here they are kept.
- EGE (Gemma tokens added to letters, with the window) is the nearest run: 6-seed confirm pooled-5 75.9-77.2 vs plain B2 73.0-74.7
  (q39/q33 RESULT.json files), but its 2-seed screen failed on the variant split and on a leak (loops:0 in_dist 18.09 on s200, PASS-MARKS
  add. 4/15). G1's G-B2 is EGE.
- Gemma readers without the letter window lost the cipher puzzles: in_dist EGE 97.5/95.0 vs EGR (Gemma + letters, no window) 5.0/2.5 and
  R0 (letters, no window) 12.5/2.5 (RESULTS-EG2.md).
- No run has tried tokens for the thinker with the letters kept (INPUT-UNITS-2026-10-07.md).
- EmbeddingGemma 2 reads up to 8,192 tokens (model card at revision 914f7f89, "Context Window 8,192 tokens";
  https://huggingface.co/google/embeddinggemma-2). Gemma is not the limit on reading length.
- Letters per Gemma token (my count 10-09, Gemma 2's tokenizer.json at 914f7f89, counted the way eg.py aligns them, prefix excluded):

| Text | Rows | Letters per token | Rows under 2.5 | Digits |
|---|---|---|---|---|
| Skill questions (own72 skills.jsonl, first 20,000) | 20,000 | 3.08 | 24.4% | 5.0% |
| Web text in 279-letter chunks (rung10 slice) | 9,068 | 4.27 | 1.0% | 1.2% |
| Web text in 2,000-letter chunks | 3,000 | 4.36 | 0.4% | 1.1% |
| Web text in 8,000-letter chunks | 600 | 4.35 | 0.2% | 1.2% |

  So 8,192 tokens is about 35,000 letters of web English.
- Seed noise (pooled-5 over 6,040 rows, my recount from RESULT.json): plain B2, 8 seeds 73.00-74.74, sd 0.55; EGE, 6 seeds 75.88-77.19,
  sd 0.51. G1's web-heavy mix has only one finished seed, so its noise is unmeasured.

## 3. The change (arm TK)

Base = gate G1's G-B2 arm exactly: code `claude/project-thread-f1to6a` at 612f5c5b0 plus the caps.py overlay from branch
`claude/nice-lamport-al1gwo` at e9125e9013 (sha256 prefix 3da2dfbb); ledger with `eg_embed`, 3M rung, 12 rounds, caps_g.json, the same
data pool, order and accum. Calculator INSIDE (as in G1). New switch `tok_think` (default off; off must be bit-identical, sec. 8):
- The reader runs as today: letters + place code + Gemma's state for each letter's token, then the two-layer letter window (+-4 letters).
- NEW: for the thinker only, each Gemma token's letters (from eg.py align(): char -> token, compacted per row) are pooled into one spot by
  a learned attention pool: score = w . x + b per letter, softmax within the token, weighted sum. w and b start at zero, so training starts
  from a plain average. 257 new weights (trained count 3,545,170; the 3% band holds). Learned rather than fixed, per Ben's rule that
  everything inside the model is learned. The thinker's cross-attention keys and values come from these token spots, with a token mask.
- Unchanged and still letter-level: `read()`, `X` and `xm` as returned, the talker's copy pointer and word keys, the number slots (from the
  regex, a hand part with its own fix, N1), the round readout. Rounds, calculator, heads and losses unchanged.
- Gemma's tokenizer is part of the borrowed reader Ben picked (FINISHED-MODEL sec. 4); the grouping and pool are about 20 new lines of
  model code, no hand rules.
- Size, Ben's rule (borrowed counted): about 274.5M whole (271.0M Gemma + 3.55M trained).

## 3b. Arm TKN: tokens with no letter window (on Ben's 9:44 AM ET question)

TKN = TK with the two letter-window layers removed (`reader_layers` 0): each token's spot is pooled from its letters' plain inputs (letter +
position + place + Gemma). The ~0.66M freed weights go to the thinker's feed-forward width (`mlp` raised until the trained count is within
0.5% of TK's, the trimming rule configs.py uses for other rungs; disclosed). One change against TK: the window.
**Prediction, written now (suggested):** "window needed". Every earlier reader without the window lost the cipher puzzles (sec. 2).

## 4. Runs

- TK and TKN, seeds 400 and 401, BensPC, B2 arm only (`--arms B2 --b2-extra '{"eg_embed": true, "tok_think": true}'`, TKN adds
  `"reader_layers": 0` and its `mlp`), same accum as G1's B2 run of that seed. Control = G1's own G-B2 3M run of the same seed (s400 done:
  73.01 pooled-5; s401 running).
- When: after G1's last job. Order relative to G2 (finished-design size test) and H1R is the big-run thread's call; my default is TK
  before G2, so that if tokens pass, G2 tests the token version once instead of twice.
- PC time (not free; the PC is the project's bottleneck): about 6.5 h per run at G1's 3M pace (s400: 23,422 s), so about 26 h for 4 runs.
- Judge: pooled-5 over 6,040 rows, chain-5 and loops:0 as for G1 (`custom_io/analyze_8a.py` numbers).
- **Cost check at 2,000 letters (report-only, standalone script, CPU-built, run on the PC in minutes):** both arms rebuilt with max_prompt
  2,000 (position table and word/number caps re-sized the same way in both; these memory-only builds are not the trained models and skip
  the size band); 2,000-letter rows made by joining web chunks, with fresh ids. One training step, batch 8, per arm: thinker key positions
  per row (letters vs tokens, valid only, workspace excluded), total peak GPU memory, activation peak (peak reset after Gemma loads), and
  step time. Expected (suggested): thinker keys about 0.23x; total peak somewhere around 0.6-0.9x, because the reader, Gemma and
  talker stay per letter.

## 5. Marks (fixed now)

Pass needs all of these. Hair rule (MARKS-D0-T1 Amendment 10 item 1, Ben 10-08): a single-seed mark missed by no more than 0.5 point (or
one case in 800 for counts), with every other mark passing on both seeds and the miss disclosed, counts as a pass on a screen. M1-M3 are
2-seed means and get no tolerance.
- **M1 (no loss):** pooled-5 TK minus G-B2, mean of the 2 seeds, >= -1.0. (At sd 0.55, a true zero fails this about 3-4% of the time.)
- **M2 (no hidden split loss):** frame and vocab each, TK minus G-B2, 2-seed mean, >= -3.0 (the splits word pieces hurt in U0).
- **M3 (spelling kept):** cipher_map pooled over in_dist, answer and frame (120 rows per seed, 240 over 2 seeds), TK >= G-B2 - 10 points.
  Judged only if G-B2's own seeds 400 and 401 differ by no more than 10 points on it; otherwise reported, not judged. (G-B2 s400: 79 of 120.)
- **M4 (chains):** chain-5 >= 99 on each seed.
- **M5 (thinker drives, MARKS-D0-T1 line 170 rule):** on each seed, (TK in_dist minus TK loops:0 in_dist) >= 80% of (G-B2 in_dist minus
  G-B2 loops:0 in_dist). loops:0 in_dist is also printed against the old absolute line of 5 (report-only, Ben 10-08: reader help allowed).
**Proved wrong:** pooled-5 2-seed mean <= -2.0, or (when M3 is judged) cipher_map more than 20 points below G-B2.
Report only: every split and family; letter families (cipher_map, letter_ops, copy_word, word_filter, seq_next); steps/s; the sec. 4 cost check.

**TKN vs TK (the window question):** "window can go" if pooled-5 TKN minus TK (2-seed mean) >= -1.0, frame and vocab each >= -3.0,
cipher_map (240 rows) TKN >= TK - 10, and M4, M5 hold for TKN. "Window needed" (proved) if pooled-5 <= -2.0 or cipher_map more than 20
below TK. Anything else: not shown, window stays (Ben's 9:29 AM ET card answer). If TK is proved wrong, TKN is read against G-B2 with M1-M5.

## 6. What each result means (fixed now)

- **TK pass:** tokens become the candidate reading for run-1, not yet adopted. Before run-1 uses them: (a) the first build that joins
  Gemma with the outside calculator (never built, PLAN sec. 2) must carry the token pool; calculator replies stay letter-level spots (they
  are at most 40 letters and Gemma does not read them); (b) the finished-design size test G2 runs on the token version; (c) Ben's go.
- **TK not shown:** letters stay for the thinker; run-1 reads up to 2,000 letters as Ben chose; tokens stay a candidate for the
  long-input stage.
- **TK proved wrong:** letters stay; record that pooling letters into tokens loses what the thinker needs.
- **TKN "window can go":** the big run drops the window only with Ben's go (he chose "Keep" at 9:29 AM). Otherwise the window stays.
- None of these results shows long reading. Reading 2,000 letters or more well is untested until training includes long rows (sec. 7).

## 7. Found while writing this (shown, code), sent to the big-run thread 9:55 AM ET

Reading 2,000 letters (Ben's Q2 answer) needs more than a bigger data cap, with or without tokens:
- The letter reader has a LEARNED position table sized to the input cap (`reader.py:58`, nn.Embedding(MAX_PROMPT, d); caps.py:125-127 sets
  it to 280; data.py:107 asserts prompts fit). At 2,000 letters that is 2,000 x width weights (0.5M at width 256, 1M at 512) and spots past
  the longest training row never train; at 35,000 letters it would be 9M at width 256. Long reading wants relative positions or a learned
  scheme that does not grow with length (big-run thread's call).
- Word slots (w_max 208) and number slots (n_num 91) are caps sized for 280 letters.
- Cloze rows are cut at 279 letters (cloze.py:21); long training rows need a new row type whose answer depends on text far away.

## 8. Build (code worker) and checks before any PC run

Branch claude/project-thread-qtxfp4 from 612f5c5b0 + the overlay. Requirements:
- New token spots and token mask are separate variables used only for the thinker's cross-attention K/V and its mask (ledger.py run(),
  the kvx line and `mask = torch.cat([valid, xm], 1)`); `read()`, `out['X']`, `out['xm']`, gen_copy, word_content, number pool, talk
  untouched.
- Pooling by index (scatter/index_add over compact token ids), no dense [B, tokens, letters] matrix. align() called after Gemma loads.
  Assert `tok_think` is not combined with `eg_thinker`.
- **Bit-identity check (CPU):** base commit vs new commit with `tok_think` off, fixed seed, the same rows, a few hundred steps of a tiny
  config with a stub Gemma: losses and every parameter `torch.equal`.
- Tests: pooling against a hand-worked prompt; masks; padding rows; prompts whose first token merges with the prefix; TKN size within 0.5%.
- The sec. 4 cost script.
- PC staging (job card, code tree) goes through Ben's Mac session after G1, with his go there.
