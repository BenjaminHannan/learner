# H5: glue design for reader -> learned reasoner -> talker (interfaces, learned vs scaffold, stub that runs without torch)

Helper H5, 2026-09-28T19:36Z (`date -u`). Builds on H4's `PLAN.md` / `PASSMARKS.md` (artifacts/claude-dir-h4-e2e-20260928/). Ben's goals page beats this file.
No model was run, nothing was trained, no GPU. The stub code `scripts/claude_dir_h5_glue.py` uses MOCK models; it proves the plumbing, not any model.
Labels: **shown** (I ran it or read the file, path given) / **suggested** / **untested**. Small card experiments and the village model are out.

## 0. In plain words

1. There are five hand-offs and today none of them is written down as one format. This file fixes them: six small formats, I1 to I6 (section 2).
2. Every piece of glue is marked **learned** or **scaffold** (a hand-written piece kept only as disclosed test scaffolding, Ben's 16:04 rule). Section 3.
   Result: the glue itself learns nothing. What is learned is the reader (lis-320), the square copier (gr-9 L9) and the loop reasoner. Everything between them is mechanical or a check.
3. The stub runs the whole chain on a 6-life dev sample in under a second on this box. All 27 stub checks pass (section 6). That says the formats fit together. It says nothing about quality.
4. **Two things the stub showed that H4's plan did not say** (section 5): the chain calls the reasoner on every message that holds a square, whatever was asked, so mark E5a cannot pass as built;
   and the hand parser used by the J-scaf arm reads only 5 of the 8 practice layouts and none of the held-out ones, so J-scaf is not a clean "reasoner given the grid" arm.

## 1. The chain and the six formats

```
user message (verbatim text, I0)
   |-- lis-320 reader ------------------------------> I1 frame + confidences --(S7 gate)--> fact thoughts  (I6)
   |-- gr-9 L9 copier ------------------------------> I2 "none" | s rows of s cells
   |        rows -> S1 -> I3 token request -> loop net -> I4 result -> S2 check -> I5 verdict -> solution / no_solution thought (I6)
   |-- notebook (every user turn, verbatim; reader facts as pointers to their turn) -> recalled facts + raw turns
   v
G2 serializer: system text = instruction line + fact lines (each with its source) + raw turns + reasoner note
   v
LFM2.5-1.2B talker (untrained)  -> reply
   v
G3 provenance: attach a source only if a verbatim user turn that holds the value the reply states
```

## 2. The formats (exact). Shown by `check_*` functions in the stub, each asserted on every turn of the agent.

**I0 message.** Plain string, kept word for word. The notebook stores it before anything else changes it (`store.remember(text, "heard", turn_no)`).

**I1 reader out** (existing, lis-319/320; `Reader319.read(turn, prev_reply, history) -> (frame, confs, raw, ms)`, scripts/claude_lis319_read.py:31-56, shown):
```json
{"act": "ASSERT", "facts": [{"owner": "me", "rel": "sister", "value": "Zorvan", "mode": "ASSERT"}]}      confs = [0.999]
```
`confs[i]` = lowest token probability of fact i. `act` in ASSERT/CORRECT/ASK/CHAT (the stub only checks it is a string). Nothing here is new.

**I2 square reader out** (existing, gr-9 L9; `Copier5.copy(text) -> {"raw","grid","complete"}`, scripts/claude_gr5.py:111-140, shown): `raw` is `none`, or `s` lines
of `s` cells separated by one space, each cell a digit or `_`; `grid` is the parsed ints (0 = blank) or None (`claude_gr4.parse`, scripts/claude_gr4.py:91-102, 3 <= s <= 9).
```json
{"raw": "1 _ 3\n_ 3 _\n3 _ 2", "grid": [[1,0,3],[0,3,0],[3,0,2]], "complete": true}
```
This is where "is there a square, and what is it" is decided, by a learned model. It is the only place the chain decides the reasoner has a job (but see section 5, finding 1).

**I3 request (glue -> reasoner)** (new, mechanical; mirrors `claude_rsn358b2_bridge.item_of`, scripts/claude_rsn358b2_bridge.py:102-114, shown). Token ids are `claude_rsn358a_envs`
(BLANK 0, MASK 1, SYM 12; scripts/claude_rsn358a_envs.py:33-40; the stub's selftest cross-checks them and passes): a clue `v` becomes `SYM+v-1`, a blank becomes `MASK`, slot = 1 on blanks, and
two legend rows follow (a blank row, then `SYM..SYM+s-1`).
```json
{"size": 3, "grid": [[1,0,3],[0,3,0],[3,0,2]],
 "tokens": [[12,1,14],[1,14,1],[14,1,13],[0,0,0],[12,13,14]],
 "slot":   [[0,1,0],[1,0,1],[0,1,0],[0,0,0],[0,0,0]], "legend": true, "env": null}
```
`env` is `null` on purpose: the kind-free nets (rsn-358u line) force one fixed kind index (`FIXED_ENV = 0`) for every item inside their loader (scripts/claude_rsn358u_run.py:33-41, shown), so the chat glue passes no kind. A
caller-given kind label was ruled out by Ben (ADDENDUM-43 per H4). The net's loader takes `tokens`, `slot`, `env`.

**I4 result (reasoner out)** (new wrapper around `LoopSolver.solve(puz) -> (grid, rounds)`, bridge :117-146, shown):
```json
{"grid": [[1,2,3],[2,3,1],[3,1,2]], "rounds": 3, "stop": "steady3"}
```
`stop` names the stop rule that ended the loop: `steady3` (the hand rule) or `learned` (a stop head, owed). The stub prints `mock`.

**I5 verdict (S2)** (new, mechanical): `{"status": "checked"|"failed_check"|"clash"|"no_grid", "grid": <ints or null>, "rounds": <int or null>}`.
`checked` = the grid agrees with every clue and every row and column holds each number once (`is_solution`, bridge :92, shown). `clash` = a clue repeats in a row or column: the net is not called.

**I6 thought (the shared currency handed to the talker)** (new):
```json
{"src": "reader"|"reasoner"|"notebook", "kind": "fact"|"solution"|"no_solution"|"recall_turn", "turn": 5,
 "body": {...}, "source_turn": 5, "source_text": "<the user's message, verbatim>" | null}
```
Examples (from the stub, shown): a fact `{"src":"reader","kind":"fact","turn":1,"body":{"owner":"me","rel":"sister","value":"Zorvan","mode":"ASSERT"},"source_turn":1,"source_text":"<turn 1 verbatim>"}`;
a solution `{"src":"reasoner","kind":"solution","turn":5,"body":{"grid":[[1,2,3],...],"rounds":3},"source_turn":5,"source_text":null}`.
Only facts carry a source (the reader's fact points to the exact user turn it came from = Ben's "word-for-word source"). The owner "me" is stored as `USER` (0.2c's notebook convention).

**Talker input (G2 output)** = one system message plus the last 6 (user, reply) pairs plus the user's message. The system text is exactly:
```
<instruction line>                                   (S5; same in every arm; in the stub a short stand-in, in the real run claude_e2e336_twin.SYSTEM)

Facts saved from earlier messages, oldest first (each line ends with the user's own words):
- turn 1: USER | sister | Zorvan | said: "<turn 1 verbatim>"

Earlier messages from the user, oldest first:
User said, "<turn text>"

Reasoner result for the number square in the last message (checked):        <- H1, the 0.2d frame (claude_e2e02d.py:240-246)
1 2 3
2 3 1
3 1 2
```
or, for a clash or failed check, the 0.2d sentence `Reasoner result for the number square in the last message: no square fits its clues.` Blocks with nothing to show are left out, so a message
with nothing recalled has a system text of the instruction line alone, and "I don't know" comes from that plus the instruction (a prompt line, not a learned doubt).
Facts and raw turns are shown in time order and never merged: which of two told values is newest is left to the talker (F1, code supersession, stays out; shown working in the stub only because the mock talker takes the newest line).

**Log row the scorer reads** (per reply, added by the runner): `{id, reply, hit_max, reasoner_called, l9_grid, sources, s6_removed, ms}`. `sources` is the list of user turns G3 attached.

## 3. Learned vs scaffold, piece by piece

| # | Piece | Where | Learned or scaffold | Notes |
|---|---|---|---|---|
| 1 | Reading a chat message into facts | I1 | **learned** (lis-320, MiniCPM5-1B LoRA) | training data GLM/Luna words + code labels; not landed (H4 B1) |
| 2 | S7 gate: `check_fact` (153 closed relation names, owner/value must be spans, pronoun owners refused) + threshold 0.995 | I1 -> facts | **scaffold** (rules inside the reader's path; scored under H-R) | shown: refuses a pronoun owner (stub check "S7 gate drops a pronoun owner") |
| 3 | Deciding a message holds a square, and copying it | I2 | **learned** (gr-9 L9) | DEV-FAIL by 3 items in two practice sets (H4 PLAN 1.2); untested on a sealed panel |
| 4 | S1 grid text -> token grid | I3 | **scaffold, mechanical** (no decisions) | token ids copied from the env file |
| 5 | Kind label | I3 `env` | **removed**: fixed constant inside the kind-free net's loader | not caller-given |
| 6 | Filling the square | loop net (358u/358u2) | **learned** | 6.44M weights; grids6 292.75 of 300 (358u2), grids7 208.5 of 300 (H4 PLAN 1.3) |
| 7 | Stop rule | I4 `stop` | **mixed**: the confidence head `q` is learned, the "3 steady rounds" rule is **scaffold** (`stop_round`: first round r >= 2 with q[r] > 0.5 and p[r] == p[r-1] == p[r-2], scripts/claude_rsn358a2_run.py:27-29, shown) | H4's Q on which stop the 358u nets use: they import the v2 stop (claude_rsn358u_run.py:8 "v2 stop", shown), so `steady3` |
| 8 | S2 answer check | I5 | **scaffold** (problem-specific answer gate) | the only reason the chain ever says "no square fits"; learned counterpart owed |
| 9 | Hand-off frame H1 | talker input | **scaffold** (interface text) | learned counterpart: a talker adapter that reads the note (owed, ADDENDUM-49 allows) |
| 10 | Notebook storage of every turn verbatim | store | **mechanical** | Ben's "keep the raw experience" |
| 11 | Recall (top-k by frozen MiniLM + BM25 in the real store v4) | store | **borrowed weights + code**, nothing of ours learned | the stub uses word overlap |
| 12 | G2 serializer (time order, no merge, no supersession) | talker input | **scaffold, mechanical template** | the one place the reader's output reaches the talker |
| 13 | S5 instruction line, "I don't know" | talker input | **scaffold** (fixed line, same in every arm, masked from any loss; nothing trained here) | learned doubt owed (y1t NO-GO) |
| 14 | Talker writing the reply | talker | **borrowed, untrained** (LFM2.5-1.2B) | whether it retells a checked grid faithfully is untested (H4 B7) |
| 15 | S6/G3 provenance | after reply | **scaffold**, allowed by Ben's "carries on" list | attach-only in the stub; converting an unsupported answer to "I don't know" needs a claim reader, see Q3 |
| 16 | Ablation switches noR, noRd, scaf; J-C | test tooling | **test scaffolding only**, never product | J-scaf uses `read_latin` (hand) |

Count for Ben's rule ("would this piece still exist in Ben's design?"): pieces 1, 3, 6 are the design's learned parts; 14 is the talker; 10 and 11 are the notebook (design keeps them);
2, 4, 7 (the 3-steady half), 8, 9, 12, 13, 15 are disclosed scaffold with a named learned counterpart owed; none of them decides what the user meant except S7 (it can refuse a fact) and S2 (it can refuse an answer).

## 4. The four arms as switches in the stub (`AgentH5`)

| Arm | Switch | What the stub does |
|---|---|---|
| J | none | full chain |
| J-scaf | `scaf=True` | square found by `claude_puzzle_reader.read_latin` instead of the copier |
| J-noR | `noR=True` | the square is still read but never sent to the reasoner; no reasoner note |
| J-noRd | `noRd=True` | no reader thoughts; the talker gets raw recalled turns only; the reader still runs |
| J-C | `jc_reply(truth_row)` | the true puzzle straight to the solver; the reply is the grid rows. It reads the truth file, so its owner is the scorer's owner, never a model runner |

The twins (T-LFM, T-MCP, T-QWEN) are not in the stub: they are plain models run by the bm-riv harness (`claude_bmriv_rivals.py`), and the scorer only needs their `arm_<name>.jsonl`.

## 5. What the stub showed that matters (shown unless stated)

1. **The reasoner is called on every message the copier reads as a square, whatever was asked.** L9 answers "is there a square", not "does the user want it solved". In the dev sample the square lookalike (a real square with a different ask) fired the reasoner
   (rehearsal report: `look_reasoner_called` 1 of 3 lookalikes for J, and the one square lookalike fired). H4's E5a asks for the reasoner to be called on at most 3 of 32 lookalikes, 12 of which are real squares by H4's own definition (PASSMARKS "square lookalikes (a square is present, the ask is something else)").
   As built, J would call it on about all 12 and fail E5a. A hand keyword rule ("solve") would break Ben's no-hand-rules order. **Suggested options** (all **untested**): (a) move E5a to "the reasoner's answer is not shown as the reply", i.e. count replies that give an unasked solution
   (E5b already does that); (b) let the reader's `act` field (ASK vs CHAT) gate the call, which needs lis-320 to read puzzle asks; (c) train L9's near-miss class to include "square present but not asked". Needs the Director. Open question Q1.
2. **J-scaf is a weak isolation arm.** `read_latin` reads 5 of my 8 seen layouts (row, bare, pipe, comma, md read back exactly in a 5x5 test I ran) and none of latex, label, colhead or the separator-mark layouts (`%`, `§`, `!` tried). In the dev sample J-scaf solved 0 of 4 size-5/6 squares where the layout-blind mock copier solved 4 of 4
   (rehearsal report). With half the panel's layouts held-out, J-scaf would mostly measure the hand parser. Better isolation: J-C (true grid) already exists; make J-scaf report-only or drop it. Open question Q2.
3. **The known pronoun failure survives the glue.** The S7 gate refuses a pronoun owner, so the backref facts (owner only by pronoun in the fact turn) are never saved; in the stub 0 of 2 backref asks were answered. The raw turns still reach the talker (noRd behaviour), so a real talker could still answer from them, which is exactly the E10 question.
4. **`stop` provenance is settled for now** (row 7): the 358u nets import the v2 stop rule, which is a learned confidence `q > 0.5` plus a hand "3 steady predictions" test. Report the stop as `steady3`.
5. **The 0.2d agent cannot simply be subclassed.** Its `_reason` calls `read_latin` (claude_e2e02d.py:287-292) and its `turn` never puts the reader's facts before the talker in whole-chat mode (:224-236, :299-314), so `AgentH5` is a rewrite of the turn loop with the same call signatures (`Reader.read`, `Copier.copy`, `LoopSolver.solve`, `Talker.reply`), not a subclass.
   `claude_e2e02d.FactBook` (F1 supersession), the DATE382 stamp and the 12,000-character switch are dropped, as H4's list said.
6. **H4 claims I checked** (shown): `claude_e2e02d.py` slot lines :75-80, `reasoner_note` :240, `Agent02d._reason` uses `read_latin` :287-292 region; `claude_puzzle_reader.read_latin` at :69; bridge `parse_grid` :75, `is_solution` :92, `item_of` :102, `LoopSolver` :117;
   `saved_facts` in claude_lis319_fullclaim.py :48; `stop_round` claude_rsn358a2_run.py :27; `FIXED_ENV = 0` in claude_rsn358u_run.py; gr-9 output shape from claude_gr4.parse. I did not re-verify the numbers quoted from result files (gr-9 94 of 100, 358u 292.75, etc.); those are H4's citations.

## 6. What the stub run shows (plumbing only)

`python -B scripts/claude_dir_h5_glue.py selftest`: 27 of 27 checks pass. They cover: token constants equal `claude_rsn358a_envs`; I1, I2, I3 (and I3 rejecting a wrong token), I5, I6 shapes; the S7 gate keeping a span-backed fact,
dropping a low-confidence fact and a pronoun owner; a fact travelling reader -> notebook -> serializer -> talker; its source is the user's own turn verbatim; nothing told gives "I don't know" with no source; the newer of two told values wins with no code rule;
a square goes L9 -> request -> reasoner -> check -> note -> talker, which retells the rows; a non-square turn does not call the reasoner; noR, noRd and the clash case behave as designed; the mock arms write the log rows and the scorer reads them (rehearsal mode);
J solves every size-5/6 square of the dev sample, J-scaf fewer, J-noR none, J-C all four.
The mock talker is a parser, not a language model. Nothing in these checks says how lis-320, L9, the loop net or LFM will do.

## 7. Open questions for the Director

Q1 (E5a). Which fix: (a) change E5a to count unasked solutions shown, (b) gate on the reader's `act`, or (c) train L9 to say `none` for a square nobody asked to solve? Marks are H4's; I changed none. The scorer applies E5a as written and will fail J on it if the reasoner fires on real squares.
Q2 (J-scaf). Keep it as a report-only arm with its weakness stated, or replace it by a tolerant "oracle reader" arm? Layout coverage of `read_latin` decides how meaningful it is.
Q3 (unsupported answers). PLAN 3.2 turns an answer with no verbatim source into "I don't know". That needs the stated value of the reply. Suggested: run the reader on the reply as a claim (the lis-319 fullclaim path exists; **untested** for this use). The stub attaches sources but does not convert. Needs a decision before E7/E8 are run with "S6 on".
Q4 (avoid list). The generator checks names only against the dev avoid list. The lis-320 test avoid list is a hash only (`avoid_test.sha256`); who checks the sealed panel's names against the real list, and how, without opening it?
Q5 (scorer readings R1-R8). Eight readings of ambiguous PASSMARKS wording are printed by the scorer (70%-per-half rule, "J" = both nets, "finished square", "states it cannot", "cut mid-sentence", "fabricated source"). Confirm or change them before any run; after a score is seen they cannot move.
