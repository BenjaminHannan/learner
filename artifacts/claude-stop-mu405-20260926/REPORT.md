# STOP rent-mu405 — duplicate rental stopped by owner (2026-09-26)

Owner order (director, 2026-09-26 18:58 UTC task issue; stop executed 2026-09-26 ~18:53–18:54 UTC):
the registered mu-405 run is already running elsewhere, so this rental is a duplicate.
Its output is NOT kept or scored. Nothing was copied back.

## 1. Local processes (`ps -axo pid,ppid,etime,command`, filter `rent-mu405` / `claude-madeup-mu405`)

| PID | PPID | elapse at listing | command (truncated) | action |
|-----|------|-------------------|---------------------|--------|
| 86300 | 86298 | 09:04 | bash …/handoff/kit/mimo/rungo4.sh …/premonition-watch/queue/rent-mu405.md | `kill` 18:53:10 UTC — dead on re-check, no `kill -9` needed |
| 86338 | 86300 | 09:03 | /usr/local/bin/opencode run … --title mimo:rent-mu405.go1.86300 … (label claude-madeup-mu405) | `kill` 18:53:10 UTC — dead on re-check, no `kill -9` needed |
| 90783 | 90749 | — | opencode run … --title mimo:000-stop-mu405.go1.90749 … (THIS stop task; matches filter only via its own task text) | NOT killed (self) |
| 90749 | 90747 | — | bash …/rungo4.sh …/queue/000-stop-mu405.md (this stop task's launcher) | NOT killed (self chain) |

- `ps -p 86300 -p 86338` after 35 s: no such processes (2/2 stopped with plain `kill`).
- Never touched pythonw 13036 or anything else.
- Orphan note: PID 90987 (child of 86338, `/bin/zsh -c sleep 120; vastai show instance 52800315 …`, reparented to PPID 1) does NOT contain either filter string, so per the exact-PID rule it was left alone. It is a read-only status poll that self-exits.

## 2. Vast.ai rental (key only via `$(cat ~/.config/vastai/vast_api_key)`, never printed)

- Label searched: exactly `claude-madeup-mu405`. Exactly 1 live instance matched.
- Instance id: **52800315** (task expected 52799415 — that id does not exist; see deviation 2).
- GPU: RTX 5090, South Korea, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime.
- Pre-destroy read (18:53:56 UTC): actual_status `running`, cur_state `running`, dph_total **$0.49444444**/h (base $0.46666667), start_date 1790448633.499 = **2026-09-26 18:50:33 UTC**, duration **202.93 s = 0.05637 h**, metered cost **$0.0279 (~$0.03)**.
- `echo y | vastai destroy instance 52800315` → "destroying instance 52800315." (~18:54:05 UTC).
- Confirmed gone (18:54:21 UTC): `vastai show instances` lists 4 instances, none labelled claude-madeup-mu405; `vastai show instance 52800315 --raw` returns `{"instances": null}`.
- Nothing copied back, per task.

## 3. Timestamps (`date -u`)

- kill issued: Sat Sep 26 18:53:10 UTC 2026
- pre-destroy instance read: Sat Sep 26 18:53:56 UTC 2026
- destroy confirmed: Sat Sep 26 18:54:21 UTC 2026
- Disk check at start: 55 GB free (`df -g /`). `uptime` load high but stop task is DISK 0 / trivial.

## 4. Deviations (4)

1. OPUS-RULES brief absent: `/private/tmp/claude-502/…/76c622f5-…/scratchpad/briefs/OPUS-RULES.txt` does not exist (that session's `scratchpad/` is empty; worktree has no `scratchpad/briefs/`). Proceeded under the rules restated in the task text (additive-only, append-only ledger, fictional names, no secrets, disk 0, exact-PID kills).
2. Expected instance id 52799415 does not exist. The ONE live instance labelled exactly `claude-madeup-mu405` is **52800315**. Destroyed 52800315.
3. Orphaned read-only poller PID 90987 (see §1) left running per the exact-PID rule; self-exits.
4. Cost/hours are metered values at last pre-destroy read (202.93 s → 0.056 h → ~$0.03); final billed total may round up slightly. No output kept or scored, per task.

## 5. Ledger

Appended via `cat >> artifacts/fable-predictions-ledger.md`:
`- 2026-09-26 18:55 UTC rent-mu405 STOPPED by owner (duplicate of CPU run); 0.056 h, ~$0.03.`
