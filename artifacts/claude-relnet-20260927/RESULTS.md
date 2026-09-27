# relnet practice gate: RESULTS (registered GPU run)

Written 2026-09-27 22:19 UTC (`date -u`) by the GPU session, from the handoff
artifacts/claude-relnet-20260927/HANDOFF-gpu-practice.md. Marks: GATE-PASSMARKS.md (not edited).

## Verdict: PASS (shown)
With lr 1e-3, on the gate panel (seed 6279901, never used for any choice), the relation net got at least 197 of 200 on
every kind in both seeds. It is never more than 2 of 200 below the same-seed loop. G1 and G2 hold in both seeds.
No lr sweep was needed or run.

| arm | seed | weights | train min | gate sums4 | gate grids5 | dev sums4 | dev grids5 |
|---|---|---:|---:|---:|---:|---:|---:|
| relnet | 0 | 1,644,198 | 9.1 | 200 of 200 | 197 of 200 | 200 of 200 | 198 of 200 |
| relnet | 1 | 1,644,198 | 9.2 | 200 of 200 | 200 of 200 | 200 of 200 | 199 of 200 |
| loop | 0 | 1,645,726 | 7.7 | 200 of 200 | 199 of 200 | 200 of 200 | 200 of 200 |
| loop | 1 | 1,645,726 | 7.7 | 199 of 200 | 198 of 200 | 200 of 200 | 200 of 200 |

| seed | G1: relnet >= 190 of 200 on both kinds | G2: relnet - loop (limit -6 of 200) | result |
|---|---|---|---|
| 0 | 200 and 197: pass | sums4 0, grids5 -2: pass | PASS |
| 1 | 200 and 200: pass | sums4 +1, grids5 +2: pass | PASS |

Full scorer output: practice-gpu/gate.md. It is `scripts/claude_relnet_gate.py --dir
artifacts/claude-relnet-20260927/practice-gpu`, rerun here on the decoded JSONs, and it is identical to the table the
GPU machine printed.

## Report-only rows (shown)
| arm | seed | mean rounds, gate (sums4/grids5) | cap hits (s/g) | best fixed depth on dev -> its gate count (s/g) | stop failure (> 4 of 200) |
|---|---|---|---|---|---|
| relnet | 0 | 7.05 / 15.32 | 0 / 1 | 4 -> 200 / 12 -> 197 | no |
| relnet | 1 | 6.61 / 13.78 | 0 / 3 | 4 -> 200 / 12 -> 199 | no |
| loop | 0 | 7.38 / 9.18 | 3 / 0 | 4 -> 200 / 24 -> 199 | no |
| loop | 1 | 6.87 / 10.85 | 0 / 0 | 8 -> 200 / 12 -> 198 | no |

- Shown: the relation net thinks longer on grids than the loop (13.8-15.3 rounds vs 9.2-10.9).
- Shown: when forced to run long, the relation net decays on sums. At a fixed 48 rounds it gets 177 and 156 of 200 on
  gate sums4, against 200 at 4-16 rounds. The loop stays at 200. The learned stop ends sums near 7 rounds, so this
  does not touch the gate. Suggested: it matters for any test that runs many rounds on long inputs.
- Shown: learning curves on dev (sums4/grids5 at steps 1,500 / 3,000 / 4,500):
  - relnet seed 0: 1/39, 184/196, 200/197;
  - relnet seed 1: 19/167, 187/197, 200/198;
  - loop seed 0: 141/2, 198/184, 200/196;
  - loop seed 1: 155/17, 195/144, 200/197.

  The relation net learned grids sooner and sums later than the loop.
- Training minutes are above. The 4 runs shared one RTX 3090 at once. Eval rounds to 0.0 min per run in the JSONs
  (under 3 s).

## Blind recount (shown)
A separate subagent read only the 4 JSONs and GATE-PASSMARKS.md. It did not see the scorer, this file or the logs.
It found:
- every gate count, mean round and cap hit identical to the tables above;
- G1 and G2 pass in both seeds, with the same margins (seed 0: 0 and -2; seed 1: +1 and +2);
- verdict PASS.

The marks do not say how to break ties for "best fixed depth on dev". The scorer takes the smallest tied depth. The
recount tried both the smallest and the largest tied depth: the largest gap is +1 of 200 either way, so there is no
stop failure under either choice.

The recount also noted that the JSONs carry no fp32/TF32 field. Strict fp32 rests on the script's `--device cuda`
path, which turns TF32 off and uses no autocast (scripts/claude_relnet_practice.py, sha256 checked on the machine),
not on the JSONs.

## GPU, time and money
- **Machine that ran it:** RTX 3090 24 GB, vast offer 50443920 (machine 84216, California), $0.1707/hr, 35.5 TFLOPS
  (208 TFLOPS per $/hr), reliability 0.988, about 14 CPUs. Image pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
  (torch 2.4.1+cu121, Python 3.11.9).
- **Timeline (UTC):**
  - rented 21:51:47; the container started 22:06:17 (14.5 min of image loading);
  - the 4 runs went from 22:06:20 to 22:15:40 (9.3 min wall), all exit code 0;
  - destroyed 22:17:28.
- **GPU memory:** 6.8 GB for all 4 runs together (sampled every 2 min, so the true peak may be a little higher), at
  99-100% GPU use.
- **Cost:** three rentals, priced from $/hr x time from rent to destroy:

| attempt | GPU | minutes | cost |
|---|---|---:|---:|
| 1 | RTX 4070 SUPER 12 GB | 8.2 | $0.018 |
| 2 | RTX 3090 24 GB (never started) | 10.7 | at most $0.026 |
| 3 | RTX 3090 24 GB (the run) | 25.7 | $0.073 |
| **total** | | | **about $0.12** of the $1.00 budget |

- The account credit fell $0.455 over the same period. Other sessions' instances on the same account were running at
  the time (one labelled claude-sleep-358t3), so that figure is an upper bound, not this job's cost.
- All three of my instances were destroyed. For each, `GET /api/v0/instances/<id>/` then returned `{"instances":
  null}`, and none of the three appears in `GET /api/v0/instances/`. I did not touch the other sessions' instances.

## Deviations (all of them)
1. **Code delivery.**
   - The repo is private.
   - vast's `onstart` field is limited to 4,048 characters, and the base64 tarball is 33,100.
   - So the job went in as the container command instead: runtype `args`, args `["bash", "-c", <script>]`. The image
     has no ENTRYPOINT, only `CMD /bin/bash`.
   - Results came out through the container log, as planned. The script, with the base64 elided, is
     practice-gpu/job-args.sh.
   - The tarball holds the 9 files from main at 5cc045e3d. On the machine, the tarball sha256 and all 9 file sha256s
     matched mine (listed in the log).
2. **API details differ from the handoff's memory.** Checked against docs.vast.ai:
   - search is `POST /api/v0/bundles/` with a JSON body;
   - the logs call caps `tail` at 20,000 lines.

   Create (`PUT /asks/<id>/`), list and destroy were as written.
3. **Three rentals instead of one.** Each failed attempt was destroyed at once, per "destroy on any failure", and no
   score existed from any of them.
   - **Attempt 1:** RTX 4070 SUPER, offer 44275548, machine 143557. This was the top of the handoff's search: 272
     TFLOPS per $/hr, $0.1307/hr.
     - relnet seed 0 died with CUDA out of memory before step 250.
     - The 4 runs held about 5.3 GB (the crashing run itself 1.9 GB), yet the 11.6 GiB card had 17 MB free.
     - Suggested: about 6 GB was held by something outside our container. It was not listed in the error.
     - The 3 surviving runs were training normally when I destroyed it. Their log is
       practice-gpu/vast-attempt1-rtx4070s-oom.log.
   - **Attempt 2:** RTX 3090, offer 44579230, machine 137041. The host's Docker could not pull the image ("proxyconnect
     tcp: dial tcp 127.0.0.1:7890: connect: connection refused"), and vast set it to stopped. There is no container
     log.
   - **Attempt 3:** ran.
4. **Search filter added after attempt 1:** GPU memory at least 23,000 MB, for headroom. Attempt 3's offer was the
   highest TFLOPS per $/hr under the handoff's filters plus that one, excluding the two failed machines. Cheaper
   12 GB and 10 GB cards were skipped because of the filter.
5. **Job additions for attempts 2-3 (no recipe change):**
   - a GPU-memory check before the runs (abort if over 2,000 MiB were already in use; attempt 3 had 1 MiB);
   - memory sampling every 2 min.
6. **Reproducibility across GPUs (shown).** The 3 runs that survived attempt 1 match attempt 3's training loss exactly
   at step 250. By steps 500-1,250 the two GPUs differ by up to 2%: for loop seed 0 at step 750, 1.3653 on the 4070
   SUPER vs 1.3377 on the 3090. The script is strict fp32 with TF32 off. Suggested: this is ordinary floating-point
   drift between GPU models. The CPU replication will not be bit-identical either.
7. **Instance key.** vast issues each instance its own instance-scoped API key. It came back in the create response,
   and my shell echoed it once into this session's tool output. I removed it from the saved response and did not
   use it.

   Untested: whether vast places that key inside the container. I put no credential on any machine. All three
   instances are destroyed.
8. **Where the commit goes.** The commit goes to main with no PR, as the handoff and the task prompt say.

## CPU replication
The first session's CPU runs (compiled, started 21:09 UTC) were not on main at 22:18 UTC. They are reported alongside
when they finish, not chosen by score (GATE-PASSMARKS.md addendum).

## Next
RACE-PASSMARKS.md from the few-example test chat (artifacts/claude-fewex-*/) was not on main at 22:18 UTC. Per the
handoff, this session stops here. Test C waits for those marks and Ben's go.
