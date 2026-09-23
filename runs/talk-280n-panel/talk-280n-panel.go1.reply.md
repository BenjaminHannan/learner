Writing your blind test panel — starting with the rules and spec.
Spec located. Now I'll pull the exact panel-spec text for the seal copy and verify the workspace.
Spec captured. Target directory doesn't exist yet (good — additive only). Disk has ~12 GB free, so I'm clear to proceed. Now I'll create the panel directory and files.
Directory created. Now writing the panel file (90 turns).
Panel written. Now the spec copy and README.
Files written. Validating format and counts (read-only check of my own data file), then sealing.
Validation passes. Sealing now.
VERDICT: PASS (panel written, validated, and sealed — ready for the 280n builder).

Marks table (integer counts, turns per category):

| Category | Count |
|---|---|
| ability | 25 |
| teach | 8 |
| called | 12 |
| smalltalk | 25 |
| mixed | 10 |
| control | 10 |
| TOTAL turns | 90 |
| TOTAL dialogs | 73 |

Every move:
- Read the OPUS-RULES file in full before starting.
- Checked `uptime` (1-min load ~60, no heavy steps run) and `df -g /` (~12 GB free, above the 3 GB floor).
- Ran `git fetch -q origin main` and read the spec with `git show origin/main:...` only. Never checked out or merged that branch. Never used `git log`.
- Read ONLY the "Panel spec (joinpanel280m, 90 turns, fresh)" section (plus the file's line count and header to locate it). Never opened scripts/, any other artifacts folder, or any existing panel (including the 280m panel).
- Created new directory artifacts/claude-joinpanel280n-20260923/ and wrote 3 new files: panel.jsonl (90 lines), SPEC-COPY.md (verbatim spec section), README.md (counts, layout, gold conventions).
- Ran a read-only format check on my own panel file (90 lines, exact key set, per-dialog turn_index 0-based and sequential). Never read or ran any repo code.
- Sealed with shasum from the worktree root. Never touched the files after sealing.

Every miss: none. Zero misses, zero deviations from the spec counts (25/8/12/25/10/10 = 90).

Deviations:
- The brief says "PUSH: artifacts/claude-joinpanel280n-20260923", but the OPUS-RULES (which apply in full) forbid git commits, PRs, and pushes. I left the sealed directory in place in the worktree, uncommitted, and did not push. The panel is delivered via these paths, not via git.
- Design choice the scorer should know: the 8 teach + 12 called turns are arranged as 8 dialogs (4 dialogs with 1 teach + 2 questions, 4 with 1 teach + 1 question); the 12 called questions use four formal shapes, 3 turns each. Mixed turns: 6 small-talk-plus-ability (gold "ability_list") and 4 small-talk-plus-called about never-taught people (gold "abstain"). Controls: 5 two-turn dialogs, each a plain teach (gold is the triple) followed by a plain question about it (gold is the value).

Seal file contents (artifacts/claude-joinpanel280n-20260923/SEAL.sha256.txt):
c8f0c056432b5e34b51d1901327fb9c80f687c8cf9ce46d305f8bca18fff8d66  artifacts/claude-joinpanel280n-20260923/panel.jsonl
9f1b3e4cf669b77cccda5138d37f97e4a7394da290c1875dc661ee9a3565c61c  artifacts/claude-joinpanel280n-20260923/SPEC-COPY.md

What it means (plain high-school English): the re-test has a fresh set of 90 test questions, built to the same recipe as last time, with all-new made-up names. Nobody on the scoring side has seen these questions before, so the score will be honest.
What it doesn't mean: this says nothing about whether the 280m agent is good or bad. I only wrote the test — I never ran the agent, never graded anything, and never quoted any test item here, so there is nothing leaked for anyone to study from.
