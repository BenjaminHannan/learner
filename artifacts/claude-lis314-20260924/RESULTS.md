# lis-314 / lis-315 / lis-316 — builder RESULTS (Mac, sealed confirm panel)

VERDICT: BLOCKED. No mark is scored. Arm A (292t alone) completed all 354 panel turns and was scored. Arm C crashed 3 dialogs in with the exact MPS out-of-memory error that blocked lis-313-f0. Arms P, K, S and G never ran. P315.1-3, P314.1-5 and P316.1-3 are NOT scored. The sealed code was never edited.

## Marks table (honest version — nothing to PASS/FAIL without the reader arms)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| P315.1 wrong-save turns (P vs C) | P <= C + 1 | no arms P/C | NOT SCORED |
| P315.2 taught facts saved (P vs C) | P >= C + 5 points | no arms P/C | NOT SCORED |
| P315.3 questions to the user (P vs C) | P <= C | no arms P/C | NOT SCORED |
| P314.1 wrong-save turns (K vs C) | K <= C + 1 and K <= 2 | no arms K/C | NOT SCORED |
| P314.2 taught facts saved or correctly pending (K) | K >= 85% | no arm K | NOT SCORED |
| P314.3 turns per question (K) | K >= 8 | no arm K | NOT SCORED |
| P314.4 asks answered right (K vs C) | K >= C + 5 asks | no arms K/C | NOT SCORED |
| P314.5 never-told asks answered with a value (K vs C) | K <= C | no arms K/C | NOT SCORED |
| P316.1 wrong-save turns (G vs S) | G <= S | no arms G/S | NOT SCORED |
| P316.2 taught facts saved or correctly pending (G vs S) | G >= S - 2 points | no arms G/S | NOT SCORED |
| P316.3 questions to the user (G vs S) | G <= S + 3 | no arms G/S | NOT SCORED |

## summary.json counts (only arm A exists; arms C, P, K, S, G have no files)

Arm A (292t alone, 354 turns): turns 354, kind_teach 135, kind_ask 129, kind_smalltalk 72, kind_correct 10, kind_other 8, questions_to_user 0, ask 129, ask_right 17, ask_wrong 9, ask_abstain 83, ask_untold 20, ask_untold_abstain 20, asks_told 109, wrong_save_turns 15, wrong_saved_facts 15, final_facts 175, final_facts_saved 41, final_facts_saved_or_pending 41, final_pending 0, facts_saved_pct 23.4, facts_saved_or_pending_pct 23.4, turns_per_question 354.0.

Device and ms (arm A, CPU only, no reader): ms_median 5.9, ms_p90 15.9, ms_max 3463.7. No reader device timing exists (arm C died before writing its file).

## Wrong saved facts for arms K, S, G

None to report: arms K, S and G never ran, so no stored triples exist. (Arm A is the bare base, not a wrapper arm, so its 15 wrong-save turns are reference-only and out of scope for this section.)

## THE EXACT ERROR (arm C)

`RuntimeError: MPS backend out of memory (MPS allocated: 42.28 GiB, other allocations: 720.00 KiB, max allowed: 42.43 GiB). Tried to allocate 384.00 MiB on shared pool.`

Traceback (sealed code, unmodified): `scripts/claude_lis314_run.py:136 run()` -> `scripts/claude_lis310_agent.py:394 turn310` -> `scripts/claude_lis310_agent.py:273 _base_pass_blocked310` -> `scripts/claude_fix282b_vocab.py:205 turn282b` -> `scripts/claude_fix260_openers.py:291 snapshot260` (`copy.deepcopy(v)`) -> torch `Parameter.__deepcopy__` -> OOM. The stack parks the live 1B reader (lis-301 merged) on the loop; every turn's snapshot260 deepcopy chain reaches the model's MPS Parameters and retains memory until the fixed ~42.4 GiB pool cap. Arm C died during dialog d04 after completing d01 (8 turns), d02 (8 turns), d03 (9 turns). This is the identical mechanism and identical allocation reading (42.28/42.43 GiB) as the lis-313-f0 arm B crash. Arms P, K, S, G run the same turn310 -> snapshot260 path with the same reader, so they would hit the same deterministic wall; they were deliberately not started.

## EVERY MOVE

1. Confirmed lis-313-f0 finished (origin/builder-outbox commit "builder results: lis-313-f0"; no lis reader process running) before starting, so only one reader job was on the Mac.
2. Built the combined tree in /tmp/lis314-build: fresh `git archive origin/builder-outbox`, overlaid fresh `git archive origin/main`, copied artifacts/fable-self122-20260922/self122_head.pt (65,741 bytes) from the Mac worktree. All runs from /tmp/lis314-build.
3. Read artifacts/claude-lis314-20260924/PASSMARKS.md and scripts/claude_lis314_run.py. Never opened, printed or quoted panel.jsonl, key.jsonl, label_B.jsonl or key_v2.jsonl; the runner read them itself.
4. Checks, all passed: panel seal 6/6 OK (run from inside artifacts/claude-lispanel314-20260924 because SEAL.sha256.txt lists bare filenames); code seal 9/9 OK from the tree root; lis301-merged model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match); claude_lis314_test.py 13/13 passed; uptime load ~20, disk 65 GB free (1G-blocks Available).
5. Ran arm A OK (354 rows, <90 s). Ran arm C in the background (PID 72749); it crashed alone during d04 with the error above. Arms P/K/S/G not started (same deterministic wall). Scored the run dir (arm A only) to summary.json.
6. Wrote this RESULTS.md (verdict first). Staged arm_A.jsonl, summary.json and the arm A / arm C logs here. Appended ONE factual BLOCKED ledger line (no scored lines earned). No push by builder (no rights; the watcher pushes).

## DEVIATIONS

(a) Panel seal command had to run from inside the panel directory (6/6 OK) because the sealed file lists bare filenames; the task's root-relative form cannot match by construction. (b) `uv run` needed `--with transformers --with safetensors` added for the reader arms (the reader imports them; sealed code untouched; cached offline packages only) — same as lis-313-f0. (c) 11 scored ledger lines NOT appended — none earned; one BLOCKED line instead (P313 BLOCKED precedent). (d) No git push by builder.

## WHAT IT MEANS IN PLAIN ENGLISH (high-school version)

The bare talking base, with no reader, keeps 41 of 175 taught facts (23%) and answers 17 of 109 asked-about facts correctly at the end, abstaining on 83. Whether the confirm-at-use / per-fact-release / guards wrappers fix that is still unknown on this Mac: the test rig crashes as soon as the real reader model is attached, because every turn photocopies the giant model inside the graphics chip's memory until it overflows — 3 dialogs this time. This says nothing bad about the wrappers, the reader weights, or the panel — the seals, checksums and all 13 stub tests passed. Fix options for the listener thread (same as lis-313): keep the model out of the per-turn snapshot, or run the reader arms on CPU.
