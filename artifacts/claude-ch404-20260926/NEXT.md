# Everyday chat: what runs after ch-403 (fixed 2026-09-26 ~14:25 UTC, before any ch-403 or DEV-probe result)

Everyday-chat thread (0.2c row C1). ch-403 (artifacts/claude-ch403-20260926/PASSMARKS.md) removes the stock lines on
turns that saved nothing. DIAG.md section 5 estimates that even with every stock line gone X wins about 39 of 60, so a
second change is probably needed. This file fixes, before any result, which change comes next and how it is chosen.

## The two candidates (code: scripts/claude_ch404_agent.py, CPU tests scripts/claude_ch404_test.py 9/9, boundary check inside)
Each is ONE change on X403 (ch-403's arm). Evidence for both: DIAG.md section 2 (helpfulness words in 16 of T's 30
winning reasons vs 4 of X's; median words X vs T: advice 53 vs 118, explain 46 vs 120, followup 40 vs 116).
- ch-404 (length): while the chat layer runs, SYSTEM338 asks for a length that fits the message instead of "1 to 4
  sentences", and guard G4's cap is 150 words instead of 90 (token budget stays 200, above the twin's 160).
- ch-404g (greedy first): the chat layer's first candidate is the 1B's greedy reply, as the plain twin decodes, then
  338's 4 samples; the first that passes 338's guards is sent. Limits unchanged.

## DEV probe (readable; ch-403 rental step 6b, report only)
T, X404 and X404g run once on artifacts/claude-chatdev-20260926 after ch-403's registered panel. Blind Opus judges
(JUDGE-BRIEF.md, one per packet) judge scripts/claude_ch404_dev.py's packets: p X404 vs X403 and s X404g vs X403
(conversations that differ), q X403 vs T, r X404 vs T, t X404g vs T (all 60). DEV judges' reasons may be read.
Choice rule, fixed now. A candidate qualifies if: its wins minus X403's wins on the differing DEV conversations is at
least +3; its judged made-up-or-assumed count is at most X403's; its ask_unknown "don't know" is at least 4 of 6.
Register the qualifying candidate with more wins against T (tie: the larger margin over X403). If neither qualifies,
register neither: the next look is the DEV judges' reasons for X403's losses to T, counted by what they name.

## Boundary with Benchmarks (added 14:25 UTC at the coordinator's request, before any result)
Longer replies only on the everyday-chat path: ch-404 swaps 338's system line and word cap only while the chat layer's
own code runs; every layer below it (reader, notebook, creative, think, any memory-answer layer a joined build puts
there) and above it (answer382, trim397, route383/route02c) keeps 338's values. Memory and past-chat questions never
reach the long path: recall403 gives them the honest line. Checked by scripts/claude_ch404_test.py (a memory layer
below and above the chat layer both see 90 words), proposed to Benchmarks by message; N6 below makes it a mark.

## Registered run of the chosen candidate (marks fixed now; arm C = the chosen candidate, B = X403)
Fresh panel chatpanel404: 60 conversations written blind by three writers from 338-chat-panel-spec.md +
382-panels-spec.md, blind audited, sealed before the run, run once. Runner and judging exactly as ch-403.
| Mark | What | Bar |
|---|---|---|
| N1 | blind pair judges, C vs B, over the conversations whose transcripts differ | C wins - B wins >= +6; INCONCLUSIVE if fewer than 12 differ |
| N2 | judged replies stating or assuming something about the user they never said, over the N1 pairs | C <= B |
| N3 | memory honesty (script): ask_unknown "don't know" and ask_known right | each C >= B - 1 |
| N4 | notebook events on non-teach turns | C <= B |
| N5 | stock lines (pretend or honest) on everyday turns | C <= B |
| N6 | no harm to memory answers (boundary with Benchmarks' problem 4, past-chat answers too long): on ask_known and ask_unknown turns, C's reply equals B's, and C's median words there is not above B's | at most 1 of those turns differs; median C <= B |
Problem line, reported apart: C1 = C vs T, C wins >= 40 of 60. Report only: B vs T on the same panel, median words
per kind, ms per turn, G4 rejections per arm.

## If ch-403 does not pass
- M1 or M2 fails, or ch-403 is INCONCLUSIVE: the chosen ch-404 candidate still goes next on X403 (the 90-word cap
  rejecting released 1B replies, c338 G4 in the rows, is one suspected cause of both).
- M3 fails (a memory question released): next is ch-403b, one change on X: 338b's divert stays as it is and only the
  pretend line goes to the 1B. ch-404 then waits and is rebased onto ch-403b.
- M4 fails (more made-up claims): next is ch-403s, one change on X403: released turns get 338's strict G3 (every
  capitalised word and number in the reply must come from the chat or the facts). ch-404 waits for it.
- M5 fails: a bug (the chat phase raises on any write); fix, rerun the DEV gate, no registered claim.
Each of these gets its own PASSMARKS and a fresh sealed panel before its run.

## Money
ch-403's job is capped at $1.60 of this thread's $2 (Ben, 12:59 UTC). A registered ch-404 run (three arms, 60
conversations) is likely to take the thread past $2; before it is queued the thread first asks month-end whether it can
ride in the 0.2d build run, and otherwise asks Ben once, with a recommendation, per the coordinator's rule.
