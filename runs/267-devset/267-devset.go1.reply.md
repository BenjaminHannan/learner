Writing your fresh 120-turn dev set — starting with rule checks and format.
Your spec files aren't in this worktree — I'll fetch them from main.
I've mapped your 120-turn mix across all seven families — now building the sealed dev set.
All 120 turns passed validation — sealing the package.
Package is sealed — final verification before handoff.
VERDICT: DONE — fresh DEV set sealed, 120/120 turns, ready for 267 diagnostic. 264 builder NOT attempted (to avoid contamination).

Marks table (integer counts, required vs actual):

| Item | Required | Actual |
|---|---|---|
| total turns | 120 | 120 |
| plain_teach | 50 | 50 |
| plural relatives R10 | 15 | 15 |
| typo or filler | 15 | 15 |
| relation traps R16 | 10 | 10 |
| stale values R17 | 10 | 10 |
| no-save pretend/plan/check | 10 | 10 |
| questions ASK | 10 | 10 |
| TEACH frames | — | 117 |
| ASK frames | — | 10 |
| no-save with gold [] | 10 | 10 |
| duplicate turns | 0 | 0 |
| banned spec names in turns | 0 | 0 |
| we/us/our owners | 0 | 0 |
| seal check shasum -c | 2 OK | 2 OK |

Every move:
- uptime + df -g / checked: 1-min load 37-48 (<60), free 14-15 GB (>3 GB), 1 process.
- git fetch -q origin main, git ls-tree to locate files.
- read OPUS-RULES.txt in full.
- git show origin/main:design/v3/30-modes/264-qa-checker.md, handoff/kit/briefs/261-earcheck.txt (head only), handoff/kit/briefs/earpanel264-spec.txt, handoff/queue/267-devset.md + 267-diag.md.
- did NOT read any scripts/claude_earcheck* or any earpanel*/panel files.
- mkdir artifacts/claude-devset267-20260923/.
- wrote make_dev.py (explicit 120 ITEMS, fixed alias lists, pet aliases include species+pet+animal+companion).
- ran uv run --offline --no-project --python 3.12 --with torch --with numpy python -B make_dev.py → self-checks OK, wrote dev.jsonl 120 lines.
- verified counts with second uv run (120 lines, families match, 117 TEACH + 10 ASK).
- shasum -a 256 dev.jsonl make_dev.py > SEAL.sha256.txt from repo root, shasum -c OK.

Every miss: 0 missing turns, 0 schema failures, 0 duplicate turns, 0 banned-name hits.

Deviations:
- Did only the second task (267 dev writer). Did not do the first task (264 builder scripts, PASSMARKS, RESULTS, ledger P264.n), because the writer task forbids reading checker code and requires CPU only. Doing both would contaminate the dev set.
- Read design 264 doc + 261 brief head in addition to the spec. Writer brief said spec only; first brief listed those docs. No panel items, no code, no relation tables were opened. All names/places are new fiction.
- Did not git add/commit/push. Repo .gitignore ignores artifacts/, and OPUS-RULES forbids pushes. PUSH means files left on disk: artifacts/claude-devset267-20260923/dev.jsonl, make_dev.py, SEAL.sha256.txt.
- Did not append ledger P267 lines (writer brief lists none).

What it means (high-school English):
- There is now a practice set of 120 chats the 267 diagnostic can tune on. It covers easy facts plus the hard cases: two-person family lines, typos, tricky wordings, old-vs-new values, pretend/plan/check lines that must save nothing, and questions.
- The seal proves the files have not changed since they were made.

What it doesn't mean:
- This is not a test score and not proof the checker works. It is DEV data, tunable by design.
- It does not certify exp 264. It does not replace the blind 264 panel, which was never opened.
