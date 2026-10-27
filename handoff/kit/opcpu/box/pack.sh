#!/bin/bash
# Runs ON the rental (called by the Mac guard/start through ssh): writes W/MANIFEST.sha256 for every small result file and streams a
# tar of exactly those files. Small = under 20 MB; never a .pt; never anything named holdout, test.pt, readpanel or blind.
# Usage: pack.sh <base folder>   (the rental's /root)
B=${1:-/root}; cd "$B" || exit 1
mkdir -p W
# out/ (what each job copied for the repo), W/ (drive state, job stdout, checks), the input list, every job's *.log (its own private archive holds
# thousands of sealed txt/json files that are NOT copied), and drive.log
{ find out W -type f 2>/dev/null; find in -maxdepth 1 -type f 2>/dev/null; find premonition-* -type f -name '*.log' 2>/dev/null; [ -f drive.log ] && echo drive.log; } \
  | grep -v -e '^W/MANIFEST.sha256' -e '^W/FILES.txt' -e '^W/EXCLUDED.txt' -e '^W/ALL.txt' | sort -u > W/ALL.txt
: > W/FILES.txt; : > W/EXCLUDED.txt
while IFS= read -r f; do
  [ -f "$f" ] || continue
  case "$f" in *.pt) echo "$f pt" >> W/EXCLUDED.txt; continue;; esac
  case "$(basename "$f")" in holdout*|test.pt|*readpanel*|*blind*) echo "$f sealed-name" >> W/EXCLUDED.txt; continue;; esac
  [ "$(wc -c < "$f")" -lt 20000000 ] || { echo "$f big" >> W/EXCLUDED.txt; continue; }
  echo "$f" >> W/FILES.txt
done < W/ALL.txt
rm -f W/ALL.txt
echo W/EXCLUDED.txt >> W/FILES.txt; echo W/FILES.txt >> W/FILES.txt   # the record of what was left out, and the list itself
grep -v -e '^W/MANIFEST.sha256$' W/FILES.txt | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256
{ cat W/FILES.txt; echo W/MANIFEST.sha256; } | sort -u | tar -cf - -T -
