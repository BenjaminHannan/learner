# Remove every hand-written part from a small reasoning model: is this ladder right? (no code or file access needed)

You are an expert in small neural reasoning models, tool-using language models and character-level input. You have **no access** to my code, files or machine, so everything you need is below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say what it is and how it would change your answer. Label every claim **shown by the data below**, **suggested** or **untested**. Two seeds is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. The model today ("B2", about 3.3M trainable parameters, trained from scratch)

Questions are short English with numbers, up to 208 ASCII characters (median about 80), from a synthetic curriculum: arithmetic chains, missing-operand equations, ciphers, rule application, few-shot number rules, lookups, short stories. About 200k training rows, about 12M word pieces in total. Answers are short (a number, a copied word, or up to 8 characters).

- **Reader:** each character gets a learned embedding + learned position + a hand-computed "place" code (the character's index from the right end of its word, so the units digit is 0). Then 2 residual 1-D conv blocks, kernel 5 (each character sees about 4 neighbours each side). No attention.
- **Workspace:** 27 slots. 16 slots hold the question's numbers: a regex `\d+` finds them and Python turns each into an exact code (9 one-hot digits, sign, valid flag, log size). 4 slots hold the constants 1, 2, 10, 100. 7 slots hold results.
- **Thinker:** 17 state vectors (8 control + 9 register), 2 transformer blocks looped 8 times. Each round they cross-attend to every reader output and every workspace slot. In rounds 1-7, control vector 0 picks an operation from a fixed list (NOOP ADD SUB MUL DIV MOD MIN MAX CMP) and two slot pointers; a Python int64 executor inside the forward pass computes the result and writes its exact code into the next result slot.
- **Talker:** a 3-way mode head. NUM: Python prints `str()` of the slot the answer pointer picks. WORD: copies a regex-delimited word of the question. GEN: writes up to 8 characters from the 9 register vectors (units first), with a pointer-generator copy gate over the question's characters.
- **Training:** teacher-forced on slot programs that a hand-written parser builds from each row's worked steps (including hand-written algebra: "? + 5 = 12" is taught as SUB(12, 5)). 24,000 updates, batch 256, lr 1e-3.

## 2. Results (shown; "pooled-5" = exact match over 5 held-out splits, 6,040 rows; "chain-5" = 5 multi-step families, 1,000 rows)

| Model (same data and updates) | Size | pooled-5 | chain-5 |
|---|---|---|---|
| B2 (6 seeds) | 3.30M | 74.0 | 99.4-99.8 |
| Plain causal character transformer, answer only (6 seeds) | 3.24M | 53.7 | 34 |
| Same, writes the worked steps as text then the answer (6 seeds) | 3.26M | 67.1 | 94 |
| Same, with a calculator forcing each step's result in when the text ends with "a op b =" (2 seeds, older run) | 3.26M | 68.9 (vs 67.7 without, same run) | 96 |

Other shown facts:
- B2 vs the step-writing transformer: paired difference +6.9 over 6 seeds (SD of the paired difference about 0.94).
- Removing the conv window costs 6.3-6.8 pooled-5 and the cipher family falls from about 97 to about 4.
- Adding a frozen pretrained sentence encoder's per-token states (270M, subword) on top of the letters: +1.6 / +2.1 (2 seeds), mostly on held-out wording (+3.6 and +2.7 on two splits). Replacing the letters with it: every version lost, ciphers collapsed to 2.5-10.
- The place code alone changed plain transformers by +0.8 and -0.8 (noise).
- B2 misses 66% of the "variant" split (new layouts and new kinds of computation) and about 10-25% of the others. Families with no worked steps in the data (few-shot number rules, lookups) are its weakest.
- Lesions: with the executor removed, program families fall to about 1%; swapping ADD and SUB inside the executor makes 99.9% of answers follow the swapped program; with zero thinker rounds B2 still answers 0-6.8% (a copy-path leak).

## 3. The owner's rule

Everything the model does must be learned. Hand-written code is allowed only inside an external tool the model chooses to call: the model writes the call as text, and the tool's reply comes back as text the model reads like the question. Teaching material (labels, worked traces) may be hand-written. If removing a hand-written part costs points, the fix must be in the learned link that broke, never putting the part back.

## 4. The proposed end state ("B3") and ladder

B3: raw bytes in, the same window reader plus (if it passes) global self-attention; the same looped thinker; no workspace slots; one small autoregressive byte writer with copy attention over the question and transcript. The writer writes either `CALL <expression>` (an external calculator parses it and replies with a string that is appended to the context, and the reader re-reads everything) or `ANSWER <text>` (stop). Training: teacher forcing on traces built from the worked steps, with the tool's real reply inserted.

Ladder, one change at a time, each screened on 2 seeds against the previous rung:
1. **D0** (no training): probes on today's checkpoints: can digits be read back from the reader output; can the talker copy a 1-9 digit string.
2. **T1**: calculator outside (call written as text, reply read as text, no exact value codes, no result slots).
3. **O1**: one learned writer for every answer (delete the three hand renderers).
4. **N1**: delete any remaining regex number slots and constants.
5. **P1**: delete the hand place code.
6. **V1**: bytes instead of the hand-built character list (identical for ASCII).
7. **B3 confirm**, 6 seeds.

Marks fixed in advance: each rung's screen passes if pooled-5 is no more than 2.0 below the previous rung on both seeds, chain-5 >= 95, cipher >= 90, no split down more than 4, plus a link check (digit probe >= 99% per place; exact answer-string copy >= 99%). B3 passes if, over 6 seeds, mean(B3 - B2) >= -1.0 with the 95% CI lower bound >= -2.0, mean(B3 - step-writing transformer) >= +3.0, chain-5 >= 99 on 5 of 6 seeds, tool-off program families < 5%, swap-inside-the-tool >= 99% followed, and no split down more than 2. Proved wrong: mean(B3 - B2) below -3.0, or B3 not ahead of the step-writing transformer.

## 5. What I want from you

1. Which link is most likely to break first (reading digits, choosing operands, writing calls, re-reading results, stopping), and the cheapest pre-registered test that would show it, with its pass mark and the result that would prove you wrong.
2. Is the ladder order right? Would you move P1 (place code) or W1 (global attention) earlier, or merge any rungs? Keep to one change at a time.
3. Are the marks sensible for 2-seed screens and a 6-seed confirm with a paired SD near 0.94? Too strict, too loose, or missing a check?
4. The step-writing transformer with a regex-triggered calculator already exists and gets 96 on chains vs B2's 99.7. What does that gap most likely come from, and how would you test that before building B3?
5. On input units: given the evidence above, is there any reason to expect subword tokens, learned byte patches (BLT, H-Net) or a pretrained encoder to beat letters plus a deeper reader at this size? One test you would run, with pass marks.
6. Keep the small synthetic curriculum and any larger "village" or world model separate; this question is only about the small curriculum model.
7. A plain-language summary for me (a high-school senior): what the plan is, what is most likely to go wrong, and what you would do first.
