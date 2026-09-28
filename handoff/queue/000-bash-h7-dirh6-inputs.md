STATUS: HELD. DO NOT RUN (helper H7, 2026-09-28 20:35 UTC from date -u). Read-only $0 check the Director may release before h7-dirh6-1-start; the start job repeats these checks itself.
BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
DISK: 1
Owner job (helper H7, Claude). Reads nothing secret and rents nothing. For each of 358u's 4 loop checkpoints it prints the sha256 sealed in artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt (on origin/main), the sha256 of ~/premonition-models/rsn358u/loop-s<S>/final.pt on this Mac, and whether they match; then whether vastai, uv python 3.12, caffeinate and ~/.ssh/id_ed25519.pub exist (existence only: no key, config or credential file is opened or printed). It ends with "4 of 4 Mac checkpoints match their seals" or says what is missing.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
SRU=artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt; MPU=${MPUH6:-$HOME/premonition-models/rsn358u}
date -u; echo "job $(basename "$0" .bo.sh)"
git fetch -q origin main || echo "git fetch failed; using the local origin/main"
git cat-file -e "origin/main:$SRU" 2>/dev/null || { echo "MISSING: $SRU is not on origin/main"; exit 0; }
n=0; for S in 13 14 15 16; do
  sha=$(git show "origin/main:$SRU" | awk -v f="loop-s$S/final.pt" '$2==f {print $1}')
  m=$(shasum -a 256 "$MPU/loop-s$S/final.pt" 2>/dev/null | awk '{print $1}')
  if [ -n "$sha" ] && [ "$m" = "$sha" ]; then n=$((n+1)); echo "loop-s$S/final.pt: sealed $sha, Mac copy matches"; else echo "loop-s$S/final.pt: sealed '${sha:-none}', Mac copy '${m:-missing}': DOES NOT MATCH"; fi
done
echo "$n of 4 Mac checkpoints match their seals"
for c in vastai caffeinate uv pgrep shasum; do command -v $c > /dev/null && echo "have $c" || echo "MISSING $c"; done
U=$(command -v uv || echo "$HOME/.local/bin/uv"); P=$("$U" python find 3.12 2>/dev/null); [ -x "${P:-/nonexistent}" ] && echo "have uv python 3.12" || echo "MISSING uv python 3.12"
[ -f "$HOME/.ssh/id_ed25519.pub" ] && echo "have ~/.ssh/id_ed25519.pub (existence only)" || echo "MISSING ~/.ssh/id_ed25519.pub"
```
