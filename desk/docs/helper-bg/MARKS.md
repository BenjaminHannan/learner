# HELPER-BG: Glim's helper runs give way to Ben's chat (2026-11-06). Pass marks, fixed before any code. Lead-approved.

Cause (CAUSE4.md, shown): helper requests carry no marker, so the brain's CHAT-FIRST guard treats them as chats.
Ben's chat cannot stop them, and 4-5 of them in flight made requests wait 85-135 s.

## Change 1 (this step)
- Helper requests are marked background with CHAT-FIRST's existing header `X-Glim-Background: 1`. No second marker.
  - They are NOT marked `x-test`, so the diary and sleep keep them.
- The gateway forwards that header (it already tags x-test / warm requests with it).
- A helper request the brain stopped or refused "so Ben's chat goes first" is retried after Ben's chat hold ends, at most 5 times.
  It is never treated as an empty answer.

## Pass marks
| # | mark | how |
|---|---|---|
| H1 | Ben's first word ≤ cleared-queue time + 3 s in **5 of 5** pairs, with 3 helper runs busy | live, lock queue, Ben idle ≥ 5 min: hb_test.py |
| H2 | all 3 helpers finish their task after the chat (3/3, none stuck or empty) | same run |
| H3 | helper requests still appear in the diary, without `test` | diary rows of the run's helper requests |
| H4 | a chat request is never tagged background | unit test over every request path in desk/ (main chat, call, summary, helpers) |
| -- | full desk suite: only the known failures | before build |

**Wrong if:** any pair is > +3 s; a helper fails or ends empty because it was stopped; helper rows vanish from the diary; or a chat path sends the header.

## Change 2 (next step, only after change 1 passes)
Helpers capped at 1 in flight on the local brain, even while Ben is away.
- **Mark:** no starvation: each queued helper starts within 10 min while Ben is idle, and all helpers finish within the day's diary window.

## Item 3 (cut-off requests still cost a full prompt read)
Built here only if small; otherwise listed as a follow-up.
