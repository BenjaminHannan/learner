BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-numeric16-r3-original-checkpoint-cpu-audit-v2
PUSH: artifacts/sol-cloud-verifier-20260930/numeric16-checkpoint-audit-r2

Additive shell-bootstrap repair to preserved r1 (`rc=2`, shell quote parse error before the PC call). Execute the pinned transport directly from an exact temporary copy fetched from origin/main; do not edit or retry r1. This remains one CPU-only, read-only audit of the four exact closed r3 checkpoints. No model, optimizer, CUDA, RNG restore, training, checkpoint copy, cleanup, or retries. Stop subsequent checks at the first audit error and preserve PC rc/stdout/stderr and any completed proofs.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
transport_file="$(mktemp -t numeric16-audit)"
expected="5f46f3a55566f8a1daa4b83cc09381da3f17d731984d31c230d2c6afab38f2be"
git show origin/main:artifacts/sol-cloud-verifier-20260930/run_numeric_checkpoint_audit_transport_v2.py > "$transport_file"
printf "%s  %s\n" "$expected" "$transport_file" | shasum -a 256 -c -
/usr/bin/python3 -B "$transport_file"
rm -f "$transport_file"
```
