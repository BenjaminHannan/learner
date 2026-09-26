# night-proc: the night as a separate process with versioned, atomically activated adapters. Acceptance marks
(Fix-sleep thread, 2026-09-26. Registered when this file is committed, before the acceptance run.)

## Why
Ben's two outside reviews (01:54 and 02:11 UTC, sections 10, 11 and 3) asked for four things:
- training in a separate process against a snapshot, with no write access to the live notebook or agent;
- candidates tied to the exact base;
- an atomic activation pointer;
- activation checked by behaviour after a restart, with milestones logged so "sleep ran" never stands in for
  "the model learned".

The split was agreed with Month-end (design/v3/30-modes/02d-month-end-followups-2026-09-26.md): this thread owns the
packaged night, and Month-end owns the joined interruption test.

This is an engineering acceptance test, not a learning claim. dl-2 is the learning claim.

## Code
scripts/claude_night_proc.py. The night rule inside is claude_night.night, which is dl-2's registered S rule.

## Acceptance run
`--accept`: tiny, on CPU, plain MiniCPM5-1B. The panel is cut to 12 items. Day groups are 3-4 puzzles; for plumbing,
each missed puzzle gets one checked answer from the exact solver.

| Mark | What must hold |
|---|---|
| A1 | A learning night exits 0, writes v0001 with record "accepted", and ACTIVE points to v0001. |
| A2 | In a fresh process, v0001 loads from ACTIVE and its behaviour fingerprint equals the record's. The fingerprint is the top-5 next-token log-probs on 8 fixed probe puzzles. |
| A3 | A night with no eligible examples leaves ACTIVE and the version list unchanged. |
| A4 | A night killed by exact PID mid-way leaves ACTIVE unchanged. The active version still loads with a matching fingerprint, and no version file is half-written (a .pt without its record). |
| A5 | An adapter whose record names another base revision is refused at load. |
| A6 | A stand-in live-notebook folder is byte-identical before and after all nights. |

- PASS = A1-A6.
- If the killed night in A4 finishes before the kill arrives, A4 fails as registered. It is then re-run once with an
  earlier kill, and that is reported as a deviation.

## Limits
- CPU and tiny sizes.
- The eval inside a real night (E2) uses the full 300-item panel against the PARENT version, with at most 10 lost.
  Its bar is not tested here, beyond the fact that it runs.
- No write protection is enforced by the OS. A6 checks the effect, not the permission.
