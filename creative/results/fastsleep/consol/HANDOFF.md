# Handoff: consolidation sleep (10-08, 12:46 PM ET)

Ben's ask: a sleep that (a) absorbs the day's finds in very few updates, (b) loses no old skills, (c) ideally improves old skills through transfer.
Branch `claude/friendly-bohr-z4dpfo`, PR #53 (base: PR #48's branch `claude/project-thread-2kevpk`).

## State in one paragraph

Literature done, three candidates picked, marks written and committed before any run, code written and tested. **No result exists yet.** Screen A
(fresh dreams vs re-read rows) is running on this cloud CPU: s202's `rlc` run was at update 20 of 128 at 16:43 UTC. Everything below "Where things
live" marked *container* is lost if this container is reclaimed. A new session must rebuild it with the commands in "How to resume".

## Files in the repo

- `LIT.md`: digest of five Haiku literature scouts and the three candidates (fresh dreams, self-chosen scale, interference-weighted replay). Rejected: EWC/SI/MAS, GEM/GPM, meta-learned rules, frozen-teacher distillation and SAM, each with the reason.
- `MARKS.md`: all pass marks and proved-wrong lines, with every amendment dated, each committed before the run it affects. Read this before running or judging anything.
- `creative/consol.py`: the sleep. Arms `rlc` (research-loop data: finds + 3 fixed replays, re-read), `fd` (fresh dreams), `fdw` (fd + interference-weighted replay), `ro` (replay-only control). `scale` subcommand = candidate 2 (no training).
- `creative/consol_report.py`: `snaps` (measures the 32/64 snapshots) and `screenA` (scores Screen A's marks exactly as written).
- `creative/tests/test_consol.py`: 12 tests, all pass (`python3 -m creative.tests.test_consol`, about 2 min on 1 core).
- `chainA3.sh`: the launch chain now running. `tput.py`: the timing probe.

## Where things live (container, not in git)

- Parents (raw B2): `~/work/ckpt/B2_s{100,101,200..205}.pt`, from branches `claude/creative-parents` and `claude/b2-confirm-checkpoints` (sha256 checked for s100/s101).
- Skills data: `~/work/data`, `~/work/data_big` (`python3 -m custom_io.local_runner setup --work ~/work --curriculum ~/work/cur`, curriculum from branch `claude/project-thread-y0sxwe`; hashes matched).
- Rebuilt N: `~/rl/parents/s{200,201,202}` (`fastsleep setup --T 3.0 --floors ~/work/dev_floors.json`). **s203-s205 not built yet.**
- Runs: `~/consol/A/<parent>/<arm>/` (result.json, hits.json, learner*.pt), logs `~/consol/A-<parent>-<arm>.log`, finish lines `~/consol/chainA.txt`.

## Facts learned (shown)

- Rebuilt N is close to, not equal to, the research loop's: last losses differ in the 3rd-4th decimal (s201 stones 0.4661 vs 0.4492; s200 0.6051 vs 0.6099; s202 0.5141 vs 0.5151). Night counts are close (s200 424 vs 420 fitting tries, s201 334 vs 344, s202 223 vs 207). Arms share one N per parent, so paired comparisons are fine; the 71.3% comparison is between near-copies.
- N (s201 / s202): C2 DEV first try 0.4 / 0.8%, skills in_dist 88.3 / 87.5, own held self-check 93.6 / 92.9, held practice fits 0.
- s202's night (896 pool questions): 178 own tries + 714 chain records. The full research-loop sleep would be about 557 updates on it; the screen's 128 is 23%.
- CPU cost: about 48-80 s per 1,024-row update on one core; a night about 13 min.
- Memory: the cgroup limit is 14.3 GB (not the 16 GB `free` shows). A night's sampling peaks at about 6.4 GB, a sleep run at 3-4 GB. The s201 night was OOM-killed twice before re-sequencing. Replay rows are now trimmed to the rows each night draws (identical draws, tested).
- The model's loss is a per-row mean, so the micro-batch gradient accumulation used on CPU gives the same update as one 1,024-row pass.

## Running now (chainA3.sh)

s202 `rlc` (sleep phase) -> s201 `rlc` (night, then sleep) -> both `fd` runs start 2 min after s201's finds.pkl appears -> `ro` s202 after s202 `rlc`, then `ro` s201.
Expected Screen A end: about 4-5 PM ET. Note: s202 `rlc` was started by an earlier chain that was stopped; a watcher writes its finish line to chainA.txt.

## Next steps

1. When Screen A finishes: `python3 -m creative.consol_report snaps --out ~/consol/A/s201` (and s202), then `python3 -m creative.consol_report screenA --root ~/consol/A --parents s201 s202`. Judge against MARKS.md as written; write the README with paired numbers, labelled shown / suggested / untested.
2. Screen B (`consol scale`) only if fd at U* fails harm; Screen C (`--arm fdw`) only if harm remains. If no step up to 128 reaches 71.2 DEV, rerun fd at 256 (rule in MARKS.md).
3. Build s203-s205 (`fastsleep setup`, one at a time beside the runs, about 45 min each; memory!).
4. Confirm on s200-s205 with `--self-stop`, cap U*, plus `ro`; holdout once per parent for the winning arm only. Never open C2 test or labelled.
5. Report only, if compute allows: the full research-loop sleep's real harm (`creative/rl/rescore_harm.py`), about 7 h per parent on this CPU.

## Open issues for Ben

- Compute: Ben's PC and Mac are not reachable from this container. Vast credit was $7.55, with 14 boxes from other threads burning about $9/h (push sent). A $20 top-up runs the whole confirm on one 5090 in about 2 h instead of about 8-10 h of CPU.
- Interpretation used for the autonomy rule: fixed procedure settings chosen in development (lr, batch, the stop rule, the scale grid) are allowed. Anything that changes per night is chosen by the model from its own signals: held practice fit rate (no answers) and its own held skills training rows.
- Holdout: the research loop's `creative/data/c2rl/holdout.jsonl` is used only in the confirm, once per parent, because the 71.3% mark was measured on it. Its line count was read once (wc -l) at setup; no content was opened.
