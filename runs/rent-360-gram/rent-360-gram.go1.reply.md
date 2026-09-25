Renting a GPU to run the registered gram-360 comparison — first syncing the worktree specs.
No duplicate run found — now checking the rental setup and model requirements.
Disk and model checks passed — now verifying rental credits and GPU availability.
Tree assembled and verified — now packaging it for upload to the GPU.
GPU instance requested — waiting for it to come online.
Instance is live with CUDA working — now staging the code and models.
Code uploaded — the large reader model transfer stalled, so retrying with resume.
Reader verified — now setting up the test environment on the GPU.
Run launched — monitoring progress on the rental.
Both arms finished cleanly — now collecting the scores and timing for the report.
Run artifacts are ready — copying them back to the Mac.
Files secured and instance destroyed — now writing the final report and ledger.
Report written — appending the cost ledger and verifying the push set.
VERDICT: DONE — registered gram-360 run on bank G completed on 1 rented RTX 5090, all steps exit 0, files copied back before destroy, instance gone. Grading marks (P360.1/P360.2) are NOT decided here — blind Opus graders run later.

MARKS TABLE (integer counts only, no reply text):
- Bank seal: 3/3 OK (turns, truth, README).
- gram360 tests: 16/16 OK. 338b: 3/3 OK. 333d: 2/2 OK. vary330c: 2/2 OK.
- P360: 250 rows / 10 lives, wall 190 s. P330c: 249 rows / 10 lives, wall 184 s.
- Twinb banner first line correct on 2/2 arms.
- Scorer P330c: user 194, confirm 55, clarify 15, creative 10 (0 writes), facts 71/134, day1 52 kept 52, new triples 81 (9 unsupported), nosave-writes 0, distinct 140, most-common 8, ms 771.1/1226.2.
- Scorer P360: user 194, confirm 56, clarify 15, creative 10 (0 writes), facts 71/134, day1 52 kept 52, new triples 80 (9 unsupported), nosave-writes 0, distinct 142, most-common 8, ms 768.0/1235.6.
- Checker: P360.3 PASS (flag 0, answer 0, ask-class 0), P360.4 PASS (word losses 0); rows 250, rule parts 183, changed 68, nonrule parts 103, nonrule changed 0, replies changed 62, distinct rule_raw 154, rule_final 154, all_final 193.
- Tracebacks: 0.

MOVES / MISSES / DEVIATIONS:
- Moves: none vs spec — ran exact commands, sidecar absent before P360, no GRAM360_LOG on control.
- Misses: none — all 5 steps ran once, exits 0.
- Deviations: (1) READER upload needed rsync resume (~120 MB second pass) — env only, code untouched. (2) One ssh launch timed out after starting nohup but job survived via setsid — no duplicate process (ps showed 1). (3) Hours/dollars are estimates from vast.ai duration (~0.60 h × $0.5037 ≈ $0.30) since per-instance billing isn't API-readable.
- Money: contract 52513907, offer 45669186, RTX 5090, dph $0.5037037, ~$0.30 of $1.50 budget, credit $1.90 at start. Post-destroy 0 rent-360-gram live.
- Models: BASE 87179e5c1f455ef22e6223592d2d61351b525bfc (expected), READER b4fd93a2 match, self122 5ca02173 match.
- Independence: bank turns/truth never opened/printed/quoted; grammar_*.jsonl, judge_*.jsonl, check/*.jsonl never opened; no reply quoted; code unedited (git-archive tree, main on top).

WHAT IT MEANS IN PLAIN ENGLISH: Like baking two identical cakes where one gets extra frosting (the grammar fixer) — both baked fine and we measured them the same way. The frosting changed 68 spots in 62 cakes slices and broke nothing it shouldn't (checker PASS). Whether the frosting actually tastes better (90%+ grammatical, +20 points) is decided later by blind taste-testers, not by me.

PUSH: artifacts/claude-gram360-20260925/RESULTS-rent.md artifacts/claude-gram360-20260925/run artifacts/claude-gram360-20260925/score artifacts/claude-gram360-20260925/check artifacts/fable-predictions-ledger.md
