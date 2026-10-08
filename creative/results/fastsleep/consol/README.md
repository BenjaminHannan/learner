# Consolidation sleep: results so far (10-08)

Marks: `MARKS.md` (committed before the runs they judge; amendments dated at its end). Literature and candidates: `LIT.md`. Code: `creative/consol.py`,
`creative/consol_report.py`. Handoff and how to resume: `HANDOFF.md`. All numbers below are C2 DEV and skills DEV only; no sealed split was opened.
Parents: s201 and s202, rebuilt on the cloud CPU (close to the research loop's N, not identical: see MARKS.md). Times in ET.

## Screen A: fresh dreams vs re-read rows (finished 5:30 PM ET)

Each arm sleeps 128 updates (batch 1,024: 512 day rows + 512 fresh skills rows) on the same night: the model's own tries plus chain search. s202: 178 own + 714 chain records.
- `rlc`: the research-loop sleep's data, the records plus 3 fixed replays each (about 18 visits per record at 128 updates).
- `fd` (fresh dreams): every day row is newly made by the executor from a found program on fresh inputs. Every row is seen once (65,536 distinct rows).
- `rp` (transfer control): the same skills rows as `fd`, the day half removed (batch 512).

| 128 updates | s201 C2 DEV | s201 in_dist (N 88.25) | s202 C2 DEV | s202 in_dist (N 87.54) |
|---|---|---|---|---|
| N (no sleep) | 0.4 | 88.25 | 0.8 | 87.54 |
| `rlc` | 57.4 | 88.25 | 52.0 | 87.71 |
| `fd` | **64.8** | 88.50 | **57.4** | 88.01 |
| `rp` | 0.0 | **89.51** | 0.0 | **89.22** |

| paired 95% intervals | s201 | s202 |
|---|---|---|
| C2: `fd` - `rlc` at 32 / 64 / 128 updates | -13.7 [-19.1, -8.6] / +2.0 [-2.3, 6.2] / **+7.4 [3.5, 11.3]** | +1.2 [-0.4, 2.7] / -1.2 [-5.1, 2.7] / **+5.5 [0.8, 10.2]** |
| in_dist: `fd` - `rlc` at 128 | +0.25 [-0.18, 0.69] | +0.31 [-0.12, 0.72] |
| in_dist: `fd` - N | +0.25 [-0.26, 0.75] | +0.47 [-0.07, 1.00] |
| in_dist: `rp` - N | **+1.26 [0.71, 1.81]** | **+1.68 [1.12, 2.28]** |
| in_dist: `fd` - `rp` | **-1.01 [-1.54, -0.47]** | **-1.21 [-1.79, -0.69]** |

Marks (judged by an Opus reviewer against MARKS.md as written): **A1 not testable** (`rlc` shows no harm at 128 updates: drop 0.00 and -0.16), **A2 pass**,
**not proved wrong**, fall-back rule **-> the confirm uses `fd`**. U*: no step up to 128 reaches 71.2 (two-parent mean `fd` C2 35.7 / 48.2 / 61.1 at 32 / 64 / 128),
so `fd` is rerun at 256 updates (running).

### How to read it

- *Shown (two parents, DEV):* at the same 128 updates, fresh dreams learn C2 better than re-reading, by +5.5 to +7.4 points, with both intervals above 0. The harm measure passes for both arms and `rp`; no family fires at 128 updates.
- *Shown:* the 7d harm is not present at 128 updates in either arm. At 32 and 64 updates (mid-schedule, lr not yet lowered) both arms do show harm (up to 4 families firing, `rlc` on s202 still fires `passage_qa` at 64), and it fades as the lr falls. *Suggested:* the early harm is the high-lr phase, not the data; one cannot tell from two parents whether the earlier 7d harm (night 1 at 32 visits) was the same thing.
- *Shown:* "old skills improve" is real for skills practice alone: `rp` raises in_dist by +1.3 to +1.7 with intervals above 0, and the fresh-row result of the 2x2 drift check (+1.6 to +2.3) agrees.
- *Not shown:* that the new skill helps old skills. `fd` - N is +0.25 and +0.47 with intervals that include 0, and `fd` is 1.0 to 1.2 points BELOW the control `rp`, with intervals below 0. *Suggested:* the day half displaces half the skills practice, which costs about 1 point of in_dist; the new skill adds nothing back that this measure can see. Under MARKS.md claim (c) the label would be "improved, not shown to come from the new skill" at best, and on these two parents even the improvement does not clear 0 for `fd`.
- *Untested:* whether more skills replay in the same batch (a smaller day share) would give the improvement and still learn the day's finds; this is the mix-ratio question Ben asked about.
- *Not met yet:* the speed mark (C2 at least 71.2 within the update cap). At 128 updates `fd` is at 61.1 (two-parent mean); the research loop's sleep used about 557 updates on s202. The 256-update rerun decides.
- Caveats: two parents; the 32- and 64-update snapshots are mid-schedule; rebuilt N are near-copies of the research loop's; the re-read arm is capped at 128 updates (about 18 visits per record), not the research loop's 80-visit, 557-update sleep.
