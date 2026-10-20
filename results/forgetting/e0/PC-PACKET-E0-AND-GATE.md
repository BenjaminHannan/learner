# PC packet: E0 readout + Main brain ship-gate runs (DRAFT, coordinator review pending). Free; PC CPU only; no GPU, no Vast.

Why this is on the PC: E0 and the ship gate need Main brain's run folders and checkpoints under `/mnt/project-files`. They are on no
remote branch (all 123 remote branches searched on Oct 18, 23:50Z), so no cloud session can run them.

## Part 1. E0, measurement only (~1-2 CPU-h; trains nothing)
Ship instrument is already fixed: the 6,800-row DEV under the house rule (coordinator ruling, Oct 16).

1. Build the 6,800-row DEV once (about 2 min), from a learner checkout of branch `claude/project-thread-y0sxwe`:
   `python -m skills_curriculum.build --out ~/sk200k_big --train 200000 --dev-per-cell 200 --seed 1`
   Check: `sha256sum ~/sk200k_big/dev/in_dist.jsonl` starts `3e3a5edb`.
2. List the four Main brain final runs E0 needs: `ls /mnt/project-files/main-brain/runs/ | grep -iE 'soft10|kl30|nk30'`
   (NK-soft10 at s200 and s201; NK30 at s200 and s201; e.g. `sheet-s200-kf99n-kl10-soft10`).
3. Score them from a learner checkout of branch `claude/forgetting-round-g` (the E0-ready commit; it holds custom_io/, domain/ and this
   script; the y0sxwe checkout of step 1 is only for building the DEV and has neither). From that checkout's root:
   `CUSTOM_IO_DATA=<seed-1 200k build> python results/forgetting/e0/e0_score.py --big ~/sk200k_big/dev/in_dist.jsonl --out e0.json RUN1 RUN2 RUN3 RUN4`
   (--repo defaults to that checkout; add `--parent <path>` if the summaries' parent paths do not resolve on the PC; e0.json records the
   repo commit and CUSTOM_IO_DATA; an existing e0.json is refused unless --overwrite.)
4. Bar (fixed in the solve doc before any result): if an NK-soft10 final fires a family on the 6,800 DEV, the ship decision is reopened
   between NK-soft10 and NK30. Report e0.json to Main brain.
   Expected from the far data (suggested, not shown): NK-soft10 = L13-like, likely fires fewshot_number_rule on 6,800.

## Part 2. Ship-gate runs (Main brain domain mode, DM1/DM3 marks, s200 and s201, lr 1e-4, scored on BOTH DEVs)
One change vs the far baseline L11 (soft 1, KL 10, energy 0.99): KL 10 -> 30, exactly the config the far work confirmed; note that vs
the shipped NK-soft10 guard it also moves soft 10 -> 1. Write each run's DM1/DM3 pass marks into its folder before launch.
| run | guard config (CONST.json / flags) | why |
|---|---|---|
| GATE-G1 | soft 1, KL 30, `protect_energy` 0.99; train to the update count that matches the far 8k stop step, then stop | round-G ship candidate (Ben's decision, Oct 20); the stop step is part of the recipe: past it the far runs leak |
G3 (energy 0.999) is not adopted (its pre-set "proved wrong" condition fired), so it has no gate run.
Read each on both axes, as in the far work: 6,800 drop + worst family at every night, and the new-skill curve long enough to tell
delay from cap. A guard ships only if it passes DM1/DM3 and the house rule on the 6,800 DEV on both seeds.
