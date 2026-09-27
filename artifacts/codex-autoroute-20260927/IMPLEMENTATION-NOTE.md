# Implementation repairs before training

The first bounded preflight completed its schedule, MPS invariance and gradient
checks with zero optimizer updates, then failed while collecting source hashes:
Torch exposes a synthetic `_classes.py` module path that is not a real file.
The manifest collector now hashes only existing local Python source files.
The failed log is preserved as `preflight.log`; the rerun uses `preflight-2.log`.
This changes bookkeeping only. No scientific trajectory had started, and no
marks, architecture, data distribution or update rule changed.
