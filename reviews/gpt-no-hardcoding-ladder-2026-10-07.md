# Remove every hand-written part from a small reasoning model: is this ladder right? (no code or file access needed)

*(Updated 10-09: the B3 paragraph in section 4 and question 5 were rewritten to match the design as built and the owner's decisions since 10-07. Sections 1-3, the ladder list, the size band and the marks under it are the 10-07 state; the ladder is now run as two groups of changes, each tested once, and B3 with the pretrained encoder is compared with a plain model at the same limits, not held to the 3.24M band.)*

You are an expert in small neural reasoning models, tool-using language models and character-level input. You have **no access** to my code, files or machine, so everything you need is below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say what it is and how it would change your answer. Label every claim **shown by the data below**, **suggested** or **untested**. Two seeds is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. The model today ("B2", about 3.3M trainable parameters, trained from scratch)

Questions are short English with numbers, up to 208 ASCII characters (median about 80), from a synthetic curriculum: arithmetic chains, missing-operand equations, ciphers, rule application, few-shot number rules, lookups, short stories. About 200k training rows, about 5.4M word pieces in total, each row seen about 30 times. Answers are short (a number, a copied word, or up to 8 characters).

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
| Same, with a calculator forcing each step's result in when the text ends with "a op b =" (6 seeds) | 3.26M | about 68 | 96.2-96.6 |

Other shown facts:
- B2 vs the step-writing transformer: paired difference +6.9 over 6 seeds (SD of the paired difference about 0.94).
- Removing the conv window costs 6.3-6.8 pooled-5 and the cipher family falls from about 97 to about 4 (letters still in). The step-writing transformer above, which attends over the whole question with no window, reads ciphers at 64 (6-seed range 38-93).
- Adding a frozen pretrained sentence encoder's per-token states (270M, subword) on top of the letters and window: +1.6 / +2.1 (2 seeds), mostly on held-out wording (+3.6 and +2.7 on two splits), but it failed its pre-registered screen (variant split +1.7 against +3.0 needed; a zero-round leak of 18% on one seed) and lost on some letter-pattern families. Four versions without the window (with or without letters) all lost, ciphers 0-10. A 6-seed confirm on fresh seeds is running.
- The place code alone changed plain transformers by +0.8 and -0.8 (noise).
- B2 misses 66% of the "variant" split (new layouts and new kinds of computation) and about 10-25% of the others. Families with no worked steps in the data (few-shot number rules, lookups) are its weakest.
- Lesions: with the executor removed, program families fall to about 1%; swapping ADD and SUB inside the executor makes 99.9% of answers follow the swapped program; with zero thinker rounds B2 still answers 0-6.8% (a copy-path leak).

## 3. The owner's rule

Everything the model does must be learned. Hand-written code is allowed only inside an external tool the model chooses to call: the model writes the call as text, and the tool's reply comes back as text the model reads like the question. Teaching material (labels, worked traces) may be hand-written. If removing a hand-written part costs points, the fix must be in the learned link that broke, never putting the part back.

## 4. The proposed end state ("B3") and ladder

B3 (as of 10-09): the question goes in as raw bytes, read once by a frozen pretrained text encoder (EmbeddingGemma 2, 271M, counted in the model's size; the owner chose it as the main reader on 10-08), with the same learned 9-letter window running on the letters on top of it; inputs up to 2,000 letters. The same looped thinker; no workspace slots. After any thinking round, a small call writer reads the thinker's first control vector and writes either one one-operation call such as `sub 12 5` or nothing. An external calculator parses the call and replies with a string (`sub 12 5 = 7`); that line is read by the letter window as a new short string and the thinker sees it from the next round. The question is not re-read; all calls happen inside one thinking pass. One small learned stop head decides after each round whether the thinking is done (at least 1 round, at most 32); there is one stop for the whole answer, not one per call. Then a learned talker writes the answer from the thinker's final state, copying exact digits or names from the question or a reply where the thinker points. Training: teacher forcing on traces built from the worked steps, with the tool's real reply inserted. The tool loop, call grammar, the tool's op list and safety caps (16 calls, 32 rounds) are hand code inside the tool, which the rule allows.

Ladder, one change at a time; each 2-seed screen is against the previous rung, same seed, same machine:
1. **D0** (no training): probes on today's checkpoints: can digits be read back from the reader output; can the talker copy a 1-9 digit string. Plus a control: the same probe on a reader trained only to read digits.
2. **D0b** (no training): on the step-writing transformer with its calculator, label each failed chain row by its first wrong link (operand copied wrong, wrong operand chosen, wrong operation, tool result copied wrong, final answer copied wrong, calculator did not fire, stopped early).
3. **T1**: calculator outside (call written as text, reply read as text, no exact value codes, no result slots). Its own screen, then its own 6-seed confirm before anything is stacked on it.
4. **O1**: final answers go through T1's writer; delete the three hand renderers (empty if T1 already did this).
5. **N1**: delete any remaining regex number slots and constants.
6. **P1**: delete the hand place code.
7. **V1**: bytes instead of the hand-built character list (identical symbols for ASCII).
8. **B3 confirm**, 6 seeds.

Size band: within +-3% of 3.24M for every rung (B2 is 3.30M, so about 39k parameters of headroom).

Screen marks for O1, N1, P1 (fixed in advance): pooled-5 no more than 2.0 below the previous rung AND no more than 2.0 below B2 on both seeds; chain-5 >= 99.0; cipher (120 rows) >= 92.5; no split down more than 3.0 on the 2-seed mean; zero-round leak <= max(5, B2 on that seed + 1); plus a link check (among number answers, rows whose right digits were available but written wrong <= 1%; specific families within 3.0 of the previous rung). Proved wrong: 2-seed mean more than 4.0 below the previous rung, or chain-5 below 95 on both.

B3 confirm (6 seeds, paired SD of B2 vs the direct-answer transformer 0.94, vs the step-writing transformer 1.33, B2 alone 0.63): parity uses T1's sealed wording, which today reads "the 95% CI of (B3 - B2) lies inside +-1.0" (I think that cannot be passed at this noise, see question 3); mean(B3 - step-writing transformer) >= +3.0 with CI lower bound > 0; chain-5 mean within 1.0 of B2 and >= 99.0 on 5 of 6 seeds; tool off: program families < 5%; + and - swapped inside the tool: >= 99% of affected chain rows follow the swap; leaks <= 5 per seed (B2 itself misses this on 2 of 6 seeds); no split down more than 2.0; an audit that no regex, int() or str() of a number runs outside the tool; call cap hit on <= 1% of rows. Proved wrong: mean(B3 - B2) below -2.0, chain-5 mean below 95, or B3 not ahead of the step-writing transformer.

## 5. What I want from you

1. Which link is most likely to break first (reading digits, choosing operands, writing calls, re-reading results, stopping), and the cheapest pre-registered test that would show it, with its pass mark and the result that would prove you wrong.
2. Is the ladder order right? Would you move P1 (place code) or W1 (global attention) earlier, or merge any rungs? Keep to one change at a time.
3. Are the marks sensible for 2-seed screens and a 6-seed confirm with paired SDs of 0.9-1.3? In particular, the parity mark "6-seed 95% CI inside +-1.0": its half-width is about 1.05 x SD, so I think it is unpassable at this noise. What parity mark would you seal instead, and how many seeds would an equivalence test need?
4. The step-writing transformer with a regex-triggered calculator already exists and gets 96 on chains vs B2's 99.7. What does that gap most likely come from, and how would you test that before building B3?
5. On input units: the owner has settled the reader (the pretrained encoder in front, the learned letter window kept on top), so please do not argue for removing either. Given the evidence above (every cipher collapse happened when the window was removed, with or without letters), and inputs of up to 2,000 letters: would letting the thinker read the encoder's word pieces instead of every letter (letters still kept for the window and for copying) cost exact letter and digit skills at this size, and what one test would show it, with pass marks?
6. Keep the small synthetic curriculum and any larger "village" or world model separate; this question is only about the small curriculum model.
7. A plain-language summary for me (a high-school senior): what the plan is, what is most likely to go wrong, and what you would do first.
