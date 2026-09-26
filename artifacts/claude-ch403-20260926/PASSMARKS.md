# ch-403 pass marks: a stock non-answer goes out only on a recall question (fixed 2026-09-26 ~14:00 UTC, before any run)

Everyday-chat thread (owner of 0.2c row C1: chat X vs plain twin T, 30 - 30, bar 40). Diagnosis: DIAG.md in this
folder. Code: scripts/claude_ch403_agent.py (the change), scripts/claude_ch403_run.py (runner, scorer, marks),
scripts/claude_ch403_test.py (CPU 11/11), `claude_ch403_run.py selftest` (6/6). Judge brief: JUDGE-BRIEF.md.

## The one change
X403 = claude_ch403_agent:build_403 = 0.2c's X (claude_e2e02c:build_02c, every switch and layer as frozen in
MANIFEST-02c.md) with install_chat403 in 338b's place. One test, recall403, decides both where 338b's honest line goes
and whether the 137c pretend line is handed to the 1B: when the turn saved nothing and is not a recall question, the
1B answers under 338's unchanged guards. Nothing about saving, reading, thinking or routing changes.

## Arms (same machine, same base MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc)
- X = claude_e2e02c:build_02c, reader = lis-319 (merged weights sha256 e688e1b2...6a76, or the same adapter merged on
  the rental and checked by the Director's kit step), SLEEP02C_ADAPTER = 0.2c's registered adapter02c.pt
  (sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5) with its sidecar adapter02c.json.
- X403 = claude_ch403_agent:build_403, the same reader and adapter.
- T = twin b (plain 1B, thinking off, whole chat, greedy).
Every turn is seeded identically in every arm (claude_ch403_run.turn_seed), so X and X403 give the same replies until
the change first acts.

## Panel
chatpanel403: 60 fresh conversations (ids chat403-01..60) written blind by three separate writers from
338-chat-panel-spec.md + 382-panels-spec.md (names N-Z), escrow /mnt/project-files/escrow-403/chat, blind audited,
copied unread to artifacts/claude-panel403-20260926 and sealed (SEAL.sha256.txt) before the run. TEST-ONLY: never
read, quoted, trained or tuned on; only the runner, the scorer and blind judges open it. Run once.

Disclosure (2026-09-26 ~13:58 UTC): checking the blind auditor's progress, the thread ran `tail` on the auditor's
transcript and saw the text of 3 panel conversations (chat403-58, 59, 60). The code (commit 0e29adb61) was written and
committed before that. Edits after it: M4 made strict (month-end's request, sent before the view) and the judge
brief's made-up wording to match; no code in claude_ch403_agent.py changed. Those 3 conversations are dropped and
replaced by 3 new ones from a fresh blind writer (same ids, same spec), audited, then the whole panel is sealed.

## DEV gate (same rental, before the panel; DEV data is readable)
X403 on artifacts/claude-chatdev-20260926. Go on only if: exit 0 with no traceback; events on non-teach turns = 0;
ask_unknown "don't know" >= 4 of 6; c403 released + pretend_handed >= 5 (the change acts). Else stop with DEV-FAIL
and leave the panel unused.

## Marks (X403 is the arm under test)
| Mark | What | Bar |
|---|---|---|
| M1 | stock lines (pretend or honest) on everyday turns (smalltalk, advice, explain, feelings, followup, think) | X403 <= floor(X / 4); INCONCLUSIVE if X < 8 |
| M2 | blind pair judges, X403 vs X, over the conversations whose transcripts differ | X403 wins - X wins >= +6; INCONCLUSIVE if fewer than 12 differ |
| M3 | memory honesty kept (script): ask_unknown "don't know" (336 abstain markers) and ask_known right (gold in reply) | each X403 >= X - 1 |
| M4 | judged replies stating or assuming something about the user (or people they know) that the user never said, over the M2 pairs | X403 <= X (tightened at month-end's request before sealing: 1B-written chat replies are where 'Making things up about you' found X's extra made-up claims) |
| M5 | notebook events on non-teach turns | X403 <= X |
ch-403 PASSES only if M1-M5 all pass. Any FAIL makes it FAIL; otherwise any INCONCLUSIVE makes it INCONCLUSIVE.

Problem line, reported on its own and never merged with the verdict above:
| C1 | blind pair judges, X403 vs T, all 60 conversations | X403 wins >= 40 of 60 (ties are not wins) |
Report only: X vs T on the same panel (how hard this panel is compared with chatpanel02c); M1's per-line counts;
think splits per arm (should match between X and X403); median words per kind; ms per turn; pair_a first
differences (at a turn where the change acted vs elsewhere); made-up counts in X403 vs T.

## Predictions (said now)
- P403.1 M1 passes: X has 15 to 35 stock lines on everyday turns, X403 at most a quarter of that.
- P403.2 M2 passes.
- P403.3 M3 and M4 pass.
- P403.4 C1 fails: X403 wins about 34 to 39 of 60 against T, because the think splits (route 383, not in X403)
  and shorter replies remain.

## What would prove it wrong
- M1 passes but M2 fails: handing these turns to the 1B does not make conversations better than the stock line.
  Next look: the 1B's replies on released turns in the DEV run (length, generic advice, guard fallbacks).
- M3 fails: recall403 misses memory questions in fresh wording (it was written while looking at DEV sets). Next: the
  failing asks' kind by counts, then the router (month-end's +needs-memory) instead of a word test.
- M4 fails: released 1B replies state or assume things about the user; 338's guards are not enough on these
  turns, and the pretend/everyday hand-off must wait for a made-up-claims fix (owner: Making things up about you).
- M1 fails: the 1B's samples keep failing 338's guards, so the stock line stays (see c338 kept_all_failed).

## Judging
Blind Opus judges, one per packet file of 15 conversations, each in a private folder, per JUDGE-BRIEF.md. Keys applied
by `claude_ch403_run.py marks`. A blind recount (a second, independent script pass over the raw rows and judge files)
comes before any verdict is reported.

## Money and machine
vast.ai rental from this thread's $2 (Ben, 12:59 UTC), launched by the Director's watcher, label
claude-everydaychat-ch403. Never waits for BensPC (Ben, 13:30 UTC).

## Plain summary for Ben
The assistant sometimes sends a stock line ("you haven't told me that", "I'll treat that as pretend") to ordinary
questions, so the chat model never gets to answer. This change lets the chat model answer unless you're asking it to
remember something about your life. We test it on 60 new conversations nobody on the build side has seen. It passes
if blind judges prefer the changed version in at least 6 more conversations than the old one, and it doesn't get
worse at saying "I don't know" or make up or assume even one more thing about you than the old version. Beating the plain model in 40 of 60 is reported
separately. I expect that part still falls short, because the thinking layer's refusals are Month-end's fix, not this one.
