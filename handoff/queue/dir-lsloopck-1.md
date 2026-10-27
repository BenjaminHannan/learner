BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Read-only $0 look (Director, for R2g-3 and R1g-3): do the baseline loop's k64 / k1024 / k16384 checkpoints exist on this Mac? Prints paths and sizes only. Rents nothing, creates nothing, deletes nothing, opens no test files.
```bash
date -u
for d in "$HOME/premonition-models" "$HOME/premonition-watch"; do
  echo "== $d"; find "$d" \( -path "*loop-s*" -o -path "*fewex*" \) \( -name "k64.pt" -o -name "k1024.pt" -o -name "k16384.pt" \) -exec ls -l {} \; 2>/dev/null | awk '{print $5, $9}' | head -40
done
df -h "$HOME" | tail -1
```
