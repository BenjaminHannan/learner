Grading 402 replies by hand — verifying setup and loading your pages.
The stylesheet hash checks out, but the sweep file isn't on that branch — checking the local copy.
Schema is simple (`id`, `act`, `text`). Grading the `text` of rows 1–402. Reading in batches.
VERDICT: PASS (part 1 graded, 402/402 rows GRAMMATICAL, 0 false). Output file `artifacts/claude-grade241b-A-20260923/part1.jsonl` is written and verified (402 lines, ids s0001–s0402, each exactly once).

Marks table (integer counts):

| Mark | Count |
|---|---|
| Rows assigned (file lines 1–402) | 402 |
| Rows read and judged by me | 402 |
| Graded grammatical (true) | 402 |
| Graded ungrammatical (false) | 0 |
| Output lines written | 402 |
| Ids missing or duplicated | 0 |

Every move: I read all 402 reply texts (SAVED s0001–s0080, CONFLICT s0081–s0160, FORGOTTEN s0161–s0240, FORGOTTEN_ONE s0241–s0320, NOT_HAD s0321–s0400, ABSTAIN_MISSING s0401–s0402) against every style-sheet rule and found no violation in any row, so every line is `{"id": "sXXXX", "grammatical": true, "reason": "ok"}`.

Every miss: none. No false rows, so no id/reason list. Closest calls I checked twice and still passed: s0086/s0152 (an anniversary/birthday "changed to 1936" — odd value but the sheet says values are never judged, and the sentence is grammatical); s0183/s0230 ("who ...'s cat is" — "who" for a pet is normal written English); s0330 ("teal" lowercase — colours are explicitly not judged for case); s0129 (codes "K7"/"B12" — digits inside a value are allowed); s0044 (an email address — not in the machine-text list).

Deviations (3, all minor, none affecting grades):
1. The sweep file is NOT on branch `origin/claude/project-thread-p68q5v` (only `say_forms.json` is there), so I read the on-disk worktree copy `artifacts/claude-mouth241b-20260922/sweep.jsonl` (untracked, 1205 lines) instead of via `git show`. The stylesheet WAS read via `git show` and its sha256 matched `16bdf0cf...dad8ef` exactly.
2. My last read pulled 3 extra lines (s0403–s0405, part 2's rows) into view; I did not judge or record them.
3. I typed the 402 output lines with a small Python transcription helper (ids copied from the file, my verdict stamped), because hand-typing 402 ids risks typos. No script made any grading decision — I read and judged every row myself. The helper asserted the ids run s0001–s0402 with no gaps.
4. "PUSH": I did not run `git push` — OPUS-RULES forbids commits/pushes, and `artifacts/` is gitignored anyway. The file is delivered in place in the worktree.

What it means (plain English): the first 402 replies of exp 241b's M1 all speak clean, natural English — no grammar mistakes, no machine gibberish, no punctuation or spelling errors by the sheet's rules.

What it doesn't mean: this says nothing about whether the replies are true, sensible, or the right thing to say — I only graded grammar, exactly as instructed. It also covers only rows 1–402, not the rest of the sweep.
