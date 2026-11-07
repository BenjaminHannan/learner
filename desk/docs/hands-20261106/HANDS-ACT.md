# HANDS-ACT partial report

This is **not a desktop-control pass**. No app was installed or started, no real input was sent, and no screenshot was taken. Ben's away status was not established. A test window cannot supply the required physical-device takeover trials by itself.

## What changed

The chat agent now checks that an actual affirmative answer or an existing `free` setting exists before the legacy hands can send an action. It also rejects an unanswered approval card for screen control. The test invokes the real legacy hands timeout with a fake clock: after the timeout, the guarded sender is not called.

This is a boundary around the **chat agent path**, not a repair of every caller. `src/hands.js` still has its old timeout and can show an incorrect notice saying Glim is using the mouse after no answer; `main.js` also has a separate `freezeOnly` path. These files are outside HANDS-ACT's write allowlist. The guard does not implement the real stop-lease. The existing native guard has no event posting and the existing lease explicitly targets the sandbox. Do not call this ready for real desktop control.

## Tests and checks

* In `desk/`, `node --test test/computer-control-consent.test.js test/hands-toy/lease.test.js`: exit 0, 8 passed, 0 failed. These are fake and sandbox tests, not physical-device proof.
* In `desk/`, `node --test test/agent.test.js`: exit 0, 59 passed, 0 failed. This ran before the final narrowing of the approval check to computer-control calls; the focused test was rerun after that narrowing.
* `git diff --check`: exit 0 at the time checked.
* Real tasks: Notes 0/2, Safari 0/2, Finder 0/2, TextEdit 0/2, Settings 0/2 **run**, not failures or passes. Screenshot hashes: none. Physical takeover timings: none. No-actions-when-not-asked and the end-to-end attempt log remain unverified.

## Log coordination

`ATTEMPT-LOG.md` was absent when checked and no NIGHT-LEARN worker was reachable in this session. Proposed JSONL shape, subject to that owner's agreement: one line per attempt, with `schema`, `attempt_id`, `request`, `started_at`, `ended_at`, `steps` (each containing `intent`, pre/post screenshot SHA-256, `action`, `actor` (`hands` or `glim`), and Glim's verification), `outcome`, and `pass`. Include cancelled and failed attempts. This is a proposal, not a published or implemented contract.

## Work still needed

Build and wire a real native input arbiter that watches physical input and releases owned holds atomically; implement screenshots, drag, scroll, typing, key chords and app opening through it; connect the big brain and small policy with fresh before/after checks; agree and implement the log; then perform the ten tasks and ten physical takeover trials under the stated conditions. The current app's tool definitions, screen adapter, legacy hands and main wiring live outside this task's write allowlist, so their owner must coordinate the required changes. No result here proves the requested 8/10 or 10/10 marks.
