Building your sleep-practice experiment — verifying code seals and queuing the GPU run.
The rules file is missing from the scratchpad — I'll proceed with the rules as stated and pull the required specs.
Seals verify clean. Now checking the GPU queue before touching BensPC.
Queue files identified. Now checking whether BensPC is free.
GPU is idle with 32GB free. Checking whether the earlier queued jobs are done.
GPU is free — no training processes running, last queued job wrote files ~4h ago. Proceeding to set up code on BensPC.
CUDA torch is ready on the default python. Copying the sealed code over.
Selftest passes. Launching the pilot timing run on BensPC.
Background launch didn't survive. Retrying with a detached process group.
Detached processes die with the SSH session. Switching to a scheduled task so the job survives.
The pilot launched but exited with code 1. Reading the error.
The failure is in shared sealed code. Confirming the mechanism with a minimal probe before reporting.
Diagnosis confirmed. Cleaning up the scheduled task on BensPC.
VERDICT: BLOCKED — slp-363 did not run. Zero training steps, zero panels, zero marks. The sealed code fails deterministically on BensPC (Windows) at its very first file write, before any timing, training, or scoring. Per instructions I did not patch anything and stopped. This is not a scientific FAIL of the sleep question; the question is untested.

MARKS TABLE (integer counts; PASSMARKS.md bars shown for reference)

| Mark | Bar (per seed) | Seed 1 | Seed 2 | Result |
|---|---|---|---|---|
| S1 school: SCHOOL − each of PLAIN, PLACEBO, NOSLEEP | ≥ +20 of 1,000 | NOT RUN | NOT RUN | no result |
| S2 reasonpanel296: SCHOOL − PLAIN | ≥ −5 | NOT RUN | NOT RUN | no result |
| S3 school, answered-without-fact: SCHOOL − min(PLAIN, NOSLEEP) | ≤ +2 | NOT RUN | NOT RUN | no result |
| Proved-wrong clause (SCHOOL − PLACEBO ≤ 5 both seeds) | — | NOT RUN | NOT RUN | not triggered (nothing ran) |
| Bases trained | 2 | 0 | 0 | miss |
| Nights trained (PLAIN/PLACEBO/SCHOOL × 2 seeds) | 6 | 0 | 0 | miss |
| Checkpoints sealed in SEAL-run.sha256.txt | 8 | 0 | 0 | miss |
| Panel evals (8 ckpts × school + reasonpanel296) | 16 | 0 | 0 | miss |
| Dev runs | 8 | 0 | 0 | miss |
| Ledger lines appended (S1–S3) | 0 expected on block | 0 | — | correct (nothing to claim) |

EVERY MOVE (in order)
1. `git fetch -q origin main` — done.
2. Read on origin/main: PASSMARKS.md, 365-sleep-roadmap.md, docstrings of `claude_slp363_run.py`, `claude_slp363_night.py`, `claude_rsn_recipe.py` — done.
3. SEAL: `git archive origin/main` → /tmp/slp363seal; `shasum -a 256 -c SEAL-code.sha256.txt` → 5/5 OK; `shasum -a 256 -c SEAL-v2.sha256.txt` → 2/2 OK. Every line OK.
4. Local `uptime` + `df -g /`: 9 GB free (above the 3 GB stop bar). Mac used only for file transfer, not compute.
5. Queue check: BensPC GPU 0% util, no `python.exe` training process; lis319 work dir last write 16:16 vs 19:56 PC clock (~4 h idle); rsn355/rsn356 checkpoint dirs present. All queued rsn-*/lis-* GPU jobs finished → proceeded.
6. CODE: tarred `scripts + artifacts/claude-slp363-20260925 + artifacts/claude-reasonpanel296-20260924` (21 MB), scp'd to BensPC, extracted to `C:\Users\benja\premonition-models\slp363\code` keeping paths. Same python as rsn jobs: torch 2.11+cu128, CUDA True. `python -B scripts\claude_rsn296_gen.py` → "selftest ok" (buckets {0: 9831, 10: 6080, 20: 3605, 30: 2367, 40: 117}, gold-action mismatches 0).
7. PILOT via schtasks (two ssh-detached launches died with the session; scheduled task survived): failed at step 1, exit 1. No step completed, so no timing numbers and no TOO-SLOW estimate exist.
8. Deleted the scheduled task afterwards. BensPC left idle with nothing running.

THE EXACT ERROR (copied from `pilot-363-stdout.txt` on BensPC, first and only failing step `claude_slp363_night.py night --world-seed 363009 --seed 9 --n 2000`):
`fable_notebook_contract.LogCorrupt: read-back mismatch` — raised in `_append` (line 176) from `declare_relation` (line 264), called by `make_world`, the first write to a fresh temp notebook.

CAUSE (verified read-only, no edits): sealed `fable_notebook_contract.py` line 169 opens the log in text mode (`open(self.path, "a", encoding="utf-8")`, no `newline=''`), writes `line + "\n"`, then re-reads in binary and compares to `line + "\n"`. On Windows, Python translates `\n` → `\r\n` on text write. Probe on BensPC proved it: writing `'abc\n'` yields bytes `b'abc\r\n'`. So the read-back check mismatches on literally every write on Windows — deterministic, not transient, not disk (32 GB free on BensPC) or GPU. It blocks night-file building, panel building, and therefore the pilot and the full run. The Fix-sleep thread's `--dry` plumbing run passed on Mac/Linux, where no translation happens. Fix requires editing + resealing by the owning thread; I did not patch.

EVERY MISS / DEVIATION
- Misses: pilot timings (none), W363-pilot rename (W363 is empty — night file never created — left in place, never deleted), full RUN, all 16 evals, dev, totals.json, RESULTS.md, ledger append, PUSH (no files exist to push; repo untouched — `git status` shows only other agents' pre-existing staged files).
- Deviation 1: OPUS-RULES.txt was missing (its scratchpad dir is empty); proceeded using the rules as quoted in the task itself.
- Deviation 2: used a Windows scheduled task to launch the pilot instead of a plain foreground ssh command, because backgrounded ssh processes died with the session. No repo impact.
- Independence kept: never opened any item of reasonpanel296 or the school panel (neither was ever built); TEST-ONLY panels never read.

WHAT THIS MEANS / DOESN'T MEAN (plain English): Think of it like a lab notebook whose safety rule is "after writing a line, re-read it to prove it saved." That rule was written on a Mac, where a line ends one way, and Ben's PC ends lines a slightly different way — so the check fails on the very first line, every time, and the experiment can't even start. It says nothing about whether sleep practice works — that question is still open. What it does prove: the sealed slp-363 code as registered cannot run on BensPC at all, and no builder can work around that without breaking the seal. Next step belongs to the Fix-sleep thread: make the notebook log Windows-safe, reseal, and re-queue the builder.
