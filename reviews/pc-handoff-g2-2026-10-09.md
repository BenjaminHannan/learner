# Group 2 PC jobs: ready for Ben's yes (written 10-09, about 5 PM ET)

Nothing here is installed. The PC has not been touched (I only read files there). Each job needs your own "yes".

## In plain words (like I'm 5)
- We made a new, "all learned" version of our model (group 2). Before the big PC computer practises it, we want a fair race.
- **Job 1, g2c3s:** a plain model gets the same practice questions, but every question shows its work step by step. It is the fair partner for group 2.
- **Job 2, group 2 at 3M:** our new model, same questions, same size class.
- We race them against group 1 (already running on the PC) and against each other. The score rules were written down before any run and are not changed.
- While getting ready I found a trap that would have spoiled job 2: both jobs share one folder of practice data, and that folder remembered the *old* ruler (68 letters wide). Group 2 needs a 95-letter ruler. It would have used the wrong one without any warning. Fixed and tested; each new job now keeps its own ruler beside the shared data.

## What is already done (CPU/Mac, free)
- Branch `claude/learner-new-g2`, pushed. Code commit: **9dbcbb579c14b336e51de04cbc2ee77d343aed10**. The staging script copies the pushed `HEAD`, which is later (this doc and the script came after it), but `git diff 9dbcbb579c HEAD -- custom_io` is empty, so the staged `custom_io` is the same code; `STAGED-SHA.txt` on the PC will name HEAD, not 9dbcbb579c.
- PTS arm (all-steps plain control): commit aad9cac7e7. Tests: `test_pts` passes (off-switch = bit-identical to 20b72089d9, answer read after the LAST `#`, no truncation, count, caps checks, shared-pool check).
- Group 2: `test_b3g2`, `test_b3g2_run`, `test_g2_input`, `test_progtext`, `test_st1`, `test_b3`, `test_g8a`, `test_plain_tf_place` pass on the Mac.
- Not runnable on the Mac (need the sk200k data dir): `test_plain_tf_steps`, `test_plain_tf_maxans`. They are unrun, not passed. The PTS and group 2 default-off paths are covered by `test_pts`'s comparison against the older commit.
- PR #56 description updated with a Group 2 section (branch `claude/learner-new-g2`; group 2 code is not in that PR's head).

## Still open before the PC (a "yes" waives these; the sealed text says every pre-PC item must pass)
- `answer_over_max` counted in bytes on the dev and eval files (PLAN addendum 2:10 PM ET item 4): not measured here, because the dev data is not on the Mac. It is only guarded at job start (the job stops on a touched row); the first sign would be a refusal on the PC at minute zero.
- `test_plain_tf_steps` and `test_plain_tf_maxans`: unrun (need the sk200k data dir).
- Item (ii), `caps_b3` re-measured in bytes on the long-chunk pool: I did not redo it; `caps_b3g2.json` states it was computed on cloud CPU (LE 95 from the longest call or note, WCAP 96). Item (iv), `progtext` per-family "rows with no trace must be 0", is covered by its unit tests but not measured on the real pool here.
- `test_writer` (645 s) was not re-run today (it passed per the earlier handoff table).

## Four rulings Ben owes for B3G2-7 (does not block the 3M run; it blocks scorecard row 4)
The B3G2-7 count is 4, all training-only (inventory part 8b). The inventory has no J-id for them (J1 to J7 cover answer-path items), so I propose new ids J8 to J11 to record each ruling. Each is allowed-as-teaching (disclosed) or blocked (row 4 stays red until ST1 replaces it):
| New id | Item | What it is | My suggestion |
|---|---|---|---|
| J8 | B1 | `progtext.py` regexes (lines 82-104) read written steps into calls | allowed as teaching for the 3M run; ST1 replaces it for new kinds |
| J9 | B3 | operand first-match: an operand is matched to the first slot with its value | allowed as teaching; ST1 replaces it |
| J10 | B4 | special cases: compare, range, sum, state update, verify_claim | allowed as teaching; ST1 replaces it |
| J11 | B6 | the NOOP row weight (`w_noop` 0.1); commutative freedom (COMM) is unused | allowed, disclosed teaching weight |
These are my suggestions, not decisions.

## Two things to know before saying yes
1. **g2c3s is not exactly "same caps_b3" as sealed.** The sealed text (PLAN 2:35 PM ET addendum) says g2c3s uses `caps_b3`. With worked steps on every row the longest target is 115 characters, not 109, so under `caps_b3` a row would be cut, and the rule is no cuts. The arm therefore pins `caps_b3s.json` (`plain_target` 115; measured on own72 only). Effects: trained count 4,023,976 instead of 4,022,440 (+1,536 numbers in the position table, 0.04%, inside the ±2% band), and its starting random numbers probably differ from g2c3's (suggested, untested). This does not change any pass mark, but it is a change to the control's definition: a dated one-paragraph addendum in PLAN.md is the right record. Draft: "10-09 5 PM ET: g2c3s runs under `caps_b3s.json` (plain_target 115) because its all-steps targets are up to 115 characters and may not be cut; trained count 4,023,976 (+0.04% vs g2c3); marks unchanged." I have only a snapshot of PLAN.md, so I did not edit it.
2. **g2c3s can stop at the very start.** Its caps were measured on own72 only. If any train or dev row (including the dev files) has an all-steps target over 115, the job refuses to start and prints which rows; nothing is cut and no GPU time is lost. Group 2 runs the same caps report against its own pinned caps (`caps_b3g2.json`). If either refuses, I report it and we decide; I would not loosen a cap on my own.

## Order and slot (PLAN: "a PC gap after g2c3 and after B3 group 1 3M seed 400")
The PC waiter (pid 2760, `q8aPost2_wait.ps1`) is running the chain: GX s400, fc100, g2c3, B3 group 1 s400, then conditional runs, g2c10, c30. G1 3M s401 (pid 24608) was still running at 3:51 PM ET. The waiter starts jobs by itself whenever no queue runner is present, so a manual launch could race it. Suggested slot: after B3 group 1 s400 and its readout, before g2c10/c30. That needs either a `WORK\STOP` hold or a change to the waiter; both touch the live chain, so I did not do either. Tell me which you prefer:
- **A (suggested):** stage the code now (inert), and I write the small waiter change for your review; nothing runs until you approve it.
- **B:** stage now, run both after the whole chain ends (c30 included), by hand.
- **C:** wait.

Order inside the slot: g2c3s first (about 2.4 h at g2c3's speed; longer targets may add some), then group 2 (unmeasured on the PC; Mac cost 0.212 s/step at 2,000 letters; G1 3M s401 is the best guide for the real speed).

## Stage the code (Mac side, inert: mkdir + tar + scp, no job, nothing started)
```bash
sh scripts/g2_pc_stage.sh
```
It refuses to run if the tree is dirty, `HEAD` is not pushed, or `src-b3g2` already exists on the PC. It copies `custom_io` of the pushed commit to `C:\Users\benja\custom-io\src-b3g2`, puts `caps_b3s.json` and `caps_b3g2.json` into `work\b3-inputs\`, and prints SHA-256 of both sides to compare. Reference hashes at commit 9dbcbb579c: caps_b3s.json `8cbea48d300a8a0d38d9a89d950274df08743326ca3f1e9eafc2763add9cbf31`, caps_b3g2.json `ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4`, job.py `28e09e53...54242`, caps.py `32862ae2...ea03e`. (Not run yet: it has only been syntax-checked.)

## The two queue files (in the repo, parse-checked with `local_runner.parse_queue`)
- `custom_io/queue_local/8aG2C3S-pc.txt` (g2c3s): `g8a: 8aG2C3S-3M-s400 --rung 3M --seed 400 --arms PTS --b2-extra '{"eg_embed": true}' --cloze-long {WORK}/b3-inputs/cloze_long.py --caps-file {WORK}/b3-inputs/caps_b3s.json --accum PTS=16`
- `custom_io/queue_local/8aB3G2s400-pc.txt` (group 2): `g8a: 8aB3G2s400-3M-s400 --rung 3M --seed 400 --arms B3G2 --b2-extra '{"eg_embed": true}' --cloze-long {WORK}/b3-inputs/cloze_long.py --caps-file {WORK}/b3-inputs/caps_b3g2.json --accum B3G2=32`
- Both reuse the data step line of g2c3 and the pool `p10-rung30-s400-a64-L`. `--accum` values are cautious guesses like group 1's (PTS=16 as g2c3; B3G2=32 as B3).

Launch line (what the waiter's `Launch()` does), after approval, from `C:\Users\benja\custom-io\src-b3g2`:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\8aG2C3S-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt
```
(with `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1`, and the Python at `C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe`).

## Job cards (pc-jobs, modelled on g1e.md; install only with the yes)
```
job: g2c3s (PTS: plain 3M control with worked steps on every row; B3G2-1's partner)
queue: 8aG2C3S
gpu: yes
log: C:\Users\benja\custom-io\work\q8aG2C3S.log
stall_minutes: 900
paths: SRC = C:\Users\benja\custom-io\src-b3g2   WORK = C:\Users\benja\custom-io\work
done_when: log prints "queue 8aG2C3S-pc done" and WORK\results\8aG2C3S-pc\8aG2C3S-3M-s400\RESULT.json says "status": "ok" (else report)
on_refuse: the job stops at start if a row is over plain_target 115 (report only; do not edit caps)
on_spill, on_crash: report only. max_restarts: 0
never: change seeds, data, marks, steps, learning rate, caps or any setting not named above; never touch finished result folders or checkpoints

job: b3g2-3m-s400 (B3 group 2 at 3M, seed 400; marks B3G2-1 to B3G2-7 sealed in PLAN.md)
queue: 8aB3G2s400
gpu: yes
log: C:\Users\benja\custom-io\work\q8aB3G2s400.log
(same stall/on_/never lines as above; done_when RESULT.json under results\8aB3G2s400-pc\8aB3G2s400-3M-s400\)
read after: score against the sealed marks (group 1 s400 readout, g2c3s); steps_unparsed must be 0 (B3G2-6)
```

## What each result will be read against (sealed, unchanged)
B3G2-1: pooled-5 within 3.0 of group 1 on seed 400 and at least +1.0 over g2c3s (proved wrong: more than 6.0 below group 1, or below g2c3s). B3G2-2..6 as in PLAN. B3G2-7 is not met on the built code (see the PR text): parts 1 to 4 count 0, part 8b counts 4 training-side items, disclosed.
