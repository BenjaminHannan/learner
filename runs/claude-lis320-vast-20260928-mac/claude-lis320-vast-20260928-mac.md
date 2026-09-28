BASH-ONLY: yes
GPU: rent
LOAD-LIGHT: yes
DISK: 5
BUDGET: $4 total; one instance; stop work at $3.25 for copy-back reserve.
RELEASED: 2026-09-28T13:26:33Z. Ben's explicit completion order authorizes this rental without asking again.
One lis-320 rental: sealed DATA, unchanged training recipe, old Mac reader, one panel read per reader, manifest copy-back before destroy; else stop. ADDENDUM-14 and MOCK-TEST.json register the mechanics. This BASH-only job starts the detached Mac runner; the coordinator collects its END.json. Do not launch any old held lis-320 job. Never read keys or auth files. The panel is script-only, counts only. No LLM builder.
```bash
set -eu -o pipefail
W=$(pwd)
JOB=claude-lis320-vast-20260928-mac
A=artifacts/claude-lis320-20260926
OUTBOX=43f2691c2c01322ef3809434a9123ee0e1202838
git fetch -q origin main builder-outbox
PIN=$(git rev-parse origin/main)
for p in DATA.md SEAL-DATA.sha256.txt SEAL-EXECUTION.sha256.txt MOCK-TEST.json; do
  git cat-file -e "$PIN:$A/$p" || { echo "STOP: missing $p before rental"; exit 1; }
done
D=$(mktemp -d)
trap 'rm -rf "$D"' EXIT
git archive "$PIN" handoff/kit/lis320v | tar -xf - -C "$D"
bash "$D/handoff/kit/lis320v/start.sh" "$W" "$PIN" "$OUTBOX" "$JOB"
mkdir -p "$W/$A"
{ echo '# lis-320 rental start'; echo "UTC: $(date -u +%FT%TZ)"; echo "pin: $PIN"; echo "data outbox: $OUTBOX"; echo 'Final state: ~/premonition-watch/lis320-vast/END.json'; echo 'Rental cap $4; main marks untested until blind scoring.'; } > "$W/$A/RUN-START.md"
```
PUSH: artifacts/claude-lis320-20260926/RUN-START.md
