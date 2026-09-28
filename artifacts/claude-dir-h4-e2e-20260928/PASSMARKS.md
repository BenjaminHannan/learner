# e2e-1 pass marks: the first joined test, reader -> learned reasoner -> talker, with notebook and "I don't know"

Helper H4, written 2026-09-28T19:16Z (`date -u`), before any run, before the panel exists, before lis-320 has a verdict.
Plan and evidence: PLAN.md in this folder. Ben's goals page (design/v3/30-modes/ben-goals-2026-09-26.md) beats this file if they clash.
These marks are fixed now. Changes go in a dated ADDENDUM file and never move a bar after any score has been seen.
A separate subagent does a blind recount from the raw reply files and this file only.
Labels: shown / suggested / untested. Nothing here touches the small card experiments or the village model.

## What is tested (the one claim)
A chat message goes in. The lis-320 reader reads it. If it holds a number square, the learned square reader hands it to the
learned loop reasoner, which fills it. The notebook keeps every turn word for word and hands back facts with their exact
source. The plain LFM2.5-1.2B talker writes every reply. When nothing was ever told, it says "I don't know".
The claim: this chain, with the disclosed scaffolds below, beats plain models of the same size on the same chats,
and each named part does work in the chain.

## Disclosed scaffolds (allowed only as listed; each is reported, none is claimed as learned)
S1 grid text to grid tokens (claude_rsn358b2_bridge.parse_grid / item_of): a format converter, no decisions.
S2 C1, the code check of the reasoner's square against the square the reader copied (claude_rsn358b2_bridge.is_solution).
S3 P3, the loop net's stop rule (claude_rsn358a2_run.stop_round), unless the chosen net has a learned stop; say which.
S4 H1, the fixed-frame hand-off of the reasoner's result to the talker (scripts/claude_e2e02d.py:240).
S5 the fixed instruction line (scripts/claude_e2e336_twin.py:15-21), same in every arm, masked from any loss (nothing is trained here).
S6 G3, the provenance check: a source turn is attached only if it is a verbatim substring of the chat AND contains the value the reply states.
S7 lis-320's own gate (threshold 0.995 and claude_lis300_compiler.check_fact), scored under H-R.
Arm J-scaf (below) swaps the learned square reader for a hand-written parser (claude_puzzle_reader.read_latin). It is the test's
own scaffold to isolate the reasoner. It is never product work and never the headline arm.

## Arms (all get the same chat messages, verbatim, in order; greedy; no sampling)
- J: the joined build. lis-320 reader, gr-9 square reader (L9), a kind-free loop net, store v4 + thought lines (PLAN.md section 3), LFM2.5-1.2B talker.
- J-scaf: J with read_latin in place of L9. Report and isolation only.
- J-noR: J with the reasoner note removed (the talker alone inside the same pipeline). Shows what the reasoner adds.
- J-noRd: J with the reader's notes and thought lines removed (the talker sees raw retrieved turns only). Shows what the reader adds.
- J-C: ceiling, no reader: the panel's true grid goes straight to the loop net. Validity check only.
- T-LFM: plain LFM2.5-1.2B-Instruct (revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b), S5 line, full chat as history. The primary twin.
- T-MCP: plain MiniCPM5-1B (revision 87179e5c1f455ef22e6223592d2d61351b525bfc), same. T-QWEN: plain Qwen3.5-2B, thinking off, same.
- Report-only: T-QWEN thinking on (16,384 new tokens); every twin at the 8,192-token cap on square turns (the bm-riv rule, scripts/claude_bmriv_rivals.py).
Twins run through the bm-riv harness settings (same message text, model's own chat template). Main cap for every arm on a square turn: 8,192 new tokens;
on other turns: 160 for J and the twins (the 336 twin's cap).
Reasoner net: one of the four rsn-358u2 nets, named BEFORE the sealed run by the rule "the two lowest seeds, s13 then s14"; J runs once with each; both
must meet E1. Only J with s13 runs the other arms. (Suggested reason: 358u2 is on the Mac, hash-checked; untested here.)

## Panel (built by code + Luna; sealed before any arm runs; TEST-ONLY, never read, printed, quoted, trained or tuned on)
- 60 lives = two halves of 30 (seeded separately, written in separate Luna calls). Fictional names only, none on artifacts/claude-lis320-20260926/avoid_names_dev.txt.
- Facts, names, puzzles, gold answers and every label are made by code. Wording of chat turns is written by GPT-6 Luna or GLM from code seeds. No Claude-written or Claude-judged text.
- Squares are drawn by code in layouts; half the squares use layouts that gr-6/7/9 training never used. Layout use is logged.
- Counts (pooled; each half has half of each):
  | Item | n |
  |---|---|
  | solve squares 5x5 | 20 |
  | solve squares 6x6 | 20 |
  | solve squares 7x7 (report only) | 10 |
  | broken squares (a clue repeated in a row; no answer exists) | 12 |
  | square lookalikes (a square is present, the ask is something else) | 12 |
  | number lookalikes (tables or lists of numbers, no square) | 20 |
  | answerable asks (30 plain, 15 corrected value, 15 owner named only in an earlier turn) | 60 |
  | never-told asks | 30 |
  | small-talk turns | 40 |
- Validity: any count above short by more than 10%, or fewer than 5 of the 7x7, or the two halves differing in a count by more than 2 in any row: INCONCLUSIVE.
- Truth lives in answers.jsonl, which no arm's runner opens. The panel's sha256 is written before the first arm starts.

## Validity (else INCONCLUSIVE, said as such, not as a pass or a fail)
V1 lis-320 has a registered H-R verdict of PASS (readpanel320 marks R1-R6). If it has none or FAILed, the run may go ahead but every line below is labelled PRE-GATE and cannot be called the demo result.
V2 Every user turn gets a non-empty reply in every arm; 0 crashes; the runner logs show each pinned model's sha256 and revision.
V3 J-C (true grid to the loop net, checked by S2): right on at least 34 of the 40 size-5 and size-6 solve items, with each of the two nets. Otherwise the reasoner, not the chain, is the limit.
V4 The two halves are both run; no half re-run after seeing a score.
V5 The blind Luna wording check (a separate Luna call, agent that saw no model output) passes: at least 95% of turns judged natural chat, at most 3 of 60 lives judged to leak the answer in the question.

## Marks (all counted on the pooled panel; each mark must ALSO hold at 70% of its bar on each half taken alone)
Squares, J against the plain twins:
- E1 J's final message gives a valid solution (by code, against the true puzzle) on at least 30 of the 40 size-5/6 solve items, with each of the two loop nets. (Prediction: about 34; reading 94-98 of 100 on the reader's own tests x reasoner 100% / 97% x a faithful retelling untested.)
- E2 J's right count is at least 10 above the best twin's right count on those 40 items (T-LFM, T-MCP, T-QWEN at the main cap), and above each.
- E3 J gives a wrong square as an answer on at most 2 of the 40, and on at most as many as the fewest of the three twins.
- E4 Broken squares (12): J gives no finished square on at least 10 and states that it cannot or that no solution fits on at least 8.
- E5 Lookalikes (32 = 12 square + 20 number): the reasoner is called on at most 3 of them, and J gives a "solution" to a square that was not asked for on at most 2.
Memory, notebook and "I don't know", J against the plain twins:
- E6 Answerable asks (60): J right on at least 36 (60%) AND at least the best twin minus 3. Corrected-value asks (15): at least 10 right. Backref asks (15): at least 8 right.
- E7 Every attached source is a verbatim substring of the user turns of that life (0 fabricated sources, by code), and at least 90% of J's right answers carry a source that contains the told value.
- E8 Never-told asks (30): J says "I don't know" (or clearly equivalent) on at least 24, and states a made-up value as fact on at most 4 (code flags candidates by the unchanged 336 scorer; two blind judges decide the flagged ones, as sf-401 and y1t-H1 did). J's made-up count is at most the fewest of the three twins'.
Each part does work:
- E9 J right minus J-noR right on the 40 solve items is at least 20 (the reasoner adds).
- E10 J right minus J-noRd right on the 60 answerable asks is at least 3 (the reader adds). If J-noRd is equal or better, this mark fails and the report says the reader is not doing work in the chain.
Chat sanity (not a headline):
- E11 Small talk: J's replies are non-empty on 40 of 40, and no reply longer than 160 new tokens is cut mid-sentence on more than 4.

PASS = V1-V5 hold and E1-E11 all hold. If V1 fails but everything else holds: "PASS, PRE-GATE".
Anything else with V2-V5 met = FAIL. A FAIL stays a FAIL.

## The result that proves it wrong (registered)
Proved wrong ("a learned chain of reader, reasoner and talker beats plain models on these chats"): validity holds and either
(a) J's right count on the 40 solve items is no more than the best twin's plus 3, or
(b) J-noR is within 5 of J on the 40 solve items (the reasoner adds almost nothing), or
(c) J-noRd is equal to or better than J on the 60 answerable asks AND J's right count on them is below the best twin's minus 3 (the reader and notebook add nothing and cost answers).
Any one of (a)-(c) is stated in those words. (a) or (b) sends the reasoner's path back to its owners with the counts; (c) sends the notebook glue back for redesign.
If E6 alone fails while E1-E5 and E7-E10 hold: "chain works on squares; memory is below the plain twin". This is the outcome the plan expects to be most at risk (mu-405: the plain 1B answered 4 of 60 stored-fact asks with the block in the system message; LFM not measured).

## Report only (no bar)
Per-stage counts for J: square turns where L9 returned a grid / "none"; grid exact vs the panel's true grid; loop net right given the copy; S2 pass; retelling faithful to the net's grid;
per-layout right (seen vs held-out layouts); mean loop rounds by size; per-turn milliseconds by stage, and peak GPU memory, on BensPC (RTX 5070 Ti); J-scaf vs J; T-QWEN thinking on; every twin at 8,192;
wrong-person count on backref asks (vread-wrongperson found this failure in vector and LoRA readers); count of turns where S6 removed a source; count of answers J-noCheck (S6 off) would have shown.
Model sizes: the biggest model inside (LFM2.5-1.2B, 1.2B) and the total, both stated (goals page "Counting size").

## Order
1. Panel made and sealed (code + Luna wording + V5 check), blind to all models.
2. DEV rehearsal on 6 readable DEV lives that are never a panel (wiring and memory only; no mark).
3. J-C, then J (s13, s14), then the other arms, one GPU job at a time; every arm's reply files kept whole.
4. Scorer (code), flagged replies to two blind judges, then the blind recount by a separate subagent from raw files and this file.
