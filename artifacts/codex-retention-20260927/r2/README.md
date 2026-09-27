# R2 ready for parent registration

R2 preparation is complete: [PASSMARKS.md](PASSMARKS.md) fixes the protocol and [run_mastered.py](run_mastered.py) implements it. No R2 benchmark, training, or GPU run has started. The parent owns committing and later execution, after the existing R1 run finishes.

Before launch, force-add these three files because `artifacts/` is git-ignored, commit the marks before any R2 run, and give the runner that commit's full SHA with `--passmarks-sha`. The runner compares committed and working PASSMARKS bytes before creating a seed output directory or benchmarking; it accepts only seeds 31 and 32 and their dedicated `r2/seed31` and `r2/seed32` paths, refusing to overwrite them. The parent should verify the committed software version and report both seeds, even if seed 31 misses mastery.

This is a distinct confirmation after R1's undertrained seed 29 (grids5 174/200 versus its 190 bar). R2 fixes A at 6,000 steps, B at 2,500 and uses fresh held-out seeds 92031/92032. Candidate and control share each seed's training trajectory; they differ only in serving the old skill through its complete immutable snapshot or through the newest mutable model. All training inputs and targets come from the repository's existing code generators and exact checkers. Capacity is two full 1,646,750-parameter models. R2 does not use a learned switch, PC, cloud, downloads, or sealed TEST-ONLY data.

R1 keeps its own verdict. **Even if R2 passes, R1 remains INCONCLUSIVE where its mastery gate failed.** R2 can establish only scoped, task-aware functional retention under its registered conditions; it cannot repair or regrade R1.
