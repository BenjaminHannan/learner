# rd-378g addendum N2 (2026-09-27 14:38:24 UTC): vast kit launch-line fix, before any rental

- Found by the Director at 14:37 UTC; it is the same bug that left 358u's rental running with no guard.
- The bug: vstart.sh started drive.sh with `cd /root/r && setsid nohup ... & echo launched`. That line backgrounds the
  whole list, so a subshell keeps ssh's stdout open until drive.sh ends. vstart then never writes its state, and the
  guard never starts.
- The fix: the brace form `cd /root/r && { setsid nohup ... & } ; echo launched`.
  - Checked here: the old form returned after the background command ended (4 s of 4); the brace form returned at once.
- vstart.sh now requires this file.
- drive.sh now checks SEAL-ADD-N2, which replaces SEAL-ADD-N for the kit. SEAL-ADD-N stays as written. Its vstart.sh and
  drive.sh lines no longer match.
- Nothing else changes.
