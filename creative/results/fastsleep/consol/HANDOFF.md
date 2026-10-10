# Handoff: consolidation sleep (10-08, 12:46 PM ET)

Ben's ask: a sleep that (a) absorbs the day's finds in very few updates, (b) loses no old skills, (c) ideally improves old skills through transfer.
Branch `claude/friendly-bohr-z4dpfo`, PR #53 (base: PR #48's branch `claude/project-thread-2kevpk`).

## State (10-09, 9:40 AM ET): finished

Done end to end: literature (`LIT.md`, `LIT-ADDENDUM.md`, checked by a Haiku workflow), marks (`MARKS.md`, every amendment dated and committed before the
run it affects), Screen A (2 parents), the 256-update rerun, and the six-parent confirm. **Verdict (README.md, top): marks 1-4 pass.** Holdout 76.1% in
256 updates; no harm vs N; old skills +0.52 [0.31, 0.74]. The "through transfer" label is not shown: the replay-only control does better on old skills
(+2.11). Report only: the old-skill gap against the raw B2 comes from the parent build, not from the sleep, and plain practice repairs it.
No job is running. Container state below is not in git, and a container restart already happened once (10-09 8:08 AM ET).

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
- Rebuilt N: `~/rl/parents/s200` to `s205` (`fastsleep setup --T 3.0 --floors ~/work/dev_floors.json`; the floors file is also in the repo as `dev_floors.json`).
- Runs: Screen A `~/consol/A/`, 256-update reruns `~/consol/A256/`, confirm `~/consol/C/<parent>/{fd,rp}/` (learner.pt kept; result, hits and holdout files are copied into `confirm/` in the repo).

## Facts learned (shown)

- Rebuilt N is close to, not equal to, the research loop's: last losses differ in the 3rd-4th decimal (s201 stones 0.4661 vs 0.4492; s200 0.6051 vs 0.6099; s202 0.5141 vs 0.5151). Night counts are close (s200 424 vs 420 fitting tries, s201 334 vs 344, s202 223 vs 207). Arms share one N per parent, so paired comparisons are fine; the 71.3% comparison is between near-copies.
- N (s201 / s202): C2 DEV first try 0.4 / 0.8%, skills in_dist 88.3 / 87.5, own held self-check 93.6 / 92.9, held practice fits 0.
- s202's night (896 pool questions): 178 own tries + 714 chain records. The full research-loop sleep would be about 557 updates on it; the screen's 128 is 23%.
- CPU cost: about 48-80 s per 1,024-row update on one core; a night about 13 min.
- Memory: the cgroup limit is 14.3 GB (not the 16 GB `free` shows). A night's sampling peaks at about 6.4 GB, a sleep run at 3-4 GB. The s201 night was OOM-killed twice before re-sequencing. Replay rows are now trimmed to the rows each night draws (identical draws, tested).
- The model's loss is a per-row mean, so the micro-batch gradient accumulation used on CPU gives the same update as one 1,024-row pass.

## Next steps (in order of value)

Ben's decision (10-09 about 10 AM ET): all three are parked for now. He wants one big proven run, not more small tests. The PC is busy with the size test
until late Saturday ET; PC job 1 is queued after that only if the big-run plan needs it. The GPT prompt is optional. The 12 learners are saved on the branch
`claude/consol-learners` (sha256 in `confirm/LEARNERS.sha256`).

1. Mix ratio, the open question (Ben asked about it; untested): the sleep's skills rows carry half the weight per step. One change: the same sleep with a larger skills share (for example 256 dream rows + 768 skills rows per update), or the control's batch-1,024 version (two halves of skills rows) as the dilution test. GPT prompt ready: `reviews/gpt-consol-transfer-2026-10-09.md`.
2. PC job 1 (`PC-JOB-1.md`): the research-loop sleep on the same rebuilt N, with the harm measure, for a paired baseline against 76.1% and its real harm.
3. A stop rule that also watches the model's own held skills rows (Vins et al. 2025 in `LIT-ADDENDUM.md`). Cheap, since both checks already run.
4. Screens B and C were never needed (fd passed harm); their code (`consol scale`, `--arm fdw`) is tested but unrun.

## Open issues for Ben

- Compute: Ben's PC and Mac are not reachable from this container. Vast credit was $7.55, with 14 boxes from other threads burning about $9/h (push sent). A $20 top-up runs the whole confirm on one 5090 in about 2 h instead of about 8-10 h of CPU.
- Interpretation used for the autonomy rule: fixed procedure settings chosen in development (lr, batch, the stop rule, the scale grid) are allowed. Anything that changes per night is chosen by the model from its own signals: held practice fit rate (no answers) and its own held skills training rows.
- Holdout: the research loop's `creative/data/c2rl/holdout.jsonl` is used only in the confirm, once per parent, because the 71.3% mark was measured on it. Its line count was read once (wc -l) at setup; no content was opened.
