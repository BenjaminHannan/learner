#!/bin/bash
# Fetch the reading list (data files only) from the datasets' official HF hosting.
# Resumable: a file whose local byte size already equals the expected size is skipped.
# Usage: bash download.sh [PARALLEL]   (default 5 concurrent transfers)
set -u
PAR="${1:-5}"
HERE="$(cd "$(dirname "$0")" && pwd)"
RAW="$HERE/raw"
mkdir -p "$RAW"

# repo|path|outname|bytes
read -r -d '' FILES <<'LIST'
SimpleStories/SimpleStories|data/train-00000-of-00007.parquet|simplestories_train-00000.parquet|238015938
SimpleStories/SimpleStories|data/train-00001-of-00007.parquet|simplestories_train-00001.parquet|238000197
SimpleStories/SimpleStories|data/train-00002-of-00007.parquet|simplestories_train-00002.parquet|237741821
SimpleStories/SimpleStories|data/train-00003-of-00007.parquet|simplestories_train-00003.parquet|237658974
SimpleStories/SimpleStories|data/train-00004-of-00007.parquet|simplestories_train-00004.parquet|238085905
SimpleStories/SimpleStories|data/train-00005-of-00007.parquet|simplestories_train-00005.parquet|237848790
SimpleStories/SimpleStories|data/train-00006-of-00007.parquet|simplestories_train-00006.parquet|237678067
SimpleStories/SimpleStories|data/test-00000-of-00001.parquet|simplestories_test-00000.parquet|16838557
roneneldan/TinyStories|TinyStoriesV2-GPT4-train.txt|tinystoriesv2_gpt4_train.txt|2227753162
roneneldan/TinyStories|TinyStoriesV2-GPT4-valid.txt|tinystoriesv2_gpt4_valid.txt|22502601
styfeng/TinyDialogues|tinydialogue_train_ordered.txt|tinydialogues_train_ordered.txt|141294602
styfeng/TinyDialogues|tinydialogue_val_ordered.txt|tinydialogues_val_ordered.txt|25376876
allenai/soda|train.parquet|soda_train.parquet|688771672
allenai/soda|valid.parquet|soda_valid.parquet|82869716
styfeng/TinyDialogues|individual_age_data.zip|tinydialogues_individual_age_data.zip|148892423
LIST

fetch_one () {
  local line="$1"
  IFS='|' read -r repo path out want <<<"$line"
  local dst="$RAW/$out"
  if [ -f "$dst" ] && [ "$(stat -f%z "$dst")" = "$want" ]; then
    echo "skip  $out"; return 0
  fi
  curl -fsSL --retry 5 --retry-delay 3 -C - -o "$dst" \
    "https://huggingface.co/datasets/$repo/resolve/main/$path" || { echo "FAIL  $out"; return 1; }
  local got; got="$(stat -f%z "$dst")"
  if [ "$got" != "$want" ]; then echo "SIZE-MISMATCH $out got=$got want=$want"; return 1; fi
  echo "ok    $out  $got B"
}
export -f fetch_one; export RAW

printf '%s\n' "$FILES" | xargs -P "$PAR" -I{} bash -c 'fetch_one "$@"' _ {}
rc=$?

# Unpack the three kept ages of TinyDialogues (plain .txt, nothing is executed).
Z="$RAW/tinydialogues_individual_age_data.zip"
if [ -f "$Z" ] && [ ! -f "$RAW/tinydialogue_age-10_val.txt" ]; then
  unzip -o -j "$Z" \
    tinydialogue_age-2_train.txt tinydialogue_age-2_val.txt \
    tinydialogue_age-5_train.txt tinydialogue_age-5_val.txt \
    tinydialogue_age-10_train.txt tinydialogue_age-10_val.txt -d "$RAW" >/dev/null
  echo "ok    unpacked TinyDialogues ages 2/5/10 (age 15 left in the zip)"
fi
echo "DOWNLOAD PHASE EXIT $rc"
exit $rc
