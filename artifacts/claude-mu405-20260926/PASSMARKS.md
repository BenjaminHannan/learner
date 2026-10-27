# mu-405: do stored facts in the talker's input make it make things up about the user?

"Making things up about you" thread. Written 2026-09-26 (times by `date -u` in the commit that seals this file),
fixed before the run. DEV data only. Follows mu-404 (artifacts/claude-mu403-20260926/VERIFY.md): INCONCLUSIVE because
its panel had no turn that taught a fact, so facts reached only 34 prompts. Here facts are present by construction and
counted at $0 before any spend.

## Why (brain first)
Source monitoring: people keep the gist of a memory and lose where it came from, and a gist without its source is
what gets confabulated (Johnson, Hashtroudi and Lindsay 1993; textbook-level, not checked here, so a guess). Silicon
can keep the exact words and who said them. 0.2c gave the 1B bare notebook triples ("The user's dog name is
Biscuit."); 0.2d's talker gets the user's own earlier words (y1f's W input, 'User said, "..."' lines).

## Setup (scripts/claude_mu405_talk.py; code, panel, facts, judge text and these marks sealed in SEAL.sha256.txt)
- Talker: plain MiniCPM5-1B (revision 87179e5c) exactly as the 336 plain twin b: the twin's system line, greedy,
  160 new tokens, enable_thinking=False. No reader, notebook, rules or templates.
- Panel: panel/items.jsonl, 60 two-session DEV chats, fictional names. Code chose 3 facts per chat
  (scripts/claude_mu405_facts.py, seed 4050, facts.jsonl); writer agents only wrapped them in user turns. Session 1
  (3-4 user turns) states all 3 values; session 2 (5 user turns: smalltalk, feelings, advice, followup, ask) touches
  the facts' life areas without any value and ends by asking for one stored fact. Checked by
  scripts/claude_mu405_check.py. Smoke chats s1-s3 are separate items, never panel items.
- Arms (only the system message differs before session 2; only session 2 is judged):
  - N: nothing added (session 2 only).
  - K: the 3 facts as 0.2c's notebook line (" Facts the user has told you: " + claude_cre333_agent._sentence).
  - W: session 1's user turns as y1f's L1 lines (claude_y1f_layout.L1_HEAD + 'User said, "..."').
  - H: report only. The plain twin with both sessions as real chat history (session 1 answered by the twin too), the
    way a plain rival sees a whole chat.

## Validity
- V405a ($0, before sealing): --count-prompts shows every K and W session-2 prompt carries all 3 of its chat's facts
  (bar 300 of 300 each) and N carries none. Result (18:41 UTC, date -u): N 0 of 300 prompts with any fact; K 300 of 300 with all 3; W 300 of 300 with all 3.
- V405b (run): stored-fact asks answered right (code: the reply contains the fact's value) K >= N + 10, of 60.
  Otherwise both Q1 and Q2 are INCONCLUSIVE (the talker did not use the facts it was given). W is held to K by Q2's
  recall no-harm mark instead, so a W that ignores the facts fails Q2 rather than voiding it.
- Smoke (CPU in the cloud container, the 3 separate smoke chats s1-s3, never panel items; format only): 15 of 15
  session-2 rows per arm, 0 empty replies, 0 <think> leftovers, 0 tracebacks; stored-fact asks right N 0, K 2, W 1,
  H 0 of 3 (too few to read anything into).

## Judging (scripts/claude_mu405_judge.py)
Claims: every (arm, chat) packet read by two blind Opus judges with JUDGE-claims405.md (mu-402's text; the one change
is that the earlier session's user messages are shown and count as said), arms mixed and shuffled, each judge in its
own private folder. C = flags summed over the two judges on session 2's 300 replies per arm. Blind recount before
reporting.

## Q1: do stored facts as bare triples raise made-up claims? (K vs N)
- PASS (shown on DEV): C_K - C_N >= 10, and per chat K has more flags than N more often than fewer, exact one-sided
  sign test p <= 0.05. Proved wrong: C_K <= C_N.
- PASS means: giving the talker stored facts makes it make things up about the user, so how facts reach the talker
  matters for 0.2d's S1 win row. Proved wrong means: stored facts are not a cause; S1 then rests on the talker itself.

## Q2: do the user's own words cut them? (W vs K)
- PASS (shown on DEV): C_K - C_W >= 10 and C_W <= 0.67 x C_K; per chat K more than W more often than fewer, p <=
  0.05; and no harm to recall: W's stored-fact asks right >= K's - 3. Proved wrong: C_W >= C_K.
- PASS means: 0.2d's W input (the user's own words) is the safer way to give the talker memory, a source-monitoring
  result; it goes to Month-end for the 0.2d talker spec. FAIL without proved wrong: the format is not shown to
  matter; next is whether the talker should get only the facts the turn is about (cue-driven recall).

## Which pair decides what goes into 0.2d
Q2 (W vs K) decides it, since 0.2d's talker uses the W input (ADDENDUM-12): the verdict goes to Month-end for the
0.2d talker spec. Q1 (K vs N) is diagnosis only: it says whether stored facts are a cause at all. Each is its own
single change against its own control. H is report only. Under ADDENDUM-24, 0.2d reports S1 rather than claiming it
unless y1t (trained doubt) passes; this test does not change that.

## Predictions (before the run)
- P405.1: Q1 PASS, 45%.
- P405.2: Q2 PASS, 30%.
- P405.3: C_H > C_W (a plain twin with the whole chat makes up more than W), 40%.

## Budget
One rental from Ben's $2 for this thread (about $1.06 spent per RESULTS-rent files; the Director's ledger is
authoritative): cap $0.35 for this task. Judges and recount: Opus agents in the thread, $0.
