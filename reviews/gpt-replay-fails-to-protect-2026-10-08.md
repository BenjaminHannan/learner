# Why doesn't half-batch replay protect a few skills during "sleep"? (no code or file access needed)

You are an expert in continual learning, catastrophic forgetting, rehearsal/replay methods and small sequence models. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer. Mark every claim as **shown by the data below**, **suggested**, or **untested**. Two parents (training seeds) is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. The model

- A small (3.3M parameters) character-level "ledger" model. A reader encodes the prompt. A looping thinker then writes a short program: up to 7 steps, each step = an operation plus two pointers to earlier numbers or results, plus an answer pointer. An exact executor runs the program, so the model never does arithmetic itself; it only picks operations and pointers.
- It was pre-trained (call this checkpoint **B2**) on 200k "skills" rows from 34 families of short text tasks, 200 DEV rows per family. Examples: arithmetic word problems, multi-step chains, table lookups, sequence continuation, rule application, ciphers, parity, passage questions, ordering.

## 2. The new task and the "sleep"

- **C2** is a few-shot number-rule task: a prompt shows 3 example pairs x → f(x) for a hidden rule (x², 2(x+k), x mod 10, a·x+b, ...) and asks for f(query). The model must write a program that fits all the examples. A python check ("does this program reproduce every example?") is the only feedback; the answer key is never used in training.
- **Day:** the model tries each of 1,024 pool questions. On the ones where its first (greedy) try fails the example check, it samples up to 512 tries and keeps up to 2 distinct tries per question that fit all examples. That gives about 800 "records" on night 1 and about 250 on night 2.
- **Night:** a fine-tune on those records. Batch 64: half the batch is records, half is **replay**, drawn uniformly from the 200k skills training rows (all 34 families) plus some practised add/mult rows. Learning rate 1e-3, Adam, and each record is seen about 32 times (updates = 32 × records / 32). Records and replay use the same loss: cross-entropy on the program steps and answer pointer.
- Before night 1 the parent is **N'**, which is B2 after a short warm-up and one "stepping-stone" night of the same kind.

## 3. Results (shown): exact % on skills DEV (200 rows per family) after each step, two parents

| exact % | seq_next | rule_apply | cipher_map | digits_parity | passage_qa | order_chain | story_chain3 | all 34 families | 5 chain families |
|---|---|---|---|---|---|---|---|---|---|
| parent A, B2 | 81.0 | 89.5 | 97.0 | 94.0 | 95.0 | 66.0 | 100.0 | 89.4 | 99.7 |
| parent A, N' | 62.0 | 77.5 | 90.0 | 87.0 | 90.0 | 63.5 | 99.0 | 86.7 | 98.1 |
| parent A, night 1 | 43.0 | 50.0 | 71.5 | 83.0 | 84.0 | 56.0 | 99.5 | 82.9 | 97.4 |
| parent A, night 2 (two variants) | 30.5 / 32.5 | 47.5 / 48.0 | 61.5 / 63.5 | 80.0 / 78.5 | 82.5 / 81.5 | 51.5 / 53.5 | 99.0 / 99.0 | 81.7 / 81.7 | 97.2 / 97.3 |
| parent B, B2 | 88.5 | 92.5 | 99.5 | 95.5 | 95.5 | 60.0 | 99.5 | 90.5 | 99.8 |
| parent B, N' | 66.5 | 85.0 | 89.0 | 85.5 | 90.5 | 59.5 | 99.0 | 87.8 | 98.9 |
| parent B, night 1 | 42.5 | 64.0 | 72.5 | 79.0 | 79.0 | 53.5 | 99.5 | 84.2 | 98.0 |
| parent B, night 2 (two variants) | 30.0 / 34.5 | 54.5 / 56.0 | 58.5 / 56.5 | 79.0 / 73.0 | 78.0 / 74.5 | 51.5 / 49.0 | 91.0 / 87.5 | 81.7 / 81.8 | 94.9 / 94.2 |

The two night-2 variants differ only in what the night trains on: one uses the night-1 model's "shaky" successes (questions it got right but only sometimes), the other a random draw of its night-1 records. Both have the same number of updates.

Other facts (shown):
- Other families also drop between B2 and night 2, but less:
  - by 5-15 points: seq_cycle, list_stats, verify_claim, state_update, odd_one_out, word_filter, kin_chain, table_calc and arith_bare, which ones depending on the parent;
  - by less than 5 points: the rest.
- fewshot_number_rule, the skills family most like C2 (examples of a number rule, then a query), goes UP: +2.5 and +6.5 points from B2.
- Our harm guard only watched the 5 chain families. It moved 2.5 points on parent A while seq_next lost 50, so it missed this.
- seq_next = "continue this sequence"; rule_apply = "apply this stated or shown rule to a new input"; cipher_map = "map letters/digits through a shown substitution". These are the families whose prompts look most like C2's: shown examples, then a query.
- On C2 itself, night 1 lowers the stuck rate (first try fails the check) from about 99% to 65-68%. Night 2 lowers it about 2.5 more points.

## 3b. New result (shown, 8:42 AM ET 10-08): a repair pass made it worse

We tested option (a) from question 2 below: after each night, the model checks itself on a held slice of its own skills **training** rows (100 per family) against the same check before the night. Families that drop more than 5 points (paired 95% interval below 0) get 64 **replay-only** updates (whole batch = 1,024 of that family's other training rows, each seen about 4 times; fresh AdamW, lr 1e-3, warmup 10, cosine to 1e-4). Then it re-checks, for up to 4 rounds. A report-only arm spreads the same 256 updates evenly over all 34 families (1,024 rows, each seen about 16 times).

| exact % | parent A | parent B |
|---|---|---|
| skills DEV, all 34 families: N' / night 1 / night 1 + repair / night 1 + even spread | 86.7 / 82.9 / **77.3** / 79.1 | 87.8 / 84.2 / **79.9** / 80.1 |
| held training-row check during the 4 repair rounds (before the night: 92.2 / 92.5) | 87.7, 84.2, 81.7, 83.5, 80.8 | 87.4, 79.8, 83.9, 79.9, 82.2 |
| C2 first try right: night 1 / + repair / + even spread | 31.2 / **0.0** / 2.0 | 34.4 / **14.8** / 2.7 |
| skills DEV after night 2 (from the repaired model / from the unrepaired one) | 82.9 / 82.9 | 84.8 / 84.7 |
| C2 first try after night 2 (repaired / unrepaired) | 38.7 / 34.0 | 40.2 / 39.5 |

Also shown: night 2 by itself adds no skills harm (night 2 vs night 1: 0.0 and -0.5 points, no family drops significantly). The loss comes from night 1 and from the N' stepping stone.

Facts about the optimiser that may matter: B2 was pre-trained with AdamW (betas 0.9/0.95, weight decay 0.1 on matrices), lr 1e-3, linear warmup then cosine to 1e-4, batch 64. Every night and every repair round starts a **fresh** AdamW at peak lr 1e-3 (the same peak as pre-training), with warmup 20 (night) or 10 (repair), then cosine to 1e-4. The night's replay rows are drawn fresh from all 200k training rows (each seen about once). The repair's rows are a small set reused several times.

## 3c. A 2 x 2 check (shown, 10:27 AM ET 10-08): reuse hurts skills; any lr 1e-3 pass erases the new task

Starting from night 1's model, 256 replay-only updates on its own skills training rows, all 34 families. lr 1e-3 or 1e-4, crossed with "reused" (1,024 rows, each seen 16 times) or "fresh" (16,384 distinct rows, each seen once). Parent A / parent B:

| cell | skills DEV all-34 exact (night-1 model: 82.9 / 84.2; N': 86.7 / 87.8) | C2 first try (night-1 model: 31.2 / 34.4) |
|---|---|---|
| lr 1e-3, reused | 79.1 / 80.1 | 2.0 / 2.7 |
| lr 1e-3, fresh | **84.7 / 86.5** | 0.0 / 2.3 |
| lr 1e-4, reused | 82.9 / 84.5 | 24.6 / 30.9 |
| lr 1e-4, fresh | **84.5 / 86.2** | 24.2 / 30.1 |

So reusing a small row set causes the skills damage, and fresh rows help at either lr. But at lr 1e-3, the new C2 skill is erased by any replay-only pass, reused or fresh. The night's C2 records are themselves a small set seen 32 times at lr 1e-3. Yet night 2 uses the same recipe and adds no skills harm, while night 1 costs about 3.7 points.

## 4. My candidate explanations (all untested)

1. **Format interference:** C2 records teach "few examples → write a rule program" on prompts that look like seq_next/rule_apply/cipher_map. The update moves exactly the representations those families use. Uniform replay gives each family about 1/34 of half a batch (about 1 row per update), against 32 C2 rows. (Against this: fewshot_number_rule, the most C2-like family, improves.)
2. **Thin replay per family:** the problem is the replay share per family, not the format.
3. **Too many visits per record (32) or too high a learning rate:** the model overfits the records and drifts.
4. **Shared output head:** C2 records use a few operations and pointer patterns heavily, which shifts the prior over ops for every task.
5. **Optimiser drift (added after 3b):** on rows the model already fits, gradients are mostly noise; a fresh Adam at the pre-training peak lr turns noise into full-size steps, so replay-only updates move the weights away. In the night, the C2 records give a real gradient and the replay half pulls back. (For: replay-only on its own training rows hurts, with every family as well as only the dropped ones. Against: the night uses the same lr for ~1,200 updates and, from a damaged model, it restores skills.)
6. **Overfitting a small replay set (added after 3b):** the repair reuses 1,024 rows 4-16 times; the night sees fresh rows.
7. Something else.

## 5. Questions

1. Rank these explanations (or better ones). For each, give the cheapest diagnostic using only what I have: the checkpoints B2, N', night 1 and night 2; the records; the replay rows; CPU only; no new data.
2. Given 3b and 3c, what is the single best next change? It must keep every step autonomous (the deployed model must be able to do it alone, with no hand-picked families or hand-tuned values). Options I'm considering:
   - (a) a repair pass after each night: the model checks itself on a held slice of its own training rows and does replay-only updates on families that dropped (**tested, section 3b: made it worse**; say whether a different version of it could work, and why);
   - (b) more replay overall;
   - (c) replay weighted toward rows whose loss rose most during the night;
   - (d) fewer visits per record or a lower learning rate;
   - (e) a regulariser toward the pre-night weights (EWC, L2-SP, or KL to the pre-night model on replay rows);
   - (f) something else.
3. For the change you pick: give pass marks fixed in advance and the result that would prove it wrong. Keep the C2 gain in the marks too (C2 first try within 2 points of the unrepaired night). Our new harm rule: all-34-family exact drops at most 1.5 points, and no family drops more than 5 points with its paired 95% interval below 0.

Please give one change at a time, label claims shown / suggested / untested, and end with a plain-language summary.
