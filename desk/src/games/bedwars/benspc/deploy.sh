#!/usr/bin/env bash
# deploy.sh - Mac side. Copies benspc/ (with truthkit/) + deskhelper.exe to BensPC and verifies the sha256 of EVERY file after copying
# (remote copies have failed silently before). Does NOT run setup.ps1 and does NOT install any SSH key.
# usage: deploy.sh [--dry-run] [--dest 'C:/Users/benja/glim-bedwars']      (default dest is the real folder)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST='C:/Users/benja/glim-bedwars'
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --dest) DEST="$2"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done
case "$DEST" in
  C:/Users/benja/glim-bedwars*) ;;   # only our own folders (the real one or the glim-bedwars-dryrun scratch folder)
  *) echo "refusing dest outside C:/Users/benja/glim-bedwars*: $DEST" >&2; exit 2 ;;
esac
WIN_DEST="${DEST//\//\\}"
DESKEXE="$HERE/../../../../vendor/helper/deskhelper.exe"
# local file -> remote relative path
FILES=(
  "$HERE/glimtool.ps1|glimtool.ps1"
  "$HERE/bridge.ps1|bridge.ps1"
  "$HERE/bridge-launch.vbs|bridge-launch.vbs"
  "$HERE/bridge-task.xml|bridge-task.xml"
  "$HERE/launch-client.ps1|launch-client.ps1"
  "$HERE/setup.ps1|setup.ps1"
  "$HERE/runbook.json|runbook.json"
  "$HERE/RUNBOOK.md|RUNBOOK.md"
  "$DESKEXE|bridge/deskhelper.exe"
  "$HERE/truthkit/build.ps1|truthkit/build.ps1"
  "$HERE/truthkit/res/plugin.yml|truthkit/res/plugin.yml"
  "$HERE/truthkit/res/config.yml|truthkit/res/config.yml"
  "$HERE/truthkit/src/glim/tk/TruthKit.java|truthkit/src/glim/tk/TruthKit.java"
)
sha_local() { shasum -a 256 "$1" | awk '{print tolower($1)}'; }
# certutil works in cmd and in PowerShell, so the quoting of the remote default shell does not matter
sha_remote() { ssh "${SSH_OPTS[@]}" "$HOST" "certutil -hashfile \"$1\" SHA256" | sed -n '2p' | tr -d ' \r' | tr 'A-F' 'a-f'; }

SSH_OPTS=(-o ConnectTimeout=8 -o BatchMode=yes)
HOST=benspc
if [ "$DRY" = 1 ]; then
  for f in "${FILES[@]}"; do echo "would copy ${f%%|*} -> $DEST/${f##*|} and verify sha256"; done
  exit 0
fi
if ssh "${SSH_OPTS[@]}" -o HostName=10.0.0.188 benspc "echo ok" >/dev/null 2>&1; then SSH_OPTS+=(-o HostName=10.0.0.188); else echo "LAN route failed, using Tailscale (ssh benspc)"; fi
for d in bridge truthkit\\res truthkit\\src\\glim\\tk; do
  ssh "${SSH_OPTS[@]}" "$HOST" "cmd /c if not exist \"$WIN_DEST\\$d\" mkdir \"$WIN_DEST\\$d\"" >/dev/null
done
bad=0
for f in "${FILES[@]}"; do
  src="${f%%|*}"; rel="${f##*|}"
  [ -f "$src" ] || { echo "MISSING local file: $src" >&2; bad=1; continue; }
  scp -q "${SSH_OPTS[@]}" "$src" "$HOST:$DEST/$rel"
  want="$(sha_local "$src")"
  got="$(sha_remote "$WIN_DEST\\${rel//\//\\}")"
  if [ "$want" = "$got" ]; then echo "ok   sha256 $want  $rel"; else echo "FAIL sha256 mismatch for $rel (local $want, remote ${got:-none})" >&2; bad=1; fi
done
[ "$bad" = 0 ] && echo "deploy verified: every file matches." || { echo "deploy FAILED hash check" >&2; exit 1; }
