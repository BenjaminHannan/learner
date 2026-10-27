---
name: research-loop
description: Autonomous, research-driven improvement of a model or codebase toward a plain-English goal, such as "new skills shouldn't overwrite old ones", "make training faster" or "raise accuracy on X". Researches the literature online, turns the goal into a locked benchmark with a hidden holdout, measures baselines and noise, then runs an overnight experiment loop (Karpathy's autoresearch loop, upgraded with a strategy bandit, fork-on-plateau, noise-aware keep/discard and rationed holdout checks) that commits only real improvements. Use this whenever the user wants Claude to go figure out and actually implement how to make their model, training setup, algorithm or code achieve a goal by running experiments, mentions autoresearch, the Karpathy loop or running experiments overnight, or says something like "research how to do X and make it work". Not for literature reviews or wiki write-ups that involve no experiments.
---

# Research loop

You are running a small research lab on the user's machine: read the literature, design the experiment, then run it for hours and keep only changes that are really better. The loop itself is simple: edit, run, measure, keep or revert. Whether it produces anything depends on what surrounds it:

- a metric that actually captures the goal, so progress on the number is progress on the goal
- a holdout the loop never sees, so dev-set luck and overfitting get caught
- a measured noise floor, so a lucky seed doesn't count as a win
- a steady supply of good ideas from the literature, so the loop isn't just random search

On ML-research benchmarks the leading agent designs, plain autoresearch included, score within noise of each other. The environment around the agent is what separates useful runs from wasted nights. Most of this skill is about building that environment well.

The bundled harness `scripts/loop.py` enforces the mechanical parts so they don't depend on your judgment in the moment. It runs every evaluation itself, compares against measured noise, commits or reverts, rations holdout checks, chooses the next strategy, and keeps a short summary. It uses only the Python standard library and works on Windows, macOS and Linux.

## Phases

0. Intake: repo, hardware, goal
1. Research: literature before design
2. Benchmark: the goal becomes a locked metric plus a holdout
3. Baselines and noise
4. The loop, until the budget or deadline
5. Wrap-up: final holdout check and report

Don't rush phases 1 to 3. An hour spent there decides whether the next ten hours produce anything.

## Phase 0: Intake

Look before asking:
- How the project trains and evaluates, how long one run takes, and where it writes outputs.
- Hardware: GPU and free VRAM (`nvidia-smi`), free disk space, and whether anything else is using the GPU.
- It must be a git repo with a clean tree. Commit or stash the user's work first.

Restate the goal as a question an experiment can answer. "Stop new skills overwriting old ones" becomes: "after training on tasks A, then B, then C, how much of A's accuracy survives, without hurting how well C is learned?"

Settle these in one message if the user is present. If they are away, choose sensible defaults and write them under "Assumptions" in `program.md`.
- Per-trial time budget. Default 5 to 10 minutes: long enough to rank methods, short enough for many trials.
- Total budget or deadline, e.g. "until 7am".
- What code may change, and what is off-limits.
- Hard limits: VRAM, disk, no paid APIs, and so on.

Then initialize, using the Python the project uses:

```
python <this skill's directory>/scripts/loop.py init --goal "<goal in the user's words>"
```

This creates `.research/`, which is excluded from git so reverts never touch it. It also creates a `research/...` branch, so the user's own branch is never modified, and copies the harness to `.research/loop.py`. From then on, run `python .research/loop.py <command>`. Fill in `.research/program.md`.

If the user wants this to run unattended, their session must be allowed to run the eval and git commands without asking. Mention this once during intake.

## Phase 1: Research

Do this before building anything. Most goals are a known problem with a name, standard metrics, strong simple baselines and known failure modes. For example, "overwriting old skills" is catastrophic forgetting, measured with average accuracy and backward transfer, and plain replay is famously hard to beat. If you build the benchmark before reading, you reinvent a worse one and re-run ideas that are already known to fail.

Search from several angles, in parallel with subagents if you have them (one angle each):
- the names of the problem
- recent surveys
- standard benchmarks and metrics
- the simple baselines papers struggle to beat
- recent methods that have code
- negative results and failure analyses
- methods that fit the user's constraints, such as a single GPU or a small model

Read the full paper for anything you will implement, because the mechanism and hyperparameters matter.

Write the results into two files:
- `.research/notes.md`: for each source, the link, what it found, and why it matters here.
- `.research/hypotheses.md`: a ranked queue of cards, using the template in the file. Aim for 10 or more, mixing cheap tweaks with bold ideas.

Never cite something you didn't read, and mark abstract-only sources as such. More detail is in `references/research-phase.md`.

## Phase 2: Benchmark

Read `references/benchmark-design.md` now. It covers turning a goal into metrics, a worked forgetting example, holdout design, noise, and the leakage and reward-hacking checklist. You are building:

- **Eval command(s)** that print `metric_name: value` for the primary metric and every guard, take the seed via `{seed}` or the `RL_SEED` env var, and exit non-zero on failure.
- **A dev split** for the loop, and **a holdout split** that tests the same ability on unseen instances. Only the harness's `confirm` ever runs the holdout.
- **Guard metrics** that must not regress, so the primary metric can't be gamed by trading away something that matters.
- **A fixed per-trial budget**, so trials are comparable.
- **Outputs written outside the repo** or to gitignored paths. Checkpoints never go into git.

Commit the benchmark, then lock it:

```
python .research/loop.py setup --metric acc_all --direction max \
  --dev-cmd "python eval.py --split dev --seed {seed}" \
  --holdout-cmd "python eval.py --split holdout --seed {seed}" \
  --lock eval/ data/holdout/ --guard "new_task_acc>=baseline-0.02" \
  --editable src/ --seeds 2 --calib-seeds 5 --timeout-min 20 --deadline 07:00
```

Locked paths are hashed, and any change to them halts the loop. `--seeds` is the number of dev runs per trial: more is slower but more reliable, and 2 to 3 is typical.

If the user is present, show them the spec in 5 to 8 lines and get a yes before continuing: what is measured, the guards, dev versus holdout, the per-trial budget and the total budget. This is the one decision that determines whether the night is useful.

## Phase 3: Baselines and noise

Implement reference points as flags or configs so they run without editing code:
- the floor, e.g. naive sequential fine-tuning
- the strong simple baseline from the research, e.g. replay
- the ceiling, e.g. joint training on everything at once

Run each one with `python .research/loop.py reference --name replay --cmd "..." --holdout-cmd "..."`.

Then run `python .research/loop.py calibrate`. It evaluates the committed code over several seeds on dev and holdout, and sets the baseline, the noise floor and the first incumbent.

Check two things before looping, and fix the benchmark if either fails. Looping on a broken benchmark wastes the night.
- **Ordering:** floor < strong baseline < ceiling should hold under the short per-trial budget. If it doesn't, the budget is too short to rank methods, so lengthen it or shrink the problem.
- **Sensitivity:** the printed minimum detectable improvement should be smaller than the effects you hope to find. If not, use more eval examples or more seeds.

The gap between the current code and the ceiling is the room you have to work in.

## Phase 4: The loop

Each iteration:

1. Run `python .research/loop.py next`. It picks the strategy arm and tells you what is due.
2. If a **research refresh** is due, re-read `summary.md`. Search for why the kept changes worked (adjacent ideas) and why the failures failed. Add and re-rank cards, retire dead ones, then run `refreshed --note "<what changed>"`.
3. If a **holdout confirm** is due, run `confirm`.
4. Make **one** change in the spirit of the arm. One idea per trial is what makes results attributable.
5. Run `python .research/loop.py trial --hypothesis "<what you changed>" --predict "<expected direction and size>" [--hyp H3] [--source <url>]`. Write the prediction before you see any result. The harness then runs dev on the trial seeds and, if the change passes, on fresh seeds too. It then commits or reverts, and saves the diff to `.research/patches/` either way.
6. Update the card's status and trial id in `hypotheses.md`, then go back to step 1.

The five arms:

| arm | what to do |
|---|---|
| literature | implement the top untried card |
| tune | a small conservative change to the current best |
| bold | substantially redesign one component; most fail, which is expected |
| simplify | remove or ablate something; kept if not worse beyond noise and net lines go down |
| combine | merge two near-miss patches, or a near-miss with a card |

The harness chooses arms with a bandit (UCB), which rewards what has been working while still exploring. Every 5th trial it forces a switch away from the arm that produced the last win. After 8 trials without a win, it restricts itself to bold, literature and combine, and requires a research refresh. The design copies what an 8-day self-improvement run of a production research agent (Weco's AIDE2) discovered for itself: bandit selection over strategies plus forking the best candidate on plateaus beat greedy hill-climbing.

### Rules, and why

- **Keep going until `next` prints STOP.** Don't stop to report after a win; the user wants the night's result, not a play-by-play. Pause only for something irreversible or outside the agreed scope.
- **Never touch the locked eval, `.research/config.json` or `state.json`. Never run the holdout command or read holdout data yourself.** The holdout is the only honest check on whether dev gains are real, and every look at it leaks information. In Weco's study, about a quarter of rejected changes had scored better on the visible metric but not on hidden data.
- **Never report numbers yourself.** The harness measures, and your summaries quote its output.
- **Never commit by hand during the loop.** The harness commits wins. If HEAD moves, it refuses to run.
- **If you find a bug in the benchmark, don't exploit it.** Fix it, commit the fix, run `relock --reason "..."`, re-run the references and `calibrate`, and log the fix in `program.md`. Earlier results become a closed segment.
- **Crashes:** if the cause is an obvious slip, reapply the saved patch (`git apply .research/patches/NNNN-arm.diff`), fix it, and run it as the next trial. If the same direction crashes twice, move on. `summary.md` lists recurring error signatures when the crash rate climbs.
- **Memory:** start each iteration from `.research/summary.md`, or run `status`, rather than scrolling back through old output. After a context compaction or in a fresh session, `status` has everything you need to continue.
- **Resources:** delete per-trial checkpoints, stay inside the disk and VRAM limits, and run one eval at a time on a single GPU. If the eval leaves files in the repo, the harness excludes them from git and warns you; move those outputs out of the repo.

## Phase 5: Wrap-up

When `next` prints STOP, run `confirm --final`, then `report`. Write the Findings section at the top of `.research/report.md`, between the findings markers:
- The headline: holdout result versus the floor, the strong baseline and the ceiling, with noise.
- Each kept change, and the mechanism that plausibly explains it.
- Notable failures, which are results too.
- Caveats: holdout checks used, noise, budget, anything assumed.
- The next hypotheses worth testing.

Leave the repo on the research branch at the last holdout-confirmed commit, and don't merge into the user's branch. Tell the user the outcome in a few lines and where the report is.

## Harness reference

| command | purpose |
|---|---|
| `init --goal TEXT [--no-branch]` | create `.research/`, the research branch and templates |
| `setup --metric M --direction max\|min --dev-cmd C --holdout-cmd C --lock P... [--guard G] [--editable P...] [--seeds N] [--calib-seeds N] [--timeout-min X] [--max-trials N] [--max-hours H] [--deadline HH:MM]` | lock the benchmark |
| `reference --name N [--cmd C] [--holdout-cmd C] [--seeds N]` | measure a floor, baseline or ceiling |
| `calibrate` | baseline, noise floor and first incumbent |
| `next` | strategy for the next trial, plus anything due, or STOP |
| `trial --hypothesis T --predict T [--hyp ID] [--source URL] [--arm A --override WHY]` | test the current uncommitted change |
| `confirm [--final]` | rationed holdout check; reverts to the last confirmed commit on regression |
| `refreshed --note T` | record a research refresh |
| `relock --reason T` | re-hash the eval after a deliberate fix (starts a new segment) |
| `status` / `report` | compact summary / full report |

Advanced `setup` flags, with their defaults: `--z 1.0` (noise multiplier for a keep), `--holdout-every 3` (keeps between holdout checks), `--holdout-cap 12`, `--fork-every 5`, `--refresh-every 10`, `--plateau 8`, `--explore 0.2`, `--min-delta 0`.

If `scripts/loop.py` is missing, for example because only this file was installed, write a small harness implementing the same protocol before starting:
1. It runs the dev eval itself across seeds.
2. It keeps a change only if the improvement exceeds the noise margin and holds on fresh seeds, and otherwise reverts with git.
3. It rations holdout checks, and reverts to the last confirmed commit on regression.
4. It hash-locks the eval files.
5. It logs every trial and maintains a short summary.

Don't run the loop without it. Self-judged keep/discard decisions are how these loops fool themselves.
