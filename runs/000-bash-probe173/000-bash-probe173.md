BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Owner probe (thought-memory thread, "Memory for its own thoughts", wrote this on 2026-09-27 10:39 UTC). Read-only look at BensPC so that job 173 can be rewritten as a BASH-ONLY job with no builder. It never touches the GPU (no CUDA calls), never starts a GPU run, stops nothing it did not start, and deletes only the two scratch folders it creates (C:/Users/benja/probe173-tmp and C:/Users/benja/probe173-tar). Its only processes on BensPC are short python sleeps (at most 90 s each). It reads the four rsn358i2 nets in place to hash them; it never copies them.
```bash
S="ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes benspc"
GB='"C:\Program Files\Git\bin\bash.exe" -s'
date -u
echo "--- 0 Mac side"; git rev-parse --short origin/main; git log -1 --format=%cd origin/main; grep -E '15[78]-claude-sleep|173-rv390' ~/premonition-watch/queue/log.txt | tail -10
echo "--- 1 cmd.exe: where"
$S 'where bash & where tar & where sha256sum & if exist "C:\Program Files\Git\bin\bash.exe" (echo gitbash-present) else (echo gitbash-missing)' </dev/null 2>&1 | cut -c1-200; echo "rc=${PIPESTATUS[0]}"
echo "--- 2 git bash stdin script"
$S "$GB" <<'EOS' 2>&1 | cut -c1-300
echo stdin-ok; uname -sr; echo "PWD=$(pwd)"; command -v tar sha256sum df nvidia-smi tasklist taskkill powershell
df -h /c | tail -1
ls -d /c/Users/benja/rv390-358i2-* 2>&1
echo "marker: $(cat /c/Users/benja/GPU-BUSY.txt 2>&1)"
EOS
echo "rc=${PIPESTATUS[0]}"
echo "--- 3 gpu (queries only)"
$S 'nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv & nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv & tasklist /FI "IMAGENAME eq python.exe" /NH' </dev/null 2>&1 | cut -c1-200
$S "powershell -NoProfile -Command \"Get-CimInstance Win32_Process -Filter \\\"Name like 'python%'\\\" | Select ProcessId,ParentProcessId,CreationDate,CommandLine | Format-List\"" </dev/null 2>&1 | sed -E 's/(key|token|secret)[=: ]+[^ ]+/\1=[removed]/Ig' | cut -c1-300
echo "--- 4 nets (hashed in place) and python"
$S "$GB" <<'EOS' 2>&1 | cut -c1-300
for s in 1 2 3 4; do sha256sum /c/Users/benja/premonition-models/rsn358i2/loop-s$s/final.pt; done
/c/Users/benja/lis300/venv/Scripts/python.exe -c "import sys, torch; print(sys.version.split()[0], torch.__version__, torch.version.cuda)"
EOS
git show origin/main:artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt | grep -E 'loop-s[1-4]'
echo "--- 5 background, wait, kill (python sleeps only, no GPU)"
$S "$GB" <<'EOS' 2>&1 | cut -c1-300
PY=/c/Users/benja/lis300/venv/Scripts/python.exe; T=/c/Users/benja/probe173-tmp; mkdir -p $T
np() { MSYS_NO_PATHCONV=1 tasklist /FI "IMAGENAME eq python.exe" /NH | grep -c -i python; }
echo "python.exe before: $(np)"
$PY -c "import time; time.sleep(3); print('bg-wait-ok')" > $T/a.txt 2>&1 & p=$!; wait $p; echo "wait rc=$?"; cat $T/a.txt
$PY -c "import time; time.sleep(90)" > $T/b.txt 2>&1 & q=$!; sleep 5; w=$(cat /proc/$q/winpid 2>/dev/null); echo "B: msys $q win $w; python.exe now $(np)"
kill $q; sleep 4; echo "B after msys kill: python.exe $(np); launcher alive: $(MSYS_NO_PATHCONV=1 tasklist /FI "PID eq $w" /NH | grep -c -i python)"
$PY -c "import time; time.sleep(89)" > $T/c.txt 2>&1 & r=$!; sleep 5; v=$(cat /proc/$r/winpid 2>/dev/null); echo "C: msys $r win $v; python.exe now $(np)"
MSYS_NO_PATHCONV=1 taskkill /T /F /PID $v; sleep 4; echo "C after taskkill /T: python.exe $(np)"
wait 2>/dev/null
rm -rf $T; ls -d $T 2>&1
EOS
echo "--- 6 tar in (Windows tar, cmd.exe) and tar out"
git archive origin/main handoff/kit/benspc-task-header.txt | $S 'mkdir C:\Users\benja\probe173-tar && tar -xf - -C C:\Users\benja\probe173-tar && dir /b C:\Users\benja\probe173-tar\handoff\kit' 2>&1; echo "in rc=$?"
git show origin/main:handoff/kit/benspc-task-header.txt | shasum -a 256
M=$(mktemp -d); $S 'tar -cf - -C C:\Users\benja\probe173-tar handoff' </dev/null | tar -x -C "$M"; echo "out rc=$?"; shasum -a 256 "$M/handoff/kit/benspc-task-header.txt"; rm -rf "$M"
$S "$GB" <<'EOS' 2>&1
rm -rf /c/Users/benja/probe173-tar; ls -d /c/Users/benja/probe173-tar 2>&1
echo "python.exe at end: $(MSYS_NO_PATHCONV=1 tasklist /FI "IMAGENAME eq python.exe" /NH | grep -c -i python)"
EOS
date -u
echo PROBE-DONE
```
