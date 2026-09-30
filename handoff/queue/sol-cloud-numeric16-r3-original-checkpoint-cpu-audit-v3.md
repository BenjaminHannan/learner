BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-numeric16-r3-original-checkpoint-cpu-audit-v3
PUSH: artifacts/sol-cloud-verifier-20260930/numeric16-checkpoint-audit-r3

Additive path-format repair to preserved r2 (`rc=1`, `WindowsPath % tuple` failed before checkpoint hashing or audit invocation). Execute the pinned v3 transport directly from an exact temporary copy fetched from origin/main; do not edit or retry r1 or r2. This remains one CPU-only, read-only audit of the four exact closed r3 checkpoints. No model, optimizer, CUDA, RNG restore, training, checkpoint copy, cleanup, or retries. Stop subsequent checks at the first audit error and preserve PC rc/stdout/stderr and any completed proofs.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
transport_file="$(mktemp -t numeric16-audit)"
expected="61d3addd461f39ac4823f2d60013d7964bc8f5a2c13234a94df3b9bc4040e6f6"
git show origin/main:artifacts/sol-cloud-verifier-20260930/run_numeric_checkpoint_audit_transport_v3.py > "$transport_file"
printf "%s  %s\n" "$expected" "$transport_file" | shasum -a 256 -c -
/usr/bin/python3 -B "$transport_file"
rm -f "$transport_file"
```
