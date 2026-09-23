Urgent rescue — auditing the dead 5090 and stopping the bleed.
Found the stuck builder and dead rental — now gathering billing and instance details.
CLI ready and dead instance confirmed — now building the rescue record and cleanup.
Dead box destroyed — now stopping the stranded builder.
Builder stopped — now finalizing costs and ledger.
All rescue steps done — final verification.
Rescue complete. `vastai` CLI installed via `uv tool install vastai` (was missing); key never printed, CLI used default key file.

1. `vastai show instances --raw` → 1 instance, table written to `runs/000-vast-rescue/instances.txt` (no secrets, secret-scan clean):
```
id | gpu | actual_status | cur_state | public_ipaddr | reliability | dph | label
52276877 | 1x RTX 5090 | offline | running | 180.189.55.38 | 0.8612003 | 0.48518518518518516 | None
count=1
```

2. Destroyed by exact id (matched IP 180.189.55.38 AND actual_status=offline; cur_state=running but not healthy):
- `vastai destroy instance 52276877 -y` → exit 0
- confirm `vastai show instances --raw` → `[]` (0 instances)
- logged in `instances.txt` destroy log. Earlier contracts 52276394/52276603 already gone (count was 1).

3. `own-m1-train` builder:
- found PIDs 23817 (rungo4.sh own-m1-train.md) → 23847 (opencode) → 27733 (zsh sleep/ssh to dead 36876) → 27734 (sleep 105)
- `kill 27734 27733 23847 23817` → `pgrep -fl own-m1-train` exact gone; new `own-m1b-train` (28140/28173) and `own-m1n-train` (28179/28208) left untouched
- `~/premonition-watch/queue/own-m1-train.running` already removed by watcher (now `own-m1-train.exit` rc=143). Verified absent.

4. Ledger appended via `cat >> artifacts/fable-predictions-ledger.md`:
- per-instance billing unreadable (`/invoices` only stripe top-ups, `/users/current` credit 6.3913 balance 0 unchanged), so estimate: start 2026-09-23T18:29:42Z, destroyed 18:41Z, alive ~677s (11.28min) x $0.485185/hr = ~$0.09

PUSH ready: `runs/000-vast-rescue/instances.txt` `artifacts/fable-predictions-ledger.md` (git status shows M ledger + ?? runs/)

RESCUED 52276877
