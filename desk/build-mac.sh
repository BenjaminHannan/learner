#!/usr/bin/env bash
# Build "Premonition.app" on an Apple-silicon Mac and install it to /Applications.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "build-mac.sh must run on macOS arm64 (this is $(uname -s) $(uname -m))." >&2
  exit 1
fi

# An x64 Node (Rosetta) silently produces no app; prefer Homebrew's arm64 Node.
if [[ "$(node -p process.arch 2>/dev/null)" != "arm64" && -x /opt/homebrew/bin/node ]]; then
  export PATH="/opt/homebrew/bin:$PATH"
fi
if [[ "$(node -p process.arch 2>/dev/null)" != "arm64" ]]; then
  echo "Node must be arm64 (found: $(command -v node) $(node -p process.arch 2>/dev/null))." >&2
  exit 1
fi

echo "==> npm ci"
npm ci

mkdir -p build
EXTRA=()
if command -v swiftc >/dev/null 2>&1 && [[ -f helper/deskhelper.swift ]]; then
  echo "==> compiling deskhelper"
  # the Info.plist is linked into the binary so the helper has its own microphone / speech usage strings (Call Glim)
  swiftc -O helper/deskhelper.swift -o build/deskhelper -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker helper/deskhelper-Info.plist
  EXTRA=(--extra-resource=build/deskhelper)
else
  echo "WARNING: swiftc or helper/deskhelper.swift missing; building without screen control (install Xcode command line tools: xcode-select --install)." >&2
fi

# The sleep trainer (a Python package, no model, no Python) and the dream checker ride along as resources (resources/sleepmlx,
# resources/sleepmode): the built-in Mac sleeps with them (src/sleepwin.js). SLEEPMODE_SRC: the folder holding sleepmode/.
STAGE=build/stage; rm -rf "$STAGE"; mkdir -p "$STAGE"
if [[ -d ../sleepmlx ]]; then
  echo "==> staging sleepmlx"
  (cd .. && tar -c --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' sleepmlx) | tar -x -C "$STAGE"
  EXTRA+=(--extra-resource="$STAGE/sleepmlx")
else
  echo "WARNING: ../sleepmlx not found; a Mac without the assistant will not be able to sleep." >&2
fi
SLEEPMODE_SRC="${SLEEPMODE_SRC:-$HOME/learner-ops/sleepmode/app}"
if [[ -d "$SLEEPMODE_SRC/sleepmode" ]]; then
  echo "==> staging the dream checker (sleepmode)"
  (cd "$SLEEPMODE_SRC" && tar -c --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' --exclude='*.bak-*' sleepmode) | tar -x -C "$STAGE"
  EXTRA+=(--extra-resource="$STAGE/sleepmode")
else
  echo "NOTE: $SLEEPMODE_SRC/sleepmode not found; sleep will run without the dream check (the morning summary says so)." >&2
fi

echo "==> packaging"
rm -rf build/app
# The bundle id MUST stay what it was when the app was called "Premonition Desk": packager derives it from the app name
# ("com.electron." + lowercased name), and macOS ties the Accessibility / Screen Recording grants to it.
APP_BUNDLE_ID="com.electron.premonition desk"
npx @electron/packager . "Premonition" \
  --app-bundle-id="$APP_BUNDLE_ID" \
  --platform=darwin --arch=arm64 --out=build/app --overwrite --icon=assets/icon.icns \
  --extend-info=assets/Info.extra.plist \
  --ignore='^/(build|test|docs|reviews|scripts|vendor|dist|README\.md|DESIGN\.md|build-mac\.sh|build-mac-cloud\.sh|build-win\.sh|build-win\.ps1)($|/)' \
  --ignore='^/helper($|/)' \
  ${EXTRA[@]+"${EXTRA[@]}"}

APP="build/app/Premonition-darwin-arm64/Premonition.app"
[[ -d "$APP" ]] || { echo "Packaging produced no app at $APP." >&2; exit 1; }
echo "==> ad-hoc codesign"
codesign --force --deep -s - "$APP"
# An ad-hoc signature's default designated requirement is its cdhash, which changes on every build, so macOS dropped the
# Accessibility / Screen Recording / Microphone grants after each update. Pin the requirement to the bundle id instead
# (inner deskhelper first, then the app, so the app's seal covers the re-signed helper).
HELPER_BIN="$APP/Contents/Resources/deskhelper"
if [[ -f "$HELPER_BIN" ]]; then
  codesign --force -s - -i com.premonition.deskhelper -r='designated => identifier "com.premonition.deskhelper"' "$HELPER_BIN"
fi
codesign --force -s - -r="designated => identifier \"$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist")\"" "$APP"
codesign --verify --deep --strict "$APP"

# INSTALL_DIR: where the app goes (default /Applications); point it at a temp folder to build without installing.
INSTALL_DIR="${INSTALL_DIR:-/Applications}"
echo "==> installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/Premonition.app"
cp -R "$APP" "$INSTALL_DIR/"
if [[ "$INSTALL_DIR" == /Applications && -d "/Applications/Premonition Desk.app" ]]; then
  echo "NOTE: the old \"Premonition Desk.app\" is still in /Applications. It can be removed once Premonition works (not deleted automatically). Your settings and chats were copied over on first launch; the old data folder stays as a backup."
fi
echo "Done. Open Premonition from $INSTALL_DIR (first launch: right-click > Open if macOS complains)."
