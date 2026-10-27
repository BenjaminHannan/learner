BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only BensPC probe after Ben's "tailscale is up" (15:06 UTC 09-27): ssh, GPU memory, python.exe list, C: free, GPU-BUSY.txt, and whether 260's folder shows recent writes. Changes nothing.
```bash
perl -e 'alarm shift; exec @ARGV' 120 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader & tasklist /FI \"IMAGENAME eq python.exe\" /NH & type C:\Users\benja\GPU-BUSY.txt & dir C:\ | find \"free\"" </dev/null 2>&1 | cut -c1-200; echo "rc=$?"
PS='Get-ChildItem C:\Users\benja -Directory | Where-Object { $_.Name -match "358t" } | ForEach-Object { $l = Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3; "$($_.FullName)"; $l | ForEach-Object { "  {0:yyyy-MM-dd HH:mm} {1}" -f $_.LastWriteTime, $_.FullName } }'
ENC=$(printf '%s' "$PS" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
perl -e 'alarm shift; exec @ARGV' 180 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "powershell -NoProfile -EncodedCommand $ENC" </dev/null 2>&1 | cut -c1-200
ls -la $HOME/premonition-watch/queue/260-claude-sleep-358t3pc.* 2>/dev/null; tail -c 600 $HOME/premonition-watch/queue/260-claude-sleep-358t3pc.go1.err.txt 2>/dev/null
date -u
```
