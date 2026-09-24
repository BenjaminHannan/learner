Building the sealed listener stack — setting up the clean run tree.
I've mapped the sealed-panel constraints — now checking the prior reader job and staging the build.
Pre-checks pass and the prior job is clear — now assembling the combined build tree.
Both seals verify — now running the unit tests and system checks.
Baseline arm finished fast — now running the reader arms.
Baseline scored — now writing up the blocked result and staging the deliverables.
VERDICT: BLOCKED. lis-314/315/316 did not finish. Arm A (292t alone) completed all 354 panel turns and scored. Arm C crashed 3 dialogs in with the exact MPS out-of-memory error that blocked lis-313-f0. Arms P, K, S, G never ran. P315.1–3, P314.1–5, P316.1–3 are NOT scored. Sealed code never edited.

MARKS TABLE (honest version — nothing to PASS/FAIL without the reader arms):

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| P315.1 wrong-save turns (P vs C) | P ≤ C+1 | no arms | NOT SCORED |
| P315.2 facts saved (P vs C) | P ≥ C+5 | no arms | NOT SCORED |
| P315.3 questions (P vs C) | P ≤ C | no arms | NOT SCORED |
| P314.1 wrong-save turns (K) | K ≤ C+1, K ≤ 2 | no arms | NOT SCORED |
| P314.2 saved-or-pending (K) | ≥85% | no arms | NOT SCORED |
| P314.3 turns/question (K) | ≥8 | no arms | NOT SCORED |
| P314.4 asks right (K vs C) | K ≥ C+5 | no arms | NOT SCORED |
| P314.5 never-told asks (K vs C) | K ≤ C | no arms | NOT SCORED |
| P316.1–3 (G vs S) | — | no arms | NOT SCORED |

Arm A counts only (from run/summary.json, 354 turns): kind_teach 135, kind_ask 129, smalltalk 72, correct 10, other 8, questions_to_user 0, ask_right 17/109 told, ask_wrong 9, ask_abstain 83, untold 20 (all abstained), wrong_save_turns 15 / facts 15, final saved 41/175 = 23.4% (pending 0), CPU ms median 5.9, p90 15.9, max 3463.7. No K/S/G wrong triples exist (arms never ran).

EVERY MOVE: (1) Confirmed lis-313-f0 finished (builder-outbox commit, no reader process) before starting — one reader job at a time. (2) Built /tmp/lis314-build from fresh `git archive origin/builder-outbox` + fresh `git archive origin/main`, copied self122_head.pt (65,741 bytes). (3) Read PASSMARKS.md + run script; never opened/printed/quoted panel.jsonl, key.jsonl, label_B.jsonl, key_v2.jsonl. (4) Checks passed: panel seal 6/6 OK, code seal 9/9 OK, lis301-merged sha256 b4fd93a2… match, test 13/13, load ~20, disk 65 GB free. (5) Arm A OK (<90 s, PID 71944). Arm C (PID 72749) crashed alone during dialog d04 (d01–d03 done). Arms P/K/S/G deliberately not started — same deterministic wall. (6) Scored arm A only. Wrote RESULTS.md (verdict first), staged arm_A.jsonl, summary.json, both arm logs in artifacts/claude-lis314-20260924/, appended ONE BLOCKED ledger line. No push (no rights; watcher pushes).

THE EXACT ERROR: `RuntimeError: MPS backend out of memory (MPS allocated: 42.28 GiB, max allowed: 42.43 GiB). Tried to allocate 384.00 MiB.` Path: run() → turn310 → _base_pass_blocked310 → turn282b → snapshot260 (`copy.deepcopy`) → torch Parameter `__deepcopy__` → OOM. Identical reading (42.28/42.43) and mechanism as lis-313-f0: the per-turn snapshot deepcopy reaches the parked MPS reader's Parameters. Sealed smoke tests use a weightless fake reader, so this path was never exercised.

DEVIATIONS: (a) Panel seal verified from inside its dir (6/6 OK) — the sealed file lists bare filenames so the root-relative command can't match by construction. (b) uv run needed `--with transformers --with safetensors` for reader arms (code untouched, offline cache only; lis-313 precedent). (c) 11 scored ledger lines NOT appended — none earned; one BLOCKED line instead. (d) No git push by builder.

WHAT IT MEANS IN PLAIN HIGH-SCHOOL ENGLISH: The bare base keeps 41 of 175 taught facts (23%) and answers 17 of 109 questions, abstaining on the rest. Whether the three new wrappers fix that is still unknown on this Mac: attaching the real reader crashes the rig within 3 dialogs because each turn photocopies the giant model in graphics memory until it overflows. Nothing about the wrappers, weights, or panel is impugned — seals, checksums, 13/13 tests all passed. Listener-thread fixes (same as lis-313): keep the model out of the per-turn snapshot, or run reader arms on CPU.

PUSH: artifacts/claude-lis314-20260924 artifacts/fable-predictions-ledger.md
