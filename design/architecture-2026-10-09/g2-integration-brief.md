You are joining three new modules into one model class for a small research model (PyTorch, CPU only). Work ONLY in the git worktree
/tmp/claude-0/-home-user-learner/19da8247-aa04-522b-b334-bd26e0565d55/scratchpad/g2int (branch g2-int; it already merges B3 group 1 at 8fce7247a8, writer.py f29cde4457, the input switches 5aab74a520 and progtext/st1 f6695cbd4a). Commit there when done; do NOT push, do NOT touch other worktrees, do NOT write under /mnt/project-files (read only), no GPU,
do not call any mcp__hearthbot__ tools. Do not install packages.

Read first: /mnt/project-files/architecture/B3-GROUP2-BUILD-2026-10-09.md (the whole spec; sections 1-3 and 6-7 are your job). Then, in the worktree:
`custom_io/models/b3.py` (B3 group 1: loop, run with the learned stop, plan/schedule, b3_evals), `custom_io/models/tool_h1.py` (loss: per-round answer,
settled stop labels; h1_evals), `custom_io/models/tool.py` (calc, entry, tape_of / read_texts, span_keys (the e_s/e_e layout terms), drills,
extra_evals: call accuracy, noexec, chain-5 lesions, opswap via sources/replay, write_copy), `custom_io/models/writer.py` (ByteWriter: forward /
teacher / nll / right / greedy), `custom_io/models/progtext.py` (steps_of, text, entry, drill, report), `custom_io/st1.py` (the interface it expects from the model),
and the input switches no_slots / no_place / bytes (see git log for their commit). Match the repo's style (dense docstrings, short names).

Build `custom_io/models/b3g2.py`, class `B3G2(B3)`, registered as model 'b3g2' wherever 'b3' is registered:
1. __init__: everything B3 group 1 builds (any_round, gap_p, eg_embed, span_copy/span_idx/span_end/ans_drill, H1 stop with label 'settled'),
   plus no_slots / no_place (pass through) and as_written (default True). Then DELETE the heads the writer replaces (op_head, W_a, W_b, q_s, k_s, g_s,
   stop_s, mode_head, q_word, the word-key and word-content modules, the GEN pointer-generator ln_t / q_cp / k_cp / g_cp / its bias; check ledger.py
   and tool.py for the exact names), keeping e_s / e_e as the writer's copy-key layout terms. Create the ByteWriter LAST (tied to self.reader.tok),
   cap WCAP = max(tool.LE, data.MAX_ANS) + 1, inner and mlp from cfg. Deleting after creation keeps every other weight's init unchanged.
2. Tools: a registry {name: fn(rest_text) -> reply}; the calculator registers tool.NAMES[1:] (rest must be exactly two whitespace-separated tokens,
   else '?'). The harness splits a written call at its first space; unknown name -> '?'. Lesions noexec (every reply '?') and opswap (add <-> sub)
   act inside the dispatch. Record calls as (t, name, a, b, reply) with a, b the two tokens when there are two (else (t, name, rest, '', reply)), so
   Tool.sources / replay / write_copy / opswap work unchanged. Tape entry text = f'{call} = {reply}' (tool.entry's form, cap LE, counted, never cut).
3. Gold: per row, progtext.steps_of(row, self.as_written); drills as Tool.train_golds does (prob ans_drill, the model's own random.Random stream,
   progtext.drill); call text f'{op} {a} {b}'; reply = calc's (assert it equals the step's result; teach the tool's real reply, never the label's);
   answer text = the row's answer (or the drilled one). Rows with no steps: no calls. Count unreadable rows (capcount or plan_stats).
4. loop(): B3.loop without number slots (no_slots) and without word keys; after each round t >= 1 the writer is asked "call?" (mode 0):
   - teacher forcing: on group 1's schedule: call rounds -> the gold call text; rounds after the row's last call -> empty target (EOS only);
     gap rounds -> no target. Context = [prompt X; tape Xt] with mask [xm; entries visible BEFORE this round's call], ids [prompt_ids; idt],
     ckeys = the e_s/e_e layout terms (factor span_keys so the layout terms can be had without k_s). Z = all thinker vectors (zmask all true).
     Run the writer only on rows that have a target this round. Call loss = sum over rounds of mean over rows of (nll * w_row * has_target),
     w_row as B3's op loss (1.0 rows with calls, w_noop otherwise).
   - free run: writer.greedy(mode 0) on every row still running; empty text = no call; tape full -> not run, counted (group 1's tape_full).
   - `each` / learned stop exactly as B3.run (state kept at each row's own stop round).
5. Per-round answer (H1): at every round t >= the row's last call round, the writer is asked "answer" (mode 1), teacher forced on the answer text;
   answer loss = the row's mean over those rounds (H1's rule), checkpointed as H1 does. "Right at round t" = writer.right (teacher-forced argmax
   equals the gold at every position). Disclose: with the selective-read feedback this approximates greedy decoding; extra_evals reports how
   often the label agrees with real greedy decoding on dev rows. Stop head: H1's, on ln_z(control 1) detached, BCE on settled(right).
6. state_of / talk / generate: state = (Z, Xt, idt, vis); talk = writer.greedy(mode 1) over [the CURRENT batch's prompt X; the state's tape], so
   donor swaps work as today. Make every lesion in the model's LESIONS work (zero_state / shuffle_state act on Z; nocopy forces the writer's gate;
   loops:K; donor); drop lesions that no longer apply (nowordc) from LESIONS with a one-line note.
7. ST1 interface for custom_io/st1.py: sample_traces(batch, temperature, generator) (free run, writer sampling for calls and answer) and
   trace_loss(batch, traces) (the normal loss with the given traces in place of progtext's).
8. extra_evals: call accuracy on the call TEXT (teacher forced and free run; a call is right when its text equals the gold call text), noexec and
   the chain-5 lesions, opswap, write_copy (reuse Tool's code paths; they need only run / talk / calls), h1_evals, b3_evals, plus: the
   writer's copy share, rows whose free-run answer is right vs the teacher-forced 'right' label, and the inventory-relevant counts (rows with
   a 'hidden' operand under as_written and their exact match). Drop evals that read deleted heads (copy_gate) with a note.
   The sealed marks for group 2's 3M run (/mnt/project-files/big-run/PLAN.md section 5, block "G2 step 2b", read it) need, in extra_evals or the
   standard eval path: pooled-5 and chain-5; thinker-off (`loops:0`) and the donor leak; calculator-off on program questions; exact match on the dev
   rows of the families progtext reports as touched by the inverse rewrite (B3G2-4, with the row count); H1's marks incl. the free `loops:32`
   lesion; B3's length buckets (b3_evals); and every cap counter including a new capcount key `writer_over` (custom_io/capcount.py: add it to
   the documented list) and the no-trace count. Make sure each of these is in the result json the analyzer reads (custom_io/analyze_8a.py
   b3_report: extend it for b3g2).
9. Config and size: `g8a/configs.py`: B3_G2 = B3_G1 + dict(no_slots=True, no_place=True, bytes=True, as_written=True); b3g2_cfg(rung) on the same
   path as b3_cfg; the 3M count must sit within 2% (PLAIN_BAND) of g2c3's 4,022,440 trained (trim the writer's MLP first, then the thinker's
   feed-forward ratio; disclose in the table); 10M/30M by block count in band; 100M = 21 x 512, no band. Add the rung table rows (trained, frozen
   Gemma, whole). Register b3g2 in caps.py's module list and job.py's arms (arm 'B3G2', --b3 caps), and in b3_cost.
10. Tests: `custom_io/tests/test_b3g2.py` (CPU, prints ALL OK; stub Gemma as in test_b3.py): no forward path touches a deleted module; teacher-forced
   loss is finite and every trainable parameter gets a gradient; free run with a scripted writer: calls dispatch, unknown tool '?', replies
   visible next round, tape full counted; noexec and opswap change replies; drills deterministic; a tiny training run on synthetic rows at
   2,000 bytes where the loss falls and free run writes calls and answers; extra_evals run on a tiny synthetic dev dir; the size table.
   `custom_io/tests/test_b3g2_run.py`: train.py end to end for a few steps with --model b3g2 (as test_b3_run does for b3). Re-run test_b3,
   test_b3_run, test_g8a, test_writer, test_progtext, test_st1, test_g2_input: all must still pass.

11. Notes (spec Addendum A; read it): progtext.steps_of(row, as_written=True) also yields note steps dict(op='note', text=..., result='').
   Their call text is progtext.text(step) (`note <step text>`), the tool registry has `note` (runs nothing, replies ''), and the tape entry is
   progtext.entry(step) (the call text itself, no ' = '). Calls and notes mix in step order; ('res', k) operand sources count note positions
   (progtext's k). A row whose steps are all notes still trains a full trace. Entries longer than LE count `tape_entry_over`, writer targets
   longer than WCAP count `writer_over`; never cut either.
12. Counters: B3G2 must count `steps_unparsed` (custom_io/capcount.py, already added by group 1: a row with worked steps but no calls) and a
   `no_trace` count (rows with non-empty steps whose steps_of list is empty); both are expected 0 under as_written and must reach the result
   json. Add `writer_over` to capcount NAMES and its docstring.
13. H1 stop loss: tool_h1.py's loss already weights the 'settled' stop loss by w_stop = 1.0 if label == 'right' or n >= cap else 0.0 (a
   batch shorter than the 32-round cap cannot see later rounds; logged as stop_w). If B3G2 computes its own stop loss, apply the same rule
   and log stop_w; never compute 'settled' over fewer than cap rounds with weight 1.

14. Writer details (spec Addendum B; writer.py docstring): train every writer call with forward(..., refine=cfg writer_refine, default 1);
   greedy returns (out, ended); `tok` is held in a list (not a submodule), so the model's reader owns and optimises it; a row with no visible
   context gets gate 1. Tests on these tiny models: torch.set_num_threads(1) at the top of main() (4 threads ran ~100x slower here).
   extra_evals reports the teacher-forced-right vs greedy-right agreement on dev rows.

Commit with a clear message ending with these two lines exactly:
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SAF2nyVsUPVemmjPa1ssA7

Final answer: commit sha, files, every test's last lines, the rung table, the deleted module list, and every place you had to choose something the
brief did not say (with your choice).

Facts from the helpers who built the parts (check them against the code):
- Input switches are plain cfg keys: `bytes` and `no_place` go through Ledger.__init__ (so Tool, ToolH1, B3), `no_slots` is on B3; a bytes /
  vocab mismatch is refused; CharVocab and ByteVocab both have length / clip / offsets. Tool.num_memory is split into num_memory / slot_kv /
  join_kv. Under caps_b3.json, b3_cfg('3M') with bytes + no_place + no_slots is 4,019,126 trained (before deleting heads and adding the writer).
- Run every test with OMP_NUM_THREADS=1 (4 threads on this busy 4-core box made tests 10-100x slower and some got killed). Run long tests in
  the background writing to a log file with the exit code appended (`> log 2>&1; echo rc=$? >> log`), never piped through tail.
- test_tool, test_tool_span, test_ledger_copy, test_ledger_span and test_tool_h1 need sk200k data files that are not here: skip them and say so.
  test_g8a prints no ALL OK line (exit 0 and its last `ok` line are the pass).
