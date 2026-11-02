#!/usr/bin/env zsh
# Run on Ben's M1 (~/learner-ops). Builds the code bundle (our branch's sleep2/ + data/recallread/, Sleep-B backbone/ at 005265d6fb),
# copies it to BensPC, unpacks it in WSL at ~/recallread-pc/src and starts recallread_pc.sh detached (it waits for GO-AFTER-V8 itself).
# Small: git archive of three folders only (the Mac disk is tight).
set -e
REPO=${REPO:-$HOME/learner-ops/status-repo}
BR=claude/project-thread-qhf0vt BB=005265d6fb
cd "$REPO"
git fetch -q origin "$BR" claude/project-thread-cqc4bi
T=$(mktemp -d)
git archive "origin/$BR" sleep2 data/recallread | tar -x -C "$T"
git archive "$BB" backbone | tar -x -C "$T"
echo "branch $(git rev-parse origin/$BR) backbone $(git rev-parse $BB)" > "$T/SHAS.txt"
tar -czf "$T.tgz" -C "$T" .
scp "$T.tgz" benspc:C:/Users/benja/pc-jobs/recallread-src.tgz
scp "$T/sleep2/recallread/pc/recallread_pc.sh" benspc:C:/Users/benja/pc-jobs/recallread_pc.sh
rm -rf "$T" "$T.tgz"
ssh benspc "wsl -d Ubuntu -e bash -lc 'rm -rf ~/recallread-pc/src && mkdir -p ~/recallread-pc/src && tar -xzf /mnt/c/Users/benja/pc-jobs/recallread-src.tgz -C ~/recallread-pc/src && sed -i \"s/\\r$//\" /mnt/c/Users/benja/pc-jobs/recallread_pc.sh && cat ~/recallread-pc/src/SHAS.txt'"
~/learner-ops/bin/pc-ps 'Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{CommandLine="wsl.exe -d Ubuntu -e bash /mnt/c/Users/benja/pc-jobs/recallread_pc.sh"}'
echo "started; log C:\\Users\\benja\\pc-jobs\\recallread\\run.log (waits for handoff\\GO-AFTER-V8)"
