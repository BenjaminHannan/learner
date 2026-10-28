#!/usr/bin/env bash
# Cross-build the Windows app from Linux/macOS: build/Premonition-win32-x64.zip containing "Premonition.exe".
# The zip holds NO model and NO Python: those download on first run.
# Needs node + npm (the Electron download is ~100 MB). Embedding the .ico into the .exe uses rcedit, which needs wine on
# Linux; without wine the build still works and the exe just keeps Electron's default icon (a warning says so).
set -euo pipefail
cd "$(dirname "$0")"

[[ -d node_modules/@electron/packager ]] || { echo "==> npm ci"; npm ci; }

echo "==> icon"
node scripts/make-ico.js assets/icon.png build/icon.ico

# The screen helper: deskhelper.exe (C#, .NET Framework 4.8). Compiled with mono's mcs when it is installed (helper/win/build.sh),
# otherwise the committed vendor/helper/deskhelper.exe is used. (A PowerShell script was flagged by Windows Defender.)
if command -v mcs >/dev/null 2>&1; then
  echo "==> compiling deskhelper.exe"
  helper/win/build.sh
elif [[ -f vendor/helper/deskhelper.exe ]]; then
  echo "NOTE: mcs not found; using the committed vendor/helper/deskhelper.exe (apt-get install -y mono-mcs to rebuild it)." >&2
else
  echo "vendor/helper/deskhelper.exe is missing and mcs is not installed (apt-get install -y mono-mcs)." >&2; exit 1
fi

# The sleep trainer (a Python package, no model, no Python) rides along as a resource: resources/sleepmlx
STAGE=build/stage; rm -rf "$STAGE"; mkdir -p "$STAGE"
EXTRA=()
if [[ -d ../sleepmlx ]]; then
  echo "==> staging sleepmlx"
  (cd .. && tar -c --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' sleepmlx) | tar -x -C "$STAGE"
  EXTRA=(--extra-resource="$STAGE/sleepmlx")
else
  echo "WARNING: ../sleepmlx not found; the Windows build will not be able to sleep." >&2
fi

# Our own CPU llama-server.exe (LFM3-capable master build) rides along as resources/llama, until an official release has LFM3
if [[ -f vendor/llama/llama-server.exe ]]; then
  echo "==> staging bundled llama-server.exe"
  mkdir -p "$STAGE/llama" && cp vendor/llama/llama-server.exe vendor/llama/LICENSE* "$STAGE/llama/" 2>/dev/null || cp vendor/llama/llama-server.exe "$STAGE/llama/"
  EXTRA+=(--extra-resource="$STAGE/llama")
else
  echo "WARNING: vendor/llama/llama-server.exe not found; the app will need an official llama.cpp release with LFM3." >&2
fi

IGNORE=(--ignore='^/(build|test|docs|reviews|scripts|vendor|dist|README\.md|DESIGN\.md|build-mac\.sh|build-mac-cloud\.sh|build-win\.sh|build-win\.ps1)($|/)' --ignore='^/helper($|/)')
OUT=build/win
NAME="Premonition"
DIR="$OUT/$NAME-win32-x64"
pack() {
  rm -rf "$OUT"
  npx @electron/packager . "$NAME" --platform=win32 --arch=x64 --out="$OUT" --overwrite \
    --extra-resource=vendor/helper/deskhelper.exe ${EXTRA[@]+"${EXTRA[@]}"} \
    --win32metadata.ProductName="$NAME" --win32metadata.FileDescription="$NAME" --win32metadata.InternalName="$NAME" --win32metadata.OriginalFilename="$NAME.exe" \
    "${IGNORE[@]}" "$@"
}

echo "==> packaging (win32 x64)"
if ! pack --icon=build/icon.ico; then
  echo "WARNING: packaging with the icon failed (rcedit needs wine on Linux). Retrying without the icon: $NAME.exe will have Electron's default icon." >&2
  pack
fi

[[ -f "$DIR/$NAME.exe" ]] || { echo "Packaging produced no $NAME.exe in $DIR." >&2; exit 1; }
[[ -f "$DIR/resources/deskhelper.exe" ]] || { echo "deskhelper.exe is missing from $DIR/resources." >&2; exit 1; }
[[ ! -e "$DIR/resources/deskhelper.ps1" ]] || { echo "deskhelper.ps1 must not ship (Defender flags it)." >&2; exit 1; }

echo "==> zip"
ZIP="$PWD/build/$NAME-win32-x64.zip"
rm -f "$ZIP"
if command -v zip >/dev/null 2>&1; then
  (cd "$OUT" && zip -qr -9 "$ZIP" "$NAME-win32-x64")
else
  python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2], sys.argv[3])" "${ZIP%.zip}" "$OUT" "$NAME-win32-x64"
fi
ls -l "$ZIP"
echo "Done: $ZIP  (unzip anywhere on the PC, run $NAME-win32-x64\\$NAME.exe)"
