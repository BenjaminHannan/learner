# y1t addendum 10: a Mac-side guard for the vast rental between passes (Answering-from-memory thread, written 2026-09-27 15:14 UTC, before any y1t training run; sealed in SEAL-y1t-add10.sha256.txt)

**Why:** the Thread manager (14:39 UTC) did not OK the ADDENDUM-9 kit yet. Between passes the rental keeps billing,
and nothing stops it at the $1.50 cap or at any time limit. The cap only acts when a later pass runs, and that pass
needs the Director to release it. This gap is what left rsn-358u's rental unguarded. The fix they asked for is a
detached Mac-side guard, started by p1, that enforces the cap and a time cap scaled to the card. It copies back, then
destroys, else stops, as handoff/kit/sleep358uv/vguard.sh does.

**The change (kit re-pinned; the held passes point at the new pin):**
1. **handoff/kit/y1tvast/guard.sh.** A pass starts it as soon as this task's instance answers ssh, unless it is
   already running (p2 and p3 restart it if it died). It is started as one backgrounded command:
   nohup, its own session (perl setsid) and caffeinate. It runs from its own copy of the kit in
   ~/premonition-watch/y1t-vast, so it outlives the pass and the queue job. Every 2 minutes it reads this task's vast
   state. It acts on the first of three things:
   - **money:** dollars so far plus 15 minutes of the instance reach $1.50;
   - **time:** the time cap has passed;
   - **done:** the rental shows chain.done (checked over ssh every 10 minutes) and no pass has copied it back.

   To act, it runs pass.sh in a new guard mode, which works like the last pass at its deadline. It asks the chain to
   stop its step, copies back and checks every file against the rental's sha256 manifest. Then it destroys the
   instance, or else stops it and prints FLAG-DIRECTOR. It writes RESULTS-vast.md with a BUDGET-STOP or TIME-STOP
   status, or COMPLETE when the chain was done. Its notes are signed y1t-vast-guard. Guard
   mode never rents, streams a tree, starts setup, runs checks or launches. The guard skips a round while a pass
   holds the lock, because that pass enforces the same caps itself. It ends when RESULTS-vast.md exists, when the
   instance is gone or stopped, or after 12 hours.
2. **Time cap, scaled to the card:** create + 20 minutes of setup + 2 x the offer's estimated chain minutes + 15
   minutes. On an RTX 5090 that is 135 minutes (estimate 50 minutes). An instance adopted after a lost create reply
   counts its estimate as 120 minutes. The passes stop the chain at the time cap too (TIME-STOP). The chain's own cap
   on the rental, set at launch, is now also at most the time cap less 5 minutes. So the chain stops itself by then
   even if no pass or guard is running.
3. **Where the results go.** A guard action writes its files in the watcher's worktree, and the adapter goes to
   ~/y1t-adapter. The watcher pushes them when the next pass job exits (p2 or p3 finds RESULTS-vast.md and stops
   with DONE). So after a NEXT-PASS-NEEDED note the next pass is still released, even if the guard has acted.
4. **Notes.** NEXT-PASS-NEEDED now names the guard's pid, the time the $1.50 cap is reached and the time cap.

Everything else in ADDENDUM-9 is unchanged: the data, the sealed scripts, the panel, the six steps, the DEV marks,
the card rule, the $1.50 cap and the estimate.

**Tests:** the fake vast and fake rental cases from ADDENDUM-9 pass with the guard running, including the normal
run, where the guard ends when RESULTS-vast.md is written. Three new cases also pass, each after p1 exits with
NEXT-PASS-NEEDED:
- **money cap:** the guard stops the chain, copies back, destroys, and writes BUDGET-STOP;
- **chain finished:** the guard copies back, destroys, and writes COMPLETE;
- **time cap:** the guard stops the chain, copies back, destroys, and writes TIME-STOP.
