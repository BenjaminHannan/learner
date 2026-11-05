#!/usr/bin/env bash
# One .dmg of Glim for someone else's Apple-silicon Mac (Nov 5, the "uncle" build). Nothing of Ben's goes in: run it on a clean
# `git archive` of desk/ (not on a working folder), so no settings, chats, notes, adapters or keys can ride along.
#   PATH=$HOME/learner-ops/node22/bin:$PATH OUT=/some/folder bash build-mac-friend.sh
# Needs vendor/eyes/glim-eyes-mmproj-f16.gguf (gitignored; see build-win.sh) and network for npm + the pinned llama.cpp archive.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${OUT:?set OUT to the folder for the .dmg}"
VERSION="$(node -p "require('./package.json').version")"
STAGE_APP="$(mktemp -d)/app"
FRIEND_BUILD=1 INSTALL_DIR="$STAGE_APP" bash build-mac.sh

APP="$STAGE_APP/Premonition.app"
DMGROOT="$(mktemp -d)/Glim"
mkdir -p "$DMGROOT"
cp -R "$APP" "$DMGROOT/"
ln -s /Applications "$DMGROOT/Applications"
cat > "$DMGROOT/Read me first.txt" <<'TXT'
Glim (the Premonition app) for a Mac with Apple silicon (M1 or newer) and at least 16 GB of memory.

1. Drag Premonition onto the Applications folder.
2. Open Applications and double-click Premonition. macOS will warn that it cannot check the app (it is not from the App Store).
   Click Done, then open System Settings > Privacy & Security, scroll down, click "Open Anyway" next to Premonition, and confirm.
   (On older macOS you can instead right-click Premonition > Open > Open.)
3. Glim sets itself up: it downloads its brain once (2 to 4.5 GB). Leave the Mac on and online until Glim says hi.

Glim's brain runs on this Mac; your chats stay on it. Glim goes online only to download its brain, for web searches and
pages you ask for, and to check for app updates.
TXT
mkdir -p "$OUT"
DMG="$OUT/Glim-$VERSION-mac.dmg"
rm -f "$DMG"
hdiutil create -volname "Glim" -srcfolder "$DMGROOT" -fs HFS+ -format UDZO -imagekey zlib-level=9 -ov "$DMG" >/dev/null
echo "Built $DMG"
shasum -a 256 "$DMG"
