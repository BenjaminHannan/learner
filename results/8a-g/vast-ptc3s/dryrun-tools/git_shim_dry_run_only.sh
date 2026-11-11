#!/bin/bash
# DRY-RUN SHIM, never used on Vast: `git ... fetch ... origin <SHA>` for the one commit named in SHIM_LOCAL_SHA (the new harness commit, not on GitHub yet) is served from the local repository
# (file:///home/user/learner/.git, objects only, nothing is pushed); the blob filter is dropped because the new blobs do not exist on GitHub. Every other git call is the real git.
REAL=/usr/bin/git
H=${SHIM_LOCAL_SHA:-}
if [ -n "$H" ]; then
  for a in "$@"; do
    if [ "$a" = "$H" ]; then
      args=()
      for b in "$@"; do
        [ "$b" = origin ] && b=file:///home/user/learner/.git
        [ "$b" = --filter=blob:none ] && continue
        args+=("$b")
      done
      echo "[git shim] $H fetched from the local repository" >&2
      GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=uploadpack.allowAnySHA1InWant GIT_CONFIG_VALUE_0=true exec $REAL "${args[@]}"
    fi
  done
fi
exec $REAL "$@"
