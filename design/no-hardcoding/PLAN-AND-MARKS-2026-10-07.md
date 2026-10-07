# No hard-coding: the learned replacement for every hand-written part, test order, sealed marks (2026-10-07)

Asked by Ben 12:01 PM ET 10-07. Thread "No hard-coding + richer input" (Opus, ultracode). Written before any run of anything in it, then checked against the code, the result files and the sealed D0/T1 file by two independent reviewers (fixes applied before sealing).
Labels: **shown** = read in code or result files, **suggested** = reasoned, **untested** = not run. The custom reader/talker thread owns B2's code and runs; the architecture thread owns D0, T1, W1 and H1 (`/mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md`, `redesign-ideas-2026-10-07.md`). This file fixes the definitions and marks for everything else. Parts list with file:line: `INVENTORY-2026-10-07.md`. Input question: `INPUT-UNITS-2026-10-07.md`.

## 0. Ben's rule, as I apply it

0. **Key rule, above all the others (Ben, 2:45 PM ET 10-07):** "everything that you do should be able to be done by the model autonomously while it's deployed." Reading (disclosed; Ben can correct it): building the first model (its design and its first training run) is ours. Everything after that is the deployed model's own: reading, deciding how long to think, which tool to call, when to stop, learning a new kind of question from plain examples, deciding when to practise or sleep and what to keep. A step that needs a researcher's hand-picked choice at run time is not finished until the model does it itself, or calls a tool for it. Section 2a lists every such step in this plan.
1. Nothing hand-written may run between the question and the answer except inside a tool. A tool is something the model calls by writing text; its reply comes back as text the model reads like the question. The tool loop itself (inventory section E) is part of the tool.
2. Teaching material may be hand-written (labels, worked steps, traces) for the first training run, the way a teacher writes worked examples. It never runs when the model answers. Under rule 0, though, a deployed model gets no hand-made traces for a new kind, so two rungs below (L1, ST1) make it learn without them.
3. Tests and scoring may be hand-written.
4. If removing a hand-written part costs points, the fix is in the learned link that broke, never putting the part back (Ben 10:35 AM ET, for the calculator; I apply it to every part).
5. Your message answers the architecture thread's open question: the outside calculator **replaces** the in-forward executor, the value codes and the result slots; it does not sit alongside them (T1, as sealed). T1 may keep regex-found spans for the question's numbers, without value codes (the sealed file leaves that to the build thread, disclosed); N1 then removes them. Nothing hand-written stays at the end.

## 1. Where it ends: "B3", everything learned (suggested)

One question, worked through B3 (call grammar is T1's own; inventory E2):

```
context  = "Tom has 12 apples, gives away 5, buys 3. How many?"
turn 1   reader reads the context as bytes -> thinker loops -> writer writes  sub 12 5
         calculator tool (hand code, allowed) returns "7"; appended:  ... | sub 12 5 = 7
turn 2   reader re-reads question + transcript -> thinker -> writer writes   add 7 3
         tool returns "10";                            ... | sub 12 5 = 7 | add 7 3 = 10
turn 3   reader -> thinker -> writer writes                    answer 10      (stop)
```

| Part | B2 today (shown) | B3 (suggested) |
|---|---|---|
| Input unit | 108 hand-listed chars + hand place code | raw bytes (256), learned position only |
| Reader | 2 conv blocks, +-4 window | the window (it matters: R0 -6.3/-6.8), plus W1's global attention only if W1 passes |
| Numbers in | regex -> int64 -> exact digit code in 16 slots | only the bytes; nothing parses a number before the model |
| Thinking | 2 blocks x 8 fixed rounds, picks 1 of 9 ops + 2 slots | same looped blocks and state vectors, cross-attending to the reader; no slots; 8 rounds per turn |
| Arithmetic | Python executor inside the forward pass | calculator tool; the model writes a one-operation call, the tool returns text |
| Steps | at most 7, fixed schedule | as many calls as needed (safety cap 16); stops by writing an answer |
| Output | 3 hand renderers: `str()`, word slicing, 8 reversed registers | one learned byte writer with copy attention over question + transcript |
| Training | teacher-forced slot programs from a hand parser | teacher-forced traces (calls + tool replies + answer); the tool's real reply is inserted, never the label's |

Why it can work (suggested):
- Exact intermediate values beat latent ones (`REPORT.md` lesson 1, shown). In B3 the exact values still exist, as text in the transcript, which the model must read and copy itself.
- With the arithmetic in a tool, the model never has to compute on digits, only copy them. Copying is a pointer job that attention does well (Jelassi 2024, 2402.01032: a 2-layer transformer can copy long strings, shown in the abstract). Place value, which is what the hand place code supplies, matters for computing, and computing moves into the tool. My reading of the numbers papers (suggested, from abstracts): the tricks that make small models good at arithmetic (Abacus, position coupling, FoNE, xVal) feed place or value from code that already knows where numbers start and end, which is the hand-written feature Ben objects to.
- Teacher forcing on traces is how the tool-use papers the helpers opened start (Toolformer, TALM, Calc-X, NPI, ReTool's cold start; abstracts). None is at 3M params, so this is untested at our size. TALM-style self-training (keep the model's own traces that end in a right answer) is the fallback if teacher forcing stalls; it is not in the ladder.
- The text baseline already runs a regex-triggered calculator and gets chain-5 96 (C1', shown: 96.2-96.6 on q33), so the open question is the gap to B2's 99.4-99.8, not whether the pattern runs at all. D0b finds where that gap comes from before T1 is built.

## 2. The test order: one change at a time

Every rung is one change on top of the previous rung, paired by seed. Recipe as B2 unless stated: same 200k skills rows and order, 24,000 updates, batch 256, lr 1e-3, bf16.
- **Size:** within +-3% of 3,244,544 trainable (plain_tf, the sealed band: 3,147,208 to 3,341,880). B2 itself is 3,302,481, so only about 39k of headroom remains above B2; every rung prints its trainable count and the margin left, and one that would go above the band says what it shrinks (disclosed) or asks Ben.
- **Seeds and machine:** screens use seeds 200 and 201 against the previous rung on the same seed; rungs compared with q33 (B2, plain_tf_steps) run on the PC, where q33 ran (same-machine rule, `PASS-MARKS.md`); on any other box the baseline is re-run beside it with the addendum-10 device check.
- **Saved outputs:** every rung saves per-row dev predictions for all 6 dev splits (`evaluate(..., return_preds=True)`) and exports its checkpoint, because the link checks below need both.
- **Scores:** pooled-5 (in_dist, answer, frame, vocab, variant; 6,040 rows) and chain-5 (1,000 rows), as in `REPORT.md`. "Zero-round" and "donor" leak checks use T1's own definitions, which the build thread fixes before T1's first run (for example: zero thinker rounds on every turn with the tool live; donor state on every turn).

- **Nothing is cut off (Ben, 2:04 PM ET 10-07: "I don't think you should have it cut off long answers"; standing rule):** no training target in any arm (B2, T1 and later rungs, C0, the growth-ladder arms, the LLM-recipe baselines) is truncated or falls back to answer-only. Every remaining length or count limit is listed below with the rows it touches; a new limit that touches a training row is a bug to fix, not a setting.

| Limit (shown in code at 2b1cbd4d7b; counts from the build thread on train sha 010af671 and the dev splits) | Where | Rows touched | Status |
|---|---|---|---|
| Worked steps only if steps + answer <= 64 chars, else answer-only | `plain_tf_steps.py:21, 27` | 840 var_chain train rows | C0 raises it to 107 (longest on train): none left. Runs tonight |
| At most 7 program steps, else no program at all | `progparse.py:8, 199` (N_RES); B2's 7 result slots; T1's 7 calls | 528 train rows (list_stats, 9-11 steps); dev: in_dist 3, answer 1, frame 2 (big dev build: 16 / 11 / 17) | K1 lifts it to 16 for T1. B2 itself keeps it: the growth-ladder B2 arms should size N_RES to the longest program on train |
| Answers of at most 8 chars | `data.py:11, 116` (MAX_ANS); B2's 8 GEN registers (`ledger.py:63`) | Train: none (longest is exactly 8). Dev: 5 of 160 "family" rows (3.1%; clock_date 3, string_transform 2; up to 12 chars; big dev build 25 of 800), cut to 8 and unanswerable; not in pooled-5 | B3's writer cap is 48. Growth-ladder arms set the answer cap to the longest answer in their data |
| First 16 numbers per question get slots | `progparse.py:8, 18` (N_NUM) | none (train max 11) | N1 removes the slots |
| First 64 words can be pointed at | `progparse.py:8`, `ledger.py:209` (W_MAX) | none (train max 50) | O1 removes word pointing |
| Questions of at most 208 chars | `data.py:11, 107` (MAX_PROMPT) | Train: none (max 204) | Growth-ladder arms with web text size it to their data |
| **Silent filter at generation:** any drawn question over 62 estimated word pieces is thrown away and redrawn, a leftover from an older 64-token model | `skills_curriculum/core.py:22`, `build.py:29-32, 48-58` (branch `claude/project-thread-y0sxwe`; manifest for train sha 010af671) | Unknown: the reject count is not saved. No answer-length filter exists there (answers are short by family design) | Long questions never reach training. The growth-ladder data must not inherit it; the next skills build should record its rejects |

| Rung | One change | Removes (INVENTORY ids) | Depends on | Owner of spec |
|---|---|---|---|---|
| D0 | no training: can the reader carry digits, can the talker copy them; plus Amendment 1's control (the same probe on a reader trained for digits only) | none (diagnosis) | B2 checkpoints | architecture thread, sealed |
| D0b | no training: on the text baseline with its calculator (C1'), classify every failed chain-5 row by its first wrong link | none (diagnosis) | existing plain_tf_steps checkpoints | this file |
| T1 | calculator outside: the model writes a one-operation call, the reply returns as text; no value codes, no result slots | A2, A5 (result cap), A6, A7, A8 (step schedule), A13 for results, A17; A4 dropped or given learned per-constant embeddings (disclosed) | D0 | architecture thread, sealed (screen and 6-seed confirm) |
| K1 | lift the 7-call limit T1 inherits from the hand teacher (progparse caps at 7 steps, B2's 7 result slots): up to 16 calls, tape 16, about +2,300 params. It binds on 528 train rows (list_stats with 5-6 numbers, 9-11 steps), which today get no calls | A5 (step cap, last part) | T1 passed its 6-seed confirm | this file (build thread's proposal, 10-07) |
| O1 | final answers go through T1's writer; delete whichever of A10-A15 T1 kept (see 3a) | A10 (output use), A11-A15 as left by T1 | K1 | this file |
| N1 | delete the number machinery T1 kept: regex spans, number slots, any constants left (skipped if T1 kept none) | A1, A3, A4, A5 (16-number cap) | O1 | this file |
| P1 | delete the place input term (the 9 place rows stay as the register tokens' own learned init) | A9, A10 (last use) | N1 | this file |
| V1 | raw bytes instead of the hand-built vocab, applied right before B3 | A16 | P1 | this file (no screen, see 3b) |
| H1 | learned number of thinking rounds per turn (today fixed at 8) | A8 (rounds) | T1 | roadmap 2d / architecture thread |
| L1 | teach from the worked steps exactly as written: no hand algebra in the traces (today "? + 5 = 12" is rewritten to SUB(12, 5) by `progparse.py:42-51`); the model must find the inverse call itself | B2 (inventory) | T1 | this file |
| ST1 | self-taught traces: on kinds held out of all trace teaching, the model gets only question-and-answer pairs, writes its own calls, and keeps for training only the traces whose answer checks out (TALM / STaR style) | B1-B4 for new kinds | L1 | this file (the fast-sleep and creative threads already do this for B2; ST1 ports it to the call-writing model) |
| B3 | 6-seed confirm of the result vs B2 and plain_tf_steps | | T1, K1, O1, N1, P1, V1, H1, L1, ST1 | this file |

**H1 is now required** (rule 0: the model decides how long to think). It stays with the roadmap (2d) and the architecture thread. A note for them: Popescu 2026 (2607.20519, abstract) found a jointly trained halt gate distorts the loop, and supervising every round and stopping on a confidence readout often matched or beat it; in B3 the stop between calls is already supervised, since the trace says when to answer.

**Marks for L1 and ST1** (fixed now, before any run; 2-seed screens on the PC):
- L1: the 3a marks against the previous rung, plus missing-operand rows (the families that used the inverse-op rewrite), pooled, 2-seed mean, within 3.0 of the previous rung. Proved wrong: those rows more than 10 below.
- ST1: pick 3 kinds before the run (the build thread names them from the variant split, sealed in the queue file), held out of all trace teaching. The model gets 2,000 question-and-answer pairs per kind and no steps; it writes calls, the tool runs them, and traces whose answer matches are kept and trained on, for up to 3 rounds. Pass: accuracy on fresh held-out rows of those kinds up by >= +20 over the same model before ST1, on both seeds, with pooled-5 not down more than 1.0. Proved wrong: < +5 on both seeds. The answer check is the only hand part, and at deployment it is the world's feedback (or a check tool the model calls).

## 2a. Steps that still need a researcher's choice at run time (rule 0)

| Step | Where today | Who owns the fix | Becomes |
|---|---|---|---|
| Fixed 8 thinking rounds | B2, T1 (A8, E6) | roadmap / architecture (H1) | learned halting, required for B3 |
| Hand-made worked traces and the inverse-op rewrite | progparse (B1-B4) | this file (L1, ST1) | learned from steps as written, then self-taught from Q/A pairs |
| Try budgets and how many extra tries where stuck (32 + 480) | C2 / C2b (D5) | creative roadmap | the model keeps trying until its check tool says right, or it decides to stop |
| Sampling temperature picked on a DEV grid | C1, C2b (D2, D5) | creative roadmap | learned, or set by the model per question |
| Notebook gate thresholds (theta 0.9 / 0.99 quantile, c = 50) | memory sleep (D6) | creative roadmap 7b (learned gate) | learned gate, then a recall tool |
| When to sleep, what to keep, nightly harm check | fast sleep (D8) | fast-sleep thread | the model decides when to practise and checks its own harm on held practice |
| Breadth-first solver for warm-up programmes | creative (D9) | creative roadmap | the model's own search (C2 already shows search is easy for these kinds) |
| Which kinds to practise, data mix, learning rate during sleep | fast sleep, C2b | fast-sleep thread | the model's own choice; a fixed recipe is disclosed until then |
| Tool-side safety caps (16 calls, 48 bytes) | B3 tool (E5) | this file | kept as the world's limits, like a game's rules; the model decides to stop well before them (mark: hit on <= 1% of rows) |

Not on this list (ours by the reading above): the model's design, its first training run, tests, scoring and pass marks.

**Gain tests beside the ladder** (they do not depend on it): W1 (global attention in the reader; architecture thread's spec), U0 (letters vs word pieces in the all-learned text baseline), U2 (learned letter groups), EGE (q39, running). See `INPUT-UNITS-2026-10-07.md`. A winner enters the ladder as its own rung on the current rung, screened with S1-S5 below plus its own gain mark, never bundled with a removal.

## 3. Sealed marks

### 3.0 D0b, report only (no pass mark; it decides where T1's effort goes)
On the plain_tf_steps checkpoints already saved (`/mnt/project-files/custom-io/checkpoints/20-screen-s100-w1/tfsteps_s100`, `22-screen-s101-w1/tfsteps_s101`; no plain_tf_steps checkpoints exist for seeds 200-205), CPU only. New code is needed: `PlainTFSteps.generate` returns only the final answer (`plain_tf_steps.py:129`), so a script (`custom_io/diag_c1_links.py`) re-generates the 1,000 chain-5 rows with the C1' calculator on and returns the written text and where the calculator fired.

Label each wrong row by its FIRST wrong link, comparing the written text with the row's gold steps:
- (a) an operand's digits copied wrong: the written operand is not any prompt number or earlier result, and differs from the gold operand in at most 1 digit;
- (b) a wrong number chosen: the written operand equals another prompt number or an earlier result;
- (c) a wrong operation;
- (d) a tool result copied wrong into a later step;
- (e) the final answer copied wrong;
- (f) a step format the calculator did not fire on;
- (g) stopped early or ran too long;
- (h) the row was trained answer-only (steps plus answer over 64 chars, `plain_tf_steps.py:15, 21-27`);
- (i) its own arithmetic wrong on a step the calculator never fires on (state_update arrows like "+5 -> 17"; `_CALC` needs "a op b =", line 18);
- (j) a wrong name (story_chain3 answers are names).

Pool both seeds (about 70 failed rows in all: C1' chain-5 is 96.2-96.6). Report (h)-(j) separately and leave them out of the call. If copying, (a)+(d)+(e), holds at least half of the remaining rows, T1's risk is the copy path; if choosing, (b)+(c), holds at least half, T1's risk is the thinker's state; otherwise "mixed". No paper the helpers opened measures where a small text-plus-calculator model loses (papers file, tools section, gaps).

**D0b result (10-07, 1:48 PM ET, shown; `D0b-RESULT-2026-10-07.md`, repo `custom_io/results/d0/D0b.md` at dd4976508):** call "mixed". 58 of the 72 wrong rows (81%) are (h): 4-5 step var_chain rows trained answer-only because steps plus answer pass the 64-char cap, so the model writes a bare number and the calculator never runs. Copy errors (a, d, e): 0 of 2,000 rows. Choosing (b, c): 3. Without (h) the baseline would miss about 14 of 2,000 (99.3). So T1's copy path is not the expected risk; the choosing set and story_chain3's final word are. It also shows the text baseline is handicapped by its own cap, which C0 below fixes before it is used as the LLM-recipe yardstick again.

### 3.1 C0: a fair LLM-recipe baseline (added after D0b, before any run of it)
plain_tf_steps writes its worked steps only when steps plus answer fit in 64 chars (`plain_tf_steps.py:15, 21-27`); longer rows are trained answer-only. That is a handicap in the yardstick, not a property of the LLM recipe.
- **One change:** raise CAP so that no step-family training row falls back to answer-only (the build thread measures the longest steps-plus-answer target on train and uses that, disclosed), with MAX_POS raised to fit prompt plus target (e.g. 288 -> 400: +28,672 params, still inside the size band). Nothing else changes. Its C1' calculator lesion is scored too.
- Seeds 200 and 201 on the PC, against q33's plain_tf_steps on the same seeds.
- Reported: pooled-5, chain-5 with and without the calculator, and B2 - C0 per seed.
- Pre-registered prediction (from D0b, suggested): C0 with the calculator reaches chain-5 >= 98.5 on both seeds. Proved wrong: below 97.5 on both.
- **Consequence (fixed now):** if C0's pooled-5 2-seed mean is at or above plain_tf_steps', C0 replaces plain_tf_steps everywhere it is the yardstick: B3 mark 2, U0's base model, and the LLM-recipe arm of the roadmap's growth ladder. A stronger yardstick only tightens marks. If B2 - C0 is more than 3.0 below today's +6.9, the "+6.9 over the LLM recipe" claim is withdrawn until a 6-seed C0 confirm restates it.

### 3a. Every parity rung (O1, N1, P1), 2-seed screen
- **S1** pooled-5: (rung - previous rung) >= -2.0 AND (rung - q33 B2) >= -2.0, same seed, on both seeds. The second clause stops losses adding up rung by rung.
- **S2** chain-5 >= 99.0 on both seeds (B2 reads 99.4-99.8; the chain-5 paired SD is 0.22-0.33).
- **S3** cipher_map pooled over in_dist, answer and frame (120 rows) >= 92.5 on both seeds (B2 on q33: 115-119 of 120; exact-letter guard).
- **S4** no dev split down by more than 3.0 against the previous rung on the 2-seed mean (per-split paired SD is 1.6-2.1, so a per-seed 4.0 mark would fail about 15% of the time with no real change).
- **S5** zero-round in_dist <= max(5, q33 B2 on that seed + 1) and donor in_dist <= 5, on both seeds; B2's and the previous rung's values printed next to them (q33 B2 reads 0.0, 10.8, 0.0, 5.7, 3.5, 0.0 on seeds 200-205).
- **S6** the rung's own link check (below).
- **Pass** = S1-S6. **Proved wrong** = pooled-5 2-seed mean (rung - previous) below -4.0, or chain-5 below 95 on both seeds: the removed part was doing work the learned path cannot do at this size. Then the part stays removed, the shortfall is reported, and the named fix runs (one change, re-screen). A second miss goes to an ultracode diagnosis of that link. Putting the part back is never the fix. A result between pass and proved wrong is "not shown": fix the link the diagnosis names, re-screen.

Family scores in the link checks are pooled over every split the family appears in (copy_word and div_exact: 5 splits; arith_bare: 4; cipher_map: 3; chain_ops from the chain-5 panel), 2-seed mean.

Link checks and named fixes:
- **K1.** list_stats (pooled over its splits, 2-seed mean) at or above T1's, and the cap-16 limit hit on <= 1% of dev rows. Named fix: none needed beyond the cap; if list_stats does not move, the traces for those rows are checked first.
- **O1.** What O1 is depends on what T1 built (the build thread reports which case applies before O1 is coded):
  - T1 already writes every answer with its call writer: O1 is empty; record "A11-A15 removed in T1" and screen N1 against T1.
  - T1 has a call writer but keeps the mode head for final answers: O1 routes final answers through that writer and deletes the mode head and renderers (one change).
  - T1 reuses the 9-register GEN path as its call writer: O1 is two rungs, O1a (an autoregressive writer) then O1b (delete NUM, WORD and the mode head).
  - T1 put the call-or-answer choice into the mode head: that decision stays where T1 put it.
  - T1 prints result answers by slicing words out of the transcript: T1 discloses it and O1 removes it.
  - Check: among number-answer dev rows, rows whose right digits are in the question or transcript but were written wrong are <= 1% of number-answer rows, on both seeds; copy_word and cipher_map each within 3.0 of T1. Named fix: one more writer layer, paid for inside the size band.
- **N1.** arith_bare, chain_ops and div_exact each within 3.0 of O1. Reported, not a gate: D0's digit probe on N1's reader output, on a synthetic set of at least 200 held-out numbers per place 1-9 (our data has few long numbers). Named fix: W1 as its own rung, if it has not already passed and entered.
- **P1.** Rows whose numbers have 6 or more digits within 3.0 of N1 (on the synthetic set if fewer than 100 dev rows qualify); the copy check from O1 still holds; digit probe reported. Named fix, in this order: (1) W1 as its own rung if it is not already in; (2) a learned boundary logit per byte from the reader, with a soft "distance from the next boundary" computed from it (cumulative sum from the right), trained only by the task loss. Option 2 is a hand-designed inductive bias that rebuilds the place code from learned boundaries: disclosed, last resort (helper's suggestion after H-Net and ACT, untested).

### 3b. V1 (bytes), no screen
Today's vocab is exactly 13 specials + the 95 printable ASCII chars (108 ids, `data.py:20-24, 55`), so every train and dev char is printable ASCII and keeps its symbol under bytes. V1 changes the table size, every id (today 13 + (ord - 32)) and, through the random draw order, every initial weight; the tied embedding and output table and its bias grow by 161 rows (+41,377 params, +1.25%). That alone is past the 39k headroom above B2, so V1 is applied after T1, O1, N1 and P1 have freed parameters (each prints its count), or names what it shrinks. Mark: a unit test confirms every row is ASCII before the switch; behaviour on ASCII data should match within seed noise, and the effect is read in the B3 confirm. If any row is not ASCII, V1 gets a normal 3a screen instead.

### 3c. B3 confirm, 6 paired seeds (200-205) against q33's B2 and plain_tf_steps, on the PC
1. **Parity with B2:** T1's sealed parity mark, word for word, whatever the architecture thread seals before T1's first run. Today it reads "the 6-seed 95% CI of the difference lies inside +-1.0". **Noise problem, raised with the architecture thread:** the CI half-width is t(5) x SD / sqrt(6) = 1.05 x SD, so at SD 0.94 the mean must sit within about +-0.01 to pass, and at SD 1.33 it cannot pass at all. Suggested re-seal before any run (not mine to make): mean(B3 - B2) >= -1.0, CI lower bound >= -2.0, and B3 >= B2 - 1.0 on at least 5 of 6 seeds. B3 never uses a looser parity mark than T1.
2. **Still beats its size:** mean(B3 - plain_tf_steps) >= +3.0 with CI lower bound > 0 (B2 is +6.9, paired SD 1.33, shown). If C0 (3.1) replaces plain_tf_steps, this mark is read against C0.
3. **Chains:** chain-5 6-seed mean within 1.0 of B2's (99.57) and >= 99.0 on at least 5 of 6 seeds (T1's sealed mark 2).
4. **Tool off,** exactly as T1 defines it: program questions (the noexec set) < 5% (B2 with its executor removed reads 0.8%).
5. **Swap:** with add and subtract swapped inside the tool, >= 99% of affected chain rows follow the swapped value. "Affected" = rows whose intact call log contains an add or a subtract, found by replaying the intact log with the swapped tool (B2's own count: 826 of 1,000, `opswap`). Needs new code: the multi-turn version of `ledger.py:610-640`.
6. **Leaks:** zero-round and donor in_dist <= 5 on every seed, T1's definitions, with B2's value on that seed printed next to it (B2 itself misses on s201, 10.8, and s203, 5.7).
7. **No split** down by more than 2.0 against B2 (6-seed mean).
8. **Audit:** `generate()` on 200 dev rows with `re`, `int` and `str` patched to raise when called from outside `tools/`; the tool loop lives in `tools/`; the model's only input tensor is byte ids. Training and scoring code are out of scope. Fails = not B3.
9. **Caps:** the 16-call cap is hit on <= 1% of dev rows and the 48-byte write cap on <= 0.1%.
- **Pass** = 1-9. **Proved wrong** (T1's thresholds, no looser) = mean(B3 - B2) below -2.0, or chain-5 mean below 95, or B3 not ahead of plain_tf_steps on the mean. Then, at 3M and this data, the hand-written parts were worth more than learning recovers; the finding goes to the roadmap's bigger rungs, and B3 stays the base anyway (Ben's rule).
- Noise, for reading the verdicts: SD 0.94 is B2 - plain_tf (the direct-answer baseline) across the 6 q33 seeds; B2 - plain_tf_steps is 1.33; B2 alone is 0.63 (`results/CONFIRM-ANALYSIS.json`, shown). The B3 - B2 paired SD is unknown until B3 runs; the build thread prints it next to each verdict.

## 4. Creative and sleep (specs for the creative roadmap thread)

**Superseded by the creative roadmap thread (10-07, about 1 PM ET):** it sealed these items in its section 7b (`/mnt/project-files/creative-roadmap/creative-roadmap-2026-10-06.md`). Its marks replace the proposals below wherever they differ. In short: the used-number mask runs only in C1, which is retired (C2 and C2b use level 0), and is never used again unless a learned replacement passes; the order is 1a, then 1b only if 1a misses, a new 1c only if same-number picks inside a step remain, then 2. The live hand part is the notebook gate (`fastsleep.py:538`): job 9's arm M is reported as "hand-gated notebook", and nightly recall is not used again until a learned gate passes. The D3 example-checker tool waits for T1's 6-seed confirm. The text below is kept as the reasoning it started from.

Parts D1-D10 are in section D of the inventory. Papers: `no-hardcoding-papers.md`, section "Learned legality and learned memory gates" and its supplement (abstracts, plus a few numbers a helper read in paper bodies; every result there is RL or a large model, the smallest 250M, nothing at 3M). The creative roadmap thread owns these marks; the ones below are proposals for it to seal or tighten. Proposed replacements (untested):

- **The used-number mask (D1, `creative/legal.py`).** In B3 it goes away by construction: the puzzle becomes a tool (the model writes a move; the tool applies it or replies "error: 5 already used"), which is the world's rules, like Minecraft refusing a block, and allowed. On B2 before that, three changes, tested one at a time:
  1. *1a, coverage input:* feed the slots each step has read back in as a learned "read" embedding on those slots (information, not a rule; Tu 2016, See 2017).
  2. *1b, coverage loss on top of 1a:* See's coverage loss, a training-time penalty on re-reading a used slot, started late. A helper read in See et al.'s paper body that the input alone gave "no discernible reduction in repetition" and that the loss from the start hurt the main objective; that is a prediction for 1a, not a reason to bundle them.
  3. *2, legality head:* a small learned head, trained on the executor's own "used / illegal" labels (Zahavy 2018's action-elimination design), whose log-probability is added to the move logits. No threshold: a threshold-and-mask step would be a hand rule again. The hand mask stays only as the ruler it is compared against.
  - Not a bare reward penalty: Zabounidis 2026 (abstract) shows unmasked training with penalties suppresses valid moves at unseen states, and a learned feasibility classifier fixes it. Huang 2020 (paper body) found a policy trained with the mask and then run without it kept most of its legality, so phasing the mask out is a further option if 1a, 1b and 2 miss.
  - Closest match to C1's puzzles: Stream of Search (Gandhi 2024, Countdown, 250M, no mask) writes the remaining numbers into the text after every step and makes few state errors (0.8%, paper body). In B3 the puzzle tool's reply can do the same ("left: 3 7 10"), which is the tool's text, so it is allowed.
  - Proposed marks for each of 1a, 1b, 2 (scored on C1's DEV puzzles, never the sealed test): legal share without the hand mask >= 0.90 (raw 0.29, masked 1.00, PR #45, shown); answer accuracy within 0.5 of the masked model; proved wrong if an illegal pick gets through on more than 1% of held-out steps.
- **Tool-side rejection (D1, D3 as tools).** Closest to Ben's rule. AutoHarness 2026 (abstract) blocked every illegal chess move with a checker that re-prompts on a reject. Fission-GRPO 2026 and Su 2025 (1.7B-8B, RL) say small models repeat a bad call after an error unless recovery is itself taught, so the teaching data needs rows of the form "bad move, tool's error text, corrected move", made by our own tool. Marks for the "try it on the examples" tool (D3) are the creative roadmap thread's to write; none are sealed here.
- **The notebook gate (D6, memory sleep).** The hand-set threshold (theta 0.9, raised to the 0.99 quantile) and the c = 50 boost become a tiny learned gate on the top-16 similarity scores and vote share, labelled by whether the stored programme was right on the night's own practice rows (Drozdov 2022, Zheng 2021, Yogatama 2021). Definitions: coverage = the share of C2b DEV answers where the gate adds votes; confident-wrong = a notebook-boosted answer that is wrong. Proposed marks: no more confident-wrong answers than today's gate at equal coverage, on a held-out frame split; proved wrong if it admits more there. Always compared with a no-notebook control (Xu 2023, Wang 2023: retrieval gains are often smaller than they look).
- **Later (B3):** the notebook becomes a recall tool the model calls, replying with stored programmes as text it can adapt, and the model is trained with the memory present (TRIME 2022, RETRO) so it learns when to trust it. Today's notebook replays slot ids, so 3x+7 cannot become 5x+2 (affine 0%, shown). Marks for it come with its build.
- **Settings and tests stay:** try budgets and temperature grids (D2, D5) are search settings around the model for now; the harm switch, checkers and blind baseline (D8, D10) are tests; the breadth-first solver's programmes (D9) are teaching material.

## 5. Order and compute (suggested)

1. D0 with its Amendment-1 control, and D0b, now, on CPU, by the build thread (no GPU).
2. T1 build, with a speed probe first; T1's screen on the PC after q39 (expected about 9 PM to midnight ET tonight).
3. T1's sealed 6-seed confirm (seeds 200-205) if the screen passes. O1 starts only after T1 passes it. If T1 is "not shown", the named link fix runs first and the ladder waits.
4. K1, then O1 (if not empty), N1, P1 in that order, then V1, L1 and ST1 (H1 when the roadmap has it), then the B3 confirm.
5. W1, U0 and U2 screens whenever a machine is free; they don't wait for T1.

Rough cost (untested estimate): the q33 B2 runs took 1.0-4.2 h on the PC (median 1.5 h; 0.7-1.2 h on the rented 5090s), depending on how many jobs shared the GPU. A T1 chain row needs about 5-6 reader-plus-8-round passes instead of one, so T1's cost per run is unknown until the speed probe. The ladder is about 20 runs (T1: 6, K1/O1/N1/P1: 2 each, B3: 6) plus 6 for the gain tests. At 3x B2's median that is roughly 80 GPU-hours for the ladder, about 3-4 PC days run one at a time, less with 2-3 sharing the GPU. Rented 5090s would need the B2 baseline re-run on the same box for each comparison (same-machine rule), roughly doubling those runs; Vast credit is $5.22 and any spend needs Ben's OK.

## 6. What would change this plan

- **D0 reading below 99%:** reported as the baseline (Amendment 1), with its control; whether T1 waits is Ben's call. **D0 writing below 99%** stops T1 as sealed, unless the writing check moves to T1's screen, which the sealed file allows if it needs the T1 build.
- **T1 proved wrong** (more than 2.0 below B2, or chain-5 mean below 95): fix the named link first; the rest of the ladder waits.
- **The architecture thread does not re-seal T1's parity mark:** T1 almost certainly cannot pass its own confirm on noise alone (3c.1), and the ladder stops at T1 on a mark, not on a finding. That needs settling before T1's first run.
- **U0 shows word pieces beat letters by >= 2 on both seeds:** add a learned word-piece side channel next to the bytes (like EGE, from scratch), as a gain test.
