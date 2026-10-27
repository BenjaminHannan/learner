#!/usr/bin/env bash
# Build "Premonition Desk.app" on an Apple-silicon Mac and install it to /Applications.
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
  swiftc -O helper/deskhelper.swift -o build/deskhelper
  EXTRA=(--extra-resource=build/deskhelper)
else
  echo "WARNING: swiftc or helper/deskhelper.swift missing; building without screen control (install Xcode command line tools: xcode-select --install)." >&2
fi

echo "==> packaging"
rm -rf build/app
npx @electron/packager . "Premonition Desk" \
  --platform=darwin --arch=arm64 --out=build/app --overwrite --icon=assets/icon.icns \
  --ignore='^/(build|test|reviews|scripts|README\.md|DESIGN\.md|build-mac\.sh)($|/)' \
  --ignore='^/helper($|/)' \
  ${EXTRA[@]+"${EXTRA[@]}"}

APP="build/app/Premonition Desk-darwin-arm64/Premonition Desk.app"
[[ -d "$APP" ]] || { echo "Packaging produced no app at $APP." >&2; exit 1; }
echo "==> ad-hoc codesign"
codesign --force --deep -s - "$APP"

echo "==> installing to /Applications"
rm -rf "/Applications/Premonition Desk.app"
cp -R "$APP" /Applications/
echo "Done. Open it from /Applications (first launch: right-click > Open if macOS complains)."
