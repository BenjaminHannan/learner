# Handoff: run the relation-net practice gate on a rented vast.ai GPU

Written 2026-09-27 21:19 UTC by the relnet chat. Ben: paste everything below the line into a new cloud session in
the beautiful-model environment. That environment holds the vast credential.

---

# Goal: practise the relation net and its same-size loop on sums and grids on a vast.ai GPU, and score the practice gate

Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first. Ben (a high-school senior) reads
your final report.

## State (all on main)
- **The task:** reviews/chat-prompt-relnet-2026-09-27.md. The relation network (GPT-6 Pro's design 3) is built
  and checked:
  - weights 1,644,198 vs the loop's 1,646,750;
  - every weight matrix gets a gradient;
  - it runs 3.6-6.2x slower than the loop on CPU.
  See artifacts/claude-relnet-20260927/REVIEW.md.
- **Practice gate, fixed before any score:** artifacts/claude-relnet-20260927/GATE-PASSMARKS.md. Read its
  addendum: **your GPU runs are the registered result.** Never edit that file.
- **Scripts (use them, don't change the recipe):**
  - scripts/claude_relnet_practice.py (has `--device cuda`: strict fp32, TF32 off, no autocast);
  - scripts/claude_relnet_gate.py (the verdict).
- **The first session** is running the same gate on CPU (about 2 hours per run). It is the replication. Ben
  decides when it stops; you don't touch it.

## Ben's authorisation and limits
- **Authorisation:** Ben asked for a vast.ai GPU at the cheapest TFLOPS per dollar-hour (2026-09-27, about
  21:10 UTC).
- **Budget:** at most **$1.00** for this job unless Ben says otherwise. Destroy the instance at $0.80 spent, when
  the job ends, or on any failure. Then confirm through the API that it is gone.
- **The key:**
  - It is an environment credential. Requests to `console.vast.ai` get `Authorization: Bearer <key>` added by the
    proxy.
  - Never print it, never ask for it, and never put it or any other credential on the rented machine.
  - First call: `GET https://console.vast.ai/api/v0/users/current/`. If it says "Invalid user key", stop and tell
    Ben.
- **If blocked:** if the sandbox's safety check denies a step, stop and tell Ben exactly what was denied. Don't
  work around it.

## How to run it
1. **API calls.** The vast API endpoints below are from memory; check them against docs.vast.ai before relying on
   them:
   - search offers: `GET /api/v0/bundles/?q=<json>`;
   - create: `PUT /api/v0/asks/<offer_id>/` with image, disk and onstart;
   - logs: `PUT /api/v0/instances/request_logs/<id>/`, which returns a URL;
   - list: `GET /api/v0/instances/`;
   - destroy: `DELETE /api/v0/instances/<id>/`.

   Plain HTTPS calls are best, because the proxy adds the key. This container has **no ssh client**, and outbound
   traffic is HTTPS through a proxy. So you cannot log into the machine: code goes in through the start-up
   (onstart) script and results come out through the logs.
2. **Offer:** 1 GPU, verified, reliability at least 0.98, CUDA 12.1 or newer, disk at least 20 GB, download at
   least 100 Mbps, on-demand. Sort by TFLOPS per $/hr (the `flops_per_dphtotal` field), highest first. Report the
   GPU, $/hr and TFLOPS you picked. Image: an official `pytorch/pytorch` CUDA runtime image with torch 2.4 or newer.
3. **Code in:** the practice needs exactly these 9 files from scripts/:
   - claude_relnet_practice.py, claude_relnet_gate.py, claude_relnet_net.py;
   - claude_xfer1_net.py, claude_xfer1_bench.py, claude_xfer1_adapt.py;
   - claude_rsn358a_envs.py, claude_rsn358m_maze.py, claude_blurt1.py.

   Take them from main at a commit you name. As a tar.gz they are about 24.5 KB, tested in a clean folder on CPU.
   - If the repo is public (check with the GitHub tools), the onstart script may `git clone` it and check out that
     commit.
   - Otherwise, embed the base64 tarball in the onstart script.
   - Either way, print the sha256 of the 9 files on the machine and check they match yours.
4. **Job, in the onstart script:** run these 4 at the same time on the one GPU, with no `--compile` and every other
   setting at its default (lr 1e-3, 6,000 batches of 64, the same seeds and panels):
   ```
   python -B scripts/claude_relnet_practice.py --arm relnet --seed 0 --device cuda --threads 2 --out OUT
   python -B scripts/claude_relnet_practice.py --arm relnet --seed 1 --device cuda --threads 2 --out OUT
   python -B scripts/claude_relnet_practice.py --arm loop   --seed 0 --device cuda --threads 2 --out OUT
   python -B scripts/claude_relnet_practice.py --arm loop   --seed 1 --device cuda --threads 2 --out OUT
   python -B scripts/claude_relnet_gate.py --dir OUT
   ```
   - Print progress to stdout, then each `practice-*.json` (gzip + base64, between clear markers) and the gate
     table.
   - Don't bring back checkpoints; their sha256 is in the JSONs.
5. **Results:** fetch the logs, decode the 4 JSONs into artifacts/claude-relnet-20260927/practice-gpu/, and rerun
   `scripts/claude_relnet_gate.py --dir artifacts/claude-relnet-20260927/practice-gpu` locally. Destroy the instance.

## Write-up and rules
- **RESULTS.md:** write artifacts/claude-relnet-20260927/RESULTS.md, verdict first, containing:
  - the gate table, with counts as "x of 200";
  - G1/G2 per seed, and PASS or FAIL per GATE-PASSMARKS.md;
  - the report-only rows: stop failure, mean rounds, cap hits;
  - GPU, minutes and dollars;
  - every deviation.
- **Commits:** commit to main with no PRs. Run `git pull --rebase` before every push, and never force-push. New
  files only, in scripts/claude_relnet_* and artifacts/claude-relnet-20260927/. Times come from `date -u`. Label
  claims shown / suggested / untested.
- **Blind recount:** a separate subagent recounts the key numbers from the raw JSONs and GATE-PASSMARKS.md only.
- **Then:** check main for the few-example test chat's `artifacts/claude-fewex-*/RACE-PASSMARKS.md`.
  - If it is there: plan the race (Test C in the task prompt) for this GPU. Send Ben the plan and a cost estimate,
    and wait for his yes.
  - If not: stop.
- **Final report to Ben:** at most 8 lines, plain words, result first. Did the relation net reach 190 of 200 on
  sums and grids, and is it within 3 points of the loop? What did the GPU cost, and how long did it take? End with
  the commit hashes.
