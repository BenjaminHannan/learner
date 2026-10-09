#!/bin/bash
# One-time setup of the pc-operator worker on Ben's Mac. Run it in Terminal (it asks for the
# environment key with hidden input, so the key never lands in a chat or a file):
#     bash ops/managed-agents/mac/setup.sh
# Safe to rerun: it refreshes the scripts and restarts the worker, and keeps the stored key.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OPS="$HOME/learner-ops"
PLIST="$HOME/Library/LaunchAgents/com.learner.pc-worker.plist"

mkdir -p "$OPS/bin" "$OPS/worker/status" "$OPS/worker/log"
cp "$HERE/bin/"* "$OPS/bin/"
chmod +x "$OPS/bin/"*
touch "$OPS/worker/log/actions.md"

if ! command -v ant >/dev/null 2>&1; then
    echo "Installing the ant CLI with Homebrew..."
    brew install anthropics/tap/ant
    xattr -d com.apple.quarantine "$(brew --prefix)/bin/ant" 2>/dev/null || true
fi
ant --version

if ! security find-generic-password -s learner-pc-worker -a env-key >/dev/null 2>&1; then
    read -r -p "Environment ID from the Console (env_...): " env_id
    security add-generic-password -U -s learner-pc-worker -a env-id -w "$env_id"
    echo "Paste the environment key (sk-ant-oat01-...) when asked for the password, twice:"
    security add-generic-password -U -s learner-pc-worker -a env-key -w
fi

if [ ! -d "$OPS/status-repo/.git" ]; then
    url="$(git -C "$HERE" remote get-url origin)"
    git init -q "$OPS/status-repo"
    git -C "$OPS/status-repo" remote add origin "$url"
    if git -C "$OPS/status-repo" fetch -q --depth 1 origin pc-status 2>/dev/null; then
        git -C "$OPS/status-repo" checkout -q -B pc-status FETCH_HEAD
    else
        git -C "$OPS/status-repo" checkout -q --orphan pc-status
    fi
fi

echo "Checking that the Mac reaches BensPC..."
"$OPS/bin/pc-check" | head -5 || echo "BensPC did not answer; the worker still starts and will report it."

sed "s|__HOME__|$HOME|g" "$HERE/com.learner.pc-worker.plist" > "$PLIST"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
sleep 5
tail -n 5 "$OPS/worker.log" 2>/dev/null || true
echo "Worker started. Log: $OPS/worker.log"
