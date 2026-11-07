# HANDS night training on BensPC

Train the existing `night-learn/pixel_model.py` on BensPC's RTX 5070 Ti. The
unmodified native trainer supplies evidence validation, labels, the time split,
and model code. Only quarantined `old.pt`, `candidate.pt`, and `no-intent.pt`
are returned, in the **exact output directory supplied by NIGHT-LEARN**.
There is no promotion, scheduler edit, or service installation here.

## Tonight's command

```sh
/Users/ben-hannan/learner-ops/desk-always-on/desk/src/night-learn-remote/tonight-remote.sh "$DATASET" "$QUARANTINE"
```

`DATASET` is the verified JSON manifest NIGHT-LEARN just compiled; `QUARANTINE`
is the same directory it would pass to `trainer.py`. The manifest's
`trainingSteps` is respected (default 100 per arm). Set `preSleepWeights` to:

```
/Users/ben-hannan/learner-ops/aon-notes/hands-pc-20261107/quarantine/candidate.pt
```

That starting checkpoint was trained **only on made-up windows**, not Ben's
recordings. The corresponding report and machine-readable handoff are in
`~/learner-ops/aon-notes/hands-pc-20261107/`.

The wrapper also accepts `--steps`, `--batch-size`, `--lr`, `--gpu-wait` (0–900
seconds), `--no-fallback`, `--force-local`, `--timeout`, and `--bench-steps`.
Diagnostics go to stderr; stdout contains exactly one trainer-compatible JSON
object. `--bench-steps 0` is the default: tonight need not run a CPU benchmark.

## Safety and ownership

- Real recordings require the Mac's local **01:00–07:00 window and at least
  1,200 seconds idle**, with finite idle readings. Check before packing and
  upload, during upload and every event-monitor tick, before output installation,
  and during any requested CPU benchmark. `STOP-TRAINING` applies to all jobs.
- Only a manifest with literal `synthetic: true` bypasses time/idle checks.
  `--synthetic` cannot turn a real manifest into a synthetic one.
- A standalone, detached Windows supervisor is acknowledged **before any frame
  upload**. It checks a PC-clock permit refreshed by the Mac every ten seconds.
  Permit expiry (60 seconds), cancellation, failure, and successful return all
  remove the unique `C:/Users/benja/hands-train/hands-*` job folder. A Mac or SSH
  process disappearing does not kill this independent cleanup supervisor.
- The supervisor imports a byte-for-byte packed copy of the gym's `gpu_gate.py`
  and obtains **`C:/Users/benja/hands-gym/GPU-OWNER.json`**, not a separate
  hands-train lock. This is the same lease LANE-B-6 uses. CUDA is initialized
  only after admission. Never clear another owner's lease or exempt a foreign
  CUDA client. Only the supervisor's own child may be terminated on cancellation.
- A pending-reboot flag is a warning, not a request to reboot or an active
  reboot. Both model arms atomically checkpoint every ten steps. No reboot or
  paused job is initiated. A disconnected/rebooting host is unavailable.
- Every uploaded frame, model source, shim, shared lease module, and starting
  checkpoint is SHA256-checked on the PC before CUDA training. All three
  returned checkpoints **and result JSON** must match the worker's hashes.
  Only then may quarantine files be installed; PC deletion must be confirmed.
- An unavailable/busy host falls back to the native **Mac CPU** trainer, retaining
  its production gate and requested step count. The real-data gate is checked
  again after the remote wait: waking the Mac or leaving the night window does
  not start a CPU fallback job. Reasons append to
  `~/learner-ops/night-learn-remote/fallback.log` (mode 0600). CUDA failures never
  fall back. After frames are uploaded, an unconfirmed cleanup is a hard error,
  not a claimed successful local fallback.

A forced Windows reboot/power loss can stop even the detached supervisor. If
that happens after upload, the runner must report unconfirmed cleanup until the
PC is reachable and deletion can be verified; this implementation installs no
Windows startup service and does not claim disk erasure across power loss.

## Reproduce the synthetic proof

```sh
PY=/Users/ben-hannan/learner-ops/p2venv/bin/python
SRC=/Users/ben-hannan/learner-ops/desk-always-on/desk/src/night-learn-remote
NOTES=/Users/ben-hannan/learner-ops/aon-notes/hands-pc-20261107
"$PY" "$SRC/make_synthetic.py" "$NOTES/synthetic" --count 400 --seed 7
"$SRC/tonight-remote.sh" "$NOTES/synthetic/dataset.json" "$NOTES/quarantine" \
  --no-fallback --steps 800 --batch-size 8 --gpu-wait 900 --bench-steps 20
"$PY" /Users/ben-hannan/learner-ops/desk-always-on/desk/test/night-learn-remote.test.py -v
```

The held-out, later 20% never enters fitting. Click accuracy is Euclidean
distance within 40 source-frame pixels, matching the reported tolerance.
`train_core.py` supplies identical AdamW steps, initial weights, batch sampling,
labels and loss for CUDA and the Mac CPU; compare the first twenty steps on
each and exclude the first three warmups. Timing excludes PNG decoding,
checkpoint I/O and network transfer. It is **not** a whole-job speedup claim.
Sparse/scroll/drag-only real datasets remain trainer-compatible; absent classes
are reported unmeasured rather than rejected.

Set `HANDS_REMOTE_AUDIT` to an absolute JSONL path to retain transport commands,
stdin source, stdout/stderr and exit codes. No frame bytes are put into that
audit. `windows_resource.py` supplies the unused POSIX import in the unmodified
toy policy; it is not used for resource admission.
