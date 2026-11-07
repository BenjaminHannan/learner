# Quarantined night learning

The LaunchAgent runs `scheduler.js` every five minutes. Production starts only
01:00–07:00 after twenty minutes of idle. It compiles yesterday's indexed clips,
asks the real Glim under the FIFO brain lock for episode goals and reasons,
binds those goals to real action indices, trains three arms on the earlier 80%,
scores later click/key actions, runs retention and writes a scored report.
No code in this directory promotes weights. Sampled desktop frames use separate
image features with timestamps; the client avoids the general-video projector,
which was observed returning an immediate empty response on real screen clips.

Coordinate calibration is an optional stage inside the run. It uses only the
signed `/Applications/Premonition.app/Contents/MacOS/Premonition` executable and
HANDS-ACT's `NativeSession`; it never asks for permissions. After checking idle
again, it posts one mouse move to an empty patch. It then finds the event and
compares before/after video frames. Missing access, activity, missing cursor or
error over ten video pixels yields `coords-unverified`; training continues.
CG global points are offset by the display origin, then scaled to backing
pixels and the recording compositor. Those scales compose to the recorded
video's fit/letterbox mapping. The probe reports error in video pixels.

Compilation hash-binds actual decoded MP4 pixels to the event index. Unmeasured
coordinates or clock mapping are recorded limitations, never fabricated proof.
Such data are useful for quarantined learning, not live policy authorization.
The comparison is in video pixels (40-pixel click radius). A missing action class
is unmeasured and cannot yield a passing promotion score. A single example
trains without inventing a held example; no actions produce an untrained
checkpoint and an explicitly unmeasured report. With video but no input actions,
Glim still describes sampled idle scenes; the report states that the hands
checkpoint contains initial weights and zero supervised updates. Optional corrections never
block a night. Mixed training/holdout clips are preserved by retention.

`node run.js --dry-run [--fixture] [--output /absolute/path]` explicitly permits
today's compute. It uses existing live segments when present, otherwise real
synthetic MP4s with fabricated, clearly labelled metadata. Fixture runs never move the mouse. Real-recording dry runs attempt the
same optional coordinate check, which still requires twenty minutes idle.
Dry runs never change or delete recordings through retention. Glim calls still acquire the FIFO lock.
It does not start, stop or restart any model service. Glim requests carry the
recognized background header and retry short chat/service interruptions within the owned FIFO turn, with foreground
chat retaining priority. Exhausted requests release their ticket before the outer backoff. A malformed optional attempt log becomes a report warning.

`node synthetic-integration.js /absolute/output` separately exercises 400
compiled actions, chronological holdout, a fixed nonzero intent and all three
model arms. It is a bounded synthetic regression, not evidence of real-world
intent understanding or permission to promote a checkpoint.

## HANDS-PC handoff

Read-only lookup happens after the Glim stage at run time in
`~/learner-ops/aon-notes/hands-pc-20261107/`. Optional `remote-training.json`,
`report.json` or `integration-result.json` can specify:

```json
{
  "checkpoint": "/absolute/local/downloaded/native-action.pt",
  "remoteTrainingCommand": ["/absolute/runner", "{dataset}", "{output}"],
  "cleanupCommand": ["/absolute/cleanup", "{dataset}", "{output}"]
}
```

The preferred handoff uses `schedulerCommand` and `managesCleanup: true`.
It calls HANDS-PC's exact leased wrapper:
`desk/src/night-learn-remote/tonight-remote.sh <dataset> <output>`.
The adapter validates the declared starting-checkpoint hash, returned checkpoint
hashes, PC copy deletion and shared GPU lease release. It preserves the runner's
logged native fallback and its refusal to fall back while cleanup is unconfirmed.
It never substitutes a direct GPU runner for this wrapper. Dry runs invoke the
same command. Real-recording jobs retain the runner's 01:00–07:00 / idle rule
and shared lease; a daytime deferral uses the explicit local dry-run fallback. Checkpoint paths can also be
read from HANDS-PC's Markdown report; absence never blocks a night.

For other handoff commands, the runner owns upload, path rewriting and download; stdout must be the same
JSON as local `trainer.py`. The cleanup argv must remove all PC recording
copies, and runs on success or failure before local fallback. Cleanup failures are
reported explicitly; local learning still completes in quarantine. No handoff means
local training. No compatible checkpoint means deterministic fresh init.
This worker never edits the remote worker's folder. A bare command without a
cleanup contract is reported and falls back locally without uploading data.
