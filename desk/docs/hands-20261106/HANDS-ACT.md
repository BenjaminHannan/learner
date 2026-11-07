# HANDS-ACT work in progress

This is **not a desktop-control pass**. The new control path has not been installed or tested with real input. Ben's away status was not established.

## What changed

The earlier chat permission fix remains. The new path sends input through a native guard in a separate Premonition process. It takes a picture, prepares one action, waits for Glim to confirm a new picture, sends the action, takes another picture, and requires a visual check. The new local attempt log follows the proposed `ATTEMPT-LOG.md` format and keeps unfinished or model-only results unknown. An approved, hash-checked toy policy can propose a point; if none exists, Glim chooses the point. This has only fake-test proof so far and is **off for ordinary chat**. A test process can opt in with `GLIM_HANDS_TEST=1`; the ordinary-chat release file is not created here.

This path is inside the chat agent; it is not a repair of every caller. `src/hands.js` still has its old timeout and can show an incorrect notice saying Glim is using the mouse after no answer; `main.js` also has a separate `freezeOnly` path. These files are outside HANDS-ACT's write allowlist. Do not call this ready for real desktop control until the physical-input tests pass and the other callers are coordinated.

## Tests and checks

* In `desk/`, `node --test test/computer-control-desktop.test.js test/computer-control-consent.test.js test/hands-toy/lease.test.js`: exit 0, 18 passed, 0 failed at that run. These are fake and sandbox tests, not physical-device proof.
* In `desk/`, `node --test test/agent.test.js`: exit 0, 59 passed, 0 failed. This ran before the final narrowing of the approval check to computer-control calls; the focused test was rerun after that narrowing.
* `git diff --check`: exit 0 at the time checked.
* Real tasks: Notes 0/2, Safari 0/2, Finder 0/2, TextEdit 0/2, Settings 0/2 **run**, not failures or passes. Screenshot hashes: none. Physical takeover timings: none. No-actions-when-not-asked and the end-to-end attempt log remain unverified.
* A takeover harness is prepared but not run. Its simulated physical input is a tagged CGEvent posted by a separate helper process. It checks release timing and up-events in a throwaway window, and stops if its independent monitor sees real input or the window loses focus.

## Log coordination

`ATTEMPT-LOG.md` now exists and is used by this path. It remains labelled a proposal. The log records image hashes, not image bytes, and therefore does not itself provide the time-aligned image/action data needed for training. It must not be treated as independently verified training evidence.

## Work still needed

Finish the shared-format agreement and coordinate the older `freezeOnly` caller; run the full suite and install from committed HEAD under the shared lock; then perform the ten tasks and ten physical takeover trials under the stated conditions. The current app's legacy hands and main wiring live outside this task's write allowlist. No result here proves the requested 8/10 or 10/10 marks.
