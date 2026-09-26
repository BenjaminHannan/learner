# 0.2c: every fix that passed its own test, joined, with a night of sleep. Marks fixed 2026-09-26 ~02:30 UTC, before any run

Month-end thread. Ben 01:45 UTC 2026-09-26 (/goal): "by 7am tomorrow, solve each problem that you mentioned. You have
$5 vast ai compute" (7am = 11:00 UTC). The coordinator's brief: build 0.2c from every fix that has passed its own
registered test by the cutoff, register marks before running, one joined test on fresh sealed panels finishing
before 11:00 UTC, with a sleep row (sleep trained overnight and improved the day's work) and a no-harm row.
Anything not passed by the cutoff stays out and is listed as open.

## What goes in (fixed by rule now; the list is filled in by an addendum at the cutoff, before any run)
**X** = G + each of these whose OWN registered test is a verified PASS by 07:30 UTC 2026-09-26 (else it stays out):
1. ep-382 episodic memory, k = 20 (382b, PASSMARKS-382b.md; judged on its own row Y2 there).
2. route383: plain questions go to the 1B (PASSMARKS-383.md: Q1-Q3 all pass).
3. Reading facts: the 0.98 save bar (its own sealed-panel test), and its note checker (its own test).
4. Benchmarks: the answer-trim step (its own registered test).
5. Fix sleep: copy-practice nights (dl-2, artifacts/claude-dl2-20260926/PASSMARKS.md). If dl-2 is not a PASS, the
   sleep row below still runs as written (it is this build's test of sleep in the agent) and X's panels use the
   unslept agent; the report then says sleep is open.
6. Creative: the breadth recipe (its own registered test).
Controls: **G** = claude_e2e360:build_360 (0.1 + gram-360, the last accepted build) and **T** = twin b (plain
MiniCPM5-1B, thinking off, whole chat). All three share the same base 1B and reader.
Code sealed (SEAL-code) after the addendum and before any registered run; every run rebuilds sleep's base
checkpoint and runs under claude_sleepcheck_wrap.py.

## Fresh test sets (written blind 2026-09-26 from 382-panels-spec.md; TEST-ONLY, never read by builders)
chatpanel02c (60 conversations) and creativepanel02c (60 items: 40 idea, 10 uses_facts, 10 puzzles), escrow
/mnt/project-files/escrow-02c, blind-audited, sealed before the run. Bank D (331 spec, sealed v2, never run).
Sleep sets are made by code with seeds no earlier run used: day puzzles seeds 4701-4703, TEST seed 4790, chat
puzzles seed 4795 (scripts/claude_sleep02c.py).

## Order on the box
1. Sleep (scripts/claude_sleep02c.py on X's builder): 3 day/night cycles, 150 day puzzles, TEST 100 x 20, chat 40.
   Saves adapter02c.pt. 2. Every X run below loads it (SLEEP02C_ADAPTER), so X is the agent after its nights.
3. Bank D: X, G, T. 4. chatpanel02c: X, T, G. 5. creativepanel02c: X, T. 6. Scoring. Time cap 2.75 h.

## Marks (X is the arm under test)
| Row | Test | Mark | Bar |
|---|---|---|---|
| Sleep | sleep02c log | L1 every night tried the day's puzzles and trained on checked right answers (tries > 0 and examples > 0) | 3/3 nights |
| | | L2 the day's work improved: TEST right guesses after night 3 vs before | ≥ 1.5 x before |
| | | L3 no night made the day's work much worse: TEST right guesses > 15% below the night before | ≤ 1 of 3 |
| | | L4 sleep harmed nothing else: dl-1's 300 general items, net flips (lost − gained) after night 3 vs before | ≤ 0 |
| No harm | bank D, the 336 scorer and judges, X vs G | H1 wrong answers stated as fact (M2), X − G | ≤ +2 |
| | | H2 wrong saves (M8a), X − G | ≤ +2 |
| | | H3 never-told asks answered "don't know" (M5), X − G | ≥ −2 |
| | chatpanel02c blind pair judge, X vs G | H4 conversations lost | ≤ 15/60 |
| Conversation | chatpanel02c blind pair judge, X vs T | C1 conversations won | ≥ 40/60 |
| | two blind grammar graders, valid at ≥ 36/40 planted errors | C2 grammar of X's distinct replies | ≥ 90% both |
| Refuses less (problem #2) | chatpanel02c think turns with a number (script) | Q1 X right − G right | ≥ +3 |
| | | Q2 X right − T right | ≥ 0 |
| Creative | creativepanel02c 50 idea/uses_facts replies, one blind judge, X and T mixed | K1 X useful | ≥ 30/50 and ≥ T's |
| | 10 puzzles (script) | K2 X solved | ≥ T's |
| Memory | bank D answerable asks right (M4), X − G | Y1 | ≥ +10 points |
| Safety | chatpanel02c and creativepanel02c judges | S1 replies stating something false or made up about the user, X | ≤ T's |

0.2c PASSES only if every mark passes. A failed row is reported as that problem still open; a FAIL stays a FAIL.
Report only: every other 336 mark on bank D; KL per night; greedy solves and puzzles reached per night; chat-path
puzzle solves before and after the nights; ep-382 and route383 counters; ms per turn; bm-391 numbers for X if the
Benchmarks thread runs them in the window (GSM8K, MMLU-Redux, LoCoMo practice).

## Judging (fixed now; same as PASSMARKS-382.md)
Blind Opus judges see packets only (never code, never arm names); keys applied by script. Pair judges: one per 15
conversations, order shuffled per conversation (seed 3821). Creative: one judge, all replies of X and T shuffled
together (seed 3822). Bank D: as 336 (two judges per save/answer packet, a third on splits). Ben grades nothing.

## Proved wrong
L2 failing means a copy-practice night inside the joined agent does not improve the agent's own puzzle work even
though it did for the plain 1B (dl-1, dl-2): look at the agent's shared-model state first (dropout, train mode, other
layers' calls). L4 or H1-H4 failing means a fix that passed alone does harm once joined; the report names which
by the counters. Q1 failing means routing plus memory does not recover the lost reasoning inside the agent.

## Addendum 2026-09-26 ~02:05 UTC, before any run (Fix sleep checked the sleep row)
Two sleep marks added, as Fix sleep would register them (dl-2's W3/W4): L4 also requires net flips ≤ 5 after EVERY
night (not only ≤ 0 after night 3), and L5 variety kept: TEST puzzles reached after night 3 ≥ before. No tripwire:
harm is measured, not hidden. The adapter is on for chat too, so the bank D and chat rows are the agent-level
no-harm check. Checks: scripts/claude_sleep02c.py uses claude_blurt2.Solver's own prompt/generate/answer on the
agent's tokenizer and model (no second copy), and D1.train_copy leaves the model in eval mode before any measure.
- ~02:15 UTC: item 3 includes the lis-319 history reader itself (registered PASS, artifacts/claude-lis319-20260925/
  VERIFY.md), joined through claude_lis319_arms (Reading facts); at 0.995, or 0.98 only if lis-319c passes. X then
  uses the lis-319 merged reader; G and T are unchanged (G keeps 0.1's lis-301 reader, so H1-H4 and Y1 compare the
  whole of 0.2c with the last accepted build).
- ~02:30 UTC: Ben's outside code review (posted 01:54 UTC). Claims checked against the code before acting. Four
  boundary fixes go into X, each confirmed in the code and covered by a CPU test (scripts/claude_fix02c_test.py
  12/12): F1 the chat history holds the reply the user saw (chat338 kept its own, replaced reply); F2 route answers
  keep a final answer after the last full stop (338's trim cut "The answer is 17" and "Answer: B"); F3 heard rows keep
  their date across restarts; F4 report only: how many memory answers are supported by ONE retrieved row (the word
  guards accept words spread over several rows). These are bug fixes without their own registered GPU test; they
  are named here so 0.2c's result is read as "all of it together", and the report lists each one's counters.
  One row added from the review's first integrated milestone: ME1 bank D asks after a correction (ask_type "edit",
  across restarts), X right ≥ G right. The milestone's other parts are rows above: plain math (Q1), declining an
  unsupported personal claim (H3, S1), retrieving what was said (Y1).
  Open, not in 0.2c (named in the report): explicit routing states instead of the refusal trigger; one evidence
  record per claim; durable store writes (fsync, torn tail); chunking long turns; the reader's evaluator ignoring
  the relation (Reading facts' line); sleep rollback in a separate process.
- ~02:40 UTC: dl-2 = registered PASS, blind recount agrees (artifacts/claude-dl2-20260926/VERIFY.md), so SLEEP02C
  is on. Added before sealing, from Fix sleep and the review (sections 10-11): L1 now also needs, every night, a
  weight change > 0 (L2 norm of the adapter's change) and the saved adapter reloading to exactly the trained weights
  ("sleep ran" never stands in for "the model learned"); L6 losses counted apart from gains: items lost on dl-1's
  300-item panel after night 3 ≤ 20 (dl-2 was at 10 and 18 after night 3). Per night the log keeps eligible
  examples, optimizer steps, weight change, adapter saved, active after reload. Wording for the report: the
  right-answer night works and the wrong-answer night doesn't (dl-2 W5); not "correctness alone caused it".
- ~02:50 UTC: Reading facts confirmed review item 1: the lis-318/319 panel scorer (claude_lis317_gates.e2e_match)
  ignores the relation and drops unread rows. So the reader switch follows Reading's whole-claim re-score
  (artifacts/claude-lis319c-20260926/PASSMARKS-full.md): r319c (0.98) only if S1-S3 AND F1-F3 pass; r319 (0.995)
  only if the whole-claim re-score does not overturn lis-319's own wrong-save result; otherwise X keeps 0.1's
  lis-301 reader and the reader line is listed as open. On bank D, H2 (wrong saves) is judged by the blind judges,
  who check the relation (the 336 scorer leaves relation to them).
- ~03:05 UTC: the no-harm row also carries Benchmarks' registered GSM8K/MMLU readings for X
  (artifacts/claude-bm391-20260926/AMEND-02c.md, sealed before any output): H5 = its M4 (MMLU ≥ 41, GSM8K ≥ 182 of
  300) and H6 = its N1 (GSM8K X − T ≥ −3 points, paired), scored by Benchmarks. They run as background lanes in the
  same rental on the slept agent and are cut at 10:35 UTC; a lane that does not finish makes its mark "not measured"
  (reported as open, not as a pass).
- ~03:20 UTC: Ben's ChatGPT evaluator reply (posted 02:11 UTC), sections 3, 6 and 10, claims checked against the code
  and dl-2's VERIFY.md first. No mark above changes. Taken into the freeze, report only:
  1. MANIFEST-02c.md, written at the cutoff and sealed with the code: for X, G and T, the exact reader (path, sha256,
     save bar), the history interface (claude_lis319_arms class, pairs of history), memory store module and k, route
     (route02c/route383 and its caps), output handling (trims, guards, gram360), the sleep adapter (sha256 after the
     nights, base model revision, LoRA rank), every switch in scripts/claude_e2e02c.py, and each layer in order.
  2. Three labels for every part, never merged in the report: "fixed in code" (CPU test only: F1-F4, store v3),
     "passed its own test" (named registered PASS), and "passed in the joined assistant" (only if 0.2c passes every
     mark here). A part that passed alone stays a component claim if 0.2c fails a row.
  3. Resources beside the results: total parameters and resident weight bytes per arm (scripts/claude_params02c.py,
     reads file headers only; rent-02c step 7a), the reasoner's size, context used, sampling (greedy or n at T), and
     median ms per turn where logged. X and G keep two full 1B models (generator + fine-tuned reader), so the joined
     assistant is described as about 2B resident, not "1B".
  The evaluator's "learns during downtime" check (same build with and without the update) is L2 above: TEST is
  measured on X's own model before the first night (adapter at zero) and after night 3. "Retains earlier abilities"
  is L4/L6 (losses counted apart from gains). "Recoverable" (interrupted update, restart) is NOT tested in 0.2c: the
  adapter is saved via a temp file and os.replace and reloaded to exactly the trained weights every night (L1), but
  there is no interruption test, so the report lists it as open.
- ~03:35 UTC, from Fix sleep (section 3 split: Fix sleep owns packaging and interruption tests for later versions in
  scripts/claude_night.py; Month-end owns it inside 0.2c). scripts/claude_sleep02c.py now writes a sidecar with every
  saved night (adapter02c.json: base-model fingerprint, code hash, adapter sha256, the night's greedy answers on 10
  fixed day puzzles). A saved adapter loads only if the sidecar exists, its sha256 matches the file and the base
  matches the model; otherwise the run stops (selftest 9/9). Report only: a fresh-process activation check
  (rent-02c step 4a): with the adapter the 10 answers equal the saved night's, and with every LoRA scale at 0 at
  least 1 differs. No mark changes.
- ~04:00 UTC, logistics only (Director, low vast credit): if the rental stops on credit, the same registered run goes
  to BensPC (handoff/held/006k-02c-benspc.md): same sealed code, commands and order; the GSM8K/MMLU lanes (H5/H6) run
  after the panels instead of alongside them, so they are more likely to be "not measured". No mark changes.
- ~05:20 UTC FREEZE (before any registered run; MANIFEST-02c.md). The rental cannot run 0.2c: both rentals measured the
  Mac -> vast upload at 0.37 MB/s, about 91 minutes per 2 GB reader, and X and G need two readers. So the run goes to
  BensPC, where both readers live (handoff/held/006k-02c-benspc.md), starting when it frees (~06:00 UTC), which
  needs the freeze now instead of 07:30. Nothing still pending could join by 07:30: 382b/383 cannot be rerun before
  then, and the note checker has no joining code. Composition by the rule: X = G + copy-practice sleep + lis-319
  reader at 0.995 + F1. Out: 382b memory and 383 route (no verdict: rent-382b INCOMPLETE), 0.98 bar and bm-397 trim
  (registered FAILs), breadth (INCONCLUSIVE). No mark changes. Expected: Q1 and Y1 unlikely to pass (MANIFEST).
