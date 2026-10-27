BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes). TIME CAP: 480 minutes. LABEL: sl-source.
DISK: 1 (two source nets of about 7 MB each stay local)
HELD-UNTIL: (a) origin/main holds artifacts/claude-dir-sl-20260928 including SEAL-code.sha256.txt; (b) the Director has read DESIGN.md, PASSMARKS.md and PASSMARKS-ADDENDUM-1.md and accepts them; (c) the Mac is not busy with another long CPU job (uptime). H12's job h12-stop-1-dev is a different test and does not need to finish first, but both use 2 processes: check load.
Owner job (helper SL, Claude, for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-dir-sl-20260928/DESIGN.md section 4 and PASSMARKS.md Part C. The ONE change: the loop's stop head is trained in sums-and-grids practice on "my answer this round equals my round-48 answer" instead of "my answer is exactly right". This job only builds the two qualified source nets (12,000 steps, batch 64, seeds 0 and 1, exactly as claude_fewex_source_qualify.py builds them) with that target. No maze is used or scored. The adapt stage is job sl-3-adapt.
Measured on the cloud box: 0.68 s per step with the baseline loss and 2.38 s per step with the new one (3.5 times slower); the Mac took 2,773 s and 2,806 s for the baseline sources, so this job is projected at about 2.7 hours (untested). The alarm below is 28,000 s (467 minutes).
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-sl; A=artifacts/claude-dir-sl-20260928; REF=${SL_REF:-origin/main}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check-source.log 2>&1 || { cat $A/seal-check-source.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-source.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
for T in claude_dir_sl_marks claude_dir_sl_selftest; do
  $PY scripts/$T.py $([ $T = claude_dir_sl_marks ] && echo selftest) > $A/SELFTEST-$T-mac.log 2>&1; cat $A/SELFTEST-$T-mac.log
  grep -q '"selftest": "ok"' $A/SELFTEST-$T-mac.log || { echo "STOP: $T selftest failed"; exit 7; }
done
mkdir -p $A/sources
for S in 0 1; do
  O=$W/sl-sources/sl-source-s$S
  [ -f $O/source.json ] && { echo "seed $S: source.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without source.json; delete that folder and start again"; exit 7; }
  nohup perl -e 'alarm shift; exec @ARGV' 28000 $PY scripts/claude_dir_sl_source.py --seed $S --out $O --threads 1 > $A/sources/source-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
for S in 0 1; do
  O=$W/sl-sources/sl-source-s$S
  echo "== seed $S"; tail -3 $A/sources/source-s$S.log
  [ -f $O/source.json ] && [ -f $O/source.pt ] || { echo "STOP: no source for seed $S; report the first traceback in its log verbatim"; exit 8; }
  mkdir -p $A/sources/sl-source-s$S && cp $O/source.json $A/sources/sl-source-s$S/
  echo "seed $S source.pt sha256 $(shasum -a 256 $O/source.pt | awk '{print $1}')" | tee -a $A/sources/SOURCE-SHA256.txt
  $PY - <<PYEOF
import json
d = json.load(open("$O/source.json"))
ok = d["old"]["sums4"]["right"] >= 190 and d["old"]["grids5"]["right"] >= 190 and d["gradient_check"]["nonzero_all"]
print("seed $S V1", "PASS" if ok else "FAIL", "| sums4", d["old"]["sums4"]["right"], "of 200, grids5", d["old"]["grids5"]["right"], "of 200, fixed depth", d["fixed_depth"], "| stop-target stats", d["sl_target_stats"], "| train seconds", round(d["train_seconds"]))
PYEOF
done
cp $A/SELFTEST-*-mac.log $A/seal-check-source.log "$G/$A/" 2>/dev/null
mkdir -p "$G/$A/sources"; cp -R $A/sources/. "$G/$A/sources/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label: sources only, no maze scored): wall time per seed; per seed the V1 line (sums4 and grids5 of 200, gradient check, fixed depth) and the stop-target stats (gradient-round items, how many had the stable target 1, how many the exact target 1, both; label the ratio "how often stable is not the same as right during practice"). A V1 FAIL is a finding: say so and do not run sl-3-adapt for that seed. Checkpoints stay in $HOME/premonition-sl/sl-sources on the Mac; do not push weights.
PUSH: artifacts/claude-dir-sl-20260928/sources artifacts/claude-dir-sl-20260928/SELFTEST-claude_dir_sl_marks-mac.log artifacts/claude-dir-sl-20260928/SELFTEST-claude_dir_sl_selftest-mac.log artifacts/claude-dir-sl-20260928/seal-check-source.log
