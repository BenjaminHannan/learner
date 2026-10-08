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

## 4. My candidate explanations (all untested)

1. **Format interference:** C2 records teach "few examples → write a rule program" on prompts that look like seq_next/rule_apply/cipher_map. The update moves exactly the representations those families use. Uniform replay gives each family about 1/34 of half a batch (about 1 row per update), against 32 C2 rows. (Against this: fewshot_number_rule, the most C2-like family, improves.)
2. **Thin replay per family:** the problem is the replay share per family, not the format.
3. **Too many visits per record (32) or too high a learning rate:** the model overfits the records and drifts.
4. **Shared output head:** C2 records use a few operations and pointer patterns heavily, which shifts the prior over ops for every task.
5. Something else.

## 5. Questions

1. Rank these explanations (or better ones). For each, give the cheapest diagnostic using only what I have: the checkpoints B2, N', night 1 and night 2; the records; the replay rows; CPU only; no new data.
2. What is the single best next change? It must keep every step autonomous (the deployed model must be able to do it alone, with no hand-picked families or hand-tuned values). Options I'm considering:
   - (a) a repair pass after each night: the model checks itself on a held slice of its own training rows and does replay-only updates on families that dropped;
   - (b) more replay overall;
   - (c) replay weighted toward rows whose loss rose most during the night;
   - (d) fewer visits per record or a lower learning rate;
   - (e) a regulariser toward the pre-night weights (EWC, L2-SP, or KL to the pre-night model on replay rows);
   - (f) something else.
3. For the change you pick: give pass marks fixed in advance and the result that would prove it wrong. Keep the C2 gain in the marks too (C2 first try within 2 points of the unrepaired night). Our new harm rule: all-34-family exact drops at most 1.5 points, and no family drops more than 5 points with its paired 95% interval below 0.

Please give one change at a time, label claims shown / suggested / untested, and end with a plain-language summary.
