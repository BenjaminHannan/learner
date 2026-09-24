Re-running the 1B reader benchmark — setting up the sealed tree and checks.
The benchmark files aren't in this worktree — I'll locate the sealed sources and build instructions.
I've got the pass marks and task spec — now checking prerequisites and assembling the combined tree.
Tree assembled with all scripts and benchmarks. Copying in the mouth weights and reading the required files.
F0 seal passes. The `echo ===` separator trips zsh — retrying without it.
Model hashes match. Running the two unit test suites.
All checks green. Recording uptime/disk, then launching the arms.
Arm A finished fast (286 rows). Launching arm C with the 1B reader.
Arm C at 26/40 dialogs. Continuing to poll.
Arm C complete, no crash — the fix holds. Launching arm D.
All three arms done. Scoring now.
MPS confirmed available. Writing a small analysis script for the triple/reply listings (outputs triples and agent replies only, never user turns).
All rows verified. Appending the ledger lines.
VERDICT: crash fix WORKS, marks MIXED — P312 2/4 PASS, P313 2/4 PASS, and the P313 proved-wrong wire fired (4 wrong answers from the wrapper itself).

Done in ~25 min of the 180-min cap. Listener code never edited; benchmark user turns never printed or quoted. PUSH paths ready in the worktree: `artifacts/claude-lis313b-20260924` (PASSMARKS.md, SEAL.sha256.txt, RESULTS.md, run/arm_{A,C,D}.jsonl 286 rows each, run/summary.json) + ledger lines appended.

Checks (all before running): F0 seal 2/2 OK; lis313b seal 5/5 OK; lis300-merged sha256 `112880d6…` and lis301-merged `b4fd93a2…` both match their RESULTS.md (lis-301 sealed T=0.995, the value used); `claude_lis313_test.py` 11/11; `claude_lis314b_test.py` 16/16; disk 53 GB free. Tree = fresh `git archive origin/builder-outbox` + fresh `origin/main` overlay, run from its root, self122_head.pt copied in. Device: Mac Apple Silicon, reader on MPS float16; ms_median A 5.3 / C 1254.9 / D 1244.7 ms (max 3934.0 / 3499.0 / 3228.7).

Marks table (integer counts):

| Mark | Bar | Result |
|---|---|---|
| P312.1 unexpected saves C vs A | C ≤ A+1 | PASS (0 vs 0) |
| P312.2 teach gold stored C vs A | C ≥ A+15 (of 84) | FAIL (14 vs 13, +1) |
| P312.3 clarifies C vs A | C ≤ A−15 (of 286) | PASS (117 vs 186, −69) |
| P312.4 asks right C vs A | C ≥ A | FAIL (2 vs 6; ask_wrong 11 vs 1) |
| P313.1 wrapper answers wrong | 0 | FAIL (4 — proved-wrong fires) |
| P313.2 right when gold stored | ≥ 90% | FAIL (11/26 = 42.3%) |
| P313.3 unexpected saves D vs C | D ≤ C | PASS (0 vs 0) |
| P313.4 asks right D vs C | D ≥ C+3 | PASS (11 vs 2, +9) |

Every move / miss: all 3 arms completed 286/286 turns, no OOM (lis-313-f0 had died at 13/40 dialogs). D's wrapper answered 13 asks: 9 right, 4 wrong; abstains fell 71→58 but ask_wrong rose 11→15. The 4 wrong: twice it answered "who is this person" when asked for a fact about them (gold job/city → reply naming the relationship), twice it repeated a stored fact disagreeing with gold (wrong city, wrong dog name). Non-gold teach saves (28 each in C and D, identical sets): mostly benign aliases (`job→occupation`, `color→favorite_color`, `turtle→pet`, `USER|relationship|Name` links) plus one wrong-relation save (a hobby stored as an occupation).

Deviations: none from the task — arm B dropped per instructions; one unpushed helper script (`scripts/claude_lis313b_report.py`) lives only in the /tmp build tree, not in PUSH paths.

What it means in plain English: the memory fix works — the run that used to crash now finishes. But at the strict threshold the reader barely raises what the assistant actually learns (1 extra taught fact of 84). It does cut "I don't understand" replies a lot. The answering wrapper gets 9 more questions right but invents 4 wrong answers where silence would have been better — that's the failed wire, and those 4 cases show exactly where the lookup goes wrong.
