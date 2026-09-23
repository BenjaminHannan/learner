# 108 — Daemon exactly-once on boot (one-change follow-up to exp 93)

Status: registered follow-up to the exp-93 soak FAIL. The one change lives in
`scripts/fable_daemon108_run.py` (new file; wraps sealed `fable_daemon74_run.py`
and, for the unregistered scale step, sealed `fable_loop102_agent.py`).
Driver `scripts/fable_soak108_run.py`, ghost demo
`scripts/fable_soak108_ghostdemo.py`, artefacts
`artifacts/fable-soak108-20260921/`. Nothing sealed was edited (dep shas match
exp 93's seal exactly).

## 1. Problem (exp 93 diagnosis, not re-argued here)

Kill -9 landing between `AgentLoop.submit()`'s state save and the end-of-step
save leaves the in-flight text in `state.json`'s loop inbox. The rebooted
daemon re-processes it as a ghost tick inside the next `turn()`, so the reply
stream is not exactly-once (exp 93: `I already have that.` written twice, fact
stored once). Worse than doubling, the ghost re-executes arbitrary text.

## 2. Fix design (the one change)

Exactly-once turn handling on boot. Each mailbox message already has a stable
id: its filename (`t000123.txt`). Two rules, enforced in `boot_reconcile()`
before any turn is served:

1. **Finish once if the reply is not durable.** A `<id>.txt` sitting in
   `inbox/` with no `outbox/<id>.txt` is processed normally, exactly once.
   Re-execution is fact-safe: teaches dedupe to DUPLICATE_OK, asks are
   read-only, corrections supersede to the same value — and only one durable
   reply ever exists per id, so the driver-visible reply set is exact.
2. **Drop if the reply is durable, never both.** `outbox/` writes are atomic
   (tmp + `os.replace`), so an existing `outbox/<id>.txt` is a complete reply:
   the still-queued `inbox/<id>.txt` is moved to `done/` WITHOUT re-executing
   the turn (this finishes the move the kill interrupted). The loop.inbox copy
   in `state.json` is a crash artefact, not a queue: it is cleared, saved, and
   logged. The daemon mailbox's own `inbox/` still holds every piece of undone
   work, so nothing submitted is lost.

A `receipts.jsonl` line (id → reply sha256) is appended after each durable
reply write and after each boot finish-move, giving a per-id audit trail:
after a correct run every id appears exactly once.

Why drop (not drain) loop.inbox: the mailbox file for the same text is still
in `inbox/` (the daemon moves it only after the reply is durable), so the work
is covered exactly once via rule 1. Draining the loop copy AND serving the
mailbox file would execute twice — that was the bug.

## 3. What it does not cover (stated limits)

- Kill mid-`_save` / mid-notebook-append relies on the existing atomic-replace
  + torn-tail repair (unchanged, sealed). A torn final `receipts.jsonl` line
  is skipped on read (receipts are audit-only, never correctness input).
- A re-executed first-teach may reply `I already have that.` where the lost
  pre-kill attempt would have said `Saved:` — exactly one durable reply
  exists, and the driver accepts both (DUPLICATE_OK rule, exp-93 verbatim).
- One seed per run (93 registered; 931 aimed-kill); template English only;
  StubSleeper path (daemon108 defaults, as in exp 93).

## 4. Verification (marks G1, K1–K5, G2; see PASSMARKS.md + RESULTS.md)

- G1 replays GHOST93 verbatim through the fixed boot path: Carol reply is
  Carol-only; mailbox half gives single-sentence Bob/Carol replies, one
  receipt per id, one Bob fact row.
- K1–K5 re-run exp 93's exact plan/schedule (kinds and all 8 restart points
  verified identical) pointed at daemon108.
- G2 aims 10 kill-9s deliberately mid-turn on seed 931 (victim solo on a
  drained pipeline; `state.json` polled until loop.inbox is nonempty; kill at
  once; per-kill evidence in `aims.jsonl`) and counts duplicate/lost/wrong
  replies, each reported, never averaged.
- Unregistered scale step (reported apart): same seed-93 soak against
  loop102 wrapped the same way, or a stop with evidence if the wrapper does
  not apply cleanly.

## 5. Consequences

If K1–K5+G2 pass, the ghost-tick class is closed for mailbox daemons built on
this loop: crash-artefact state is never re-executed, and every kill window
(finish vs drop) resolves to exactly one durable reply per stable id. The
remaining soak risks (throughput halving ~44→20/s, RSS growth) are unchanged
by this fix and stay visible in the K4/checkpoint curve.
