# mu-407: does a clear "this is the message to answer now" label stop the 1B treating its memory as the present?

"Making things up about you" thread. Written 2026-09-27 02:56 UTC (date -u). DRAFT for the Thread manager's
review. It will be sealed before the talker runs. DEV data only. Nothing is trained. Cost: $0: GLM through Ben's
opencode route on the Mac (about 80 calls, reasoning effort low); the plain 1B on this container's CPU; blind judges
are agents in this thread.

## Why this test, and why now
- mu-405b (VERIFY.md, 00816bdbe and its notes 31c296498) put session 1's lines in the latest user message (U).
  - The plain 1B then made up far more about the user than with no memory: 166 claim flags vs 46.
  - It often answered the old chat instead of the current turn.
- GPT's outside review (reviews/gpt-reply-memory-confab-2026-09-27.md) proposed a first experiment that trains
  nothing: change only the separator before the user's actual turn to an explicit current-message label.
- This is the obvious fix to try before mu-406's training (Ben 19:20, obvious fix first; the Thread manager, 02:51 UTC).
- It is also the brain-first reading. Confabulating patients act on memories that do not belong to the present, and
  the brain keeps "now" apart from "then" with context signals. The label is the simplest such signal. That is a
  guess, not a mechanism.

## Setup
- Chats: 60 fresh two-session DEV chats, plus 3 smoke chats that are never among the 60.
  - Code picks 3 facts per chat (claude_mu405_facts.slots, seed 4070).
  - GLM words the user's messages around them (scripts/claude_mu407_prep.py; job handoff/queue/madeup-mu407-prep-mac.md).
  - Checks per chat, as mu-405's: session 1 has 3-4 turns and states all 3 values. Session 2 has the 5 kinds in order
    (smalltalk, feelings, advice, followup, ask) and contains no value.
  - 75 candidates are written, and the first 60 that pass are kept, in id order (rule fixed now).
- Frames: GLM words all four pieces the talker sees. Nothing Claude-written reaches the talker, so a passing label
  could join a build.
  - A system line. It carries the twin's instructions, but now says the user's earlier conversations may be shown
    and answers may come from them. This removes the clash the Thread manager named: the twin's line said "only
    from what they have told you in this chat" (claude_e2e336_twin.py:17-18) while the block came from earlier
    conversations.
  - A memory header, a per-line prefix, and the current-message label.
  - All arms share the system line, so it is not a change between the arms compared.
  - GLM's prompt describes each piece's job and gives none of its words (claude_mu407_prep.FRAMES_PROMPT).
- Talker: plain MiniCPM5-1B 87179e5c, greedy, 160 new tokens, thinking off, CPU fp32, as mu-405/405b.
- Arms (only the latest user message differs; earlier session-2 turns stay plain history):
  - N: GLM system line; session 2 only, no memory. Report and validity only.
  - U0: GLM system line. The latest user message is the memory header, then one line per session-1 message
    (prefix + the message in quotes), then a blank line, then the user's turn.
  - U1: U0 with ONE change. The GLM label sits on its own line between that blank line and the user's turn.
- Judging: two fresh blind Opus judges per packet, in private folders, arms mixed and shuffled. Each packet shows
  the earlier user messages and session 2.
  - Claims: mu-405's JUDGE-claims405.md, unchanged.
  - Fit (new, JUDGE-fit407.md, fixed before any reply exists). For each reply, "on_turn": does it respond to the
    user's current message rather than to something from the earlier messages or to nothing? For the last turn,
    "answer": does it answer the question with the value the user gave earlier, stated as the answer and about the
    right thing? Reciting it, mentioning it in passing, or hedging ("if you're allergic to X") does not count.
  - Blind recount before reporting.

## Marks (fixed before any reply exists)
- V (validity: the failure is present here). C_U0 >= C_N + 10, where C = claim flags summed over both judges on
  session 2's 300 replies. If not, INCONCLUSIVE.
- L1 (fewer made-up claims). C_U1 <= 0.5 x C_U0, and per chat U1 has fewer flags than U0 more often than more
  (one-sided sign test, p <= 0.05).
- L2 (recall not lost; silence cannot win). Real answers U1 >= U0, where a real answer is an ask turn both fit
  judges mark "answer".
- L3 (still useful). Non-ask replies both fit judges mark "on_turn": U1 >= U0 and U1 >= 192 of 240. The 192 is
  GPT's bar.
- PASS = V and L1 and L2 and L3.
- Proved wrong: C_U1 >= C_U0.
- Anything else is FAIL.

## Report only
- Real answers per arm against GPT's target of 30 of 60. It is not a pass mark: the label is not built to add
  recall, and on the unblinded reads of mu-405b, U gave about 2-4 real answers of 60.
- mu-405's substring count per arm, kept for comparison.
- Per turn kind, for claims and on_turn.
- N's on_turn, as a no-memory reference.
- Replies flagged by both and by either claims judge.

## What each result means
- PASS: the label goes to Month-end as a one-change input fix for 0.2d, with these counts (Month-end decides).
  mu-406's inputs would then include the label.
- FAIL or proved wrong: a label alone does not separate then from now for this 1B, and mu-406 (trained) is next.
  GPT suggests distillation over rejection sampling, which the mu-406 plan will weigh.
- INCONCLUSIVE (V fails): the GLM frames or system line already remove the failure U showed. That is itself worth
  reporting, and the next step is a U0-vs-mu-405b-U check.

## Predictions (before any reply exists)
- P407.1: PASS, 20%.
- P407.2: proved wrong (C_U1 >= C_U0), 25%.
