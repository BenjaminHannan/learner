# Hand-written parts of B3 group 1 (2026-10-09)

Asked by Ben under the 10-07 rule: everything the model does when it answers must be learned. Hand-written code is allowed only inside an outside tool the model chooses to call. Teaching labels, data building, caps from data and test scoring may be hand-written.

This re-runs `INVENTORY-2026-10-07.md` for B3 group 1 (spec: `architecture/B3-GROUP1-BUILD-2026-10-09.md`, written 11:05 AM ET 10-09). Labels: **shown** = read in the code at the commit named. **suggested** = reasoned. **untested** = not run.

**Refresh, 12:55 PM ET 10-09 (architecture thread, after the no-hard-coding thread's check):** B3 group 1 is now BUILT (PR #56, `claude/project-thread-qtxfp4`: e070556ce5, and 425b036e8f fixes H1's round cap, which caps.apply had set to 109). The counts below do not change: group 1 adds no hand part and removes none of the counted ones. Two items are stale and corrected here: the tape entry is now LE = 68 characters and a longer one is counted (`tape_entry_over`), not cut silently, and operand cells are 21 (no-truncation audit, 1d69257a99; CAP-AUDIT), so E5, X2, X6 and J6's 40-char / 11-cell wording is out of date. A full re-run against built code follows when B3 group 2 is built (`architecture/B3-GROUP2-BUILD-2026-10-09.md` sec. 7, check 5).

~~**B3 group 1 is not built.** No B3 code is in the repo at the commits read. `tool.py:120` still refuses `eg_embed`, and `any_round` appears in neither `tool.py` nor `tool_h1.py`. So each B3 switch is shown for the base code, and marked "spec" where only the spec changes a line. Nothing here is a run.~~ (stale, see the refresh above)

## Summary (scorecard counts)

1. **Part 1 (how long it thinks): 0 left.** The stop is learned. Its 0.5 threshold and cap of 32 are allowed (decoding and safety cap).
2. **Part 2 (arithmetic): 2 left.** X1 (operand span copy) and X2 (operand cells, units first). J1 (the harness writes the op word) is flagged, not counted.
3. **Part 3 (reading numbers and words): 6 left.** A1, A3, A9, A10, A11, A16.
4. **Part 4 (writing answers): 4 left.** A12, A14, A15, X1 (same code as part 2).
5. **Part 8b (new kinds, training only): 6 left.** B1 to B6 in `progparse.py`. B3 group 1 does not meet 8b until L1 and ST1 exist (suggested reading of the roadmap's "required before B3").

Parts 2, 3, 4 and 8b are nonzero, as expected. Group 2 (N1, O1, P1, V1, L1, ST1) is not built.

## The picture (suggested)

B3 group 1 moves the calculator, Gemma and the stop into one model. Calls, stopping and the arithmetic become the model's own. The reader still finds numbers and words by regex and place codes. Answers still come from a mode head that picks one of three hand renderers. The span copy and the operand cells have hand direction and hand order.

## A. Old items A1 to A17 on the B3 group 1 answer path

Line numbers: `tool.py` and `tool_h1.py` at `17a356e62`. `ledger.py`, `reader.py`, `progparse.py`, `data.py`, `eg.py` at `612f5c5b0`.

| # | Part | B3 g1 status | Where | Note |
|---|---|---|---|---|
| A1 | 3 | STILL (regex). Value parse moved into calc. | Regex: `ledger.py:200-202` via `tokenize` (`ledger.py:208-211`), called at `tool.py:302`, used at `tool.py:306-308`. `int()` at `ledger.py:202` still runs, but `nv` is unused after `tool.py:302`. Parse to int is inside `calc`, `tool.py:99` (allowed). | The regex still sets the 16 number slots. Learned replacement N1. |
| A2 | - | REMOVED | `ledger.py:143` builds `vcode`; `tool.py:125` deletes it. No value code in `tool.py:306-325`. The spec adds none. | None. |
| A3 | 3 | STILL | `tool.py:306-309`: mean of reader output over each number's digits, plus ordinal and slot type. B2 original: `ledger.py:283-290`. | N1. |
| A4 | 2 | REMOVED | Constants appear only in training (`tool.py:438`, `461`). No constant slots in `tool.py:306-309`. A constant is written as digits in a cell (`tool.py:183-188`). | None. |
| A5 | 2, 3 | CHANGED (results), STILL (16 slots), REMOVED (27 slots) | 16 prompt slots: `progparse.py:8`, `tool.py:309`. Results: 7 tape entries (`tool.py:321`, `progparse.py:8`). Spec section 3 makes the tape `max(16, n_res)`. The 27-slot workspace is gone: `tool.py:125` deletes the slot pointers. | The slot cap goes with A3 (data-set cap, allowed). The tape cap is allowed (E5). |
| A6 | 2 | ALLOWED (judgement J1) | Op head: `ledger.py:149` used at `tool.py:340`. Op list: `progparse.py:11`, via `NAMES` at `tool.py:86`, into `calc` at `tool.py:93-103`. | The harness writes the op word (J1). |
| A7 | 2 | REMOVED from the forward pass. calc is outside. | B2's executor (`ledger.py:76-86`) is not called by `Tool`. calc is called from the loop at `tool.py:362`. | Allowed (tool). |
| A8 | 1 | STILL in base code. Spec section 3 and 5 change it. | Fixed call schedule: `tool.py:338` (`1 <= t <= N_RES`), `tool.py:350` (`k = t - 1`), and `tool_h1.py:124-127` (call k at iteration k + 1). Answer read after the last round: `tool.py:377-381`. Spec removes the schedule and keeps the learned stop (`tool_h1.py:97-119`). | Part 1: 0 left. |
| A9 | 3 | STILL | `reader.py:17-23` (place ids), `reader.py:71` (added to every char). Entries are read the same way (`tool.py:168` calls `self.reader`). Also cells (`tool.py:183`) and registers (`tool.py:325`). | P1, after O1 (old file). |
| A10 | 3 | STILL | `data.py:149-154` regex. `ledger.py:203-204`. `tool.py:310` (word keys). `tool.py:411` (WORD slices). | O1. |
| A11 | 3 | STILL | `ledger.py:213-219` (`word_keys`). `tool.py:310`. Word pointer `tool.py:379`. | O1. |
| A12 | 4 | CHANGED in part (NUM print gone, span copy added). STILL (WORD and GEN renderers). | Mode head: `tool.py:379`. Span copy in place of NUM: `tool.py:412-413`. WORD: `tool.py:414-415`. GEN: `tool.py:416-417`. Fallback to GEN on a bad pointer: `tool.py:414`. | O1. |
| A13 | 4 | REMOVED | No `str()` of a slot in the answer path (`tool.py:406-418`). `str()` remains in calc (`tool.py:103`, allowed) and in training (`tool.py:441-443`). | Replaced by X1. |
| A14 | 4 | STILL | Prompt slice by word span: `tool.py:414-415`. | O1. |
| A15 | 4 | STILL | 9 registers from place rows: `tool.py:325`. Units first and reversed: `tool.py:417` (answer), `tool.py:188` and `237` (cells and spans). Count and cap: `ledger.py:62-63` (`N_REG = 9`, `GEN_MAX = 8`), `data.py:11` (`MAX_ANS = 8`). | O1 (normal order). The 8-char cap is data-set (allowed). |
| A16 | 3 | STILL | Hand char table: `data.py:40-60` (`CharVocab`), ASCII set at `data.py:24`, build at `data.py:52-55`. | V1. |
| A17 | not in parts 1-4 or 8b | CHANGED: 208 to 2,000 letters (spec section 4) | `data.py:11` (`MAX_PROMPT`), `data.py:107` (assert), `reader.py:58` (position table). | A design cap from Ben's limit. Allowed, flagged (J7). Positions stay learned. |

Learned already (shown): the op head and both op pointers (`tool.py:340-341`), the mode head and word pointer (`tool.py:379`), the word-content term (`ledger.py:225-231`), and the copy attention and gate (`ledger.py:233-243`). The spec adds learned span pointers, gates and a stop head (`tool.py:344-348`, spec sections 2 and 3).

## B. Training-only items (part 8b)

| # | Where | What it does | Learned replacement (suggested) |
|---|---|---|---|
| B1 | `progparse.py:108-167` (regexes at 117, 128, 135, 143, 151) | Step parser `to_program`: worked steps become slot programs. The trace builder `tool.py:429-448` (E7) feeds it. | ST1 |
| B2 | `progparse.py:42-51`, `111-114`, `117-127` | Inverse-op rewrite: "? + 5 = 12" becomes SUB(12, 5). The last prompt number is the answer of a missing-operand equation. | L1 |
| B3 | `progparse.py:40-41`, `57-58`; `tool.py:274-282` | Operand values are matched to slots (any slot with the value is right). Pointer targets are every visible occurrence. | ST1 |
| B4 | `progparse.py:128-155`, `175-177` | Special cases: compare, range, sum, state update, verify_claim (CMP). | ST1 |
| B5 | `progparse.py:178-182`, `208`; `tool.py:445-446` | Mode labels from the answer text (NUM if the answer equals a value). | ST1 |
| B6 | `progparse.py:12` (COMM); `tool.py:580-602` (`w_row`); `tool.py:118` (`w_noop = 0.1`) | Commutative freedom and the NOOP weight. | ST1, or disclosed as teaching |

New in B3 and training only (allowed): gap rounds with masked op loss (spec section 3, a training schedule). Stop labels "settled", built from the model's own readout (`tool_h1.py:48-53`, a teaching label). Drill answers with random digits (`tool.py:454-470`, `484-487`, self-supervised data).

## C and D. Not on the B3 answer path

- C1' (text baseline calculator): not in B3 group 1.
- D1 to D10 (creative and sleep code): not in the B3 code path. The spec lists its files in sections 1 and 6, and none is a creative or notebook file. None runs when B3 answers.

## E. Harness and tool pieces

| # | Where | Status |
|---|---|---|
| E1 | Tool loop: `tool.py:350-374` (append entry, read it, next round) | ALLOWED. B3 adds a per-row count (spec section 3). |
| E2 | Call grammar: `tool.py:106-107` (`op a b = r`); calc reads the text at `tool.py:93-103` | ALLOWED. |
| E3 | Op set: `progparse.py:11`, used at `tool.py:86` | ALLOWED. |
| E4 | Reply format: `'?'` for an invalid call, `BIG` bound `tool.py:98-103` (`ledger.py:62`) | ALLOWED. |
| E5 | Safety caps: 16 calls (spec section 3), 32 rounds (`tool_h1.py:38`, `109`), 40 chars per entry (`tool.py:85`, `107`), 11 cells (`tool.py:84`), span ceiling 40 (`tool.py:89`, `229`) | ALLOWED as caps. The 40-char cut is silent (J6). (Stale: 68 chars now, counted, not cut.) |
| E6 | Fixed 8 rounds | CHANGED: learned stop (`tool_h1.py:97-119`, spec section 5). `n_loops` stays 8 (`ledger.py:130`). |
| E7 | Trace builder `row_gold`: `tool.py:429-448` | Training only. ALLOWED. |

## F. New hand-written things the old inventory does not have

| # | Where | What is hand-set | Verdict | Counted in |
|---|---|---|---|---|
| X1 | `tool.py:222-237` (`span_read`), `239-247` (`written`), `402`, `412-413` | **Span copy.** The learned pointer picks the start char (`tool.py:226`). The copy then steps one char left per step (`tool.py:230`). Bounds: the string start (`tool.py:200-203`, `227`, `233`) and the mask. Ceiling 40 (`tool.py:89`, `229`). Learned: the pointer (`tool.py:347`), the gate (`tool.py:246`), the stop (`tool.py:233`). | STILL. Direction, start convention, string bound and ceiling are hand. | Parts 2 and 4 (O1, suggested). |
| X2 | `tool.py:84`, `181-188`, `451` | **Operand cells.** 11 cells (9 digits, sign, EOS). Cell j has place row j (`tool.py:183`). The model writes each cell's character. The harness reverses the string (`tool.py:188`). | STILL. Order and width are hand. | Part 2 (O1, normal-order writer, suggested). |
| X3 | `tool.py:355-364`; `entry()` at `tool.py:106-107` | **Op word.** The op is a learned 9-way head (`tool.py:340`). The harness writes `NAMES[op]` into the call text. | ALLOWED as call grammar (E2). Judgement J1. | Not counted. |
| X4 | `tool.py:331`, `350`, `352`, `369`, `374`; spec section 3 | **Entry index and visibility.** Call k goes to entry k (T1: `t - 1`, `tool.py:350`). B3: the row's own count. An entry is visible from the next round (`tool.py:331`, `374`). `tape_emb[k]` is added (`tool.py:178`, `369`). | ALLOWED as transcript order (E1). Judgement J2. | Not counted. |
| X5 | `tool.py:210-219` (`e_s`, `e_e`) | **Layout codes.** Entry id and distance from the string end, from the text layout, fed to learned tables. | ALLOWED as position codes. Judgement J3. | Not counted. |
| X6 | `tool.py:106-107`; drill check `tool.py:467` | **Entry cut.** Entry text is cut to 40 chars. A longer result is cut silently in the transcript. | ALLOWED as reply format and cap (E4, E5). Judgement J6. | Not counted. |
| X7 | `tool_h1.py:107-117` (freeze), `124-131` (later calls dropped), `133-135` | **Stop freeze.** When a row stops, the harness copies its state and drops its later calls. Spec: "a call not yet made is simply not made." | ALLOWED as a consequence of the learned stop (E1). | Not counted. |
| X8 | `tool.py:233` (`stop_logit < 0`), `246` (`ga >= 0`); `tool_h1.py:109` (`>= P_STOP`, 0.5) | **Midpoint cuts** on learned outputs. | ALLOWED as decoding, the same as argmax over two classes. Judgement J5. | Not counted. |
| X9 | `tool.py:330` (`ts = min(t, n_loops - 1)`); `ledger.py:145` | **Round index clamp.** Rounds past 8 share round 8's embedding. | ALLOWED as a position code. Judgement J4. Under a strict reading part 1 = 1. | Not counted (see H). |
| X10 | Spec section 3 (not built) | **Tape full.** A call is not run and is counted (cap 16). Gap-round schedule. | ALLOWED (E5; training schedule). | Not counted. |
| X11 | `eg.py:22` (PREFIX), `51-69` (char to token offsets), `63-65` (fallback: the token before), `ledger.py:255-256` | **Gemma tokenizer and alignment.** This is the borrowed part Ben approved. | NOT counted. The fallback rule `eg.py:63-65` is hand code inside that part (J8). | Not counted. |
| X12 | Spec section 2; `tool.py:168` | **Entries read by the letter reader alone** (no Gemma). | Design choice from the spec. | Not counted. |

## G. Count per part

| Part | Count | Item ids | Group 2 step that removes each (suggested) |
|---|---|---|---|
| 1 how long | 0 | none | none needed |
| 2 arithmetic | 2 | X1, X2 | O1 (learned byte writer in normal order, with learned start and end copy pointers) |
| 3 reading numbers and words | 6 | A1, A3, A9, A10, A11, A16 | N1 (A1, A3); O1 (A10, A11); P1 after O1 (A9); V1 (A16) |
| 4 writing answers | 4 | A12, A14, A15, X1 | O1 (A12, A14, A15, X1) |
| 8b new kinds (training) | 6 | B1 to B6 | L1 (B2); ST1 (B1, B3, B4, B5, B6 for new kinds) |

Flagged, not counted: J1 (op word, part 2), J4 (round clamp, part 1). If Ben counts them, part 2 goes to 3 and part 1 to 1.

## H. Unsure

- **J1.** The op word is written by the harness. The model picks the op with a head and does not type it. I read this as call grammar, not as a hand decision. Ben should confirm.
- **J2 and J3.** Entry index, visibility and layout codes are read as transcript layout, not as rules that pick content.
- **J4.** The round clamp (`tool.py:330`) means rounds 9 to 32 share one step embedding. The thinker can still see its own state change.
- **J5.** Midpoint cuts are read as decoding (argmax over two classes).
- **J6.** The 40-char cut (`tool.py:107`) silently shortens a result the model reads. A cap, but worth a look. (Resolved: LE 68, a longer entry is counted by `tape_entry_over`.)
- **J7.** The 2,000-letter cap is Ben's input limit, not a value from data.
- **Registers.** Spec addendum G (36 answer registers) is not in the commits read. In code the register count is fixed at 9 (`ledger.py:62`, `tool.py:325`, `tool.py:501`) and the place table has 16 rows (`reader.py:13`). A larger count needs code changes. Not checked further.
- **Method.** Old line numbers were for `e10ea0232d`. I re-cited each line at `612f5c5b0` or `17a356e62`. Most matched. `Tool.generate` falls through to `base.py:50-58` (`612f5c5b0`) and then to `Tool.state` and `Tool.talk`. `tool.py` is not an ancestor of `612f5c5b0` (merge base `23c0d598b2`). The spec's port plan (section 1) joins them.
- **Not read in full.** Training loss and replay code (`tool.py:519-630`), extra evals (`tool.py:631-876`), `tool_h1.py` loss and evals, and `ledger.py` B2 loss and evals. None runs at answer time, because `Tool` overrides `run` and `talk`.
- The brief says A1 to A16. The old file also has A17, so A17 is included.
- Every B3 claim here is from the spec and untested.
