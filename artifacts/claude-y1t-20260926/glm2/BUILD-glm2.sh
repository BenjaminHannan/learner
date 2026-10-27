#!/usr/bin/env bash
# y1t glm2 build (Answering-from-memory thread). ADDENDUM-3 rule 4 + ADDENDUM-4 route filter + ADDENDUM-5 Luna rows,
# then GATE-ADDENDUM-1's G1b filter. Counts only are printed. Run from the repo root after
# `git fetch origin main builder-outbox`.
#   bash BUILD-glm2.sh OUTDIR LUNA_RAW
# OUTDIR: where the files go. LUNA_RAW: the Luna rows (raw_luna.jsonl of the last Luna job; route-filtered here).
set -euo pipefail
OUT=$1; LUNA=$2
PY="python3.12 -S -B"   # -S: no site-packages (the scripts are standard-library only)
A=artifacts/claude-y1t-20260926
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
mkdir -p "$OUT/items_unfiltered" "$OUT/items"
echo "python: $(python3.12 --version)"
shasum -a 256 -c $A/SEAL-y1t-add5.sha256.txt > /dev/null || { echo SEAL-MISMATCH; exit 5; }
echo "seal: SEAL-y1t-add5 all OK"
git show origin/builder-outbox:$A/glm/raw.jsonl > "$T/raw_first.jsonl"
git show origin/builder-outbox:$A/topup/raw_new.jsonl > "$T/raw_new.jsonl"
$PY scripts/claude_lis320_seed.py --seed 4027 --n 2400 --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt \
  --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out "$T/seeds.jsonl" > /dev/null
echo "42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43  $T/seeds.jsonl" | shasum -a 256 -c - > /dev/null \
  || { echo SEED-MISMATCH; exit 5; }
echo "split: $($PY scripts/claude_y1t_topup.py split --seeds "$T/seeds.jsonl" --raw "$T/raw_first.jsonl" --out "$T/split")"
echo "route filter, first run's parsed rows: $($PY scripts/claude_y1t_routefilter.py filter --raw "$T/split/raw_ok.jsonl" --out "$OUT/raw_ok_rf.jsonl")"
echo "route filter, GLM top-up rows: $($PY scripts/claude_y1t_routefilter.py filter --raw "$T/raw_new.jsonl" --out "$OUT/raw_new_rf.jsonl")"
echo "route filter, Luna rows: $($PY scripts/claude_y1t_routefilter.py filter --raw "$LUNA" --out "$OUT/raw_luna_rf.jsonl")"
cat "$OUT/raw_new_rf.jsonl" "$OUT/raw_luna_rf.jsonl" > "$T/new_all.jsonl"
echo "merge: $($PY scripts/claude_y1t_topup.py merge --ok "$OUT/raw_ok_rf.jsonl" --new "$T/new_all.jsonl" --out "$OUT/raw_merged.jsonl")"
$PY scripts/claude_lis320_check.py --seeds "$T/seeds.jsonl" --raw "$OUT/raw_merged.jsonl" --out "$OUT/kept.jsonl" \
  --drops "$OUT/drops.jsonl" > "$OUT/check.json"
echo "lis-320 check: $($PY -c 'import json,sys; c=json.load(open(sys.argv[1]))["counts"]; print(json.dumps({k: c[k] for k in ("dialogs", "dialogs_unparsed", "turns", "kept", "dropped")}))' "$OUT/check.json")"
echo "items: $($PY scripts/claude_y1t_data.py items --seeds "$T/seeds.jsonl" --kept "$OUT/kept.jsonl" --out "$OUT/items_unfiltered" | tail -1)"
for s in train dev; do
  echo "G1b $s: $($PY scripts/claude_y1t_gate2.py filter --items "$OUT/items_unfiltered/items_$s.jsonl" --out "$OUT/items/items_$s.jsonl")"
done
(cd "$OUT" && shasum -a 256 raw_ok_rf.jsonl raw_new_rf.jsonl raw_luna_rf.jsonl raw_merged.jsonl kept.jsonl \
  items_unfiltered/items_train.jsonl items_unfiltered/items_dev.jsonl items/items_train.jsonl items/items_dev.jsonl)
