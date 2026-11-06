# Local hands recorder

Standalone install: `python3 install.py`. This copies only the recorder and builds a small native helper in `~/learner-ops/hands-recorder/`. It does not load launchd or start recording. No Electron app edit/build is needed.

- Permission buttons: `~/learner-ops/hands-recorder/recorderctl permissions`
- Native fake-field test permission buttons: `~/learner-ops/hands-recorder/recorderctl canary-permissions`
- Fake-field test, with Ben away five minutes: `~/learner-ops/hands-recorder/recorderctl canary`
- Read-only check: `~/learner-ops/hands-recorder/recorderctl preflight`
- **After lead go:** `~/learner-ops/hands-recorder/recorderctl start`
- **Stop:** `~/learner-ops/hands-recorder/recorderctl stop`
- Status: `~/learner-ops/hands-recorder/recorderctl status`

macOS needs Screen & System Audio Recording (screen capture only, no audio) and Input Monitoring for Hands Recorder/the responsible host shown in the prompt. The native fake-field test additionally needs Accessibility to inject its fake typing. Enable only the named test/recorder host; quit/restart after macOS requests it. No permission prompt was opened during installation.

ScreenCaptureKit captures the foreground window at 20 fps into local H.264 hardware encoding, 1280×720 overview plus a center detail crop. No field detector or password screen blanking. A Quartz tap saves events macOS delivers, optionally noting Secure Event Input. The current detail crop is centered; cursor-following detail is deferred. Mouse motion is coalesced to 120 events/s; key and button transitions are retained. A bounded 256 KiB event-log cap pauses collection rather than buffering without limit. Encoded bytes pass through a byte-budgeted writer, so an encoder cannot write beyond its reserved clip budget.

30-second clip chunks; at most 3 GiB newly written/day, 12 GiB total; stop/pause below 10 GiB free. Mathematical keep-set at most 2 GiB. Untrained clips expire after seven days. `Retention.finishSleep({judged:true,trainedIds,losses})` handles judged-sleep cleanup without reading video while awake. No sleep reader or app integration is installed yet. A crashed/unfinished sleep cannot mark clips spent. Actual native secret-canary testing is blocked until the required permissions are granted; do not call T9 passed before that test.
