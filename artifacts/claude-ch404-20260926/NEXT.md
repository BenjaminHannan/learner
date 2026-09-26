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
below and above the chat layer both see 90 words); N6 below makes it a mark. AGREED with Benchmarks 14:37 UTC:
longer replies only on the everyday-chat path; memory and past-chat answers keep the 90-word cap and their own caps;
past-chat length is owned by bm-398e (copy-only span trimmer, sealed 3b6fc7b1e) if it passes, else by those caps.

## Registered run of the chosen candidate (marks fixed now; arm C = the chosen candidate, B = X403)
Fresh panel chatpanel404: 60 conversations written blind by three writers from 338-chat-panel-spec.md +
382-panels-spec.md, blind audited, sealed before the run, run once (sealed: artifacts/claude-panel404-20260926,
81bd131db). Runs with ch-403's runner; scoring and marks scripts/claude_ch404_run.py (selftest 3/3); judging as
ch-403 (JUDGE-BRIEF.md); job handoff/held/rent-ch404.md (held until CAND and ADAPTER_MODE are filled).
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

## Adapter and picker (added ~14:30 UTC after the thread manager's note, before any result)
- The registered ch-404 run seals only after mu-402's M3 (sleep adapter on vs off in chat, owner Making things up is
  about you) is in. Both arms B and C then use whichever chat-path adapter setting 0.2d adopts (Month-end's plan:
  adapter off on the chat path), so the result transfers to 0.2d. The DEV probe in rent-ch403 uses 0.2c's adapter.
- One shared picker over the chat layer's 1B samples, owned by Making things up (mu-403). This thread does not build
  its own. If C1 is still short after ch-404, the candidate after it (ch-405) is a helpfulness score added to that
  picker as one change on top of it, with the made-up-claims row as a no-harm mark. Proposed to Making things up and
  Creative answers in chat by message.

Filled 14:55 UTC: mu-402 is in (VERIFY.md: M3 PASS, adapter-off chats preferred 92-66 of 160 pair judgements), and
0.2d keeps the adapter off the chat path, so B and C run with the adapter OFF (rent-ch404 ADAPTER_MODE: off).

## Scope after Ben's goals page (written 2026-09-26 15:00 UTC)
design/v3/30-modes/ben-goals-2026-09-26.md: the reasoner is the model; the reader and talker only turn words into
thoughts and thoughts into words (Ben 14:49), so everyday chat should be solid and plain, not a big talker project.
So this line stops at removing harms: ch-403 (stock non-answers) and one of ch-404/ch-404g (length or decoding). The
ch-405 helpfulness score for the shared picker is dropped. Questions for Ben go only through the Thread manager.

## Money
ch-403's job is capped at $1.60 of this thread's $2 (Ben, 12:59 UTC). A registered ch-404 run (three arms, 60
conversations) is likely to take the thread past $2; before it is queued the thread first asks month-end whether it can
ride in the 0.2d build run, and otherwise asks Ben once, with a recommendation, per the coordinator's rule.

## Joining with mu-403's system line (written 2026-09-26 15:17 UTC, before any ch-403 or DEV result)
Making things up's mu-403 arm P appends one sentence to SYSTEM338 at build time; build_404 swaps in a SYSTEM404 made at
import, so in a joined build that sentence would be dropped while ch-404's chat turn runs. scripts/claude_ch404_join.py
(build_404_live, selftest 5/5) recomputes the swap from the SYSTEM338 in force at each turn; with SYSTEM338 unchanged it
sends exactly what build_404 sends. The registered ch-404 run keeps build_404 (the DEV-probed code); a joined build that
takes both uses build_404_live. ch-404g needs nothing.

## After Ben's Redirect (16:04 UTC) and "ask how the brain does it" (16:05 UTC); written 2026-09-26 16:10 UTC, before any ch-403 result
Goals page (328b97c78, b285cebc3): no new work on hand-written rules, routing gates or answer templates; the talker's
writing and saying "I don't know" carry on; the next build is judged against plain same-size models, not the rule build.
- Stops: ch-403b and ch-403s (rule fallbacks), recall403's rule gate and the honest-line template as product work, and
  the registered ch-404/ch-404g run against X403 (rent-ch404 stays held and will not be released). ch-403 and its DEV
  probe are already running: they finish and their verdicts stand. The DEV probe is kept as evidence about the talker's
  writing (length, decoding), report only.
- How the brain does it (simplified textbook science, not checked here): speech production is fluent and plain and does
  not choose from stock phrases; what to say comes from the situation model and memory; "I don't know" comes from doubt
  at recall (the notebook), not from a template picked by a rule.
- Replaces them: tk-1, the design's talker on the chat layer. Every reply that reaches the chat layer is written by the
  talker (the 1B) from the chat and the reader's notes, decoding the way the plain model does (the twin's settings), with
  no stock lines, rule gates or rule guards. One change: the rule chat layer out, the talker in; every other layer stays
  its owner's. Built and CPU-tested at no cost. Measured against plain MiniCPM5-1B, Qwen3.5-2B and LFM2.5-1.2B on the
  sealed, unread chatpanel404. Bar, fixed before any run: against plain MiniCPM5-1B, tk-1's wins are at least its losses,
  and its judged made-up claims about the user are at most plain's; the two bigger or different rivals are reported.
- Money: recommended to measure tk-1 inside the next build's rival comparison (Benchmarks runs the rivals), with no
  separate rental, because reasoning gets money first. A separate run would cost about $0.50 and take this thread past
  $2, so it needs Ben's yes through the Thread manager.

## tk-1 folded into 0.2d's talker (written 2026-09-26 16:14 UTC, before any result)
Month-end's 0.2d ADDENDUM-12 (9fda097de, 16:08 UTC) already defines the design's talker: plain MiniCPM5-1B fed the
notebook through y1f's W input (whole chat when it fits), k1a for creative, "I don't know" when the notebook has
nothing, and no rule layers. That is the tk-1 described above, so this thread does not build a second talker; tk-1 is
withdrawn before any code or run. Brain check: speech has no separate everyday-chat module; one language system
puts whatever is in mind into words, so everyday chat is the talker's own job, not a layer on top.
This thread's part of 0.2d's everyday-chat row (C1, pair judge vs each rival):
- Panel: chatpanel404 (artifacts/claude-panel404-20260926, sealed 81bd131db, never read or run), offered to Month-end.
  chatpanel403 (sealed 78fc677bd, never run) is the spare.
- Rival arms need no new code: claude_ch403_run.py run --arm twin --gen-model <rival dir> under
  claude_twinb_wrap.py (plain twin recipe, thinking off, greedy, 160 tokens) for MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B.
- Judging: JUDGE-BRIEF.md (artifacts/claude-ch403-20260926) and claude_ch403_run.packets for any pair.
- What the diagnosis says the talker must not bring back on everyday turns: stock lines, a 1-to-4-sentence rule, a
  90-word cap (DIAG.md sections 2-4).
Spend: none now. ch-403 used about $0.79 of this thread's $2.
