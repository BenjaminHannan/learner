BASH-ONLY: yes
GPU: vast (one rented card; BensPC is treated as busy. If BensPC is free the Director may instead run box/drive.sh's steps there for $0). CAP: $4.00 for the whole job (the guard stops at $3.00). Estimate 2.5 to 5 hours (inferred from slp-358n3, not measured).
DISK: 1 (Mac only; the rental holds the work)
HELD: do not release until (a) the Director has committed this folder and scripts/claude_dir_h6_sleeplen.py, (b) the kit copy below exists on main, and (c) <PIN> is set to the commit that holds both.
Owner job (helper H6, Claude, wrote this on 2026-09-28 19:2x UTC for the Director). Follow handoff/director-briefs/rules.md: additive only, no git by the job, fictional names only, blind panels and readpanel320 never opened, never read or print keys or tokens, counts only, every deviation reported.
WHY: artifacts/claude-dir-h6-sleeplen-20260928/DESIGN.md and PASSMARKS.md (committed before this job). One change to slp-358n3's long night: the learning rate 3e-5 becomes 1.5e-6 (same learning rate x steps as the 300-step night). Arms N, S, L, B on 358u's 4 loop checkpoints, seeds 13-16, 3 nights. Do not touch slp-358n3 or its files; the new script only imports its sealed code.

KIT (Director's copy, not yet written): copy handoff/kit/sleep358nv to handoff/kit/sleeph6v and change only these things.
- vcommon.sh: A=artifacts/claude-dir-h6-sleeplen-20260928; LABEL=claude-dir-h6-sleeplen; G default $HOME/premonition-watch/dirh6-vast; CAP_STOP=3.00 (hard cap 4.00); MAXDPH=0.60 and the fit check stay; BASE_H=4.0 (inferred); ORDER="s13 s14 s15 s16"; CKPTS="" (nothing to fetch back but JSON and logs: no weights are saved); EXPECT="dirh6-seed%S.json"; keep MINRAM_GB=24 and the 16-core CPU line only if drive.sh still runs anything on the CPU (it does not: drop the cpu_cores_effective clause).
- vstart.sh: the duplicate gate checks $A/RESULTS.md and $A/runs; `git archive "$PIN"` must include scripts, artifacts/claude-slp358n3-20260927 (SEAL-code.sha256.txt and run-vast/sizes.json), artifacts/claude-dir-h6-sleeplen-20260928, artifacts/claude-rsn358i-20260926/tests and handoff/kit/sleeph6v/box. The 4 checkpoints go up from ~/premonition-models/rsn358u/loop-s{13..16}/final.pt, each sha-checked against artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt (same as the sleep358nv kit).
- box/drive.sh: same header checks as sleep358nv (torch==2.11.0 cu128 pinned, SEAL-code 18 of 18 from slp-358n3, checkpoints 4 of 4, `claude_rsn358u_run.py selftest`). Then: copy run-vast/sizes.json to W/sizes.json (no pick-sizes); NO RESUME step; run `python -B scripts/claude_dir_h6_sleeplen.py smoke` and stop with FAILED if it does not print "smoke ok"; then launch the four seeds `python -B scripts/claude_dir_h6_sleeplen.py run --ckpt ck/s$S/final.pt --seed $S --sizes W/sizes.json --out W/s$S` (no --long flag: L and B are in every seed), each while 5 GB is free; no S-final.pt sealing. Write W/drive-state.txt lines and end with DONE or FAILED as before.
- vguard.sh / vcollect.sh: expect W/s$S/dirh6-seed$S.json instead of slp358n3-seed$S.json and S-final.pt; collect into artifacts/claude-dir-h6-sleeplen-20260928/runs/.

STOP RULES: if smoke fails, report the first traceback verbatim and STOP (the guard destroys the rental after copy-back). Do not fix the script. Do not re-run a failed seed with changed settings. If spend reaches $3.00 the guard copies back what exists and destroys the instance; report which seeds finished (a seed with fewer than 4 finished arms counts as dead, per PASSMARKS.md).

```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=<PIN>
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleeph6v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleeph6v/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
COLLECT: a second held job, modelled on handoff/held/rent358n3-3-collect.md with `sleeph6v` in place of `sleep358nv`, runs vcollect.sh after the guard ends (NOT-YET means wait).
BLIND STEP after collect: a separate agent recounts every mark from PASSMARKS.md and the 4 dirh6-seed*.json only, before RESULTS.md is written.
PUSH: artifacts/claude-dir-h6-sleeplen-20260928/runs artifacts/claude-dir-h6-sleeplen-20260928/run-vast (never weights; there are none).
REPORT (final reply, counts only): verdict first (PASS / proved wrong / partial / VOID), then for each seed and arm the day_grids, day_sums and old-skill counts after nights 1-3, the INTEGRITY flags, torch and GPU name, minutes, dollars spent, every deviation.
