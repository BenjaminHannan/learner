BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only BensPC look (BensPC's ssh shell is cmd.exe; PowerShell via powershell -NoProfile -Command). Also tests the watcher's GPU gate command.
```bash
S="ssh -o ConnectTimeout=10 -o BatchMode=yes benspc"
echo "--- gate command"; $S 'nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits & tasklist /FI "IMAGENAME eq python.exe" /NH' </dev/null 2>&1; echo "rc=$?"
echo "--- nvidia-smi"; $S nvidia-smi </dev/null 2>&1; echo "rc=$?"
echo "--- marker"; $S 'type C:\Users\benja\GPU-BUSY.txt' </dev/null 2>&1
echo "--- python"; $S "powershell -NoProfile -Command \"Get-CimInstance Win32_Process -Filter \\\"Name like 'python%'\\\" | Select ProcessId,CreationDate,CommandLine | Format-List\"" </dev/null 2>&1 | sed -E 's/(key|token|secret)[=: ]+[^ ]+/\1=[removed]/Ig' | cut -c1-400; echo "rc=$?"
grep -E 'gpu busy' ~/premonition-watch/queue/log.txt ~/premonition-watch/log.txt 2>/dev/null | tail -5
```
