#!/bin/zsh
# usage: withlock.sh LOG cmd...
# Waits for the M3 MPS lock (pid-alive check), holds it while cmd runs,
# streams unbuffered output to LOG (preserving warnings), releases on EXIT/INT/TERM
# (terminating cmd before releasing the lock), and exits with cmd's real exit code.
set -u
if [ "$#" -lt 2 ]; then
  echo "usage: withlock.sh LOG cmd..." >&2
  exit 2
fi

L=${PREMONITION_MPS_LOCK:-/tmp/premonition_m3_mps.lock}
POLL=${PREMONITION_LOCK_POLL:-20}
LOG=$1
shift

LOCK_OWNED=0
FIFO=""
CMD_PID=""
TEE_PID=""

cleanup() {
  if [ -n "$FIFO" ]; then
    rm -f "$FIFO"
    FIFO=""
  fi
  if [ "$LOCK_OWNED" -eq 1 ]; then
    owner=$(cut -d' ' -f1 "$L" 2>/dev/null || true)
    if [ "$owner" = "$$" ]; then
      rm -f "$L"
      echo "lock released $(date)"
    else
      echo "lock not ours at release (owner=$owner), left alone $(date)"
    fi
    LOCK_OWNED=0
  fi
}

on_signal() {
  local sig_rc=$1
  if [ -n "$CMD_PID" ]; then
    kill -TERM "$CMD_PID" 2>/dev/null || true
    wait "$CMD_PID" 2>/dev/null || true
    CMD_PID=""
  fi
  if [ -n "$TEE_PID" ]; then
    wait "$TEE_PID" 2>/dev/null || true
    TEE_PID=""
  fi
  cleanup
  exit "$sig_rc"
}

trap cleanup EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM
trap 'on_signal 129' HUP

# Atomic acquire: write full content to a private tmp file, then hard-link it to
# the lock path (ln fails if the lock exists), so the lock is never seen empty.
# Stale reaping is serialized by an mkdir mutex and re-checks the holder first.
TMPL="$L.$$.tmp"
while true; do
  echo "$$ $(date +%s)" > "$TMPL"
  if ln "$TMPL" "$L" 2>/dev/null; then
    rm -f "$TMPL"
    LOCK_OWNED=1
    break
  fi
  rm -f "$TMPL"
  if mkdir "$L.reap" 2>/dev/null; then
    content=$(cat "$L" 2>/dev/null || true)
    pid=${content%% *}
    if [ -z "$content" ]; then
      # empty lock (writer from a non-atomic script mid-write): reap only if older than 30 s
      if [ -f "$L" ] && [ $(( $(date +%s) - $(stat -f %m "$L") )) -gt 30 ]; then rm -f "$L"; fi
    elif ! ps -p "$pid" >/dev/null 2>&1; then
      # holder dead: remove only if the lock still holds the same content we inspected
      [ "$(cat "$L" 2>/dev/null || true)" = "$content" ] && rm -f "$L"
    fi
    rmdir "$L.reap" 2>/dev/null || true
  fi
  [ "$LOCK_OWNED" -eq 1 ] || sleep "$POLL"
done
echo "lock taken $(date)"

FIFO=$(mktemp -u "${TMPDIR:-/tmp}/withlock_fifo.XXXXXX")
mkfifo "$FIFO"
tee "$LOG" < "$FIFO" &
TEE_PID=$!

"$@" > "$FIFO" 2>&1 &
CMD_PID=$!
wait "$CMD_PID"
rc=$?
CMD_PID=""
wait "$TEE_PID" 2>/dev/null || true
TEE_PID=""
exit "$rc"
