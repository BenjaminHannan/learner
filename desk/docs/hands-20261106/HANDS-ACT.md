# HANDS-ACT work in progress

This is **not a desktop-control pass**. REC-LIVE-4 installed a signed app containing the new control path, but it has not yet been tested with real input.

## What changed

The earlier chat permission fix remains. The new path sends input through a native guard in a separate Premonition process. It takes a picture, prepares one action, waits for Glim to confirm a new picture, checks that the screen has not materially changed, sends the action, takes another picture, and requires a visual check. The new local attempt log follows the proposed `ATTEMPT-LOG.md` format and keeps unfinished or model-only results unknown. An approved, hash-checked toy policy can propose a point; if none exists, Glim chooses the point. This has only fake-test proof so far and is **off for ordinary chat**. A test process can opt in with `GLIM_HANDS_TEST=1`; the ordinary-chat release file is not created here.

Desktop screenshots now use Glim's existing eye encoder and image-feature path, even when the separate captioning setting is off. An unavailable encoder stops the task. The running brain's projector and the complete image path still need real-model verification. A terminal takeover also stops the chat task.

Mac chat now blocks its old mouse, keyboard and app-opening tools when the checked path is unavailable. This path is inside the chat agent; it is not a repair of every caller. `src/hands.js` still has its old timeout and can show an incorrect notice saying Glim is using the mouse after no answer; `main.js` also has a separate `freezeOnly` path. These files are outside HANDS-ACT's write allowlist. Do not call this ready for real desktop control until the physical-input tests pass and the other callers are coordinated.

## Tests and checks

* In `desk/`, `node --test test/computer-control-desktop.test.js test/computer-control-consent.test.js test/hands-toy/lease.test.js test/agent.test.js`: exit 0, 86 passed, 0 failed. These are fake and sandbox tests, not physical-device proof.
* After the takeover test harness changes, the first three focused files above: exit 0, 27 passed; the test helper compiled with `xcrun swiftc` for arm64: exit 0.
* At committed `31277e836`, with `TMPDIR=/tmp` in a clean archive under the shared install lock, `perl -e 'alarm 900; exec @ARGV' node --test`: exit 1, 1,230 passed, 8 failed, 1 skipped. The eight failures are the listed known agentbench, fake-sleepmode, login1-electron, realpath, and 8192-token failures. Raw output: `/tmp/aon/hands-act-full-31277e836-space-restored.log`. Earlier runs exposed recorder test failures when temporary copies reduced free space below the recorder's 10 GiB floor; removing our obsolete copies restored space and the recorder tests passed in this full run.
* The newly installed app's `codesign --verify --deep --strict /Applications/Premonition.app`: exit 0. Its installed `src/agent.js` and `src/computer-control/vision.js` match the working source hashes `b884b9e0dd5166012a9c44fcd11d55016794b1c53526fcc5db7940b10807cf9d` and `90feecbce5f1d17da4ca93550664a3f716ef6b30de139dd6fcfc2a53310485c2`. `node src/computer-control/trial-launch.js preflight`: exit 0, accessibility/input/screen all `true` under Premonition's identity.
* `git diff --check`: exit 0 at the time checked.
* Real tasks: Notes 0/2, Safari 0/2, Finder 0/2, TextEdit 0/2, Settings 0/2 **run**, not failures or passes. Screenshot hashes: none. No-actions-when-not-asked and the end-to-end attempt log remain unverified.
* The first takeover attempt stopped before trials because its window was not frontmost. A second attempt failed its first trial: a separate helper posted a tagged CGEvent, the guard's terminal revoke arrived 11.573459 ms later and rejected further input, but reported zero held inputs released. The test observed a key-down and key-up, so it could not prove the key was still held when takeover arrived. The raw result is `~/learner-ops/hands-attempts/takeover-1794064717318.json`. This is a failed trial, not a 10/10 pass. The harness is being changed to inject immediately when it observes the guard's down event and to record all revocations; the real test must be rerun and both results reported.
* The independent Notes check can find the test sentence but cannot yet prove the note was newly created. It therefore does not count either Notes trial as a pass without stronger evidence.

## Log coordination

`ATTEMPT-LOG.md` now exists and is used by this path. The log records image hashes, not image bytes, and therefore does not itself provide the time-aligned image/action data needed for training. It must not be treated as independently verified training evidence.

## Work still needed

Coordinate the older `freezeOnly` caller; after REC-LIVE-4's setup and with Ben idle, perform the ten tasks and ten physical takeover trials. The older main wiring lives outside this task's write allowlist. No result here proves the requested 8/10 or 10/10 marks.
