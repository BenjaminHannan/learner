# Glim's recorder, inside Premonition

Recording is OFF. The lead must give a separate go after the password test.
Everything stays on this Mac. No recording reader or controller runs here.

`~/learner-ops/hands-recorder/recorderctl`:

- `preflight`: check actual Screen Recording, Input Monitoring and Accessibility from a native role of Premonition. Shows its OS responsible bundle and process.
- `start --fake`: record generated test pictures only.
- `stop`: stop capture, close the host, persist OFF. No auto-resume or launchd job.
- `status`: check without starting anything.
- `canary`: fake normal/secure field test inside Premonition; requires Ben idle five minutes. It stops on physical input or focus loss.
- `permissions`: explicitly request missing screen/input grants for Premonition.
- `canary-permissions`: explicitly request missing input/accessibility grants for Premonition.
- `start`: real capture only when `LEAD-RELEASE.json` says `{"approved":true}`. Installation never creates approval. The lead creates it only after reviewing T9 and giving the separate go.

The app's entry chooses its role before loading `main.js`. Normal launches load chat unchanged. Recorder launches load neither chat nor a brain. Native capture and the canary are libraries inside a dedicated process of the existing Premonition executable; this reuses its real bundle identity. The controller uses LaunchServices with ELECTRON_RUN_AS_NODE removed. A direct shell launch can instead inherit the shell's Privacy identity, so do not use it.

1280×720 overview, 192×192 center detail, 20 fps, H.264 VideoToolbox. Mouse motion at most 120 events/s; key/button changes as received. No password detection, pixel blanking or field pause. Secure Event Input must pass the fake native-field canary before release. No audio capture.

Caps: 12 GiB total, 3 GiB/day, 2 GiB keep-set, seven days, pause below 10 GiB free. Every write checks quota/free bytes. Judged sleep deletion keeps only the fixed mathematical keep-set. Deletes use exact indexed paths and append retention.log. The sleep reader is still a later step.

Build/install: `python3 desk/tools/hands-recorder/install.py`, after the full desk suite. This adds a bootstrap and recorder modules to the installed app; it does not restart chat or re-sign the outer app. The original package.json is saved under `hands-recorder/rollback/`. Restore that original manifest after stopping the recorder to route all launches straight back to main.js. Any actual chat/brain restart still needs the model lock and five idle minutes.


2026-11-06 test run: Ben confirmed he was away, so the lead authorized `recorderctl canary --ben-confirmed-away` without waiting five minutes. Default canary idle checks and physical-input/focus-loss stops remain. The native secure-field canary passed with a normal-field positive control.

The separately authorized `recorderctl scratch-benchmark --ben-confirmed-away` captures only the main display for at most 120 seconds, stops on physical input, deletes its two exact scratch video files, and leaves regular recording OFF. It requires explicit away confirmation. `recorderctl stop` also stops this role. This test command does not create LEAD-RELEASE.json. See REPORT.md for actual CPU/RAM/storage cost.
