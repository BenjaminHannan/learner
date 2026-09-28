# rsn-358u2: re-run of rsn-358u's 4 loop nets (plan, written 2026-09-28T00:05:43Z, before any training)

Written by a stand-in chat acting for the stopped sleep research thread on this one job, under Ben's prompt of
2026-09-27 23:45 UTC. Additive: nothing in artifacts/claude-rsn358u-20260927/ changes, and 358u's verdict (PASS) stands on its own run.

## Why
slp-358n3 (the sealed sleep gate) starts from rsn-358u's 4 loop nets. None of them reached the Mac:
- 358u's guard copy-back broke on a broken pipe at 77 of 78 files (loop-s13/final.pt truncated), so instance 52964920 was stopped
  with the files on its disk.
- rent358u-4-recopy (18:55 UTC) and rent358u-4b-recopy (19:45 UTC): NO-START, the instance stayed "exited" for 15 min.
- rent358u-4c-recopy (2026-09-28 00:00 UTC): the instance started and ssh answered within about 1 min, but all 8 copies came back
  empty (sha256 e3b0c442..., the hash of an empty file), so it printed RECOPY-INCOMPLETE-STOPPED. The job ran each copy under
  `timeout`, and other jobs on the Mac have printed "command not found: timeout", so the copy command most likely failed on the
  Mac and the files are most likely still on 52964920's disk (suggested, not checked).

Ben's rule for this prompt: after NO-START or RECOPY-INCOMPLETE, retrain the 4 loop runs. **52964920 stays stopped with
358u's original files. It is not destroyed here.** It keeps costing a small storage charge; Ben decides what to do with it.

## What runs (358u's sealed code and settings, unchanged)
- Code: pinned commit, checked on the rental against 358u's SEAL-code (20 of 20), plus 358u's selftest and check-mask.
- The 4 loop runs only, seeds 13-16: `python -B scripts/claude_rsn358u_run.py train --arm loop --seed <s> --out W/loop-s<s>`
  (defaults only), then sha256 of each final.pt into this folder's SEAL-run.sha256.txt, then V1 poison once and eval once on
  artifacts/claude-rsn358i-20260926/tests, the same commands as 358u. torch 2.11.0+cu128 is pinned, fail-closed.
- The plain runs are not retrained (n3 does not use them).
- Machine: one vast RTX 5090 (reliability >= 0.98, >= 16 CPU cores), as 358u. Kit: handoff/kit/sleep358u2v/ (copy of 358u's).

## What differs from 358u's run (disclosed; none of it is in the sealed code)
1. 4 runs share the GPU instead of 8, and the host may differ. GPU training is not bit-identical from run to run anyway, so the
   re-run nets are new nets from the same recipe and seeds, not copies. That is why there is an acceptance mark below.
2. Kit: a new host gets 15 min to answer ssh, not 8 (358u's first 2 hosts stayed "loading" for 8 min).
3. Kit: copy-back. The small files come back in one tar (up to 3 tries). Each final.pt comes back one file at a time through a tmp
   file and is kept only if its sha256 matches both the rental's own manifest and SEAL-run (up to 3 tries per file). The instance
   is destroyed only after all 4 are verified on the Mac; otherwise it is stopped, not destroyed. No `timeout` command is used.
4. Money: the guard stops at $2.50 (cap $3, under Ben's $4 per job) or 3 h 30 min from the first rental.

## Acceptance mark (fixed now, before any training)
The re-run is accepted as n3's base only if BOTH hold:
- **A1 (358u's V0):** steps_block_nograd = 0 in the train_summary.json of each of the 4 re-run loop nets.
- **A2 (close to 358u):** the 4-seed loop mean of `right` (of 300) is within 15 points of 358u's on both report tests:
  - sums8: 358u 274.25, so the re-run mean must be in [259.25, 289.25];
  - grids7: 358u 184.00, so the re-run mean must be in [169.00, 199.00].

If A1 or A2 is missed (or fewer than 4 loop nets come back), stop and report; slp-358n3 does not run on these nets.
Everything else (the other tests, V1 poison) is report only.

## Predictions (before any run)
- A1: 95%. A2 sums8: 85%. A2 grids7: 65% (358u's own loop grids7 ranged 145-211 across seeds). Accepted: 60%.

## Estimate (inferred, not measured)
358u trained 8 runs at once on one 5090 in about 90-102 min. 4 at once: about 60-100 min, plus about 5 min of evals and up to
15 min per host that fails to start. About $0.60-1.20 at about $0.50/h.
