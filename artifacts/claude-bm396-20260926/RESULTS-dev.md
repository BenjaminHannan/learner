# bm-396 (dev, report only): is the plain 1B's LoCoMo loss answer length or content? (benchmarks thread, 2026-09-26)

Asked for by GPT-6 Pro's reply to reviews/gpt6pro-benchmark-gap-2026-09-26.md. Runs on replies that already exist
(bm-390 run/ and run2/, bm-395 run/); nothing generated, trained or tuned; the gold is used only to measure.
After using LoCoMo for development. Script: scripts/claude_bm396_audit.py. Categories 1-4, 1,540 questions.

| Arm | F1 | best-span bound* | keep-matches bound | all gold words present | zero overlap | a later line scores higher |
|---|---|---|---|---|---|---|
| Qwen3.5-2B, whole chat | 47.87 | 54.15 | 54.77 | 469 | 405 | 3 |
| plain 1B, whole chat (T) | 27.50 | 48.30 | 49.87 | 402 | 475 | 16 |
| plain 1B + store top 20 | 29.85 | 44.90 | 45.66 | 360 | 538 | 2 |
| plain 1B + store top 10 | 26.84 | 40.08 | 40.78 | 293 | 613 | 5 |
| plain 1B + BM25 top 10 (Rb) | 25.06 | 37.82 | 38.16 | 278 | 663 | 1 |
| LFM2.5-1.2B, whole chat | 19.01 | 33.95 | 34.86 | 202 | 667 | 0 |
| Premonition 0.1 | 2.98 | 6.73 | 6.92 | 18 | 1,302 | 9 |

*Mean F1 if each reply were cut to its single best run of consecutive words. It is an optimistic, gold-guided bound:
a real shortener cannot see the gold. Multi-hop uses whole-answer token F1 here, so both bounds are approximate
there.

What it shows:
- The plain 1B's replies already hold most of what Qwen's hold. The gold words are all present in 402 of its replies
  against Qwen's 469, and it has zero overlap on 475 against 405. Perfect cutting would take the 1B from 27.50 to at
  most 48.30. Qwen is already close to its own bound (47.87 of 54.15).
- So most of the 20-point lead is how the answer is written, as an upper bound. How much a faithful shortener can
  recover is untested; the semantic audit and a registered shortener test decide that.
- The scored-first-line rule costs almost nothing (16 of T's replies score higher on a later line).

Store vs BM25 on the same questions (the check GPT asked for). On the 730 questions where both found an evidence
line, the store's top 10 scored 37.35 and BM25's 38.08. On the 276 only the store found, the store scored 31.58 and
BM25 12.97. The lower "F1 when found" in bm-395 comes mostly from the store finding harder questions, not from
near-miss lines confusing the model.

Conversation-level bootstrap (resampling the 10 chats, seed 396, 10k) versus bm-390's question-level one:
- E − Rb2: +1.66, interval [+0.04, +3.31] (question-level was [+0.31, +3.03]). The bm-395 verdict is unchanged.
- Q2 − T: +20.37 [18.54, 22.30].
- P − T: −24.52 [−25.77, −23.22].
- Per-chat differences are in the script output.
