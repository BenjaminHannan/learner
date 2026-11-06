# Helper fix: handoff from PROMPT-DIET-S

Date: November 6, 2026. Live checks are not yet a pass.

## 1. Helpers let Ben go first

The earlier tag change is in commit `cea67a78a`. Helpers use the same
`X-Glim-Background` header as the existing chat-first guard. There is no second
tag. Real helpers are not test traffic, so their answers can still reach the
diary and sleep.

This handoff also fixes helper summaries that skipped the one-at-a-time queue.
A cut-off helper answer, even one with a few words, is not called finished work.
Ben's chat cannot keep a background tag passed by mistake.

| Mark | Need | Result |
| --- | --- | --- |
| H1 | First word no more than 3 seconds slower, all 5 pairs | Waiting for a safe live turn |
| H2 | All 3 helpers finish after each chat | Waiting for the same check |
| H3 | Helper answers reach the diary without a test flag | Waiting for the same check |
| H4 | Chat paths never get the helper tag | Pass in the small tests |

The live check uses Fast mode, with the normal two-loop brain. Each chat asks for
one word and has room for 16 tokens. It times actual reply text, not the empty
opening of a stream. Helpers use saved requests and keep their diary rows.
Only the replay chats have `test:true` in their body. They do not use `X-Test`,
because that header would wrongly put the chat in the background lane.
The check also makes sure three helper requests were still busy when chat began.
This checks replayed model requests, not a whole web-research run with every tool.

## 2. One helper asks the local brain at a time

Helper runs can still read pages or files together. Only their brain requests
take turns, oldest first. Waiting for Ben does not hold a turn. A cancelled
helper leaves the line. Ben never waits in that line. Helper summaries use it too.

| Mark | Need | Result |
| --- | --- | --- |
| One at a time | At most one helper brain request | Pass in small tests |
| Fair turns | Each queued helper starts within 10 minutes while Ben is away | Small FIFO test passes; live check still waiting |
| No lost turns | All queued helpers finish | Small test passes; live check still waiting |

Two signed app copies are ready. The tag-only app has the cap off. The queued
runner puts the cap on only after H1-H3 and the live three-helper queue check pass.
Each old app is saved under `/Applications` before a new copy replaces it.
The app was built with Node 22 from the earlier desk source plus this helper fix,
so another agent's unfinished recorder app is not mixed into the build.

## 3. Requests whose sender left

| Mark | Need | Result |
| --- | --- | --- |
| Skip dead requests before prompt reading | A small, safe change | Follow-up, not changed here |

The gateway can still be waiting on the brain after the desk app has gone away.
The brain needs a reliable cancellation signal from that gateway before it can
skip the request. Guessing from the brain socket alone is not enough. This also
touches code shared with the memory work, so it is not a small add-on.

## 4. Keep the two measurements

| Job | Need | Result |
| --- | --- | --- |
| 2 GB cache | Live guard must match v2b; replay chats must be test; never 3 GB | Old job refused the old guard; safely requeued |
| One loop versus two | Measure only; keep the question set and marks fixed | Safely requeued; both frozen hashes match |
| Blind judge | Sol only | Not started here; no new answers to judge yet |

Cache queue PID: `73083`. Loop queue PID: `73082`. Helper queue PID: `56406`.
No ticket was renamed. The loop runner had only been waiting for idle; its exact
child PID was stopped so the new runner could read the safety checks.
All three jobs now check the lock owner, at least 5 idle minutes, and at least
40% free memory. The loop run still needs 10 idle minutes to start, as its fixed
setup says. The cache stays at 2 GB. No one-loop setting is installed.

## Checks run

| Check | Result |
| --- | --- |
| Focused Node 22 checks | 25 passed, none failed |
| Full desk suite, requested 900-second limit | 1,102 passed; 8 failed; 5 cancelled; 1 skipped |
| Same suite before this fix | 1,097 passed; same 8 failures, same 5 cancellations, 1 skipped |
| Compare failing and cancelled test names | Exact match; no added broken test |
| Lock/idle/memory gate tests | 2 passed |
| Runner syntax and both frozen hashes | Pass |
| App build and both app signatures | Pass |

The 8 suite failures are in the known agentbench, fake-sleepmode,
login1-electron, realpath, and 8192-token groups. The 5 cancellations are in
`secure-login.test.js`; those also happen before this fix. They are called out
because they were not in the supplied known-failure list.

Full local records and the queued runner live in:
`~/learner-ops/aon-notes/helper-bg-20261106/`.
Read `live.log`, then the newest `out-*` folder, for any live results after this
handoff. The source for that live check is `hb_test.py`; the queue check uses
`hb_cap_test.js`. Do not count an incomplete or safety-stopped run as a pass.

## Three short lines

The helper fix is built.
The one-at-a-time line is ready, but still off.
The safe live check must pass before we call it a win.
