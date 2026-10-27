# y1t addendum 9: run y1t on one vast rental while BensPC is unreachable (Answering-from-memory thread, written 2026-09-27 14:36 UTC, before any y1t training run; sealed in SEAL-y1t-add9.sha256.txt)

**Why:** BensPC stopped answering ssh at 12:30 UTC 09-27. Ben, 12:45 UTC: "Just use vast for now". The Thread manager
(12:48 UTC) asked for y1t on vast with a pinned kit, the same sealed runner and panel, disk and stall rules fit for Linux,
a cap of at most $4 with an estimate, and an addendum naming the machine; the job stays held. Ben's yes at 12:49:44 UTC
lets the Director spend up to $5 of the $30 pool on jobs that were waiting for BensPC, rsn-358u first, then rv390, then
y1t (ledger, 12:50 UTC). Ben's standing order of 14:05 UTC (as other threads' held jobs quote it): jobs waiting on BensPC
go to vast, at most $4 per job, on the card with the best TFLOPS per $/h.

**The machine:** one vast.ai instance labelled claude-memory-y1t, on the 1-GPU offer with the best TFLOPS per $/h (vast's
total_flops over dph_total) among offers with at least 16 GB of GPU RAM (BensPC's card, where y1t was planned),
compute capability 7.5 or higher and CUDA 12.8 drivers (torch 2.11 cu128), reliability at least 0.98, at least 8 cores,
at least 60 GB disk, download at least 200 Mbps, a direct port, at most $1.00 an hour, and at most $0.02 per GB for
download and for upload. The offer's time must also fit: estimated chain minutes = 50 x the larger of 1 and
104.8 / its TFLOPS (50 minutes on an RTX 5090, an upper guess; the scaling is inferred, not measured) must be at most
120, and (chain + 20 minutes of setup) x its $/h at most $1.20. Image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime;
inside it torch 2.11.0 (cu128 wheels) and transformers 5.17.0, the versions in BensPC's lis300 venv. torchvision and
torchaudio are removed (the rent kit's TORCH UPGRADE rule) and gcc is installed only if missing (y1g's rental needed it).
The only model is plain MiniCPM5-1B, downloaded at commit 87179e5c1f455ef22e6223592d2d61351b525bfc (the rent kit's
section C downloads the newest and records the commit; asking for the commit means a newer upload can never be picked
up). RESULTS-vast.md and the pass notes name the card, its TFLOPS, its $/h and the torch, CUDA and driver versions.

**What stays the same:** the data (glm2/items, GATE-PASS, the same two sha256), the sealed scripts
(SEAL-y1t-rental 16 of 16, SEAL-y1tH1-runner 1 of 1, the spare401 panel line 1 of 1), the four selftests, and the six
steps with the same commands in the same order as the BensPC chain (drafts, train, eval, eval_plain, h1_A, h1_B). A
failed step ends the chain, so, as ADDENDUM-8 disclosed, h1_B does not run when h1_A fails. The DEV marks, the H1 step
and its paths are unchanged. RESULTS-vast.md carries no verdict; the thread scores the marks in VERIFY-y1t.md.

**The runner:** handoff/kit/y1tvast (pass.sh on the Mac; remote/bov.sh and remote/chain.sh on the rental), pinned,
run by the BASH-ONLY jobs rent-y1t-vast-p1 (the only one that rents), p2 and p3 (the last). A separate reviewer read
the first version and found 10 problems (among them: the watcher's alarm did not reach the pass, the last pass could
exit with the instance running, a lost create reply could leave an instance nobody tracked, a dead chain looked like a
slow one); all 10 are fixed below. It was then tested against a fake vast CLI and a fake rental in 21 cases: the normal
run, a stuck host and a failed create, a create whose reply is lost (the instance is found and used), a lost reply
whose instance shows up late (destroyed at the end of the run, or by the next pass), the job moved back to held or
edited after launch, an instance with this label that the task did not create, pass 2 with no instance, the hand-over
from pass 1 to pass 2, a hung step, the last pass's deadline, the money cap, a setup failure, a selftest that prints
FAIL with exit code 0, ssh lost, a copy that fails its check, a chain that died (rental restarted), vast not answering at
the last pass, the last pass locked out, the watcher's alarm during the rent (the next pass destroys the instance that
never came up), and a BensPC launch already recorded. The card choice was changed to Ben's 14:05 order after that
run and re-tested in the normal run and the bad-host case.

**Changes from the BensPC runner (ADDENDUM-6 to 8), disclosed now:**
1. **Stall and time rules on Linux.** chain.sh watches its own step every 30 seconds on the rental, so the rule holds
   between passes too. It stops the step when the step's log has not changed for 20 minutes, the step passes its cap
   (drafts 120, train 60, eval 30, eval_plain 30, h1_A 45, h1_B 45 minutes), the chain passes its own cap, or a pass
   asks it to stop. The stop is TERM, then KILL after 60 seconds, to the exact PID chain.sh started for that step and
   nothing else. The step is recorded as rc=stopped and the chain ends; nothing is started again. This replaces
   ADDENDUM-8's peeks and owner-stop, which were for BensPC. The rent kit's 10-minute rule is widened to 20 minutes
   because the train step prints nothing while it checks 291 DEV rows before training and while it merges and saves
   (a guess that this can pass 10 minutes on a slow host).
2. **Money.** Cap $1.50 for the whole task, every create included, under Ben's $4 per job. Estimate $0.30 to $0.70 on
   an RTX 5090 at about $0.45 to $0.55 an hour: about 40 to 70 minutes. This is a guess from y1g's rental, where 71
   asks took 283 ms each on average with 7 generations per ask; y1t's drafts are 1,762 items with 5 generations each
   (about 7 to 10 minutes), training about 190 steps (5 to 10 minutes), the two DEV checks and two H1 runs about 2
   minutes each, and startup and setup 10 to 20 minutes. A card picked for more TFLOPS per $/h should cost about the
   same for the same work (inferred). Each pass counts dollars as the instance's $/h times hours, from each create
   until vast shows it gone or stopped, plus 8 GB (a guess at the torch and model downloads) times the offer's download
   $/GB for each instance that answered ssh. When that plus 15 minutes of the instance would pass the cap, the pass asks
   the chain to stop, copies back, and destroys (BUDGET-STOP). The chain's own cap is set at launch to the minutes the
   money left pays for, less 15, at most 180.
3. **Passes.** p1 rents, sets up, checks, launches and watches until 55 minutes into the pass. If the chain is done by
   then, p1 copies back and destroys. If not, it leaves the instance running and writes a NEXT-PASS-NEEDED note, then
   p2 continues (55 minutes), then p3. p3 is the last pass: at 45 minutes it asks the chain to stop, copies back what
   exists and destroys (LAST-PASS-STOP), keeping 30 minutes before the watcher's 75-minute alarm for the stop, the copy
   and the destroy. Between passes nothing can destroy the rental (a vast key is never sent to it) and the instance
   bills every hour, so p2 and p3 go into the queue as soon as the previous pass has written NEXT-PASS-NEEDED. They rent
   nothing. The Director moves them, or this thread does if the Director agrees.
4. **Destroy only after a checked copy** (the Thread manager's rule for vast kits, 13:27 UTC). The rental lists every
   result file with its sha256, and the Mac copies them and compares. If the check fails twice, a pass that is not the
   last leaves the instance running (NEXT-PASS-NEEDED). The last pass, or a failure stop, stops the instance instead: GPU
   billing ends and its disk keeps the files. The pass then prints FLAG-DIRECTOR. An instance that never answered ssh
   as this task's instance has nothing on it and is destroyed, by any pass that finds it.
5. **What is kept.** The adapter goes to ~/y1t-adapter on the Mac and is never pushed. tr/merged is not copied and goes
   with the instance; it can be rebuilt from the adapter and the base model. Files over 3,900 KiB are pushed as gzip
   copies, split if needed, as in ADDENDUM-6.
6. **Disk.** Setup needs 20 GB free on the rental's 60 GB disk; the chain starts only with 8 GB free. On the Mac the run
   writes a few MB of results plus the adapter (a guess: tens of MB).
7. **Selftests.** A selftest counts only with exit code 0 and its own pass line. claude_bm398r_train.py's selftest exits
   0 even when it prints FAIL. The BensPC kit counted exit codes only.
8. **One route only.** The vast passes stop with DUPLICATE if a BensPC chain has launched (RUN-NOTE-bo.md) or results
   from another route exist, and p1 rents only while no 180-y1t-benspc-bo-p* job is in handoff/queue/ on main. They use
   the BensPC kit's lock, so the two never run a pass at once. The BensPC kit's own check stops once the vast run's files
   are on builder-outbox. The Director keeps 180-y1t-benspc-bo-p1..p4 held while the vast job is out.
   handoff/held/rent-0y1t.md (an LLM-builder job) is superseded.
9. **Records.** RESULTS-vast.md, RUN-NOTE-vast.md, vast-state.txt (instance ids, $/h and times; no keys), the rental's
   manifest and its last state. The Director files the spending ledger line from the pass's LEDGER-SUGGESTION line.
   The thread adds the result line after VERIFY-y1t.md.
10. **Time limits.** Every vastai call is ended after 90 seconds and every ssh call after 40 seconds to 10 minutes (the
    tree upload and the copy back get the longest). The job block execs pass.sh, so the watcher's 75-minute alarm reaches
    the pass itself; the pass then writes the same notes as any other early exit.
11. **Nothing left running unsaid.** Any exit that leaves an instance of this task running says so: NEXT-PASS-NEEDED from
    p1 or p2 (with the $/h, the dollars so far and the time the cap would be reached), ACTION NEEDED (FLAG-DIRECTOR) with
    the instance id from p3. The last pass asks vast five times over about 5 minutes before giving up, and waits up to 20
    minutes for another pass's lock. A create whose reply is lost is followed by 2 minutes of looking for a labelled
    instance that started after this task's first create call; one found is recorded and used, and one that shows up
    later is destroyed (it never answered ssh). At the end of a run every such instance still listed is destroyed.
12. **A dead chain or setup.** The rental reports how many setup and chain processes are running (read from /proc, since
    the image may have no ps). If the chain (or setup) is running on the rental's record but no process is left on two
    looks at least 60 seconds apart, the pass records DIED, copies back what exists and destroys.

**VERIFY-y1t.md will also give:** the card, its TFLOPS and $/h, the versions, the minutes per step against the estimate
above, the dollars, and whether any step was stopped.
