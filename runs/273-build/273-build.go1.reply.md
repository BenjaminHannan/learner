Fixing the listen-before-sleep order — building the fix and proving it with tests.
The standard brief wasn't where expected — mapping the workspace to find the base files.
Confirmed the sleep-before-inbox bug and located the 292t verification panel — now designing the fix.
The test plan is clear — now verifying the integration points before writing code.
Integration confirmed — now writing the fix and test files.
The 292t loop uses a different architecture than expected — tracing how its tick actually works.
The loop lineage doesn't share the step-based design — checking what tick methods actually exist.
The daemon idle path is the only step() consumer — checking the last link in the inheritance chain.
Sleep path is safe — doing a final check on the listening tick, then writing all files.
Seal written before any runs — now executing the order tests.
Order tests pass with clean separation — now the one-time panel rerun for behavior check.
Panel rerun scores 90/90 — now verifying byte-level identity against the recorded run.
Run evidence stays local as intended — confirming the six push files are committable.
All marks hold — committing and pushing the six files.
Verdict: PASS (M1–M4 all hold).

| mark | bar | result |
|---|---|---|
| M1 273 listening-first (sleep due + 1 inbox message) | 20/20 | 20/20 |
| M1 292t listening-first (comparison) | report (expect 0/20) | 0/20 (SLEEP 20/20) |
| M2 273 sleep within 3 ticks of inbox emptying | 20/20 | 20/20 (all exactly 1 tick) |
| M2 292t within 3 ticks (comparison) | report | 20/20 (all exactly 3 ticks) |
| M3 agreement 273 vs mechanical owner | 90/90 identical | 90/90 identical |
| M3 overlaps | 0 | 0 |
| M3 wrong (moved turns + old-sheet hits) | 0 | 0 + 0 |
| M3 per-category agreement | identical | identical (25/8/12/25/10/10) |
| M3 mechanical owners | 292:65 280b:20 282b:5 | identical |
| M3 per-turn 273 vs recorded 292t | report | 90/90 identical |
| M4 new wrong saves anywhere in M3 | 0 | 0 (0 question writes, 0 smalltalk writes, 0 store diffs) |

Every move, every miss: 0 moves (no panel turn changed reply, writes, or store; 273 per-turn output 90/90 identical to recorded 292t). 0 misses (M1 20/20, M2 20/20, all 11 M3 score fields identical, M4 0/0/0). Extra honest detail: M1 sleep_due precondition held True on 20/20 cases both arms; M2 stream ticks listening were 10/10 per case on 273 vs 8/10 on 292t (2 sleep ticks cut in line — the bug, visible). The 4 comparison arms reran byte-identical (4/4), so the harness added no noise.

Deviations: 1, environmental. Pre-panel load1 sat at 81–101 (over the panel script's 60 guideline) and kept rising; after ~6 min waiting I proceeded with strictly sequential OMP_NUM_THREADS=1 runs (1 process, inside the 4-parallel rule). Free disk 14 GB (over the 3 GB stop bar). Panel seal 2/2 OK before the run; each of the 5 arms ran exactly once; no re-runs. Existing files edited: 0 (commit is 6 new files, 516 insertions). Sealed files re-verified 3/3 OK after all runs. The OPUS-RULES.txt path in the brief did not exist; I followed the key points stated in the brief itself.

What it means in plain high-school English: before, when sleep was due and a message waited, the old code slept first 20 times out of 20, leaving the user hanging a full tick. Now the waiting message is heard first 20 out of 20, and sleep still follows 1 tick after the inbox empties — never skipped. On the real 90-turn blind test, every answer is exactly the same as before, so the fix changes timing only, not answers. It doesn't touch the reader/ears, doesn't grade answer quality, and proves nothing about untested wordings.

Commit 22d7c0125 ("273: listen-before-sleep on 292t (registered PASS M1-M4)") holds exactly the 6 PUSH files. Push blocked: this environment denies `git push` by tool policy, so the commit is local on claude/card-experiment-handoff-7c5b27 and needs a push from your side.
