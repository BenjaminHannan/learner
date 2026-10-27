BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 75 minutes
LABEL: sol-cloud-capability256-v1-s0-loop-train
PUSH: artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v1/execution-sol-cloud-capability256-v1-s0-loop-train

First approved arm of the sealed capability256 serial fit. Use the exact pinned Mac relay/spec below; it performs actual watcher pickup verification, native package/import/help smoke, fresh process/GPU/disk/resource gates, then the runner's own release/inventory gates before any model or optimizer import. Do not retry or run other arms concurrently. Preserve every receipt and PC original; any overflow raw evidence stays on PC for later read-only collection.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 4500 /usr/bin/python3 -B artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v1/MAC-LAUNCH-v1.py --spec artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v1/SPEC-s0-loop-v1.json --spec-sha256 627ce619df1e901782361b34dee84a1d130203784986aed105f89d3829bc62c4
```
