#!/bin/bash
# 0.2d-G checks on ONE vast rental (design/v3/30-modes/02d-gates-ADDENDUM-52.md). Runs ON the rental, detached (setsid
# nohup), from /root/r: code from the pinned commit (git archive, sent by kit/mac.sh), G's adapter copied from Ben's Mac
# into /root/r/adapter. Steps:
#   setup   card check; torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0 (rd-378g's rental stack, fail-closed); the
#           base openbmb/MiniCPM5-1B@87179e5c (the only model download; no MiniLM: recall checks use bm25)
#   pins    claude_e2e02d.py unchanged (sha256 below), rd-378g's SEAL (the writer code), the adapter's six files
#   selftests  claude_e2e02d.py (W3, unchanged), claude_e2e02d_g.py (W3/W2 stub), checks.py
#   merge   claude_e2e02d_g.py merge -> W/merge1.json (merged sha256 vs a0fb1c9b...); only if that differs and the
#           adapter is not stored in fp32, a second try without peft's fp32 upcast (W/merge2.json); every try reported
#   w1      claude_rd378_write.py (the CLI rd-378g ran) and checks.py w1 (the build's note step) over the 43 G5 dialogs,
#           same card, same dtype; checks.py compare -> W/w1.json. If W1 is not 504 of 504, the CLI runs a second time
#           (W/w1_cli2.jsonl) to tell run-to-run noise from wiring (report only)
#   w2      checks.py w2 over the 14 chat dialogs -> W/w2.json
#   timing  checks.py timing (2 chat dialogs x 4 user turns, the base MiniCPM5-1B as the talker stand-in)
#   seal    sha256 of every file in W/ into W/MANIFEST.sha256 (the Mac checks it after the copy-back)
# Progress lines go to W/state.txt (the last is DONE or FAILED <why>). G's merged weights stay in /root/r/g (never in W/).
# Nothing is trained; the G5 dialogs are test input only.
set -u
cd "${RROOT:-/root/r}" || exit 1
export PATH=/opt/conda/bin:$PATH
E=artifacts/claude-e2e02dg-20260927
N=artifacts/claude-rd378g-20260926
BASE_SHA_E2E02D=4870333c7ad562f5635b09b7b92629f6fd26cb30b9de5e0f3779891de33a3929   # scripts/claude_e2e02d.py (ADDENDUM-52)
MINRAM_MB=${1:-16000}
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/state.txt; }
seal() { (cd W && find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum > MANIFEST.sha256); }
finish() { seal; touch FINISHED; }    # the Mac copies back only after FINISHED (the manifest is complete by then)
fail() { st "FAILED $*"; finish; exit 1; }
jl() { python -c "import json,sys; v=json.loads(open(sys.argv[1]).read().strip().splitlines()[-1])[sys.argv[2]]; print(','.join(v) if isinstance(v, list) else v)" "$1" "$2" 2>/dev/null; }
st START
[ -e W/steps.txt ] && { st "FAILED W/steps.txt already exists (never a second chain)"; exit 1; }
sl() { echo "$* $(date -u +%FT%TZ)" >> W/steps.txt; }
sl setup start
GL=$(nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader,nounits 2>&1 | head -1)
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; GPU $GL"
mt=$(echo "$GL" | awk -F', ' '{print int($2)}')
[ "${mt:-0}" -ge $(( MINRAM_MB * 95 / 100 )) ] || fail "GPU RAM ${mt:-?} MiB is under $(( MINRAM_MB * 95 / 100 )) MiB"
# attempt 1 (rent-e2e02dg-1) failed here: its host timed out reading download.pytorch.org (15 s reads, 5 retries, 2 tries).
# Now: 60 s reads, 10 retries, 3 tries on the same index rd-378g used; PyPI's torch==2.11.0 only if that index stays
# unreachable (its source and CUDA build are logged; a different build can change the merge bytes and the notes).
export PIP_BREAK_SYSTEM_PACKAGES=1
PIPX="--no-cache-dir -q --timeout 60 --retries 10"
TSRC=""
for t in 1 2 3; do pip install $PIPX torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 >> W/pip.log 2>&1 && { TSRC=download.pytorch.org/whl/cu128; break; }; sleep 20; done
[ -n "$TSRC" ] || { pip install $PIPX torch==2.11.0 >> W/pip.log 2>&1 && TSRC=pypi.org; }
[ -n "$TSRC" ] || fail "pip install torch==2.11.0 (see W/pip.log)"
st "TORCH-SOURCE $TSRC"
pip uninstall -y torchvision torchaudio >> W/pip.log 2>&1
pip install $PIPX transformers==5.17.0 peft==0.21.0 safetensors huggingface_hub accelerate numpy >> W/pip.log 2>&1 || fail "pip install transformers/peft (see W/pip.log)"
pip list 2>/dev/null | grep -iE "^(torch|nvidia-|transformers|peft|safetensors|accelerate) " > W/libs.txt
python -c "import importlib.util as u, torch, transformers, peft; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), 'transformers', transformers.__version__, 'peft', peft.__version__, 'torchvision', u.find_spec('torchvision'))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt && grep -q 'transformers 5.17.0 peft 0.21.0 torchvision None' W/torch.txt || fail "import check: $(tr '\n' ' ' < W/torch.txt | cut -c1-240)"
st "TORCH $(cat W/torch.txt)"
unset HF_HOME HF_HUB_CACHE
HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc'))" > W/hf.txt 2> W/hf.err
BASE=$(sed -n 1p W/hf.txt)
[ -d "$BASE" ] || fail "base download (see W/hf.err)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
st "BASE $BASE"
sl setup end
sl pins start
{
  echo "E2E02D $(sha256sum scripts/claude_e2e02d.py | cut -c1-64) want $BASE_SHA_E2E02D"
  echo "RD378G-SEAL $(sha256sum -c $N/SEAL.sha256.txt 2>/dev/null | grep -c ': OK$') of $(grep -c . $N/SEAL.sha256.txt)"
  echo "WRITER $(grep -E 'claude_rd378_(write|common)\.py' $N/SEAL.sha256.txt | sha256sum -c 2>&1 | tr '\n' ' ')"
  for f in README.md adapter_config.json adapter_model.safetensors chat_template.jinja tokenizer.json tokenizer_config.json; do
    want=$(grep " W/g/adapter/$f\$" $N/vast/SEAL-run.sha256.txt | cut -c1-64); got=$(sha256sum adapter/$f 2>/dev/null | cut -c1-64)
    echo "ADAPTER $f $([ -n "$want" ] && [ "$want" = "$got" ] && echo OK || echo "MISMATCH got=$got want=$want")"
  done
  echo "RENTAL-NOTES $(grep ' W/g5_G.jsonl$' $N/vast/SEAL-run.sha256.txt | cut -c1-64) vs $(sha256sum $N/vast/g5/notes_G.jsonl | cut -c1-64)"
} > W/pins.txt 2>&1
cat W/pins.txt >> W/state.txt
grep -q "^E2E02D $BASE_SHA_E2E02D want" W/pins.txt || fail "scripts/claude_e2e02d.py is not the file ADDENDUM-52 names"
grep -q 'WRITER .*claude_rd378_write.py: OK.*claude_rd378_common.py: OK\|WRITER .*claude_rd378_common.py: OK.*claude_rd378_write.py: OK' W/pins.txt || fail "writer code does not match rd-378g's SEAL"
[ "$(grep -c '^ADAPTER .* OK$' W/pins.txt)" = 6 ] || fail "G's adapter files do not match SEAL-run"
sl pins end
sl selftests start
{ python -B scripts/claude_e2e02d.py selftest; echo "rc=$?"; python -B scripts/claude_e2e02d_g.py selftest; echo "rc=$?"
  python -B $E/checks.py selftest; echo "rc=$?"; } > W/selftests.txt 2>&1
st "SELFTESTS $(grep -E 'SELFTEST (PASS|FAIL)' W/selftests.txt | tr '\n' ' ')"
[ "$(grep -c '^rc=0$' W/selftests.txt)" = 3 ] || fail "a selftest failed (W/selftests.txt)"
sl selftests end
sl merge start
python -B scripts/claude_e2e02d_g.py merge --base "$BASE" --adapter adapter --out g/merged > W/merge1.json 2> W/merge1.err || fail "merge (W/merge1.err)"
MSHA=$(jl W/merge1.json merged_sha256)
MDT=$(jl W/merge1.json adapter_dtypes)
[ -n "$MSHA" ] || fail "merge wrote no sha (W/merge1.json)"
st "MERGE1 $MSHA (want a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed) adapter dtypes $MDT"
if [ "$MSHA" != a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed ] && [ "$MDT" != float32 ] && [ "$MDT" != F32 ]; then
  python -B scripts/claude_e2e02d_g.py merge --base "$BASE" --adapter adapter --out g/merged2 --no-autocast > W/merge2.json 2> W/merge2.err
  M2=$(jl W/merge2.json merged_sha256)
  st "MERGE2 ${M2:-failed} (no fp32 upcast)"
  [ "$M2" = a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed ] && { rm -rf g/merged; mv g/merged2 g/merged; MSHA=$M2; }
fi
export E2E02D_NOTES=$(pwd)/g/merged
WANT=""; [ "$MSHA" = a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed ] || WANT="--want-sha $MSHA"
echo "$MSHA" > W/merged_sha_used.txt
sl merge end
sl w1 start
python -B scripts/claude_rd378_write.py --model g/merged --dialogs $N/g5/dialogs.jsonl --out W/w1_cli.jsonl > W/w1_cli.log 2>&1 || fail "w1 CLI (W/w1_cli.log)"
python -B $E/checks.py w1 --dialogs $N/g5/dialogs.jsonl --out W/w1_build.jsonl $WANT > W/w1_build.log 2>&1 || fail "w1 build note step (W/w1_build.log)"
python -B $E/checks.py compare --dialogs $N/g5/dialogs.jsonl --cli W/w1_cli.jsonl --build W/w1_build.jsonl --rental $N/vast/g5/notes_G.jsonl --out W/w1.json > W/w1_compare.log 2>&1 || fail "w1 compare (W/w1_compare.log)"
st "$(cat W/w1_compare.log | tr '\n' ' ')"
if ! grep -q '"verdict": "PASS"' W/w1.json; then
  python -B scripts/claude_rd378_write.py --model g/merged --dialogs $N/g5/dialogs.jsonl --out W/w1_cli2.jsonl > W/w1_cli2.log 2>&1
  python -B $E/checks.py compare --dialogs $N/g5/dialogs.jsonl --cli W/w1_cli.jsonl --build W/w1_cli2.jsonl --rental $N/vast/g5/notes_G.jsonl --out W/w1_cli_vs_cli2.json > W/w1_cli2_compare.log 2>&1
  st "W1-NOISE CLI vs CLI: $(cat W/w1_cli2_compare.log | tr '\n' ' ')"
fi
sl w1 end
sl w2 start
python -B $E/checks.py w2 --dialogs $N/g5/dialogs.jsonl --cli W/w1_cli.jsonl --out W/w2.json $WANT > W/w2.log 2>&1 || st "w2 failed (W/w2.log)"
st "$(tail -1 W/w2.log)"
sl w2 end
sl timing start
python -B $E/checks.py timing --dialogs $N/g5/dialogs.jsonl --talker "$BASE" --out W/timing.json $WANT > W/timing.log 2>&1 || st "timing failed (W/timing.log)"
st "$(tail -1 W/timing.log)"
sl timing end
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader > W/gpu_end.txt 2>&1
st DONE
finish
