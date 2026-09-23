Writing your blind test panel — pulling the spec and building fresh items.
Spec is clear — now building the 60-turn panel.
Panel checks out — sealing the files.
Verdict: DONE — blind panel for exp 281 written and sealed. 60 turns, counts match the spec quotas.

Marks table (integer counts, turns):

| category | turns |
|---|---|
| stored_called (called/named/name-of, fact taught in-dialog) | 25 |
| nostore_called (same wording, fact never taught) | 10 |
| ambiguous_called (called belongs to the value/name) | 10 |
| teach_setup (control teach, gold = stored triple) | 10 |
| control_plain (plain possessive, no called/named) | 5 |
| total | 60 |
| controls (teach_setup + control_plain) | 15 |

Every move:
- Ran from the worktree root; `uptime` load ~44, `df -g /` free 12 GB (above the 3 GB stop line).
- `git fetch -q origin main`, read ONLY the 281 section of `design/v3/30-modes/280-282-chat-fixes.md` via `git show`. Did not open `scripts/`, `artifacts/claude-chatweak-20260923/`, or any other panel.
- Created `artifacts/claude-calledpanel281-20260923/panel.jsonl` (60 lines; keys `dialog_id`, `turn_index`, `user_text`, `category`, `gold`).
- Created `artifacts/claude-calledpanel281-20260923/SPEC-COPY.md` (281 section copied verbatim).
- Created `artifacts/claude-calledpanel281-20260923/README.md` (counts, schema, write expectations).
- Validated JSONL (60 rows, category counts as above, uniform keys, turn indexes sequential per dialog).
- Sealed: `shasum -a 256 panel.jsonl SPEC-COPY.md > SEAL.sha256.txt`. No changes after sealing.

Misses: 0. No missing quota, no invalid JSON, no edits to existing files.

Seal file contents (`SEAL.sha256.txt`):
- panel.jsonl: `149f7373eb4652570deed8b9be1fdf7986f6dc67d3b4d31e8240042d16d7409b`
- SPEC-COPY.md: `00c3b8fb65a12170d6f4e89d941175eae087229fbd7e4f9f21e9db8d0d085e95`

Deviations / judgment calls (spec was ambiguous, so I document them):
- The spec's numbers sum to exactly 60 including teaches (25+10+10+15). So the 10 `teach_setup` turns ARE the setups for the 25 stored questions: 10 dialogs × (1 teach + questions sharing that dialog's fact). Stored questions reuse one dialog fact with 2–3 different called/named wordings each. This is why `teach_setup` (10) + `control_plain` (5) = 15 controls exactly.
- Gold for `teach_setup` is `Subject|relation|Object`; for stored/control_plain answers it is the exact value string; for not-stored and ambiguous it is the literal `abstain`. All question turns expect zero notebook writes (documented in README, not a separate field, to match the brief's 5-field line).
- No `smalltalk` or `no_write` gold literals appear in the file because this spec has no small-talk family; write expectations are stated in README instead.
- PUSH: per the hard no-commits/no-pushes rule that applies in full, I did not `git commit` or `git push`. The sealed directory `artifacts/claude-calledpanel281-20260923/` (panel.jsonl, SPEC-COPY.md, README.md, SEAL.sha256.txt) is in place in the worktree for pickup.

What it means (plain English): there is now a fresh 60-question test, with made-up names only, that checks whether the "called/named" fix works without guessing on untaught or trick questions.

What it doesn't mean: this does not test the fix itself, does not grade any agent, and does not prove the fix works — a separate scorer and registered run do that later.
