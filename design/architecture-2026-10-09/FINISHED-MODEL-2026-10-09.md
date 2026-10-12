# The finished model, in one place (source of truth, Fri Oct 9; audited 12:20 PM ET)

Asked by Ben, 9:07 AM ET 10-09: "I want to clear up any ambiguities in how the architecture works."
Thread "Architecture ambiguities". This file describes the model we plan to ship (the "big run" model) and settles what the
evidence settles. Where it disagrees with an older note, this file wins until Ben says otherwise; owners of those notes were told.
Labels: **shown** = read in code or result files; **suggested** = reasoned; **untested** = never run; **Ben** = his own words, dated;
**open** = waiting on Ben (section 7).
Code cited: `claude/custom-reader-talker-4x309r` at 17a356e62 (T1SDR/H1 model code), `claude/project-thread-f1to6a` at 612f5c5b0
(8a/G1 code), and B3 group 1 on `claude/project-thread-qtxfp4` at e070556ce5 (PR #56). The 12:20 PM ET audit (220 checked findings,
`architecture/AUDIT-2026-10-09.md`) corrected this file; the fixes are listed there. 1:25 PM ET: the reader/talker thread's checks
(`custom-io/audit-2026-10-09/FINISHED-fixes.md`, which also has the full table of fixed rules on the T1SDR path) were applied.

## 1. In one paragraph

The model reads a question, thinks in rounds, uses a calculator by writing text, and then says the answer.
A frozen, borrowed reader (EmbeddingGemma 2) gives every letter its meaning in context. Our own thinker, a fixed set of
vectors run through the same blocks again and again, looks at the whole question every round. After each round a small call
writer reads the thinker's first control vector and either writes a calculator call such as `sub 12 5` or writes nothing; the
thinker reads the reply in later rounds and decides by itself when it is done. Our own talker turns the thinker's final state into
the answer, copying exact names and digits from the text where the thinker points, and adds no thinking of its own.
About 397M numbers planned in all, borrowed parts counted: reader about 271M, thinker about 100M (21 blocks at width 512 = 97.1M),
talker about 25M. B3 group 1 at the 100M rung, as built, is 373.1M whole (102.1M trained, which includes the Gemma adapter and the
letter window, plus 271.0M frozen Gemma), because the 25M English talker is not built (shown, `g8a/configs.py` rung table).
(**Ben**, 10:49 AM ET 10-09: "Hundred. If I see demonstrable results then I may give you vast compute." So the finished thinker stays 100M;
30M is the third rung of the size ladder 3M, 10M, 30M, then 100M, and a 326M fallback. Plan on the PC and Macs only; big-run PLAN.md REPLAN item 2.)

## 2. The parts

| Part | What it does | Size | Learned? | Status |
|---|---|---|---|---|
| Reader: EmbeddingGemma 2 text part | Reads the question once; each letter gets the 768-number state of the Gemma token it sits in | 271,002,624 | borrowed, frozen | **shown** at 3M (EGE: +2.67 over B2, 6 of 6 seeds), but EGE's 6-seed confirm missed its zero-round leak mark (mean 6.59 against a limit of 4.62, plain B2's 3.62 + 1.0; RESULTS-EG2, addendum 15, per the no-hard-coding thread 10-09) and its 2-seed screen failed the variant and leak marks; Ben 10:16 AM ET 10-08: "main inputting/encoder" |
| Gemma adapter | One linear layer from Gemma's 768 numbers to the thinker's width | 196,864 at width 256, 393,728 at 512 | yes | counted as trained (8a-G spec sec. 2) |
| Reader: letter window | Two small learned layers that let each letter see 4 letters each side, on top of Gemma's meaning | about 0.7M at width 256, about 2.6M at 512 | yes | kept (**Ben**, Q3 card, 9:29 AM ET 10-09: "Keep"); tokens instead of letters are being tested (TK, sec. 6) |
| Thinker | 8 control vectors + 36 memory vectors under the caps (B3 group 1; T1SDR and H1 at 17a356e62 have 8 + 9 = 17, the 9 taken from the reader's place rows, `tool.py:325`); each round they look at every letter and every calculator reply, compare notes, and think; same weights every round | about 100M (about 21 blocks at width 512) | yes, from scratch | shape **untested** at 100M; grows depth first (Ben 10-07: "as deep as possible") |
| Call writer | After each round, reads control vector 0 and picks one of 8 operations or "no call", then copies the numbers from the question or an earlier reply | part of the thinker's output heads (the code files it under the talker, `tool.py:15`) | yes | **shown** in T1SDR; group 2 changes it to write the whole call as letters, operation name included (sec. 4) |
| Learned stop (H1) | After each round a tiny head decides "done"; at least 1 round, at most 32 | width + 1: 257 at width 256, 513 at 512 | yes | built, **never run**; first run is B3 group 1 at 3M after G1 |
| Calculator | Plain Python with 8 operations (add, sub, mul, div, mod, min, max, cmp); takes the call as text, replies as text, or `?` | 0 | hand code, allowed as a tool | **shown** working outside the model at 3M (T1SDR, 6 seeds, Ben cleared the leak mark 8:21 AM ET 10-09) |
| Talker | Writes only the final answer from the thinker's final state. Today: a span copy (its own pointer and stop head) from the question or a reply, a word pointer, or letter slots; the old number-copy mode is gone (`tool.py:19-20`) | about 25M planned | yes, from scratch | today a small stand-in; the English talker is **unbuilt** |

## 3. One question, step by step (T1SDR + H1 code, with B3 group 1's changes, which are built but have never run)

"Tom has 12 apples. He gives away 5, then buys 3. How many does he have?"
1. **Read.** Gemma reads the whole question once. Its meaning is added to every letter, and the letter window runs on top
   (`tool.py:301` calls `ledger.py:255-267`; `reader.py:82-96`). T1's code refused Gemma (`tool.py:120`); B3 group 1 removed that
   refusal, so this step is code, not yet a result.
2. **Think, rounds 1 and 2.** The thinker's vectors look at all letters and talk to each other. No call is written after the first
   round (code `t` = round - 1; calls need `t >= 1`, `tool.py:338`), so a row that stops after one round never calls. After round 2 the
   call writer writes `sub 12 5`, copying `12` and `5` from the question (`tool.py:329-374`): a learned pointer picks each number's last
   digit and the code copies one letter at a time to the left until a learned stop head says stop (`tool.py:222-247`); a number that is
   not in the text is written letter by letter in 21 slots, last digit first.
3. **Calculator.** Plain Python returns `7` (`tool.py:93-103`). The line `sub 12 5 = 7` is read by the letter reader as a new
   short string and added to the thinker's notes. The question is not re-read and the thinker keeps its vectors (`tool.py:155-170, 368-374`).
4. **Round 3.** The thinker now also sees `sub 12 5 = 7`; after it the call writer writes `add 7 3`, and the reply `10` is added the same way.
5. **More rounds.** Rounds with nothing to calculate write no call (the "no-op" choice). The learned stop ends the thinking at
   the first round it judges settled. It is trained on the "settled" label: stop once no later round would be right, so it also
   learns to stop on questions it cannot solve, not only when it is sure. At most 32 rounds (`tool_h1.py:11-17, 24, 38-40`).
6. **Talk.** The talker copies `10` from the last reply. Answer: `10`.

Two facts this pins down (**shown**, code):
- **Calls happen inside the thinking, at most one per round, not as separate passes.** In T1SDR and H1 the first call follows
  round 2 and call k follows round k + 1, up to call 7 after round 8; rounds 9-32 cannot call, and a round with no call leaves its tape
  slot empty (`tool.py:338, 350`). Ben chose "Any time" (Q1 card, 9:30 AM ET 10-09). B3 group 1
  builds it (`models/b3.py`, any_round): a call may follow any round from round 2 up to 32, tape entry k is the row's k-th call, its reply is seen from the next round, the tape holds 16 calls, and in training a quarter of
  the rows put 0-2 think-only rounds before each call. Built, **untested**. Older notes describe "turns" where the reader re-reads
  everything after each call (no-hardcoding PLAN sec. 1, redesign-ideas sec. 8b). The code does not do that.
- **The learned stop ends the whole answer.** There is one stop, not one per call (`tool_h1.py:5-17`). The sealed H1 text that
  speaks of "rounds inside one turn, separate from the stop between calls" (redesign-ideas sec. 8b) does not match the built code;
  the code is what was reviewed and queued (PASS-MARKS addendum 21). Risk (suggested): the "settled" label is judged only over the
  rounds the row ran, so a stop that fires early is never shown a later right answer; the B3 3M readout reports it.

## 4. What is learned, what is hand code, and what still has to go

Ben's rules (10-07): everything inside the model is learned; hand code runs only inside a tool the model calls; the deployed
model does everything itself; no training answer is ever cut short.

Allowed and staying: the calculator (a tool), Gemma and its own tokenizer (`eg.py`, not the `data.py` word regex; a borrowed part Ben picked, 10-06 and 10-08),
the safety caps (32 rounds, 16 calls), and everything used only to teach or to score.

Exception on today's code (**shown**): T1SDR and H1 hold 8 answer letters, and `tool.py:510` cuts a longer non-drill training answer to
8 letters. It never fired in the T1SDR runs (0 of 200,000 training answers over 8; `data.py:109` refuses longer ones), but it would fire
on 9-12 letter fill-in blanks. B3 under caps_b3 writes up to 35 letters and counts a longer answer (`gen_answer_over`), and a run with
any count above 0 fails its sealed mark, so blanks of 9-12 letters are safe only on the caps path.

Hand code still on the path today (**shown**; counts re-run against B3 group 1 in `no-hardcoding/INVENTORY-B3-2026-10-09.md`:
stop 0, arithmetic 2, reading 6, writing 4, new kinds 6; the pass mark is 0 for each). Each has a learned replacement in
**B3 group 2**, whose build started 12:15 PM ET 10-09 (code only; its 3M run waits for G1):
| Hand part | Where | Replaced by |
|---|---|---|
| Regex that finds the question's numbers (number slots: 16 in T1SDR, 91 in G1's caps, 240 in caps_b3; positions only, no values) | `ledger.py:206`, slots described at `tool.py:10-12` | N1: the thinker finds numbers in the letters |
| Word splitter for one-word answers and for the letter "place" code | `tool.py:411`, `reader.py:17-23` | O1 (one learned writer) and P1 (no place code) |
| Operation word written by the code from a fixed list of 8 (inventory J1) | `ledger.py` OPS, `tool.py` NAMES and `op_head` | group 2: the call writer writes the whole call as letters, operation name included, so a tool added later can be called |
| Hand list of 108 characters | `data.py` | V1: raw bytes |
| Worked steps rewritten by hand rules (e.g. "? + 5 = 12" becomes a subtraction) | `progparse.py:42-51` | L1 (learn the steps as written), ST1 (keep its own checked tries) |
| Fixed number of rounds (8 in T1SDR, 12 in G1) | `tool.py:118, 326`; G1 caps | H1 learned stop (in B3 group 1) |
| Layout codes on the copy pointer and the tape: which string a letter is in, its distance from the string's end (clipped), each reply's number | `tool.py:127, 178, 205-219, 369` | kept as position codes (inventory J2, J3; Ben has not ruled); group 2's writer keeps them on its copy keys |
| Span copy rules: start at the pointer's letter, step one letter left, stop at the learned stop head, the string start or the ceiling (used for 98% of written operands and 91.5% of answers on every T1SDR seed) | `tool.py:191-197, 222-247` | O1, the one learned writer (inventory X1) |
| Operand slots: a number the call writer makes itself goes in fixed slots, last digit first, and the code flips it | `tool.py:84, 181-188, 451` | O1 (inventory X2) |
| Last letter first: every writer today writes the last character first and the code flips the text | `tool.py:188, 237, 417, 451, 510` | O1, a writer in normal order |

The model with all of these done is called **B3** (no-hardcoding PLAN sec. 2). It is built in two groups: group 1 (calls at any
round, Gemma plus calculator, 2,000-letter inputs, learned stop; built, PR #56) and group 2 (the rows above). The big run trains
B3 grown to 100M, not today's B2.

## 5. Settled by the evidence (no answer needed from Ben)

1. **The calculator is outside.** T1SDR matched B2 over 6 seeds: pooled-5 +0.62 (CI -0.23 to +1.46), chain-5 99.6-99.8 (mean 99.72; B2 99.4-99.7), and
   with the calculator switched off program questions score 0.0 (MARKS-D0-T1 Record 13). Shown. Not yet shown: mark 5 (answers
   follow the reply when the reply is swapped) holds on 5 of 6 seeds; seed 205 is unscored because its checkpoint was lost.
2. **The thinker drives, with Gemma in front.** In G1's first finished run (3M, seed 400) the Gemma model scored 73.01 with the
   thinker on and 0.66 with it off (8a-G spec addendum G). Shown on one seed; reader help is allowed (Ben 10:16 AM ET 10-08).
   But Gemma-reader arms do answer some questions with zero rounds (EGE 18.09 in-distribution on seed 200 against 1.40 for B2V;
   PASS-MARKS addendum 14, cause not settled).
3. **Gemma also reaches the talker's copy keys**, not only the thinker (`ledger.py:284-302`). Allowed by Ben's 10-08 words
   ("You don't have to ban any help from the gemma reader"), and checked by the thinker-off score above.
4. **The talker may copy from the question and the calculator replies, but only where the thinker points.** It cannot answer
   alone in G1's one thinker-off check (0.66, one seed); some arms, plain B2 included on some seeds, answer a few questions with zero
   rounds (item 2), so "cannot" is not shown. This is my reading of Ben's 09-29 rule ("the
   talker translates the thinker's final state") and 10-08 rule; the "notes" he barred the talker from reading are the notebook
   memory, which the talker does not read. Suggested.
5. **Calculator replies are read by the letter window only, not by Gemma.** Gemma reads the question once (`tool.py:301`, through
   `ledger.py:255-267`); replies go through `read_texts` (`tool.py:155-170`). B3 group 1 builds it this way. Suggested: replies like
   `add 7 3 = 10` carry nothing Gemma would add.
6. **The outside calculator and Gemma have never run together.** B3 group 1 joins them in code (PR #56); the first run is
   B3 group 1 at 3M, seed 400, after G1 (PLAN G2 step 2 marks, sealed 12:10 PM ET 10-09).
7. **The finished design must pass Ben's size bar itself, not only G1.** G1 tests today's model (calculator inside, 12 fixed
   rounds, hand number slots). B3 climbs its own ladder on the PC (3M, then 10M with both groups as the G2 screen, then 30M), each
   paired with a plain model at the same caps (PLAN REPLAN). The calls-at-any-round change (K1) is folded into B3 group 1, so it
   adds no test. Earlier 8a ladder runs of this family gained only +0.03 and +0.28 from 3M to 10M (plain step model +3.08 and
   +4.25), but those runs had the register bug that G1 re-runs fixed (register-bug-8a-caps), so they do not count either way.
8. **Size counts every weight that runs, borrowed ones included** (Ben 10-06, roadmap sec. 4), the adapter and letter window
   too. This replaces the 09-28 handoff line "size counts only the biggest model inside".
9. **"About 30 blocks at width 512" is about 139M, not 100M.** One thinker block at width 512 holds 4,624,281 numbers (from
   `ledger.py:102-111`; my count, the formula reproduces G1's 10M size of 10,495,513 at 8 blocks of 256). So 100M is about 21
   blocks at 512, or 30 blocks at about width 432 (the width must divide by the head count). B3's 100M rung is 21 blocks at 512
   with 8 heads (`configs.py`).
10. **Experts.** Ben asked on 09-29 for "a sparse moe (however many active experts frontier models have) for our model"
    (handoff/director-roadmap.md:33) and on 10-09, 10:18 AM ET, to queue "trying many experts with many layers" (GX,
    `architecture/EXPERTS-TEST-2026-10-09.md`). GX stage 1 runs on the PC. Experts join only if both GX stages pass before group 2
    is frozen; otherwise run-1 is dense and experts are a second line (PLAN item 7).
11. **How web text trains the model.** FineWeb-Edu enters as fill-in-the-blank rows: a chunk with one word of 3-12 letters
    blanked out (`cloze.py:1-25`), at most 280 letters in G1, and up to 2,000 letters in B3's long-chunk pool (`data_pool/cloze_long.py`,
    `job.py --cloze-long`). So the run teaches reading English, not writing it. These rows have no worked steps, so they train on the
    missing word alone (with a "no call" label at weight 0.1), as do 62.5% of the skills rows the 3M models trained on. **Ben, 1:20 PM ET
    10-09 (card "Allow", relayed by the coordinator):** one-word blank rows with no worked steps are fine under the no-answer-only rule; the
    rule is about rows that have steps or longer answers and lose them. Blanks of 9-12 letters need the 35-letter answer path (sec. 4). How the 25M talker learns to write English is not
    in the plan; your separate "talking from scratch" session owns that.
12. **The web pool has a gate.** It must not be used for training until the protected-panel hashes are merged and checked
    (DATA-POOL-PLAN sec. 6 and 10). The hash file waits on a Mac job.
13. **Depth has a known cost.** On one B2 probe, 16 rounds cost 1.2-1.9 points against fewer rounds (INPUT-UNITS-2026-10-07 line 31).
    The learned stop is meant to avoid paying it; the B3 readout reports rounds used. Open risk for the 100M run.

## 6. Being tested, and not in run-1

Being tested for run-1:
- **Tokens instead of letters** (Ben 9:30 AM ET: "experiment with doing tokens instead of just letters"; 9:44 AM ET he asked why
  the letter window matters). Test TK and TKN on the PC in the first gap, seed 400 first, kill-first, never delaying the B3
  ladder (`architecture/TOKENS-EXPERIMENT-2026-10-09.md`). Letters or tokens is decided before the 30M freeze.
- **ST1 as a training step** (keep its own checked tries for worked steps) is part of group 2.

Not in run-1 (later, planned):
- Learning new kinds after shipping, sleep it schedules itself, practice choice (fast-sleep and creative threads), and the
  domain mode (`domain-mode/DESIGN-AND-MARKS-2026-10-09.md`, which needs group 2's whole-call writer).
- More outside tools: a use-once puzzle tool and an example checker (`check <program>`), both planned for B3's tool loop
  (creative roadmap sec. 7b).
- The notebook as a recall tool it calls (creative roadmap 7b/7c). Saying "I don't know" (Ben's 09-28 goal) has no design yet.
- Reading text longer than 2,000 letters by carrying its vectors from one piece to the next (running-summary note, 10-08).
- Eyes, ears and hands for games (paused).

## 7. Questions for Ben (asked on cards 10-09; all three answered by 9:30 AM ET)

- **Q1. When can it call the calculator?** **Answered "Any time" by Ben, 9:30 AM ET 10-09.** Built in B3 group 1 (any_round)
  and tested in its 3M run, no extra test. The other choice was "First rounds": one call per round in the first 7 (later 16) rounds only.
- **Q2. How much text can it read at once?** **Answered "2,000 letters" by Ben, 9:29 AM ET 10-09.** Built in B3 group 1:
  `caps_b3.json` sets max_prompt 2000, so the learned position table has 2,000 rows, and the long-chunk pool supplies the long
  rows. G1 stays at 280 (`caps_g.json`). In a sample of 4,000 bAbI test questions (200 per task), 32% are longer than 280 letters,
  1% longer than 2,000 (task 3: 98% over 280) (shown, my count, Muennighoff/babi test split). The race needs "ahead on bAbI" (PLAN R4).
- **Q3. Keep the small letter window under Gemma?** **Answered "Keep" by Ben, 9:29 AM ET 10-09.** It is learned, and every reader
  without it lost letter puzzles (cipher_map 100% down to 2.5-10%, RESULTS-EG2). Ben then asked for tokens to be tried (sec. 6).

## 8. Older notes that disagree, and who was told

| Note | What it says | What is true | Owner |
|---|---|---|---|
| big-run PLAN sec. 2, 6 | thinker "about 30 blocks, width 512" | about 21 blocks at 512 for 100M (item 9) | big-run thread |
| big-run PLAN R2 | G1 alone proves the size bar | B3 must pass it too (item 7) | big-run thread |
| big-run PLAN sec. 6 | back-propagate through only the last few rounds | H1's code back-propagates through every round with checkpointing (`tool_h1.py:18-20, 68-71`); the PC fit check decides | big-run thread |
| redesign-ideas sec. 8b | H1 stops rounds "inside one turn", separate from the stop between calls | one stop for the whole answer (section 3) | architecture thread |
| no-hardcoding PLAN sec. 1, 5 | each call is a new turn that re-reads the question; "5-6 passes" per chain row | one pass; each reply is read as a short new string (section 3) | no-hardcoding thread |
| model-deep-dive.html | 17 thinker vectors, 8 rounds | 44 vectors (8 + 36) and 12 rounds in G1 after the caps fix. T1SDR/H1 at 17a356e62 also had 17 (9 registers written into the code); B3 fixed it to the caps' 36 | (page, dated 10-07) |
| custom-io/WHY-GEMMA-LOST-2026-10-06.md, custom-io/REPORT-custom-reader-talker.md, reader-talker-compare/verdict.md | earlier reader and talker conclusions | superseded (each carries a banner) | reader/talker thread, compare thread |
| whole-model roadmap, memory | the talker writes the calls | the call writer reads the thinker's control vector 0; the talker writes only the answer (section 2) | roadmap thread |
