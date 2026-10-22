# Facts pack for the creative-prototype redo (2026-10-03)

All paths below are local copies in this folder or in the repo at /home/user/learner (read-only for you).

## Task
Ben (high-school senior, project owner) approved a "creative prototype": a worker attempt, then varied complete candidate
solutions, checker acceptance, then verified TRAIN experiences. His rules: sampling alone is not learned creativity; gold
scoring is not unknown-live verification; claims never exceed evidence; fresh, independently checked evaluation with pass
marks fixed in advance; one change at a time; never inspect reserved user/blind panels; consumed panels never reused for
training, tuning or a claimed fresh score; learned stopping, compressed notes and n-grams are out of scope; no unrelated
generated-code/data training. The design must show the model learning to generate better candidates from verified
experiences, measured on fresh problems, with controls (plain sampling, no creative training). It connects to a later
sleep-replay part. Ben (10-03 12:09) removed the approval need for scaling and extra loops and gave broad autonomy:
where something makes sense but a rule technically says no, use judgment and say so. Ask only before spending >= $0.50,
deleting unique data, reusing consumed/reserved evaluation, or anything irreversible.

## Current system (source: integrated-design-v6-text.txt = the integrated design doc, plus CURRENT.json)
- Frozen LiquidAI/LFM2.5-1.2B-Instruct gives language components. Reader (static lexical or contextual causal states, thin
  trainable adapter) -> ~9M core (2 shared blocks, 8 experts top-2), fixed 4 loops -> 8 learned 2048-d prefix vectors ->
  frozen LM decodes the final answer from prefix + BOS only (it does not see the question).
- Calculator protocol (v6 text ~lines 76-86): on every loop the reasoner chooses no call or a typed request (allowed op,
  ordered operand references, call id). At most one call per loop, four total. Host validates and returns exact result or
  structured error. Domain: addition and subtraction, supported two-digit single-token results. Pointers can select
  earlier successful results. Shared heads choose action and ordered operand pointers. The first policy reads initialized
  state plus input features before any core advance. Training: checked supervision requests the correct calculation until
  it succeeds, then targets no call; final-answer loss plus averaged call cross-entropy.
- IMPORTANT: the calculator-pipeline source code is NOT in the repo (runs on Ben's Windows PC). Code-level claims about it
  are unverified; the v6 text is the source. PR #23's design (pr23-design.md section 2) lists the repo code that does exist
  (v6 grounding/english scripts) and notes calls fire at loop 0 in 127/128 panel outputs.
- Results: consumed 16-question panel x 8 checkpoints = 128 outputs: 86 right calls, 15 right finals, 71 right call but
  wrong final, 38 wrong operation, 0/64 pairs by final, 25/64 by call. PR #23 F1 (pr23-f1-report.md): all 113 wrong finals
  are numbers from the training-answer set (27 values); 64 of 128 rows have a right answer NOT in the training answers and
  all 64 are wrong. "Small shelf of familiar numbers." Ben allowed mining these 128 consumed outputs for design only.
- TRAIN32 fitting: six branches 32/32, seed1/contextual 24/32 and 29/32. Depth comparison and 8-vs-32 coverage test both
  0/8 fresh pairs. Generalization is unproved.
- Inference-only creative diagnostic (v6 text, "Creative exploration" section): 40 calls, rescued 2 of 6 practice
  failures, saved 2 checked experiences, known-answer acceptance, zero optimizer updates. Proves neither answer-hidden
  verification nor learned creativity. Receipt path unknown.
- v6 doc's creative section: explorer should find correct answers the worker misses; useful when it adds verified coverage
  or experiences that later improve the worker; plain stochastic sampling is the first baseline; later specialized explorer
  rewarded for newly rescued problems vs a named frozen worker version; clean task-state restarts; rejected guesses never
  become authoritative context; cold start: no hits means no signal; STaR rationalization uses privileged info; compare an
  explorer with ordinary sampling under the same budget (newly solved, duplicates, unresolved, latency); replaying the same
  rescued questions is insufficient evidence of method learning; multiple spellings of one correct number are artificial
  diversity. Verification: accepted / rejected / unresolved states; calculator validates arithmetic not interpretation
  (Mira: 18-7 vs 18+7); restricted formal tasks may provide exact semantics and goal predicates at deployment; checked
  input-answer pairs safer than self-authored explanations; exclude consumed panels from positive replay. Learning path:
  context reuse first, then a small adapter (core frozen), then overnight replay; each persistent update needs fresh
  transfer and retention after context reset and intervening learning. Experience store records problem, evidence
  versions, selected actions, tool outputs, supported outcome, checking method.
- Pending in the queue: fresh terminal panel (16 Luna questions x 8 checkpoints), approved two-arm 1024-example curriculum
  (512 numeric pairs, existing architecture/loss/calculator; "new_worked_example_supervision_authorized": false in
  CURRENT.json), approved small English pilot (24 passages). PC GPU (RTX 5070 Ti 16 GB) is now Premonition's full time.
  Measured cost: ~0.41 s per optimizer update in the disposable benchmark.
- PR #23 section 6 (pr23-design.md): shared Workspace contract: tokens [B,N,256], (role, modality) id pair (roles:
  question 0, notebook 1, example 2, tool_result 3, register 4, action 5), coords [B,N,3] + per-axis valid flags, valid
  mask, provenance metadata never used as an input feature. Examples: row = example index, column = token position.

## Older creative evidence (different model: MiniCPM5-1B + LoRA, number puzzles "use each of 4,7,8 once with + - * / to
make 39"; keep separate from current-architecture claims)
- design/v3/30-modes/creative-roadmap-2026-09-25.md; artifacts/claude-blurt2-20260925/ (PASSMARKS-*.md, VERIFY-*.md,
  RESULTS-*.md). blurt-3: lucky hits per ~1,980 samples 63 -> W 126/136 vs C (known answers only) 85/87; puzzles reached
  27 -> 38/38 vs C 3/4. blurt-3r replicated: 59 -> 129/148 vs 59/58. blurt-2 first-try loop failed its mark on GPU;
  blurt-2p placebo failed. design/v3/30-modes/creative-scaling-plan-2026-09-25.md and reviews/creative-research-2026-09-25/
  (expert iteration stalls after ~2 rounds without new problems, cannot start from 0 hits, variety collapse, Hindsight
  Experience Replay relabeling of misses as solutions to the goal they reached).
- TEACHING_TO_TEST_CONTRACT.md (repo root, long): rules against teaching to the test.

## The previous design to review
OLD-creative-prototype.md (written by a Sonnet thread with one Opus draft; Ben has not read it).

## Calculator pipeline code (shown; read-only copies in ./pipeline_code/, from branch
## claude/critical-thinking-data-128-outputs; do NOT open GOLD-PRIVATE-v1.json or any eval panel files)
- calculator_runtime_depth_compare.py, class CalculatorPath: action head = nn.Linear(256,3) over the mean of (h+e) at
  question positions -> logits for NONE/ADD/SUB. Two bilinear pointer heads (left, right) score candidate references
  (original integer literals found mechanically in the question, plus earlier OK result slots). At inference the runtime
  takes argmax for action and both pointers every loop (no sampling exists today). Logits are returned per loop, so call
  cross-entropy can train them. Four loops always run; each loop: decide call from current state -> execute -> write result
  into a reserved value/status pair -> core.advance_latent. After the 4th advance, read_latent -> prefix -> frozen LM greedy
  decode (max_new_tokens 32) of the final answer. Trainable modules: core, reader, prefix, tool.
- A call result is fed back only if it is ONE canonical numeric token of the LM tokenizer (else ERROR
  UNSUPPORTED_NUMERIC_TOKEN). The result's state is the frozen LM input embedding of that token through the same reader.
- calculator_tools.py: actions NONE/ADD/SUB; exactly two distinct references (DUPLICATE_REFERENCE error if left==right);
  max 8 literals, max 3 prior results referenced, max 4 calls; the tool never reads labels or infers semantics.
- So: a complete call trajectory (all 4 loops) can be produced WITHOUT decoding the LM (only the LM embedding table and
  reader are touched for results). LM sampling temperature cannot change which calls are made, because calls are chosen by
  the heads before the LM decodes; it can only change the final answer tokens.
- The "inference-only creative diagnostic (40 calls, 2 of 6 rescued)" has NO receipt: the execution owner has no record
  and a repo search found none. Its only source is a sentence in the integrated design text. Treat it as unverified.
