BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only check (Thread manager 15:08 UTC): does BensPC's lis300 venv python import torch with CUDA. Changes nothing.
```bash
perl -e 'alarm shift; exec @ARGV' 180 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "dir C:\Users\benja\lis300\venv\Scripts\python.exe & C:\Users\benja\lis300\venv\Scripts\python.exe -c \"import torch; print(torch.__version__, torch.cuda.is_available())\"" </dev/null 2>&1 | cut -c1-200; echo "rc=$?"
date -u
```
