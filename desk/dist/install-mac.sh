#!/bin/bash
# Premonition for Mac: one-step installer. Paste this ONE line into Terminal:
#
#   curl -fsSL https://github.com/BenjaminHannan/learner/raw/main/desk/dist/install-mac.sh | bash
#
# What it does (no sudo, no Homebrew, nothing else to install):
#   1. downloads Premonition-mac-arm64.zip into a temporary folder
#   2. unpacks it into /Applications (or ~/Applications when /Applications is not writable), replacing an older Premonition.app
#   3. clears the "downloaded from the internet" flag and signs the app on this Mac (the app is built in the cloud, so it has no seal yet)
#   4. opens Premonition
# Safe to run again: it just reinstalls the newest version. Your chats and settings are kept (they live in ~/Library/Application Support).
#
# For testing:  INSTALL_DIR=/some/folder   install somewhere else
#               ZIP_URL=file:///path.zip   use another zip (any URL curl understands)
#               DRY_RUN=1                  print what would happen and change nothing
#               NO_OPEN=1                  do not launch the app at the end
set -euo pipefail

ZIP_URL="${ZIP_URL:-https://github.com/BenjaminHannan/learner/raw/main/desk/dist/Premonition-mac-arm64.zip}"
APP_NAME="Premonition"
DRY_RUN="${DRY_RUN:-0}"
NO_OPEN="${NO_OPEN:-0}"

say()  { printf '%s\n' "$*"; }
step() { printf '\n[%s] %s\n' "$1" "$2"; }
die()  {
  printf '\nSomething went wrong: %s\n' "$1" >&2
  if [[ -n "${2:-}" ]]; then printf '%s\n' "$2" >&2; fi
  printf 'Nothing is broken: you can paste the same line into Terminal again to retry.\n' >&2
  exit 1
}
# run a command, or only print it in DRY_RUN
run()  { if [[ "$DRY_RUN" == 1 ]]; then printf '  (dry run) %s\n' "$*"; else "$@" </dev/null; fi; }

TMP=""; STAGE=""
cleanup() {
  [[ -n "$STAGE" && -d "$STAGE" ]] && rm -rf "$STAGE"
  [[ -n "$TMP" && -d "$TMP" ]] && rm -rf "$TMP"
  return 0
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# Everything runs inside main(), so bash has read the whole script before it starts (this matters for "curl | bash": a cut-off
# download then runs nothing, and no command can swallow the rest of the script from the pipe).
main() {
  say "Installing Premonition. This takes a minute or two."

  # ---- 0. is this the right kind of Mac? ---------------------------------------------------------------------------------
  if [[ "$(uname -s)" != "Darwin" ]]; then
    [[ "$DRY_RUN" == 1 ]] && say "  (dry run) this is not a Mac; carrying on only to show the steps" || die "this installer is for Macs (this computer says it is $(uname -s))."
  elif [[ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" != "1" ]]; then
    die "this Mac has an Intel chip. Premonition is built for Macs with an Apple chip (M1, M2, M3 or M4)." "Check with the Apple menu > About This Mac."
  fi
  for tool in curl ditto xattr codesign; do
    command -v "$tool" >/dev/null 2>&1 || [[ "$DRY_RUN" == 1 ]] || die "the tool \"$tool\" is missing, which a normal Mac always has." "Is this a Mac with a standard macOS install?"
  done

  # ---- 1. where to put it ----------------------------------------------------------------------------------------------------
  if [[ -n "${INSTALL_DIR:-}" ]]; then
    DEST_DIR="$INSTALL_DIR"
  elif [[ -w /Applications ]]; then
    DEST_DIR=/Applications
  else
    DEST_DIR="$HOME/Applications"
    say "Note: /Applications needs an administrator, so Premonition goes in your own Applications folder instead ($DEST_DIR)."
  fi
  APP="$DEST_DIR/$APP_NAME.app"
  step "1/4" "Downloading Premonition (about 100 MB)"
  say "  from $ZIP_URL"
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/premonition-install.XXXXXX")" || die "could not make a temporary folder."
  ZIP="$TMP/$APP_NAME.zip"
  if [[ "$DRY_RUN" == 1 ]]; then
    say "  (dry run) curl -fL --retry 3 -o $ZIP $ZIP_URL"
  else
    curl -fL --retry 3 --retry-delay 2 --progress-bar -o "$ZIP" "$ZIP_URL" \
      || die "the download did not work." "Check that the Wi-Fi is on and try again. (Address: $ZIP_URL)"
    SIZE="$(wc -c < "$ZIP" | tr -d ' ')"
    # a missing file on GitHub can come back as a small text page; the real zip is ~100 MB
    [[ "$SIZE" -gt 1000000 ]] || die "the downloaded file is only $SIZE bytes, so it is not the app." "Ask Ben to check that the Mac zip is on GitHub."
  fi

  # ---- 2. unpack ---------------------------------------------------------------------------------------------------------------------
  step "2/4" "Putting Premonition in $DEST_DIR"
  run mkdir -p "$DEST_DIR" || die "could not create $DEST_DIR."
  [[ "$DRY_RUN" == 1 || -w "$DEST_DIR" ]] || die "$DEST_DIR is not writable for you." "Try again with:  INSTALL_DIR=\"\$HOME/Applications\" bash"
  # quit a running copy first, so the old app can be replaced
  if [[ "$DRY_RUN" == 1 ]]; then
    say "  (dry run) quit Premonition if it is running"
  elif pgrep -x "$APP_NAME" >/dev/null 2>&1; then
    say "  Premonition is open; closing it first."
    osascript -e "tell application \"$APP_NAME\" to quit" >/dev/null 2>&1 || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do pgrep -x "$APP_NAME" >/dev/null 2>&1 || break; sleep 1; done
    pgrep -x "$APP_NAME" >/dev/null 2>&1 && pkill -x "$APP_NAME" >/dev/null 2>&1 || true
  fi
  STAGE="$DEST_DIR/.$APP_NAME-install.$$"   # inside DEST_DIR so the final move is a plain rename
  run mkdir -p "$STAGE"
  run ditto -x -k "$ZIP" "$STAGE" || die "the downloaded file could not be unpacked." "It may have been cut short. Try again."
  if [[ "$DRY_RUN" != 1 ]]; then
    [[ -d "$STAGE/$APP_NAME.app" ]] || die "the download does not contain $APP_NAME.app." "Ask Ben to rebuild the Mac zip."
  fi
  run rm -rf "$APP"
  run mv "$STAGE/$APP_NAME.app" "$APP" || die "could not move the app into $DEST_DIR."
  run rm -rf "$STAGE"

  # ---- 3. let macOS run it -------------------------------------------------------------------------------------------------------
  step "3/4" "Getting macOS to trust it"
  run xattr -cr "$APP" || die "could not clear the download flag on the app."
  # the cloud build has no valid seal, so seal it here (free, local, no Apple account needed)
  run codesign --force --deep -s - "$APP" || die "could not sign the app on this Mac." "Try: open System Settings > Privacy & Security and look for Open Anyway next to Premonition."

  # ---- 4. open it -----------------------------------------------------------------------------------------------------------------------
  step "4/4" "Opening Premonition"
  if [[ "$NO_OPEN" == 1 ]]; then
    say "  (not opening it: NO_OPEN is set)"
  else
    run open -a "$APP" || die "the app is installed but would not open." "Open it from $DEST_DIR (right-click the icon, then Open)."
  fi

  say ""
  say "Done. Premonition is in $DEST_DIR."
  say "The first time it opens, it downloads its language model (about 1 GB), so keep Wi-Fi on for a few minutes."
  say "It will then ask for two permissions (Screen Recording and Accessibility): say yes, so it can see and use your apps."
  [[ "$DRY_RUN" == 1 ]] && say "(This was a dry run: nothing was downloaded or changed.)"
  exit 0
}
main "$@"
