# bm-397t PLAN: teach the plain 1B to answer short, from code-made practice (benchmarks thread, 2026-09-26 ~03:05 UTC)

Registered before any training run and before any output of this model exists. This is bm-397's registered next step:
its plan, sealed before its run, said a result of TF − T ≤ +1.0 sends the next dollar to evidence-conditioned
training, not to more prompt-shortening. bm-397 gave +0.28 and failed its blind audit (RESULTS-run.md there). Every
LoCoMo number is "after using LoCoMo for development". LongMemEval stays untouched.

## Why
- The plain MiniCPM5-1B, reading the whole chat (arm T), scores 27.50 F1 on LoCoMo categories 1-4.
- Its token recall is close to Qwen3.5-2B's (43.6 vs 48.6), but its precision is far lower (23.7 vs 54.5). Its
  median scored answer is 10 words.
- Asking it to shorten its own answers (bm-397) did not work: it handed the draft back unchanged 1,019 of 1,533
  times.
- Question: does a little practice at answering in few words, on made-up chats, carry over to the real test?

## The one change
A LoRA on the plain MiniCPM5-1B (revision 87179e5c), trained by scripts/claude_bm397t_train.py:
- rank 16, alpha 32, dropout 0.05, on q/k/v/o; AdamW lr 2e-4, 8 examples a step, 1 epoch, seed 3970, bf16 on GPU;
  thinking off.
- Loss on the answer tokens and the end-of-turn token only. Merged into a copy of the weights afterwards.

The data is code-made (scripts/claude_bm397t_data.py): 180 conversations and 1,800 questions, seed 3970, sha256
0654bd2f60ac002d1465cc55a45cd462bd8b68be8d9c7606c2894b7856f06237.
- Fictional names and invented places. Seven-to-ten dated sessions of small talk, with facts said by each speaker.
- Questions and answers come from code: where someone moved, a new job, a pet's name, what was bought, who someone
  went out with, a favourite dish, where a relative lives; "when" questions (today, yesterday, last week); and
  two-item lists said in two sessions.
- The answer is the code-made label. No benchmark item, no model output, no teacher and no Claude-written answer
  is trained on. The chat text itself carries no loss.
- The chat rendering and the six brevity instructions differ from the LoCoMo harness's, so the test measures
  transfer.
- Dev (report only): 20 more conversations, 200 questions, seed 3971, sha256
  675a2d854153700c80eee701a290cb4b2c39c58a4dd2065640b56caa67942da9.

The trained model (TS) is scored ONCE with the sealed bm-390 harness and scorer, as `plain:<merged folder>`, exactly
as T was: LoCoMo whole chat, MMLU-Redux-300 and GSM8K-300, greedy, bf16, on the same kind of GPU (RTX 5090). The
baselines are T's registered run2 files (baselines.sha256.txt in bm-391), which are not re-run.

## Marks (fixed now; TS vs T)
- A1 (gain): LoCoMo cat 1-4 F1, TS − T ≥ +5.0 (TS ≥ 32.50), with the conversation-level 95% interval
  (scripts/claude_bm396_audit.py cluster_boot, seed 396, 10k) above 0.
- A2 (no harm): TS ≥ T − 3 points on MMLU-Redux-300 (≥ 41/300) and on GSM8K-300 (≥ 182/300), with the sealed pickers
  (bm-390's M4).
- A3 (still right, blind): 300 cat 1-4 questions drawn with random.Random(3972) (scripts/claude_bm397t_judge.py).
  Blind Opus judges label each reply A-E as in bm-397, and no judge sees both replies to one question.
  TS's A-count ≥ T's A-count − 3. Two extra judges relabel 60 items; the agreement is reported.
- A4 (not a refuser): the scorer's cat 1-4 abstentions for TS ≤ T's + 20 (T = 7, so ≤ 27).
- PASS = A1 and A2 and A3 and A4. Anything else is a registered FAIL.

A pass is reported as "the 1B learned to answer about chats in fewer words, and it carried over to LoCoMo". It is not
reported as better memory. It is scored on the plain 1B, not inside 0.2c.

## Proved wrong
TS − T < +2.0: short-answer practice on made-up chats does not carry over, and the length gap needs practice on
natural chats or a different method.

## Report only
- Per-category F1, confident wrong, and category 5.
- Token precision and recall, and median words (scripts/claude_bm391_prf.py).
- bm-396's bound columns.
- GSM8K under the strict pick.
- Dev sanity before, after the LoRA, and after merging; training loss first and last 10 steps; wall times.
- Resources: one 1B model resident (same as T); context = the whole chat; greedy; ms per question from the run files.

## Predictions
- P1 (45%): A1 passes. Point guess TS − T = +6.
- P2 (60%): A2 passes. The risk is GSM8K, if the model also drops its working.
- P3 (60%): A3 passes.
- P4 (85%): A4 passes.
- P5 (75%): dev right answers after training ≥ before, and median dev words after training ≤ before (the base
  already answers the code-made dev questions in about 5 words, so this is only a sanity check).
- P6 (35%): all four pass.

## Where it runs
One RTX 5090 rental (handoff/held/rent-bm397t.md), about 1.5 h, cap $1.40, released only by the Director. Train
once; each scoring command is launched once. A crash with no output may be relaunched once, unchanged, and that is
disclosed. Scoring, the bootstrap, the blind audit and the recount happen afterwards on CPU.

Before sealing, a CPU smoke of the train script (6 training rows cut to 1,200 characters of chat, 1 step, 2 dev
rows, nothing saved) ran every stage without error: dev before, LoRA training, dev after the LoRA, merge (96 layers)
and dev after merging. Nothing from the smoke is used.
