# 331 end-to-end banks: seals only (items are escrowed, TEST-ONLY)

Spec: design/v3/30-modes/331-e2e-bank-spec.md. Banks A and B are TEST-ONLY. Their items live only in the project's
shared folder (escrow-331/A, escrow-331/B) and are never put on builder-outbox, read by builders or quoted. They go
to the runner only for the registered runs 336 (bank A) and 336b (bank B).

- Bank A: 40 lives, 663 user turns, 318 facts. Blind writer, then a blind key audit: 5 flags (1 never-told ask about
  a hypothetical, 1 fact left open after a correction, 1 ask on an unrecorded nickname, 2 gender-assumed relations).
  Applied blind as v2: 3 asks no longer scored (set to "other"), 1 fact closed, 3 relations made neutral.
  Registered files: turns_v2.jsonl, truth_v2.jsonl (the runner is given them as turns.jsonl/truth.jsonl).
  v2: 242 scored asks (one_hop 63, two_hop 37, reversal 29, edit 35, yesno 29, never_told 36, partial 13).
  Seal: SEAL-A.sha256.txt (7 files, including v1 and the audit).
- Bank B: audit running; seal to follow.
- Bank DEV: artifacts/claude-e2e331-dev-20260924 (readable).
