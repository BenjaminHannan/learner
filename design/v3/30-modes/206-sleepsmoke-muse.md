# 206 — Sleep smoke mark for merges (Muse)

## Problem

`scripts/fable_marks123_all.py` sets `cfg["sleep_threshold"] = 100000` and
its SLEEP suite returns `skipped=True, pass=True` on every branch. Merges
138g/138h/138i therefore ship a sleep path (the 145 retrofit:
`Sleep145Reasoner` + `Sleep145Sleeper` via `retrofit_sleep145`) that no
registered mark ever fires. A broken sleeper, a dead threshold, or a
word-file regression would all pass marks123 green.

## Design (harness only, additive)

`scripts/fable_sleepsmoke206.py` treats the agent as a black box: it reads
the agent script + config, writes a scratch config copy (`state_dir` =
fresh run dir, `sleep_threshold` = 75, all `sleep*_seed` = 1), boots the
real daemon subprocess (`--idle-seconds 30`), and replays the frozen
exp-104 world (builders imported read-only from
`fable_sleep104_drive`: 50 teaches, 20 episode asks, 5 fillers, 5
new-people probes) plus one broken-chain probe (`Who is Q99's maternal
grandmother?`, never taught). Threshold 75 fills the log exactly at the
last filler, so sleep fires mid-run exactly as in exp 104. It never edits
the agent, never touches the repo-root notebook/, and never averages:
every count is reported per run.

## What it checks per run

Sleeps logged; install (`maternal_grandmother` in `sleep145-words.json` +
episodes); new-people probes right/wrong/abstain; broken-chain verdict
(must abstain — an invented grandmother is a wrong); taught facts
overwritten by sleep (must be 0, via the 104 `sleep_overwrites` read);
taught recall (50/50, dupes 0); wall seconds. Bars: reproduce 145's sealed
seed numbers (install, 20 episodes, 5/5, 0 wrong, 50/50, 0 overwrites),
broken-chain abstains, each run < 300 s Mac CPU.

## Result

Both merges pass with identical numbers (138i 98.9 s, 138h 208.4 s;
details in `artifacts/fable-sleepsmoke206-20260922/RESULTS.md`). Had 138i
diverged, the protocol records a registered FAIL with a diagnosis and no
agent patch — the smoke mark diagnoses, it never fixes.

## For future merges

Run the one-liner in RESULTS.md against the new agent+config after sealing
a PASSMARKS that copies the expected numbers. Cost is ~2–4 min Mac CPU.
Known limits: clean seed only (no Z4 kill-9 / Z5 noise, no grown slots);
extend the frozen case file rather than complicating the driver.
