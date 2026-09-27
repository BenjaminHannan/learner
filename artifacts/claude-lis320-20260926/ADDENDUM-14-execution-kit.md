# lis-320 ADDENDUM-14: execution kit for Ben's completion order

Written 2026-09-27T22:34:28Z. No lis-320 training or panel reader run has started.

Ben's current request supersedes the old held jobs' smaller rental budgets,
old writer routes and depot source. The new kit is handoff/kit/lis320v/.
One rental is launched by one BASH-ONLY Mac queue job, after DATA.md and
SEAL-DATA.sha256.txt exist. The Mac runner is detached so the watcher's
75-minute job limit cannot terminate a training run or strand its rental.
Its final files are collected by this coordinator from the Mac, without a
second rental. This implements the requested single rental job; it does
not release any old held queue file.

Cost cap: $4 for the job. Offers are a single 24+ GB RTX 4090/5090,
reliability at least .98, at least 8 CPU cores and 60 GB disk, price at most
$0.85/hour. Stop work at $3.25 measured as quoted hourly rate times elapsed
rental time, reserving $0.75 for copy-back, shutdown and transfer charges.
One create attempt; a startup failure stops the job. Cost reports label
hourly-rate calculations as estimates unless a billing receipt is available.
Ben explicitly authorized this rental; no new approval is needed.

The old merged reader comes from the Mac, SHA-256
970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b.
The base revision and training arguments in PASSMARKS remain unchanged.
The kit pins torch 2.11.0, transformers 5.17.0, peft 0.21.0, as the existing
rd378gv kit does. It removes incompatible image torchvision/torchaudio.
A complete two-epoch run is required; time-limited partial training is a stop,
not a trained reader. Batch stays 16; OOM is a stop, not a changed recipe.
Gradient presence is checked on the first backward result. The watchdog
allows 120 seconds for load/first backward and stops if its result is absent.
This replaces the held job's first-minute inspection with an automated check;
nonzero missing-gradient counts still stop immediately.

Each panel arm gets an exclusive started marker before its single read.
No partial read is retried. T remains .995 and the compiler is unchanged.
All data and execution hashes must match before training. Panel rows stay
unseen by the coordinator. Two fresh blind judges use JUDGE_SAME.md;
a fresh subagent recounts score files only after scoring.

The kit never opens keys or auth files: vastai and ssh use their normal
configured authentication. No key is copied to the rental. Only this job's
recorded instance ID with the matching label can be stopped or destroyed.
Destroy requires a manifest-checked copy of every output, including the
adapter and merged model when training completes. Otherwise stop and retain
the rental disk. Any ongoing storage charges are reported if that happens.
The adapter and merged reader are put under ~/premonition-models/.
A new run-vast/RENTAL-RESULT.json is the rental ledger record; the existing
root ledger and notebook/ are untouched, following Ben's add-only rule.

Shown: MOCK-TEST.json records fake-CLI lifecycle and copy checks with zero
real rentals. Suggested: these guard the expensive and destructive steps.
Untested: real host setup, training, panel reads and verdicts.
