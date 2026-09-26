#!/usr/bin/env python3
"""bm-398i run 2 (AMEND-1, benchmarks thread, 2026-09-26). The sealed scripts/claude_bm398i_switch.py is run
unchanged except for one memory fix: its _last_logits kept a view of the whole logits tensor (prompt length x
vocabulary, about 0.8 GB per LoCoMo prompt), so 36 stored rows held ~10 GB and the first run was killed for memory
during its last pass, before writing any result. Here the last-position row is copied out instead. The values
compared are identical; only the memory they keep changes.

  python -B scripts/claude_bm398i_run2.py run --data DATA --e20 E20.jsonl --model BASE --out OUT [--adapter ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm398i_switch as M  # noqa: E402


def _last_logits(model_dir: str, it: dict):
    import torch
    tok, model, dev, _ = M.B.plain_model(model_dir)
    enc = M.B._ids(tok, it["system"], it["user"]).to(dev)
    with torch.no_grad():
        return model(**enc).logits[0, -1].float().cpu().clone()


M._last_logits = _last_logits

if __name__ == "__main__":
    sys.exit(M.main())
