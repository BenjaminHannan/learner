# Every hand-written part of B2 and its helpers (2026-10-07)

Asked by Ben 12:01 PM ET 10-07: no hard-coding. Everything the model does must be learned; hand-written code is fine only inside an external tool the model chooses to call (it writes the call as text, the result comes back as text it reads).
Thread "No hard-coding + richer input" (Opus, ultracode). Labels: **shown** = read in the code, **suggested** = reasoned, **untested** = not run.
All B2 lines are at commit `e10ea0232d` of branch `claude/custom-reader-talker-4x309r` (paths under `custom_io/`). Two helpers swept the code independently (B2; creative + sleep); I read B2's model files myself and checked their lines.

## The one-line picture (shown)

When B2 answers, it never reads a number as text. Python pulls every digit run out of the question with a regex and turns it into an exact integer code; the model only picks which operation to run and which slots to point at; a Python executor does the sum; the talker prints Python `str()` of the result. Everything that ends in a learned head is learned. Everything that makes or consumes an integer is hand-written.

## A. Runs every time B2 answers (on the model's path)

| # | Part | Where | What it does | Learned replacement (rung, see PLAN) |
|---|---|---|---|---|
| A1 | Number regex + `int()` | `models/progparse.py:14,17-18`; `models/ledger.py:194-206` (200-202) | `\d+` finds the first 16 numbers and turns each into an int64 | The reader reads digits as bytes; numbers reach the calculator only as text the model copies into a call; the tool parses them (allowed). Rungs T1 + N1 |
| A2 | Exact 93-number value code | `ledger.py:68-73`, `143`, `288` | 9 digit one-hots, sign, valid flag, log size: the thinker gets each number's exact digits for free (exact up to 9 digits: clamped at 999,999,999, `ledger.py:70`; results >= 1e9 marked invalid, `83`) | Removed. The reader's own output is the only view of a number. T1 (as sealed: "no exact value codes") |
| A3 | Number-span pooling | `ledger.py:281-289` | Averages the reader output over each regex digit span to make the 16 number slots | Removed with the slots; the thinker attends to every byte already (`ledger.py:121`, `295`). N1 (if T1 kept prompt slots) |
| A4 | Constants 1, 2, 10, 100 | `progparse.py:8`; `ledger.py:285-287` | Four hand-picked numbers always sit in the workspace | The model writes any constant as digits inside a call (`mul 7 100`). With no value codes the four constant slots become identical vectors (`ledger.py:288-289`), so T1 must drop them or give them learned per-constant embeddings (disclosed); N1 removes any left |
| A5 | Workspace caps 16 numbers / 7 results / 27 slots | `progparse.py:8-10`; `ledger.py:61, 285-290` | At most 16 question numbers and 7 steps | Results live in the text transcript, so steps are not capped by slots (a safety cap on calls only). T1 removes the result cap; the 16-number cap goes in N1 if T1 keeps prompt slots |
| A6 | Fixed list of 9 ops + op head | `progparse.py:11-12`; `ledger.py:149, 314` | The thinker must choose one of NOOP ADD SUB MUL DIV MOD MIN MAX CMP | The model writes a one-operation call in T1's grammar (`sub 12 5`); the op list lives inside the calculator tool (allowed). Multi-operation expressions would be a separate, later change. T1 |
| A7 | Executor inside the forward pass | `ledger.py:76-86` (rules 83-85), `323-330` | Exact int64 sum, DIV only when exact, result written into the next slot as an exact code | External calculator tool; result returns as text and is read by the reader. T1 |
| A8 | Fixed 8 rounds, round t writes step t | `ledger.py:130, 299-330` (310, 328) | 8 loops always; at most 7 steps; answer read after the last round | T1 removes the "round t writes step t" schedule and the 7-step cap: stop = the writer outputs an answer instead of a call (learned). Rounds per turn stay fixed at 8 (depth, not a hand rule on values); learned halting is optional (H1, roadmap 2d) |
| A9 | Place code | `models/reader.py:17-23, 26-40, 58, 71` (sum `x = tok + pos + place` at 71) | Every char gets "its index from the right end of its regex word" (units digit = 0) added to its input | Dropped. Global attention in the reader (W1) can find the end of a number itself. The place table doubles as the init of the 9 GEN register tokens (`ledger.py:296-297`), so P1 drops only the place input term, and only after O1. P1 |
| A10 | Word regex `word_spans` | `data.py:149-154`; used `reader.py:21`, `ledger.py:203, 383`, `progparse.py:204` | Splits the question into words and punctuation by a hand rule | Copy by learned start/end pointers over bytes; optional learned chunker (U2). O1 |
| A11 | Content-free word keys | `ledger.py:65, 151, 213-219` | Word pointer keys from sin/cos of word index, start char and word length | Gone with WORD mode; the writer's copy attention reads byte content + learned position. O1 |
| A12 | Mode head NUM / WORD / GEN | `ledger.py:149, 335, 382-396` | Picks one of three hand-written renderers; bad pointer falls back to GEN | One learned byte writer for every answer and every call: T1 builds it for calls; O1 routes final answers through it and deletes what T1 left (PLAN 3a lists the cases) |
| A13 | NUM printed with Python `str()` | `ledger.py:389-390` | The answer's digits are printed by Python, never written by the model | The writer writes digits, copying them from the question or the tool's reply. T1 already removes it for results (no result slots); O1 removes what is left (best match for the "number-copy rule" the coordinator heard of: no code has that name) |
| A14 | WORD printed by slicing the question | `ledger.py:391-394` | Copies a whole regex word | Writer + copy attention, byte by byte. O1 |
| A15 | GEN: 9 registers, units-first order, 8-char cap | `ledger.py:63, 296-297, 356-357, 381, 438`; `data.py:11` | Answers are written reversed, at most 8 chars | Autoregressive byte writer, normal order, length learned (cap 48 for safety). T1 or O1, depending on which writer T1 builds |
| A16 | Hand-built char vocab (108 ids) | `data.py:20-24, 40-55, 81-98` | Alphabet = printable ASCII + seen chars | Raw bytes (256 ids). Same symbols as today for every ASCII prompt, but every id shifts (today 13 + (ord - 32), `data.py:40-46`) and the tied output table grows, so V1 also changes every initial weight. V1 |
| A17 | Prompt cap 208 chars | `data.py:11, 107`; `reader.py:58` | Position table size | Grows to fit question + transcript (about 400 bytes). T1 |

Learned already (shown, for fairness): op choice and both pointers (`ledger.py:314`), the mode, answer and word pointers (`335-336`), the word-content term and the copy attention and gate (`225-243`), every embedding and block.

## B. Shapes training labels only (never runs when the model answers)

| # | Part | Where | Note |
|---|---|---|---|
| B1 | Step parser `to_program` (regex over the `steps` text) | `progparse.py:108-165` | Turns worked steps into slot programs |
| B2 | Inverse-op rewriting for missing-operand questions | `progparse.py:42-51, 111-114, 117-127` | "? + 5 = 12" is taught as SUB(12, 5): hand-written algebra in the labels |
| B3 | Operand-to-slot matching by value | `progparse.py:33-41, 57-58` | Any slot holding the value is a right answer |
| B4 | verify_claim CMP rule; compare / range / sum / state_update special cases | `progparse.py:128-155, 175-177` | |
| B5 | Mode labels from the answer text | `progparse.py:196-209`; stored at `ledger.py:436` | NUM if the answer equals a slot value, WORD if it equals a word |
| B6 | Commutative operand freedom; w_noop 0.1 for rows with no program | `ledger.py:492-503` | |

These are teaching, like a teacher writing worked examples, and are allowed under Ben's rule as I read it (suggested). After T1 they are replaced by a trace builder that writes each step as a text call; the inverse-op rewriting (B2) stays as teaching and is disclosed. Rung L1 (backlog) removes even that: the model is taught from the steps exactly as written and must find the inverse call itself.

## C. Baseline and eval code (allowed, listed for completeness)

- C1' calculator in the text baseline, `models/plain_tf_steps.py:18, 30-56, 125`: the model writes `a op b =` and a regex-triggered calculator forces the result in. It is already the tool pattern Ben wants, except that a regex, not the model, decides when to call. Shown: chain-5 96 vs plain_tf_steps 94 vs B2 99.7 (`REPORT.md` table).
- Scoring (`evalx.py:15-66`) is the test, not the model.

## D. Creative (C1, C2/C2b) and memory sleep (shown, from the second sweep; branches `claude/project-thread-2zeaoc` = 2zeaoc, `claude/project-thread-2kevpk` = 2kevpk)

None of these is a tool the model chooses to call today. Each acts on B2's logits or on which tries count.

| # | Part | Where | When it acts | Learned or tool replacement (suggested) |
|---|---|---|---|---|
| D1 | Used-number mask, 4 levels: ops + - x / only and k-1 steps then stop; operands only unspent given numbers or results, never constants or the target slot; exact division only; answer = last result (B2's own answer heads bypassed) | 2zeaoc `creative/legal.py:26-43, 66-67, 113-124`, applied `93-94, 121`; level set `sampler.py:20, 138-145`, `pilot.py:22-23` | C1 answer time (C2/C2b never use it: `raw_samples(level=0)`) | Puzzle **tool**: the model writes a move, the tool applies it or replies "error: 5 already used". Used numbers are visible in the transcript (B3). On B2 meanwhile: a coverage input, then a learned legality head, tested one at a time (PLAN section 4) |
| D2 | C1 first-step branching (top 8 first steps, 32 tries, up to 4 rounds in all: 1 branching + 3 top-up, dedup) and a temperature picked by a DEV rule | 2zeaoc `sampler.py:111-176`, `legal.py:132-192`; `scoreboard.py:114-144`, `pilot.py:34` | C1 answer time | Search settings around the model. Keep as settings for now; the learned version is the model deciding to try again after a tool says "wrong" |
| D3 | C2 example checker: re-runs a try on the puzzle's examples with Python and B2's executor; only fitting tries count | 2zeaoc `creative/fewshot.py:34-103`; `c2_stuck.py:22-40` | C2/C2b, choosing which tries become sleep records and where to spend more tries | A **"try it on the examples" tool** the model calls, which replies pass/fail per example |
| D4 | C2 number parser: regex reads x1 y1 ... xk yk q from the prompt | 2zeaoc `fewshot.py:20-31`; `c2_stones.py:23-24`; `programs.py:50-62` | C2 checker and record building | Goes inside the D3 tool (allowed there) |
| D5 | C2 try budget: 32 tries, then 480 more only where none fits; T per parent from a DEV grid | 2zeaoc `c2_stuck.py:16-17, 43-54`; `c2b.py:141-147, 171-224`; `c2_dev.py` | C2/C2b | Settings for now; learned version = the model chooses to keep trying (after B3) |
| D6 | Notebook (memory sleep): stores thinker state -> op and the FIRST allowed slot per step; at answer time a top-16 cosine vote (tau 0.05) adds c = 50 x votes to B2's op and pointer logits when the best similarity >= theta (0.9, raised to the 0.99 quantile of skills-row similarity); B2's heads are monkey-patched; steps tracked by call order | 2kevpk `creative/fastsleep.py:124-157, 220-295, 301-326`, `545` | C2b arm M answer time | A **recall tool** the model calls, replying with stored programmes as text that the model can adapt (today's notebook replays slot ids, so 3x+7 cannot become 5x+2: affine 0%, `RESEARCH-2026-10-07.md` sec. 1, shown) |
| D7 | Answer note and its agreement gate (off in arm M) | 2kevpk `fastsleep.py:243-278, 305-320` | off | Dropped with D6 |
| D8 | Nightly harm switch: notebook off for the night if chain-5 harm > 2.0 | 2kevpk `fastsleep.py:566-579`; 2zeaoc `c2b.py:164-166, 308-314` | nightly | A monitoring check, like a test. Allowed |
| D9 | Warm and stepping-stone programmes from a hand-written breadth-first solver; W/R/H record rules (2 fits per question, relabel bounds) | 2zeaoc `rules_real.py:26-101, 197-207`, `stones.py`, `fewshot.py:143-271`, `c2_stuck.py:57-68` | training only | Teaching material. Allowed and disclosed |
| D10 | Checkers, puzzle generator, marks, bootstrap, blind baseline | 2zeaoc `checkers.py:19-112`, `puzzles.py`, `c2b.py:260-396` | scoring | Tests. Allowed |

Also from this sweep (shown): B2's number regex drops minus signs (`\d+`), and the C2 tasks are built so that no prompt number equals a constant slot, a data-side workaround for the hand-set constants.

## E. Hand-written parts B3 keeps, as the tool's interface (allowed, disclosed)

These sit in `tools/`, outside the model. They are the "outside world" the model talks to, the way Minecraft's rules are. Listed so the B3 audit (PLAN 3c, mark 8) knows what is allowed.

| # | Part | Note |
|---|---|---|
| E1 | Tool loop: tell a call from an answer, strip the prefix, append `sub 12 5 = 7` to the transcript, re-run the reader | The harness, like a game loop |
| E2 | Call grammar | T1's own (`add 12 5`), unchanged in B3 |
| E3 | The tool's operations | Today's 9-op list (`progparse.py:11`), including MIN, MAX, CMP and MOD; the text baseline's calculator does only + - * / (`plain_tf_steps.py:43-53`) |
| E4 | Reply format | Digits, minus sign, "error", the exact-division rule |
| E5 | Safety caps | 16 calls per question (after K1; T1 keeps 7), 48 bytes per write, a position table of about 400 bytes. Marks: call cap hit on <= 1% of dev rows, write cap on <= 0.1% |
| E6 | Fixed 8 rounds per turn | Depth, as in T1; H1 would make it learned |
| E7 | Trace builder for teaching (from B1-B4) | Teaching only; never runs when the model answers |
