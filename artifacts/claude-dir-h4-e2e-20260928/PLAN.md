# H4 plan: the first end-to-end test with learned parts (audit, minimal build, sealed test, blockers)

Helper H4, 2026-09-28T19:16Z (`date -u`). Read-only audit of the repo clone plus these two files (PLAN.md, PASSMARKS.md). No model was run: this box has no torch,
and nothing was trained. Labels: **shown** = I read it in a file (path:line given), **suggested** = fits the evidence, **untested** = nobody has run it.
Ben's goals page beats my framing. The small card experiments and the village model are kept out of every claim.
I never opened readpanel320 or any TEST-ONLY panel. The older fable-talker line (talker24/101/120, "contract statuses") belongs to the earlier village-style
system and is not used here.

## 0. Headline (plain words)

1. **Nothing has run end to end with learned parts (shown).** The joined build scripts/claude_e2e02d.py says "nothing has run" (ADDENDUM-52) and its slots
   (reader, reasoner, sleep) are empty (claude_e2e02d.py:76-80). I found no sealed 358b3 marks and no 358b3 result anywhere in artifacts/.
2. **The chain is not a chain yet (shown).** On chats shorter than 12,000 characters the talker reads the user's raw earlier turns (claude_e2e02d.py:224-236, 84).
   The reader's saved facts go only to a fact book and to notes that are pointers (:319-323), and the fact book is never shown to the talker. So the reader
   does not change the reply on short chats. The reader also has no way to hand a puzzle to the reasoner: the square is found by a hand-written parser (:290).
3. **Three formats, no shared one (shown).** Reader out = a JSON frame of facts. Reasoner in = grid tokens for one kind of puzzle. Talker in = plain text with a
   fixed note. Details in section 1.
4. **Learned parts that exist:** the reader (lis-320, still training), the square copier gr-9 L9 (practice DEV-FAIL, sealed-panel untested), the loop reasoner
   (358i3 PASS, 358u kind-free PASS), the frozen LFM talker. **Not learned in any current path:** deciding "this is a puzzle", the "I don't know" (a prompt line;
   y1t trained doubt was NO-GO and proved wrong), the reasoner's "am I sure" (a code check), and the reasoner's stop rule (hand rule in the 358a2 code).
5. **Smallest build that obeys the rule:** 0.2d's shape plus four small glue pieces (section 3). Biggest model inside 1.2B (LFM talker), total about 2.3B.
6. **Sealed test:** 60 lives, code-made truth, Luna-worded, 11 registered marks, three plain twins, four ablations (PASSMARKS.md). GPU jobs go through the queue.
7. **Biggest gap:** the parts do not share one interface, and the puzzle reader that would make the chain fully learned is not yet a passing part. Blocker order in section 5.

## 1. What each part reads and writes today, and where the interface gap is

### 1.1 Reader (lis-320 line)
- **Shown:** `Reader319.read(turn, prev_reply, history)` returns `(frame, confs, raw_text, ms)` (scripts/claude_lis319_read.py:31-56). The frame is JSON text
  `{act, facts:[{owner, rel, value, mode}]}`; `confs[i]` is the lowest token probability of fact i. A fact is saved only if
  `claude_lis300_compiler.check_fact` finds no structural problem (mode allowed, relation on a closed list of 153 names, owner and value are whole-word spans
  of the turn or the previous reply, scripts/claude_lis300_compiler.py:39-62) and conf >= 0.995 (scripts/claude_lis319_fullclaim.py:48-54).
- It reads facts about people. It has no square, no question, no sum output (shown: the frame has only facts).
- **Status:** lis-320 data sealed (artifacts/claude-lis320-20260926/DATA.md); the rental job was released 2026-09-28T13:26Z
  (handoff/queue/claude-lis320-vast-20260928-mac.md); the repo has no RUN-START.md, END.json, weights or panel result yet (searched). Caller says it is training.
- **Alternative reader, not in the build:** the vector reader "vread" (cards of pointers into the prompt, 9,281,982 trainable weights, 18 ms/turn vs 1,130 ms for
  the LoRA reader) is FAIL (V2, V3 backref) (artifacts/claude-vread-20260927/RESULTS.md); vread2 (crediting any copy of the name) is INCONCLUSIVE
  (artifacts/claude-vread2-20260928/RESULTS.md, validity mark failed). Wrong-person picks stay ~16 of 41 rival-named backref cards
  (artifacts/claude-vread-wrongperson-20260928/DIAGNOSIS.md section 2). Nothing joins the build.

### 1.2 Square reader (the piece that turns a chat message into the reasoner's input)
- **Hand-written today:** `read_latin` finds s consecutive lines of s cells (scripts/claude_puzzle_reader.py:30-35, def at :69); 0.2d calls it on every turn
  to decide both "is there a square" and "what is it" (claude_e2e02d.py:287-292).
- **Learned candidate:** gr-9 L9, a rank-16 LoRA on the MiniCPM 1B that copies the square as rows with `_` or writes `none` (scripts/claude_gr5.py:1-12,
  scripts/claude_gr9.py:1-30). **Shown, practice data only:** held-out layouts 94 of 100 exact (L7: 44), lookalikes read as a square 5 (L7: 8), but
  practice squares 197 of 200 (bar 199) and seen-separator 97 of 100 (bar 98): DEV-FAIL (artifacts/claude-gr9-20260927/RESULT-gr9.md). No sealed panel, no PASS.
- The plain 1B cannot copy a square (drops `_`): 25/39/28 of 100 exact (artifacts/claude-rsn358b2-20260926/VERIFY-recount.md).

### 1.3 Learned reasoner
- **Consumes (shown):** a grid of integer tokens, `BLANK=0, MASK=1, digits 2-11, SYM=12..20 (nine anonymous symbols), ops, values`, vocabulary 125
  (scripts/claude_rsn358a_envs.py:33-40). A chat square becomes `tokens = SYM+v-1 for a clue, MASK for a blank`, plus two legend rows, with a slot mask
  (scripts/claude_rsn358b2_bridge.py:102-114, the "358b3 bridge" grid format). The unspecified kind label is a learned embedding added to every cell
  (claude_rsn358a_run.py:97,172 per ADDENDUM-43); rsn-358u's nets get one fixed constant instead (scripts/claude_rsn358u_run.py:1-20,39-42), so the kind must
  be read from the puzzle itself.
- **Produces (shown):** a token per cell each round; `LoopSolver.solve` takes the stop round from a hand rule (`stop_round`, scripts/claude_rsn358a2_run.py:27,
  "3 steady rounds") and returns the filled grid plus rounds (bridge :117-146). Code then checks the grid against the copied square (`is_solution`, :92).
- **Never consumes:** a fact, a question in words, or a notebook line. It has no interface to the reader's frame (shown: nothing in the code passes
  reader output to `solve`).
- **Status (shown):** loop beats same-size plain twin, kind told (358i3 PASS, artifacts/claude-rsn358i3-20260926/VERIFY-recount.md) and kind not told
  (358u PASS, artifacts/claude-rsn358u-20260927/RESULTS.md: sums6 298 vs 154, grids6 291 vs 250 of 300; 358u2 re-run nets: grids5 300, grids6 292.75,
  grids7 208.5; "NOT ACCEPTED" for slp-358n3 only because grids7 left its band, artifacts/claude-rsn358u2-20260928/RESULTS.md). Number puzzles: 0-3 of 300 in all
  nets. Size: 6.44M loop (2 x d512) vs 6.39M plain (358i3 recount).
- Only Latin squares are wired to chat (ADDENDUM-24 audit; Redirect stops sum puzzles in chat). No word reasoning exists (Ben: ordinary word questions
  start right after 358b3 passes).
- **First chat try (shown):** 358b2 put the 1B in the middle and failed on copying (copy exact 25/39/28 of 100, INCONCLUSIVE). The 358a net solved 100/95/71
  when the square reached it intact (ceiling C). That is why the reader must copy, not the plain 1B.

### 1.4 Talker
- **Consumes (shown):** a chat-template with a system message `TW.SYSTEM + reasoner note + "User said, ..." lines`, and the last 6 (user, reply) pairs
  (claude_e2e02d.py:249-260,299-314; claude_e2e336_twin.py:15-21). **Produces:** free text, greedy, at most 160 new tokens, thinking off, `<think>` stripped.
- Model: plain LFM2.5-1.2B-Instruct at revision 0f604ada... (ADDENDUM-51; was MiniCPM). Untrained. No adapter loads (ADDENDUM-46/49).
- The reasoner's result arrives as "Reasoner result ... (checked): rows" or "no square fits its clues" (claude_e2e02d.py:240-246). The talker must retell the
  rows. Whether LFM retells them faithfully is **untested** (358b2's 1B copy failed; retelling a checked grid was scored there only as "reply faithful").

### 1.5 The gap, in five lines
1. Reader -> reasoner: **none**. Puzzle reading is a separate reader (hand parser or gr-9).
2. Reader -> talker: only through pointer notes; in whole-chat mode (chat < 12,000 characters) the talker ignores the reader completely.
3. Notebook -> reasoner: none. The reasoner cannot use a remembered square or fact.
4. Reasoner -> talker: a fixed text frame; the talker retells; nothing checks the retelling.
5. "I don't know": prompt line only (claude_e2e336_twin.py:19-20); DOUBT02D = "" (claude_e2e02d.py:80). y1t trained doubt: NO-GO on its own DEV (22 right, 20
   wrong candidates, 5 of 10 never-told; artifacts/claude-y1t-20260926/VERIFY-y1t.md) and proved wrong on corrections (y1t-H1 VERIFY). mu-406 has no verdict in the repo.

## 2. Learned parts vs hand-written stand-ins in each joined path

| Path | Reader | Square finder | Reasoner | Check / "don't know" | Talker | Notebook |
|---|---|---|---|---|---|---|
| 0.1 / 0.2c rule builds (claude_e2e02c.py etc.) | lis-319 + many rule layers | rule routes | hand-written reasoner (Redirect stops it) | rules, stock lines | 1B + templates | rules |
| 358b2 bridge (claude_rsn358b2_bridge.py) | none (1B copies) | 1B copy (failed) | learned loop 358a | code check, fixed "couldn't" sentence (:51) | 1B | none |
| 358b3 (sealed marks not found) | - | rt-02g-style pattern / read_latin | 358i loop | - | - | - |
| 0.2d (claude_e2e02d.py, unsealed) | lis-320 (learned; rules inside its gate) | **read_latin (hand)** | learned loop, **kind told, hand stop rule** | **code check; prompt "I don't know"** | LFM (plain) | store v4 + fact book (hand supersession) |
| 0.2d-G (claude_e2e02d_g.py) | same | same | same | same | same | + rd-378g notes (learned, ~49% unsupported by the judges) |

### Hand-written pieces that would break Ben's rule if they stayed in the build
(Rule: "would this piece still exist in Ben's design?", ben-goals-2026-09-26.md:39.) Each is on the path in claude_e2e02d.py.
1. **P1 read_latin as the square detector and reader** (:30, :290; claude_puzzle_reader.py:69). It decides "is this a puzzle" = hand routing. Replace by the learned copier.
2. **E1 kind label** fixed to "grids" by the bridge (:31; bridge :102-114). Use kind-free nets (358u line). Ben ruled caller-given kind labels out (ADDENDUM-43).
3. **P3 stop rule** "3 steady rounds" (:37; claude_rsn358a2_run.py:27). Director roadmap item 2 says the race baseline has a learned stop and cap 48; I did not
   verify that the 358u nets use it (untested). Report which stop rule each net uses.
4. **C1 code verifier** as the only reason the reasoner ever says "no square fits" (:38, :287-296; bridge :92). It works as a problem-specific answer gate.
   Allowed only as disclosed scaffolding; learned counterpart (the reasoner's own confidence) is owed.
5. **Prompt-only "I don't know"** (claude_e2e336_twin.py:15-21, Claude-written instruction). Fine as a disclosed fixed line in a test (Ben, 16:50 UTC "Count it"), but
   the learned doubt is missing (y1t NO-GO).
6. **F1 newest value wins** in the fact book (:45, FactBook :100-135). It does not reach the talker today; if its lines were shown to the talker it would be a
   hand supersession rule. Plan avoids it (show facts in time order with sources; the talker resolves).
7. **Reader gate rules:** closed 153-name relation list, owner/value must be spans, pronoun-owner refusal, threshold 0.995 (claude_lis300_compiler.py:39-62, :23). Kept
   inside the reader and scored under H-R (ADDENDUM-24), but they cap what can be saved (DEV cap 103/131 for a perfect reader, 370-reading-roadmap.md).
8. **D15 date regex** DATE382 (claude_e2e382.py:45; used at claude_e2e02d.py:301). Only stamps rows. Drop it for this test (no dates in the panel).
9. **N0 note text** = "owner rel value" join (:47, :322). Mechanical; the learned note writer G exists but half its notes are unsupported. Keep N0 (no generation).
10. **H1 hand-off frame** (:39-42, 240-246). An interface, not reasoning. Allowed, disclosed; learned counterpart (a talker that reads the reasoner) is owed.
11. **W length switch** (12,000 characters, :48, :84). Mechanical.
Not violations (mechanical): grid-text-to-token conversion (bridge parse_grid :75, item_of :102), THINK-tag stripping.
In the older paths, the rule layers listed in ADDENDUM-24 (stock lines, templates, 292t question reader, think299, confirm rows, guards) already left the plan.

## 3. The minimal end-to-end build (small scale, principles only)

Shape: 0.2d as drafted, with the reader put into the causal path, a learned square reader in place of read_latin, a kind-free reasoner, and source display.
Sleep and the always-on reasoner are out (Ben: next version; ADDENDUM-46 moved sleep to the reasoner). This is a small-scale demo of principles, not an assistant.

### 3.1 Components and sizes
| Part | Model | Size | Status / label |
|---|---|---|---|
| Reader | MiniCPM5-1B (rev 87179e5c) + lis-320 LoRA rank 32, merged | about 1.1B base (vread RESULTS "frozen 1.1B"); LoRA 22,413,312 weights (that count is for the same recipe in vread's LoRA arm) | lis-320: training / not landed |
| Square reader | same base + gr-9 LoRA rank 16 (q,k,v,o) | adapter size not counted (untested) | DEV-FAIL on practice data |
| Reasoner | loop net, 2 shared blocks d512, kind-free (358u code) | 6.44M | 358u PASS; 358u2 nets on Mac (4 of 4 hash-checked) |
| Recall | frozen MiniLM-L6 + BM25 in store v4 (claude_ep382_store_v4) | about 22.7M (my figure; not in the repo) | in use since 0.2 |
| Talker | LFM2.5-1.2B-Instruct, plain | 1.2B | pinned, untrained |
- **Biggest model inside: 1.2B (the talker). Total: about 2.3B** (1.1B + 1.2B + about 0.06B of small parts). If the square reader keeps a separate copy of the base
  instead of swapping LoRAs on one base, the total is about 3.4B. State both (goals page "Counting size"). Rivals: MiniCPM5-1B, Qwen3.5-2B (covers both counts),
  LFM2.5-1.2B.
- Memory at run time (arithmetic, untested): about 4.6 GB in bf16 for the two 1B-class models; it fits the 16 GB RTX 5070 Ti on BensPC (ADDENDUM-28).

### 3.2 How the notebook and "I don't know" fit
- **Notebook (Ben's hippocampus):** store v4 keeps every user turn word for word (claude_e2e02d.py:316-317) and the reader's facts as note pointers to their turn
  (:319-323). Exact recall = the raw turn comes back with the fact. That is the "word-for-word source".
- **Change 1 (make the reader matter):** the talker's memory block lists, in time order, the facts the reader saved for the entities in the question (top-k by MiniLM over
  notes), each as `fact line + "source: <verbatim user turn>"`, and the store's top-k raw turns; the whole-chat dump is switched off for this test
  (CTX_CHARS02D = 0). A fact the reader missed can still come back as a raw turn, so this cannot make recall worse than raw retrieval. (Suggested; untested.)
- **"I don't know":** stays the fixed instruction line plus an empty memory block (S5). The provenance check S6 attaches a source turn to an answer only when the source
  is a verbatim substring of the chat and holds the stated value; an answer whose value has no such source is turned into the fixed sentence "I don't know." This
  check is on Ben's "carries on" list (goals :38, notebook "word-for-word provenance check"). Reported both with and without it.

### 3.3 The smallest NEW glue (all in scripts/claude_dir_h4_*.py, not written yet)
| # | Glue | Learned or scaffold | Why it is needed |
|---|---|---|---|
| G1 | `Agent_E2E` (subclass of claude_e2e02d.Agent02d): runs L9 on every turn; if it returns rows, parse (S1), call the kind-free `LoopSolver`, check (S2), build the H1 note; if `none`, no reasoner call | detection = **learned** (L9 says grid or none); parse, check, note = scaffold-mechanical | removes read_latin as the detector |
| G2 | thought serializer: fact lines + verbatim source lines for the recalled facts, time-ordered; replaces "User said" dump | scaffold-mechanical (a text template, no decisions) | puts the reader's output in front of the talker |
| G3 | provenance appender / checker (S6): substring test on the reply and the retrieved turns | scaffold, allowed by Ben's list, disclosed | word-for-word source, and the only rule that turns an unsupported answer into "I don't know" |
| G4 | kind-free loader: `LoopSolver` with the fixed env of scripts/claude_rsn358u_run.py:39-42 (a flag, ~5 lines) | learned net, mechanical loader | E1 removed |
| G5 | test tooling (not the build): panel maker (code truth + Luna wording jobs), multi-arm runner over lives, scorer + selftest, blind-recount script | tooling | sealed test |
Existing code reused unchanged: claude_e2e02d.py (Talker, FactBook, w_rows), claude_lis319_read.py, claude_gr9.py copier, claude_rsn358b3_panel.py `final_grid`/`score_panel`
(the answer-read rule), claude_e2e336_score.py (RIGHT / WRONG_CANDIDATE), claude_bmriv_rivals.py (rivals), claude_e2e02d_d0.py (DEV health counts).
Nothing the model must learn is added by glue. If L9 fails the sealed test, the fallback for the whole build is NOT read_latin (that is a hand-written route);
the honest fallback is "the reasoner is tested given the grid" (arm J-scaf), reported in those words (goals page :40).

## 4. Sealed end-to-end test design (marks: PASSMARKS.md)

- **Panel:** 60 lives (two seeded halves of 30), fictional names, code-made facts/puzzles/labels, wording by Luna (or GLM), never Claude. Squares appear in several
  layouts, half of them unseen by gr-6/7/9 training. Counts: 20 + 20 + 10 solve squares (5x5, 6x6, 7x7 report-only), 12 broken squares, 12 square lookalikes, 20 number
  lookalikes, 60 answerable asks (15 corrected, 15 owner-named-earlier), 30 never-told asks, 40 small-talk turns. Sealed by sha256 before any arm runs. Truth in a
  file no runner opens. Judged replies: code first (unchanged 336 scorer and the 358b3 final-grid rule); flagged replies to two blind judges; a separate
  subagent recounts from raw files.
- **Pass marks written now** (PASSMARKS.md, timestamp 19:16Z): E1 >= 30 of 40 squares right with each of two nets; E2 at least 10 above the best of three plain twins;
  E3-E5 no wrong squares, honest on broken squares, few false fires; E6-E8 memory, sources and "I don't know"; E9-E10 the reasoner and the reader each add;
  E11 sanity. Validity: lis-320 H-R PASS, ceiling arm J-C >= 34 of 40, panel counts, blind wording check.
- **The result that proves it wrong:** J no more than 3 above the best twin on squares, or J-noR within 5 of J, or J-noRd no worse than J on memory while J is more than
  3 below the best twin. Each is stated in those words. Most at risk (suggested): E6 memory, because the plain 1B used the memory block on 4 of 60 direct asks in the
  system-message form (mu-405).
- **Comparison against a plain twin:** T-LFM (same talker weights, same instruction line, whole chat as history) is the primary twin; T-MCP and T-QWEN (thinking off;
  thinking on report-only) run through the bm-riv harness; the 8,192-token cap on square turns follows 358b3's sealing. Ablations J-noR, J-noRd, J-scaf, J-C isolate
  each learned part (one change each).
- **Two seeds:** two panel halves, two loop nets (s13, s14, named before the run); the reader is a single training run (limit, said in the report).
- **What runs where:**
  | Step | Where |
  |---|---|
  | glue code, panel maker, scorer, selftests, wiring on stubs, blind recount | this CPU box |
  | Luna wording of the panel; V5 wording check | Director's Codex/Luna path (Mac) |
  | J, J-noR, J-noRd, J-scaf, J-C; T-LFM, T-MCP, T-QWEN | GPU via handoff/queue (BensPC RTX 5070 Ti, one job at a time, or the Mac watcher); no rental unless Ben says yes |
  Rough GPU time: about 600 turns per arm; suggested 1-2 h per J-type arm and less per twin, with Qwen's long replies the main risk; about 8-13 GPU hours is the 0.2d
  estimate in ADDENDUM-28 (a guess, not measured). Queue files: written by the Director from my folder as queue-<name>.md once the panel is sealed; none written yet.
- **Not in this test:** sleep, the always-on reasoner, sums/number puzzles in chat, a learned "I don't know", word reasoning, a puzzle spread over two turns (the notebook
  feeding the reasoner). Stretch test after this: give the square in one turn and ask for the solution three turns later.

## 5. Blockers, owners, and the order to unblock

| # | Blocker | State (checked 2026-09-28) | Owner | Blocks |
|---|---|---|---|---|
| B1 | lis-320 reader weights and its H-R verdict (matches lis-319f on readpanel320) | rental job released 13:26Z; no weights or verdict in repo | reading thread / Director; Ben's Mac | V1; the whole J arm |
| B2 | Sealed panel + Luna wording | not started; needs the Director's Codex/Luna path to pass its probe (goals :112) | Director (Luna), H4 (spec) | everything after |
| B3 | Reasoner net choice and its stop rule | 358u originals not copied back (rent358u-4d held); 358u2 nets verified on Mac, NOT ACCEPTED for slp-358n3 but usable; stop-rule source unverified | sleep research / Director | E1, V3 |
| B4 | Learned square reader | gr-9 L9 DEV-FAIL by 3 items in two sets; no sealed panel; rt-02h learned "is it a puzzle" head FAIL | plain-English-puzzles thread | learned chain; fallback = J-scaf |
| B5 | 358b3 (learned reasoner in chat) has no sealed marks in the repo | this test would cover the same ground; the Director should decide whether E1 replaces 358b3 as H-A | Director / Ben | headline gate wording |
| B6 | Glue G1-G5 | not written (this folder holds only the plan) | a builder helper after the Director's yes | dev rehearsal |
| B7 | Faithful retelling by the LFM talker | untested; 358b2's 1B copying failed | E2E test measures it; if bad, a talker adapter that reads the note is owed (allowed by ADDENDUM-49) | E1 |
| B8 | Memory use by the plain talker | mu-405: 4 of 60; mu-406 no verdict found; y1t NO-GO | making-things-up / answering-from-memory threads | E6, E8 |
| B9 | Rival runs on the same panel | bmriv harness exists; needs GPU slot | Benchmarks helper via queue | E2, E6, E8 |
Not blockers for this test: **vread2** (INCONCLUSIVE; a faster reader for later; do not wait), **numbers puzzles** (H2; only needed for a second kind), **sleep**
(slp-358n3, distill test), the patch and relation-net races (a better reasoner can be swapped in later; the harness takes any checkpoint plus its format).

**Order (suggested):**
1. Now, no GPU: write the panel spec/seeds and the wording jobs (B2), the glue and the scorer with stub selftests (B6), and pre-name the reasoner nets by the rule in PASSMARKS (B3).
2. In parallel, owners finish lis-320 (B1) and settle gr-9's status (B4). Do not wait for either to build the harness.
3. Seal the panel blind to every model (B2), then the DEV rehearsal of 6 readable lives (wiring, memory, no marks).
4. Run J-C and J-scaf first (they need no lis-320 verdict beyond the loader), then J and the ablations as lis-320 lands, then the twins.
5. Blind recount. Report as PASS / FAIL / INCONCLUSIVE / PRE-GATE.
6. Afterwards: swap in a better reasoner if the races produce one; add sleep; add the two-turn square.

## Evidence index (paths)
scripts/claude_e2e02d.py (:30-48 stand-ins, :76-84 slots, :224-260 talker input, :287-323 turn); scripts/claude_lis319_read.py:31-56; scripts/claude_lis319_fullclaim.py:48-54;
scripts/claude_lis300_compiler.py:23,39-62; scripts/claude_puzzle_reader.py:30-35,69; scripts/claude_gr5.py, claude_gr9.py; scripts/claude_rsn358a_envs.py:33-40;
scripts/claude_rsn358b2_bridge.py:51,75,92,102-146; scripts/claude_rsn358u_run.py:1-20,39-42; scripts/claude_rsn358a2_run.py:27; scripts/claude_rsn358b3_panel.py;
scripts/claude_e2e336_twin.py:15-21; scripts/claude_bmriv_rivals.py; design/v3/30-modes/02d-gates-ADDENDUM-12,18,24,29,31,43,46,49,50,51,52;
ben-goals-2026-09-26.md:35-41,74-84,86-88; artifacts/claude-lis320-20260926/{DATA,PASSMARKS,ADDENDUM-13,14}.md; artifacts/claude-vread-20260927/RESULTS.md;
artifacts/claude-vread2-20260928/RESULTS.md; artifacts/claude-vread-wrongperson-20260928/DIAGNOSIS.md; artifacts/claude-gr9-20260927/RESULT-gr9.md;
artifacts/claude-rsn358i3-20260926/VERIFY-recount.md; artifacts/claude-rsn358u-20260927/RESULTS.md; artifacts/claude-rsn358u2-20260928/RESULTS.md;
artifacts/claude-rsn358b2-20260926/VERIFY-recount.md; artifacts/claude-panel-rsn358b3-smoke-20260926/NOTE-scorer-smoke*.md; artifacts/claude-y1t-20260926/VERIFY-y1t.md;
handoff/director-roadmap.md; handoff/queue/claude-lis320-vast-20260928-mac.md.
