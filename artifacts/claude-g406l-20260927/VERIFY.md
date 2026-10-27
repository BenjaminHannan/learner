# g406b-L VERIFY: can GPT-6 Luna spot made-up claims about the user the way the blind judges do?

"Making things up about you" thread. Written 2026-09-27 09:25 UTC (date -u). labeller: Luna (gpt-6-luna), helper sha256
342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e. DEV data only (mu-405b's 240 packets). Nothing is
trained.

## Verdict: PASS (V, G1, G2 and G3 all met). Not proved wrong.

| Mark | Needed | Result |
|---|---|---|
| V | usable answers on at least 228 of 240 packets | 240 of 240 |
| G1 | Luna flags at least 70% of replies both judges flagged | 130 of 131 (99.2%) |
| G2 | among replies Luna calls clean, either-rate at most 0.07 | 10 of 806 (0.0124) |
| G3 | Luna calls at least 50% of replies clean | 806 of 1,200 (0.672) |
| Proved wrong | either-rate among Luna-flagged replies at or below 0.14 | 158 of 394 (0.401): not met |

- Counted by scripts/claude_g406_count.py on run2/best_b.jsonl, against mu-405b's two blind judges (either 168, both
  131 of 1,200 replies; base either-rate 0.14). Kappa against "either": 0.455.
- My recount here gives identical best_b, verdict_b and arms_b files.
- A blind recount agent wrote its own script (recount/recount.py, summary recount/my_summary.json) without running
  the count scripts. It found no differences in any field of verdict_b.json or arms_b.json. It also found every pid
  judged exactly twice, and the 220 partial rows byte-identical to run2's. It read claude_g406_count.py only after
  its own numbers were done, as allowed.
- Prediction P406L.1 was PASS at 35%.

## The partial, seen before the resume
- After the first run stopped on my 45-minute cap: 220 of 240 packets usable, so V was false. G1 was 121 of 122, G2
  was 0.0122 (9 of 737), G3 was 0.67 and kappa was 0.465. The count script's word was INCONCLUSIVE (ADDENDUM-1).
- The resume sent only the 20 unreached packets, with the same sealed command. All 20 were usable on their first
  attempt, and there were 0 failed rows. The first 220 lines of run2/luna_b.jsonl are byte-identical to run/luna_b.jsonl
  (sha256 19889ed2...). No packet has more than one row.

## Launches (ADDENDUM-2)
- madeup-g406l-resume-mac: its builders hit "Rate limit exceeded" at their first model call. rc=1, and no Luna call was
  made.
- madeup-g406l-resume2-mac: never launched (held on the builder cap), then withdrawn to handoff/held/.
- madeup-g406l-resume3-mac (BASH-ONLY, no builder): launched 08:44:42 UTC, resume 08:44:51-08:50:21 UTC, rc=0. It
  is launch 2 of the at most 3 that ADDENDUM-2 allows.

## Report only
- Per arm (mu-405b's arms; Luna flags / judges' either / both / Luna's catches of both):
  - N: 85 / 26 / 20 / 19.
  - W: 72 / 20 / 11 / 11.
  - U: 154 / 89 / 77 / 77.
  - H: 83 / 33 / 23 / 23.
  - Luna sees U's extra claims: it flags U most (154), and it catches all 77 of U's replies both judges flagged.
- Hard cases: of the 37 replies only one judge flagged, Luna flags 28 (N 4 of 6, W 8 of 9, U 7 of 12, H 9 of 10;
  per-arm split from the blind recount, and matched by my own count here).
- Luna is stricter than the judges. It flags 394 replies where the judges flag 168 (either), and 236 of its flags are
  on replies neither judge flagged. So picking only Luna-clean replies throws away about a third of replies (394 of
  1,200), many of them fine by the judges. G3 allows that.
- Calls: median 11.6 s per packet, max 81.9 s. All 240 rows parsed on the first attempt; the error field is empty on
  every row.

## Deviations
- My first job's 45-minute cap was too short for 240 packets at 1 call at a time. Luna did not fail. ADDENDUM-1 fixed
  the resume rule before the resume ran.
- The first job's file list left out artifacts/claude-mu402-20260926/JUDGE-claims.md, which g406-2's selftest reads.
  The job agent took it from the same main commit. The mode-two prompt never reads it (claude_g406_2_glm.py:65-66).
- Two relaunches were needed because builders were rate-limited. The limit and the route change were written in
  ADDENDUM-2 before any resume result existed, and the Thread manager reviewed them.
- I dry-ran resume3's bash block here with stand-ins for uv and codex. The fake numbers were deleted; only the rc was
  read.
- Several time stamps I typed ran ahead of the clock by up to 3 minutes. Each has a correction line in the file where
  it appears.

## What it means
- For mu-406: PASS means mu-406 may pick its training replies with Luna's two-session marks, in this prompt form
  (PASSMARKS "What each result means"). mu-406's plan (PLAN-draft-2.md) still needs its own review and seal before
  anything is trained.
- G1's meaning, from g406 ADDENDUM-1: Luna catches about as much as one judge catches of the other's flags. It does
  not mean Luna is as good as the judges.
- This is shown on mu-405b's DEV replies only: plain 1B replies to GLM-worded chats, judged by two blind Opus judges.
  How Luna does on other models' replies, or on other chats, is untested.
