# Probe-2: look at the world first, then write the tests

Fixed 2026-10-26 ~10:05Z, before any Probe-2 probe is written. Follows Probe-1 (PROVED WRONG: K2 tests written from
the request alone pick 29.7%, Haiku's 27.1%, vs self-judge 34.4%). Probe-1's diagnosis (shown): 25 of the 48 hard
tasks are traps (confirm_irreversible, clarify) where the right end state is "did not act, asked first", and the trap
is only visible in the user's data (two people with one name, a confidential note), which the test writer never saw.

## One change
Everything is as in PREREG.md (same 192 pools, replay, 4 samples at T0.7, scoring, pickers, tie-breaks), except the
test writer's prompt also contains the task's start state as JSON (files, mail, calendar, notes, reminders; the
same data the assistant can reach with its read tools). Still never shown: any try, the reference plan, the rubric,
the task's checks. Switch: `PROBE_WITH_STATE=1` / `--with-state` in write_probes.py (test planted in tests/).
Haiku (Batches, default sampling since the model rejects temperature) is again a reference arm only.

## Pass marks (fixed now, same as Probe-1)
- P1: PROBE-S (K2) pick rate >= SELF + 5 points (>= 39.4%).
- P2: AUROC of the K2 probe score over all 2,304 tries >= 0.75.
PASS = P1 and P2. PROVED WRONG: PROBE-S <= 35.4%. Otherwise INCONCLUSIVE.

## Diagnostics (do not decide)
Reference agreement of valid probes (Probe-1: K2 38.5%, Haiku 64.7%), share of traps where some probe is a "did not
act" check (no_email_sent / no_event_created / file_absent / reply_contains asking), all-tie rate.

## What the result would mean
- PASS: seeing the world is what the small judge lacked; probe-then-pick goes on top of 12 tries end to end next.
- PROVED WRONG for K2 but Haiku passes P1's mark: the idea works and the small writer is the limit (distil Haiku's
  tests later). Both fail: test-first picking is dropped for this test bed.

## Cost
192 short K2 generations (one T4, ~6 min as in Probe-1); Haiku batch ~$0.05.
