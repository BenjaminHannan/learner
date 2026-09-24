# lis-313 F0 result: BLOCKED (arm B crashed, C/D never ran; no marks scored)

Builder run 2026-09-24 on the Mac (CPU/MPS, no GPU rental). Sealed code run
unmodified; no existing file edited. The four-arm run did not complete, so
P312.1-P312.4 and P313.1-P313.4 are NOT scored and no ledger score lines were
earned (one factual OUTCOME line appended instead; see Deviations).

## Verdict first

BLOCKED. Arm A (292t alone) finished: 286/286 turns, scored. Arm B (292t +
lis-300 reader, T = 0.995) crashed 13 dialogs in with an MPS out-of-memory
error and wrote no output file. Arms C and D were never started: they use the
same code path and the same size reader, so they would hit the same wall.
The failure is in the sealed scripts' composition on MPS, not in the
benchmark or the weights. Fix belongs to the listener thread (see Mechanism).

## Pre-run checks (all passed, from the combined-tree root)

- `shasum -a 256 -c artifacts/claude-convbench-f0-20260923/SEAL.sha256.txt`:
  2/2 OK (dialogs.jsonl, README.md).
- Model hashes match RESULTS.md exactly:
  - lis300-merged/model.safetensors =
    112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0be8285324
  - lis301-merged/model.safetensors =
    b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890
- `python -B scripts/claude_lis313_test.py`: 11/11 passed.
- `uptime` at start: load ~79-127 (shared Mac, other agents active); disk
  71 GB free (start) / 63 GB free (end). No disk or time-cap pressure caused
  this; ~45 min of the 240 min cap was used.
- Sealed BEFORE running into artifacts/claude-lis313-20260924/SEAL.sha256.txt
  (verified 4/4 OK after the crash; seal covers files, run output came later):
  - PASSMARKS.md (lis-313): 2b4c86770b0d5ec61e11dda1cbdb6ef26e1537d6f403f33aa77660a26d66ef9e
  - PASSMARKS.md (lis-312): bf6a80ef571cb2bb96dbff1d64c98d5804496a9141d25774027e3d820ead9342
  - scripts/claude_lis313_f0.py: f95ac28cec6f1a0f05f1c97c16286104544f4144365e6d27e9817fcc193cad80
  - scripts/claude_lis313_agent.py: 5b9d43aff5dc9c131d5ae20ab3adecc65669f1996faca35774411c9504927f24

## The exact error (arm B)

After `[lis313/B] conv-f0-13 turns=7` (13 of 40 dialogs done, ~90 of 286
turns), the process died inside a turn with:

```
RuntimeError: MPS backend out of memory (MPS allocated: 42.28 GiB, other
allocations: 720.00 KiB, max allowed: 42.43 GiB). Tried to allocate
384.00 MiB on shared pool. Use PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 to
disable upper limit for memory allocations (may cause system failure).
```

Full traceback (kept in lis313-armB.log): `claude_lis313_f0.py run()` ->
`loop.turn(text)` -> `claude_lis310_agent.py turn310` ->
`_base_pass_blocked310` -> `loop.turn310_inner` -> ... -> `turn260` ->
`snapshot260` (`claude_fix260_openers.py:291`, `attrs[k] =
(v, copy.deepcopy(v))`) -> `copy.py` -> `torch/nn/parameter.py:79
__deepcopy__` (`self.data.clone(...)`) -> OOM. Both PIDs (uv wrapper and
child python) exited on their own; nothing was killed. No single turn hung
past 5 minutes; pace was ~2.5 min/dialog before the crash.

## Mechanism (from code reading only; no benchmark content involved)

- `install_turn310` stores the live Reader on the loop
  (`claude_lis310_agent.py:292`, `loop.lis310_reader = reader`), and the
  Reader holds the 2.1 GB model on MPS.
- Every turn, `turn260`'s `snapshot260` deep-copies loop-side structures, and
  the deepcopy chain reaches the model's torch Parameters (see traceback),
  cloning hundreds of MB per turn into the MPS pool.
- The pool cap is fixed at ~42.4 GiB. Crash at ~90 turns implies roughly
  450 MB retained per turn: arms C and D (same reader size, same wrapper
  family) would exhaust the same pool at about the same point, so starting
  them would only burn ~40 min each for the same wall. They were not started.
- The sealed smoke tests used a fake always-CHAT reader (no weights), so this
  path was never exercised before the real run. lis-311's 30-turn try-out
  stayed under the cap; 286 turns do not.
- Suggested fixes (listener's call, not done here): keep the Reader/model off
  the snapshotted loop (e.g. exclude it from snapshot260/restore260), or run
  the F0 reader arms with the model on CPU.

## Arm A counts (292t alone; the only completed arm; from run/summary.json)

| count | n |
|---|---|
| turns | 286 |
| clarify (all) | 186 |
| teach turns | 84 |
| teach_match (gold triple stored) | 13 |
| teach_other_new_triples | 7 |
| ask turns | 84 |
| ask_right | 6 |
| ask_wrong | 1 |
| ask_abstain | 77 |
| ask_gold_stored | 17 |
| ask_gold_stored_right | 6 |
| ask_gold_stored_abstain | 11 |
| smalltalk turns | 68 |
| smalltalk_clarify | 55 |
| other turns | 40 |
| other_clarify | 25 |
| correct turns | 10 |
| ms_median | 5.3 |
| ms_max | 2952.7 |

Device for arm A: rule chain only (no reader, no torch device involved).
Reader arms B/C/D: device would have been MPS (Reader auto-selects MPS on
this Mac); no reader timing was recorded because arm B died before writing
its output file. Per-turn ms above are rule-chain times, not reader times.

## Marks

- P312.1-P312.4 (need arms A vs C): NOT scored (no arm C).
- P313.1-P313.4 (need arms C vs D): NOT scored (no arms C, D).
- `summary.json` counts for B, C, D: do not exist. Only arm A counts exist
  (table above; full dict in run/summary.json).
- Teach-turn wrong-save triples for C/D and wrapper-answered asks for D:
  cannot be listed (no C/D runs). No benchmark user turn is quoted anywhere
  in this report or the logs (the runner script never prints them).

## Deviations from the task text (all disclosed)

- The COMMON RULES `uv run` line names only torch+numpy, but the reader arms
  import transformers+safetensors (`claude_lis300_read.py:21`). The sealed
  scripts were NOT edited; the run command only added the two cached,
  offline packages (`--with transformers --with safetensors`). The 11/11
  stub test used torch+numpy as written.
- Combined tree built as instructed: fresh `git archive origin/builder-outbox`
  extracted, fresh `git archive origin/main` overlaid, plus
  artifacts/fable-self122-20260922/self122_head.pt (65,741 bytes) copied from
  the Mac worktree (origin/main does not carry the .pt).
- Ledger: the 8 scored lines (P312.1-P312.4, P313.1-P313.4) are NOT appended
  because none was scored; one factual P313 OUTCOME/BLOCKED line is appended
  instead (precedent: the P294 HOST-FAIL line). Scoring lines must never
  exceed the numbers.
- No `git push` by this builder (no push rights in this environment; the
  watcher pushes the PUSH paths).

## What this means / doesn't mean (plain English)

- What it means: on this Mac, the 292t loop plus the real 1B reader cannot get
  through 286 conversation turns in one process; memory used by the graphics
  chip grows every turn until it hits a hard 42 GB ceiling and crashes. The
  baseline alone (arm A) understands little by itself: 13 of 84 taught facts
  kept, 6 of 84 questions answered right, 77 of 84 left unanswered.
- What it doesn't mean: it says nothing about whether the reader helps (arms
  B/C/D never finished), nothing about the reader's quality (weights and
  hashes verified fine), and nothing about the benchmark (its seal is intact).
  A fix to what gets copied each turn, or running the reader on the CPU
  instead of the graphics chip, could unblock the same sealed scripts.
