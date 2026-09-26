Resuming — picking up the prior run and checking for sealed work.
No explicit task text was included — I'm hunting for the unfinished experiment.
No task body arrived — only the RESUME wrapper.

Inspected worktree `card-experiment-handoff-7c5b27` (at `996b9348e`):

- Staged, uncommitted: 88 files — `claude-brd7`, `claude-e2e02c`, `claude-e2e02c-dev`, `claude-brd5/6`, `blurt2/4/5s`, `dl1`, `tgt5`, `lis319c` RESULTS + raw JSON, plus 2 new lines in `artifacts/fable-predictions-ledger.md` (`rent-bm391` BUDGET-STOP, `rent-brd7` NOT SHOWN). Did not commit or edit.
- Untracked: 243 `scripts/claude_*` files, `runs/`, `scratchpad/`, `notebook/`, `data/` — left untouched.
- Sealed artifacts: existing `PASSMARKS.md`/`SEAL.sha256.txt` under `artifacts/` not edited. No `shasum -c` run yet — needs the target exp name.
- No queue at `scratchpad/mimo/queue/`; `handoff/HANDOFF.md` is Sep-22 director handoff (already merged to main in `7c0216220`), not the cut-off task.

Cannot continue from “first unfinished step” or avoid duplicating ledger predictions without the actual task text (exp id / prefix / PASSMARKS path).

Paste the task again and I’ll resume from the seal check (`shasum -a 256 -c` from repo root) within the 90 min.
