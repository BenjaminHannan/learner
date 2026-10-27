# k1h Luna pilot RESULT: PASS (Creative answers in chat thread, written 2026-09-27 05:50 UTC)

Marks fixed in ADDENDUM-5-luna.md (sealed, 94accde3b) before any Luna call. Pass or fail only. No answer was kept,
dropped or labelled because of a judge.

## Run (the Mac job k1h-luna-pilot-mac; its REPORT.md is in ../pilot/)
- 05:14 to 05:25 UTC, 2026-09-27, origin/main 91e5d89cb. All 6 k1h seal files OK (25/2/4/5/3/5) and 3 selftests ok.
- 40 answers, 1 call at a time: 40 tries, all kind=ok. That is 0 timeouts, 0 exits and 0 errlike tries, so 0 answers
  could have been lost falsely to the helper's error markers. Median 7.55 s a call, longest 26.4 s, 6.0 min in all.
- Route filter (ADDENDUM-4): 0 route losses.
- The copies here match the Mac's sha256 for all 5 files.

## Marks
| mark | result | needed | verdict |
|---|---|---|---|
| P1 non-empty after the route filter | 40 of 40 | 36 | PASS |
| P2 kept by trim and guard333d | 40 of 40 | 34 | PASS |
| P3 useful (blind judges) | 40 of 40 | 32 | PASS |
| P3 made_up_user_facts >= 1 | 2 of 40 | at most 2 | PASS (at the limit) |
| Chat pilot: chats kept of 40 asked | 37 | 30 | PASS |

- P2, reported beside it: sealed check keeps 39. It drops 1 chat as a near-copy of a DEV chat, counted before any
  answer existed.
- P3: judges 1 and 2 (blind Opus, private folders, JUDGE-k1f.md's words) agreed on all 40 lines, so judge 3 was not
  needed.
  - Both marked the same 2 lines as made up: L0018 and L0024 (kt-197 and kt-079).
  - Files: judge1.jsonl, judge2.jsonl, pilot_packet.jsonl (seed 4615), pilot_key.json and pilot_score.json.
- Chat pilot: 2 calls, 0 failed. It rejected 3 chats ("fact value not in teach turns"). The mix was idea1 14,
  idea0 14, uf1 3, uf2 3 and uf3 3. These chats are not used in training.
- Gate 1 (report only in the pilot):
  - Sealed check's gate 1 fails: "1." is in 14 of 39 kept answers. Those are list numbers, not sentences.
  - Top opening share: 0.051.
  - See ADDENDUM-6-gate1-DRAFT.md. The sealed gate splits numbered lists into "1.", "2." and "3."; GLM's 240 answers
    fail it the same way (72 of 225).

## What this does and does not show
- Shown: on 40 k1e practice chats, Luna's answers pass the pilot marks fixed before the run.
- Not shown: anything about the full run's other chats, or about training. The made-up count is at the limit, so
  gate 2 (60 kept answers, at most 3 made up) is a real test on the full data.
- GLM's 240 k1e answers are on file (../../glm/answers.jsonl, from the salvage) and are not trained on.
