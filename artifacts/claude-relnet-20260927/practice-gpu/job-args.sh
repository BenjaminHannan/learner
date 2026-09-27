# The bash script passed to the vast instance as args ["bash","-c",<this>] (runtype args, image
# pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime). Attempts 2 and 3 used this text; attempt 1 lacked the
# 'GPU MEMORY BEFORE RUNS' pre-check and the MEM sampler. The tarball holds the 9 scripts from main at 5cc045e3d.
set -u
echo "=== RELNET-GPU START $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
nproc; free -m | head -2
python -c "import torch,sys;print('python',sys.version.split()[0],'torch',torch.__version__,'cuda',torch.version.cuda,torch.cuda.is_available(),torch.cuda.get_device_name(0))"
mkdir -p /job && cd /job
echo "<base64 of code.tgz, 33,100 characters, elided here; code.tgz sha256 on the next line>" | base64 -d > code.tgz
echo "e1d34404a24c8ad875277876fd8d7bbe2ea32bc4b037047b2ca5a819d36f13c3  code.tgz" | sha256sum -c || { echo "=== RELNET-GPU TARBALL-BAD"; sleep 1800; exit 1; }
tar xzf code.tgz
echo "=== SHA256 of the 9 files"
sha256sum scripts/* | sort -k2
cat > expected.sha <<'SHA'
c00aa62f4bc9ed710019581ee61288256238539c5bcfb6759d17f89c01a958de  scripts/claude_blurt1.py
dc0a0f2d00cb9e495c198abaa21886ab16e1a924033f394060789e32f83ead74  scripts/claude_relnet_gate.py
febac2b96c593b7607c998ad73779065563b7f6e0bea2980fb2fd8c451346183  scripts/claude_relnet_net.py
ec9af5b1144541570cb2f504b4ba1fa61fc72e2f91e15cddd6527da72f343c74  scripts/claude_relnet_practice.py
af350749936eaa084af696cf191c9111cc3aaf03594cd84e8827ba883c9b54d0  scripts/claude_rsn358a_envs.py
99c0b77c13deb32a146abda79784157c6bbad3745a9fa0a65840a12d27ad99bc  scripts/claude_rsn358m_maze.py
f16499155de19639be0ba1240de0b243e3db77bd3644a05008b92af89ab69fa4  scripts/claude_xfer1_adapt.py
e1d6e99b534f50f7f0f45e3ed567d509b1610ab890133cc30e147878b6b82224  scripts/claude_xfer1_bench.py
a8b79315a6bd69453ba9e596259da70cd94cdb32858a475b646dc5f2f9240d10  scripts/claude_xfer1_net.py
SHA
sha256sum -c expected.sha || { echo "=== RELNET-GPU SHA-MISMATCH"; sleep 1800; exit 1; }
export RELNET_CACHE=/job/cache
echo "=== GPU MEMORY BEFORE RUNS"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if [ "$used" -gt 2000 ]; then echo "=== RELNET-GPU GPU-BUSY $used MiB in use before any run"; sleep 1800; exit 1; fi
(while true; do echo "=== MEM $(date -u +%H:%M:%S) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"; sleep 120; done) &
memloop=$!
echo "=== RUNS START $(date -u +%FT%TZ)"
pids=""
for spec in "relnet 0" "relnet 1" "loop 0" "loop 1"; do
  set -- $spec
  timeout 5h python -B scripts/claude_relnet_practice.py --arm $1 --seed $2 --device cuda --threads 2 --out OUT 2>&1 &
  pids="$pids $!"
done
for p in $pids; do wait $p; echo "=== exit $p $?"; done
kill $memloop
echo "=== RUNS END $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader
python -B scripts/claude_relnet_gate.py --dir OUT
for f in OUT/practice-*.json; do
  echo "=== JSON-BEGIN $(basename $f) $(sha256sum $f | cut -d' ' -f1)"
  gzip -9nc $f | base64 -w 76
  echo "=== JSON-END $(basename $f)"
done
echo "=== RELNET-GPU DONE $(date -u +%FT%TZ)"
sleep 7200
