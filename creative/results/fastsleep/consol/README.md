# Consolidation sleep: results (10-08 to 10-09)

## Verdict (confirm, six parents, finished 10-09 9:20 AM ET)

The recipe: the model runs its own night (its own tries plus chain search, an outside tool), then sleeps 256 updates of 1,024 rows. Half of
each batch is **fresh dreams** (the executor writes a new prompt from a found program each time, so no day row is read twice); half is fresh
skills rows. The model checks its own fit rate on 128 held practice questions every 32 updates and keeps its best checkpoint.

| mark (MARKS.md, fixed before the runs) | result | verdict |
|---|---|---|
| 1. C2 holdout first try, six-parent mean >= 71.3% | **76.1%** (78.3, 77.9, 71.3, 75.8, 76.4, 77.0) | **pass** |
| 2. at most 256 updates, and at most half the research-loop sleep's updates on that parent | 256 on every parent; half the research loop's = 279 to 305 | **pass** |
| 3. no harm vs the pre-sleep model (harm_measure, every parent) | in_dist +0.12 to +0.82, no family fires on any parent | **pass** |
| 4. old skills up: pooled in_dist, sleep - pre-sleep, interval above 0 | **+0.52 [0.31, 0.74]** | **pass** |
| "through transfer" label (sleep - replay-only control above 0) | **-1.58 [-1.79, -1.37]** | **not shown**: "improved, not shown to come from the new skill" |
| proved wrong (harm on 3 or more parents) | harm on 0 parents | not proved wrong |

Claims (a) and (b) are met as the marks define them; claim (c) is met only as "old skills improved", not as transfer.

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

## Confirm: six parents (finished 10-09 9:20 AM ET; `confirm/`)

Parents s200-s205, each rebuilt into its N on the cloud CPU. Two arms per parent, run two at a time with 2 threads each:
- `fd`: the recipe above. The stop rule never ended a night early. It kept the update-224 state on s201, s202 and s205 and the final (256) state on the other three.
- `rp`: the replay-only control: the same 256 updates and the same skills rows as `fd`, with the day half removed (batch 512).

The holdout (`creative/data/c2rl/holdout.jsonl`, 512 questions) was read once per `fd` learner, after all of that parent's runs had finished. C2 test and labelled were never opened.
The container restarted at 8:08 AM ET on 10-09 and killed the s205 control at update 240 of 256. That run was restarted from scratch (`chainD.sh`); no other run was affected.

| parent | night: own + chain records | C2 DEV | C2 holdout | in_dist: N -> `fd` (harm) | `rp` in_dist | B2 in_dist |
|---|---|---|---|---|---|---|
| s200 | 362 + 614 | 79.3 | 78.3 | 88.12 -> 88.24 (passes) | 90.22 | 90.19 |
| s201 | 190 + 732 | 81.6 | 77.9 | 88.25 -> 89.04 (passes) | 90.28 | 90.38 |
| s202 | 178 + 714 | 71.9 | 71.3 | 87.54 -> 88.37 (passes) | 89.79 | 90.15 |
| s203 | 311 + 651 | 80.1 | 75.8 | 87.60 -> 88.16 (passes) | 89.84 | 90.31 |
| s204 | 296 + 642 | 79.3 | 76.4 | 87.79 -> 88.13 (passes) | 89.49 | 89.71 |
| s205 | 275 + 646 | 78.1 | 77.0 | 87.91 -> 88.43 (passes) | 90.24 | 90.24 |
| mean | | 78.4 | **76.1** | 87.87 -> 88.39 | 89.98 | 90.16 |

Report only, against the raw B2 parent (`confirm/vs_b2.json`; six-parent means of the rule-from-examples families named in the task):

| family | B2 | N (after the parent build) | `fd` (after sleep) | `rp` (replay only) |
|---|---|---|---|---|
| fewshot_number_rule | 35.5 | 15.2 | 17.8 | 36.2 |
| seq_next | 83.6 | 69.9 | 71.0 | 80.8 |
| rule_apply | 90.6 | 80.2 | 82.8 | 89.7 |
| in_dist (34 families) | 90.16 | 87.87 | 88.39 | 89.98 |

harm_measure vs B2: N fails on all six parents (2 to 6 families fire); `fd` fails on all six (3 families fire on each); `rp` fires only seq_next, on 2 parents.

### How to read it

- *Shown (six parents, holdout):* after the sleep, C2 first try on the holdout is 76.1% after 256 updates. Before the sleep, N scored 0.4 to 3.1% on the DEV questions; N's holdout was not read. That is above the research-loop sleep's 71.3%, which used about 560 to 610 updates on the same kind of night.
- *Shown:* against the model it starts from, the sleep loses nothing on old skills. No family fires on any parent, and in_dist rises by +0.52 [0.31, 0.74] pooled.
- *Shown:* the old-skill rise is not from the new skill. The replay-only control, with the same updates and the same skills rows and no C2 rows, rises much more: +2.11 [1.88, 2.32] over N, and 1.58 points above the sleep. The control trains on exactly the same skills rows. In the sleep those rows share every update with 512 C2 rows, so each one carries half the weight per step.
- *Shown:* the rule-from-examples damage the task describes comes from the parent build (B2 to N: warm-up and stepping stones, researcher-designed, before any sleep), not from this sleep. The sleep claws back about 0.5 of the build's 2.3 points; the replay-only control claws back almost all of it (89.98 vs B2's 90.16, with fewshot_number_rule fully back).
- *Suggested:* fresh skills replay repairs old skills, and sharing each update with the C2 rows (half the weight per skills row, and maybe some interference) is what limits the repair. A sleep with a larger skills share, or more updates, may get both the C2 gain and the full repair. This is the mix-ratio question Ben asked about. *Untested.*
- *Suggested:* fresh dreams are what make 256 updates enough. At the same 128 updates they beat re-read rows by +7.4 and +5.5 on two parents (Screen A), but the research-loop sleep itself was not re-run on these parents, so 76.1 vs 71.3 is not a paired comparison.
- Caveats:
  - The 71.3% is the research loop's stored number from its own copies of these parents (rebuilt here as near-copies), not a paired baseline. PC job 1 would re-run it on the same N.
  - The research-loop sleep's real harm is still unmeasured.
  - Update counts compare training steps of equal size (1,024 rows); night sampling is about the same for both and is not counted; FLOPs were not counted on this CPU.
  - The holdout had been read 14 times by the research loop before this; here each learner read it once.

### Plain summary for Ben

The model now learns the new puzzle kinds in one night of 256 practice steps, and gets 76% of fresh puzzles right on the first try, better than the old
sleep's 71% with fewer than half its steps. It does not forget anything it knew the evening before. Its old skills even go up a little, but that
comes from the practice rows mixed into the night, not from the new puzzles: practising old skills alone helps them four times as much. The
old-skill damage you saw before comes from the warm-up steps that build each starting model, and plain practice repairs it almost completely.
