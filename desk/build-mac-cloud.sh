#!/usr/bin/env bash
# Cross-build the Mac app from Linux (or any machine with node + zip): dist/Premonition-mac-arm64.zip containing "Premonition.app".
# Counterpart of build-win.sh. The zip holds NO model and NO llama.cpp: the app downloads both on first run (a Mac without
# ~/learner-ops/assistant/serve.sh runs the built-in model, like Windows).
#
# The app is NOT code-signed here (a cloud build has no Mac toolchain), so dist/install-mac.sh ad-hoc signs it on the Mac
# (xattr -cr; codesign --force --deep -s -) after unpacking.
#
# Screen control: the Mac helper (deskhelper) is a Swift binary that only a Mac can compile (build-mac.sh does it with swiftc).
# If an arm64 build of it is committed at vendor/helper/deskhelper it is packed into Contents/Resources; otherwise the app is
# built without it. Without the helper the app still runs: chat, the built-in browser, Glims, memory and the permission prompts
# work; only the tools that look at and click in other apps answer "screen control helper not installed".
#
# Needs: node + npm (the arm64 Electron download is ~100 MB, fetched by electron-packager), and `zip` (or python3).
set -euo pipefail
cd "$(dirname "$0")"

[[ -d node_modules/@electron/packager ]] || { echo "==> npm ci"; npm ci; }

NAME="Premonition"
# The bundle id MUST match build-mac.sh (macOS ties the Accessibility / Screen Recording grants to it).
APP_BUNDLE_ID="com.electron.premonition desk"
OUT=build/mac-cloud
APPDIR="$OUT/$NAME-darwin-arm64"
APP="$APPDIR/$NAME.app"
ZIP="${ZIP_OUT:-$PWD/dist/$NAME-mac-arm64.zip}"

EXTRA=()
HELPER=vendor/helper/deskhelper
if [[ -f "$HELPER" ]]; then
  # a Mac binary must be Mach-O arm64; refuse anything else (a Linux/Windows file by mistake)
  case "$(head -c4 "$HELPER" | od -An -tx1 | tr -d ' \n')" in
    cffaedfe|cafebabe|bebafeca) echo "==> including the committed Mac screen helper ($HELPER)"; EXTRA=(--extra-resource="$HELPER") ;;
    *) echo "$HELPER is not a Mac (Mach-O) binary; remove it or rebuild it on a Mac with: swiftc -O helper/deskhelper.swift -o vendor/helper/deskhelper -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker helper/deskhelper-Info.plist" >&2; exit 1 ;;
  esac
  # the committed binary is rebuilt on a Mac from helper/deskhelper.swift; say so when the source changed since
  if [[ -f "$HELPER.swift.sha256" ]] && [[ "$(cat "$HELPER.swift.sha256")" != "$( (sha256sum helper/deskhelper.swift 2>/dev/null || shasum -a 256 helper/deskhelper.swift) | awk '{print $1}')" ]]; then
    echo "WARNING: helper/deskhelper.swift changed since $HELPER was built; the zip has the OLD helper. Rebuild it on a Mac (build-mac.sh, then copy Contents/Resources/deskhelper here and update $HELPER.swift.sha256)." >&2
  fi
else
  echo "NOTE: $HELPER not found; building WITHOUT screen control (only a Mac can compile helper/deskhelper.swift:" >&2
  echo "      swiftc -O helper/deskhelper.swift -o vendor/helper/deskhelper -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker helper/deskhelper-Info.plist, then commit it and rebuild)." >&2
fi

# the local speech-to-text server rides along as resources/stt, as in build-mac.sh (src/stt.js)
if [[ -f stt/lfm_stt.py ]]; then STT_STAGE="$(mktemp -d)/stt"; mkdir -p "$STT_STAGE" && cp stt/lfm_stt.py "$STT_STAGE/"; EXTRA+=(--extra-resource="$STT_STAGE"); fi

IGNORE=(--ignore='^/(build|test|docs|reviews|scripts|vendor|dist|README\.md|DESIGN\.md|build-mac\.sh|build-mac-cloud\.sh|build-win\.sh|build-win\.ps1)($|/)' --ignore='^/helper($|/)' --ignore='^/stt($|/)')

echo "==> packaging (darwin arm64)"
rm -rf "$OUT"
npx @electron/packager . "$NAME" \
  --app-bundle-id="$APP_BUNDLE_ID" \
  --platform=darwin --arch=arm64 --out="$OUT" --overwrite --icon=assets/icon.icns \
  --extend-info=assets/Info.extra.plist \
  "${IGNORE[@]}" ${EXTRA[@]+"${EXTRA[@]}"} "$@"

[[ -d "$APP" ]] || { echo "Packaging produced no app at $APP." >&2; exit 1; }
[[ -x "$APP/Contents/MacOS/$NAME" ]] || { echo "$APP/Contents/MacOS/$NAME is missing or not executable." >&2; exit 1; }
[[ -f "$APP/Contents/Resources/app/main.js" ]] || { echo "The app code is missing from $APP/Contents/Resources/app." >&2; exit 1; }
[[ ! -e "$APP/Contents/Resources/app/vendor" && ! -e "$APP/Contents/Resources/app/dist" ]] || { echo "vendor/ or dist/ leaked into the app." >&2; exit 1; }
if [[ ${#EXTRA[@]} -gt 0 ]]; then [[ -f "$APP/Contents/Resources/deskhelper" ]] || { echo "deskhelper is missing from $APP/Contents/Resources." >&2; exit 1; }; fi

echo "==> zip (symlinks kept: the Electron frameworks need them)"
mkdir -p "$(dirname "$ZIP")"
rm -f "$ZIP"
if command -v zip >/dev/null 2>&1; then
  (cd "$APPDIR" && zip -qry -9 "$ZIP" "$NAME.app")
else
  # python's zipfile follows symlinks, so write the entries by hand to keep them as links
  python3 - "$ZIP" "$APPDIR" "$NAME.app" <<'PY'
import os, stat, sys, zipfile
zpath, base, top = sys.argv[1:4]
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk(os.path.join(base, top)):
        for n in dirs + files:
            full = os.path.join(root, n); rel = os.path.relpath(full, base); st = os.lstat(full)
            zi = zipfile.ZipInfo(rel + ('/' if stat.S_ISDIR(st.st_mode) else '')); zi.external_attr = (st.st_mode & 0xFFFF) << 16
            if stat.S_ISLNK(st.st_mode): z.writestr(zi, os.readlink(full))
            elif stat.S_ISDIR(st.st_mode): zi.compress_type = zipfile.ZIP_STORED; z.writestr(zi, b'')
            else:
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(full, 'rb') as f: z.writestr(zi, f.read())
PY
fi

# Check what we built: symlinks stored as links and the main program executable (ditto -x -k on the Mac restores both)
python3 -I - "$ZIP" "$NAME" <<'PY'
import stat, sys, zipfile
z = zipfile.ZipFile(sys.argv[1]); name = sys.argv[2]
links = [i for i in z.infolist() if stat.S_ISLNK(i.external_attr >> 16)]
main = z.getinfo(name + '.app/Contents/MacOS/' + name)
if not links: sys.exit('the zip has no symlinks: the Electron frameworks would be broken')
if not (main.external_attr >> 16) & 0o111: sys.exit('the main program lost its executable bit')
print('zip ok: %d entries, %d symlinks, main program executable' % (len(z.infolist()), len(links)))
PY
ls -l "$ZIP"
echo "Done: $ZIP"
echo "Commit it (desk/dist/*.zip is stored in Git LFS) together with dist/install-mac.sh."
