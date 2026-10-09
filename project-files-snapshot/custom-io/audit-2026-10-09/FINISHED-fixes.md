# Fixes for FINISHED-MODEL-2026-10-09.md from the 10-09 audit (reader/talker thread)

For the owner of `architecture/FINISHED-MODEL-2026-10-09.md`. This thread did not edit that file. Each item names the audit id, the
place in FINISHED, and suggested text. Checked on CPU at 17a356e62, whose forward path is the same as the T1SDR pin f6d724cffc.
Counts come from the T1SDR training file (sk200k train.jsonl, 200,000 rows, sha256 010af671...). Labels: **shown** = read in code or
measured; **suggested** = reasoned; **untested**. Round numbers below count from 1 (code `t` = round - 1).

## Wrong numbers (shown)

- **B12-13, sec. 5 item 1:** change 'chain-5 99.7-99.8' to 'chain-5 99.6-99.8 (mean 99.72; B2 99.4-99.7, mean 99.57)'. Source:
  `custom_io/results/T1SDR-ANALYSIS.json`, confirm mark 2, seeds 200-205: 99.7, 99.7, 99.8, 99.6, 99.7, 99.8.
- **B13-4, sec. 2 Thinker row:** 'In T1SDR and H1 (17a356e62): 8 control vectors + 9 answer registers = 17 vectors (`tool.py:325`).
  The 9 registers start as rows 0-8 of the reader's place table and share those weights. The talker's letter slots read them at the
  end (`tool.py:379`). B3 group 1: 8 control + 36 registers = 44 under the caps (untested here).' Sec. 8 deep-dive row: replace
  '(9 registers written into the code)' with '(8 control + 9 registers, `tool.py:325`)'.
- **G1 numbers where T1SDR differs (sec. 4):** row 6 says 12 fixed rounds (G1); T1SDR runs 8 (`tool.py:118, 326`). Row 1 says 91 or
  240 number slots; T1SDR has 16 (`progparse.py:8`). T1SDR's question cap is 208 letters (`data.py:11, 107`), which FINISHED never states.
- **Round numbering, sec. 3 steps 2 and 4 (B14-8):** they are one round off. The first call follows round 2, not round 1, and the
  thinker first sees its reply in round 3 (`tool.py:338, 350, 352`).

## Rows missing from the sec. 4 hand-coded table (shown, all on in every T1SDR seed)

| rule | where | replaced by |
|---|---|---|
| Layout codes on the copy pointer and the tape (B00-7, B12-2): which string a letter is in (question 0, reply k is k + 1), how far the letter is from the end of its string (0 to 39; anything farther counts as 39), and each reply's number k | `tool.py:127, 178, 205-219, 369` | Not planned. The inventory reads them as allowed position codes (judgement J3), but Ben has not ruled. They need no word splitter, only the string edges the tool loop makes |
| Span copy rules (B00-8, B13-7): the copy starts at the letter the pointer picks and steps one letter left at a time; it stops when the learned stop head says stop, at the start of its string, or after 40 letters. The stop head sees only the next letter and whether that letter is in the question or a reply. Learned: the pointer, the copy gate and the stop head. Used for 98.08% of written operands and 91.5% of answers on every seed (span_use) | `tool.py:191-197, 222-247` | O1 (inventory X1) |
| Operand slots (B13-13): a number the call writer makes itself is written in 11 slots (9 digits, a sign, an end mark), last digit first, and the code flips it. The teaching target is cut to 10 letters, which never fired in T1SDR | `tool.py:84, 181-188, 451` | Group 2's letter call writer (inventory X2) |
| Last letter first (B14-15): every writer today writes the last character first and the code flips the text: operand slots, span copies, letter-slot answers and their targets | `tool.py:188, 237, 417, 451, 510` | O1 (a writer in normal order, inventory G) |

The complete list of fixed rules and hand-computed inputs on the T1SDR/H1R path, with whether FINISHED lists each, is in the table at
the end of this file.

## Other sec. 4 edits

- **B14-1, after 'no training answer is ever cut short':** 'Exception on today's code (shown): the letter slots of T1SDR and H1 hold
  8 letters, and `tool.py:510` cuts a longer non-drill training answer to 8 letters plus the stop sign. It never fired in the T1SDR
  runs: their training answers are all 8 letters or fewer (0 of 200,000 over 8) and `data.py:109` refuses anything longer. It would
  fire on fill-in rows with 9-12 letter blanks. B3 under caps_b3 writes up to 35 letters and counts a longer answer instead of cutting
  it (cap audit). So 9-12 letter blanks are safe only on the caps path.' Add to sec. 5 item 11: 'Blanks of 9-12 letters need the
  35-letter slots; see sec. 4.'
- **B14-6, row 2 'Where' cell:** '`data.py:149-154` (the regex). It sets the place code (`reader.py:17-23`, on the question and on each
  reply), the word pointer's keys (word number, first-letter position and length, `ledger.py:209, 219-225`, via `tool.py:302, 310-312`)
  and the one-word answer slice (`tool.py:411-415`).' Replaced-by cell: 'O1 removes word pointing; P1 removes the place code.' In
  'Allowed and staying', change 'Gemma and its own word splitter' to 'Gemma and its own tokenizer (`eg.py`; not the `data.py` regex)'.
  WORD rows are 62,786 of the 200,000 training rows (31%).
- **B13-8, word splitter row:** 'The word pointer reaches only the first W_MAX words: 64 in T1SDR/H1 code, 208 in G1's caps and 727 in
  B3's caps (cap audit). A word answer beyond that is trained as letters. The skills file has at most 50 words per question, so no T1SDR
  row is affected (measured: 0).'
- **B12-2, 'Allowed and staying':** replace 'the safety caps (32 rounds, 16 calls)' with 'the safety caps (32 rounds, 16 calls; in T1SDR
  also 7 replies of at most 40 letters, operand slots of 11 letters, and a 40-letter span ceiling, `tool.py:84-89, 107`)'. None bound on
  T1SDR data (shown).
- **B13-11, 'Allowed and staying':** 'Greedy reading of learned outputs: each choice takes its top score, and each yes/no head counts as
  yes at 0.5. That covers the copy gate (`tool.py:246`), the span stop (`tool.py:233`) and the learned stop (`tool_h1.py:40, 109`). The
  inventory calls this decoding (judgement J5); Ben has not ruled.'
- **B13-14, 'used only to teach or to score':** 'Teaching labels can use only the question's numbers, earlier results and the constants
  1, 2, 10 and 100 (`progparse.py:8`). A worked step that needs any other number gets no program. The model can still write any
  constant in its operand slots. On the T1SDR training file no row lost its program this way.'
- **Not in FINISHED today (shown):** programs over 7 steps get no labels (`progparse.py:199`; 528 of 200,000 rows), and the code cuts
  each calculator reply to 40 letters (`tool.py:107`, inventory J6).

## Sec. 2 and sec. 3 wording

- **B14-9, letter window row:** 'Each letter's input is a learned letter vector + a learned position vector (208 positions in T1SDR,
  2,000 in B3) + the hand place code (sec. 4) + Gemma's meaning, then two 5-wide convolution layers (`reader.py:72-96`). T1SDR and H1 at
  17a356e62 have no Gemma term (`tool.py:120`). Calculator replies are read the same way, with positions starting at 0
  (`tool.py:155-170`).'
- **B12-11, B13-9, B14-7, Thinker row (one edit covers all three):** 'Each round the thinker also gets a learned round marker. There are
  n_loops markers: 8 in T1SDR and H1, 12 under G1's caps. Later rounds reuse the last marker (`tool.py:330`), so from round 9 (round 13
  in G1) the thinker is not told which round it is. The learned stop has to judge from the state alone. This is on purpose
  (`tool_h1.py:6`). Whether the stop needs a round count is untested.'
- **B12-10, Talker row or sec. 3 step 6:** 'With the learned stop, the last round is not fixed. So in training the talker reads the state
  after every round from the row's last call on, and its loss is the mean over those rounds (`tool_h1.py:7-9, 187-203`). The stop
  labels need this, because they read each round's answer. At test time the talker reads only the state at the model's own stop
  round.' T1SDR itself trains the talker on the final state only (`tool.py:523-536`).
- **B12-3, sec. 3 step 2, last sentence:** 'After round 2 the call writer picks `sub` and copies `12` and `5` from the question. For each
  number a learned pointer picks its last digit, and the code copies one letter at a time to the left until a learned stop head says
  stop (`tool.py:222-247`). A number that is not in the text, such as a constant, is written letter by letter in 11 slots, last digit
  first (`tool.py:181-188`).' (Round 2 per the numbering fix above.)
- **B14-8, sec. 3 'Calls happen inside the thinking':** 'In T1SDR and H1 the first call follows round 2, and call k follows round k + 1,
  up to call 7 after round 8 (`tool.py:338, 350`). Rounds 9 to 32 cannot call. The tape slot is the round, so a round with no call
  leaves its slot empty. Under "Any time" (B3 group 1, any_round), tape entry k is the row's k-th call, whatever round it came in; its
  reply is seen from the next round; the tape holds 16 calls. Built, untested.'
- **B12-5, sec. 5 item 4 (optional):** replace 'It cannot answer alone' with 'In G1's one thinker-off check it does not answer alone
  (0.66, one seed). Some arms do answer a few questions with zero rounds, including plain B2 on some seeds (up to 11.9% in_dist), so
  "cannot" is not shown.'

## A question for Ben (B14-10, sec. 5 item 11)

Fill-in rows have no worked steps, so they train on the missing word alone (no program, only a 'no call' label at weight 0.1). The
same is true of 124,991 of the 200,000 skills rows (62.5%) the 3M models trained on. Whether the no-answer-only rule (I12) covers them
is Ben's call; FINISHED does not raise it. Suggested item 11 text: 'Open for Ben (I12): fill-in rows have no worked steps, so they
train on the missing word alone. The same is true of 62.5% of the skills rows the 3M models trained on. Does the no-answer-only rule
cover them?' Suggested card: 'Does your "no answer-only" rule cover rows that never had worked steps, like fill-in blanks? YES: the
plan must give web rows steps or drop them. NO: the rule is about rows that have steps and lose them, and the plan says so in one line.'

## Sec. 8 (notes list)

Add rows marking four notes superseded (each now carries a banner): `custom-io/WHY-GEMMA-LOST-2026-10-06.md` and
`custom-io/REPORT-custom-reader-talker.md` (owner: reader/talker thread), `reader-talker-compare/verdict.md` (owner: compare thread).

## For the B3 owner (not FINISHED text)

- **B13-2, H1's 'settled' label (shown, real):** in a batch of n < 32 rounds, a row first right after round n is labelled stop at
  every round, which pushes the stop early. B3's loss calls `ToolH1.loss`, which still has this. Fix with a CPU test:
  `custom-io/audit-2026-10-09/h1-settled-fix.diff` (applies cleanly at 17a356e62; the new test and the existing H1 tests pass). It
  changes the sealed H1R build, so it needs a PASS-MARKS amendment before any H1R or B3 run, and B3's check P must then compare
  against the fixed H1R.
- **B13-1, a silent cut guard (proposed, untested):** `train.py:142` stops only a model that declares a smaller max_ans; 'tool' and
  'ledger' declare none, so `--max-ans` above 8 cuts silently. Suggested: in `tool.py` gold(), in the branch at line 509, before the
  encode, `assert not (self.training and len(ans) > GEN_MAX), f"I12: a training answer of {len(ans)} letters would be cut to
  {GEN_MAX}"`. Not applied here because B3 counts over-length answers under caps_b3 and this assert would stop such a run; B3 should
  pick refuse or count, not cut.
- **Operand target cut (B13-13):** give an operand longer than 10 letters no cell target, as `tool.py:509` already does for long drill
  answers.

## Every fixed rule or hand-computed input on the T1SDR / H1R path (shown, read at 17a356e62)

| rule | file:line | what it does | listed in FINISHED sec. 4? |
|---|---|---|---|
| 108-character list | data.py:20-24, 52-58 | Maps each character to one of 108 ids; any other character becomes UNK. | Yes (row 4, V1) |
| Question cap 208 | data.py:11, 107; reader.py:72 | A question over 208 letters is refused; the position table has 208 rows. | No (sec. 7 names only 280 and 2,000) |
| Word regex | data.py:149-154 | Splits text into words, numbers, times and punctuation. | Partly (row 2 cites only tool.py:411, reader.py:17-23) |
| Place code | reader.py:13-14, 17-23, 86 | Each letter gets its index from the right end of its word (clipped at 14; 15 for spaces and padding), added to its input. | Yes (row 2, P1) |
| Place code and positions on replies | tool.py:155-170 | Each reply is read as its own string, with positions from 0 and its own place codes. | Partly (row 2 does not say replies get it) |
| Reader input sum and window | reader.py:44, 72-96 | Input = letter + position + place (+ Gemma when on), then 2 conv blocks 5 wide. | No (sec. 2 gives only Gemma and the window) |
| Gemma refused | tool.py:120 | T1SDR and H1 cannot take the Gemma input. | No (sec. 3 step 1 notes it) |
| Number regex, first 16 | progparse.py:14, 17-18; ledger.py:200-212 | Finds unsigned digit runs in the question; keeps the first 16. | Yes (row 1, N1) |
| 16 number slots | progparse.py:8; tool.py:304-309 | Slot k = mean reader state over number k's digits + ordinal[k] + slot-type vector. | Partly (row 1 gives G1/B3 counts, not 16) |
| First 64 words | progparse.py:8; ledger.py:209 | Only the first 64 words can be pointed at. | Partly (splitter row; the cap is not named) |
| Word keys | ledger.py:65, 151, 219-225; tool.py:310 | Key = sin/cos of word number and first-letter position at fixed frequencies 0.03 x 1.6^k, + a learned length vector (clipped at 23). | No |
| Word content term | ledger.py:231-237; tool.py:311-312 | Adds the mean reader state over the word's letters to its key. | No (learned, uses the splitter) |
| Memory type vectors | ledger.py:145; tool.py:309, 313-314, 324 | src[0] for slots and src[1] for text, plus a slot-type vector: hand flags into learned vectors. | No |
| Memory layout | tool.py:334 | The thinker attends to [16 slots; visible replies; question] in that order. | No |
| Reply number per position | tool.py:323 | Each tape position's reply number = position // reply length. | No |
| Reply number vector | tool.py:127, 178, 369 | Adds the learned tape_emb[k] to every letter of reply k. | No (inventory X4, J2) |
| Thinker start | tool.py:325; ledger.py:62, 145 | 8 control vectors + 9 registers that are place rows 0-8 (17 vectors). | No |
| Fixed rounds | tool.py:118, 326 | T1SDR always runs 8 rounds. | Yes (row 6), but gives G1's 12 |
| Round marker clip | tool.py:330, 335 | Round marker = min(t, 7) (t from 0); H1R rounds 9-32 share one. | No (inventory X9, J4) |
| Reply visibility | tool.py:327, 331, 352, 374 | A reply is seen from the round after its call. | No (inventory X4) |
| Call schedule | tool.py:338, 350 | Calls only at t = 1-7 (after rounds 2-8); the call at t goes to slot t-1. | No (sec. 3 states it as a fact) |
| Head roles | tool.py:339, 378; tool_h1.py:77, 108 | Control 0 drives the call writer; control 1 drives the answer heads and H1R's stop. | No (sec. 2 names control 0) |
| Fixed op list | progparse.py:11; tool.py:86, 340, 354, 357 | Top of 9 ops (NOOP + 8); NOOP means no call. | Yes (row 3) |
| Operand cells | tool.py:84, 181-184, 341-342 | 11 slots per operand; slot j's query = W_k(z) + place row j. | No (inventory X2) |
| Cell decode | tool.py:186-188; data.py:60-69 | Top letter per slot; a = first 11, b = next 11; stop at the end mark; flip. | No |
| String id on copy keys | tool.py:142, 210-213 | Adds e_s[0 for the question, 1 + k for reply k]. | No (inventory X5, J3) |
| End distance on copy keys | tool.py:147, 214-219 | Adds e_e[distance from the string's end], clipped at 39. | No (X5, J3) |
| String start | tool.py:199-203, 227 | Start position of the string each letter sits in. | No |
| Span start | tool.py:226 | The copy starts at the pointer's top letter. | No (inventory X1) |
| Walk left | tool.py:229-236 | The copy steps one letter left per step. | No |
| Span ends | tool.py:89, 229, 233 | Stops at the string start, at a hidden letter, at stop logit >= 0, or after 40 letters. | No |
| Stop head input | tool.py:191-197, 233 | Only the next letter's detached letter vector + a prompt-or-reply bit, so where a copy ends cannot depend on the thinker. | No |
| Span flip | tool.py:237 | The copied letters are flipped into reading order. | No |
| Copy gate cut | tool.py:239-247 | An operand takes the span if gate logit >= 0, else its cells. | No (inventory X8, J5) |
| Calculator | tool.py:93-103; progparse.py:21-30; ledger.py:62 | Plain Python: 8 ops on integer text, abs < 10^9, DIV only when exact, MOD needs b != 0, else '?'. | Allowed (tool) |
| Call text and 40 cut | tool.py:106-107, 363 | The code writes 'op a b = r' and cuts it to 40 letters. | Partly (row 3 covers the op word; the cut is not named) |
| Reply read | tool.py:368-374 | Each new reply is read alone and gets tape_emb[k]. | No |
| Answer heads | tool.py:377-384 | Mode head (3-way), word pointer, span answer query, 9 registers. | No |
| Talk layout | tool.py:400-402 | Reply length = tape width / 7 (assumes the free-run layout). | No |
| Answer renderers | tool.py:406-418 | Mode 0 = span copy; mode 1 = slice word w of the question (a bad pointer falls back to letters); else letter slots. | No (inventory A12, A14) |
| Letter-slot answer | tool.py:397, 417; ledger.py:62-63, 239-249 | 9 registers, top letter each, stop at the end mark, flip; at most 8 letters taught. | No (audit B00-1; inventory A15) |
| Pointer scale and mask | ledger.py:227-229 | Dot product / sqrt(64); hidden places get -1e9. | No (standard) |
| Decoding specials | data.py:60-69 | Decoding stops at the first end mark and drops special ids. | No (standard) |
| H1R stop threshold | tool_h1.py:40, 94-95, 109 | Stop when sigmoid(stop) >= 0.5. | No (inventory J5) |
| H1R round cap | tool_h1.py:38, 109 | At most 32 rounds. | Yes (allowed caps) |
| H1R at least 1 round | tool_h1.py:107-119; tool.py:375 | The first stop check is after round 1, before any call. | No (sec. 3 step 2 says it) |
| H1R freeze | tool_h1.py:110-116, 124-135 | A stopped row keeps its own round's state; its later calls become NOOP. | No (inventory X7) |
| H1R calls after rounds 2-8 only | tool.py:338 via tool_h1.py:119 | Rounds 9-32 cannot call. | No (sec. 3 states it) |
| H1R training rounds | tool_h1.py:39, 144-145 | Training runs max(K, longest program + 1) rounds, with K drawn from {4, 8, 16, 32}. | Teaching only (allowed) |
| H1R stop labels | tool_h1.py:44-53, 204-219 | 'settled' labels from the model's own greedy answers; text compared after lowercasing (see B13-2). | Teaching only (allowed) |
| Step parser and inverse rewrite | progparse.py:42-51, 108-182 | Turns worked steps into programs. | Yes (row 5) |
| 7-step program cap | progparse.py:199 | Programs over 7 steps get no labels (528 of 200,000 rows). | No |
| Constants list | progparse.py:8, 37; tool.py:438, 461 | Labels may use only 1, 2, 10 and 100 besides text numbers and results. | No |
| First matching slot | tool.py:441 | The operand label is the text of the first slot holding the value. | No (teaching) |
| Span labels | tool.py:88, 249-283 | Tokens are \d+ in the question and -?\d+ in replies; stop label = go on inside a token, stop left of it; pointer targets every visible copy. | No (teaching; disclosed tool.py:43-48) |
| Mode-0 label rule | tool.py:445-446 | A number answer found in the context is taught as a span copy. | No (teaching) |
| Cell target cut | tool.py:450-452 | Operand targets cut to 10 letters (never fired in T1SDR). | No |
| Letter-slot target cut | tool.py:509-511 | Answer targets cut to 8 letters; long drill answers get none. | No (audit B00-1) |
| Drills | tool.py:90, 454-495 | 25% of eligible rows get random 1-10 digit results. | No (teaching) |
| NOOP weight, either order | tool.py:118, 554-560, 584-597 | NOOP rows weigh 0.1; ADD, MUL, MIN and MAX operands may come in either order. | No (teaching, inventory B6) |

Also: the reader's place table does three jobs (the place code; rows 0-8 are the thinker's 9 registers; rows 0-10 give the 11 operand
slots their positions, `tool.py:183, 325`). P1 keeps rows 0-8 as the register start but does not mention rows 9-10.
