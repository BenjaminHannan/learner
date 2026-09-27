# rd-378g addendum L (2026-09-27 12:12:07 UTC): the BensPC run goes through a builder-free kit, with a disk floor

Written after SEAL-B (1c2d4461b) and before any BensPC step for rd-378g has run. The runner changes; the experiment
does not. PASSMARKS.md and addenda A-K stay as sealed; this file adds to them.

## Why
- Runner. The Thread manager asked for this at 12:0x UTC. rd378g-pc2 was an LLM-builder job, and the free builders stall
  (Director, 11:12 UTC, on the same kind of y1t job). A builder that stalls mid-training would hold the GPU with no stop
  path. rd378g-pc2 was pulled back to held/ before it launched (5d7456382; now handoff/held/rd378g-pc2-q.md, never run).
- Disk. BensPC C: had 5 GB free at 11:07 UTC. Ben's floor is 3 GB (his choice at 01:30:47 UTC). G's merged model is
  about 2.3 GB (bf16), and R's merged model, if it must be copied from the Mac, is about 2.1 GB.

## The runner (procedure only)
- handoff/kit/rd378gpc runs the steps of handoff/held/rd378g-pc2-q.md with the same commands and settings, as fixed Mac
  bash passes (BASH-ONLY queue jobs, GPU: yes) that drive a detached Windows chain on BensPC. It follows the tested y1tpc
  and sleep358s kits, and it was run against a mock BensPC before sealing (launch, running, stalled, died, collect, and
  the seal, kit, pin, lock, busy, disk and selftest refusals).
- The tree is C:\Users\benja\rd378g2\tree, made once from `git archive` of the pinned commit. The kit's own files are
  checked by sha256 against that commit before every pass.
- Before launch: the seals (SEAL-B 8 of 8, SEAL-ADD-K 6 of 6, SEAL-ADD-A and B 5 of 5, SEAL 13 OK with only
  scripts/claude_lis300_train.py FAILED, which ADDENDUM-A replaces), the four selftests, the MiniLM snapshot and the
  LoCoMo file hash. Any miss stops the pass with nothing launched.
- The chain:
  - dialogs59: its hash (CR removed) must be rd-378u's;
  - train G: same command and settings; on out-of-memory it retries once with --batch 8;
  - dev format check: dev_unparsed <= 2% (G4's DEV check);
  - LoCoMo 5-9 write and store v4 score;
  - the when-off score;
  - the two G5 writes (G, then R).
- The chain stops at the first failure of dialogs, train, dev check or the LoCoMo write. The two scores and the two G5
  writes each stop only themselves.
- The kit never edits sealed code, never stops or deletes anything on BensPC, never starts the chain twice and never
  relaunches a chain that died.
- LoCoMo files (dialogs59, G's notes on it, per_question) stay in C:\Users\benja\rd378g2-private and ~/rd378g-private
  on the Mac, outside git. Kit output prints counts and hashes only (plus write-time median and p90, report only).

## Where the results land
- The run's files go to artifacts/claude-rd378g-20260926/benspc/: notes_confirm.json, ranked_turns.jsonl (positions
  only), notes_confirm_whenoff.json, train/ (summary.json, train_log.jsonl, gdev.jsonl), logs/, steps.txt, checks.txt,
  gpu_log.txt and r-path.txt. The G5 notes go to g5/notes_G.jsonl and g5/notes_R.jsonl. rd378g-pc2-q named other
  folders; only the place changes.
- RESULTS-benspc.md is a run record with no verdict. The thread scores G1-G4 from notes_confirm.json, runs G5's blind
  judges, writes RESULTS.md, does a blind recount and writes the ledger line.

## The disk floor (the Thread manager's request, following y1t's ADDENDUM-7)
- R is used where it already is on BensPC: a model.safetensors with sha256 dbcc8db5...8510 in any
  premonition-models folder or in a folder named *rd378* (not *rd378g*) up to depth 3 under C:\Users\benja.
- If R is not on BensPC:
  - it is copied from the Mac (~/premonition-models/rd378-notes-merged, same sha256 checked on the Mac) only when C: has
    at least 9 GB free before the copy;
  - otherwise R's G5 write is skipped (R-SKIPPED), and G5 uses ADDENDUM-K's fallback: R's share is taken as 52%, so the
    bar is G at most 57%.
- The chain launches only when C: has at least 6 GB free (after any R copy). That leaves at least 3 GB after G's ~2.3 GB.
- G's merged model stays in the BensPC tree (no second 2 GB copy). Only G's adapter is copied, to premonition-models\rd378g
  on BensPC and to ~/premonition-models/rd378g-adapter on the Mac. Weights are never pushed.

## Unchanged
Everything the experiment measures:
- the rows (SEAL-B) and the trainer and its settings;
- the LoCoMo 5-9 test and the G1-G4 marks;
- G5 (ADDENDUM-K), including its judges, bar, fallback and wording;
- the proved-wrong lines and R = 585 of 772.
