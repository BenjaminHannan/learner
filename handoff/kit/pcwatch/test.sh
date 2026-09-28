#!/bin/bash
# Fake-remote test of watcher.sh (no GPU, no network, no token). Run: bash handoff/kit/pcwatch/test.sh
# Builds a bare "origin", puts fake jobs on main, runs the watcher in ONCE mode round after round, checks the results.
set -u
HERE=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export PCW_HOME=$T/home BUSYF=$T/GPU-BUSY.txt REPO_URL=$T/origin.git CYCLE=1 NO_SELF_UPDATE=1 ONCE=1
git init -q --bare "$T/origin.git"; git init -q "$T/seed"; cd "$T/seed"; git config user.email t@t; git config user.name t
mkdir -p handoff/pcqueue handoff/queue handoff/kit/pcwatch; cp "$HERE/watcher.sh" handoff/kit/pcwatch/
mk() { printf 'GPU: yes\nRUNNER: pc\nTIME CAP: 1 minutes\nPUSH: out/%s\n```bash\n%s\n```\n' "$1" "$2" > "handoff/pcqueue/$1.md"; }
mk a-ok 'mkdir -p out/a-ok; echo hello > out/a-ok/r.txt; head -c 6000000 /dev/zero > out/a-ok/big.bin.txt; echo done'
mk b-fetchfail 'if [ ! -e "$JOBDIR/../b.flag" ]; then touch "$JOBDIR/../b.flag"; echo "fetch failed"; exit 75; fi; mkdir -p out/b-fetchfail; echo second-try > out/b-fetchfail/r.txt'
mk c-fail 'echo boom; exit 3'
printf 'GPU: yes\n```bash\necho mac job must not run\n```\n' > handoff/queue/mac-only.md
git add -A; git commit -qm seed; git push -q "$T/origin.git" HEAD:refs/heads/main
W=$PCW_HOME; run() { bash "$HERE/watcher.sh"; sleep 1; }
for i in 1 2 3 4 5 6 7 8; do run; done
echo "--- stale-marker round"; mkdir -p "$W/state"; echo 999999 > "$W/state/zz-stale.running"; run; run
ok=0; bad=0; chk() { if eval "$2"; then echo "PASS $1"; ok=$((ok+1)); else echo "FAIL $1"; bad=$((bad+1)); fi; }
L() { git -C "$T/origin.git" ls-tree -r --name-only pc-outbox 2>/dev/null; }
chk "pc-outbox branch exists"        '[ -n "$(L)" ]'
chk "a-ok result pushed"             'L | grep -q "^out/a-ok/r.txt$"'
chk "file over 5 MB not pushed"      '! L | grep -q big.bin'
chk "runs/a-ok/a-ok.exit pushed"     'L | grep -q "^runs/a-ok/a-ok.exit$"'
chk "status file pushed"             'L | grep -q "^status/pc-watcher.txt$"'
chk "exit 75 retried, not marked done" 'grep -q "b-fetchfail rc=75, retry 1" "$W/watch.log"'
chk "retried job did not run again before backoff" '! L | grep -q "^out/b-fetchfail"'
chk "failing job marked done rc=3"   'grep -q "c-fail finished rc=3" "$W/watch.log"'
chk "Mac-only job (no RUNNER: pc) never run" '! grep -q "mac-only" "$W/watch.log"'
chk "stale marker cleared"           'grep -q "stale marker cleared: zz-stale" "$W/watch.log"'
chk "GPU-BUSY.txt removed after jobs" '[ ! -f "$BUSYF" ]'
chk "no token-like text in log/status" '! grep -qi "ghp_\|github_pat" "$W/watch.log" "$W/status.txt"'
echo "$ok passed, $bad failed"; echo "--- log"; cat "$W/watch.log"; echo "--- status"; head -20 "$W/status.txt"
[ "$bad" = 0 ]
