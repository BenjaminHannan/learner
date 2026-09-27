BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director job, no LLM builder (rungo5 BASH-ONLY route). Touches the runner stop files of 172 and of my two hung builder jobs (no kill), then a read-only BensPC look.
```bash
Q=~/premonition-watch/queue
for j in 172-rv390-358i2-pc-c 000-stop-172-rv390 000-probe-benspc-gpu-0827; do touch "$Q/$j.stop"; done
ls -l "$Q"/172-rv390-358i2-pc-c.* | awk '{print $5, $6, $7, $8, $9}'
grep -E '172-rv390|000-stop-172|000-probe-benspc-gpu' "$Q/log.txt" | tail -10
echo "--- BensPC"
ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "nvidia-smi; type C:\Users\benja\GPU-BUSY.txt; Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Select ProcessId,CreationDate,CommandLine | Format-List" < /dev/null 2>&1 | sed -E 's/(key|token|secret)[=: ]+[^ ]+/\1=[removed]/Ig' | cut -c1-400
echo "ssh rc=$?"
```
