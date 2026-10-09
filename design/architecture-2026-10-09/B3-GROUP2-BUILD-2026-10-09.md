# B3 group 2: learned reading and writing (build spec, Fri Oct 9, 12:35 PM ET)

Thread "Architecture ambiguities". Hold lifted 12:15 PM ET 10-09 (big-run thread, via the coordinator): build now, code only; no PC time until
group 2's own 3M run, which waits for G1 GO. Builds on B3 group 1 (`claude/project-thread-qtxfp4` at e070556ce5, PR #56).
Labels: **shown** = read in code; **suggested** = reasoned; **untested** = never run. Every choice below is a default I picked where the plans
leave it open; each is disclosed and can be changed by a dated addendum before the first run.

## 0. In plain words

Group 1 gave the model the calculator at any round, Gemma, long inputs and its own stop. Group 2 takes out the last hand-written parts on the
answer path. Today a small head picks one of 8 operations and the code types the operation word; numbers are found by a regex; answers come out
of three hand-made printers (copy a number backwards, slice a word, fill reversed letter slots); every letter gets a hand-made "place in its word"
code; the alphabet is a hand list of 108 characters; and worked steps like "7 + 5 = 12" are rewritten by hand rules into "12 - 5".

After group 2 there is **one learned writer**. After each round of thinking it writes either nothing or a whole tool call as letters, operation
name included (`sub 12 5`); when the model stops, the same writer writes the answer. It reads the thinker's vectors and copies letters from the
question and the replies one at a time, choosing each letter itself. The input is raw bytes. Nothing finds numbers or words before the model.
The worked steps are taught as written. Then the model teaches itself new kinds from question-and-answer pairs alone (ST1).

## 1. The parts (switches on a new model class `b3g2`; every switch off = B3 group 1 exactly)

`custom_io/models/b3g2.py`: class `B3G2(B3)`. Group 2 = all switches on. Bisect, only on failure, by turning switches off.

| Part | Switch | Removes (INVENTORY-B3 ids) | What replaces it |
|---|---|---|---|
| O1 writer | always on in `b3g2` | op head and the code typing the op word (J1, X3), operand cells (X2), span copy (X1), mode head, word pointer, word slicing, reversed GEN registers (A12, A14, A15), word keys and word content (A10, A11) | one learned byte writer (sec. 2) |
| N1 | `no_slots` | regex number spans, the 240 number slots and their ordinal / type tables (A1, A3) | nothing: the thinker reads the letters and the tape only |
| P1 | `no_place` | the place-in-word code added to every letter (A9) | nothing: positions stay learned (the place table survives only as the registers' learned starting vectors) |
| V1 | `bytes` | the hand list of 108 characters (A16) | 256 raw byte values + the same 13 specials (269 ids) |
| L1 | `as_written` | the inverse-op rewrite (B2) | the worked steps exactly as written (sec. 4) |
| ST1 | stage `custom_io/st1.py` | B1, B3-B6 for new kinds | self-taught traces (sec. 5) |

## 2. The writer (O1), `custom_io/models/writer.py`

One small decoder, autoregressive, left to right (normal reading order).
- **Input at step i:** the byte table row of the previous byte (BOS at step 0) + a learned position row (0..CAP) + a learned start row for the
  question asked (row 0 "call?" after a round, row 1 "answer" after the stop) + W_fb(feedback), where feedback is the context state the previous
  byte was copied from (CopyNet's "selective read", Gu et al. 2016, arXiv 1603.06393). Teacher forcing: the mean context state over the gold
  sources of byte i-1 (positions j whose byte equals it and, for i-1 > 0, whose left neighbour equals byte i-2), zero if it has none.
  Free run: (1 - gate) times the copy-attention-weighted context state of step i-1. No rule says where to copy next.
- **One block:** one attention whose keys are [the thinker's vectors (8 controls + 36 registers); the writer's own earlier steps, causal], then an
  MLP. Inner width d/2 (keeps the 3M count near its control, sec. 6). It does not attend to the question directly: it reads the thinker and
  copies (Ben's 09-29 rule, the talker only translates).
- **Output:** pointer-generator in fp32, as B2's GEN: gate * softmax(readout tied to the reader's byte table) + (1 - gate) * copy, copy = softmax
  of q_c(h) . k_c(context) over the visible context (prompt + entries written so far), scattered onto byte ids. The copy keys keep T1SD's learned
  layout terms (e_s which string, e_e distance from the string's end; judged allowed J2, J3).
- **Loss:** -log p(gold byte) per step, EOS included. Teacher forced, one pass per question asked.
- **Cap:** WCAP = max(LE, max_ans) + 1 steps (69 under caps_b3). A gold string longer than WCAP is counted (capcount `writer_over`) and the row
  gets no target for it, never a cut one (no-truncation rule).
- **Free run:** greedy (argmax) until EOS or WCAP, batched; rows that wrote EOS stop. `sample(temperature)` for ST1.
- **Lesions:** nocopy (gate = 1), and the existing state lesions (zero, shuffle, donor) act on the thinker vectors the writer reads.

## 3. The loop (B3G2.loop, from B3.loop)

- After each round t >= 1: the writer is asked "call?". Writing EOS first = no call. Otherwise the text up to EOS is the call. The harness splits it at
  the first space: the first word names the tool, the rest goes to it as text. Tools are a registry `{name: function(text) -> reply text}`;
  the calculator registers its 8 operation names (`add 12 5` -> calc('add', '12', '5')). An unknown name or a call the tool cannot read
  replies `?`. A domain tool added later (for example `sheet`) is one more registry entry; the model needs no new head.
- The entry `<call> = <reply>` goes to the row's next free tape entry (16), read by the letter reader as in group 1; visible from round t + 1.
  Tape full: not run, counted (group 1's tape_full).
- After the stop (H1's head, unchanged), the writer is asked "answer" and writes the answer.
- Teacher forcing uses group 1's schedule (calls at rounds 1..L, or gap rounds with p 0.25). Call rounds: gold call text. Rounds after the last
  call: target EOS ("no call"). Gap rounds: no label (as group 1). Row weights as group 1 (w_noop 0.1 for rows without calls; disclosed teaching).
- **Per-round answer (H1's settled label):** at every round t >= L the writer is asked "answer" teacher-forced; the answer loss is the row's mean
  over those rounds (H1's rule); "right at round t" = every teacher-forced argmax equals the gold byte (the same as greedy decoding being right).
  Rounds >= 9 checkpointed (H1's rule) to keep memory down.
- Gemma: unchanged from group 1 (question once, replies by the letter reader only).
- tok_think (token test) stays a separate switch; if it cannot combine with `no_slots`, the build asserts and says so.

## 4. Traces as written (L1), `custom_io/models/progtext.py`

A new trace builder: worked steps -> a list of calls as text `(op, a, b, result)` in evaluation order, with no slot matching (operands are strings,
so an operand that is not in the question is still a target; the writer composes it).
- `as_written=False` (bisect parity): the same calls T1's progparse gives today (inverse rewrite included).
- `as_written=True` (L1): no inverse rewrite. "7 + 5 = 12", where 7 is the answer and not in the question, is taught as `add 7 5`: the model must
  find 7 itself and the calculator checks it (reply 12). The answer is then copied from its own call. This is the steps exactly as written.
- Either way: the operand order is the trace's own (T1's either-order freedom for add/mul/min/max, B6, is dropped with the writer; disclosed).
- Counts printed per family: rows touched by the rewrite, rows whose calls change, rows with no trace (expected 0; any > 0 is a bug, the
  no-answer-only rule).

## 5. Self-taught traces (ST1), `custom_io/st1.py`

A stage that runs on a trained group 2 checkpoint (no new model parts).
- Input: Q/A rows (no steps) of 3 kinds held out of all trace teaching. Which kinds and where their rows come from is for the big-run thread to
  seal before the run (default suggestion: 3 kinds of the variant split, 2,000 fresh generator rows each, ids disjoint from every dev split).
- Up to 3 rounds: for each question, sample 4 traces (writer temperature 1.0, fixed); the tool runs the calls; keep the traces whose answer
  matches; train on kept traces (the model's own calls, the tool's real replies, its answer; teacher forced) mixed 1:1 with ordinary training
  rows, 500 updates per round at lr 1e-4 (fixed now, disclosed, not tuned).
- The answer check is the only hand part (at deployment, the world's feedback or a check tool).
- Marks as sealed in no-hardcoding PLAN sec. 2: held-out accuracy up >= +20 on both seeds, pooled-5 not down more than 1.0; proved wrong < +5 on both.

## 6. Sizes and machines

- 3M: the trained count should sit within 2% of g2c3 (4,022,440, the G-PT control already queued), so that control is reused and no new PC run is
  needed. If the writer leaves it outside, trim the writer's MLP first, then the thinker's feed-forward ratio (disclosed in the rung table).
- 10M / 30M / 100M: `b3_cfg` picks the block count as today (rung bands; 100M = 21 blocks x 512, no band). The writer is a few hundred thousand
  numbers there.
- Caps: `bytes` counts the prompt in bytes, so caps_b3 is re-checked in bytes on cloud CPU (`caps.py`, the long-chunk pool); any growth is a new caps
  file, never a cut.
- No PC or Mac time for the build. CPU tests only.

## 7. Checks before group 2 can queue (all CPU)

1. Parity of the parts (the writer is always on in `b3g2`, so `b3g2` itself never equals B3): the trace builder with `as_written=False` gives
   the same calls as progparse on every training row it can read (a sample of 50,000 rows where data exists, else the test rows); `bytes` on ASCII
   gives the same text; `no_slots` and `no_place` off leave the reader and thinker inputs bit-identical to group 1 (tensor check), and B3 with
   no new switch stays bit-identical to e070556ce5 (check P).
2. The writer alone learns, on CPU in minutes: copy a random 1-12 digit number from a context, write an op name and two copied operands, and
   write a number that is not in the context (exact match >= 99% on held-out toy rows; proved wrong < 90%).
3. A tiny end-to-end B3G2 run at 2,000 bytes (all switches on): loss falls, free run writes calls, the tool replies, the stop fires, answers come out.
4. The T1SDR evals still run (call accuracy on the call text, tool off, opswap replay, write_copy).
5. The hand-code inventory re-run against the built code: pass = 0 for parts 1-4 and 8b (scorecard principle 4).
6. Rung table: trained and whole counts at 3M, 10M, 30M, 100M.

## 8. Marks for group 2's 3M run (proposed here; the big-run thread seals them)

Against B3 group 1 at 3M on the same seed and pool: pooled-5 within 3.0 (proved wrong: more than 6.0 below); chain-5 within 2.0; tool-off
on program questions under 5%; missing-operand rows within 3.0 (L1's mark; proved wrong more than 10 below); inventory count 0. Then ST1's
marks (sec. 5). Kill-first: seed 400 first, stop on proved wrong.

## 9. Risks (suggested)

- Copying long numbers left to right with a learned pointer is the job the hand span copy fixed in T1S (write_copy failed at 4+ digits with
  cells). The selective-read feedback and the drills are the defence; check 2 tests it on CPU first.
- Missing-operand rows now need the inverse found in the head (L1). They may drop; that is what L1's mark measures. ST1 is the fallback.
- The per-round answer pass costs more than group 1's register readout; b3_cost measures it before any run.
- Bytes change Gemma's alignment only for non-ASCII text (byte -> its letter -> its Gemma token).

## Addendum A (1:30 PM ET 10-09): worked steps the calculator cannot express become notes

Found by the reader/talker thread (PASS-MARKS addendum 23): about 5,900 calculator-family training rows have worked steps the parser cannot turn
into calls (list_stats "count_even of [..]" and "second_largest of [..]", verify_claim "scan", arith_bare final mismatch), so in T1SDR, G1's B2
arms and B3 group 1 they train on the answer alone. Group 1 now counts them (`steps_unparsed`, a cap counter). Ben's no-answer-only rule covers
rows that have steps (his 1:20 PM ET "Allow" covers only rows with none). Default for group 2, agreed by the coordinator 1:25 PM ET:
- **A note entry.** With `as_written=True`, a step that is not a calculator call is taught as written in a note: the writer writes
  `note <the step text>`; the tool registry has `note`, which runs nothing and replies nothing; the tape entry is the call text itself. The
  thinker must still do the work in its head; the note only puts the written step on its own tape, as a person writes a line of working.
- Calls and notes mix in the step order; later calls may still use earlier results. A row whose steps are all notes still has a full trace.
- No hand algorithm is added: a step is never decomposed into calls the data did not write.
- The note's length counts against the tape entry cap (LE 68) and the writer cap (69); a longer step is counted (`tape_entry_over`,
  `writer_over`) and must be 0 on the pool (pre-PC check; if not, both caps rise to the longest step, never a cut).
- `progtext.report` counts notes per family; "rows with steps but no trace" must be 0.
Ben's card (1:25 PM ET) decides group 1 only: run disclosed, drop those rows from both arms, or wait for group 2.

## Addendum B (1:45 PM ET 10-09): the writer trains on its own feedback (refine)

Built: `custom_io/models/writer.py` (ByteWriter, commit f29cde4457 on g2-writer; test_writer ALL OK, CPU). Toy checks (500 held-out rows,
greedy exact): copy a number 100.0%, `<op> <a> <b>` with op from Z and numbers copied 99.0%, a number given only through Z 99.8%; nocopy on the
copy toy drops it to 1.0%, so the copy head does the writing. Sizes (tok table not counted): d 256 / inner 128 = 349,293; d 512 / inner 256 =
1,288,173.

One change from sec. 2: with the spec's teacher-forced feedback (the gold sources of byte i-1), the `<op> <a> <b>` toy reached about 79%
teacher-forced right but 0% greedy: the writer copied a space from the context, so in free run its own feedback pointed somewhere the gold
feedback never did. `forward(..., refine=k)` first runs k passes without gradient and replaces the feedback with the writer's own
`(1 - gate) * attn` from the step before, so training sees what free run feeds back. That toy then reached 99% greedy. refine=0 is exactly the
sec. 2 spec. B3G2 trains with refine=1 (cfg `writer_refine`, one extra no-grad writer pass per asked round) and reports how often the
teacher-forced `right` label agrees with greedy right on dev rows (B3G2-6 already lists the counters; this rate is reported, not a mark).
Nothing here is hand code: the feedback is the writer's own attention.

## Addendum C (2:05 PM ET 10-09): pre-PC check, caps in bytes

Shown from code: both pool builders drop any row or web chunk with a non-ASCII character (`data_pool/cloze_long.py:92` at 3d0afbeadd,
`custom_io/g8a/pool.py:61`; the cap audit counted 25,042 of 632,098 web chunks and 17 teach rows dropped). So every B3 training row is ASCII,
one letter is one byte, and `caps_b3.json` (2,000 / 35 / 240 / 727 / 11 / 36 / 109) holds unchanged in bytes. The dev and eval files are not
filtered by those builders; a non-ASCII dev answer that passes 35 bytes is counted by `answer_over_max` (Dataset, in bytes under V1), and
B3G2-6 needs that counter at 0. Choice, disclosed: group 2's 3M run keeps the ASCII-only pool so it trains on the same rows as group 1's
3M run (and the same filter as G1's pool behind g2c3); the 4% non-ASCII chunks a bytes model could read stay out until the bigger rungs, and adding them would be a separate, named change.

## Addendum D (2:20 PM ET 10-09): progtext on the real pool, and the control it implies

Shown (progtext f6695cbd4a, `as_written=True`, own72 `skills.jsonl`, 1,583,731 rows, all with steps; script and full output in this
thread's scratchpad, numbers copied here):
- Every row gets a trace: unreadable 0, steps_no_trace 0. 932,497 rows (59%) carry at least one note (1,025,650 notes). 19 families are
  all notes (odd_one_out, seq_next, fewshot_number_rule, order_chain, digits_parity, passage_qa, rule_apply, word_filter, prop_eval,
  seq_cycle, syllogism, letter_ops, group_induct, table_lookup, cipher_map, copy_word, kin_chain, list_index, object_track); among the
  calculator families, list_stats has 30,255 note rows and verify_claim 17,335. Many notes are short labels ("read passage", "swap", "all");
  some carry real work (list_index "list = [...]", state_update "-3 -> 4").
- arith_bare: 13,074 rows have a 'hidden' operand under as_written (the answer as written is not a prompt number).
- Longest call or note: 95 bytes (list_index notes; 15,761 entries over LE 68). Per Addendum A the caps rise, never a cut: group 2 uses
  LE 95 and WCAP 96 from a caps file (`caps_b3g2.json` = caps_b3 + le 95), group 1 keeps LE 68.
- `progparse` cannot read 932,806 of these rows, so B3 group 1's new `steps_unparsed` counter will report about 59% of skill rows, not
  "about 5,900" (that figure was T1SDR's calculator-only data). The plain model is no different: it writes steps only for 11 families
  (`plain_tf_steps.py:14-15` STEP_FAMILIES), so 23 families have trained answer-only in every arm so far, plain and calculator alike, and
  group 1 against plain stays like for like.
- Consequence for group 2: with notes it learns from worked steps on 23 families that the g2c3 control never saw, so part of any
  B3G2-1 margin over g2c3 could be that extra teaching rather than the design. Card to Ben (2:20 PM ET): give the plain control steps for
  every family (one more 3M plain run on the PC) or keep g2c3 and disclose.
