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
  # the Info.plist is linked into the binary so the helper has its own microphone usage string (Call Glim)
  swiftc -O helper/deskhelper.swift -o build/deskhelper -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker helper/deskhelper-Info.plist
  EXTRA=(--extra-resource=build/deskhelper)
else
  echo "WARNING: swiftc or helper/deskhelper.swift missing; building without screen control (install Xcode command line tools: xcode-select --install)." >&2
fi

# FRIEND_BUILD=1 (Nov 5, the "uncle" Mac): a package for someone else's Mac. No sleep trainer and no dream checker (sleep is off
# for the Nanbeige brain), no Bedwars/BensPC scripts; the Metal engine (vendor/llama) and Glim's eyes (vendor/eyes) ride inside;
# an Intel guard (helper/mac-launcher) becomes the front door. build-mac-friend.sh wraps this and makes the .dmg.
FRIEND_BUILD="${FRIEND_BUILD:-0}"
# The sleep trainer (a Python package, no model, no Python) and the dream checker ride along as resources (resources/sleepmlx,
# resources/sleepmode): the built-in Mac sleeps with them (src/sleepwin.js). SLEEPMODE_SRC: the folder holding sleepmode/.
STAGE=build/stage; rm -rf "$STAGE"; mkdir -p "$STAGE"
if [[ "$FRIEND_BUILD" == 1 ]]; then
  echo "==> friend build: no sleepmlx (sleep is off for the Nanbeige brain)"
elif [[ -d ../sleepmlx ]]; then
  echo "==> staging sleepmlx"
  (cd .. && tar -c --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' sleepmlx) | tar -x -C "$STAGE"
  EXTRA+=(--extra-resource="$STAGE/sleepmlx")
else
  echo "WARNING: ../sleepmlx not found; a Mac without the assistant will not be able to sleep." >&2
fi
# The local speech-to-text server (stt/lfm_stt.py, LFM3-Audio via mlx-vlm) rides along as resources/stt (src/stt.js).
if [[ -d stt ]]; then
  echo "==> staging stt"
  mkdir -p "$STAGE/stt" && cp stt/lfm_stt.py "$STAGE/stt/"
  EXTRA+=(--extra-resource="$STAGE/stt")
fi
SLEEPMODE_SRC="${SLEEPMODE_SRC:-$HOME/learner-ops/sleepmode/app}"
[[ "$FRIEND_BUILD" == 1 ]] && SLEEPMODE_SRC=/nonexistent
if [[ -d "$SLEEPMODE_SRC/sleepmode" ]]; then
  echo "==> staging the dream checker (sleepmode)"
  (cd "$SLEEPMODE_SRC" && tar -c --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' --exclude='*.bak-*' sleepmode) | tar -x -C "$STAGE"
  EXTRA+=(--extra-resource="$STAGE/sleepmode")
else
  echo "NOTE: $SLEEPMODE_SRC/sleepmode not found; sleep will run without the dream check (the morning summary says so)." >&2
fi

FRIEND_IGNORE=()
if [[ "$FRIEND_BUILD" == 1 ]]; then
  LLAMA_TGZ=vendor/llama/llama-b11946-bin-macos-arm64.tar.gz
  WANT=d618da5e7bbb19077f086e6a7e1d77eab55b9bfd481f7531aadada86d13db9ed
  [[ -f "$LLAMA_TGZ" ]] || curl -fL -o "$LLAMA_TGZ" "https://github.com/ggml-org/llama.cpp/releases/download/b11946/$(basename "$LLAMA_TGZ")"
  [[ "$(shasum -a 256 "$LLAMA_TGZ" | cut -d' ' -f1)" == "$WANT" ]] || { echo "llama.cpp archive checksum mismatch" >&2; exit 1; }
  echo "==> staging the Metal engine (llama.cpp b11946)"
  mkdir -p "$STAGE/llama" && cp "$LLAMA_TGZ" "$STAGE/llama/"
  EXTRA+=(--extra-resource="$STAGE/llama")
  MMPROJ=glim-eyes-mmproj-f16.gguf
  if [[ -f vendor/eyes/$MMPROJ ]]; then
    echo "==> staging Glim's eyes"
    mkdir -p "$STAGE/eyes" && cp "vendor/eyes/$MMPROJ" "$STAGE/eyes/" && cp assets/eyes-NOTICE.txt "$STAGE/eyes/NOTICE.txt"
    EXTRA+=(--extra-resource="$STAGE/eyes")
  else
    echo "WARNING: vendor/eyes/$MMPROJ missing; the friend build will have no eyes." >&2
  fi
  echo "==> compiling the Intel guard (universal)"
  swiftc -O -target arm64-apple-macos12 helper/mac-launcher/launcher.swift -o build/launcher-arm64
  swiftc -O -target x86_64-apple-macos12 helper/mac-launcher/launcher.swift -o build/launcher-x64
  lipo -create build/launcher-arm64 build/launcher-x64 -output build/launcher
  FRIEND_IGNORE=(--ignore='^/src/games/bedwars/(benspc|TOOLS\.md|README\.md)($|/)' --ignore='^/src/games/bedwars/benspc\.js$' --ignore='^/\.gitignore$')
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
  --ignore='^/helper($|/)' --ignore='^/stt($|/)' \
  ${FRIEND_IGNORE[@]+"${FRIEND_IGNORE[@]}"} \
  ${EXTRA[@]+"${EXTRA[@]}"}

APP="build/app/Premonition-darwin-arm64/Premonition.app"
[[ -d "$APP" ]] || { echo "Packaging produced no app at $APP." >&2; exit 1; }
if [[ "$FRIEND_BUILD" == 1 ]]; then
  # the Intel guard becomes CFBundleExecutable "Premonition"; Electron itself moves to Premonition-app (the guard execs it)
  mv "$APP/Contents/MacOS/Premonition" "$APP/Contents/MacOS/Premonition-app"
  cp build/launcher "$APP/Contents/MacOS/Premonition"
fi
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
