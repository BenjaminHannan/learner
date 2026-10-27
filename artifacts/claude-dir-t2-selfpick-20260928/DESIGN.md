# T2 design: the model picks its own replay store

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Analysis and design only; nothing was run on this box (no torch).
Labels: **shown** = read off committed raw files by code; **suggested** = a reading; **untested** = nothing here tests it.
Serves finish-line item 5 (sleep keeps old skills; overnight the model gets better at what it did) through Ben's idea "the model chooses what to replay".
Not the keep-old-skills thread's levers (weight blending, weakest-first draw from a fixed 16-store, `claude-dir-ks-20260928`): those change how a fixed store is used. T2 changes which 16 go in the store.

## 1. What the store test starts from (shown, from `artifacts/claude-distill-20260928/`)
A store of 16 per kind collapses every arm: R16 old-kind scores are 2 to 18 of 200 (all 4 cells, 3 draws), R128 gets 42 to 174 (sums4) and 80 to 139 (grids5).
So there is room: a better 16 could gain a lot, or nothing. After a maze day the net scores **0 of 200** on both old kinds in all 4 cells (shown), so "what it got right" cannot be
used to choose. The three-draw spread is small on old kinds (R16 SD 1.5 to 3.8 sums4, 0.6 to 5.3 grids5) and large on the maze count (SD 14.6 to 35.2 of 300).

## 2. The mechanism
The model's choice = its own cross-entropy on each pool puzzle at round 16, computed by the post-maze net itself (`item_losses`, `pick_store` in `scripts/claude_dir_t12_sleep.py`).
PICK: 8 highest and 8 lowest loss per kind (a mix of "hard" and "easy for it"), HARD: 16 highest, R16: first 16, R16b: items 16 to 31. The 128-pool is code-made and i.i.d., so R16 and R16b are two random 16s.
Why a loss ordering and not a correctness split: see PASSMARKS. Why a mix: Ben's idea keeps failed and successful items; the literature warns hardest-only small buffers can overfit (standing note 06 Q2, MIR arXiv 1908.04742, Rainbow Memory, tags A), so HARD is the control that could lose for that reason.
What the net can and cannot know (suggested): it has forgotten the old kinds entirely, so its loss ranking may reflect puzzle difficulty (long carries, hard grids) rather than "what I would forget". The test measures whether that ordering beats chance; it does not say a model that remembers more would choose better.

## 3. Where each number comes from (raw files, recounted 22:13 UTC)
| number | value | source | why |
|---|---|---|---|
| M1 bar sums4 | 12 of 200 | 3 x largest R16 draw SD (3.8) in `distill/sleeps/*.json`, up | 3 x the noisiest measured cell |
| M1 bar grids5 | 16 of 200 | 3 x largest R16 draw SD (5.3), up | same |
| which-16 spread rule | gain >= 2 x mean abs(R16b - R16) | measured in this run | a store choice must beat store-choice noise; unmeasured before |
| margin | max(6, 2 x SE) | Ben's rule (3 draws) | SE = sqrt(sum var / 3) |
| M2 slack | 20 | ks G_fresh (`claude-dir-ks-20260928/PASSMARKS.md`) and the distill fresh-panel check | fixed vs fresh 200-puzzle panels differ by up to ~14 by sampling alone |
| M3 plain floor | plain sleep64 9x9 = 14, 9 (+30) | `eq-runs/plain-s0-pre`, `plain-s1-pre` `adapt.json` | as ks Lead 2's plain row |
| proved wrong | seed mean gain < +5 | distill's own proved-wrong line, ks Lead 2 | same |
Replaces the draft's +15 (borrowed from distill's +20) and "at most 6 loss on the day's kinds": 6 is inside the 9x9 draw noise (SD 14.6 to 35.2), so the maze gate uses the margin instead.

## 4. Jobs (queue files, all HELD; Mac CPU, $0, fp32, one thread per process, 2 at a time)
Needs the keep-old-skills prep nets: `$HOME/premonition-ks/nets/loop-s{0,1}-pre/{k0,k64,k16384}.pt` (written by `ks-1-lead0`); a job says WAITING and exits 5 if they are missing. It does not rebuild nets.
| job | arm | sleeps | est. minutes (inferred: distill's sleeps took ~255 to 290 s each, +2 min of scoring here) |
|---|---|---|---|
| `dst-t2-1-r16-mac` | R16 (also T1's comparator) + selftest | 12 | 40 |
| `dst-t2-2-pick-mac` | PICK | 12 | 40 |
| `dst-t2-3-r16b-mac` | R16b | 12 | 40 |
| `dst-t2-4-hard-mac` | HARD | 12 | 40 |
Order: 1, then 2 (the verdict needs 1 to 3); 4 is the control. Each cap 100 minutes. Job files: `handoff/queue/dst-t2-*-mac.md` (HELD).

## 5. Risks and things not checked
- `scripts/claude_dir_t12_sleep.py` never ran (no torch here): py_compile only; the marks code ran (`selftest`, 12 cases, pure python). The job's first step is `selftest`; if it fails, stop and report the traceback (do not patch).
- Nets are the ks prep nets: ruler copies if their dev 9x9 matches the committed count, else rebuilt (not bit-identical to the ruler); every arm uses the same nets, so comparisons are like for like; absolute numbers must not be quoted against the ruler.
- The store choice reads true labels for the chosen items (as every arm does). A model that must also label its own picks is a second question.
- Two seeds and 4 cells: a small sample; the every-seed reading and 3 draws are the guard, not a rate.
- The comparator R16 is one fixed 16 (R16b tells how much another 16 moves it).
