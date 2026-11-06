# HANDS toy report

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
| T9 recorder | **INCOMPLETE** | Caps/retention/stop/fake-resource checks passed; native secret canary and real capture cost blocked by macOS permissions. |
| T10 sleep/undo | PARTIAL | Pixel model, shared-file workers, training/idle gates and whole-bundle quarantine checkpointed. No training, export, promotion or neural rollback evidence yet. |

Original frozen marks hash: 59087e05d7536d2ae5cf9bb44015e564ab1745a229c73adfcf01f655000b49ac. Dated retention/password/lean amendments are preserved separately. No marks were quietly relaxed to call this a pass. BensPC, its GPU, real Nanbeige, and Ben's recordings were not used.

### Five lines for Ben

The recorder is built, but it is off.  
Fake recordings used about 123 MB of memory.  
Old clips have small limits and clear delete rules.  
Mac permission buttons block the real password test.  
Nothing is watching you yet.
