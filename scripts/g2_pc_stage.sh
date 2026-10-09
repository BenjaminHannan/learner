#!/bin/sh
# Stage the group 2 code and caps files on BensPC (inert: copies files only, installs no job, starts nothing). Run from the repo root of branch
# claude/learner-new-g2 AFTER Ben says yes (reviews/pc-handoff-g2-2026-10-09.md). Plain ssh/scp/tar, like scripts/remote_benspc.sh.
set -eu
HOST=${BENSPC_HOST:-benspc}
SRC='C:\Users\benja\custom-io\src-b3g2'
INP='C:\Users\benja\custom-io\work\b3-inputs'
test -z "$(git status --porcelain custom_io)" || { echo "custom_io has uncommitted changes: commit first"; exit 1; }
git fetch -q origin claude/learner-new-g2
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/claude/learner-new-g2)" || { echo "HEAD is not pushed: push claude/learner-new-g2 first"; exit 1; }
echo "staging $(git rev-parse HEAD)"
ssh -o ConnectTimeout=10 "$HOST" "if exist $SRC (echo $SRC already exists: not touching it & exit 1) else mkdir $SRC"
git archive --format=tar HEAD custom_io | ssh "$HOST" "tar -xf - -C $SRC"
scp custom_io/g8a/caps_b3s.json "$HOST:C:/Users/benja/custom-io/work/b3-inputs/caps_b3s.json"
scp custom_io/g8a/caps_b3g2.json "$HOST:C:/Users/benja/custom-io/work/b3-inputs/caps_b3g2.json"
git rev-parse HEAD > /tmp/g2_stage_sha.txt
scp /tmp/g2_stage_sha.txt "$HOST:C:/Users/benja/custom-io/src-b3g2/STAGED-SHA.txt"
echo "check the staged files against the Mac (SHA-256):"
shasum -a 256 custom_io/g8a/caps_b3s.json custom_io/g8a/caps_b3g2.json custom_io/g8a/job.py custom_io/g8a/caps.py custom_io/models/b3g2.py custom_io/models/plain_tf_steps.py
ssh "$HOST" "certutil -hashfile $INP\caps_b3s.json SHA256 & certutil -hashfile $INP\caps_b3g2.json SHA256 & certutil -hashfile $SRC\custom_io\g8a\job.py SHA256 & certutil -hashfile $SRC\custom_io\g8a\caps.py SHA256 & certutil -hashfile $SRC\custom_io\models\b3g2.py SHA256 & certutil -hashfile $SRC\custom_io\models\plain_tf_steps.py SHA256"
