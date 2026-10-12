# B3 group 1: build spec (calls at any round, Gemma + outside calculator, 2,000-letter inputs, learned stop)

Written 11:05 AM ET Fri Oct 9 by the "Architecture ambiguities" thread, before any build or run.
Asked by: the big-run REPLAN (big-run/PLAN.md, 10:55 AM ET 10-09, substitution 6 and the queue changes), relayed by the coordinator
10:48 AM ET and 10:52 AM ET: "Build B3 group 1 now: calls at any round, Gemma + calculator join, 2,000-letter inputs, learned stop. Hold
group 2 (learned reading/writing) until G1 reads." and "make B3 buildable at 3M, 10M, 30M and 100M from one config."
Ben's answers it builds on (FINISHED-MODEL-2026-10-09.md sec. 7): calculator calls "Any time" (9:30 AM ET), inputs up to "2,000 letters"
(9:29 AM ET), "Keep" the letter window (9:29 AM ET), "Hundred" (10:49 AM ET: the finished thinker is 100M; 30M is a rung).
Labels: **shown** = read in code or results; **suggested** = reasoned; **untested** = never run.
This file is the build only. When it runs, its marks and the G2 size test belong to the big-run thread (PLAN.md sec. 5).

## 0. In plain words (for Ben)

Today the calculator-outside model (T1SDR) and the Gemma reader have each worked, but never together, and the learned stop has never
run. Group 1 puts four things into one model: Gemma reads the question, the model can call the calculator at any thinking round (not
only the first few), it can read inputs up to 2,000 letters, and it decides by itself when to stop thinking. Each of the four is a
switch, so if the 3M test fails we can turn them off one at a time to find which one broke it. Nothing here costs money or runs on the
GPU; the build and its checks run on the cloud CPU.

## 1. Starting code (shown)

- Base: branch `claude/project-thread-qtxfp4` = G1's exact code `612f5c5b0` + the caps overlay (sha256 3da2dfbb...) + the `tok_think`
  switch (PR #56). G1's G-B2 is the control every B3 test is compared with, so B3 is built on G1's code line.
- Port from `custom-reader-talker` at `17a356e62` (T1SDR and H1R, the reader/talker thread's code, PR #39): `custom_io/models/tool.py`,
  `custom_io/models/tool_h1.py`, `custom_io/tests/test_tool_span.py`, `custom_io/tests/test_tool_h1.py`, the `tool_h1` entry in
  `models/__init__.py`, and `train.py`'s `LOOP_SWEEP` hunk. Not ported: W1's `gattn` / `GlobalAttn` (W1 is not shown), results folders,
  diagnosis scripts. Both lines share merge base `23c0d598b2`; G1's line did not touch `ledger.py` or `reader.py` (checked with
  `git diff --stat`), so the port should be clean apart from the `tok_think` lines.
- **Check P (bit-identity of the port):** H1R's config (`label settled, span_copy, span_idx, span_end, ans_drill 0.25`), tiny width, CPU,
  fixed seed, the same rows, 50 training steps on this branch and at `17a356e62`: every loss equal and every parameter `torch.equal`.
  Caps not applied in either.

## 2. Part A: Gemma and the outside calculator together (switch `eg_embed` on the tool model)

- Remove only the `eg_embed` refusal in `Tool.__init__` (`tool.py:120`); keep the refusals of `eg_teach`, `span`, `round_readout`.
- Prompt: read exactly as G1's EGE (`ledger.py read()`: Gemma's state of the token holding each letter is added before the letter window).
- Calculator entries: read by the letter reader alone, no Gemma (`Tool.read_texts` calls `self.reader`, not `self.read`; PLAN item 4's
  default). Gemma sees the question once per batch; the run and the talker share one Gemma pass (the `encode` memo).
- Size: Gemma's 271,002,624 frozen weights count in the whole size (`n_params` dict as EGE).
- Disclosed: Ledger creates Gemma's adapter last in its own `__init__`, so the tool's new weights draw their random start after it. B3 at a
  seed therefore does not start identical to T1SDR at that seed; no comparison here relies on that.
- Tests: with a stub Gemma, (a) `encode` is called with prompts only, never entry strings (spy); (b) one Gemma pass per training step;
  (c) the reader's output for an entry string is the same with `eg_embed` on and off, given the same weights; (d) off = check P.

## 3. Part B: calculator calls at any round (switch `any_round`, default off = H1R exactly)

Today: call k can be written only at round k + 1, rounds 1-7 (`tool.py:338`, `tool_h1.py:5-6`); with G1's caps, rounds 1-11.
- **Tape:** `TAPE = max(16, n_res)` entries (K1's 16 calls, the inventory's E5 safety cap); `tape_emb` gets TAPE rows when the switch is on.
- **Running (no teacher):** after every round t >= 1, up to the cap of 32, the op head reads control 0 as today. A call goes into that
  row's next free entry (k = that row's calls so far, so rows fill entries at their own pace) and its reply is visible from round t + 1.
  The learned stop ends the turn as in H1 (a call not yet made is simply not made). A call when the tape is full is not run and is
  counted (reported per split as "tape full"; E5's line: on at most 1% of dev rows, reported, not gated here).
- **Training (teacher forcing):** each row gets a schedule of rounds for its L gold calls. Default (suggested, fixed now, not tuned):
  with probability `gap_p = 0.25` per row, each call is preceded by g extra thinking rounds, g drawn uniformly from {0, 1, 2}; otherwise
  calls sit at rounds 1..L as today. If L + (sum of g) + 1 > 32 the row uses today's schedule (counted). Draws come from the model's own
  `random.Random` stream (as `ans_drill`), so torch's draws and the data order do not change.
  - Op loss: the gold op at each call round; NOOP at every round after the row's last call, up to the batch's n rounds (so the head learns
    to stop calling; T1 already trains NOOP after the program up to round 7); **no op loss at gap rounds** (no label ever says "wait").
  - Cell, span and gate losses at call rounds only, as T1SDR. Answer loss each round from the row's last call round on (H1R's rule with
    L = that round). Stop labels unchanged (settled).
  - Rounds per batch: n = max(K, longest schedule + 1), K from {4, 8, 16, 32}, as H1.
- **Why the gaps (suggested):** without them every trained call comes in the first L rounds, so a call the model chooses to make after
  more thinking lands in a state it never trained on. Masked gap rounds show it replies arriving after thinking, without teaching any timing.
- **Evals:** T1SDR's extra evals (call accuracy, tool off, opswap replay, write_copy) work with calls in call order, not round order.
  New report-only items: the rounds at which calls happen (histogram), calls per row, tape-full count, rows that fell back to today's
  schedule in training.
- Tests: (a) off = check P; (b) running: a row that calls at rounds 2 and 5 gets entries 0 and 1, visible from rounds 3 and 6, while a
  row that calls at rounds 1, 2, 3 in the same batch fills entries 0-2; (c) a 17th call is not run and is counted; (d) teacher forcing with
  gaps: visibility masks follow the schedule, op loss is masked at gap rounds and NOOP after; (e) the gap draws leave `torch` RNG
  untouched; (f) the cap fallback; (g) feeding the gold calls as an oracle at the scheduled rounds in a free run gives the same thinker
  states as teacher forcing (fp32, CPU, tolerance 1e-5).

## 4. Part C: inputs up to 2,000 letters

- **Code:** caps `max_prompt` up to 2,000 (reader position table, `data.py:107` assert); `w_max`, `n_num` computed from the pool by
  `caps.py compute` as now (no truncation; at 2,000 letters they grow to about 1,485 and 650, `tok_cost.py`'s count). Gemma reads the
  whole input (EmbeddingGemma 2 window 8,192 tokens; 2,000 letters is about 460 tokens at the measured 4.36 letters per token).
- **Positions:** decision (a) of the big-run thread: keep the learned table and train with long rows (PLAN.md Revision item 7).
- **Caps reach every module (the G1 bug class):** add `custom_io.models.tool_h1` and any new module to the import-then-patch list in
  `caps.apply` (`caps.py:140`; today `tool_h1` imports `N_RES` by value and is not patched). Test: after `apply` with a caps file, grep-driven,
  every module that defines one of `N_RES N_NUM W_MAX R0 M MAX_PROMPT N_REG GEN_MAX` holds the caps value, and a built B3 has `n_res`
  tape and `n_reg` registers.
- **Found 11:25 AM ET by the inventory re-run (shown, `17a356e62`):** the tool model hard-codes 9 answer registers, `tool.py:325`
  (`place.weight[:9]`) and `tool.py:501` (`np.full((B, 9), ...)`), while `GEN_MAX` comes from the caps. Under G1's caps (36 registers)
  that would break or cut GEN answers, the same class as G1's register bug. Fix: use `N_REG` there (as `ledger.py:303, 437`), with a
  test that B3 under the caps has 36 registers and a 30-letter answer keeps its full target. Sent to the builder.
- **Data (owner: the data thread, CPU):** `cloze.py`'s `CHUNK_MAX = 279` becomes a pool-build parameter with a `long_share` (the share
  of web chunks cut long, up to 1,999 letters); defaults keep today's pool byte for byte (test: manifest sha unchanged). The long pool
  itself, its mix and its protected-panel hash are the data thread's and the big-run thread's.
- **Readout:** the analyzer reports exact match per input-length bucket (<= 280, 281-700, 701-1,300, 1,301-2,000 letters) on every dev
  split that has rows there (PLAN's G2 bucket rule is the big-run thread's mark).
- **Cost (report-only, CPU here):** a `b3_cost.py` like `tok_cost.py` (separate file): tiny-width B3 at max_prompt 2,000 vs 280, one
  training step each at batch 2, counts of thinker key positions (letters, number slots, tape) and step time. The real fit check (memory
  on the 16 GB PC at 3M and 100M) is the big-run thread's.

## 5. Part D: the learned stop

H1R as built at `17a356e62` (stop head on control 1, label "settled", P_STOP 0.5, cap 32, rounds past `n_loops` checkpointed,
`tool_h1.py:1-40`). No change. It has never run (built, queued, then folded into this test by REPLAN substitution 5).

## 6. One model, four sizes

- Model name `b3` (a subclass of `ToolH1`; every switch default off, so `b3` with no switches = H1R). Group 1 config
  `B3_G1 = {label: settled, span_copy, span_idx, span_end: true, ans_drill: 0.25, eg_embed: true, any_round: true, gap_p: 0.25}`.
  `tok_think` also works inside `b3` (the same three lines in the tool's `run`, off by default), so G2 can use tokens if test TK passes.
- `custom_io/g8a/configs.py`: arm `B3` with `b3_cfg(rung)` for **3M, 10M, 30M and 100M** from the same code path as `b2_cfg`
  (3M: B2's S shape; 10M and 30M: B2's rung widths with blocks chosen to the target; **100M: width 512, 8 heads, mlp 4.8, 21 blocks**,
  the PLAN's 97.1M thinker shape, no band). `n_loops = max(8, n_res + 1)` as G1. Print a table: trained, frozen Gemma, whole, per rung.
  The 100M rung's pool fields say "not built" (the 600M pool is the data thread's, waits for a GO).
- `custom_io/g8a/job.py` runs arm B3 like B2 (same train.py path, lesions, `LOOP_SWEEP`, accum option), and `analyze_8a`-style readout
  gets B3's items (rounds, calls, tape full, length buckets).

## 7. Checks before anything leaves the cloud (all CPU, here)

Check P; every test above; `test_tok_think` and the TK scorer tests still ALL OK; G1's own `test_g8a` still passes; a tiny end-to-end
B3_G1 training run on CPU with a stub Gemma at max_prompt 2,000 (50 steps, loss finite and falling on a small repeated set); the rung
table; extra evals on a tiny dev set. Staging for the PC or a Mac goes through Ben's Mac session with his go; when it runs is the
big-run thread's call (after G1 reads GO).

## 8. Not in group 1

Group 2 (held until G1 reads): N1, O1, P1, V1, L1, ST1 (the learned reading and writing parts, no-hardcoding PLAN sec. 2).
Noted for the group 2 spec (11:25 AM ET, from the domain-learning thread via the coordinator, after Ben's 10:57 AM ET ask for a mode where
the model learns a whole domain by itself): the call writer must write the WHOLE call as letters, operation name included. Today the
op head picks one of 8 fixed operations plus no-call (`ledger.py` OPS, `tool.py` NAMES and `op_head`), and the harness writes the op word
(inventory item J1), so a tool added after shipping (for example spreadsheets) could not be called. Experts (GX)
join only if both its stages GO. Relative positions (decision (b)) only if TK passes and the limit rises. Long input past 2,000 letters
(carry-over of thinker vectors) is a later stage.

## 9. Risks (suggested)

Memory and time at 2,000 letters x 32 rounds x a 16-entry tape x about 650 number slots are unmeasured; Gemma plus the outside
calculator is a first-ever join; the learned stop is a first run; gaps change the training distribution of a quarter of the rows.
Each is a switch, so a failed 3M test is bisected by turning them off one at a time.
