# HANDS toy report

## T9 password canary PASS — 2026-11-06, Ben confirmed away

The real Premonition canary typed into a normal NSTextField and a real NSSecureTextField. The normal control was seen by the tap, the secure field received the fake secret, and the fake secret had **zero hits in 26 saved files**. Ben explicitly waived the five-minute idle wait for this run; physical-input and focus-loss stops stayed on. No Glim/chat process was changed.

Search scope: every regular file recursively under `~/learner-ops/hands-recorder/premonition-canary`, `premonition-fake-recordings`, `canary-results`, `fake-recordings`, and `recordings` (absent). This includes saved movies, input logs, indexes, state and canary verification output. Source and binaries are excluded because they contain the fake test constant. Evidence: `T9-premonition-canary.json`.

T9 retention, caps, stop/OFF and reader checks retain their earlier PASS marks. **T9 now PASS for the requested recorder gate.** Recording remains OFF and no regular lead release exists. The separately authorized two-minute desktop-cost measurement is complete; both scratch videos and their directory were deleted.


### Live desktop cost and final state

| Item | Measured result |
|---|---|
| Capture | Main display, 1280×720, configured 20 fps; overview plus 192×192 center crop, H.264 VideoToolbox; no audio or key text |
| Duration / frames | 120.013 seconds / 2,336 frames (19.46 frames/s delivered) |
| Added recorder peak RAM | 373.95 MiB summed process RSS |
| Added recorder mean CPU | 49.63% of one CPU core over a 120.078-second sample window |
| Saved bytes | 20,918,214 bytes; 10,457,974 bytes/minute (10.46 decimal MB/min) |
| Scratch cleanup | PASS: both exact generated video paths deleted, scratch directory absent |
| Stop / regular setting | PASS: all recorder-role descendants stopped; regular setting OFF; LEAD-RELEASE.json absent |
| Permissions | Premonition: screen/input/accessibility all granted; no new toggle needed |

CPU is the sum of process CPU-time increments sampled once per second. RAM is the maximum summed resident memory of the isolated recorder host and its descendants, including native capture and ffmpeg. Existing chat/brain processes are excluded; system-wide WindowServer/GPU service costs are not included. This measures live desktop capture, not policy inference or frame→action latency. **About half of one core is a material cost: the live path is not yet proved lightweight for Ben's everyday use.** No optimization or release is implied by the T9 safety-test PASS.

Only numerical evidence survives outside the scratch folder: `T9-live-desktop-resources.json` (local per-second process samples), compact mirrored evidence, and this report. No footage was uploaded, trained on, or retained. The existing foreground-window regular recorder was not enabled; the one-time benchmark explicitly selected the main display. RUN-NOW's Glim/chat processes were not stopped or restarted.

Validation: full desk suite before native build: 1,120 tests, 1,111 passed, eight known failures (agentbench ×2, fake-sleepmode, login1-electron, realpath ×3, 8192-token prompt), one skipped, 39.690 seconds. Focused recorder tests: 16/16 pass. After the live run, the stop/no-auto-resume/release smoke check passed again using fake pictures only. All other T1–T10 statuses below are unchanged.

## Earlier handoff, before the authorized canary — 2026-11-06

**Installed and OFF. No new Privacy toggle is needed. T9 is still INCOMPLETE because Ben is active, so the native password test deferred.** This section supersedes the standalone permission instructions below. No Ben footage or keys were collected. Do not release real recording yet.

The recorder now runs as a recorder-only process of **Premonition.app**, and the canary uses that same executable. The native code loads inside that process through a small N-API bridge. Normal app launches still load the existing main.js. Recorder launches do not load chat or a neural model. No chat or brain restart was performed. The existing Python Glim was attributed to T3 Code during the initial inspection, so putting capture there would not have solved this permission problem.

Actual native preflight from the new role reports **screen=true, input=true, accessibility=true**, responsible name Premonition, bundle `com.electron.premonition-desk`, bundle path `/Applications/Premonition.app`. Electron's own screen/accessibility checks agree. A first Swift-child prototype had the right responsible parent but could not use those grants; native calls inside the Premonition executable resolved that. The final path uses the real app identity, not a second app that merely copies its name or bundle ID.

| Privacy & Security list | Entry | Measured state | Ben needs to do |
|---|---|---|---|
| Screen & System Audio Recording | Premonition | Allowed | Nothing |
| Input Monitoring | Premonition | Allowed | Nothing |
| Accessibility | Premonition | Allowed | Nothing |

No permission request prompt was opened. The old **Hands Recorder.app** and **Hands Recorder Canary.app** were removed, along with their unused launchd plist and daemon. If old Hands Recorder entries remain in System Settings, Ben can turn them off/remove them. No TCC grants were reset. The outer app was already ad-hoc signed with an invalid resource seal before this work; its executable and outer signature were not replaced or re-signed. The observed existing grants still work.

| Recorder check | Result | Evidence / limit |
|---|---|---|
| Actual Premonition Privacy identity and grants | PASS | Native preflight above; TCC log subject is the real bundle ID. |
| Retention/caps/path scope/log consistency | PASS | Existing 12 tests across seeds 101/202/303; spent cleanup, keep cap, age/space backstops, untrained protection and outside-path rejection. Production caps remain 12 GiB total, 3 GiB/day, 2 GiB keep-set, seven days, pause below 10 GiB free. |
| Entry isolation, release gate, canary byte-search guard | PASS | Four added unit tests; 16 targeted tests total, all pass. A deliberately leaking fake saved file fails verification even if a synthetic native result says PASS. This unit test does not substitute for the native canary. |
| Stop and persistent OFF | PASS | Fake recording stops the exact recorder host and descendants. Fresh preflight does not resume it. Real start is refused without the separate lead release. Two smoke runs passed. |
| Native NSSecureTextField canary | DEFERRED | Premonition has permission, but physical idle time was below 300 seconds. No normal/secure typing or complete saved-file canary search occurred. This is not a zero-hit pass. |
| Native capture cost on Ben's desktop | NOT RUN | Real recording remains forbidden pending the separate go. |

Fake recording measurement: **35.236 seconds**, generated 1280×720 video at 20 fps plus a 192×192 center crop, H.264 VideoToolbox. Saved **11,486,425 bytes**, or **19,558,945 bytes/minute** (~19.6 decimal MB/minute). RAM is peak summed process RSS; CPU uses deltas in process CPU time over a 30.001-second window after a five-second warm-up, as percent of one core. The fake source includes generation/encoding, not live ScreenCaptureKit/event-tap overhead.

| Processes measured | Peak RAM | CPU, one core |
|---|---:|---:|
| Added recorder role + all its children/encoder | 277.9 MiB | 9.83% |
| Existing Premonition chat + children | 904.0 MiB | 63.33% |
| Existing Glim brain + children | 2042.5 MiB | 2.20% |
| All together, simultaneous peak | 3219.8 MiB | 75.36% |

The chat/brain workload was already running; its CPU is not recorder overhead. Their PIDs stayed unchanged during the measurement. The total peak is measured at one instant, not the sum of unrelated peak times. The recorder exited after measurement and after the repeated stop tests. Persistent state is `{"enabled":false}`. No launchd job is loaded.

Commands:

    ~/learner-ops/hands-recorder/recorderctl preflight
    ~/learner-ops/hands-recorder/recorderctl canary
    ~/learner-ops/hands-recorder/recorderctl stop
    ~/learner-ops/hands-recorder/recorderctl status

Run the canary only when Ben is away; its own 300-second check enforces this. It runs entirely under Premonition and verifies its fake saved files, including a normal-field positive control. Stop after checking. Real start remains blocked by the missing `LEAD-RELEASE.json`; installation never creates approval. The lead can create that separate approval only after the native canary passes and the lead gives the go. The Settings switch and sleep reader remain deferred, as requested; recorderctl is the current switch.

Rollback: after `recorderctl stop`, `python3 ~/learner-ops/hands-recorder/rollback.py` changes only the package entry back to main.js. It does not restart chat or touch recordings. The first exact installed manifest backup is in `hands-recorder/rollback/20261106-125037/`. A future restart still needs the real-model lock and five idle minutes.

Validation: full desk suite was run before installation and after the code changes. Baseline: 1115 tests, 1106 pass, eight known failures, one skip. Final: **1120 tests, 1111 pass, eight known failures, one skip**, 42.080 seconds. The eight failures are agentbench (2), fake-sleepmode, login1-electron, realpath (3), and the 8192-token prompt check. No new failure category appeared. Full logs remain local in the notes folder. No BensPC, new brain, app bundle duplication, training, or publishing was used.

```text
The recorder now lives inside Premonition.
It uses the permission switches already on.
The pretend-picture test and stop button work.
The password test waits until you are away.
It is OFF and has not watched you.
```

---


## Milestone (a), 2026-11-06

Design frozen before toy outcomes: SHA-256 59087e05d7536d2ae5cf9bb44015e564ab1745a229c73adfcf01f655000b49ac. Approved disk amendment is in that hash. T1–T10 are not relaxed.

Built a bounded lease, sandbox-only input receiver, actual RGB playground with the four GUI tasks and the existing Sparks engine, a manual playground window, and a native Mac stop-guard source. No production OS input backend exists in this toy.

- New Node tests: 3/3 pass. Structured rule reference finishes all four GUI tasks on seeds 101, 202, 303. These short contract checks are not the frozen 120-episode T1 evaluation.
- Synthetic sandbox takeovers: 300, zero later accepted packets, zero stuck holds. Callback→release p95 0.009875 ms, max 0.031208 ms.
- Compiled Swift guard, same locked revoke path as its physical tap: 300 synthetic callbacks, 0 failures, p95 0.000125 ms, max 0.000792 ms. This excludes physical input/tap delivery and IPC.
- **T8 is PARTIAL, not passed:** physical-device delivery and native OS held-input release remain unproven. The helper deliberately cannot post real input. Neither measurement proves a 10 ms physical-device response.
- Full baseline desk suite: 1,092 tests; 1,083 pass, 8 fail, 1 skip. All eight failures are in the supplied known list: agentbench (2), fake-sleepmode, login1-electron, realpath (3), and 8192-token prompt. Baseline log is beside this report.

No Ben recording, real-brain use, BensPC use, app install, or desktop input. Next: pixel worker and sleep/export, then fake recorder tests.

The big brain picks the job.  
The little playground is ready for safe tests.  
Its stop switch drops old moves when touched.  
We have not proved the real mouse stop yet.  
Nothing is watching Ben.


## Standalone recorder handoff — 2026-11-06T12:41:43.946605-05:00

**Built and installed at ~/learner-ops/hands-recorder/. OFF. launchd is not loaded. T9 is INCOMPLETE, not passed.** The native fake-password test cannot run in this session: macOS preflight reports Screen Recording=false, Input Monitoring=false, Accessibility=false. It did not type the canary or search a saved tap stream. An empty tap is not counted as a zero-hit pass. No Ben screen or key recording has occurred.

The latest lead order supersedes the old app build order: ship standalone first, test essentials, report and stop. Electron integration was removed from this change. No app wiring, app rebuild, install, or new full desk suite was performed for the standalone step. Other agents' main.js/agent.js/test edits remain theirs.

### Essential checks

| Check | Result | Evidence / limit |
|---|---|---|
| Native NSSecureTextField password canary | **INCOMPLETE** | Missing Input Monitoring/Accessibility. Normal-field control=false; secure typing=false; saved-file search=false. Need permission before this can pass. No password detector or blanking is implemented, per latest rule. |
| Tiny caps, spent cleanup, keep-set, seven-day expiry, outside-path protection, byte log | **PASS** | 12 Node tests, seeds 101/202/303. Exact indexed paths only; traversal and symlink escapes rejected before any deletion. Keep-set uses the frozen arithmetic formula, never model prose. Untrained clips deleted only under expiry/space backstop or explicit Delete this session. |
| Stop command | **PASS** | Fake standalone daemon PID 60554 exited; state and status are OFF; no launchd job loaded. No per-delete prompts. Child stops use their exact PIDs. |
| Fake recording resource measurement | **MEASURED** | See numbers below. Native ScreenCaptureKit/event-tap overhead is unmeasured because permissions are absent. |

### Recording cost measured on this M1

Final production byte-budgeted writer, using a fake moving 1280×720 source at 20 fps, two local H.264 VideoToolbox streams (overview plus 192×192 center detail), no Ben data:

- Duration: 30.034 seconds.
- Peak combined resident RAM, Node recorder + encoder/generator: **122.875 MiB**.
- Mean combined CPU after five-second warm-up: **4.764% of one CPU core**, sampled with ps. This is not percent of the whole Mac.
- Saved bytes: **9,873,153**; **19,723,920 bytes/minute** (about 19.72 MB/minute, decimal).
- Recorder state after stop: OFF; encoder error: none. This is a fake-source encoder cost, **not a measurement of the complete real desktop capture path**. The earlier 65-second run measured 126.188 MiB / 3.055% one-core CPU / 19.23 MB/min but included an intentional-stop status bug; that bug was fixed, and the final run above is authoritative.

Source overhead includes making the fake moving image. The real source uses ScreenCaptureKit and a Quartz tap, but its RAM/CPU still needs a permitted run. Current detail is centered; cursor-following detail is deferred. Mouse motion is coalesced to at most 120 events/s, while key/button transitions are preserved. A 256 KiB event-log cap pauses instead of growing RAM. The recorder has no policy, no replay API, and no path to send input.

### Caps and retention actually installed

12 GiB total / 3 GiB newly saved per day / seven-day maximum age / 10 GiB free-space floor. Keep-set <=2 GiB, with audit/rare/high-loss/untrained tags. The encoded streams go through a quota-checked writer before disk writes; in-flight chunks count toward the reserved clip budget. Deleting clips never resets the daily ingestion counter. At judged-sleep completion, the retention API marks trained clips spent, keeps only selected useful/audit examples, and deletes spent non-keep clips, including frames, events and labels. A crash or unjudged sleep cannot mark anything spent. The sleep reader itself remains deferred to the later app step.

retention.log records exact clip IDs, paths, actual indexed bytes and spent/over-cap/expired reasons (user-delete for Ben's explicit button/API). Recovery journals allow a partially deleted indexed clip to finish. A stale lock is reclaimed only after its exact owner PID is dead. No personal file is a deletion candidate.

### Ben's permission buttons and commands

No permission prompt was opened by this work. Ben needs to click Allow/enable the named Hands Recorder (or responsible host macOS identifies) in System Settings → Privacy & Security → **Screen & System Audio Recording** and **Input Monitoring**. Capture records no audio. The fake-typing test additionally needs **Accessibility** for Hands Recorder Canary, plus Input Monitoring. Follow macOS's quit/restart instruction if shown.

    ~/learner-ops/hands-recorder/recorderctl permissions
    ~/learner-ops/hands-recorder/recorderctl canary-permissions
    ~/learner-ops/hands-recorder/recorderctl preflight
    ~/learner-ops/hands-recorder/recorderctl canary

The canary command uses a real NSSecureTextField, a normal-field positive control, stops if Ben touches the controls or focus changes, and searches every file in its fake result directory. It requires Ben away for five minutes. It does not enable real recording. A passed native test proves this field path only; it does not establish Secure Event Input behavior for every third-party password widget.

**After the lead sees T9 pass and gives the go:**

    ~/learner-ops/hands-recorder/recorderctl start

**One-command stop, tested:**

    ~/learner-ops/hands-recorder/recorderctl stop

The launchd plist is ~/learner-ops/hands-recorder/local.glim.hands-recorder.plist. Start loads it; installation did not. Stop writes persistent OFF, signals only the verified exact daemon PID and unloads the job. Later login cannot override OFF. Standalone state.json is the on/off switch for this release; there is no Electron settings toggle yet.

### Frozen toy marks at handoff

| Mark | State | Evidence / remaining work |
|---|---|---|
| T1 GUI | NOT RUN for pixel policy | Glim's own structured-rule collector completed 120 GUI episodes, 120 successful, 1605 saved frames. This is controller B data, not W1 evidence. |
| T2 game | NOT RUN | Pixel renderer wraps the real Sparks adapter; no frozen pixel-policy game trial yet. |
| T3 comparisons | INCOMPLETE | No real slow-brain A run, W0 or W1. No model lock or second brain used. |
| T4 actions/s | NOT RUN | No trained pixel artifact; fake recorder's fps is not action throughput. |
| T5 frame→action | NOT RUN | No end-to-end pixel-control measurement. Recorder encoding is not frame→action latency. |
| T6 sleep gain | INCOMPLETE | One actual day of own-attempt data only. No fabricated held-out/audit days; no training or promotion performed. |
| T7 intent | NOT RUN | Checked versions/lease exist; no trained intent ablation yet. |
| T8 takeover | PARTIAL | Milestone (a) synthetic evidence above; physical-device/native OS input proof still missing. Not a gate on observation-only recorder, per lead. |
| T9 recorder | **PASS — recording OFF pending lead go** | Native secure-field canary and positive control passed; zero secret hits in 26 saved files. Caps/retention/stop/OFF and fake-data checks passed. Two-minute live screen cost measured and scratch capture deleted. |
| T10 sleep/undo | PARTIAL | Pixel model, shared-file workers, training/idle gates and whole-bundle quarantine checkpointed. No training, export, promotion or neural rollback evidence yet. |

Original frozen marks hash: 59087e05d7536d2ae5cf9bb44015e564ab1745a229c73adfcf01f655000b49ac. Dated retention/password/lean amendments are preserved separately. No marks were quietly relaxed to call this a pass. BensPC, its GPU, and real Nanbeige were not used. Ben separately authorized the temporary real desktop measurement reported above; it was deleted.

### Five lines for Ben

The password test passed.  
Normal typing showed up; the fake password did not.  
The short screen test used some memory and about half of one core.  
Its videos are gone.  
The recorder is off until you say go.
