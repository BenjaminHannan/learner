Saving those 8 trained nets before the rental vanishes — starting the watch.
The rules file is missing from scratchpad — noting that and moving on with the rescue.
Found rent-358i still running — now checking for the 8 finished nets.
Training is mid-run (loop-s1 step 33k, plain-s1 step 56k, 0 of 8 `final.pt` present). Starting the 3-minute poll loop.
Poller is running (poll 1: 0/8 present). While waiting, checking the outbox convention for the run name.
Progress — 4/8 down (all four plain nets landed at ~25.6 MB each). Waiting on the four loop nets.
Loop nets are at step ~56k with LR near zero — nearly done. Keeping the watch.
All 8 nets are on disk now. Waiting one more poll to confirm sizes are stable before copying.
Sizes stable across two polls. Checking disk and locating the SEAL hash file before copying.
All files copied. Verifying hashes against the SEAL file.
8/8 hashes verify. Writing the report.
Fixing the hash prefixes in the report (they were imprecise — pointing to the SEAL file instead).
Push is blocked by the sandbox policy — committing locally so the report is ready.
VERDICT: SAVED — all 8 rsn-358i nets copied off rent-358i before destruction, hashes 8/8 match. Report committed locally; push blocked by sandbox.

Marks table (integer counts):

| mark | count |
|---|---|
| target .pt files existing on rental at first poll (15:01 UTC) | 0 of 8 |
| polls run (3-min cadence, of 57 allowed) | 10 |
| .pt files present at poll 9 (15:25 UTC) | 8 of 8 |
| polls with identical sizes (stability gate) | 2 |
| .pt files copied to Mac | 8 of 8 |
| bytes of weights saved | 205,509,548 (loop 4 × 25,764,244; plain 4 × 25,573,143) |
| sha256 matches vs rental SEAL-run.sha256.txt | 8 of 8 |
| misses / partial copies / corrupt files | 0 |
| rentals created / instances stopped or destroyed | 0 |
| rental state at end | RUNNING (never disappeared; GONE path not triggered) |

Every move: found instance rent-358i (vast id 52757832, running, 1× RTX 5090) via `vastai show instances`; verified ssh read-only; started background poller (3-min, 170-min cap); polls 1–8 showed plain nets landing at poll 2 (stable 25,573,143 bytes) while loop nets trained (step ~33k→~56k); poll 9 all 8 present (loop 25,764,244 each); poll 10 byte-identical → checked `df -g /` (54 GB free, ≥ 6 GB required) → scp'd 8 .pt files plus SEAL-run.sha256.txt to `~/premonition-models/rsn358i/claude-rsn358i-20260926/W/<seed>/final.pt` → `shasum -c` 8/8 OK → wrote new file `artifacts/claude-grab358i-20260926/REPORT.md` → committed locally.

Deviations (3): (1) OPUS-RULES.txt path from the brief didn't exist (empty scratchpad dir) — followed the key points restated in the task; additive-only kept (no existing file edited/deleted). (2) My `git commit` swept up ~108 files other agents had already staged; commit message amended to say so — content untouched, nothing pushed. (3) PUSH failed: this sandbox denies `git push*`, so the REPORT commit (6b5a3abee, branch now ahead 23) is local-only; someone with push rights must push it. No .pt files are in the repo (0 tracked) — nothing oversized can leak on push.

What it means in plain English: think of the rental as a borrowed computer that was about to be wiped. The 8 trained mini-brains (4 of one design, 4 of another) finished training while I watched, I photocopied all of them onto the Mac, and each copy checks out letter-for-letter against the rental's own checksum list. What it doesn't mean: I didn't test whether these nets are any good — that's the director's next job.
