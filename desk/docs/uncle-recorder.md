# Glim for Wujek Bartek: recording setup

Recording is off. The new Yes/No screen saves a choice only. It cannot start a recorder, request Mac permissions, read a picture, or run a brain. Yes is not a T9 pass. Do not share this build yet.

The first Mac setup asks: “Glim can learn by watching how you use the computer. It stays on this Mac.” Enter, Escape and Skip cannot say Yes. No is saved too, so the screen does not keep coming back. A broken choice file means ask again, not start recording. Only the app's own window can save the choice; ordinary settings and model tools cannot grant it.

## Space limits

`src/recorder-setup.js` exports `diskCaps(freeBytes)`. Leave at least 10 GiB free. Use at most one fifth of the space above that floor, up to 12 GiB total. New clips per day use at most one quarter of that total, up to 3 GiB. The keep-set uses at most one sixth of the total, up to 2 GiB. Clips still expire after seven days. A failed disk check gives a zero-byte budget. For example, with 30 GiB free, the caps are 4 GiB total, 1 GiB/day and about 0.67 GiB kept.

The HANDS recorder must enforce these caps through its existing quota writer and retention code, not just show them on screen. Its fixed keep formula, spent-clip rules, exact indexed-path deletion and retention log stay unchanged. Never delete personal files to make room. Recheck free disk before each new capture session; the recorder must also keep checking the 10 GiB floor while writing.

## After the lead approves T9

1. Bring the reviewed HANDS source and native bridge into this `mac-uncle` checkout. Use Premonition's own child process and Mac identity. Do not bring over `state.json`, approvals, logs, clips, canary output, saved settings or any part of Ben's home folder.
2. Replace the setup-only status with the actual recorder status. Real capture must require the saved local Yes, the approved bundled recorder, and both Mac permissions. Enforce that check in the host and direct native capture entry too. A CLI flag, Mac permission, generic setting, old standalone release file or restart must not bypass No.
3. Pass `diskCaps()` into `new Recorder({ retentionOptions: { caps } })`. Keep the choice file and clips under the uncle's own app data, not a developer home path. Add a visible recording switch and exact-PID stop; turning it off, quitting or crashing must not resume capture on restart.
4. Request permissions only after Yes and a deliberate start. The screen already explains the Premonition name, Screen & System Audio Recording, Input Monitoring, quit/reopen, no audio, and the risk of private things appearing in pictures. Do not promise every password widget is safe.
5. Run consent/host/native-path tests and the full desk suite. Build from a clean archive, sweep the whole package, and rerun the fresh-home e2e and both brain-size measurements under the idle model lock.

Only after the recorder is in the package and the final package passes e2e may Ben share it. UNCLE-S does not upload to Drive.

## The first-run test

The checked-in runner is in `tools/uncle-mac/`; the live copy is `~/learner-ops/uncle-mac/test/`. Keep both copies together. Shell files must be executable. `gated.sh` uses the canonical `~/learner-ops/bin/realmodel-lock.sh` and the same `uncle-mac` owner. Never rename a ticket. It waits for five idle minutes and 40% free memory, then checks again inside the lock. The idle guard stops the exact test process if Ben returns; its cleanup stops only the app and brain PIDs it owns. This is a retry, not a pass.

Every run gets its own empty home under `test-home/runs/`. The app is still taken from `test-home/Applications/`; it must match the app on the image mount in `.mnt`. After a rebuild, remount the new image and replace that test app before requeueing. `test/last-home` tells the two measurements where the latest test brain lives. Old synthetic test homes stay separate; they never enter a package.

`test/marks.jsonl` lists actual checks. `test/results.json` exists only after all required marks and both measurements pass, and includes the unchanged image's SHA-256. A recorder-bearing app also needs off-by-default, explicit No, and still-off-after-restart marks. Missing replies, wrong names/facts, failed measurements and a changed image cannot pass. A successful run appends its checked marks to `REPORT-S.md`. A “done” line alone is not proof.
