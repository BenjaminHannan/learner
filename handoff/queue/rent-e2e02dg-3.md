BASH-ONLY: yes
GPU: rent. LOAD-LIGHT: yes
DISK: 1
Build-notes chat (Claude) job, acting for Month-end on 0.2d's notes slot only (design/v3/30-modes/02d-gates-ADDENDUM-52.md, sealed in commit ee96d8f04 before any check ran). Attempt 3 of the same rental job: attempt 1 (rent-e2e02dg-1, $0.08) stopped at the torch download on host 483833; attempt 2 (rent-e2e02dg-2, $0.04) stopped at the selftests because design/v3/60-listener was not sent. Both before any check; both destroyed after a checked copy-back. This attempt sends it (the exact rental tree was tested in the cloud) and keeps the whole job under $4. ONE vast rental under Ben's standing rule (this job's money stop $2, cap $4): an RTX 5090 first. The Mac reads G's adapter at ~/premonition-models/rd378g-vast-adapter and sends a copy (never moves or changes it) with the pinned code; the rental rebuilds G from MiniCPM5-1B (the only model download) and runs checks W1, W2, W2b, W3 and the report-only rows; W/ is copied back and checked against the rental's manifest; the instance is destroyed only then, otherwise stopped. A detached watchdog stops (never destroys) it if this job ends early. No training. Never reads keys or auth files (the vastai CLI reads its own config); kills nothing. Kit: artifacts/claude-e2e02dg-20260927/kit/ (mac.sh here, box.sh on the rental).
```bash
set -u -o pipefail
PIN=32b700b63fb213105fdc23fe7cac741444885526
W=$(pwd)
git fetch -q origin main && git fetch -q origin +refs/heads/builder-outbox:refs/remotes/origin/builder-outbox || { echo "STOP: git fetch failed"; exit 4; }
git cat-file -e "$PIN^{commit}" || { echo "STOP: $PIN not fetched"; exit 4; }
D=$(mktemp -d)
trap 'rm -rf "$D"; [ -e "$D" ] && echo "tree NOT removed: $D" || echo "tree removed: $D"' EXIT
git archive "$PIN" scripts design/v3/30-modes/02d-gates-ADDENDUM-52.md design/v3/60-listener artifacts/claude-e2e02dg-20260927 artifacts/claude-rd378g-20260926 | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
bash "$D/artifacts/claude-e2e02dg-20260927/kit/mac.sh" "$D" "$PIN" "$W" vast3 483833 0.12
```
PUSH: artifacts/claude-e2e02dg-20260927/vast3
