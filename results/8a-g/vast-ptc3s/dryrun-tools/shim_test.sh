#!/bin/bash
# test of the dry-run git shim: fetch the new harness commit into an empty folder the way fetch_sha does
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
export PATH=$B/shimbin:$PATH SHIM_LOCAL_SHA=${1:-1d728b99ef7180c567b285b07ede9aac7a46427a}
cd $B || exit 1
rm -rf shimt; mkdir shimt
d=$B/shimt
git -C $d init -q && git -C $d remote add origin https://github.com/BenjaminHannan/learner || exit 1
git -C $d sparse-checkout init --cone && git -C $d sparse-checkout set results/8a-g/speedup || exit 1
timeout 600 git -C $d fetch -q --depth 1 --filter=blob:none origin $SHIM_LOCAL_SHA && git -C $d checkout -q FETCH_HEAD && git -C $d rev-parse HEAD
sha256sum $d/results/8a-g/speedup/prof/prof_train.py | cut -c1-64
du -sm $d | cut -f1
