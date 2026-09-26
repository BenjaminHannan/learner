# rd-371b step 1: note writer's drafts (BensPC) — RESULTS-notes

Builder run 2026-09-26 on BensPC (RTX 5070 Ti, CUDA). Sealed code run unmodified.
Panel notepanel371b written over once (greedy only); only counts and ms viewed.
No panel turn, dialog, or note is quoted anywhere in this file.

## Verdict: STEP 1 DONE (drafts written; no checker, no marks decided here)

## Printed counts (verbatim from scripts/claude_rd371b_sample.py)

- Step 2 TRAINING DRAFTS (greedy + 1 sample, temp 0.8, seed 371):
  {"drafts": 2526, "notes": 2514, "unparsed": 7, "device": "cuda"}
- Step 3 PANEL NOTES (greedy only, once, samples 0):
  {"drafts": 319, "notes": 314, "unparsed": 5, "device": "cuda"}

## Counts check

- train_drafts.jsonl lines: 2526 (matches printed drafts 2526)
- panel_notes.jsonl lines: 319 (matches printed drafts 319)
- Expected step-2 drafts from train windows (1263 windows x 2): 2526 (matches)

## Write ms per draft (ms field only; no text viewed)

- Train drafts (n=2526): median 995.0, p90 1893.5, max 3009.8
- Panel notes (n=319): median 1010.3, p90 1900.1, max 3112.4

## Device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode (+1 sample at temp 0.8 for step 2). No rental, $0.
- WRITER: C:/Users/benja/rd378/tree/WORK/nrun/merged, model.safetensors sha256 dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510 (verified before running; match).
- Venv: C:/Users/benja/lis300/venv (torch 2.11.0+cu128, cuda True). PYTHONUTF8=1.
- No training, no downloads.

## Wall time per step (UTC 2026-09-26; BensPC local = UTC-4)

- Setup (fetch, tree build builder-outbox + main on top, chunked scp, extract, WRITER sha, venv check): 02:15-02:43.
- Step 1 seals (BensPC tree): 02:40-02:43 (rd371b SEAL 1/1 OK, SEAL-data 6/6 OK, notepanel371b SEAL 2/2 OK).
- GPU wait (other job rsn358a loop then plain, one job at a time): 02:15-02:59 (GPU 0%, 426 MiB at 02:59).
- Step 2 training drafts: launched 02:59:42 (died silently), relaunched ~03:02, finished 03:45:24 (~43 min).
- Step 3 panel notes (once): launched ~03:46, finished ~03:53 (~7 min).
- Medians + copy-back: 03:53-03:55.
- Total ~1 h 40 min, over the 90 min cap (see deviations).

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv and the rd-378 merged writer instead of new downloads; new work dir C:/Users/benja/rd371b used throughout.
2. Set PYTHONUTF8=1 (env var only).
3. shasum absent; seals checked with git-bash sha256sum -c (same format), all OK.
4. First step-2 launch (immediate-exit ssh) died silently with empty log and no output file; relaunched with the ssh session kept alive ~100 s (nohup + disown, no setsid in git-bash) and it survived — same fix as lis-318/rd-378.
5. Launch-then-wait ssh calls timed out locally (180-300 s) with no output even on success; status checked via separate ssh (GPU util, line counts, logs). No data lost.
6. Tree.tgz (164 MB) transferred in 6 split chunks (whole-file scp stalled at 53 MB on the slow link) and reassembled; sha matches (903bd79f...).
7. GPU was busy with another agent's rsn358a job on arrival (loop seed 2, then plain seed 2); waited for 0% idle before launching, one GPU job at a time throughout.
8. Time cap exceeded by ~10 min (90 min cap to 03:45, finished copy-back 03:55) due to GPU wait + ~43 min sampling; Ben's 7am goal still met.
9. Panel seal lists 2 files (dialogs.jsonl, README.md), both OK; panel written over exactly once; panel_notes.jsonl pushed unread (only counts and ms viewed).
